"""Existing Italian demand estimates, synthetic curves and supply identifiers."""
from __future__ import annotations
from dataclasses import dataclass
import re
from typing import TYPE_CHECKING
import numpy as np
from meridiana.i18n import _, number
from . import calendar
if TYPE_CHECKING:
    import pandas as pd
    from meridiana.core.energy.consumption import Context, Guess

def _shape(*pairs) -> list[float]:
    """24 hourly weights from (from_hour, weight) pairs, each weight holding until the next pair."""
    out = [0.0] * 24
    for (h, w), nxt in zip(pairs, list(pairs[1:]) + [(24, None)], strict=True):
        for k in range(h, nxt[0]):
            out[k] = w
    return out


PROFILES = {
    "residential": (
        [0.35, 0.30, 0.28, 0.27, 0.27, 0.30, 0.50, 0.80, 0.70, 0.50, 0.45, 0.48, 0.60, 0.62, 0.50, 0.45, 0.50, 0.65,
         0.85, 1.00, 1.00, 0.90, 0.70, 0.50],
        [0.40, 0.33, 0.30, 0.28, 0.28, 0.30, 0.40, 0.55, 0.75, 0.80, 0.80, 0.80, 0.85, 0.80, 0.65, 0.60, 0.65, 0.75,
         0.90, 1.00, 1.00, 0.90, 0.75, 0.55],
        [0.42, 0.35, 0.30, 0.28, 0.28, 0.29, 0.33, 0.45, 0.65, 0.80, 0.85, 0.90, 0.95, 0.85, 0.65, 0.60, 0.65, 0.75,
         0.90, 1.00, 0.98, 0.88, 0.72, 0.52],
        [1.18, 1.08, 1.00, 0.92, 0.88, 0.92, 1.02, 0.95, 0.90, 0.95, 1.05, 1.15]),
    "residential_day": (
        [0.35, 0.30, 0.28, 0.27, 0.27, 0.30, 0.45, 0.70, 0.75, 0.75, 0.75, 0.80, 0.90, 0.85, 0.70, 0.65, 0.68, 0.75,
         0.88, 1.00, 1.00, 0.90, 0.70, 0.50],
        [0.40, 0.33, 0.30, 0.28, 0.28, 0.30, 0.40, 0.55, 0.75, 0.80, 0.80, 0.80, 0.85, 0.80, 0.65, 0.60, 0.65, 0.75,
         0.90, 1.00, 1.00, 0.90, 0.75, 0.55],
        [0.42, 0.35, 0.30, 0.28, 0.28, 0.29, 0.33, 0.45, 0.65, 0.80, 0.85, 0.90, 0.95, 0.85, 0.65, 0.60, 0.65, 0.75,
         0.90, 1.00, 0.98, 0.88, 0.72, 0.52],
        [1.18, 1.08, 1.00, 0.92, 0.88, 0.95, 1.08, 1.00, 0.92, 0.95, 1.05, 1.15]),
    "office": (
        _shape((0, 0.20), (7, 0.40), (8, 0.80), (9, 1.00), (13, 0.85), (14, 1.00), (18, 0.70), (19, 0.40), (20, 0.22)),
        _shape((0, 0.20), (8, 0.30), (13, 0.22)),
        _shape((0, 0.18)),
        [1.05, 1.00, 0.95, 0.90, 0.95, 1.10, 1.20, 0.85, 1.00, 0.95, 1.00, 1.05]),
    "shop": (
        _shape((0, 0.18), (8, 0.55), (9, 1.00), (13, 0.85), (15, 1.00), (20, 0.50), (21, 0.20)),
        _shape((0, 0.18), (8, 0.55), (9, 1.00), (20, 0.50), (21, 0.20)),
        _shape((0, 0.18), (10, 0.35), (13, 0.18)),
        [1.00, 0.95, 0.95, 0.92, 0.98, 1.10, 1.20, 1.05, 0.98, 0.92, 0.95, 1.10]),
    "industry_1": (
        _shape((0, 0.15), (6, 0.35), (7, 0.80), (8, 1.00), (12, 0.75), (13, 1.00), (17, 0.55), (18, 0.25), (19, 0.15)),
        _shape((0, 0.15)),
        _shape((0, 0.12)),
        [1.00, 1.02, 1.02, 1.00, 1.00, 1.02, 1.02, 0.60, 1.02, 1.02, 1.02, 0.95]),
    "industry_2": (
        _shape((0, 0.20), (6, 1.00), (22, 0.20)),
        _shape((0, 0.20), (6, 0.80), (14, 0.20)),
        _shape((0, 0.15)),
        [1.00, 1.02, 1.02, 1.00, 1.00, 1.02, 1.02, 0.65, 1.02, 1.02, 1.02, 0.95]),
    "industry_3": (
        _shape((0, 1.00)),
        _shape((0, 0.97)),
        _shape((0, 0.90)),
        [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 0.90, 1.00, 1.00, 1.00, 0.97]),
    "school": (
        _shape((0, 0.12), (7, 0.40), (8, 1.00), (14, 0.55), (17, 0.20), (19, 0.12)),
        _shape((0, 0.12), (8, 0.50), (13, 0.12)),
        _shape((0, 0.10)),
        [1.10, 1.08, 1.00, 0.92, 0.88, 0.70, 0.30, 0.20, 0.80, 1.00, 1.05, 0.90]),
    "hotel": (
        _shape((0, 0.45), (6, 0.70), (7, 1.00), (10, 0.75), (12, 0.85), (15, 0.70), (18, 0.90), (19, 1.00), (23, 0.60)),
        _shape((0, 0.45), (6, 0.70), (7, 1.00), (10, 0.75), (12, 0.85), (15, 0.70), (18, 0.90), (19, 1.00), (23, 0.60)),
        _shape((0, 0.45), (6, 0.70), (7, 1.00), (10, 0.75), (12, 0.85), (15, 0.70), (18, 0.90), (19, 1.00), (23, 0.60)),
        [0.75, 0.75, 0.85, 0.95, 1.05, 1.20, 1.35, 1.40, 1.15, 0.95, 0.75, 0.80]),
    "flat": ([1.0] * 24, [1.0] * 24, [1.0] * 24, [1.0] * 12),
}


