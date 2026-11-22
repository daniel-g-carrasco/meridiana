"""The time a job has left (study 48, chapter 3, rule 3), from the pace of its units of work.

- The pace is measured on the units done (`done`), not on the fraction: a total that grows (the sun map finding more
  tiles, a process telling its share late) changes what is left, not the pace, so the estimate follows it at once
  instead of starting again.
- The pace is that of the last WINDOW seconds: a job's passes go at different paces (the preview, the finest tiles),
  and the estimate follows the pass in hand.
- Nothing is said before WARMUP seconds of data: the first steps (imports, a cache read) do not promise what the rest
  will not keep. Units counted again from less (a new phase that counts from zero, a run started again after a
  change) start the measure again: nothing is said until it is warm again.
- What is said does not jump: between two pieces of data it counts down, and a new piece of data moves it by STEADY of
  the difference (a real change of the total is taken at once). When there is no pace (nothing moved in the window
  and nothing was said yet), nothing is said: no time made up."""

from __future__ import annotations

from collections import deque

WARMUP = 5.0                    # seconds of data before the bar says a time
WINDOW = 20.0                   # seconds: the pace is that of the last stretch this long
STEADY = 0.3                    # a new estimate moves the one said by this share of the difference


class Eta:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self._samples: deque = deque()          # (time, done) of the measure, the oldest one WINDOW back at most
        self._start: float | None = None        # when the measure started
        self._total: float | None = None
        self._said: tuple[float, float] | None = None       # (time, seconds) of the last estimate given
        self._fresh = False                     # data came after the last estimate

    def feed(self, now: float, done: float, total: float = 1.0) -> None:
        """`done` units over `total` at `now` (the center's clock). `total` may grow; `done` going back starts the
        measure again."""
        done, total = float(done), float(total)
        if self._samples and done < self._samples[-1][1] - 1e-9:
            self.reset()
        if self._start is None:
            self._start = now
        if self._total is not None and abs(total - self._total) > 1e-9 and self._said is not None:
            self._said = None                   # a new total is a fact, not noise: the next estimate is taken whole
        self._total = total
        self._samples.append((now, done))
        while len(self._samples) > 2 and self._samples[1][0] <= now - WINDOW:
            self._samples.popleft()
        self._fresh = True

    def left(self, now: float) -> float | None:
        """Seconds left, or None while there is not enough to say."""
        if self._start is None or len(self._samples) < 2:
            return None
        t0, d0 = self._samples[0]
        t1, d1 = self._samples[-1]
        if t1 - self._start < WARMUP:
            return None
        counted = None if self._said is None else max(0.0, self._said[1] - (now - self._said[0]))
        if not self._fresh:
            return counted if counted else None
        self._fresh = False
        raw = None
        if t1 > t0 and d1 > d0:
            pace = (d1 - d0) / (t1 - t0)                    # units per second
            raw = max(0.0, max(0.0, self._total - d1) / pace - (now - t1))
        if raw is None:
            if counted:
                self._said = (now, counted)
            return counted if counted else None
        said = raw if counted is None else counted + STEADY * (raw - counted)
        self._said = (now, said)
        return said
