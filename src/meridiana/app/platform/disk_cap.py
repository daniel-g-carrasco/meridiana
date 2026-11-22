"""One ceiling for the stores the program keeps on disk under its caches (study 48, chapter 8): the sun map's levels
(app/work/store.py) and the IFC models' geometry (app/exchange/ifc_cache.py), and whatever store comes next.

- A store is a folder under the caches' root that says so: register(folder, root) adds it to the root's list
  (STORES, its path from the root) and leaves a mark in it (MARK). The cleaning reads the list, in any process, so a
  job's process and the window count the same stores together, also one deeper in the root (the window's own caches,
  `quick-profile/cache/ifc`).
- The ceiling follows the disk: a share of the room the stores could have (the free space plus what they hold),
  never under KEEP / LOW_MARK and never over MOST. Past the ceiling the oldest files go until the stores are down to
  LOW_MARK of it (so that the next write does not clean again), and never under KEEP, even on a disk almost full (a
  large project would compute again at every opening). A disk full makes the writes fail: said in the log, and
  computed again the next time.
- The oldest by last use: a file's date of change, or the date its group was last declared in use (USED), whichever
  is later. A file of the sun map's store is also touched when it is read (store.read). NTFS often does not update
  the date of access, and the IFC geometry's date is part of the keys of what is made from it (the IFC shadows, the
  3D): it is never touched.
- A file of a group in use is never taken: whoever uses a store declares the groups the open project uses (protect:
  the sun map the keys of its surfaces, the IFC the geometry of the model linked to the project), in a lease of its
  process (LEASES), valid while that process lives. A file younger than YOUNG is never taken either: a job may be
  about to read what another one just wrote. A file that cannot be taken (open in another process, on Windows) is
  left and the cleaning goes on; one taken while another process reads it is computed again by that one.
- A group is a file's name up to its first dot: «ifc-<key>-m3.npz» and «ifc-<key>-m3.read-<code>.json» go together.
  Pieces being written (a name with a leading dot, or with «.part») are left alone, and taken after STALE_PART.
- Cleaning is cheap and off the window's thread: `wrote` after a write counts the bytes and scans only when the count
  passes the ceiling or RESCAN seconds went by; `clean_soon` once at the start, in a thread of its own.

Without Qt. Every value in the constants below."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

from meridiana.app.platform import log

GIB = 1 << 30
KEEP = 2 * GIB              # never cleaned below this: the stores of about 15 projects as large as model A
MOST = 20 * GIB             # the ceiling whatever the disk
FREE_SHARE = 0.10           # the ceiling: this share of the free space plus what the stores hold
LOW_MARK = 0.75             # past the ceiling the stores go down to this share of it
YOUNG = 3600.0              # seconds: a file used more recently than this is never taken
STALE_PART = 86400.0        # seconds: a piece being written left older than this (a crash) is taken
RESCAN = 600.0              # seconds: a process that writes looks at the whole stores at least this often
STORES = ".stores.json"     # in the root: the stores, by their path from it
MARK = ".store"             # in a store: the mark that it is one
LEASES = ".in-use"          # in the root: what each process uses
USED = ".used.json"         # in a store: when each group was last declared in use (seconds since the epoch)


def ceiling(free: int, used: int) -> int:
    """The bytes the stores may hold together: FREE_SHARE of the free space plus what they hold, between
    KEEP / LOW_MARK and MOST."""
    return int(max(KEEP / LOW_MARK, min(MOST, FREE_SHARE * (max(0, free) + max(0, used)))))


def group_of(name: str) -> str:
    """The group of a file: its name up to the first dot ("" for a piece being written)."""
    if name.startswith(".") or ".part" in name:
        return ""
    return name.split(".", 1)[0]


def _name(folder: Path, root: Path) -> str:
    """A store's name: its path from the root."""
    return Path(os.path.relpath(folder, root)).as_posix()


_registered: set = set()
_registered_lock = threading.Lock()


def register(folder, root=None) -> Path:
    """`folder` made a store of `root` (its parent by default): created, marked and listed. What it holds counts under
    the one ceiling of the root. Once per process and folder it looks at the disk; then it costs nothing."""
    folder = Path(folder)
    root = folder.parent if root is None else Path(root)
    key = (str(folder), str(root))
    with _registered_lock:
        if key in _registered:
            return folder
    folder.mkdir(parents=True, exist_ok=True)
    mark = folder / MARK
    if not mark.exists():
        mark.touch()
    name = _name(folder, root)
    listed = _read_json(root / STORES, [])
    if name not in listed:
        _write_whole(root / STORES, sorted({*map(str, listed), name}))
    with _registered_lock:
        _registered.add(key)
    return folder


