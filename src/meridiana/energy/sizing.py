"""Automatic inverter sizing, accepted only together with a complete and valid string proposal.

The choice looks at the DC/AC ratio first (R420): a combination whose ratio is within a band around the one asked
(`band`) comes before any other, and only among those the fewer inverters, the fewer different models and the ratio
closest to the one asked. Outside the band: a ratio below the band but not under 1, then one above it, and last a
ratio under 1 (an oversized inverter), which is said in the result. The band is a proposal of 05/11/2026, for Daniel to
confirm (docs/studio/34-catalogo-marche-fonti.md, section on the sizing). Up to `MAX_ALTERNATIVES` other valid
combinations come with the choice, so that the designer can take another one. Catalogue source and model name only
break exact ties. A combination that leaves modules out or violates an input's voltage or current limits is not a
sizing result.

Each combination's strings are searched within its own share of the search (CANDIDATE_STATES): one combination
whose strings cannot be decided in it does not use up the search of the others; it is said, never taken for
impossible. When no combination is valid, the reason names the limit that stops each model (series length against
the MPPT window, input current, SolarEdge's optimizer rules, maximum DC power) or the datasheet fields the
catalogue lacks, and the brands of the catalogue that could size the plant instead (R267).
"""

from __future__ import annotations

import copy
import dataclasses
import itertools
import math
import time
from dataclasses import dataclass, field

from ..i18n import _, ngettext, number
from . import faces, optimizers, plant, stringing
from .components import InverterSpec


CRITERION = _("the DC/AC ratio within the band first, then fewer inverters, then fewer models, then the closest ratio")
BAND_BELOW, BAND_ABOVE, BAND_FLOOR = 0.15, 0.20, 0.95  # around the ratio asked, measured on real rows: docs/studio/34
MAX_ALTERNATIVES = 3
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
    wanted: float = 0.0                             # the DC/AC ratio asked
    standing: int = 0                               # where the ratio stands: IN_BAND, BELOW_BAND, ABOVE_BAND, UNDER_ONE
    why: str = ""                                   # why this combination, in words for the window
    alternatives: list = field(default_factory=list)  # other valid combinations (Results), best first
    # R522, only the modules in no string (choose_free): "inputs" (the free inputs of the inverters there are) or "new"
    # (inverters added for them); the inverters added, the strings added (the designer's are not in it), how many
    # modules were free
    mode: str = ""
    added: list = field(default_factory=list)
    new_runs: list = field(default_factory=list)
    free: int = 0
    left: int = 0           # R522: modules a partial proposal leaves in no string (choose(partial=True)), said
    first: list = field(default_factory=list)   # R522: the strings of `new_runs` on free inputs of the inverters there are
    faces_why: dict = field(default_factory=dict)   # R522 r24: sub-field -> why its small face went on over no other

    @property
    def ac_w(self) -> float:
        return sum(_power(e["record"]) * e["count"] for e in self.entries)

    @property
    def dc_max_w(self) -> float | None:
        """The most DC power the datasheets allow these inverters, when every one prints it."""
        values = [float(e["record"].get("dc_power_max_w") or 0) * e["count"] for e in self.entries]
        return sum(values) if values and all(values) else None

    @property
    def units(self) -> int:
        return sum(e["count"] for e in self.entries)

    @property
    def unit_ratios(self) -> list:
        """The DC/AC ratio of each inverter, in its order (R428)."""
        return list(plant.unit_ratios(self.plant).values()) if self.plant is not None else []

    @property
    def ratio_spread(self) -> float:
        ratios = self.unit_ratios
        return max(ratios) - min(ratios) if ratios else 0.0


IN_BAND, BELOW_BAND, ABOVE_BAND, UNDER_ONE = 0, 1, 2, 3


def band(wanted: float) -> tuple[float, float]:
    """The DC/AC ratios taken as what was asked: from `BAND_BELOW` under it, not under `BAND_FLOOR` (a 20 kW inverter on
    19.95 kWp is not oversized) unless the designer asked for less than that, to `BAND_ABOVE` above it."""
    low = wanted - BAND_BELOW
    return (max(BAND_FLOOR, low) if wanted >= BAND_FLOOR else low), wanted + BAND_ABOVE


def standing(actual: float, wanted: float) -> int:
    """Where a DC/AC ratio stands against the one asked; a lower number is a better one."""
    low, high = band(wanted)
    if low - 1e-9 <= actual <= high + 1e-9:
        return IN_BAND
    if actual > high:
        return ABOVE_BAND
    return BELOW_BAND if actual >= 1.0 else UNDER_ONE


def alternative_row(result: "Result") -> dict:
    """One combination as the window lists it: the fields of a line, in numbers and words."""
    return {"names": _names(result.entries), "ratio": result.ratio, "units": result.units, "ac_w": result.ac_w,
            "dc_max_w": result.dc_max_w, "standing": result.standing, "why": result.why, "unit_ratios": result.unit_ratios}


def free_line(result: "Result") -> str:
    """One proposal for the modules in no string as the window lists it (R522 r22-impianto): what it adds, the ratio of
    each inverter it touches and of the whole plant, the modules it leaves."""
    ratios = plant.unit_ratios(result.plant) if result.plant is not None else {}
    mine = sorted({int(r.get("inverter") or 0) for r in result.new_runs})
    text = _("{added} · by inverter {ratios} · whole plant {ratio}").format(
        added=_names(result.added) if result.added else _("only the free inputs of the inverters there are"),
        ratios=" · ".join(f"{k}: {number(ratios.get(k, 0.0), 2)}" for k in mine), ratio=number(result.ratio, 2))
    if result.left:
        text += " · " + ngettext("{m} module in no string", "{m} modules in no string", result.left).format(m=result.left)
    return text


def explain(result: "Result") -> str:
    """Why a combination was chosen, in words: what the ratio is against the band, and what it costs when outside."""
    low, high = band(result.wanted)
    text = _("{names}: DC/AC ratio {ratio}, asked {wanted}, band {low}-{high}.").format(
        names=_names(result.entries), ratio=number(result.ratio, 2), wanted=number(result.wanted, 2),
        low=number(low, 2), high=number(high, 2))
    if len(result.unit_ratios) > 1:
        text += " " + _("By inverter: {ratios}.").format(ratios=" · ".join(number(r, 2) for r in result.unit_ratios))
    if result.standing == IN_BAND:
        return text + " " + _("Within the band: the fewest inverters that stay in it.")
    if result.standing == BELOW_BAND:
        return text + " " + _("Below the band: no valid combination inside it was found.")
    if result.standing == ABOVE_BAND:
        return text + " " + _("Above the band: the inverter clips more than asked, and no valid combination inside it "
                              "was found.")
    return text + " " + _("Under 1: the inverter is oversized for this field. It was taken because no other valid "
                          "combination was found.")


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
    """Each combination of `units` inverters of `models` models. Not offered: single-phase and three-phase inverters
    together, or more than one single-phase inverter, which no designer would propose for one connection."""
    for indices in itertools.combinations(range(len(records)), models):
        phases = {records[i]["_sizing_record"].get("phases") for i in indices}
        if 1 in phases and (len(phases) > 1 or units > 1):
            continue
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


def time_up(budget) -> str:
    """The words of a search ended by its time limit or by «Stop» (R522)."""
    if budget.enough is not None and budget.enough():
        return _("Search stopped: the best proposal found until then is given.")
    return _("Search stopped at its time limit: the best proposal found until then is given.")


