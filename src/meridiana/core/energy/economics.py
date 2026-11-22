"""The balance between production and consumption, hour by hour, and what it is worth over the years.

Self-consumption is, every hour, the lesser of the production and the consumption; the rest of the
production is fed into the grid, the rest of the consumption is taken from it. Cash flows and their
provenance are supplied by the project's economic policy.

The prices and costs have defaults so that a first result comes at once; every default is said to be
indicative and is meant to be replaced by the bill and the offer of the job (the pedigree marks them).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from typing import TYPE_CHECKING

import numpy as np

from meridiana.core.model.settings import EconomicsSettings
from meridiana.core.rules import registry
from meridiana.i18n import _, number
from . import bands

if TYPE_CHECKING:
    import pandas as pd             # imported where it is used: 0,4 s at the window's start otherwise (task 18c)
from .pedigree import Quantity, Record, Source, Step, computed







@dataclass
class Settings(EconomicsSettings):
    """The economic inputs of a project; the defaults are indicative and the pedigree says so."""
    defaults: list = field(default_factory=list)   # names the designer has not changed

    @classmethod
    def from_dict(cls, data: dict | None, *, profile_id: str = "it") -> Settings:
        out = cls(**registry.get(profile_id).defaults("economics"))
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
        if s.storage_coupling:
            from .storage import operating_battery
            return operating_battery(vars(s))
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
           export_limit_kw: float, index: pd.DatetimeIndex, band: np.ndarray | None = None, *, profile_id: str = "it", timezone: str | None = None) -> pd.DataFrame:
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
                         "band": band if band is not None else bands.band_of(index, profile_id=profile_id, timezone=timezone)}, index=index)


def balance(production: pd.Series, load: pd.Series, battery: Battery | None = None,
            export_limit_kw: float = -1.0, *, profile_id: str = "it", timezone: str | None = None) -> pd.DataFrame:
    """The hourly balance; with an export limit (kW at the injection point, 0 for zero export) the energy
    above it is curtailed: the inverters hold back what the grid may not take."""
    prod, cons = _arrays(production, load)
    stored = given = soc = np.zeros_like(prod)
    if battery is not None:
        stored, given, soc = dispatch(prod, cons, battery)
    return _frame(prod, cons, stored, given, soc, export_limit_kw, load.index, profile_id=profile_id, timezone=timezone)


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
             band: np.ndarray | None = None, detail: bool = True, *, profile_id: str = "it", timezone: str | None = None) -> Result:
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
    band_h = band if band is not None else bands.band_of(load.index, profile_id=profile_id, timezone=timezone)
    hb = _frame(prod_h, cons_h, *first, float(s.export_limit_kw), load.index, band_h, profile_id=profile_id, timezone=timezone)
    masks = [band_h == b for b in registry.get(profile_id).calendar().codes]
    year1 = {c: float(hb[c].to_numpy().sum()) for c in ("production", "consumption", "self", "export", "import",
                                                         "stored", "given", "curtailed")}
    self_h = hb["self"].to_numpy()
    self_by_band = {b: float(self_h[m].sum()) for b, m in zip(registry.get(profile_id).calendar().codes, masks, strict=True)}
    capex = s.capex_total if s.capex_total > 0 else s.capex_per_kwp * p_stc_kw
    if battery is not None and s.capex_total <= 0:
        capex += battery.usable_kwh * s.battery_cost_per_kwh
    policy = registry.get(profile_id).economics()
    prices = policy.prices(s)

    # the years as arrays (years, hours): the production degraded, what is self-consumed and fed in
    ys = range(1, n_years + 1)
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
    policy_flows = policy.flows(s, tuple(by_band), export_y, p_stc_kw, address, capex)
    saving, sale = policy_flows.saving, policy_flows.sale
    incentive, deduction = policy_flows.incentive, policy_flows.deduction
    zone, tariff = policy_flows.zone, policy_flows.tariff
    opex = np.array([s.opex_per_kwp * p_stc_kw * (1.0 + s.opex_escalation / 100.0) ** (y - 1) for y in ys])
    replacement = np.array([s.inverter_per_kw * p_ac_kw if y == s.inverter_year else 0.0 for y in ys])
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
           "bill_before": sum(float(cons_arr[m].sum()) * prices[b] for b, m in zip(registry.get(profile_id).calendar().codes, masks, strict=True)),
           "bill_after": sum(float(import_arr[m].sum()) * prices[b] for b, m in zip(registry.get(profile_id).calendar().codes, masks, strict=True)),
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
                 policy.text("balance_explanation"),
                 [Quantity(r"\sum P_h", _("production, first year"), year1["production"], "kWh", computed_, 0),
                  Quantity(r"\sum C_h", _("consumption"), year1["consumption"], "kWh", computed_, 0)],
                 Quantity(r"E_{auto}", _("energy self-consumed"), year1["self"], "kWh", computed_, 0), registry.get(profile_id).calendar().source))
    if battery is not None:
        bsrc = Source("data", _("datasheet of {name}").format(name=battery.name), (s.battery or {}).get("datasheet_url", ""))
        eta_source = (Source("input", _("AC round-trip efficiency given by the designer"))
                      if s.storage_coupling and s.storage_efficiency_pct else bsrc)
        power_source = computed_ if s.storage_coupling else bsrc
        rec.add(Step("battery", _("Storage"),
                     r"S_h = S_{h-1} + \sqrt{\eta}\,C_h - \frac{D_h}{\sqrt{\eta}},\quad 0 \leq S_h \leq E_u,"
                     r"\ C_h \leq P_c,\ D_h \leq P_d",
                     _("The surplus of each hour charges the battery, the shortfall discharges it, within its usable "
                       "energy and its power; the round-trip efficiency is split half in and half out. The battery "
                       "starts empty and does not charge from the grid.") +
                     (_(" AC-bus equivalent: storage conversion losses are counted once; DC clipping recovery is not modelled.")
                      if s.storage_coupling else ""),
                     [Quantity(r"E_u", _("usable energy"), battery.usable_kwh, "kWh", bsrc, 1),
                      Quantity(r"P_c", _("charge power"), battery.charge_kw, "kW", power_source, 1),
                      Quantity(r"P_d", _("discharge power"), battery.discharge_kw, "kW", power_source, 1),
                      Quantity(r"\eta", _("round-trip efficiency"), 100 * battery.efficiency, "%", eta_source, 0),
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
                else Source("default", _("default value of the calculation (0.4%/year)"))))
    capex_src = s.source("capex_total") if s.capex_total > 0 else s.source("capex_per_kwp")
    rec.add(Step("saving", _("Saving on the bill"), policy.text("saving_formula"),
                 policy.text("saving_explanation"),
                 [
                     *[Quantity(rf"E_{{auto,{code}}}", code, self_by_band[code], "kWh", computed_, 0)
                       for code in registry.get(profile_id).calendar().codes],
                     *[Quantity(rf"c_{{{code}}}", policy.text("price_label:" + code), prices[code], "€/kWh",
                                s.source(policy.text("price_field:" + code)), 3)
                       for code in registry.get(profile_id).calendar().codes]],
                 Quantity(r"R_1", _("saving, first year"), float(saving[0]), "€", computed_, 0), registry.get(profile_id).calendar().source))
    rec.add(Step("sale", _("Energy sold"), policy.text("sale_formula"),
                 policy.text("sale_explanation"),
                 [Quantity(r"E_{imm}", _("energy fed in"), year1["export"], "kWh", computed_, 0),
                  Quantity(r"p_{RID}", _("value of the energy fed in"), s.sell, "€/kWh", s.source("sell"), 3)],
                 Quantity(r"V_1", _("sale, first year"), float(sale[0]), "€", computed_, 0), ""))
    for item in policy.community_steps(s, year1, zone, tariff):
        rec.add(item)
    rec.add(Step("npv", _("Net present value"), r"VAN = -I_0 + \sum_{y=1}^{N} \frac{F_y}{(1 + r)^y}",
                 policy.text("npv_explanation"),
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
    _worked(rec, flows, s.discount, rate, float(np.sum((opex + replacement) / dfac)), discounted_production)
    return Result(hourly=hb, monthly=monthly, years=years, kpi=kpi, record=rec)


def _worked(rec: Record, flows, discount_pct: float, rate, costs_discounted: float, production_discounted: float) -> None:
    """R661 (Daniel 15/11/2026: «come mai per ogni formula dopo quella con i simboli sotto non c'è quella con i valori
    sostituiti??»): the money's formulas written again with the numbers (energy/worked.py, R479), each number the
    table's of its step (its value at the decimals the table shows, so the line and the table never differ) or one
    the calculation kept (the cash flows, the discounted sums); the sums over the years as their first two terms, the
    dots and the last. The steps over the hours (the balance, the battery, the export limit) are sums of the year's
    8760 hours, whose result is their table's; the community's tariff has its figures in the rules (tip): neither has
    a line."""
    from .worked import Lines, V

    def table(step, symbol):
        q = next((q for q in [*step.inputs, step.result] if q is not None and q.symbol == symbol), None)
        return V(q.value, q.decimals, q.unit) if q is not None and not isinstance(q.value, str) else None

    step = rec.find("saving")
    if step is not None:
        pairs = [(table(step, q.symbol), table(step, "c_{" + q.label + "}")) for q in step.inputs
                 if q.symbol.startswith("E_{auto,")]
        if pairs and all(e is not None and c is not None for e, c in pairs):
            w = Lines()
            values = {f"e{i}": e for i, (e, _c) in enumerate(pairs)} | {f"c{i}": c for i, (_e, c) in enumerate(pairs)}
            w.add("R_1 = " + " + ".join(rf"@e{i}\cdot @c{i}" for i in range(len(pairs))), table(step, "R_1"),
                  [], " + ".join(f"e{i} * c{i}" for i in range(len(pairs))), **values)
            w.put(step)
    step = rec.find("sale")
    if step is not None and table(step, r"E_{imm}") is not None:
        w = Lines()
        w.add(r"V_1 = @e\cdot @p", table(step, "V_1"), [], "e * p", e=table(step, r"E_{imm}"),
              p=table(step, r"p_{RID}"))
        w.put(step)

    def series(head: str, count: int, rate_symbol: str) -> str:
        """−I0 + F1/(1+r)^1 + F2/(1+r)^2 + … + FN/(1+r)^N, or every term when there are three or fewer."""
        term = r"\frac{@f%d}{(1 + @" + rate_symbol + r")^{%d}}"
        years = list(range(1, count + 1))
        shown = years if count <= 3 else [1, 2]
        parts = [term % (y, y) for y in shown]
        if count > 3:
            parts += [r"\dots", term % (count, count)]
        return head + " + ".join(parts)

    n = len(flows) - 1
    cash = {f"f{y}": V(flows[y], 0, "€") for y in range(1, n + 1)}
    step = rec.find("npv")
    if step is not None and n >= 1:
        w = Lines()
        w.add(series("VAN = -@i + ", n, "r"), table(step, "VAN"), [], i=table(step, "I_0"),
              r=V(discount_pct, 1, "%"), **cash)
        w.put(step)
    step = rec.find("irr")
    if step is not None and n >= 1 and rate is not None and step.result is not None:
        w = Lines()
        w.add(series("-@i + ", n, "t"), V(0, 0, "€"), [], i=V(-flows[0], 0, "€"), t=table(step, "TIR"), **cash)
        w.put(step)
    step = rec.find("lcoe")
    if step is not None and production_discounted > 0:
        w = Lines()
        i0 = rec.find("npv")
        w.add(r"LCOE = \frac{@i + @o}{@e}", table(step, "LCOE"), [], "(i + o) / e",
              i=table(i0, "I_0") if i0 is not None else V(-flows[0], 0, "€"), o=V(costs_discounted, 0, "€"),
              e=V(production_discounted, 0, "kWh"))
        w.put(step)


# what if: the same system larger or smaller, a battery larger or smaller

SIZE_FACTORS = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0)
STORAGE_FACTORS = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)


def _point(r: Result, **extra) -> dict:
    k = r.kpi
    return {**extra, "self_ratio": k["self_ratio"], "self_sufficiency": k["self_sufficiency"], "npv": k["npv"],
            "irr": k["irr"], "payback": k["payback"], "capex": k["capex"]}


def sizing(production: pd.Series, load: pd.Series, p_stc_kw: float, p_ac_kw: float, s: Settings, address: str = "",
           module_degradation: float | None = None, factors=SIZE_FACTORS, *, profile_id: str = "it", timezone: str | None = None) -> pd.DataFrame:
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
    band = bands.band_of(load.index, profile_id=profile_id, timezone=timezone)
    for f, dispatched in zip(factors, per_size, strict=True):
        sf = s
        if s.capex_total > 0:
            sf = Settings(**{**s.__dict__, "capex_total": s.capex_total * f})
        r = evaluate(production * f, load, p_stc_kw * f, p_ac_kw * f, sf, address, module_degradation,
                     dispatched=dispatched, band=band, detail=False, profile_id=profile_id, timezone=timezone)
        rows.append(_point(r, factor=f, kwp=p_stc_kw * f))
    return pd.DataFrame(rows)


def storage_sizing(production: pd.Series, load: pd.Series, p_stc_kw: float, p_ac_kw: float, s: Settings,
                   address: str = "", module_degradation: float | None = None,
                   factors=STORAGE_FACTORS, *, profile_id: str = "it", timezone: str | None = None) -> tuple[pd.DataFrame, str]:
    """The system with a battery from none to twice the daily energy it can usefully shift (the lesser of the
    surplus fed in and the consumption, a day on average): a generic battery whose power is half its
    capacity, 90% round trip, at the cost per kWh of the settings. The capacities and what each gives."""
    import pandas as pd
    hb = balance(production, load, None, float(s.export_limit_kw), profile_id=profile_id, timezone=timezone)
    scale = max(1.0, min(float(hb.export.sum()), float(hb.consumption.sum())) / 365.0)
    own = Battery.from_settings(s)
    # an offer's total holds its own battery: the generic one takes its place at the cost per kWh
    offer = s.capex_total - (own.usable_kwh * s.battery_cost_per_kwh if own is not None else 0.0)
    cases = []
    for f in factors:
        kwh = round(scale * f, 1)
        battery = ({"manufacturer": _("generic battery"), "model": number(kwh, None) + " kWh", "usable_energy_kwh": kwh,
                    "max_charge_power_w": kwh * 500.0, "max_discharge_power_w": kwh * 500.0,
                    "round_trip_efficiency_pct": 90.0} if kwh > 0 else {})
        changes = {"battery": battery, "battery_units": 1, "storage_coupling": "", "storage_inverter": {}}
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
    band = bands.band_of(load.index, profile_id=profile_id, timezone=timezone)
    for f, kwh, sb in cases:
        each = None
        if Battery.from_settings(sb) is not None:
            each = (dispatched[0][i], dispatched[1][i], dispatched[2][i])
            i += 1
        r = evaluate(production, load, p_stc_kw, p_ac_kw, sb, address, module_degradation, dispatched=each,
                     band=band, detail=False, profile_id=profile_id, timezone=timezone)
        rows.append(_point(r, factor=f, kwh=kwh))
    return pd.DataFrame(rows), _("a generic battery: power half its capacity, 90% round trip, {eur} €/kWh installed").format(
        eur=number(s.battery_cost_per_kwh, 0))


def zone_from_address(address: str, *, profile_id: str = "it") -> str:
    return registry.get(profile_id).economics().zone_from_address(address)


def tip(pz_eur_mwh, power_kw: float, zone: str, grant_pct: float = 0.0, *, profile_id: str = "it"):
    return registry.get(profile_id).economics().tip(pz_eur_mwh, power_kw, zone, grant_pct)
