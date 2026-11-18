"""Power optimizers on inverters with MPPT of their own (R456, Daniel on 06/11/2026: «non solo per Huawei, va fatto anche
con gli altri principali marchi [...] anche la possibilità quando ammesso di combinare ottimizzatori doppi con
ottimizzatori singoli»): Huawei's SUN2000-P, PA0 and MERC, Sungrow's SP600S, Tigo's TS4. SolarEdge's architecture, an
inverter at a fixed string voltage, stays in energy.optimizers.

The rules are the families of catalog/data/optimizer_rules.json (catalog.rules.Family), each from its maker's documents
with page; here they become the length of a string the proposals may use and the checks of a string, of an input and of
an inverter:

- the length: Huawei's long strings with full optimization from the count of optimizers and the power per string of the
  tables (the optimizers hold the voltage below the inverter's limit: Huawei's guides, DE 10/11/2025 p. 9, FR 15/07/2026
  p. 8), never above the power per string, the most a string carries (Daniel, 06/11/2026: the automatic proposals never
  above the continuous power); Tigo and Sungrow as without optimizers, the inverter's own window (Tigo's FAQ of
  17/01/2025: «the string configuration with optimizer will be the identical one without the Optimizers»; Sungrow
  prints no string rule);
- units of one and of two modules in one string (MERC, TS4-A-2F with TS4-A-F): only where the documents allow it; where
  they do not say (MERC) a string drawn by hand is warned and the proposals keep every unit with two;
- the parallel strings of one input: the same length (Huawei), one string an input (MERC), at most 25 % shorter (Tigo
  TS4-O), the same length and orientation (Tigo's safety devices);
- the year's energy: since R456 (r18) optimizer by optimizer, each at its module's maximum power point and with its
  efficiency, the inverter's MPPT choosing the string's voltage within its window (energy.electrical_network); a family
  whose energy were not modelled would be said by the check `mlpe_energy`.

No Qt here."""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass

from ..catalog import rules
from ..i18n import _, number
from . import optimizers, stringing

VOLTAGE_KEYS = ("uoc", "mppt_high", "range")     # stringing.plan's checks a long string replaces


@dataclass(frozen=True)
class Setup:
    """The optimizers of an inverter with MPPT: the record, its family, the string rule on this inverter, the modules on
    one unit."""
    optimizer: optimizers.Optimizer
    record: dict
    family: rules.Family
    rule: rules.Rule
    per: int
    inverter: str

    @property
    def long_string(self) -> bool:
        """Sized on the count of optimizers and the power per string (Huawei with a row of its table)."""
        return self.family.sizing == rules.LONG_STRING and self.rule.state == rules.OK

    @property
    def singles_allowed(self) -> bool:
        """Whether a unit of two may carry one module in a string of units of two, by the documents."""
        return self.family.mixing in ("ok", "one_single")

    @property
    def max_strings_per_input(self) -> int:
        return int(self.family.part("parallel").get("max_strings_per_mppt") or 0)

    def source(self, key: str) -> str:
        return str(self.family.part(key).get("source") or self.family.datasheet)


def setup(entry: dict, inverter: dict | None) -> Setup | None:
    """The optimizers of an entry of energy["inverters"] on an inverter with MPPT; None without an optimizer, for an
    inverter at a fixed string voltage (energy.optimizers) or for an optimizer whose family is not on file."""
    rec = entry.get("optimizer") if isinstance(entry.get("optimizer"), dict) and entry.get("optimizer") else None
    if rec is None or not inverter or optimizers.is_fixed_voltage(inverter):
        return None
    fam = rules.family(rec)
    if fam is None or fam.sizing == rules.SOLAREDGE_TABLES:
        return None
    opt = optimizers.Optimizer.from_record(rec)
    per = entry.get("per_optimizer")
    if per.__class__ is not int or per not in fam.modules_per_unit:
        per = max(fam.modules_per_unit)
    return Setup(opt, rec, fam, rules.string_rule(fam, inverter), per, str(inverter.get("model") or ""))


def length_allowed(s: Setup, n: int) -> bool:
    """Whether a string of `n` modules may be proposed: with units of two whose documents do not allow one with a single
    module, only an even count."""
    return s.per == 1 or s.singles_allowed or n % s.per == 0


