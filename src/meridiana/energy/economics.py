"""The balance between production and consumption, hour by hour, and what it is worth over the years.

Self-consumption is, every hour, the lesser of the production and the consumption; the rest of the
production is fed into the grid, the rest of the consumption is taken from it. The energy self-consumed is
saved at the price of the band it falls in; the energy fed in is sold (dedicated withdrawal, "ritiro
dedicato", at the zonal price) and, in a renewable energy community, the share of it the community
consumes in the same hour earns the premium tariff of DM MASE 414/2023 and the valuation of the GSE rules.

The prices and costs have defaults so that a first result comes at once; every default is said to be
indicative and is meant to be replaced by the bill and the offer of the job (the pedigree marks them).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from typing import TYPE_CHECKING

import numpy as np

from ..i18n import _
from . import bands

if TYPE_CHECKING:
    import pandas as pd             # imported where it is used: 0,4 s at the window's start otherwise (task 18c)
from .pedigree import Quantity, Record, Source, Step, computed

NORTH = ("emilia-romagna", "emilia romagna", "friuli", "liguria", "lombardia", "piemonte", "trentino", "alto adige",
         "südtirol", "valle d'aosta", "vallée d'aoste", "veneto")
CENTRE = ("lazio", "marche", "toscana", "umbria", "abruzzo")
DM414 = "DM MASE 414/2023, Allegato 1 (in reference\\laws)"
GSE_RULES = "GSE, Regole operative CACER e TIAD, versione del 16/07/2025, §2.2.2.2.2, p. 45-46"


def zone_from_address(address: str) -> str:
    """The zone of DM 414/2023's correction for PV ("north", "centre", "other") from the site's address."""
    a = address.lower()
    if any(r in a for r in NORTH):
        return "north"
    if any(r in a for r in CENTRE):
        return "centre"
    return "other"


def tip(pz_eur_mwh, power_kw: float, zone: str, grant_pct: float = 0.0):
    """The premium tariff on the shared energy, €/MWh (DM MASE 414/2023, Allegato 1): a fixed part by size plus
    max(0, 180 - Pz), capped by size; then the correction for PV by zone (+10 North, +4 Centre); then the cut
    for a capital grant, F growing linearly to 0.50 for a grant of 40% of the investment."""
    base, cap = (60.0, 100.0) if power_kw > 600 else (70.0, 110.0) if power_kw > 200 else (80.0, 120.0)
    t = np.minimum(base + np.maximum(0.0, 180.0 - np.asarray(pz_eur_mwh, dtype=float)), cap)
    t = t + {"north": 10.0, "centre": 4.0}.get(zone, 0.0)
    f = min(max(grant_pct, 0.0), 40.0) / 40.0 * 0.5
    return t * (1.0 - f)


@dataclass
class Settings:
    """The economic inputs of a project; the defaults are indicative and the pedigree says so."""
    buy_f1: float = 0.25            # €/kWh, every variable cost of the energy bought, taxes included
    buy_f2: float = 0.25
    buy_f3: float = 0.25
    sell: float = 0.10              # €/kWh, energy fed in (dedicated withdrawal at the zonal price)
    pz: float = 110.0               # €/MWh, the zonal price expected, for the community's tariff
    capex_per_kwp: float = 1300.0   # €/kWp, turnkey
    capex_total: float = 0.0        # €, when the offer is known (then it wins)
    opex_per_kwp: float = 20.0      # €/kWp a year: maintenance, insurance, monitoring
    inverter_year: int = 12
    inverter_per_kw: float = 150.0  # €/kW AC
    years: int = 25
    discount: float = 4.0           # %
    escalation: float = 2.0         # %/year, energy prices
    opex_escalation: float = 2.0    # %/year
    degradation: float = -1.0       # %/year; negative: from the module's datasheet, else 0.4
    deduction_pct: float = 0.0      # % of the investment given back as a tax deduction over 10 years
    community: bool = False
    shared_pct: float = 60.0        # % of the energy fed in consumed by the community in the same hour
    zone: str = ""                  # "north", "centre", "other"; "" from the address
    grant_pct: float = 0.0          # % of the investment as a capital grant
    trase: float = 0.0              # €/kWh, TRASE of the low-voltage users: from ARERA's table of the year
    battery: dict = field(default_factory=dict)      # a battery of the catalogue; empty: none
    battery_units: int = 1
    battery_cost_per_kwh: float = 650.0              # €/kWh usable, installed (indicative)
    export_limit_kw: float = -1.0   # kW at the injection point: -1 none, 0 zero export
    defaults: list = field(default_factory=list)   # names the designer has not changed

    @classmethod
    def from_dict(cls, data: dict | None) -> Settings:
        out = cls()
        given = set()
        for k, v in (data or {}).items():
            if hasattr(out, k) and k != "defaults":
                setattr(out, k, v)
                given.add(k)
        out.defaults = [f for f in cls.__dataclass_fields__ if f not in given and f != "defaults"]
        return out

    def source(self, name: str) -> Source:
        if name in self.defaults:
            return Source("default", _("indicative default: replace it with the bill or the offer"))
        return Source("input", _("given by the designer"))


@dataclass
class Result:
    hourly: pd.DataFrame            # production, consumption, self, export, import (kWh), band
    monthly: pd.DataFrame
    years: pd.DataFrame             # one row a year
    kpi: dict
    record: Record


@dataclass
class Battery:
    usable_kwh: float
    charge_kw: float
    discharge_kw: float
    efficiency: float               # round trip, 0-1
    name: str = ""

    @classmethod
    def from_settings(cls, s: Settings) -> Battery | None:
        r = s.battery or {}
        e = r.get("usable_energy_kwh") or r.get("nominal_energy_kwh")
        if not e:
            return None
        n = max(1, int(s.battery_units or 1))
        ch = (r.get("max_charge_power_w") or 0) / 1000.0 or float(e) / 2.0
        dis = (r.get("max_discharge_power_w") or 0) / 1000.0 or ch
        eta = (r.get("round_trip_efficiency_pct") or 90.0) / 100.0
        return cls(float(e) * n, float(ch) * n, float(dis) * n, float(eta),
                   f"{r.get('manufacturer', '')} {r.get('model', '')}".strip())


def dispatch(prod: np.ndarray, cons: np.ndarray, b: Battery) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Charge with the surplus, discharge on the consumption, hour by hour, within the battery's energy and
    power; the round-trip efficiency is split half on the way in and half on the way out. The energy
    stored (kWh into the battery from the system) and given (kWh to the loads) of each hour, and the
    state of charge at the end of it."""
    eta = b.efficiency ** 0.5
    stored = np.zeros_like(prod)
    given = np.zeros_like(prod)
    soc = np.zeros_like(prod)
    level = 0.0
    surplus = prod - cons
    for h in range(len(prod)):
        x = surplus[h]
        if x > 0:
            room = (b.usable_kwh - level) / eta
            c = min(x, b.charge_kw, room)
            stored[h] = c
            level += c * eta
        elif x < 0:
            d = min(-x, b.discharge_kw, level * eta)
            given[h] = d
            level -= d / eta
        soc[h] = level
    return stored, given, soc


