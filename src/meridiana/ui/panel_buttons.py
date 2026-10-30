"""The cards' buttons in the status bar (R72; Daniel, 24/10/2026: «nel momento in cui chiudo una qualsiasi scheda o la
copro deve esserci modo di riaprirla con un bottone»), as VS Code's buttons of its side bars and panel: one for each
card, its icon full when the card is on screen and faint when it is closed or covered. Project and Help open,
bring forward or close their card. Right and bottom operate on every card touching that edge, including a shared
corner; another click restores the exact group just hidden.

`PanelButtons([(dock, icon, command), ...])`: the command's QAction gives the key for the tooltip."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import QDockWidget, QHBoxLayout, QMainWindow, QToolButton, QWidget

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
        self.collapsed_edges: dict[str, list[QDockWidget]] = {}
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
            dock.visibilityChanged.connect(lambda _v: QTimer.singleShot(0, self, self._refresh))
            dock.dockLocationChanged.connect(lambda _a: QTimer.singleShot(0, self, self._refresh))
            row.addWidget(b)
            self.buttons[dock] = b
            self._show(dock)

    def _refresh(self) -> None:
        for dock in self.buttons:
            self._show(dock)

    @staticmethod
    def covered(dock: QDockWidget) -> bool:
        """Open but not seen: a tab behind another card."""
        return not dock.isHidden() and dock.visibleRegion().isEmpty()

    def _clicked(self, dock: QDockWidget) -> None:
        from .dock_motion import reflow
        window = dock.parentWidget()
        if isinstance(window, QMainWindow):
            edge = {"panel-bottom": "bottom", "panel-right": "right", "panel-left": "left"}.get(
                self.buttons[dock].property("icon_name"), "right")
            reflow(window, lambda: self._clicked_now(dock), edge=edge)
        else:
            self._clicked_now(dock)

    def _clicked_now(self, dock: QDockWidget) -> None:
        edge = self.buttons[dock].property("icon_name")
        if edge in ("panel-right", "panel-bottom"):
            collapsed = self.collapsed_edges.get(edge, [])
            if collapsed and all(member.isHidden() for member in collapsed):
                for member in self.collapsed_edges.pop(edge):
                    member.show()
                for member in self.buttons:
                    self._show(member)
                return
            members = self._edge_members(dock, edge)
            if members:
                self.collapsed_edges[edge] = members
                # Decide the entire group before hiding: Qt reallocates the freed space at each hide.
                for member in members:
                    member.hide()
            else:
                for member in self.collapsed_edges.pop(edge, [dock]):
                    member.show()
            for member in self.buttons:
                self._show(member)
            return
        if dock.isHidden():
            dock.show()
            dock.raise_()
        elif self.covered(dock):
            dock.raise_()
        else:
            dock.hide()
        self._show(dock)

    @staticmethod
    def _edge_members(dock: QDockWidget, edge: str) -> list[QDockWidget]:
        """Include corner cards in both touching edges, regardless of their Qt dock area."""
        window = dock.parentWidget()
        if not isinstance(window, QMainWindow):
            return [] if dock.isHidden() else [dock]
        from .cards import arena
        room = arena(window)
        area = {"panel-right": Qt.DockWidgetArea.RightDockWidgetArea,
                "panel-bottom": Qt.DockWidgetArea.BottomDockWidgetArea}[edge]
        members = []
        for member in window.findChildren(QDockWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
            if member.isHidden() or member.isFloating():
                continue
            rect = member.geometry()
            touching = (abs(rect.right() - room.right()) <= 2 if edge == "panel-right" else
                        rect.bottom() >= room.bottom() - 2)
            if window.dockWidgetArea(member) == area or touching:
                members.append(member)
        return members

    def _show(self, dock: QDockWidget) -> None:
        try:
            b = self.buttons[dock]
            edge = b.property("icon_name")
            group = edge in ("panel-right", "panel-bottom")
            seen = bool(self._edge_members(dock, edge)) if group else not dock.isHidden() and not self.covered(dock)
            if group and (collapsed := self.collapsed_edges.get(edge)):
                seen = any(not member.isHidden() for member in collapsed)
        except (KeyError, RuntimeError):
            return
        name = b.property("icon_name")
        b.setIcon(icons.icon(name) if seen else icons.icon(name, self.colours["off"]))
        action = b.property("action")
        keys = action.shortcut().toString(action.shortcut().SequenceFormat.NativeText) if action is not None else ""
        if group:
            keys = ""  # the menu and its key address the individual card, not this edge group
        title = dock.windowTitle().split(" (")[0]
        if group:
            title = {"panel-right": _("Right panels"),
                     "panel-bottom": _("Bottom panels")}[edge]
        what = (_("Close {card}") if seen else _("Bring back {card}") if self.covered(dock)
                else _("Open {card}")).format(card=title)
        b.setToolTip(f"{what} ({keys})" if keys else what)

    def set_colours(self, t: dict) -> None:
        self.colours = {"on": t["text2"], "off": t["muted"]}
        for dock in list(self.buttons):
            self._show(dock)