STARTING_KWH = {"residential": 2700.0, "residential_day": 3500.0, "office": 25000.0, "shop": 20000.0,
                "industry_1": 100000.0, "industry_2": 250000.0, "industry_3": 500000.0, "school": 60000.0,
                "hotel": 150000.0, "flat": 10000.0}


def profile_names() -> dict:
    return {
        "residential": _("Home, out during the day"), "residential_day": _("Home, lived in during the day"),
        "office": _("Office"), "shop": _("Shop"), "industry_1": _("Industry, one shift (Monday to Friday)"),
        "industry_2": _("Industry, two shifts (and Saturday morning)"), "industry_3": _("Industry, round the clock"),
        "school": _("School"), "hotel": _("Hotel"), "flat": _("Constant"),
    }


HOUSEHOLD_KWP = 20.0               # up to this size a system is taken for a home's


YIELD_GUESS = 1200.0               # kWh/kWp, an Italian order of magnitude, until the production is computed


def guess(ctx: Context) -> Guess:
    """The user the context suggests. Up to HOUSEHOLD_KWP a home: the household ARERA's price tables refer to,
    2,700 kWh a year with 3 kW. Above it a business working one shift, with a yearly consumption equal to the
    production (a system sized for self-consumption); its supply is low voltage up to 100 kW, medium above, as
    CEI 0-21:2026 6.3 Table 5 lets the distributor propose."""
    from meridiana.core.energy.consumption import Guess
    p = ctx.p_stc_kw
    if p <= HOUSEHOLD_KWP:
        return Guess("residential", "domestic", 3.0, STARTING_KWH["residential"],
                     _("a system of {kwp} kWp is taken for a home's: the household of ARERA's price tables, 2,700 kWh "
                       "a year with 3 kW").format(kwp=number(p, 1)))
    known = ctx.production_kwh is not None and ctx.production_kwh > 0
    annual = float(ctx.production_kwh) if known else p * YIELD_GUESS
    supply = "mv" if p > 100.0 else "other_lv"
    return Guess("industry_1", supply, float(round(p)), round(annual, -2),
                 (_("a system of {kwp} kWp is taken for a business working one shift, consuming in a year what the "
                    "system produces") if known else
                  _("a system of {kwp} kWp is taken for a business working one shift, consuming in a year about what "
                    "the system will produce ({y} kWh/kWp until the production is computed)")).format(
                     kwp=number(p, 1), y=number(YIELD_GUESS, 0)))


def shape(profile: str, index: pd.DatetimeIndex | None = None) -> pd.Series:
    """The typical profile on the reference year, not scaled (its mean is about 1)."""
    import pandas as pd
    week, sat, sun, months = PROFILES.get(profile, PROFILES["flat"])
    hour = index.hour.to_numpy()
    weekday = index.weekday.to_numpy()
    days = {d for y in set(index.year) for d in calendar.holidays(int(y))}
    holiday = np.array([d in days for d in index.date])
    w = np.where(holiday | (weekday == 6), np.take(sun, hour),
                 np.where(weekday == 5, np.take(sat, hour), np.take(week, hour)))
    w = w * np.take(months, index.month.to_numpy() - 1)
    return pd.Series(w.astype(float), index=index)


POD_RE = re.compile(r"^IT\d{3}E\d{8,9}$")


def valid_pod(pod: str) -> bool:
    """An Italian electricity POD: IT, the distributor's three digits, E, eight or nine digits."""
    return bool(POD_RE.match(pod.replace(" ", "").upper()))


@dataclass(frozen=True)
class ItalianConsumptionPolicy:
    yield_guess: float = YIELD_GUESS
    household_kwp: float = HOUSEHOLD_KWP
    def profiles(self):
        return PROFILES

    def starting_kwh(self):
        return dict(STARTING_KWH)

    def names(self):
        return profile_names()

    def guess(self, ctx):
        return guess(ctx)

    def shape(self, profile, index):
        return shape(profile, index)

    def valid_supply_id(self, value):
        return valid_pod(value)

    def prepare(self, consumption):
        return consumption

    def has_data(self, c):
        return bool(c.measured or (c.monthly_bands_kwh and len(c.monthly_bands_kwh) == 12)
                    or (c.monthly_kwh and len(c.monthly_kwh) == 12)
                    or (c.bands_kwh and any(c.bands_kwh.get(b) for b in calendar.CODES)) or c.annual_kwh > 0)

    def follows_production(self, c, ctx):
        return not self.has_data(c) and ctx.p_stc_kw > HOUSEHOLD_KWP

    def text(self, key):
        return {"spread": _("The typical profile gives the weight w of each hour (weekday, Saturday, Sunday and holiday, month); "
                            "the designer's kWh are spread on those weights within each group, so every group keeps its kWh. "
                            "Bands as in ARERA's table.")}[key]
