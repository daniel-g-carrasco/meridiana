"""Native checkbox indicators: quiet selection, canonical signs and a fully contained focus ring.

Mixed into the application's existing proxy style, so checkboxes and item-view checks keep Qt's interaction and accessibility.
The 16 px square sits in a 22 px allocation: 3 px per side keep the 2 px focus stroke and its antialiasing inside
the control, including at the left edge and fractional display densities. No widget masks or extra proxy styles.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractItemView, QCheckBox, QStyle

from .. import theme_colors
from . import symbols
from .design import Icon, Line, Radius, Size, Space


class CheckboxStyle:
    """Style mixin; the owning proxy supplies `tokens` and delegates the other native controls."""

    def pixelMetric(self, metric, option=None, widget=None):
        if isinstance(widget, (QCheckBox, QAbstractItemView)):
            if metric in (QStyle.PixelMetric.PM_IndicatorWidth, QStyle.PixelMetric.PM_IndicatorHeight):
                return Icon.CONTROL + Space.S
            if isinstance(widget, QCheckBox) and metric == QStyle.PixelMetric.PM_CheckBoxLabelSpacing:
                return Space.M
        return super().pixelMetric(metric, option, widget)

    def sizeFromContents(self, kind, option, size, widget=None):
        result = super().sizeFromContents(kind, option, size, widget)
        if kind == QStyle.ContentsType.CT_CheckBox and isinstance(widget, QCheckBox):
            return QSize(result.width(), max(Size.CONTROL, result.height()))
        return result

    def drawPrimitive(self, element, option, painter, widget=None):
        checkbox = isinstance(widget, QCheckBox)
        item_check = (isinstance(widget, QAbstractItemView)
                      and element == QStyle.PrimitiveElement.PE_IndicatorItemViewItemCheck)
        if not (checkbox or item_check) or not self.tokens:
            return super().drawPrimitive(element, option, painter, widget)
        if checkbox and element == QStyle.PrimitiveElement.PE_FrameFocusRect:
            return  # The whole focus indicator is drawn around the square below.
        if element != QStyle.PrimitiveElement.PE_IndicatorCheckBox and not item_check:
            return super().drawPrimitive(element, option, painter, widget)
        t = self.tokens
        flags = QStyle.StateFlag
        enabled = bool(option.state & flags.State_Enabled)
        checked = bool(option.state & flags.State_On)
        partial = bool(option.state & flags.State_NoChange)
        ground = t["select_bg"] if checked or partial else t["field"]
        ink, border = t["text"], t["field_line"]
        if enabled and option.state & flags.State_MouseOver:
            ground = theme_colors.state(t, ground, theme_colors.HOVER)
            border = t["text2"]
        if enabled and option.state & flags.State_Sunken:
            ground = theme_colors.state(t, ground, theme_colors.PRESS)
        if not enabled:
            ground, ink, border = t["field"], t["muted"], t["line"]
        glyph = QRectF(0, 0, Icon.CONTROL, Icon.CONTROL)
        glyph.moveCenter(QRectF(option.rect).center())
        rect = glyph.adjusted(Line.HAIR / 2, Line.HAIR / 2, -Line.HAIR / 2, -Line.HAIR / 2)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(ground))
        painter.setPen(QPen(QColor(border), Line.HAIR))
        painter.drawRoundedRect(rect, Radius.INNER, Radius.INNER)
        if checked or partial:
            painter.fillPath(symbols.sign("stop" if partial else "check", glyph), QColor(ink))
        if enabled and option.state & flags.State_HasFocus:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(t["accent"]), Line.FOCUS))
            painter.drawRoundedRect(rect.adjusted(-Space.XXS, -Space.XXS, Space.XXS, Space.XXS),
                                    Radius.CONTROL, Radius.CONTROL)
        painter.restore()
