"""The six phases of the work, described once (design document, 2.1 and 3.3; study 17, B4; Daniel, 23/10/2026:
«bella la suddivisione in fasi»): 1 Modelling, 2 Plant, 3 Production, 4 Consumption, 5 Balance and economics,
6 Report. Each phase has its number and title, the groups of its bar with the commands in order, the inspector
the right panel shows, the areas of the checks it produces and the three questions ready for Meridio. No Qt here:
the window builds the row of the phases and the bar of each from this, and never reasons with «index == 0».

The Modelling holds the model alone, the site, the buildings, the roofs, the canopies as structures, the
obstacles; the modules are laid in the Plant, before the inverters and the storage (R277, study 22, 3.1-3.3;
Daniel, 30/10/2026: «in Impianto, con ordine, si metteranno i pannelli, poi gli inverter e poi l'accumulo»). The
phase is the interface's only: a project keeps none of it, and the ids stay those of before («model», «plant»).

The phases are places, not stages (design 2.1): every one is always open, none asks for the previous one to be
finished; the numbers say the natural order of the work, and are keys too: Ctrl+1 to Ctrl+6 (Daniel, 24/10/2026,
past C8), with Ctrl+Tab, Ctrl+PgDown and Ctrl+PgUp to move between them.

A command the bar cites must exist in shortcuts.py, except the ones a later task brings (`planned`: the task's
name): they stay here so that the bar is designed once, and the bar leaves them out until the window has their
action; then they come in by themselves, where they were designed (R277: «Su pensilina», canopy_layout).
Nothing of the views (the sun, the background) is here: that stays in the views' own bars (R27, C5)."""

from __future__ import annotations

from dataclasses import dataclass

from .i18n import _


@dataclass(frozen=True)
class Tool:
    """A button of the bar: the command it starts, the word under its icon (one line: a long name is shortened
    here and stays whole in the tooltip), the icon (ui/icons.NAMES; the command's id when empty), whether it is
    the one button full of accent of the phase, and the task that brings it when it is not there yet."""
    command: str
    label: str = ""
    icon: str = ""
    primary: bool = False
    planned: str = ""


@dataclass(frozen=True)
class Group:
    id: str
    title: str
    tools: tuple


@dataclass(frozen=True)
class Phase:
    id: str
    number: int
    title: str
    groups: tuple
    inspector: str                  # "properties", "plant" (panels, inverters, storage: R277), "results" or
                                    # "deliverables"
    areas: tuple                    # of checks.area_names()
    questions: tuple                # three, for Meridio

    @property
    def label(self) -> str:
        """As the row of the phases writes it: «1 Modellazione»."""
        return f"{self.number} {self.title}"

    def tools(self, planned: bool = False) -> list[Tool]:
        """The tools of the bar in their order; `planned` includes those a later task brings."""
        return [t for g in self.groups for t in g.tools if planned or not t.planned]

    def commands(self) -> list[str]:
        """Every command the bar cites, planned ones included."""
        return [t.command for t in self.tools(planned=True)]


INSPECTORS = ("properties", "plant", "results", "deliverables")


