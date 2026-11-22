"""R643: the sign of North, one drawing for the plan, the 3D view and the report (Daniel 15/11/2026, proposal A of
the sketches of r35-bussola: «ago a due colori»).

A needle across a box of BOX x BOX units, pointing up: the North half full, the South half soft over a view (the
ink at SOFT) and white with its outline on paper. Over a view it stands on the overlays' glass, a disc as wide as
the box (Controls/NorthSign.qml, through ThemeTokens.signs); on paper it has no ground and an «N» over its tip
(report/figures.py). The colours are the theme's roles, never here: over a view `overlay.glass`, `overlay.ink`,
`overlay.hover`; on paper the report's ink.

No Qt here: the window reads `as_map()`, the report `paper_svg()`."""

from __future__ import annotations

import math
from xml.sax.saxutils import escape

BOX = 100.0                             # the drawing's box, in units; its middle is the needle's pivot
NORTH = "M50,10 L60,50 L40,50 Z"        # the North half, full
SOUTH = "M40,50 L60,50 L50,90 Z"        # the South half
SOFT = 0.42                             # over a view: the South half is the ink at this opacity
LETTER_AT = 62.0                        # on paper: the «N»'s middle, in units from the pivot towards North
PAPER_MM = 12.0                         # on paper: the box's side
PAPER_LINE_MM = 0.3                     # on paper: the outline of the two halves (a photocopy keeps it)
PAPER_LETTER_MM = 2.8                   # on paper: the «N»'s size (as the 8 pt of the plan's north before R643)


def as_map() -> dict:
    """What the window needs to draw the sign: the box, the two halves, the South half's opacity."""
    return {"box": BOX, "north": NORTH, "south": SOUTH, "soft": SOFT}


def letter_point(cx: float, cy: float, side: float, bearing: float = 0.0) -> tuple[float, float]:
    """Where the «N» goes for a sign of `side` centred on (cx, cy), with North `bearing` degrees clockwise from up
    (y down, as on screen and in SVG)."""
    a = math.radians(bearing)
    r = LETTER_AT * side / BOX
    return cx + r * math.sin(a), cy - r * math.cos(a)


def paper_svg(cx: float, cy: float, mm: float, ink: str, paper: str = "#ffffff", bearing: float = 0.0,
              family: str = "IBM Plex Sans") -> str:
    """The sign as SVG for a drawing whose unit is `mm` units a millimetre: centred on (cx, cy), PAPER_MM wide, North
    `bearing` degrees clockwise from up (0: the plan printed North up), the «N» upright over the tip."""
    side = PAPER_MM * mm
    k = side / BOX
    line = PAPER_LINE_MM * mm / k
    lx, ly = letter_point(cx, cy, side, bearing)
    size = PAPER_LETTER_MM * mm
    return (f'<g transform="translate({cx - side / 2:.3f} {cy - side / 2:.3f}) scale({k:.5f}) '
            f'rotate({bearing:.3f} 50 50)" stroke="{ink}" stroke-width="{line:.4f}" stroke-linejoin="miter">'
            f'<path d="{SOUTH}" fill="{paper}"/><path d="{NORTH}" fill="{ink}"/></g>'
            f'<text x="{lx:.3f}" y="{ly + 0.36 * size:.3f}" font-family="{escape(family)}" font-weight="600" '
            f'font-size="{size:.3f}" text-anchor="middle" fill="{ink}">N</text>')


def paper_extent(mm: float) -> tuple[float, float, float]:
    """On paper, in the drawing's units: half the sign's width, how far the «N»'s top stands above the pivot, how far
    the tail stands below it (to keep the sign inside the figure)."""
    side = PAPER_MM * mm
    return side / 2, LETTER_AT * side / BOX + 0.5 * PAPER_LETTER_MM * mm, 0.4 * side
