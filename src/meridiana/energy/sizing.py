"""Automatic inverter sizing, accepted only together with a complete and valid string proposal.

The choice is deliberately lexicographic: fewer inverters first, then fewer different models, then the DC/AC
ratio closest to the one requested. Catalogue source and model name only break exact ties. A combination that
leaves modules out or violates an input's voltage or current limits is not a sizing result.

Each combination's strings are searched within its own share of the search (CANDIDATE_STATES): one combination
whose strings cannot be decided in it does not use up the search of the others; it is said, never taken for
impossible. When no combination is valid, the reason names the limit that stops each model (series length against
the MPPT window, input current, SolarEdge's optimizer rules, maximum DC power) or the datasheet fields the
catalogue lacks, and the brands of the catalogue that could size the plant instead (R267).
"""

from __future__ import annotations

import copy
import itertools
import math
from dataclasses import dataclass, field

from ..i18n import _, ngettext, number
from . import optimizers, plant, stringing
from .components import InverterSpec


CRITERION = _("fewer inverters, then fewer models, then the closest DC/AC ratio")
MAX_CANDIDATES = 2048  # total across the whole search, including each category's ordering
MAX_SEARCH_STATES = 200000
CANDIDATE_STATES = 20000  # string-search steps of one combination; past them it is undecided, not impossible
MAX_CAUSES = 6

# brands of the catalogue that make or sell what another name did: (name, why, source)
SUCCESSORS = {"abb": ("FIMER", _("FIMER took over ABB's solar inverter business on 2 March 2020"),
                      "fimer.com, «FIMER becomes the 4th largest solar inverter supplier in the world», 02/03/2020")}


@dataclass
class Result:
    entries: list = field(default_factory=list)
    runs: list = field(default_factory=list)
    plant: plant.Plant | None = None
    ratio: float = 0.0
    criterion: str = CRITERION
    reason: str = ""
    ok: bool = False
    search_complete: bool = True
    search_nodes: int = 0
    evaluated: int = 0
    notes: list = field(default_factory=list)       # what the window says with a valid choice (conditions, undecided)
    undecided: list = field(default_factory=list)   # combinations ranked earlier whose strings were not decided


def _power(record: dict) -> float:
    return float(record.get("ac_power_nominal_w") or record.get("pac") or 0.0)


def field_names() -> dict:
    return {"ac_power_nominal_w": _("nominal AC power"), "mppt_count": _("number of MPPT"),
            "mppt_voltage_min_v": _("MPPT minimum voltage"), "mppt_voltage_max_v": _("MPPT maximum voltage")}


def missing_fields(rec: dict) -> list[str]:
    """The datasheet fields the sizing needs and `rec` lacks (catalogue keys); empty when it can be sized."""
    missing = [] if _power(rec) > 0 else ["ac_power_nominal_w"]
    if optimizers.fixed_voltage(rec) is None:
        missing += [key for key in ("mppt_count", "mppt_voltage_min_v", "mppt_voltage_max_v") if not rec.get(key)]
    return missing


def _counts(total: int, parts: int, prefix=()):
    """Every composition of `total` in `parts` positive integers, in a stable order."""
    if parts == 1:
        yield prefix + (total,)
        return
    for n in range(1, total - parts + 2):
        yield from _counts(total - n, parts - 1, prefix + (n,))


def _combinations(records: list[dict], units: int, models: int, target_ac: float):
    for indices in itertools.combinations(range(len(records)), models):
        for counts in _counts(units, models):
            ac = sum(records[i]["_sizing_pac"] * n for i, n in zip(indices, counts, strict=True))
            entries = [{"record": records[i]["_sizing_record"], "count": n, "name": ""}
                       for i, n in zip(indices, counts, strict=True)]
            yield abs(target_ac / ac - 1), entries


def _dc_capacity(entries: list[dict]) -> float | None:
    """The most DC power at STC the inverters of `entries` take, when every one is at a fixed string voltage with
    its maximum printed (optimizers' rule «opt_dc_max»); None when it is not a hard limit of all of them."""
    total = 0.0
    for e in entries:
        fixed = optimizers.fixed_voltage(e["record"])
        if fixed is None or not fixed.p_dc_max:
            return None
        total += fixed.p_dc_max * e["count"]
    return total


def _candidate(project, entries: list[dict]):
    candidate = copy.copy(project)
    strings = dict((project.energy or {}).get("strings") or {})
    strings["auto"] = True
    candidate.energy = {**(project.energy or {}), "inverters": entries, "strings": strings}
    return candidate


