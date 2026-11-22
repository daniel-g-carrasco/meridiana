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
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from meridiana.core.model.settings import ConsumptionSettings
from meridiana.i18n import _, number

if TYPE_CHECKING:
    import pandas as pd             # imported where it is used: 0,4 s at the window's start otherwise (task 18c)
from . import bands
from .pedigree import Quantity, Record, Source, Step
from .simulate import REFERENCE_YEAR
from meridiana.core.rules import registry




# weekday, Saturday, Sunday and holidays, months (January first): conventional shapes of Meridiana (see the
# docstring), not measured curves; the pedigree says so


# a yearly consumption to start from, by profile, when the designer has given none: round figures of the
# order of magnitude of each kind of user, said to be indicative in the pedigree






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




@dataclass
class Consumption(ConsumptionSettings):
    """What the designer knows of the consumption; every field may be empty. "auto" (and 0 for the numbers)
    leaves the choice to the context (guess())."""

    @classmethod
    def from_dict(cls, data: dict | None, *, profile_id: str = "it") -> Consumption:
        out = cls(**registry.get(profile_id).defaults("consumption"))
        for k, v in (data or {}).items():
            if hasattr(out, k):
                setattr(out, k, v)
        return out

    def has_data(self, *, profile_id: str = "it") -> bool:
        return registry.get(profile_id).consumption().has_data(self)

    def follows_production(self, ctx: Context, *, profile_id: str = "it") -> bool:
        return registry.get(profile_id).consumption().follows_production(self, ctx)


@dataclass
class Load:
    hourly: pd.Series                 # kWh per hour, local time of REFERENCE_YEAR
    record: Record
    basis: str                        # what it was built from
    profile_id: str = "it"
    timezone: str = ""

    @property
    def annual_kwh(self) -> float:
        return float(self.hourly.sum())

    def by_band(self) -> dict:
        b = bands.band_of(self.hourly.index, profile_id=self.profile_id, timezone=self.timezone)
        return {k: float(self.hourly[b == k].sum()) for k in registry.get(self.profile_id).calendar().codes}

    def monthly_by_band(self) -> list[dict]:
        """The kWh of each month in each band, January first: what the bills would say of this load."""
        b = bands.band_of(self.hourly.index, profile_id=self.profile_id, timezone=self.timezone)
        months = self.hourly.index.month
        return [{k: float(self.hourly[(months == m) & (b == k)].sum()) for k in registry.get(self.profile_id).calendar().codes} for m in range(1, 13)]

    def figures(self) -> dict:
        """What an energy audit looks at first: the base load (the power below which the use never goes,
        taken as the 5th percentile of the hours), the highest hour, the load factor (mean over highest),
        the share used between 8 and 18 (when a system produces most) and the share on weekends and holidays."""
        h = self.hourly
        days_off = {d for y in set(h.index.year) for d in bands.holidays(int(y), profile_id=self.profile_id)}
        off = np.array([d in days_off for d in h.index.date]) | (h.index.weekday.to_numpy() >= 5)
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


def _index(*, profile_id: str = "it", timezone: str | None = None) -> pd.DatetimeIndex:
    import pandas as pd
    return pd.date_range(f"{REFERENCE_YEAR}-01-01 00:00", periods=8760, freq="h", tz="UTC").tz_convert(timezone or registry.get(profile_id).calendar().default_timezone)




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


