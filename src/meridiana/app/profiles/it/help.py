"""Italian help fragments, preserving existing messages and sources."""
from meridiana.i18n import _

def texts():
    from meridiana.app.interface.help import Help
    h = Help
    return {
        'phase.plant': h(
            _("Plant"), _("Modules, inverters and storage, in this order; then the strings."),
            _("The sub-fields with their modules laid, the inverters, chosen from the catalogue or sized by "
              "Meridiana, the storage and the strings, checked against CEI 64-8/7: the voltage at the coldest cell "
              "and the current at the hottest, within what the inverter and the modules stand."),
            ("CEI 64-8/7:2024",), "2-impianto.md#2-impianto"),
        'phase.consumption': h(
            _("Consumption"), _("The site's consumption, hour by hour, from bills, a curve or a profile."),
            _("The consumption decides how much of the production is used on site. Enter a year, the bands F1, "
              "F2, F3, the bills month by month or a measured curve; without them Meridiana guesses from the "
              "project and says so in the Checks."),
            manual="4-consumi.md#4-consumi", pedigree="consumption"),
        'phase.economics': h(
            _("Balance and economics"), _("Self-consumption, the bill and what the system is worth over the years."),
            _("Production and consumption meet hour by hour: what is used on site saves on the bill, the rest is "
              "sold. The cash flows over the years of the analysis then give the net present value, the internal "
              "rate of return and the payback."),
            manual="5-bilancio.md#5-bilancio-ed-economia", pedigree="economics"),
        'subfield.sun_window': h(
            _("Row pitch from the sun"), _("The day and the hours in which no row shades the next one."),
            _("On the design day and between those solar hours, no row shades the next one. The pitch and the "
              "shadows kept out come from this window. The sub-field follows the project default until changed; "
              "«Use for all sub-fields» applies the shown values everywhere. CEI 82-25/3 6.2 gives only the limit "
              "angle."),
            ("CEI 82-25/3 6.2",), "1-modello.md#passo-delle-file-dal-sole"),
        'site.network': h(
            _("Grid connection (optional)"), _("Distributor, POD, voltage, phases, level and powers of the connection."),
            _("The data of the connection to the grid, for the report and the rules: the distributor and the POD of "
              "the supply, its voltage (which picks the technical rule of the connection), the phases, the "
              "connection level, the power available and the power requested for the plant. What you do not know "
              "stays «not stated»."),
            manual="1-modello.md#il-sito"),
        'site.rules': h(
            _("Connection and obligations"), _("What the rules need beyond the drawing: grid level, obligations, premises."),
            _("The connection level comes from the power unless you choose it (the distributor decides). The "
              "minimum renewable capacity depends on the building and its use. The contracted power, the floor "
              "area and the premises decide who may design (DM 37/2008 art. 5 par. 2)."),
            ("N02", "N24"), "1-modello.md#connessione-e-obblighi"),
        'building.fire': h(
            _("Fire brigade"), _("The activity of DPR 151/2011 here, and the rules for the modules."),
            _("A plant is not an activity itself: the building is, if it hosts one of Annex I of DPR 151/2011 "
              "(DCPREV 14030/2025, 1.1). Choose it here, by number or words: threshold and categories follow. For an "
              "activity subject to control, the sub-fields keep 1 m from the edge and from vents and plant, in "
              "groups of at most 20 m with 2 m corridors."),
            ("N13", "N15"), "1-modello.md#prevenzione-incendi"),
        'subfield': h(
            _("Sub-field"), _("The area where the modules go, on a roof pitch or on the ground."),
            _("A sub-field is the area drawn for the modules: Meridiana lays them inside with its mounting, its "
              "gaps and the fire-brigade rules of the building it lies on. «Fill» lays an empty one, «Empty» takes "
              "the modules out; the figures and the notes of the result are under the buttons."),
            manual="1-modello.md#il-sottocampo"),
        'subfield.support': h(
            _("Auxiliary support plane"), _("A plane of its own for the modules, instead of the roof pitch."),
            _("The modules are laid on a plane of their own, with its elevation at the centre of the area, its tilt "
              "and its azimuth, instead of the pitch of the building they stand on: a structure on a flat roof, a "
              "canopy whose plane differs from the roof's. The building and the pitch stay as references; the "
              "model received is unchanged."),
            manual="1-modello.md#il-sottocampo"),
        'subfield.gaps': h(
            _("Gaps and margins"), _("The free space between modules, rows and tables, and from the edge."),
            _("The gaps between the modules, from the edge of the area, between the rows and between the tables. "
              "Where the building is subject to fire-brigade control, Meridiana keeps at least 1 m from the edge "
              "and adds the corridors between the groups by itself."),
            ("N15",), "1-modello.md#distanze-e-margini"),
        'subfield.edge': h(
            _("From the edge of the area"), _("A free strip along the outline, where no module goes."),
            _("A free strip along the outline of the area, where the modules do not go: for maintenance and for "
              "the fire-brigade rules. With an activity subject to control it is at least 1 m (DCPREV "
              "14030/2025, 3.3.5.1), and Meridiana applies it by itself."),
            ("N15",), "1-modello.md#dal-bordo-dellarea"),
        'subfield.pitch': h(
            _("Row pitch"), _("From the sun, given, or from the ground cover ratio."),
            _("«From the sun»: the shortest pitch with no row shading the next on the design day, between the "
              "sub-field's hours. «Given pitch»: a distance you choose. «Ground cover ratio»: the depth of the "
              "modules across the row divided by the pitch."),
            ("CEI 82-25/3 6.2",), "1-modello.md#passo-delle-file"),
        'exclusion': h(
            _("Exclusion"), _("An area with no modules: skylight, vent, plant, chimney, walkway."),
            _("An exclusion keeps the modules out of its outline and of its extra clearance. With a height it is "
              "also an obstacle that casts shadows. Smoke vents, openings and roof plant get 1 m more by "
              "themselves where the fire-brigade rules apply (DCPREV 14030/2025, 3.3.5.1)."),
            ("N15",), "1-modello.md#le-esclusioni"),
        'plant.strings': h(
            _("Strings"), _("This inverter's inputs with their strings; the view from the menu beside."),
            _("The whole plant's strings on the first line; then the inverter shown and its inputs, as cards (each "
              "with its mark and strings, «+» draws one) or as a single-line diagram in miniature (a bar per "
              "string), from the menu left of the «?». A click chooses a string, on the plan too; a double click "
              "redraws it; the right button has the rest."),
            ("CEI 64-8/7:2024",), "2-impianto.md#le-stringhe-sono-tue"),
        'production.power': h(
            _("Power"), _("The modules' power at STC, the inverters' AC power and their ratio."),
            _("The sum of the modules' nameplate power at standard test conditions (kWp); under it, the inverters' "
              "AC power and the DC/AC ratio. For the grid rules the nominal power of the plant is the lower of the "
              "two (CEI 0-21:2026-07 3.61)."),
            ("CEI 0-21:2026-07 3.61",), "3-producibilita.md#potenza", "production:inverter"),
        'consumption.bands': h(
            _("Time bands"), _("F1 weekdays 8 to 19; F2 and F3 the other hours, nights and holidays."),
            _("F1 is Monday to Friday from 8 to 19; F2 Monday to Friday from 7 to 8 and from 19 to 23, and "
              "Saturday from 7 to 23; F3 the nights, Sundays and holidays. A site that uses its energy in F1 "
              "matches the production of the day best."),
            manual="4-consumi.md#le-fasce", pedigree="consumption:load"),
    }


HELP_IDS = ('phase.plant', 'phase.consumption', 'phase.economics', 'subfield.sun_window', 'site.network', 'site.rules', 'building.fire', 'subfield', 'subfield.support', 'subfield.gaps', 'subfield.edge', 'subfield.pitch', 'exclusion', 'plant.strings', 'production.power', 'consumption.bands')
