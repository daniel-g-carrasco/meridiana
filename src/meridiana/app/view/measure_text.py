"""The words of the measuring tool: the pills of its spans, the text copied, the constraint, the hints (study 46).

Daniel's choice 4: in the plan the large number is the length in plan, with the length along the slope and the
height difference below it; in the 3D view the large number is the true length. A «≈» in front of a number whose
end came from a point the 3D view hit, not from the project's geometry. No Qt.
"""

from __future__ import annotations

from meridiana.core.geometry.measure import Span
from meridiana.i18n import N_, _, ngettext, number

APPROX = "≈"
SEP = " · "

# the snaps the menu offers (Shift + right button), for the point being placed; "none" switches them off
SNAP_CHOICES = (("vertex", N_("Vertex")), ("midpoint", N_("Midpoint")), ("edge", N_("Edge")),
                ("intersection", N_("Intersection")), ("perpendicular", N_("Perpendicular")), ("none", N_("None")))
_CONSTRAINTS = {"east": N_("East"), "north": N_("North"), "up": N_("Vertical"), "perpendicular": N_("Perpendicular"),
                "parallel": N_("Parallel"), "held": N_("Direction held")}


def metres(value: float) -> str:
    return _("{length} m").format(length=number(value))


def _approx(text: str, approx: bool) -> str:
    return APPROX + text if approx else text


def _slope(s: Span) -> str:
    if s.percent is None:
        return number(s.slope, 1) + "°"
    return _("{d}° ({p} %)").format(d=number(s.slope, 1), p=number(s.percent, 1))


def snap_label(kind: str) -> str:
    return next((_(label) for k, label in SNAP_CHOICES if k == kind), "")


def snap_menu() -> list:
    """The entries of the snaps' menu (Shift + right button, Daniel's choice 2), as the common menu entry reads them
    (Controls/MenuEntry.qml): {kind, text}, with a rule before «None», which switches them all off."""
    entries = []
    for kind, label in SNAP_CHOICES:
        if kind == "none":
            entries.append({"kind": "", "separator": True})
        entries.append({"kind": kind, "text": _(label)})
    return entries


def constraint_label(kind: str | None, pitch: bool) -> str:
    """The small pill at the end of the guide: the constraint on, and the pitch's plane when the point keeps to it."""
    parts = ([_(_CONSTRAINTS[kind])] if kind in _CONSTRAINTS else []) + ([_("on the pitch plane")] if pitch else [])
    text = SEP.join(parts)
    return text[:1].upper() + text[1:]


def span_pill(s: Span, view: str, approx: bool, elastic: bool = False) -> dict:
    """{"text", "below", "approx"} of one span, as the view shows it (section 2.5 of the state)."""
    below = []
    if view == "plan":
        text = metres(s.plan)
        if not s.level:
            below = [_("along the slope {length}").format(length=metres(s.length)),
                     _("height difference {length}").format(length=metres(abs(s.rise)))]
    else:
        text = metres(s.length)
        if not s.level:
            below = [_("in plan {length}").format(length=number(s.plan)),
                     _("height difference {length}").format(length=number(abs(s.rise))), _slope(s)]
    if elastic and s.bearing is not None:
        below.append(_("direction {bearing}° from North").format(bearing=number(s.bearing, 1)))
    return {"text": _approx(text, approx), "below": SEP.join(below), "approx": approx}


def height_pill(s: Span, top: float, approx: bool) -> dict:
    """The height mode: the height difference large, «from the foot · elevation 10,50» below."""
    return {"text": _approx(metres(abs(s.rise)), approx),
            "below": SEP.join([_("from the foot"), _("elevation") + " " + number(top)]), "approx": approx}


