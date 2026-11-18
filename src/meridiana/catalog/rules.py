"""What goes with what, by maker, as data: the one source of the rules of optimizers and their strings (R423, R456).

`data/optimizer_rules.json` holds, for each maker, its families of optimizers (R456): what each one is (an optimizer or a
safety device), how its strings are sized (SolarEdge's tables, Huawei's long strings, or the inverter's own window),
the modules on one unit, whether units of one and of two modules go in one string, whether the optimizers may be on some
modules only, the parallel strings, and the string rules by inverter, every number with its document and page.
`energy.optimizers` takes SolarEdge's tables from here, `energy.optimizer_strings` the families on inverters with MPPT;
`rule()` answers for any pair. What a datasheet does not say stays "unknown": neither passed nor refused, and the window
says so.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache

from . import DATA

OK, NO, UNKNOWN, BY_TABLE = "ok", "no", "unknown", "by_table"

# how the strings of a family are sized
SOLAREDGE_TABLES = "solaredge_tables"   # an inverter at a fixed string voltage, SolarEdge's tables (energy.optimizers)
LONG_STRING = "long_string"             # the count of optimizers and the power per string (Huawei, full optimization)
INVERTER_WINDOW = "inverter_window"     # as without optimizers: the inverter's MPPT window and voltage (Tigo, Sungrow)


@lru_cache(maxsize=1)
def data() -> dict:
    return json.loads((DATA / "optimizer_rules.json").read_text(encoding="utf-8"))


def solaredge() -> dict:
    return data()["SolarEdge"]


@dataclass(frozen=True)
class Rule:
    state: str = UNKNOWN            # ok, no, unknown; by_table: energy.optimizers decides with SolarEdge's tables
    modules_per_unit: int = 0       # 0: not said
    minimum: int = 0                # optimizers in a string, 0: not said
    maximum: int = 0
    p_string_w: float = 0.0
    source: str = ""
    why: str = ""
    consult: bool = False           # the maker asks to be consulted before the order (Sungrow's ***)


@dataclass(frozen=True)
class Family:
    """A family of optimizers as its maker's documents describe it; `raw` is its entry of the data file."""
    maker: str
    id: str
    name: str
    function: str                   # "optimizer" (it tracks the module's maximum power) or "safety" (shutdown only)
    sizing: str                     # SOLAREDGE_TABLES, LONG_STRING or INVERTER_WINDOW
    modules_per_unit: tuple         # (1,) or (1, 2)
    datasheet: str
    raw: dict = field(default_factory=dict, compare=False, hash=False)

    def part(self, key: str) -> dict:
        value = self.raw.get(key)
        return value if isinstance(value, dict) else {}

    @property
    def mixing(self) -> str:
        """Units of one and of two modules in one string: "ok", "one_single" (at most one unit with one module, or all),
        "no", "not_stated", "n/a" (one module a unit), "with_safety"/"with_optimizer" (Tigo's selective deployment)."""
        return str(self.part("mixing").get("state") or "n/a")

    @property
    def partial(self) -> str:
        """Optimizers on some modules only: "no", "conditions", "not_stated"."""
        return str(self.part("partial").get("state") or "not_stated")

    @property
    def orientations_free(self) -> bool:
        """Whether one string may run over different orientations (with every module on the family's units)."""
        return self.part("orientations").get("state") == "free"

    @property
    def energy_modelled(self) -> bool:
        """Whether the year's energy models what the family does: SolarEdge's and, since R456 (r18), the optimizers on
        inverters with MPPT ("modelled"), the safety devices computed as a plain string with their small loss ("plain")."""
        return self.raw.get("energy") in ("modelled", "plain")


def _maker_key(maker: str) -> str:
    return next((k for k in data() if k.casefold() == maker.casefold()), maker)


def _families(maker: str) -> list[Family]:
    entry = data().get(maker)
    out = []
    for raw in (entry or {}).get("families", []) if isinstance(entry, dict) else []:
        out.append(Family(maker, raw["id"], raw.get("name", raw["id"]), raw.get("function", "optimizer"),
                          raw.get("sizing", INVERTER_WINDOW), tuple(raw.get("modules_per_unit") or (1,)),
                          raw.get("datasheet", ""), raw))
    return out


def family(optimizer: dict | None) -> Family | None:
    """The family of an optimizer's record (its maker and model), None when the data file has none for it."""
    maker = _maker_key(str((optimizer or {}).get("manufacturer") or ""))
    model = str((optimizer or {}).get("model") or "")
    return next((f for f in _families(maker) if re.search(f.raw["optimizers"], model)), None)


def families() -> list[Family]:
    """Every family of the data file, maker by maker."""
    return [f for maker, entry in data().items() if isinstance(entry, dict) for f in _families(maker)]


def string_rule(fam: Family, inverter: dict | None) -> Rule:
    """The string rule of a family on an inverter: the row of its maker's table, "no" when the documents do not name
    the inverter (or it is of another maker and the documents name only their own), "unknown" when they do not say."""
    if inverter is None:
        return Rule(UNKNOWN)
    other = (data().get(fam.maker) or {}).get("other_makers")
    if other and str(inverter.get("manufacturer") or "").casefold() != fam.maker.casefold():
        return Rule(other["state"], why=other.get("why", ""))
    name = str(inverter.get("model") or "")
    per = max(fam.modules_per_unit)
    for row in fam.raw.get("string_rules", []):
        if re.search(row["inverters"], name):
            return Rule(row["state"], per, int(row.get("min") or 0), int(row.get("max") or 0),
                        float(row.get("p_string_w") or 0), row.get("source", ""), row.get("why", ""),
                        bool(row.get("consult")))
    fallback = fam.raw.get("default")
    return Rule(fallback["state"], why=fallback.get("why", "")) if fallback else Rule(UNKNOWN)


def rule(optimizer: dict, inverter: dict | None) -> Rule:
    """The rule of an optimizer's strings on an inverter, from the optimizer maker's data; unknown when the catalogue holds
    nothing about that maker."""
    maker = str((optimizer or {}).get("manufacturer") or "")
    model = str((optimizer or {}).get("model") or "")
    entry = data().get(_maker_key(maker))
    if not isinstance(entry, dict):
        return Rule(UNKNOWN, why=f"no rules on file for {maker}")
    fam = family(optimizer)
    if fam is not None and fam.sizing != SOLAREDGE_TABLES:
        return string_rule(fam, inverter) if inverter is not None else Rule(UNKNOWN)
    groups = [g for g in entry.get("groups", []) if re.search(g["optimizers"], model)]
    if not groups:
        return Rule(UNKNOWN, why=f"{model} is not in the rules on file for {maker}")
    if inverter is None:
        return Rule(UNKNOWN)
    other = entry.get("other_makers")
    if other and str(inverter.get("manufacturer") or "").casefold() != maker.casefold():
        return Rule(other["state"], why=other.get("why", ""))
    name = str(inverter.get("model") or "")
    for group in groups:
        if re.search(group["inverters"], name):
            return Rule(group["state"], int(group.get("modules_per_unit") or 0), int(group.get("min") or 0),
                        int(group.get("max") or 0), float(group.get("p_string_w") or 0), group.get("source", ""),
                        group.get("why", ""))
    fallback = entry.get("default")
    return Rule(fallback["state"], why=fallback.get("why", "")) if fallback else Rule(UNKNOWN)
