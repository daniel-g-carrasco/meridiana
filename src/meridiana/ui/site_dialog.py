"""The dialog that finds the site: an address searched with Nominatim (services/geocoding.py, through Qt's
network) or the coordinates typed."""

from __future__ import annotations

import copy

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QPushButton, QVBoxLayout)

from .. import geo, model
from ..i18n import _, ngettext
from ..services import geocoding


class SiteDialog(QDialog):
    """Search an address (OpenStreetMap's Nominatim, at most one request a second as its policy asks) or
    type the coordinates."""

    def __init__(self, site: model.Site, parent=None, network: bool = True):
        super().__init__(parent)
        self.network = network                  # off in Settings > Privacy: coordinates only
        self.setWindowTitle(_("Find the site"))
        self.site = copy.copy(site)
        box = QVBoxLayout(self)
        row = QHBoxLayout()
        self.query = QLineEdit(site.address)
        self.query.setPlaceholderText(_("Address, or coordinates as 45.5226, 9.0300 or 45,5226; 9,0300"))
        search = QPushButton(_("Search"))
        row.addWidget(self.query, 1)
        row.addWidget(search)
        box.addLayout(row)
        self.found = QListWidget()
        box.addWidget(self.found)
        form = QFormLayout()
        self.lat = QDoubleSpinBox(decimals=6, minimum=-90, maximum=90, value=site.lat)
        self.lon = QDoubleSpinBox(decimals=6, minimum=-180, maximum=180, value=site.lon)
        form.addRow(_("Latitude"), self.lat)
        form.addRow(_("Longitude"), self.lon)
        box.addLayout(form)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        box.addWidget(self.status)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        box.addWidget(buttons)
        search.clicked.connect(self._search)
        self.query.returnPressed.connect(self._search)
        self.found.currentRowChanged.connect(self._choose)
        self.places: list[geocoding.Place] = []
        self.throttle = geocoding.Throttle()
        from PySide6.QtNetwork import QNetworkAccessManager
        self.net = QNetworkAccessManager(self)
        self.net.setTransferTimeout(15000)         # a search that hangs is said, not waited for ever

    def _search(self):
        text = self.query.text().strip()
        coordinates = geo.parse_coordinates(text)
        if coordinates is not None:
            self.lat.setValue(coordinates[0])
            self.lon.setValue(coordinates[1])
            self.status.setText(_("Coordinates taken."))
            return
        if not self.network:
            self.status.setText(_("The address search is off in Settings > Privacy: type the coordinates."))
            return
        if not self.throttle.allow():
            self.status.setText(_("One search a second, please (OpenStreetMap's rule)."))
            return
        from PySide6.QtCore import QUrl
        from PySide6.QtNetwork import QNetworkRequest

        from .tileloader import USER_AGENT
        req = QNetworkRequest(QUrl(geocoding.search_url(text)))
        req.setRawHeader(b"User-Agent", USER_AGENT)
        self.status.setText(_("Searching…"))
        reply = self.net.get(req)
        reply.finished.connect(lambda r=reply: self._found(r))

    def _found(self, reply):
        from PySide6.QtNetwork import QNetworkReply
        data = bytes(reply.readAll())
        ok = reply.error() == QNetworkReply.NetworkError.NoError
        message = reply.errorString()
        reply.deleteLater()
        self.show_answer(data if ok else None, message)

    def show_answer(self, data: bytes | None, message: str = "") -> None:
        """What the search gave: the places listed, or why there are none (also from the tests, without the
        network)."""
        self.found.clear()
        self.places = []
        if data is None:
            self.status.setText(_("The search did not answer: {error}").format(error=message))
            return
        try:
            self.places = geocoding.places(data)
        except ValueError:
            self.status.setText(_("The search answered something unreadable."))
            return
        for p in self.places:
            self.found.addItem(p.name)
        self.status.setText(ngettext("{n} place found. Choose it.", "{n} places found. Choose one.",
                                     len(self.places)).format(n=len(self.places)) if self.places else
                            _("Nothing found. Try fewer words, or type the coordinates."))

    def _choose(self, row):
        if 0 <= row < len(self.places):
            p = self.places[row]
            self.lat.setValue(p.lat)
            self.lon.setValue(p.lon)
            self.site.address = p.name

    def result(self) -> model.Site:
        self.site.lat, self.site.lon = self.lat.value(), self.lon.value()
        if not self.site.address:
            self.site.address = self.query.text().strip()
        return self.site
