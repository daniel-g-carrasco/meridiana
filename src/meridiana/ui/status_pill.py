"""A level's sign and its count, without a container (R328, P1 and P5; Daniel, 02/11/2026: no bean left): the sign in
its colour, the number in the text's. The same in the tree's rows and in the segments of the Checks' levels
(checks_page.CountChip), which stand on a track (ui/segments.py); a count of nought has its sign grey and its number
muted. The sign is `symbols.paint`, the one drawing of a symbol: to change how the signs look is to change it there.

The module keeps its old name (it drew a pill until R328): the tests and the two callers know it by it."""
from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath

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


def paint(painter: QPainter, rect: QRectF, level: str, text: str, font: QFont, ink: QColor, off: bool = False) -> None:
    """The sign of `level` at the left of `rect` and `text` at its right, in `ink`; `off`: the sign grey, for a count of
    nought, which keeps its place."""
    parts = layout(rect, text, font)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    symbols.paint(painter, parts.symbol_box, symbols.LEVEL.get(level, "info"), off=off)
    painter.fillPath(parts.number, ink)
    painter.restore()