def _unit_bounds(project, groups: list, records: list[dict]) -> tuple[int, int]:
    """Conservative electrical bounds, independent of the requested DC/AC ratio.

    Each active unit needs at least one string. For regular inverters, each string needs at least the smallest
    supported series length, and each tracker can host only one module/facing signature in the proposal.
    Capacity uses the best module/inverter pairing, so the lower bound cannot rule out a valid mixed solution.
    Inverters at a fixed string voltage take at most their maximum DC power at STC each.
    """
    count = sum(len(g.placed) for g in groups)
    if any(optimizers.fixed_voltage(r) is not None for r in records):
        caps = [_dc_capacity([{"record": r, "count": 1}]) for r in records]
        if all(caps):
            p_stc = sum(len(g.placed) * g.module.pmax for g in groups)
            return max(1, math.ceil(p_stc / max(caps) - 1e-9)), count
        return 1, count
    cond = plant.conditions(project)
    specs = [InverterSpec.from_record(r) for r in records]
    minimum, capacity = count + 1, 0
    for g in groups:
        for spec in specs:
            lo, hi = stringing.series_range(g.module, spec, cond.t_min, cond.t_cell_max, cond.t_cell_cold)
            parallel = sum(stringing.strings_allowed(g.module, spec, k) for k in range(spec.mppt_count or 1))
            if lo and parallel:
                minimum = min(minimum, lo)
                capacity = max(capacity, hi * parallel)
    if not capacity:
        return 1, 0
    signatures = len({plant._group_signature(g) for g in groups if g.placed})
    trackers = max(s.mppt_count or 1 for s in specs)
    return max(1, math.ceil(count / capacity), math.ceil(signatures / trackers)), count // minimum


# why nothing fits

def _maker(records: list[dict]) -> str:
    return str(records[0].get("manufacturer") or "") if records else ""


def alternatives(maker: str, catalogue: list[dict] | None = None) -> list[str]:
    """Other names of the catalogue that could be sized in place of `maker`: the same company under another name
    (the CEC's «SolarEdge Technologies Ltd» and the curated «SolarEdge»), a successor (SUCCESSORS); each with its
    models that have the data the sizing needs."""
    if catalogue is None:
        from .. import catalog
        catalogue = list(catalog.load("inverters"))
    key = maker.casefold().split()[0] if maker.split() else ""
    names: dict = {}
    for rec in catalogue:
        name = str(rec.get("manufacturer") or "")
        if not name or name.casefold() == maker.casefold() or missing_fields(rec):
            continue
        first = name.casefold().split()[0]
        if first == key or (key in SUCCESSORS and name == SUCCESSORS[key][0]):
            names.setdefault(name, []).append(rec)
    out = []
    for name, recs in sorted(names.items()):
        kw = sorted({_power(r) / 1000 for r in recs})
        text = ngettext("{name}: {n} model with complete data, {lo} to {hi} kW",
                        "{name}: {n} models with complete data, {lo} to {hi} kW", len(recs)).format(
            name=name, n=len(recs), lo=number(kw[0], 1), hi=number(kw[-1], 1))
        if key in SUCCESSORS and name == SUCCESSORS[key][0]:
            text += f" ({SUCCESSORS[key][1]}; {SUCCESSORS[key][2]})"
        out.append(text)
    return out


def _unusable_reason(records: list[dict]) -> str:
    maker = _maker(records)
    missing: dict = {}
    for rec in records:
        for key in missing_fields(rec):
            missing.setdefault(key, []).append(str(rec.get("model") or ""))
    names = field_names()
    parts = [ngettext("{field} missing in {n} record", "{field} missing in {n} records", len(models)).format(
        field=names.get(key, key), n=len(models)) for key, models in missing.items()]
    text = _("None of the {n} inverters of {maker} in the catalogue can be sized: {missing} (for example {model}). "
             "Meridiana does not invent missing datasheet values.").format(
        n=len(records), maker=maker or "?", missing="; ".join(parts),
        model=next(iter(missing.values()))[0] if missing else "?")
    sources = {str(r.get("source") or "") for r in records}
    markets = {m for r in records for m in (r.get("markets") or [])}
    if sources == {"cec"}:
        volts = sorted({int(float(r["ac_voltage_nominal_v"])) for r in records if r.get("ac_voltage_nominal_v")})
        text += " " + _("These records come from the CEC list of the California Energy Commission, which gives no "
                        "MPPT count and no current per input")
        if markets == {"US"}:
            text += _(", for the US market (grid {volts} V), not for a 230/400 V grid").format(
                volts="/".join(str(v) for v in volts))
        text += "."
    others = alternatives(maker) if maker else []
    if others:
        text += " " + _("Sizable instead: {brands}.").format(brands="; ".join(others))
    return text


