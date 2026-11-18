"""A round help control for rows of fields, with its question mark optically centred."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPalette
from PySide6.QtWidgets import QStyle, QStyleOptionToolButton, QToolButton

from .design import Size, Text, text_font


class HelpButton(QToolButton):
    """The help action on a control row; its tooltip also names it to assistive tools.

    The small help marks inside card titles keep their separate Button.HELP scale.
    Connect ``clicked`` to the application's help view and supply its tooltip.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("row-help-button")
        self.setText("?")
        self.setFont(text_font(Text.STRONG))
        self.setFixedSize(Size.CONTROL, Size.CONTROL)
        self.setAutoRaise(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def setToolTip(self, text: str) -> None:
        super().setToolTip(text)
        self.setAccessibleName(text)

    def paintEvent(self, event) -> None:
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        option.text = ""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.style().drawComplexControl(QStyle.ComplexControl.CC_ToolButton, option, painter, self)
        if not self.text():
            return
        glyph = QPainterPath()
        glyph.addText(QPointF(), self.font(), self.text())
        offset = QRectF(self.rect()).center() - glyph.boundingRect().center()
        painter.translate(offset)
        painter.fillPath(glyph, option.palette.color(QPalette.ColorRole.ButtonText))
