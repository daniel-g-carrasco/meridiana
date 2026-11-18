"""The session's undo stack (session.Undo, without Qt) as the window's menus, toolbar and tests know it:
the part of QUndoStack they used, with its signals."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction

from .. import session


class UndoBridge(QObject):
    indexChanged = Signal(int)
    cleanChanged = Signal(bool)
    canUndoChanged = Signal(bool)
    canRedoChanged = Signal(bool)
    undoTextChanged = Signal(str)
    redoTextChanged = Signal(str)

    def __init__(self, stack: session.Undo, parent=None):
        super().__init__(parent)
        self.stack = stack
        self._last = self._state()
        stack.listeners.append(self._changed)

    def _state(self) -> tuple:
        s = self.stack
        return (s.index, s.is_clean(), s.can_undo(), s.can_redo(), s.undo_text(), s.redo_text())

    def _changed(self) -> None:
        now = self._state()
        was, self._last = self._last, now
        for signal, before, after in zip((self.indexChanged, self.cleanChanged, self.canUndoChanged,
                                          self.canRedoChanged, self.undoTextChanged, self.redoTextChanged),
                                         was, now, strict=True):
            if before != after:
                signal.emit(after)

    def undo(self, _checked: bool = False) -> None:
        self.stack.undo()

    def redo(self, _checked: bool = False) -> None:
        self.stack.redo()

    def count(self) -> int:
        return self.stack.count()

    def index(self) -> int:
        return self.stack.index

    def canUndo(self) -> bool:
        return self.stack.can_undo()

    def canRedo(self) -> bool:
        return self.stack.can_redo()

    def undoText(self) -> str:
        return self.stack.undo_text()

    def redoText(self) -> str:
        return self.stack.redo_text()

    def isClean(self) -> bool:
        return self.stack.is_clean()

    def setClean(self) -> None:
        self.stack.set_clean()

    def clear(self) -> None:
        self.stack.clear()

    def _action(self, parent, prefix: str, can, text, changed_can, changed_text, do) -> QAction:
        action = QAction(prefix, parent)

        def label(what: str) -> None:
            action.setText(f"{prefix} {what}" if what else prefix)
        label(text())
        action.setEnabled(can())
        changed_can.connect(action.setEnabled)
        changed_text.connect(label)
        action.triggered.connect(do)
        return action

    def createUndoAction(self, parent, prefix: str) -> QAction:
        """«&Undo Draw a building», enabled when there is a step to undo, as QUndoStack's."""
        return self._action(parent, prefix, self.canUndo, self.undoText, self.canUndoChanged, self.undoTextChanged,
                            self.undo)

    def createRedoAction(self, parent, prefix: str) -> QAction:
        return self._action(parent, prefix, self.canRedo, self.redoText, self.canRedoChanged, self.redoTextChanged,
                            self.redo)
