"""Install, run and uninstall an existing bundle in a private Flatpak user profile, using cached runtimes only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


APP = "io.github.daniel_g_carrasco.meridiana"
RUNTIME = "runtime/org.kde.Platform/x86_64/6.11"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(command: list[str], env: dict, log: Path, timeout: int = 180) -> str:
    print("Running:", command, flush=True)
    result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            encoding="utf-8", errors="replace", timeout=timeout)
    log.write_text(json.dumps(command) + "\n" + result.stdout + f"\nexit={result.returncode}\n", encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"{command[0]} failed, see {log}: {result.stdout[-1200:]}")
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    base = Path(tempfile.mkdtemp(prefix="meridiana-installed-check-20261029-R02-", dir="/home/daniel"))
    environment = dict(os.environ)
    original_refs = run(["flatpak", "list", "--columns=ref,installation"], environment, out / "original-refs-before.log")
    original_repo = Path("/home/daniel/.local/share/flatpak/repo")
    runtime_commit = run(["ostree", f"--repo={original_repo}", "rev-parse", "deploy/" + RUNTIME],
                         environment, out / "cached-runtime-commit.log").strip()
    cache_repo = base / "runtime-repo"
    run(["ostree", f"--repo={cache_repo}", "init", "--mode=archive-z2"], environment, out / "runtime-init.log")
    run(["ostree", f"--repo={cache_repo}", "pull-local", str(original_repo), runtime_commit],
        environment, out / "runtime-seed.log")
    run(["ostree", f"--repo={cache_repo}", "refs", "--create=" + RUNTIME, runtime_commit],
        environment, out / "runtime-ref.log")
    run(["flatpak", "build-update-repo", str(cache_repo)], environment, out / "runtime-summary.log")
    env = dict(environment)
    for variable, relative in (("HOME", "private-home"), ("FLATPAK_USER_DIR", "installation"),
                               ("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"),
                               ("XDG_STATE_HOME", "state"), ("XDG_CACHE_HOME", "cache")):
        location = base / relative
        location.mkdir()
        env[variable] = str(location)
    package = next(args.packages.glob("*-linux-x86_64.flatpak"))
    expected = next(item["sha256"] for item in json.loads(
        (args.packages / "package-receipt-R04.json").read_text(encoding="utf-8-sig"))["artifacts"]
                    if item["name"] == package.name)
    if digest(package) != expected:
        raise RuntimeError("The existing bundle differs from its receipt")
    result = {"base": str(base), "package": str(package), "sha256": expected, "runtime_commit": runtime_commit}
    run(["flatpak", "remote-add", "--user", "--no-gpg-verify", "runtime-cache", cache_repo.as_uri()],
        env, out / "remote-add.log")
    run(["flatpak", "install", "--user", "--noninteractive", "--no-related", "--no-deps", "runtime-cache", RUNTIME],
        env, out / "runtime-install.log")
    marker = base / "config" / "preserve-after-uninstall.txt"
    marker.write_text("Private test data must survive app removal.\n", encoding="utf-8")
    result["data_sha256"] = digest(marker)
    try:
        run(["flatpak", "install", "--user", "--noninteractive", "--no-related", "--no-deps", str(package)],
            env, out / "app-install.log")
        run(["flatpak", "info", "--user", APP], env, out / "installed-info.log")
        result["installed"] = True
        exports = base / "installation" / "exports" / "share"
        result["desktop_exported"] = (exports / "applications" / f"{APP}.desktop").exists()
        run(["flatpak", "run", "--user", "--unshare=network", "--nofilesystem=home", f"--filesystem={base}",
             "--nosocket=wayland", "--nosocket=x11", "--nosocket=fallback-x11", "--nosocket=pulseaudio",
             "--env=QT_QPA_PLATFORM=offscreen", APP, "--self-test", str(base / "installed-selftest.txt")],
            env, out / "installed-selftest-runtime.log")
        (out / "installed-selftest.txt").write_bytes((base / "installed-selftest.txt").read_bytes())
        result["selftest_passed"] = True
    finally:
        if result.get("installed"):
            run(["flatpak", "uninstall", "--user", "--noninteractive", APP], env, out / "app-uninstall.log")
        listed = run(["flatpak", "list", "--user", "--app", "--columns=application"], env, out / "private-refs-after.log")
        result["app_removed"] = APP not in listed.splitlines()
        result["desktop_removed"] = not (base / "installation" / "exports" / "share" / "applications" / f"{APP}.desktop").exists()
        result["data_preserved"] = marker.is_file() and digest(marker) == result["data_sha256"]
        result["package_unchanged"] = digest(package) == expected
        refs_after = run(["flatpak", "list", "--columns=ref,installation"], environment, out / "original-refs-after.log")
        result["original_installation_unchanged"] = original_refs == refs_after
        (out / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if all(result.get(k) for k in ("installed", "selftest_passed", "app_removed", "desktop_removed",
                                           "data_preserved", "package_unchanged", "original_installation_unchanged")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
