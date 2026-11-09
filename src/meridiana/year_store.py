"""The year computed, kept by what it was computed from (R437).

Daniel: «avevo fatto i calcoli, salvato, chiuso, riaperto, e me li ha persi». A year that took minutes is written in the
program's own cache under the fingerprint of its inputs (session.year_fingerprint): opening the project again, or an undo
back to a state already computed, finds it there, without a new computation. Nothing goes in the project file, which keeps
its format and its size; on another PC the year is computed again, and nothing is wrong.

The files are pickles written by this program in the user's own cache, as those the computation's process hands back;
never a file that came with a project. One that cannot be read is as one that is not there. The newest KEEP stay.
"""

from __future__ import annotations

import gzip
import hashlib
import os
import pickle
from pathlib import Path

VERSION = 1
KEEP = 20
FOLDER = "years"


def fingerprint_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def path_of(cache: Path, fingerprint: str) -> Path:
    return Path(cache) / FOLDER / f"{fingerprint}.year"


def write(cache: Path, fingerprint: str, key: str, energy: dict, results: dict, layout_keys: dict) -> Path:
    """Written whole or not at all; the oldest beyond KEEP go. OSError when the disk says no: the year stays in hand."""
    target = path_of(cache, fingerprint)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(f".{os.getpid()}.part")
    # Light compression: a year of 200 modules is 63 MB as it is and 2,6 MB so (hourly series that repeat).
    with gzip.open(partial, "wb", compresslevel=3) as stream:
        pickle.dump(dict(version=VERSION, key=key, energy=energy, results=results, layout_keys=layout_keys), stream,
                    protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(partial, target)
    _prune(target.parent)
    return target


def read(cache: Path, fingerprint: str, key: str) -> dict | None:
    """The year of exactly these inputs, or None: never found, of another version, damaged."""
    path = path_of(cache, fingerprint)
    try:
        with gzip.open(path, "rb") as stream:
            data = pickle.load(stream)
    except (OSError, EOFError, ValueError, AttributeError, ImportError, IndexError, TypeError, pickle.UnpicklingError):
        return None
    if not isinstance(data, dict) or data.get("version") != VERSION or data.get("key") != key:
        return None
    return data


def _prune(folder: Path) -> None:
    files = sorted(folder.glob("*.year"), key=lambda f: f.stat().st_mtime, reverse=True)
    for old in files[KEEP:]:
        old.unlink(missing_ok=True)
