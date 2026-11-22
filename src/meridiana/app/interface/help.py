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
import re

from meridiana import REPO_ROOT
from meridiana.i18n import _

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


def texts(*, profile_id: str = "it") -> dict[str, Help]:
    from meridiana.app.profiles import registry
    h = Help
    values = {
        'phase.model': h(
            _("Modelling"), _("The model: buildings, roofs, canopies and obstacles."),
            _("Draw the buildings with their roofs, the canopies as structures and the exclusions; the modules are "
              "laid in the Plant phase. Select an object to see its properties above: this box explains the field "
              "you are in. F1 explains a field, Shift+F1 what you click next."),
            manual="1-modello.md#1-modellazione"),
        'phase.production': h(
            _("Production"), _("The energy of a typical year, hour by hour, with every loss."),
            _("Meridiana computes the year hour by hour, from the sun on the modules to the meter, with the "
              "weather of the site from PVGIS. The figures of the variant are in the panel above; each tile has "
              "its «?», and «How it is computed» gives the formula and the source of every number."),
            manual="3-producibilita.md#3-producibilità", pedigree="production"),
        'phase.report': h(
            _("Report"), _("The deliverables: the report, the drawings, the notes for the documents."),
            _("The panel above lists the deliverables with their state: done, to make again because the project "
              "changed, to make, or not yet available. The PDF report carries every calculation with its source; "
              "the notes of the rules can be copied into the technical report."),
            manual="6-relazione.md#6-relazione"),
        'site': h(
            _("Site"), _("Where the project is: the drawing and the sun are measured from it."),
            _("The site gives the latitude and longitude of the drawing's origin: the sun, the weather from PVGIS "
              "and the region's rules start from it. It can be moved only before anything is drawn, because the "
              "drawing is measured from it."),
            manual="1-modello.md#il-sito"),
        'subfield.sun_window.day': h(
            _("Day"), _("21 December by default: the lowest sun of the year, the longest shadows."),
            _("The day on which the rows must not shade each other, with the hours in solar time (10 to 14 by "
              "default). A day nearer the equinox gives a shorter pitch and more modules, with some shade between "
              "the rows on winter mornings and evenings."),
            manual="1-modello.md#giorno-e-ore-del-sottocampo"),
        'building': h(
            _("Building"), _("A footprint with its eave height and roof, where the sub-fields lie."),
            _("The building is drawn as its footprint. The eave height and the roof (flat, mono-pitch, gable, hip "
              "or pitches drawn by hand) give the pitches the sub-fields lie on, and the shadows the building "
              "casts on the others. On a flat roof the parapet shades the modules near it."),
            manual="1-modello.md#gli-edifici"),
        'building.roof': h(
            _("Roof"), _("Type, covering, slope, ridge height; each side an eave or a gable end."),
            _("Gable and hip roofs follow any outline: a pitch for each eave, ridges and valleys by themselves. "
              "A gable end is a side whose wall rises to the roof. The covering proposes the slope (tiles 35 %, "
              "pantiles 30 %: ANDIL manual 2025, p. 7); a ridge height written sets it instead."),
            manual="1-modello.md#tetto"),
        'sides': h(
            _("Sides"), _("The length of each side: change it and the side stretches, as in CAD."),
            _("Each side of the outline with its length. A new length moves the far end of the side, and what "
              "comes after it, as the stretch of the CAD programs; a double click on a side's measure on the plan "
              "does the same."),
            manual="1-modello.md#lati"),
        'subfield.mounting': h(
            _("Mounting"), _("How the modules stand: flush, tilted rows, east-west, ground, canopy."),
            _("How the modules stand on the surface: flush with the pitch, integrated in the roof, on tilted rows "
              "(anchored or ballasted), in east-west pairs, on the ground or on a canopy. It decides the tilt and "
              "whether the row pitch comes from the sun."),
            manual="1-modello.md#montaggio"),
        'subfield.stack': h(
            _("Modules per table, across"), _("Modules one above the other in a table: 2 is the «2V» of ground mounts."),
            _("How many modules stand one above the other in a table, across the row: with the modules in "
              "portrait, 2 is the «2V» of the ground mounts. More modules across make a taller row, so a longer "
              "pitch from the sun."),
            manual="1-modello.md#moduli-per-tavola-in-altezza"),
        'subfield.placement': h(
            _("Module placement"), _("How the rows stand to each other, and how much power to lay."),
            _("Aligned: one grid, straight columns. Staggered: a row may move half a module from the next, where that lays "
              "more. Free: each row takes all its room and they lay the most. A sub-field saved earlier stays as it was "
              "until you change it. Power asked: the nearest number of modules, in adjacent rows, from the places least "
              "in shadow."),
            manual="1-modello.md#la-posa-dei-moduli"),
        'subfield.row_gap': h(
            _("Between rows"), _("The space between rows on the pitch; on tilted rows the sun gives it."),
            _("On a pitch the modules lie flush and the rows do not shade each other: the gap is a value, for the "
              "clamps and for walking. On tilted rows and on the ground the pitch comes from the sun instead: no "
              "row shades the next on the design day, between the sub-field's hours."),
            manual="1-modello.md#tra-le-file"),
        'subfield.shade_free': h(
            _("Out of the obstacles' shadows"), _("Takes out the modules the obstacles shade on the design day."),
            _("No module where parapets, plant, chimneys, trees and the other buildings cast their shadow on the "
              "design day, between the sub-field's hours: the same rule as the row pitch. When the obstacles "
              "take much light, the Checks propose it and say how many modules it costs."),
            manual="1-modello.md#fuori-dalle-ombre-degli-ostacoli"),
        'plant.inverters': h(
            _("Inverter"), _("Each inverter of the plant: name, model, strings, DC/AC, and its menu."),
            _("One card for each inverter. The disc with its number is the handle: drag it, or Alt+Up and "
              "Alt+Down, to change the order; the number names its strings (1.3.2 is inverter 1), so moving one "
              "renumbers them. F2 renames. The menu «⋯»: rename, move, datasheet, string, empty, take out. «Choose "
              "automatically…» picks them for the modules laid."),
            manual="2-impianto.md#il-pannello-di-destra"),
        'plant.conditions': h(
            _("Conditions of the checks"), _("The temperatures every check of the strings is made at."),
            _("The lowest temperature of the site sets the open-circuit voltage on the coldest morning, checked "
              "against the inverter's and the modules' maximum; the MPP voltage is checked at the hottest and the "
              "coldest cell, PVsyst's design conditions until the production is computed, then the typical year's."),
            manual="2-impianto.md#le-stringhe-sono-tue"),
        'plant.string': h(
            _("String chosen"), _("The string chosen on the plan or in the list: path, bars, checks."),
            _("Where it goes (inverter and input) and its modules; the open-circuit voltage in the cold against "
              "the maximum, the MPP voltage at the hottest and coldest cell against the MPPT window, the current "
              "against the input's, each a bar as long as its limit; then every check with its article. Redraw it, "
              "move it up to another input, or delete it."),
            manual="2-impianto.md#il-pannello-di-destra"),
        'plant.subfield': h(
            _("Sub-field selected"), _("Where «Propose the strings» sends the strings of this sub-field."),
            _("The sub-field selected on the plan, and the inverter and the input its strings go to in the next "
              "proposal; «automatic» leaves the choice to Meridiana. The strings of now do not change until you "
              "propose again."),
            manual="2-impianto.md#il-pannello-di-destra"),
        'production.energy': h(
            _("Energy a year"), _("The AC energy at the meter in a typical year, every loss included."),
            _("The energy the system gives at the meter in the typical year of the site, after the whole chain of "
              "losses: shading, reflection, soiling, temperature, wiring, inverter. It is the figure of the "
              "report; «How it is computed» shows each step with its source."),
            manual="3-producibilita.md#energia-allanno", pedigree="production:ac"),
        'production.specific_yield': h(
            _("Specific yield"), _("The kWh produced in a year for each kWp installed."),
            _("The energy of a year divided by the power of the modules: it compares plants of different sizes. In "
              "Italy it is often between 1,000 and 1,500 kWh/kWp, from north to south; well below that, look at "
              "the shading and the orientation."),
            manual="3-producibilita.md#producibilità-specifica", pedigree="production:pr"),
        'production.pr': h(
            _("Performance ratio"), _("How much of the energy reaching the modules becomes energy at the meter."),
            _("The energy at the meter divided by the energy the modules would give at their nominal power with "
              "the irradiation on their plane. Between 75 and 85% is usual for a plant with little shade; lower, "
              "look at the losses."),
            manual="3-producibilita.md#indice-di-prestazione", pedigree="production:pr"),
        'production.pvgis': h(
            _("PVGIS, second opinion"), _("The typical year and the horizon of the site, from the European service."),
            _("PVGIS, the service of the European Commission's Joint Research Centre, gives the typical weather "
              "year and the horizon of the site, fetched once and kept in the cache. The tile shows its own "
              "estimate for the same plant, as a second opinion."),
            manual="3-producibilita.md#pvgis"),
        'production.losses': h(
            _("Losses"), _("Each item is a step of the chain, from the sun to the meter."),
            _("Each item is a step of the chain from the sun to the meter: shading, reflection, soiling, "
              "temperature, mismatch, wiring, inverter, unavailability. The defaults are marked as such; «How it "
              "is computed» shows the formula and the source of every number."),
            manual="3-producibilita.md#perdite", pedigree="production"),
        'consumption.year': h(
            _("Consumption a year"), _("The energy the site uses in a year, without the system."),
            _("The consumption of a year, from what you entered: a yearly figure, the bands, the bills month by "
              "month, a measured curve or a typical profile. The other tiles give its shape: the bands, the "
              "highest hour, the base load, when it happens."),
            manual="4-consumi.md#consumo-allanno", pedigree="consumption:load"),
        'consumption.shape': h(
            _("Shape of the consumption"), _("When the site uses energy: the shape decides the self-consumption."),
            _("The highest hour; the base load, the power the use stays above in 95% of the hours; the load "
              "factor, the mean over the highest; the share between 8 and 18 and on weekends and holidays. A "
              "site busy in the daytime uses more of the production."),
            manual="4-consumi.md#la-forma-dei-consumi", pedigree="consumption:load"),
        'economics.self_consumption': h(
            _("Self-consumption"), _("The share of the production used on site, hour by hour."),
            _("The production used on site in the same hour, over the whole production; the rest goes to the "
              "grid. A battery stores part of the surplus for the evening. It is computed hour by hour over the "
              "typical year, not on monthly totals."),
            manual="5-bilancio.md#autoconsumo", pedigree="economics:balance"),
        'economics.self_sufficiency': h(
            _("Self-sufficiency"), _("The share of the consumption covered by the system."),
            _("The consumption covered by the system, directly or through the battery, over the whole "
              "consumption. With storage it rises; without it, the nights always come from the grid."),
            manual="5-bilancio.md#autosufficienza", pedigree="economics:balance"),
        'economics.first_year': h(
            _("The first year"), _("What the system saves on the bill and earns from the energy sold."),
            _("The saving is the energy self-consumed in each band times its price; the sale is the energy fed in "
              "times its value, with the community's incentive when there is one. The bill is the energy part "
              "of the bill, without the system and with it."),
            manual="5-bilancio.md#il-primo-anno", pedigree="economics:saving"),
        'economics.npv': h(
            _("Net present value"), _("What the system is worth today over its years, its cost included."),
            _("The cash flows of every year of the analysis (25 by default), discounted at the rate chosen (4% by "
              "default), minus the investment. Positive, the system pays more than it costs at that rate; the "
              "internal rate of return is the rate that brings it to zero."),
            manual="5-bilancio.md#valore-attuale-netto", pedigree="economics:npv"),
        'economics.return': h(
            _("Return"), _("The investment, the rate of return, the payback and the cost of the energy."),
            _("The investment from the cost per kWp or the offer; the internal rate of return, at which the net "
              "present value is zero; the payback, the year the cumulative cash flow turns positive; the "
              "levelised cost, what each kWh produced costs over the years."),
            manual="5-bilancio.md#il-rendimento", pedigree="economics:irr"),
        'economics.prices': h(
            _("Prices"), _("Indicative values until you enter those of the bill and the offer."),
            _("The prices of the energy bought and sold and the costs start from indicative values, marked as "
              "defaults in «How it is computed» and in the Checks; the report lists them. Replace them with the "
              "bill (every variable cost, taxes included) and the offer."),
            manual="5-bilancio.md#prezzi", pedigree="economics:saving"),
        'checks': h(
            _("Checks"), _("What needs your attention, by level, each with its source."),
            _("The checks gather what needs attention from every part of the project: to fix, to check, to know, "
              "and what passed. A click shows the object in the views, the arrow opens the detail, «Fix» applies "
              "the change proposed (Ctrl+.)."),
            manual="verifiche.md#verifiche"),
        'checks.fail': h(
            _("To fix"), _("Something the rules or the layout do not allow: do not deliver it so."),
            _("Something a standard or the layout does not allow: the project should not be delivered like this. "
              "«Fix» makes the change proposed, and Undo takes it back."),
            manual="verifiche.md#da-correggere"),
        'checks.warn': h(
            _("To check"), _("A loss or a risk, not a prohibition: you decide."),
            _("A loss or a risk, not a prohibition: the shade of the obstacles, modules left out of the strings, "
              "a value worth a look. Read the detail under the row (why, and what to do) and decide."),
            manual="verifiche.md#da-controllare"),
        'checks.info': h(
            _("To know"), _("A fact the report will mention: a threshold passed, a default in use."),
            _("A fact the report will mention: a threshold passed (the power that asks for a dedicated interface "
              "relay), a rule that applies, a value still at its default. Nothing to fix; the notes of the rules "
              "can be copied into the technical report."),
            manual="verifiche.md#da-sapere"),
        'checks.ok': h(
            _("Passed"), _("What was checked and found right, closed by default."),
            _("The checks that passed, each with its source: what Meridiana verified and found right. The section "
              "is closed by default, so that what needs attention comes first."),
            manual="verifiche.md#superate"),
        'checks.source': h(
            _("Source"), _("The standard with its clause and page, or the model of calculation."),
            _("Each check says where it comes from: a standard with its edition, clause and page, a law, or the "
              "model of calculation. The rules that apply are listed with their paragraphs, ready for the "
              "technical report."),
            manual="verifiche.md#fonte"),
    }
    values.update(registry.get(profile_id).help_texts())
    return {key: values[key] for key in ('phase.model', 'phase.plant', 'phase.production', 'phase.consumption', 'phase.economics', 'phase.report', 'site', 'subfield.sun_window', 'subfield.sun_window.day', 'site.network', 'site.rules', 'building', 'building.roof', 'building.fire', 'sides', 'subfield', 'subfield.mounting', 'subfield.stack', 'subfield.support', 'subfield.placement', 'subfield.gaps', 'subfield.edge', 'subfield.row_gap', 'subfield.pitch', 'subfield.shade_free', 'exclusion', 'plant.inverters', 'plant.strings', 'plant.conditions', 'plant.string', 'plant.subfield', 'production.energy', 'production.specific_yield', 'production.pr', 'production.power', 'production.pvgis', 'production.losses', 'consumption.year', 'consumption.bands', 'consumption.shape', 'economics.self_consumption', 'economics.self_sufficiency', 'economics.first_year', 'economics.npv', 'economics.return', 'economics.prices', 'checks', 'checks.fail', 'checks.warn', 'checks.info', 'checks.ok', 'checks.source') if key in values}



