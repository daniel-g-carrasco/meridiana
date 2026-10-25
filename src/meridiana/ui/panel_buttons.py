"""The cards' buttons in the status bar (R72; Daniel, 24/10/2026: «nel momento in cui chiudo una qualsiasi scheda o la
copro deve esserci modo di riaprirla con un bottone»), as VS Code's buttons of its side bars and panel: one for each
card, its icon full when the card is on screen and faint when it is closed or covered. A click opens a closed card,
brings a covered one to the front (a card stacked as a tab behind another), and closes one on screen.

`PanelButtons([(dock, icon, command), ...])`: the command's QAction gives the key for the tooltip."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import QDockWidget, QHBoxLayout, QToolButton, QWidget

from ..i18n import _
from . import icons
from .design import Icon, Space


class PanelButtons(QWidget):
    def __init__(self, cards: list, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, Space.S, 0)
        row.setSpacing(Space.XXS)
        self.buttons: dict = {}
        from .cards import default_tokens
        self.set_colours(default_tokens())
        for dock, icon, action in cards:
            b = QToolButton()
            b.setObjectName("panel-toggle")
            b.setAutoRaise(True)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setIconSize(QSize(Icon.CONTROL, Icon.CONTROL))
            b.setProperty("icon_name", icon)
            b.setProperty("action", action)
            b.clicked.connect(lambda _c=False, d=dock: self._clicked(d))
            dock.visibilityChanged.connect(lambda _v, d=dock: QTimer.singleShot(0, self, lambda: self._show(d)))
            row.addWidget(b)
            self.buttons[dock] = b
            self._show(dock)

    @staticmethod
    def covered(dock: QDockWidget) -> bool:
        """Open but not seen: a tab behind another card."""
        return not dock.isHidden() and dock.visibleRegion().isEmpty()

    def _clicked(self, dock: QDockWidget) -> None:
        if dock.isHidden():
            dock.show()
            dock.raise_()
        elif self.covered(dock):
            dock.raise_()
        else:
            dock.hide()
        self._show(dock)

    def _show(self, dock: QDockWidget) -> None:
        try:
            b = self.buttons[dock]
            seen = not dock.isHidden() and not self.covered(dock)
        except (KeyError, RuntimeError):
            return
        name = b.property("icon_name")
        b.setIcon(icons.icon(name) if seen else icons.icon(name, self.colours["off"]))
        action = b.property("action")
        keys = action.shortcut().toString(action.shortcut().SequenceFormat.NativeText) if action is not None else ""
        title = dock.windowTitle().split(" (")[0]
        what = (_("Close {card}") if seen else _("Bring back {card}") if self.covered(dock)
                else _("Open {card}")).format(card=title)
        b.setToolTip(f"{what} ({keys})" if keys else what)

    def set_colours(self, t: dict) -> None:
        self.colours = {"on": t["text2"], "off": t["muted"]}
        for dock in list(self.buttons):
            self._show(dock)