def stores(root) -> list[tuple[str, Path]]:
    """The stores of `root`: (name, folder), those listed that are still there and marked."""
    root = Path(root)
    out = []
    for name in _read_json(root / STORES, []):
        folder = root / str(name)
        if (folder / MARK).exists():
            out.append((str(name), folder))
    return sorted(out)


# what is in use

def protect(folder, owner: str, groups, root=None) -> None:
    """The groups of the store `folder` (of `root`, its parent by default) this process uses now, under `owner`
    (one per user of a store: "sun_map", "ifc"); () lets them go. Written whole in this process's lease, and noted as
    their last use. Disk work: call it off the window's thread (protect_soon)."""
    folder = Path(folder)
    root = folder.parent if root is None else Path(root)
    groups = sorted({str(g) for g in groups if g})
    target = root / LEASES / f"{os.getpid()}-{owner}.json"
    if groups:
        target.parent.mkdir(parents=True, exist_ok=True)
        _write_whole(target, {"pid": os.getpid(), "store": _name(folder, root), "groups": groups})
        if folder.is_dir():
            used = _read_json(folder / USED, {})
            used = used if isinstance(used, dict) else {}
            used.update({g: time.time() for g in groups})
            _write_whole(folder / USED, used)
    else:
        try:
            target.unlink()
        except FileNotFoundError:
            pass                            # nothing was declared


_pending: dict = {}
_pending_lock = threading.Lock()
_pending_wake = threading.Event()
_writer: list = [None, False]               # the writing thread, and whether it is writing


def protect_soon(folder, owner: str, groups, root=None) -> None:
    """protect(), in a thread of its own: the caller (the window's thread) only hands the groups over. Only the last
    groups of each (folder, owner) are written."""
    with _pending_lock:
        _pending[(str(folder), owner)] = (folder, owner, tuple(groups), root)
        if _writer[0] is None or not _writer[0].is_alive():
            _writer[0] = threading.Thread(target=_write_pending, name="meridiana-disk-cap", daemon=True)
            _writer[0].start()
    _pending_wake.set()


def settle_pending(timeout: float = 5.0) -> bool:
    """Whether what protect_soon was given is written, waiting at most `timeout` seconds (the tests)."""
    done = threading.Event()
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        with _pending_lock:
            if not _pending and not _writer[1]:
                return True
        _pending_wake.set()
        done.wait(0.01)
    return False


def _write_pending() -> None:
    while True:
        _pending_wake.wait(30.0)
        _pending_wake.clear()
        while True:
            with _pending_lock:
                if not _pending:
                    _writer[1] = False
                    break
                _key, (folder, owner, groups, root) = _pending.popitem()
                _writer[1] = True
            try:
                protect(folder, owner, groups, root)
            except OSError as error:        # the files stay unprotected: they are young, or computed again
                log.complain(f"What the open project uses in {Path(folder).name} could not be noted", error)


def _alive(pid: int) -> bool:
    if pid == os.getpid():
        return True
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x1000, False, int(pid))         # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ctypes.get_last_error() == 5                    # access denied: it is there
        try:
            code = wintypes.DWORD()
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def in_use(root) -> dict[str, set]:
    """{store's name: groups} declared by the processes alive; the leases of processes gone are taken away."""
    out: dict[str, set] = {}
    try:
        entries = list(os.scandir(Path(root) / LEASES))
    except FileNotFoundError:
        return out
    for entry in entries:
        if not entry.name.endswith(".json") or entry.name.startswith("."):
            continue
        lease = _read_json(entry.path, None)
        try:
            pid = int(lease["pid"])
        except (TypeError, ValueError, KeyError):
            continue                        # broken: the files it named are young, or wait for the next pass
        if not _alive(pid):
            _remove_quietly(entry.path)
            continue
        out.setdefault(str(lease.get("store", "")), set()).update(str(g) for g in lease.get("groups") or ())
    return out


def _read_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _write_whole(target: Path, data) -> None:
    fd, part = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".part", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        os.replace(part, target)
    except BaseException:
        _remove_quietly(part)
        raise


def _remove_quietly(path) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass                                # gone already, or open: the next pass


# the cleaning

def survey(root) -> list[tuple[Path, str, int, float]]:
    """Every file of every store of `root`: (path, store's name, bytes, date of change)."""
    out = []
    for name, folder in stores(root):
        try:
            entries = list(os.scandir(folder))
        except OSError:
            continue
        for entry in entries:
            if entry.name in (MARK, USED) or not entry.is_file():
                continue
            try:
                st = entry.stat()
            except OSError:
                continue                    # gone meanwhile
            out.append((Path(entry.path), name, st.st_size, st.st_mtime))
    return out