def dispatch_many(surplus: np.ndarray, batteries: list[Battery]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """dispatch() for every battery against every row of `surplus` (production less consumption, kWh, one
    row a year or a size), in one pass over the hours with the state of every (battery, row) pair as one
    vector: arrays (batteries, rows, hours) of stored, given and soc, each equal to dispatch()'s on its pair.
    The recurrence is L_h = clip(L_{h-1} + d_h, 0, E): the clamp does what the three minima of dispatch do,
    and what went in or out of the battery is read back from the change of its level."""
    surplus = np.atleast_2d(np.asarray(surplus, dtype=float))
    nb, (nr, nh) = len(batteries), surplus.shape
    pairs = nb * nr
    eta = np.repeat([b.efficiency ** 0.5 for b in batteries], nr)
    cap = np.repeat([b.usable_kwh for b in batteries], nr)
    charge = np.repeat([b.charge_kw for b in batteries], nr)
    discharge = np.repeat([b.discharge_kw for b in batteries], nr)
    rows_t = np.broadcast_to(surplus, (nb, nr, nh)).reshape(pairs, nh).T           # (hours, pairs)
    # what each hour would add to the level (the surplus within the charge power, times eta) or take from
    # it (the shortfall within the discharge power, over eta); the clamp to [0, E] does the rest
    steps = np.where(rows_t > 0, eta * np.minimum(rows_t, charge),
                     np.where(rows_t < 0, -np.minimum(-rows_t, discharge) / eta, 0.0))
    soc_t = np.empty_like(steps)
    level = np.zeros(pairs)
    zero = np.zeros(pairs)
    for h in range(nh):
        np.add(level, steps[h], out=level)
        np.maximum(level, zero, out=level)
        np.minimum(level, cap, out=level)
        soc_t[h] = level
    delta = np.diff(soc_t, axis=0, prepend=0.0)
    stored_t = np.where(rows_t > 0, delta / eta, 0.0)
    given_t = np.where(rows_t < 0, -delta * eta, 0.0)
    shape = (nb, nr, nh)
    return (np.ascontiguousarray(stored_t.T).reshape(shape), np.ascontiguousarray(given_t.T).reshape(shape),
            np.ascontiguousarray(soc_t.T).reshape(shape))


def _arrays(production: pd.Series, load: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """The hourly production and consumption on the load's hours, kWh."""
    return production.reindex(load.index).fillna(0.0).to_numpy(), load.to_numpy()


def _frame(prod: np.ndarray, cons: np.ndarray, stored: np.ndarray, given: np.ndarray, soc: np.ndarray,
           export_limit_kw: float, index: pd.DatetimeIndex, band: np.ndarray | None = None) -> pd.DataFrame:
    """The hourly balance as a frame, from the arrays of a year and its battery's dispatch; `band` the
    band of every hour, when the caller has it already."""
    import pandas as pd
    direct = np.minimum(prod, cons)
    export = prod - direct - stored
    curtailed = np.zeros_like(prod)
    if export_limit_kw >= 0:
        curtailed = np.clip(export - export_limit_kw, 0.0, None)
        export = export - curtailed
    return pd.DataFrame({"production": prod, "consumption": cons, "direct": direct, "stored": stored,
                         "given": given, "soc": soc, "self": direct + given, "export": export,
                         "curtailed": curtailed, "import": cons - direct - given,
                         "band": band if band is not None else bands.band_of(index)}, index=index)


def balance(production: pd.Series, load: pd.Series, battery: Battery | None = None,
            export_limit_kw: float = -1.0) -> pd.DataFrame:
    """The hourly balance; with an export limit (kW at the injection point, 0 for zero export) the energy
    above it is curtailed: the inverters hold back what the grid may not take."""
    prod, cons = _arrays(production, load)
    stored = given = soc = np.zeros_like(prod)
    if battery is not None:
        stored, given, soc = dispatch(prod, cons, battery)
    return _frame(prod, cons, stored, given, soc, export_limit_kw, load.index)


def _degradation(s: Settings, module_degradation: float | None) -> float:
    """The yearly degradation, %: the settings', else the module's datasheet, else 0.4."""
    return s.degradation if s.degradation >= 0 else (module_degradation if module_degradation is not None else 0.4)


def _year_factors(deg: float, years: int) -> np.ndarray:
    """The production of each year as a share of the first: 1 for year 1, then the degradation."""
    return np.array([(1.0 - deg / 100.0) ** (y - 1) for y in range(1, years + 1)])


def _surplus_years(prod: np.ndarray, cons: np.ndarray, k: np.ndarray) -> np.ndarray:
    """Production less consumption for every year (rows), the production degraded by `k`."""
    return prod[None, :] * k[:, None] - cons[None, :]


def _npv(rate: float, flows: np.ndarray) -> float:
    years = np.arange(len(flows))
    return float(np.sum(flows / (1.0 + rate) ** years))


def irr(flows: np.ndarray) -> float | None:
    """The rate that brings the net present value to zero; None when there is none (no change of sign).
    Searched between -99% and +100% first, then up to +10 000% a year: a tiny investment with a large
    return has a rate beyond 100%, which came back as None before 23/10/2026 (study 18, B-calcoli 6.6)."""
    from scipy.optimize import brentq
    lo, hi = -0.99, 1.0
    f_lo = _npv(lo, flows)
    while np.sign(f_lo) == np.sign(_npv(hi, flows)):
        if hi >= 100.0:
            return None
        hi *= 10.0
    return float(brentq(_npv, lo, hi, args=(flows,), xtol=1e-9))


def _payback(cumulative: np.ndarray) -> float | None:
    """Years until the cumulative cash flow turns positive, interpolated within the year; None if never."""
    for y in range(1, len(cumulative)):
        if cumulative[y] >= 0 > cumulative[y - 1]:
            return y - 1 + (-cumulative[y - 1]) / (cumulative[y] - cumulative[y - 1])
    return None if cumulative[-1] < 0 else 0.0


def evaluate(production: pd.Series, load: pd.Series, p_stc_kw: float, p_ac_kw: float, s: Settings,
             address: str = "", module_degradation: float | None = None,
             dispatched: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None,
             band: np.ndarray | None = None, detail: bool = True) -> Result:
    """The balance and the money of the system over the years. `dispatched`: the battery's stored, given
    and soc for every year, (years, hours) each, when a caller has already run dispatch_many for several
    cases at once; otherwise evaluate runs it (the first year's balance is the first row). `band`: the
    band of every hour, when the caller has it. `detail`: with the pedigree and the monthly frame; the
    sweeps of sizing and storage_sizing, which read only the kpi, leave them out."""
    import pandas as pd
    rec = Record(_("Energy balance and economics"))
    battery = Battery.from_settings(s)
    n_years = max(1, int(s.years))
    deg = _degradation(s, module_degradation)
    k = _year_factors(deg, n_years)
    prod_h, cons_h = _arrays(production, load)
    if battery is None:
        dispatched = None
    elif dispatched is None or dispatched[0].shape != (n_years, len(prod_h)):
        dispatched = tuple(a[0] for a in dispatch_many(_surplus_years(prod_h, cons_h, k), [battery]))
    first = [a[0] for a in dispatched] if dispatched is not None else [np.zeros_like(prod_h)] * 3
    band_h = band if band is not None else bands.band_of(load.index)
    hb = _frame(prod_h, cons_h, *first, float(s.export_limit_kw), load.index, band_h)
    masks = [band_h == b for b in bands.BANDS]
    year1 = {c: float(hb[c].to_numpy().sum()) for c in ("production", "consumption", "self", "export", "import",
                                                         "stored", "given", "curtailed")}
    self_h = hb["self"].to_numpy()
    self_by_band = {b: float(self_h[m].sum()) for b, m in zip(bands.BANDS, masks, strict=True)}
    capex = s.capex_total if s.capex_total > 0 else s.capex_per_kwp * p_stc_kw
    if battery is not None and s.capex_total <= 0:
        capex += battery.usable_kwh * s.battery_cost_per_kwh
    zone = s.zone or zone_from_address(address)
    tariff = float(tip(s.pz, p_stc_kw, zone, s.grant_pct)) / 1000.0 if s.community else 0.0
    prices = {"F1": s.buy_f1, "F2": s.buy_f2, "F3": s.buy_f3}

    # the years as arrays (years, hours): the production degraded, what is self-consumed and fed in
    ys = range(1, n_years + 1)
    esc = np.array([(1.0 + s.escalation / 100.0) ** (y - 1) for y in ys])
    p = prod_h[None, :] * k[:, None]
    if battery is not None:
        stored, given = dispatched[0], dispatched[1]
        direct = np.minimum(p, cons_h[None, :])
        self_ = direct + given
        export = p - direct - stored
    else:
        self_ = np.minimum(p, cons_h[None, :])
        export = p - self_
    if s.export_limit_kw >= 0:
        export = np.minimum(export, s.export_limit_kw)
    by_band = [self_[:, m].sum(axis=1) for m in masks]
    export_y = export.sum(axis=1)
    saving = (by_band[0] * prices["F1"] + by_band[1] * prices["F2"] + by_band[2] * prices["F3"]) * esc
    sale = export_y * s.sell * esc
    if s.community:
        shared = export_y * s.shared_pct / 100.0
        incentive = np.where(np.array(ys) <= 20, shared * (tariff + s.trase), 0.0)
    else:
        incentive = np.zeros(n_years)
    opex = np.array([s.opex_per_kwp * p_stc_kw * (1.0 + s.opex_escalation / 100.0) ** (y - 1) for y in ys])
    replacement = np.array([s.inverter_per_kw * p_ac_kw if y == s.inverter_year else 0.0 for y in ys])
    deduction = np.array([capex * s.deduction_pct / 100.0 / 10.0 if y <= 10 else 0.0 for y in ys])
    flow = saving + sale + incentive + deduction - opex - replacement
    years = pd.DataFrame({"production": p.sum(axis=1), "self": self_.sum(axis=1), "export": export_y,
                          "saving": saving, "sale": sale, "incentive": incentive, "deduction": deduction,
                          "opex": opex, "replacement": replacement, "flow": flow},
                         index=pd.Index(np.arange(1, n_years + 1), name="year"))
    flows = np.concatenate([[-capex], flow])
    r = s.discount / 100.0
    disc = flows / (1.0 + r) ** np.arange(len(flows))
    years["cumulative"] = np.cumsum(flows)[1:]
    years["discounted_cumulative"] = np.cumsum(disc)[1:]
    npv = float(disc.sum())
    rate = irr(flows)
    payback = _payback(np.cumsum(flows))
    payback_d = _payback(np.cumsum(disc))
    dfac = (1.0 + r) ** np.arange(1, n_years + 1)
    discounted_production = float(np.sum(years.production.to_numpy() / dfac))
    lcoe = (float((capex + np.sum((opex + replacement) / dfac)) / discounted_production)
            if discounted_production > 0 else float("inf"))

    cons_arr, import_arr = hb.consumption.to_numpy(), hb["import"].to_numpy()
    kpi = {"production": year1["production"], "consumption": year1["consumption"], "self": year1["self"],
           "export": year1["export"], "import": year1["import"],
           "self_ratio": year1["self"] / year1["production"] if year1["production"] else 0.0,
           "self_sufficiency": year1["self"] / year1["consumption"] if year1["consumption"] else 0.0,
           "capex": capex, "npv": npv, "irr": rate, "payback": payback, "payback_discounted": payback_d,
           "lcoe": lcoe, "saving_1": float(saving[0]), "sale_1": float(sale[0]),
           "incentive_1": float(incentive[0]), "tip": tariff * 1000.0, "zone": zone,
           "bill_before": sum(float(cons_arr[m].sum()) * prices[b] for b, m in zip(bands.BANDS, masks, strict=True)),
           "bill_after": sum(float(import_arr[m].sum()) * prices[b] for b, m in zip(bands.BANDS, masks, strict=True)),
           "stored": year1["stored"], "given": year1["given"], "battery": battery.name if battery else "",
           "curtailed": year1["curtailed"]}
    if not detail:
        return Result(hourly=hb, monthly=pd.DataFrame(), years=years, kpi=kpi, record=rec)

    price_h = hb.band.map(prices).astype(float)
    monthly = hb.drop(columns="band").groupby(hb.index.month).sum()
    # the energy part of the bill, before and after, and what the energy fed in earns, month by month
    monthly["bill_before"] = (hb.consumption * price_h).groupby(hb.index.month).sum()
    monthly["bill_after"] = (hb["import"] * price_h).groupby(hb.index.month).sum()
    monthly["sale"] = (hb.export * s.sell).groupby(hb.index.month).sum()

    # the pedigree: the balance, the battery and the limit, then the money
    computed_ = computed("")
    rec.add(Step("balance", _("Hourly balance"),
                 r"E_{auto} = \sum_h \min(P_h, C_h),\quad E_{imm} = \sum_h (P_h - C_h)^+,\quad E_{rete} = \sum_h (C_h - P_h)^+",
                 _("Every hour the production first covers the consumption; what is left is fed into the grid, what "
                   "is missing is taken from it. Hours in Italian local time, bands as ARERA's table."),
                 [Quantity(r"\sum P_h", _("production, first year"), year1["production"], "kWh", computed_, 0),
                  Quantity(r"\sum C_h", _("consumption"), year1["consumption"], "kWh", computed_, 0)],
                 Quantity(r"E_{auto}", _("energy self-consumed"), year1["self"], "kWh", computed_, 0), bands.SOURCE))
    if battery is not None:
        bsrc = Source("data", _("datasheet of {name}").format(name=battery.name), (s.battery or {}).get("datasheet_url", ""))
        rec.add(Step("battery", _("Storage"),
                     r"S_h = S_{h-1} + \sqrt{\eta}\,C_h - \frac{D_h}{\sqrt{\eta}},\quad 0 \leq S_h \leq E_u,"
                     r"\ C_h \leq P_c,\ D_h \leq P_d",
                     _("The surplus of each hour charges the battery, the shortfall discharges it, within its usable "
                       "energy and its power; the round-trip efficiency is split half in and half out. The battery "
                       "starts empty and does not charge from the grid."),
                     [Quantity(r"E_u", _("usable energy"), battery.usable_kwh, "kWh", bsrc, 1),
                      Quantity(r"P_c", _("charge power"), battery.charge_kw, "kW", bsrc, 1),
                      Quantity(r"P_d", _("discharge power"), battery.discharge_kw, "kW", bsrc, 1),
                      Quantity(r"\eta", _("round-trip efficiency"), 100 * battery.efficiency, "%", bsrc, 0),
                      Quantity(r"\sum C_h", _("energy into the battery, first year"), year1["stored"], "kWh", computed_, 0)],
                     Quantity(r"\sum D_h", _("energy from the battery to the loads"), year1["given"], "kWh", computed_, 0),
                     ""))
    if s.export_limit_kw >= 0:
        rec.add(Step("export_limit", _("Export limit at the injection point"),
                     r"E_{imm,h} = \min(E_{imm,h},\ P_{lim}\,\Delta t),\quad E_{tagliata} = \sum_h (E_{imm,h} - P_{lim}\,\Delta t)^+",
                     _("Above the power the grid may take, the inverters hold the production back: that energy is lost."),
                     [Quantity(r"P_{lim}", _("export limit"), s.export_limit_kw, "kW", s.source("export_limit_kw"), 1)],
                     Quantity(r"E_{tagliata}", _("energy curtailed, first year"), year1["curtailed"], "kWh", computed_, 0),
                     ""))
    deg_src = (s.source("degradation") if s.degradation >= 0 else
               (Source("data", _("yearly degradation of the module's datasheet")) if module_degradation is not None
                else Source("default", _("Meridiana's default (0.4%/year)"))))
    capex_src = s.source("capex_total") if s.capex_total > 0 else s.source("capex_per_kwp")
    rec.add(Step("saving", _("Saving on the bill"), r"R_1 = \sum_{F} E_{auto,F}\, c_F",
                 _("The energy self-consumed in each band is energy not bought at that band's price."),
                 [Quantity(r"E_{auto,F1}", "F1", self_by_band["F1"], "kWh", computed_, 0),
                  Quantity(r"E_{auto,F2}", "F2", self_by_band["F2"], "kWh", computed_, 0),
                  Quantity(r"E_{auto,F3}", "F3", self_by_band["F3"], "kWh", computed_, 0),
                  Quantity(r"c_{F1}", _("price F1"), s.buy_f1, "€/kWh", s.source("buy_f1"), 3),
                  Quantity(r"c_{F2}", _("price F2"), s.buy_f2, "€/kWh", s.source("buy_f2"), 3),
                  Quantity(r"c_{F3}", _("price F3"), s.buy_f3, "€/kWh", s.source("buy_f3"), 3)],
                 Quantity(r"R_1", _("saving, first year"), float(saving[0]), "€", computed_, 0), bands.SOURCE))
    rec.add(Step("sale", _("Energy sold"), r"V_1 = E_{imm}\, p_{RID}",
                 _("The energy fed into the grid, sold to the GSE by the dedicated withdrawal at the zonal price."),
                 [Quantity(r"E_{imm}", _("energy fed in"), year1["export"], "kWh", computed_, 0),
                  Quantity(r"p_{RID}", _("value of the energy fed in"), s.sell, "€/kWh", s.source("sell"), 3)],
                 Quantity(r"V_1", _("sale, first year"), float(sale[0]), "€", computed_, 0), ""))
    if s.community:
        rec.add(Step("community", _("Renewable energy community"),
                     r"TIP = \min\left(T_0 + \max(0;\ 180 - P_z),\ T_{max}\right) + \Delta_{zona},\quad "
                     r"I_1 = E_{cond}\,(TIP + CU_{Af,a})",
                     _("On the energy fed in that the community consumes in the same hour (shared energy) the GSE pays "
                       "the premium tariff, for 20 years, and gives back the transmission component (TRASE)."),
                     [Quantity(r"E_{cond}", _("shared energy, first year"), year1["export"] * s.shared_pct / 100.0, "kWh",
                               s.source("shared_pct"), 0),
                      Quantity(r"P_z", _("zonal price expected"), s.pz, "€/MWh", s.source("pz"), 0),
                      Quantity("", _("zone"), {"north": _("North (+10 €/MWh)"), "centre": _("Centre (+4 €/MWh)")}.get(
                          zone, _("South and islands")), "", Source("computed", _("from the site's address"))),
                      Quantity(r"CU_{Af,a}", "TRASE", s.trase, "€/kWh", s.source("trase"), 4)],
                     Quantity("TIP", _("premium tariff"), tariff * 1000.0, "€/MWh", computed_, 1),
                     f"{DM414}; {GSE_RULES}"))
    rec.add(Step("npv", _("Net present value"), r"VAN = -I_0 + \sum_{y=1}^{N} \frac{F_y}{(1 + r)^y}",
                 _("Each year's cash flow: saving and sale (growing with the energy prices, shrinking with the "
                   "modules' degradation), incentives and tax deduction, less running costs and the inverter's "
                   "replacement; discounted to today."),
                 [Quantity(r"I_0", _("investment"), capex, "€", capex_src, 0),
                  Quantity("N", _("years"), s.years, "", s.source("years"), 0),
                  Quantity("r", _("discount rate"), s.discount, "%", s.source("discount"), 1),
                  Quantity("e", _("energy price growth"), s.escalation, "%/a", s.source("escalation"), 1),
                  Quantity("d", _("degradation of the modules"), deg, "%/a", deg_src, 2),
                  Quantity("O", _("running costs, first year"), s.opex_per_kwp * p_stc_kw, "€", s.source("opex_per_kwp"), 0)],
                 Quantity("VAN", _("net present value"), npv, "€", computed_, 0), ""))
    rec.add(Step("irr", _("Internal rate of return"), r"\sum_{y=0}^{N} \frac{F_y}{(1 + TIR)^y} = 0",
                 _("The discount rate at which the investment just pays back."), [],
                 Quantity("TIR", _("internal rate of return"), 100 * rate if rate is not None else _("none"), "%",
                          computed_, 1), ""))
    rec.add(Step("lcoe", _("Levelised cost of energy"),
                 r"LCOE = \frac{I_0 + \sum_y \frac{O_y}{(1 + r)^y}}{\sum_y \frac{E_y}{(1 + r)^y}}",
                 _("What each kWh produced costs over the life of the system, at today's money."), [],
                 Quantity("LCOE", _("levelised cost of energy"), lcoe, "€/kWh", computed_, 3), ""))
    return Result(hourly=hb, monthly=monthly, years=years, kpi=kpi, record=rec)


# what if: the same system larger or smaller, a battery larger or smaller

SIZE_FACTORS = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0)
STORAGE_FACTORS = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)


