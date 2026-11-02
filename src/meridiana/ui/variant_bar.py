"""The variants in the corner of the phases' row (R73; Daniel, 24/10/2026: «il tasto + Variante fa schifo. Mi aspetto
che in quest'area sia possibile passare da una variante ad un'altra con facilità»): the segments of every choice between
views (ui/segments.py, R322), each variant a segment on the track, the one in hand raised in the panels' colour and
sliding to the next; a click on another and the window works on it; «+» makes a new one from the one in hand; the right
button opens rename, delete and compare. With more than MAX_SHOWN variants the one in hand and the first others stay as
segments and the rest are in «…»."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QToolButton

from ..i18n import _
from . import icons
from .design import Icon
from .segments import Segments

MAX_SHOWN = 4


class VariantBar(Segments):
    """`chosen`: the id of the variant clicked, another than the one in hand."""

    def __init__(self, new_action: QAction, menu_actions: list, parent=None):
        super().__init__(True, parent)
        self.setObjectName("variant-bar")
        self.setToolTip(_("The variants of the project: each keeps its own sub-fields, modules, inverter, losses and "
                          "economics. Click one to work on it, + to make a copy of the one in hand; the right button "
                          "renames, deletes and compares."))
        self.menu_actions = menu_actions
        self.more = QToolButton()
        self.more.setObjectName("variant-more")
        self.more.setText("…")
        self.more.setToolTip(_("The other variants"))
        self.more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.more.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.more.setVisible(False)
        self.plus = QToolButton()
        self.plus.setObjectName("variant-add")
        self.plus.setIcon(icons.icon("plus"))
        self.plus.setIconSize(QSize(Icon.CONTROL - 2, Icon.CONTROL - 2))
        self.plus.setToolTip(_("A new variant, a copy of the one in hand, to change without losing it (another "
                               "module, another tilt, a battery) and compare the two"))
        self.plus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.plus.clicked.connect(new_action.trigger)
        self.row.addWidget(self.more)
        self.row.addWidget(self.plus)
        self.variants: list[tuple[str, str]] = []
        self.current_id = ""
        self.rest: list = []

    def _split(self, variants: list, current: str) -> tuple[list, list]:
        """The segments shown (the one in hand always among them) and the rest, behind «…»."""
        shown, rest = list(variants), []
        if len(shown) > MAX_SHOWN:
            keep = [v for v in shown if v[0] == current]
            others = [v for v in shown if v[0] != current]
            keep = others[:MAX_SHOWN - 1] + keep
            order = {v[0]: i for i, v in enumerate(variants)}
            shown = sorted(keep, key=lambda v: order[v[0]])
            rest = [v for v in variants if v not in shown]
        return shown, rest

    def _tip(self, vid: str, name: str, current: str) -> str:
        return (_("Work on the variant {name}").format(name=name) if vid != current
                else _("The variant in hand: {name}").format(name=name))

    def set_variants(self, variants: list, current: str) -> None:
        """`variants`: (id, name) in their order; `current` the id of the one in hand. The same segments stay when
        only the one in hand changes (R101: they were made again at every change, and the row jumped)."""
        shown, rest = self._split(list(variants), current)
        if self.items and [(b.property("data"), b.text()) for b in self.items] == shown and self.rest == rest:
            self.variants, self.current_id = list(variants), current
            self.set_current(current)
            for b in self.items:
                b.setToolTip(self._tip(b.property("data"), b.text(), current))
            return
        self.setUpdatesEnabled(False)
        try:
            self._build(list(variants), current, shown, rest)
        finally:
            self.setUpdatesEnabled(True)

    def _build(self, variants: list, current: str, shown: list, rest: list) -> None:
        self.variants, self.current_id, self.rest = variants, current, rest
        self.clear()
        for vid, name in shown:
            self.add(name, vid, self._tip(vid, name, current))
        self.set_current(current)
        menu = QMenu(self.more)
        for vid, name in rest:
            a = menu.addAction(name)
            a.triggered.connect(lambda _c=False, v=vid: self.chosen.emit(v))
        self.more.setMenu(menu)
        self.more.setVisible(bool(rest))
        self.adjustSize()

    def count(self) -> int:
        return len(self.variants)

    def currentText(self) -> str:                   # noqa: N802 (as a QComboBox, for the window's tests)
        return next((n for v, n in self.variants if v == self.current_id), "")

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        for a in self.menu_actions:
            if a is None:
                menu.addSeparator()
            else:
                menu.addAction(a)
        menu.exec(event.globalPos())
