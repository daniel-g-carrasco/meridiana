"""The guard of the window that never waits (R598, docs/studio/48-lavori-pesanti.md, chapter 5): two measures while
a job runs.

1. The calls of the jobs' center on the window's thread: Center.pump() times every one (Center.stats()), the longest
   with its name. Threshold `call_ms` (5 ms by default).
2. The window's beat: a timer of the event loop every BEAT_MS; the longest gap between two beats says how long the
   window stood still, whatever the cause (a thread holding the interpreter too). Threshold `beat_ms` (50 ms, three
   frames: a loaded PC steals time).

    with window_stays_free(center) as seen:
        ...the job runs, the test turns the events (wait_for, never time.sleep)...
    # out of the block: AssertionError with the longest call and its name, or the longest beat

`beat_ms=None`: the beat is measured and left in `seen` for the test to report, not asserted. For a window whose own
frames run on its thread (the plan off screen: Qt's software renderer draws there, 30-60 ms a frame without any job),
where the beat would measure the renderer and not the work; the calls stay asserted.

`software_frames(window)` says whether that is the case (Qt's software renderer, off screen or asked for), so that a
test asserts the beat where it means the work (a graphics API: the frames are drawn on the render thread) and only
prints it where it does not.

`settled(window)` waits for the frames of the opening to end (the forms made ahead by Properties, R465, the first
tiles, the plan fitted): a block started on a window just opened measures them, not the job (test_sun_map, 13/11/2026:
a beat of 255-281 ms off screen was warmForms building a form 600 ms after the layout came, not the map).

Every job brought to the mechanism adds its test with the same line."""

import contextlib
import time
from dataclasses import dataclass, field

BEAT_MS = 5


@dataclass
class Seen:
    call_ms: float = 0.0
    call_name: str = ""
    calls: int = 0
    beat_ms: float = 0.0
    beats: int = 0
    left: dict = field(default_factory=dict)        # name -> ms: the calls outside `only`, measured, not asserted

    def __str__(self):
        return (f"longest call {self.call_ms:.1f} ms ({self.call_name or 'none'}, {self.calls} calls), "
                f"longest beat {self.beat_ms:.1f} ms ({self.beats} beats)")

    def over(self, ms: float) -> dict:
        """The calls outside `only` over `ms`, the longest first: what is still to bring under the threshold."""
        return dict(sorted(((k, round(v, 1)) for k, v in self.left.items() if v > ms), key=lambda kv: -kv[1]))


def software_frames(window) -> bool:
    """Whether the window's frames are drawn by Qt's software renderer, on the window's own thread."""
    from PySide6.QtQuick import QSGRendererInterface
    api = window.rendererInterface().graphicsApi() if window.rendererInterface() is not None else None
    return api in (None, QSGRendererInterface.GraphicsApi.Software)


def settled(window, quiet_ms: int = 1000, ms: int = 60000) -> bool:
    """The events turned until the window has drawn no frame for `quiet_ms` (at most `ms`): whether it did."""
    import _setup
    last = [time.perf_counter()]

    def frame():
        last[0] = time.perf_counter()
    window.afterAnimating.connect(frame)
    try:
        return _setup.wait_for(lambda: time.perf_counter() - last[0] >= quiet_ms / 1000, ms)
    finally:
        window.afterAnimating.disconnect(frame)


@contextlib.contextmanager
def window_stays_free(center, call_ms: float = 5, beat_ms: float | None = 50, only: tuple = ()):
    """`only`: the prefixes of the names of the calls the step brought to the mechanism, the ones asserted; the others
    (a later step's, study 48 chapter 6: the views told in pieces, the threads of the window that hold the
    interpreter meanwhile) measured and kept in `seen.left`, for the test to name them with their numbers. Without
    it every call is asserted. Never a way to loosen the threshold of what a step has brought in."""
    from PySide6.QtCore import Qt, QTimer
    seen = Seen()
    last = [time.perf_counter()]

    def beat():
        now = time.perf_counter()
        seen.beat_ms = max(seen.beat_ms, (now - last[0]) * 1000)
        seen.beats += 1
        last[0] = now
    timer = QTimer()
    timer.setTimerType(Qt.TimerType.PreciseTimer)
    timer.setInterval(BEAT_MS)
    timer.timeout.connect(beat)
    center.reset_stats()
    timer.start()
    last[0] = time.perf_counter()
    try:
        yield seen
    finally:
        timer.stop()
        stats = center.stats()
        seen.call_ms, seen.call_name = stats["longest_call"][0] * 1000, stats["longest_call"][1]
        seen.calls = stats["calls"]
        if only:
            by_name = stats.get("by_name", {})
            seen.left = {k: v * 1000 for k, v in by_name.items() if not k.startswith(only)}
            kept = {k: v for k, v in by_name.items() if k.startswith(only)}
            name = max(kept, key=kept.get) if kept else ""
            seen.call_ms, seen.call_name = (kept[name] * 1000 if name else 0.0), name
    if seen.call_ms > call_ms:
        raise AssertionError(f"the window waited for a call of {seen.call_ms:.1f} ms > {call_ms} ms: "
                             f"{seen.call_name} ({seen})")
    if beat_ms is not None and seen.beat_ms > beat_ms:
        raise AssertionError(f"the window stood still {seen.beat_ms:.1f} ms > {beat_ms} ms ({seen})")
