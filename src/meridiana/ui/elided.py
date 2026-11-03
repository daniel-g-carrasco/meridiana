"""A label on one line, cut with «…» when the room is short."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


class ElidedLabel(QLabel):
    """A label on one line: cut with «…» when the room is short, whole in its tooltip unless the owner gives a
    tooltip of its own (`tip`); it never makes its row wider."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setProperty("sized_by_owner", True)        # ui/style.pad_fields leaves it on its line
        self.tip = ""
        self._tip()

    def setText(self, text: str) -> None:
        super().setText(text)
        self._tip()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._tip()

    def _tip(self) -> None:
        cut = self.fontMetrics().horizontalAdvance(self.text()) > self.contentsRect().width()
        self.setToolTip(self.tip or (self.text() if cut else ""))

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        hint.setWidth(24)
        return hint

    def paintEvent(self, event) -> None:
        from PySide6.QtGui import QPainter
        p = QPainter(self)
        r = self.contentsRect()
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, r.width())
        self.style().drawItemText(p, r, int(self.alignment()), self.palette(), self.isEnabled(), text,
                                  self.foregroundRole())
