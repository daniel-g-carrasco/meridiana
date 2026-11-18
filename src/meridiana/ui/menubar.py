"""The menu bar hidden, and Alt that shows it (R40, R53; Daniel's choice of 24/10/2026: «alt non fa ancora nulla»,
then «ci sta mi piace» to hidden menus that Alt shows plus the File page, ui/file_page.py). As Firefox and the
Explorer of Windows: Alt pressed and let go alone opens the first menu, Alt with a menu's letter opens that menu;
the arrows go from one to the next, Esc or a click elsewhere closes them and the bar goes again. While it shows it
takes its place above the phases and the window under it moves down to make room, and back up when it goes (R164,
Daniel 25/10/2026: it stood over the row of the phases, «invece deve "aggiungersi" e spostare con un'animazione il
resto sotto»). With «Menu bar» on (View, and the preferences) it stays in its place above the phases.

`AltMenus(window, bar)`: the window keeps its QMenuBar; `set_always(on)` with the setting."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMenu, QMenuBar, QWidget


def mnemonic(text: str) -> str:
    """The letter after the & of a menu's text, in lower case; "" without one («&&» is a plain &)."""
    plain = text.replace("&&", "")
    i = plain.find("&")
    return plain[i + 1].lower() if 0 <= i < len(plain) - 1 else ""


class AltMenus(QObject):
    def __init__(self, window: QWidget, bar: QMenuBar, home):
        """`home`: the layout the bar stands in when it is always shown (the top of the window)."""
        super().__init__(window)
        self.window = window
        self.bar = bar
        self.home = home
        self.always = True
        self.alone = False                  # Alt went down and nothing else since
        self.shown = False                  # shown by Alt, over the phases' row
        for menu in bar.findChildren(QMenu):
            if menu.parentWidget() is bar:
                menu.aboutToHide.connect(self._maybe_hide)
        from .app_events import events     # the application's one filter (R120)
        events().on((QEvent.Type.KeyPress, QEvent.Type.KeyRelease, QEvent.Type.MouseButtonPress), self,
                    self.eventFilter)

    def set_always(self, on: bool) -> None:
        """The bar always in its place (True), or hidden until Alt (False)."""
        self.always = bool(on)
        self.shown = False
        if self.always:
            if self.home.indexOf(self.bar) < 0:
                self.home.insertWidget(0, self.bar)
            self.bar.show()
        else:
            self.home.removeWidget(self.bar)
            self.bar.hide()

    def reveal(self, action=None) -> None:
        """The bar in its place above the phases, the window moving down to make room, and a menu open: `action`'s,
        else the first."""
        if self.always:
            return
        from . import motion

        def add() -> None:
            self.home.insertWidget(0, self.bar)
            self.bar.show()
            QApplication.sendPostedEvents(None, QEvent.Type.LayoutRequest)    # its place now: the menu opens under it
        motion.push(self.window, add, lambda: self.bar.height(), self._kept)
        self.shown = True
        first = next((a for a in self.bar.actions() if a.isVisible() and a.menu() is not None), None)
        target = action or first
        if target is not None:
            self.bar.setActiveAction(target)

    def conceal(self) -> None:
        """The bar gone, the window moving back up."""
        if self.always or not self.shown:
            return
        self.shown = False
        from . import motion
        height = self.bar.height()

        def remove() -> None:
            self.home.removeWidget(self.bar)
            self.bar.hide()
            QApplication.sendPostedEvents(None, QEvent.Type.LayoutRequest)
        motion.push(self.window, remove, lambda: -height, self._kept)

    def _kept(self) -> int:
        """The strip at the bottom of the window that stays while the rest moves: the status bar."""
        status = getattr(self.window, "statusBar", None)
        bar = status() if callable(status) else None
        return bar.height() if bar is not None and bar.isVisible() else 0

    def _maybe_hide(self) -> None:
        # after the menu has closed: another of the bar may have opened in its place (the arrows)
        QTimer.singleShot(0, self, lambda: None if self.bar.activeAction() is not None else self.conceal())

    def eventFilter(self, obj, event) -> bool:
        kind = event.type()
        if self.always or kind not in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease, QEvent.Type.MouseButtonPress):
            return False
        if kind == QEvent.Type.MouseButtonPress:
            self.alone = False
            return False
        # a key once, where it first lands: the widget with the keyboard (or the window when none has it); Qt
        # hands the same key on to the parents, and a second look would show the bar and hide it again
        try:
            if not isinstance(obj, QWidget) or obj.window() is not self.window:
                return False
            focus = QApplication.focusWidget()
            if obj is not (focus if focus is not None and focus.window() is self.window else self.window):
                return False
        except RuntimeError:                                # the window going
            return False
        key = event.key()
        if kind == QEvent.Type.KeyPress:
            if event.isAutoRepeat():
                return False
            if key == Qt.Key.Key_Alt:
                self.alone = event.modifiers() in (Qt.KeyboardModifier.AltModifier, Qt.KeyboardModifier.NoModifier)
                return False
            self.alone = False
            mods = event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
            if mods == Qt.KeyboardModifier.AltModifier and not self.shown and event.text():
                letter = event.text().lower()
                for a in self.bar.actions():
                    if a.menu() is not None and a.isVisible() and mnemonic(a.text()) == letter:
                        self.reveal(a)
                        return True
            return False
        if key == Qt.Key.Key_Alt and not event.isAutoRepeat():   # Alt let go
            if self.alone:
                self.alone = False
                if self.shown:
                    self.bar.setActiveAction(None)
                    self.conceal()
                else:
                    self.reveal()
                return True
        return False