def choose(project, groups: list, records: list[dict], ratio: float, *, cancelled=None, search=None,
           partial: bool = False) -> Result:
    """Size the plant of `project` on its laid `groups`, using only `records` of the brand chosen.

    Every candidate is stringed by `plant.build` and checked at the project's temperatures. The first complete
    and valid proposal in the order of CRITERION wins. With no such candidate, no inverter choice is returned; with
    `partial` (R522, the modules in no string) the candidate whose strings are all valid and that leaves the fewest
    modules in no string is returned instead, `left` says how many.
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
    reached = set().union(*(served for served, _cause, _fewest in static))
    if partial and reached and reached != set(range(len(pooled))):
        # R522 partial: the planes no model can string stay in no string, the others are sized (said by `left`)
        keep = {id(g) for i in reached for g in pooled[i]}
        out_of_reach = sum(len(g.placed) for g in groups if id(g) not in keep)
        result = choose(project, [g for g in groups if id(g) in keep], records, ratio, cancelled=cancelled,
                        search=search, partial=True)
        for r in [result, *result.alternatives]:
            if r.ok:
                r.left += out_of_reach
        return result
    if reached != set(range(len(pooled))):
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
        if near and not (stop is not None and stop()):   # R522 partial: the best of those that leave modules out
            best = min(near, key=lambda item: item[0])[1]
            best.notes.append(reason)
            best.search_nodes, best.evaluated, best.search_complete = budget.nodes, evaluated, True
            return best
        return Result(reason=reason, search_complete=False, search_nodes=budget.nodes, evaluated=evaluated,
                      undecided=undecided)

    wanted = max(0.1, float(ratio))
    low, _high = band(wanted)
    smallest = min(u["_sizing_pac"] for u in usable)
    found: list = []                    # the valid combinations, in the order they were reached
    near: list = []                     # R522 partial: (rank, Result) of the valid ones that leave modules out
    total = sum(len(g.placed) for g in groups)

    def judge(entries):
        """The whole check of one combination: a Result when it is valid, None when not; SearchStopped-free."""
        nonlocal evaluated
        capacity = _dc_capacity(entries)
        if capacity is not None and capacity + 1e-6 < p_stc:
            return None                 # opt_dc_max fails whatever the strings: no search spent on it
        evaluated += 1
        left = budget.limit - budget.nodes
        if left <= 0:
            return None
        share = budget.part(min(CANDIDATE_STATES, left))
        share.cancelled = stop
        out = plant.build(_candidate(project, entries), groups=groups, search=share)
        budget.nodes += share.nodes
        if not out.search_complete:
            if not (stop is not None and stop()) and not budget.expired():
                undecided.append(_names(entries))
            return None
        if (out.left or not out.strings or not all(plant.acceptable(s) for s in out.strings)
                or any(c.level == "fail" or (c.key == "imp_total" and c.level == "warn")
                       for checks in out.checks.values() for c in checks)):
            if len(tried) < MAX_CAUSES * 4:
                tried.setdefault(_names(entries), _why(out))
            if (partial and out.left and out.strings and len(out.left) < total
                    and all(plant.acceptable(s) for s in out.strings)
                    and not any(_bad(c) for checks in out.checks.values() for c in checks)):
                ac = sum(_power(e["record"]) * e["count"] for e in entries)
                strung = p_stc * (1 - len(out.left) / max(1, total))
                ratio_strung = strung / ac
                kept = Result(entries=out.entries or entries, runs=plant.runs_of(out), plant=out, ratio=ratio_strung,
                              ok=True, notes=plant.conditions_of(out.strings), wanted=wanted,
                              standing=standing(ratio_strung, wanted), left=len(out.left))
                kept.why = explain(kept)
                near.append(((kept.standing, len(out.left), kept.units, abs(ratio_strung / wanted - 1)), kept))
            return None
        ac = sum(_power(e["record"]) * e["count"] for e in entries)
        notes = plant.conditions_of(out.strings)
        if undecided:
            notes.append(ngettext(
                "{n} combination ranked before this one could not be decided within the search limit: {which}",
                "{n} combinations ranked before this one could not be decided within the search limit: "
                "{which}", len(undecided)).format(n=len(undecided), which=", ".join(undecided[:MAX_CAUSES])))
        result = Result(entries=out.entries or entries, runs=plant.runs_of(out), plant=out, ratio=p_stc / ac, ok=True,
                        notes=notes, undecided=list(undecided), wanted=wanted, standing=standing(p_stc / ac, wanted))
        result.why = explain(result)
        return result

    def finished(cut_short: str = "") -> Result:
        """The best of what was found, the others as its alternatives."""
        ranked = sorted(found, key=lambda r: (r.standing, r.units, len(r.entries), round(r.ratio_spread, 2), abs(r.ratio / wanted - 1),
                                              r.entries[0]["record"].get("source") != "curated",
                                              [(e["record"].get("model", ""), e["count"]) for e in r.entries]))
        best = ranked[0]
        best.alternatives = ranked[1:1 + MAX_ALTERNATIVES]
        best.search_nodes, best.evaluated, best.undecided = budget.nodes, evaluated, undecided
        if best.standing == UNDER_ONE:
            best.notes.append(_("The inverter is oversized: DC/AC ratio {ratio}, under 1.").format(
                ratio=number(best.ratio, 2)))
        if cut_short:
            best.notes.append(cut_short)
        return best

    settled_at = 0                      # the number of inverters of the first valid combination in the band
    for units in range(min_units, max_units + 1):
        if settled_at and units > settled_at + 1:
            break                       # one step beyond is enough for an alternative: more inverters are never better
        if found and units * smallest * low > p_stc * 1.0001 and not settled_at:
            break                       # every ratio from here on is below the band, and a valid combination is at hand
        for models in range(1, min(units, len(usable)) + 1):
            if settled_at and models > 1 and units == settled_at + 1:
                break
            if stop is not None and stop():
                return stopped(_("Inverter search cancelled; no choice has been applied."))
            category = []
            try:
                for candidate in itertools.islice(_combinations(usable, units, models, target_ac),
                                                   MAX_CANDIDATES - evaluated + 1):
                    budget.step()
                    category.append(candidate)
            except stringing.SearchStopped:
                reason = time_up(budget) if budget.expired() else budget.reason
                return finished(reason) if found else stopped(reason)
            if len(category) > MAX_CANDIDATES - evaluated:
                limit = _("Inverter search incomplete: the limit of {n} combinations was reached. "
                          "Narrow the catalogue selection and try again.").format(n=MAX_CANDIDATES)
                return finished(limit) if found else stopped(limit)

            def order(item):
                ac = sum(_power(e["record"]) * e["count"] for e in item[1])
                return (standing(p_stc / ac, wanted), item[0], item[1][0]["record"].get("source") != "curated",
                        [(e["record"].get("model", ""), e["count"]) for e in item[1]])
            taken: set = set()          # outside the band only the nearest valid one of each standing is worth a search
            for candidate in sorted(category, key=order):
                entries = candidate[1]
                place = order(candidate)[0]
                if stop is not None and stop():
                    return stopped(_("Inverter search cancelled; no choice has been applied."))
                if place in taken or (settled_at and place != IN_BAND):
                    continue
                if budget.limit - budget.nodes <= 0:
                    limit = _("String assignment incomplete: the search limit was reached.")
                    return finished(limit) if found else stopped(limit)
                if budget.expired():
                    return finished(time_up(budget)) if found else stopped(time_up(budget))
                result = judge(entries)
                if stop is not None and stop():
                    return stopped(_("Inverter search cancelled; no choice has been applied."))
                if result is None:
                    continue
                found.append(result)
                taken.add(place)
                if place == IN_BAND and not settled_at:
                    settled_at = units
            if settled_at == units and IN_BAND in taken:
                break
    if found:
        return finished()
    if near:
        return stopped(_("No combination strings every module."))
    base = (_("No valid combination was found among those decided, and not every combination could be decided: "
              "this is not a proof that none exists.") if undecided else
            _("No complete string proposal was found within the voltage, current and input limits. "
              "The search exhausted the supplied catalogue and the selected geometry constraints."))
    return Result(reason=_no_choice(project, groups, records, tried, undecided, base), search_nodes=budget.nodes,
                  evaluated=evaluated, search_complete=not undecided, undecided=undecided)


# R522: only the modules in no string (Daniel 07/11/2026)

FREE_INPUTS, FREE_NEW, FREE_BOTH = "inputs", "new", "both"
FREE_STATES = 100000    # string-search steps for the free inputs of the inverters there are (the window's «Complete»)
# R522, Daniel 07/11/2026 «un limite di tempo ragionevole»: the proposal for the modules in no string ends within this
# many seconds with the best one found (Rho, 196 modules in no string: 11 minutes and no proposal without it)
FREE_SECONDS = 25.0


def free_keys(project, groups: list, runs: list | None = None) -> list[str]:
    """The modules laid ("sub-field/key") in none of the strings `runs` (the designer's when None), in layout order."""
    if runs is None:
        runs = ((project.energy or {}).get("strings") or {}).get("runs") or []
    taken = {k for r in runs if r.__class__ is dict for k in r.get("modules") or []}
    return [f"{g.sfid}/{pm.key}" for g in groups for pm in g.placed if f"{g.sfid}/{pm.key}" not in taken]


def _bad(c) -> bool:
    return c.level == "fail" or (c.key == "imp_total" and c.level == "warn")


def _failing_units(out: plant.Plant) -> set:
    """What keeps a plant from being a valid proposal (the rule of «Propose»): the inputs (inverter, input) of its
    strings that fail and the checks (inverter, key, label) that fail."""
    return ({("input", s.inverter, s.mppt) for s in out.strings if not plant.acceptable(s)}
            | {("check", u, c.key, c.label) for u, checks in out.checks.items() for c in checks if _bad(c)})


def _failure(out: plant.Plant, kept: int = 0, before: set = frozenset()) -> str:
    """Why a plant is not a complete and valid proposal, by the rule the window applies to «Propose»; "" when it is.
    What fails already with the designer's strings alone (`before`, _failing_units) is not held against it: a string of
    his that fails, as long as no new string goes on its input; a check that failed before, the same check of the same
    inverter. The first `kept` strings are the designer's (String.run), the others are new."""
    if not out.search_complete:
        return out.search_reason or _("String assignment incomplete: the search limit was reached.")
    fresh = {(s.inverter, s.mppt) for s in out.strings if s.run < 0 or s.run >= kept}
    def spared(s):
        return 0 <= s.run < kept and ("input", s.inverter, s.mppt) in before and (s.inverter, s.mppt) not in fresh
    if out.left:                    # the cause said first: _why would name a string of his that is spared
        return ngettext("{n} module in no string", "{n} modules in no string", len(out.left)).format(n=len(out.left))
    if (not out.strings
            or not all(plant.acceptable(s) or spared(s) for s in out.strings)
            or any(_bad(c) and ("check", u, c.key, c.label) not in before
                   for u, checks in out.checks.items() for c in checks)):
        return _why(out) or _("No complete string proposal was found within the voltage, current and input limits.")
    return ""


def _with(project, entries: list, runs: list):
    """`project` with these inverters and these strings of the designer (no live proposal)."""
    candidate = copy.copy(project)
    strings = {k: v for k, v in dict((project.energy or {}).get("strings") or {}).items() if k != "auto"}
    strings["runs"] = [dict(r) for r in runs]
    candidate.energy = {**(project.energy or {}), "inverters": entries, "strings": strings}
    return candidate


def _run_of(s: plant.String) -> dict:
    """One string as the file keeps it (plant.runs_of for one)."""
    return {"inverter": s.inverter, "mppt": s.mppt, "modules": s.keys,
            **({"optimizer_group_sizes": list(s.optimizer_group_sizes)} if s.optimizer_group_sizes else {})}


def _free_why(res: Result, head: str, kept: int) -> str:
    """The words of a choice for the modules in no string: what was done and why, the ratio of the whole plant and of
    each inverter against the band."""
    low, high = band(res.wanted)
    ratios = plant.unit_ratios(res.plant) if res.plant is not None else {}
    tail = ngettext("The {k} string there is stays as it is.", "The {k} strings there are stay as they are.",
                    kept).format(k=kept) if kept else ""
    tail += (" " if tail else "") + _("DC/AC ratio of the whole plant {ratio}, asked {wanted}, band {low}-{high}; by "
                                      "inverter: {ratios}.").format(
        ratio=number(res.ratio, 2), wanted=number(res.wanted, 2), low=number(low, 2), high=number(high, 2),
        ratios=" · ".join(f"{n}: {number(r, 2)}" for n, r in ratios.items()))
    return head + " " + tail


# R522 r22-impianto (Daniel 07/11/2026): the proposal for the modules in no string as a designer makes it. The free
# inputs of the inverters there are take modules up to a ratio (the one asked, the top and the foot of the band), whole
# rows of them; for what is left, the inverters of the right size (the remaining kWp over the ratio asked), a few sizes
# nearest to it, each tried with its strings: no blind combinatorics. Each try is one string search, within the time.
FREE_TRIES = 3          # inverter combinations of the right size tried for each share the inverters there are take
FREE_UNITS = 3          # at most this many inverters added at once
FREE_ENOUGH = MAX_ALTERNATIVES + 2   # valid proposals after which a perfect one (all strung, all in the band) ends it


def dump_key(res: Result) -> tuple:
    """What a proposal for the modules in no string adds, to list the same one once."""
    return (tuple((e["record"].get("model", ""), e["count"]) for e in res.added),
            tuple(sorted((int(r.get("inverter") or 0), int(r.get("mppt") or 0), tuple(r.get("modules") or []))
                         for r in res.new_runs)))


def _free_combos(usable: list, p_w: float, wanted: float) -> list:
    """Inverters of the right size for `p_w` of modules: the combinations of up to FREE_UNITS inverters of one or two
    models, those in the band first, nearest to the ratio asked; FREE_TRIES of them (the nearest outside when none
    is in it)."""
    out = []
    for units in range(1, FREE_UNITS + 1):
        for models in range(1, min(units, 2, len(usable)) + 1):
            for _d, entries in _combinations(usable, units, models, p_w / wanted):
                ac = sum(_power(e["record"]) * e["count"] for e in entries)
                capacity = _dc_capacity(entries)
                if not ac or capacity is not None and capacity + 1e-6 < p_w:
                    continue
                r = p_w / ac
                out.append(((standing(r, wanted), units, models, round(abs(r / wanted - 1), 4),
                             entries[0]["record"].get("source") != "curated",
                             [(e["record"].get("model", ""), e["count"]) for e in entries]), entries))
    out.sort(key=lambda item: item[0])
    inside = [item for item in out if item[0][0] == IN_BAND]
    return (inside or out)[:FREE_TRIES]


def _free_lengths(res: Result, groups: list, project) -> str:
    """R522 r24 (Daniel 08/11/2026): the length of the new strings is the one that gives most within the inverter's
    rules, not the one of the strings there are: said with the range each inverter allows."""
    if res.plant is None or project is None or not res.new_runs:
        return ""
    cond = plant.conditions(project)
    module_of = {f"{g.sfid}/{pm.key}": g.module for g in groups for pm in g.placed}
    kept = res.runs[:len(res.runs) - len(res.new_runs)]
    parts, theirs = [], set()
    for k in sorted({int(r.get("inverter") or 0) for r in res.new_runs}):
        u = res.plant.unit(k)
        news = [r for r in res.new_runs if int(r.get("inverter") or 0) == k and r.get("modules")]
        if u is None or u.fixed is not None or u.mlpe is not None or not news:
            continue
        module = module_of.get(news[0]["modules"][0])
        lo, hi = plant._series_range(module, u, cond) if module is not None else (0, 0)
        lengths = sorted({len(r["modules"]) for r in news})
        parts.append(_("inverter {k}: {lengths} modules (it takes {lo}-{hi})").format(
            k=k, lengths=", ".join(str(n) for n in lengths), lo=lo, hi=hi))
        theirs |= {len(r.get("modules") or []) for r in kept if int(r.get("inverter") or 0) == k}
    if not parts:
        return ""
    theirs = theirs or {len(r.get("modules") or []) for r in kept}
    text = _("Length of the new strings: {parts}; the length that brings each input nearest to the power asked and, "
             "at a tie, the longest (higher voltage, less current), within the inverter's MPPT window and maximum "
             "voltage in the cold").format(parts=" · ".join(parts))
    if theirs:
        text += _(", not that of the strings there are ({lengths})").format(
            lengths=", ".join(str(n) for n in sorted(theirs)))
    return text + "."


def _free_tell(res: Result, low: float, high: float, offset: int, groups: list, project=None) -> None:
    """What the window says besides the choice (R522 r22-impianto): the inverters outside the band, the new ones and
    those of the designer it does not touch, and where the modules left in no string are; r24: the length of the new
    strings and why, a string that goes on over the face next to it, a small face left and why."""
    ratios = plant.unit_ratios(res.plant) if res.plant is not None else {}
    mine = {int(r.get("inverter") or 0) for r in res.new_runs}
    lengths = _free_lengths(res, groups, project)
    if lengths:
        res.why += " " + lengths
    if res.plant is not None:
        kept = len(res.runs) - len(res.new_runs)
        for c in res.plant.crossings:
            x = res.plant.strings[c.index] if 0 <= c.index < len(res.plant.strings) else None
            if x is None or not 0 <= x.run - kept or len(c.faces) < 2:
                continue
            res.why += " " + _("String {label} runs over {first} and {then}: a face too small for a string of "
                               "whole rows goes on over the one next to it (R433; the check says what its exposures "
                               "cost).").format(
                label=c.label, first=", ".join(f.name for f in c.faces[:-1]), then=c.faces[-1].name)

    def listed(items):
        return " · ".join(f"{k}: {number(r, 2)}" for k, r in items)
    off = [(k, r) for k, r in sorted(ratios.items()) if k in mine and not low - 1e-9 <= r <= high + 1e-9]
    if off:
        res.why += " " + _("Outside the band {low}-{high}: inverter {which}; no combination of this brand tried "
                           "keeps them inside it.").format(low=number(low, 2), high=number(high, 2), which=listed(off))
    theirs = [(k, r) for k, r in sorted(ratios.items()) if k <= offset and k not in mine
              and not low - 1e-9 <= r <= high + 1e-9]
    if theirs:
        res.why += " " + _("The inverters there are outside the band ({which}) keep their strings as they were: the "
                           "ratio of the whole plant counts them.").format(which=listed(theirs))
    if res.left and res.plant is not None:
        names = {g.sfid: g.name or g.sfid for g in groups}
        where: dict = {}
        for k in res.plant.left:
            where[k[0]] = where.get(k[0], 0) + 1
        for sfid in [s for s in where if s in res.faces_why]:
            m = where.pop(sfid)
            res.why += " " + ngettext(
                "Left in no string: the {m} module of {where}; its face makes no string of whole rows and {why}.",
                "Left in no string: the {m} modules of {where}; their face makes no string of whole rows and {why}.",
                m).format(m=m, where=names.get(sfid, sfid), why=res.faces_why[sfid])
        if not where:
            return
        res.why += " " + ngettext(
            "Left in no string: {where}; that module does not make up one more string of a length the free inputs "
            "take within their voltage and current limits.",
            "Left in no string: {where}; those {m} modules do not make up one more string of a length the free "
            "inputs take within their voltage and current limits.", sum(where.values())).format(
            m=sum(where.values()), where=", ".join(f"{names.get(s, s)}: {c}" for s, c in where.items()))


def _slots(u, runs: list, module) -> list:
    """The inputs of unit `u` with no string of the designer, each with how many strings it takes: (mppt, strings)."""
    used = {int(r.get("mppt") or 0) for r in runs if int(r.get("inverter") or 0) == u.number}
    return [(m + 1, max(1, stringing.strings_allowed(module, u.spec, m))) for m in range(u.inputs) if m + 1 not in used]


JOIN_LOSS = 0.01        # R522 r24: without optimizers a string goes on over the next face up to this estimated loss


class _Joiner:
    """R522 r24-scelte (Daniel 08/11/2026): a face too small for a string of whole rows does not go along a path of its
    own on an input of its own: its string goes on over the face next to it, by the rules of R433 (faces.py): on the
    same face, or another face of the same building; without optimizers (the only inverters `_lay` draws for) when the
    exposures are compatible, the loss faces.py estimates within JOIN_LOSS, or when the designer asked for strings over
    the faces (energy["strings"]["across_faces"]); between buildings never (by hand only). Otherwise its modules stay in
    no string and `why` says why, by sub-field."""

    def __init__(self, project, groups: list, strategy: str, free: set = frozenset()):
        self.project = project
        # each face's modules in no string when the search starts: what decides whether it is a small face
        self.initial = {g.key or g.sfid: [pm for pm in g.placed if f"{g.sfid}/{pm.key}" in free] for g in groups}
        self._small: dict = {}
        self.group_of = {g.key or g.sfid: g for g in groups}
        self.strategy = strategy
        self.face_of = faces.faces_of(project)
        self.plain_too = bool(((project.energy or {}).get("strings") or {}).get(plant.ACROSS))
        self.orientations = {(g.sfid, pm.key): plant._orientation(pm) for g in groups for pm in g.placed}
        self.why: dict = {}

    def small(self, name, g, u, cond) -> bool:
        """A face too small for a string of whole rows on unit `u`: its free modules are no more than one string and
        no length the unit takes strings all of them along the strategy (rows: every row whole)."""
        key = (name, u.number, u.spec.model if hasattr(u.spec, "model") else id(u.spec))
        if key not in self._small:
            placed = self.initial.get(name) or []
            lo, hi = plant._series_range(g.module, u, cond)
            self._small[key] = bool(hi and placed and len(placed) <= hi and not any(
                not plant.order(placed, n, self.strategy)[1]
                for n in range(lo, len(placed) + 1) if plant._length_allowed(u, n)))
        return self._small[key]

    def _partners(self, name, g, near) -> list:
        """The groups `near` ({name: (group, modules)}: free or strung on this unit) a string of `g` may go on over,
        the same face first, then the nearest."""
        mine = self.face_of.get(g.sfid)
        here = [tuple(pm.centre[:2]) for pm in near[name][1]]
        found, foreign = [], []
        for k, (og, placed) in near.items():
            if k == name or not placed or plant._module_key(og.module) != plant._module_key(g.module):
                continue
            d = min(math.dist(a, tuple(pm.centre[:2])) for a in here for pm in placed)
            f = self.face_of.get(og.sfid)
            if mine is not None and f is not None and (faces.same_face(mine, f)
                                                       or mine.building and f.building == mine.building):
                found.append((not faces.same_face(mine, f), d, k))
            else:
                foreign.append((d, k, f))
        if not found and not foreign:
            # its neighbours may be strung already on another inverter: the faces with free modules at the start
            for k, placed in self.initial.items():
                og = self.group_of.get(k)
                f = self.face_of.get(og.sfid) if og is not None else None
                if k == name or not placed or og is None or (mine is not None and f is not None and mine.building
                                                             and f.building == mine.building):
                    continue
                foreign.append((min(math.dist(a, tuple(pm.centre[:2])) for a in here for pm in placed), k, f))
        if not found:
            if foreign:
                f = min(foreign, key=lambda x: x[:2])[2]
                self.why[g.sfid] = _("the nearest face with free modules ({face}) is on another building or field: a "
                                     "string goes on over two buildings only by hand (R433)").format(
                                         face=f.name if f is not None else "?")
            else:
                self.why[g.sfid] = _("no other face of the same building has free modules to go on over")
        return [k for *_k, k in sorted(found)]

    def _allowed(self, string) -> str:
        """'' when a string over these modules is allowed, else why not."""
        refs = [(gg.sfid, pm.key, tuple(pm.centre)) for gg, pm in string]
        try:
            c = faces.crossing(self.project, 0, "", refs, self.orientations, self.face_of, lambda sf, k: False)
        except (AttributeError, TypeError, ValueError):
            c = None
        if c is None or len(c.exposures) < 2 or self.plain_too or c.loss <= JOIN_LOSS + 1e-12:
            return ""
        return _("without optimizers a string goes on over another face only with compatible exposures: the loss "
                 "estimated for theirs is {loss} %, above {most} % (R433)").format(
                     loss=number(100 * c.loss, 1), most=number(100 * JOIN_LOSS, 0))

    @staticmethod
    def _towards(own, other):
        """`own` turned so that it ends where `other` is nearest, `other` so that it starts there."""
        near = min(other, key=lambda pm: math.dist(pm.centre[:2], own[-1].centre[:2]))
        if math.dist(own[0].centre[:2], near.centre[:2]) < math.dist(own[-1].centre[:2], near.centre[:2]):
            own = own[::-1]
        if math.dist(other[-1].centre[:2], own[-1].centre[:2]) < math.dist(other[0].centre[:2], own[-1].centre[:2]):
            other = other[::-1]
        return own, other

    def join(self, name, pools, u, cond, lengths, laid) -> tuple:
        """One string of the modules of group `name` going on over the face next to it: (string as [(group, module)],
        the place in the runs of the string it lengthens or None), or ([], None) and `why` says it. First over the
        partner's free modules (the length of its strings on this unit first, else the longest allowed); else the
        partner's string nearest to it on this unit goes on over this face, when the sum is a length allowed.
        `laid` {group name: [(run index, modules, group)]} the strings drawn on this unit."""
        g, placed = pools[name]
        lo, hi = plant._series_range(g.module, u, cond)
        own = plant._path(placed, self.strategy)
        if not hi or len(own) >= hi:
            return [], None
        near = {k: (og, list(op)) for k, (og, op) in pools.items()}
        for k, rows in laid.items():
            og = rows[0][2]
            near[k] = (og, near.get(k, (og, []))[1] + [pm for _i, row, _g in rows for pm in row])
        for other in self._partners(name, g, near):
            og = near[other][0]
            free = list(pools[other][1]) if other in pools else []
            if free:
                mine, path = self._towards(own, plant._path(free, self.strategy))
                total = len(mine) + len(path)
                options = [lengths.get(other)] + list(range(min(hi, total), lo - 1, -1))
                for length in dict.fromkeys(x for x in options if x):
                    if not (lo <= length <= hi and len(mine) < length <= total and plant._length_allowed(u, length)):
                        continue
                    string = [(g, pm) for pm in mine] + [(og, pm) for pm in path[:length - len(mine)]]
                    refused = self._allowed(string)
                    if not refused:
                        self.why.pop(g.sfid, None)
                        return string, None
                    self.why[g.sfid] = refused
                    break
            for index, row, rg in sorted(laid.get(other, []), key=lambda x: min(
                    math.dist(a.centre[:2], b.centre[:2]) for a in own for b in x[1])):
                length = len(own) + len(row)
                if not (lo <= length <= hi and plant._length_allowed(u, length)):
                    continue
                mine, path = self._towards(own, list(row))
                string = [(rg, pm) for pm in path[::-1]] + [(g, pm) for pm in mine[::-1]]
                refused = self._allowed(string)
                if not refused:
                    self.why.pop(g.sfid, None)
                    return string, index
                self.why[g.sfid] = refused
                break
            self.why.setdefault(g.sfid, _("with the modules of the face next to it no string reaches a length the "
                                          "inverter takes"))
        return [], None


def _take(pools: dict, string: list) -> None:
    """Take the modules of `string` [(group, module)] out of `pools`."""
    gone = {id(pm) for _g, pm in string}
    for name in list(pools):
        g, placed = pools[name]
        rest = [pm for pm in placed if id(pm) not in gone]
        if len(rest) != len(placed):
            if rest:
                pools[name] = (g, rest)
            else:
                pools.pop(name)


def _lay(plan: list, pools: dict, cond, strategy: str, joiner: _Joiner | None = None) -> list:
    """Strings as a designer draws them on the free inputs of `plan` [(unit, DC power wanted on it, slots)]: on each
    unit the groups from the smallest, each in strings of one length along the strategy's path, as many as come nearest
    to the power wanted; one group and one length per input. A face too small for a string of whole rows: with a
    `joiner` (R522 r24) its string goes on over the face next to it when R433 allows it, on an input of its own (its
    exposures are not those of the strings beside it), else it stays in no string; without one (as before 08/11) along
    a path of its own. `pools` ({group: (group, modules)}) loses the modules taken."""
    runs = []
    for u, want_w, slots in plan:
        slots = [list(x) for x in slots]
        small, lengths, laid = [], {}, {}
        for name in sorted(pools, key=lambda k: (len(pools[k][1]), k)):
            if not slots or want_w <= 0:
                break
            if name not in pools:
                continue
            g, placed = pools[name]
            lo, hi = plant._series_range(g.module, u, cond)
            count = len(placed)
            tiny = joiner is not None and bool(hi) and joiner.small(name, g, u, cond)
            if not hi or count < lo:
                if tiny:
                    small.append(name)
                continue
            room = sum(n for _m, n in slots)
            want = want_w / g.module.pmax
            best = None
            # the project's strategy first; before 08/11 along the path when it left a face of a few modules out
            for way in dict.fromkeys((strategy,) if tiny else (strategy, "serpentine")):
                for length in range(lo, min(hi, count) + 1):
                    if not plant._length_allowed(u, length):
                        continue
                    cut = plant.order(placed, length, way)[0]
                    for n in {min(room, len(cut), max(1, round(want / length))),
                              min(room, len(cut), max(1, int(want // length)))}:
                        if n < 1:
                            continue
                        key = (abs(n * length - want) + (0 if count == n * length else 0.5)
                               + (0 if way == strategy else 0.25), -length)
                        if best is None or key < best[0]:
                            best = (key, n, length, cut)
            if best is None:
                if tiny:
                    small.append(name)          # too small for a string of whole rows: after the others
                continue
            _key, n, length, cut = best
            strings = cut[:n]
            if not strings:
                continue
            lengths[name] = length
            taken = set()
            for row in strings:
                if not slots:
                    break
                runs.append({"inverter": u.number, "mppt": slots[0][0],
                             "modules": [f"{g.sfid}/{pm.key}" for pm in row]})
                laid.setdefault(name, []).append((len(runs) - 1, row, g))
                taken.update(id(pm) for pm in row)
                slots[0][1] -= 1
                want_w -= length * g.module.pmax
                if slots[0][1] <= 0:
                    slots.pop(0)
            if slots and taken and runs and runs[-1]["mppt"] == slots[0][0]:
                slots.pop(0)                    # an input with strings of this group takes no other group
            rest = [pm for pm in placed if id(pm) not in taken]
            if rest and tiny:
                small.append(name)      # what the rows leave of a small face
            if rest:
                pools[name] = (g, rest)
            else:
                pools.pop(name)
        for name in small:
            if name not in pools:
                continue
            string, index = joiner.join(name, pools, u, cond, lengths, laid)
            if not string:
                continue
            keys = [f"{g.sfid}/{pm.key}" for g, pm in string]
            if index is not None:
                # the partner's string goes on over this face: on its input when it is alone there, else on a free one
                old = runs[index]
                alone = sum(1 for r in runs if r["inverter"] == old["inverter"] and r["mppt"] == old["mppt"]) == 1
                if not alone and not slots:
                    continue
                runs[index] = {"inverter": u.number, "mppt": old["mppt"] if alone else slots.pop(0)[0],
                               "modules": keys}
                mine = pools[name][0].sfid
                _take(pools, [(g, pm) for g, pm in string if g.sfid == mine])
            elif slots:
                runs.append({"inverter": u.number, "mppt": slots.pop(0)[0], "modules": keys})
                _take(pools, string)
    return runs


def _slots_all(u, module) -> list:
    return [(m + 1, max(1, stringing.strings_allowed(module, u.spec, m))) for m in range(u.inputs)]


def _pools(groups: list, keys: set) -> dict:
    out = {}
    for g in groups:
        placed = [pm for pm in g.placed if f"{g.sfid}/{pm.key}" in keys]
        if placed:
            out[g.key or g.sfid] = (g, placed)
    return out


def _free_plan(project, groups, records, entries, runs, free, wanted, budget, stop, before, offset, base,
               partial) -> list:
    """The planner's proposals (Results without words: `choose_free` writes them), the best guesses tried first."""
    usable = [{"_sizing_pac": _power(rec), "_sizing_record": rec} for rec in records if not missing_fields(rec)]
    if not usable:
        return []
    low, high = band(wanted)
    cond = plant.conditions(project)
    strategy = ((project.energy or {}).get("strings") or {}).get("strategy") or "serpentine"
    joiner = _Joiner(project, groups, strategy, free)
    p_stc = sum(len(g.placed) * g.module.pmax for g in groups)
    by_key = {f"{g.sfid}/{pm.key}": g for g in groups for pm in g.placed}
    main = max(_pools(groups, free).values(), key=lambda gp: len(gp[1]))[0].module
    ratios = plant.unit_ratios(base)
    mine = [u for u in base.units if 0 <= u.entry and u.number <= offset and u.fixed is None and u.mlpe is None
            and u.checkable and ratios.get(u.number, 0.0) < high]
    # 1. what the free inputs of the inverters there are take: up to the ratio asked, the top, the foot of the band
    shares = [([], set(free))]
    marks = set()
    if partial:
        shares.append(([_run_of(s) for s in partial], set(free) - {k for s in partial for k in s.keys}))
        marks.add(frozenset(k for s in partial for k in s.keys))
    for level in (wanted, (wanted + high) / 2, high, low):
        plan = [(u, level * u.spec.pac - ratios.get(u.number, 0.0) * u.spec.pac, _slots(u, runs, main)) for u in mine]
        plan = [p for p in plan if p[1] > 0 and p[2]]
        if not plan:
            continue
        pools = _pools(groups, free)
        laid = _lay(plan, pools, cond, strategy, joiner)
        mark = frozenset(k for r in laid for k in r["modules"])
        if laid and mark not in marks:
            marks.add(mark)
            shares.append((laid, set(free) - mark))
    # 2. for the rest, inverters of the right size, each combination with its strings drawn the same way
    tries = []
    for first, rest in shares:
        done = {}
        for r in first:
            k = int(r["inverter"])
            done[k] = done.get(k, 0.0) + sum(by_key[x].module.pmax for x in r["modules"])
        reach = {k: (ratios.get(k, 0.0) * base.units[k - 1].spec.pac + w) / base.units[k - 1].spec.pac
                 for k, w in done.items()}
        cost = sum(abs(r - wanted) for r in reach.values())
        if not rest:                            # the free inputs take every one: no inverter added
            tries.append(((max(standing(r, wanted) for r in reach.values()), 0, 0, round(cost, 4), len(tries)), first,
                          [], None, 0.0))
            continue
        alone = [dataclasses.replace(g, placed=[pm for pm in g.placed if f"{g.sfid}/{pm.key}" in rest], target=(0, 0))
                 for g in groups]
        alone = [g for g in alone if g.placed]
        pooled = _pooled(alone)
        static = [_static(u["_sizing_record"], pooled, cond) for u in usable]
        reached = set().union(*(served for served, _cause, _fewest in static))
        if not reached:
            continue
        keep = {id(g) for i in reached for g in pooled[i]}
        fit = [u for u, (served, _c, _f) in zip(usable, static, strict=True) if served]
        p_w = sum(len(g.placed) * g.module.pmax for g in alone if id(g) in keep)
        # r24: a face no model strings alone (too few modules) comes too, for its string to go on over the next face
        kinds = {plant._module_key(g.module) for g in alone if id(g) in keep}
        within = [g for g in alone if id(g) in keep or plant._module_key(g.module) in kinds]
        for key, combo in _free_combos(fit, p_w, wanted):
            tries.append(((key[0], key[1], key[2], round(key[3] + cost, 4), len(tries)), first, within, combo, p_w))
    tries.sort(key=lambda t: t[0])
    found = []
    for _key, first, within, combo, p_w in tries:
        if stop is not None and stop():
            return []
        if budget.expired():
            break
        if len(found) >= FREE_ENOUGH and any(not r.left and r.standing == IN_BAND for r in found):
            break
        more = copy.deepcopy(combo or [])
        ac = sum(_power(e["record"]) * e["count"] for e in more)
        units = plant.units_of(_candidate(_with(project, [], []), more), p_w, within[0].module, cond.t_min) if more else []
        ways = [] if more else [[]]
        if more and all(u.fixed is None and u.mlpe is None and u.checkable for u in units):
            pools = _pools(within, {f"{g.sfid}/{pm.key}" for g in within for pm in g.placed})
            plan = [(dataclasses.replace(u, number=u.number + offset), p_w * u.spec.pac / ac, _slots_all(u, main))
                    for u in units]
            if plan:                        # the last one takes what is left, up to the top of the band
                last = plan[-1]
                plan[-1] = (last[0], max(last[1], high * last[0].spec.pac), last[2])
            ways.append(_lay(plan, pools, cond, strategy, joiner))
        result = None
        for laid in ways + [None]:
            if laid is None:
                if not more or result is not None and not result.left:
                    break
                # the strings as the proposal draws them (optimizers, SolarEdge, or the drawing above fell short)
                part = budget.part(max(1, min(CANDIDATE_STATES, budget.limit - budget.nodes)))
                part.cancelled = stop
                sub = plant.build(_candidate(_with(project, [], []), more), groups=within, search=part)
                budget.nodes += part.nodes
                if (not sub.search_complete or not sub.strings or not all(plant.acceptable(s) for s in sub.strings)
                        or any(_bad(c) for checks in sub.checks.values() for c in checks)):
                    continue
                laid = [dict(x, inverter=int(x.get("inverter") or 0) + offset) for x in plant.runs_of(sub)]
                if budget.expired() and result is not None:
                    break
            new_runs = copy.deepcopy(first) + laid
            out = plant.build(_with(project, entries + more, runs + new_runs), groups=groups)
            left = {f"{k[0]}/{k[1]}" for k in out.left}
            if not left <= free or _failure(dataclasses.replace(out, left=[]), len(runs), before):
                continue
            ac_all = sum(u.spec.pac for u in out.units)
            unit_ratio = plant.unit_ratios(out)
            touched = {int(r.get("inverter") or 0) for r in new_runs}
            res = Result(entries=copy.deepcopy(entries) + more, runs=runs + new_runs, plant=out,
                         ratio=p_stc / ac_all if ac_all else 0.0, ok=True,
                         notes=plant.conditions_of([s for s in out.strings if s.run >= len(runs) or s.run < 0]),
                         wanted=wanted, standing=max(standing(unit_ratio.get(k, 0.0), wanted) for k in touched),
                         mode=(FREE_BOTH if more else FREE_INPUTS) if first else FREE_NEW, added=more, new_runs=new_runs, free=len(free),
                         search_nodes=budget.nodes, left=len(left), first=copy.deepcopy(first),
                         faces_why=dict(joiner.why))
            if result is None or (res.left, res.standing) < (result.left, result.standing):
                result = res
        if result is not None:
            found.append(result)
    return found


def choose_free(project, groups: list, records: list[dict], ratio: float, runs: list | None = None, *,
                cancelled=None, search=None, enough=None, seconds: float | None = FREE_SECONDS) -> Result:
    """Inverters and strings for the modules in no string only (R522): the designer's strings (`runs`, the project's
    when None) and inverters stay as they are, the modules in none of them are strung by the rules of `choose` and
    of the proposal (the DC/AC band, the brand chosen, the optimizers, R433 and R456 as `plant.proposal` applies them).

    The ways, said in `mode` and in the words:
    - FREE_INPUTS: the free inputs of the inverters there are (the window's «Complete»), when its strings pass the checks
      and no inverter that takes them goes above the band: taken at once, nothing is added;
    - FREE_NEW: inverters of `records` added after the others (their numbers follow), sized by `choose` on the free
      modules alone at the ratio asked, when the free inputs do not take them or would go above the band;
    - FREE_BOTH: the free inputs take part of them with valid strings, inverters are added for the rest.
    Between FREE_NEW and FREE_BOTH: the fewer inverters that take a free module outside the band (each inverter's
    ratio), then the fewer inverters added, then the whole plant's ratio closest to the one asked; the others are the
    alternatives. The free inputs above the band are taken only when no inverter added makes a valid proposal, and that
    is said. `ratio` is that of the whole plant; each inverter's is in the words and in `unit_ratios`.
    The search ends within `seconds` (FREE_SECONDS; None for no limit) or when `enough()` (the window's «Stop») with the
    best proposal found until then; `cancelled` throws it away."""
    runs = [r for r in (runs if runs is not None else
                        (((project.energy or {}).get("strings") or {}).get("runs") or [])) if r.__class__ is dict]
    if not groups:
        return Result(reason=_("Lay the modules before sizing the inverters: their DC power is not known yet."))
    free = set(free_keys(project, groups, runs))
    if not free:
        return Result(reason=_("Every module laid is in a string already: there are no modules in no string."))
    from . import system
    entries = system.inverter_entries(project.energy)
    wanted = max(0.1, float(ratio))
    low, high = band(wanted)
    p_stc = sum(len(g.placed) * g.module.pmax for g in groups)
    base = plant.build(_with(project, entries, runs), groups=groups)
    offset = sum(1 for u in base.units if u.entry >= 0)
    # what is wrong already in the designer's part is his: said by the checks, never a reason to refuse the free modules
    before = _failing_units(base) if runs else set()
    if runs and not offset:
        return Result(reason=_("The strings there are are on no inverter of the catalogue: choose their inverter "
                               "first, or size the whole plant."), free=len(free))
    budget = search if search is not None else stringing.SearchBudget(MAX_SEARCH_STATES, cancelled)
    if seconds is not None and budget.deadline is None:
        budget.deadline = time.monotonic() + float(seconds)
    if enough is not None:
        budget.enough = enough
    stop = cancelled if cancelled is not None else budget.cancelled
    n = len(free)

    # 1. the free inputs of the inverters there are
    inputs, why_inputs, over, partial = None, "", [], []
    if offset:
        share = budget.part(FREE_STATES)
        share.cancelled = stop
        out = plant.proposal(_with(project, entries, runs), groups=groups, keep=runs, search=share)
        budget.nodes += share.nodes
        added = [s for s in out.strings if s.run < 0]
        why_inputs = _failure(out, len(runs), before) or ("" if added else _("no input takes a string of them"))
        fresh = {(s.inverter, s.mppt) for s in added}
        clean = (out.search_complete
                 and all(plant.acceptable(s) or (s.run >= 0 and ("input", s.inverter, s.mppt) in before
                                                 and (s.inverter, s.mppt) not in fresh) for s in out.strings)
                 and not any(_bad(c) and ("check", u, c.key, c.label) not in before
                             for u, checks in out.checks.items() for c in checks))
        if not why_inputs:
            ratios = plant.unit_ratios(out)
            ac = sum(u.spec.pac for u in out.units)
            touched = sorted({s.inverter for s in added})
            over = [(k, ratios[k]) for k in touched if ratios.get(k, 0.0) > high + 1e-9]
            inputs = Result(entries=copy.deepcopy(entries), runs=runs + [_run_of(s) for s in added], plant=out,
                            ratio=p_stc / ac if ac else 0.0, ok=True, notes=plant.conditions_of(added), wanted=wanted,
                            standing=ABOVE_BAND if over else IN_BAND, mode=FREE_INPUTS,
                            new_runs=[_run_of(s) for s in added], free=n, search_nodes=budget.nodes)
            inputs.why = _free_why(inputs, ngettext(
                "The {n} module in no string goes on free inputs of the inverters there are (inverter {which}): no "
                "inverter is added.",
                "The {n} modules in no string go on free inputs of the inverters there are (inverter {which}): no "
                "inverter is added.", n).format(n=n, which=", ".join(str(k) for k in touched)), len(runs))
        elif clean and added and out.left:
            partial = added             # the free inputs take part of them: inverters added for the rest (FREE_BOTH)
    if stop is not None and stop():
        return Result(reason=_("Inverter search cancelled; no choice has been applied."), search_complete=False)
    if inputs is not None and not over:
        return inputs

    def word(res, mode, m, which):
        """The words of a proposal with inverters added: `m` modules on them, the others on the free inputs of
        inverters `which`."""
        if res.left:
            res.notes.insert(0, ngettext(
                "{m} module stays in no string: no combination of these inverters strings every one.",
                "{m} modules stay in no string: no combination of these inverters strings every one.",
                res.left).format(m=res.left))
        names = _names(res.added)
        if mode == FREE_INPUTS:
            head = ngettext(
                "The {n} module in no string goes on free inputs of the inverters there are (inverter {which}): no "
                "inverter is added.",
                "The {n} modules in no string go on free inputs of the inverters there are (inverter {which}): no "
                "inverter is added.", n).format(n=n, which=", ".join(str(k) for k in which))
        elif mode == FREE_BOTH:
            head = ngettext(
                "{k} of the {n} module in no string go on free inputs of the inverters there are (inverter "
                "{which}); {names} added for the other {m}.",
                "{k} of the {n} modules in no string go on free inputs of the inverters there are (inverter "
                "{which}); {names} added for the other {m}.", n).format(
                k=n - m, n=n, m=m, names=names,
                which=", ".join(str(k) for k in which))
        elif over:
            head = ngettext(
                "On free inputs of the inverters there are, inverter {k} would reach a DC/AC ratio of {ratio}, "
                "above the band (up to {high}): {names} added for the {n} module in no string.",
                "On free inputs of the inverters there are, inverter {k} would reach a DC/AC ratio of {ratio}, "
                "above the band (up to {high}): {names} added for the {n} modules in no string.", n).format(
                k=over[0][0], ratio=number(over[0][1], 2), high=number(high, 2), names=names, n=n)
        elif offset:
            head = ngettext(
                "The free inputs of the inverters there are do not take them ({why}): {names} added for the "
                "{n} module in no string.",
                "The free inputs of the inverters there are do not take them ({why}): {names} added for the "
                "{n} modules in no string.", n).format(why=why_inputs.rstrip("."), names=names, n=n)
        else:
            head = ngettext("{names} added for the {n} module in no string.",
                            "{names} added for the {n} modules in no string.", n).format(names=names, n=n)
        res.why = _free_why(res, head, len(runs))
        return res

    # 2. inverters added: for every free module, and for those the free inputs leave
    news, why_new = [], ""
    targeted = sorted({g.target[0] for g in groups
                       if g.target[0] and any(f"{g.sfid}/{pm.key}" in free for pm in g.placed)})
    if targeted:
        why_new = _("a sub-field sends its strings to inverter {which}: its modules go there only").format(
            which=", ".join(str(k) for k in targeted))
    elif not records:
        why_new = _("There is no inverter in the catalogue to size.")
    else:
        # R522 r22-impianto: first as a designer would (the free inputs up to the ratio asked, then the right size)
        news = _free_plan(project, groups, records, entries, runs, free, wanted, budget, stop, before, offset, base,
                          partial)
        ways = [] if news or budget.expired() else [(FREE_NEW, [], free)]
        if partial and ways:
            ways.append((FREE_BOTH, [_run_of(s) for s in partial], free - {k for s in partial for k in s.keys}))
        sized_any = bool(news)
        news = [word(r, r.mode, n - sum(len(x["modules"]) for x in r.first), sorted({x["inverter"] for x in r.first}))
                for r in news]
        ways.reverse()                  # the fewer modules first: the time left is shared out evenly between the ways
        for i, (mode, first, keys) in enumerate(ways):
            alone = [dataclasses.replace(g, placed=[pm for pm in g.placed if f"{g.sfid}/{pm.key}" in keys],
                                         target=(0, 0)) for g in groups]
            alone = [g for g in alone if g.placed]
            part = budget.part(budget.limit)
            if budget.deadline is not None:
                part.deadline = time.monotonic() + max(0.0, budget.deadline - time.monotonic()) / (len(ways) - i)
            sub = choose(_with(project, [], []), alone, records, ratio, cancelled=stop, search=part, partial=True)
            budget.nodes += part.nodes
            if not sub.ok:
                why_new = why_new or sub.reason
                continue
            sized_any = True
            for r in [sub, *sub.alternatives]:
                added = copy.deepcopy(r.entries)
                new_runs = copy.deepcopy(first) + [dict(x, inverter=int(x.get("inverter") or 0) + offset) for x in r.runs]
                out = plant.build(_with(project, entries + added, runs + new_runs), groups=groups)
                left = {f"{k[0]}/{k[1]}" for k in out.left}
                if _failure(dataclasses.replace(out, left=[]) if r.left and left <= free else out, len(runs), before):
                    continue
                ac = sum(u.spec.pac for u in out.units)
                res = Result(entries=copy.deepcopy(entries) + added, runs=runs + new_runs, plant=out,
                             ratio=p_stc / ac if ac else 0.0, ok=True, notes=list(r.notes), wanted=wanted,
                             standing=r.standing, mode=mode, added=added, new_runs=new_runs, free=n,
                             search_nodes=budget.nodes, evaluated=sub.evaluated, undecided=list(sub.undecided),
                             left=len(left))
                news.append(word(res, mode, len(keys), sorted({s.inverter for s in partial})))
        if sized_any and not news:
            why_new = _("the inverters added do not pass the checks together with the strings there are")
    if news:
        fewest = min(r.left for r in news)
        slack = 2                       # less than a string: the rounding of the lengths, not a way to leave modules
        module = next(g.module for g in groups for pm in g.placed if f"{g.sfid}/{pm.key}" in free)
        # the inverters there are with an input free: one the proposal leaves under the band counts as outside it
        open_units = {u.number for u in base.units if 0 <= u.entry and u.number <= offset and u.fixed is None
                      and _slots(u, runs, module)}

        def score(res):
            # R522 r22-impianto: the fewest modules left (give or take a few), then each inverter that takes a free
            # module against the band (by inverter, not only on the whole), then the modules left, the whole plant in
            # the band, the fewer inverters and models added, and the ratios closest to the one asked
            ratios = plant.unit_ratios(res.plant)
            mine = {int(r.get("inverter") or 0) for r in res.new_runs}
            outside = sum(1 for k in mine if not low - 1e-9 <= ratios.get(k, 0.0) <= high + 1e-9)
            outside += sum(1 for k in open_units - mine if ratios.get(k, 0.0) < low - 1e-9)
            whole = 0 if low - 1e-9 <= res.ratio <= high + 1e-9 else 1
            return (res.left > fewest + slack, outside, res.left, whole, sum(e["count"] for e in res.added),
                    len(res.added), round(sum(abs(ratios.get(k, 0.0) - wanted) for k in mine), 3),
                    abs(res.ratio / wanted - 1))
        news.sort(key=score)
        unique, seen = [], set()
        for res in news:                # the same inverters and strings reached by two ways: listed once
            mark = dump_key(res)
            if mark not in seen:
                seen.add(mark)
                unique.append(res)
        best = unique[0]
        # the free inputs alone (above the band) stay among the alternatives: another way, not another size
        tail = [inputs] if inputs is not None else []
        best.alternatives = unique[1:1 + MAX_ALTERNATIVES - len(tail)] + tail
        for res in [best, *best.alternatives]:
            _free_tell(res, low, high, offset, groups, project)
        if budget.expired() and not any(time_up(budget) in x for x in best.notes):
            best.notes.append(time_up(budget))
        return best
    if inputs is not None:
        inputs.notes.append(_("Above the band: no inverter added for these modules makes a valid proposal ({why}).")
                            .format(why=why_new.split("\n")[0].rstrip(".")))
        return inputs
    reason = ngettext("No proposal for the {n} module in no string.", "No proposal for the {n} modules in no string.",
                      n).format(n=n)
    if why_inputs:
        reason += "\n" + _("Free inputs of the inverters there are: {why}").format(why=why_inputs)
    if why_new:
        reason += "\n" + _("Inverters added: {why}").format(why=why_new)
    if budget.enough is not None and budget.enough():
        reason += "\n" + _("Search stopped before a valid proposal was found.")
    elif seconds is not None and budget.deadline is not None and time.monotonic() > budget.deadline:
        reason += "\n" + _("No valid proposal was found within the time limit of {s} s.").format(
            s=number(seconds, 0))
    return Result(reason=reason, free=n, search_nodes=budget.nodes,
                  search_complete=not (stop is not None and stop()))