def length_range(s: Setup, module, t_min: float | None, window: tuple[int, int]) -> tuple[int, int]:
    """The fewest and the most modules of a string the proposals may use: Huawei's long strings by the count of
    optimizers, the power per string and (SUN2000-P) 1900 V over the module's Voc in the cold, not below the inverter's
    own fewest (its MPPT window at the hottest cell); otherwise the inverter's own `window`. (0, 0): none."""
    if s.rule.state == rules.NO:
        return 0, 0
    if not s.long_string:
        return window
    lo = max(window[0] or 1, s.per * s.rule.minimum - (s.per - 1 if s.singles_allowed else 0), 1)
    hi = s.per * s.rule.maximum if s.rule.maximum else 10 ** 6
    if s.rule.p_string_w and module.pmax > 0:
        hi = min(hi, int(s.rule.p_string_w / module.pmax + 1e-9))
    v_long = s.family.raw.get("long_string_voc_v")
    if v_long:
        hi = min(hi, int(float(v_long) / (stringing.ku(module, t_min) * module.voc) + 1e-9))
    return (lo, hi) if lo <= hi else (0, 0)


def _check(key, label, ok, detail, level="", source="") -> stringing.Check:
    return stringing.Check(key, label, bool(ok), detail, level, source)


def module_checks(s: Setup, module, k: int, t_min: float | None) -> list:
    """The module on its unit: power, Voc in the cold, Isc, Imp, by the family's own rule and level."""
    opt, fam = s.optimizer, s.family
    power = fam.part("module_power")
    out = []
    if power.get("per_module") and s.record.get("max_module_power_w"):
        limit = float(s.record["max_module_power_w"])
        total = float(s.record.get("max_input_power_w") or limit * k)
        ok = module.pmax <= limit + 1e-6 and k * module.pmax <= total + 1e-6
        detail = _("{p} W a module of {lim} W, {t} W on the unit of {tot} W").format(
            p=number(module.pmax, 0), lim=number(limit, 0), t=number(k * module.pmax, 0), tot=number(total, 0))
    elif power.get("per_input"):
        limit = opt.rated_w / max(1, max(fam.modules_per_unit))
        ok = module.pmax <= limit + 1e-6
        detail = _("{p} W of {lim} W an input").format(p=number(module.pmax, 0), lim=number(limit, 0))
    else:
        limit = float(power.get("factor") or 1.0) * opt.rated_w
        ok = k * module.pmax <= limit + 1e-6
        detail = _("{p} W of {lim} W").format(p=number(k * module.pmax, 0), lim=number(limit, 0))
    level = str(power.get("level") or "fail")
    out.append(_check("mlpe_power", _("Module power within what the optimizer takes"), ok or level != "fail", detail,
                      "ok" if ok else level, s.source("module_power")))
    if opt.voc_max:
        voc = (1 if opt.parallel_inputs else k) * stringing.ku(module, t_min) * module.voc
        out.append(_check("mlpe_voc", _("Module Voc at the lowest temperature within the optimizer's input"),
                          voc <= opt.voc_max + 1e-6, _("{v} V at {t} °C of {lim} V").format(
                              v=number(voc, 1), t=number(t_min, 0) if t_min is not None else "?",
                              lim=number(opt.voc_max, 0)), "", fam.datasheet))
    if opt.isc_max:
        out.append(_check("mlpe_isc", _("Module Isc within the optimizer's input"), module.isc <= opt.isc_max + 1e-6,
                          _("{i} A of {lim} A").format(i=number(module.isc, 2), lim=number(opt.isc_max, 1)), "",
                          fam.datasheet))
    imp_limit = opt.i_in_max or opt.i_out_max
    if imp_limit and module.imp > imp_limit:
        level = str(fam.part("imp_over").get("level") or "warn")
        out.append(_check("mlpe_imp", _("Module Imp within the optimizer's current"), level != "fail",
                          _("{i} A of {lim} A: the optimizer limits the current and loses power").format(
                              i=number(module.imp, 2), lim=number(imp_limit, 1)), level,
                          s.source("imp_over")))
    return out


