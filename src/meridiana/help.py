"""The help next to things (study 17, E; design document 3.6, C3, C7 and 5.1; R24): for each group, field and
result tile that needs it, a title, a short sentence, a text of a few lines, its source, its place in the manual
and its step of «How it is computed». The window shows them in the help box at the foot of the right panel
(ui/help_box.py), from the «?» beside the titles of the groups and the result tiles, with F1 on the field that
has the keyboard and with Shift+F1 («What's this?») on what is clicked next. The manual is docs/manuale/, a
chapter per phase in Markdown, read inside the program; its anchors are the headings' (as GitHub makes them),
so that the same files read on GitHub too.

The texts are drafts written from the computations and the rules, for Daniel to read again (the substance and
the sources). A standard is cited only where rules.py or checks.py already cite it (tests/test_help.py); the
figures that are orders of magnitude say so in the manual. No Qt here."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .i18n import _

SHORT = 75              # characters of the short sentence: Apple's 60 to 75 for a tooltip
TEXT = 350              # characters of the text, and at most LINES lines of LINE characters (JetBrains' inline help)
LINES, LINE = 5, 70
CHAPTERS = ("README.md", "1-modello.md", "2-impianto.md", "3-producibilita.md", "4-consumi.md", "5-bilancio.md",
            "6-relazione.md", "verifiche.md")


@dataclass(frozen=True)
class Help:
    title: str              # the name of what it explains, as the window writes it
    short: str              # one sentence, the hint under a field and the tooltip of the «?»
    text: str               # what it is and why, in a few lines
    source: tuple = ()      # rule ids of rules.py ("N15"), or references written as checks.py writes them
    manual: str = ""        # "1-modello.md#il-sottocampo": the chapter and the heading's anchor
    pedigree: str = ""      # "production:pr": the phase and the step of «How it is computed»; "production": the page


def texts() -> dict[str, Help]:
    """Every help by its id: the group, field or tile it is about ("subfield.row_gap"), the phases as
    "phase.<id>" (phases.py), the levels of the checks as "checks.<level>". Built at each call, in the language
    of the window."""
    h = Help
    return {
        # the phases: what the box says when nothing else is in hand
        "phase.model": h(
            _("Model"), _("The drawing: buildings, sub-fields, exclusions and the modules laid."),
            _("Draw the buildings with their roofs, the sub-fields where the modules go and the exclusions. "
              "Select an object to see its properties above: this box explains the field you are in. F1 "
              "explains a field, Shift+F1 what you click next."),
            manual="1-modello.md#1-modello"),
        "phase.plant": h(
            _("Plant"), _("Inverters and strings: what joins the modules to the grid."),
            _("The inverters, chosen from the catalogue or sized by Meridiana, and the strings, checked against "
              "CEI 64-8/7: the voltage at the coldest cell and the current at the hottest, within what the "
              "inverter and the modules stand."),
            ("CEI 64-8/7:2024",), "2-impianto.md#2-impianto"),
        "phase.production": h(
            _("Production"), _("The energy of a typical year, hour by hour, with every loss."),
            _("Meridiana computes the year hour by hour, from the sun on the modules to the meter, with the "
              "weather of the site from PVGIS. The figures of the variant are in the panel above; each tile has "
              "its «?», and «How it is computed» gives the formula and the source of every number."),
            manual="3-producibilita.md#3-producibilità", pedigree="production"),
        "phase.consumption": h(
            _("Consumption"), _("The site's consumption, hour by hour, from bills, a curve or a profile."),
            _("The consumption decides how much of the production is used on site. Enter a year, the bands F1, "
              "F2, F3, the bills month by month or a measured curve; without them Meridiana guesses from the "
              "project and says so in the Checks."),
            manual="4-consumi.md#4-consumi", pedigree="consumption"),
        "phase.economics": h(
            _("Balance and economics"), _("Self-consumption, the bill and what the system is worth over the years."),
            _("Production and consumption meet hour by hour: what is used on site saves on the bill, the rest is "
              "sold. The cash flows over the years of the analysis then give the net present value, the internal "
              "rate of return and the payback."),
            manual="5-bilancio.md#5-bilancio-ed-economia", pedigree="economics"),
        "phase.report": h(
            _("Report"), _("The deliverables: the report, the drawings, the notes for the documents."),
            _("The panel above lists the deliverables with their state: done, to make again because the project "
              "changed, to make, or not yet available. The PDF report carries every calculation with its source; "
              "the notes of the rules can be copied into the technical report."),
            manual="6-relazione.md#6-relazione"),
        # the site
        "site": h(
            _("Site"), _("Where the project is: the drawing and the sun are measured from it."),
            _("The site gives the latitude and longitude of the drawing's origin: the sun, the weather from PVGIS "
              "and the region's rules start from it. It can be moved only before anything is drawn, because the "
              "drawing is measured from it."),
            manual="1-modello.md#il-sito"),
        "site.sun_window": h(
            _("Row pitch from the sun"), _("The day and the hours in which no row shades the next one."),
            _("On the design day, between those solar hours, no row shades the next one: the row pitch of the "
              "tilted rows comes from it, and so do the shadows kept off by «Out of the obstacles' shadows». The "
              "standards leave the choice to the designer: CEI 82-25/3 6.2 gives only the limit angle."),
            ("CEI 82-25/3 6.2",), "1-modello.md#passo-delle-file-dal-sole"),
        "site.sun_window.day": h(
            _("Day"), _("21 December by default: the lowest sun of the year, the longest shadows."),
            _("The day on which the rows must not shade each other, with the hours in solar time (10 to 14 by "
              "default). A day nearer the equinox gives a shorter pitch and more modules, with some shade between "
              "the rows on winter mornings and evenings."),
            manual="1-modello.md#giorno-e-ore-di-progetto"),
        "site.rules": h(
            _("Connection and obligations"), _("What the rules need beyond the drawing: grid level, obligations, premises."),
            _("The connection level comes from the power unless you choose it (the distributor decides). The "
              "minimum renewable capacity depends on the building and its use. The contracted power, the floor "
              "area and the premises decide who may design (DM 37/2008 art. 5 par. 2)."),
            ("N02", "N24"), "1-modello.md#connessione-e-obblighi"),
        # the building
        "building": h(
            _("Building"), _("A footprint with its eave height and roof, where the sub-fields lie."),
            _("The building is drawn as its footprint. The eave height and the roof (flat, mono-pitch, gable, hip "
              "or pitches drawn by hand) give the pitches the sub-fields lie on, and the shadows the building "
              "casts on the others. On a flat roof the parapet shades the modules near it."),
            manual="1-modello.md#gli-edifici"),
        "building.roof": h(
            _("Roof"), _("Type, covering, slope, ridge height; each side an eave or a gable end."),
            _("Gable and hip roofs follow any outline: a pitch for each eave, ridges and valleys by themselves. "
              "A gable end is a side whose wall rises to the roof. The covering proposes the slope (tiles 35 %, "
              "pantiles 30 %: ANDIL manual 2025, p. 7); a ridge height written sets it instead."),
            manual="1-modello.md#tetto"),
        "building.fire": h(
            _("Fire brigade"), _("The fire-brigade rules for the modules on this building's roof."),
            _("For an activity subject to fire-brigade control, the sub-fields on this building keep 1 m from the "
              "roof edge and from vents and plant, in groups of at most 20 m with 2 m corridors: Meridiana applies "
              "them by itself. On a fire-resistant slab the rule spares the 1 m from the walls below."),
            ("N15",), "1-modello.md#prevenzione-incendi"),
        "sides": h(
            _("Sides"), _("The length of each side: change it and the side stretches, as in CAD."),
            _("Each side of the outline with its length. A new length moves the far end of the side, and what "
              "comes after it, as the stretch of the CAD programs; a double click on a side's measure on the plan "
              "does the same."),
            manual="1-modello.md#lati"),
        # the sub-field
        "subfield": h(
            _("Sub-field"), _("The area where the modules go, on a roof pitch or on the ground."),
            _("A sub-field is the area drawn for the modules: Meridiana lays them inside with its mounting, its "
              "gaps and the fire-brigade rules of the building it lies on. «Lay the modules» starts the layout; "
              "the figures and the notes of the result are under the buttons."),
            manual="1-modello.md#il-sottocampo"),
        "subfield.mounting": h(
            _("Mounting"), _("How the modules stand: flush, tilted rows, east-west, ground, canopy."),
            _("How the modules stand on the surface: flush with the pitch, integrated in the roof, on tilted rows "
              "(anchored or ballasted), in east-west pairs, on the ground or on a canopy. It decides the tilt and "
              "whether the row pitch comes from the sun."),
            manual="1-modello.md#montaggio"),
        "subfield.stack": h(
            _("Modules per table, across"), _("Modules one above the other in a table: 2 is the «2V» of ground mounts."),
            _("How many modules stand one above the other in a table, across the row: with the modules in "
              "portrait, 2 is the «2V» of the ground mounts. More modules across make a taller row, so a longer "
              "pitch from the sun."),
            manual="1-modello.md#moduli-per-tavola-in-altezza"),
        "subfield.gaps": h(
            _("Gaps and margins"), _("The free space between modules, rows and tables, and from the edge."),
            _("The gaps between the modules, from the edge of the area, between the rows and between the tables. "
              "Where the building is subject to fire-brigade control, Meridiana keeps at least 1 m from the edge "
              "and adds the corridors between the groups by itself."),
            ("N15",), "1-modello.md#distanze-e-margini"),
        "subfield.edge": h(
            _("From the edge of the area"), _("A free strip along the outline, where no module goes."),
            _("A free strip along the outline of the area, where the modules do not go: for maintenance and for "
              "the fire-brigade rules. With an activity subject to control it is at least 1 m (DCPREV "
              "14030/2025, 3.3.5.1), and Meridiana applies it by itself."),
            ("N15",), "1-modello.md#dal-bordo-dellarea"),
        "subfield.row_gap": h(
            _("Between rows"), _("The space between rows on the pitch; on tilted rows the sun gives it."),
            _("On a pitch the modules lie flush and the rows do not shade each other: the gap is a value, for the "
              "clamps and for walking. On tilted rows and on the ground the pitch comes from the sun instead: no "
              "row shades the next on the design day, between the hours of the site."),
            manual="1-modello.md#tra-le-file"),
        "subfield.pitch": h(
            _("Row pitch"), _("From the sun, given, or from the ground cover ratio."),
            _("«From the sun»: the shortest pitch with no row shading the next on the design day, between the "
              "hours of the site. «Given pitch»: a distance you choose. «Ground cover ratio»: the depth of the "
              "modules across the row divided by the pitch."),
            ("CEI 82-25/3 6.2",), "1-modello.md#passo-delle-file"),
        "subfield.shade_free": h(
            _("Out of the obstacles' shadows"), _("Takes out the modules the obstacles shade on the design day."),
            _("No module where parapets, plant, chimneys, trees and the other buildings cast their shadow on the "
              "design day, between the hours of the site: the same rule as the row pitch. When the obstacles "
              "take much light, the Checks propose it and say how many modules it costs."),
            manual="1-modello.md#fuori-dalle-ombre-degli-ostacoli"),
        # the exclusion
        "exclusion": h(
            _("Exclusion"), _("An area with no modules: skylight, vent, plant, chimney, walkway."),
            _("An exclusion keeps the modules out of its outline and of its extra clearance. With a height it is "
              "also an obstacle that casts shadows. Smoke vents, openings and roof plant get 1 m more by "
              "themselves where the fire-brigade rules apply (DCPREV 14030/2025, 3.3.5.1)."),
            ("N15",), "1-modello.md#le-esclusioni"),
        # production
        "production.energy": h(
            _("Energy a year"), _("The AC energy at the meter in a typical year, every loss included."),
            _("The energy the system gives at the meter in the typical year of the site, after the whole chain of "
              "losses: shading, reflection, soiling, temperature, wiring, inverter. It is the figure of the "
              "report; «How it is computed» shows each step with its source."),
            manual="3-producibilita.md#energia-allanno", pedigree="production:ac"),
        "production.specific_yield": h(
            _("Specific yield"), _("The kWh produced in a year for each kWp installed."),
            _("The energy of a year divided by the power of the modules: it compares plants of different sizes. In "
              "Italy it is often between 1,000 and 1,500 kWh/kWp, from north to south; well below that, look at "
              "the shading and the orientation."),
            manual="3-producibilita.md#producibilità-specifica", pedigree="production:pr"),
        "production.pr": h(
            _("Performance ratio"), _("How much of the energy reaching the modules becomes energy at the meter."),
            _("The energy at the meter divided by the energy the modules would give at their nominal power with "
              "the irradiation on their plane. Between 75 and 85% is usual for a plant with little shade; lower, "
              "look at the losses."),
            manual="3-producibilita.md#indice-di-prestazione", pedigree="production:pr"),
        "production.power": h(
            _("Power"), _("The modules' power at STC, the inverters' AC power and their ratio."),
            _("The sum of the modules' nameplate power at standard test conditions (kWp); under it, the inverters' "
              "AC power and the DC/AC ratio. For the grid rules the nominal power of the plant is the lower of the "
              "two (CEI 0-21:2026-07 3.61)."),
            ("CEI 0-21:2026-07 3.61",), "3-producibilita.md#potenza", "production:inverter"),
        "production.pvgis": h(
            _("PVGIS, second opinion"), _("The typical year and the horizon of the site, from the European service."),
            _("PVGIS, the service of the European Commission's Joint Research Centre, gives the typical weather "
              "year and the horizon of the site, fetched once and kept in the cache. The tile shows its own "
              "estimate for the same plant, as a second opinion."),
            manual="3-producibilita.md#pvgis"),
        "production.losses": h(
            _("Losses"), _("Each item is a step of the chain, from the sun to the meter."),
            _("Each item is a step of the chain from the sun to the meter: shading, reflection, soiling, "
              "temperature, mismatch, wiring, inverter, unavailability. The defaults are marked as such; «How it "
              "is computed» shows the formula and the source of every number."),
            manual="3-producibilita.md#perdite", pedigree="production"),
        # consumption
        "consumption.year": h(
            _("Consumption a year"), _("The energy the site uses in a year, without the system."),
            _("The consumption of a year, from what you entered: a yearly figure, the bands, the bills month by "
              "month, a measured curve or a typical profile. The other tiles give its shape: the bands, the "
              "highest hour, the base load, when it happens."),
            manual="4-consumi.md#consumo-allanno", pedigree="consumption:load"),
        "consumption.bands": h(
            _("Time bands"), _("F1 weekdays 8 to 19; F2 and F3 the other hours, nights and holidays."),
            _("F1 is Monday to Friday from 8 to 19; F2 Monday to Friday from 7 to 8 and from 19 to 23, and "
              "Saturday from 7 to 23; F3 the nights, Sundays and holidays. A site that uses its energy in F1 "
              "matches the production of the day best."),
            manual="4-consumi.md#le-fasce", pedigree="consumption:load"),
        "consumption.shape": h(
            _("Shape of the consumption"), _("When the site uses energy: the shape decides the self-consumption."),
            _("The highest hour; the base load, the power the use stays above in 95% of the hours; the load "
              "factor, the mean over the highest; the share between 8 and 18 and on weekends and holidays. A "
              "site busy in the daytime uses more of the production."),
            manual="4-consumi.md#la-forma-dei-consumi", pedigree="consumption:load"),
        # balance and economics
        "economics.self_consumption": h(
            _("Self-consumption"), _("The share of the production used on site, hour by hour."),
            _("The production used on site in the same hour, over the whole production; the rest goes to the "
              "grid. A battery stores part of the surplus for the evening. It is computed hour by hour over the "
              "typical year, not on monthly totals."),
            manual="5-bilancio.md#autoconsumo", pedigree="economics:balance"),
        "economics.self_sufficiency": h(
            _("Self-sufficiency"), _("The share of the consumption covered by the system."),
            _("The consumption covered by the system, directly or through the battery, over the whole "
              "consumption. With storage it rises; without it, the nights always come from the grid."),
            manual="5-bilancio.md#autosufficienza", pedigree="economics:balance"),
        "economics.first_year": h(
            _("The first year"), _("What the system saves on the bill and earns from the energy sold."),
            _("The saving is the energy self-consumed in each band times its price; the sale is the energy fed in "
              "times its value, with the community's incentive when there is one. The bill is the energy part "
              "of the bill, without the system and with it."),
            manual="5-bilancio.md#il-primo-anno", pedigree="economics:saving"),
        "economics.npv": h(
            _("Net present value"), _("What the system is worth today over its years, its cost included."),
            _("The cash flows of every year of the analysis (25 by default), discounted at the rate chosen (4% by "
              "default), minus the investment. Positive, the system pays more than it costs at that rate; the "
              "internal rate of return is the rate that brings it to zero."),
            manual="5-bilancio.md#valore-attuale-netto", pedigree="economics:npv"),
        "economics.return": h(
            _("Return"), _("The investment, the rate of return, the payback and the cost of the energy."),
            _("The investment from the cost per kWp or the offer; the internal rate of return, at which the net "
              "present value is zero; the payback, the year the cumulative cash flow turns positive; the "
              "levelised cost, what each kWh produced costs over the years."),
            manual="5-bilancio.md#il-rendimento", pedigree="economics:irr"),
        "economics.prices": h(
            _("Prices"), _("Indicative values until you enter those of the bill and the offer."),
            _("The prices of the energy bought and sold and the costs start from indicative values, marked as "
              "defaults in «How it is computed» and in the Checks; the report lists them. Replace them with the "
              "bill (every variable cost, taxes included) and the offer."),
            manual="5-bilancio.md#prezzi", pedigree="economics:saving"),
        # the checks
        "checks": h(
            _("Checks"), _("What needs your attention, by level, each with its source."),
            _("The checks gather what needs attention from every part of the project: to fix, to check, to know, "
              "and what passed. A click shows the object in the views, the arrow opens the detail, «Fix» applies "
              "the change proposed (Ctrl+.)."),
            manual="verifiche.md#verifiche"),
        "checks.fail": h(
            _("To fix"), _("Something the rules or the layout do not allow: do not deliver it so."),
            _("Something a standard or the layout does not allow: the project should not be delivered like this. "
              "«Fix» makes the change proposed, and Undo takes it back."),
            manual="verifiche.md#da-correggere"),
        "checks.warn": h(
            _("To check"), _("A loss or a risk, not a prohibition: you decide."),
            _("A loss or a risk, not a prohibition: the shade of the obstacles, modules left out of the strings, "
              "a value worth a look. Read the detail under the row (why, and what to do) and decide."),
            manual="verifiche.md#da-controllare"),
        "checks.info": h(
            _("To know"), _("A fact the report will mention: a threshold passed, a default in use."),
            _("A fact the report will mention: a threshold passed (the power that asks for a dedicated interface "
              "relay), a rule that applies, a value still at its default. Nothing to fix; the notes of the rules "
              "can be copied into the technical report."),
            manual="verifiche.md#da-sapere"),
        "checks.ok": h(
            _("Passed"), _("What was checked and found right, closed by default."),
            _("The checks that passed, each with its source: what Meridiana verified and found right. The section "
              "is closed by default, so that what needs attention comes first."),
            manual="verifiche.md#superate"),
        "checks.source": h(
            _("Source"), _("The standard with its clause and page, or the model of calculation."),
            _("Each check says where it comes from: a standard with its edition, clause and page, a law, or the "
              "model of calculation. The rules that apply are listed with their paragraphs, ready for the "
              "technical report."),
            manual="verifiche.md#fonte"),
    }


def get(hid: str) -> Help | None:
    return texts().get(hid) if hid else None


def for_phase(pid: str) -> str:
    """The help id of a phase (phases.py), what the box says when nothing else is in hand."""
    return f"phase.{pid}"


def sources(h: Help) -> list[str]:
    """The sources as they are read: a rule of rules.py by its own source, a reference as it is written."""
    from . import rules
    by_id = {r.id: r for r in rules.RULES}
    return [by_id[s].source() if s in by_id else s for s in h.source]


def question(h: Help) -> str:
    """What «Ask Meridio» puts in the assistant's field."""
    return _("Explain «{title}» for this project.").format(title=h.title)


