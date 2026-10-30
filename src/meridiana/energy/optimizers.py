"""Power optimizers (task 22, Daniel on 24/10/2026: «gli ottimizzatori (SolarEdge) dopo»): SolarEdge's architecture,
a power optimizer on every module (or on two in series) that tracks the module's maximum power point, the optimizers'
outputs in series in a string, and an inverter without MPPT that holds the string at a fixed DC voltage (380 V
single-phase, 750 V three-phase on the 230/400 V grid). Every rule is SolarEdge's own, from the documents archived
in the designer's reference (catalogs/SolarEdge, README_INDICE.md), cited with code, date and page:

- the module on its optimizer: the module's power at STC within the optimizer's rated input power, modules with a
  power tolerance up to +5 % allowed; the module's Voc at the lowest temperature within the optimizer's absolute
  maximum input voltage; the module's Isc within the most the optimizer takes (DS-000091-IT p. 2, note 1;
  DS-000105-IT p. 2, note 2; DS-000205-EU p. 2, note 1); two modules in series on one optimizer: their power and their
  Voc add up («multiply all values by 2», Power Optimizer Compatibility with PV Modules v1.0, p. 3); a module whose Imp
  is above the optimizer's continuous input current is clipped (same note, p. 2); a bifacial module counts with its
  front side alone (Bi-facial Modules v1.5, p. 1-2);
- the string: the fewest and the most optimizers (and modules, for the optimizers of two modules), the power it
  carries continuously and the power that may be connected to it, by the kind of inverter (residential S-series:
  DS-000091-IT p. 3; S1000 and S1200: DS-000105-IT p. 3; S1400: DS-000205-EU p. 3; the P-series of before:
  DS-000047-ITA p. 2 and DS-000012-ENG p. 3); with several strings the higher power only when they differ by 2000 W
  at most (the residential and the P-series tables); parallel strings of different lengths or orientations allowed
  (every table); at most 5 optimizers between the shortest and the longest string of an inverter unit (the commercial
  tables); S-series and P-series never in one string (DS-000091-IT p. 3, note 7: one model per inverter here);
- the inverter: its maximum DC power (the modules at STC) from its datasheet, 11 kW at least for the commercial
  inverters (the commercial tables), only 1:1 optimizers on the Home Hub (DS-000279-ROW p. 3); the S1200 on an SE33.3K
  only with the string voltage switched to 850 V, which SetApp offers in a few countries, Italy not among them
  (DS-000105-IT p. 3, note 11; Toggle Fixed String Voltage v1.1, p. 1).

What a string carries beyond its continuous power is cut («potenza troncata», Single String Design Guidelines v1.1,
p. 4); SolarEdge advises against it above 5.7 kW single-phase and 11.25 kW three-phase (p. 5). The strings' power
limits of the tables are what SolarEdge allows without its Designer: «per collegare più potenza STC per stringa,
progettare il progetto usando SolarEdge Designer» (DS-000105-IT p. 3, note 6). No Qt here."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from ..i18n import _, ngettext, number
from . import stringing
from .pedigree import Quantity, Record, Source, Step, computed

# the documents, as the checks cite them (the files are in reference/catalogs/SolarEdge)
RES = "SolarEdge DS-000091-IT (14/09/2026)"
COM = "SolarEdge DS-000105-IT (01/12/2025)"
S1400_DS = "SolarEdge DS-000205-EU (08/01/2024)"
P_RES = "SolarEdge DS-000047-ITA (15/02/2022)"
P_COM = "SolarEdge DS-000012-ENG (29/12/2022)"
SINGLE = "SolarEdge, Single String Design Guidelines v1.1 (08/2026)"
MODULES = "SolarEdge, Power Optimizer Compatibility with PV Modules v1.0 (01/2025)"
MULTIPLE = "SolarEdge, Connecting Power Optimizers to Multiple PV Modules v1.7 (11/2025)"
BIFACIAL = "SolarEdge, Bi-facial Modules with Power Optimizers v1.5 (01/2022)"
TOGGLE = "SolarEdge, Toggle Fixed String Voltage from 750 to 850 Vdc v1.1 (12/2025)"
S1400_NOTE = "SolarEdge, S1400/S1500 inverter inter-compatibility v1.1 (06/2025)"
HUB = "SolarEdge DS-000279-ROW (29/04/2026)"

GRIDS = ("single_phase", "three_phase_short", "three_phase_400", "three_phase_480")
DIFF_W = 2000.0                 # W: several strings at the higher limit only within this of each other
DIFF_OPTIMIZERS = 5             # optimizers between the shortest and the longest string of an inverter unit
MIN_DC_W = 11000.0              # W at STC, the least the commercial inverters should have


def grid_names() -> dict:
    """The columns of SolarEdge's residential table (DS-000091-IT p. 3), as the window says them."""
    return {"single_phase": _("single-phase"), "three_phase_short": _("three-phase, short string"),
            "three_phase_400": _("three-phase, 230/400 V grid"), "three_phase_480": _("three-phase, 277/480 V grid")}


# the optimizer

