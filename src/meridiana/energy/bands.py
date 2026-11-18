"""The Italian time bands of electricity, F1, F2 and F3, as ARERA defines them (resolution 181/06, Table 1,
in force since 1 January 2007; in reference\\laws):
- F1, peak: Monday to Friday, 8.00 to 19.00;
- F2, mid-level: Monday to Friday 7.00 to 8.00 and 19.00 to 23.00; Saturday 7.00 to 23.00;
- F3, off-peak: Monday to Friday 23.00 to 7.00; Sundays and holidays all day. Saturday's other hours
  (0.00 to 7.00 and 23.00 to 24.00) are in no other band, so they are F3.
The holidays are the table's own list: 1 and 6 January, Easter Monday, 25 April, 1 May, 2 June, 15 August,
1 November, 8, 25 and 26 December. Hours are local hours, daylight saving time included."""

from __future__ import annotations

from datetime import date, timedelta

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import pandas as pd             # only named in the annotations: imported where it is used (task 18c)

BANDS = ("F1", "F2", "F3")
SOURCE = "ARERA, delibera 181/06, Tabella 1 (fasce orarie dal 1 gennaio 2007)"


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


def holidays(year: int) -> set[date]:
    fixed = {(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)}
    days = {date(year, m, d) for m, d in fixed}
    days.add(easter(year) + timedelta(days=1))
    return days


def band_of(index: pd.DatetimeIndex) -> np.ndarray:
    """The band ("F1", "F2", "F3") of each local hour; the hour is the one starting at the timestamp."""
    idx = index if index.tz is None else index.tz_convert("Europe/Rome")
    hour = idx.hour.to_numpy()
    weekday = idx.weekday.to_numpy()             # Monday 0 ... Sunday 6
    days = {d for y in set(idx.year) for d in holidays(int(y))}
    holiday = np.array([d in days for d in idx.date])
    out = np.full(len(idx), "F3", dtype=object)
    working = (weekday <= 4) & ~holiday
    saturday = (weekday == 5) & ~holiday
    out[working & (hour >= 8) & (hour < 19)] = "F1"
    out[working & (((hour >= 7) & (hour < 8)) | ((hour >= 19) & (hour < 23)))] = "F2"
    out[saturday & (hour >= 7) & (hour < 23)] = "F2"
    return out
