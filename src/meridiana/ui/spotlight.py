"""A brief, pointer-transparent guide around an existing control, without changing its focus or value."""

from __future__ import annotations

import math

from PySide6.QtCore import QEvent, QRect, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import QScrollArea, QWidget

from . import motion
from .design import Radius, Space

DURATION = 1500
MARGIN = Space.S + Space.XS


class Spotlight(QWidget):
    """One small overlay on the target's window; follows layout and scroll changes and expires by itself."""

    def __init__(self, target: QWidget, duration: int = DURATION, region=None):
        super().__init__(target.window())
        self.target = target
        self.region = region
        self.still = motion.reduced()
        self.progress = 0.0
        self.watched = []
        self.setObjectName("navigation-spotlight")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.colour = target.palette().color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent)
        ancestor = target
        while ancestor is not None:
            ancestor.installEventFilter(self)
            self.watched.append(ancestor)
            if ancestor is self.parentWidget():
                break
            ancestor = ancestor.parentWidget()
        target.destroyed.connect(self.finish)
        self.animation = QVariantAnimation(self)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setDuration(max(1, duration))
        self.animation.valueChanged.connect(self._advance)
        self.animation.finished.connect(self.finish)
        self._place()
        self.show()
        self.raise_()
        self.animation.start()

    def _place(self) -> None:
        rect = self.region() if self.region is not None else self.target.rect()
        origin = self.target.mapTo(self.parentWidget(), rect.topLeft())
        wanted = QRect(origin.x() - MARGIN, origin.y() - MARGIN,
                       rect.width() + 2 * MARGIN, rect.height() + 2 * MARGIN)
        visible = wanted.intersected(self.parentWidget().rect())
        self.setGeometry(visible)
        self.target_rect = QRectF(origin.x() - visible.x(), origin.y() - visible.y(), rect.width(), rect.height())

    def ring_rect(self) -> QRectF:
        pulse = 0.0 if self.still else 1.5 * math.sin(self.progress * math.pi * 2) ** 2
        growth = 3 + pulse
        ring = self.target_rect.adjusted(-growth, -growth, growth, growth)
        return ring.intersected(QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5))

    def _advance(self, value) -> None:
        self.progress = float(value)
        self.update()

    def finish(self, *_args) -> None:
        self.animation.stop()
        self.hide()
        for watched in self.watched:
            try:
                watched.removeEventFilter(self)
            except RuntimeError:
                continue  # The control may be destroyed when its page is rebuilt.
        self.watched.clear()
        self.deleteLater()

    def eventFilter(self, obj, event) -> bool:
        if event.type() in (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.LayoutRequest):
            self._place()
        elif event.type() in (QEvent.Type.Hide, QEvent.Type.Close):
            self.finish()
        return False

    def paintEvent(self, _event) -> None:
        opacity = min(1.0, self.progress / 0.1, (1.0 - self.progress) / 0.3)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(max(0.0, opacity))
        ink = QColor(self.colour)
        ink.setAlpha(220)
        fill = QColor(self.colour)
        fill.setAlpha(16)
        painter.setPen(QPen(ink, 2.0))
        painter.setBrush(fill)
        painter.drawRoundedRect(self.ring_rect(), Radius.CONTROL + 2, Radius.CONTROL + 2)


def reveal(target: QWidget, duration: int = DURATION, region=None) -> Spotlight:
    """Scroll each enclosing area to `target`, then guide the eye. Never focuses or edits the control."""
    if not target.isVisible():
        raise ValueError("the requested control is not visible")
    ancestor = target.parentWidget()
    while ancestor is not None:
        if isinstance(ancestor, QScrollArea):
            ancestor.ensureWidgetVisible(target, MARGIN, MARGIN)
        ancestor = ancestor.parentWidget()
    for previous in target.window().findChildren(Spotlight):
        previous.finish()
    return Spotlight(target, duration, region)