@dataclass(frozen=True)
class Optimizer:
    """A power optimizer of the catalogue (catalog/data/optimizers_curated.json), as the checks read it."""
    manufacturer: str
    model: str
    rated_w: float                  # W, the rated input DC power: the module (or the two) at STC within it
    voc_max: float                  # V, the absolute maximum input voltage (the module's Voc at the lowest temperature)
    isc_max: float                  # A, the most the connected module's Isc may be
    isc_max_hub: float | None       # A, the same with the SolarEdge Home Hub (16.5 A for the residential S-series)
    i_in_max: float | None          # A, the continuous input current it draws at most (None: not printed)
    i_out_max: float                # A, its maximum output current: the string's
    eta: float                      # its weighted efficiency, 0-1
    per_unit: int                   # the most modules it takes (1 or 2); topology depends on the model
    datasheet: str                  # its datasheet, code and date, as printed
    v_in_min: float | None = None
    v_in_max: float | None = None
    v_out_max: float | None = None
    topology: str = ""              # explicit input wiring; empty for legacy records

    @property
    def name(self) -> str:
        return f"{self.manufacturer} {self.model}".strip()

    @property
    def parallel_inputs(self) -> bool:
        """Dual physical inputs, each with its own Isc rating (DS-000012-ENG p. 3 for P800p)."""
        if self.topology in ("series", "parallel"):
            return self.topology == "parallel"
        return self.manufacturer.casefold() == "solaredge" and self.model.casefold() in {"p485", "p800p", "p860", "p960"}

    @property
    def series(self) -> str:
        """SolarEdge's series: "S" or "P" (never in one string), "" for another maker."""
        if self.manufacturer.casefold() != "solaredge":
            return ""
        return self.model[:1].upper() if self.model[:1].upper() in ("S", "P") else ""

    @classmethod
    def from_record(cls, rec: dict) -> Optimizer:
        def num(key, default=0.0):
            v = rec.get(key)
            return float(v) if v.__class__ in (int, float) and math.isfinite(v) else default
        eta = num("efficiency_weighted_pct") or num("efficiency_peak_pct") or 98.5
        per = rec.get("modules_per_unit")
        hub = rec.get("max_input_isc_home_hub_a")
        current = rec.get("max_input_current_a")
        revision = str(rec.get("datasheet_revision") or "").strip()
        return cls(manufacturer=str(rec.get("manufacturer") or ""), model=str(rec.get("model") or ""),
                   rated_w=num("rated_input_power_w"), voc_max=num("max_input_voltage_v"),
                   isc_max=num("max_input_isc_a"), isc_max_hub=float(hub) if hub.__class__ in (int, float) else None,
                   i_in_max=float(current) if current.__class__ in (int, float) else None,
                   i_out_max=num("max_output_current_a", 15.0), eta=eta / 100.0,
                   per_unit=per if per.__class__ is int and per in (1, 2) else 1,
                   v_in_min=num("mppt_voltage_min_v", None), v_in_max=num("mppt_voltage_max_v", None),
                   v_out_max=num("max_output_voltage_v", None), topology=str(rec.get("input_topology") or ""),
                   datasheet=f"{rec.get('manufacturer', '')} {revision}".strip() if revision else
                   _("datasheet of {name}").format(name=f"{rec.get('manufacturer', '')} {rec.get('model', '')}"))


def module_groups(modules: list, per: int, group_sizes: list[int] | None = None) -> list[list]:
    """Physical optimizer groups in string order, including explicit single modules between pairs.

    A malformed explicit partition is rejected instead of silently changing the wiring.
    """
    if type(per) is not int or per not in (1, 2):
        raise ValueError(_("An optimizer supports one or two modules"))
    if group_sizes:
        if (any(type(n) is not int or not 1 <= n <= per for n in group_sizes)
                or sum(group_sizes) != len(modules)):
            raise ValueError(_("Optimizer groups must partition the string into supported groups"))
        sizes = group_sizes
    else:
        sizes = [min(per, len(modules) - i) for i in range(0, len(modules), per)]
    out, offset = [], 0
    for n in sizes:
        out.append(modules[offset:offset + n])
        offset += n
    return out


# the inverter at a fixed string voltage

@dataclass(frozen=True)
class FixedVoltage:
    """An inverter that holds its strings at a fixed DC voltage and has no MPPT of its own (SolarEdge): the column of
    SolarEdge's tables it is in, its string voltage, its Synergy units (the inverter units of the rules), its maximum
    DC power; what was inferred and not read from the record, said."""
    model: str
    grid: str                       # one of GRIDS
    unit_model: str                 # the column of the commercial tables ("SE25K"...), "" for the residential ones
    v_string: float                 # V
    units: int                      # Synergy units, each an inverter unit for the rules (1 otherwise)
    pac: float                      # W, its rated AC power (the whole inverter)
    p_dc_max: float                 # W, its maximum DC power with the modules at STC (0: unknown)
    pairs: int                      # MC4 input pairs, per unit (0: unknown)
    home_hub: bool
    datasheet: str
    inferred: tuple = ()            # what Meridiana inferred: ("grid", "voltage", "unit model", "units")
    p_dc_max_unit: float = 0.0      # W, the maximum DC power of one Synergy unit at STC (0: unknown)

    @property
    def unit_pac(self) -> float:
        return self.pac / max(1, self.units)


