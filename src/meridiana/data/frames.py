"""Objects written with their large arrays apart (pickle protocol 5, PEP 574): a small head, then the bytes of each
array. Reading one back is a read of the file, which a thread does without holding the interpreter (the disk), and a
rebuild that copies nothing: the head unpickled with the arrays on the bytes read, a few milliseconds where the whole
pickle of a year held the window's thread for one or two seconds (R598, study 48 chapter 6 step 4).

The first rebuild of a year in the window imported pandas and the year's modules (333 modules, about a second on Rho):
a frame carries apart the classes and functions its objects are made with, each pickled by its name, and whoever
reads it on a thread unpickles those there (`prepare`), which imports their modules, so that the rebuild on the
window's thread finds them imported.

A frame: MAGIC; the length of the head, the number of arrays and the length of the classes (three 8-byte integers);
the length of each array (8 bytes each); the classes (a pickle of the list of their pickles); the head; then each array
at an offset from the frame's start aligned to ALIGN. Frames follow one another in a stream (a gzip file holds two,
data/year_store.py). Written and read by this program only, in its own caches and temporary folders, as the pickles
before them. The arrays come back writable, on the bytes read, which live as long as one of them does."""

from __future__ import annotations

import gc
import io
import os
import pickle
import struct
import types
from pathlib import Path

MAGIC = b"MERFRAM1"
ALIGN = 64
_COUNTS = struct.Struct("<QQQ")
_TOP = len(MAGIC) + _COUNTS.size
MOST = 1 << 36                  # bytes: a frame that says more is damaged (a year is tens of MB)


class _Pickler(pickle.Pickler):
    """Protocol 5 with the arrays apart; the classes and the functions of the objects noted."""

    def __init__(self, stream, buffers: list, made_with: dict):
        super().__init__(stream, protocol=5, buffer_callback=buffers.append)
        self.made_with = made_with

    def reducer_override(self, obj):
        self.made_with[type(obj)] = None
        if isinstance(obj, (type, types.FunctionType, types.BuiltinFunctionType)):
            self.made_with[obj] = None
        return NotImplemented


def _by_name(made_with) -> bytes:
    """Those of the classes and functions that pickle by their name (a module's own; not Cython's types), pickled."""
    out = []
    for thing in made_with:
        if getattr(thing, "__module__", None) in (None, "builtins"):
            continue
        try:
            out.append(pickle.dumps(thing, protocol=5))
        except (pickle.PicklingError, TypeError, AttributeError):
            continue
    return pickle.dumps(out, protocol=5)


def dump(obj, stream) -> int:
    """`obj` written to `stream` as one frame; the bytes written."""
    buffers: list = []
    made_with: dict = {}
    out = io.BytesIO()
    _Pickler(out, buffers, made_with).dump(obj)
    head = out.getbuffer()
    names = _by_name(made_with)
    raws = [buffer.raw() for buffer in buffers]
    top = (MAGIC + _COUNTS.pack(len(head), len(raws), len(names))
           + struct.pack(f"<{len(raws)}Q", *(r.nbytes for r in raws)) + names)
    stream.write(top)
    stream.write(head)
    at = len(top) + len(head)
    for raw in raws:
        pad = -at % ALIGN
        if pad:
            stream.write(bytes(pad))
        stream.write(raw)
        at += pad + raw.nbytes
    return at


def write(path: Path, obj) -> None:
    with open(path, "wb") as stream:
        dump(obj, stream)


def _layout(view) -> tuple:
    """(head, arrays, names, lengths, start of the modules' names) of a frame's top."""
    head, count, names = _COUNTS.unpack_from(view, len(MAGIC))
    lengths = struct.unpack_from(f"<{count}Q", view, _TOP) if len(view) >= _TOP + 8 * count else ()
    return head, count, names, lengths, _TOP + 8 * count


def _size(head: int, names: int, lengths: tuple) -> int:
    at = _TOP + 8 * len(lengths) + names + head
    for n in lengths:
        at += -at % ALIGN + n
    return at


def read_from(stream) -> bytearray | None:
    """The frame at the stream's position, whole, as bytes to give to `loads`; None when what is there is not a
    frame. On a thread: the reading leaves the interpreter to the window (only the copies of the stream hold it)."""
    top = stream.read(_TOP)
    if len(top) < _TOP or top[:len(MAGIC)] != MAGIC:
        return None
    head, count, names = _COUNTS.unpack_from(top, len(MAGIC))
    if count > MOST // 8 or names > MOST or head > MOST:
        return None
    table = stream.read(8 * count)
    if len(table) < 8 * count:
        return None
    size = _size(head, names, struct.unpack(f"<{count}Q", table))
    if size > MOST:
        return None
    blob = bytearray(size)
    blob[:_TOP] = top
    blob[_TOP:_TOP + len(table)] = table
    view, at = memoryview(blob), _TOP + len(table)
    while at < size:
        got = stream.readinto(view[at:])
        if not got:
            return None
        at += got
    return blob


def read(path: Path) -> bytearray | None:
    """The frame of a file, as `read_from`."""
    with open(path, "rb", buffering=0) as stream:
        if os.fstat(stream.fileno()).st_size < _TOP:
            return None
        return read_from(stream)


def made_with(blob) -> list:
    """The classes and functions a frame's objects are made with (those that pickle by their name), unpickled: their
    modules imported."""
    view = memoryview(blob)
    _head, _count, names, _lengths, at = _layout(view)
    out = []
    for one in pickle.loads(view[at:at + names]) if names else ():  # noqa: S301 - private IPC or own year cache
        try:
            out.append(pickle.loads(one))  # noqa: S301 - names from the same internal frame
        except (ImportError, AttributeError, pickle.UnpicklingError):   # one gone: the rebuild will say what is wrong
            continue
    return out


def prepare(blob):
    """The modules of a frame imported (made_with), on the thread that read it, not the window's: the rebuild there
    then finds them (pandas and the year's own, the first time: a second). `blob` itself."""
    made_with(blob)
    return blob


def loads(blob) -> object:
    """The object of a frame read (`read`, `read_from`): its arrays on `blob`, nothing copied. ValueError when it is
    not a frame; what pickle raises for a damaged one. The collector waits meanwhile: the rebuild makes tens of
    thousands of objects, none of them garbage, and a full collection of the window's objects falling on it took
    0,1 s."""
    view = memoryview(blob)
    if bytes(view[:len(MAGIC)]) != MAGIC:
        raise ValueError("not a frame")
    head, _count, names, lengths, at = _layout(view)
    start = at + names
    at = start + head
    buffers = []
    for n in lengths:
        at += -at % ALIGN
        buffers.append(view[at:at + n])
        at += n
    if at > len(view):
        raise ValueError("a frame cut short")
    collecting = gc.isenabled()
    gc.disable()
    try:
        return pickle.loads(view[start:start + head], buffers=buffers)  # noqa: S301 - private IPC or own year cache
    finally:
        if collecting:
            gc.enable()
