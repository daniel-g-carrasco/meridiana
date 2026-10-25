"""The keyboard shortcuts: every command with its keys and their defaults, a search over both, and the keys of
the chosen command changed in place. While the new keys are typed the editor says what they would take away
from another command, or why they are better avoided (shortcuts.clashes and shortcuts.problem, in the core),
as FreeCAD's dialog does but in words (study 15, 3.9). The same editor is a page of the preferences."""

from __future__ import annotations

import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QKeySequenceEdit, QLabel,
                               QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import shortcuts
from ..i18n import _
from . import symbols

ID = Qt.ItemDataRole.UserRole


def native(keys: list) -> str:
    """Keys as the system writes them in its menus (Ctrl+Maiusc+P on an Italian Windows)."""
    return ", ".join(QKeySequence(k).toString(QKeySequence.SequenceFormat.NativeText) for k in keys)


class ShortcutsEditor(QWidget):
    changed = Signal()

    def __init__(self, bindings: dict, parent=None):
        super().__init__(parent)
        self.bindings = {k: list(v) for k, v in bindings.items()}
        self.defaults = shortcuts.bindings({})
        self.names = {c.id: shortcuts.plain(c.text) for c in shortcuts.commands()}
        box = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Search a command or a key"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        box.addWidget(self.search)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([_("Command"), _("Keys"), _("Default")])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.setRootIsDecorated(False)
        self.tree.currentItemChanged.connect(lambda *_a: self._chosen())
        box.addWidget(self.tree, 1)
        row = QHBoxLayout()
        self.edit = QKeySequenceEdit()
        self.edit.setMaximumSequenceLength(1)
        self.edit.setClearButtonEnabled(True)
        self.edit.keySequenceChanged.connect(self._typed)
        row.addWidget(QLabel(_("New keys")))
        row.addWidget(self.edit, 1)
        self.use = QPushButton(_("Use"))
        self.use.clicked.connect(self._use)
        row.addWidget(self.use)
        self.none = QPushButton(_("No key"))
        self.none.clicked.connect(lambda: self._set(self._current(), []))
        row.addWidget(self.none)
        self.back = QPushButton(_("Default"))
        self.back.clicked.connect(lambda: self._set(self._current(), list(self.defaults[self._current()])))
        row.addWidget(self.back)
        box.addLayout(row)
        self.warning = QLabel()
        self.warning.setWordWrap(True)
        self.warning.setTextFormat(Qt.TextFormat.RichText)
        box.addWidget(self.warning)
        bottom = QHBoxLayout()
        note = QLabel(_("Single letters work everywhere except while writing in a field. On a laptop the F keys may "
                        "need Fn (or Fn+Esc to lock it)."))
        note.setWordWrap(True)
        bottom.addWidget(note, 1)
        reset = QPushButton(_("All defaults"))
        reset.clicked.connect(self._reset_all)
        bottom.addWidget(reset)
        box.addLayout(bottom)
        self._fill()
        self._chosen()

    def _fill(self) -> None:
        current = self._current()
        self.tree.clear()
        groups = shortcuts.groups()
        for c in shortcuts.commands():
            keys = self.bindings.get(c.id, [])
            it = QTreeWidgetItem([self.names[c.id], native(keys), native(self.defaults[c.id])])
            it.setData(0, ID, c.id)
            it.setToolTip(0, groups.get(c.group, ""))
            if keys != self.defaults[c.id]:
                font = it.font(1)
                font.setWeight(font.Weight.DemiBold)      # the catalogue's one weight that stands out (R121)
                it.setFont(1, font)
            self.tree.addTopLevelItem(it)
            if c.id == current:
                self.tree.setCurrentItem(it)
        self._filter(self.search.text())

    def _filter(self, text: str) -> None:
        t = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            it.setHidden(bool(t) and not any(t in it.text(col).lower() for col in range(3)))

    def _current(self) -> str:
        it = self.tree.currentItem()
        return it.data(0, ID) if it is not None else ""

    def _chosen(self) -> None:
        cid = self._current()
        for w in (self.edit, self.use, self.none, self.back):
            w.setEnabled(bool(cid))
        self.edit.clear()
        self.warning.setText("")

    def _typed(self, seq: QKeySequence) -> None:
        """While the keys are typed: what they would take away, or why not."""
        keys = seq.toString(QKeySequence.SequenceFormat.PortableText)
        self.warning.setText(self.verdict(self._current(), keys) if keys else "")

    def verdict(self, cid: str, keys: str) -> str:
        why = shortcuts.problem(keys)
        if why:
            return symbols.html("stop") + " " + html.escape(why)
        others = shortcuts.clashes(self.bindings, cid, keys)
        if others:
            return symbols.html("warning") + " " + html.escape(_("{keys} is used by {what}: there it would stop working.").format(
                keys=native([keys]), what=", ".join(f"«{self.names[o]}»" for o in others)))
        return ""

    def _use(self) -> None:
        cid = self._current()
        keys = self.edit.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
        if not cid or not keys or shortcuts.problem(keys):
            return
        self.assign(cid, keys)

    def assign(self, cid: str, keys: str) -> None:
        """`keys` for `cid`, taken away from the commands that had them."""
        keys = shortcuts.normalize(keys)
        for other in shortcuts.clashes(self.bindings, cid, keys):
            self.bindings[other] = [k for k in self.bindings[other] if k != keys]
        self._set(cid, [keys])

    def _set(self, cid: str, keys: list) -> None:
        if not cid:
            return
        self.bindings[cid] = keys
        self._fill()
        self.edit.clear()
        self.changed.emit()

    def _reset_all(self) -> None:
        self.bindings = {k: list(v) for k, v in self.defaults.items()}
        self._fill()
        self.changed.emit()


class ShortcutsDialog(QDialog):
    def __init__(self, bindings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Keyboard shortcuts"))
        self.resize(640, 560)
        box = QVBoxLayout(self)
        self.editor = ShortcutsEditor(bindings, self)
        box.addWidget(self.editor)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        box.addWidget(buttons)
        self.editor.search.setFocus()

    @property
    def bindings(self) -> dict:
        return self.editor.bindings