SYNERGY = {"SE50K": (2, "SE25K"), "SE66.6K": (2, "SE33.3K"), "SE90K": (3, "SE30K"), "SE100K": (3, "SE33.3K")}
# W, «Maximum DC Power (Module STC) Inverter / Synergy Unit», the Synergy unit's figure as printed (DS-000297-EU,
# 05/04/2026, p. 1): SE100K's 58,300 W is not 175,000 / 3, so the figure is read, never divided
SYNERGY_UNIT_DC = {"SE50K": 43750.0, "SE66.6K": 58275.0, "SE90K": 52500.0, "SE100K": 58300.0}
SYNERGY_DS = "SolarEdge DS-000297-EU (05/04/2026)"
COMMERCIAL = ("SE15K", "SE16K", "SE17K", "SE20K", "SE25K", "SE27.6K", "SE30K", "SE33.3K", "SE40K")
# the string voltage of a commercial column: the continuous power per string over the optimizer's output current of
# the tables (SE27.6K 13950 W / 18 A = 775 V; SE30K and SE40K 15300 W / 18 A = 850 V), the others 750 V as the
# three-phase datasheets print it
COLUMN_VOLTAGE = {"SE27.6K": 775.0, "SE30K": 850.0, "SE40K": 850.0}
GRID_VOLTAGE = {"single_phase": 380.0, "three_phase_short": 375.0, "three_phase_400": 750.0, "three_phase_480": 850.0}


def _kw_model(model: str) -> str:
    """"SE33.3K" from a model's name ("SE33.3K", "SE 33.3K-RW00...", "SE100K"); "" when it is not one."""
    m = re.search(r"SE\s*(\d+(?:\.\d+)?)\s*K", model or "", re.IGNORECASE)
    return f"SE{m.group(1)}K" if m else ""


def is_fixed_voltage(rec: dict | None) -> bool:
    """Whether an inverter's record is one at a fixed string voltage: said by the record, or a SolarEdge inverter
    without an MPPT window (the records of the catalogue before task 22, kept in the projects)."""
    if not rec:
        return False
    if rec.get("dc_architecture") == "fixed_string_voltage":
        return True
    return (str(rec.get("manufacturer") or "").casefold() == "solaredge" and not rec.get("mppt_voltage_min_v")
            and not rec.get("mppt_count"))


def fixed_voltage(rec: dict | None) -> FixedVoltage | None:
    """The inverter of `rec` as the optimizers' rules read it; None for an inverter with MPPT."""
    if not is_fixed_voltage(rec):
        return None
    inferred = []
    model = str(rec.get("model") or "")
    grid = rec.get("optimizer_grid")
    if grid not in GRIDS:
        inferred.append("grid")
        if rec.get("phases") == 1:
            grid = "single_phase"
        elif float(rec.get("ac_voltage_nominal_v") or 400) >= 450:
            grid = "three_phase_480"
        else:
            grid = "three_phase_400"
    kw = _kw_model(model)
    units = rec.get("synergy_units")
    unit_model = rec.get("optimizer_unit_model") or ""
    if units.__class__ is not int or units < 1:
        units = SYNERGY.get(kw, (1, ""))[0]
        if units > 1:
            inferred.append("units")
    if not unit_model and grid != "single_phase":
        unit_model = SYNERGY[kw][1] if kw in SYNERGY else (kw if kw in COMMERCIAL else "")
        if unit_model:
            inferred.append("unit model")
    voltage = rec.get("string_voltage_v")
    if voltage.__class__ not in (int, float) or voltage <= 0:
        inferred.append("voltage")
        voltage = COLUMN_VOLTAGE.get(unit_model) or rec.get("dc_voltage_nominal_v") or GRID_VOLTAGE[grid]
    pairs = rec.get("dc_input_pairs")
    series = f"{rec.get('series') or ''} {model}"
    p_dc_max = float(rec.get("dc_power_max_w") or 0.0)
    unit_dc = rec.get("dc_power_max_unit_w")
    if unit_dc.__class__ not in (int, float) or unit_dc <= 0:
        unit_dc = SYNERGY_UNIT_DC.get(kw, 0.0) if int(units) > 1 else p_dc_max
    revision = str(rec.get("datasheet_revision") or "").strip()
    return FixedVoltage(model=model, grid=grid, unit_model=unit_model, v_string=float(voltage), units=int(units),
                        pac=float(rec.get("ac_power_nominal_w") or rec.get("pac") or 0.0),
                        p_dc_max=p_dc_max, p_dc_max_unit=float(unit_dc),
                        pairs=pairs if pairs.__class__ is int and pairs > 0 else 0,
                        home_hub="home hub" in series.casefold(),
                        datasheet=f"{rec.get('manufacturer', '')} {revision}".strip() if revision else
                        _("datasheet of {name}").format(name=f"{rec.get('manufacturer', '')} {model}"),
                        inferred=tuple(inferred))


# the rules of the strings

@dataclass(frozen=True)
class Rules:
    """SolarEdge's rules of the strings for one optimizer on one kind of inverter (one column of a table)."""
    opt_min: int
    opt_max: int
    p_cont: float                   # W, the most a string carries continuously (I_out x U_string)
    p_one: float                    # W at STC connected per string, with fewer than `many` strings
    p_many: float                   # W at STC connected per string, with `many` strings or more
    many: int = 2
    mod_min: int = 0                # the fewest and the most modules (the optimizers of two modules), 0: no rule
    mod_max: int = 0
    diff_w: float = 0.0             # the higher limits only with the strings within this of each other (0: no rule)
    diff_opt: int = 0               # the most optimizers between the shortest and the longest string of a unit
    min_dc: float = 0.0             # W at STC the inverter should have at least
    commercial: bool = False        # the commercial tables: more power with SolarEdge Designer
    source: str = ""                # the document and its page
    column: str = ""                # the table's column, in words
    warnings: tuple = ()            # (key, label, detail, source) said whatever the strings


