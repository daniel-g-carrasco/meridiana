"""An editable issue draft with a deliberate browser handoff."""
import platform
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFileDialog, QFormLayout,
                              QGridLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout)

from .. import __version__, feedback
from ..i18n import _
from .design import Space


class FeedbackDialog(QDialog):
    def __init__(self, parent=None, summary="", details="", context="", opener=None):
        super().__init__(parent)
        self.setWindowTitle(_("Report a problem"))
        self.resize(640, 640)
        self.context_text = context
        self.opener = opener or QDesktopServices.openUrl
        box = QVBoxLayout(self)
        box.setContentsMargins(Space.L, Space.L, Space.L, Space.L)
        intro = QLabel(_("Review this draft before sharing it. The browser opens a GitHub draft; you decide whether to submit it. Reports there are public."))
        intro.setWordWrap(True)
        box.addWidget(intro)
        form = QFormLayout()
        self.title = QLineEdit(summary[:180])
        self.title.setMaxLength(180)
        self.description = QTextEdit()
        self.description.setAcceptRichText(False)
        self.description.setPlainText(details)
        self.description.setPlaceholderText(_("What were you doing? What happened, and what did you expect? Add the steps needed to reproduce it."))
        form.addRow(_("Title"), self.title)
        form.addRow(_("Description"), self.description)
        box.addLayout(form)
        self.environment = QCheckBox(_("Include application and system versions"))
        self.environment.setChecked(True)
        self.context = QCheckBox(_("Include the current phase and object counts"))
        self.context.setEnabled(bool(context))
        box.addWidget(self.environment)
        box.addWidget(self.context)
        self.include_diagnostics = QCheckBox(_("Include a selected diagnostic excerpt"))
        self.diagnostics = QTextEdit()
        self.diagnostics.setAcceptRichText(False)
        self.diagnostics.setPlaceholderText(_("Paste only the diagnostic lines you want to share. Review the redacted preview below."))
        self.diagnostics.setMaximumHeight(80)
        self.diagnostics.setEnabled(False)
        box.addWidget(self.include_diagnostics)
        box.addWidget(self.diagnostics)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setAccessibleName(_("Preview of the shared text"))
        box.addWidget(QLabel(_("Preview of the shared text")))
        box.addWidget(self.preview)
        self.notice = QLabel(_("Project files, paths, logs and the conversation are not attached. You can add selected files yourself on GitHub."))
        self.notice.setWordWrap(True)
        box.addWidget(self.notice)
        row = QGridLayout()
        self.copy = QPushButton(_("Copy draft"))
        self.save = QPushButton(_("Save draft…"))
        self.open = QPushButton(_("Open GitHub draft"))
        close = QPushButton(_("Close"))
        for index, button in enumerate((self.copy, self.save, self.open, close)):
            row.addWidget(button, index//2, index % 2)
        box.addLayout(row)
        self.copy.clicked.connect(lambda: QApplication.clipboard().setText(self.preview.toPlainText()))
        self.save.clicked.connect(self._save)
        self.open.clicked.connect(self._open)
        close.clicked.connect(self.reject)
        self.title.textChanged.connect(self._refresh)
        self.description.textChanged.connect(self._refresh)
        self.environment.toggled.connect(self._refresh)
        self.context.toggled.connect(self._refresh)
        self.include_diagnostics.toggled.connect(self.diagnostics.setEnabled)
        self.include_diagnostics.toggled.connect(self._refresh)
        self.diagnostics.textChanged.connect(self._refresh)
        self._refresh()

    def draft(self):
        return feedback.Draft(self.title.text(), self.description.toPlainText(), __version__, platform.system(),
                              platform.python_version(), self.context_text if self.context.isChecked() else "",
                              self.diagnostics.toPlainText() if self.include_diagnostics.isChecked() else "",
                              include_environment=self.environment.isChecked())

    def _refresh(self):
        draft = self.draft()
        self.preview.setPlainText(draft.body())
        self.open.setEnabled(bool(draft.title.strip() and draft.description.strip()))

    def _open(self):
        try:
            url = self.draft().issue_url()
        except ValueError:
            self.notice.setText(_("This draft is too long for a browser link. Copy or save it, then paste it into a new issue."))
            return
        if not self.opener(QUrl(url)):
            self.notice.setText(_("The browser could not be opened. Copy or save the draft to keep it."))

    def _save(self):
        path, _filter = QFileDialog.getSaveFileName(self, _("Save draft"), "meridiana-issue.txt", _("Text files (*.txt)"))
        if not path:
            return
        try:
            # Existing files are never replaced by the draft exporter.
            with Path(path).open("x", encoding="utf-8") as stream:
                stream.write(self.title.text() + "\n\n" + self.preview.toPlainText())
        except OSError as error:
            self.notice.setText(_("The draft could not be saved: {error}").format(error=error))
