"""The settings of the energy side of a project, typed: what the free dictionaries `energy`, `consumption`
and `economics` of the project may hold, each key with the type of its default. The project keeps the
dictionaries (the pages write them by path, energy/* reads them); this is their schema, and `from_dict`
says which keys the program does not know, so that a path mistaken or a file edited by hand is seen and not
kept in silence (study 18, A 5.4 and 7.14).

These schemas define the loss chain's defaults; the initial values of consumption and economics come from
the single table of the regulatory profile (core/rules/profiles/<id>/defaults.py, study 44 §4). The distinct
runtime classes in energy/simulate.py, energy/consumption.py and energy/economics.py inherit them and add their
methods. The model keeps no dependency on the energy implementation (A 7.12)."""

from __future__ import annotations

import dataclasses
import math
from meridiana.core.rules import registry
from dataclasses import dataclass, field


LID_FALLBACK = 1.0      # %: the light-induced degradation of a module whose datasheet gives none (simulate.lid_pct)
DESIGN_COLD = -10.0     # °C: the open-circuit voltage when the designer gave no lowest temperature (t_min None):
                        # Daniel's choice of 23/10/2026, a program's choice, not a standard (energy/plant.py)


@dataclass
class Losses:
    """energy.simulate.Losses: the loss chain."""
    transposition: str = "perez"
    albedo: float = 0.20
    use_horizon: bool = True
    use_near: bool = True           # the shadows of the obstacles of the scene
    iam_b0: float = 0.05
    soiling: float = 2.0            # % of the irradiance
    quality: float = 0.0            # %, negative for a gain
    lid: float | None = None        # %; None: the module's first-year loss, else LID_FALLBACK
    mismatch: float = 1.0           # %
    dc_wiring: float = 1.5          # % at STC
    ac_wiring: float = 1.0          # % at the nominal AC power
    unavailability: float = 0.0     # %
    # the electrical effect of the shade of the rows and of the obstacles on the strings (PVsyst: "linear
    # shadings" against "according to module strings", with its "fraction for electrical effect"); the
    # defaults are what the chain did before 23/10/2026: the full effect, always
    electrical_shading: bool = True
    electrical_fraction: float = 100.0     # % of the electrical effect applied


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
    # the maker chosen to size the inverters (R141), remembered for the next time; written since R141 but known to
    # the file's check only from 27/10/2026 (opening a project left it out with a notice)
    inverter_maker: str = ""
    losses: Losses = field(default_factory=Losses)
    thermal: dict = field(default_factory=dict)         # sub-field id -> "open", "close", "insulated"
    t_min: float | None = None                          # None: DESIGN_COLD (energy/plant.conditions)
    strings: Strings = field(default_factory=Strings)
    pvsyst_import: dict = field(default_factory=dict)
    pvsyst_results: dict = field(default_factory=dict)


@dataclass
class ConsumptionSettings:
    """energy.consumption.Consumption: the consumption of the supply point."""
    pod: str = field(default_factory=lambda: registry.legacy_default("consumption", "pod"))
    supply: str = field(default_factory=lambda: registry.legacy_default("consumption", "supply"))  # "domestic", "other_lv", "mv"
    contract_kw: float = field(default_factory=lambda: registry.legacy_default("consumption", "contract_kw"))
    profile: str = field(default_factory=lambda: registry.legacy_default("consumption", "profile"))
    annual_kwh: float = field(default_factory=lambda: registry.legacy_default("consumption", "annual_kwh"))
    bands_kwh: dict = field(default_factory=lambda: registry.legacy_default("consumption", "bands_kwh"))  # yearly kWh, by band code of the calendar
    monthly_kwh: list = field(default_factory=lambda: registry.legacy_default("consumption", "monthly_kwh"))  # 12 values
    monthly_bands_kwh: list = field(default_factory=lambda: registry.legacy_default("consumption", "monthly_bands_kwh"))  # 12 dicts, by band code of the calendar
    measured: list | dict = field(default_factory=lambda: registry.legacy_default("consumption", "measured"))  # {"start", "values"} hourly, or [[iso, kWh], ...]