def get(hid: str, *, profile_id: str = "it") -> Help | None:
    return texts(profile_id=profile_id).get(hid) if hid else None


def for_phase(pid: str, *, profile_id: str = "it") -> str:
    """The help id of a phase (phases.py), what the box says when nothing else is in hand."""
    return f"phase.{pid}"


def sources(h: Help, *, profile_id: str = "it") -> list[str]:
    """The sources as they are read: a rule of rules.py by its own source, a reference as it is written."""
    from meridiana.core.rules import registry
    by_id = {r.id: r for r in registry.get(profile_id).rules()}
    return [by_id[s].source() if s in by_id else s for s in h.source]


def question(h: Help) -> str:
    """What «Ask Meridio» puts in the assistant's field."""
    return _("Explain «{title}» for this project.").format(title=h.title)


# the manual

def manual_dir() -> Path | None:
    """docs/manuale in a checkout; manuale/ next to the shipped files in a build (paths.shipped)."""
    here = REPO_ROOT / "docs" / "manuale"
    if here.is_dir():
        return here
    from meridiana.app.platform import paths
    return paths.shipped("manuale")


def manual_sections(chapter: str) -> list[tuple[int, str, str, str]]:
    """Read the interface language, falling back to Italian for each missing section.

    The stable anchors are also the regulatory profile's section identifiers. The
    glossary is a bilingual maintenance reference, not a chapter fed to Meridio.
    """
    from meridiana import i18n
    folder = manual_dir()
    if folder is None or chapter not in CHAPTERS:
        return []

    def read(path):
        try:
            return sections(path.read_text(encoding="utf-8"))
        except OSError:
            return []

    italian = read(folder / chapter)
    if i18n.language() == "it":
        return italian
    translated = read(folder / "en" / chapter)
    if not italian:
        return translated
    by_anchor = {anchor: section for section in translated for anchor in (section[2],)}
    return [by_anchor.get(section[2], section) for section in italian]