def phases() -> list[Phase]:
    """The six phases in order, with the groups of the design document (3.3)."""
    T = Tool
    return [
        Phase("model", 1, _("Modelling"), (
            Group("edit", _("Edit"), (
                T("tool_select", icon="select"),
                T("tool_move", _("Move"), icon="move"),
                T("tool_rotate", _("Rotate"), icon="rotate"))),
            Group("draw", _("Draw"), (
                T("tool_building", icon="building"),
                T("building_template", _("Template")),
                T("carport", _("Canopy")),
                T("tool_pitch", icon="pitch"),
                T("tool_ridge", icon="ridge"))),        # R275: the roof from its ridge
            # the objects of the scene (trees, cars, people) once they are part of the program (study 22, 3.2 and
            # question 10: on the bar only when they are there)
            Group("obstacles", _("Obstacles"), (
                T("tool_exclusion", icon="exclusion"),  # an exclusion is an obstacle on the roof (a vent, a skylight)
                T("object_3d", _("3D object"), planned="oggetti-3d"))),
            Group("precision", _("Precision"), (
                T("tool_measure", icon="measure"),
                T("square", _("Square")),
                T("rectangle", _("Rectangle"))))),
            "properties", ("shade", "import"),
            (_("Is the roof plausible?"),
             _("Is any obstacle missing for the shadows?"),
             _("Are the heights consistent with the photo?"))),
        # the work in the order Daniel asked for (R277): the modules, then the inverters, then the storage; the
        # strings close, they need both
        Phase("plant", 2, _("Plant"), (
            Group("modules", _("Panels"), (
                T("tool_subfield", icon="subfield"),
                T("tool_row", _("Row"), icon="row"),
                T("layout_east_west", _("East-west")),
                T("canopy_layout", _("On canopy"), icon="carport"),
                T("fill", _("Lay"), primary=True),
                T("empty", _("Empty")))),
            Group("inverter", _("Inverter"), (
                T("inverter_catalog", _("Catalogue")),
                T("inverter_auto", _("Size it")))),
            Group("storage", _("Storage"), (T("battery_catalog", _("Configure")),)),
            Group("strings", _("Strings"), (
                T("strings_auto", _("Propose")),
                T("strings_complete", _("Complete")),
                T("strings_manual", _("Draw")),
                T("strings_clear", _("Start again"))))),
            "plant", ("layout", "strings", "connection"),
            (_("What do you think of this layout?"),
             _("Are the distances from the edges right for the fire brigade?"),
             _("Are the strings right for this inverter?"))),
        Phase("production", 3, _("Production"), (
            Group("compute", _("Computation"), (
                T("compute", _("Compute"), primary=True),
                T("fetch_pvgis", _("From PVGIS")))),
            Group("compare", _("Comparison"), (
                T("new_variant", _("New variant"), icon="copy-plus"),
                T("pvgis_side", _("PVGIS beside"), planned="17c"),
                T("compare_variants", _("Variants"))))),
            "results", ("production", "shade"),
            (_("Why is the performance ratio this one?"),
             _("Which losses weigh most?"),
             _("Is this specific yield plausible for the site?"))),
        Phase("consumption", 4, _("Consumption"), (
            Group("data", _("Data"), (
                T("consumption_base", _("Base")),
                T("import_curve", _("Curve")))),),
            "results", ("consumption",),
            (_("Does this load profile look plausible?"),
             _("How much of the production is used on site?"),
             _("Would a battery help here?"))),
        Phase("economics", 5, _("Balance and economics"), (
            Group("compute", _("Computation"), (
                T("compute", _("Compute"), primary=True),)),
            Group("compare", _("Comparison"), (
                T("new_variant", _("New variant"), icon="copy-plus"),
                T("compare_variants", _("Variants")),))),
            "results", ("economics",),
            (_("Is the investment worth it?"),
             _("What weighs most on the payback?"),
             _("What would change with a battery?"))),
        Phase("report", 6, _("Report"), (
            Group("compare", _("Comparison"), (
                T("new_variant", _("New variant"), icon="copy-plus"),
                T("compare_variants", _("Compare")))),
            Group("export", _("Export"), (
                T("export_report", _("Report")),
                T("export_dxf", _("DXF"), planned="relazione"),
                T("export_ifc", _("IFC4")),
                T("export_csv", _("CSV")),
                T("save_revision", _("Revision")),
                T("copy_notes", _("Copy the notes"))))),
            "deliverables", ("rules",),
            (_("Is the report complete for the client?"),
             _("Which values are still at their default?"),
             _("What should the installer get with the drawings?"))),
    ]


def ids() -> list[str]:
    return [p.id for p in phases()]


def by_id(pid: str) -> Phase:
    """KeyError when no phase has that id."""
    for p in phases():
        if p.id == pid:
            return p
    raise KeyError(pid)


