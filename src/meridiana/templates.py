"""Building templates (study 16, A.7; task 16a): a rectangle, an L, a T, a U or a trapezoid from its measures, as
an outline the designer places with a click and changes afterwards side by side (the Sides group). The roof
comes from the skeleton like any other outline; a courtyard (a hole) waits for step 4 of the task.

Every outline starts at its South-West corner (0, 0) and runs counter-clockwise; `placed` moves it to the point
clicked and turns it."""

from __future__ import annotations

import math

from .i18n import _

# the measures of each template in their order, with their defaults (m): those of the proof's footprints
# (docs/studio/16-prove/scheletro.py)
KINDS: dict[str, tuple] = {
    "rectangle": (("width", 20.0), ("depth", 10.0)),
    "L": (("width", 20.0), ("depth", 18.0), ("arm_south", 8.0), ("arm_west", 8.0)),
    "T": (("width", 24.0), ("depth", 20.0), ("bar", 8.0), ("stem", 8.0)),
    "U": (("width", 24.0), ("depth", 16.0), ("base", 7.0), ("arm", 8.0)),
    "trapezoid": (("base", 22.0), ("top", 15.0), ("depth", 10.0), ("offset", 3.0)),
}


def kind_names() -> dict:
    return {"rectangle": _("Rectangle"), "L": _("L shape"), "T": _("T shape"), "U": _("U shape"),
            "trapezoid": _("Trapezoid")}


def measure_names() -> dict:
    return {"width": _("Width (West-East)"), "depth": _("Depth (South-North)"),
            "arm_south": _("Depth of the South arm"), "arm_west": _("Width of the West arm"),
            "bar": _("Depth of the bar"), "stem": _("Width of the stem"), "base": _("Length of the base"),
            "arm": _("Width of each arm"), "top": _("Length of the top side"),
            "offset": _("Top side from the West end of the base")}


def defaults(kind: str) -> dict:
    return dict(KINDS[kind])


def footprint(kind: str, measures: dict | None = None) -> list[list[float]]:
    """The outline of a template with its measures (the defaults for those not given), from (0, 0) and
    counter-clockwise. ValueError, said in words, for measures that make no outline."""
    if kind not in KINDS:
        raise ValueError(f"no template {kind!r}")
    m = {**defaults(kind), **(measures or {})}
    for key, value in m.items():
        if not (isinstance(value, (int, float)) and math.isfinite(value)) or (value <= 0 and key != "offset"):
            raise ValueError(_("{what} must be more than zero").format(what=measure_names().get(key, key)))
    w = m.get("width")
    d = m.get("depth")
    if kind == "rectangle":
        ring = [(0, 0), (w, 0), (w, d), (0, d)]
    elif kind == "L":
        a, b = m["arm_south"], m["arm_west"]
        if a >= d or b >= w:
            raise ValueError(_("the arms must be narrower than the building"))
        ring = [(0, 0), (w, 0), (w, a), (b, a), (b, d), (0, d)]
    elif kind == "T":
        a, b = m["bar"], m["stem"]
        if a >= d or b >= w:
            raise ValueError(_("the bar and the stem must be narrower than the building"))
        east, west = (w + b) / 2, (w - b) / 2
        ring = [(0, 0), (w, 0), (w, a), (east, a), (east, d), (west, d), (west, a), (0, a)]
    elif kind == "U":
        a, b = m["base"], m["arm"]
        if a >= d or 2 * b >= w:
            raise ValueError(_("the base and the two arms must leave a courtyard open to the North"))
        ring = [(0, 0), (w, 0), (w, d), (w - b, d), (w - b, a), (b, a), (b, d), (0, d)]
    else:
        base, top, s = m["base"], m["top"], m["offset"]     # two parallel sides: any offset makes a trapezoid
        ring = [(0, 0), (base, 0), (s + top, d), (s, d)]
    return [[float(x), float(y)] for x, y in ring]


def placed(ring, at, turn: float = 0.0) -> list[list[float]]:
    """The outline moved so that its first corner stands at `at` and turned by `turn` degrees about it
    (counter-clockwise, as angles on the plan), to the millimetre."""
    c, s = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    x0, y0 = ring[0]
    out = []
    for x, y in ring:
        dx, dy = x - x0, y - y0
        out.append([round(at[0] + dx * c - dy * s, 4), round(at[1] + dx * s + dy * c, 4)])
    return out
