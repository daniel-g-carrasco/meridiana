"""Strings and their checks: how many modules in series and how many strings in parallel an inverter's input
takes, and what CEI 64-8/7:2024 (9th edition, in reference\\standards\\cei) asks of them.

- UOC MAX = KU UOC STC, KU = 1 + (aUoc / 100) (Tmin - 25), Tmin the lowest temperature of the site; without
  it, 1.2 UOC STC (Annex B, B.1, p. 109). It must stay within the inverter's and the module's maximum DC
  voltage; up to 120 V the DC side may be SELV or PELV (712.414.101, p. 94).
- ISC MAX = KI ISC STC, KI at least 1.25 (Annex B, B.2, p. 109).
- With more than two strings in parallel on one input, each string needs a protection when
  1.35 I_MOD_MAX_OCPR < (Ns - 1) ISC MAX (712.431.101, p. 95), rated 1.1 ISC MAX <= In <= I_MOD_MAX_OCPR
  (712.431.102, p. 95); the string cable carries ISC MAX, or (Ns - 1) ISC MAX without protection, or In
  with it (712.433.101, p. 97).
- The MPP voltage of the string must stay within the inverter's MPPT window: at the hottest cell of the
  typical year (the lowest voltage) and at the coldest (the highest). These voltages come from the
  module's single-diode model at 1000 W/m² (components.py), not from a linear coefficient.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from meridiana.i18n import _, number
from .components import InverterSpec, ModuleSpec
from meridiana.core.model.settings import DESIGN_COLD
from meridiana.core.rules import registry
from .dependencies import load_pvlib
from .pedigree import Quantity, Record, Source, Step, computed



@dataclass
class Check:
    key: str
    label: str
    ok: bool
    detail: str
    level: str = ""                 # "ok", "warn" (a loss, not a danger), "fail", "info"; from ok when empty
    source: str = ""                # the document and its page, when not the standard of the module (optimizers.py)

    def __post_init__(self):
        if not self.level:
            self.level = "ok" if self.ok else "fail"


@dataclass
class StringPlan:
    n_series: int
    strings_per_mppt: list[int]
    checks: list[Check] = field(default_factory=list)
    record: Record | None = None
    n_series_min: int = 0
    n_series_max: int = 0
    suggested: bool = False
    uoc_max: float = 0.0            # V, at the lowest temperature
    v_limit: float = 0.0            # V, the lower of the inverter's and the modules' maximum
    vmp_hot: float = 0.0            # V, the string's MPP voltage at the hottest cell
    vmp_cold: float = 0.0           # V, at the coldest
    window: tuple = (0.0, 0.0)      # V, the inverter's MPPT window (0 where unknown)
    power_w: float = 0.0            # W at STC on the inputs of this plan

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    @property
    def modules(self) -> int:
        return self.n_series * sum(self.strings_per_mppt)


class SearchStopped(Exception):
    """A deterministic search stopped before proving feasibility or infeasibility."""


@dataclass
class SearchBudget:
    limit: int = 100000
    cancelled: object = None
    nodes: int = 0
    reason: str = ""
    # R522: a time limit (time.monotonic) and «Stop» (a callable): past either the search ends as at its step limit,
    # and the sizing keeps the best proposal found so far (cancelled throws everything away)
    deadline: float | None = None
    enough: object = None

    def expired(self) -> bool:
        return ((self.enough is not None and bool(self.enough()))
                or (self.deadline is not None and time.monotonic() > self.deadline))

    def part(self, limit: int) -> "SearchBudget":
        """A share of this search of at most `limit` steps, with its cancellation, time limit and «Stop»."""
        return SearchBudget(max(1, min(limit, self.limit - self.nodes)), self.cancelled,
                            deadline=self.deadline, enough=self.enough)

    def step(self, depth: int = 0) -> None:
        if self.cancelled is not None and self.cancelled():
            self.reason = _("String assignment cancelled; no complete choice has been applied.")
        elif self.nodes >= self.limit or depth >= 400:
            self.reason = _("String assignment incomplete: the search limit was reached.")
        elif (self.deadline is not None or self.enough is not None) and not self.nodes & 63 and self.expired():
            self.reason = _("String assignment incomplete: the time limit was reached.")
        if self.reason:
            raise SearchStopped(self.reason)
        self.nodes += 1


def strings_allowed(module: ModuleSpec, inverter: InverterSpec, k: int, ki: float | None = None, *, profile_id: str = "it") -> int:
    """How many equal strings input k takes without exceeding either current of its datasheet: the operating
    current Np x Imp and the maximum short-circuit current Np x 1.25 x Isc. A string drawn by hand may still
    exceed the operating current and gets the loss warning of `plan`; an automatic proposal never does. With no
    known series fuse, or none that can protect three strings, the proposal stops at two."""
    if not registry.get(profile_id).electrical().allow_auto:
        return 0
    policy = registry.get(profile_id).electrical()
    ki = policy.ki_default if ki is None else ki
    limits = []
    if inverter.inputs_per_mppt and k < len(inverter.inputs_per_mppt):
        limits.append(int(inverter.inputs_per_mppt[k]))
    isc_limit = inverter._limit(inverter.iscmax_per_mppt, k)
    if isc_limit is not None and ki * module.isc > 0:
        limits.append(int(isc_limit // (ki * module.isc)))
    counts = {1}
    if inverter.imax_by_strings and 0 <= k < len(inverter.imax_by_strings):
        rule = inverter.imax_by_strings[k]
        if isinstance(rule, dict):
            counts.update(int(n) for n in rule if str(n).isdigit() and int(n) > 0)
    currents = [inverter.current_limit(k, n) for n in counts]
    known = [value for value in currents if value is not None]
    if known and module.imp > 0:
        limits.append(int(max(known) / module.imp + 1e-9))
    for value, current in ((inverter.connector_current_limit(k), module.imp),
                           (inverter.connector_isc_limit(k), ki * module.isc)):
        if value is not None and current > value + 1e-9:
            return 0
    cap = policy.parallel_cap(module, ki)
    if cap is not None:
        limits.append(cap)
    upper = max(0, min(limits)) if limits else 1
    return max((n for n in range(1, upper + 1)
                if (inverter.current_limit(k, n) is None and
                    (not inverter.imax_by_strings or k >= len(inverter.imax_by_strings)
                     or not inverter.imax_by_strings[k]))
                or (inverter.current_limit(k, n) is not None
                    and n * module.imp <= inverter.current_limit(k, n) + 1e-9)), default=0)


def vmp_at(module: ModuleSpec, t_cell: float) -> float:
    """MPP voltage of one module at 1000 W/m² and the cell temperature given."""
    load_pvlib()
    from pvlib.pvsystem import max_power_point
    if module.sdm().get("linear"):
        return module.vmp * (1.0 + module.beta_voc / 100.0 * (t_cell - 25.0))
    il, io, rs, rsh, nnsvth = module.diode_params(1000.0, t_cell)      # the module's own model form
    return float(max_power_point(il, io, rs, rsh, nnsvth)["v_mp"])


def ku(module: ModuleSpec, t_min: float | None, *, profile_id: str = "it") -> float | None:
    policy = registry.get(profile_id).electrical()
    declared = getattr(module, "declared_inputs", None)
    absent = declared is not None and not {"voc", "beta_voc"}.issubset(declared)
    if t_min is None or module.beta_voc is None or (policy.voc_fallback is None and absent):
        return policy.voc_fallback
    return 1.0 + module.beta_voc / 100.0 * (t_min - 25.0)


def voltage_limit(module: ModuleSpec, inverter: InverterSpec, *, profile_id: str = "it") -> float:
    """The lower of the inverter's maximum DC voltage and the module's maximum system voltage; 1000 V, the
    common class, when neither is known."""
    limits = [float(v) for v in (inverter.vdc_max, module.max_system_voltage) if v]
    return min(limits) if limits else registry.get(profile_id).electrical().voltage_fallback


def series_range(module: ModuleSpec, inverter: InverterSpec, t_min: float | None, t_cell_max: float,
                 t_cell_min: float | None = None, *, profile_id: str = "it") -> tuple[int, int]:
    """The fewest and the most modules in series the input takes (0, 0 when none fits)."""
    if not registry.get(profile_id).electrical().allow_auto:
        return (0, 0)
    v_max = voltage_limit(module, inverter, profile_id=profile_id)
    uoc_max = ku(module, t_min, profile_id=profile_id) * module.voc
    n_hi = math.floor(v_max / uoc_max)
    if inverter.vmppt_max:
        cold = vmp_at(module, t_cell_min if t_cell_min is not None else (t_min if t_min is not None else DESIGN_COLD))
        n_hi = min(n_hi, math.floor(float(inverter.vmppt_max) / cold))
    n_lo = 1
    if inverter.vmppt_min:
        n_lo = math.ceil(float(inverter.vmppt_min) / vmp_at(module, t_cell_max))
    return (n_lo, n_hi) if n_lo <= n_hi else (0, 0)


def plan(module: ModuleSpec, inverter: InverterSpec, n_series: int, strings_per_mppt: list[int],
         t_min: float | None, t_cell_max: float, i_mod_max_ocpr: float | None = None, ki: float | None = None,
         t_min_source: Source | None = None, t_cell_cold: float | None = None,
         t_cell_source: Source | None = None, *, profile_id: str = "it") -> StringPlan:
    """Check a layout of strings on one inverter, every rule with its clause. The MPP voltage is checked at the
    hottest cell `t_cell_max` and at the coldest `t_cell_cold` (the lowest temperature when not given); before
    the year is computed, the design conditions of energy/plant.py stand in for them, said by `t_cell_source`."""
    policy = registry.get(profile_id).electrical()
    if not policy.allow_auto:
        from .physical_strings import manual_plan
        return manual_plan(module, inverter, n_series, strings_per_mppt, t_min, t_cell_max, ki, t_cell_cold, policy, registry.get(profile_id))
    ki = policy.ki_default if ki is None else ki
    rec = Record(policy.text("title"))
    out = StringPlan(n_series=n_series, strings_per_mppt=list(strings_per_mppt), record=rec,
                     power_w=n_series * sum(strings_per_mppt) * module.pmax)
    if t_cell_cold is None:
        t_cell_cold = t_min if t_min is not None else DESIGN_COLD
    out.n_series_min, out.n_series_max = series_range(module, inverter, t_min, t_cell_max, t_cell_cold, profile_id=profile_id)
    t_src = t_min_source or (Source("input", _("given by the designer")) if t_min is not None else
                             policy.pedigree("temperature_missing"))
    c_src = t_cell_source or computed("")
    m_src = module.source
    k_u = ku(module, t_min, profile_id=profile_id)
    uoc_max = k_u * module.voc * n_series
    out.uoc_max = uoc_max
    isc_max = ki * module.isc
    hot = vmp_at(module, t_cell_max) * n_series
    cold = vmp_at(module, t_cell_cold) * n_series
    v_lim = voltage_limit(module, inverter, profile_id=profile_id)
    out.v_limit, out.vmp_hot, out.vmp_cold = v_lim, hot, cold
    out.window = (float(inverter.vmppt_min or 0), float(inverter.vmppt_max or 0))

    def add(key, label, ok, detail, level=""):
        out.checks.append(Check(key, label, bool(ok), detail, level))

    rec.add(Step("uocmax", _("Maximum open-circuit voltage of the string"),
                 r"U_{OC\,MAX} = K_U\,N_s\,U_{OC\,STC},\quad K_U = 1 + \frac{\alpha_{U_{OC}}}{100}\,(T_{min} - 25)",
                 _("The open-circuit voltage grows as the modules get cold: the string must stand it on the coldest "
                   "morning of the site."),
                 [Quantity(r"N_s", _("modules in series"), n_series, "", Source("input", _("given by the designer")), 0),
                  Quantity(r"U_{OC\,STC}", _("open-circuit voltage of the module"), module.voc, "V", m_src, 2),
                  Quantity(r"\alpha_{U_{OC}}", _("temperature coefficient of Uoc"), module.beta_voc, "%/°C", m_src, 3),
                  Quantity(r"T_{min}", _("lowest temperature of the site"), t_min if t_min is not None else _("unknown"),
                           "°C", t_src, 1)],
                 Quantity(r"U_{OC\,MAX}", _("maximum open-circuit voltage"), uoc_max, "V", computed(""), 1),
                 policy.text("uoc_reference")))
    add("uoc", _("Uoc max within the maximum DC voltage of the inverter and of the modules"), uoc_max <= v_lim,
        _("{u} V of {lim} V").format(u=number(uoc_max, 0), lim=number(v_lim, 0)))
    out.checks.extend(policy.selv(uoc_max))
    if inverter.vmppt_min:
        add("mppt_low", _("MPP voltage within the MPPT window at the hottest cell"), hot >= float(inverter.vmppt_min),
            _("{v} V at {t} °C, the window starts at {lo} V").format(v=number(hot, 0), t=number(t_cell_max, 0),
                                                                      lo=number(float(inverter.vmppt_min), 0)))
    if inverter.vmppt_max:
        add("mppt_high", _("MPP voltage within the MPPT window at the coldest cell"), cold <= float(inverter.vmppt_max),
            _("{v} V at {t} °C, the window ends at {hi} V").format(v=number(cold, 0), t=number(t_cell_cold, 0),
                                                                    hi=number(float(inverter.vmppt_max), 0)))
    rec.add(Step("vmp", _("MPP voltage of the string at the extremes"),
                 r"U_{MPP}(T) = N_s\,U_{MPP,mod}(1000\ W/m^2,\ T)",
                 _("From the module's single-diode model: at the hottest cell the voltage is lowest, at the coldest "
                   "it is highest; both must stay within the inverter's MPPT window."),
                 [Quantity(r"T_{c,max}", _("hottest cell"), t_cell_max, "°C", c_src, 0),
                  Quantity(r"T_{c,min}", _("coldest cell"), t_cell_cold, "°C", c_src, 0),
                  Quantity(r"U_{MPPT,min}", _("start of the MPPT window"), float(inverter.vmppt_min or 0), "V",
                           inverter.source, 0),
                  Quantity(r"U_{MPPT,max}", _("end of the MPPT window"), float(inverter.vmppt_max or 0), "V",
                           inverter.source, 0)],
                 Quantity(r"U_{MPP}(T_{c,max})", _("lowest MPP voltage of the string"), hot, "V", computed(""), 0), ""))
    rec.add(Step("iscmax", _("Maximum short-circuit current of a string"), policy.text("isc_formula"),
                 policy.text("isc_explanation"),
                 [Quantity(r"I_{SC\,STC}", _("short-circuit current of the module"), module.isc, "A", m_src, 2),
                  Quantity(r"K_I", policy.text("ki_label"), ki, "", policy.pedigree("ki"), 2)],
                 Quantity(r"I_{SC\,MAX}", _("maximum short-circuit current"), isc_max, "A", computed(""), 2),
                 policy.text("isc_reference")))
    isc_in = inverter.iscmax_per_mppt
    if i_mod_max_ocpr is None:
        i_mod_max_ocpr = module.max_series_fuse
    for k, ns in enumerate(strings_per_mppt):
        if ns <= 0:
            continue
        name = _("input {k}").format(k=k + 1)
        rec.add(Step(f"isc_input{k}", _("{name}: maximum short-circuit current").format(name=name),
                     r"I_{SC,in} = N_p\,K_I\,I_{SC\,STC}",
                     _("Equal strings in parallel add their maximum short-circuit currents on the same input."),
                     [Quantity(r"N_p", _("strings in parallel"), ns, "", Source("input", _("given by the designer")), 0),
                      Quantity(r"I_{SC\,STC}", _("short-circuit current of the module"), module.isc, "A", m_src, 2),
                      Quantity(r"K_I", policy.text("ki_label"), ki, "", policy.pedigree("ki"), 2)],
                     Quantity(r"I_{SC,in}", _("maximum short-circuit current of the input"), ns * isc_max, "A",
                              computed(""), 2), policy.text("isc_reference")))
        rec.add(Step(f"power_input{k}", _("{name}: DC power at STC").format(name=name),
                     r"P_{DC,in} = N_s\,N_p\,P_{STC}",
                     _("Modules in series and equal strings in parallel add their nominal powers."),
                     [Quantity(r"N_s", _("modules in series"), n_series, "", Source("input", _("given by the designer")), 0),
                      Quantity(r"N_p", _("strings in parallel"), ns, "", Source("input", _("given by the designer")), 0),
                      Quantity(r"P_{STC}", _("nominal power of the module"), module.pmax, "W", m_src, 1)],
                     Quantity(r"P_{DC,in}", _("DC power of the input"), n_series * ns * module.pmax, "W",
                              computed(""), 1), ""))
        operating_limit = inverter.current_limit(k, ns)
        if operating_limit is None:
            add(f"imp_missing{k}", _("{name}: operating-current limit is unknown").format(name=name), True,
                _("The inverter's total current is not a per-MPPT limit. Enter the manufacturer's per-MPPT "
                  "data to verify this input."), "warn")
        isc_limit = inverter._limit(isc_in, k)
        if isc_limit is None:
            add(f"isc_missing{k}", _("{name}: short-circuit current limit is unknown").format(name=name), True,
                _("Enter the manufacturer's short-circuit current limit for this MPPT to verify it."), "warn")
        if inverter.inputs_per_mppt and k < len(inverter.inputs_per_mppt):
            connectors = int(inverter.inputs_per_mppt[k])
            if ns > connectors:
                add(f"connections{k}", _("{name}: more strings than physical inputs").format(name=name), True,
                    _("{n} strings on {m} connector pairs: an external parallel connection must be designed; "
                      "the inputs share this MPPT.").format(n=ns, m=connectors), "warn")
        elif inverter.inputs_per_mppt is not None:
            add(f"connections_missing{k}", _("{name}: physical input count is unknown").format(name=name), True,
                _("This tracker has no physical input count in the supplied list."), "warn")
        if operating_limit is not None:
            lim = operating_limit
            over = ns * module.imp > lim
            add(f"imp{k}", _("{name}: operating current within the input's maximum").format(name=name), True,
                (_("{i} A of {lim} A: the inverter holds the current and loses a little power") if over else
                 _("{i} A of {lim} A")).format(i=number(ns * module.imp, 1), lim=number(lim, 1)),
                "warn" if over else "ok")
        for suffix, value, current in (("imp", inverter.connector_current_limit(k), module.imp),
                                        ("isc", inverter.connector_isc_limit(k), isc_max)):
            values = inverter.imax_per_input if suffix == "imp" else inverter.iscmax_per_input
            if values is not None and value is None:
                add(f"connector_{suffix}_missing{k}", _("{name}: physical input current is unknown").format(name=name),
                    True, _("This tracker has no physical input rating in the supplied list."), "warn")
            if value is not None:
                add(f"connector_{suffix}{k}", _("{name}: current of each physical input").format(name=name),
                    current <= value + 1e-9,
                    _("{i} A of {lim} A").format(i=number(current, 1), lim=number(value, 1)))
        if isc_limit is not None:
            lim = isc_limit
            add(f"isc{k}", _("{name}: short-circuit current within the input's maximum").format(name=name),
                ns * isc_max <= lim, _("{i} A of {lim} A").format(i=number(ns * isc_max, 1), lim=number(lim, 1)))
        out.checks.extend(policy.protection(ns, isc_max, i_mod_max_ocpr, k))
    if sum(strings_per_mppt) <= 0:
        add("strings", _("At least one string"), False, _("no string on any input"))
    if out.n_series_max:
        add("range", _("Modules in series within the range the input takes"),
            out.n_series_min <= n_series <= out.n_series_max,
            _("{n}, the range is {lo} to {hi}").format(n=n_series, lo=out.n_series_min, hi=out.n_series_max))
    else:
        add("range", _("Modules in series within the range the input takes"), False,
            _("no number of modules fits this inverter's window"))
    return out


def suggest(module: ModuleSpec, inverter: InverterSpec, modules: int, t_min: float | None, t_cell_max: float,
            i_mod_max_ocpr: float | None = None, *, profile_id: str = "it") -> StringPlan | None:
    """A layout that uses as many of the modules as the inverter takes: the longest strings within the
    range, spread as evenly as the inputs allow, the current of each input respected."""
    if not registry.get(profile_id).electrical().allow_auto:
        return None
    lo, hi = series_range(module, inverter, t_min, t_cell_max, profile_id=profile_id)
    if not hi:
        return None
    inputs = int(inverter.mppt_count or 1)
    best = None
    for n in range(hi, lo - 1, -1):
        strings = modules // n
        if strings == 0:
            continue
        per = [min(p, strings_allowed(module, inverter, k, profile_id=profile_id)) for k, p in enumerate(spread(strings, inputs))]
        used = n * sum(per)
        if best is None or used > best[0]:
            best = (used, n, per)
        if used == modules:
            break
    if best is None:
        return None
    return plan(module, inverter, best[1], best[2], t_min, t_cell_max, i_mod_max_ocpr, profile_id=profile_id)


def spread(strings: int, inputs: int) -> list[int]:
    """The strings over the inputs as PVsyst spreads them: as evenly as they go, the ones more at the end
    (10 strings on 3 MPPT: 3 + 3 + 4)."""
    inputs = max(1, int(inputs))
    base, extra = divmod(max(0, int(strings)), inputs)
    return [base + (1 if k >= inputs - extra else 0) for k in range(inputs)]


# the inverter: how much it is loaded, and how evenly its inputs (calculation thresholds, said as such, not standards)

# % of the energy lost beyond the inverter's nominal power: a warning from here (Daniel's scale of 24/10/2026, R62:
# green under 1 %, yellow to 3 %, red beyond; PVsyst warns from 0.2 %)
OVERLOAD_WARN = 1.0
OVERLOAD_FAIL = 3.0             # % beyond which PVsyst does not simulate («Red warnings mean the simulation cannot run»)
IMBALANCE = 30.0                # % an input's DC power may differ from the mean of the inputs used, before a warning


def threshold_source() -> Source:
    return Source("default", _("calculation threshold, as PVsyst's: not a standard"))


def overload_loss(p_dc_w, pac_w: float, eta: float) -> float:
    """The share of the AC energy, in %, an inverter of `pac_w` loses to its limit with the DC power `p_dc_w` of
    each hour (an array of the year) at the efficiency `eta`: PVsyst's «overload loss»."""
    import numpy as np
    ac = np.clip(np.asarray(p_dc_w, dtype=float), 0.0, None) * float(eta)
    total = float(ac.sum())
    if total <= 0 or pac_w <= 0:
        return 0.0
    return 100.0 * float(np.clip(ac - pac_w, 0.0, None).sum()) / total


