"""The shapes of the window's symbols, with no Qt (R330, the flat ones): the tracks of the ten symbols in a 16-unit
square, their tones, the checks' levels, and the SVG of one. `ui/symbols.py` draws them in the window with Qt's renderer;
the report's Typst template (`report_typst/`) draws the same tracks, so a check has the same sign on the screen and on
the paper. A change of geometry is made here, once.

Flat: the ground of one tone (a disc, the warning's triangle, the forbidden's ring), the sign opaque on it, always
white, painted and never cut out of the ground (the flat ones of 25/10/2026 were refused because their sign was cut
out and showed what lay under it). The warning's triangle is as wide as the disc's diameter (R330, Daniel
02/11/2026: «in larghezza sia uguale al diametro del cerchio»)."""

from __future__ import annotations

from . import theme_colors

DISC = "M0.5,8 A7.5,7.5 0 1 1 15.5,8 A7.5,7.5 0 1 1 0.5,8 Z"
# as wide as the disc (R330: «in larghezza sia uguale al diametro del cerchio»), so a little over it above and below
TRIANGLE = ("M9.31,2.801 L14.658,12.496 A1.491,1.491 0 0 1 13.358,14.711 L2.642,14.711 A1.491,1.491 0 0 1 1.342,12.496 "
            "L6.69,2.801 A1.491,1.491 0 0 1 9.31,2.801 Z")
# each symbol: its tone, its ground (the disc, the triangle, a ring) and its sign, drawn on the ground
SHAPES = {
    "check": ("good", DISC, "M3.5,8.9 L6.93,12.34 L12.53,6.07 L11.27,4.93 L6.87,9.86 L4.7,7.7 Z"),       # Spola
    "cross": ("critical", DISC, "M6.338,10.864 L5.136,9.662 L6.798,8 L5.136,6.338 L6.338,5.136 L8,6.798 "
                                "L9.662,5.136 L10.864,6.338 L9.202,8 L10.864,9.662 L9.662,10.864 L8,9.202 Z"),
    # Spola's ring, red and its bar turned as the prohibition sign (ISO 7010), running into the ring (to r 6.6)
    "forbidden": ("critical", DISC + " M3,8 A5,5 0 1 1 13,8 A5,5 0 1 1 3,8 Z",
                  "M4.249,2.551 L13.449,11.751 L11.751,13.449 L2.551,4.249 Z"),
    "stop": ("critical", DISC, "M3.6,7.15 L12.4,7.15 L12.4,8.85 L3.6,8.85 Z"),
    "info": ("info", DISC, "M6.95,4.6 A1.05,1.05 0 1 1 9.05,4.6 A1.05,1.05 0 1 1 6.95,4.6 Z "
                           "M7.15,6.8 L8.85,6.8 L8.85,12.4 L7.15,12.4 Z"),
    # Spola's triangle with the error's «!» (1.7 wide, its dot 1.05), shorter to stand in the triangle
    "warning": ("warning", TRIANGLE, "M7.15,5.4 L8.85,5.4 L8.85,9.9 L7.15,9.9 Z "
                                     "M6.95,12.05 A1.05,1.05 0 1 1 9.05,12.05 A1.05,1.05 0 1 1 6.95,12.05 Z"),
    "error": ("critical", DISC, "M7.15,3.6 L8.85,3.6 L8.85,9.2 L7.15,9.2 Z "                              # Spola
                                "M6.95,11.4 A1.05,1.05 0 1 1 9.05,11.4 A1.05,1.05 0 1 1 6.95,11.4 Z"),
    # a bin: its handle, its lid and its body narrowing to a rounded bottom
    "trash": ("critical", DISC, "M6.6,3.4 L9.4,3.4 L9.4,4.6 L11.7,4.6 L11.7,6 L4.3,6 L4.3,4.6 L6.6,4.6 Z "
                                "M5,6.8 L11,6.8 L10.45,12 L9.65,12.7 L6.35,12.7 L5.55,12 Z"),
    # the arrow of going back: its head to the left, its shaft turning down and back under it, 1.7 wide
    "back": ("neutral", DISC, "M3.3,6.6 L6.7,3.7 L6.7,5.75 L9,5.75 A3.35,3.35 0 0 1 9,12.45 L5.4,12.45 "
                              "L5.4,10.75 L9,10.75 A1.65,1.65 0 0 0 9,7.45 L6.7,7.45 L6.7,9.5 Z"),
    # to do again: what is shown is the previous one, an arrow going round (R330, the «⟳» of a font before)
    "update": ("neutral", DISC, "M12.06,11.41 A5.3,5.3 0 1 1 9.81,3.02 L10.39,1.42 L12.62,4.95 L8.65,6.21 L9.23,4.62 A3.6,3.6 0 1 0 10.76,10.31 Z"),
}
NAMES = tuple(SHAPES)
LEVEL = {"fail": "stop", "warn": "warning", "info": "info", "ok": "check"}      # the checks' levels (checks.LEVELS)
TONES = {"good": theme_colors.STATUS["good"], "warning": theme_colors.WARNING_INK,
         "critical": theme_colors.STATUS["critical"], "info": "#2e4a6b", "neutral": "#77767b"}
TONES_DARK = dict(TONES, info="#5b8fc9", neutral="#9a9996")       # on a dark ground the dark blue and the grey vanish
LIGHT_SIGN = "#ffffff"                                              # the sign on every symbol, opaque


def colour(name: str, dark: bool = False) -> str:
    return (TONES_DARK if dark else TONES)[SHAPES[name][0]]


def svg(name: str, dark: bool = False, fill: str | None = None, signed: bool | None = None) -> bytes:
    """The symbol as an SVG file of 16 x 16. `fill`: the ground in that colour instead of the symbol's tone (a halo,
    an off symbol, the report's palette); `signed`: whether the white sign is on it, by default only when `fill` is
    not asked for."""
    _tone, ground, track = SHAPES[name]
    signed = fill is None if signed is None else signed
    head = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
    paint_ = fill or colour(name, dark)
    if name == "forbidden":
        # the ring and its bar are the ground, of one tone: the bar runs into the ring
        body = f'<path fill="{paint_}" fill-rule="evenodd" d="{ground}"/><path fill="{paint_}" d="{track}"/>'
    else:
        body = f'<path fill="{paint_}" d="{ground}"/>' + (
            f'<path fill="{LIGHT_SIGN}" fill-rule="evenodd" d="{track}"/>' if signed else "")
    return (head + body + "</svg>").encode()


FILL_TOKEN = "@fill@"


def report_marks() -> dict:
    """The marks of the report's results, by level (ok, warn, fail, info): each the symbol's SVG with FILL_TOKEN where
    the report's own colour of the level goes (the template, report_typst/template.typ, puts it there)."""
    return {level: svg(name, fill=FILL_TOKEN, signed=True).decode() for level, name in LEVEL.items()}
