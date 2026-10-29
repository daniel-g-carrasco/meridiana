"""Choosing a product from the catalogue: a search box (every word must appear in the maker, model or series),
the filters above the list, the list, and the full record of the one selected with the address of its datasheet.

The filters (study 16, theme E): the origin (datasheets read for Meridiana, or the CEC list), the maker of that
origin, and a power range for every kind; for the modules also the cell family (TOPCon, HJT, back contact, PERC,
thin film, polycrystalline, monocrystalline, not stated), monofacial or bifacial, the efficiency from and the
length up to. They are remembered from one opening to the next while the program runs, each kind with its own,
and «Clear filters» gives the whole list back.

The list shows every record (Daniel, R25: «arriva solo a 400 righe»; 16,959 modules): a QAbstractTableModel that
makes a cell only when the view draws it, sorted by the column clicked (catalog.sorted_by, on the data, not on
the text shown), behind a QSortFilterProxyModel that keeps the rows the search finds (catalog.search)."""

from __future__ import annotations

import html

from PySide6.QtCore import (QAbstractTableModel, QObject, QRunnable, QSignalBlocker, QSortFilterProxyModel, Qt,
                            QThreadPool, QTimer, Signal)
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QSplitter, QTableView, QTextBrowser, QVBoxLayout)

from .. import catalog, log
from ..i18n import _, ngettext, number
from . import tell, waiting
from .theme import marked

SEARCH_PAUSE_MS = 200

# what each kind of catalogue had in its filters when its window was last left: kind -> filters()
_REMEMBERED: dict = {}


def forget_filters() -> None:
    """The next window of every kind opens with no filter (the tests, and nothing else, ask for this)."""
    _REMEMBERED.clear()


def kind_titles() -> dict:
    return {"modules": _("PV modules"), "inverters": _("Inverters"), "microinverters": _("Microinverters"),
            "optimizers": _("Optimizers"), "batteries": _("Batteries")}


def family_names() -> dict:
    """The families of the cell, as the list and the card say them. «Monocrystalline» alone is a listing that
    gives the silicon and not the cell: the name says so, or a designer would take it for every mono cell."""
    return {"topcon": _("TOPCon"), "hjt": _("HJT (heterojunction)"), "back_contact": _("Back contact"),
            "perc": _("PERC"), "thin_film": _("Thin film"), "poly": _("Polycrystalline"),
            "mono": _("Monocrystalline, cell not stated"), catalog.UNKNOWN_FAMILY: _("Cell not stated")}


