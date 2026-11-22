"""The year computed, kept by what it was computed from (R437).

Daniel: «avevo fatto i calcoli, salvato, chiuso, riaperto, e me li ha persi». A year that took minutes is written in the
program's own cache under the fingerprint of its inputs (session.year_fingerprint): opening the project again, or an undo
back to a state already computed, finds it there, without a new computation. Nothing goes in the project file, which keeps
its format and its size; on another PC the year is computed again, and nothing is wrong.

The files are written by this program in the user's own cache, as those the computation's process hands back; never a
file that came with a project. One that cannot be read is as one that is not there. The newest KEEP stay.

Since version 3 (R598, study 48 chapter 6 step 4) a year is two frames (data/frames.py) in one gzip file: the year as
the window reads it (`split`: the near shading of the simulation's first pass left out, 76 of its 80 MB on Rho, which
only the computation reads) with its layouts, then that near shading. The window validates both and rebuilds the first alone, on a thread
(`read_light`, `light_of`); the report's process reads both, the year whole (`read`).
"""

from __future__ import annotations

import dataclasses
import gzip
import hashlib
import os
import pickle
import struct
import zlib
from pathlib import Path

from meridiana.data import frames

VERSION = 3          # 3: two frames, the near shading apart (R598); 2: the modules moved to the layers (study 43)
KEEP = 20
FOLDER = "years"
_UNREADABLE = (OSError, EOFError, ValueError, AttributeError, ImportError, IndexError, TypeError, MemoryError,
               struct.error, zlib.error, pickle.UnpicklingError)


def fingerprint_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def path_of(cache: Path, fingerprint: str) -> Path:
    return Path(cache) / FOLDER / f"{fingerprint}.year"


def _per_array(energy: dict):
    sim = energy.get("sim") if isinstance(energy, dict) else None
    parts = getattr(sim, "parts", None)
    per = getattr(parts, "per_array", None)
    if not (dataclasses.is_dataclass(sim) and dataclasses.is_dataclass(parts) and per
            and all(dataclasses.is_dataclass(ap) and hasattr(ap, "near") for ap in per)):
        return None
    return sim, parts, per


def split(energy: dict) -> tuple[dict, list | None]:
    """The year as the window reads it, and what it leaves out: each array's near shading of the simulation's first
    pass (simulate._ArrayPass.near), which only the year's own computation reads again (the strings, the electrical
    network). Everything else is the same objects; nothing is changed in `energy`. A year without a first pass (a
    test's) is itself, with nothing left out (None)."""
    found = _per_array(energy)
    if found is None:
        return energy, None
    sim, parts, per = found
    light = [dataclasses.replace(ap, near=None) for ap in per]
    return dict(energy, sim=dataclasses.replace(sim, parts=dataclasses.replace(parts, per_array=light))), \
        [ap.near for ap in per]


def join(energy: dict, near: list | None) -> dict:
    """The year whole again from `split`'s two halves."""
    found = _per_array(energy) if near is not None else None
    if found is None or len(found[2]) != len(near):
        return energy
    sim, parts, per = found
    whole = [dataclasses.replace(ap, near=n) for ap, n in zip(per, near, strict=True)]
    return dict(energy, sim=dataclasses.replace(sim, parts=dataclasses.replace(parts, per_array=whole)))


def write(cache: Path, fingerprint: str, key: str, energy: dict, results: dict, layout_keys: dict) -> Path:
    """Written whole or not at all; the oldest beyond KEEP go. OSError when the disk says no: the year stays in hand."""
    target = path_of(cache, fingerprint)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(f".{os.getpid()}.part")
    light, near = split(energy)
    # Light compression: a year of 200 modules is 63 MB as it is and 2,6 MB so (hourly series that repeat).
    with gzip.open(partial, "wb", compresslevel=3) as stream:
        frames.dump(dict(version=VERSION, key=key, energy=light, results=results, layout_keys=layout_keys), stream)
        frames.dump(near, stream)
    os.replace(partial, target)
    _prune(target.parent)
    return target


def _checked(data, key: str) -> dict | None:
    if not isinstance(data, dict) or data.get("version") != VERSION or data.get("key") != key:
        return None
    return data


def read(cache: Path, fingerprint: str, key: str) -> dict | None:
    """The year of exactly these inputs, whole, or None: never found, of another version, damaged."""
    try:
        with gzip.open(path_of(cache, fingerprint), "rb") as stream:
            first = frames.read_from(stream)
            data = _checked(frames.loads(first), key) if first is not None else None
            if data is None:
                return None
            second = frames.read_from(stream)
            if second is None:
                return None
            while stream.read(1024 * 1024):
                pass                 # CRC and trailer checked before any result escapes
            near = frames.loads(second)
    except _UNREADABLE:
        return None
    return dict(data, energy=join(data["energy"], near))


def read_light(cache: Path, fingerprint: str) -> bytearray | None:
    """The first frame of the year of `fingerprint` (the year as the window reads it, with its layouts), as bytes for
    `light_of`; None when there is none that can be read. On a thread: the disk and the inflating leave the interpreter
    to the window."""
    try:
        with gzip.open(path_of(cache, fingerprint), "rb") as stream:
            first = frames.read_from(stream)
            if first is None or frames.read_from(stream) is None:
                return None
            while stream.read(1024 * 1024):
                pass                 # validate the whole gzip, including the unused near shading
            return first
    except _UNREADABLE:
        return None


def light_of(blob, key: str) -> dict | None:
    """The year of `read_light`'s bytes when it is of exactly these inputs (as `read`, the near shading left out), or
    None. On the window's thread: milliseconds, the arrays are not copied."""
    if blob is None:
        return None
    try:
        return _checked(frames.loads(blob), key)
    except _UNREADABLE:
        return None


def _prune(folder: Path) -> None:
    files = sorted(folder.glob("*.year"), key=lambda f: f.stat().st_mtime, reverse=True)
    for old in files[KEEP:]:
        old.unlink(missing_ok=True)
