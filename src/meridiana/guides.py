"""The help card that guides while modelling (R43; Daniel, 24/10/2026: «la scheda aiuto deve proprio guidare man mano
che si modella dicendo di preciso a seconda dell'azione che si sta compiendo che cosa fare con una guida fatta come si
deve»): for each tool of the plan the steps of its gesture, and the step the designer is at from what the plan holds
(the points given, a row begun). The help card shows them as a numbered list with the step in hand marked; the «?»
and F1 still pin a subject of their own (R44). No Qt here.

The words are the window's (the shortcuts of shortcuts.py, the menus' names); a step that ends a gesture says what
comes next in the properties."""

from __future__ import annotations

from dataclasses import dataclass

from .i18n import _


@dataclass(frozen=True)
class Guide:
    title: str
    steps: tuple                # the sentences, in order
    manual: str = ""            # the chapter and heading of docs/manuale it continues in


def guides() -> dict[str, Guide]:
    g = Guide
    close = _("Close it: click the first point again, press Enter or double-click. The right button opens Close, "
              "Remove the last point and Cancel; Esc cancels.")
    return {
        "building": g(_("Drawing a building"), (
            _("Click the first corner of its outline. It snaps to the corners and the edges near it; F3 turns "
              "the snaps off, F8 keeps the sides square."),
            _("Click the next corners. For an exact side type its length and Enter («12» or «12;90» for a "
              "length and a turn); R makes a rectangle by three clicks; Backspace takes the last corner back."),
            close,
            _("Done. Give it its height and its roof in Properties: two pitches, a hip, flat, the height of the "
              "ridge; the sub-fields go on it next.")), "1-modello.md#gli-edifici"),
        "pitch": g(_("Drawing a pitch"), (
            _("A pitch belongs to a building: click its first corner inside the building or on its outline."),
            _("Click the next corners: along the eave first, then up to the ridge."),
            close,
            _("Done. Choose its eave side and its slope in Properties, or the height of the ridge, which decides "
              "the slope.")), "1-modello.md#gli-edifici"),
        "subfield": g(_("Drawing a sub-field"), (
            _("Double-click a pitch to take it whole, or click the first corner of the area where the modules "
              "may go, on a roof or on the ground."),
            _("Click the next corners: the edges of the building and of its pitches snap, so the area can follow "
              "them exactly."),
            close,
            _("Done. Choose the module, the mounting and the distances in Properties, then «Lay the modules».")),
            "1-modello.md#il-sottocampo"),
        "exclusion": g(_("Drawing an exclusion"), (
            _("Click the first corner of the skylight, the smoke vent, the roof plant or the walkway."),
            _("Click the next corners; R makes a rectangle by three clicks."),
            close,
            _("Done. Choose its kind and its height in Properties: the modules keep away from it and it casts its "
              "shadow.")), "1-modello.md#le-esclusioni"),
        "row": g(_("Drawing a row of modules"), (
            _("Click where the row starts, inside a sub-field."),
            _("Click where it ends, or type its length and Enter. It takes the module, the gaps and the orientation "
              "of the sub-field; red, it goes past the edge or onto an exclusion.")), "1-modello.md#le-file-a-mano"),
        "move": g(_("Moving"), (
            _("Click what to move: a building, a sub-field, an exclusion, a row."),
            _("Click a base point, then where it goes; or type the move, East;North in metres, and Enter. R turns "
              "it, Ctrl leaves a copy.")), "1-modello.md#spostare-e-ruotare"),
        "measure": g(_("Measuring"), (
            _("Click the first point; it snaps as when drawing."),
            _("Click the second: the distance stays on screen until the next click.")), "1-modello.md#1-modello"),
    }


DRAWING = ("building", "pitch", "subfield", "exclusion")


def step(tool: str, points: int, begun: bool = False, done: bool = False) -> int:
    """The step the designer is at: `points` given to an outline, `begun` a row, a move or a measure under way,
    `done` the gesture just ended."""
    if tool in DRAWING:
        if done:
            return 3
        return 0 if points == 0 else 1 if points < 3 else 2
    return 1 if begun else 0
