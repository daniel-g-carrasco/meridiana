"""The rules that apply to the system, as notes for its technical report: design standards, grid connection,
fire safety, the minimum renewable capacity of buildings, permitting and storage. Each rule has its
condition, its paragraphs (at most 300 characters each) and its source. They come from Daniel's library
«Utilità Fotovoltaico R02» (21/10/2026), whose texts were checked on the documents of the archive.

One difference from R02: the thresholds of CEI 0-21 (6, 11.08, 20 and 100 kW) are compared with the nominal
power of a PV plant as CEI 0-21:2026-07 3.61 (p. 16) defines it, the lower of the inverters' power and the
modules' STC power; R02 compares 11.08 and 20 kW with the modules' power.

No Qt here: the checks page lists the rules that apply, the report prints their paragraphs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .i18n import _, number

LEVELS = ("BT", "MT", "AT")
OBLIGATIONS = ("", "none", "new", "renovation")
USES = ("other", "data_centre", "logistics_big", "logistics_small", "large_retail")
PREMISES = ("", "productive", "domestic", "condominium")
MV_KW = 100.0                   # CEI 0-16:2026-07 6.3, Tab. 4 (p. 43): up to 0.1 MW low voltage
HV_KW = 10000.0                 # ... medium voltage up to 6 MW for production, 6 to 10 MW MV or HV, above HV
C016_TAB4 = "CEI 0-16:2026-07, 6.3, Tab. 4, p. 43"
# DM 37/2008 (consolidated with DM 130/2025) art. 5 par. 2, p. 4: a registered professional designs above 6 kW
# of contracted power, or above 200 m² for production, commerce and services (c), 400 m² for a dwelling (a)
DESIGN_KW = 6.0
DESIGN_M2 = {"productive": 200.0, "domestic": 400.0}


def level_names() -> dict:
    return {"auto": _("Automatic from the power"), "BT": _("Low voltage (CEI 0-21)"),
            "MT": _("Medium voltage (CEI 0-16)"), "AT": _("High voltage (Terna)")}


def obligation_names() -> dict:
    return {"": _("Not stated"), "none": _("Not subject"), "new": _("New building"),
            "renovation": _("Existing building, major renovation")}


def use_names() -> dict:
    return {"other": _("Other"), "data_centre": _("Data centre"), "logistics_big": _("Logistics over 3 ha"),
            "logistics_small": _("Logistics up to 3 ha"), "large_retail": _("Large retail")}


def premises_names() -> dict:
    """The premises of DM 37/2008 art. 5 par. 2: letter c) production, commerce, services and other uses;
    letter a) a single dwelling, or a condominium (always with a professional's design)."""
    return {"": _("Not stated"), "productive": _("Production, commerce, services, other uses"),
            "domestic": _("Domestic, a single dwelling"), "condominium": _("Condominium")}


def chapter_names() -> dict:
    return {1: _("1. Reference standards and design"), 2: _("2. Grid connection"), 3: _("3. Fire safety"),
            4: _("4. Minimum renewable capacity obligation"), 5: _("5. Permitting regime and storage")}


def auto_level(p_kw: float) -> str:
    """The voltage level CEI 0-16 indicates for a production plant of this power (Tab. 4: the DSO decides)."""
    return "BT" if p_kw <= MV_KW else ("MT" if p_kw <= HV_KW else "AT")


def region_of(address: str) -> str:
    """The region, when the address found says it (Nominatim writes it); only Lombardy has rules of its own here."""
    low = (address or "").lower()
    return "Lombardia" if ("lombardia" in low or "lombardy" in low) else ""


@dataclass
class Facts:
    """What the rules look at, gathered from the project and the last computation."""
    p_dc_kw: float = 0.0                 # the modules' STC power
    p_ac_kw: float = 0.0                 # the inverters' AC power
    inverters: int = 1
    level: str = "BT"
    level_auto: bool = True
    fire: bool | None = None             # an activity subject to fire-brigade control; None: no building
    installs: set = field(default_factory=set)      # "BAPV", "BIPV", "canopy", "ground"
    storage: bool = False
    uoc_max: float | None = None         # V, the strings' highest open-circuit voltage
    obligation: str = ""
    public: bool = False
    use: str = "other"
    permit_2027: bool = False
    region: str = ""
    footprint_m2: float = 0.0
    footprint_of: list = field(default_factory=list)     # the buildings whose footprint S sums
    # the supply and the premises, for DM 37/2008 art. 5 par. 2: 0 and "" mean not stated
    contracted_kw: float = 0.0           # the contracted power of the supply, not the PV power
    floor_m2: float = 0.0                # the floor area of the premises
    premises: str = ""                   # one of PREMISES
    risk: bool = False                   # higher fire risk, medical use or explosion hazard (letter d)

    @property
    def p_nominal_kw(self) -> float:
        """CEI 0-21:2026-07 3.61: a PV plant gives no more than its inverters, when they are the smaller."""
        return min(self.p_dc_kw, self.p_ac_kw) if self.p_ac_kw > 0 else self.p_dc_kw

    @property
    def subject(self) -> bool:
        return self.obligation in ("new", "renovation")


def facts(project, results: dict | None = None, energy: dict | None = None, inverter=None) -> Facts:
    """The facts of a project. `results` are the layouts by sub-field, `energy` what the energy job gave (or
    None), `inverter` the InverterSpec."""
    from shapely.geometry import Polygon
    energy = energy or {}
    results = results or {}
    r = getattr(project, "rules", None) or {}
    f = Facts()
    sim = energy.get("sim")
    if sim is not None:
        f.p_dc_kw = float(sim.p_stc_kw)
    else:
        f.p_dc_kw = sum(float(project.modules.get(sf.module, {}).get("power_kw") or 0.0) * results[sf.id].count
                        for sf in project.subfields if sf.filled and hasattr(results.get(sf.id), "count"))
    if inverter is not None:
        f.p_ac_kw = float(inverter.pac_total) / 1000.0
        f.inverters = int(getattr(inverter, "count", 1) or 1)
    chosen = r.get("connection") or "auto"
    f.level_auto = chosen not in LEVELS
    f.level = auto_level(f.p_nominal_kw) if f.level_auto else chosen
    hosts = {sf.building for sf in project.subfields}
    roofs = [b for b in project.buildings if b.id in hosts]
    buildings = roofs or ([] if project.subfields else list(project.buildings))
    if buildings:
        f.fire = any(b.fire.subject for b in buildings)
    for sf in project.subfields:
        mounting = sf.layout_params().mounting
        if sf.building is None or mounting == "ground":
            f.installs.add("canopy" if mounting == "canopy" else "ground")
        elif mounting == "integrated":
            f.installs.add("BIPV")
        elif mounting == "canopy":
            f.installs.add("canopy")
        else:
            f.installs.add("BAPV")
    f.storage = float(energy.get("battery_kwh") or 0.0) > 0
    plan = (energy.get("strings") or {}).get("plan")
    if plan is not None and getattr(plan, "uoc_max", None):
        f.uoc_max = float(plan.uoc_max)
    plant = energy.get("plant")                     # the inputs of the inverters (task 16d): the highest of them
    highest = max((s.plan.uoc_max for s in getattr(plant, "inputs", {}).values() if s.plan is not None), default=0.0)
    if highest:
        f.uoc_max = float(highest)
    f.obligation = r.get("obligation") or ""
    f.public = bool(r.get("public"))
    f.use = r.get("use") or "other"
    f.permit_2027 = bool(r.get("permit_2027"))
    f.region = region_of(project.site.address)
    f.footprint_of = [b.name for b in buildings if len(b.footprint) >= 3]
    f.footprint_m2 = sum(Polygon(b.footprint).area for b in buildings if len(b.footprint) >= 3)
    f.contracted_kw = float(r.get("contracted_kw") or 0.0)
    f.floor_m2 = float(r.get("floor_m2") or 0.0)
    f.premises = r.get("premises") if r.get("premises") in PREMISES else ""
    f.risk = bool(r.get("risk"))
    return f


def design(f: Facts) -> str:
    """Who may design under DM 37/2008 art. 5 (p. 4): "professional" when par. 2 requires a registered
    professional, "installer" when par. 1 leaves the design to the installer's technical manager, "unknown"
    while the site does not say enough (then the professional's design is taken as due)."""
    if f.level != "BT" or f.risk or f.fire is True or f.premises == "condominium":
        return "professional"
    if f.premises not in DESIGN_M2:
        return "unknown"
    if f.contracted_kw > DESIGN_KW or f.floor_m2 > DESIGN_M2[f.premises]:
        return "professional"
    return "installer" if (f.contracted_kw > 0 and f.floor_m2 > 0) else "unknown"


def minimum(f: Facts) -> tuple[float, float] | None:
    """(k in kW/m², the minimum power in kW) of D.Lgs. 199/2021, Annex III, for a building subject to it."""
    if not f.subject or f.footprint_m2 <= 0:
        return None
    if f.obligation == "new":
        k = 0.05
        if f.region == "Lombardia" and f.permit_2027:
            k = {"data_centre": 0.08, "logistics_big": 0.08, "logistics_small": 0.06, "large_retail": 0.06}.get(f.use, 0.05)
    else:
        k = 0.025
    return k, k * f.footprint_m2 * (1.1 if f.public else 1.0)


@dataclass
class Rule:
    id: str
    chapter: int
    applies: Callable[[Facts], bool]
    paragraphs: Callable[[Facts], list[str]]
    source: Callable[[], str]
    level: str = "info"


def _n24(f: Facts) -> list[str]:
    k, p = minimum(f) or (0.0, 0.0)
    first = _("Legislative Decree 199/2021 (art. 26 and Annex III, as amended by Legislative Decree 5/2026 for permit "
              "applications filed 180 days after its entry into force: from 03/08/2026, a date inferred from GU no. 15 "
              "of 20/01/2026) requires a minimum renewable electrical capacity for the building P = k × S = {p} kW, "
              "with k = {k} kW/m² and S = {s} m².").format(
        p=number(p, 1), k=number(k, 3), s=number(f.footprint_m2, 0, grouping=True))
    if f.public:
        first += " " + _("Public building: the capacity is raised by 10%.")
    return [first,
            _("S is the building footprint at ground level, excluding ancillary areas. The system is installed on or "
              "inside the building or in its ancillary areas; ground-mounted PV does not count towards the obligation "
              "(Annex III, Sect. C p. 2)."),
            _("Calculations and checks are given in the report under art. 8(1) of Legislative Decree 192/2005. Failure "
              "to comply leads to refusal of the building permit (art. 26 par. 4).")]


def _n02(f: Facts) -> list[str]:
    """Why DM 37/2008 art. 5 par. 2 asks for a registered professional, or that the site does not say enough."""
    kw, m2 = number(f.contracted_kw, 1), number(f.floor_m2, 0, grouping=True)
    if f.level != "BT":
        why = _("premises supplied at a voltage above 1000 V, including the low-voltage part (art. 5 par. 2 c).")
    elif f.risk:
        why = _("premises with environments at higher fire risk, for medical use or with an explosion hazard "
                "(art. 5 par. 2 d).")
    elif f.premises == "condominium":
        why = _("condominium premises (art. 5 par. 2 a).")
    elif f.fire is True:
        why = _("premises subject to fire prevention controls, taken as environments at higher fire risk (art. 5 "
                "par. 2 d; the classification follows CEI 64-8/7 sect. 751.03 and the fire risk assessment).")
    elif f.premises == "domestic" and (f.contracted_kw > DESIGN_KW or f.floor_m2 > DESIGN_M2["domestic"]):
        why = (_("a dwelling with a contracted power of {kw} kW, above 6 kW (art. 5 par. 2 a).")
               if f.contracted_kw > DESIGN_KW else
               _("a dwelling with a floor area of {m2} m², above 400 m² (art. 5 par. 2 a).")).format(kw=kw, m2=m2)
    elif f.premises == "productive" and (f.contracted_kw > DESIGN_KW or f.floor_m2 > DESIGN_M2["productive"]):
        why = (_("premises for production, commerce or services with a contracted power of {kw} kW, above 6 kW "
                 "(art. 5 par. 2 c).") if f.contracted_kw > DESIGN_KW else
               _("premises for production, commerce or services with a floor area of {m2} m², above 200 m² "
                 "(art. 5 par. 2 c).")).format(kw=kw, m2=m2)
    else:
        return [_("The contracted power of the supply, the floor area and the use of the premises are not stated "
                  "(site properties): the design is taken as due from a registered professional (Ministerial Decree "
                  "37/2008, art. 5 par. 2), to be confirmed with those data."),
                _("Art. 5 par. 2 requires it for condominiums and for dwellings above 6 kW of contracted power or "
                  "400 m² (a); for production, commerce and services above 6 kW or 200 m², or supplied above 1000 V "
                  "(c); with environments at higher fire risk, for medical use or with an explosion hazard (d)."),
                _("Outside these cases the design may be prepared by the installer's technical manager (art. 5 par. "
                  "1); the declaration of conformity is always due (art. 7)."),
                _n02_tail()]
    return [_("The system design is prepared by a registered professional, as required by Ministerial Decree "
              "37/2008, art. 5 par. 2: ") + why, _n02_tail()]


def _n02_tail() -> str:
    return _("The design includes at least diagrams, layouts and a technical report (art. 5 par. 4). On completion the "
             "installer issues the declaration of conformity (art. 7); if the system is part of a building permit, the "
             "design is filed with the building design (art. 11 par. 2).")


def _n03(f: Facts) -> list[str]:
    return [_("Premises supplied at low voltage with a contracted power of {kw} kW (not above 6 kW) and a floor area "
              "of {m2} m² (not above {max} m²), outside the cases of art. 5 par. 2: Ministerial Decree 37/2008 "
              "allows the design to be prepared by the installer's technical manager (art. 5 par. 1, art. 7 par. "
              "2).").format(kw=number(f.contracted_kw, 1), m2=number(f.floor_m2, 0, grouping=True),
                            max=number(DESIGN_M2[f.premises], 0)),
            _("The declaration of conformity is always due (art. 7). A design by a registered professional is "
              "nevertheless recommended for a grid-connected system.")]


RULES: list[Rule] = [
    # 1. Reference standards and design
    Rule("N01", 1, lambda f: True, lambda f: [
        _("The system is designed to CEI 64-8/7:2024-07, section 712 (photovoltaic systems). DC-side components are "
          "selected for the voltage Uoc MAX (712.512.1.1) and for the current Isc MAX = KI × Isc STC, with KI not less "
          "than 1.25 (712.512.1.2 and Annex B.2)."),
        _("Where the minimum temperature and the temperature coefficient are not known, Uoc MAX is taken as 1.2 × Uoc "
          "STC (Annex B.1). Cables exposed to heating from the modules are sized for a temperature of 70 °C (712.523)."),
        _("The inverter can be isolated on both the DC and the AC side (712.537.2.101), with a DC isolator or circuit "
          "breaker (712.537.2.2.101). String protective devices are provided per 712.431.101, only with more than two "
          "strings in parallel."),
        _("The DC side is protected against overvoltages by SPDs selected per 712.443 and 712.534. The presence of the "
          "PV system is indicated by warning notices and markings per 712.514.")],
        lambda: _("CEI 64-8/7:2024-07 sect. 712 (p. 91-110)")),
    Rule("N02", 1, lambda f: design(f) != "installer", _n02,
         lambda: _("DM 37/2008 (consolidated with DM 130/2025) art. 5 par. 2 (p. 4), art. 5 par. 4, arts. 7, 11")),
    Rule("N03", 1, lambda f: design(f) == "installer", _n03,
         lambda: _("DM 37/2008 (consolidated with DM 130/2025) art. 5 par. 1-2 (p. 4), art. 7")),
    Rule("N12", 1, lambda f: f.uoc_max is not None and f.uoc_max > 1500, lambda f: [
        _("WARNING: the maximum open-circuit voltage exceeds 1500 V, outside the scope of CEI 64-8 (installations up to "
          "1500 V DC) and of the fire brigade guidelines DCPREV 14030/2025 (sect. 1.2). Reduce the number of modules "
          "per string.")],
        lambda: _("CEI 64-8/1; DCPREV 14030/2025 sect. 1.2"), "fail"),
    # 2. Grid connection
    Rule("N04", 2, lambda f: f.level == "BT" and f.p_nominal_kw <= 11.08, lambda f: [
        _("Low-voltage connection per CEI 0-21:2026-07. With a total power up to 11.08 kW several interface protection "
          "systems (SPI) are allowed, at most one per interface device (DDI) (8.2.2.2)."),
        _("The interface protection system may be integrated in the inverter or be a dedicated protection relay "
          "(8.6.2): the integrated one is checked on site with the self-test (A.4.4), the dedicated relay with the "
          "tests of A.4.3."),
        _("For inverters up to 11.08 kW with an internal DDI, two devices are required, at least one of them an AC1 "
          "contactor with the clearances of IEC 62109 (8.2.2.3). Below 800 W the settings of Table 14 apply "
          "(8.6.2.1), in a fixed execution not adjustable by the user (Annex D D.1, p. 249; Annex Bbis.5.1, p. 174)."),
        _("The operating agreement with the distributor follows Annex Gbis (systems up to 11.08 kW connected to the "
          "LV network through inverters, p. 272).")],
        lambda: _("CEI 0-21:2026-07 8.2.2.2, 8.2.2.3, 8.6.2 (p. 96), 8.6.2.1, Annex A.4.3-A.4.4, Annex D D.1 (p. 249), "
                  "Annex Gbis (p. 272)")),
    Rule("N05", 2, lambda f: f.level == "BT" and f.p_nominal_kw > 11.08, lambda f: [
        _("Low-voltage connection per CEI 0-21:2026-07. With a total power above 11.08 kW the interface protection "
          "system is a dedicated protection relay, tested on site per A.4.3: an SPI integrated in the inverter is "
          "allowed only up to 11.08 kW (8.6.2)."),
        _("The 11.08 kW threshold refers to the total power of the generating plant: a storage system belongs to the "
          "generating group (8.4.1, p. 65) and the requirements of Annex Bbis apply also when it shares the inverter "
          "with the PV generator (Bbis.1, p. 166)."),
        _("The interface device is normally single. Up to three separate DDIs are allowed, each with its own "
          "protection, without OR logic; with more than three DDIs OR logic is used, so that a fault detected by any "
          "SPI opens all DDIs (8.2.2.2)."),
        _("The DDI is a circuit breaker suitable for isolation or an all-pole AC3 contactor controlled by the SPI "
          "(8.2.2.3). The operating agreement with the distributor follows Annex G (systems above 11.08 kW in "
          "parallel with the LV network).")],
        lambda: _("CEI 0-21:2026-07 8.2.2.2, 8.2.2.3, 8.4.1 (p. 65), 8.6.2 (p. 96), Annex Bbis.1 (p. 166), Annex G")),
    Rule("N06", 2, lambda f: f.level == "BT" and f.p_nominal_kw > 20, lambda f: [
        _("With a power above 20 kW a back-up trip for failure of the DDI to open is provided (CEI 0-21:2026-07, "
          "8.2.2.4): the SPI trip command, delayed by at most 0.5 s, also acts on a second device (possibly the main "
          "switch); reset is manual only."),
        _("If the inverter has an internal electromechanical DDI compliant with 8.2.2, it may provide the back-up "
          "provided it receives the delayed trip signal from the external SPI. There are therefore always at least two "
          "devices between generator and network controlled by the interface protection.")],
        lambda: _("CEI 0-21:2026-07 8.2.2.4 (p. 63-64)")),
    Rule("N07", 2, lambda f: f.level == "BT" and f.p_nominal_kw > 100, lambda f: [
        _("Above 100 kW of injected power the distributor may propose a medium-voltage connection (CEI 0-21:2026-07, "
          "Table 5 and 7.4.10; TICA): the connection solution must be checked before defining switchboards and "
          "protections.")],
        lambda: _("CEI 0-21:2026-07 Table 5, 7.4.10")),
    Rule("N08", 2, lambda f: f.inverters > 1, lambda f: [
        _("With several generators the interface device is normally single and separates all generators at once; "
          "several DDIs controlled by a single SPI are allowed (CEI 0-21:2026-07, 8.2.2.2; at MV CEI 0-16:2026-07, "
          "8.8.3.1).")],
        lambda: _("CEI 0-21:2026-07 8.2.2.2; CEI 0-16:2026-07 8.8.3.1 (p. 117)")),
    Rule("N09", 2, lambda f: f.level == "MT", lambda f: [
        _("Medium-voltage connection per CEI 0-16:2026-07, section 8.8; for generation up to 30 kW the requirements of "
          "CEI 0-21 apply."),
        _("Between the generators and the network there are the interface device (DDI) and the generator device (DDG): "
          "two circuit breakers in series, or a breaker and a contactor, in the user's installation (8.8.3). Inverters "
          "are tested per Annex N."),
        _("Above 400 kW a back-up trip for failure of the DDI to open is provided, with a delay of at most 1 s and "
          "manual reset (8.8.7.3). Parallel operation is governed by the operating agreement with the distributor.")],
        lambda: _("CEI 0-16:2026-07 8.8, 8.8.3, 8.8.7.3, Annex N")),
    Rule("N10", 2, lambda f: f.level == "MT" and f.p_nominal_kw >= 100, lambda f: [
        _("The PV system, with nominal power (the lower of module and inverter power) of at least 100 kW and connected "
          "at MV, falls under the RIGEDI procedure of Annex A.72 to the Terna Grid Code (ARERA 385/2025/R/eel, art. 2)."),
        _("The system has a Central Plant Controller (CCI) per CEI 0-16, Annexes O and T, with the PF2 function 'active "
          "power limitation on external DSO command', installed and active at the commissioning date (ARERA "
          "385/2025/R/eel, arts. 3.1 and 4.1).")],
        lambda: _("ARERA 385/2025/R/eel arts. 2-4; CEI 0-16 Annexes O and T")),
    Rule("N11", 2, lambda f: f.level == "AT", lambda f: [
        _("Connection to the national transmission network: the Terna Grid Code and the connection offer (STMG) apply. "
          "CEI 0-16 covers distribution networks and, above 35 kV, only users fed by a dedicated line from a "
          "distributor's primary substation (CEI 0-16:2026-07, sect. 1)."),
        _("If the request to Terna was made for a load-only connection, the generation inside the user's installation "
          "must be notified and the request updated. Interface protection and generator tests are to be agreed with "
          "Terna.")],
        lambda: _("CEI 0-16:2026-07 sect. 1 (p. 7); Terna Grid Code")),
    # 3. Fire safety
    Rule("N13", 3, lambda f: f.fire is True, lambda f: [
        _("The system serves premises subject to fire prevention controls: the fire brigade guidelines DCPREV 14030 of "
          "01/09/2025 apply to PV systems with DC voltage up to 1500 V on buildings, pergolas, shelters and canopies of "
          "such premises or interfering with them."),
        _("The installation changes the fire safety conditions and may increase the risk (sect. 2.2): it must be "
          "assessed and, where needed, the fire prevention file updated. Where the Fire Prevention Code (DM "
          "03/08/2015) applies, its additional requirements of S.10.6, in particular S.10.6.1 and S.10.6.2, are "
          "followed (3.2.1 point 4, 3.3.5.2 point 3)."),
        _("An emergency isolation device is provided, in a signposted position, protected from fire and accessible to "
          "rescuers, separating the installation from all sources including the PV generator (3.3.5.2)."),
        _("The system is protected against overcurrents, insulation faults, series faults, overvoltages and reverse "
          "currents (3.3.5.3). The sign required by point 3.3.5.4 is placed in the generator area and every 10 m along "
          "the DC wiring."),
        _("Text of the sign (in Italian): 'ATTENZIONE: IMPIANTO FOTOVOLTAICO IN TENSIONE DURANTE LE ORE DIURNE (… "
          "Volt)', i.e. 'WARNING: PV SYSTEM LIVE DURING DAYLIGHT HOURS (… V)' (3.3.5.4)."),
        _("The system is built to good practice per CEI 64-8 and guide CEI 82-25 (sect. 2.3). Maintenance is recorded "
          "in the fire safety register, with checks every two years and periodic thermography (ch. 5).")],
        lambda: _("DCPREV 14030 of 01/09/2025 sect. 1.2, 2.2, 2.3, 3.2.1, 3.3.5.2-3.3.5.4, ch. 5; Fire Prevention Code "
                  "S.10.6.1-S.10.6.2")),
    Rule("N14", 3, lambda f: f.fire is False, lambda f: [
        _("The premises are not subject to fire prevention controls: the fire brigade guidelines DCPREV 14030/2025 "
          "remain a useful reference for design, installation, operation and maintenance (sect. 1.2); good practice "
          "applies (CEI 64-8 section 712, guide CEI 82-25).")],
        lambda: _("DCPREV 14030/2025 sect. 1.2 p. 4")),
    Rule("N15", 3, lambda f: f.fire is True and "BAPV" in f.installs, lambda f: [
        _("Modules applied above the roof (BAPV): panels are grouped in sub-arrays no larger than 20 m in any "
          "direction, separated by corridors of at least 2 m free of everything but cables, with a strip of at least "
          "1 m free from the roof edge (3.3.5.1 points 2 and 7)."),
        _("Panels, wiring, inverters and switchboards are at least 1 m from smoke vents, other openings and the "
          "plant on the roof (point 3), in horizontal projection on pitched roofs (point 4), and 1 m from the "
          "fire compartment walls below, except on fire-resistant roofs (point 5)."),
        _("On saw-tooth roofs the panels keep 1 m from the windows of the facing pitch and a 0.1 m clearance on the "
          "adjacent pitch (point 6); with 2 m zones free in one direction a sub-array may reach 30 m in the other "
          "(point 8)."),
        _("To reduce those distances, panels of limited fire propagation (e.g. glass-glass of class B-s2,d0) with "
          "fire-resistant rooflights are a compensating measure, judged on the view factor (3.3.5.1 point 6)."),
        _("The spread of fire from the panels to the building is limited per sect. 4.2: case 1, incombustible roof "
          "structure and elements (class A1, EN 13501-1); case 2, under the panels a layer of at least EI 30 with a "
          "continuous A1 layer, extended 2 m beyond them (points 3-4)."),
        _("Otherwise, case 3a: panels of at least class E (EN 13501-1) and Broof(T1-T4) on a roof Broof(T3, T4) (EN "
          "13501-5, point 6), or a test of the panel-roof system per CEI TS 82-89 with a class not below Crv "
          "(points 7-8); case 3b, a specific fire risk analysis (point 9).")],
        lambda: _("DCPREV 14030/2025 sect. 3.3.5.1 (p. 13-16), 4.2 (p. 20-22)")),
    Rule("N16", 3, lambda f: f.fire is True and "BIPV" in f.installs, lambda f: [
        _("Modules integrated in the roof (BIPV): compliant with CEI EN 61730-2 and, for the mounting category, with CEI "
          "EN 50583-1; fire classified per UNI EN 13501-1 as building envelope elements (sect. 4.4)."),
        _("For civil buildings with a fire height above 12 m the solution is consistent with chapter V.13 of the Fire "
          "Prevention Code (building envelopes).")],
        lambda: _("DCPREV 14030/2025 sect. 4.4")),
    Rule("N18", 3, lambda f: f.fire is True and "canopy" in f.installs, lambda f: [
        _("Modules on canopies, shelters or car-park roofs: if the panels are the only roofing element (BIPV, e.g. "
          "glass-glass) they have a reaction-to-fire class of at least B-s2,d0 per EN 13501-1 (sect. 4.5)."),
        _("For BAPV panels above car-park roofs not interfering with the premises no reaction-to-fire class is "
          "required (sect. 4.5). Interfering canopies (close to the building, or with inverters and DC section within "
          "its volume) fall under the guidelines (sect. 1.2).")],
        lambda: _("DCPREV 14030/2025 sect. 1.2 p. 2, 4.5")),
    # 4. Minimum renewable capacity obligation
    Rule("N24", 4, lambda f: minimum(f) is not None, _n24,
         lambda: _("Legislative Decree 199/2021 art. 26, Annex III Sect. B-C (GU no. 15 of 20/01/2026)")),
    Rule("N25", 4, lambda f: f.subject and f.region == "Lombardia" and f.permit_2027, lambda f: [
        _("In Lombardy, for permit applications from 01/01/2027, k is increased: 0.08 kW/m² for data centres "
          "(Delegated Regulation (EU) 2024/1364) and logistics over 3 ha, 0.06 kW/m² for logistics up to 3 ha and "
          "large retail, 0.05 kW/m² otherwise."),
        _("Source: resolution XII/6153 of 11/05/2026, implemented in the Lombardy building energy rules (decree 6437 "
          "of 15/05/2026), point 6.27. For extensions the increased k applies to the ground projection of the "
          "extended part."),
        _("The rules in force on the date of the permit application apply (point 4.7). For new buildings the share of "
          "thermal consumption to be covered by renewables is 65% (point 6.14 c iv); any exemption for technical or "
          "economic impossibility is justified in the technical report (point 6.16 v).")],
        lambda: _("Lombardy building energy rules (decree 6437/2026) points 4.7, 6.14, 6.16, 6.27; DGR XII/6153/2026")),
    Rule("N26", 4, lambda f: f.region == "Lombardia" and f.use == "data_centre", lambda f: [
        _("For data centres in Lombardy, Regional Law 11/2026 (art. 2 par. 1 b, art. 4 par. 5) and resolution XII/6645 "
          "of 03/08/2026 (Annex A, sect. 2.2) require maximum use of the site's available surfaces: roofs, car parks, "
          "canopies, yards and open areas."),
        _("The ratio RS between the area occupied by the systems and the available area is at least 60%; unused "
          "surfaces are justified in a sworn technical report. The energy report of Annex B is mandatory; the minimum "
          "P = k × S alone is not enough.")],
        lambda: _("Lombardy Regional Law 11/2026 arts. 2, 4; DGR XII/6645/2026 Annex A sect. 2.2, Annex B")),
    Rule("N20", 4, lambda f: f.subject and bool({"BAPV", "BIPV"} & f.installs), lambda f: [
        _("For the obligation (Annex III, Sect. C p. 3), on pitched roofs the modules are flush or integrated, with the "
          "same slope and orientation as the roof; on flat roofs the module mid-axis does not exceed the minimum "
          "parapet height, or 30 cm above the roof where there is no parapet.")],
        lambda: _("Legislative Decree 199/2021 Annex III Sect. C p. 3 (GU no. 15/2026)")),
    Rule("N19", 4, lambda f: f.subject and "canopy" in f.installs, lambda f: [
        _("For the obligation, the system on canopies counts if they lie within the building's ancillary area, i.e. "
          "the buildings' footprint plus an adjacent area no larger than three times the footprint; ancillary areas "
          "are not included in S (Annex III, Sect. C p. 2).")],
        lambda: _("Legislative Decree 199/2021 Annex III Sect. C p. 2 (GU no. 15/2026)")),
    Rule("N21", 4, lambda f: "ground" in f.installs, lambda f: [
        _("A ground-mounted system does not count towards the buildings' minimum capacity obligation (Annex III, Sect. "
          "C p. 2) and is outside the fire brigade guidelines on PV in buildings (DCPREV 14030/2025, sect. 1.2).")],
        lambda: _("Legislative Decree 199/2021 Annex III Sect. C; DCPREV 14030/2025 1.2")),
    # 5. Permitting regime and storage
    Rule("N23", 5, lambda f: True, lambda f: [
        _("Permitting: under the renewables consolidated act (Legislative Decree 190/2024, updated by Legislative "
          "Decree 178/2025) a system on existing buildings or structures or their ancillary areas is a free activity up "
          "to 12 MW, outside zone A and free of heritage and landscape constraints (Annex A, Sect. I, letters a and "
          "b)."),
        _("For a free activity the single form (Part III of the Modello Unico, Ministerial Decree MASE 223/2026) is "
          "filed on the GSE SUER platform within five days of commissioning (art. 5 par. 2, art. 7 par. 10). For a "
          "new building the system is part of the building's permit (Presidential Decree 380/2001)."),
        _("The single form of Ministerial Decree 19/05/2015 is extended to systems up to 50 kW (Legislative Decree "
          "199/2021, art. 25 par. 3). Connection is requested from the network operator under the TICA (ARERA 99/08) "
          "and the plant is registered in Terna's GAUDÌ system.")],
        lambda: _("Legislative Decree 190/2024 arts. 5, 7 and Annex A Sect. I (p. 19); DM MASE 223/2026; Legislative "
                  "Decree 199/2021 art. 25 (GU 15/2026)")),
    Rule("N27", 5, lambda f: "ground" in f.installs, lambda f: [
        _("For a ground-mounted system the renewables consolidated act (Legislative Decree 190/2024, Annex A, Sect. "
          "I) allows free activity up to 5 MW in industrial, craft and commercial zones (letter c) and up to 1 MW "
          "adjacent to the building served outside zone A (letter b.2); constraints and suitable areas must be "
          "checked.")],
        lambda: _("Legislative Decree 190/2024 Annex A Sect. I (p. 19)")),
    Rule("N22", 5, lambda f: f.storage, lambda f: [
        _("The storage system is part of the plant: converters with storage are also tested per Annex Bbis of CEI "
          "0-21, also when the storage shares the inverter with the PV generator (Bbis.1; at MV Annex Nbis of CEI "
          "0-16), and the permitting regimes of the renewables consolidated act also apply to storage (Legislative "
          "Decree 190/2024, art. 1 par. 1)."),
        _("For fire safety the storage is part of the system (DCPREV 14030/2025, sect. 2.1); for lithium batteries "
          "ventilation, off-gas detection and separation distances must be assessed.")],
        lambda: _("CEI 0-21:2026-07 Annex Bbis (p. 166); CEI 0-16:2026-07 Annex Nbis; Legislative Decree 190/2024; "
                  "DCPREV 14030/2025 sect. 2.1")),
]


def title(r: Rule, f: Facts) -> str:
    """The rule in a line, for the list of checks."""
    if r.id == "N24":
        _k, p = minimum(f) or (0.0, 0.0)
        return _("Minimum renewable capacity of the building: {p} kW").format(p=number(p, 1))
    return {
        "N01": _("Design to CEI 64-8/7, section 712"),
        "N02": (_("Design by a registered professional, until the supply and the premises are stated")
                if design(f) == "unknown" else _("Design by a registered professional (DM 37/2008)")),
        "N03": _("The installer's technical manager may design (DM 37/2008 art. 5 par. 1)"),
        "N12": _("Open-circuit voltage above 1500 V"),
        "N04": _("Low voltage up to 11.08 kW: the interface protection may be inside the inverter"),
        "N05": _("Low voltage above 11.08 kW: dedicated interface protection relay"),
        "N06": _("Above 20 kW: a back-up to the interface device"),
        "N07": _("Above 100 kW the distributor may propose medium voltage"),
        "N08": _("Several inverters: one interface device"),
        "N09": _("Medium-voltage connection (CEI 0-16)"),
        "N10": _("Medium voltage, 100 kW or more: RIGEDI and the plant controller (CCI)"),
        "N11": _("Connection to the transmission network (Terna)"),
        "N13": _("Activity subject to fire-brigade control: guidelines DCPREV 14030/2025"),
        "N14": _("Activity not subject to fire-brigade control"),
        "N15": _("Fire safety of modules above the roof (BAPV)"),
        "N16": _("Fire safety of modules integrated in the roof (BIPV)"),
        "N18": _("Fire safety of canopies and shelters"),
        "N25": _("Lombardy, permits from 01/01/2027: a higher k"),
        "N26": _("Lombardy, data centre: the most of the available surfaces (RS at least 60%)"),
        "N20": _("For the obligation: modules flush on pitched roofs, below the parapet on flat roofs"),
        "N19": _("For the obligation: canopies within the ancillary area"),
        "N21": _("Ground-mounted: outside the obligation and the fire guidelines for buildings"),
        "N23": _("Permitting: free activity, single form, connection request, GAUDÌ"),
        "N27": _("Ground-mounted: the limits of free activity"),
        "N22": _("Storage is part of the plant"),
    }.get(r.id, r.id)


def applying(f: Facts) -> list[Rule]:
    """The rules that apply, in the order of the chapters."""
    return sorted((r for r in RULES if r.applies(f)), key=lambda r: r.chapter)


def notes(f: Facts) -> list[tuple[str, list[tuple[Rule, list[str]]]]]:
    """The notes for the report: [(chapter title, [(rule, paragraphs)])] for the chapters with a rule."""
    names = chapter_names()
    out: list = []
    for r in applying(f):
        if not out or out[-1][0] != names[r.chapter]:
            out.append((names[r.chapter], []))
        out[-1][1].append((r, r.paragraphs(f)))
    return out


def notes_text(f: Facts) -> str:
    """The notes as plain text, to paste into the technical report: the title of each chapter, a paragraph
    per block, the source of each rule after its paragraphs."""
    blocks = []
    for title, rules in notes(f):
        blocks.append(title.upper())
        for r, paragraphs in rules:
            blocks += paragraphs
            blocks.append(_("Source: {source}").format(source=r.source()))
    return "\n\n".join(blocks) + "\n"