# the residential tables: (fewest for the optimizers of the long and of the short modules, most, continuous power,
# what may be connected above the continuous power: (with one string, with `many`), whether an inverter whose rated
# AC power is within the continuous power takes up to its own maximum DC power)
RES_S = {"single_phase": (8, 6, 25, 5700.0, (6000.0, 6800.0), True),
         "three_phase_short": (9, 8, 20, 5625.0, None, True),
         "three_phase_400": (16, 14, 50, 11250.0, (13500.0, 13500.0), True),
         "three_phase_480": (18, 14, 50, 12750.0, (15000.0, 15000.0), True)}
RES_S_LONG = ("S440", "S500")                   # DS-000091-IT p. 3: the fewest 8, 9, 16, 18; S500B and S650B fewer
RES_P = {"single_phase": (8, 6, 25, 5700.0, (5700.0, 5700.0), True),
         "three_phase_short": (9, 8, 20, 5625.0, (5625.0, 5625.0), True),
         "three_phase_400": (16, 14, 50, 11250.0, (13500.0, 13500.0), False),
         "three_phase_480": (18, 14, 50, 12750.0, (15000.0, 15000.0), False)}
RES_P_LONG = ("P370", "P401", "P500")
# the commercial tables, by optimizer and column: (fewest optimizers, fewest modules, most optimizers, most modules,
# continuous power, connected with one string or fewer than `many`, connected with `many` or more, many)
COM_S = {
    "S1000": {"SE25K": (14, 27, 30, 60, 13500.0, 15750.0, 18500.0, 2),
              "SE27.6K": (14, 27, 30, 60, 13950.0, 16200.0, 18950.0, 2),
              "SE30K": (15, 29, 30, 60, 15300.0, 17550.0, 20300.0, 2),
              "SE33.3K": (14, 27, 30, 60, 13500.0, 15750.0, 18500.0, 3),
              "SE40K": (15, 29, 30, 60, 15300.0, 17550.0, 20300.0, 3)},
    "S1200": {"SE25K": (14, 27, 30, 60, 15000.0, 17250.0, 20000.0, 2),
              "SE27.6K": (14, 27, 30, 60, 15500.0, 17750.0, 20500.0, 2),
              "SE30K": (15, 29, 30, 60, 17000.0, 19250.0, 23000.0, 2),
              "SE33.3K": (15, 29, 30, 60, 17000.0, 19250.0, 23000.0, 2),
              "SE40K": (15, 29, 30, 60, 17000.0, 19250.0, 23000.0, 3)},
    "S1400": {"SE20K": (14, 27, 30, 60, 18000.0, 20250.0, 28000.0, 2),
              "SE25K": (14, 27, 30, 60, 18000.0, 20250.0, 28000.0, 2),
              "SE27.6K": (14, 27, 30, 60, 18600.0, 20850.0, 28600.0, 2),
              "SE30K": (15, 29, 30, 60, 20400.0, 22650.0, 30400.0, 2),
              "SE33.3K": (14, 27, 30, 60, 18000.0, 20250.0, 28000.0, 2),
              "SE40K": (15, 29, 30, 60, 20400.0, 22650.0, 30400.0, 2)}}
COM_S_SOURCE = {"S1000": COM, "S1200": COM, "S1400": S1400_DS}
P_COM_TABLE = {"SE16K": (14, 27, 30, 60, 13500.0, 15750.0, 18500.0, 2),
               "SE17K": (14, 27, 30, 60, 13500.0, 15750.0, 18500.0, 2),
               "SE25K": (14, 27, 30, 60, 13500.0, 15750.0, 18500.0, 2),
               "SE27.6K": (14, 27, 30, 60, 13950.0, 16200.0, 18950.0, 2),
               "SE30K": (15, 29, 30, 60, 15300.0, 17550.0, 20300.0, 2),
               "SE33.3K": (14, 27, 30, 60, 13500.0, 15750.0, 18500.0, 3),
               "SE40K": (14, 27, 30, 60, 15300.0, 17550.0, 20300.0, 3)}
P_COM_MODELS = ("P800P", "P850", "P950", "P1100")
SINGLE_MODULE_NOTE = {"S1000": "2", "S1200": "2", "S1400": "9"}     # the note of the rule, by datasheet


def _residential(opt: Optimizer, inv: FixedVoltage) -> Rules:
    p_series = opt.series == "P"
    table, long_models = (RES_P, RES_P_LONG) if p_series else (RES_S, RES_S_LONG)
    lo_long, lo_short, hi, cont, over, ac_rule = table[inv.grid]
    lo = lo_long if opt.model.upper() in long_models else lo_short
    if p_series and inv.grid == "three_phase_400" and lo == 14 and inv.unit_model == "SE30K":
        lo = 15                                         # DS-000047-ITA p. 2: «14 (15 con SE30K)»
    max_dc = inv.p_dc_max or math.inf
    if over is None or (ac_rule and inv.unit_pac <= cont):
        one = many_w = max_dc                           # «secondo la potenza CC massima in ingresso dell'inverter»
    else:
        one, many_w = over
        if inv.grid == "single_phase" and not p_series and inv.unit_pac < 8000.0:
            many_w = one                                # 6800 W only with 8000 W of AC or more and two strings
    source = (f"{P_RES}, p. 2" if p_series else f"{RES}, p. 3")
    return Rules(opt_min=lo, opt_max=hi, p_cont=cont, p_one=one, p_many=many_w, many=2,
                 diff_w=DIFF_W if (not p_series or inv.grid in ("three_phase_400", "three_phase_480")) else 0.0,
                 source=source, column=grid_names()[inv.grid])