def overload_check(name: str, loss_pct: float) -> Check:
    """The overload of an inverter as a check: ok below 1 %, a warning to 3 %, a failure beyond (the program's
    thresholds, the scale of the DC/AC ratio's: not a standard)."""
    level = "ok" if loss_pct < OVERLOAD_WARN else ("warn" if loss_pct <= OVERLOAD_FAIL else "fail")
    return Check("overload", _("{name}: energy lost beyond the nominal power").format(name=name), level != "fail",
                 _("{pct} % of the year (calculation thresholds: a warning from {w} %, too much beyond {f} %, as "
                   "PVsyst's red)").format(pct=number(loss_pct, 1), w=number(OVERLOAD_WARN, 0), f=number(OVERLOAD_FAIL, 0)),
                 level)


def imbalance_check(name: str, powers_w: list[float]) -> Check | None:
    """How evenly the inputs used of one inverter are loaded: a warning when one differs from their mean by more
    than IMBALANCE % (a program's threshold); None with fewer than two inputs used."""
    used = [p for p in powers_w if p > 0]
    if len(used) < 2:
        return None
    mean = sum(used) / len(used)
    worst = max(abs(p - mean) for p in used) / mean * 100.0
    level = "warn" if worst > IMBALANCE else "ok"
    return Check("imbalance", _("{name}: the inputs loaded alike").format(name=name), True,
                 _("the most different input is {pct} % from their mean (a warning beyond {lim} %, a program's "
                   "threshold)").format(pct=number(worst, 0), lim=number(IMBALANCE, 0)), level)


