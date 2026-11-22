"""The results of a job kept on disk by key (study 48, rule 8): one `.npz` file of arrays for each key in a folder of
the session's cache, written whole or not at all (a temporary file renamed at the end), read by the job's process.
What a job keeps in memory stays with resources.Cache, in whoever receives it.

The folder is a store under the one ceiling of the stores on disk (app/platform/disk_cap.py, study 48 chapter 8): a
write counts there (and cleans the oldest when the ceiling is passed), a read touches the file (its last use)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from meridiana.app.platform import disk_cap, log


def name(key: bytes | str) -> str:
    """The name of a key's file without its ending: its digest in hexadecimal (resources.fingerprint gives bytes);
    the group the ceiling of the stores knows it by (disk_cap.protect)."""
    text = key.hex() if isinstance(key, (bytes, bytearray)) else str(key)
    if not text or any(c in text for c in '\\/:*?"<>|.'):
        raise ValueError(f"not a key for a file name: {text!r}")
    return text


def path(folder: Path, key: bytes | str) -> Path:
    """The file of a key."""
    return Path(folder) / f"{name(key)}.npz"


def write(folder: Path, key: bytes | str, arrays: dict) -> Path:
    """`arrays` ({name: NumPy array}) kept under `key`, whole or not at all: an error leaves the file that was there,
    and no piece of the new one."""
    import numpy as np
    target = path(folder, key)
    disk_cap.register(target.parent)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.stem}.", suffix=".part", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            np.savez(fh, **{name: np.asarray(value) for name, value in arrays.items()})
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError as error:
            log.complain("A piece of a job's result could not be taken away", error)
        raise
    try:
        disk_cap.wrote(target.parent, target.stat().st_size)
    except OSError as error:            # the result is kept: only the ceiling's count missed it
        log.complain("The stores on disk could not be counted", error)
    return target


def read(folder: Path, key: bytes | str) -> dict | None:
    """The arrays kept under `key`, or None when there are none; a file that cannot be read is said in the log and
    counts as none (the job computes it again)."""
    import zipfile

    import numpy as np
    target = path(folder, key)
    if not target.exists():
        return None
    try:
        with np.load(target, allow_pickle=False) as data:
            found = {name: data[name] for name in data.files}
    except FileNotFoundError:           # taken away by the ceiling between the look and the read: computed again
        return None
    except (OSError, ValueError, EOFError, zipfile.BadZipFile) as error:
        log.complain(f"A job's result kept in {target.name} could not be read", error)
        return None
    try:
        os.utime(target)                # its last use: the oldest go first (NTFS often keeps no date of access)
    except OSError:
        pass                            # taken away meanwhile, or read only: it only looks older
    return found