def rules_for(opt: Optimizer, inv: FixedVoltage) -> tuple[Rules | None, str]:
    """The rules of `opt`'s strings on `inv`, or None with the reason in words (an optimizer SolarEdge's tables do not
    put with that inverter, or of another maker)."""
    if opt.manufacturer.casefold() != "solaredge":
        return None, _("{name}: only SolarEdge's power optimizers work with a SolarEdge inverter").format(
            name=opt.name)
    model = opt.model.upper()
    warnings: list = []
    if model in COM_S or model in P_COM_MODELS:
        table = COM_S.get(model) if model in COM_S else P_COM_TABLE
        if model == "P1100":
            table = {k: v for k, v in table.items() if k not in ("SE16K", "SE17K")}     # «SE25K & larger»
        column = inv.unit_model
        if column == "SE20K" and model != "S1400":
            column = ""
        row = table.get(column)
        if row is None:
            return None, _("{name} is in SolarEdge's tables for the commercial three-phase inverters only ({models}): "
                           "not for {inverter}").format(name=opt.name, models=", ".join(table), inverter=inv.model)
        lo, mlo, hi, mhi, cont, one, many_w, many = row
        source = f"{COM_S_SOURCE.get(model, P_COM)}, p. 3"
        if model == "S1200" and column == "SE33.3K":
            warnings.append(("toggle", _("S1200 on an SE33.3K: the string voltage at 850 V"),
                             _("SolarEdge allows it only with the fixed string voltage switched from 750 to 850 V in "
                               "SetApp, offered in Australia, Brazil, India, Israel, South Africa, Thailand and Taiwan: "
                               "ask SolarEdge for Italy, or use S1000 or S1400"),
                             f"{COM}, p. 3, note 11; {TOGGLE}, p. 1"))
        if model == "S1400":
            warnings.append(("fuses", _("S1400: an inverter without DC fuses"),
                             _("Its 24 A of output are too many for the inverters with integrated 25 or 30 A DC fuses "
                               "(part numbers ending in A4, B4, C4, D4, E4, F4, L4, S4, X4, Z4): they take neutral "
                               "links instead"), f"{S1400_DS}, p. 2, note 4; {S1400_NOTE}, p. 1"))
        return Rules(opt_min=lo, opt_max=hi, mod_min=mlo, mod_max=mhi, p_cont=cont, p_one=one, p_many=many_w,
                     many=many, diff_w=DIFF_W if model in P_COM_MODELS else 0.0, diff_opt=DIFF_OPTIMIZERS,
                     min_dc=MIN_DC_W, commercial=True, source=source,
                     column=_("{model} (or a Synergy unit of the same power)").format(model=column),
                     warnings=tuple(warnings)), ""
    if model in ("S440", "S500", "S500B", "S650B") or model in ("P370", "P401", "P404", "P485", "P500", "P505",
                                                                  "P601"):
        return _residential(opt, inv), ""
    return None, _("{name}: Meridiana does not know SolarEdge's string rules for it").format(name=opt.name)


def connected_limit(r: Rules, strings: int, spread_w: float) -> tuple[float, str]:
    """The most a string may have connected (W at STC) with `strings` strings on the inverter unit whose powers differ
    by `spread_w` at most, and why in words when the higher limit does not apply."""
    base = r.p_many if strings >= r.many else r.p_one
    if r.diff_w and strings > 1 and spread_w > r.diff_w and base > r.p_cont:
        return r.p_cont, _("the strings differ by {d} W, more than {lim} W: each within its continuous power").format(
            d=number(spread_w, 0, grouping=True), lim=number(r.diff_w, 0, grouping=True))
    return base, ""


