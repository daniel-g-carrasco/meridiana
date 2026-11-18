"""Whether the designer is working or still (r27, R548 corrected): what is made ahead (the report's preview, R548)
starts only when nobody has touched the window for IDLE_S (no change of phase, no gesture, no edit), and stops as soon
as the designer comes back. Measured on the Dell (docs/prestazioni/2026-11-08/confronto-r25-dell.md): with the preview
made ahead 2.5 s after the year, whatever the designer did, the first entry of the phases walked one after the other
cost 40-150 ms more than in r24.

`touch()` is called for every input of the window (window_frame.AltTap reads them all already) and at every change
of phase; the first touch after IDLE_S of quiet tells the listeners (`resumed`), at once, on the window's thread."""
from __future__ import annotations

import time
import weakref

IDLE_S = 4.0            # nothing done for this long: the designer is still, work ahead may start

_last = [time.monotonic()]
_listeners: list = []


def touch() -> None:
    """The designer did something now: a key, a button, the wheel, a drag, a change of phase."""
    now = time.monotonic()
    was_idle = now - _last[0] >= IDLE_S
    _last[0] = now
    if was_idle:
        for ref in list(_listeners):
            listener = ref()
            if listener is None:
                _drop(ref)
                continue
            try:
                listener()
            except RuntimeError:        # its Qt object is gone
                _drop(ref)


def _drop(ref) -> None:
    try:
        _listeners.remove(ref)
    except ValueError:
        pass


def idle_for() -> float:
    """Seconds since the designer last did something."""
    return time.monotonic() - _last[0]


def idle() -> bool:
    return idle_for() >= IDLE_S


def wait_left_ms() -> int:
    """Milliseconds until the designer counts as still (0 when already)."""
    return max(0, int((IDLE_S - idle_for()) * 1000) + 1)


def subscribe(listener) -> None:
    """`listener()` called at the first touch after a quiet of IDLE_S; a bound method is held weakly (its object
    goes when nothing else holds it)."""
    ref = weakref.WeakMethod(listener) if hasattr(listener, '__self__') else (lambda: listener)
    if all(r() != listener for r in _listeners):
        _listeners.append(ref)


def unsubscribe(listener) -> None:
    for ref in list(_listeners):
        if ref() == listener:
            _drop(ref)
