"""How the window arranges itself for its size (R334, study 27), as a plain function without Qt: `arrangement(width, height,
phase, choices)` says what goes where, the window only carries it out (Widgets now, Qt Quick if it comes to that), and
the tables of study 27 are its tests (tests/nucleo/test_arrangement.py).

The rules:
- the thresholds look at the room there is, never at the device: half a 4K screen is a tablet;
- nothing jumps to and fro near a threshold: every line has a band of BAND pixels, and which side of it counts depends
  on what `choices.previous` was;
- what the user chose wins: `choices.pins` holds a value per field, for the shape of the window (`shape_of`), chosen by
  hand or by Undo on a change the program made; the window keeps them per shape, so a monitor turned back gets the
  arrangement left on it;
- the text never changes with the window (study 27, principle 8), and no command exists only in a wide window."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

BAND = 40                   # px: study 27, principle 4
LOW_WINDOW = 900            # below it no words under the icons, and the Checks panel closes (H)
NARROW = 1000               # below it the side panels share a side
ONE_VIEW = 480              # an area narrower than this shows one view at a time (V2), a lower one when stacked would be
                            # too flat as well

SHAPES = ("wide", "medium", "vertical")
UNDER, BESIDE, ICONS = "under", "beside", "icons"     # the same as ui/design.Bar, which this module does not import


@dataclass(frozen=True)
class Choices:
    """What the function needs beyond the window's size: numbers the window measures, what the user chose."""
    toolbar: str = "text"           # the preference: "text", or "icons" always
    needs: dict = field(default_factory=dict)       # mode of the bar -> phase -> the width its groups ask for
    trailing: dict = field(default_factory=dict)    # phase -> the least width of what stands at its bar's end
    bar_heights: dict = field(default_factory=lambda: {UNDER: 69, BESIDE: 31, ICONS: 47})
    bar_sides: int = 44             # what the window takes off its width before the bar
    row_needs: int = 1000           # the row of the phases with its names, with File and the variant
    columns: tuple = (240, 300)     # the side panels' widths (0: closed by the user)
    sides: tuple = (16, 81)         # the window's width and height that are neither panels, nor checks, nor the bar
    checks: int = 238               # the height the Checks panel takes when open
    pins: dict = field(default_factory=dict)        # a field of Arrangement -> the value chosen, for this shape
    previous: Arrangement | None = None


@dataclass(frozen=True)
class Arrangement:
    shape: str = "wide"             # SHAPES
    tall: bool = True               # the window's height over LOW_WINDOW
    row: str = "names"              # the row of the phases: "names", or "numbers" with the name of the phase open
    bar: str = UNDER                # UNDER, BESIDE, ICONS
    trailing_in_bar: bool = True    # what stands at the end of this phase's bar, in it or above the page
    panels: str = "apart"           # the side panels: "apart", or "together" on one side
    checks_open: bool = True
    views: str = "side"             # plan and 3D: "side", "stacked", or "one" at a time


def _at_least(value: float, line: float, was: bool | None) -> bool:
    """`value` reaches `line`: at once when it has not been asked yet or it was already so; from below, only BAND
    past it, so that a window moved to and fro across the line changes once."""
    return value >= (line + BAND if was is False else line)


def shape_of(width: int, height: int, previous: str | None = None) -> str:
    """The shape of the window, what arrangements are remembered by: «vertical» higher than wide (a monitor turned, a
    tablet held upright), «medium» a laptop or half a screen, «wide» the rest."""
    if height >= (width + 1 if previous is None else width if previous == "vertical" else width + BAND):
        return "vertical"
    was_wide = None if previous is None else previous == "wide"
    return "wide" if _at_least(width, NARROW, was_wide) and _at_least(height, LOW_WINDOW, was_wide) else "medium"


