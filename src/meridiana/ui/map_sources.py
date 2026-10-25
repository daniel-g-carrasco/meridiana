"""Preferences > Maps (R36): the background the plan starts from (the best source for the site, a source, none), the
sources that cover the site in hand and every source of the program with its licence, as rows (ui/rows.py: no table
in a card), and the designer's own sources: an XYZ template, or a WMS or WMTS read from its capabilities, with the
attribution its licence asks for (without it the source is not used), the licence and where it was read, and the key
for the sources that want one (`{key}` in the address; the key goes to the system's keyring, never to the settings).
The capabilities are asked only when Preferences > Privacy lets the map servers be reached."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QComboBox, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QPushButton,
                               QSpinBox, QVBoxLayout, QWidget)

from .. import capabilities, tiles
from ..i18n import _
from .rows import RowList
from .style import Group


def kind_names() -> dict:
    return {"xyz": _("XYZ tiles (an address with {z}, {x}, {y})"), "wmts": _("WMTS (from its capabilities)"),
            "wms": _("WMS (from its capabilities)")}


def imagery_names() -> dict:
    return {"photo": _("Photo"), "map": _("Map")}


def _rows(sources) -> list:
    out = []
    for s in sources:
        licence = tiles.display_licence(s)
        tip = "\n".join(t for t in (s.credit(), _("Licence: {licence}").format(licence=licence) if licence else "",
                                    _("Read on {url} on {date}").format(url=s.licence_url, date=s.checked)
                                    if s.licence_url else "") if t)
        out.append((tiles.display_name(s), licence, tip))
    return out


class MapsPage(QWidget):
    def __init__(self, cfg, site=None, network=None, parent=None):
        """`site`: (lat, lon) of the project in hand, None for none; `network()`: whether the map servers may be
        asked (Preferences > Privacy, as the dialog shows it now)."""
        super().__init__(parent)
        from PySide6.QtNetwork import QNetworkAccessManager
        self.site = site
        self.network = network or (lambda: cfg.network_tiles)
        self.custom = [dict(d) for d in cfg.map_sources if isinstance(d, dict)]
        self.current = -1
        self.loading = False
        self.caps: capabilities.Capabilities | None = None
        self.known_keys: dict = {}              # source -> its key in the keyring, "" none, None no keyring
        self.net = QNetworkAccessManager(self)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)

        # the background the plan starts from
        group = Group(_("Background of the plan"))
        inside = QVBoxLayout(group)
        form = QFormLayout()
        self.default = QComboBox()
        form.addRow(_("Start from"), self.default)
        inside.addLayout(form)
        note = QLabel(_("Automatic takes the best source for the site of each project: the open orthophoto of the "
                        "region or of the country where there is one, else Sentinel-2 at 10 m. A source chosen here "
                        "or in the plan's Background menu is used where it covers the site; elsewhere the automatic "
                        "one is. The attribution of the source in use is always on the plan, at the bottom right."))
        note.setWordWrap(True)
        note.setObjectName("row-detail")
        inside.addWidget(note)
        box.addWidget(group)
        self._fill_default(cfg.background)

        # the sources at the site and all of them, as rows
        if site is not None:
            here = Group(_("At the site of the project"))
            QVBoxLayout(here).addWidget(self._list(self._covering()))
            box.addWidget(here)
        every = Group(_("The program's sources"))
        lay = QVBoxLayout(every)
        lay.addWidget(self._list(list(tiles.SOURCES.values())))
        left_out = QLabel(_("Each licence was read on its official page on 25/10/2026: the address and the date are "
                            "in the tooltip. Esri, Google, Bing and Azure are not here: their terms want an account "
                            "and a key and forbid keeping the tiles; they can be added below with your own key, under "
                            "their terms."))
        left_out.setWordWrap(True)
        left_out.setObjectName("row-detail")
        lay.addWidget(left_out)
        box.addWidget(every)

        # the designer's sources
        own = Group(_("Your sources"))
        lay = QVBoxLayout(own)
        row = QHBoxLayout()
        self.chooser = QComboBox()
        self.chooser.currentIndexChanged.connect(self._chosen)
        row.addWidget(self.chooser, 1)
        add = QPushButton(_("New source"))
        add.clicked.connect(self._add)
        row.addWidget(add)
        self.remove = QPushButton(_("Remove"))
        self.remove.setProperty("destructive", True)
        self.remove.clicked.connect(self._remove)
        row.addWidget(self.remove)
        lay.addLayout(row)
        form = QFormLayout()
        self.fields: dict[str, QWidget] = {}
        self.name = QLineEdit()
        form.addRow(_("Name"), self.name)
        self.kind = QComboBox()
        for key, text in kind_names().items():
            self.kind.addItem(text, key)
        form.addRow(_("Type"), self.kind)
        self.url = QLineEdit()
        form.addRow(_("Address"), self.url)
        read = QHBoxLayout()
        self.read = QPushButton(_("Read the capabilities"))
        self.read.clicked.connect(self.read_capabilities)
        read.addWidget(self.read)
        self.read_state = QLabel("")
        self.read_state.setWordWrap(True)
        self.read_state.setObjectName("row-detail")
        read.addWidget(self.read_state, 1)
        form.addRow("", read)
        self.layer = QComboBox()
        form.addRow(_("Layer"), self.layer)
        self.attribution = QLineEdit()
        self.attribution.setPlaceholderText(_("as its licence asks, for example «© Name of the provider, CC BY 4.0»"))
        form.addRow(_("Attribution"), self.attribution)
        self.licence = QLineEdit()
        self.licence.setPlaceholderText(_("for example CC BY 4.0, or the terms in a line"))
        form.addRow(_("Licence"), self.licence)
        self.licence_url = QLineEdit()
        self.licence_url.setPlaceholderText(_("where you read it"))
        form.addRow(_("Licence address"), self.licence_url)
        self.imagery = QComboBox()
        for key, text in imagery_names().items():
            self.imagery.addItem(text, key)
        form.addRow(_("It is"), self.imagery)
        self.max_zoom = QSpinBox()
        self.max_zoom.setRange(1, tiles.MAX_ZOOM)
        form.addRow(_("Highest zoom"), self.max_zoom)
        keys = QHBoxLayout()
        self.key_state = QLabel("")
        self.key_state.setWordWrap(True)
        keys.addWidget(self.key_state, 1)
        self.set_key = QPushButton(_("Set the key…"))
        self.set_key.clicked.connect(self._set_key)
        keys.addWidget(self.set_key)
        form.addRow(_("Key"), keys)
        self.form = QWidget()
        self.form.setLayout(form)
        lay.addWidget(self.form)
        self.problems = QLabel("")
        self.problems.setWordWrap(True)
        self.problems.setObjectName("problem")
        lay.addWidget(self.problems)
        how = QLabel(_("An XYZ address is a template with {z}, {x} and {y} (or {-y}), and {key} where a key goes. For "
                       "a WMS or a WMTS paste the address of the service or of its capabilities and read them: the "
                       "layers usable on the plan are listed (a WMS in EPSG:3857 or in degrees, a WMTS on the Web "
                       "Mercator grid). The tiles are kept in the cache like the others; read the terms of the "
                       "source before using it in a report."))
        how.setWordWrap(True)
        how.setObjectName("row-detail")
        lay.addWidget(how)
        box.addWidget(own)
        box.addStretch(1)
        for w in (self.name, self.url, self.attribution, self.licence, self.licence_url):
            w.textEdited.connect(lambda _t: self._typed())
        self.kind.currentIndexChanged.connect(lambda _i: self._typed())
        self.imagery.currentIndexChanged.connect(lambda _i: self._typed())
        self.max_zoom.valueChanged.connect(lambda _v: self._typed())
        self.layer.currentIndexChanged.connect(self._layer_chosen)
        self._fill(0 if self.custom else -1)

    # the lists

    def _covering(self) -> list:
        lat, lon = self.site
        return tiles.covering(tiles.catalogue(self.custom), lon, lat)

    def _list(self, sources) -> RowList:
        rows = RowList(_("No source covers the site."))
        rows.set_rows(_rows(sources))
        return rows

    def _fill_default(self, choice: str) -> None:
        keep = self.default.currentData() if self.default.count() else choice
        self.default.blockSignals(True)
        self.default.clear()
        sources = tiles.catalogue(self.custom)
        if self.site is not None:
            lat, lon = self.site
            best = sources.get(tiles.best(sources, lon, lat))
            self.default.addItem(_("Automatic: {name}").format(name=tiles.display_name(best)) if best
                                 else _("Automatic"), tiles.AUTO)
            listed = self._covering()
        else:
            self.default.addItem(_("Automatic: the best for the site"), tiles.AUTO)
            listed = list(sources.values())
        for s in listed:
            self.default.addItem(tiles.display_name(s), s.key)
        if keep not in (tiles.AUTO, tiles.NONE) and self.default.findData(keep) < 0 and keep in sources:
            self.default.addItem(_("{name} (not at this site)").format(name=tiles.display_name(sources[keep])), keep)
        self.default.addItem(_("None"), tiles.NONE)
        self.default.setCurrentIndex(max(0, self.default.findData(keep)))
        self.default.blockSignals(False)

    # the designer's sources

    def _fill(self, index: int) -> None:
        self.loading = True
        try:
            self.chooser.clear()
            for d in self.custom:
                usable = not tiles.problems(d)
                self.chooser.addItem(d.get("name") or _("(no name)") if usable else
                                     _("{name} (not used yet)").format(name=d.get("name") or _("(no name)")))
            self.current = index
            self.chooser.setCurrentIndex(index)
            self.form.setEnabled(index >= 0)
            self.remove.setEnabled(index >= 0)
            d = self.custom[index] if index >= 0 else {}
            self.name.setText(d.get("name", ""))
            self.kind.setCurrentIndex(max(0, self.kind.findData(d.get("kind", "xyz"))))
            self.url.setText(d.get("url", "") if d.get("kind", "xyz") == "xyz" or not d.get("capabilities")
                             else d.get("capabilities", ""))
            self.attribution.setText(d.get("attribution", ""))
            self.licence.setText(d.get("licence", ""))
            self.licence_url.setText(d.get("licence_url", ""))
            self.imagery.setCurrentIndex(max(0, self.imagery.findData(d.get("imagery", "photo"))))
            self.max_zoom.setValue(int(d.get("max_zoom", 19)) if isinstance(d.get("max_zoom", 19), int) else 19)
            self.layer.clear()
            if d.get("layer"):
                self.layer.addItem(d["layer"], d["layer"])
            self.caps = None
            self.read_state.setText("")
        finally:
            self.loading = False
        self._show_state()

    def _show_state(self) -> None:
        d = self.custom[self.current] if self.current >= 0 else None
        wms = self.kind.currentData() in ("wms", "wmts")
        self.read.setEnabled(d is not None and wms)
        self.layer.setEnabled(d is not None and wms)
        if d is None:
            self.problems.setText("")
            self.key_state.setText("")
            self.set_key.setEnabled(False)
            return
        found = tiles.problems(d)
        self.problems.setText(_("Not used until it is complete: {what}").format(what=" ".join(found)) if found else "")
        needs = "{key}" in d.get("url", "")
        self.set_key.setEnabled(needs)
        self.key_state.setText(self._key_text(d) if needs else _("This address has no {key}: none is needed."))
        self.chooser.setItemText(self.current, d.get("name") or _("(no name)") if not found else
                                 _("{name} (not used yet)").format(name=d.get("name") or _("(no name)")))

    def _key_text(self, d: dict) -> str:
        """What the keyring has for the source, asked once (not at every key typed in the address)."""
        from ..assistant import keys
        from .tileloader import KEYS
        if d["key"] not in self.known_keys:
            try:
                self.known_keys[d["key"]] = keys.get(d["key"], service=KEYS)
            except keys.KeyringMissing:
                self.known_keys[d["key"]] = None
        key = self.known_keys[d["key"]]
        if key is None:
            return _("No keyring on this system: a source that needs a key cannot be used.")
        return _("Key in the system's keyring: {key}").format(key=keys.masked(key)) if key else _("No key yet.")

    def _set_key(self) -> None:
        from ..assistant import keys
        from .tileloader import KEYS
        if self.current < 0:
            return
        key, ok = QInputDialog.getText(self, _("Key of the map source"), _("The key the provider gave you (it goes to "
                                       "the system's keyring, never to a file):"), QLineEdit.EchoMode.Password)
        if ok and key.strip():
            try:
                keys.put(self.custom[self.current]["key"], key, service=KEYS)
            except keys.KeyringMissing as error:
                self.key_state.setText(_("The key could not be kept: {why}").format(why=error))
                return
            self.known_keys[self.custom[self.current]["key"]] = key.strip()
        self._show_state()

    def _typed(self) -> None:
        if self.loading or self.current < 0:
            return
        d = self.custom[self.current]
        before = (not tiles.problems(d), d.get("name"))
        kind = self.kind.currentData()
        address = self.url.text().strip()
        if kind != d.get("kind"):
            d.update(kind=kind, layer="", matrix_set="", matrices=[], capabilities="")
            self.layer.clear()
        if kind == "xyz":
            d["url"] = address
        elif address != d.get("capabilities"):
            # another server: its capabilities are to be read again, and the layer and the matrices go with the old one
            d.update(capabilities=address, url=capabilities.base_url(address) if address else "", layer="",
                     matrix_set="", matrices=[])
            self.layer.clear()
        d.update(name=self.name.text().strip(), attribution=self.attribution.text().strip(),
                 licence=self.licence.text().strip(), licence_url=self.licence_url.text().strip(),
                 imagery=self.imagery.currentData(), max_zoom=max(self.max_zoom.value(), int(d.get("min_zoom", 0))))
        self._show_state()
        after = (not tiles.problems(d), d.get("name"))
        if after != before and (before[0] or after[0]):          # usable now, or no longer, or renamed: the defaults
            self._fill_default(self.default.currentData())

    def _add(self) -> None:
        self.custom.append({"key": tiles.new_key(), "name": _("New source"), "kind": "xyz", "url": "",
                            "attribution": "", "licence": "", "licence_url": "", "imagery": "photo", "min_zoom": 0,
                            "max_zoom": 19, "bbox": [], "matrices": [], "added": date.today().isoformat()})
        self._fill(len(self.custom) - 1)
        self.name.setFocus()
        self.name.selectAll()

    def _remove(self) -> None:
        if self.current < 0:
            return
        gone = self.custom.pop(self.current)
        from ..assistant import keys
        from .tileloader import KEYS
        try:
            keys.forget(gone["key"], service=KEYS)
        except keys.KeyringMissing:
            pass                                    # no keyring: no key was ever kept for it
        self._fill(min(self.current, len(self.custom) - 1))
        self._fill_default(self.default.currentData())

    # the capabilities

    def read_capabilities(self) -> None:
        if self.current < 0:
            return
        address = self.url.text().strip()
        kind = self.kind.currentData()
        if not address:
            self.read_state.setText(_("Paste the address of the service first."))
            return
        if not self.network():
            self.read_state.setText(_("The map servers are switched off in Preferences > Privacy."))
            return
        from PySide6.QtNetwork import QNetworkRequest

        from .tileloader import USER_AGENT
        req = QNetworkRequest(QUrl(capabilities.capabilities_url(address, kind)))
        req.setRawHeader(b"User-Agent", USER_AGENT)
        req.setTransferTimeout(30000)
        self.read_state.setText(_("Reading…"))
        reply = self.net.get(req)
        reply.finished.connect(lambda r=reply: self._read(r))

    def _read(self, reply) -> None:
        from PySide6.QtNetwork import QNetworkReply
        data = bytes(reply.readAll())
        ok = reply.error() == QNetworkReply.NetworkError.NoError
        message = reply.errorString()
        reply.deleteLater()
        self.show_capabilities(data if ok else None, message)

    def show_capabilities(self, data: bytes | None, message: str = "") -> None:
        """What the server answered (also from the tests, without the network): the usable layers listed, the first
        chosen, the form filled with what the server says; or why not."""
        if self.current < 0:
            return
        if data is None:
            self.read_state.setText(_("The server did not answer: {error}").format(error=message))
            return
        try:
            caps = capabilities.read(data)
        except ValueError as error:
            self.read_state.setText(_("Not readable: {why}").format(why=error))
            return
        kind = self.kind.currentData()
        if caps.kind != kind:
            self.kind.setCurrentIndex(self.kind.findData(caps.kind))
        usable = [la for la in caps.layers if not la.problem(caps.kind)]
        self.caps = caps
        self.loading = True
        self.layer.clear()
        for la in usable:
            self.layer.addItem(f"{la.title} ({la.name})" if la.title != la.name else la.name, la.name)
        self.loading = False
        skipped = len(caps.layers) - len(usable)
        self.read_state.setText(
            _("{title}: {n} layers usable on the plan, {m} not (another grid or system).").format(
                title=caps.title or caps.kind.upper(), n=len(usable), m=skipped) if skipped else
            _("{title}: {n} layers usable on the plan.").format(title=caps.title or caps.kind.upper(), n=len(usable)))
        if usable:
            previous = self.custom[self.current].get("layer")
            self.layer.setCurrentIndex(max(0, self.layer.findData(previous)))
            self._layer_chosen(self.layer.currentIndex())

    def _layer_chosen(self, _index: int) -> None:
        if self.loading or self.current < 0 or self.caps is None:
            return
        layer = self.caps.layer(self.layer.currentData())
        if layer is None:
            return
        d = self.custom[self.current]
        typed = {k: d.get(k, "") for k in ("name", "attribution", "licence", "licence_url")}
        if typed["name"] == _("New source"):       # the name a new source starts with: the layer's title is better
            typed["name"] = ""
        new = capabilities.source_dict(self.caps, layer, d["key"], typed["name"], self.url.text().strip(),
                                       d.get("added") or date.today().isoformat())
        for k, v in typed.items():                 # what the designer wrote stays; the server fills what is empty
            if v:
                new[k] = v
        new["imagery"] = d.get("imagery", "photo")
        self.custom[self.current] = new
        self.loading = True
        self.name.setText(new["name"])
        self.attribution.setText(new["attribution"])
        self.licence.setText(new["licence"])
        self.licence_url.setText(new["licence_url"])
        self.max_zoom.setValue(new["max_zoom"])
        self.loading = False
        self._show_state()
        self._fill_default(self.default.currentData())

    def _chosen(self, index: int) -> None:
        if not self.loading and index != self.current:
            self._fill(index)

    def choice(self) -> tuple[str, list]:
        """The background to start from and the designer's sources (complete or not: an incomplete one is kept, not
        used, and said here)."""
        return self.default.currentData() or tiles.AUTO, [dict(d) for d in self.custom]
