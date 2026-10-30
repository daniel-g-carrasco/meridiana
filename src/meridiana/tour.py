"""Stable guided-tour content and explicit offline assistant commands.

The tour is Meridio's (R264): a small sun, cordial, a little witty and never sugary, who knows photovoltaics. Every
step says what a thing is for and how it is used, not only where it is (R293): a short title, a paragraph or two,
two or three points, and the key or command to try."""
from dataclasses import dataclass
import re
import unicodedata

from .i18n import _


@dataclass(frozen=True)
class Step:
    id: str
    title: str
    text: str
    target: tuple[str, ...]
    points: tuple[str, ...] = ()        # two or three things worth knowing, one line each
    hint: str = ""                      # the key, the command or the menu to try


def steps() -> tuple[Step, ...]:
    return (
        Step("file", _("Your projects live here"),
             _("Hello, I am Meridio: a small sun with a weakness for well-placed modules. Let me show you around; "
               "nothing in your project changes while we walk. File is where every project starts and comes back "
               "to: new, open, the recent ones, and the revisions you save along the way."),
             ("file",),
             (_("New: a site, a name and the first roof in a few minutes."),
              _("Save and revisions: a revision is a new file next to the previous one, never over it."),
              _("Import and Export: PVsyst, IFC and the hourly CSV.")),
             _("Ctrl+N new project, Ctrl+O open")),
        Step("model", _("Model and place the modules"),
             _("This is where the plant takes shape. Draw the footprint of the buildings and give them roofs; on "
               "each roof define the subfields and I fill them with modules at the pitch and orientation you "
               "choose. The toolbar follows the task: Edit, Draw, Layout and Precision."),
             ("phase", "model"),
             (_("Roofs flat or pitched on any footprint; the fire brigade rules keep the walkways free."),
              _("Layout: rows, pitch and setbacks; drag a module to lay out a row by hand."),
              _("Undo is always one key away: experiment freely.")),
             _("Ctrl+Z undo, F fits the drawing to the view")),
        Step("views", _("Plan and 3D, side by side"),
             _("The plan is for measuring and drawing, the 3D view for seeing roofs and shadows as they really "
               "are. In a narrow window one view is shown at a time; the view bar switches between them."),
             ("views",),
             (_("Orbit, pan and zoom follow the navigation style you choose in Settings."),
              _("The compass and Home put north back where it belongs when you lose your bearings."),
              _("The sun bar under the 3D view moves the sun through the day and the year, shadows included.")),
             _("Ctrl+Shift+3 shows or hides the 3D view")),
        Step("properties", _("Select, inspect, change"),
             _("Click an object and its properties come up here: a building, a roof, a subfield, a module. Every "
               "field explains itself: put the cursor in it and press F1. The site holds what the grid connection "
               "needs: distributor, POD, voltage, phases and the power you ask for."),
             ("property", "site.voltage"),
             (_("Every change is one undo step."),
              _("A grey field is computed: change what feeds it, not the result."),
              _("I read these values when you ask me about the project.")),
             _("F1 help on the field, Shift+F1 what is this")),
        Step("plant", _("Inverters, strings and storage"),
             _("Modules make direct current; here it becomes a plant. Pick an inverter from the catalogue or let "
               "me size one, then connect the strings to its MPPTs. Propose fills in a sensible stringing, "
               "Complete finishes what you started by hand, and neither touches a choice you made yourself."),
             ("phase", "plant"),
             (_("Sizing checks voltages and currents at the extreme temperatures, and the DC/AC ratio."),
              _("Storage goes beside the inverters: battery, coupling and power."),
              _("A string drawn by hand is yours: I never redraw it.")),
             _("Compute > Propose the strings, then Complete the strings")),
        Step("checks", _("Checks and explanations"),
             _("I keep an eye on the plant and tell you here when something is off: an error that stops the "
               "computation, a warning worth a look, or a plain note. Open a group to read why, and where the "
               "rule comes from."),
             ("checks",),
             (_("Follow the destination: the check takes you to the exact field."),
              _("A suggested fix is applied only when you click it, and it is one undo step."),
              _("The checks follow every edit: there is no button to press.")),
             _("Panels > Checks shows or hides this panel")),
        Step("production", _("Production and losses"),
             _("My favourite part. The year is computed hour by hour with the weather of the site: irradiance on "
               "each module, temperature, shadows between the rows and from the buildings, wiring, inverter "
               "clipping. Only the modules connected to a string contribute energy; the others wait their turn."),
             ("phase", "production"),
             (_("The loss diagram says where every kilowatt-hour went."),
              _("One tab per inverter, MPPT by MPPT."),
              _("Calculation details list the assumptions and the sources: every number can be checked.")),
             _("F5 computes the year; the weather comes from PVGIS when you allow it")),
        Step("consumption", _("Consumption, the other half of the balance"),
             _("A plant is only as good as the use of its energy. Enter a load profile by hand or import the "
               "measured consumption from your distributor, then compare production with demand hour by hour, "
               "before you think about storage or self-consumption."),
             ("phase", "consumption"),
             (_("Measured data: a CSV of hourly values, aligned with the weather year."),
              _("The base of the consumption separates what is always on from what varies."),
              _("The chart overlays production and demand: the gap is what storage could fill.")),
             _("Compute > Import a load curve…")),
        Step("economics", _("Balance and economics"),
             _("Here energy becomes money. Self-consumption, what goes to the grid, how the battery cycles, costs "
               "and returns over the years: all from the hourly results of the previous phases, so a change "
               "upstream shows up here at once."),
             ("phase", "economics"),
             (_("Variants compare designs side by side, each with its own assumptions."),
              _("Tariffs and incentives are inputs you control, never hidden defaults."),
              _("The payback comes with its assumptions written next to it.")),
             _("Compute > Variants compares the designs")),
        Step("report", _("Reports and exchange"),
             _("Everything ends up in a document someone else will read. Choose the purpose and the detail of "
               "the report, check the preview and export the PDF: every number says where it comes from. For "
               "the rest of the team there are IFC for the model and an hourly CSV for independent checks."),
             ("phase", "report"),
             (_("Complete or summary report, with the signature profile you set in Settings."),
              _("IFC keeps buildings, roofs and modules for BIM."),
              _("The CSV holds the hourly results: open it in a spreadsheet.")),
             _("File > Export")),
        Step("assistant", _("Ask me anything about the plant"),
             _("That is me, in my bubble. Ask about the current project, request an explanation of a result, or "
               "say «Show me the theme setting» and I take you there and point at it. Attach a datasheet and I "
               "read it for you."),
             ("assistant",),
             (_("I propose, you confirm: nothing changes in the project without your yes."),
              _("I can think on this computer with a local model or in the cloud with your key; the chip above "
                "says where."),
              _("Drag me where you like; I keep off what you are drawing.")),
             _("Ctrl+L opens or closes my bubble; keys 1, 2, 3 pick a suggested question")),
        Step("settings", _("Make the workspace yours"),
             _("Appearance, navigation, keyboard, maps, privacy and my own settings live here. The theme follows "
               "one colour you choose, light or dark; the navigation style can mimic the CAD you know; the "
               "privacy page says what may go online, and nothing does without your leave."),
             ("settings", "appearance"),
             (_("Keyboard: every shortcut can be changed, and Ctrl+? lists them."),
              _("Privacy: geocoding, PVGIS and map tiles each have their own switch."),
              _("You can restart this tour from Help, or simply ask me.")),
             _("Ctrl+, opens the Settings; Alt+Left takes you back")),
        Step("start", _("Now, let us design"),
             _("That was the tour: thirteen stops and not one cloud. Now it is your turn. Choose the site for "
               "your new project, give it a name and draw the first roof; I stay here in my corner whenever you "
               "need a hand or a second opinion."),
             ("new",),
             (_("Start from the address or the coordinates of the site."),
              _("Help > Guided tour brings me back any time.")),
             _("Ctrl+N starts a new project")),
    )


def local_command(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", "", text).strip()
    if re.fullmatch(r"(?:(?:avvia|mostra|riprendi|inizia|rifai) (?:la )?)?(?:visita guidata|tour)|(?:start|show|resume) (?:the )?(?:guided tour|tour)", text):
        return "tour"
    if re.fullmatch(r"(?:segnala|segnalare) (?:un |il )?(?:bug|problema|errore)|(?:report|submit) (?:a )?(?:bug|issue)", text):
        return "bug"
    if re.fullmatch(r"(?:come (?:si naviga|navigo|mi muovo)(?: (?:nel modello|in 2d|in 3d))?|(?:mostra|spiega) (?:i )?(?:comandi di navigazione|gesti del touchpad)|(?:show|explain) navigation controls)", text):
        return "navigation"
    return ""