def arrangement(width: int, height: int, phase: str, choices: Choices) -> Arrangement:
    was, pins = choices.previous, choices.pins
    tall = _at_least(height, LOW_WINDOW, None if was is None else was.tall)
    # the mode of the bar is one for all the phases: a bar that changes height with the phase would move the views
    room = width - choices.bar_sides

    def need(mode: str) -> int:
        return max(choices.needs.get(mode, {}).values(), default=0)

    bar = pins.get("bar")
    if bar is None:
        fits_under = _at_least(room, need(UNDER), None if was is None else was.bar == UNDER)
        fits_beside = _at_least(room, need(BESIDE), None if was is None else was.bar == BESIDE)
        if choices.toolbar != "text":
            bar = ICONS
        elif tall:
            bar = UNDER if fits_under else ICONS
        else:
            bar = BESIDE if fits_beside else ICONS
    # what stands at the bar's end: in the bar when the groups leave it room, above the page when not (no group of
    # tools is lost to it); the low bar has no room for two lines of text
    end = choices.trailing.get(phase, 0)
    in_bar = pins.get("trailing_in_bar")
    if in_bar is None:
        own = choices.needs.get(bar, {}).get(phase, 0)
        in_bar = not end or (bar != BESIDE and _at_least(room, own + end, None if was is None else was.trailing_in_bar))
    names = _at_least(width, choices.row_needs, None if was is None else was.row == "names")
    row = pins.get("row", "names" if names else "numbers")
    apart = _at_least(width, NARROW, None if was is None else was.panels == "apart")
    panels = pins.get("panels", "apart" if apart else "together")
    checks_open = pins.get("checks_open", tall)
    # the area the views have: from the numbers, not measured, so that the answer cannot depend on what it changes
    left, right = choices.columns
    columns = left + right if panels == "apart" else max(left, right)
    area_w = width - choices.sides[0] - columns
    area_h = height - choices.sides[1] - choices.bar_heights.get(bar, 47) - (choices.checks if checks_open else 0)
    return Arrangement(shape_of(width, height, was.shape if was else None), tall, row, bar, in_bar, panels, checks_open,
                       pins.get("views", _views(area_w, area_h, panels, was)))


def _views(area_w: int, area_h: int, panels: str, was: Arrangement | None) -> str:
    """Plan and 3D: one above the other when the area is higher than wide (V1), and always in a narrow window with height
    for two, where side by side each would be a slit; one at a time when there is no room for two (V2)."""
    if not _at_least(area_w, ONE_VIEW, None if was is None else was.views != "one"):
        return "one"
    if panels == "together":
        if not _at_least(area_h, ONE_VIEW, None if was is None else was.views != "one"):
            return "one"
        return "stacked"
    return "stacked" if _at_least(area_h, area_w, None if was is None else was.views == "stacked") else "side"


# what a change of arrangement is said for: the rest (the row, what stands at the bar's end) follows the room and hides nothing
SAID = ("panels", "checks_open", "views", "bar")


def changes(before: Arrangement, after: Arrangement) -> tuple:
    """The fields that changed and are told to the user, who can undo them."""
    return tuple(name for name in SAID if getattr(before, name) != getattr(after, name))


def pinned(pins: dict, before: Arrangement, fields: tuple) -> dict:
    """The pins that hold `fields` at what they were in `before`: Undo on a change the program made."""
    return {**pins, **{name: getattr(before, name) for name in fields}}


def from_dict(data: dict) -> Arrangement | None:
    """An arrangement as it was saved with the window's state; None when it cannot be read."""
    try:
        got = {name: data[name] for name in ("shape", "tall", "row", "bar", "trailing_in_bar", "panels", "checks_open", "views")}
    except (KeyError, TypeError):
        return None
    if got["shape"] not in SHAPES or got["bar"] not in (UNDER, BESIDE, ICONS):
        return None
    return replace(Arrangement(), **got)


PIN_FIELDS = {"row": ("names", "numbers"), "bar": (UNDER, BESIDE, ICONS), "trailing_in_bar": (True, False),
              "panels": ("apart", "together"), "checks_open": (True, False), "views": ("side", "stacked", "one")}


def clean_pins(data) -> dict:
    """The pins of a saved window's state, what is not one left out (a file is never to be trusted)."""
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if k in PIN_FIELDS and v in PIN_FIELDS[k]}