def string_checks(s: Setup, module, n: int, group_sizes: list[int] | None, t_min: float | None,
                  window: tuple[int, int], power_w: float | None = None) -> list:
    """The checks of one string of `n` modules on the units of `s` (`group_sizes`: the designer's units, of one or two
    modules each, in string order): the module on its unit, the rule of the string on this inverter, the count of
    optimizers and the power per string (long strings), units of one and two modules together, what the year's energy
    does not model; each with its document and page."""
    fam, rule = s.family, s.rule
    try:
        groups = optimizers.module_groups(list(range(n)), s.per, group_sizes)
    except ValueError as error:
        return [_check("mlpe_groups", _("Modules on the optimizers"), False, str(error))]
    out = []
    for k in sorted({len(g) for g in groups}):
        out += module_checks(s, module, k, t_min)
    n_opt = len(groups)
    power = float(power_w) if power_w is not None else n * module.pmax
    if rule.state == rules.NO:
        out.append(_check("mlpe_inverter", _("{name} on this inverter").format(name=s.optimizer.name), False,
                          _(rule.why) if rule.why else _("not named by the maker's documents"),
                          "", fam.datasheet))
    elif rule.state == rules.UNKNOWN:
        sizing = fam.sizing == rules.INVERTER_WINDOW
        out.append(_check("mlpe_rules", _("{name}: the string's rules on this inverter").format(name=s.optimizer.name),
                          True, (_("the maker asks to be consulted before the order; the string is sized as without "
                                   "optimizers") if rule.consult else
                                 _("as without optimizers, the inverter's own window") if sizing else
                                 _("not printed by the maker: to be checked with the maker")),
                          "warn" if (rule.consult or not sizing) else "info", rule.source or fam.datasheet))
    if s.long_string:
        out.append(_check("mlpe_count", _("Optimizers in the string within the maker's range"),
                          rule.minimum <= n_opt <= rule.maximum,
                          _("{n}, from {lo} to {hi} on this inverter").format(n=n_opt, lo=rule.minimum, hi=rule.maximum),
                          "", rule.source))
        if rule.p_string_w:
            over = str(fam.raw.get("p_string_over") or "fail")
            ok = power <= rule.p_string_w + 1e-6
            out.append(_check("mlpe_string_power", _("String power within the maker's power per string"),
                              ok or over != "fail", _("{p} W of {lim} W at STC").format(
                                  p=number(power, 0, grouping=True), lim=number(rule.p_string_w, 0, grouping=True)),
                              "ok" if ok else over, rule.source if ok or over == "fail" else
                              f"{rule.source}; {fam.raw.get('p_string_over_source', '')}".rstrip("; ")))
        v_long = fam.raw.get("long_string_voc_v")
        if v_long:
            # a warning, not a limit (Daniel, 06/11/2026, R456 answer 4): the figure is of Huawei's Swiss guides, a
            # presentation, not of the datasheet; the proposals still keep within it
            v = n * stringing.ku(module, t_min) * module.voc
            within = v <= float(v_long) + 1e-6
            out.append(_check("mlpe_long_voc", _("Long string: the modules' Voc in the cold within {v} V").format(
                v=number(float(v_long), 0)), True,
                _("{v} V of {lim} V").format(v=number(v, 0), lim=number(float(v_long), 0)), "ok" if within else "warn",
                fam.raw.get("long_string_source", "")))
    singles = sum(1 for g in groups if len(g) == 1)
    if s.per > 1 and 0 < singles < n_opt:
        state, source = fam.mixing, s.source("mixing")
        name = fam.part("mixing").get("with") or ""
        if state == "ok":
            out.append(_check("mlpe_mixed", _("Units of one and of two modules in the string"), True,
                              (_("{n} modules alone, each on a {name}").format(n=singles, name=name) if name else
                               _("{n} modules alone, allowed").format(n=singles)), "ok", source))
        elif state == "one_single":
            out.append(_check("mlpe_mixed", _("At most one optimizer with a single module in the string"), singles <= 1,
                              _("{n} optimizers with a single module: either one, or all of them").format(n=singles),
                              "", source))
        elif state == "not_stated":
            out.append(_check("mlpe_mixed", _("Units of one and of two modules in the string"), True,
                              _("{n} units with one module among units with two: the documents do not say whether one "
                                "string may have both; ask the maker").format(n=singles), "warn", source))
        else:
            out.append(_check("mlpe_mixed", _("Units of one and of two modules in the string"), False,
                              _("not allowed by the documents"), "", source))
    if not fam.energy_modelled:
        beyond = window[1] and n > window[1]
        out.append(_check("mlpe_energy", _("The year's energy with these optimizers"), True,
                          (_("computed as without optimizers, and this string is longer than the inverter's own "
                             "window: the year's energy is not reliable for it yet") if beyond else
                           _("computed as without optimizers: no module-level MPPT nor optimizer losses yet")),
                          "warn" if beyond else "info", "Meridiana, docs/studio/35-ottimizzatori-marche.md"))
    return out