def field_names() -> dict:
    return {
        "manufacturer": _("Manufacturer"), "model": _("Model"), "series": _("Series"), "technology": _("Technology"),
        "cell_family": _("Cell family"),
        "pmax": _("Power at STC (W)"), "vmp": "Vmp (V)", "imp": "Imp (A)", "voc": "Voc (V)", "isc": "Isc (A)",
        "gamma_pmax": _("γ Pmax (%/K)"), "beta_voc": _("β Voc (%/K)"), "alpha_isc": _("α Isc (%/K)"),
        "cells": _("Cells"), "cells_in_series": _("Cells in series"), "length": _("Length (m)"),
        "width": _("Width (m)"), "weight_kg": _("Weight (kg)"), "efficiency_pct": _("Efficiency (%)"),
        "bifacial": _("Bifacial"), "bifaciality": _("Bifaciality (%)"),
        "bifaciality_estimated": _("Bifaciality, estimated (%)"), "fire_rating": _("Fire rating"),
        "max_system_voltage_v": _("Maximum system voltage (V)"), "warranty_power_years": _("Power warranty (years)"),
        "ac_power_nominal_w": _("Nominal AC power (W)"), "dc_voltage_max_v": _("Maximum DC voltage (V)"),
        "mppt_voltage_min_v": _("MPPT from (V)"), "mppt_voltage_max_v": _("MPPT to (V)"),
        "mppt_count": _("MPPT"), "efficiency_euro_pct": _("European efficiency (%)"),
        "efficiency_max_pct": _("Maximum efficiency (%)"), "phases": _("Phases"),
        "cei_0_21": _("CEI 0-21 cited"), "usable_energy_kwh": _("Usable energy (kWh)"),
        "nominal_energy_kwh": _("Nominal energy (kWh)"), "chemistry": _("Chemistry"),
        "voltage_class": _("Voltage class"), "nominal_voltage_v": _("Nominal voltage (V)"),
        "max_charge_power_w": _("Maximum charge power (W)"), "max_discharge_power_w": _("Maximum discharge power (W)"),
        "round_trip_efficiency_pct": _("Round-trip efficiency (%)"), "depth_of_discharge_pct": _("Depth of discharge (%)"),
        "cycles_warranted": _("Cycles warranted"), "modules_min": _("Modules, from"), "modules_max": _("Modules, to"),
        "modules_per_unit": _("Modules per unit"), "rated_input_power_w": _("Rated input power (W)"),
        "max_input_voltage_v": _("Maximum input voltage (V)"), "max_input_isc_a": _("Maximum input Isc (A)"),
        "max_output_current_a": _("Maximum output current (A)"), "rapid_shutdown": _("Rapid shutdown"),
        "efficiency_weighted_pct": _("Weighted efficiency (%)"), "efficiency_peak_pct": _("Peak efficiency (%)"),
        "compatible_inverters": _("Compatible inverters"), "warranty_years": _("Warranty (years)"),
        "notes": _("Notes"), "coupling": _("AC/DC coupling"),
        "efficiency_basis": _("Efficiency measurement basis"), "voltage_range_v": _("Voltage range (V)"),
        "max_charge_current_a": _("Maximum charge current (A)"),
        "max_discharge_current_a": _("Maximum discharge current (A)"),
        "max_parallel_units": _("Maximum parallel units"),
        "battery_voltage_range_v": _("Battery voltage range (V)"),
        "battery_charge_power_max_w": _("Maximum battery charge power (W)"),
        "battery_discharge_power_max_w": _("Maximum battery discharge power (W)"),
        "battery_current_max_a": _("Maximum battery current (A)"),
        "storage_compatibility": _("Attested battery compatibility"),
        "datasheet_url": _("Datasheet"), "retrieved": _("Read on"), "source": _("Origin"),
    }


def origin_names() -> dict:
    return {"curated": _("datasheet"), "cec": _("CEC list (USA)"), "personal": _("Personal catalogue")}


def how_many(kind: str, n: int) -> str:
    """«N modules», «N inverters»…: the count under the list."""
    words = {"modules": ngettext("{n} module", "{n} modules", n),
             "inverters": ngettext("{n} inverter", "{n} inverters", n),
             "microinverters": ngettext("{n} microinverter", "{n} microinverters", n),
             "optimizers": ngettext("{n} optimizer", "{n} optimizers", n),
             "batteries": ngettext("{n} battery", "{n} batteries", n)}
    return words.get(kind, "{n}").format(n=number(n, 0, grouping=True))


