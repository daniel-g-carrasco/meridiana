"""The symbols of the window (R138, Daniel 25/10/2026: «per l'applicativo Spola avevamo creato dei begli svg ... che
vorrei utilizzare anche qua in Meridiana a livello globale»): Spola's check, forbidden, warning and error, and the
cross, the stop and the info drawn in the same geometry (a 16-unit disc, strokes 1.7 wide). Drawn as Spola draws its
status on Windows: the ground in a gradient, a little lighter at the top, the sign solid and light on it, the same
for all seven (the warning's «!» is the error's, on the ochre of the warnings: a light sign does not read on the
yellow), so that it reads on any ground, an orthophoto and the dark panels too, with no halo (the flat ones, the
sign cut out, showed what lay under it: the comparison of 25/10/2026). SVG drawn by Qt's own renderer at the size and
the density asked, never a character of a font (a missing glyph left a box in the place of the cross).

What each one says (the same in the template, qtkit):
- check: confirmed, passed;
- cross: close, cancel;
- forbidden: an operation not allowed;
- stop: a block (the checks to fix);
- info: details (the checks to know, notes);
- warning: a possible problem (the checks to check);
- error: the program ran into an error.

Colours: the status colours of the theme (theme_colors.STATUS), a lighter blue and grey on a dark ground, where the
dark ones vanish. `sign` is the sign alone, for a pill already in the level's colour."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QIconEngine, QPainter, QPainterPath, QPixmap, QTransform
from PySide6.QtSvg import QSvgRenderer

from .. import theme_colors

DISC = "M0.5,8 A7.5,7.5 0 1 1 15.5,8 A7.5,7.5 0 1 1 0.5,8 Z"
TRIANGLE = ("M9.23,3.12 L14.25,12.22 A1.4,1.4 0 0 1 13.03,14.3 L2.97,14.3 A1.4,1.4 0 0 1 1.75,12.22 L6.77,3.12 "
            "A1.4,1.4 0 0 1 9.23,3.12 Z")
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
}
NAMES = tuple(SHAPES)
LEVEL = {"fail": "stop", "warn": "warning", "info": "info", "ok": "check"}      # the checks' levels (checks.LEVELS)
TONES = {"good": theme_colors.STATUS["good"], "warning": theme_colors.WARNING_INK,
         "critical": theme_colors.STATUS["critical"], "info": "#2e4a6b", "neutral": "#77767b"}
TONES_DARK = dict(TONES, info="#5b8fc9", neutral="#9a9996")       # on a dark ground the dark blue and the grey vanish
LIGHT_SIGN = "#f3f1ea"                                              # Spola's sign, at 92 %, on every symbol
LIFT = 0.12                                                         # the gradient's top: the tone, this much whiter

_RENDERERS: dict = {}


def colour(name: str, dark: bool = False) -> str:
    return (TONES_DARK if dark else TONES)[SHAPES[name][0]]


def svg(name: str, dark: bool = False, fill: str | None = None) -> bytes:
    """The symbol as an SVG file of 16 x 16; with `fill`, its ground alone in that colour (a halo)."""
    _tone, ground, sign = SHAPES[name]
    head = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
    if fill:
        paint_, defs = fill, ""
    else:
        base = colour(name, dark)
        top = theme_colors.mix(base, "#ffffff", LIFT)
        paint_ = f"url(#g-{name})"
        # in the symbol's units, the same for every path of it (each path's own box gave its own gradient)
        defs = (f'<defs><linearGradient id="g-{name}" gradientUnits="userSpaceOnUse" x1="0" y1="0.5" x2="0" '
                f'y2="15.5"><stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{base}"/>'
                f'</linearGradient></defs>')
    if name == "forbidden":
        # the ring and its bar are the ground, in one gradient: the bar runs into the ring
        body = f'<path fill="{paint_}" fill-rule="evenodd" d="{ground}"/><path fill="{paint_}" d="{sign}"/>'
    else:
        body = f'<path fill="{paint_}" d="{ground}"/>' + (
            "" if fill else f'<path fill="{LIGHT_SIGN}" fill-opacity="0.92" fill-rule="evenodd" d="{sign}"/>')
    return (head + defs + body + "</svg>").encode()


def renderer(name: str, dark: bool = False, fill: str | None = None) -> QSvgRenderer:
    key = (name, dark, fill)
    if key not in _RENDERERS:
        _RENDERERS[key] = QSvgRenderer(QByteArray(svg(name, dark, fill)))
    return _RENDERERS[key]


def dark_ground() -> bool:
    """Whether the window's ground is dark (the theme in use)."""
    app = QGuiApplication.instance()
    return app is not None and QGuiApplication.palette().window().color().lightnessF() < 0.5


