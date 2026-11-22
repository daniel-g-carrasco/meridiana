"""The year's files read off the window's thread (R598, study 48 chapter 6 step 4): a thread job of the mechanism, since
it waits for the disk. What the year's process hands back (its layouts, `layout.bin`, and its year, `result.bin`) and
the year kept in the store (R437, a project opened again) come to the window as frames (data/frames.py): the thread
reads the bytes, the window rebuilds the objects on them in milliseconds, without copying the arrays. Without Qt.

The year as the window holds it is the light one (data/year_store.split: the near shading of the first pass stays with
the computation and in the store): what every view, the checks, the plant and the report read of it is the same."""

from __future__ import annotations

from pathlib import Path

from meridiana.app.work.job import Kind
from meridiana.data import frames, year_store
from meridiana.i18n import N_

# The year's own title in the bar (gui/backend/work.py YEAR_TITLE): a read is a moment of the year. Never restarted
# (no topics): the read of a file is of that file. Not cancellable: its owner waits for its answer, and it is short.
KIND = Kind(name="year_read", title=N_("Production"), run="meridiana.app.year_read:run", where="thread",
            topics=(), cancellable=False, in_bar=False)


def file_request(path) -> dict:
    """The request to read one of the year's files written by its process, `path`."""
    return {"file": str(path)}


def store_request(cache, fingerprint: str) -> dict:
    """The request to read the year kept under `fingerprint` in the store of `cache` (as the window reads it)."""
    return {"cache": str(cache), "fingerprint": fingerprint}


def run(request: dict, ctx) -> bytearray | None:
    """The bytes of the frame asked for (frames.loads, year_store.light_of make the objects on the window's thread),
    its modules imported; None when the store has no year that can be read. A file of the year's process that cannot
    be read raises (its owner says why)."""
    if "file" in request:
        blob = frames.read(Path(request["file"]))
        if blob is None:
            raise ValueError(f"{Path(request['file']).name} is not a frame")
    else:
        blob = year_store.read_light(Path(request["cache"]), request["fingerprint"])
    # the modules of its objects imported here, not in the rebuild on the window's thread: pandas and the year's,
    # the first time (a second of the window on Rho)
    return frames.prepare(blob) if blob is not None else None
