"""Italian connection checks and the corresponding presentation texts."""
from __future__ import annotations
from meridiana.core.rules.types import Item
from meridiana.i18n import _, number
from . import rules
from .thresholds import BACKUP_KW, LV_KW, SPI_KW
SINGLE_PHASE_KW = 6.0           # CEI 0-21:2026 8.3: single-phase production up to 6 kW (10 if the DSO allows)
C021 = "CEI 0-21:2026-07"


def area_names() -> dict:
    return {"components": _("Components"), "layout": _("Layout"), "shade": _("Shading"), "strings": _("Strings (CEI 64-8/7)"),
            "connection": _("Connection"), "production": _("Production"),
            "consumption": _("Consumption"), "economics": _("Economics"), "rules": _("Rules and report notes"),
            "import": _("From PVsyst"), "defaults": _("Values still at their default")}


def string_why() -> dict:
    """Why a check of the strings (energy/stringing.py, by the key of the check without the input's number)
    fails or warns, and what to do about it."""
    return {
        "uoc": _("On the coldest morning the open-circuit voltage of the string is highest; above the maximum DC "
                 "voltage of the inverter or of the modules it damages them. Fewer modules in series, or an inverter "
                 "with a higher maximum voltage."),
        "mppt_low": _("At the hottest cell the voltage of the string is lowest; below the MPPT window the inverter "
                      "does not follow the maximum power and loses energy. More modules in series."),
        "mppt_high": _("At the coldest cell the voltage of the string is highest; above the MPPT window the inverter "
                       "limits the power. Fewer modules in series."),
        "imp": _("The operating current of the strings on this input is above what it takes: the inverter holds it "
                 "and loses a little power. Fewer strings on this input, or an inverter with more current per input."),
        "isc": _("The short-circuit current of the strings on this input, with the margin of the standard, is above "
                 "what the input stands. Fewer strings on this input, or an inverter with more current per input."),
        "fuse": _("With three or more strings on an input the reverse current of the others can exceed what a "
                  "module stands: a protection on each string is needed when 1.35 times the module's maximum fuse "
                  "is below it. Enter the module's maximum series fuse to check."),
        "fuserange": _("No fuse rating fits: 1.1 times the maximum short-circuit current is above the module's "
                       "maximum protection. Fewer strings on this input."),
        "strings": _("No string on any input: the inverter has nothing to convert. Give at least one string to an "
                     "input."),
        "range": _("The modules in series must keep the string within the inverter's voltage window at the hottest "
                   "and at the coldest cell. Choose a number within the range, or another inverter."),
        # the strings with power optimizers (task 22, energy/optimizers.py): SolarEdge's rules
        "opt_power": _("The module's power at STC must not exceed the optimizer's rated input power (modules with a "
                       "power tolerance up to +5 % are allowed). Choose a larger optimizer, or one module on each."),
        "opt_voc": _("On the coldest morning the module's open-circuit voltage is highest; above the optimizer's "
                     "absolute maximum input voltage it damages it. Choose an optimizer with a higher input voltage, or "
                     "one module on each."),
        "opt_isc": _("The module's short-circuit current (its front side, for a bifacial one) is above what the "
                     "optimizer takes. Choose an optimizer for higher currents (S1000, S1200 or S1400 take 20 A)."),
        "opt_imp": _("The module's operating current is above the optimizer's continuous input current: the optimizer "
                     "draws no more and loses a little power at the peaks. SolarEdge Designer computes the loss."),
        "opt_count": _("SolarEdge's table gives the fewest and the most optimizers in a string for this inverter: "
                       "fewer and the inverter cannot reach its string voltage, more and they cannot share it. Add or "
                       "take modules from the string, or join two strings."),
        "opt_modules": _("With two modules on an optimizer SolarEdge's table also gives the fewest and the most modules "
                         "in a string. Add or take modules from the string."),
        "opt_string_power": _("The power connected to a string is limited by SolarEdge's table for this inverter; with "
                              "several strings the higher limit holds only when they differ by 2000 W at most. Move "
                              "modules to another string, or make one more."),
        "opt_continuous": _("A string carries at most its optimizers' output current at the inverter's fixed voltage: "
                            "above it the peaks are cut. SolarEdge advises two strings when the inverter's AC power is "
                            "above that limit."),
        "opt_toggle": _("The S1200 on an SE33.3K needs the string voltage at 850 V, which SetApp offers only in some "
                        "countries. Ask SolarEdge, or choose the S1000 or the S1400."),
        "opt_fuses": _("The S1400 gives up to 24 A: an inverter with integrated 25 or 30 A DC fuses takes SolarEdge's "
                       "neutral links instead of them. Check the inverter's part number."),
        "opt_gap": _("On one inverter unit SolarEdge allows at most 5 optimizers between the shortest and the longest "
                     "string. Make the strings more alike."),
        "opt_dc_max": _("The modules' power at STC is above the inverter's maximum DC power of its datasheet. Fewer "
                        "modules, or a larger inverter."),
        "opt_min_dc": _("SolarEdge's table asks the commercial inverters for 11 kW at STC at least. More modules, or a "
                        "smaller inverter."),
        "opt_hub": _("The Home Hub takes only optimizers with one module each. Choose one module on each optimizer."),
        "opt_rules": _("SolarEdge's tables do not put this optimizer with this inverter. Choose another optimizer in "
                       "the Plant."),
        "opt_none": _("None of SolarEdge's optimizers in the catalogue takes this module (its power, Voc or Isc). "
                      "Choose one by hand, or another module."),
    }


