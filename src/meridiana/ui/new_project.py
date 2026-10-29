"""New project from the place: one field, offline suggestions, an explicit online search,
a map to confirm the point, optional data after it, then Create and draw."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QTransform
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (QCheckBox, QComboBox, QCompleter, QDoubleSpinBox, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from .. import geo, model, places, worldmap
from ..coordinates import CoordinateError, CoordinateReading
from ..i18n import _, ngettext
from ..services import geocoding
from .design import Space, Text, set_text
from .plan import PlanView
from .style import SectionGate, grow_label
from .tileloader import USER_AGENT


class SitePreview(PlanView):
    locationPicked = Signal(float, float)

    def __init__(self, cache_dir, parent=None):
        self.tiles_allowed = False
        self.has_point = False
        super().__init__(cache_dir, parent)
        self.pressed = None
        self.loader.offline = True
        self.setMinimumSize(320, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.show_overview()

    def show_overview(self) -> None:
        self.set_source("none")
        self.set_origin(41.5, 12.5)
        self.setTransform(QTransform().fromScale(1 / 1800, 1 / 1800))
        self.centerOn(0, 0)
        # PlanView otherwise fits an empty 120 m drawing on the first resize.
        self.user_moved = True
        self._moved()

    def set_point(self, lat: float, lon: float) -> None:
        self.has_point = True
        self.set_origin(lat, lon)
        scale = 1.0 if self.tiles_allowed else 1 / 600
        self.setTransform(QTransform().fromScale(scale, scale))
        self.user_moved = True
        self.centerOn(0, 0)
        self.site_mark.setPos(0, 0)
        self.site_mark.show()
        self._moved()

    def clear_point(self) -> None:
        had_point = self.has_point
        self.has_point = False
        self.site_mark.hide()
        if had_point:
            self.show_overview()

    def _moved(self) -> None:
        super()._moved()
        self.site_mark.setVisible(self.has_point)

    def _credit(self) -> None:
        if self.source == "none":
            from . import plan_overlays
            self.attribution.set_text("Natural Earth", self.viewport().width())
            plan_overlays.place(self)
        else:
            super()._credit()

    def coordinates_at(self, point) -> tuple[float, float]:
        if self.world.equal_earth:
            lon, lat = worldmap.from_equal_earth(point.x(), -point.y(), self.origin.lon, self.origin.lat)
        else:
            lon, lat = self.origin.to_lonlat(point.x(), -point.y())
        return lat, lon

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.pressed = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.pressed is not None:
            if (event.position().toPoint() - self.pressed).manhattanLength() < 6:
                point = self.mapToScene(event.position().toPoint())
                try:
                    lat, lon = self.coordinates_at(point)
                except ValueError:
                    pass  # The margin outside the projected globe is not a geographic point.
                else:
                    self.locationPicked.emit(lat, lon)
            self.pressed = None
        super().mouseReleaseEvent(event)


class NewProjectPage(QWidget):
    created = Signal(dict)

    def __init__(self, paths, cfg, choices=None, parent=None, registry=None):
        super().__init__(parent)
        self.paths, self.cfg, self.registry = paths, cfg, registry
        self.choices = list(places.municipalities() if choices is None else choices)
        self.candidate: CoordinateReading | None = None
        self.address = ""
        self.coordinate_error = ""
        self.online_places: list[geocoding.Place] = []
        self.throttle = geocoding.Throttle()
        self.net = QNetworkAccessManager(self)
        self.net.setTransferTimeout(15000)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(Space.XXXL, Space.XXL, Space.XXXL, Space.XXL)
        outer.setSpacing(Space.S)
        title = QLabel(_("New project"))
        set_text(title, Text.DISPLAY)
        outer.addWidget(title)
        lead = QLabel(_("Start from the place. Type an address, a municipality, coordinates or a map link; "
                        "then check the point on the map."))
        set_text(lead, Text.DESCRIPTION)
        lead.setWordWrap(True)
        outer.addWidget(lead)
        outer.addSpacing(Space.M)
        columns = QHBoxLayout()
        columns.setSpacing(Space.XL)
        outer.addLayout(columns, 1)
        left_panel = QWidget()
        left_panel.setMinimumWidth(340)
        left_panel.setMaximumWidth(460)
        left_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        left = QVBoxLayout(left_panel)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(Space.M)
        columns.addWidget(left_panel, 2)
        query_row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText(_("Address, municipality, coordinates or link"))
        self.search = QPushButton(_("Search"))
        query_row.addWidget(self.query, 1)
        query_row.addWidget(self.search)
        left.addLayout(query_row)
        coordinate_row = QHBoxLayout()
        self.latitude = QLineEdit()
        self.longitude = QLineEdit()
        for field, label, example in ((self.latitude, _("Latitude"), "45.5226"),
                                      (self.longitude, _("Longitude"), "9.0300")):
            column = QVBoxLayout()
            caption = QLabel(label)
            caption.setBuddy(field)
            column.addWidget(caption)
            field.setPlaceholderText(example)
            field.setAccessibleName(label)
            column.addWidget(field)
            coordinate_row.addLayout(column)
        left.addLayout(coordinate_row)
        coordinates_help = QLabel(_("Latitude, longitude: 45.5226, 9.0300. Paste coordinates or a full map link "
                                   "above, or paste both coordinates into Latitude."))
        coordinates_help.setWordWrap(True)
        set_text(coordinates_help, Text.SECONDARY)
        left.addWidget(coordinates_help)
        privacy = QLabel(_("Suggestions while you type come only from ISTAT and your recent projects. "
                           "OpenStreetMap Nominatim is asked only by Search."))
        privacy.setWordWrap(True)
        set_text(privacy, Text.SECONDARY)
        left.addWidget(privacy)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        set_text(self.status, Text.SECONDARY)
        left.addWidget(self.status)
        self.found = QListWidget()
        self.found.setMaximumHeight(170)
        self.found.hide()
        left.addWidget(self.found)
        self.optional = QCheckBox(_("Optional project data"))
        left.addWidget(self.optional)
        optional_scroll = QScrollArea()
        optional_scroll.setWidgetResizable(True)
        optional_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        optional_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        optional_scroll.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.optional_body = QWidget()
        form = QFormLayout(self.optional_body)
        form.setContentsMargins(0, 0, Space.S, 0)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.name = QLineEdit()
        form.addRow(_("Project name"), self.name)
        self.client = QComboBox()
        form.addRow(_("Client"), self.client)
        self.job = QComboBox()
        form.addRow(_("Job"), self.job)
        self.reserved = QCheckBox(_("Reserved project"))
        form.addRow(self.reserved)
        reserved_help = QLabel(_("Names and addresses never leave this PC."))
        reserved_help.setWordWrap(True)
        set_text(reserved_help, Text.SECONDARY)
        form.addRow(reserved_help)
        self.maps_consent = QCheckBox(_("Allow online map tiles for this project"))
        form.addRow(self.maps_consent)
        consent_help = QLabel(_("The area shown is sent to the map provider. For reserved projects only, "
                               "with this explicit consent."))
        consent_help.setWordWrap(True)
        set_text(consent_help, Text.SECONDARY)
        form.addRow(consent_help)
        self.distributor = QLineEdit()
        form.addRow(_("Distributor"), self.distributor)
        self.pod = QLineEdit()
        form.addRow("POD", self.pod)
        self.voltage = QDoubleSpinBox(maximum=1_000_000, decimals=0, suffix=" V")
        self.voltage.setSpecialValueText(_("not stated"))
        form.addRow(_("Supply voltage"), self.voltage)
        self.phases = QComboBox()
        self.phases.addItem(_("not stated"), "")
        self.phases.addItem(_("Single phase"), "1")
        self.phases.addItem(_("Three phase"), "3")
        form.addRow(_("Phases"), self.phases)
        self.level = QComboBox()
        self.level.addItem(_("not stated"), "")
        for level in ("BT", "MT", "AT"):
            self.level.addItem(level, level)
        form.addRow(_("Connection level"), self.level)
        self.connection = QComboBox()
        self.connection.addItem(_("not stated"), "")
        for key, label in (("existing", _("Existing connection")), ("new", _("New connection")),
                           ("modification", _("Modification of the connection"))):
            self.connection.addItem(label, key)
        form.addRow(_("Connection"), self.connection)
        self.available = QDoubleSpinBox(maximum=1_000_000_000, decimals=1, suffix=" kW")
        self.available.setSpecialValueText(_("not stated"))
        form.addRow(_("Available or contracted power"), self.available)
        self.requested = QDoubleSpinBox(maximum=1_000_000_000, decimals=1, suffix=" kW")
        self.requested.setSpecialValueText(_("not stated"))
        form.addRow(_("Power requested for the new plant"), self.requested)
        self.practice = QLineEdit()
        form.addRow(_("Connection practice code"), self.practice)
        for label in self.optional_body.findChildren(QLabel):
            label.setWordWrap(True)
            grow_label(label)
        optional_scroll.setWidget(self.optional_body)
        left.addWidget(optional_scroll, 1)
        self.optional_gate = SectionGate(self.optional, _("Enable Optional project data to edit these fields."),
                                         [self.optional_body])
        self.create = QPushButton(_("Create and draw"))
        self.create.setEnabled(False)
        left.addWidget(self.create)
        self.preview = SitePreview(paths.cache)
        self.preview.loader.offline = True
        columns.addWidget(self.preview, 5)

        self.suggestion_rows: dict[str, places.PlaceSuggestion] = {}
        from PySide6.QtCore import QStringListModel
        self.suggestions = QStringListModel(self)
        completer = QCompleter(self.suggestions, self.query)
        completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.query.setCompleter(completer)
        completer.activated[str].connect(self.choose_suggestion)
        self.query.textChanged.connect(self._changed)
        self.query.returnPressed.connect(self._search)
        self.latitude.textChanged.connect(self._axes_changed)
        self.longitude.textChanged.connect(self._axes_changed)
        self.search.clicked.connect(self._search)
        self.found.currentRowChanged.connect(self._choose_online)
        self.preview.locationPicked.connect(self._picked)
        self.create.clicked.connect(self._create)
        self.reserved.toggled.connect(self._privacy_changed)
        self.maps_consent.toggled.connect(lambda _v: self._apply_map_privacy(start=True))
        self.maps_consent.setEnabled(False)
        self.client.currentIndexChanged.connect(self._fill_jobs)
        self.job.currentIndexChanged.connect(self._job_changed)
        self.refresh_registry()

    def refresh_registry(self) -> None:
        self.client.blockSignals(True)
        self.client.clear()
        self.client.addItem(_("No client"), "")
        if self.registry is not None:
            for client in self.registry.list_clients():
                self.client.addItem(client["name"], client["id"])
        self.client.blockSignals(False)
        self._fill_jobs()

    def _fill_jobs(self) -> None:
        client_id = self.client.currentData() or ""
        self.job.blockSignals(True)
        self.job.clear()
        self.job.addItem(_("No job"), "")
        if self.registry is not None:
            for job in self.registry.list_jobs(client_id=client_id):
                self.job.addItem(f"{job['code']}  {job['name']}", job["id"])
        self.job.blockSignals(False)

    def _job_reserved(self) -> bool:
        job = self.registry.job(self.job.currentData()) if self.registry is not None and self.job.currentData() else None
        return bool(job and job["reserved"])

    def _effective_reserved(self) -> bool:
        return self.reserved.isChecked() or self._job_reserved()

    def _job_changed(self) -> None:
        if self._job_reserved():
            self.reserved.setChecked(True)
        self._privacy_changed(self.reserved.isChecked())

    def set_choices(self, choices) -> None:
        self.choices = list(choices)
        self._changed(self.query.text())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_map_privacy()

    def hideEvent(self, event) -> None:
        self.preview.loader.offline = True
        super().hideEvent(event)

    def _privacy_changed(self, reserved: bool) -> None:
        job_reserved = self._job_reserved()
        if job_reserved and not reserved:
            self.reserved.blockSignals(True)
            self.reserved.setChecked(True)
            self.reserved.blockSignals(False)
            reserved = True
        self.reserved.setEnabled(not job_reserved)
        self.search.setEnabled(not reserved)
        self.maps_consent.setEnabled(reserved)
        if not reserved:
            self.maps_consent.setChecked(False)
        self._apply_map_privacy(start=True)

    def _apply_map_privacy(self, start: bool = False) -> None:
        allowed = (self.candidate is not None and self.cfg.network_tiles
                   and (not self._effective_reserved() or self.maps_consent.isChecked()))
        changed = self.preview.tiles_allowed != allowed
        self.preview.tiles_allowed = allowed
        self.preview.loader.offline = not allowed
        self.preview.set_source("osm" if allowed else "none")
        if changed and start and self.candidate is not None:
            self.preview.set_point(self.candidate.lat, self.candidate.lon)

    def reset(self) -> None:
        self.query.clear()
        self.name.clear()
        self.refresh_registry()
        self.maps_consent.setChecked(False)
        self.reserved.setChecked(False)
        for field in (self.distributor, self.pod, self.practice):
            field.clear()
        for field in (self.voltage, self.available, self.requested):
            field.setValue(0)
        for field in (self.phases, self.level, self.connection):
            field.setCurrentIndex(0)
        self.optional.setChecked(False)
        self.found.clear()
        self.found.hide()
        self.online_places = []
        self.candidate = None
        self._set_axes(None)
        self._apply_map_privacy()
        self.preview.clear_point()
        self.create.setEnabled(False)
        self.status.clear()

    @staticmethod
    def _coordinate_shaped(text: str) -> bool:
        return bool(re.search(r"°|º|https?://|^\s*(?:EPSG:|UTM\b|Gauss|GB\s|\d{1,2}[NSC-HJ-NP-X]\s)",
                              text, re.IGNORECASE)
                    or re.fullmatch(r"[\s\d.,;+\-]+", text))

    def _changed(self, text: str) -> None:
        rows = places.search(text, self.choices)
        self.suggestion_rows = {row.display: row for row in rows}
        self.suggestions.setStringList(list(self.suggestion_rows))
        self.coordinate_error = ""
        try:
            point = geo.read_coordinates(text)
        except CoordinateError as error:
            self.coordinate_error = str(error)
            self.candidate = None
            self._set_axes(None)
            self._apply_map_privacy()
            self.preview.clear_point()
            self.create.setEnabled(False)
            self.status.setText(self.coordinate_error if self._coordinate_shaped(text) else "")
            return
        self._take(point, text)

    def _take(self, point: CoordinateReading, address: str, sync_axes: bool = True) -> None:
        self.candidate = point
        self.address = address.strip()
        if sync_axes:
            self._set_axes(point)
        labels = {"decimal": _("Decimal degrees"), "dms": "DMS", "ddm": _("Degrees and decimal minutes"),
                  "link": _("Map link"), "grid": _("Projected coordinates"), "place": _("Local place"),
                  "map": _("Point clicked on the map")}
        detail = f"{point.datum} {point.zone}".strip()
        self.status.setText(f"{labels.get(point.format, point.format)} · {detail}")
        self._apply_map_privacy()
        self.preview.set_point(point.lat, point.lon)
        self.create.setEnabled(True)

    def choose_suggestion(self, display: str) -> None:
        choice = self.suggestion_rows.get(display)
        if choice is not None:
            self.query.blockSignals(True)
            self.query.setText(choice.display)
            self.query.blockSignals(False)
            self._take(CoordinateReading(choice.lat, choice.lon, "place"), choice.display)

    def _set_axes(self, point: CoordinateReading | None) -> None:
        for field, value in ((self.latitude, point.lat if point else None),
                             (self.longitude, point.lon if point else None)):
            field.blockSignals(True)
            field.setText(format(value, ".8f").rstrip("0").rstrip(".") if value is not None else "")
            field.blockSignals(False)

    def _axes_changed(self, _text: str) -> None:
        latitude, longitude = self.latitude.text().strip(), self.longitude.text().strip()
        pasted_pair = True
        try:
            # In a dedicated axis field, an Italian decimal comma is a decimal separator.
            # Whole pairs use an unambiguous separator (comma + space, semicolon, or two decimals).
            if re.fullmatch(r"[+-]?\d+(?:[.,]\d*)?", latitude):
                raise CoordinateError("one coordinate")
            # A whole pair, DMS, grid reference or map link can be pasted into the first field.
            point = geo.read_coordinates(latitude)
        except CoordinateError:
            pasted_pair = False
            try:
                point = geo.read_coordinates(f"{latitude};{longitude}")
            except CoordinateError as error:
                self.candidate = None
                self.create.setEnabled(False)
                self.status.setText(str(error) if latitude and longitude else "")
                self._apply_map_privacy()
                self.preview.clear_point()
                return
        self._take(point, f"{point.lat:.8f}, {point.lon:.8f}", sync_axes=pasted_pair)

    def _picked(self, lat: float, lon: float) -> None:
        self._take(CoordinateReading(lat, lon, "map"), self.query.text())

    def _search(self) -> None:
        if self.candidate is not None and self.candidate.format != "place":
            return
        text = self.query.text().strip()
        if not text:
            self.status.setText(_("Write a place first."))
            return
        if self._effective_reserved():
            self.status.setText(_("A reserved project never sends names or addresses. Use local suggestions, "
                                  "coordinates or a click on the offline map."))
            return
        if not self.cfg.network_geocoding:
            self.status.setText(_("The online search is off in Settings > Privacy. Local suggestions and "
                                  "coordinates still work."))
            return
        if self.coordinate_error and self._coordinate_shaped(text):
            self.status.setText(self.coordinate_error)
            return
        if not self.throttle.allow():
            self.status.setText(_("One search a second, please (OpenStreetMap's rule)."))
            return
        from PySide6.QtNetwork import QNetworkRequest
        request = QNetworkRequest(QUrl(geocoding.search_url(text)))
        request.setRawHeader(b"User-Agent", USER_AGENT)
        self.status.setText(_("Searching with OpenStreetMap Nominatim…"))
        self.send(request)

    def send(self, request: QNetworkRequest) -> None:
        reply = self.net.get(request)
        reply.finished.connect(lambda r=reply: self._answer(r))

    def _answer(self, reply: QNetworkReply) -> None:
        data = bytes(reply.readAll())
        ok = reply.error() == QNetworkReply.NetworkError.NoError
        message = reply.errorString()
        reply.deleteLater()
        self.show_answer(data if ok else None, message)

    def show_answer(self, data: bytes | None, message: str = "") -> None:
        self.found.clear()
        self.online_places = []
        if data is None:
            self.status.setText(_("The search did not answer: {error}").format(error=message))
            return
        try:
            self.online_places = geocoding.places(data)
        except ValueError:
            self.status.setText(_("The search answered something unreadable."))
            return
        for place in self.online_places:
            self.found.addItem(place.name)
        self.found.setVisible(bool(self.online_places))
        self.status.setText(ngettext("{n} place found. Choose it.", "{n} places found. Choose one.",
                                     len(self.online_places)).format(n=len(self.online_places))
                            if self.online_places else _("Nothing found. Try fewer words or type coordinates."))

    def _choose_online(self, row: int) -> None:
        if 0 <= row < len(self.online_places):
            place = self.online_places[row]
            self._take(CoordinateReading(place.lat, place.lon, "place"), place.name)

    def _create(self) -> None:
        if self.candidate is None:
            return
        import datetime
        consent = ({"tiles": datetime.date.today().isoformat()}
                   if self.reserved.isChecked() and self.maps_consent.isChecked() else {})
        site = model.Site(self.candidate.lat, self.candidate.lon, self.address)
        network = model.Network(distributor=self.distributor.text().strip(), pod=self.pod.text().strip(),
                                voltage_v=self.voltage.value(), phases=self.phases.currentData(),
                                level=self.level.currentData(), connection=self.connection.currentData(),
                                available_kw=self.available.value(), requested_kw=self.requested.value(),
                                practice_code=self.practice.text().strip())
        job = self.registry.job(self.job.currentData()) if self.registry is not None and self.job.currentData() else None
        self.created.emit({"name": self.name.text().strip(), "site": site,
                           "reserved": self.reserved.isChecked() or bool(job and job["reserved"]), "network": network,
                           "network_consent": consent,
                           "client_id": job["client_id"] if job is not None else self.client.currentData() or "",
                           "job_id": self.job.currentData() or ""})