# which module goes in which string

@dataclass
class Run:
    inverter: int                   # from 1
    mppt: int                       # from 1
    string: int                     # from 1, within its input
    modules: list                   # (sub-field id, module key, (x, y)) in the order the string runs

    @property
    def label(self) -> str:
        return f"{self.inverter}.{self.mppt}.{self.string}"


@dataclass
class Wiring:
    runs: list[Run]
    left: list                      # modules in no string, as in Run.modules


def serpentine(placed: list) -> list:
    """The modules of one array in the order a string runs along them: row by row (and, in a table of two,
    along the lower modules and back along the upper ones), each row the other way from the last, so that a
    string's ends stay close and its cables short."""
    from meridiana.core.geometry import geo
    rows: dict = {}
    for pm in placed:
        rows.setdefault((pm.row, getattr(pm, "level", 0)), []).append(pm)
    out = []
    for k, key in enumerate(sorted(rows)):
        fx, fy = geo.facing_vector(rows[key][0].azimuth)
        along = sorted(rows[key], key=lambda pm: -fy * pm.centre[0] + fx * pm.centre[1])
        out.extend(along if k % 2 == 0 else along[::-1])
    return out


def assign(arrays: list, n_series: int, per_mppt: list[int], inverters: int = 1) -> Wiring:
    """The strings of the layout on the modules: `arrays` are (sub-field id, placed modules) of one module
    type and one orientation each; every input of every inverter takes the strings the plan gives it, in
    order. A string never mixes two arrays; what does not fill a whole string, or finds no input left,
    stays out and is said to."""
    slots = [(i + 1, k + 1) for i in range(max(1, inverters)) for k, n in enumerate(per_mppt) for _s in range(n)]
    runs: list[Run] = []
    left: list = []
    taken: dict = {}
    for sfid, placed in arrays:
        order = [(sfid, pm.key, tuple(pm.centre)) for pm in serpentine(placed)]
        n = max(1, int(n_series))
        whole = len(order) // n
        for j in range(whole):
            if len(runs) >= len(slots):
                left.extend(order[j * n:])
                break
            inv, mppt = slots[len(runs)]
            taken[(inv, mppt)] = taken.get((inv, mppt), 0) + 1
            runs.append(Run(inv, mppt, taken[(inv, mppt)], order[j * n:(j + 1) * n]))
        else:
            left.extend(order[whole * n:])
    return Wiring(runs, left)


def __getattr__(name):
    if name == "NORM":
        return registry.get("it").electrical().source
    raise AttributeError(name)
