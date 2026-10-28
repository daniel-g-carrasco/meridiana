"""The right panel follows the phase (study 12, N2; study 12a, 4.2 and 4.7; design document 3.6): the properties
of what is selected in the Model and in the Plant, the figures of the variant in hand in Production, Consumption
and Balance, where the model's properties are of no use, the deliverables with their state in the Report. One
panel, not panels that come and go by themselves, which disorients; its title changes, the panel does not; Ctrl+1
shows or hides it. Which inspector each phase has is said by phases.py."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QStackedWidget, QVBoxLayout, QWidget)

from .. import compare, phases
from ..i18n import _
from .design import Text, set_text, text_font


class ResultsInspector(QScrollArea):
    """The variant in hand, to switch, and its figures, as the comparison of the variants writes them."""

    variantChosen = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page = QWidget()
        box = QVBoxLayout(page)
        self.heading = set_text(QLabel(), Text.STRONG)
        box.addWidget(self.heading)
        form = QFormLayout()
        self.variant = QComboBox()
        self.variant.activated.connect(lambda i: self.variantChosen.emit(self.variant.itemData(i)))
        form.addRow(_("Variant"), self.variant)
        box.addLayout(form)
        self.figures = QFormLayout()
        box.addLayout(self.figures)
        self.note = QLabel(_("The properties of the objects are in the Model phase; this panel shows or hides with "
                             "Ctrl+1."))
        self.note.setWordWrap(True)
        set_text(self.note, Text.SECONDARY)
        box.addWidget(self.note)
        box.addStretch(1)
        self.setWidget(page)

    def show_results(self, title: str, variants: list, current: str, energy: dict) -> None:
        self.heading.setText(title)
        self.variant.blockSignals(True)
        self.variant.clear()
        for vid, name in variants:
            self.variant.addItem(name, vid)
        self.variant.setCurrentIndex(max(0, self.variant.findData(current)))
        self.variant.blockSignals(False)
        while self.figures.rowCount():
            self.figures.removeRow(0)
        s = compare.summary(energy or {})
        if "error" in s:
            why = QLabel(s["error"])
            why.setWordWrap(True)
            self.figures.addRow(why)
            return
        for key, label, decimals, _better in compare.rows():
            value = QLabel(compare.cell(s, key, decimals))
            value.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.figures.addRow(label, value)


class DeliverablesInspector(QScrollArea):
    """The deliverables of the Report phase (design 2.7 and 7.3), each with its state and, when the program makes
    it, the button that does: done (with the file and the time), to make again because the project changed, to
    make, not available (why), not yet (which task brings it)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page = QWidget()
        self.box = QVBoxLayout(page)
        self.heading = set_text(QLabel(_("Deliverables")), Text.STRONG)
        self.box.addWidget(self.heading)
        self.rows: list[QWidget] = []
        self.states: dict = {}                     # deliverable id -> its state, for the tests
        self.box.addStretch(1)
        self.setWidget(page)
        self.top: QWidget | None = None

    def set_top(self, widget: QWidget) -> None:
        """What is chosen for the report (ui/report_page.ReportSide), above the deliverables."""
        self.top = widget
        self.box.insertWidget(0, widget)

    def show_deliverables(self, items: list, actions: dict) -> None:
        for row in self.rows:
            self.box.removeWidget(row)
            row.deleteLater()
        self.rows = []
        self.states = {}
        names = phases.state_names()
        for n, d in enumerate(items):
            tile = QFrame()
            tile.setObjectName("tile")
            tile.setFrameShape(QFrame.Shape.NoFrame)
            inside = QVBoxLayout(tile)
            inside.setContentsMargins(8, 6, 8, 6)
            inside.setSpacing(2)
            head = QHBoxLayout()
            title = set_text(QLabel(d.title), Text.STRONG)
            title.setWordWrap(True)             # a long title on two lines, its state still inside the panel
            from .style import grow_label
            grow_label(title)
            head.addWidget(title, 1)
            state = QLabel(names.get(d.state, d.state))
            state.setObjectName(f"state-{d.state}")
            state.setFont(text_font(Text.CONTROL))          # a pill: a control's word (Button.CHIP)
            head.addWidget(state)
            inside.addLayout(head)
            note = QLabel(d.note)
            note.setWordWrap(True)
            grow_label(note)
            inside.addWidget(note)
            action = actions.get(d.command) if d.command else None
            if action is not None:
                from .. import shortcuts
                b = QPushButton(shortcuts.plain(action.text()))
                b.setEnabled(d.state != "unavailable")
                b.clicked.connect(action.trigger)
                inside.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)
            self.box.insertWidget(1 + n + (self.top is not None), tile)
            self.rows.append(tile)
            self.states[d.id] = d.state


class Inspector(QStackedWidget):
    def __init__(self, properties, parent=None):
        super().__init__(parent)
        self.properties = properties
        self.results = ResultsInspector()
        self.deliverables = DeliverablesInspector()
        self.plant = None                   # the inverters of the Plant phase (ui/plant_page.py, add_plant)
        self.sides: dict = {}               # phase id -> what is typed in that phase (the energy pages' `side`)
        self.addWidget(properties)
        self.addWidget(self.results)
        self.addWidget(self.deliverables)

    def add_plant(self, widget) -> None:
        """The Plant phase's inspector (design C10): made by the window once its actions are there."""
        self.plant = widget
        self.addWidget(widget)

    def add_side(self, pid: str, widget) -> None:
        """What is typed in the phase `pid` (its page's form), shown here instead of the figures (the drafts of
        24/10/2026: the results in the middle, what is typed on the right, as the model's properties)."""
        self.sides[pid] = widget
        self.addWidget(widget)

    def set_kind(self, kind: str, pid: str = "") -> None:
        """What the phase wants (phases.Phase.inspector): "properties", "plant", "results" or "deliverables"; a
        phase of results with a form of its own shows the form."""
        if kind == "results" and pid in self.sides:
            self.setCurrentWidget(self.sides[pid])
            return
        self.setCurrentWidget({"results": self.results, "deliverables": self.deliverables,
                               "plant": self.plant}.get(kind) or self.properties)
