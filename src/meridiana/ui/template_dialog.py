"""«Building from a template…» (task 16a, step 8): the shape, its measures and its turn, with the outline drawn
as it will be; the building is then placed with a click on the plan (window._building_template). The outlines
come from templates.py."""

from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout, QWidget

from .. import templates
from ..i18n import _
from .properties import combo, make_form, spin


class Outline(QWidget):
    """The outline of the template, fitted in the widget, North up, with the number of each side."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ring: list | None = None
        self.setMinimumSize(220, 160)

    def show_ring(self, ring) -> None:
        self.ring = ring
        self.update()

    def paintEvent(self, _event) -> None:
        if not self.ring:
            return
        xs, ys = [p[0] for p in self.ring], [p[1] for p in self.ring]
        w, h = max(xs) - min(xs) or 1.0, max(ys) - min(ys) or 1.0
        margin = 18.0
        k = min((self.width() - 2 * margin) / w, (self.height() - 2 * margin) / h)

        def at(x, y):
            return QPointF(margin + (x - min(xs)) * k, self.height() - margin - (y - min(ys)) * k)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self.palette().text().color(), 1.5)
        painter.setPen(pen)
        painter.drawPolygon(QPolygonF([at(x, y) for x, y in self.ring]))
        n = len(self.ring)
        for i in range(n):
            (ax, ay), (bx, by) = self.ring[i], self.ring[(i + 1) % n]
            mid = at((ax + bx) / 2, (ay + by) / 2)
            painter.drawText(mid + QPointF(3, -3), str(i + 1))
        painter.end()


class TemplateDialog(QDialog):
    """The template chosen, with its measures; outline() is the footprint from (0, 0), turn() its turn."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Building from a template"))
        box = QVBoxLayout(self)
        form = make_form()
        self.kind: QComboBox = combo(templates.kind_names().items(), "L")
        form.addRow(_("Shape"), self.kind)
        box.addLayout(form)
        self.measures_form: QFormLayout = make_form()
        box.addLayout(self.measures_form)
        self.fields: dict = {}
        turn_form = make_form()
        self.turn_field = spin(-180, 180, 0.0, " °", 1, 5)
        turn_form.addRow(_("Turn (counter-clockwise)"), self.turn_field)
        box.addLayout(turn_form)
        self.preview = Outline(self)
        box.addWidget(self.preview, 1)
        self.problem = QLabel()
        self.problem.setWordWrap(True)
        box.addWidget(self.problem)
        note = QLabel(_("The sides can be changed afterwards one by one, in the Sides group of the building."))
        note.setWordWrap(True)
        box.addWidget(note)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(_("Place it on the plan"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        box.addWidget(self.buttons)
        self.kind.currentIndexChanged.connect(lambda _i: self._fill())
        self._fill()

    def _fill(self) -> None:
        while self.measures_form.rowCount():
            self.measures_form.removeRow(0)
        self.fields = {}
        names = templates.measure_names()
        for key, value in templates.KINDS[self.kind.currentData()]:
            low = -1000.0 if key == "offset" else 0.1
            field = spin(low, 1000, value, " m", 2, 0.5)
            field.valueChanged.connect(lambda _v: self._update())
            self.measures_form.addRow(names[key], field)
            self.fields[key] = field
        self._update()

    def measures(self) -> dict:
        return {key: float(f.value()) for key, f in self.fields.items()}

    def turn(self) -> float:
        return float(self.turn_field.value())

    def outline(self) -> list | None:
        """The footprint from (0, 0), or None when the measures make none (the reason is shown)."""
        try:
            return templates.footprint(self.kind.currentData(), self.measures())
        except ValueError:
            return None

    def _update(self) -> None:
        try:
            ring = templates.footprint(self.kind.currentData(), self.measures())
            self.problem.setText("")
        except ValueError as error:
            ring = None
            self.problem.setText(str(error))
        self.problem.setVisible(ring is None)
        self.preview.show_ring(ring)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ring is not None)

