"""A level's sign and its count: the sign in its colour, the number in the text's. `paint` draws the two without a
container (R328, P1; Daniel, 02/11/2026: no bean left), as the tree's rows have them; a count of nought has its sign
grey and its number muted. `paint_pill` draws them in a pill of their own, separate from the next, radius 6, tinted
with the level's tone (R335, P3: «forse le pillole P3 sono meglio di quelle a pista», 03/11/2026): the counts of the
Checks' head (checks_page.CountChip). The sign is `symbols.paint`, the one drawing of a symbol: to change how the
signs look is to change it there.

The module keeps its old name: the tests and the callers know it by it."""
from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen

from .. import theme_colors
from . import symbols

LEFT, RIGHT, GAP = 6, 8, 4
SYMBOL = 12


@dataclass(frozen=True)
class Parts:
    symbol_box: QRectF
    number: QPainterPath


def _number(text: str, font: QFont) -> QPainterPath:
    path = QPainterPath()
    path.addText(QPointF(), font, text)
    return path


def size_hint(text: str, font: QFont, height: int, reserve: str = "") -> QSize:
    width = max(_number(text, font).boundingRect().width(), _number(reserve, font).boundingRect().width())
    return QSize(math.ceil(LEFT + SYMBOL + GAP + width + RIGHT), height)


def layout(rect: QRectF, text: str, font: QFont) -> Parts:
    box = QRectF(rect.left() + LEFT, rect.center().y() - SYMBOL / 2, SYMBOL, SYMBOL)
    number = _number(text, font)
    bounds = number.boundingRect()
    number.translate(rect.right() - RIGHT - bounds.right(), rect.center().y() - bounds.center().y())
    return Parts(box, number)


def tints(level: str, t: dict, dark: bool) -> dict:
    """The grounds and lines of a level's pill (R335, P3: the bozzetto's `.p3`): the level's tone mixed into the
    window's colour, 10 % with a line of 28 % at rest (17 % and 38 % on a dark ground), 19 % (26 %) with a line of
    65 % while its filter is on; under the pointer half way between rest and on."""
    tone = symbols.colour(symbols.LEVEL.get(level, "info"), dark)
    ground = t["window"]

    def mix(share: float) -> QColor:
        return QColor(theme_colors.mix(ground, tone, share))
    rest = (0.17, 0.38) if dark else (0.10, 0.28)
    on = (0.26 if dark else 0.19, 0.65)
    return {"rest": (mix(rest[0]), mix(rest[1])), "on": (mix(on[0]), mix(on[1])),
            "hover": (mix((rest[0] + on[0]) / 2), mix((rest[1] + on[1]) / 2))}


def paint_pill(painter: QPainter, rect: QRectF, level: str, text: str, font: QFont, t: dict, on: bool = False,
               off: bool = False, hover: bool = False, ring: bool = False) -> None:
    """A level's count as a pill of its own (R335, P3; Daniel, 03/11/2026): a ground and a line tinted with the level's
    tone, radius 6, the sign in its colour and the number in the text's. `on`: its filter is on; `off`: a count of
    nought, faded as a whole but in its place; `hover`: under the pointer; `ring`: the keyboard is on it."""
    from .design import Line, Radius
    dark = symbols.dark_ground()
    ground, line = tints(level, t, dark)["on" if on else "hover" if hover else "rest"]
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if off:
        painter.setOpacity(0.55)
    inset = Line.HAIR / 2
    painter.setPen(QPen(line, Line.HAIR))
    painter.setBrush(ground)
    painter.drawRoundedRect(rect.adjusted(inset, inset, -inset, -inset), Radius.CONTROL, Radius.CONTROL)
    paint(painter, rect, level, text, font, QColor(t["text"]))
    painter.setOpacity(1)
    if ring:
        painter.setPen(QPen(QColor(t["accent"]), Line.FOCUS))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inset = Line.FOCUS / 2
        painter.drawRoundedRect(rect.adjusted(inset, inset, -inset, -inset), Radius.CONTROL, Radius.CONTROL)
    painter.restore()


def paint(painter: QPainter, rect: QRectF, level: str, text: str, font: QFont, ink: QColor, off: bool = False) -> None:
    """The sign of `level` at the left of `rect` and `text` at its right, in `ink`; `off`: the sign grey, for a count of
    nought, which keeps its place."""
    parts = layout(rect, text, font)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    symbols.paint(painter, parts.symbol_box, symbols.LEVEL.get(level, "info"), off=off)
    painter.fillPath(parts.number, ink)
    painter.restore()