def _point(r: Result, **extra) -> dict:
    k = r.kpi
    return {**extra, "self_ratio": k["self_ratio"], "self_sufficiency": k["self_sufficiency"], "npv": k["npv"],
            "irr": k["irr"], "payback": k["payback"], "capex": k["capex"]}


def sizing(production: pd.Series, load: pd.Series, p_stc_kw: float, p_ac_kw: float, s: Settings, address: str = "",
           module_degradation: float | None = None, factors=SIZE_FACTORS) -> pd.DataFrame:
    """The system as designed, and larger or smaller in the same proportions: the production scaled with the
    power (same orientation, same losses), the investment too (a total of an offer scales as a cost per kWp
    would), the battery and every other setting as they are. To see which size suits the consumption."""
    import pandas as pd
    own = Battery.from_settings(s)
    years = max(1, int(s.years))
    per_size: list = [None] * len(factors)
    if own is not None:
        # the battery against every size and every year in one pass
        prod, cons = _arrays(production, load)
        k = _year_factors(_degradation(s, module_degradation), years)
        surplus = np.concatenate([_surplus_years(prod * f, cons, k) for f in factors])
        stored, given, soc = (a[0] for a in dispatch_many(surplus, [own]))
        per_size = [(stored[i * years:(i + 1) * years], given[i * years:(i + 1) * years],
                     soc[i * years:(i + 1) * years]) for i in range(len(factors))]
    rows = []
    band = bands.band_of(load.index)
    for f, dispatched in zip(factors, per_size, strict=True):
        sf = s
        if s.capex_total > 0:
            sf = Settings(**{**s.__dict__, "capex_total": s.capex_total * f})
        r = evaluate(production * f, load, p_stc_kw * f, p_ac_kw * f, sf, address, module_degradation,
                     dispatched=dispatched, band=band, detail=False)
        rows.append(_point(r, factor=f, kwp=p_stc_kw * f))
    return pd.DataFrame(rows)