def _measured_on_reference(measured, *, profile_id: str = "it", timezone: str | None = None) -> pd.Series:
    """A measured hourly curve moved onto the reference year keeping the weekdays: each day of the reference
    year takes the measured day with the same weekday nearest to the same date."""
    import pandas as pd
    timezone = timezone or registry.get(profile_id).calendar().default_timezone
    measured = _rows(measured)
    texts = [str(t) for t, _v in measured]
    if any(OFFSET_RE.search(t) for t in texts[:100]):
        times = pd.to_datetime(texts, utc=True).tz_convert(timezone)       # offsets change with summer time
    else:
        times = pd.to_datetime(texts).tz_localize(timezone, ambiguous="NaT", nonexistent="shift_forward")
    src = pd.Series([float(v) for _t, v in measured], index=times)
    src = src[~src.index.isna()]
    src = src.groupby(src.index.tz_convert("UTC").floor("h").tz_convert(timezone)).sum()   # floored in UTC: no ambiguous hour
    if src.empty:
        raise ValueError(_("the measured curve is empty"))
    lookup = {(ts.date(), ts.hour): float(v) for ts, v in src.items()}
    index = _index(profile_id=profile_id, timezone=timezone)
    year = int(src.index[len(src) // 2].year)          # the year most of the curve is in
    out = np.full(len(index), np.nan)
    for i, ts in enumerate(index):
        target = ts.date().replace(year=year, day=min(ts.day, 28) if ts.month == 2 else ts.day)
        shift = (ts.weekday() - target.weekday() + 3) % 7 - 3
        out[i] = lookup.get((target + timedelta(days=shift), ts.hour), np.nan)
    series = pd.Series(out, index=index)
    missing = series.isna().mean()
    if missing > 0.2:
        raise ValueError(_("the measured curve covers only {pct}% of a year").format(pct=number(100 * (1 - missing), 0)))
    return series.interpolate(limit_direction="both")


def build(c: Consumption, ctx: Context | None = None, *, profile_id: str = "it", timezone: str | None = None) -> Load:
    """The hourly load of the reference year from what the designer gave, the best source first; what is
    left to "auto" is guessed from the context."""
    policy = registry.get(profile_id).consumption()
    timezone = timezone or registry.get(profile_id).calendar().default_timezone
    c = policy.prepare(c)
    index = _index(profile_id=profile_id, timezone=timezone)
    rec = Record(_("Consumption"))
    g = guess(ctx or Context(), profile_id=profile_id)
    by_context = Source("default", _("guessed from the context: {why}").format(why=g.why))
    guessed = c.profile == "auto" or c.profile not in policy.profiles()
    if guessed:
        c = Consumption(**{**c.__dict__, "profile": g.profile})
    synthetic = Source("default", _("conventional profile of the calculation '{name}' (a shape drawn by hand, from no "
                                    "survey or standard: the bills or the curve of the POD replace it)").format(
        name=profile_names(profile_id=profile_id).get(c.profile, c.profile)) + ("; " + by_context.label if guessed else ""))
    given = Source("input", _("given by the designer"))
    band = bands.band_of(index, profile_id=profile_id, timezone=timezone)
    month = index.month.to_numpy()
    if c.measured:
        hourly = _measured_on_reference(c.measured, profile_id=profile_id, timezone=timezone)
        basis = _("measured load curve")
        rec.add(Step("load", _("Load curve"), "",
                     _("The measured curve, moved onto the reference year keeping the weekdays (each day takes the "
                       "measured day with the same weekday nearest to its date)."),
                     [Quantity("", _("measured values"), len(_rows(c.measured)), "", Source("data", _("load curve imported")), 0)],
                     Quantity("E_{prel}", _("yearly consumption"), float(hourly.sum()), "kWh", given, 0)))
        return Load(hourly, rec, basis, profile_id, timezone)
    base = shape(c.profile, index, profile_id=profile_id)
    if c.monthly_bands_kwh and len(c.monthly_bands_kwh) == 12:
        groups = np.array([f"{m}{b}" for m, b in zip(month, band, strict=True)])
        targets = {f"{m + 1}{b}": float(c.monthly_bands_kwh[m].get(b, 0.0) or 0.0) for m in range(12) for b in registry.get(profile_id).calendar().codes}
        hourly = _calibrate(base, groups, targets)
        basis = _("bills: kWh by month and band")
        formula = r"E_h = E_{m,F}\,\frac{w_h}{\sum_{k \in (m,F)} w_k}"
    elif c.monthly_kwh and len(c.monthly_kwh) == 12:
        targets = {m + 1: float(v or 0.0) for m, v in enumerate(c.monthly_kwh)}
        hourly = _calibrate(base, month, targets)
        basis = _("kWh by month")
        formula = r"E_h = E_{m}\,\frac{w_h}{\sum_{k \in m} w_k}"
    elif c.bands_kwh and any(c.bands_kwh.get(b) for b in registry.get(profile_id).calendar().codes):
        targets = {b: float(c.bands_kwh.get(b, 0.0) or 0.0) for b in registry.get(profile_id).calendar().codes}
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
        basis = _("estimated from the yearly kWh")      # R447: under the kWh it read as their unit
        formula = r"E_h = E_{anno}\,\frac{w_h}{\sum_k w_k}"
    rec.add(Step("load", _("Hourly consumption"), formula,
                 policy.text("spread"),
                 [Quantity("", _("profile"), profile_names(profile_id=profile_id).get(c.profile, c.profile), "", synthetic),
                  Quantity("", _("basis"), basis, "", given)],
                 Quantity("E_{prel}", _("yearly consumption"), float(hourly.sum()), "kWh", given, 0),
                 registry.get(profile_id).calendar().source))
    return Load(hourly, rec, basis, profile_id, timezone)


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


OFFSET_RE = re.compile(r"(Z|[+-]\d\d:?\d\d)$")






def profile_names(*, profile_id: str = "it"):
    return registry.get(profile_id).consumption().names()


def guess(ctx, *, profile_id: str = "it"):
    return registry.get(profile_id).consumption().guess(ctx)


def shape(profile, index=None, *, profile_id: str = "it"):
    index = index if index is not None else _index(profile_id=profile_id)
    return registry.get(profile_id).consumption().shape(profile, index)


def valid_pod(pod, *, profile_id: str = "it"):
    return registry.get(profile_id).consumption().valid_supply_id(pod)


def __getattr__(name):
    if name in {"PROFILES", "STARTING_KWH", "YIELD_GUESS", "HOUSEHOLD_KWP"}:
        policy = registry.get("it").consumption()
        if name == "PROFILES": return policy.profiles()
        if name == "STARTING_KWH": return policy.starting_kwh()
        return policy.yield_guess if name == "YIELD_GUESS" else policy.household_kwp
    raise AttributeError(name)
