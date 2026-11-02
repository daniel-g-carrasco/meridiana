"""The symbols of the window (R138, Daniel 25/10/2026: «per l'applicativo Spola avevamo creato dei begli svg ... che
vorrei utilizzare anche qua in Meridiana a livello globale»): Spola's check, forbidden, warning and error, and the
cross, the stop and the info drawn in the same geometry (a 16-unit disc, strokes 1.7 wide). Flat (R330, Daniel
02/11/2026: «come simboli usiamo quelli piatti»): the ground of one tone, the sign opaque on it, the same for all of
them, so that it reads on any ground, an orthophoto and the dark panels too (the flat ones of 25/10/2026 were refused
because their sign was cut out and showed what lay under it: this one is painted). The warning's triangle is as wide
as the disc's diameter. SVG drawn by Qt's own renderer at the size and the density asked, never a character of a font
(a missing glyph left a box in the place of the cross).

What each one says (the same in the template, qtkit):
- check: confirmed, passed;
- cross: close, no;
- forbidden: an operation not allowed;
- stop: a block (the checks to fix);
- info: details (the checks to know, notes);
- warning: a possible problem (the checks to check);
- error: the program ran into an error;
- trash: throw away (a dialog's «Discard»), on the red;
- back: go back, nothing done (a dialog's «Cancel»), on the grey (R169, Daniel 26/10/2026: «il pulsante scarta vorrei
  che avesse un bel cestino. Mentre l'annulla un simbolo di tornare indietro»).

Colours: the status colours of the theme (theme_colors.STATUS), a lighter blue and grey on a dark ground, where the
dark ones vanish. `sign` is the sign alone, for a pill already in the level's colour. The tracks, the tones and the SVG
are in `meridiana/symbol_shapes.py`, without Qt, because the report's Typst template draws the same marks (R330)."""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QIconEngine, QImage, QPainter, QPainterPath, QPixmap, QTransform
from PySide6.QtSvg import QSvgRenderer

# the tracks, the tones and the SVG are in symbol_shapes.py, which the report reads too without Qt
from ..symbol_shapes import DISC, LEVEL, LIGHT_SIGN, NAMES, SHAPES, TONES, TONES_DARK, TRIANGLE, colour, svg  # noqa: F401

_RENDERERS: dict = {}


def renderer(name: str, dark: bool = False, fill: str | None = None) -> QSvgRenderer:
    key = (name, dark, fill)
    if key not in _RENDERERS:
        _RENDERERS[key] = QSvgRenderer(QByteArray(svg(name, dark, fill)))
    return _RENDERERS[key]


def dark_ground() -> bool:
    """Whether the window's ground is dark (the theme in use)."""
    app = QGuiApplication.instance()
    return app is not None and QGuiApplication.palette().window().color().lightnessF() < 0.5


def paint(painter: QPainter, rect: QRectF, name: str, dark: bool | None = None, off: bool = False) -> None:
    """The symbol in `rect` (square), as it is on any ground: no halo (Daniel, 25/10/2026: «terribili»). `off`: in the
    grey of the symbols, for a level with nothing in it (R328). The one drawing of a symbol: the signs of the views, of
    the tree and of the counts all come through here, and a new look of them changes here."""
    dark = dark_ground() if dark is None else dark
    if off:
        renderer(name, dark, fill=TONES_DARK["neutral"] if dark else TONES["neutral"]).render(painter, rect)
        painter.fillPath(sign(name, rect), QColor(LIGHT_SIGN))
        return
    renderer(name, dark).render(painter, rect)


def sign(name: str, rect: QRectF) -> QPainterPath:
    """The sign alone (the check, the cross, the stop's bar, the i, the !) as a path in `rect`, for a pill already in the level's colour."""
    path = _parse(SHAPES[name][2])
    scale = rect.width() / 16
    return QTransform().translate(rect.x(), rect.y()).scale(scale, scale).map(path)


def _parse(d: str) -> QPainterPath:
    """The few SVG path commands the shapes use (M, L, A for half circles or two halves of a dot, Z) into a
    QPainterPath."""
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
            # the shapes' arcs are half circles: the circle through `last` and (x, y)
            cx, cy = (last[0] + x) / 2, (last[1] + y) / 2
            box = QRectF(cx - r, cy - r, 2 * r, 2 * r)
            if i + 8 < len(tokens) and tokens[i + 8] == "A":    # two halves of the same dot
                path.addEllipse(box)
                last, i = (x, y), i + 16
                continue
            # SVG's sweep 1 turns clockwise on the screen, which is Qt's negative way
            start = math.degrees(math.atan2(cy - last[1], last[0] - cx))
            path.arcTo(box, start, -180.0 if tokens[i + 5] == "1" else 180.0)
            last, i = (x, y), i + 8
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


IN_TEXT = 14            # logical pixels of a symbol in a line of text (13 px)
_FILES: dict = {}       # (name, dark) -> the 1x file of its pictures


def html(name: str, size: int = IN_TEXT) -> str:
    """The symbol in rich text, for a label (R154, Daniel 25/10/2026: «non hai applicato i simboli nuovi
    dappertutto»: the notes, the checks of the strings, the keys' dialog had the characters ⚠ ✘ ℹ ✔). Its pictures
    are written once at 1, 2 and 3 times the size in the temporary folder: Qt takes the «@2x» or «@3x» one on a
    screen at 200 or 250 % by itself. The character when the folder cannot be written."""
    dark = dark_ground()
    path = _FILES.get((name, dark))
    if path is None:
        path = _write(name, dark, size)
        _FILES[(name, dark)] = path
    if not path:
        return {"check": "✔", "cross": "✕", "warning": "⚠", "error": "✘", "stop": "✘", "info": "ℹ",
                "back": "↶", "update": "⟳"}.get(name, "")
    return f'<img src="{path}" width="{size}" height="{size}" style="vertical-align: middle">'


def _write(name: str, dark: bool, size: int) -> str:
    folder = Path(tempfile.gettempdir()) / "meridiana-symbols"
    first = folder / f"{name}-{'dark' if dark else 'light'}-{size}.png"
    try:
        folder.mkdir(exist_ok=True)
        for k in (1, 2, 3):
            f = first if k == 1 else first.with_name(f"{first.stem}@{k}x.png")
            if f.exists():
                continue
            image = QImage(size * k, size * k, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            p = QPainter(image)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer(name, dark).render(p, QRectF(0, 0, size * k, size * k))
            p.end()
            if not image.save(str(f)):
                return ""
    except OSError:
        return ""
    return first.as_posix()