def string_detail(key: str) -> str:
    return string_why().get(key if key.startswith("opt_") else key.rstrip("0123456789"), "")


def connection(p_kw: float, phases: int | None, chosen: bool, level: str = "BT", auto: bool = True) -> list[Item]:
    """What the connection asks of a production plant of this nominal power: for a PV plant the lower of the
    inverters' and the modules' power (CEI 0-21:2026-07 3.61, p. 16)."""
    out = []
    if p_kw <= 0:
        return out
    kw = number(p_kw, 2)
    if level != "BT":
        text = (_("{kw} kW: connection in medium voltage, under CEI 0-16") if level == "MT" else
                _("{kw} kW: connection to the transmission network, under Terna's grid code")).format(kw=kw)
        detail = (_("The level follows the nominal power, as Table 4 of CEI 0-16 indicates; the distributor decides "
                    "it in the connection offer. The site's properties take the level when it is known.") if auto else
                  _("The level is the one chosen in the site's properties."))
        out.append(Item("info", "connection", text, rules.C016_TAB4, ("site",), detail=detail))
    else:
        if p_kw > LV_KW:
            out.append(Item("warn", "connection", _("{kw} kW: above 100 kW the distributor may propose medium "
                                                    "voltage").format(kw=kw), f"{C021}, 6.3, Tab. 5, p. 33", ("site",),
                            detail=_("CEI 0-21 covers low-voltage connections up to 100 kW; above it the distributor "
                                     "may connect in medium voltage under CEI 0-16, with a transformer cabin and its "
                                     "costs. Ask the distributor for the connection offer before the final design, "
                                     "or choose medium voltage in the site's properties.")))
        if phases == 1:
            ok = p_kw <= SINGLE_PHASE_KW
            out.append(Item("ok" if ok else "fail", "connection",
                            (_("Single-phase connection of {kw} kW, within 6 kW") if ok else
                             _("Single-phase connection of {kw} kW: above 6 kW it is three-phase")).format(kw=kw),
                            f"{C021}, 8.3, p. 65", ("phase", "production"),
                            detail="" if ok else _("CEI 0-21 allows single-phase production up to 6 kW, 10 kW only if "
                                                   "the distributor agrees. Choose a three-phase inverter in the "
                                                   "catalogue, or ask the distributor for the 10 kW limit.")))
        elif phases is None and p_kw > SINGLE_PHASE_KW:
            out.append(Item("info", "connection", _("{kw} kW: three-phase connection, or single-phase up to 10 kW if "
                                                    "the distributor allows").format(kw=kw), f"{C021}, 8.3, p. 65",
                            detail=_("Above 6 kW the production is connected three-phase; the distributor may allow "
                                     "single-phase up to 10 kW. The phases are checked once an inverter is chosen.")))
        if p_kw > SPI_KW:
            out.append(Item("info", "connection", _("Above 11.08 kW the interface protection is a dedicated relay"),
                            f"{C021}, 8.6.2, p. 96",
                            detail=_("The interface protection inside the inverter is allowed up to 11.08 kW; above "
                                     "it a dedicated relay opens the interface device. It goes into the design and "
                                     "into the costs of the switchboard.")))
        else:
            out.append(Item("ok", "connection", _("Up to 11.08 kW the interface protection may be the one inside the "
                                                  "inverter"), f"{C021}, 8.6.2, p. 96"))
        if p_kw > BACKUP_KW:
            out.append(Item("info", "connection", _("Above 20 kW the interface device needs a backup device that opens "
                                                    "if it fails to"), f"{C021}, 8.2.2.4, p. 63",
                            detail=_("A second device, downstream of the interface device, opens when the first does "
                                     "not: the general switch or the inverter's own may serve. It goes into the "
                                     "single-line diagram.")))
    if not chosen:
        out.append(Item("info", "connection", _("The inverter is sized by itself: choose one from the catalogue"), "",
                        ("phase", "production"),
                        detail=_("Meridiana takes an inverter of typical values from the DC/AC ratio: its phases, its "
                                 "MPPT window and its inputs are not checked. The Production page chooses one from "
                                 "the catalogue."), window_only=True))
    return out


