"""The existing Italian tariff calendar, independent of geographic timezone."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING
import numpy as np
if TYPE_CHECKING:
    import pandas as pd

CODES = ("F1", "F2", "F3")
SOURCE = "ARERA, delibera 181/06, Tabella 1 (fasce orarie dal 1 gennaio 2007)"
DEFAULT_TIMEZONE = "Europe/Rome"

def holidays(year: int) -> set[date]:
    from meridiana.core.energy.bands import easter
    fixed = {(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)}
    days = {date(year, m, d) for m, d in fixed}
    days.add(easter(year) + timedelta(days=1))
    return days


def band_of(index: pd.DatetimeIndex, timezone: str) -> np.ndarray:
    """The band ("F1", "F2", "F3") of each local hour; the hour is the one starting at the timestamp."""
    idx = index if index.tz is None else index.tz_convert(timezone)
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


@dataclass(frozen=True)
class ItalianCalendar:
    codes: tuple[str, ...] = CODES
    default_timezone: str = DEFAULT_TIMEZONE
    source: str = SOURCE

    def holidays(self, year):
        return holidays(year)

    def band_of(self, index, timezone):
        return band_of(index, timezone)
