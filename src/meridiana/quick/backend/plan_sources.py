"""Map source editor for Quick: the common catalogue, capabilities and keyring.

The editor owns a draft of settings. Apply emits that draft; credentials never
enter it. Network replies and parsing are asynchronous and scoped to the source
and address which requested them.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date

from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, QUrl, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from meridiana import capabilities, tiles
from meridiana.assistant import keys
from meridiana.i18n import _

KEYS = "meridiana-maps"
USER_AGENT = b"Meridiana (photovoltaic design; map capabilities)"


class _Parsed(QObject):
    done = Signal(int, object, str)


class _Read(QRunnable):
    def __init__(self, serial, data):
        super().__init__()
        self.serial, self.data, self.signals = serial, data, _Parsed()

    def run(self):
        try:
            result, error = capabilities.read(self.data), ""
        except ValueError as exc:
            result, error = None, str(exc)
        self.signals.done.emit(self.serial, result, error)


class MapSourcesController(QObject):
    changed = Signal()
    applied = Signal(str, "QVariantList")

    def __init__(self, cfg, site=None, network=None, key_store=None, parent=None):
        super().__init__(parent)
        self.site, self.network = site, network or (lambda: cfg.network_tiles)
        self._store = key_store if key_store is not None else keys
        self._custom = deepcopy([d for d in cfg.map_sources if isinstance(d, dict)])
        self._default, self._current = cfg.background, 0 if self._custom else -1
        self._caps, self._layers, self._known = None, [], {}
        self._read_state, self._key_error = "", ""
        self._reply, self._jobs, self._serial, self._busy = None, {}, 0, False
        self._downloads, self._oversize = {}, set()
        self._closed = False
        self.net = QNetworkAccessManager(self)
        self._refresh()

    def _source(self):
        return self._custom[self._current] if 0 <= self._current < len(self._custom) else None

    def load_preferences(self, choice, sources):
        """Reload a saved draft when another settings surface changes it."""
        self._cancel()
        self._custom = deepcopy([d for d in sources if isinstance(d, dict)])
        self._default = choice
        self.select(0 if self._custom else -1)

    @staticmethod
    def _rows(sources):
        out = []
        for source in sources:
            licence = tiles.display_licence(source)
            tip = "\n".join(t for t in (source.credit(),
                _("Licence: {licence}").format(licence=licence) if licence else "",
                _("Read on {url} on {date}").format(url=source.licence_url, date=source.checked)
                if source.licence_url else "") if t)
            out.append({"key": source.key, "name": tiles.display_name(source), "licence": licence, "tip": tip})
        return out

    def _refresh(self):
        catalogue = tiles.catalogue(self._custom)
        if self.site is None:
            covering = list(catalogue.values())
            automatic = _("Automatic: the best for the site")
        else:
            lat, lon = self.site
            covering = tiles.covering(catalogue, lon, lat)
            best = catalogue.get(tiles.best(catalogue, lon, lat))
            automatic = _("Automatic: {name}").format(name=tiles.display_name(best)) if best else _("Automatic")
        self._site_rows = self._rows(covering)
        self._all_rows = self._rows(tiles.SOURCES.values())
        self._defaults = [{"key": tiles.AUTO, "name": automatic}] + self._rows(covering)
        if self._default in catalogue and self._default not in [row["key"] for row in self._defaults]:
            self._defaults.append({"key": self._default, "name": _("{name} (not at this site)").format(
                name=tiles.display_name(catalogue[self._default]))})
        self._defaults.append({"key": tiles.NONE, "name": _("None")})
        if self._default not in [row["key"] for row in self._defaults]:
            self._default = tiles.AUTO
        self._custom_rows = []
        for source in self._custom:
            name = source.get("name") or _("(no name)")
            ready = not tiles.problems(source)
            self._custom_rows.append({"key": source["key"], "name": name if ready else
                _("{name} (not used yet)").format(name=name), "ready": ready})
        source = self._source()
        problems = tiles.problems(source) if source else []
        self._problems = _("Not used until it is complete: {what}").format(what=" ".join(problems)) if problems else ""
        self._needs_key = bool(source and "{key}" in source.get("url", ""))
        self._key_state = self._key_error
        if not self._key_state:
            self._key_state = self._key_text(source) if self._needs_key else (
                _("This address has no {key}: none is needed.") if source else "")
        self.changed.emit()

    def _key_text(self, source):
        name = source["key"]
        if name not in self._known:
            try:
                value = self._store.get(name, service=KEYS)
                # Retain only a masked status, never the credential in a QML property.
                self._known[name] = _("Key in the system's keyring: {key}").format(key=keys.masked(value)) \
                    if value else _("No key yet.")
            except keys.KeyringMissing:
                self._known[name] = _("No keyring on this system: a source that needs a key cannot be used.")
        return self._known[name]

    def _cancel(self):
        self._serial += 1
        reply, self._reply = self._reply, None
        if reply is not None:
            reply.abort()
        self._busy = False

    @Slot()
    def close(self):
        self._closed = True
        self._cancel()
        for job in self._jobs.values():
            job.signals.done.disconnect(self._parsed)
        self._jobs.clear()

    @Slot(int)
    def select(self, index):
        if index < -1 or index >= len(self._custom):
            return
        self._cancel()
        self._current, self._caps, self._layers = index, None, []
        self._read_state, self._key_error = "", ""
        source = self._source()
        if source and source.get("layer"):
            self._layers = [{"key": source["layer"], "name": source["layer"]}]
        self._refresh()

    @Slot()
    def add(self):
        self._custom.append({"key": tiles.new_key(), "name": _("New source"), "kind": "xyz", "url": "",
            "attribution": "", "licence": "", "licence_url": "", "imagery": "photo", "min_zoom": 0,
            "max_zoom": 19, "bbox": [], "matrices": [], "added": date.today().isoformat()})
        self.select(len(self._custom)-1)

    @Slot()
    def remove(self):
        source = self._source()
        if not source:
            return
        try:
            self._store.forget(source["key"], service=KEYS)
        except keys.KeyringMissing:
            # Without a keyring this editor could never store a credential.
            pass
        self._known.pop(source["key"], None)
        self._custom.pop(self._current)
        self.select(min(self._current, len(self._custom)-1))

    @Slot(str, "QVariant")
    def updateField(self, field, value):
        source = self._source()
        if source is None:
            return
        allowed = {"name", "kind", "url", "attribution", "licence", "licence_url", "imagery", "max_zoom"}
        if field not in allowed:
            return
        if field == "max_zoom":
            try:
                value = max(int(source.get("min_zoom", 0)), min(tiles.MAX_ZOOM, max(1, int(value))))
            except (ValueError, TypeError):
                return
        else:
            # QML binds the editor back to this draft on every keystroke. A
            # trailing space is the next word's separator until editing ends.
            value = str(value) if field in {"name", "attribution", "licence", "licence_url"} else str(value).strip()
        if field == "kind" and value not in {"xyz", "wms", "wmts"}:
            return
        if field == "imagery" and value not in {"photo", "map"}:
            return
        if field in {"kind", "url"}:
            self._cancel()
            self._caps, self._layers, self._read_state = None, [], ""
            if field == "kind" and value != source.get("kind"):
                source.update(layer="", matrix_set="", matrices=[], capabilities="")
            if field == "url" and source.get("kind") != "xyz":
                source.update(capabilities=value, url=capabilities.base_url(value) if value else "",
                              layer="", matrix_set="", matrices=[])
            else:
                source[field] = value
        else:
            source[field] = value
        self._key_error = ""
        self._refresh()

    @Slot(str)
    def setDefault(self, key):
        if key in [row["key"] for row in self._defaults]:
            self._default = key
            self.changed.emit()

    @Slot(str)
    def setKey(self, value):
        source = self._source()
        if source is None or not self._needs_key or not value.strip():
            return
        try:
            self._store.put(source["key"], value, service=KEYS)
        except keys.KeyringMissing:
            self._key_error = _("No keyring on this system: a source that needs a key cannot be used.")
        else:
            self._key_error = ""
            self._known[source["key"]] = _("Key in the system's keyring: {key}").format(key=keys.masked(value.strip()))
        self._refresh()

    @Slot()
    def readCapabilities(self):
        source = self._source()
        if source is None:
            return
        address = source.get("capabilities") or source.get("url", "")
        if not address:
            self._read_state = _("Paste the address of the service first.")
        elif not self.network():
            self._read_state = _("The map servers are switched off in Settings > Privacy.")
        elif source.get("kind") not in {"wms", "wmts"}:
            return
        else:
            self._cancel()
            request = QNetworkRequest(QUrl(capabilities.capabilities_url(address, source["kind"])))
            request.setRawHeader(b"User-Agent", USER_AGENT)
            request.setTransferTimeout(30000)
            self._busy, self._read_state = True, _("Reading…")
            reply = self._reply = self.net.get(request)
            serial = self._serial
            self._downloads[serial] = bytearray()
            reply.readyRead.connect(lambda: self._chunk(reply, serial))
            reply.finished.connect(lambda: self._finished(reply, serial))
        self.changed.emit()

    def _chunk(self, reply, serial):
        data = bytes(reply.readAll())
        if serial not in self._downloads:
            return
        self._downloads[serial].extend(data)
        if len(self._downloads[serial]) > capabilities.MAX_BYTES:
            self._oversize.add(serial)
            self._downloads.pop(serial, None)
            reply.abort()

    def _finished(self, reply, serial):
        if reply.isOpen():
            self._chunk(reply, serial)
        data = bytes(self._downloads.pop(serial, b""))
        oversized = serial in self._oversize
        self._oversize.discard(serial)
        ok, message = reply.error() == QNetworkReply.NetworkError.NoError, reply.errorString()
        reply.deleteLater()
        if self._closed or serial != self._serial:
            return
        self._reply = None
        if oversized or not self.network():
            self._busy = False
            self._read_state = (_("Not readable: {why}").format(
                why=f"the document is larger than {capabilities.MAX_BYTES // 1_000_000} MB") if oversized else
                _("The map servers are switched off in Settings > Privacy."))
            self.changed.emit()
            return
        if not ok:
            self._busy = False
            self.show_capabilities(None, message)
            return
        job = _Read(serial, data)
        self._jobs[serial] = job
        job.signals.done.connect(self._parsed)
        QThreadPool.globalInstance().start(job)

    @Slot(int, object, str)
    def _parsed(self, serial, caps, error):
        self._jobs.pop(serial, None)
        if self._closed or serial != self._serial:
            return
        self._busy = False
        if not self.network():
            self._read_state = _("The map servers are switched off in Settings > Privacy.")
            self.changed.emit()
            return
        if error:
            self._read_state = _("Not readable: {why}").format(why=error)
            self.changed.emit()
        else:
            self._show_caps(caps)

    def show_capabilities(self, data, message=""):
        """Feed recorded documents through the same result path without networking."""
        if self._source() is None:
            return
        if data is None:
            self._read_state = _("The server did not answer: {error}").format(error=message)
        else:
            try:
                caps = capabilities.read(data)
            except ValueError as error:
                self._read_state = _("Not readable: {why}").format(why=error)
            else:
                self._show_caps(caps)
                return
        self.changed.emit()

    def _show_caps(self, caps):
        self._caps = caps
        usable = [layer for layer in caps.layers if not layer.problem(caps.kind)]
        self._layers = [{"key": layer.name, "name": f"{layer.title} ({layer.name})"
                        if layer.title != layer.name else layer.name} for layer in usable]
        skipped = len(caps.layers)-len(usable)
        self._read_state = (_("{title}: {n} layers usable on the plan, {m} not (another grid or system).")
                            if skipped else _("{title}: {n} layers usable on the plan.")).format(
                                title=caps.title or caps.kind.upper(), n=len(usable), m=skipped)
        source = self._source()
        source["kind"] = caps.kind
        if usable:
            previous = source.get("layer")
            self.chooseLayer(previous if previous in [layer.name for layer in usable] else usable[0].name)
        else:
            source.update(layer="", matrices=[], matrix_set="")
            self._refresh()

    @Slot(str)
    def chooseLayer(self, name):
        source = self._source()
        layer = self._caps.layer(name) if self._caps else None
        if source is None or layer is None or layer.problem(self._caps.kind):
            return
        typed = {key: source.get(key, "") for key in ("name", "attribution", "licence", "licence_url")}
        if typed["name"] == _("New source"):
            typed["name"] = ""
        new = capabilities.source_dict(self._caps, layer, source["key"], typed["name"],
            source.get("capabilities") or source.get("url", ""), source.get("added") or date.today().isoformat())
        new.update({key: value for key, value in typed.items() if value})
        new["imagery"] = source.get("imagery", "photo")
        self._custom[self._current] = new
        self._refresh()

    def choice(self):
        sources = deepcopy(self._custom)
        for source in sources:
            for field in ("name", "attribution", "licence", "licence_url"):
                if isinstance(source.get(field), str):
                    source[field] = source[field].strip()
        return self._default, sources

    @Slot()
    def apply(self):
        self.applied.emit(*self.choice())

    defaultOptions = Property("QVariantList", lambda self: deepcopy(self._defaults), notify=changed)
    defaultChoice = Property(str, lambda self: self._default, notify=changed)
    siteSources = Property("QVariantList", lambda self: deepcopy(self._site_rows), notify=changed)
    allSources = Property("QVariantList", lambda self: deepcopy(self._all_rows), notify=changed)
    customRows = Property("QVariantList", lambda self: deepcopy(self._custom_rows), notify=changed)
    currentIndex = Property(int, lambda self: self._current, notify=changed)
    currentSource = Property("QVariantMap", lambda self: deepcopy(self._source() or {}), notify=changed)
    layers = Property("QVariantList", lambda self: deepcopy(self._layers), notify=changed)
    problems = Property(str, lambda self: self._problems, notify=changed)
    readState = Property(str, lambda self: self._read_state, notify=changed)
    keyState = Property(str, lambda self: self._key_state, notify=changed)
    needsKey = Property(bool, lambda self: self._needs_key, notify=changed)
    busy = Property(bool, lambda self: self._busy, notify=changed)

    @Property("QVariantMap", constant=True)
    def texts(self):
        return {"title": _("Background of the plan"), "start": _("Start from"),
                "site": _("At the site of the project"), "all": _("The program's sources"),
                "own": _("Your sources"), "new": _("New source"), "remove": _("Remove"),
                "name": _("Name"), "type": _("Type"), "address": _("Address"),
                "read": _("Read the capabilities"), "layer": _("Layer"), "attribution": _("Attribution"),
                "licence": _("Licence"), "licenceUrl": _("Licence address"), "imagery": _("It is"),
                "zoom": _("Highest zoom"), "photo": _("Photo"), "map": _("Map"),
                "key": _("Key"), "setKey": _("Set the key…"), "keyTitle": _("Key of the map source"),
                "keyHelp": _("The key the provider gave you (it goes to the system's keyring, never to a file):"),
                "apply": _("Apply"), "xyz": _("XYZ tiles (an address with {z}, {x}, {y})"),
                "wms": _("WMS (from its capabilities)"), "wmts": _("WMTS (from its capabilities)"),
                "customHelp": _("An XYZ address is a template with {z}, {x} and {y} (or {-y}), and {key} where a key goes. For "
                    "a WMS or a WMTS paste the address of the service or of its capabilities and read them: the "
                    "layers usable on the plan are listed (a WMS in EPSG:3857 or in degrees, a WMTS on the Web "
                    "Mercator grid). The tiles are kept in the cache like the others; read the terms of the "
                    "source before using it in a report."),
                "automaticHelp": _("Automatic takes the best source for the site of each project: the open orthophoto of the "
                    "region or of the country where there is one, else Sentinel-2 at 10 m. A source chosen here "
                    "or in the plan's Background menu is used where it covers the site; elsewhere the automatic "
                    "one is. The attribution of the source in use is always on the plan, at the bottom right.")}
