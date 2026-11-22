"""Minimal physical calculation policy, without national authorisation or conformity claims."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, fields
import numpy as np
from meridiana.i18n import _, N_
from meridiana.core.rules.profiles import common
from meridiana.core.rules.types import Facts, FirePolicy, InputField, Item, PolicyFlows, StandardRef

SCOPE = N_("Generic IEC profile: physical calculations and declared data; local obligations and regulatory conformity are not assessed")
ELECTRICAL_SCOPE = N_("Checks limited to physical data; regulatory conformity is not assessed")
MISSING = N_("Missing declared data: {data}")


def _empty_values(cls):
    """Read the shared schema's types, without running a legacy default factory."""
    constructors = {"str": str, "float": float, "int": int, "bool": bool, "dict": dict, "list": list}
    result = {}
    for item in fields(cls):
        if item.name == "defaults":
            continue
        kind = str(item.type)
        result[item.name] = None if "None" in kind else constructors[kind.split(" | ")[0]]()
    return result


@dataclass(frozen=True)
class GenericCalendar:
    codes: tuple[str, ...] = ("ALL",)
    default_timezone: str = "UTC"
    source: str = ""

    def holidays(self, year):
        return set()

    def band_of(self, index, timezone):
        return np.full(len(index), "ALL")


@dataclass(frozen=True)
class GenericConsumption:
    def guess(self, ctx):
        from meridiana.core.energy.consumption import Guess
        return Guess("uniform", "", 0.0, 0.0, _("No consumption data supplied; consumption is zero"))

    def valid_supply_id(self, value):
        return isinstance(value, str)

    def shape(self, profile, index):
        import pandas as pd
        return pd.Series(np.ones(len(index)), index=index)

    def profiles(self):
        return {"uniform": ()}

    def names(self):
        return {"uniform": _("Uniform declared consumption")}

    def starting_kwh(self):
        return {"uniform": 0.0}

    def prepare(self, consumption):
        result = deepcopy(consumption)
        def total(values):
            return float(values.get("ALL") or 0) if "ALL" in values else sum(float(v or 0) for v in values.values())
        if result.bands_kwh:
            result.bands_kwh = {"ALL": total(result.bands_kwh)}
        if result.monthly_bands_kwh:
            result.monthly_bands_kwh = [{"ALL": total(row)} for row in result.monthly_bands_kwh]
        result.profile = "uniform"
        return result

    def has_data(self, consumption):
        c = self.prepare(consumption)
        return bool(c.measured or c.annual_kwh > 0 or any(c.monthly_kwh) or any(c.bands_kwh.values())
                    or any(any(row.values()) for row in c.monthly_bands_kwh))

    def follows_production(self, consumption, ctx):
        return False

    def text(self, key):
        return {"spread": _("Declared annual or monthly totals are distributed uniformly over the actual hours; an imported hourly curve is preserved.")}[key]


@dataclass(frozen=True)
class GenericEconomy:
    regimes: tuple[str, ...] = ("ordinary",)

    def prices(self, settings):
        return {"ALL": settings.buy_f1}

    def zone_from_address(self, address):
        return ""

    def tip(self, pz_eur_mwh, power_kw, zone, grant_pct=0.0):
        return np.zeros_like(pz_eur_mwh, dtype=float) if isinstance(pz_eur_mwh, np.ndarray) else 0.0

    def flows(self, settings, self_by_band, export_y, p_stc_kw, address, capex):
        scale = np.array([(1 + settings.escalation / 100) ** year for year in range(len(export_y))])
        return PolicyFlows(self_by_band[0] * settings.buy_f1 * scale, export_y * settings.sell * scale,
                           np.zeros(len(export_y)), np.zeros(len(export_y)), "", 0.0)

    def community_steps(self, settings, year1, zone, tariff):
        return []

    def pedigree(self, key):
        from meridiana.core.energy.pedigree import Source
        return Source("input", _("given by the designer"))

    def text(self, key):
        return {
            "sale_tile": _('Sale, first year'),
            "npv_explanation": _("Each year's cash flow: saving and sale, less running costs and replacement, discounted to today."),
            "balance_explanation": _("The hourly physical balance uses declared consumption and production, with one purchase price."),
            "saving_formula": r"R_y = E_{auto,y}\,c_{buy}\,(1+e)^{y-1}",
            "saving_explanation": _("Self-consumed energy is valued at the declared purchase price."),
            "sale_formula": r"V_y = E_{export,y}\,c_{sell}\,(1+e)^{y-1}",
            "sale_explanation": _("Exported energy is valued at the declared sale price; no national incentive is applied."),
            "price_field:ALL": "buy_f1", "price_label:ALL": _("Purchase price"),
        }[key]