def _optimizer_options(module, fixed, t_min) -> tuple[list, list[str]]:
    """Every SolarEdge optimizer of the catalogue with rules for `fixed` that takes `module` (one or two on it), as
    (optimizer, modules on it, rules); and, when none does, why each one refuses, in words."""
    from .. import catalog
    options, refusals = [], []
    records = catalog.search("optimizers", manufacturer="SolarEdge", limit=None)
    # the most capable first, so that the refusals said are the nearest misses
    for rec in sorted(records, key=lambda r: (-float(r.get("rated_input_power_w") or 0), str(r.get("model")))):
        opt = optimizers.Optimizer.from_record(rec)
        rules, _why = optimizers.rules_for(opt, fixed)
        if rules is None or any(w[0] == "toggle" for w in rules.warnings):
            continue
        for per in range(1, opt.per_unit + 1):
            fails = [c for c in optimizers.module_checks(module, opt, per, t_min, fixed) if c.level == "fail"]
            if fails:
                what = {"opt_power": "P", "opt_voc": "Voc", "opt_isc": "Isc"}.get(fails[0].key, fails[0].label)
                refusals.append(f"{opt.model} x {per}: {what} {fails[0].detail}")
            else:
                options.append((opt, per, rules))
    return options, refusals


def _pooled(groups: list) -> list[list]:
    """The groups as the proposal strings them: those of the same module and plane together, different planes never
    in one string."""
    pooled: dict = {}
    for g in groups:
        if g.placed:
            pooled.setdefault(plant._group_signature(g), []).append(g)
    return list(pooled.values())


def _static(rec: dict, pooled: list[list], cond) -> tuple[set, str, int]:
    """What `rec` can string without a search, whatever the quantity: the indices of `pooled` it can serve, the
    first cause in words for one it cannot, the fewest modules of one of its strings. The limits: the series length
    against the MPPT window, the input current, SolarEdge's optimizers for the module and their fewest per string;
    formulas and data are those of stringing.py and optimizers.py."""
    fixed = optimizers.fixed_voltage(rec)
    spec = None if fixed is not None else InverterSpec.from_record(rec)
    served, causes, fewest_all = set(), [], []
    for i, same in enumerate(pooled):
        g, n = same[0], sum(len(x.placed) for x in same)
        where = ", ".join(x.name for x in same)
        cause = ""
        if fixed is not None:
            options, refusals = _optimizer_options(g.module, fixed, cond.t_min)
            if not options:
                cause = _("no SolarEdge optimizer of the catalogue takes {module} (Pmax {p} W, Voc {voc} V, Isc "
                          "{isc} A): {why}").format(module=g.module.model or where, p=number(g.module.pmax, 0),
                                                    voc=number(g.module.voc, 2), isc=number(g.module.isc, 2),
                                                    why="; ".join(refusals[:3]) or "?")
            else:
                best = min(options, key=lambda o: max(o[2].opt_min, o[2].mod_min))
                fewest = max(best[2].opt_min, best[2].mod_min)
                fewest_all.append(fewest)
                if n < fewest:
                    cause = _("{group}: {n} modules on one plane, a string needs at least {lo} even with {opt} "
                              "({source})").format(group=where, n=n, lo=fewest, opt=best[0].name,
                                                   source=best[2].source)
        else:
            lo, hi = stringing.series_range(g.module, spec, cond.t_min, cond.t_cell_max, cond.t_cell_cold)
            if not lo:
                cause = _("no series length of {module} fits the MPPT window {vmin} to {vmax} V within {vdc} V "
                          "(cell from {cold} to {hot} °C, lowest {tmin} °C)").format(
                    module=g.module.model or where, vmin=number(spec.vmppt_min or 0, 0),
                    vmax=number(spec.vmppt_max or 0, 0), vdc=number(stringing.voltage_limit(g.module, spec), 0),
                    cold=number(cond.t_cell_cold, 0), hot=number(cond.t_cell_max, 0), tmin=number(cond.t_min, 0))
            elif n < lo:
                cause = _("{group}: {n} modules, a string needs {lo} to {hi} in series (MPPT from {vmin} V, module "
                          "Vmp {vmp} V at {hot} °C of cell)").format(
                    group=where, n=n, lo=lo, hi=hi, vmin=number(spec.vmppt_min or 0, 0),
                    vmp=number(stringing.vmp_at(g.module, cond.t_cell_max), 1), hot=number(cond.t_cell_max, 0))
            elif not any(stringing.strings_allowed(g.module, spec, k) for k in range(spec.mppt_count or 1)):
                limits = [(spec.current_limit(k, 1), spec._limit(spec.iscmax_per_mppt, k))
                          for k in range(spec.mppt_count or 1)]
                cause = _("{module}: no input takes even one string: the input current limits ({limits}) are below "
                          "the module's Imp {imp} A or Isc x 1.25 = {i} A").format(
                    module=g.module.model or where, i=number(1.25 * g.module.isc, 2), imp=number(g.module.imp, 2),
                    limits=", ".join(sorted({f"{number(a, 1) if a else '?'} / {number(b, 1) if b else '?'} A"
                                             for a, b in limits})))
            else:
                fewest_all.append(lo)
        if cause:
            causes.append(cause)
        else:
            served.add(i)
    return served, (causes[0] if causes else ""), min(fewest_all, default=0)


