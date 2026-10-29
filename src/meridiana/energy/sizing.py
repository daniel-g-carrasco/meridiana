"""Automatic inverter sizing, accepted only together with a complete and valid string proposal.

The choice is deliberately lexicographic: fewer inverters first, then fewer different models, then the DC/AC
ratio closest to the one requested. Catalogue source and model name only break exact ties. A combination that
leaves modules out or violates an input's voltage or current limits is not a sizing result.
"""

from __future__ import annotations

import copy
import itertools
import math
from dataclasses import dataclass, field

from ..i18n import _
from . import optimizers, plant, stringing
from .components import InverterSpec


CRITERION = _("fewer inverters, then fewer models, then the closest DC/AC ratio")
MAX_CANDIDATES = 2048  # total across the whole search, including each category's ordering
MAX_SEARCH_STATES = 200000


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


def _power(record: dict) -> float:
    return float(record.get("ac_power_nominal_w") or record.get("pac") or 0.0)


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
    """
    count = sum(len(g.placed) for g in groups)
    if any(optimizers.fixed_voltage(r) is not None for r in records):
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


def choose(project, groups: list, records: list[dict], ratio: float, *, cancelled=None, search=None) -> Result:
    """Size the plant of `project` on its laid `groups`, using only `records` of the brand chosen.

    Every candidate is stringed by `plant.build` and checked at the project's temperatures. The first complete
    and valid proposal in the order of CRITERION wins. With no such candidate, no inverter choice is returned.
    """
    usable = []
    for rec in records:
        pac = _power(rec)
        if pac > 0 and (optimizers.fixed_voltage(rec) is not None or
                        rec.get("mppt_count") and rec.get("mppt_voltage_min_v") and rec.get("mppt_voltage_max_v")):
            usable.append({"_sizing_pac": pac, "_sizing_record": rec})
    if not usable or not groups:
        return Result(reason=_("No inverter with a nominal AC power and a complete MPPT datasheet is available."))
    p_stc = sum(len(g.placed) * g.module.pmax for g in groups)
    target_ac = p_stc / max(0.1, float(ratio))
    min_units, max_units = _unit_bounds(project, groups, [r["_sizing_record"] for r in usable])
    required = max((g.target[0] for g in groups), default=0)
    min_units, max_units = max(min_units, required), max(max_units, required)
    evaluated = 0
    budget = search if search is not None else stringing.SearchBudget(MAX_SEARCH_STATES, cancelled)
    for units in range(min_units, max_units + 1):
        for models in range(1, min(units, len(usable)) + 1):
            if cancelled is not None and cancelled():
                return Result(reason=_("Inverter search cancelled; no choice has been applied."), search_complete=False,
                              search_nodes=budget.nodes, evaluated=evaluated)
            category = []
            try:
                for candidate in itertools.islice(_combinations(usable, units, models, target_ac),
                                                   MAX_CANDIDATES - evaluated + 1):
                    budget.step()
                    category.append(candidate)
            except stringing.SearchStopped:
                return Result(reason=budget.reason, search_complete=False, search_nodes=budget.nodes,
                              evaluated=evaluated)
            if len(category) > MAX_CANDIDATES - evaluated:
                return Result(reason=_("Inverter search incomplete: the limit of {n} combinations was reached. "
                                       "Narrow the catalogue selection and try again.").format(n=MAX_CANDIDATES),
                              search_complete=False, search_nodes=budget.nodes, evaluated=evaluated)
            candidates = sorted(category,
                                key=lambda item: (item[0], item[1][0]["record"].get("source") != "curated",
                                                  [(e["record"].get("model", ""), e["count"]) for e in item[1]]))
            for _error, entries in candidates:
                if cancelled is not None and cancelled():
                    return Result(reason=_("Inverter search cancelled; no choice has been applied."), search_complete=False,
                                  search_nodes=budget.nodes, evaluated=evaluated)
                evaluated += 1
                out = plant.build(_candidate(project, entries), groups=groups, search=budget)
                if not out.search_complete:
                    return Result(reason=out.search_reason, search_complete=False, search_nodes=budget.nodes,
                                  evaluated=evaluated)
                if out.left or not out.strings or any(s.state != "ok" for s in out.strings):
                    continue
                if any(c.level == "fail" or (c.key == "imp_total" and c.level == "warn")
                       for checks in out.checks.values() for c in checks):
                    continue
                ac = sum(_power(e["record"]) * e["count"] for e in entries)
                return Result(entries=out.entries or entries, runs=plant.runs_of(out), plant=out, ratio=p_stc / ac,
                              ok=True, search_nodes=budget.nodes, evaluated=evaluated)
    return Result(reason=_("No complete string proposal was found within the voltage, current and input limits. "
                           "The search exhausted the supplied catalogue and the selected geometry constraints."),
                  search_nodes=budget.nodes, evaluated=evaluated)
