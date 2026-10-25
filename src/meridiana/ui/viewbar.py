"""The bar of a view's own commands (Daniel, 23/10/2026, R14 and R27: «ciò che riguarda le viste non può stare nelle
viste?»): inside the view, in its top left corner, as Revit's view control bar. Which views are shown (plan, 3D, side
by side) as one selector of three, «Fit», and on the plan the drawing aids (snaps F3, ortho F8) as switches that show
their state. The buttons carry the window's QActions: one command, one action, the same keys and tooltips as in the
menus. The bar is in the theme's colours, as the other buttons over the views.

Each button with its icon alone, its word and its key in the tooltip («Pianta», «3D», «Affiancate», «Inquadra»,
«Agganci», «Orto»; Daniel, 24/10/2026: «sostituire i testi con solo simboli»); the one on in the selection's
colour; a menu (the plan's background) keeps its arrow. The selector of the views is on one bar
only when the two views are side by side (`show_group`: it was there twice)."""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QToolButton, QWidget

from .. import theme_colors
from .design import Radius, Space
from .phasebar import ToolButton

MARGIN = Space.M                # from the corner of the view, as the other things over it (ui/plan_overlays)


class ViewBar(QFrame):
    def __init__(self, parent: QWidget, groups: list[list], keys: tuple = (), words: dict | None = None):
        """`groups`: lists of QActions, a thin line between one group and the next; `keys`: the actions shown by
        their key (the drawing aids); `words`: a shorter word for an action than its text («Inquadra»)."""
        super().__init__(parent)
        self.setObjectName("viewbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        row = QHBoxLayout(self)
        row.setContentsMargins(2, 2, 2, 2)
        row.setSpacing(1)
        self.buttons: dict = {}             # the action -> its button
        self.keys = tuple(keys)
        self.words = dict(words or {})
        self.last_place = None              # (area, avoid) of the last `place`, to place it again when it narrows
        self.groups: list[list] = []        # the widgets of each group, its line first (none for the first)
        for i, actions in enumerate(groups):
            widgets: list = []
            if i:
                line = QFrame()
                line.setObjectName("viewbar-line")
                line.setFixedSize(1, 16)
                row.addWidget(line)
                widgets.append(line)
            for action in actions:
                if action.menu() is not None:                   # a menu (the plan's background): its icon
                    b = QToolButton()
                    b.setDefaultAction(action)
                    b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
                    b.setIconSize(QSize(16, 16))
                    b.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
                else:
                    b = ToolButton(action, self.label(action))
                    b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
                    b.setIconSize(QSize(16, 16))
                    b.own_tip = self.tip(action)
                    b.setToolTip(b.own_tip)
                b.setAutoRaise(True)
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)        # the keyboard stays on the drawing
                row.addWidget(b)
                widgets.append(b)
                self.buttons[action] = b
            self.groups.append(widgets)
        self.adjustSize()

    def label(self, action) -> str:
        """The word of a button: a shorter one when given, else the action's text without its «&»."""
        if action in self.words:
            return self.words[action]
        from .phasebar import _plain
        return _plain(action.text())

    def tip(self, action) -> str:
        """A button's tooltip: its word, and its key when it has one."""
        key = action.shortcut().toString(action.shortcut().SequenceFormat.NativeText)
        return f"{self.label(action)} ({key})" if key else self.label(action)

    def set_words(self, on: bool) -> None:
        """The buttons with their icons and words, or with their icons alone (a narrow view)."""
        style = Qt.ToolButtonStyle.ToolButtonTextBesideIcon if on else Qt.ToolButtonStyle.ToolButtonIconOnly
        changed = False
        for b in self.buttons.values():
            if isinstance(b, ToolButton) and b.toolButtonStyle() != style:
                b.setToolButtonStyle(style)
                b.setIconSize(QSize(16, 16))
                changed = True
        if changed:
            self.adjustSize()

    def show_group(self, n: int, on: bool) -> None:
        """A group (and its line) shown or hidden: the selector of the views on one bar only."""
        if 0 <= n < len(self.groups):
            for w in self.groups[n]:
                w.setVisible(on)
            if n == 0 and len(self.groups) > 1 and self.groups[1] and self.groups[1][0].objectName() == "viewbar-line":
                self.groups[1][0].setVisible(on)        # no line before what is now the first group
            self.adjustSize()
            if self.last_place is not None:
                self.place(*self.last_place)

    def set_colours(self, t: dict) -> None:
        """The theme's tokens (theme_colors): the panel's colour, a little see-through; under the pointer the
        controls' veil, a switch that is on in the selection's grey (R104: no accent here)."""
        from .theme import veil
        panel = theme_colors.qt_hex(t["panel"])
        dark = theme_colors.luminance(t["panel"]) < 0.2
        hover = veil(t, dark, 0.35 if dark else 0.14)
        self.setStyleSheet(f"""
#viewbar {{ background: {panel}; border: 1px solid {t['line']}; border-radius: {Radius.CONTROL}px; }}
#viewbar-line {{ background: {t['line']}; margin: 0 3px; }}
#viewbar QToolButton {{ border: none; border-radius: {Radius.INNER}px; padding: {Space.XS}px {Space.S}px;
                       color: {t['text2']}; }}
#viewbar QToolButton[popupMode="2"] {{ padding-right: {Space.XL + 2}px; }}
#viewbar QToolButton:hover {{ background: {hover}; color: {t['text']}; }}
#viewbar QToolButton:checked {{ background: {t['select_bg']}; color: {t['select_fg']}; }}
""")
        self.adjustSize()

    def place(self, area, avoid=()) -> None:
        """In the top left corner of `area` (a QRect in the parent's pixels: the view's viewport); in a view too
        narrow for it and the widgets of the other corner (`avoid`: the cube, the north arrow), below them."""
        self.last_place = (area, avoid)
        x, y = area.left() + MARGIN, area.top() + MARGIN
        mine = QRect(x, y, self.width(), self.height())
        crossed = [r for r in avoid if mine.intersects(r)]
        if crossed:
            y = max(r.bottom() for r in crossed) + 1 + MARGIN
        self.move(x, y)
        self.raise_()