def _static_causes(project, groups: list, records: list[dict]) -> list[tuple[str, str]]:
    """(model, cause) for each model that cannot string some group whatever its quantity (_static)."""
    cond = plant.conditions(project)
    pooled = _pooled(groups)
    return [(str(rec.get("model") or ""), cause) for rec in records
            for _served, cause, _fewest in [_static(rec, pooled, cond)] if cause]


def _why(out: plant.Plant) -> str:
    """The first thing that keeps a built candidate from being a sizing result, in words."""
    for s in out.strings:
        if not plant.acceptable(s):
            return f"{_('string')} {s.label}: {s.why}"
    for checks in out.checks.values():
        for c in checks:
            if c.level == "fail" or (c.key == "imp_total" and c.level == "warn"):
                return f"{c.label}: {c.detail}"
    if out.corrections:
        return out.corrections[0]
    if out.left:
        return ngettext("{n} module in no string", "{n} modules in no string", len(out.left)).format(n=len(out.left))
    return "; ".join(out.notes)


def _names(entries: list[dict]) -> str:
    return " + ".join(f"{e['count']} x {e['record'].get('model', '')}" for e in entries)


def _no_choice(project, groups, records, tried: dict, undecided: list, base: str) -> str:
    found = _static_causes(project, groups, records)
    known = {model for model, _cause in found}
    found += [(names, why) for names, why in tried.items() if names.split(" x ", 1)[-1] not in known]
    by_cause: dict = {}
    for model, cause in found:                  # one line per cause, the models that share it together
        by_cause.setdefault(cause, []).append(model)
    lines = []
    for cause, models in by_cause.items():
        names = ", ".join(models[:4])
        if len(models) > 4:
            names += " " + ngettext("and {n} other", "and {n} others", len(models) - 4).format(n=len(models) - 4)
        lines.append(f"{names}: {cause}")
    text = base
    if undecided:
        text += " " + ngettext(
            "{n} combination could not be decided within {k} search steps: {which}.",
            "{n} combinations could not be decided within {k} search steps each: {which}.", len(undecided)).format(
            n=len(undecided), k=number(CANDIDATE_STATES, 0, grouping=True), which=", ".join(undecided[:MAX_CAUSES]))
    if lines:
        more = len(lines) - MAX_CAUSES
        text += "\n" + _("Why:") + "\n" + "\n".join(f"• {line}" for line in lines[:MAX_CAUSES])
        if more > 0:
            text += "\n" + ngettext("• and {n} more", "• and {n} more", more).format(n=more)
    others = alternatives(_maker(records)) if records else []
    if others:
        text += "\n" + _("Other names in the catalogue: {brands}.").format(brands="; ".join(others))
    return text


