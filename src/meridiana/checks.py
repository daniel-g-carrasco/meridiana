"""What needs the designer's attention, gathered from every part of the project: the layout's notes, the
shade the obstacles cast, the strings' checks of CEI 64-8/7, what the connection asks, the production's
notes, the guesses still standing in for data, and the rules that apply (rules.py), whose paragraphs go into
the report. Each item has its level, where it comes from (a standard with its edition, article and page, or
Meridiana's own reading) and the object or page it is about, so that the list leads to the place to act;
some carry a fix the window can apply (and undo).

No Qt here: the window shows the list (ui/checks_page.py)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from . import rules
from .i18n import _, number

LEVELS = ("fail", "warn", "info", "ok")
SPI_KW = 11.08                  # CEI 0-21:2026 8.6.2: above it a dedicated interface protection
SINGLE_PHASE_KW = 6.0           # CEI 0-21:2026 8.3: single-phase production up to 6 kW (10 if the DSO allows)
BACKUP_KW = 20.0                # CEI 0-21:2026 8.2.2.4: above it a backup to the interface device
LV_KW = 100.0                   # CEI 0-21:2026 6.3 Table 5: up to 100 kW low voltage
OBSTACLE_SHADE = 0.03           # share of the irradiance lost to obstacles above which the layout is worth a look
C021 = "CEI 0-21:2026-07"


@dataclass
class Item:
    level: str                  # "fail", "warn", "info", "ok"
    area: str
    text: str                   # one sentence, the problem first, the number that counts (study 17, F.6)
    source: str = ""
    target: tuple = ()          # ("subfield", id), ("building", id), ("phase", id), ("site",)
    fix: tuple = ()             # ("energy", path, value), ("edit", kind, id, changes), ("action", what, kind, id),
                                # ("compute",)
    fix_label: str = ""         # what the fix does, in a few words
    detail: str = ""            # why, and what to do (also when there is no fix): two or three sentences, shown
                                # on request (task 17e)


TEXT_LENGTH = 90                # the most characters a text may have: the detail takes the rest


def area_names() -> dict:
    return {"layout": _("Layout"), "shade": _("Shading"), "strings": _("Strings (CEI 64-8/7)"),
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


def left_detail() -> str:
    """Why modules in no string are a problem, and what to do."""
    return _("A module in no string is connected to no inverter: in the real plant it produces nothing, while the "
             "production counts it as if it were connected. Draw a string through it, or «Complete the strings»: "
             "Meridiana proposes strings for the modules left out on the free inputs, and yours stay as they are.")


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
                                 "the catalogue.")))
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
                                 "this is. The site's properties have the choice.")))
    if rules.design(f) == "unknown":
        out.append(Item("info", "rules", _("Say the supply's contracted power, the floor area and the use of the "
                                           "premises"), _("DM 37/2008 art. 5 par. 2 (p. 4)"), ("site",),
                        detail=_("Who may design depends on them (DM 37/2008 art. 5 par. 2): until they are known, "
                                 "the design of a registered professional is taken as due. The site's properties "
                                 "have the fields.")))
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
                        detail=paragraphs[0] if paragraphs else ""))
    return out


def gather(project, results: dict, energy: dict | None, inverter=None, chosen: bool = False) -> list[Item]:
    """Every item, most serious first. `results` are the layouts by sub-field, `energy` what the energy job
    gave (or None before it ran), `inverter` the InverterSpec of the project."""
    items: list[Item] = []
    energy = energy or {}
    filled = False
    for sf in project.subfields:
        r = results.get(sf.id)
        if isinstance(r, Exception):
            items.append(Item("fail", "layout", _("{name}: the layout could not be computed ({error})").format(
                name=sf.name, error=r), "", ("subfield", sf.id),
                detail=_("Nothing is laid and nothing is computed for this sub-field. Check its outline and the "
                         "margins in its properties: an area too small, or outside its roof, gives no layout.")))
            continue
        if not sf.filled:
            items.append(Item("info", "layout", _("{name}: the modules are not laid yet").format(name=sf.name), "",
                              ("subfield", sf.id), ("action", "fill", "subfield", sf.id), _("Lay the modules"),
                              detail=_("The sub-field has its outline but no modules, so nothing is computed for it. "
                                       "«Lay the modules» fills it with the module and the mounting of its "
                                       "properties.")))
            continue
        filled = True
        if sf.manual:
            from .energy import system
            items += manual_items(project, sf, r, system.shadow_exclusions)
        unmatched = len(getattr(r, "unmatched", None) or [])
        if unmatched:
            from .i18n import ngettext
            items.append(Item("info", "layout", ngettext(
                "{name}: {n} module taken out by hand is no longer in the layout",
                "{name}: {n} modules taken out by hand are no longer in the layout", unmatched).format(
                    name=sf.name, n=unmatched), "", ("subfield", sf.id),
                detail=_("The layout changed after they were taken out (another module, pitch or row): the place they "
                         "had is not there any more. Check the layout, and take out again what should not be "
                         "there.")))
        for note in getattr(r, "notes", []) or []:
            if "NTC" in note:
                items.append(Item("warn", "layout", _("{name}: ballast alone does not restrain the modules on a roof "
                                                      "slab").format(name=sf.name), "NTC 2018 7.2.4; CEI 82-25/3 6.2",
                                  ("subfield", sf.id),
                                  detail=_(note) + " " + _("Choose an anchored mounting in the sub-field's properties, "
                                                           "or add tie-downs to the design.")))
            else:
                items.append(Item("warn", "layout", f"{sf.name}: {_(note)}", "", ("subfield", sf.id)))
    if not project.subfields:
        items.append(Item("info", "layout", _("No sub-field yet: draw one on a roof or on the ground"), "",
                          detail=_("The modules are laid in sub-fields: a sub-field is an outline on a roof or on the "
                                   "ground with its module, its mounting and its distances. The Draw tools make "
                                   "one.")))

    sim = energy.get("sim")
    if sim is not None:
        for a in sim.arrays:
            lost = float(a.get("obstacle_shading") or 0.0)
            if lost > OBSTACLE_SHADE:
                sfid = str(a["key"]).split(".")[0]
                sf = next((s for s in project.subfields if s.id == sfid), None)
                fix, label = (), ""
                # by hand the shadows are a check of their own (manual_items): the option would move nothing
                if sf is not None and not sf.layout_params().shade_free and not sf.manual:
                    w = vars(project.fill_params(sf).window)
                    fix = ("edit", "subfield", sfid, {"params.shade_free": True})
                    label = _("Keep the modules out of the obstacles' shadows on {day}/{month}, {start} to {end} "
                              "solar time").format(day=w["day"], month=w["month"], start=number(w["start"], 1),
                                                   end=number(w["end"], 1))
                    now = getattr(results.get(sfid), "count", None)
                    # the energy job counts them in its thread; computed here only when it did not
                    counts = energy.get("shade_free_counts")
                    then = counts.get(sfid) if counts is not None else count_out_of_shadows(project, sf)
                    if now is not None and then is not None:
                        label += ": " + _("{then} modules instead of {now}").format(then=then, now=now)
                items.append(Item("warn", "shade", _("{name}: the obstacles take {pct}% of the irradiance").format(
                    name=a["name"], pct=number(100 * lost, 1)), _("Meridiana: shading of the obstacles"),
                    ("subfield", sfid), fix, label,
                    detail=_("Chimneys, parapets and plant shade the modules nearby, and a shaded module drags its "
                             "whole string. Keep the modules out of the shadows of the design day (the fix), move the "
                             "sub-field, or give the obstacles a wider clearance in their properties.")))
        for note in sim.notes:
            items.append(Item("warn", "production", note, "", ("phase", "production"),
                              detail=_("The inverter cuts what the modules give above its AC power. A lower DC/AC "
                                       "ratio, a larger inverter or fewer modules shrink the loss; the Production "
                                       "page shows it among the losses.") if "clip" in note else ""))
    elif filled:
        items.append(Item("info", "production", energy.get("error_sim") or
                          _("Compute the production to check the shading, the strings and the balance"), "",
                          ("phase", "production"), ("compute",), _("Compute"),
                          detail=_("Shading, strings and the balance come from the hourly year: until it is computed "
                                   "the checks that need it are missing.")))
    for note in energy.get("notes") or []:
        items.append(Item("info", "production", note, "", ("phase", "production")))

    strings = energy.get("strings") or {}
    plan = strings.get("plan")
    better = strings.get("suggestion")
    fix, fix_label = (), ""
    if plan is not None and not plan.suggested and better is not None and better.ok:
        fix = ("energy", "strings", None)
        fix_label = _("Use the suggested strings: {n} in series, {per} on the inputs").format(
            n=better.n_series, per=" + ".join(str(x) for x in better.strings_per_mppt))
    if plan is not None:
        for c in plan.checks:
            if c.level in ("fail", "warn"):
                items.append(Item(c.level, "strings", f"{c.label}: {c.detail}", "CEI 64-8/7:2024",
                                  ("phase", "production"), fix, fix_label, detail=string_detail(c.key)))
        if plan.ok:
            items.append(Item("ok", "strings", _("{n} modules in series, every check passed").format(n=plan.n_series),
                              "CEI 64-8/7:2024", ("phase", "production")))
    wiring = energy.get("wiring")
    if wiring is not None and wiring.left:
        items.append(Item("warn", "strings", _("{n} modules are in no string").format(n=len(wiring.left)),
                          "", ("phase", "production"), fix, fix_label, detail=left_detail()))

    f = rules.facts(project, results, energy, inverter)
    if inverter is not None and filled:
        items += connection(f.p_nominal_kw, inverter.phases, chosen, f.level, f.level_auto)
    if filled:
        items += rule_items(f)

    imported = (project.energy or {}).get("pvsyst_import") or {}
    source = _("PVsyst file {file}").format(file=imported.get("file", ""))
    details = {"missing": _("PVsyst's file does not carry it: enter it in Meridiana before trusting the results."),
               "approximated": _("Meridiana has no exact equivalent: the value nearest to PVsyst's was taken, and the "
                                 "results may differ a little."),
               "not_imported": _("Meridiana does not read this part of PVsyst's file yet: enter it by hand if it "
                                 "matters.")}
    for level, key in (("warn", "missing"), ("info", "approximated"), ("info", "not_imported")):
        items += [Item(level, "import", text, source, detail=details[key]) for text in imported.get(key, [])]

    from .energy.consumption import Consumption
    if filled and not Consumption.from_dict(project.consumption).has_data():
        items.append(Item("info", "consumption", _("The consumption is guessed from the project: enter the bills or the "
                                                   "POD's curve"), "", ("phase", "consumption"),
                          detail=_("Without data Meridiana takes a user of the size of the system; self-consumption "
                                   "and the balance depend on it. The Consumption page takes the yearly kWh, the "
                                   "bills or the curve of the POD.")))
    econ = energy.get("econ")
    if econ is not None and {"buy_f1", "sell", "capex_per_kwp"} <= set(_defaults(project)):
        items.append(Item("info", "economics", _("Prices and costs are indicative defaults: enter those of the bill "
                                                 "and of the offer"), "", ("phase", "economics"),
                          detail=_("The balance and the payback are only as good as the prices: Meridiana's are "
                                   "national averages. The Balance page takes the price of the bill, the sale price "
                                   "and the cost of the offer.")))
    items.sort(key=lambda i: LEVELS.index(i.level))
    return items


FIRE_SOURCE = "DCPREV 14030/2025 sect. 3.3.5.1 (p. 13-16)"     # the 1 m, 20 m and 2 m of layout.py and rules.py


def manual_items(project, sf, result, shade=None) -> list[Item]:
    """The checks of a sub-field laid by hand (task 16c, step 6; study 16, C.5): what the automatic layout makes sure
    of by building it, said on the rows as they are, as Aurora flags errors in colour without blocking (study 05):
    the rows by hand (to know); under the fire-brigade rules the groups of modules closer than 2 m that reach beyond
    20 m and the corridors left narrower than 2 m; the modules on an exclusion or beyond the edge band; the modules
    in the obstacles' shadows on the design day (`shade`, energy.system.shadow_exclusions, the same rule as the layout
    out of the shadows). Each with «Lay again automatically» as its fix."""
    from shapely.geometry import Polygon

    from . import layout, model
    if result is None or isinstance(result, Exception) or not sf.manual:
        return []
    fix, label = ("action", "relayout", "subfield", sf.id), _("Lay again automatically")
    here = ("subfield", sf.id)
    items = [Item("info", "layout", _("{name}: rows by hand, not laid again by the automatic layout").format(
        name=sf.name), "", here, fix, label,
        detail=_("The rows were drawn, moved or exploded by hand: Meridiana lays them as they are and checks them, and "
                 "a new pitch or new margins do not move them. «Lay again automatically» gives them back to the "
                 "layout, and the changes by hand are lost."))]
    placed = result.modules
    if not placed:
        return items
    p = project.fill_params(sf)
    frame = layout.Frame.of(result.azimuth, result.tilt, p.mounting in layout.FLUSH)
    size = layout.Sizes.of(project.module_of(sf), p, result.tilt)
    import numpy as np
    import shapely
    # the modules as one array of shapes: a sub-field of 4,000 modules exploded is checked in a few tens of ms
    polys = shapely.polygons(np.array([m.corners for m in placed], dtype=float))

    def touching(zone) -> int:
        return int(np.count_nonzero(shapely.area(shapely.intersection(polys, zone)) > 1e-4))
    if p.fire_rules:
        for members in layout.clusters(placed, p.fire_corridor):
            reach = layout.extent(placed, members, frame)
            if reach <= p.fire_group + layout.DISTANCE_TOLERANCE:
                continue
            items.append(Item("warn", "layout", _("{name}: group of {m} m, beyond the {limit} m").format(
                name=sf.name, m=number(reach, 1), limit=number(p.fire_group, 0)), FIRE_SOURCE, here, fix, label,
                detail=_("Modules closer than {corridor} m make one group, and a group reaches at most {limit} m in "
                         "every direction. Leave a corridor of {corridor} m across it, move the rows apart, or lay "
                         "the sub-field again automatically.").format(corridor=number(p.fire_corridor, 0),
                                                                     limit=number(p.fire_group, 0))))
            gaps = layout.narrow_gaps(placed, members, frame, size.along, p, result.clearance)
            if gaps:
                items.append(Item("warn", "layout", _("{name}: corridor of {m} m, below the {limit} m").format(
                    name=sf.name, m=number(gaps[0], 2), limit=number(p.fire_corridor, 0)), FIRE_SOURCE, here, fix,
                    label, detail=_("The rows left a gap between them that is narrower than a corridor: the groups on "
                                    "its two sides count as one. Widen it to {corridor} m.").format(
                                        corridor=number(p.fire_corridor, 0))))
    names, numbers = model.exclusion_names(), project.exclusion_numbers()
    for e in project.exclusions:
        if e.building != sf.building or len(e.ring) < 3:
            continue
        grow = e.clearance + (p.fire_edge if p.fire_rules and e.kind in ("vent", "opening", "plant") else 0.0)
        n = touching(Polygon([tuple(map(float, q)) for q in e.ring]).buffer(grow, join_style="mitre"))
        if n:
            from .i18n import ngettext
            what = f"{names.get(e.kind, e.kind)} {numbers[e.id]}"
            items.append(Item("warn", "layout", ngettext("{name}: {n} module on the exclusion {what}",
                                                         "{name}: {n} modules on the exclusion {what}", n).format(
                name=sf.name, n=n, what=what), FIRE_SOURCE if grow > e.clearance else "", here, fix, label,
                detail=_("Modules keep away from an exclusion and its clearance (1 m more for smoke vents, openings "
                         "and roof plant under the fire-brigade rules). Move the rows, take the modules out, or lay "
                         "the sub-field again automatically.")))
    edge = max(p.edge, p.fire_edge if p.fire_rules else 0.0)
    if edge > 0:
        inner = Polygon([tuple(map(float, q)) for q in sf.ring]).buffer(0).buffer(-edge, join_style="mitre")
        inner = inner.buffer(layout.DISTANCE_TOLERANCE)
        n = int(np.count_nonzero(shapely.area(shapely.difference(polys, inner)) > 1e-4))
        if n:
            from .i18n import ngettext
            items.append(Item("warn", "layout", ngettext("{name}: {n} module beyond the edge band of {m} m",
                                                         "{name}: {n} modules beyond the edge band of {m} m", n).format(
                name=sf.name, n=n, m=number(edge, 2)), FIRE_SOURCE if p.fire_rules and p.fire_edge >= p.edge else "",
                here, fix, label,
                detail=_("The modules stay inside the edge band of the sub-field (1 m from the roof edge under the "
                         "fire-brigade rules). Move the rows inwards, or lay the sub-field again automatically.")))
    if shade is not None:
        n = in_shade(project, sf, result, shade)
        if n:
            from .i18n import ngettext
            w = vars(p.window)
            items.append(Item("warn", "shade", ngettext("{name}: {n} module in the shade on the design day",
                                                        "{name}: {n} modules in the shade on the design day", n).format(
                name=sf.name, n=n), _("Meridiana: shading of the obstacles"), here, fix, label,
                detail=_("The obstacles cast their shadow on these modules on {day}/{month} between {start} and {end} "
                         "solar time, the day the pitch is computed for. Move them out of it, or lay the sub-field "
                         "again automatically out of the obstacles' shadows.").format(
                    day=w["day"], month=w["month"], start=number(w["start"], 1), end=number(w["end"], 1))))
    return items


_SHADED: dict = {}              # layout key of a sub-field by hand -> its modules in the shade (as _COUNTS)


def in_shade(project, sf, result, shade) -> int:
    """How many modules of the layout are in the obstacles' shadows of the design window (`shade(project, sf,
    window)` gives them as exclusions, energy.system.shadow_exclusions), kept by the layout's key."""
    import json

    from shapely.geometry import Polygon
    # by hand the layout's key leaves the shadows out (model.layout_key): every building and obstacle casts them
    key = json.dumps([project.layout_key(sf), [b.geometry_key() for b in project.buildings],
                      [[e.ring, e.kind, e.height, e.building] for e in project.exclusions]], default=str)
    with _COUNTS_LOCK:
        if key in _SHADED:
            return _SHADED[key]
    areas = [Polygon(e.ring, e.holes or None) for e in shade(project, sf, project.fill_params(sf).window)]
    n = 0
    if areas and result.modules:
        import numpy as np
        import shapely
        from shapely.ops import unary_union
        dark = unary_union(areas)
        polys = shapely.polygons(np.array([m.corners for m in result.modules], dtype=float))
        n = int(np.count_nonzero(shapely.area(shapely.intersection(polys, dark)) > 1e-4))
    with _COUNTS_LOCK:
        while len(_SHADED) >= COUNTS_KEPT:
            _SHADED.pop(next(iter(_SHADED)))
        _SHADED[key] = n
    return n


ESTIMATE_AREAS = ("consumption", "economics", "import")     # the guesses and approximations standing in for data
# the phase (phases.py) where each calculation's values are edited
RECORD_PHASES = (("sim", "production"), ("plan", "plant"), ("load", "consumption"), ("econ", "economics"))


def defaults_in_use(energy: dict | None) -> list[Item]:
    """The values Meridiana chose because none was given, read from the records of the calculations (the same
    table report.py prints last): one item each, for the «ready for delivery» view."""
    energy = energy or {}
    # the strings' plan: the first one of the plant (task 16d, as report.py takes it), or the one of before
    plant = energy.get("plant")
    plan = next((s.plan for s in getattr(plant, "strings", []) if s.plan is not None),
                (energy.get("strings") or {}).get("plan"))
    out, seen = [], set()
    for name, phase in RECORD_PHASES:
        holder = plan if name == "plan" else energy.get(name)
        record = getattr(holder, "record", None)
        for st in (record.steps if record is not None else []):
            for q in st.inputs:
                if q.source is None or q.source.kind != "default":
                    continue
                key = (st.title, q.label, q.text())
                if key in seen:
                    continue
                seen.add(key)
                out.append(Item("info", "defaults", _("{step}: {label} = {value}").format(step=st.title, label=q.label,
                                                                                            value=q.text()),
                                q.source.label, ("phase", phase),
                                detail=_("Meridiana chose this value because none was given: check it before the "
                                         "final design, or enter the one of the project.")))
    return out


@dataclass
class Group:
    """A section of the Checks panel: its items as indices into the list, the worst level inside."""
    key: tuple                  # ("level", lv), ("object", kind, id), ("area", area), ("delivery", what)
    name: str
    kind: str = ""              # the kind of the object (building, subfield, exclusion, site), for its icon
    items: list = field(default_factory=list)
    level: str = "ok"
    closed: bool = False        # shown closed by default (what passed)


BY = ("level", "object", "area", "delivery")


def delivery_names() -> dict:
    return {"fail": _("To fix"), "warn": _("To check"), "defaults": _("Values still at their default"),
            "estimates": _("Estimates in use")}


def grouped(items: list[Item], by: str, names: dict | None = None) -> list[Group]:
    """The items in sections. By level, in the order of LEVELS (F2, the default; what passed closed); by object,
    from `target` (the name from `names`, {(kind, id): name}; the site for what has no object), the groups
    ordered by their worst level; by area, as the list comes (worst first); «delivery»: what is to fix and to
    check, the values still at their default (area «defaults», from defaults_in_use) and the estimates in use
    (ESTIMATE_AREAS), for the Report phase."""
    if by not in BY:
        raise ValueError(f"grouped by {by!r}")
    names = names or {}
    groups: dict = {}

    def put(key, name, n, kind=""):
        g = groups.get(key)
        if g is None:
            g = groups[key] = Group(key, name, kind, level=items[n].level)
        else:
            g.level = worst((g.level, items[n].level))
        g.items.append(n)

    level_words = level_names()
    for n, it in enumerate(items):
        if by == "level":
            put(("level", it.level), level_words[it.level].capitalize(), n)
        elif by == "object":
            t = it.target
            if len(t) >= 2 and t[0] in OBJECTS:
                put(("object", t[0], t[1]), names.get((t[0], t[1]), t[1]), n, t[0])
            else:
                put(("object", "site", ""), names.get(("site", ""), _("Site")), n, "site")
        elif by == "area":
            put(("area", it.area), area_names().get(it.area, it.area), n)
        else:
            words = delivery_names()
            if it.level in ("fail", "warn"):
                put(("delivery", it.level), words[it.level], n)
            elif it.area == "defaults":
                put(("delivery", "defaults"), words["defaults"], n)
            elif it.area in ESTIMATE_AREAS and it.level != "ok":
                put(("delivery", "estimates"), words["estimates"], n)
    out = list(groups.values())
    if by == "level":
        out.sort(key=lambda g: LEVELS.index(g.key[1]))
        for g in out:
            g.closed = g.key[1] == "ok"
    elif by == "object":
        out.sort(key=lambda g: LEVELS.index(g.level))        # stable: the list's order within a level
    elif by == "delivery":
        order = ("fail", "warn", "defaults", "estimates")
        out.sort(key=lambda g: order.index(g.key[1]))
    return out


# where an item without a target is acted on, by its area: a phase of phases.py, None for every phase
PHASE_OF_AREA = {"layout": "model", "shade": "model", "strings": "production", "connection": "production",
                 "production": "production", "consumption": "consumption", "economics": "economics",
                 "rules": "model", "defaults": None, "import": None}


def phase_of(it: Item) -> str | None:
    """The phase (phases.py) where the item is acted on: the one its target names, the model for an object or the
    site, else by area; None for what belongs to every phase (what PVsyst's import left)."""
    t = it.target
    if len(t) >= 2 and t[0] == "phase":
        return t[1]
    if t and (t[0] in OBJECTS or t[0] == "site"):
        return "model"
    return PHASE_OF_AREA.get(it.area)


def shown_in_phase(it: Item, phase: str) -> bool:
    """What «Only this phase» keeps: the items acted on in `phase`, those of every phase, and those of the areas
    the phase declares (phases.Phase.areas: the Plant's strings and connection, the Report's rules)."""
    from . import phases
    try:
        areas = phases.by_id(phase).areas
    except KeyError:
        areas = ()
    return phase_of(it) in (None, phase) or it.area in areas


def in_phase(items: list[Item], phase: str) -> list[int]:
    """The items of a phase («Only this phase»), as indices."""
    return [n for n, it in enumerate(items) if shown_in_phase(it, phase)]


_COUNTS: dict = {}              # layout key of the sub-field out of the shadows -> its count (task 18c, step 5)
_COUNTS_LOCK = threading.Lock()
COUNTS_KEPT = 32


def count_out_of_shadows(project, sf) -> int | None:
    """How many modules the sub-field would keep out of the obstacles' shadows: what the fix costs. A layout
    with the shadows as exclusions (the energy job calls it in its thread), kept by everything that layout
    reads (model.layout_key): a change of the losses or of the money computes the year again, not this."""
    import copy

    from .energy import system
    alt = copy.deepcopy(sf)
    alt.params["shade_free"] = True
    key = project.layout_key(alt)
    with _COUNTS_LOCK:
        if key in _COUNTS:
            return _COUNTS[key]
    try:
        count = project.fill(alt, shade=system.shadow_exclusions).count
    except ValueError:
        count = None
    with _COUNTS_LOCK:
        while len(_COUNTS) >= COUNTS_KEPT:
            _COUNTS.pop(next(iter(_COUNTS)))
        _COUNTS[key] = count
    return count


def _defaults(project) -> list:
    from .energy.economics import Settings
    return Settings.from_dict(project.economics).defaults


def counts(items: list[Item]) -> dict:
    return {lv: sum(1 for i in items if i.level == lv) for lv in LEVELS}


def level_names() -> dict:
    return {"fail": _("to fix"), "warn": _("to check"), "info": _("to know"), "ok": _("passed")}


def mark_text(items: list[Item], mark, inside: bool = False) -> str:
    """What a mark of the project's tree stands for, in words, the worst first (Daniel, R30: «non si capisce cosa
    sono»): «1 to check, 3 to know in this object and inside» for the site and the groups, «… about this object» for
    an object."""
    n = counts([items[i] for i in mark.items])
    names = level_names()
    what = ", ".join(f"{n[lv]} {names[lv]}" for lv in LEVELS if n[lv])
    return (_("{counts} in this object and inside") if inside else _("{counts} about this object")).format(counts=what)


OBJECTS = ("building", "subfield", "exclusion")
SHOWN = ("fail", "warn", "info")        # what earns a mark on the views; what passed does not


@dataclass
class Mark:
    """What the views show on an object (study 12, C1): the worst level of its items, how many there are, which."""
    level: str
    count: int
    items: list = field(default_factory=list)       # indices into the list of items


def worst(levels) -> str:
    return min(levels, key=LEVELS.index)


def marks(items: list[Item], levels=SHOWN) -> dict:
    """(kind, id) -> Mark for every building, sub-field and exclusion an item is about, of the levels given."""
    out: dict = {}
    for n, it in enumerate(items):
        if it.level not in levels or len(it.target) < 2 or it.target[0] not in OBJECTS:
            continue
        key = (it.target[0], it.target[1])
        m = out.get(key)
        if m is None:
            out[key] = Mark(it.level, 1, [n])
        else:
            m.level, m.count = worst((m.level, it.level)), m.count + 1
            m.items.append(n)
    return out


def tree_marks(items: list[Item], levels=SHOWN) -> dict:
    """The marks of the project's tree, rising to the parents (study 12, C3): every object's, its group's
    ("group", "building"|"subfield"|"exclusion") and the site's ("site", ""), which gathers every item of the levels
    given, those about the site and the pages included."""
    out = dict(marks(items, levels))
    for (kind, _oid), m in list(out.items()):
        g = out.get(("group", kind))
        out[("group", kind)] = Mark(m.level if g is None else worst((g.level, m.level)), m.count + (g.count if g else 0),
                                    (g.items if g else []) + m.items)
    shown = [n for n, it in enumerate(items) if it.level in levels]
    if shown:
        out[("site", "")] = Mark(worst(items[n].level for n in shown), len(shown), shown)
    return out


def about(items: list[Item], kind: str, oid: str) -> list[int]:
    """The items about an object, as Revit's «Show Related Warnings» (study 12, 6): indices into the list."""
    return [n for n, it in enumerate(items) if len(it.target) >= 2 and it.target[0] == kind and it.target[1] == oid]


def filtered(items: list[Item], levels) -> list[int]:
    """The items of the levels the filter keeps."""
    return [n for n, it in enumerate(items) if it.level in levels]


def plant_items(plant) -> list[Item]:
    """The checks of the strings and the inverters (task 16d, energy/plant.py), in the area «strings» of the Plant
    phase: what each input's plan finds (CEI 64-8/7, the clauses stringing.py cites), the strings without an input
    and those whose modules are gone, each inverter's overload and the balance of its inputs (program thresholds,
    said as such), the modules in no string by inverter, and what keeps the strings from being checked. The fix of
    the modules in no string is «Complete the strings» (Meridiana proposes them, the designer's strings stay); a
    string that fails is the designer's to change: no fix rewrites the strings (R114, Daniel 25/10/2026)."""
    if plant is None:
        return []
    from .energy import stringing
    from .energy.plant import unit_label
    from .i18n import ngettext
    norm, here = "CEI 64-8/7:2024", ("phase", "plant")
    module_checks = ("opt_power", "opt_voc", "opt_isc", "opt_imp", "opt_toggle", "opt_fuses")
    redo, redo_label = (), ""
    complete = ("command", "strings_complete")
    complete_label = _("Complete the strings")
    items: list[Item] = []
    for note in plant.notes:
        # a short sentence in the panel, the note in the detail (task 17e: at most TEXT_LENGTH characters)
        items.append(Item("info", "strings", _("The strings cannot be checked yet"), "", here, detail=note))
    bad = 0
    seen: set = set()
    for (unit_no, k), slot in sorted(plant.inputs.items()):
        unit = plant.unit(unit_no)
        # every plan of the input: one per length of its strings (they should be alike; by hand they may not)
        plans = list({id(p): p for p in [slot.plan] + [plant.strings[i].plan for i in slot.strings] if p}.values())
        for p in plans:
            for c in p.checks:
                if c.level not in ("fail", "warn"):
                    continue
                if unit.optimized:
                    # the module on its optimizer is the same in every string of the inverter: said once
                    per_module = c.key in module_checks
                    where = (unit_label(unit) if per_module else
                             _("{inverter}, a string of {n} modules").format(inverter=unit_label(unit), n=p.n_series))
                    if unit.inputs > 1 and not per_module:
                        where = _("{where}, Synergy unit {k}").format(where=where, k=k)
                    key = (unit_no, None if per_module else k, c.key, None if per_module else (p.n_series, p.power_w))
                else:
                    per_input = c.key.startswith(("imp", "isc", "fuse"))        # their label names the input already
                    where = (unit_label(unit) if per_input else
                             _("{inverter}, input {k}, {n} in series").format(inverter=unit_label(unit), k=k,
                                                                              n=p.n_series))
                    key = (unit_no, k, c.key, None if per_input else p.n_series)
                if key in seen:
                    continue
                seen.add(key)
                bad += 1
                items.append(Item(c.level, "strings", f"{where}: {c.label}: {c.detail}", c.source or norm, here, redo,
                                  redo_label, detail=string_detail(c.key)))
    for s in plant.strings:
        if not plant.inputs.get((s.inverter, s.mppt)):
            bad += 1
            items.append(Item("fail", "strings", _("String {name}: on no input of an inverter").format(name=s.label),
                              "", here, redo, redo_label))
    for label, keys in plant.lost:
        bad += 1
        items.append(Item("warn", "strings", ngettext("String {name}: {n} module is no longer laid (the layout changed)",
                                                      "String {name}: {n} modules are no longer laid (the layout "
                                                      "changed)", len(keys)).format(name=label, n=len(keys)),
                          "", here, redo, redo_label))
    threshold = stringing.threshold_source().label
    for _unit_no, unit_checks in sorted(plant.checks.items()):
        for c in unit_checks:
            if c.level in ("fail", "warn"):
                bad += 1
                items.append(Item(c.level, "strings", f"{c.label}: {c.detail}", c.source or threshold, here,
                                  detail=string_detail(c.key) if c.key.startswith("opt_") else ""))
            elif c.level == "info" and c.key in ("opt_suggested", "opt_pairs"):
                items.append(Item("info", "strings", f"{c.label}: {c.detail}", c.source, here))
    for unit_no, n in sorted(plant.left_by_unit.items()):
        unit = plant.unit(unit_no)
        text = (ngettext("{inverter}: {n} module in no string", "{inverter}: {n} modules in no string", n).format(
            inverter=unit_label(unit), n=n) if unit is not None else
            ngettext("{n} module in no string and on no inverter", "{n} modules in no string and on no inverter",
                     n).format(n=n))
        items.append(Item("warn", "strings", text, "", here, complete, complete_label, detail=left_detail()))
    if plant.strings and not bad and not plant.left and any(slot.plan for slot in plant.inputs.values()):
        used = sum(1 for slot in plant.inputs.values() if slot.used)
        if getattr(plant, "optimized", False):
            source = next((c.source for slot in plant.inputs.values() if slot.plan is not None
                           for c in slot.plan.checks if c.key == "opt_count"), norm)
            items.append(Item("ok", "strings", ngettext("{n} string of power optimizers, every check passed",
                                                        "{n} strings of power optimizers, every check passed",
                                                        len(plant.strings)).format(n=len(plant.strings)),
                              source, here))
        else:
            items.append(Item("ok", "strings", ngettext("{n} string on {m} inputs, every check passed",
                                                        "{n} strings on {m} inputs, every check passed",
                                                        len(plant.strings)).format(n=len(plant.strings), m=used),
                              norm, here))
    return items
