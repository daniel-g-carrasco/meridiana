"""Opening a PVsyst project: the variants found next to its .PRJ to choose from, then what was read, what is
approximated, what is left out and what is missing, before anything is created (pvsyst/mapping.py)."""

from __future__ import annotations

import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QListWidget, QListWidgetItem, QTextBrowser,
                               QVBoxLayout)

from ..i18n import _


class VariantsChoice(QDialog):
    """The variants of the project, ticked to import: all of them when they are few, else the first."""

    def __init__(self, prj, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Import a PVsyst project"))
        box = QVBoxLayout(self)
        intro = QLabel(_("{name}: {n} variants next to the project file. Each one ticked becomes a variant of the "
                         "Meridiana project.").format(name=prj.name, n=len(prj.variants)))
        intro.setWordWrap(True)
        box.addWidget(intro)
        self.list = QListWidget()
        for k, v in enumerate(prj.variants):
            text = f"{v.path.suffix[1:]} · {v.comment or '?'}"
            details = ", ".join(x for x in (v.system_kind, _("PVsyst {v}").format(v=v.version) if v.version else "",
                                            v.computed) if x)
            item = QListWidgetItem(text + (f"  ({details})" if details else ""))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if (len(prj.variants) <= 4 or k == 0) else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, k)
            self.list.addItem(item)
        box.addWidget(self.list, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(_("Read the variants"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        box.addWidget(buttons)
        self.resize(560, 360)

    def chosen(self) -> list[int]:
        return [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.CheckState.Checked]


def summary_html(report) -> str:
    parts = []
    for title, items in ((_("Read"), report.read), (_("Approximated"), report.approximated),
                         (_("Not imported"), report.not_imported), (_("Missing"), report.missing)):
        if not items:
            continue
        parts.append(f"<h3>{html.escape(title)} ({len(items)})</h3><ul>")
        parts += [f"<li>{html.escape(x)}</li>" for x in items]
        parts.append("</ul>")
    return "".join(parts)


class ImportSummary(QDialog):
    def __init__(self, name: str, report, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Import a PVsyst project"))
        box = QVBoxLayout(self)
        intro = QLabel(_("What Meridiana read from {name}, and how. Nothing is written beside PVsyst's files; the new "
                         "project opens unsaved.").format(name=name))
        intro.setWordWrap(True)
        box.addWidget(intro)
        self.text = QTextBrowser()
        self.text.setHtml(summary_html(report))
        box.addWidget(self.text, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(_("Create the project"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        box.addWidget(buttons)
        self.resize(720, 560)
