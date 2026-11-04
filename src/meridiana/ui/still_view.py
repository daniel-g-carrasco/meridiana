"""A heavy drawing that holds still while its size changes: while a panel's edge or the window is dragged, a chart or the
plan would be drawn again whole at each step, and that was the largest part of the gesture's cost (R372: 1057 ms out of
2739 ms on the Consumption page's edge, 444 ms out of 1991 ms on the plan's). From the second step of a gesture on, the
view shows a picture of itself; when the size has been still for a moment it draws itself again.

A single change of size costs nothing more: the picture is made only when a second one follows it. Whatever arrives during
the gesture (new data, a change of zoom) is drawn when it ends.

The view calls `resized` after its own resizeEvent and asks `painted` at the top of its paintEvent. The children of the
viewport (labels, handles) are not in the picture: they draw themselves over it, where they are."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QTimer
from PySide6.QtGui import QPainter, QPixmap, QRegion
from PySide6.QtWidgets import QGraphicsView, QWidget

SETTLE_MS = 120         # no change of size for this long: the gesture is over


class StillWhileResized:
    def __init__(self, view: QGraphicsView, stretch: bool):
        self.view = view
        self.stretch = stretch          # the picture fills the view (a chart); or it stays as it is, in the middle (the plan)
        self.picture: QPixmap | None = None
        self.timer = QTimer(view)
        self.timer.setSingleShot(True)
        self.timer.setInterval(SETTLE_MS)
        self.timer.timeout.connect(self._settled)

    def resized(self) -> None:
        if not self.view.isVisible():
            return
        if self.timer.isActive() and self.picture is None:
            self.picture = self._take()
        self.timer.start()

    def _take(self) -> QPixmap | None:
        port = self.view.viewport()
        ratio = port.devicePixelRatioF()
        size = port.size() * ratio
        if size.isEmpty():
            return None
        picture = QPixmap(size)
        picture.setDevicePixelRatio(ratio)
        port.render(picture, QPoint(), QRegion(), QWidget.RenderFlag.DrawWindowBackground)
        return picture

    def _settled(self) -> None:
        if self.picture is not None:
            self.picture = None
            self.view.viewport().update()

    def painted(self) -> bool:
        """Whether the picture stood in for the drawing."""
        picture = self.picture
        if picture is None:
            return False
        port = self.view.viewport()
        p = QPainter(port)
        if self.stretch:
            p.drawPixmap(port.rect(), picture)
        else:
            p.fillRect(port.rect(), self.view.backgroundBrush())
            size = picture.deviceIndependentSize().toSize()
            p.drawPixmap(QRect((port.width() - size.width()) // 2, (port.height() - size.height()) // 2,
                               size.width(), size.height()), picture)
        p.end()
        return True