def rule_items(f: rules.Facts) -> list[Item]:
    """The rules that apply, one line each (their paragraphs go into the report), and the minimum renewable
    capacity of the building against the system."""
    out = []
    if f.obligation == "" and f.footprint_m2 > 0:
        out.append(Item("info", "rules", _("Say whether the building must reach a minimum renewable capacity"),
                        _("Legislative Decree 199/2021 art. 26, Annex III"), ("site",),
                        detail=_("A new building or a major renovation must have a renewable electrical capacity of "
                                 "k × S (Legislative Decree 199/2021, Annex III); the check needs to know which case "
                                 "this is. The site's properties have the choice."), window_only=True))
    if rules.design(f) == "unknown":
        out.append(Item("info", "rules", _("Say the supply's contracted power, the floor area and the use of the "
                                           "premises"), _("DM 37/2008 art. 5 par. 2 (p. 4)"), ("site",),
                        detail=_("Who may design depends on them (DM 37/2008 art. 5 par. 2): until they are known, "
                                 "the design of a registered professional is taken as due. The site's properties "
                                 "have the fields."), window_only=True))
    need = rules.minimum(f)
    if need is not None and f.p_dc_kw > 0:
        k, p_min = need
        ok = f.p_dc_kw + 1e-9 >= p_min
        out.append(Item("ok" if ok else "warn", "rules",
                        (_("{p} kWp, at least the {min} kW the building must have (k = {k} kW/m², S = {s} m²)") if ok else
                         _("{p} kWp, below the {min} kW the building must have (k = {k} kW/m², S = {s} m²)")).format(
                            p=number(f.p_dc_kw, 1), min=number(p_min, 1), k=number(k, 3),
                            s=number(f.footprint_m2, 0, grouping=True)),
                        _("Legislative Decree 199/2021 art. 26, Annex III Sect. B p. 3"), ("site",),
                        detail="" if ok else _("The building permit is refused if the minimum is not reached (art. 26 "
                                               "par. 4). Lay more modules on the building or in its ancillary areas: "
                                               "ground-mounted modules do not count.")))
    for r in rules.applying(f):
        paragraphs = r.paragraphs(f)
        out.append(Item(r.level, "rules", f"{r.id} · {rules.title(r, f)}", r.source(), ("site",),
                        detail=paragraphs[0] if paragraphs else "", window_only=not rules.in_document(r, f)))
    return out



def layout_note(name, sfid, note):
    if "NTC" not in note:
        return None
    return Item("warn", "layout", _("{name}: ballast alone does not restrain the modules on a roof "
                                                      "slab").format(name=name), "NTC 2018 7.2.4; CEI 82-25/3 6.2",
                                  ("subfield", sfid),
                                  detail=_(note) + " " + _("Choose an anchored mounting in the sub-field's properties, "
                                                           "or add tie-downs to the design."))
