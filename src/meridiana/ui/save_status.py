"""A discreet report of project and recovery saves in the status bar (R195)."""

from __future__ import annotations

import time

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ..i18n import _
from .design import Text, set_text
from .waiting import Spinner


class SaveStatus(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        box = QHBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        self.spinner = Spinner(size=12)
        box.addWidget(self.spinner)
        self.label = set_text(QLabel(), Text.SECONDARY)
        box.addWidget(self.label)

    def begin(self) -> None:
        self.label.setText(_("Saving…"))
        self.spinner.start()

    def finish(self, automatic: bool) -> None:
        self.spinner.stop()
        at = time.strftime("%H:%M")
        self.label.setText(_("Saved automatically at {time}").format(time=at) if automatic else
                           _("Saved at {time}").format(time=at))

    def failed(self) -> None:
        self.spinner.stop()
        self.label.clear()
