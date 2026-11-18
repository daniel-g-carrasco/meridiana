"""Storage setup page; all persistence is delegated to the caller's session edit."""
from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDoubleSpinBox, QFormLayout,
                               QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget)

from ..energy.storage import check_storage, operating_battery
from ..i18n import _


class StoragePage(QWidget):
    def __init__(self, settings: dict, inverters: list, on_change, parent=None):
        super().__init__(parent)
        self._settings = deepcopy(settings)
        self._battery = deepcopy(settings.get("battery") or {})
        self._on_change = on_change
        layout = QVBoxLayout(self)
        title = QLabel(_("Storage"))
        layout.addWidget(title)
        self.name = QLabel()
        self.name.setWordWrap(True)
        layout.addWidget(self.name)
        choose = QPushButton(_("Choose battery…"))
        choose.clicked.connect(self._choose)
        layout.addWidget(choose)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.coupling = QComboBox()
        self.coupling.addItem(_("AC: independent storage converter"), "ac")
        self.coupling.addItem(_("DC: hybrid inverter"), "dc")
        self.coupling.setCurrentIndex(1 if settings.get("storage_coupling") == "dc" else 0)
        form.addRow(_("Connection"), self.coupling)
        self.inverter = QComboBox()
        self.inverter.addItem(_("No inverter selected"), {})
        selected = settings.get("storage_inverter") or {}
        records = [entry.get("record", entry) for entry in inverters]
        if selected and selected not in records:
            records.append(selected)
        for rec in records:
            self.inverter.addItem(f"{rec.get('manufacturer', '')} {rec.get('model', '')}".strip(), rec)
            if rec == selected:
                self.inverter.setCurrentIndex(self.inverter.count() - 1)
        form.addRow(_("Storage inverter"), self.inverter)
        self.units = QSpinBox()
        self.units.setRange(1, 1000)
        self.units.setValue(settings.get("battery_units", 1))
        form.addRow(_("Complete battery systems in parallel"), self.units)
        self.efficiency = QDoubleSpinBox()
        self.efficiency.setRange(0, 100)
        self.efficiency.setSpecialValueText(_("Not supplied"))
        self.efficiency.setSuffix(" %")
        self.efficiency.setValue(settings.get("storage_efficiency_pct") or 0)
        form.addRow(_("AC round-trip efficiency (designer input)"), self.efficiency)
        layout.addLayout(form)
        explanation = QLabel(_("Hourly balance uses AC production and an equivalent AC round-trip efficiency once. "
                              "DC coupling does not recover clipped PV energy. Unknown compatibility is not approval."))
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status)
        self.apply_button = QPushButton(_("Apply storage configuration"))
        self.apply_button.clicked.connect(self._apply)
        layout.addWidget(self.apply_button)
        remove = QPushButton(_("Remove storage"))
        remove.clicked.connect(lambda: self._on_change({"battery": {}, "storage_coupling": "", "storage_inverter": {}}))
        layout.addWidget(remove)
        for widget in (self.coupling, self.inverter):
            widget.currentIndexChanged.connect(self._refresh)
        self.units.valueChanged.connect(self._refresh)
        self.efficiency.valueChanged.connect(self._refresh)
        layout.addStretch()
        self._refresh()

    def _choose(self):
        from .catalog_dialog import CatalogDialog
        dialog = CatalogDialog("batteries", self)
        if dialog.exec() == QDialog.DialogCode.Accepted and (rec := dialog.chosen()):
            self._battery = deepcopy(rec)
            self._refresh()

    def patch(self):
        return {"battery": deepcopy(self._battery), "battery_units": self.units.value(),
                "storage_coupling": self.coupling.currentData(),
                "storage_inverter": deepcopy(self.inverter.currentData()) if self.coupling.currentData() == "dc" else {},
                "storage_efficiency_pct": self.efficiency.value() or None}

    def _refresh(self, *_args):
        self.name.setText(f"{self._battery.get('manufacturer', '')} {self._battery.get('model', '')}".strip() or _("No battery"))
        patch = self.patch()
        self.inverter.setEnabled(patch["storage_coupling"] == "dc")
        result = check_storage(self._battery, patch["storage_inverter"], patch["storage_coupling"], patch["battery_units"])
        states = {"compatible": _("Model pairing documented"), "incompatible": _("Incompatible configuration"),
                  "unknown": _("Compatibility unknown")}
        messages = [states[result.status], *result.messages, *result.sources]
        valid = bool(self._battery)
        try:
            operating_battery(patch)
        except ValueError as exc:
            messages.append(str(exc))
            valid = False
        self.status.setText("\n".join(messages))
        self.apply_button.setEnabled(valid)

    def _apply(self):
        patch = self.patch()
        operating_battery(patch)
        self._on_change(patch)