# the manual

def manual_dir() -> Path | None:
    """docs/manuale in a checkout; manuale/ next to the shipped files in a build (paths.shipped)."""
    here = Path(__file__).resolve().parent.parent.parent / "docs" / "manuale"
    if here.is_dir():
        return here
    from . import paths
    return paths.shipped("manuale")


def split(ref: str) -> tuple[str, str]:
    """«1-modello.md#tra-le-file» as the chapter and the anchor; a chapter alone has no anchor."""
    chapter, _hash, anchor = ref.partition("#")
    return chapter, anchor


def slug(heading: str) -> str:
    """A heading's anchor as GitHub makes it: lower case, letters, digits, spaces, hyphens and underscores kept
    (accented letters too), the spaces as hyphens."""
    kept = "".join(ch for ch in heading.strip().lower() if ch.isalnum() or ch in " -_")
    return kept.replace(" ", "-")


def headings(markdown: str) -> list[tuple[int, str]]:
    """The headings of a Markdown text, (level, text), outside the fenced code."""
    out, fenced = [], False
    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced or not line.startswith("#"):
            continue
        hashes = len(line) - len(line.lstrip("#"))
        if 1 <= hashes <= 6 and line[hashes:hashes + 1] == " ":
            out.append((hashes, line[hashes:].strip().rstrip("#").strip()))
    return out


def anchors(markdown: str) -> list[str]:
    """The anchors of the headings in their order; a second heading with the same anchor gets «-1», as GitHub."""
    seen: dict[str, int] = {}
    out = []
    for _level, text in headings(markdown):
        base = slug(text)
        n = seen.get(base, 0)
        out.append(base if n == 0 else f"{base}-{n}")
        seen[base] = n + 1
    return out


def chapter_title(markdown: str) -> str:
    """The first heading of a chapter, its name in the list of the manual."""
    first = headings(markdown)
    return first[0][1] if first else ""