# the plan's tools that work wherever the plan is (the Modelling and the Plant, which borrows it): choosing what to
# edit and measuring never take the designer to another phase (R277)
PLAN_PHASES = ("model", "plant")
SHARED_TOOLS = ("tool_select", "tool_measure")


def home(command: str, current: str) -> str:
    """The phase a command of the plan works in, seen from the phase `current`: `current` itself when its bar has
    the command, or when the command is shared by the phases of the plan; else the first phase whose bar has it;
    else the Modelling. «Sub-field» asked in the Modelling opens the Plant, «Building» asked in the Plant opens
    the Modelling, «Select» stays where it is (R277)."""
    if current in PLAN_PHASES and (command in SHARED_TOOLS or command in by_id(current).commands()):
        return current
    for p in phases():
        if command in p.commands():
            return p.id
    return "model"


def by_number(number: int) -> Phase:
    for p in phases():
        if p.number == number:
            return p
    raise KeyError(number)


def index_of(pid: str) -> int:
    return ids().index(pid)


def next(pid: str) -> str:               # noqa: A001  the name the design uses
    """The phase after `pid`; after the last, the first again (as Ctrl+Tab goes round in a browser)."""
    order = ids()
    return order[(order.index(pid) + 1) % len(order)]


def previous(pid: str) -> str:
    order = ids()
    return order[(order.index(pid) - 1) % len(order)]


# the deliverables of the Report phase (design 2.7 and 7.3): each with its state in the inspector

@dataclass(frozen=True)
class Deliverable:
    id: str
    title: str
    command: str                    # the command that makes it, or "" when a later task brings it
    state: str                      # "done", "stale", "todo", "unavailable", "planned"
    note: str                       # why, or when


def _made(did: str, title: str, command: str, production_ready: bool, exports: dict, state_key: str) -> Deliverable:
    """A deliverable the program makes from the year: done, to make again, to make, not available."""
    done = exports.get(did)
    if done is not None:
        name, when, key = done
        if key == state_key:
            return Deliverable(did, title, command, "done", _("{file}, {when}").format(file=name, when=when))
        return Deliverable(did, title, command, "stale",
                           _("The project changed after {when}: export it again").format(when=when))
    if production_ready:
        return Deliverable(did, title, command, "todo", _("Not exported yet"))
    return Deliverable(did, title, command, "unavailable", _("Compute the production first"))


def deliverables(production_ready: bool, exports: dict, state_key: str) -> list[Deliverable]:
    """The state of each deliverable: `exports` is id -> (file name, when, the project's state key at the time),
    as the window keeps them; `state_key` is the project's now. Made after the project changed, a deliverable is
    «to make again» (design 7.3). The hourly series is the register of the calculations (energy/register.py), on
    its own or beside the report."""
    out = [_made("report", _("Technical report (PDF)"), "export_report", production_ready, exports, state_key),
           _made("csv", _("Hourly series (CSV)"), "export_csv", production_ready, exports, state_key)]
    # the model (IFC4, R91): the project's geometry, it needs no computed year
    model_ifc = exports.get("ifc")
    if model_ifc is None:
        out.append(Deliverable("ifc", _("Model (IFC4)"), "export_ifc", "todo", _("Not exported yet")))
    else:
        name, when, key = model_ifc
        out.append(Deliverable("ifc", _("Model (IFC4)"), "export_ifc", "done" if key == state_key else "stale",
                               _("{file}, {when}").format(file=name, when=when) if key == state_key else
                               _("The project changed after {when}: export it again").format(when=when)))
    for did, title, task in (("dxf", _("Plan with the modules (DXF)"), "relazione"),
                             # in the technical report since task 16d; a file of its own with the report's task
                             ("strings", _("List of modules and strings"), "relazione")):
        out.append(Deliverable(did, title, "", "planned", _("Comes with task {task}").format(task=task)))
    return out


def state_names() -> dict:
    return {"done": _("done"), "stale": _("to make again"), "todo": _("to make"), "unavailable": _("not available"),
            "planned": _("not yet")}
