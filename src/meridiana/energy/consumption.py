"""The consumption of the supply point (POD), hour by hour over the reference year, from what the designer
has: the measured load curve (a CSV from the distributor's portal), the bills (kWh by month and by band),
the yearly kWh by band, or just the yearly kWh. Whatever is missing is shaped by a typical profile.

The typical profiles (PROFILES) are conventional shapes of Meridiana, drawn by hand on 21/10/2026 from the
habits of each kind of user (weekday, Saturday, Sunday and holiday, month): they come from no survey, no
standard and no distributor's data, and they are said to be conventional in the pedigree. The same for
the yearly kWh to start from (STARTING_KWH): round figures of the order of magnitude of each user.
Whoever has the bills or the load curve of the POD should give them: they replace the profile. Calibration
keeps the designer's numbers exactly: the shape is scaled band by band (and month by month when the bills
are there), so the profile sums to the kWh of each band of each month as given.

Before the designer has the data, the kind of user, its supply and its yearly kWh are guessed from the
context (guess()): a small system is taken for a home, a larger one for a business whose consumption is
of the order of the production. Every guess is said to be one and gives way to what the designer enters.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from ..i18n import _

if TYPE_CHECKING:
    import pandas as pd             # imported where it is used: 0,4 s at the window's start otherwise (task 18c)
from . import bands
from .pedigree import Quantity, Record, Source, Step
from .simulate import REFERENCE_YEAR, TIMEZONE


def _shape(*pairs) -> list[float]:
    """24 hourly weights from (from_hour, weight) pairs, each weight holding until the next pair."""
    out = [0.0] * 24
    for (h, w), nxt in zip(pairs, list(pairs[1:]) + [(24, None)], strict=True):
        for k in range(h, nxt[0]):
            out[k] = w
    return out


# weekday, Saturday, Sunday and holidays, months (January first): conventional shapes of Meridiana (see the
# docstring), not measured curves; the pedigree says so
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


# a yearly consumption to start from, by profile, when the designer has given none: round figures of the
# order of magnitude of each kind of user, said to be indicative in the pedigree
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


@dataclass
class Context:
    """What the project says about its user before the bills come: the system laid and, once computed, its
    yearly production."""
    p_stc_kw: float = 0.0
    production_kwh: float | None = None


@dataclass
class Guess:
    profile: str
    supply: str
    contract_kw: float
    annual_kwh: float
    why: str


def guess(ctx: Context) -> Guess:
    """The user the context suggests. Up to HOUSEHOLD_KWP a home: the household ARERA's price tables refer to,
    2,700 kWh a year with 3 kW. Above it a business working one shift, with a yearly consumption equal to the
    production (a system sized for self-consumption); its supply is low voltage up to 100 kW, medium above, as
    CEI 0-21:2026 6.3 Table 5 lets the distributor propose."""
    p = ctx.p_stc_kw
    if p <= HOUSEHOLD_KWP:
        return Guess("residential", "domestic", 3.0, STARTING_KWH["residential"],
                     _("a system of {kwp} kWp is taken for a home's: the household of ARERA's price tables, 2,700 kWh "
                       "a year with 3 kW").format(kwp=f"{p:.1f}"))
    known = ctx.production_kwh is not None and ctx.production_kwh > 0
    annual = float(ctx.production_kwh) if known else p * YIELD_GUESS
    supply = "mv" if p > 100.0 else "other_lv"
    return Guess("industry_1", supply, float(round(p)), round(annual, -2),
                 (_("a system of {kwp} kWp is taken for a business working one shift, consuming in a year what the "
                    "system produces") if known else
                  _("a system of {kwp} kWp is taken for a business working one shift, consuming in a year about what "
                    "the system will produce ({y} kWh/kWp until the production is computed)")).format(
                     kwp=f"{p:.1f}", y=f"{YIELD_GUESS:.0f}"))


@dataclass
class Consumption:
    """What the designer knows of the consumption; every field may be empty. "auto" (and 0 for the numbers)
    leaves the choice to the context (guess())."""
    pod: str = ""
    supply: str = "auto"              # "domestic", "other_lv", "mv"
    contract_kw: float = 0.0
    profile: str = "auto"
    annual_kwh: float = 0.0
    bands_kwh: dict = field(default_factory=dict)            # {"F1": , "F2": , "F3": } yearly
    monthly_kwh: list = field(default_factory=list)          # 12 values
    monthly_bands_kwh: list = field(default_factory=list)    # 12 dicts {"F1", "F2", "F3"}
    measured: list | dict = field(default_factory=list)     # {"start", "values"} hourly, or [[iso, kWh], ...]

    @classmethod
    def from_dict(cls, data: dict | None) -> Consumption:
        out = cls()
        for k, v in (data or {}).items():
            if hasattr(out, k):
                setattr(out, k, v)
        return out

    def has_data(self) -> bool:
        """Whether the designer gave any kWh: otherwise the yearly consumption is guessed."""
        return bool(self.measured or (self.monthly_bands_kwh and len(self.monthly_bands_kwh) == 12)
                    or (self.monthly_kwh and len(self.monthly_kwh) == 12)
                    or (self.bands_kwh and any(self.bands_kwh.get(b) for b in bands.BANDS)) or self.annual_kwh > 0)

    def follows_production(self, ctx: Context) -> bool:
        """Whether the guessed consumption changes once the production is known."""
        return not self.has_data() and ctx.p_stc_kw > HOUSEHOLD_KWP


@dataclass
class Load:
    hourly: pd.Series                 # kWh per hour, local time of REFERENCE_YEAR
    record: Record
    basis: str                        # what it was built from

    @property
    def annual_kwh(self) -> float:
        return float(self.hourly.sum())

    def by_band(self) -> dict:
        b = bands.band_of(self.hourly.index)
        return {k: float(self.hourly[b == k].sum()) for k in bands.BANDS}

    def monthly_by_band(self) -> list[dict]:
        """The kWh of each month in each band, January first: what the bills would say of this load."""
        b = bands.band_of(self.hourly.index)
        months = self.hourly.index.month
        return [{k: float(self.hourly[(months == m) & (b == k)].sum()) for k in bands.BANDS} for m in range(1, 13)]

    def figures(self) -> dict:
        """What an energy audit looks at first: the base load (the power below which the use never goes,
        taken as the 5th percentile of the hours), the highest hour, the load factor (mean over highest),
        the share used between 8 and 18 (when a system produces most) and the share on weekends and holidays."""
        h = self.hourly
        holidays = {d for y in set(h.index.year) for d in bands.holidays(int(y))}
        off = np.array([d in holidays for d in h.index.date]) | (h.index.weekday.to_numpy() >= 5)
        day = (h.index.hour >= 8) & (h.index.hour < 18)
        total = float(h.sum()) or 1.0
        peak = float(h.max())
        return {"base_kw": float(np.percentile(h.to_numpy(), 5)), "peak_kw": peak,
                "load_factor": float(h.mean()) / peak if peak > 0 else 0.0,
                "day_share": float(h[day].sum()) / total, "off_share": float(h[off].sum()) / total}

    def duration(self) -> np.ndarray:
        """The hours of the year from the highest load to the lowest: the load duration curve."""
        return np.sort(self.hourly.to_numpy())[::-1]

    def week(self) -> np.ndarray:
        """The average load of each hour of the week, Monday 0:00 first (168 values)."""
        import pandas as pd
        h = self.hourly
        key = h.index.weekday.to_numpy() * 24 + h.index.hour.to_numpy()
        return pd.Series(h.to_numpy()).groupby(key).mean().reindex(range(168), fill_value=0.0).to_numpy()


def _index() -> pd.DatetimeIndex:
    import pandas as pd
    return pd.date_range(f"{REFERENCE_YEAR}-01-01 00:00", periods=8760, freq="h", tz="UTC").tz_convert(TIMEZONE)


def shape(profile: str, index: pd.DatetimeIndex | None = None) -> pd.Series:
    """The typical profile on the reference year, not scaled (its mean is about 1)."""
    import pandas as pd
    index = index if index is not None else _index()
    week, sat, sun, months = PROFILES.get(profile, PROFILES["flat"])
    hour = index.hour.to_numpy()
    weekday = index.weekday.to_numpy()
    days = {d for y in set(index.year) for d in bands.holidays(int(y))}
    holiday = np.array([d in days for d in index.date])
    w = np.where(holiday | (weekday == 6), np.take(sun, hour),
                 np.where(weekday == 5, np.take(sat, hour), np.take(week, hour)))
    w = w * np.take(months, index.month.to_numpy() - 1)
    return pd.Series(w.astype(float), index=index)


def _calibrate(base: pd.Series, groups: np.ndarray, targets: dict) -> pd.Series:
    """Scale `base` so that each group sums to its target; a group the shape leaves empty gets its kWh spread
    evenly over its hours."""
    import pandas as pd
    out = base.to_numpy().copy()
    for g, target in targets.items():
        mask = groups == g
        if not mask.any():
            continue
        s = out[mask].sum()
        out[mask] = out[mask] * (target / s) if s > 0 else target / mask.sum()
    return pd.Series(out, index=base.index)


def to_hourly(rows: list) -> dict:
    """A curve read from a file, summed by local hour and kept compact: the first hour and the values."""
    import pandas as pd
    times = pd.to_datetime([t for t, _v in rows])
    s = pd.Series([float(v) for _t, v in rows], index=times).sort_index()
    s = s.groupby(s.index.floor("h")).sum()
    full = pd.date_range(s.index[0], s.index[-1], freq="h")
    s = s.reindex(full).interpolate(limit_direction="both")
    return {"start": full[0].isoformat(), "values": [round(float(v), 4) for v in s.to_numpy()]}


def _rows(measured) -> list:
    if isinstance(measured, dict):
        import pandas as pd
        start = pd.Timestamp(measured["start"])
        values = measured.get("values") or []
        return [[(start + pd.Timedelta(hours=k)).isoformat(), v] for k, v in enumerate(values)]
    return list(measured)


def _measured_on_reference(measured) -> pd.Series:
    """A measured hourly curve moved onto the reference year keeping the weekdays: each day of the reference
    year takes the measured day with the same weekday nearest to the same date."""
    import pandas as pd
    measured = _rows(measured)
    texts = [str(t) for t, _v in measured]
    if any(OFFSET_RE.search(t) for t in texts[:100]):
        times = pd.to_datetime(texts, utc=True).tz_convert(TIMEZONE)       # offsets change with summer time
    else:
        times = pd.to_datetime(texts).tz_localize(TIMEZONE, ambiguous="NaT", nonexistent="shift_forward")
    src = pd.Series([float(v) for _t, v in measured], index=times)
    src = src[~src.index.isna()]
    src = src.groupby(src.index.tz_convert("UTC").floor("h").tz_convert(TIMEZONE)).sum()   # floored in UTC: no ambiguous hour
    if src.empty:
        raise ValueError(_("the measured curve is empty"))
    lookup = {(ts.date(), ts.hour): float(v) for ts, v in src.items()}
    index = _index()
    year = int(src.index[len(src) // 2].year)          # the year most of the curve is in
    out = np.full(len(index), np.nan)
    for i, ts in enumerate(index):
        target = ts.date().replace(year=year, day=min(ts.day, 28) if ts.month == 2 else ts.day)
        shift = (ts.weekday() - target.weekday() + 3) % 7 - 3
        out[i] = lookup.get((target + timedelta(days=shift), ts.hour), np.nan)
    series = pd.Series(out, index=index)
    missing = series.isna().mean()
    if missing > 0.2:
        raise ValueError(_("the measured curve covers only {pct}% of a year").format(pct=round(100 * (1 - missing))))
    return series.interpolate(limit_direction="both")


def build(c: Consumption, ctx: Context | None = None) -> Load:
    """The hourly load of the reference year from what the designer gave, the best source first; what is
    left to "auto" is guessed from the context."""
    index = _index()
    rec = Record(_("Consumption"))
    g = guess(ctx or Context())
    by_context = Source("default", _("guessed from the context: {why}").format(why=g.why))
    guessed = c.profile == "auto" or c.profile not in PROFILES
    if guessed:
        c = Consumption(**{**c.__dict__, "profile": g.profile})
    synthetic = Source("default", _("Meridiana's conventional profile '{name}' (a shape drawn by hand, from no "
                                    "survey or standard: the bills or the curve of the POD replace it)").format(
        name=profile_names().get(c.profile, c.profile)) + ("; " + by_context.label if guessed else ""))
    given = Source("input", _("given by the designer"))
    band = bands.band_of(index)
    month = index.month.to_numpy()
    if c.measured:
        hourly = _measured_on_reference(c.measured)
        basis = _("measured load curve")
        rec.add(Step("load", _("Load curve"), "",
                     _("The measured curve, moved onto the reference year keeping the weekdays (each day takes the "
                       "measured day with the same weekday nearest to its date)."),
                     [Quantity("", _("measured values"), len(_rows(c.measured)), "", Source("data", _("load curve imported")), 0)],
                     Quantity("E_{prel}", _("yearly consumption"), float(hourly.sum()), "kWh", given, 0)))
        return Load(hourly, rec, basis)
    base = shape(c.profile, index)
    if c.monthly_bands_kwh and len(c.monthly_bands_kwh) == 12:
        groups = np.array([f"{m}{b}" for m, b in zip(month, band, strict=True)])
        targets = {f"{m + 1}{b}": float(c.monthly_bands_kwh[m].get(b, 0.0) or 0.0) for m in range(12) for b in bands.BANDS}
        hourly = _calibrate(base, groups, targets)
        basis = _("bills: kWh by month and band")
        formula = r"E_h = E_{m,F}\,\frac{w_h}{\sum_{k \in (m,F)} w_k}"
    elif c.monthly_kwh and len(c.monthly_kwh) == 12:
        targets = {m + 1: float(v or 0.0) for m, v in enumerate(c.monthly_kwh)}
        hourly = _calibrate(base, month, targets)
        basis = _("kWh by month")
        formula = r"E_h = E_{m}\,\frac{w_h}{\sum_{k \in m} w_k}"
    elif c.bands_kwh and any(c.bands_kwh.get(b) for b in bands.BANDS):
        targets = {b: float(c.bands_kwh.get(b, 0.0) or 0.0) for b in bands.BANDS}
        hourly = _calibrate(base, band, targets)
        basis = _("yearly kWh by band")
        formula = r"E_h = E_{F}\,\frac{w_h}{\sum_{k \in F} w_k}"
    else:
        total = float(c.annual_kwh or 0.0)
        if total <= 0:
            total = g.annual_kwh
            given = Source("default", _("guessed from the context, to be replaced by the bills or the curve of the POD: "
                                        "{why}").format(why=g.why))
        hourly = base * (total / base.sum()) if base.sum() > 0 else base * 0.0
        basis = _("yearly kWh")
        formula = r"E_h = E_{anno}\,\frac{w_h}{\sum_k w_k}"
    rec.add(Step("load", _("Hourly consumption"), formula,
                 _("The typical profile gives the weight w of each hour (weekday, Saturday, Sunday and holiday, month); "
                   "the designer's kWh are spread on those weights within each group, so every group keeps its kWh. "
                   "Bands as in ARERA's table."),
                 [Quantity("", _("profile"), profile_names().get(c.profile, c.profile), "", synthetic),
                  Quantity("", _("basis"), basis, "", given)],
                 Quantity("E_{prel}", _("yearly consumption"), float(hourly.sum()), "kWh", given, 0),
                 bands.SOURCE))
    return Load(hourly, rec, basis)


# reading a measured curve

def read_curve(path: Path, unit: str = "kWh") -> list:
    """A load curve from a CSV: one row per interval (date and time, value) or one row per day with 24 or 96
    columns (the layout of the distributors' portals). Separators ";" "," or tab, decimal comma or point;
    a power (kW) is turned into energy by the length of the interval. [[iso local timestamp, kWh], ...]"""
    import pandas as pd
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    sep = max((";", "\t", ","), key=text.splitlines()[0].count) if text.strip() else ";"
    df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str, engine="python")
    df = df.dropna(how="all")

    def num(s: pd.Series) -> pd.Series:
        s = s.astype(str).str.strip().str.replace(" ", "", regex=False)
        if sep != "," and s.str.contains(",").any():
            s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        return pd.to_numeric(s, errors="coerce")

    cols = list(df.columns)
    numeric = [c for c in cols if num(df[c]).notna().mean() > 0.9]
    rows: list = []
    if len(numeric) in (24, 96, 48):
        date_col = next(c for c in cols if c not in numeric)
        dates = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")
        step = 24 * 60 // len(numeric)
        for d, (_i, row) in zip(dates, df.iterrows(), strict=True):
            if pd.isna(d):
                continue
            for k, c in enumerate(numeric):
                v = num(pd.Series([row[c]])).iloc[0]
                if pd.notna(v):
                    t = d.normalize() + pd.Timedelta(minutes=k * step)
                    rows.append([t, float(v) * (step / 60.0 if unit == "kW" else 1.0)])
    else:
        value_col = numeric[-1] if numeric else cols[-1]
        others = [c for c in cols if c != value_col and c not in numeric[:-1]]
        stamp = df[others].astype(str).agg(" ".join, axis=1) if others else df[cols[0]]
        times = pd.to_datetime(stamp.str.replace(r"\s+", " ", regex=True), dayfirst=True, errors="coerce")
        values = num(df[value_col])
        ok = times.notna() & values.notna()
        times, values = times[ok], values[ok]
        if len(times) > 1:
            minutes = float(pd.Series(times).diff().dropna().dt.total_seconds().median() / 60.0)
        else:
            minutes = 60.0
        k = minutes / 60.0 if unit == "kW" else 1.0
        rows = [[t, float(v) * k] for t, v in zip(times, values, strict=True)]
    if not rows:
        raise ValueError(_("no date and value found in {file}").format(file=Path(path).name))
    return [[pd.Timestamp(t).isoformat(), v] for t, v in rows]


POD_RE = re.compile(r"^IT\d{3}E\d{8,9}$")
OFFSET_RE = re.compile(r"(Z|[+-]\d\d:?\d\d)$")


def valid_pod(pod: str) -> bool:
    """An Italian electricity POD: IT, the distributor's three digits, E, eight or nine digits."""
    return bool(POD_RE.match(pod.replace(" ", "").upper()))
