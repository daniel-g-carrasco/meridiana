"""What the review window asks for each kind of product: groups, names, units, what the calculations cannot do without.

The calculations decide what is required (R415), not `personal.REQUIRED`, which is only what a personal row must have to be
loaded at all and stays as lax as it was so that an older personal catalogue keeps opening:
- modules: energy.components.ModuleSpec and stringing (the five STC values, the three coefficients, size, cells, maximum
  system voltage, series fuse);
- inverters with MPPT: energy.components.InverterSpec, sizing.missing_fields and plant (AC power, phases, DC maximum voltage,
  MPPT window and count, current and Isc per tracker, efficiency);
- inverters at a fixed string voltage: energy.optimizers.fixed_voltage (DC power at STC, string voltage);
- microinverters: catalog.compat and the module checks;
- optimizers: energy.optimizers.Optimizer and module_checks;
- batteries: energy.storage (energy, coupling, charge and discharge power, efficiency).

Labels are English msgids, translated by the window. A value not printed stays empty: what is `required` is said, never
filled in.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    unit: str = ""
    type: str = "number"        # number, integer, text, choice, yesno, per_mppt, range, dimensions
    required: bool = False      # the calculations need it
    low: float | None = None    # a credible value is within low..high: outside it is said, not refused
    high: float | None = None
    choices: tuple = ()         # (key, label)
    when: tuple = ()            # (field, value): shown and required only then
    hint: str = ""


IDENTITY = ("Product", (
    Field("manufacturer", "Manufacturer", type="text", required=True),
    Field("model", "Model", type="text", required=True, hint="The exact code: a family's range goes in the table of classes."),
    Field("series", "Series", type="text"),
    Field("datasheet_url", "Source document or URL", type="text", required=True,
          hint="The address of the datasheet, or its file name."),
    Field("datasheet_revision", "Datasheet revision", type="text"),
))
NOTES = ("Notes", (Field("notes", "Notes", type="text"),))

_DC_ARCHITECTURE = (("", "MPPT in the inverter"), ("fixed_string_voltage", "Fixed string voltage, with optimizers"))
_MPPT = ("dc_architecture", "")
_FIXED = ("dc_architecture", "fixed_string_voltage")

KINDS = {
    "modules": (
        IDENTITY,
        ("Electrical values at STC", (
            Field("pmax", "Power at STC", "W", required=True, low=20, high=1000),
            Field("vmp", "Vmp", "V", required=True, low=5, high=120),
            Field("imp", "Imp", "A", required=True, low=1, high=30),
            Field("voc", "Voc", "V", required=True, low=5, high=130),
            Field("isc", "Isc", "A", required=True, low=1, high=32),
            Field("efficiency_pct", "Efficiency", "%", low=5, high=30),
        )),
        ("Temperature coefficients", (
            Field("gamma_pmax", "γ Pmax", "%/K", required=True, low=-0.7, high=-0.1),
            Field("beta_voc", "β Voc", "%/K", required=True, low=-0.5, high=-0.1),
            Field("alpha_isc", "α Isc", "%/K", required=True, low=0.0, high=0.15),
        )),
        ("Size and limits", (
            Field("length", "Length", "m", required=True, low=0.5, high=3.5),
            Field("width", "Width", "m", required=True, low=0.3, high=2.0),
            Field("thickness_mm", "Thickness", "mm", low=2, high=80),
            Field("weight_kg", "Weight", "kg", low=2, high=70),
            Field("cells", "Cells", type="integer", required=True, low=30, high=320),
            Field("max_system_voltage_v", "Maximum system voltage", "V", required=True, low=500, high=2000),
            Field("max_series_fuse_a", "Maximum series fuse", "A", required=True, low=5, high=80),
        )),
        ("Technology", (
            Field("technology", "Technology", type="text"),
            Field("bifacial", "Bifacial", type="yesno"),
            Field("bifaciality", "Bifaciality", "%", low=40, high=100, when=("bifacial", True)),
        )),
        ("Warranty and ageing", (
            Field("warranty_product_years", "Product warranty", "years", low=1, high=40),
            Field("warranty_power_years", "Power warranty", "years", low=1, high=40),
            Field("first_year_loss", "First year degradation", "%", low=0, high=5),
            Field("yearly_loss", "Yearly degradation", "%", low=0, high=2),
        )),
        NOTES,
    ),
    "inverters": (
        IDENTITY,
        ("Output", (
            Field("ac_power_nominal_w", "Nominal AC power", "W", required=True, low=100, high=2000000),
            Field("ac_power_max_va", "Maximum AC power", "VA", low=100, high=2500000),
            Field("phases", "Phases", type="choice", required=True, choices=(("1", "Single-phase"), ("3", "Three-phase"))),
            Field("ac_voltage_nominal_v", "Nominal AC voltage", "V", low=100, high=1000),
            Field("ac_current_max_a", "Maximum AC current", "A", low=0.5, high=3000),
            Field("efficiency_euro_pct", "European efficiency", "%", required=True, low=80, high=100),
            Field("efficiency_max_pct", "Maximum efficiency", "%", low=80, high=100),
        )),
        ("DC input", (
            Field("dc_architecture", "DC architecture", type="choice", choices=_DC_ARCHITECTURE),
            Field("dc_voltage_max_v", "Maximum DC voltage", "V", required=True, low=100, high=2000),
            Field("dc_power_max_w", "Maximum DC power", "W", low=100, high=4000000),
            Field("mppt_voltage_min_v", "MPPT from", "V", required=True, low=10, high=1500, when=_MPPT),
            Field("mppt_voltage_max_v", "MPPT to", "V", required=True, low=50, high=2000, when=_MPPT),
            Field("mppt_count", "Number of MPPT", type="integer", required=True, low=1, high=40, when=_MPPT),
            Field("strings_per_mppt", "Strings per MPPT", type="per_mppt", when=_MPPT, hint="One value, or one for each MPPT: 2 2 1."),
            Field("dc_current_max_per_mppt_a", "Maximum current per MPPT", "A", type="per_mppt", required=True, when=_MPPT,
                  hint="One value, or one for each MPPT: 30 30 16."),
            Field("dc_isc_max_per_mppt_a", "Maximum Isc per MPPT", "A", type="per_mppt", required=True, when=_MPPT,
                  hint="One value, or one for each MPPT."),
            Field("string_voltage_v", "Fixed string voltage", "V", required=True, low=100, high=1500, when=_FIXED),
            Field("startup_voltage_v", "Start-up voltage", "V", low=10, high=1500, when=_MPPT),
        )),
        ("Storage", (
            Field("type", "Type", type="choice", choices=(("string", "String"), ("hybrid", "Hybrid"))),
            Field("battery_power_max_w", "Maximum battery power", "W", low=100, high=2000000, when=("type", "hybrid")),
        )),
        ("Installation", (
            Field("weight_kg", "Weight", "kg", low=1, high=3000),
            Field("dimensions_mm", "Dimensions", "mm", type="dimensions"),
            Field("ip_rating", "IP rating", type="text"),
            Field("warranty_years", "Warranty", "years", low=1, high=40),
            Field("cei_0_21", "CEI 0-21 stated", type="yesno"),
        )),
        NOTES,
    ),
    "microinverters": (
        IDENTITY,
        ("Output", (
            Field("ac_power_nominal_w", "Nominal AC power", "W", required=True, low=50, high=10000),
            Field("ac_power_max_va", "Maximum AC power", "VA", low=50, high=10000),
            Field("phases", "Phases", type="choice", choices=(("1", "Single-phase"), ("3", "Three-phase"))),
            Field("efficiency_weighted_pct", "Weighted efficiency", "%", required=True, low=80, high=100),
            Field("efficiency_peak_pct", "Peak efficiency", "%", low=80, high=100),
        )),
        ("Modules on it", (
            Field("modules_per_unit", "Modules per unit", type="integer", required=True, low=1, high=8),
            Field("dc_power_max_per_input_w", "Maximum power per input", "W", required=True, low=50, high=2000),
            Field("dc_voltage_max_v", "Maximum voltage per input", "V", required=True, low=20, high=200),
            Field("mppt_voltage_min_v", "MPPT from", "V", required=True, low=5, high=200),
            Field("mppt_voltage_max_v", "MPPT to", "V", required=True, low=10, high=200),
            Field("dc_current_max_per_input_a", "Maximum current per input", "A", required=True, low=1, high=40),
            Field("dc_isc_max_per_input_a", "Maximum Isc per input", "A", required=True, low=1, high=50),
        )),
        ("Installation", (
            Field("weight_kg", "Weight", "kg", low=0.1, high=30),
            Field("warranty_years", "Warranty", "years", low=1, high=40),
            Field("cei_0_21", "CEI 0-21 stated", type="yesno"),
        )),
        NOTES,
    ),
    "optimizers": (
        IDENTITY,
        ("Input", (
            Field("rated_input_power_w", "Rated input power", "W", required=True, low=50, high=3000),
            Field("max_input_voltage_v", "Maximum input voltage", "V", required=True, low=20, high=300),
            Field("mppt_voltage_min_v", "MPPT from", "V", required=True, low=1, high=200),
            Field("mppt_voltage_max_v", "MPPT to", "V", required=True, low=10, high=300),
            Field("max_input_isc_a", "Maximum input Isc", "A", required=True, low=1, high=50),
            Field("max_input_current_a", "Maximum input current", "A", low=1, high=50),
            Field("modules_per_unit", "Modules per unit", type="integer", required=True, low=1, high=4),
        )),
        ("Output", (
            Field("max_output_current_a", "Maximum output current", "A", required=True, low=1, high=50),
            Field("max_output_voltage_v", "Maximum output voltage", "V", low=20, high=300),
            Field("efficiency_weighted_pct", "Weighted efficiency", "%", required=True, low=80, high=100),
            Field("efficiency_peak_pct", "Peak efficiency", "%", low=80, high=100),
        )),
        ("Compatibility", (
            Field("compatible_inverters", "Compatible inverters", type="text", required=True,
                  hint="As the datasheet says it: the rules of its strings come with the catalogue's data for the maker."),
            Field("rapid_shutdown", "Rapid shutdown", type="yesno"),
        )),
        ("Installation", (
            Field("weight_kg", "Weight", "kg", low=0.05, high=10),
            Field("warranty_years", "Warranty", "years", low=1, high=40),
        )),
        NOTES,
    ),
    "batteries": (
        IDENTITY,
        ("Energy", (
            Field("usable_energy_kwh", "Usable energy", "kWh", required=True, low=0.1, high=10000),
            Field("nominal_energy_kwh", "Nominal energy", "kWh", low=0.1, high=10000),
            Field("depth_of_discharge_pct", "Depth of discharge", "%", low=10, high=100),
            Field("round_trip_efficiency_pct", "Round-trip efficiency", "%", required=True, low=50, high=100),
            Field("chemistry", "Chemistry", type="text"),
        )),
        ("Power and connection", (
            Field("coupling", "Coupling", type="choice", required=True, choices=(("dc", "DC"), ("ac", "AC"))),
            Field("voltage_class", "Voltage class", type="text"),
            Field("nominal_voltage_v", "Nominal voltage", "V", low=10, high=1500),
            Field("max_charge_power_w", "Maximum charge power", "W", required=True, low=50, high=5000000),
            Field("max_discharge_power_w", "Maximum discharge power", "W", required=True, low=50, high=5000000),
            Field("compatible_inverters", "Compatible inverters", type="text"),
        )),
        ("Modules and warranty", (
            Field("modules_min", "Modules, from", type="integer", low=1, high=100),
            Field("modules_max", "Modules, up to", type="integer", low=1, high=100),
            Field("energy_per_module_kwh", "Energy per module", "kWh", low=0.1, high=500),
            Field("cycles_warranted", "Warranted cycles", type="integer", low=100, high=30000),
            Field("warranty_years", "Warranty", "years", low=1, high=40),
            Field("weight_kg", "Weight", "kg", low=1, high=30000),
        )),
        NOTES,
    ),
}


def groups(kind: str) -> tuple:
    return KINDS[kind]


def fields(kind: str) -> list[Field]:
    return [f for _title, members in KINDS[kind] for f in members]


def _applies(field: Field, record: dict) -> bool:
    if not field.when:
        return True
    key, value = field.when
    have = record.get(key)
    return bool(have) is value if isinstance(value, bool) else (have or "") == value


def visible(field: Field, record: dict) -> bool:
    return _applies(field, record)


def _empty(value) -> bool:
    return value is None or value == "" or value == []


def missing(kind: str, record: dict) -> list[Field]:
    """The fields the calculations need and `record` does not have."""
    return [f for f in fields(kind) if f.required and _applies(f, record) and _empty(record.get(f.key))]


def _number(value):
    return float(value) if value.__class__ in (int, float) and math.isfinite(value) else None


def coherence(kind: str, record: dict) -> list[dict]:
    """What does not add up in a record about to be reviewed: {"level": "error" or "warning", "field", "text"}, with the
    text an English msgid with its values already in {braces} for the window to fill, in `values`. An error stops the
    saving; a warning is said, and the designer decides. None of them says the values are right."""
    out = []

    def say(level, where, text, **values):
        out.append({"level": level, "field": where, "text": text, "values": values})

    for f in fields(kind):
        value = _number(record.get(f.key))
        if value is not None and _applies(f, record) and (
                (f.low is not None and value < f.low) or (f.high is not None and value > f.high)):
            say("warning", f.key, "{field}: {value} {unit} is unusual for this kind of product (from {low} to {high})",
                field=f.label, value=value, unit=f.unit, low=f.low, high=f.high)
    get = lambda key: _number(record.get(key))  # noqa: E731
    if kind == "modules":
        pmax, vmp, imp, voc, isc = (get(k) for k in ("pmax", "vmp", "imp", "voc", "isc"))
        if vmp and voc and voc <= vmp:
            say("error", "voc", "Voc must be above Vmp ({voc} V, {vmp} V)", voc=voc, vmp=vmp)
        if imp and isc and isc <= imp:
            say("error", "isc", "Isc must be above Imp ({isc} A, {imp} A)", isc=isc, imp=imp)
        if pmax and vmp and imp and abs(vmp * imp - pmax) > 0.03 * pmax:
            say("warning", "pmax", "Vmp × Imp gives {product} W, not {pmax} W: check the three values",
                product=round(vmp * imp, 1), pmax=pmax)
        length, width = get("length"), get("width")
        if pmax and length and width and get("efficiency_pct"):
            derived = 100.0 * pmax / (1000.0 * length * width)
            if abs(derived - get("efficiency_pct")) > 1.0:
                say("warning", "efficiency_pct", "Power and size give an efficiency of {derived} %, not {stated} %",
                    derived=round(derived, 2), stated=get("efficiency_pct"))
        if length and width and width > length:
            say("warning", "length", "The width is above the length: check the order of the two")
        for entry in record.get("classes") or []:
            power, v, i = entry.get("pmax"), entry.get("vmp"), entry.get("imp")
            if power and v and i and abs(v * i - power) > 0.03 * power:
                say("warning", "classes", "The class of {pmax} W: Vmp × Imp gives {product} W", pmax=power, product=round(v * i, 1))
            if entry.get("voc") and v and entry["voc"] <= v:
                say("error", "classes", "The class of {pmax} W: Voc must be above Vmp", pmax=power)
    if kind in ("inverters", "microinverters", "optimizers"):
        low, high = get("mppt_voltage_min_v"), get("mppt_voltage_max_v")
        if low and high and low >= high:
            say("error", "mppt_voltage_min_v", "The MPPT window must rise: from {low} V to {high} V", low=low, high=high)
    if kind == "inverters":
        top, dc = get("mppt_voltage_max_v"), get("dc_voltage_max_v")
        if top and dc and top > dc:
            say("warning", "mppt_voltage_max_v", "The MPPT window ends above the maximum DC voltage ({top} V, {dc} V)", top=top, dc=dc)
        ac, va = get("ac_power_nominal_w"), get("ac_power_max_va")
        if ac and va and va < ac:
            say("warning", "ac_power_max_va", "The maximum AC power is below the nominal one ({va} VA, {ac} W)", va=va, ac=ac)
        dc_w = get("dc_power_max_w")
        if ac and dc_w and dc_w < ac:
            say("warning", "dc_power_max_w", "The maximum DC power is below the nominal AC power ({dc} W, {ac} W)", dc=dc_w, ac=ac)
        count = record.get("mppt_count")
        for key in ("dc_current_max_per_mppt_a", "dc_isc_max_per_mppt_a"):
            value = record.get(key)
            if isinstance(value, list) and count.__class__ is int and len(value) not in (1, count):
                say("error", key, "{count} MPPT and {given} values: one value, or one for each MPPT", count=count, given=len(value))
    if kind == "batteries":
        usable, nominal = get("usable_energy_kwh"), get("nominal_energy_kwh")
        if usable and nominal and usable > nominal:
            say("error", "usable_energy_kwh", "The usable energy is above the nominal one ({usable} kWh, {nominal} kWh)", usable=usable, nominal=nominal)
    return out


# the words a model or a person may use for a catalogue field, and what multiplies the value
ALIASES = {
    "modules": {"pmax_w": ("pmax", 1), "vmp_v": ("vmp", 1), "imp_a": ("imp", 1), "voc_v": ("voc", 1), "isc_a": ("isc", 1),
                "length_mm": ("length", 0.001), "width_mm": ("width", 0.001), "temp_coeff_pmax_pct_c": ("gamma_pmax", 1),
                "temp_coeff_voc_pct_c": ("beta_voc", 1), "temp_coeff_isc_pct_c": ("alpha_isc", 1),
                "bifaciality_pct": ("bifaciality", 1), "degradation_first_year_pct": ("first_year_loss", 1),
                "degradation_annual_pct": ("yearly_loss", 1)},
}


def normalised(kind: str, record: dict) -> dict:
    """A proposed record in the catalogue's terms: known synonyms renamed and converted, a tracker's single value kept
    as it is. Fields it does not know are kept: nothing a source said is dropped on the way to the review."""
    out = {}
    aliases = ALIASES.get(kind, {})
    for key, value in record.items():
        target, factor = aliases.get(key, (key, 1))
        if factor != 1 and value.__class__ in (int, float):
            value = value * factor
        if target not in out or key == target:
            out[target] = value
    return out