@dataclass
class EconomicsSettings:
    """energy.economics.Settings, less `defaults` (what the designer has not changed is told by absence)."""
    buy_f1: float = field(default_factory=lambda: registry.legacy_default("economics", "buy_f1"))  # €/kWh, every variable cost of the energy bought, taxes included
    buy_f2: float = field(default_factory=lambda: registry.legacy_default("economics", "buy_f2"))
    buy_f3: float = field(default_factory=lambda: registry.legacy_default("economics", "buy_f3"))
    sell: float = field(default_factory=lambda: registry.legacy_default("economics", "sell"))  # €/kWh, energy fed in (dedicated withdrawal at the zonal price)
    pz: float = field(default_factory=lambda: registry.legacy_default("economics", "pz"))  # €/MWh, the zonal price expected, for the community's tariff
    capex_per_kwp: float = field(default_factory=lambda: registry.legacy_default("economics", "capex_per_kwp"))  # €/kWp, turnkey
    capex_total: float = field(default_factory=lambda: registry.legacy_default("economics", "capex_total"))  # €, when the offer is known (then it wins)
    opex_per_kwp: float = field(default_factory=lambda: registry.legacy_default("economics", "opex_per_kwp"))  # €/kWp a year: maintenance, insurance, monitoring
    inverter_year: int = field(default_factory=lambda: registry.legacy_default("economics", "inverter_year"))
    inverter_per_kw: float = field(default_factory=lambda: registry.legacy_default("economics", "inverter_per_kw"))  # €/kW AC
    years: int = field(default_factory=lambda: registry.legacy_default("economics", "years"))
    discount: float = field(default_factory=lambda: registry.legacy_default("economics", "discount"))  # %
    escalation: float = field(default_factory=lambda: registry.legacy_default("economics", "escalation"))  # %/year, energy prices
    opex_escalation: float = field(default_factory=lambda: registry.legacy_default("economics", "opex_escalation"))  # %/year
    degradation: float = field(default_factory=lambda: registry.legacy_default("economics", "degradation"))  # %/year; negative: from the module's datasheet, else 0.4
    deduction_pct: float = field(default_factory=lambda: registry.legacy_default("economics", "deduction_pct"))  # % of the investment given back as a tax deduction over 10 years
    community: bool = field(default_factory=lambda: registry.legacy_default("economics", "community"))
    shared_pct: float = field(default_factory=lambda: registry.legacy_default("economics", "shared_pct"))  # % of the energy fed in consumed by the community in the same hour
    zone: str = field(default_factory=lambda: registry.legacy_default("economics", "zone"))  # "north", "centre", "other"; "" from the address
    grant_pct: float = field(default_factory=lambda: registry.legacy_default("economics", "grant_pct"))  # % of the investment as a capital grant
    trase: float = field(default_factory=lambda: registry.legacy_default("economics", "trase"))  # €/kWh, a grid-tariff component of low-voltage users: the profile says its source
    battery: dict = field(default_factory=lambda: registry.legacy_default("economics", "battery"))  # a battery of the catalogue; empty: none
    battery_units: int = field(default_factory=lambda: registry.legacy_default("economics", "battery_units"))
    storage_coupling: str = field(default_factory=lambda: registry.legacy_default("economics", "storage_coupling"))  # empty: legacy estimate; ac/dc: explicit AC-bus equivalent
    storage_inverter: dict = field(default_factory=lambda: registry.legacy_default("economics", "storage_inverter"))
    storage_efficiency_pct: float | None = field(default_factory=lambda: registry.legacy_default("economics", "storage_efficiency_pct"))  # AC-bus round trip, entered explicitly
    battery_cost_per_kwh: float = field(default_factory=lambda: registry.legacy_default("economics", "battery_cost_per_kwh"))  # €/kWh usable, installed (indicative)
    export_limit_kw: float = field(default_factory=lambda: registry.legacy_default("economics", "export_limit_kw"))  # kW at the injection point: -1 none, 0 zero export


