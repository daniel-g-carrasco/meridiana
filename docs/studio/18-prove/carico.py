"""The load of the machine while a measurement runs, so that every number of study 18 says under which load it
was taken: the CPU is shared with other sessions, and a figure without its load is not comparable.

`CpuMeter` samples the system's idle and busy times at `start()` and `stop()` (GetSystemTimes on Windows,
/proc/stat on Linux) and gives the busy share of all the logical processors over that window, as a percentage.
`median_of` runs a callable several times and returns the median and every sample.

    from carico import CpuMeter, median_of
    meter = CpuMeter().start()
    ...
    print(meter.stop())          # e.g. 31.2 (per cent busy, all cores, over the window)
"""

from __future__ import annotations

import ctypes
import statistics
import sys
import time


def _times() -> tuple[float, float]:
    """(idle, total) processor time of the whole machine, in arbitrary units."""
    if sys.platform == "win32":
        idle, kernel, user = ctypes.c_ulonglong(), ctypes.c_ulonglong(), ctypes.c_ulonglong()
        ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
        # the kernel time includes the idle time
        return float(idle.value), float(kernel.value + user.value)
    with open("/proc/stat", encoding="ascii") as f:
        fields = [float(x) for x in f.readline().split()[1:]]
    idle = fields[3] + (fields[4] if len(fields) > 4 else 0.0)
    return idle, sum(fields)


class CpuMeter:
    """The busy share of every logical processor between start() and stop()."""

    def __init__(self):
        self.t0 = None
        self.wall0 = 0.0
        self.busy_pct = None
        self.seconds = 0.0

    def start(self) -> "CpuMeter":
        self.t0 = _times()
        self.wall0 = time.perf_counter()
        return self

    def stop(self) -> float:
        idle0, total0 = self.t0
        idle1, total1 = _times()
        self.seconds = time.perf_counter() - self.wall0
        total = total1 - total0
        self.busy_pct = 100.0 * (1.0 - (idle1 - idle0) / total) if total > 0 else float("nan")
        return self.busy_pct


def median_of(fn, repeats: int = 5, inner: int = 1) -> tuple[float, list[float]]:
    """`fn()` timed `repeats` times (each time the mean over `inner` consecutive calls): the median in seconds
    and every sample, so that the spread is on record."""
    samples = []
    for _ in range(repeats):
        t = time.perf_counter()
        for _ in range(inner):
            fn()
        samples.append((time.perf_counter() - t) / inner)
    return statistics.median(samples), samples


def describe(samples: list[float], unit: float = 1e3, digits: int = 2) -> str:
    """«median 12.3 ms (min 11.9, max 13.0, n=5)»."""
    s = sorted(samples)
    return (f"median {statistics.median(s) * unit:.{digits}f} ms (min {s[0] * unit:.{digits}f}, "
            f"max {s[-1] * unit:.{digits}f}, n={len(s)})")
