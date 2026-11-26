"""The messages on the pipes of a job's process: four bytes of length, then a pickle (study 48, chapter 3). The worker
keeps the real standard output for these messages alone; whatever its code prints goes to the standard error, which the
window keeps for the log (worker._own_pipes). Pickle is safe here: both ends are this program, the worker started by the
window with the window's own requests.

Messages, worker to window: ("ready", pid), ("progress", run, done, total, phase), ("partial", run, key, data),
("rss", run, bytes), ("done", run, result), ("stopped", run), ("failed", run, text), ("memory", run, bytes, quota).
Window to worker: ("job", run, function, request, share, quota), ("stop", run), ("quit",)."""

from __future__ import annotations

import pickle
import struct
import threading

HEADER = struct.Struct(">I")
LIMIT = 1 << 31                 # one message, at most: what a 4-byte length can say


def frame(message) -> bytes:
    """A message as the bytes that go on the pipe."""
    body = pickle.dumps(message, protocol=5)
    if len(body) >= LIMIT:
        raise ValueError(f"a message of {len(body)} bytes is too long for the pipe")
    return HEADER.pack(len(body)) + body


def frames(read):
    """The messages read with `read(n)` (n bytes, fewer only at the end), until the end of the pipe."""
    while True:
        head = _exact(read, HEADER.size)
        if head is None:
            return
        (size,) = HEADER.unpack(head)
        body = _exact(read, size)
        if body is None:
            return
        yield pickle.loads(body)  # noqa: S301 - private pipes between the parent and its own worker


def _exact(read, n: int) -> bytes | None:
    parts, left = [], n
    while left:
        chunk = read(left)
        if not chunk:
            return None
        parts.append(chunk)
        left -= len(chunk)
    return b"".join(parts)


class Writer:
    """The messages of more threads on one descriptor, each written whole (os.write may write less than asked)."""

    def __init__(self, write):
        self._write = write
        self._lock = threading.Lock()

    def send(self, message) -> None:
        data = memoryview(frame(message))
        with self._lock:
            while data:
                written = self._write(data)
                data = data[written:]