def paint(painter: QPainter, rect: QRectF, name: str, dark: bool | None = None) -> None:
    """The symbol in `rect` (square), as it is on any ground: no halo (Daniel, 25/10/2026: «terribili»)."""
    renderer(name, dark_ground() if dark is None else dark).render(painter, rect)


def sign(name: str, rect: QRectF) -> QPainterPath:
    """The sign alone (the check, the cross, the stop's bar, the i, the !) as a path in `rect`, for a pill already in the level's colour."""
    path = _parse(SHAPES[name][2])
    scale = rect.width() / 16
    return QTransform().translate(rect.x(), rect.y()).scale(scale, scale).map(path)


def _parse(d: str) -> QPainterPath:
    """The few SVG path commands the shapes use (M, L, A for full circles, Z) into a QPainterPath."""
    import re
    path = QPainterPath()
    tokens = re.findall(r"[MLAZ]|-?\d+(?:\.\d+)?", d)
    i, last = 0, None
    while i < len(tokens):
        t = tokens[i]
        if t == "M":
            x, y = float(tokens[i + 1]), float(tokens[i + 2])
            path.moveTo(x, y)
            last, i = (x, y), i + 3
        elif t == "L":
            x, y = float(tokens[i + 1]), float(tokens[i + 2])
            path.lineTo(x, y)
            last, i = (x, y), i + 3
        elif t == "A":
            r = float(tokens[i + 1])
            x, y = float(tokens[i + 6]), float(tokens[i + 7])
            # the shapes' arcs are the two halves of a dot: the circle through `last` and (x, y)
            cx, cy = (last[0] + x) / 2, (last[1] + y) / 2
            path.addEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
            last, i = (x, y), i + 8
            if i < len(tokens) and tokens[i] == "A":           # the second half of the same dot
                i += 8
        else:                                                   # Z
            path.closeSubpath()
            i += 1
    path.setFillRule(Qt.FillRule.WindingFill)
    return path


class SymbolIcon(QIconEngine):
    """A symbol as an icon, drawn at the size and the density asked; light or dark with the window's ground."""

    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def paint(self, painter: QPainter, rect, mode, state) -> None:
        side = min(rect.width(), rect.height())
        r = QRectF(rect.x() + (rect.width() - side) / 2, rect.y() + (rect.height() - side) / 2, side, side)
        if mode == QIcon.Mode.Disabled:
            painter.setOpacity(0.4)
        paint(painter, r, self.name)

    def pixmap(self, size: QSize, mode, state) -> QPixmap:
        pix = QPixmap(size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.paint(p, pix.rect(), mode, state)
        p.end()
        return pix

    def scaledPixmap(self, size: QSize, mode, state, scale: float) -> QPixmap:
        pix = self.pixmap(QSize(round(size.width() * scale), round(size.height() * scale)), mode, state)
        pix.setDevicePixelRatio(scale)
        return pix

    def clone(self) -> "SymbolIcon":
        return SymbolIcon(self.name)


def icon(name: str) -> QIcon:
    if name not in SHAPES:
        raise KeyError(f"symbol {name!r}: one of {', '.join(NAMES)}")
    return QIcon(SymbolIcon(name))