def clean(root, *, free: int | None = None, now: float | None = None) -> dict:
    """One pass over the stores of `root`: past the ceiling, the oldest groups neither in use nor young go until the
    stores are at LOW_MARK of it (never under KEEP). `free` (the disk's free bytes) and `now` (seconds since the
    epoch) for the tests. What was done: used, ceiling, removed (paths), freed (bytes), busy (files that could not be
    taken)."""
    now = time.time() if now is None else now
    report = {"used": 0, "ceiling": 0, "removed": [], "freed": 0, "busy": 0}
    kept = []
    for path, store, size, mtime in survey(root):         # the pieces a crash left
        if not (group_of(path.name) == "" and now - mtime > STALE_PART and _remove(path, report, size)):
            kept.append((path, store, size, mtime))
    used = sum(size for _p, _s, size, _m in kept)
    if free is None:
        try:
            free = shutil.disk_usage(root).free
        except OSError:
            free = 0
    top = ceiling(free, used)
    report["used"], report["ceiling"] = used, top
    if used <= top:
        return report
    target = max(KEEP, int(LOW_MARK * top))
    busy = in_use(root)
    noted = {name: _read_json(folder / USED, {}) for name, folder in stores(root)}
    groups: dict = {}
    for path, store, size, mtime in kept:
        group = group_of(path.name)
        if group:
            groups.setdefault((store, group), []).append((path, size, mtime))
    last = {}
    for (store, group), members in groups.items():
        declared = noted.get(store) if isinstance(noted.get(store), dict) else {}
        try:
            declared = float(declared.get(group, 0.0))
        except (TypeError, ValueError):
            declared = 0.0
        last[(store, group)] = max([m for _p, _s, m in members] + [declared])
    for key in sorted(groups, key=lambda k: last[k]):
        if used <= target:
            break
        store, group = key
        if group in busy.get(store, ()) or now - last[key] < YOUNG:
            continue
        for path, size, _mtime in groups[key]:
            if _remove(path, report, size):
                used -= size
    report["used"] = used
    if report["removed"]:
        log.note(f"The stores on disk were over their ceiling: {len(report['removed'])} files taken away, "
                 f"{report['freed'] >> 20} MB freed, {used >> 20} MB kept of {top >> 20} MB")
    return report


def _remove(path: Path, report: dict, size: int) -> bool:
    try:
        os.unlink(path)
    except FileNotFoundError:               # another process took it first
        return True
    except OSError:                         # open in another process (Windows), or not ours to take: left
        report["busy"] += 1
        return False
    report["removed"].append(str(path))
    report["freed"] += size
    return True


# when to clean

_state: dict = {}                           # root -> [bytes counted, ceiling, time of the last scan]
_state_lock = threading.Lock()


def wrote(folder, size: int, root=None) -> dict | None:
    """After a write of `size` bytes in the store `folder` (of `root`, its parent by default), in the job's process or
    thread: counted, and the stores cleaned when the count passes the ceiling or RESCAN went by since this process
    last looked. The report of the cleaning, None when there was none."""
    root = str(Path(folder).parent if root is None else Path(root))
    now = time.monotonic()
    with _state_lock:
        state = _state.get(root)
        if state is not None and now - state[2] < RESCAN and state[0] + size <= state[1]:
            state[0] += size
            return None
        _state[root] = [0, 1 << 62, now]    # this thread looks: the others writing meanwhile only count
    try:
        report = clean(root)
    except OSError as error:
        log.complain("The stores on disk could not be looked over", error)
        return None
    with _state_lock:
        _state[root] = [report["used"], report["ceiling"], now]
    return report


def clean_soon(root, register_too=()) -> threading.Thread:
    """A pass over the stores of `root` in a thread of its own (the window's start), after registering the folders
    `register_too` that exist (stores written by code that does not register them itself: the IFC reader's; one made
    after this start counts from the next one)."""
    def work():
        try:
            for folder in register_too:
                if Path(folder).is_dir():
                    register(folder, root)
            report = clean(root)
        except OSError as error:
            log.complain("The stores on disk could not be looked over", error)
            return
        with _state_lock:
            _state[str(Path(root))] = [report["used"], report["ceiling"], time.monotonic()]
    thread = threading.Thread(target=work, name="meridiana-disk-cap-clean", daemon=True)
    thread.start()
    return thread