class CatalogModel(QAbstractTableModel):
    """Every record of a kind; a cell is made only when it is drawn. A column is (field, title) or (field, title,
    key): the key, a function of the record, is what a click on the column sorts by."""

    def __init__(self, columns: list, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.records: list = []
        self.origins = origin_names()
        self.families = family_names()

    def set_records(self, records) -> None:
        self.beginResetModel()
        self.records = list(records)
        self.endResetModel()

    def rowCount(self, parent=None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self.records)

    def columnCount(self, parent=None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        r = self.records[index.row()]
        key = self.columns[index.column()][0]
        v = r.get(key)
        numeric = isinstance(v, (int, float)) and not isinstance(v, bool)
        if role == Qt.ItemDataRole.DisplayRole:
            if key == "source":
                return self.origins.get(v, v)
            if key == "cell_family":
                return self.families.get(v, "")
            return number(float(v), 0) if numeric else str(v or "")
        if role == Qt.ItemDataRole.TextAlignmentRole and numeric:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.UserRole:
            return r
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.columns[section][1]
        return None

    def sort(self, column: int, order=Qt.SortOrder.AscendingOrder) -> None:
        """By the column clicked, in Python: a comparison called back from C++ for each pair of 17,000 rows
        would take seconds. The selection follows its record."""
        if not 0 <= column < len(self.columns):
            return
        spec = self.columns[column]
        self.layoutAboutToBeChanged.emit()
        before = self.persistentIndexList()
        kept = [(self.records[i.row()], i.column()) for i in before]
        self.records = catalog.sorted_by(self.records, spec[2] if len(spec) > 2 else spec[0],
                                         order == Qt.SortOrder.DescendingOrder)
        where = {id(r): n for n, r in enumerate(self.records)}
        self.changePersistentIndexList(before, [self.index(where[id(r)], c) for r, c in kept])
        self.layoutChanged.emit()


class CatalogFilter(QSortFilterProxyModel):
    """The rows the search keeps (`accepted`: the records' ids; None, all). Sorting is the model's."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.accepted: set | None = None

    def set_accepted(self, accepted: set | None) -> None:
        self.beginFilterChange()                        # Qt 6.10 on: invalidateRowsFilter is deprecated
        self.accepted = accepted
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, row: int, parent) -> bool:
        return self.accepted is None or id(self.sourceModel().records[row]) in self.accepted

    def sort(self, column: int, order=Qt.SortOrder.AscendingOrder) -> None:
        self.sourceModel().sort(column, order)


class ReaderSignals(QObject):
    done = Signal(str)                  # what went wrong; "" when the records are read


class CatalogReader(QRunnable):
    """The first reading of a kind of the catalogue (the files unpacked and put in order: 0,4 s for the modules on
    Daniel's PC), away from the window's thread: the catalogue's window opens at once, with the arc over the list
    (study 16, F3)."""

    def __init__(self, kind: str):
        super().__init__()
        self.kind = kind
        self.signals = ReaderSignals()

    def run(self):
        error = ""
        try:
            catalog.prepare(self.kind)
        except Exception as e:      # noqa: BLE001 (a thread's boundary: said out loud, not lost)
            log.complain(f"catalogue {self.kind}", e)
            error = f"{type(e).__name__}: {e}"
        tell(self.signals.done, error)


class CatalogDialog(QDialog):
    def __init__(self, kind: str, parent=None, browse: bool = False):
        super().__init__(parent)
        self.kind = kind
        self.browse = browse
        self.setWindowTitle(_("Catalogue: {what}").format(what=kind_titles().get(kind, kind)))
        self.resize(1000, 620)
        modules = kind == "modules"
        self.query = QLineEdit()
        self.query.setPlaceholderText(_("Maker, model, series: every word must appear"))
        self.origin = QComboBox()
        self.origin.addItem(_("All"), "")
        self.origin.addItem(_("Datasheets read for Meridiana"), "curated")
        self.origin.addItem(_("CEC list (USA)"), "cec")
        self.origin.addItem(_("Personal catalogue"), "personal")
        self.maker = QComboBox()
        self.maker.setEditable(True)                    # typed, with the completer, among hundreds of makers
        self.maker.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.maker.lineEdit().setPlaceholderText(_("All the makers"))
        self.maker.lineEdit().setClearButtonEnabled(True)
        self.maker.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.maker.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.maker.setToolTip(_("The maker's whole name, as the list below writes it: pick it from the list or type it"))
        unit = "kWh" if kind == "batteries" else "W"
        self.low = QDoubleSpinBox(minimum=0, maximum=10_000_000, decimals=0, suffix=f" {unit}")
        self.high = QDoubleSpinBox(minimum=0, maximum=10_000_000, decimals=0, suffix=f" {unit}")
        self.high.setSpecialValueText(_("no limit"))
        self.low.setSpecialValueText(_("from 0"))
        self.family = self.bifacial = self.efficiency = self.length = None
        if modules:
            self.family = QComboBox()
            self.family.addItem(_("Any cell"), "")
            for key, name in family_names().items():
                self.family.addItem(name, key)
            self.family.setToolTip(_("The cell as the datasheet or the listing names it. «Monocrystalline» alone is "
                                     "a listing that gives the silicon and not the cell type."))
            self.bifacial = QComboBox()
            self.bifacial.addItem(_("Monofacial and bifacial"), "")
            self.bifacial.addItem(_("Bifacial only"), "yes")
            self.bifacial.addItem(_("Monofacial only"), "no")
            self.efficiency = QDoubleSpinBox(minimum=0, maximum=40, decimals=1, singleStep=0.5, suffix=" %")
            self.efficiency.setSpecialValueText(_("any efficiency"))
            self.efficiency.setPrefix(_("efficiency from "))
            self.efficiency.setToolTip(_("A module whose efficiency is not known is left out when this is on. For the "
                                         "CEC list the efficiency is worked out from power and size, where it has them."))
            self.length = QDoubleSpinBox(minimum=0, maximum=4, decimals=2, singleStep=0.1, suffix=" m")
            self.length.setSpecialValueText(_("any length"))
            self.length.setPrefix(_("length up to "))
            self.length.setToolTip(_("The long side of the module. A module whose size is not known is left out "
                                     "when this is on."))
        self.clear = QPushButton(_("Clear filters"))
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.hide()
        # the first opening of a kind reads the catalogue in a worker (CatalogReader): the window opens at once,
        # empty, with the arc over the list past the threshold; the filters can be set meanwhile
        self.reading = not catalog.ready(kind)
        self.pending_maker = ""
        self._fill_makers()
        self._restore(_REMEMBERED.get(kind))
        row = QHBoxLayout()
        row.addWidget(self.query, 3)
        row.addWidget(self.origin, 1)
        row.addWidget(self.maker, 2)
        row.addWidget(self.clear)
        facets = QHBoxLayout()
        if modules:
            facets.addWidget(self.family, 2)
            facets.addWidget(self.bifacial, 2)
        facets.addWidget(QLabel(_("Power")))
        facets.addWidget(self.low)
        facets.addWidget(QLabel("-"))
        facets.addWidget(self.high)
        if modules:
            facets.addWidget(self.efficiency)
            facets.addWidget(self.length)
        facets.addStretch(1)
        self.model = CatalogModel(self._columns(), self)
        if not self.reading:
            self.model.set_records(catalog.search(kind, limit=None))      # all of them, in the catalogue's order
        self.rows = CatalogFilter(self)
        self.rows.setSourceModel(self.model)
        self.table = QTableView()
        self.table.setModel(self.rows)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # the catalogue's order until a column is clicked: without the indicator at -1, enabling the sorting would
        # sort by the first column at once
        self.table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(False)
        self.table.horizontalHeader().sectionClicked.connect(
            lambda _c: self.table.horizontalHeader().setSortIndicatorShown(True))
        self.table.horizontalHeader().setResizeContentsPrecision(60)       # the widths from the first rows
        self.table.verticalHeader().setDefaultSectionSize(self.table.fontMetrics().height() + 8)
        self.table.verticalHeader().hide()
        from .shared_tables import install
        install(self.table)
        self.table.selectionModel().selectionChanged.connect(lambda *_a: self._selected())
        self.table.doubleClicked.connect(lambda _i: None if self.browse else self.accept())
        self.detail = QTextBrowser()
        self.detail.setOpenExternalLinks(True)
        split = QSplitter()
        split.addWidget(self.table)
        split.addWidget(self.detail)
        split.setSizes([620, 380])
        self.count = QLabel()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if browse:
            buttons.setStandardButtons(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(self.reject)
            self.ok = None
        box = QVBoxLayout(self)
        box.addLayout(row)
        box.addLayout(facets)
        box.addWidget(split, 1)
        box.addWidget(self.count)
        box.addWidget(self.hint)
        self.new_product = QPushButton(_("Add personal product…"))
        self.new_product.clicked.connect(lambda: self._new_personal())
        self.compare_products = QPushButton(_("Compare selected products"))
        self.compare_products.setToolTip(_("Select two to four rows with Ctrl or Shift, then compare their fields."))
        self.compare_products.clicked.connect(self._compare_selected)
        box.addWidget(self.compare_products)
        self.revise_product = QPushButton(_("Review selected as personal product…"))
        self.revise_product.clicked.connect(lambda: self._new_personal(self.chosen()) if self.chosen() else None)
        box.addWidget(self.revise_product)
        box.addWidget(self.new_product)
        box.addWidget(buttons)
        self.timer = QTimer(self, singleShot=True, interval=SEARCH_PAUSE_MS)
        self.timer.timeout.connect(self._search)
        signals = [self.query.textChanged, self.origin.currentIndexChanged, self.maker.editTextChanged,
                   self.low.valueChanged, self.high.valueChanged]
        if modules:
            signals += [self.family.currentIndexChanged, self.bifacial.currentIndexChanged,
                        self.efficiency.valueChanged, self.length.valueChanged]
        for w in signals:
            w.connect(lambda *_a: self.timer.start())
        self.origin.currentIndexChanged.connect(lambda _i: self._fill_makers())     # the makers of that origin
        self.clear.clicked.connect(self._clear)
        self.records: list = []
        self.sized = False
        self.spinner = waiting.Spinner(self.table.viewport(), 48, tip=_("Reading the catalogue…"))
        waiting.pin(self.spinner, self.table.viewport(), where="centre")
        self.reading_wait = waiting.Delayed(self.spinner, self)
        if self.reading:
            self.count.setText(_("Reading the catalogue…"))
            self.reading_wait.begin()
            self.reader = CatalogReader(kind)
            self.reader.signals.done.connect(self._read)
            QThreadPool.globalInstance().start(self.reader)
        else:
            self._search()

    def _compare_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not 2 <= len(rows) <= 4:
            self.hint.setText(_("Select two to four products to compare (Ctrl or Shift)."))
            self.hint.show()
            return
        records = [self.record_at(row.row()) for row in rows]
        names = field_names()
        present = list(dict.fromkeys(key for rec in records for key in rec))
        keys = [key for key in names if key in present] + [key for key in present if key not in names]
        header = "<tr><th></th>" + "".join("<th>" + html.escape(str(r.get("model", ""))) + "</th>"
                                               for r in records) + "</tr>"
        lines = []
        for key in keys:
            if key == "id":
                continue
            values = [r.get(key) for r in records]
            cells = []
            for value in values:
                if value is None or value == "" or value == []:
                    cells.append(_("Unknown"))
                elif isinstance(value, bool):
                    cells.append(_("yes") if value else _("no"))
                elif isinstance(value, (int, float)):
                    cells.append(number(value, 3 if abs(value) < 10 else 1))
                elif key == "source":
                    cells.append(origin_names().get(value, value))
                else:
                    cells.append(str(value))
            lines.append("<tr><th>" + html.escape(names.get(key, key)) + "</th>" +
                         "".join("<td>" + html.escape(value) + "</td>" for value in cells) + "</tr>")
        self.detail.setHtml("<table>" + header + "".join(lines) + "</table>")
        self.detail.verticalScrollBar().setValue(0)

    def _new_personal(self, record=None):
        from .catalog_editor import review_record
        if review_record(self.kind, record, parent=self) is not None:
            self.model.set_records(catalog.search(self.kind, limit=None))
            self._fill_makers()
            self.origin.setCurrentIndex(self.origin.findData("personal"))
            self._search()

    def _read(self, error: str) -> None:
        """The catalogue is read: the makers, the filters the designer set meanwhile, the list."""
        self.reading = False
        self.reading_wait.end()
        if error:
            self.count.setText(_("The catalogue could not be read: {error}").format(error=error))
            return
        wanted = self.maker.currentText().strip() or self.pending_maker
        self._fill_makers()
        if wanted:
            with QSignalBlocker(self.maker):
                i = self.maker.findText(wanted, Qt.MatchFlag.MatchFixedString)
                if i >= 0:
                    self.maker.setCurrentIndex(i)
                else:
                    self.maker.setEditText(wanted)
        self.model.set_records(catalog.search(self.kind, limit=None))
        self.timer.stop()
        self._search()

    def _columns(self):
        if self.kind == "modules":
            return [("manufacturer", _("Manufacturer")), ("model", _("Model")), ("pmax", "W"),
                    ("cell_family", _("Cell family"), catalog.family_rank), ("source", _("Origin"))]
        if self.kind == "batteries":
            return [("manufacturer", _("Manufacturer")), ("model", _("Model")), ("usable_energy_kwh", "kWh"),
                    ("voltage_class", _("Class")), ("source", _("Origin"))]
        if self.kind == "optimizers":
            return [("manufacturer", _("Manufacturer")), ("model", _("Model")), ("rated_input_power_w", "W"),
                    ("max_input_voltage_v", _("V max")), ("source", _("Origin"))]
        if self.kind == "microinverters":
            return [("manufacturer", _("Manufacturer")), ("model", _("Model")), ("ac_power_nominal_w", _("W AC")),
                    ("modules_per_unit", _("Modules")), ("source", _("Origin"))]
        return [("manufacturer", _("Manufacturer")), ("model", _("Model")), ("ac_power_nominal_w", _("W AC")),
                ("phases", _("Phases")), ("source", _("Origin"))]

    # -- the filters ---------------------------------------------------------------------------------------

    def maker_name(self) -> str:
        """The maker asked for, written as the list writes it; "" when the box is empty or holds only a part of a
        name (the search box finds those)."""
        text = self.maker.currentText().strip()
        i = self.maker.findText(text, Qt.MatchFlag.MatchFixedString) if text else -1       # without case
        return self.maker.itemText(i) if i >= 0 else ""

    def _fill_makers(self) -> None:
        """The makers of the origin chosen, keeping the one asked for if that origin has it (once the catalogue is
        read)."""
        if self.reading:
            return
        keep = self.maker_name()
        with QSignalBlocker(self.maker):
            self.maker.clear()
            self.maker.addItems(catalog.brands(self.kind, self.origin.currentData() or ""))
            self.maker.setCurrentIndex(self.maker.findText(keep, Qt.MatchFlag.MatchFixedString) if keep else -1)
            if not keep:
                self.maker.setEditText("")

    def filters(self) -> dict:
        """Every filter as it stands now, to remember and to search by."""
        return {"text": self.query.text(), "origin": self.origin.currentData() or "", "maker": self.maker_name(),
                "low": self.low.value(), "high": self.high.value(),
                "family": self.family.currentData() if self.family else "",
                "bifacial": self.bifacial.currentData() if self.bifacial else "",
                "efficiency": self.efficiency.value() if self.efficiency else 0.0,
                "length": self.length.value() if self.length else 0.0}

    def _restore(self, state: dict | None) -> None:
        """Put the filters of the last window of this kind back, before anything listens to them."""
        if not state:
            return
        self.query.setText(state["text"])
        self.origin.setCurrentIndex(max(self.origin.findData(state["origin"]), 0))
        self._fill_makers()
        if self.reading:
            self.pending_maker = state["maker"]            # put back once the makers are known
        elif state["maker"]:
            self.maker.setCurrentIndex(self.maker.findText(state["maker"], Qt.MatchFlag.MatchFixedString))
        self.low.setValue(state["low"])
        self.high.setValue(state["high"])
        if self.family:
            self.family.setCurrentIndex(max(self.family.findData(state["family"]), 0))
            self.bifacial.setCurrentIndex(max(self.bifacial.findData(state["bifacial"]), 0))
            self.efficiency.setValue(state["efficiency"])
            self.length.setValue(state["length"])

    def _clear(self) -> None:
        self.timer.stop()
        self.query.clear()
        self.origin.setCurrentIndex(0)
        self.maker.setCurrentIndex(-1)
        self.maker.setEditText("")
        self.low.setValue(0)
        self.high.setValue(0)
        if self.family:
            self.family.setCurrentIndex(0)
            self.bifacial.setCurrentIndex(0)
            self.efficiency.setValue(0)
            self.length.setValue(0)
        self.timer.stop()
        self._search()

    def _search(self) -> None:
        """The rows the search finds, every one of them; the count says how many. While the catalogue is read the
        filters wait: the search runs when it is."""
        if self.reading:
            return
        f = self.filters()
        options = {"family": f["family"], "bifacial": {"yes": True, "no": False}.get(f["bifacial"]),
                   "manufacturer": f["maker"], "efficiency_min": f["efficiency"], "length_max": f["length"]}
        everything = not (f["text"].split() or f["origin"] or f["low"] or f["high"] or f["maker"] or f["family"]
                          or f["bifacial"] or f["efficiency"] or f["length"])
        self.records = (list(self.model.records) if everything else
                        catalog.search(self.kind, f["text"], f["origin"], f["low"], f["high"], limit=None, **options))
        self.rows.set_accepted(None if everything else {id(r) for r in self.records})
        if not self.sized:
            self.table.resizeColumnsToContents()
            self.sized = True
        total = len(self.model.records)
        shown = self.rows.rowCount()
        self.count.setText(how_many(self.kind, shown) if shown == total else
                           _("{shown} of {total}").format(shown=how_many(self.kind, shown),
                                                          total=number(total, 0, grouping=True)))
        self._say_what_is_left_out(f, options)
        _REMEMBERED[self.kind] = f
        if self.ok is not None:
            self.ok.setEnabled(False)
        if shown:
            self.table.selectRow(0)
            self.table.scrollToTop()
        else:
            self.detail.clear()

    def _say_what_is_left_out(self, f: dict, options: dict) -> None:
        """A module whose efficiency or size is not known cannot satisfy a filter on it, and is left out: the
        window says how many of the others were, or the list would look shorter than the catalogue is."""
        lacking = 0
        if f["efficiency"] or f["length"]:
            wide = catalog.search(self.kind, f["text"], f["origin"], f["low"], f["high"], limit=None,
                                  **{**options, "efficiency_min": 0.0, "length_max": 0.0})
            lacking = sum(1 for r in wide if (f["efficiency"] and not r.get("efficiency_pct"))
                          or (f["length"] and not r.get("length")))
        self.hint.setText(ngettext("{n} module without this data is left out",
                                   "{n} modules without this data are left out", lacking)
                          .format(n=number(lacking, 0, grouping=True)) if lacking else "")
        self.hint.setVisible(bool(lacking))

    # -- the card ------------------------------------------------------------------------------------------

    def record_at(self, row: int) -> dict:
        """The record of a row as the list shows it now."""
        return self.rows.index(row, 0).data(Qt.ItemDataRole.UserRole)

    def _selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if self.ok is not None:
            self.ok.setEnabled(bool(rows))
        if not rows:
            return
        r = self.record_at(rows[0].row())
        names = field_names()
        lines = []
        for key, label in names.items():
            v = r.get(key)
            if v in (None, "", []):
                continue
            if key == "datasheet_url":
                lines.append(f"<tr><td>{html.escape(label)}</td><td><a href='{html.escape(str(v))}'>"
                             f"{html.escape(str(v))}</a></td></tr>")
                continue
            if key == "source":
                v = origin_names().get(v, v)
            elif key == "cell_family":
                v = family_names().get(v, v)
            if isinstance(v, bool):
                v = _("yes") if v else _("no")
            elif isinstance(v, float):
                v = number(v, 3 if abs(v) < 10 else 1)
            if key == "efficiency_pct" and r.get("efficiency_derived"):
                v = f"{v} ({_('worked out from power and size')})"
            elif key == "bifaciality_estimated":
                v = f"{v} ({_('estimated from the cell family, not on the datasheet')})"
            lines.append(f"<tr><td>{marked(html.escape(label))}</td><td>{marked(html.escape(str(v)))}</td></tr>")
        note = ""
        if r.get("source") == "cec":
            note = "<p><i>" + html.escape(_("From the CEC list: a model for the US market, with the values tested "
                                            "for the California Energy Commission.")) + "</i></p>"
        self.detail.setHtml(f"<h3>{html.escape(str(r.get('manufacturer', '')))} {html.escape(str(r.get('model', '')))}"
                            f"</h3><table>{''.join(lines)}</table>{note}")

    def accept(self):
        from ..catalog.audit import audit_record
        record = self.chosen()
        if record is None and not self.browse:
            return
        if record is not None:
            issues = audit_record(record, self.kind)["issues"]
            if issues:
                self.hint.setText(_("Product not selected: inconsistent data. {issues}").format(
                    issues="; ".join(issues)))
                self.hint.show()
                return
        super().accept()

    def chosen(self) -> dict | None:
        rows = self.table.selectionModel().selectedRows()
        return dict(self.record_at(rows[0].row())) if rows else None