def adapt_plan(plan: stringing.StringPlan, s: Setup, module, n: int, group_sizes: list[int] | None,
               t_min: float | None, window: tuple[int, int], extra: list | None = None,
               power_w: float | None = None) -> stringing.StringPlan:
    """A copy of the plan of a string (stringing.plan, kept in a cache: never changed) with the optimizers' checks: on a
    long string the inverter's voltage checks are replaced by what the maker says, the others are kept."""
    checks = []
    for c in plan.checks:
        if s.long_string and c.key in VOLTAGE_KEYS:
            checks.append(_check(c.key, c.label, True,
                                 _("long string with full optimization: the optimizers hold the string below the "
                                   "inverter's limit; the maker gives a declaration on request"), "info",
                                 str(s.family.raw.get("long_string_source") or s.rule.source or s.family.datasheet)))
        else:
            checks.append(c)
    checks += string_checks(s, module, n, group_sizes, t_min, window, power_w)
    checks += list(extra or [])
    lo, hi = length_range(s, module, t_min, (plan.n_series_min, plan.n_series_max)) if s.long_string else (
        plan.n_series_min, plan.n_series_max)
    return dataclasses.replace(plan, checks=checks, n_series_min=lo, n_series_max=hi)


def input_checks(s: Setup, lengths: list[int], facings: list[tuple]) -> tuple[list, bool]:
    """The parallel strings of one input with these optimizers: their count, lengths and orientations by the family.
    (checks, whether the family settles the input's rule of alike strings in place of the plain one)."""
    par = s.family.part("parallel")
    source = str(par.get("source") or s.family.datasheet)
    level = str(par.get("level") or "fail")
    out = []
    if len(lengths) > 1:
        most = s.max_strings_per_input
        if most and len(lengths) > most:
            out.append(_check("mlpe_parallel", _("Strings on one input"), level != "fail",
                              _("{n} strings on an input that takes {m}").format(n=len(lengths), m=most), level, source))
        if par.get("same_length") and len(set(lengths)) > 1:
            out.append(_check("mlpe_lengths", _("Parallel strings of the same length"), False,
                              _("from {lo} to {hi} modules").format(lo=min(lengths), hi=max(lengths)), "", source))
        gap = par.get("length_mismatch_max")
        if gap and max(lengths):
            mismatch = 1.0 - min(lengths) / max(lengths)
            out.append(_check("mlpe_lengths", _("Parallel strings within {p} % of each other").format(
                p=number(100 * float(gap), 0)), mismatch <= float(gap) + 1e-9,
                _("the shortest {p} % shorter than the longest").format(p=number(100 * mismatch, 0)), "", source))
        distinct = {f for f in facings}
        if s.family.orientations_free and len(distinct) > 1 and s.family.function == "optimizer":
            out.append(_check("mlpe_facings", _("Parallel strings with different orientations"), True,
                              _("allowed with an optimizer on every module; separate inputs are better where possible"),
                              "info", s.source("orientations")))
    return out, s.family.function == "optimizer" and s.family.orientations_free


def unit_checks(name: str, s: Setup, powers: list[float]) -> list:
    """The checks of an inverter with these optimizers: the difference of power between its strings (MERC)."""
    out = []
    spread = s.family.raw.get("inverter_spread_w")
    if spread and len(powers) > 1:
        gap = max(powers) - min(powers)
        out.append(_check("mlpe_spread", _("{name}: strings within {w} W of each other").format(
            name=name, w=number(float(spread), 0, grouping=True)), True,
            _("{d} W between the strings").format(d=number(gap, 0, grouping=True)),
            "warn" if gap > float(spread) + 1e-6 else "ok", str(s.family.raw.get("inverter_spread_source") or "")))
    return out


def describe(s: Setup) -> str:
    """One line for the window: the family and how its strings are sized here."""
    if s.rule.state == rules.NO:
        return _("{name}: not for this inverter").format(name=s.optimizer.name)
    if s.long_string:
        return _("{name}: from {lo} to {hi} optimizers a string, at most {w} W a string ({source})").format(
            name=s.optimizer.name, lo=s.rule.minimum, hi=s.rule.maximum,
            w=number(s.rule.p_string_w, 0, grouping=True), source=s.rule.source)
    return _("{name}: strings as without optimizers ({source})").format(
        name=s.optimizer.name, source=s.rule.source or s.family.datasheet)