@dataclass(frozen=True)
class GenericElectrical:
    voc_fallback: float | None = None
    voltage_fallback: float | None = None
    ki_default: float | None = None
    allow_auto: bool = False
    source: str = ""

    def parallel_cap(self, module, ki):
        return None

    def selv(self, uoc_max):
        return []

    def protection(self, parallel, isc_max, ocpr, input_index):
        return []

    def pedigree(self, key):
        from meridiana.core.energy.pedigree import Source
        return Source("input", _("given by the designer"))

    def text(self, key):
        return {"title": _("Physical string checks"), "uoc_reference": "", "isc_reference": "", "check_source": "",
                "ki_label": _("factor given by the designer"), "scope": _(ELECTRICAL_SCOPE),
                "isc_formula": r"I_{SC,max} = K_I I_{SC,STC}",
                "isc_explanation": _("The explicit design factor is applied to the declared short-circuit current.")}[key]


@dataclass(frozen=True)
class GenericProfile:
    id: str = "generic"
    revision: int = 1

    def standards(self):
        return (StandardRef("IEC 61724-1", "2021", "reference_only", "IEC 61724-1:2021"),
                *(StandardRef(name, None, "reference_only", name) for name in ("IEC 61853-1", "IEC 61215", "IEC 61730")))

    def facts(self, project, results=None, energy=None, inverter=None):
        from shapely.geometry import Polygon
        results, energy = results or {}, energy or {}
        sim = energy.get("sim")
        facts = Facts(profile_id=self.id, level="", level_auto=False)
        facts.p_dc_kw = (float(sim.p_stc_kw) if sim is not None else
                         sum(float(project.modules.get(sf.module, {}).get("power_kw") or 0) * results[sf.id].count
                             for sf in project.subfields if sf.filled and hasattr(results.get(sf.id), "count")))
        if inverter is not None:
            facts.p_ac_kw = float(inverter.pac_total) / 1000
            facts.inverters = int(getattr(inverter, "count", 1) or 1)
        facts.storage = float(energy.get("battery_kwh") or 0) > 0
        facts.footprint_of = [b.name for b in project.buildings if len(b.footprint) >= 3]
        facts.footprint_m2 = sum(Polygon(b.footprint).area for b in project.buildings if len(b.footprint) >= 3)
        return facts

    def rules(self): return ()
    def title(self, rule, facts): return ""
    def in_document(self, rule, facts): return False
    def chapter_names(self): return {}
    def design(self, facts): return "unknown"
    def minimum(self, facts): return None
    def auto_level(self, power_kw): return ""
    def region_of(self, address): return ""
    def technical_rule(self, network): return ""
    def connection(self, p_kw, phases, chosen, level="", auto=True): return []

    def rule_items(self, facts):
        return [Item("info", "rules", _(SCOPE), window_only=False)]

    def fire(self, project, sf=None):
        return FirePolicy(False, 0.0, 0.0, 0.0, 0.0, "", "")

    def fire_group_items(self, *args, **kwargs): return []
    def layout_note(self, name, sfid, note): return None
    def activity(self, number): return None
    def activities(self, query=""): return []
    def validate_inputs(self, raw): pass
    def validate_fire(self, raw, path): pass

    def rule_call(self, name, *args):
        if name in {"level_names", "obligation_names", "use_names", "premises_names", "chapter_names"}: return {}
        raise KeyError(name)

    def activity_call(self, name, *args):
        if name == "activity": return None
        if name in {"search", "index"}: return []
        if name == "shown": return 0
        raise ValueError(_("National fire activities are unavailable in this profile"))

    def check_call(self, name, *args):
        if name == "area_names":
            return {"components": _("Components"), "layout": _("Layout"), "shade": _("Shading"), "strings": _("Physical string checks"),
                    "connection": _("Connection"), "production": _("Production"), "consumption": _("Consumption"),
                    "economics": _("Economics"), "rules": _("Calculation scope"), "import": _("From PVsyst"),
                    "defaults": _("Values still at their default")}
        if name == "string_why": return {}
        if name == "string_detail": return ""
        raise KeyError(name)

    def defaults(self, section):
        if section == "layout": return {"fire_edge": 0.0, "fire_group": 0.0, "fire_corridor": 0.0}
        if section == "strings": return {"voc_fallback": None, "voltage_fallback": None, "ki_default": None}
        if section == "consumption":
            from meridiana.core.energy.consumption import Consumption
            values = _empty_values(Consumption)
            values.update(common.CONSUMPTION)
            return values
        if section == "economics":
            from meridiana.core.energy.economics import Settings
            values = _empty_values(Settings)
            values.update(common.ECONOMICS)
            return values
        raise KeyError(section)

    def fields(self, section):
        if section in {"site", "network", "building"}: return ()
        values = self.defaults(section)
        allowed = {"consumption": {"pod", "contract_kw", "annual_kwh", "bands_kwh", "monthly_kwh", "monthly_bands_kwh", "measured"},
                   "economics": {"buy_f1", "sell", "capex_total", "capex_per_kwp", "opex_per_kwp", "years", "discount", "escalation",
                                 "opex_escalation", "degradation", "inverter_year", "inverter_per_kw", "battery_cost_per_kwh",
                                 "battery", "battery_units", "storage_coupling", "storage_inverter", "storage_efficiency_pct", "export_limit_kw"}}
        return tuple(InputField(key, type(value).__name__ if value is not None else "float", value, (), ())
                     for key, value in values.items() if key in allowed.get(section, set()))

    def calendar(self): return GenericCalendar()
    def consumption(self): return GenericConsumption()
    def economics(self): return GenericEconomy()
    def electrical(self): return GenericElectrical()

    def market_rules(self, opt, inv, base, reason):
        if reason == "country_limited_voltage":
            return None, _("This configuration has only a documented national market condition; it is unavailable in the generic profile")
        return base, reason

    def partial_fixed_check(self, string):
        from meridiana.core.energy.stringing import Check
        return Check("generic_market", _("Partial fixed-voltage configuration unavailable"), False,
                     _("No global manufacturer permission is documented for this partial configuration"), "info")

    def optimizer_parallel(self, family_id, declared):
        # This record contains a national inference, not a manufacturer limit.
        return None if family_id == "sungrow_sp" else dict(declared)

    def text(self, key):
        return {"scope": _(SCOPE), "electrical_scope": _(ELECTRICAL_SCOPE), "missing_data": _(MISSING),
                "auto_unavailable": _("Automatic electrical sizing is unavailable in this profile; enter manual strings and declared equipment data"),
                "profile_name": _("Generic IEC"), "ballast_warning": "", "fire_source": "", "exclusion_band": _("Free band"),
                "manual_edge_0": _("Modules intersect an exclusion or its explicit clearance."),
                "manual_edge_1": _("Modules cross the explicit geometric margin."),
                "manual_edge_2": _("Modules cross the explicit geometric margin."),
                "transposition_reference": _("Transposition: {model} (pvlib.irradiance)."),
                "azimuth_label": _("azimuth from South, + West")}[key]
