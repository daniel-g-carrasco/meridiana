"""A LibreOffice of the computer as a measure for the editable files (R506): it opens the ODT or the DOCX the program
wrote, hidden, in a LibreOffice of its own (headless, its own profile: a LibreOffice the user has open is not
touched), lays it out and says the size of each formula and the page of each entry of the contents (lo_measure.py,
run by LibreOffice's Python). The program writes those numbers into its own file (odt.apply, word.apply): the file
stays the program's, LibreOffice saves nothing.

    found = measure(path)        # {"formulas": {frame name: [w, h] in 1/100 mm}, "toc": [[text, page]], "pages": n}
                                 # or None: no LibreOffice, or it did not answer in time

Nothing here is needed: without LibreOffice the files are written as before, the contents without page numbers until
they are updated."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from .. import log

SCRIPT = Path(__file__).with_name("lo_measure.py")
SECONDS = 150


def found() -> tuple[Path, Path] | None:
    """(LibreOffice's Python, soffice) when there is a LibreOffice that can run the measure; None otherwise.
    MERIDIANA_LIBREOFFICE names its «program» folder; MERIDIANA_NO_LIBREOFFICE=1 turns the measure off."""
    if os.environ.get("MERIDIANA_NO_LIBREOFFICE") == "1":
        return None
    folders = []
    if os.environ.get("MERIDIANA_LIBREOFFICE"):
        folders.append(Path(os.environ["MERIDIANA_LIBREOFFICE"]))
    if sys.platform == "win32":
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), r"C:\Program Files"):
            if base:
                folders.append(Path(base) / "LibreOffice" / "program")
        for folder in folders:
            if (folder / "python.exe").is_file() and (folder / "soffice.exe").is_file():
                return folder / "python.exe", folder / "soffice.exe"
        return None
    if sys.platform == "darwin":
        folders.append(Path("/Applications/LibreOffice.app/Contents/MacOS"))
        for folder in folders:
            python = folder.parent / "Resources" / "python"
            if (folder / "soffice").is_file() and python.is_file():
                return python, folder / "soffice"
        return None
    # Linux: the system's soffice and a python3 that has LibreOffice's uno module (python3-uno)
    soffice = next((folder / "soffice" for folder in folders if (folder / "soffice").is_file()), None)
    soffice = soffice or (Path(shutil.which("soffice")) if shutil.which("soffice") else None)
    python = shutil.which("python3")
    if soffice is None or python is None:
        return None
    probe = subprocess.run([python, "-c", "import uno"], capture_output=True, timeout=20)
    return (Path(python), soffice) if probe.returncode == 0 else None


def profile_folder() -> Path:
    """LibreOffice's profile for the measures, kept from one to the next (the first one makes it, a few seconds).
    MERIDIANA_LIBREOFFICE_PROFILE names another one (the tests: a profile of their own, never the program's)."""
    if os.environ.get("MERIDIANA_LIBREOFFICE_PROFILE"):
        return Path(os.environ["MERIDIANA_LIBREOFFICE_PROFILE"])
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    return Path(tempfile.gettempdir()) / f"meridiana-libreoffice-{user}"


def _contained(process: subprocess.Popen):
    """Windows: a job object holding the measure and the LibreOffice it starts (its children enter it by themselves),
    closed by `_release` once the measure is over, or by Windows when this process ends: a soffice.bin never outlives
    its measure. 07/11/2026: one started by a test at 00:35 was still there at 03:40, its test process gone, holding
    the shared profile, and every measure after it on that profile came back empty. None elsewhere (the measure has a
    session of its own, `stop` ends it)."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
        kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        job = kernel.CreateJobObjectW(None, None)
        if not job:
            return None

        class Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class Extended(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", ctypes.c_uint64 * 6),
                        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]
        info = Extended()
        info.BasicLimitInformation.LimitFlags = 0x2000              # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if (not kernel.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
                or not kernel.AssignProcessToJobObject(job, wintypes.HANDLE(int(process._handle)))):
            kernel.CloseHandle(job)
            return None
        return kernel, job
    except (OSError, AttributeError, ValueError):
        return None


def _release(job) -> None:
    """The measure's job closed: what is still in it (a LibreOffice that did not quit) ends with it."""
    if job is not None:
        kernel, handle = job
        kernel.CloseHandle(handle)


def measure(path: Path, seconds: int = SECONDS) -> dict | None:
    """What LibreOffice finds laying out `path` (see the module), or None."""
    where = found()
    if where is None:
        return None
    python, soffice = where
    with tempfile.TemporaryDirectory(prefix="meridiana-measure-") as folder:
        out = Path(folder) / "measure.json"
        copy = Path(folder) / ("measured" + path.suffix)
        shutil.copy2(path, copy)
        args = [str(python), str(SCRIPT), str(copy), str(out), profile_folder().as_uri(), str(soffice)]
        extra = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {"start_new_session": True}
        env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}   # LibreOffice's Python, not ours
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, **extra)
        job = _contained(process)
        try:
            _stdout, stderr = process.communicate(timeout=seconds)
        except subprocess.TimeoutExpired:
            stop(process)
            log.complain("report export: LibreOffice", RuntimeError(f"no answer in {seconds} s"))
            return None
        finally:
            _release(job)
        if process.returncode != 0 or not out.is_file():
            log.complain("report export: LibreOffice", RuntimeError(stderr.decode("utf-8", "replace")[-800:]))
            return None
        try:
            return json.loads(out.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            log.complain("report export: LibreOffice", error)
            return None


def stop(process: subprocess.Popen) -> None:
    """The measure and the LibreOffice it started, ended: on Windows its tree, elsewhere its session."""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=30,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        process.kill()
    process.wait(10)
