"""«Building from a template…» (task 16a, step 8): the shape, its measures and its turn, with the building drawn
in 3D as it will be (R282, study 22, 3.8: ui/preview3d.py); the building is then placed with a click on the plan
(window._building_template). The outlines come from templates.py.

Each side of the preview has a pill with its number and its length: a click opens a field in it, and the length
written goes to the measure that makes that side (`side_measure`): an outer side to the building's width or depth,
an inner one so that the arms keep their thickness."""

from __future__ import annotations

import math

from PySide6.QtCore import QEvent, QObject, QPointF
from PySide6.QtGui import QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout, QWidget

from .. import quantity, templates
from ..i18n import _, number
from .preview3d import Pill, Preview3D, prism
from .properties import combo, make_form, spin

HEIGHT = 6.0        # the height window._template_placed gives the building (m): drawn, not asked here


def side_measure(kind: str, side: int, value: float, m: dict) -> tuple[str, float]:
    """The measure of the template `kind` to set, and its value, so that its side `side` (from 1, as numbered on
    the outline) is `value` long, the other measures `m` kept. ValueError, said in words, when no value of that
    measure makes the side so long."""
    if kind == "rectangle":
        return ("width" if side in (1, 3) else "depth"), value
    if kind == "L":
        a, b = m["arm_south"], m["arm_west"]
        return {1: ("width", value), 2: ("arm_south", value), 3: ("width", b + value), 4: ("depth", a + value),
                5: ("arm_west", value), 6: ("depth", value)}[side]
    if kind == "T":
        a, b = m["bar"], m["stem"]
        return {1: ("width", value), 2: ("bar", value), 3: ("width", b + 2 * value), 4: ("depth", a + value),
                5: ("stem", value), 6: ("depth", a + value), 7: ("width", b + 2 * value), 8: ("bar", value)}[side]
    if kind == "U":
        a, b = m["base"], m["arm"]
        return {1: ("width", value), 2: ("depth", value), 3: ("arm", value), 4: ("depth", a + value),
                5: ("width", 2 * b + value), 6: ("depth", a + value), 7: ("arm", value), 8: ("depth", value)}[side]
    if kind == "trapezoid":
        if side in (1, 3):
            return ("base" if side == 1 else "top"), value
        run = (m["offset"] + m["top"] - m["base"]) if side == 2 else m["offset"]    # the slanted side's run
        if value <= abs(run):
            raise ValueError(_("A slanted side must be longer than its run along the base, {run} m").format(
                run=number(abs(run))))
        return "depth", math.sqrt(value * value - run * run)
    raise ValueError(f"no template {kind!r}")


def sides_of(kind: str, key: str) -> set:
    """The sides of the template whose length the measure `key` sets (lit when its field is pointed)."""
    m = templates.defaults(kind)
    out = set()
    for side in range(1, len(templates.footprint(kind)) + 1):
        try:
            if side_measure(kind, side, 1.0, m)[0] == key:
                out.add(side)
        except ValueError:
            continue                        # a slanted side shorter than its run: it still sets the depth
    if kind == "trapezoid" and key == "depth":
        out |= {2, 4}
    return out


def parse_measure(text: str, unit: str) -> float:
    """What is typed in a pill, as the number fields read it: «12,5», «12 m + 30 cm» (quantity.parse)."""
    return quantity.parse(text, "angle" if unit == "°" else "length", unit)


class LightSides(QObject):
    """Lights the preview's sides while the pointer or the focus is on a field: `fields` {field: keys}."""

    def __init__(self, preview: Preview3D, fields: dict, parent=None):
        super().__init__(parent)
        self.preview, self.fields = preview, fields
        for field in fields:
            field.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        kind = event.type()
        if obj in self.fields:
            if kind in (QEvent.Type.Enter, QEvent.Type.FocusIn):
                self.preview.set_highlight(self.fields[obj])
            elif kind in (QEvent.Type.Leave, QEvent.Type.FocusOut):
                self.preview.set_highlight(())
        return False


class Outline(QWidget):
    """The outline of a template in plan, North up, with the number of each side: the 2D preview before the 3D one
    (R282); kept for the «Plan» tab of study 22, 3.8, not made yet."""

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
        self.ring: list | None = None           # the outline drawn, None when the measures make none
        self.preview = Preview3D(self, number=number, parse=parse_measure)
        self.preview.hint = _("Drag to turn · click a side to write its length")
        self.preview.setMinimumSize(300, 240)
        self.preview.edited.connect(self._side_written)
        box.addWidget(self.preview, 1)
        self._lights: LightSides | None = None
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
        self.turn_field.valueChanged.connect(lambda _v: self._update())
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
        if self._lights is not None:
            self._lights.deleteLater()
        kind = self.kind.currentData()
        self._lights = LightSides(self.preview, {f: sides_of(kind, key) for key, f in self.fields.items()}, self)
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
        self.ring = ring
        self._draw(ring)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ring is not None)

    def _draw(self, ring) -> None:
        """The building as it will be: the outline turned, HEIGHT high, with a pill on each side of its top."""
        if ring is None:
            self.preview.show_scene()
            return
        placed = templates.placed(ring, (0.0, 0.0), self.turn())
        n = len(placed)
        pills = []
        for i in range(n):
            (ax, ay), (bx, by) = placed[i], placed[(i + 1) % n]
            length = math.hypot(bx - ax, by - ay)
            out = ((by - ay) / length, (ax - bx) / length, 0.0) if length else None   # outward: the ring is CCW
            pills.append(Pill(i + 1, [(ax, ay, HEIGHT), (bx, by, HEIGHT)], length, f"{number(length)} m", i + 1,
                              out=out))
        self.preview.show_scene(prism(placed, 0.0, HEIGHT), (), pills)

    def _side_written(self, side, value: float) -> None:
        """A length written in a side's pill: to the measure that makes it, or refused with the reason."""
        try:
            key, measure = side_measure(self.kind.currentData(), int(side), value, self.measures())
        except ValueError as error:
            self.preview.refuse(str(error))
            return
        field = self.fields[key]
        if not field.minimum() <= measure <= field.maximum():
            self.preview.refuse(_("{what}: between {low} and {high}").format(
                what=templates.measure_names()[key], low=number(field.minimum()), high=number(field.maximum())))
            return
        field.setValue(measure)
