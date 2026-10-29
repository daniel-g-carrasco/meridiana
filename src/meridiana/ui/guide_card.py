"""A reusable non-modal guide card. Its consumer owns navigation and persistence."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ..i18n import _
from .design import Space


class GuideCard(QDialog):
    def __init__(self, title: str, parent=None, *, invitation: bool = False):
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle(title)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, invitation)
        self.setModal(False)
        self.setMaximumWidth(470)
        box = QVBoxLayout(self)
        box.setContentsMargins(Space.L, Space.L, Space.L, Space.L)
        self.progress = QLabel()
        self.heading = QLabel()
        self.heading.setWordWrap(True)
        self.heading.setTextFormat(Qt.TextFormat.PlainText)
        self.description = QLabel()
        self.description.setWordWrap(True)
        self.description.setMinimumWidth(280)
        self.description.setTextFormat(Qt.TextFormat.PlainText)
        for label in (self.progress, self.heading, self.description):
            box.addWidget(label)
        row = QHBoxLayout()
        self.previous = QPushButton(_("Previous"))
        self.next = QPushButton(_("Next"))
        self.skip = QPushButton(_("Later"))
        for button in (self.previous, self.next, self.skip):
            row.addWidget(button)
        box.addLayout(row)
        self.resize(430, 240)
