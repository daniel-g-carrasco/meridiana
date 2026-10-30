"""Quiet status counts shared by tree indicators and interactive filter chips.

The painter accepts a palette and a font, with no project or check model dependency. Signs and counts
are vector paths centred on their visible ink, with one geometry at every screen density.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPainterPath, QPalette, QPen, QTransform

from .. import theme_colors
from . import symbols

LEFT, RIGHT, GAP = 6, 10, 4
SYMBOL = 13


@dataclass(frozen=True)
class Parts:
    symbol_box: QRectF
    symbol: QPainterPath
    number: QPainterPath


def _number(text: str, font: QFont) -> QPainterPath:
    path = QPainterPath()
    path.addText(QPointF(), font, text)
    return path


def size_hint(text: str, font: QFont, height: int, reserve: str = "") -> QSize:
    width = max(_number(text, font).boundingRect().width(), _number(reserve, font).boundingRect().width())
    return QSize(math.ceil(LEFT + SYMBOL + GAP + width + RIGHT), height)


def layout(rect: QRectF, level: str, text: str, font: QFont) -> Parts:
    box = QRectF(rect.left() + LEFT, rect.center().y() - SYMBOL / 2, SYMBOL, SYMBOL)
    sign = symbols.sign(symbols.LEVEL.get(level, "info"), QRectF(0, 0, 16, 16))
    bounds = sign.boundingRect()
    scale = SYMBOL / max(bounds.width(), bounds.height())
    sign = QTransform.fromScale(scale, scale).map(sign)
    sign.translate(box.center() - sign.boundingRect().center())
    number = _number(text, font)
    bounds = number.boundingRect()
    number.translate(rect.right() - RIGHT - bounds.right(), rect.center().y() - bounds.center().y())
    return Parts(box, sign, number)


def _mix(first: QColor, second: QColor, amount: float) -> QColor:
    return QColor(theme_colors.mix(first.name(), second.name(), amount))


def colours(level: str, palette: QPalette, *, zero: bool = False, checked: bool = False,
            hovered: bool = False, pressed: bool = False, enabled: bool = True) -> tuple[QColor, QColor, QColor]:
    base = palette.color(QPalette.ColorRole.Window)
    if base.alpha() < 255:
        # Qt style sheets expose transparent controls' Window as transparent black,
        # and a tree's Base can even become opaque black. Use the real themed floor.
        base = QGuiApplication.palette().color(QPalette.ColorRole.Window)
    ink = palette.color(QPalette.ColorRole.WindowText)
    dark = base.lightness() < 128
    tone = QColor(symbols.colour(symbols.LEVEL.get(level, "info"), dark))
    ground = _mix(base, tone, (0.26 if checked else 0.17) if dark else (0.19 if checked else 0.10))
    line = _mix(base, tone, 0.65 if checked else 0.38 if dark else 0.28)
    if hovered or pressed:
        ground = _mix(ground, ink, 0.09 if pressed else 0.04)
    if zero or not enabled:
        ground = _mix(base, ground, 0.5)
        line = _mix(base, line, 0.5)
        ink = _mix(ink, base, 0.45)
    return ground, ink, line


def paint(painter: QPainter, rect: QRectF, level: str, text: str, font: QFont, palette: QPalette,
          *, checked: bool = False, hovered: bool = False, pressed: bool = False,
          focused: bool = False, enabled: bool = True) -> None:
    ground, ink, line = colours(level, palette, zero=text == "0", checked=checked, hovered=hovered,
                               pressed=pressed, enabled=enabled)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    width = 2 if focused else 1
    painter.setPen(QPen(palette.color(QPalette.ColorRole.Highlight) if focused else line, width))
    painter.setBrush(ground)
    outline = rect.adjusted(width / 2, width / 2, -width / 2, -width / 2)
    painter.drawRoundedRect(outline, outline.height() / 2, outline.height() / 2)
    parts = layout(rect, level, text, font)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.fillPath(parts.symbol, ink)
    painter.fillPath(parts.number, ink)
    painter.restore()
