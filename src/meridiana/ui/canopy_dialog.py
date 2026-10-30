"""Parking dimensions and a 3D preview (R282, study 22, 3.8) before placing editable canopy slopes.

The preview draws what the dialog makes today: the placement planes of canopies.fields, one per row, over their
dashed footprint and with the height under their low edge; columns and beams come with the canopy structure (study
22, lot L5) as preview3d.box faces. The pills: sides 1 and 3 the length of the row (the width per space follows,
the spaces kept), sides 2 and 4 the depth (per row, the rows kept), the height under the low edge and the slope."""
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QSpinBox, QVBoxLayout

from .. import canopies
from ..i18n import _, number
from .preview3d import Face, Guide, Pill, Preview3D
from .properties import combo, make_form, spin
from .template_dialog import LightSides, parse_measure


class CanopyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Parking canopy"))
        self.setMinimumWidth(440)
        box = QVBoxLayout(self)
        form = make_form()
        self.stalls = QSpinBox()
        self.stalls.setRange(1, 100)
        self.stalls.setValue(4)
        self.rows = combo([(1, _("One row, single slope")), (2, _("Two rows, opposed slopes"))], 1)
        form.addRow(_("Spaces per row"), self.stalls)
        form.addRow(_("Arrangement"), self.rows)
        self.fields = {}
        for key, label, low, high, value, unit in (
                ('bay_width', _("Width per space"), 0.5, 20, 2.5, ' m'),
                ('depth', _("Depth per row"), 1, 50, 5, ' m'),
                ('clearance', _("Minimum height of placement plane"), 0.1, 100, 2.7, ' m'),
                ('tilt', _("Slope"), 0, 60, 8, ' °'),
                ('turn', _("Turn (counter-clockwise)"), -180, 180, 0, ' °')):
            self.fields[key] = spin(low, high, value, unit, 2, 0.5)
            form.addRow(label, self.fields[key])
        box.addLayout(form)
        self.ring: list | None = None           # the footprint of all the rows, as the 2D preview drew it
        self.preview = Preview3D(self, number=number, parse=parse_measure)
        self.preview.hint = _("Drag to turn · click a side to write its length")
        self.preview.setMinimumSize(300, 220)
        self.preview.edited.connect(self._pill_written)
        box.addWidget(self.preview, 1)
        self._lights = LightSides(self.preview, {self.fields['bay_width']: {1, 3}, self.fields['depth']: {2, 4},
                                                 self.fields['clearance']: {'clearance'},
                                                 self.fields['tilt']: {'tilt'}, self.stalls: {1, 3}}, self)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        box.addWidget(self.summary)
        note = QLabel(_("Creates placement surfaces and modules. Dimensions are editable examples; columns, beams, "
                        "vehicle clearance and structural checks are not modelled."))
        note.setWordWrap(True)
        box.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(_("Place it on the plan"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        box.addWidget(buttons)
        self.stalls.valueChanged.connect(self._update)
        self.rows.currentIndexChanged.connect(self._update)
        for field in self.fields.values():
            field.valueChanged.connect(self._update)
        self._update()

    def spec(self):
        return canopies.Spec(stalls=self.stalls.value(), rows=self.rows.currentData(),
                             **{key: field.value() for key, field in self.fields.items()})

    def _update(self, *_args):
        spec = self.spec()
        fields = canopies.fields(spec, (0, 0))
        self.ring = fields[0].ring if len(fields) == 1 else fields[0].ring[:2] + fields[1].ring[2:]
        self._draw(spec, fields)
        self.summary.setText(_("{n} spaces · {width:g} × {depth:g} m footprint").format(
            n=spec.stalls * spec.rows, width=spec.stalls * spec.bay_width, depth=spec.rows * spec.depth))

    def _draw(self, spec, fields) -> None:
        def corners(sf):
            surface = sf.support.surface()
            return [(x, y, surface.z(x, y)) for x, y in sf.ring]
        rows = [corners(sf) for sf in fields]
        first, last = rows[0], rows[-1]
        faces = [Face(points, "plane") for points in rows]
        outline = [first[0], first[1], last[2], last[3]]
        guides = [Guide([(x, y, 0.0) for x, y, _z in outline + outline[:1]], "ground")]
        guides += [Guide([p, (p[0], p[1], 0.0)], "dashed") for p in outline]
        if len(rows) == 2:
            guides.append(Guide([first[2], first[3]], "ridge"))
        length, depth = spec.stalls * spec.bay_width, spec.rows * spec.depth
        east = [first[1], first[2]] + ([last[2]] if len(rows) == 2 else [])
        west = [last[3]] + ([first[3]] if len(rows) == 2 else []) + [first[0]]
        low_mid = tuple((first[0][i] + first[1][i]) / 2 for i in range(3))
        high_mid = tuple((first[3][i] + first[2][i]) / 2 for i in range(3))
        text_m = f"{number(length)} m"
        pills = [Pill(1, [first[0], first[1]], length, text_m, 1), Pill(2, east, depth, f"{number(depth)} m", 2),
                 Pill(3, [last[2], last[3]], length, text_m, 3), Pill(4, west, depth, f"{number(depth)} m", 4),
                 Pill('clearance', [(first[0][0], first[0][1], 0.0), first[0]], spec.clearance,
                      f"{number(spec.clearance)} m"),
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