def ceiling_modules(s: Setup, module) -> float:
    """The most modules a string may have by the power per string (inf: no rule)."""
    if s.long_string and s.rule.p_string_w and module.pmax > 0:
        return math.floor(s.rule.p_string_w / module.pmax + 1e-9)
    return math.inf


PARTIAL_SOURCES = {
    "huawei_sun2000_p": ("Huawei Digital Power Schweiz, Optimierer-Anleitung, 10/11/2025, p. 11 («Teilweise Optimierung: "
                         "Einheitliche Ausrichtung im Strang, Auslegung wie ohne Optimierer, Optimierer frei auslegen») "
                         "e p. 12; Huawei Digital Power Suisse, Instructions Optimiseurs, 15/07/2026, p. 10 e 11"),
    "huawei_pa0": "Huawei Digital Power Suisse, Instructions Optimiseurs, 15/07/2026, p. 5",
}


def partial_checks(s: Setup, n: int, k: int, planes: int, parallel: int) -> list:
    """R456 (Daniel's answer 6, 06/11/2026): a string of `n` modules with an optimizer on `k` of them, on an input with
    `parallel` strings, over `planes` orientations, by its family's rule of partial use (optimizer_rules.json, «partial»):
    - Huawei SUN2000-450W-P2/600W-P: optimizers anywhere in the string, one orientation, sized as without optimizers; on
      an MPPT with two inputs only on one string, or on both identical strings (not recommended: guide DE 10/11/2025
      p. 11-12, FR 15/07/2026 p. 10-11);
    - Huawei SUN2000-600W-PA0: possible with the inverter's update, one input a MPPT (FR p. 5);
    - Tigo TS4-A-O: the string on its own MPPT, none in parallel, one orientation and tilt, the others without TS4 or
      with TS4-A-S (Tigo's pages, in the data file);
    - Huawei MERC: note 8 wants a MERC on every module; selective optimization asked to Huawei on 06/11/2026, to be
      confirmed (a warning, not a block);
    - Sungrow SP600S: the datasheet does not say (a warning);
    - Tigo TS4-A-F/2F: every module of the string on one (a failure)."""
    fam = s.family
    part = fam.part("partial")
    source = PARTIAL_SOURCES.get(fam.id) or str(part.get("source") or fam.datasheet)
    label = _("Optimizers on some modules only")
    detail = _("{k} of the {n} modules on {name}").format(k=k, n=n, name=s.optimizer.name)
    state = fam.partial
    if fam.id == "huawei_merc":
        return [_check("mlpe_partial", label, False, detail + "; " + _(
            "Huawei's note 8 asks a MERC on every module under the same inverter; the selective optimization was asked to "
            "Huawei on 06/11/2026: to be confirmed"), "warn", source)]
    if state == "no":
        return [_check("mlpe_partial", label, False, detail + "; " + _(
            "the maker wants every module of the string on its devices"), "fail", source)]
    if state != "conditions":
        return [_check("mlpe_partial", label, False, detail + "; " + _(
            "the datasheet does not say whether the optimizers may go on some modules only: ask the maker"), "warn",
            source)]
    out = [_check("mlpe_partial", label, True, detail + "; " + _(
        "sized as without optimizers: the inverter's window"), "info", source)]
    if planes > 1:
        out.append(_check("mlpe_partial_planes", _("One orientation in a string with optimizers on some modules"), False,
                          _("{p} orientations in the string: with the optimizers on some modules only the maker wants "
                            "one orientation and tilt (or an optimizer on every module)").format(p=planes), "fail",
                          source))
    if parallel > 1:
        if fam.id.startswith("tigo"):
            out.append(_check("mlpe_partial_parallel", _("A string with optimizers on some modules on its own MPPT"),
                              False, _("{p} strings on the input: TS4-O on some modules only on a string with its own "
                                       "MPPT, none in parallel").format(p=parallel), "fail", source))
        else:
            out.append(_check("mlpe_partial_parallel", _("A string with optimizers on some modules on its own MPPT"),
                              False, _("{p} strings on the input: optimizers on one string of the MPPT, or on every "
                                       "module of both identical strings; partial optimization of parallel strings is "
                                       "not recommended").format(p=parallel), "warn", source))
    if fam.id == "huawei_pa0":
        out.append(_check("mlpe_partial_update", _("Inverter's software for partial optimization"), True,
                          _("the partial optimization of the SUN2000-600W-PA0 needs the inverter's update"), "info",
                          source))
    return out