SECTIONS = {"energy": EnergySettings, "consumption": ConsumptionSettings, "economics": EconomicsSettings}


def _is_number(value) -> bool:
    return value.__class__ in (int, float) and math.isfinite(value)


def initial_values(kls, profile_id: str = "it") -> dict:
    """The initial values the profile gives a section's schema (consumption, economics; none for the energy), over
    the schema's own: as from_dict and the assistant's fields read them."""
    section = {ConsumptionSettings: "consumption", EconomicsSettings: "economics"}.get(kls)
    return registry.get(profile_id).defaults(section) if section else {}


def from_dict(kls, data: dict | None, path: str = "", unknown: list[str] | None = None, *, profile_id: str = "it"):
    """An instance of `kls` from the keys of `data` it knows, each checked against the type of its default
    (ValueError with the path of the key otherwise); the keys it does not know go to `unknown` as paths, and
    are left out. A nested dataclass (the losses, the strings) is read the same way."""
    data = data or {}
    if data.__class__ is not dict:
        raise ValueError(f"{path or kls.__name__}: {data!r} is not a table")
    policy_defaults = initial_values(kls, profile_id)
    known = {f.name: f for f in dataclasses.fields(kls)}
    values = {}
    for key, value in data.items():
        where = f"{path}.{key}" if path else key
        f = known.get(key)
        if f is None:
            if unknown is not None:
                unknown.append(where)
            continue
        default = (policy_defaults[key] if key in policy_defaults else
                   f.default if f.default is not dataclasses.MISSING else f.default_factory())
        if dataclasses.is_dataclass(default):
            values[key] = from_dict(default.__class__, value, where, unknown, profile_id=profile_id)
            continue
        if value is None and default is None:
            continue
        kind = default.__class__
        if kind is bool and value.__class__ is not bool:
            raise ValueError(f"{where}: {value!r} is not a switch")
        if kind is int and value.__class__ is not int:
            raise ValueError(f"{where}: {value!r} is not a whole number")
        if (kind is float or default is None) and not _is_number(value):
            raise ValueError(f"{where}: {value!r} is not a number")
        if kind is str and value.__class__ is not str:
            raise ValueError(f"{where}: {value!r} is not text")
        if kind is dict and value.__class__ is not dict:
            raise ValueError(f"{where}: {value!r} is not a table")
        if kind is list and value.__class__ not in (list, dict if key == "measured" else list):
            raise ValueError(f"{where}: {value!r} is not a list")
        values[key] = value
    return kls(**{**policy_defaults, **values})


def check(section: str, data: dict | None, unknown: list[str], path: str = "", *, profile_id: str = "it") -> None:
    """The dictionary of a section of the project against its schema: ValueError with the path of a value
    of the wrong type; the keys the program does not know appended to `unknown` (under `path`, or the name
    of the section). The inverters and the strings of the energy are lists of tables: each is checked too."""
    where = path or section
    read = from_dict(SECTIONS[section], data, where, unknown, profile_id=profile_id)
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
        sizes = run.get("optimizer_group_sizes", [])
        if (type(sizes) is not list or any(type(n) is not int or n not in (1, 2) for n in sizes)
                or (sizes and sum(sizes) != len(modules))):
            raise ValueError(f"{here}.optimizer_group_sizes: invalid partition of the string")


def known_paths(section: str) -> set[str]:
    """Every path a page may write in a section ("losses.soiling", "dc_ac_ratio"...)."""
    out: set[str] = set()

    def walk(kls, prefix: str) -> None:
        for f in dataclasses.fields(kls):
            scalar = {"str": str, "float": float, "int": int, "bool": bool, "list": list, "dict": dict}.get(f.type)
            default = (scalar() if scalar is not None else None if "| None" in str(f.type) else
                       f.default if f.default is not dataclasses.MISSING else f.default_factory())
            here = f"{prefix}{f.name}"
            out.add(here)
            if dataclasses.is_dataclass(default):
                walk(default.__class__, here + ".")
    walk(SECTIONS[section], "")
    return out
