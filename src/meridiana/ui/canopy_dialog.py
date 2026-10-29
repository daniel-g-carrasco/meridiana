"""Parking dimensions and a plan preview before placing editable canopy slopes."""
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QSpinBox, QVBoxLayout

from .. import canopies
from ..i18n import _
from .properties import combo, make_form, spin
from .template_dialog import Outline


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
        self.preview = Outline()
        box.addWidget(self.preview)
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
        ring = fields[0].ring if len(fields) == 1 else fields[0].ring[:2] + fields[1].ring[2:]
        self.preview.show_ring(ring)
        self.summary.setText(_("{n} spaces · {width:g} × {depth:g} m footprint").format(
            n=spec.stalls * spec.rows, width=spec.stalls * spec.bay_width, depth=spec.rows * spec.depth))