def total_pill(view: str, true: float, plan: float, count: int, area: float | None, approx: bool) -> dict:
    """The total of a path at its end: in plan the total in plan, in the 3D view the true one (choice 4)."""
    large, other = (plan, true) if view == "plan" else (true, plan)
    below = [ngettext("{n} segment", "{n} segments", count).format(n=count)]
    if abs(true - plan) >= 0.005:
        below.append((_("along the slope {length}") if view == "plan" else _("in plan {length}")).format(
            length=metres(other)))
    if area is not None:
        below.append(_("area {a} m²").format(a=number(area)))
    return {"text": _approx(_("Total") + " " + metres(large), approx), "below": SEP.join(below), "approx": approx}


def span_copy(s: Span, approx: bool) -> str:
    """«6,78 m; in plan 6,40 m; height difference 2,24 m; 19,3°» (study §3.6)."""
    parts = [_approx(metres(s.length), approx)]
    if not s.level:
        parts += [_("in plan {length}").format(length=metres(s.plan)),
                  _("height difference {length}").format(length=metres(abs(s.rise))), number(s.slope, 1) + "°"]
    return "; ".join(parts)


def height_copy(s: Span, top: float, approx: bool) -> str:
    return "; ".join([_approx(metres(abs(s.rise)), approx), _("elevation") + " " + metres(top)])


def path_copy(spans: list[Span], true: float, plan: float, area: float | None, approx: bool) -> str:
    """The total on the first line, then one line per span."""
    head = [_("Total") + " " + _approx(metres(true), approx), _("in plan {length}").format(length=metres(plan))]
    if area is not None:
        head.append(_("area {a} m²").format(a=number(area)))
    return "\n".join(["; ".join(head)] + [span_copy(s, approx) for s in spans])


def typed_text(mode: str, typed: str) -> str:
    return (_("height: {value}_") if mode == "height" else _("length: {value}_")).format(value=typed)


def hint(mode: str, points: int, typed: bool) -> str:
    """The hint bar's line for the state, in the style of the drawing tools'; while a point is to be placed it ends
    with the snaps' menu, which holds for that point."""
    if typed:
        return _("Enter: apply length") + _(" · Backspace: delete digit · Esc: clear")
    return _gestures(mode, points) + SEP + _("Shift+right-click: snaps")


def _gestures(mode: str, points: int) -> str:
    if mode == "height":
        return (_("Click: top · Number: height · Esc: cancel") if points
                else _("Click: foot of the height · Esc: exit"))
    if not points:
        return _("Click: first point · Esc: exit")
    if points == 1:
        return _("Click: next point · Arrows: axis · Number: length · Backspace: back · Esc: cancel")
    if points == 2:
        return _("Click: next point · Enter or double-click: finish · Arrows: axis · Number: length · Esc: cancel")
    return _("Click: next point or the first to close · Enter or double-click: finish · Arrows: axis · Esc: cancel")


def chosen_hint(about: str = "") -> str:
    """The hint bar's line with Select while measurements made are chosen (study 46, 3.6), after what the drawing does
    not write (R609): `about`, the numbers of the one chosen, or how many are chosen."""
    gestures = _("Delete: remove · Ctrl+C: copy · Shift+click: add a measure · Esc: let go")
    return about + SEP + gestures if about else gestures


def chosen_count(n: int) -> str:
    return ngettext("{n} measure chosen", "{n} measures chosen", n).format(n=n)


def details(pill: dict, total: dict | None = None) -> str:
    """R609: what the drawing no longer writes beside a span, for the hint bar: its number, the line that was under
    it (along the slope, height difference, slope, direction from North) and, on a path, the total with its own."""
    parts = [pill["text"]] + ([pill["below"]] if pill.get("below") else [])
    if total is not None:
        parts += [total["text"]] + ([total["below"]] if total.get("below") else [])
    return SEP.join(parts)


def no_edge() -> str:
    return _("Down: no reference edge yet; pass over an edge first")


def bad_length() -> str:
    return _("Type a length greater than zero")


def no_direction() -> str:
    return _("Move the pointer to show the direction, then type the length")