def storage_sizing(production: pd.Series, load: pd.Series, p_stc_kw: float, p_ac_kw: float, s: Settings,
                   address: str = "", module_degradation: float | None = None,
                   factors=STORAGE_FACTORS) -> tuple[pd.DataFrame, str]:
    """The system with a battery from none to twice the daily energy it can usefully shift (the lesser of the
    surplus fed in and the consumption, a day on average): a generic battery whose power is half its
    capacity, 90% round trip, at the cost per kWh of the settings. The capacities and what each gives."""
    import pandas as pd
    hb = balance(production, load, None, float(s.export_limit_kw))
    scale = max(1.0, min(float(hb.export.sum()), float(hb.consumption.sum())) / 365.0)
    own = Battery.from_settings(s)
    # an offer's total holds its own battery: the generic one takes its place at the cost per kWh
    offer = s.capex_total - (own.usable_kwh * s.battery_cost_per_kwh if own is not None else 0.0)
    cases = []
    for f in factors:
        kwh = round(scale * f, 1)
        battery = ({"manufacturer": _("generic battery"), "model": f"{kwh:g} kWh", "usable_energy_kwh": kwh,
                    "max_charge_power_w": kwh * 500.0, "max_discharge_power_w": kwh * 500.0,
                    "round_trip_efficiency_pct": 90.0} if kwh > 0 else {})
        changes = {"battery": battery, "battery_units": 1}
        if s.capex_total > 0:
            changes["capex_total"] = max(0.0, offer) + kwh * s.battery_cost_per_kwh
        cases.append((f, kwh, Settings(**{**s.__dict__, **changes})))
    # every battery against every year in one pass of the dispatch
    batteries = [b for _f, _kwh, sb in cases if (b := Battery.from_settings(sb)) is not None]
    k = _year_factors(_degradation(s, module_degradation), max(1, int(s.years)))
    prod, cons = _arrays(production, load)
    dispatched = dispatch_many(_surplus_years(prod, cons, k), batteries) if batteries else None
    rows = []
    i = 0
    band = bands.band_of(load.index)
    for f, kwh, sb in cases:
        each = None
        if Battery.from_settings(sb) is not None:
            each = (dispatched[0][i], dispatched[1][i], dispatched[2][i])
            i += 1
        r = evaluate(production, load, p_stc_kw, p_ac_kw, sb, address, module_degradation, dispatched=each,
                     band=band, detail=False)
        rows.append(_point(r, factor=f, kwh=kwh))
    return pd.DataFrame(rows), _("a generic battery: power half its capacity, 90% round trip, {eur} €/kWh installed").format(
        eur=f"{s.battery_cost_per_kwh:.0f}")
