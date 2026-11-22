"""Compatibility calendar API; Easter is a shared astronomical algorithm."""
from __future__ import annotations
from datetime import date
from meridiana.core.rules import registry


def easter(year: int) -> date:
    """Easter Sunday of the Gregorian calendar (the anonymous algorithm, Meeus, Astronomical Algorithms)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    month, day = divmod(h + ll - 7 * m + 114, 31)
    return date(year, month, day + 1)


def holidays(year: int, *, profile_id: str = "it") -> set[date]:
    return registry.get(profile_id).calendar().holidays(year)


def band_of(index, *, profile_id: str = "it", timezone: str | None = None):
    calendar = registry.get(profile_id).calendar()
    return calendar.band_of(index, timezone or calendar.default_timezone)


def __getattr__(name):
    if name in {"BANDS", "SOURCE"}:
        calendar = registry.get("it").calendar()
        return calendar.codes if name == "BANDS" else calendar.source
    raise AttributeError(name)
