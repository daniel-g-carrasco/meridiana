"""A reviewed product card. Unknown technical values stay empty, never guessed."""
from __future__ import annotations

import json

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QVBoxLayout)
from ..catalog import KINDS, personal
from ..i18n import _


class CatalogEditor(QDialog):
    def __init__(self, kind='modules', record=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Review personal product"))
        self.resize(600, 660)
        self.saved = None
        self.kind = QComboBox()
        for key, title in zip(KINDS, (_("Modules"), _("Inverters"), _("Microinverters"),
                                     _("Optimizers"), _("Batteries")), strict=True):
            self.kind.addItem(title, key)
        self.kind.setCurrentIndex(max(self.kind.findData(kind), 0))
        self.kind.setEnabled(False)
        record = dict(record or {})
        self.fields = {}
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.addRow(_("Product type"), self.kind)
        for key, label in (('manufacturer', _("Manufacturer")), ('model', _("Model")),
                           ('datasheet_url', _("Source document or URL"))):
            field = QLineEdit(str(record.pop(key, '') or ''))
            self.fields[key] = field
            form.addRow(label, field)
        for key in ('id', 'kind', 'source'):
            record.pop(key, None)
        from .catalog_dialog import field_names
        labels = field_names()
        self.technical_fields = {}
        for key in personal.REQUIRED[kind]:
            value = record.pop(key, None)
            field = QLineEdit("" if value is None else str(value))
            field.setPlaceholderText(_("Required stated value"))
            form.addRow(labels.get(key, key), field)
            self.technical_fields[key] = field
        self.values = QPlainTextEdit()
        self.values.setPlainText(json.dumps(record, indent=2, ensure_ascii=False))
        self.values.setAccessibleName(_("Technical fields in JSON"))
        self.kind.currentIndexChanged.connect(lambda: self.values.setPlainText(
            json.dumps(self.template(self.kind.currentData()), indent=2)))
        self.error = QLabel()
        self.error.setWordWrap(True)
        note = QLabel(_("Check every value against the source. Empty values are unknown. "
                        "Saving adds a local catalogue entry; it does not change the project."))
        note.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(note)
        layout.addLayout(form)
        extra_label = QLabel(_("Additional fields (JSON). Units: W, V, A, m, kWh"))
        extra_label.setWordWrap(True)
        layout.addWidget(extra_label)
        layout.addWidget(self.values, 1)
        layout.addWidget(self.error)
        layout.addWidget(buttons)

    @staticmethod
    def template(kind):
        return dict.fromkeys(personal.REQUIRED[kind])

    def record(self):
        values = json.loads(self.values.toPlainText())
        if not isinstance(values, dict):
            raise ValueError(_("Technical fields must be a JSON object."))
        for key, field in self.technical_fields.items():
            try:
                values[key] = float(field.text().strip().replace(",", "."))
            except ValueError as error:
                raise ValueError(_("A stated numeric value is required: {field}").format(field=key)) from error
        values.update({key: field.text().strip() for key, field in self.fields.items()})
        return personal.validate(self.kind.currentData(), values)

    def accept(self):
        try:
            self.saved = personal.save(self.kind.currentData(), self.record())
        except (ValueError, OSError) as error:
            self.error.setText(_("Not saved: {reason}").format(reason=error))
            return
        super().accept()


def review_record(kind, record=None, parent=None):
    dialog = CatalogEditor(kind, record, parent)
    return dialog.saved if dialog.exec() == QDialog.DialogCode.Accepted else None
