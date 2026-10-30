"""Autosave and recovery. While a project has unsaved changes a copy goes to the state folder every few
minutes; a save, or a close that discards the changes, takes it away. A copy still there at the next start
means Meridiana stopped without saving, and the designer is offered it back. The copy never replaces the
project's file by itself.

A copy belongs to the Meridiana that wrote it while that one runs: each start holds a lock file in
recovery/owners (`claim`), the system's lock on it goes with the process, even when it crashes, and a copy
whose owner still holds its lock is neither offered nor deleted by another start (R07: a second start used to
offer, and on «No» delete, the copy of the window still open).

Revisions follow the habit of the office: a new revision is a new file next to the previous one, with the
suffix _Rnn, and no file is ever written over."""

from __future__ import annotations

import hashlib
import os
import re
import time
import uuid
from contextlib import suppress
from pathlib import Path

from . import atomic

REVISION = re.compile(r"^(?P<stem>.*?)_R(?P<n>\d{2,})$")
OWNERS = "owners"                           # recovery/owners/<owner>.lock, one for each Meridiana running
OWNER = re.compile(r"[0-9]+-[0-9a-f]{8}")   # the process and a random tag: never a path
_claims: dict[str, tuple[str, int]] = {}    # state folder -> (owner, the lock file held open and locked)


def _lock(fd: int) -> bool:
    """The system's lock on the first byte of an open file, without waiting: False when another process has it."""
    try:
        if os.name == "nt":
            import msvcrt
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _unlock(fd: int) -> None:
    if os.name == "nt":
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN)


def claim(state_dir: Path) -> str:
    """This process's mark on the copies it writes in `state_dir`, held until `release` or the end of the process
    (app.main; the tests' windows claim nothing and write copies without an owner, as before). OSError when the
    lock cannot be taken."""
    key = str(Path(state_dir).resolve())
    if key in _claims:
        return _claims[key][0]
    folder = Path(state_dir) / "recovery" / OWNERS
    folder.mkdir(parents=True, exist_ok=True)
    for _attempt in range(3):
        owner = f"{os.getpid()}-{uuid.uuid4().hex[:8]}"
        path = folder / f"{owner}.lock"
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        if not _lock(fd):
            os.close(fd)
            continue
        # another start may have taken the new file for a lock left behind and removed it before the lock was
        # taken (Linux lets a file open elsewhere be removed): then the lock is on a name nobody sees, try again
        try:
            same = os.path.samestat(os.fstat(fd), os.stat(path))
        except OSError:
            same = False
        if same:
            _claims[key] = (owner, fd)
            for left in folder.glob("*.lock"):      # the locks of starts that crashed: free, removed
                _running(state_dir, left.stem)
            return owner
        _unlock(fd)
        os.close(fd)
    raise OSError(f"the recovery lock in {folder} could not be taken")


def release(state_dir: Path) -> None:
    """The mark let go at a normal end (the system lets it go at any other)."""
    entry = _claims.pop(str(Path(state_dir).resolve()), None)
    if entry is None:
        return
    owner, fd = entry
    _unlock(fd)
    os.close(fd)
    # a lock file that cannot be removed now is free all the same: the next start clears it (_running)
    with suppress(OSError):
        (Path(state_dir) / "recovery" / OWNERS / f"{owner}.lock").unlink(missing_ok=True)


def _mine(state_dir: Path) -> str:
    entry = _claims.get(str(Path(state_dir).resolve()))
    return entry[0] if entry else ""


def _running(state_dir: Path, owner: str) -> bool:
    """Whether the Meridiana that wrote a copy still runs: its lock file is there and locked. A lock left by a
    process that stopped is free: it is removed. In doubt (a lock file that cannot be opened) it runs: a copy is
    never offered, nor deleted, on a guess."""
    if not OWNER.fullmatch(owner) or owner == _mine(state_dir):
        return False
    path = Path(state_dir) / "recovery" / OWNERS / f"{owner}.lock"
    try:
        fd = os.open(path, os.O_RDWR)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    try:
        if not _lock(fd):
            return True
        _unlock(fd)
    finally:
        os.close(fd)
    with suppress(OSError):                 # another start clearing it at the same moment
        path.unlink(missing_ok=True)
    return False


def slot(state_dir: Path, project_path: Path | None) -> Path:
    """Where the copy of a project goes: one place per project file, one for a project not yet saved."""
    if project_path is None:
        key = "new"
    else:
        key = hashlib.sha1(str(Path(project_path).resolve()).encode("utf-8")).hexdigest()[:16]
    return Path(state_dir) / "recovery" / f"{key}.json"


def write(state_dir: Path, project_path: Path | None, data: dict) -> Path:
    from . import model, portability
    project = model.Project.from_json(data)
    portability.embed(project, project_path or Path("untitled.mer"))
    path = slot(state_dir, project_path)
    atomic.write_json(path, {"path": str(project_path) if project_path else "", "saved": time.time(),
                             "owner": _mine(state_dir), "project": project.to_json()},
                      keep_backup=False)
    return path


def clear(state_dir: Path, project_path: Path | None) -> None:
    slot(state_dir, project_path).unlink(missing_ok=True)


_ANY = object()


def pending(state_dir: Path, project_path=_ANY) -> list[dict]:
    """The copies left behind, newest first: {"file", "path", "saved", "owner", "project"}; with `project_path`
    (a project asked for by name; None for a new one) only its copy. The copies of a Meridiana still running are
    not left behind and are not listed. A copy that cannot be read is set aside (renamed), not lost and not
    offered again."""
    folder = Path(state_dir) / "recovery"
    wanted = None if project_path is _ANY else slot(state_dir, project_path)
    out = []
    for f in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        if wanted is not None and f != wanted:
            continue
        try:
            data, _notice = atomic.read_json(f)
            copy = {"file": f, "path": str(data.get("path") or ""), "saved": float(data["saved"]),
                    "owner": str(data.get("owner") or ""), "project": data["project"]}
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            f.replace(f.with_suffix(".unreadable"))
            continue
        if not _running(state_dir, copy["owner"]):
            out.append(copy)
    return sorted(out, key=lambda c: c["saved"], reverse=True)


def next_revision(path: Path) -> Path:
    """The file of the next revision next to `path`: name_R01 after name, name_R04 after name_R03, never a
    file that exists."""
    path = Path(path)
    m = REVISION.match(path.stem)
    stem, n = (m.group("stem"), int(m.group("n"))) if m else (path.stem, 0)
    while True:
        n += 1
        candidate = path.with_name(f"{stem}_R{n:02d}{path.suffix}")
        if not candidate.exists():
            return candidate
