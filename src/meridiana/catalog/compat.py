"""One check of what goes with what, for the five kinds of the catalogue (R421).

`check(kind, record, context)` says whether a product of the catalogue goes with what the project has in hand, and why
not, in the designer's words. The context holds only what is known: `module`, `inverter`, `t_min` (°C) and, for a battery,
`coupling`. With nothing to compare against, the verdict is "unknown" and no row is hidden.

The rules are not repeated here: they are the ones of energy.optimizers (power, Voc, Isc, modules on one unit, the tables of
SolarEdge), energy.stringing and energy.storage. What a datasheet does not state stays unknown: an unknown limit neither
passes nor fails.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..i18n import _, number
from . import rules

OK, NOT_OK, UNKNOWN = "ok", "no", "unknown"


@dataclass
class Verdict:
    state: str = UNKNOWN
    reasons: list = field(default_factory=list)     # why not, or what remains unsaid
    passed: list = field(default_factory=list)      # what was checked and passed, in words
    per_unit: int = 0                               # an optimizer: the modules on one unit that make it pass

    def as_dict(self) -> dict:
        return {"state": self.state, "reasons": list(self.reasons), "passed": list(self.passed), "perUnit": self.per_unit}


def _positive(value) -> float | None:
    if value.__class__ in (int, float) and math.isfinite(value) and value > 0:
        return float(value)
    if isinstance(value, (list, tuple)) and value and all(v.__class__ in (int, float) for v in value):
        return float(min(value))
    return None


def _maker(rec: dict) -> str:
    return str((rec or {}).get("manufacturer") or "").casefold()


def _module_spec(record: dict):
    from ..energy.components import ModuleSpec
    return ModuleSpec.from_record(record)


def _voc_at_cold(module_record: dict, t_min: float | None) -> float | None:
    voc = _positive(module_record.get("voc"))
    if voc is None:
        return None
    beta = module_record.get("beta_voc")
    if t_min is None or beta.__class__ not in (int, float):
        return voc
    return voc * (1.0 + float(beta) / 100.0 * (float(t_min) - 25.0))


def _optimizer(record: dict, context: dict) -> Verdict:
    from ..energy import optimizers
    verdict = Verdict()
    module, inverter, t_min = context.get("module"), context.get("inverter"), context.get("t_min")
    opt = optimizers.Optimizer.from_record(record)
    if inverter:
        if _maker(record) == "solaredge" and _maker(inverter) != "solaredge":
            verdict.state = NOT_OK
            verdict.reasons.append(_("{name}: SolarEdge's optimizers work only with a SolarEdge inverter.").format(name=opt.name))
            return verdict
        if _maker(record) != "solaredge":
            maker_rule = rules.rule(record, inverter)
            if maker_rule.state == rules.NO:
                verdict.state = NOT_OK
                verdict.reasons.append(_(maker_rule.why) if maker_rule.why else _("{name} is not for this inverter.").format(name=opt.name))
                return verdict
            if maker_rule.minimum:
                verdict.passed.append(_("from {low} to {high} optimizers a string, at most {w} W a string ({source})").format(
                    low=maker_rule.minimum, high=maker_rule.maximum, w=number(maker_rule.p_string_w, 0), source=maker_rule.source))
            if maker_rule.state == rules.UNKNOWN:
                verdict.reasons.append(_("The datasheets do not say the rules of its strings on this inverter: {source}").format(
                    source=maker_rule.source or maker_rule.why))
            if not module:
                verdict.state = OK if maker_rule.state == rules.OK else UNKNOWN
                return verdict
    fixed = optimizers.fixed_voltage(inverter) if inverter else None
    if inverter and fixed is not None:
        table, why = optimizers.rules_for(opt, fixed)
        if table is None:
            verdict.state = NOT_OK
            verdict.reasons.append(why)
            return verdict
    if not module:
        verdict.state = OK if inverter and fixed is not None else UNKNOWN
        return verdict
    spec = _module_spec(module)
    refusals = []
    for per in range(opt.per_unit, 0, -1):      # the most modules on one unit first: that is what a designer wants
        failed = [c for c in optimizers.module_checks(spec, opt, per, t_min, fixed) if c.level == "fail"]
        if not failed:
            verdict.state = UNKNOWN if inverter and _maker(record) != "solaredge" and rules.rule(record, inverter).state == rules.UNKNOWN else OK
            verdict.per_unit = per
            verdict.passed.append(_("{n} module(s) of {w} W on it").format(n=per, w=number(spec.pmax, 0)))
            return verdict
        refusals.append((per, failed))
    verdict.state = NOT_OK
    for per, failed in refusals:
        for check in failed:
            verdict.reasons.append(_("{n} module(s) on it: {label}: {detail}").format(n=per, label=check.label, detail=check.detail))
    return verdict


def _inverter(record: dict, context: dict) -> Verdict:
    from ..energy import optimizers
    verdict = Verdict()
    module, t_min = context.get("module"), context.get("t_min")
    if not module:
        return verdict
    if optimizers.fixed_voltage(record) is not None:
        options = []
        refusals = []
        from .. import catalog
        for rec in catalog.search("optimizers", manufacturer="SolarEdge", limit=None):
            seen = _optimizer(rec, {"module": module, "inverter": record, "t_min": t_min})
            if seen.state == OK:
                options.append(f"{rec.get('model')} × {seen.per_unit}")
            else:
                refusals.extend(seen.reasons[:1])
        if options:
            verdict.state = OK
            verdict.passed.append(_("with the optimizers {names}").format(names=", ".join(options[:6])))
        else:
            verdict.state = NOT_OK
            verdict.reasons.append(_("No SolarEdge optimizer takes this module on this inverter."))
            verdict.reasons.extend(refusals[:3])
        return verdict
    dc_max = _positive(record.get("dc_voltage_max_v"))
    low, high = _positive(record.get("mppt_voltage_min_v")), _positive(record.get("mppt_voltage_max_v"))
    isc_limit = _positive(record.get("dc_isc_max_per_mppt_a"))
    voc = _voc_at_cold(module, t_min)
    vmp, isc = _positive(module.get("vmp")), _positive(module.get("isc"))
    known = 0
    if dc_max and voc and high and vmp:
        known += 1
        longest = math.floor(dc_max / voc)
        shortest = math.ceil(low / vmp) if low else 1
        if longest < 1 or longest < shortest:
            verdict.reasons.append(_("Series length: {low} modules for the MPPT window, at most {high} for the maximum voltage "
                                     "({v} V).").format(low=shortest, high=longest, v=number(dc_max, 0)))
        else:
            verdict.passed.append(_("from {low} to {high} modules in series").format(low=shortest, high=longest))
    if isc and isc_limit:
        known += 1
        if isc > isc_limit:
            verdict.reasons.append(_("Module Isc {isc} A over the {limit} A of one input.").format(
                isc=number(isc, 2), limit=number(isc_limit, 1)))
        else:
            verdict.passed.append(_("Isc {isc} A within {limit} A").format(isc=number(isc, 2), limit=number(isc_limit, 1)))
    verdict.state = NOT_OK if verdict.reasons else (OK if known else UNKNOWN)
    if not known:
        verdict.reasons.append(_("The datasheet values for this check are missing from the catalogue."))
    return verdict


def _micro(record: dict, context: dict) -> Verdict:
    verdict = Verdict()
    module, t_min = context.get("module"), context.get("t_min")
    if not module:
        return verdict
    per_input = _positive(record.get("dc_power_max_per_input_w"))
    v_max = _positive(record.get("dc_voltage_max_v"))
    isc_limit = _positive(record.get("dc_isc_max_per_input_a"))
    low, high = _positive(record.get("mppt_voltage_min_v")), _positive(record.get("mppt_voltage_max_v"))
    pmax, voc, vmp, isc = _positive(module.get("pmax")), _voc_at_cold(module, t_min), _positive(module.get("vmp")), _positive(module.get("isc"))
    known = 0
    if per_input and pmax:
        known += 1
        if pmax > per_input:
            verdict.reasons.append(_("Module {w} W over the {limit} W of one input.").format(w=number(pmax, 0), limit=number(per_input, 0)))
    if v_max and voc:
        known += 1
        if voc > v_max:
            verdict.reasons.append(_("Voc in the cold {v} V over the {limit} V of one input.").format(v=number(voc, 1), limit=number(v_max, 0)))
    if low and high and vmp:
        known += 1
        if not low <= vmp <= high:
            verdict.reasons.append(_("Vmp {v} V outside the MPPT window {low}-{high} V.").format(v=number(vmp, 1), low=number(low, 0), high=number(high, 0)))
    if isc_limit and isc:
        known += 1
        if isc > isc_limit:
            verdict.reasons.append(_("Module Isc {isc} A over the {limit} A of one input.").format(isc=number(isc, 2), limit=number(isc_limit, 1)))
    verdict.state = NOT_OK if verdict.reasons else (OK if known else UNKNOWN)
    if not known:
        verdict.reasons.append(_("The datasheet values for this check are missing from the catalogue."))
    return verdict


def _battery(record: dict, context: dict) -> Verdict:
    from ..energy.storage import check_storage
    inverter = context.get("inverter")
    if not inverter:
        return Verdict()
    seen = check_storage(record, inverter, context.get("coupling") or "dc")
    state = {"compatible": OK, "incompatible": NOT_OK}.get(seen.status, UNKNOWN)
    return Verdict(state, list(seen.messages) + list(seen.missing_limits) if state != OK else [], list(seen.messages) if state == OK else [])


def _module(record: dict, context: dict) -> Verdict:
    """A module chosen for what is already there: the same rules seen from the module's side."""
    inverter, optimizer = context.get("inverter"), context.get("optimizer")
    if optimizer:
        return _optimizer(optimizer, {**context, "module": record})
    if inverter:
        return _inverter(inverter, {**context, "module": record})
    return Verdict()


_CHECKS = {"modules": _module, "inverters": _inverter, "microinverters": _micro, "optimizers": _optimizer, "batteries": _battery}


def check(kind: str, record: dict, context: dict | None = None) -> Verdict:
    """Whether `record` goes with `context`; never raises for what a record lacks, it says it is unknown."""
    context = context or {}
    if not any(context.get(key) for key in ("module", "inverter", "optimizer")):
        return Verdict()
    try:
        return _CHECKS[kind](record, context)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        return Verdict(UNKNOWN, [_("This combination could not be checked: {why}").format(why=error)])


def proposed(kind: str, context: dict) -> dict | None:
    """What Meridiana would propose for the context, when it has a rule for it: today the current SolarEdge optimizer for
    a module on a fixed-voltage inverter (energy.optimizers.suggest). None otherwise."""
    if kind != "optimizers" or not context.get("module") or not context.get("inverter"):
        return None
    from ..energy import optimizers
    fixed = optimizers.fixed_voltage(context["inverter"])
    if fixed is None:
        return None
    found = optimizers.suggest(_module_spec(context["module"]), fixed, context.get("t_min"))
    return found[0] if found else None
