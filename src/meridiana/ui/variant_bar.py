"""The variants in the corner of the phases' row (R73; Daniel, 24/10/2026: «il tasto + Variante fa schifo. Mi aspetto
che in quest'area sia possibile passare da una variante ad un'altra con facilità»): a segmented control, each variant
a pill on a track, the one in hand raised in the panels' colour; a click on another and the window works on it; «+»
makes a new one from the one in hand; the right button opens rename, delete and compare. With more than MAX_PILLS
variants the one in hand and the first others stay as pills and the rest are in «…».

The measures are the design system's (ui/design.py): pills CHIP high with round ends, the track 2 px around them."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QMenu, QToolButton

from ..i18n import _
from . import icons
from .design import Icon, Space

MAX_PILLS = 4


class VariantBar(QFrame):
    chosen = Signal(str)                    # the id of the variant clicked

    def __init__(self, new_action: QAction, menu_actions: list, parent=None):
        super().__init__(parent)
        self.setObjectName("variant-bar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setToolTip(_("The variants of the project: each keeps its own sub-fields, modules, inverter, losses and "
                          "economics. Click one to work on it, + to make a copy of the one in hand; the right button "
                          "renames, deletes and compares."))
        self.menu_actions = menu_actions
        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(Space.XXS, Space.XXS, Space.XXS, Space.XXS)
        self.row.setSpacing(Space.XXS)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.pills: list[QToolButton] = []
        self.more = QToolButton()
        self.more.setObjectName("variant-more")
        self.more.setText("…")
        self.more.setToolTip(_("The other variants"))
        self.more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.more.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.add = QToolButton()
        self.add.setObjectName("variant-add")
        self.add.setIcon(icons.icon("plus"))
        self.add.setIconSize(QSize(Icon.CONTROL - 2, Icon.CONTROL - 2))
        self.add.setToolTip(_("A new variant, a copy of the one in hand, to change without losing it (another "
                              "module, another tilt, a battery) and compare the two"))
        self.add.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.add.clicked.connect(new_action.trigger)
        self.variants: list[tuple[str, str]] = []
        self.current = ""

    def _split(self, variants: list, current: str) -> tuple[list, list]:
        """The pills shown (the one in hand always among them) and the rest, behind «…»."""
        shown, rest = list(variants), []
        if len(shown) > MAX_PILLS:
            keep = [v for v in shown if v[0] == current]
            others = [v for v in shown if v[0] != current]
            keep = others[:MAX_PILLS - 1] + keep
            order = {v[0]: i for i, v in enumerate(variants)}
            shown = sorted(keep, key=lambda v: order[v[0]])
            rest = [v for v in variants if v not in shown]
        return shown, rest

    def _tip(self, vid: str, name: str, current: str) -> str:
        return (_("Work on the variant {name}").format(name=name) if vid != current
                else _("The variant in hand: {name}").format(name=name))

    def set_variants(self, variants: list, current: str) -> None:
        """`variants`: (id, name) in their order; `current` the id of the one in hand. The same pills stay when only
        the one in hand changes (R101: they were made again at every change, and the row jumped)."""
        shown, rest = self._split(list(variants), current)
        if self.pills and [(b.property("vid"), b.text()) for b in self.pills] == shown \
                and getattr(self, "rest", None) == rest:
            self.variants, self.current = list(variants), current
            for b in self.pills:
                vid = b.property("vid")
                b.setChecked(vid == current)
                b.setToolTip(self._tip(vid, b.text(), current))
            return
        self.setUpdatesEnabled(False)
        try:
            self._build(list(variants), current, shown, rest)
        finally:
            self.setUpdatesEnabled(True)

    def _build(self, variants: list, current: str, shown: list, rest: list) -> None:
        self.variants, self.current, self.rest = variants, current, rest
        for b in self.pills:
            self.group.removeButton(b)
            self.row.removeWidget(b)
            b.deleteLater()
        self.pills = []
        self.row.removeWidget(self.more)
        self.row.removeWidget(self.add)
        for vid, name in shown:
            b = QToolButton()
            b.setObjectName("variant-pill")
            b.setText(name)
            b.setCheckable(True)
            b.setChecked(vid == current)
            b.setProperty("vid", vid)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setToolTip(self._tip(vid, name, current))
            b.clicked.connect(lambda _c=False, v=vid: self._clicked(v))
            self.group.addButton(b)
            self.row.addWidget(b)
            self.pills.append(b)
        menu = QMenu(self.more)
        for vid, name in rest:
            a = menu.addAction(name)
            a.triggered.connect(lambda _c=False, v=vid: self._clicked(v))
        self.more.setMenu(menu)
        self.more.setVisible(bool(rest))
        self.row.addWidget(self.more)
        self.row.addWidget(self.add)
        self.adjustSize()

    def _clicked(self, vid: str) -> None:
        if vid != self.current:                     # the one in hand stays checked (the group is exclusive)
            self.chosen.emit(vid)

    def count(self) -> int:
        return len(self.variants)

    def currentText(self) -> str:                   # noqa: N802 (as a QComboBox, for the window's tests)
        return next((n for v, n in self.variants if v == self.current), "")

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        for a in self.menu_actions:
            if a is None:
                menu.addSeparator()
            else:
                menu.addAction(a)
        menu.exec(event.globalPos())