def manual_text(chapter: str) -> str:
    """The same localised sections as search, rendered for the internal Markdown reader."""
    return "\n\n".join(f'<a id="{anchor}"></a>\n\n{"#" * level} {title}\n\n{body}'
                       for level, title, anchor, body in manual_sections(chapter))


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
    return [(level, text) for level, text, _anchor, _body in sections(markdown)]


def sections(markdown: str) -> list[tuple[int, str, str, str]]:
    """(level, title, stable anchor, body), recognising explicit translated anchors."""
    out, fenced, pending = [], False, ""
    current = None
    body = []
    seen: dict[str, int] = {}
    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        explicit = re.fullmatch(r'<a id="([^"]+)"></a>', line.strip()) if not fenced else None
        if explicit:
            pending = explicit[1]
            continue
        match = re.match(r"^(#{1,6}) (.+)$", line) if not fenced else None
        if match:
            if current is not None:
                out.append((*current, "\n".join(body).strip()))
            title = match[2].strip().rstrip("#").strip()
            base = slug(title)
            n = seen.get(base, 0)
            anchor = pending or (base if n == 0 else f"{base}-{n}")
            seen[base] = n + 1
            current, body, pending = (len(match[1]), title, anchor), [], ""
        elif current is not None:
            body.append(line)
    if current is not None:
        out.append((*current, "\n".join(body).strip()))
    return out


def anchors(markdown: str) -> list[str]:
    """Heading anchors in order: explicit IDs, otherwise GitHub slugs with duplicate suffixes."""
    return [anchor for _level, _title, anchor, _body in sections(markdown)]


def chapter_title(markdown: str) -> str:
    """The first heading of a chapter, its name in the list of the manual."""
    first = headings(markdown)
    return first[0][1] if first else ""
