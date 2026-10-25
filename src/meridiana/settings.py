"""The settings of the energy side of a project, typed: what the free dictionaries `energy`, `consumption`
and `economics` of the project may hold, each key with the type of its default. The project keeps the
dictionaries (the pages write them by path, energy/* reads them); this is their schema, and `from_dict`
says which keys the program does not know, so that a path mistaken or a file edited by hand is seen and not
kept in silence (study 18, A 5.4 and 7.14).

The losses, the consumption and the economics mirror the dataclasses of energy/simulate.py,
energy/consumption.py and energy/economics.py field by field (tests/test_settings.py holds the two together):
written here again so that the model does not import the energy side (A 7.12)."""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field


@dataclass
class Losses:
    """energy.simulate.Losses: the loss chain."""
    transposition: str = "perez"
    albedo: float = 0.20
    use_horizon: bool = True
    use_near: bool = True
    iam_b0: float = 0.05
    soiling: float = 2.0
    quality: float = 0.0
    lid: float | None = None
    mismatch: float = 1.0
    dc_wiring: float = 1.5
    ac_wiring: float = 1.0
    unavailability: float = 0.0
    electrical_shading: bool = True         # the electrical effect of the near shadows (18d), or linear only
    electrical_fraction: float = 100.0      # % of that effect applied, as PVsyst's fraction


STRATEGIES = ("serpentine", "rows", "u", "row_per_mppt")


@dataclass
class Strings:
    """The strings (task 16d, R114): `runs` are the designer's, {"inverter": unit from 1, "mppt": input from 1,
    "modules": ["sub-field id/module key", ...]} in the order the string runs, made by hand or by Meridiana's
    proposal when he asked for it, with the `strategy`, `n_series` and `per_mppt` of the proposal (0 and []:
    Meridiana chooses). `auto` (format 14) marks the live proposal of an older project, or a PVsyst import's
    counts: written down as `runs` at the first layout (energy/plant.py)."""
    auto: bool = False
    strategy: str = "serpentine"
    n_series: int = 0
    per_mppt: list = field(default_factory=list)
    runs: list = field(default_factory=list)


@dataclass
class EnergySettings:
    """The `energy` dictionary of a project: the inverters chosen ({"record": a record of the catalogue, "count",
    "name", and for an inverter at a fixed string voltage its power optimizers, "optimizer": a record of the
    catalogue, "per_optimizer": 1 or 2 modules on each, format 13}; none, and the ratio to size one), the losses, the thermal case of each sub-field, the design
    temperature, the strings, and what a PVsyst import left behind."""
    inverters: list = field(default_factory=list)
    dc_ac_ratio: float = 1.1
    losses: Losses = field(default_factory=Losses)
    thermal: dict = field(default_factory=dict)         # sub-field id -> "open", "close", "insulated"
    t_min: float | None = None
    strings: Strings = field(default_factory=Strings)
    pvsyst_import: dict = field(default_factory=dict)
    pvsyst_results: dict = field(default_factory=dict)


@dataclass
class ConsumptionSettings:
    """energy.consumption.Consumption: the consumption of the supply point."""
    pod: str = ""
    supply: str = "auto"
    contract_kw: float = 0.0
    profile: str = "auto"
    annual_kwh: float = 0.0
    bands_kwh: dict = field(default_factory=dict)
    monthly_kwh: list = field(default_factory=list)
    monthly_bands_kwh: list = field(default_factory=list)
    measured: list | dict = field(default_factory=list)


@dataclass
class EconomicsSettings:
    """energy.economics.Settings, less `defaults` (what the designer has not changed is told by absence)."""
    buy_f1: float = 0.25
    buy_f2: float = 0.25
    buy_f3: float = 0.25
    sell: float = 0.10
    pz: float = 110.0
    capex_per_kwp: float = 1300.0
    capex_total: float = 0.0
    opex_per_kwp: float = 20.0
    inverter_year: int = 12
    inverter_per_kw: float = 150.0
    years: int = 25
    discount: float = 4.0
    escalation: float = 2.0
    opex_escalation: float = 2.0
    degradation: float = -1.0
    deduction_pct: float = 0.0
    community: bool = False
    shared_pct: float = 60.0
    zone: str = ""
    grant_pct: float = 0.0
    trase: float = 0.0
    battery: dict = field(default_factory=dict)
    battery_units: int = 1
    battery_cost_per_kwh: float = 650.0
    export_limit_kw: float = -1.0


SECTIONS = {"energy": EnergySettings, "consumption": ConsumptionSettings, "economics": EconomicsSettings}


def _is_number(value) -> bool:
    return value.__class__ in (int, float) and math.isfinite(value)