def choose(project, groups: list, records: list[dict], ratio: float, *, cancelled=None, search=None) -> Result:
    """Size the plant of `project` on its laid `groups`, using only `records` of the brand chosen.

    Every candidate is stringed by `plant.build` and checked at the project's temperatures. The first complete
    and valid proposal in the order of CRITERION wins. With no such candidate, no inverter choice is returned.
    """
    usable = [{"_sizing_pac": _power(rec), "_sizing_record": rec} for rec in records if not missing_fields(rec)]
    if not groups:
        return Result(reason=_("Lay the modules before sizing the inverters: their DC power is not known yet."))
    if not usable:
        return Result(reason=_unusable_reason(records) if records else
                      _("No inverter with a nominal AC power and a complete MPPT datasheet is available."))
    cond = plant.conditions(project)
    pooled = _pooled(groups)
    static = [_static(u["_sizing_record"], pooled, cond) for u in usable]
    if set().union(*(served for served, _cause, _fewest in static)) != set(range(len(pooled))):
        # some plane is served by no model, whatever the quantities: nothing to search
        return Result(reason=_no_choice(project, groups, records, {}, [], _(
            "No complete string proposal is possible with these inverters: some modules cannot be strung by any "
            "of them, whatever their quantity.")))
    usable = [u for u, (served, _cause, _fewest) in zip(usable, static, strict=True) if served]
    p_stc = sum(len(g.placed) * g.module.pmax for g in groups)
    target_ac = p_stc / max(0.1, float(ratio))
    min_units, max_units = _unit_bounds(project, groups, [r["_sizing_record"] for r in usable])
    fewest = [f for served, _cause, f in static if served]
    if fewest and all(f > 0 for f in fewest):
        # every inverter needs at least one string of at least its fewest modules
        max_units = min(max_units, sum(len(g.placed) for g in groups) // min(fewest))
    required = max((g.target[0] for g in groups), default=0)
    min_units, max_units = max(min_units, required), max(max_units, required)
    evaluated = 0
    budget = search if search is not None else stringing.SearchBudget(MAX_SEARCH_STATES, cancelled)
    stop = cancelled if cancelled is not None else budget.cancelled
    tried: dict = {}
    undecided: list = []

    def stopped(reason):
        return Result(reason=reason, search_complete=False, search_nodes=budget.nodes, evaluated=evaluated,
                      undecided=undecided)

    for units in range(min_units, max_units + 1):
        for models in range(1, min(units, len(usable)) + 1):
            if stop is not None and stop():
                return stopped(_("Inverter search cancelled; no choice has been applied."))
            category = []
            try:
                for candidate in itertools.islice(_combinations(usable, units, models, target_ac),
                                                   MAX_CANDIDATES - evaluated + 1):
                    budget.step()
                    category.append(candidate)
            except stringing.SearchStopped:
                return stopped(budget.reason)
            if len(category) > MAX_CANDIDATES - evaluated:
                return stopped(_("Inverter search incomplete: the limit of {n} combinations was reached. "
                                 "Narrow the catalogue selection and try again.").format(n=MAX_CANDIDATES))
            candidates = sorted(category,
                                key=lambda item: (item[0], item[1][0]["record"].get("source") != "curated",
                                                  [(e["record"].get("model", ""), e["count"]) for e in item[1]]))
            for _error, entries in candidates:
                if stop is not None and stop():
                    return stopped(_("Inverter search cancelled; no choice has been applied."))
                capacity = _dc_capacity(entries)
                if capacity is not None and capacity + 1e-6 < p_stc:
                    continue                    # opt_dc_max fails whatever the strings: no search spent on it
                evaluated += 1
                left = budget.limit - budget.nodes
                if left <= 0:
                    return stopped(_("String assignment incomplete: the search limit was reached."))
                share = stringing.SearchBudget(min(CANDIDATE_STATES, left), stop)
                out = plant.build(_candidate(project, entries), groups=groups, search=share)
                budget.nodes += share.nodes
                if not out.search_complete:
                    if stop is not None and stop():
                        return stopped(_("Inverter search cancelled; no choice has been applied."))
                    undecided.append(_names(entries))
                    continue
                if (out.left or not out.strings or not all(plant.acceptable(s) for s in out.strings)
                        or any(c.level == "fail" or (c.key == "imp_total" and c.level == "warn")
                               for checks in out.checks.values() for c in checks)):
                    if len(tried) < MAX_CAUSES * 4:
                        tried.setdefault(_names(entries), _why(out))
                    continue
                ac = sum(_power(e["record"]) * e["count"] for e in entries)
                notes = plant.conditions_of(out.strings)
                if undecided:
                    notes.append(ngettext(
                        "{n} combination ranked before this one could not be decided within the search limit: {which}",
                        "{n} combinations ranked before this one could not be decided within the search limit: "
                        "{which}", len(undecided)).format(n=len(undecided), which=", ".join(undecided[:MAX_CAUSES])))
                return Result(entries=out.entries or entries, runs=plant.runs_of(out), plant=out, ratio=p_stc / ac,
                              ok=True, search_nodes=budget.nodes, evaluated=evaluated, notes=notes,
                              undecided=undecided)
    base = (_("No valid combination was found among those decided, and not every combination could be decided: "
              "this is not a proof that none exists.") if undecided else
            _("No complete string proposal was found within the voltage, current and input limits. "
              "The search exhausted the supplied catalogue and the selected geometry constraints."))
    return Result(reason=_no_choice(project, groups, records, tried, undecided, base), search_nodes=budget.nodes,
                  evaluated=evaluated, search_complete=not undecided, undecided=undecided)
