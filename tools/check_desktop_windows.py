"""Install and remove one existing preview in a new test folder, preserving user registrations and data."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import winreg


APP_ID = "io.github.daniel_g_carrasco.meridiana"
UNINSTALL = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{BC7761C0-15BD-40FC-87D1-98D297118957}_is1"
REGISTRY = [UNINSTALL, r"Software\Classes\.mer", r"Software\Classes\Meridiana.Project",
            r"Software\Classes\Applications\Meridiana.exe"]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def tree(root, path: str, view: int):
    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_READ | view) as key:
            values, children = {}, {}
            for index in range(winreg.QueryInfoKey(key)[1]):
                name, value, kind = winreg.EnumValue(key, index)
                values[name] = [kind, value.hex() if isinstance(value, bytes) else value]
            for index in range(winreg.QueryInfoKey(key)[0]):
                name = winreg.EnumKey(key, index)
                children[name] = tree(root, path + "\\" + name, view)
            return {"values": values, "children": children}
    except FileNotFoundError:
        return None


def registry() -> dict:
    return {f"{name}-{bits}/{path}": tree(root, path, view)
            for name, root in (("HKCU", winreg.HKEY_CURRENT_USER), ("HKLM", winreg.HKEY_LOCAL_MACHINE))
            for bits, view in ((32, winreg.KEY_WOW64_32KEY), (64, winreg.KEY_WOW64_64KEY))
            for path in REGISTRY}


def shortcuts() -> dict:
    folders = set()
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        key = tree(hive, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders", 0)
        if key:
            for name, (_kind, value) in key["values"].items():
                if name in ("Desktop", "Programs", "Common Desktop", "Common Programs"):
                    folders.add(Path(os.path.expandvars(value)))
    paths = [path for folder in folders for path in (folder / "Meridiana.lnk",
                                                      folder / "Meridiana" / "Meridiana.lnk")]
    return {str(path): digest(path) if path.is_file() else None for path in paths}


def check_mutex() -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenMutexW.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR)
    kernel.OpenMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenMutexW(0x00100000, False, APP_ID)
    error = ctypes.get_last_error()
    if handle:
        kernel.CloseHandle(handle)
        raise RuntimeError("A real app is running; the installer could restart it")
    if error != 2:
        raise RuntimeError(f"The app mutex could not be checked safely: {error}")


def foreground() -> int:
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetForegroundWindow.argtypes = ()
    user.GetForegroundWindow.restype = wintypes.HWND
    return user.GetForegroundWindow() or 0


def run(command: list[str], env: dict, log: Path, limit: int) -> int:
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    started = time.perf_counter()
    with log.open("x", encoding="utf-8") as output:
        output.write(json.dumps(command) + "\n")
        output.flush()
        result = subprocess.run(command, env=env, stdout=output, stderr=subprocess.STDOUT,
                                timeout=limit, startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
        output.write(f"\nexit={result.returncode}, elapsed={time.perf_counter() - started:.3f}s\n")
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--receipt", type=Path, help="Explicit receipt of a separately rebuilt test installer")
    parser.add_argument("--platform", choices=("offscreen", "windows"), default="offscreen",
                        help="Native Windows self-test still starts hidden with SW_HIDE")
    parser.add_argument("--expected-commit", help="Require the package receipt to identify this source commit")
    parser.add_argument("--bundle", type=Path, help="Require the installed executable to match this frozen bundle")
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise RuntimeError("Refusing an existing test revision")
    out.mkdir(parents=True)
    app = out / "installed-app"
    if app.exists() or not app.resolve().is_relative_to(out):
        raise RuntimeError("The install target is not a new child of the test folder")
    state = {"target": str(app), "registry_before": registry(), "shortcuts_before": shortcuts()}
    for key, value in state["registry_before"].items():
        if value is not None and (UNINSTALL in key or r"Software\Classes\Applications\Meridiana.exe" in key):
            raise RuntimeError(f"Refusing an existing app registration: {key}")
    check_mutex()
    packages = list(args.packages.glob("meridiana-setup-*-windows-x64.exe"))
    if len(packages) != 1:
        raise RuntimeError("Select a package revision containing exactly one installer")
    package = packages[0]
    receipts = [args.receipt] if args.receipt else list(args.packages.glob("package-receipt-*.json"))
    if len(receipts) != 1:
        raise RuntimeError("Select exactly one package receipt with --receipt")
    receipt = json.loads(receipts[0].read_text(encoding="utf-8-sig"))
    if args.expected_commit and receipt.get("application_commit") != args.expected_commit:
        raise RuntimeError("The package receipt does not match the expected source freeze")
    state["package_receipt"] = str(receipts[0].resolve())
    state["application_commit"] = receipt.get("application_commit")
    expected = next(item["sha256"] for item in receipt["artifacts"] if item["name"] == package.name)
    state["package"] = {"path": str(package), "sha256": digest(package)}
    if state["package"]["sha256"] != expected:
        raise RuntimeError("Package checksum does not match its receipt")
    env = dict(os.environ)
    for key in ("TEMP", "TMP", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
        folder = out / key.lower()
        folder.mkdir()
        env[key] = str(folder)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["MERIDIANA_SELF_TEST_PLATFORM"] = args.platform
    state["selftest_platform"] = args.platform
    state["startup_show"] = 0
    if args.platform == "windows":
        env["MERIDIANA_SCREENSHOT"] = str(out / "installed-native-window.png")
    marker = Path(env["XDG_CONFIG_HOME"]) / "user-data-marker.txt"
    marker.write_text("Isolated user data must survive uninstall.\n", encoding="utf-8")
    state["data_marker_sha256"] = digest(marker)
    try:
        command = [str(package.resolve()), "/CURRENTUSER", "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                   "/NOCLOSEAPPLICATIONS", "/NORESTARTAPPLICATIONS", "/NOICONS", "/TASKS=",
                   f"/DIR={app}", f"/LOG={out / 'inno-install.log'}"]
        state["install_exit"] = run(command, env, out / "install-process.log", 180)
        state["registry_installed"] = registry()
        state["shortcuts_installed"] = shortcuts()
        if state["install_exit"] != 0 or not (app / "Meridiana.exe").is_file():
            raise RuntimeError("The isolated installation did not complete")
        state["installed_executable_sha256"] = digest(app / "Meridiana.exe")
        if args.bundle:
            state["bundle"] = str(args.bundle.resolve())
            state["bundle_executable_sha256"] = digest(args.bundle / "Meridiana.exe")
            state["installed_matches_bundle"] = state["installed_executable_sha256"] == state["bundle_executable_sha256"]
            if not state["installed_matches_bundle"]:
                raise RuntimeError("The installed executable does not match the selected frozen bundle")
        for key, value in state["registry_before"].items():
            if r"Software\Classes\.mer" in key or r"Software\Classes\Meridiana.Project" in key:
                if state["registry_installed"][key] != value:
                    raise RuntimeError(f"An association changed: {key}")
        if state["shortcuts_installed"] != state["shortcuts_before"]:
            raise RuntimeError("A desktop or Start Menu shortcut changed")
        foreground_before = foreground()
        state["selftest_exit"] = run([str(app / "Meridiana.exe"), "--self-test", str(out / "installed-selftest.txt")],
                                     env, out / "installed-selftest-runtime.log", 180)
        state["selftest_foreground_unchanged"] = foreground_before == foreground()
        if args.platform == "windows":
            selftest = (out / "installed-selftest.txt").read_text(encoding="utf-8")
            state["native_graphics_passed"] = "PASS 3D graphics:" in selftest
            state["native_frame_passed"] = "PASS 3D first frame:" in selftest
    finally:
        uninstaller = app / "unins000.exe"
        if uninstaller.is_file():
            if not uninstaller.resolve().is_relative_to(out) or app.parent.resolve() != out:
                raise RuntimeError("Refusing an uninstaller outside the verified test directory")
            state["uninstall_exit"] = run([str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                                           f"/LOG={out / 'inno-uninstall.log'}"],
                                          env, out / "uninstall-process.log", 120)
        state["registry_after"] = registry()
        state["shortcuts_after"] = shortcuts()
        state["package_unchanged"] = digest(package) == expected
        state["data_preserved"] = marker.is_file() and digest(marker) == state["data_marker_sha256"]
        state["app_executable_removed"] = not (app / "Meridiana.exe").exists()
        state["registry_restored"] = state["registry_after"] == state["registry_before"]
        state["shortcuts_restored"] = state["shortcuts_after"] == state["shortcuts_before"]
        (out / "receipt.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    passed = (state.get("install_exit") == state.get("uninstall_exit") == state.get("selftest_exit") == 0
              and all(state[k] for k in ("package_unchanged", "data_preserved", "app_executable_removed",
                                         "registry_restored", "shortcuts_restored")))
    if args.platform == "windows":
        passed = passed and all(state.get(key) for key in ("selftest_foreground_unchanged", "native_graphics_passed",
                                                            "native_frame_passed"))
    print(json.dumps({k: v for k, v in state.items() if not k.startswith(("registry", "shortcuts"))}, indent=2))
    print("PASS" if passed else "FAIL", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