def from_dict(kls, data: dict | None, path: str = "", unknown: list[str] | None = None):
    """An instance of `kls` from the keys of `data` it knows, each checked against the type of its default
    (ValueError with the path of the key otherwise); the keys it does not know go to `unknown` as paths, and
    are left out. A nested dataclass (the losses, the strings) is read the same way."""
    data = data or {}
    if data.__class__ is not dict:
        raise ValueError(f"{path or kls.__name__}: {data!r} is not a table")
    known = {f.name: f for f in dataclasses.fields(kls)}
    values = {}
    for key, value in data.items():
        where = f"{path}.{key}" if path else key
        f = known.get(key)
        if f is None:
            if unknown is not None:
                unknown.append(where)
            continue
        default = f.default if f.default is not dataclasses.MISSING else f.default_factory()
        if dataclasses.is_dataclass(default):
            values[key] = from_dict(default.__class__, value, where, unknown)
            continue
        if value is None and f.default is None:
            continue
        kind = default.__class__
        if kind is bool and value.__class__ is not bool:
            raise ValueError(f"{where}: {value!r} is not a switch")
        if kind is int and value.__class__ is not int:
            raise ValueError(f"{where}: {value!r} is not a whole number")
        if (kind is float or f.default is None) and not _is_number(value):
            raise ValueError(f"{where}: {value!r} is not a number")
        if kind is str and value.__class__ is not str:
            raise ValueError(f"{where}: {value!r} is not text")
        if kind is dict and value.__class__ is not dict:
            raise ValueError(f"{where}: {value!r} is not a table")
        if kind is list and value.__class__ not in (list, dict if key == "measured" else list):
            raise ValueError(f"{where}: {value!r} is not a list")
        values[key] = value
    return kls(**values)


def check(section: str, data: dict | None, unknown: list[str], path: str = "") -> None:
    """The dictionary of a section of the project against its schema: ValueError with the path of a value
    of the wrong type; the keys the program does not know appended to `unknown` (under `path`, or the name
    of the section). The inverters and the strings of the energy are lists of tables: each is checked too."""
    where = path or section
    read = from_dict(SECTIONS[section], data, where, unknown)
    if section != "energy":
        return
    for i, item in enumerate(read.inverters):
        here = f"{where}.inverters[{i}]"
        if item.__class__ is not dict:
            raise ValueError(f"{here}: {item!r} is not a table")
        if item.get("record").__class__ is not dict:
            raise ValueError(f"{here}.record: {item.get('record')!r} is not a table")
        count = item.get("count", 1)
        if count.__class__ is not int or count < 1:
            raise ValueError(f"{here}.count: {count!r} is not a whole number from 1")
        if item.get("name", "").__class__ is not str:
            raise ValueError(f"{here}.name: {item.get('name')!r} is not text")
        if item.get("optimizer") is not None and item["optimizer"].__class__ is not dict:
            raise ValueError(f"{here}.optimizer: {item['optimizer']!r} is not a table")
        per = item.get("per_optimizer", 1)
        if per.__class__ is not int or per not in (1, 2):
            raise ValueError(f"{here}.per_optimizer: {per!r} is not 1 or 2")
        unknown.extend(f"{here}.{k}" for k in item if k not in ("record", "count", "name", "optimizer",
                                                                 "per_optimizer"))
    if read.strings.strategy not in STRATEGIES:
        raise ValueError(f"{where}.strings.strategy: {read.strings.strategy!r} is not one of {', '.join(STRATEGIES)}")
    for i, run in enumerate(read.strings.runs):
        here = f"{where}.strings.runs[{i}]"
        if run.__class__ is not dict:
            raise ValueError(f"{here}: {run!r} is not a table")
        for key in ("inverter", "mppt"):
            if run.get(key, 1).__class__ is not int:
                raise ValueError(f"{here}.{key}: {run.get(key)!r} is not a whole number")
        modules = run.get("modules", [])
        if modules.__class__ is not list or any(m.__class__ is not str for m in modules):
            raise ValueError(f"{here}.modules: {modules!r} is not a list of module keys")


def known_paths(section: str) -> set[str]:
    """Every path a page may write in a section ("losses.soiling", "dc_ac_ratio"...)."""
    out: set[str] = set()

    def walk(kls, prefix: str) -> None:
        for f in dataclasses.fields(kls):
            default = f.default if f.default is not dataclasses.MISSING else f.default_factory()
            here = f"{prefix}{f.name}"
            out.add(here)
            if dataclasses.is_dataclass(default):
                walk(default.__class__, here + ".")
    walk(SECTIONS[section], "")
    return out
