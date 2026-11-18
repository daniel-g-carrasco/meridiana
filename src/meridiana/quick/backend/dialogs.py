"""Quick dialog drafts, original core services and cancellable workers."""

from __future__ import annotations

import copy
import html
import json
import datetime
import math
import re
import threading
from dataclasses import asdict
from pathlib import Path

from PySide6.QtGui import QKeySequence
from PySide6.QtCore import (
    QKeyCombination,
    Qt,
    QObject,
    Property,
    QRunnable,
    QThreadPool,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from ... import (
    canopies,
    config,
    geo,
    ifc_import,
    model,
    places,
    shortcuts,
    templates,
    updates,
)
from ...coordinates import CoordinateError, CoordinateReading
from ...i18n import _, number
from ...services import geocoding


class _Signals(QObject):
    done = Signal(int, object, str)


class _Job(QRunnable):
    def __init__(self, generation, function):
        super().__init__()
        self.generation, self.function = generation, function
        self.signals = _Signals()

    def run(self):
        try:
            value = self.function()
        except Exception as error:  # Every worker failure is displayed.
            self.signals.done.emit(self.generation, None, str(error))
        else:
            self.signals.done.emit(self.generation, value, "")


def field(key, label, kind="text", **options):
    return dict(key=key, label=label, kind=kind, **options)


def choice(key, label, values):
    return field(
        key, label, "choice", options=[{"value": k, "label": v} for k, v in values]
    )


def numeric(key, label, low, high, unit="", decimals=2):
    return field(
        key, label, "number", minimum=low, maximum=high, unit=unit, decimals=decimals
    )


class DialogsBackend(QObject):
    changed = Signal()
    fieldsChanged = Signal()
    created = Signal(dict)
    projectReady = Signal(object)
    placementRequested = Signal(str, object)
    modelPlaced = Signal()
    shortcutsChanged = Signal(dict)
    registryChanged = Signal()
    closed = Signal()
    commandRequested = Signal(str)
    installerReady = Signal(str)
    fieldHighlighted = Signal(str)

    @Slot(str)
    def highlightField(self, key):
        self.fieldHighlighted.emit(key)

    @property
    def choices(self):
        """The places a search looks in: ISTAT's municipalities, read when first wanted. Read at the start, they were
        most of the 0.43 s of DialogsBackend at every opening of the Quick (studio 41, 3.9)."""
        if self._choices is None:
            self._choices = list(places.municipalities())
        return self._choices

    @choices.setter
    def choices(self, value):
        self._choices = value

    def __init__(self, session, cfg=None, paths=None, parent=None):
        super().__init__(parent)
        from .dialogs_preview import register
        register()
        self.session, self.cfg, self.paths = session, cfg or config.Config(), paths
        self.registry = None
        self._kind, self._status, self._busy = "", "", False
        self._state, self._fields = {}, []
        self.candidate = None
        self._choices = None             # the municipalities, read at the first search (r24-fasi, studio 41 S8)
        self.local_places, self.online_places = [], []
        self.net = QNetworkAccessManager(self)
        self.net.setTransferTimeout(15000)
        self.throttle = geocoding.Throttle()
        self._generation, self._jobs, self._callbacks = 0, {}, {}
        self._signal_tokens = {}
        self._closed = False
        self._latest_job = None
        self._reply, self._ifc_reader, self._map = None, None, None
        self._ifc_found, self._ifc_plan, self._pv_project, self._pv_result = (
            None,
            None,
            None,
            None,
        )
        self._pending_import = None
        self._cancel_download = threading.Event()
        self.bindings = {}
        self._release, self._installer = None, None
        self._coordinate_error = ""
        self.open("new")

    @Property(str, notify=changed)
    def kind(self):
        return self._kind

    @Property(str, notify=changed)
    def status(self):
        return self._status

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property("QVariantMap", notify=changed)
    def state(self):
        return json.loads(json.dumps(self._state))

    @Property("QVariantList", notify=fieldsChanged)
    def fields(self):
        return self._fields

    @Property("QVariantMap", constant=True)
    def labels(self):
        return {
            k: _(v)
            for k, v in {
                "cancel": "Cancel",
                "accept": "OK",
                "place": "Place it on the plan",
                "addModel": "Add the model",
                "close": "Close",
                "ifcLead": "An IFC model (.ifc, .ifczip), or a Revit file (.rvt) to see which version it is and what to do with it.",
                "whereTitle": "Where it goes",
                "chooseIfc": "Choose the exported IFC…",
                "bimFilter": "BIM (*.ifc *.IFC *.ifczip *.ifcZIP *.rvt *.RVT)",
                "importProject": "Create the project",
                "search": "Search",
                "create": "Create and draw",
                "client": "New client",
                "job": "New job",
                "saveClient": "Save client",
                "saveJob": "Save job",
                "import": "Import registry…",
                "export": "Export registry…",
                "apply": "Apply import",
                "folder": "Link folder…",
                "chooseFile": "Choose the file…",
                "read": "Read the variants",
                "use": "Use",
                "none": "No key",
                "default": "Default",
                "allDefaults": "All defaults",
                "keys": "Keys",
                "newKeys": "New keys",
                "keyboardNote": "Single letters work everywhere except while writing in a field. On a laptop the F keys may need Fn (or Fn+Esc to lock it).",
                "command": "Command",
                "defaults": "Default",
                "download": "Download and install",
                "release": "Open the release page",
                "later": "Later",
                "optional": "Optional project data",
                "latitude": "Latitude",
                "longitude": "Longitude",
                "newLead": "Start from the place. Type an address, a municipality, coordinates or a map link; then check the point on the map.",
                "queryHint": "Address, municipality, coordinates or link",
                "coordinatesHelp": "Latitude, longitude: 45.5226, 9.0300. Paste coordinates or a full map link above, or paste both coordinates into Latitude.",
                "privacy": "Suggestions while you type come only from ISTAT and your recent projects. OpenStreetMap Nominatim is asked only by Search.",
                "reservedExport": "The registry contains reserved jobs. The JSON file is not encrypted and includes their names, contacts, project paths and folder paths. Write it only where these data may be stored.",
                "confirmExport": "Export reserved jobs",
                "zoomIn": "Zoom in",
                "zoomOut": "Zoom out",
                "shortcutsSearch": "Search a command or a key",
                "clientName": "Client name",
                "jobName": "Job name",
                "jobCode": "Job code",
                "reserved": "Reserved job",
                "clientLabel": "Client",
                "parkingSpaces": "Parking spaces",
                "structure": "Structure",
            }.items()
        }

    def set_registry(self, registry):
        self.registry = registry
        if self._kind:
            self.refreshRegistry("")

    @Slot(str)
    def open(self, kind):
        kind = {
            "import_ifc": "ifc",
            "import_pvsyst": "pvsyst",
            "new_project": "new",
        }.get(kind, kind)
        self.cancel(emit=False)
        self.blockSignals(True)
        self._kind, self._status = kind, ""
        self._state = {
            "valid": False,
            "title": "",
            "ring": [],
            "faces": [],
            "structure": [],
            "optional": False,
            "localPlaces": [],
            "onlinePlaces": [],
            "clients": [],
            "jobs": [],
            "folders": [],
            "summary": [],
            "variants": [],
            "selectedVariants": [],
            "progress": 0.0,
            "sides": [],
            "canExport": False,
            "canApplyImport": False,
            "fileName": "",
            "selectedJob": "",
            "shortcuts": [],
            "hasInstaller": False,
            "releaseUrl": "",
            "releaseNotes": "",
            "note": "",
        }
        self._fields = []
        self.candidate = None
        self._coordinate_error = ""
        if kind in ("new", "site"):
            self._state.update(
                title=_("New project") if kind == "new" else _("Find the site"),
                query="",
                latitude="",
                longitude="",
                address="",
                name="",
                reserved=False,
                maps_consent=False,
                client_id="",
                job_id="",
                networkLocked=False,
                tilesAllowed=False,
            )
            self._fields = [
                field("name", _("Project name")),
                choice("client_id", _("Client"), []),
                choice("job_id", _("Job"), []),
                field("reserved", _("Reserved project"), "bool"),
                field(
                    "maps_consent", _("Allow online map tiles for this project"), "bool"
                ),
                field("distributor", _("Distributor")),
                field("pod", "POD"),
                numeric("voltage_v", _("Supply voltage"), 0, 1e6, "V", 0),
                choice(
                    "phases",
                    _("Phases"),
                    [
                        ("", _("not stated")),
                        ("1", _("Single phase")),
                        ("3", _("Three phase")),
                    ],
                ),
                choice(
                    "level",
                    _("Connection level"),
                    [(v, v or _("not stated")) for v in ("", "BT", "MT", "AT")],
                ),
                choice(
                    "connection",
                    _("Connection"),
                    [
                        ("", _("not stated")),
                        ("existing", _("Existing connection")),
                        ("new", _("New connection")),
                        ("modification", _("Modification of the connection")),
                    ],
                ),
                numeric(
                    "available_kw", _("Available or contracted power"), 0, 1e9, "kW", 1
                ),
                numeric(
                    "requested_kw",
                    _("Power requested for the new plant"),
                    0,
                    1e9,
                    "kW",
                    1,
                ),
                field("practice_code", _("Connection practice code")),
            ]
            self._state.update(asdict(model.Network()))
            if kind == "site":
                site = self.session.project.site
                self._state.update(
                    query=site.address,
                    reserved=self.session.project.reserved,
                    maps_consent=bool(
                        self.session.project.network_consent.get("tiles")
                    ),
                )
                self._take(CoordinateReading(site.lat, site.lon, "place"), site.address)
            elif self._map is not None:
                self._map.reset()
            self.refreshRegistry("")
        elif kind == "canopy":
            self._state.update(asdict(canopies.Spec()), title=_("Parking canopy"))
            self._fields = [
                numeric("stalls", _("Spaces per row"), 1, 100, decimals=0),
                choice(
                    "rows",
                    _("Rows"),
                    [(1, _("One row, one slope")), (2, _("Two rows, back to back"))],
                ),
                numeric("bay_width", _("Width of a space"), 0.5, 20, "m"),
                numeric("depth", _("Depth of a space"), 1, 50, "m"),
                numeric("clearance", _("Clear height"), 0.1, 100, "m"),
                numeric("tilt", _("Slope"), 0, 60, "°", 1),
                choice(
                    "pillars",
                    _("Columns"),
                    [
                        ("cantilever", _("Cantilever, one line")),
                        ("two_rows", _("Two lines")),
                    ],
                ),
                numeric("columns", _("Columns per line"), 0, 200, decimals=0),
                numeric("turn", _("Turn"), -180, 180, "°", 1),
            ]
            self._state["note"] = _(
                "Draws the structure only: columns, beams and the roof. The modules are laid on it afterwards, in Plant › On a canopy. Indicative sizes, not a structural design."
            )
            self._geometry()
        elif kind == "canopy-layout":
            found = canopies.canopies(self.session.project)
            self._state.update(
                title=_("Modules on a canopy"),
                bid=found[0].id if found else "",
                portrait=True,
                gap=0.02,
                overhang=0.0,
                edge=0.1,
                valid=bool(found),
            )
            self._fields = [
                choice("bid", _("Canopy"), [(b.id, b.name) for b in found]),
                choice(
                    "portrait",
                    _("Modules"),
                    [(True, _("Along the slope")), (False, _("Across the slope"))],
                ),
                numeric("gap", _("Gap between modules"), 0, 0.5, "m"),
                numeric("overhang", _("Beyond the structure"), 0, 2, "m"),
                numeric("edge", _("Free edge"), 0, 2, "m"),
            ]
            if not found:
                self._status = _(
                    "There is no canopy yet: place one in Modelling with «Parking canopy…»."
                )
        elif kind == "template":
            self._state.update(title=_("Building from a template"), shape="L", turn=0.0)
            self._state["note"] = _("The sides can be changed afterwards one by one, in the Sides group of the building.")
            self._template_fields("L")
        elif kind == "shortcuts":
            self._state.update(title=_("Keyboard shortcuts"), valid=True)
            self.bindings = shortcuts.bindings(self.cfg.shortcuts)
            self.filterShortcuts("")
        elif kind == "registry":
            self._state.update(title=_("Clients and jobs"))
            self.refreshRegistry("")
        elif kind in ("ifc", "pvsyst"):
            self._state["title"] = (
                _("Import an IFC model")
                if kind == "ifc"
                else _("Import a PVsyst project")
            )
        elif kind == "about":
            from meridiana import __version__
            self._state.update(title=_("About Meridiana"), note=_(
                "<b>Meridiana</b> {version}<br>Photovoltaic design: map, building model, sun path, module layout and "
                "Italian standards.<br><br>GPL-3.0-or-later. Qt for Python (LGPL), Qt Quick 3D (GPL), shapely (BSD), "
                "numpy (BSD). Backgrounds: the map sources of Settings > Maps, each named on the plan with its "
                "attribution (among them the national orthophoto of the Geoportale Nazionale, MASE, and © OpenStreetMap "
                "contributors); the outlines of their areas from Natural Earth (public domain).").format(version=__version__))
        elif kind == "report_bug":
            self._state.update(title=_("Report a problem"))
        elif kind == "update":
            from meridiana import __version__
            self._state["title"] = _("Update")
            self._state['currentVersion'] = _("You are using version {version}.").format(version=__version__)
        else:
            self._status = _("Unknown command")
        self.blockSignals(False)
        self.fieldsChanged.emit()
        self.changed.emit()
        if kind == "new" and self.cfg.recent:
            self._start(
                lambda: places.recent(list(self.cfg.recent)), self._recent_places
            )

    def _recent_places(self, rows):
        self.choices = [*rows, *places.municipalities()]
        self.local_places = places.search(self._state.get("query", ""), self.choices)
        self._state["localPlaces"] = [
            dict(label=p.display, lat=p.lat, lon=p.lon) for p in self.local_places
        ]

    @staticmethod
    def _coordinate_shaped(text):
        return bool(
            re.search(
                r"°|º|https?://|^\s*(?:EPSG:|UTM\b|Gauss|GB\s|\d{1,2}[NSC-HJ-NP-X]\s)",
                text,
                re.IGNORECASE,
            )
            or re.fullmatch(r"[\s\d.,;+\-]+", text)
        )

    @Slot()
    def cancel(self, emit=True):
        self._generation += 1
        self._cancel_download.set()
        if self._reply is not None:
            self._reply.abort()
            self._reply = None
        if self._ifc_reader is not None:
            self._ifc_reader.cancel()
            self._ifc_reader = None
        if self._map is not None:
            self._map.pause()
        self._busy = False
        self._pending_import = None
        self._ifc_found = self._ifc_plan = self._pv_project = self._pv_result = None
        self._kind = ""
        if emit:
            self.changed.emit()
            self.closed.emit()

    @Slot(str, "QVariant")
    def setValue(self, key, value):
        if hasattr(value, "toVariant"):
            value = value.toVariant()
        descriptor = next((f for f in self._fields if f["key"] == key), None)
        if descriptor and descriptor["kind"] == "number":
            try:
                value = float(value)
                if (
                    not math.isfinite(value)
                    or not descriptor["minimum"] <= value <= descriptor["maximum"]
                ):
                    raise ValueError(
                        _("Between {low} and {high}").format(
                            low=number(descriptor["minimum"]),
                            high=number(descriptor["maximum"]),
                        )
                    )
            except (ValueError, TypeError) as error:
                self._status = str(error)
                self.changed.emit()
                return
        self._state[key] = value
        self._status = ""
        if key == "query":
            self.local_places = places.search(str(value), self.choices)
            self._state["localPlaces"] = [
                dict(label=p.display, lat=p.lat, lon=p.lon) for p in self.local_places
            ]
            try:
                self._take(geo.read_coordinates(str(value)), str(value))
            except CoordinateError as error:
                self._coordinate_error = str(error)
                if self._coordinate_shaped(str(value)):
                    self._status = str(error)
                self.candidate = None
                self._state["valid"] = False
                self._state.update(latitude="", longitude="")
                self._privacy()
                if self._map is not None:
                    self._map.reset()
        elif key in ("latitude", "longitude"):
            try:
                try:
                    p = geo.read_coordinates(str(value)) if key == "latitude" else None
                except CoordinateError:
                    p = None
                if p is None:
                    p = geo.read_coordinates(
                        f"{self._state['latitude']};{self._state['longitude']}"
                    )
                self._take(p, f"{p.lat:.8f}, {p.lon:.8f}")
            except CoordinateError as error:
                self.candidate = None
                self._state["valid"] = False
                self._status = str(error) if self._state["latitude"] != "" and self._state["longitude"] != "" else ""
                self._privacy()
                if self._map is not None:
                    self._map.reset()
        elif key == "client_id":
            self._state["job_id"] = ""
            self.refreshRegistry("")
        elif key in ("job_id", "reserved", "maps_consent"):
            self._privacy()
        elif self._kind == "template" and key == "shape":
            self._template_fields(value)
        elif self._kind in ("template", "canopy"):
            self._geometry()
        elif self._kind == "ifc" and key in ("how", "north", "solids", "solidKinds", "zone", "zoneBox", "storeys",
                                             "shade"):
            if key == "zoneBox":
                self._state["zone"] = "box" if value else "all"
            self._plan_ifc()
        self._privacy()
        self.changed.emit()

    def _privacy(self):
        if self._kind not in ("new", "site"):
            return
        job = (
            self.registry.job(self._state.get("job_id", ""))
            if self.registry and self._state.get("job_id")
            else None
        )
        locked = bool(job and job["reserved"]) or (
            self._kind == "site" and self.session.project.reserved
        )
        if locked:
            self._state["reserved"] = True
        self._state["networkLocked"] = locked
        self._state["tilesAllowed"] = bool(
            self.candidate
            and self.cfg.network_tiles
            and (not self._state["reserved"] or self._state["maps_consent"])
        )
        if self._state["reserved"] and self._reply is not None:
            self._reply.abort()
            self._reply = None
        if self._map is not None:
            self._map.set_allowed(self._state["tilesAllowed"])

    def _take(self, point, address):
        self.candidate = point
        self._coordinate_error = ""
        self._state.update(
            latitude=point.lat, longitude=point.lon, address=address.strip(), valid=True
        )
        self._privacy()
        if self._map is not None:
            self._map.set_point(point.lat, point.lon)

    @Slot(float, float)
    def pickLocation(self, lat, lon):
        if (
            math.isfinite(lat)
            and math.isfinite(lon)
            and -90 <= lat <= 90
            and -180 <= lon <= 180
        ):
            self._take(CoordinateReading(lat, lon, "map"), self._state.get("query", ""))
            self.changed.emit()

    @Slot(int, bool)
    def choosePlace(self, index, online=False):
        rows = self.online_places if online else self.local_places
        if 0 <= index < len(rows):
            p = rows[index]
            self._take(
                CoordinateReading(p.lat, p.lon, "place"),
                p.name if online else p.display,
            )
            self.changed.emit()

    @Slot()
    def search(self):
        if self.candidate and self.candidate.format != "place":
            return
        text = self._state.get("query", "").strip()
        if not text:
            self._status = _("Write a place first.")
        elif self._coordinate_error and self._coordinate_shaped(text):
            self._status = self._coordinate_error
        elif self._state.get("reserved"):
            self._status = _(
                "A reserved project never sends names or addresses. Use local suggestions, coordinates or a click on the offline map."
            )
        elif not self.cfg.network_geocoding:
            self._status = _(
                "The online search is off in Settings > Privacy. Local suggestions and coordinates still work."
            )
        elif not self.throttle.allow():
            self._status = _("One search a second, please (OpenStreetMap's rule).")
        else:
            from ... import __version__

            request = QNetworkRequest(QUrl(geocoding.search_url(text)))
            request.setRawHeader(
                b"User-Agent",
                f"Meridiana/{__version__} (+https://github.com/daniel-g-carrasco/meridiana)".encode(),
            )
            generation = self._generation
            reply = self.net.get(request)
            self._reply = reply

            def finished():
                data = bytes(reply.readAll())
                ok = reply.error() == QNetworkReply.NetworkError.NoError
                error = reply.errorString()
                if self._reply is reply:
                    self._reply = None
                reply.deleteLater()
                if generation == self._generation and not self._state.get("reserved"):
                    self.show_answer(data if ok else None, error)

            reply.finished.connect(finished)
            self._status = _("Searching with OpenStreetMap Nominatim…")
        self.changed.emit()

    def show_answer(self, data, message=""):
        self.online_places = []
        if data is None:
            self._status = _("The search did not answer: {error}").format(error=message)
        else:
            try:
                self.online_places = geocoding.places(data)
            except ValueError:
                self._status = _("The search answered something unreadable.")
            else:
                self._status = (
                    _("Nothing found. Try fewer words or type coordinates.")
                    if not self.online_places
                    else ""
                )
        self._state["onlinePlaces"] = [
            dict(label=p.name, lat=p.lat, lon=p.lon) for p in self.online_places
        ]
        self.changed.emit()

    def _template_fields(self, shape):
        if shape not in templates.KINDS:
            return
        self._state.update(templates.defaults(shape))
        self._fields = [choice("shape", _("Shape"), templates.kind_names().items())]
        self._fields += [
            numeric(
                k,
                templates.measure_names()[k],
                -1000 if k == "offset" else 0.1,
                1000,
                "m",
            )
            for k in templates.defaults(shape)
        ]
        self._fields += [
            numeric("turn", _("Turn (counter-clockwise)"), -180, 180, "°", 1)
        ]
        self.fieldsChanged.emit()
        self._geometry()

    def canopy_spec(self):
        values = {k: self._state[k] for k in asdict(canopies.Spec())}
        for k in ("stalls", "rows", "columns"):
            values[k] = int(values[k])
        spec = canopies.Spec(**values)
        spec.validate()
        return spec

    def _geometry(self):
        try:
            if self._kind == "canopy":
                spec = self.canopy_spec()
                b = canopies.building(spec, (0, 0))
                self._state["ring"] = b.footprint
                self._state["faces"] = [p.corners_3d() for p in b.pitches()]
                self._state["structure"] = canopies.structure(b)
                self._state["proposedColumns"] = _("{n}, proposed").format(n=canopies.proposed_columns(spec.stalls))
                self._state["summary"] = [
                    _("{n} spaces · {width} × {depth} m · {columns} columns").format(
                        n=spec.stalls * spec.rows,
                        width=number(spec.stalls * spec.bay_width),
                        depth=number(spec.rows * spec.depth),
                        columns=sum(
                            s["kind"] == "column" for s in self._state["structure"]
                        ),
                    )
                ]
            else:
                shape = self._state["shape"]
                self._state["ring"] = templates.footprint(
                    shape, {k: self._state[k] for k in templates.defaults(shape)}
                )
                ring = templates.placed(
                    self._state["ring"], (0, 0), self._state["turn"]
                )
                self._state["faces"] = [[[x, y, 6.0] for x, y in ring]]
                for i, (x, y) in enumerate(ring):
                    nx, ny = ring[(i + 1) % len(ring)]
                    self._state["faces"].append(
                        [[x, y, 0.0], [nx, ny, 0.0], [nx, ny, 6.0], [x, y, 6.0]]
                    )
                self._state["structure"] = []
            ring = self._state["ring"]
            self._state["sides"] = [
                dict(
                    key=str(i + 1),
                    label=f"{i + 1}: {number(math.dist(p, ring[(i + 1) % len(ring)]))} m",
                )
                for i, p in enumerate(ring)
            ]
            if self._kind == "canopy":
                self._state["sides"] += [
                    dict(
                        key="clearance",
                        label=f"{_('Clear height')}: {number(spec.clearance)} m",
                    ),
                    dict(key="tilt", label=f"{_('Slope')}: {number(spec.tilt)}°"),
                ]
            self._state["valid"] = True
        except (ValueError, TypeError) as error:
            self._status = str(error)
            self._state.update(valid=False, ring=[], faces=[], structure=[])

    @Slot(str, str, result=bool)
    def editMeasure(self, side, text):
        from ... import quantity
        from ...ui.template_dialog import side_measure

        try:
            value = quantity.parse(
                text,
                "angle" if side == "tilt" else "length",
                "°" if side == "tilt" else "m",
            )
            if self._kind == "template":
                shape = self._state["shape"]
                key, value = side_measure(
                    shape,
                    int(side),
                    value,
                    {k: self._state[k] for k in templates.defaults(shape)},
                )
            elif self._kind == "canopy":
                key, share = {
                    "1": ("bay_width", self._state["stalls"]),
                    "3": ("bay_width", self._state["stalls"]),
                    "2": ("depth", self._state["rows"]),
                    "4": ("depth", self._state["rows"]),
                    "clearance": ("clearance", 1),
                    "tilt": ("tilt", 1),
                }[side]
                value /= share
            else:
                return False
            spec = next(f for f in self._fields if f["key"] == key)
            if not spec["minimum"] <= value <= spec["maximum"]:
                raise ValueError(
                    _("Between {low} and {high}").format(
                        low=number(spec["minimum"]), high=number(spec["maximum"])
                    )
                )
            self.setValue(key, value)
            return True
        except (ValueError, KeyError) as error:
            self._status = str(error)
            self.changed.emit()
            return False

    @Slot(result=bool)
    def accept(self):
        if self._busy or not self._state.get("valid"):
            return False
        try:
            if self._kind == "new":
                if self.candidate is None:
                    return False
                job = (
                    self.registry.job(self._state["job_id"])
                    if self.registry and self._state["job_id"]
                    else None
                )
                consent = (
                    {"tiles": datetime.date.today().isoformat()}
                    if self._state["reserved"] and self._state["maps_consent"]
                    else {}
                )
                values = {k: self._state[k] for k in asdict(model.Network())}
                data = dict(
                    name=self._state["name"].strip(),
                    site=model.Site(
                        self.candidate.lat, self.candidate.lon, self._state["address"]
                    ),
                    reserved=self._state["reserved"],
                    network=model.Network(**values),
                    network_consent=consent,
                    client_id=job["client_id"] if job else self._state["client_id"],
                    job_id=self._state["job_id"],
                )
                self.created.emit(data)
            elif self._kind == "site":
                if self.candidate is None:
                    return False
                if self.session.project.buildings or self.session.project.subfields:
                    self._status = _(
                        "The site can be moved only before anything is drawn: the drawing is measured from it. Start a new project for another site."
                    )
                    self.changed.emit()
                    return False
                site = copy.copy(self.session.project.site)
                site.lat, site.lon, site.address = (
                    self.candidate.lat,
                    self.candidate.lon,
                    self._state["address"],
                )
                self.session.edit(
                    _("Find the site"), lambda p: setattr(p, "site", site)
                )
            elif self._kind == "canopy":
                self.placementRequested.emit("canopy", self.canopy_spec())
            elif self._kind == "template":
                self.placementRequested.emit(
                    "template",
                    {"ring": self._state["ring"], "turn": self._state["turn"]},
                )
            elif self._kind == "canopy-layout":
                values = {
                    k: self._state[k]
                    for k in ("bid", "portrait", "gap", "overhang", "edge")
                }
                self.session.edit(
                    _("Modules on a canopy"), lambda p: canopies.lay(p, **values)
                )
            elif self._kind == "ifc":
                if self._ifc_plan is None or ifc_import.problem(self._ifc_plan):
                    return False
                how = self._state["how"]
                if how not in ("site", "origin", "file") or self.session.project.buildings:
                    # R454: placed on the plan by the mouse or by coordinates, the buildings already drawn in view
                    place = ifc_import.place_of(self._ifc_found or {})
                    if self._state["north"] in ("map", "context") and (
                            self._state["north"] == "context" or place.north_map is not None):
                        place.north = self._state["north"]
                    self.placementRequested.emit("ifc", {
                        "plan": self._ifc_plan, "place": place, "follow": how == "hand",
                        "name": Path(self._state["fileName"]).stem})
                    added = None
                else:
                    added = []
                    self.session.edit(
                        _("Import an IFC model"),
                        lambda p: added.extend(ifc_import.apply(p, self._ifc_plan)),
                    )
                if added:
                    self.session.select("building", added[0])
                    self.modelPlaced.emit()
            elif self._kind == "pvsyst":
                if self._pv_result is None:
                    return False
                self.projectReady.emit(self._pv_result[0])
            elif self._kind == "shortcuts":
                candidate = copy.deepcopy(self.cfg)
                candidate.shortcuts = shortcuts.differences(self.bindings)
                if self.paths is not None:
                    config.save(candidate, Path(self.paths.config_file))
                self.cfg.shortcuts = candidate.shortcuts
                self.shortcutsChanged.emit(self.cfg.shortcuts)
            else:
                return False
        except (ValueError, OSError, TypeError) as error:
            self._status = str(error)
            self.changed.emit()
            return False
        self.closed.emit()
        return True

    def _start(self, function, callback):
        self._busy = True
        job = _Job(self._generation, function)
        token = id(job)
        self._latest_job = token
        self._jobs[token] = job
        self._callbacks[token] = callback
        self._signal_tokens[id(job.signals)] = token
        job.signals.done.connect(self._job_result)
        QThreadPool.globalInstance().start(job)
        self.changed.emit()

    @Slot(int, object, str)
    def _job_result(self, generation, value, error):
        token = self._signal_tokens.pop(id(self.sender()), None)
        if token is not None:
            self._job_done(token, generation, value, error)

    def close(self):
        """Stop delivery before the host destroys QML; no user cancel signal."""
        if self._closed:
            return
        self._closed = True
        self.cancel(emit=False)
        for job in self._jobs.values():
            job.signals.done.disconnect(self._job_result)
        self._callbacks.clear()
        self._signal_tokens.clear()

    def _job_done(self, token, generation, value, error):
        self._jobs.pop(token, None)
        callback = self._callbacks.pop(token, None)
        if generation != self._generation or token != self._latest_job:
            return
        self._busy = False
        if error:
            self._status = error
        elif callback:
            callback(value)
        self.changed.emit()

    @Slot(str)
    def readFile(self, path):
        local = QUrl(path).toLocalFile() if path.startswith("file:") else path
        if not local:
            return
        self._state["fileName"] = local
        self._state["valid"] = False
        if self._kind == "ifc" and local.lower().endswith((".rvt", ".rfa", ".rte")):
            self._read_rvt(local)
            return
        if self._kind == "ifc":
            self._state.update(rvtInfo=None, ifcRead=False, progress=0, ifcStage=_("Opening the file…"))
            self._status = ""
        if self._kind == "pvsyst":
            from ...pvsyst import project as pvproject

            self._start(lambda: pvproject.read_project(Path(local)), self._pvsyst_head)
        elif self._kind == "ifc":
            from ...ui.ifc_import import IfcReading

            self._ifc_reader = IfcReading(local, parent=self)
            generation = self._generation
            self._ifc_reader.done.connect(
                lambda found: self._ifc_done(generation, found)
            )
            self._ifc_reader.failed.connect(
                lambda error: self._ifc_failed(generation, error)
            )
            self._ifc_reader.progress.connect(self._progress_ifc)
            self._busy = True
            self._ifc_reader.start()
            self.changed.emit()

    def _read_rvt(self, local):
        """A Revit file: its version and preview, and what to do; its geometry cannot be read (study 32)."""
        import base64

        from ... import rvt_read
        self._state.update(ifcRead=False, rvtInfo=None)
        self._status = ""
        try:
            info = rvt_read.read(local)
        except rvt_read.RvtError as error:
            self._status = _("This is not a Revit file Meridiana can read: {why}").format(why=error)
            self.changed.emit()
            return
        years = rvt_read.installed_revit()
        usable = rvt_read.can_open(info["format"], years)
        version = info["format"] or _("unknown")
        lines = [_("Meridiana cannot read the geometry of a Revit file: its format is Autodesk's and is not published. "
                   "It needs an IFC exported from Revit.")]
        if usable:
            lines.append(_("On this PC, Revit {year} can open it (it upgrades a copy): File > Export > IFC, IFC 2x3 or 4, "
                           "with the option to export only the elements visible in a 3D view without furniture; then "
                           "choose that IFC here.").format(year=usable))
        elif years:
            lines.append(_("Revit {have} on this PC cannot open it: Revit never opens what a later version saved. Ask for "
                           "an IFC from whoever has Revit {need} or later.").format(
                               have=", ".join(str(y) for y in years), need=version))
        else:
            lines.append(_("Ask for an IFC from whoever has Revit {need} or later: most architects export one in a few "
                           "minutes.").format(need=version))
        if info["central"]:
            lines.append(_("It is a file of a shared model: work on a detached copy, never on the central model."))
        self._state["rvtInfo"] = dict(
            headline=_("Revit {version} file, {mb} MB").format(version=version, mb=number(info["size"] / 1e6, 0)),
            lines=lines, preview=("data:image/png;base64," + base64.b64encode(info["preview"]).decode("ascii"))
            if info["preview"] else "")
        self.changed.emit()

    def _progress_ifc(self, fraction, what):
        self._state["progress"] = fraction
        stages = {"open": _("Opening the file…"), "structure": _("Reading the storeys and the buildings…"),
                  "roofs": _("Reading the roofs…"), "tessellate": _("Making the shapes of the complex elements…"),
                  "planes": _("Finding the roof planes…"), "terraces": _("Looking for slabs under the open sky…"),
                  "obstacles": _("Looking for what stands on the roofs…"), "done": _("Done."),
                  "again": _("IfcOpenShell stopped on this file: reading again, the simple shapes only…"),
                  "scan": _("Reading the file, in several processes at once…"),
                  "solids": _("Making the solids of the elements…"),
                  "context": _("Preparing the model's true geometry for the 3D…"),
                  "scan_failed": _("The fast reading stopped: reading with IfcOpenShell…")}
        self._state["ifcStage"] = stages.get(what, what)
        self.changed.emit()

    def _ifc_failed(self, generation, error):
        if generation == self._generation:
            self._busy = False
            self._status = error
            self.changed.emit()

    def _ifc_done(self, generation, found):
        if generation != self._generation:
            return
        self._busy = False
        self._ifc_found = found
        context = found.get('context') if isinstance(found, dict) else None
        if isinstance(context, dict) and context.get('mesh'):
            from .scene_context import preload
            preload(str(context['mesh']))       # R548: ready in memory when the import is accepted
        place = ifc_import.place_of(found)
        project = self.session.project
        self._state['ifcFile'] = Path(self._state['fileName']).name
        seconds = found.get('read_seconds') or (found.get('times') or {}).get('total') or 0
        self._state['fileDescription'] = _("{schema}, from {app}; read in {s} s.").format(
            schema=found.get('schema', '?'), app=found.get('application') or _('an unknown program'),
            s=number(float(seconds), 1))
        self._state.update(
            how=ifc_import.default_how(place, project),
            north="map" if place.disagree() else "",
            ifcRead=True, rvtInfo=None,
        )
        site = project.site
        here = (number(site.lat, 4), number(site.lon, 4))
        offered = ifc_import.offers(place, project)
        source = (_("its map conversion ({crs})").format(crs=place.crs or "?") if place.trust == "map"
                  else _("its site «{name}»").format(name=place.site_name))
        km = ifc_import.distance_km(place, site) or 0.0
        choices = [("hand", _("With the mouse on the plan: the model follows the pointer and takes the corners of the "
                              "buildings drawn, a click lays it (C: by coordinates)")),
                   ("origin", _("At the middle of the plan: the project stays at {lat}, {lon}").format(lat=here[0], lon=here[1]))]
        if "file" in offered:
            choices.append(("file", _("Where the file says, by {source}: {km} km from the project's site").format(
                source=source, km=number(km, 2 if km < 10 else 0))))
        if "site" in offered:
            choices.append(("site", _("Move the project's site to the file's place ({lat}, {lon}): {km} km away, sun and "
                                      "climate change").format(lat=number(place.lat, 4), lon=number(place.lon, 4),
                                                               km=number(km, 2 if km < 10 else 0))))
        notes = [_("On the plan R or Shift+wheel turns it, C gives its coordinates, Esc gives the import up; afterwards "
                   "M and R move and turn it, Ctrl+Z takes the whole import back.")]
        if place.trust == "default":
            notes.insert(0, _("The file's site ({name}, {lat}, {lon}) is {km} km from the project and looks like a template's: "
                              "not proposed.").format(name=f"«{place.site_name}»" if place.site_name else _("no name"),
                                                      lat=number(place.lat, 4), lon=number(place.lon, 4),
                                                      km=number(km, 0)))
        elif place.trust == "none":
            notes.insert(0, _("The file does not say where it is."))
        self._state["ifcPlaceNote"] = " ".join(notes)
        self._fields = [choice("how", _("Where the buildings go"), choices)]
        if found.get("solids"):
            # R400: how much of the model comes in: the solids by group, by element or none; which; where
            self._state.update(solids=ifc_import.default_solids(found), solidKinds="all", zone="all", zoneBox=None)
            self._fields += [
                choice("solids", _("The model's solids, as outlines with their heights"), [
                    ("groups", _("One body for each group of the model (an assembly, a skid): the lightest")),
                    ("elements", _("One body for each element: finer, many bodies")),
                    ("none", _("None: only the roofs and what stands on them"))]),
                choice("solidKinds", _("Which"), [
                    ("all", _("Everything")), ("building", _("The building: walls, slabs, roofs, structure")),
                    ("plant", _("The installations and the machines: what is not the building"))]),
                choice("zone", _("Where"), [
                    ("all", _("The whole model")),
                    ("box", _("Only inside the rectangle drawn on the preview (drag on it)"))])]
        names = ifc_import.storeys_of(found)
        self._state["storeys"] = list(names)
        if len(names) > 1:
            # r22-ifc: the storeys to take, all of them at first (the roofs, the solids, the 3D, the shadows)
            self._fields.append(field("storeys", _("Storeys"), "checks", options=[
                {"value": n, "label": n or _("On no storey")} for n in names]))
        self._state["shade"] = "off"
        if (found.get("context") or {}).get("mesh"):
            # r22-ifc: the model's true shapes as the calculation's shadows (ifc_shade), off unless chosen
            self._fields.append(choice("shade", _("The shapes of the model cast shadows on the modules"), [
                ("off", _("No: the bodies cast them, as outlines with their heights")),
                ("20", _("Yes, what stands above the modules within 20 m of them")),
                ("50", _("Yes, what stands above the modules within 50 m of them")),
                ("all", _("Yes, the whole model: the slowest calculation"))]))
        if place.disagree():
            self._fields.append(
                choice(
                    "north",
                    _("Where north is"),
                    [
                        ("map", _("By the map conversion: {deg}° from the model's Y axis").format(deg=number(place.north_map, 1))),
                        ("context", _("By the TrueNorth: {deg}°").format(deg=number(place.north_context, 1))),
                    ],
                )
            )
        self.fieldsChanged.emit()
        self._plan_ifc()

    def _zone_ring(self):
        x0, y0, x1, y1 = (float(v) for v in self._state["zoneBox"])
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

    def _plan_ifc(self):
        if self._ifc_found is None:
            return
        found, project = (
            # R400: the solids are only read by the plan: shared, not copied (a second of the window for 13 000)
            {k: (v if k == "solids" else copy.deepcopy(v)) for k, v in self._ifc_found.items()},
            copy.deepcopy(self.session.project),
        )
        how, north = self._state["how"], self._state["north"] or None
        filename = self._state["fileName"]
        # R400: the solids chosen, the kinds and the zone drawn on the preview
        box = self._state.get("zoneBox") if self._state.get("zone") == "box" else None
        options = dict(solids=self._state.get("solids") or None, kinds=self._state.get("solidKinds") or "all",
                       zone=tuple(float(v) for v in box) if box and len(box) == 4 else None,
                       shade=self._state.get("shade") or "off")
        names = ifc_import.storeys_of(self._ifc_found)
        chosen = [n for n in names if n in set(self._state.get("storeys") or [])]
        if len(names) > 1 and len(chosen) < len(names):
            options["storeys"] = chosen
        self._state["valid"] = False
        self._start(
            lambda: ifc_import.plan(
                found,
                project,
                how,
                north,
                name=Path(filename).stem,
                source_name=filename,
                **options,
            ),
            self._planned_ifc,
        )

    def _planned_ifc(self, plan):
        self._ifc_plan = plan
        self._state["ifcLists"] = [
            dict(title=title, items=list(items))
            for title, items in [
                (_("To check"), plan.approximated),
                (_("Left out"), plan.left_out),
            ]
            if items
        ]
        found = self._ifc_found or {}
        counts = found.get("counts") or {}
        kinds: dict = {}
        for b in plan.buildings:
            kinds[b.roof.type] = kinds.get(b.roof.type, 0) + 1
        names = {"flat": _("flat"), "mono": _("mono-pitch"), "gable": _("gable"), "hip": _("hip"), "free": _("free pitches")}
        top = max((b.ridge() for b in plan.buildings), default=0.0)
        facts = [dict(label=_("Bodies"), value=_("{n}: {list}, up to {m} m").format(
            n=len(plan.buildings), list=", ".join(f"{names.get(k, k)} {v}" for k, v in kinds.items()), m=number(top, 1)))]
        pitches = sum(len(b.pitches()) for b in plan.buildings)
        facts.append(dict(label=_("Roof planes"), value=str(pitches)))
        by_kind: dict = {}
        for e, _host in plan.exclusions:
            by_kind[e.kind] = by_kind.get(e.kind, 0) + 1
        facts.append(dict(label=_("On the roofs"), value=(", ".join(
            f"{model.exclusion_names().get(k, k)} {v}" for k, v in by_kind.items()) or _("nothing"))))
        if counts.get("under_roof"):
            facts.append(dict(label=_("Set aside"), value=_("{n} elements under the roofs (beams, walls): they cast no "
                                                            "shadow").format(n=counts["under_roof"])))
        if found.get("address"):
            facts.append(dict(label=_("Address"), value=" ".join(str(found["address"]).split())))
        listing = found.get("listing") or {}
        if listing:
            classes = sorted((listing.get("classes") or {}).items(), key=lambda kv: -kv[1]["elements"])
            facts.append(dict(label=_("In the file"), value=_(
                "{mb} MB, {entities} entities; {n} elements with a shape in {g} groups, {t} triangles").format(
                    mb=number(listing.get("size_mb") or 0, 0), entities=number(listing.get("entities") or 0, 0),
                    n=number(listing.get("elements") or 0, 0), g=number(listing.get("groups") or 0, 0),
                    t=number(listing.get("triangles") or 0, 0))
                + ("; " + ", ".join(f"{k[3:] if k.startswith('Ifc') else k} {number(v['elements'], 0)}"
                                    for k, v in classes[:4]) if classes else "")))
            if listing.get("instances"):
                facts.append(dict(label=_("Repeated"), value=_("{m} shapes used {n} times").format(
                    m=number(listing.get("maps") or 0, 0), n=number(listing["instances"], 0))))
            left = sum((listing.get("left_out") or {}).values())
            if left:
                facts.append(dict(label=_("Not read"), value=_("{n} items of a kind the fast reading does not make "
                                                               "({kinds})").format(
                    n=number(left, 0), kinds=", ".join(sorted(listing["left_out"])[:4]))))
        self._state["ifcFacts"] = facts
        self._state['ifcDrawing'] = (
            [dict(kind='roof', ring=p.ring) for b in plan.buildings for p in b.pitches()]
            + [dict(kind='building', ring=b.footprint) for b in plan.buildings]
            + [dict(kind='exclusion', ring=e.ring) for e, _h in plan.exclusions]
            + [dict(kind='support', ring=sf.ring) for sf, _h in plan.supports]
            + [dict(kind='left', ring=r) for r in plan.zone_rings]
            + ([dict(kind='zone', ring=self._zone_ring())] if self._state.get("zone") == "box"
               and self._state.get("zoneBox") else []))
        self._state["faces"] = [
            [[x, y, 0.0] for x, y in b.footprint] for b in plan.buildings
        ]
        self._status = ifc_import.problem(plan) or (
            "" if plan.buildings or plan.supports else _("Nothing to add.")
        )
        self._state["valid"] = not self._status

    def _pvsyst_head(self, project):
        self._pv_project = project
        self._state["variants"] = [
            {
                "label": f"{v.path.suffix[1:]} · {v.comment or '?'}",
                "index": i,
                "detail": ", ".join(
                    x for x in (v.system_kind, v.version, v.computed) if x
                ),
            }
            for i, v in enumerate(project.variants)
        ]
        self._state["selectedVariants"] = (
            list(range(len(project.variants))) if len(project.variants) <= 4 else [0]
        )
        if not project.variants:
            self._status = _("No variants found next to the project file.")

    @Slot(int, bool)
    def selectVariant(self, index, selected):
        self._pv_result = None
        self._state['valid'] = False
        self._state['summary'] = []
        values = set(self._state["selectedVariants"])
        if selected:
            values.add(index)
        else:
            values.discard(index)
        self._state["selectedVariants"] = sorted(values)
        self.changed.emit()

    @Slot()
    def readVariants(self):
        if self._pv_project is None:
            return
        chosen = list(self._state["selectedVariants"])
        if not chosen:
            self._status = _("Choose a variant.")
            self.changed.emit()
            return
        from ...pvsyst import mapping, project as pvproject

        project = self._pv_project
        self._start(
            lambda: mapping.to_project(
                project,
                [pvproject.read_variant(project.variants[i].path) for i in chosen],
            ),
            self._mapped_pvsyst,
        )

    def _mapped_pvsyst(self, result):
        self._pv_result = result
        report = result[1]
        self._state["summary"] = [
            f"{title}: " + str(item)
            for title, items in [
                (_("Read"), report.read),
                (_("Approximated"), report.approximated),
                (_("Not imported"), report.not_imported),
                (_("Missing"), report.missing),
            ]
            for item in items
        ]
        self._state["valid"] = True

    @Slot(str)
    def filterShortcuts(self, text):
        defaults = shortcuts.bindings({})
        rows = [
            dict(
                id=c.id,
                label=shortcuts.plain(c.text),
                keys=", ".join(self.bindings.get(c.id, [])),
                defaults=", ".join(defaults[c.id]),
            )
            for c in shortcuts.commands()
        ]
        self._state["shortcuts"] = [
            r
            for r in rows
            if text.lower() in " ".join(str(v) for v in r.values()).lower()
        ]
        self.changed.emit()

    @Slot(int, int, result=str)
    def captureKey(self, key, modifiers):
        return QKeySequence(
            QKeyCombination(Qt.KeyboardModifier(modifiers), Qt.Key(key))
        ).toString(QKeySequence.SequenceFormat.PortableText)

    @Slot(str, str, result=str)
    def shortcutVerdict(self, cid, keys):
        why = shortcuts.problem(keys)
        if why:
            return why
        names = {c.id: shortcuts.plain(c.text) for c in shortcuts.commands()}
        others = shortcuts.clashes(self.bindings, cid, keys)
        return (
            _("{keys} is used by {what}: there it would stop working.").format(
                keys=keys, what=", ".join(names[o] for o in others)
            )
            if others
            else ""
        )

    @Slot(str, str, result=bool)
    def assignShortcut(self, cid, keys):
        if cid not in self.bindings:
            return False
        if keys and shortcuts.problem(keys):
            self._status = shortcuts.problem(keys)
            self.changed.emit()
            return False
        normalized = shortcuts.normalize(keys) if keys else ""
        if normalized:
            for other in shortcuts.clashes(self.bindings, cid, normalized):
                self.bindings[other] = [
                    k for k in self.bindings[other] if k != normalized
                ]
        self.bindings[cid] = [normalized] if normalized else []
        self.filterShortcuts("")
        return True

    @Slot(str)
    def resetShortcut(self, cid):
        defaults = shortcuts.bindings({})
        if cid:
            self.bindings[cid] = list(defaults[cid])
        else:
            self.bindings = defaults
        self.filterShortcuts("")

    @Slot(str)
    def refreshRegistry(self, text=""):
        if self.registry is None:
            return
        self._state["clients"] = self.registry.list_clients(text)
        self._state["jobs"] = self.registry.list_jobs(
            text,
            client_id=self._state.get("client_id", "") if self._kind == "new" else "",
        )
        self._state["canExport"] = True
        for f in self._fields:
            if f["key"] == "client_id":
                f["options"] = [{"value": "", "label": _("No client")}] + [
                    {"value": r["id"], "label": r["name"]}
                    for r in self._state["clients"]
                ]
            if f["key"] == "job_id":
                f["options"] = [{"value": "", "label": _("No job")}] + [
                    {"value": r["id"], "label": r["code"] + " " + r["name"]}
                    for r in self._state["jobs"]
                ]
        self.fieldsChanged.emit()
        self.changed.emit()

    def _registry_action(self, function):
        if self.registry is None:
            self._status = _("No registry is open.")
            self.changed.emit()
            return False
        try:
            function()
        except (ValueError, OSError) as error:
            self._status = str(error)
            self.changed.emit()
            return False
        self._status = ""
        self.refreshRegistry("")
        self.registryChanged.emit()
        return True

    @Slot(str, result=bool)
    def saveClient(self, name):
        return self._registry_action(lambda: self.registry.create_client(name))

    @Slot(str, str, str, bool, result=bool)
    def saveJob(self, code, name, client, reserved):
        return self._registry_action(
            lambda: self.registry.create_job(
                code, name, client, status="in_progress", reserved=reserved
            )
        )

    @Slot(str)
    def selectJob(self, jid):
        if self.registry is None:
            return
        self._state["selectedJob"] = jid
        self._state["jobDetail"] = self.registry.job(jid) or {}
        self._state["folders"] = self.registry.list_folders(jid)
        self._state["projects"] = self.registry.list_projects(jid)
        self.changed.emit()

    @Slot(str, result=bool)
    def linkFolder(self, path):
        path = QUrl(path).toLocalFile() if path.startswith("file:") else path
        ok = self._registry_action(
            lambda: self.registry.link_folder(
                self._state.get("selectedJob", ""), Path(path)
            )
        )
        if ok:
            self.selectJob(self._state["selectedJob"])
        return ok

    @Slot(str, bool, result=bool)
    def manifestConsent(self, fid, allowed):
        ok = self._registry_action(
            lambda: self.registry.set_manifest_consent(fid, allowed)
        )
        if ok:
            self.selectJob(self._state["selectedJob"])
        return ok

    @Slot(str)
    def importRegistry(self, path):
        from ...registry import read_exchange

        path = QUrl(path).toLocalFile() if path.startswith("file:") else path
        self._pending_import = None
        self._state["canApplyImport"] = False

        def read():
            data = read_exchange(Path(path))
            preview = self.registry.preview_import(data)
            self._pending_import = data
            self._state["canApplyImport"] = not preview["conflicts"]
            self._state["summary"] = [
                _(
                    "Import preview: {new} new, {updated} updated, {unchanged} unchanged."
                ).format(**preview),
                *preview["conflicts"],
            ]

        self._registry_action(read)

    @Slot(result=bool)
    def applyImport(self):
        if self._pending_import is None or not self._state["canApplyImport"]:
            return False
        if not self._registry_action(
            lambda: self.registry.import_data(self._pending_import)
        ):
            return False
        self._pending_import = None
        self._state["canApplyImport"] = False
        self.changed.emit()
        return True

    @Slot(result=bool)
    def hasReservedJobs(self):
        return bool(
            self.registry
            and any(
                j["reserved"] for j in self.registry.list_jobs(include_archived=True)
            )
        )

    @Slot(str, bool, result=bool)
    def exportRegistry(self, path, consent=False):
        if self.hasReservedJobs() and not consent:
            self._status = self.labels["reservedExport"]
            self.changed.emit()
            return False
        path = QUrl(path).toLocalFile() if path.startswith("file:") else path
        return self._registry_action(lambda: self.registry.export(Path(path)))

    @Slot()
    def checkUpdate(self):
        def checked(release):
            if release is None or not updates.is_newer(release.version):
                self._status = _("You are using the latest version.")
                self._state.update(hasInstaller=False, releaseUrl='', releaseNotes='')
                return
            self._release = release
            self._installer = (
                updates.installer_of(release) if updates.installed_build() else None
            )
            self._state.update(
                releaseUrl=release.url,
                releaseLink=_("The release and its signed files: <a href=\"{url}\">{url}</a>").format(url=html.escape(release.url, quote=True)),
                releaseNotes=release.notes[:4000],
                hasInstaller=self._installer is not None,
                title=_("Version {version} is available").format(
                    version=release.version
                ),
            )

        def latest():
            try:
                return updates.latest_release()
            except updates.NoRelease:
                return None
            except updates.UpdateError as error:      # r28: said as what it is, not as a bare socket error
                raise updates.UpdateError(_("The check for updates failed: {error}").format(error=error)) from None
        self._start(latest, checked)

    @Slot()
    def downloadUpdate(self):
        if self._installer is None:
            return
        if self.paths is None:
            self._status = _("Choose a download folder first.")
            self.changed.emit()
            return
        self._cancel_download = threading.Event()
        asset = self._installer
        destination = Path(self.paths.cache) / "updates" / asset.name
        cancelled = self._cancel_download

        def download():
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                updates.download(asset, destination, cancelled=cancelled)
            except updates.UpdateError as error:      # r28: nothing was installed; said with the reason
                raise updates.UpdateError(_("The update was not installed: {error}").format(error=error)) from None
            return str(destination)

        def downloaded(path):
            if not cancelled.is_set():
                self.installerReady.emit(path)

        self._start(download, downloaded)

    @Property(QObject, constant=True)
    def mapBackend(self):
        if self._map is None:
            from .dialogs_map import DialogMap

            self._map = DialogMap(self)
            self._privacy()
            if self.candidate:
                self._map.set_point(self.candidate.lat, self.candidate.lon)
        return self._map