def optimizer_count(modules: int, per: int) -> int:
    """The optimizers of a string of `modules` with `per` modules each: one may take a single module (DS-000105-IT
    p. 3, note 2)."""
    return -(-max(0, modules) // max(1, per))


# the checks

def _check(key, label, ok, detail, level="", source="") -> stringing.Check:
    return stringing.Check(key, label, bool(ok), detail, level, source)


def module_checks(module, opt: Optimizer, per: int, t_min: float | None, inv: FixedVoltage | None) -> list:
    """The module on its optimizer: power, Voc at the lowest temperature, Isc, Imp (stringing.Check, with `source`).
    Series inputs add voltage; the P800p/P485 dual parallel inputs keep each module's Voc and per-input Isc.
    Power is combined in either topology. Branch cables on serial-input models are not modelled here."""
    out = []
    k = max(1, per)
    note = f"{opt.datasheet}, p. {3 if opt.model.casefold() == 'p800p' else 2}"
    p = k * module.pmax
    out.append(_check("opt_power", _("Module power within the optimizer's rated input power"), p <= opt.rated_w + 1e-6,
                      (_("{n} x {p} W = {t} W of {r} W (modules with a power tolerance up to +5 % allowed)") if k > 1
                       else _("{t} W of {r} W (modules with a power tolerance up to +5 % allowed)")).format(
                          n=k, p=number(module.pmax, 0), t=number(p, 0), r=number(opt.rated_w, 0)), "",
                      note + (f"; {MODULES}, p. 3" if k > 1 else "")))
    voc = (1 if opt.parallel_inputs else k) * stringing.ku(module, t_min) * module.voc
    out.append(_check("opt_voc", _("Module Voc at the lowest temperature within the optimizer's input"),
                      voc <= opt.voc_max + 1e-6,
                      _("{v} V at {t} °C of {lim} V").format(v=number(voc, 1), t=number(t_min, 0) if t_min is not None
                                                            else "?", lim=number(opt.voc_max, 0)),
                      "", f"{note}; {MODULES}, p. 3"))
    limit = opt.isc_max_hub if (inv is not None and inv.home_hub and opt.isc_max_hub) else opt.isc_max
    front = getattr(module, "bifaciality", 0.0) > 0
    out.append(_check("opt_isc", _("Module Isc within the optimizer's input"), module.isc <= limit + 1e-6,
                      (_("{i} A of {lim} A (the front side alone)") if front else _("{i} A of {lim} A")).format(
                          i=number(module.isc, 2), lim=number(limit, 1)),
                      "", note + (f"; {BIFACIAL}, p. 2" if front else "")))
    if opt.i_in_max:
        over = module.imp > opt.i_in_max
        out.append(_check("opt_imp", _("Module Imp within the optimizer's continuous input current"), True,
                          (_("{i} A of {lim} A: the optimizer clips the current and loses a little power") if over
                           else _("{i} A of {lim} A")).format(i=number(module.imp, 2), lim=number(opt.i_in_max, 1)),
                          "warn" if over else "ok", f"{MODULES}, p. 2"))
    return out


@dataclass
class OptimizedPlan(stringing.StringPlan):
    """The checks of a string of optimizers: in place of the voltages, how many optimizers and how much power against
    SolarEdge's limits (the window's strip says them, R57)."""
    optimizers: int = 0
    power_w: float = 0.0
    limit_w: float = 0.0            # W at STC the string may have connected here
    continuous_w: float = 0.0       # W it carries continuously
    opt_range: tuple = (0, 0)
    mod_range: tuple = (0, 0)
    v_string: float = 0.0
    optimizer: str = ""
    per: int = 1
    limit_why: str = ""


def string_plan(module, opt: Optimizer, per: int, inv: FixedVoltage, rules: Rules, modules: int, strings: int,
                spread_w: float, t_min: float | None, t_min_source: Source | None = None,
                power_w: float | None = None, group_sizes: list[int] | None = None) -> OptimizedPlan:
    """The checks of one string of `modules` modules on optimizers `opt` (`per` modules each) on an inverter unit with
    `strings` strings whose powers differ by `spread_w`: the module on its optimizer, the optimizers and the modules
    against the fewest and the most, the power against what may be connected and what is carried; each check with its
    source, the steps in the record. `power_w`: the string's power at STC when its modules are not all `module`."""
    groups = module_groups(list(range(modules)), per, group_sizes)
    n_opt = len(groups)
    power = float(power_w) if power_w is not None else modules * module.pmax
    limit, why = connected_limit(rules, strings, spread_w)
    rec = Record(_("Strings with power optimizers: SolarEdge's design rules"))
    out = OptimizedPlan(n_series=modules, strings_per_mppt=[strings], record=rec, optimizers=n_opt, power_w=power,
                        limit_w=limit, continuous_w=rules.p_cont, opt_range=(rules.opt_min, rules.opt_max),
                        mod_range=(rules.mod_min, rules.mod_max), v_string=inv.v_string, optimizer=opt.name, per=per,
                        limit_why=why, n_series_min=rules.opt_min, n_series_max=rules.opt_max)
    for occupancy in sorted({len(g) for g in groups}):
        out.checks += module_checks(module, opt, occupancy, t_min, inv)
    out.checks.append(_check("opt_count", _("Optimizers in the string within SolarEdge's range"),
                             rules.opt_min <= n_opt <= rules.opt_max,
                             _("{n}, from {lo} to {hi} on this inverter").format(n=n_opt, lo=rules.opt_min,
                                                                                  hi=rules.opt_max),
                             "", rules.source))
    if rules.mod_min:
        out.checks.append(_check("opt_modules", _("Modules in the string within SolarEdge's range"),
                                 rules.mod_min <= modules <= rules.mod_max,
                                 _("{n}, from {lo} to {hi}").format(n=modules, lo=rules.mod_min, hi=rules.mod_max),
                                 "", rules.source))
    singles = sum(1 for g in groups if len(g) == 1)
    if per == 2 and rules.commercial and 1 < singles < n_opt:
        # «a power optimizer may be connected to a single PV module if each one is, or if it is the only one in the
        # string» (DS-000105-IT p. 3, note 2; DS-000205-EU p. 3, note 9; DS-000012-ENG p. 3, note 6)
        note = SINGLE_MODULE_NOTE.get(opt.model.upper(), "6")
        out.checks.append(_check("opt_singles", _("At most one optimizer with a single module in the string"), False,
                                 _("{n} optimizers with a single module: either one, or all of them").format(
                                     n=singles), "", f"{rules.source}, note {note}"))
    ok = power <= limit + 1e-6
    detail = _("{p} W of {lim} W at STC").format(p=number(power, 0, grouping=True),
                                                 lim=number(limit, 0, grouping=True) if math.isfinite(limit) else "∞")
    if why:
        detail += f" ({why})"
    if not ok and rules.commercial:
        detail += "; " + _("SolarEdge Designer may allow more for the site")
    out.checks.append(_check("opt_string_power", _("String power within what SolarEdge allows"), ok, detail,
                             "warn" if (not ok and rules.commercial) else "", rules.source))
    if power > rules.p_cont:
        # the advice is the residential optimizers' (the single string guidelines cover the S- and P-series for
        # homes): the commercial tables allow more connected than carried on purpose
        advised = inv.unit_pac > rules.p_cont and not rules.commercial
        out.checks.append(_check(
            "opt_continuous", _("String power within what it carries continuously"), True,
            (_("{p} W of {c} W: the power above is cut at the peaks; SolarEdge advises two strings") if advised else
             _("{p} W of {c} W: the power above is cut at the peaks, as SolarEdge's table allows") if rules.commercial
             else _("{p} W of {c} W: the power above is cut at the peaks, within the inverter's own limit")).format(
                p=number(power, 0, grouping=True), c=number(rules.p_cont, 0, grouping=True)),
            "warn" if advised else "info", f"{SINGLE}, p. 4-5"))
    for key, label, text, source in rules.warnings:
        out.checks.append(_check(f"opt_{key}", label, True, text, "warn", source))
    _plan_steps(rec, module, opt, per, inv, rules, modules, n_opt, power, limit, t_min, t_min_source)
    return out


def _plan_steps(rec: Record, module, opt: Optimizer, per: int, inv: FixedVoltage, rules: Rules, modules: int,
                n_opt: int, power: float, limit: float, t_min, t_min_source) -> None:
    ds = Source("data", _("datasheet of {name}").format(name=opt.name), opt.datasheet)
    table = Source("data", _("SolarEdge's design table: {column}").format(column=rules.column), rules.source)
    m_src = module.source
    t_src = t_min_source or Source("default", _("Meridiana's prudent default"))
    rec.add(Step("opt_module", _("The module on its optimizer"),
                 (r"k\,P_{STC} \leq P_{opt},\quad K_U\,U_{OC} \leq U_{in,max},\quad I_{SC} \leq I_{SC,max}"
                  if opt.parallel_inputs else
                  r"k\,P_{STC} \leq P_{opt},\quad k\,K_U\,U_{OC} \leq U_{in,max},\quad I_{SC} \leq I_{SC,max}"),
                 (_("The modules use separate parallel input connectors: their powers add, their voltages do not. "
                    "The datasheet's short-circuit current limit applies to each physical input.") if opt.parallel_inputs else
                  _("Each optimizer tracks the maximum power point of its module (or of its two modules in series, k = "
                   "2): the module's power at STC within the optimizer's rated input power, its open-circuit voltage "
                   "on the coldest morning within the optimizer's absolute maximum input voltage, its short-circuit "
                   "current within what the optimizer takes; a bifacial module with its front side alone.")),
                 [Quantity("k", _("modules on an optimizer"), per, "", Source("input", _("chosen by the designer")), 0),
                  Quantity(r"P_{STC}", _("module power at STC"), module.pmax, "W", m_src, 0),
                  Quantity(r"P_{opt}", _("optimizer's rated input power"), opt.rated_w, "W", ds, 0),
                  Quantity(r"U_{OC}", _("open-circuit voltage of the module"), module.voc, "V", m_src, 2),
                  Quantity(r"T_{min}", _("lowest temperature of the site"), t_min if t_min is not None else _("unknown"),
                           "°C", t_src, 1),
                  Quantity(r"U_{in,max}", _("optimizer's absolute maximum input voltage"), opt.voc_max, "V", ds, 0),
                  Quantity(r"I_{SC}", _("short-circuit current of the module"), module.isc, "A", m_src, 2),
                  Quantity(r"I_{SC,max}", _("optimizer's maximum module Isc"), opt.isc_max, "A", ds, 1)],
                 None, f"{opt.datasheet}, p. 2; {MODULES}, p. 2-3; {BIFACIAL}, p. 1-2"))
    rec.add(Step("opt_string", _("The string of optimizers"),
                 r"N_{opt} = \lceil N_{mod} / k \rceil,\quad N_{min} \leq N_{opt} \leq N_{max},\quad "
                 r"P_{string} = N_{mod}\,P_{STC} \leq P_{max},\quad P_{cont} = I_{out,max}\,U_{string}",
                 _("The optimizers' outputs in series make the string; the inverter holds it at its fixed voltage, so "
                   "the string's current is its power over that voltage, at most the optimizers' output current. "
                   "SolarEdge's table for this inverter gives the fewest and the most optimizers, the power the string "
                   "carries continuously and the power that may be connected to it (with several strings the higher "
                   "one only when they differ by 2000 W at most, where the table says so)."),
                 [Quantity(r"N_{mod}", _("modules in the string"), modules, "", Source("input", _("drawn by the "
                                                                                                "designer")), 0),
                  Quantity(r"N_{min}", _("fewest optimizers"), rules.opt_min, "", table, 0),
                  Quantity(r"N_{max}", _("most optimizers"), rules.opt_max, "", table, 0),
                  Quantity(r"U_{string}", _("inverter's fixed string voltage"), inv.v_string, "V",
                           Source("default" if "voltage" in inv.inferred else "data",
                                  _("inferred from the inverter's table") if "voltage" in inv.inferred else
                                  _("datasheet of {name}").format(name=inv.model), inv.datasheet), 0),
                  Quantity(r"I_{out,max}", _("optimizer's maximum output current"), opt.i_out_max, "A", ds, 1),
                  Quantity(r"P_{cont}", _("power a string carries continuously"), rules.p_cont, "W", table, 0),
                  Quantity(r"P_{max}", _("power that may be connected to a string here"),
                           limit if math.isfinite(limit) else _("the inverter's maximum DC power"), "W", table, 0)],
                 Quantity(r"P_{string}", _("power of the string at STC"), power, "W", computed(""), 0),
                 f"{rules.source}; {SINGLE}, p. 1-5"))


def unit_checks(name: str, inv: FixedVoltage, opt: Optimizer | None, per: int, powers: list[float],
                optimizers: list[int], total_dc_w: float, rules: Rules | None) -> list:
    """The checks of an inverter unit (a Synergy unit, or the inverter): the optimizers' difference between its
    strings, the strings on its input pairs, a Synergy unit's own maximum DC power; and of the whole inverter
    (`total_dc_w`, given only once): its maximum DC power, the least of the commercial ones, 1:1 on the Home Hub."""
    out = []
    if inv.units > 1 and inv.p_dc_max_unit and powers:
        unit_dc = sum(powers)
        out.append(_check("opt_unit_dc_max", _("{name}: DC power within the Synergy unit's maximum").format(name=name),
                          unit_dc <= inv.p_dc_max_unit + 1e-6,
                          _("{p} W of {lim} W at STC").format(p=number(unit_dc, 0, grouping=True),
                                                              lim=number(inv.p_dc_max_unit, 0, grouping=True)),
                          "", f"{SYNERGY_DS}, p. 1" if _kw_model(inv.model) in SYNERGY_UNIT_DC else inv.datasheet))
    if rules is not None and rules.diff_opt and len(optimizers) > 1:
        gap = max(optimizers) - min(optimizers)
        out.append(_check("opt_gap", _("{name}: strings within {n} optimizers of each other").format(
            name=name, n=rules.diff_opt), gap <= rules.diff_opt,
            _("from {lo} to {hi} optimizers").format(lo=min(optimizers), hi=max(optimizers)), "", rules.source))
    if inv.pairs and len(powers) > inv.pairs:
        out.append(_check("opt_pairs", _("{name}: strings on its DC inputs").format(name=name), True,
                          ngettext("{n} string on {m} input pair: the others in parallel outside the inverter",
                                   "{n} strings on {m} input pairs: the others in parallel outside the inverter",
                                   len(powers)).format(n=len(powers), m=inv.pairs), "info",
                          _("datasheet of {name}").format(name=inv.model) + f" ({inv.datasheet})"))
    if total_dc_w > 0:
        if inv.p_dc_max:
            out.append(_check("opt_dc_max", _("{name}: DC power within the inverter's maximum").format(name=name),
                              total_dc_w <= inv.p_dc_max + 1e-6,
                              _("{p} W of {lim} W at STC").format(p=number(total_dc_w, 0, grouping=True),
                                                                  lim=number(inv.p_dc_max, 0, grouping=True)),
                              "", f"{inv.datasheet}, p. 2"))
        if rules is not None and rules.min_dc and total_dc_w < rules.min_dc:
            out.append(_check("opt_min_dc", _("{name}: at least {p} kW at STC").format(
                name=name, p=number(rules.min_dc / 1000, 0)), False,
                _("{p} W: SolarEdge's table asks for {lim} W at least").format(
                    p=number(total_dc_w, 0, grouping=True), lim=number(rules.min_dc, 0, grouping=True)),
                "warn", rules.source))
        if inv.home_hub and per > 1:
            out.append(_check("opt_hub", _("{name}: only 1:1 optimizers on the Home Hub").format(name=name), False,
                              _("two modules on an optimizer are not allowed here"), "", f"{HUB}, p. 3"))
    return out


# the optimizer Meridiana proposes when none is chosen

RESIDENTIAL_ORDER = ("S440", "S500", "S500B", "S650B")
COMMERCIAL_ORDER = ("S1000", "S1400", "S1200")


def suggest(module, inv: FixedVoltage, t_min: float | None) -> tuple[dict, int] | None:
    """The current SolarEdge optimizer (S-series) for `module` on `inv` when the designer chose none: on a commercial
    inverter two modules on an S1000, S1400 or S1200 (the S1200 last: on an SE33.3K it needs 850 V), else one on the
    smallest residential S-series that takes the module; the record and the modules on each. None when none fits."""
    from .. import catalog
    records = {r.get("model"): r for r in catalog.search("optimizers", manufacturer="SolarEdge", limit=None)}
    options = []
    if inv.unit_model and inv.grid != "single_phase":
        options += [(m, 2) for m in COMMERCIAL_ORDER]
    options += [(m, 1) for m in RESIDENTIAL_ORDER]
    for model, per in options:
        rec = records.get(model)
        if rec is None:
            continue
        opt = Optimizer.from_record(rec)
        rules, _why = rules_for(opt, inv)
        if rules is None or any(rule[0] == "toggle" for rule in rules.warnings):
            continue
        if all(c.level != "fail" for c in module_checks(module, opt, per, t_min, inv)):
            return rec, per
    return None


@dataclass
class Choice:
    """The optimizers of an inverter: chosen by the designer or suggested by Meridiana."""
    optimizer: Optimizer
    record: dict
    per: int
    suggested: bool = False
    rules: Rules | None = None
    why: str = ""                   # why there are no rules
    notes: list = field(default_factory=list)


def choice(entry: dict, module, inv: FixedVoltage, t_min: float | None) -> Choice | None:
    """The optimizers of an entry of energy["inverters"] (its "optimizer" record and "per_optimizer"), or the ones
    Meridiana proposes for its module; None when none fits."""
    rec = entry.get("optimizer") if entry.get("optimizer").__class__ is dict and entry.get("optimizer") else None
    suggested = rec is None
    per = entry.get("per_optimizer")
    if rec is None:
        found = suggest(module, inv, t_min) if module is not None else None
        if found is None:
            return None
        rec, per = found
    opt = Optimizer.from_record(rec)
    per = per if per.__class__ is int and 1 <= per <= opt.per_unit else (opt.per_unit if not suggested else 1)
    rules, why = rules_for(opt, inv)
    return Choice(opt, rec, per, suggested, rules, why)
