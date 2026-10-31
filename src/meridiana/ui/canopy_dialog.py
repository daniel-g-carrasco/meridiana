"""The parking canopy as a structure (R281, study 22, 3.7) with its 3D preview (R282, 3.8); and «On a canopy», the
modules laid on one (study 22, decision 9).

«Parking canopy…» draws only the structure: the spaces it covers, then the columns, the beams and the roof plane,
no module. The preview shows them as `canopies.structure` makes them; its pills: sides 1 and 3 the length of the
row (the width per space follows, the spaces kept), sides 2 and 4 the depth (per row, the rows kept), the height
under the low edge and the slope. «On a canopy» asks four things: the canopy, the modules' orientation, the gap
between them and how far they go beyond the structure, with the free edge."""
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout,
                               QWidget)

from .. import canopies, model
from ..i18n import _, number
from .preview3d import Face, Guide, Pill, Preview3D, prism
from .properties import combo, make_form, spin
from .style import Group
from .template_dialog import LightSides, parse_measure


class CanopyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Parking canopy"))
        self.setMinimumWidth(760)
        outer = QVBoxLayout(self)
        body = QHBoxLayout()
        outer.addLayout(body, 1)
        holder = QWidget()
        holder.setMinimumWidth(340)          # the labels beside their fields, never wrapped over them
        side = QVBoxLayout(holder)
        side.setContentsMargins(0, 0, 0, 0)
        body.addWidget(holder)
        spaces = Group(_("Parking spaces"), collapsible=False)
        form = make_form(spaces)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        self.stalls = QSpinBox()
        self.stalls.setRange(1, 100)
        self.stalls.setValue(4)
        self.stalls.setToolTip(_("How many cars park side by side in a row"))
        self.rows = combo([(1, _("One row, one slope")), (2, _("Two rows, back to back"))], 1)
        self.rows.setToolTip(_("Two rows face each other under two slopes that meet at a ridge"))
        form.addRow(_("Spaces per row"), self.stalls)
        form.addRow(_("Rows"), self.rows)
        self.fields = {}

        def field(form, key, label, low, high, value, unit, tip, decimals=2, step=0.5):
            self.fields[key] = spin(low, high, value, unit, decimals, step)
            self.fields[key].setToolTip(tip)
            form.addRow(label, self.fields[key])
        field(form, 'bay_width', _("Width of a space"), 0.5, 20, 2.5, ' m', _("Across a car, side to side"))
        field(form, 'depth', _("Depth of a space"), 1, 50, 5, ' m', _("Along a car, front to back"))
        side.addWidget(spaces)
        build = Group(_("Structure"), collapsible=False)
        form = make_form(build)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        field(form, 'clearance', _("Clear height"), 0.1, 100, 2.7, ' m',
              _("Under the low edge of the roof: what a vehicle passes under"))
        field(form, 'tilt', _("Slope"), 0, 60, 8, ' °', _("Of the roof plane, the same for the modules on it"), 1, 1)
        self.pillars = combo([("cantilever", _("Cantilever, one line")), ("two_rows", _("Two lines"))], "cantilever")
        self.pillars.setToolTip(_("One line of columns under the high edge, the roof projecting from it; or a line "
                                  "at each long edge"))
        form.addRow(_("Columns"), self.pillars)
        self.columns = QSpinBox()
        self.columns.setRange(0, 200)
        self.columns.setToolTip(_("Columns on each line; the first value is the one proposed, one every two spaces"))
        form.addRow(_("Columns per line"), self.columns)
        field(form, 'turn', _("Turn"), -180, 180, 0, ' °',
              _("The rows run East at 0°; the canopy can also be turned on the plan afterwards"), 1, 15)
        side.addWidget(build)
        side.addStretch(1)
        self.ring: list | None = None           # the footprint at the origin, as the preview draws it
        self.preview = Preview3D(self, number=number, parse=parse_measure)
        self.preview.hint = _("Drag to turn · click a side to write its length")
        self.preview.setMinimumSize(320, 280)
        self.preview.turn(225, 18)          # low enough to see the columns under the roof
        self.preview.edited.connect(self._pill_written)
        body.addWidget(self.preview, 1)
        self._lights = LightSides(self.preview, {self.fields['bay_width']: {1, 3}, self.fields['depth']: {2, 4},
                                                 self.fields['clearance']: {'clearance'},
                                                 self.fields['tilt']: {'tilt'}, self.stalls: {1, 3}}, self)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        outer.addWidget(self.summary)
        note = QLabel(_("Draws the structure only: columns, beams and the roof. The modules are laid on it afterwards, "
                        "in Plant › On a canopy. Indicative sizes, not a structural design."))
        note.setWordWrap(True)
        outer.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(_("Place it on the plan"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        for signal in (self.stalls.valueChanged, self.rows.currentIndexChanged, self.pillars.currentIndexChanged,
                       self.columns.valueChanged):
            signal.connect(self._update)
        for f in self.fields.values():
            f.valueChanged.connect(self._update)
        self._update()

    def spec(self):
        return canopies.Spec(stalls=self.stalls.value(), rows=self.rows.currentData(),
                             pillars=self.pillars.currentData(), columns=self.columns.value(),
                             **{key: field.value() for key, field in self.fields.items()})

    def _update(self, *_args):
        self.columns.setSpecialValueText(_("{n}, proposed").format(n=canopies.proposed_columns(self.stalls.value())))
        spec = self.spec()
        b = canopies.building(spec, (0, 0))
        self.ring = [tuple(q) for q in b.footprint]
        self._draw(spec, b)
        columns = len([s for s in canopies.structure(b) if s["kind"] == "column"])
        self.summary.setText(_("{n} spaces · {width} × {depth} m · {columns} columns").format(
            n=spec.stalls * spec.rows, width=number(spec.stalls * spec.bay_width),
            depth=number(spec.rows * spec.depth), columns=columns))

    def _draw(self, spec, b: model.Building) -> None:
        pitches = b.pitches()
        faces = [Face(p.corners_3d(), "plane") for p in pitches]
        for s in canopies.structure(b):
            faces += [Face(f.points, "structure") for f in prism(s["ring"], s["z0"], s["z1"])]
        f0, f1, f2, f3 = ((x, y, canopies.roof_at(pitches, x, y)) for x, y in self.ring)
        guides = [Guide([(x, y, 0.0) for x, y in self.ring + self.ring[:1]], "ground")]
        east, west = [f1, f2], [f3, f0]
        high_mid = tuple((f3[i] + f2[i]) / 2 for i in range(3))
        if spec.rows == 2 and spec.tilt > 0:
            ridge = [(x, y, canopies.roof_at(pitches, x, y)) for x, y in
                     (((f1[0] + f2[0]) / 2, (f1[1] + f2[1]) / 2), ((f0[0] + f3[0]) / 2, (f0[1] + f3[1]) / 2))]
            guides.append(Guide(ridge, "ridge"))
            east, west = [f1, ridge[0], f2], [f3, ridge[1], f0]
            high_mid = tuple((ridge[0][i] + ridge[1][i]) / 2 for i in range(3))
        length, depth = spec.stalls * spec.bay_width, spec.rows * spec.depth
        low_mid = tuple((f0[i] + f1[i]) / 2 for i in range(3))
        text_m = f"{number(length)} m"
        pills = [Pill(1, [f0, f1], length, text_m, 1), Pill(2, east, depth, f"{number(depth)} m", 2),
                 Pill(3, [f2, f3], length, text_m, 3), Pill(4, west, depth, f"{number(depth)} m", 4),
                 Pill('clearance', [(f0[0], f0[1], 0.0), f0], spec.clearance, f"{number(spec.clearance)} m"),
                 Pill('tilt', [low_mid, high_mid], spec.tilt, f"{number(spec.tilt, 1)}°", unit="°")]
        self.preview.show_scene(faces, guides, pills)

    def _pill_written(self, key, value: float) -> None:
        """A measure written in a pill: to its field (a side's length divided among the spaces or the rows)."""
        rows, stalls = self.rows.currentData(), self.stalls.value()
        field_key, share = {1: ('bay_width', stalls), 3: ('bay_width', stalls), 2: ('depth', rows),
                            4: ('depth', rows), 'clearance': ('clearance', 1), 'tilt': ('tilt', 1)}[key]
        field = self.fields[field_key]
        if not field.minimum() <= value / share <= field.maximum():
            self.preview.refuse(_("Between {low} and {high}").format(
                low=number(field.minimum() * share), high=number(field.maximum() * share)))
            return
        field.setValue(value / share)


class CanopyLayoutDialog(QDialog):
    """«On a canopy» (R281, study 22, decision 9): the canopy and four values; the general layout does the rest,
    flush with the canopy's plane, a sub-field on each slope."""

    def __init__(self, project: model.Project, chosen: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Modules on a canopy"))
        self.setMinimumWidth(420)
        box = QVBoxLayout(self)
        form = make_form()
        found = canopies.canopies(project)
        self.canopy = combo([(b.id, b.name) for b in found], chosen if any(b.id == chosen for b in found) else
                            (found[0].id if found else ""))
        form.addRow(_("Canopy"), self.canopy)
        self.portrait = combo([(1, _("Along the slope")), (0, _("Across the slope"))], 1)
        self.portrait.setToolTip(_("The long side of the modules up the slope, or level along the rows"))
        form.addRow(_("Modules"), self.portrait)
        self.gap = spin(0, 0.5, 0.02, " m", 2, 0.01)
        self.gap.setToolTip(_("Between two modules, along the rows and up the slope (the clamps)"))
        form.addRow(_("Gap between modules"), self.gap)
        self.overhang = spin(0, 2, 0.0, " m", 2, 0.05)
        self.overhang.setToolTip(_("How far the modules may go beyond the structure, on the outer sides"))
        form.addRow(_("Beyond the structure"), self.overhang)
        self.edge = spin(0, 2, 0.1, " m", 2, 0.05)
        self.edge.setToolTip(_("A free band along the outline of each slope"))
        form.addRow(_("Free edge"), self.edge)
        box.addLayout(form)
        note = QLabel(_("A sub-field on each slope, flush with the roof plane; those the canopy had are replaced. "
                        "The slope and the height are the structure's.") if found else
                      _("There is no canopy yet: place one in Modelling with «Parking canopy…»."))
        note.setWordWrap(True)
        box.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(_("Lay the modules"))
        buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(found))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        box.addWidget(buttons)

    def values(self) -> dict:
        """What canopies.lay takes."""
        return {"bid": self.canopy.currentData(), "portrait": bool(self.portrait.currentData()),
                "gap": self.gap.value(), "overhang": self.overhang.value(), "edge": self.edge.value()}
