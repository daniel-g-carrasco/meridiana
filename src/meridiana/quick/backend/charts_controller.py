"""Install cached result pages over the existing session, without Widgets.

The pipeline owns calculation and publishes immutable results. This controller
only adapts those results in a worker, then publishes complete pages on the GUI
thread. Property reads and QML interactions never run a calculation or adapter.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, Qt, Signal, Slot

from . import charts_data


_KINDS = ("production", "consumption", "economics")


def _pages(result):
    """Use the pipeline's actual fields, including a partially available year."""
    sim = result.get("sim")
    production_error = result.get("error_sim") or ""
    pages = {
        "production": charts_data.production(sim, result.get("pvgis"), production_error),
        "consumption": charts_data.consumption(result.get("load"), result.get("error_load") or ""),
        "economics": charts_data.economics(
            result.get("econ"),
            result.get("error_econ") or (production_error if result.get("econ") is None else ""),
            sizing=result.get("sizing"),
            storage=result.get("storage"),
            p_stc_kw=sim.p_stc_kw if sim is not None else 0,
            battery_kwh=result.get("battery_kwh") or 0,
        ),
    }
    if result.get('basis') is not None:
        basis = charts_data.calculation_basis(result['basis'])
        for page in pages.values():
            page['basis'] = basis
    return pages


class _Signals(QObject):
    finished = Signal(int, object, str)


class _Prepare(QRunnable):
    def __init__(self, serial, result, input_key=""):
        super().__init__()
        self.serial, self.result = serial, result
        self.input_key = input_key
        self.signals = _Signals()

    def run(self):
        try:
            pages = _pages(self.result)
        except Exception as error:  # Worker boundary: surfaced, previous pages stay readable.
            self.signals.finished.emit(self.serial, None, str(error))
        else:
            self.signals.finished.emit(self.serial, pages, "")


class ResultsController(QObject):
    productionChanged = Signal()
    consumptionChanged = Signal()
    economicsChanged = Signal()
    storageChanged = Signal()
    stateChanged = Signal()
    actionRequested = Signal(str)
    helpRequested = Signal(str)

    @Slot(str)
    def help(self, topic):
        self.helpRequested.emit(topic)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pages = {key: {**page, "stale": False} for key, page in _pages({}).items()}
        self._statuses = {key: page["status"] for key, page in self._pages.items()}
        self._storage = charts_data.storage({})
        self._serial, self._revision = 0, 0
        self._jobs = {}
        self._adapting = self._computing = self._stale = self._closed = False
        self._error = ""
        self._session = self._bridge = None
        self._bridge_error = ""
        self._computed_key = ""

    production = Property("QVariantMap", lambda self: self._pages["production"], notify=productionChanged)
    consumption = Property("QVariantMap", lambda self: self._pages["consumption"], notify=consumptionChanged)
    economics = Property("QVariantMap", lambda self: self._pages["economics"], notify=economicsChanged)
    storage = Property("QVariantMap", lambda self: self._storage, notify=storageChanged)
    busy = Property(bool, lambda self: self._adapting or self._computing, notify=stateChanged)
    error = Property(str, lambda self: self._error or self._bridge_error, notify=stateChanged)
    stale = Property(bool, lambda self: self._stale, notify=stateChanged)
    revision = Property(int, lambda self: self._revision, notify=stateChanged)

    @Slot(object)
    def update_results(self, result):
        """Accept EnergyResult or its dict, from the GUI thread, once per result.

        Result objects/frames are read-only after publication, as in ProjectSession.
        The mapping is copied; no DataFrame is copied on the GUI thread.
        """
        if self._closed:
            return
        if not isinstance(result, Mapping):
            result = result.as_dict()
        self._serial += 1
        self._error = ""
        self._adapting = True
        task = _Prepare(self._serial, dict(result), self._session.energy_key_computed if self._session else "")
        self._jobs[self._serial] = task
        task.signals.finished.connect(self._accept, Qt.ConnectionType.QueuedConnection)
        self.stateChanged.emit()
        QThreadPool.globalInstance().start(task)

    @Slot(int, object, str)
    def _accept(self, serial, pages, error):
        task = self._jobs.pop(serial, None)
        if self._closed or serial != self._serial:
            return
        self._adapting = False
        if error:
            self.update_error(error)
            return
        # All three maps change before any signal, so bindings never see mixed years.
        self._computed_key = task.input_key
        self._stale = self._inputs_changed()
        self._pages = {key: {**page, "stale": self._stale} for key, page in pages.items()}
        self._statuses = {key: page["status"] for key, page in self._pages.items()}
        self._revision += 1
        for key in _KINDS:
            getattr(self, key + "Changed").emit()
        self.stateChanged.emit()

    @Slot("QVariantMap")
    def update_settings(self, settings):
        """Update the storage summary from project.economics, not a simulation."""
        if self._closed:
            return
        page = charts_data.storage(settings or {})
        if page != self._storage:
            self._storage = page
            self.storageChanged.emit()

    @Slot(str)
    def update_error(self, message):
        """Surface a failed computation while retaining readable previous results."""
        if self._closed or message == self._error:
            return
        self._error = message
        if message:
            self._serial += 1
            self._adapting = False
            self._stale = self._inputs_changed()
        self._pages = {
            key: {**page, "status": message or self._statuses[key], "stale": self._stale}
            for key, page in self._pages.items()
        }
        for key in _KINDS:
            getattr(self, key + "Changed").emit()
        self.stateChanged.emit()

    @Slot(str)
    def requestAction(self, action):
        """Forward documented IDs to ShellController.trigger, never run work here."""
        if action:
            self.actionRequested.emit("battery_catalog" if action == "choose_battery" else action)

    def attach_session(self, session):
        """Follow ProjectSession's public topics, including file replacement."""
        if self._session is session:
            return
        self._detach_session()
        self._session = session
        if session is not None:
            session.subscribe(self._session_changed)
            self.update_settings(session.project.economics)
            self.update_results(session.energy)

    def _detach_session(self):
        if self._session is not None:
            # ProjectSession currently exposes subscribe and the public listeners list.
            if self._session_changed in self._session.listeners:
                self._session.listeners.remove(self._session_changed)
            self._session = None

    def _inputs_changed(self):
        """Compare today's inputs with the visible year, even after a failed refresh.

        Bridge stores an empty result on a worker failure. Keep the key of the
        displayed snapshot instead of consulting that empty session.energy.
        Expected layout keys follow ProjectSession.energy_outdated exactly.
        """
        if self._session is None or not self._computed_key:
            return False
        project = self._session.project
        keys = {sf.id: project.layout_key(sf) for sf in project.subfields if sf.filled}
        return self._session.energy_key(keys) != self._computed_key

    def _session_changed(self, topics):
        if self._closed:
            return
        if "file" in topics:
            self._serial += 1
            self._adapting = False
            self._error, self._stale = "", False
            self._computed_key = ""
            self._pages = {key: {**page, "stale": False} for key, page in _pages({}).items()}
            self._statuses = {key: page["status"] for key, page in self._pages.items()}
            self.update_settings(self._session.project.economics)
            for key in _KINDS:
                getattr(self, key + "Changed").emit()
            self.stateChanged.emit()
        elif "energy" in topics:
            result = self._session.energy
            if (
                self._bridge is not None
                and self._bridge.error
                and not any(result.get(key) is not None for key in ("sim", "load", "econ"))
            ):
                self.update_error(self._bridge.error)
            else:
                self.update_results(result)
        elif topics & {"project:energy", "project:geometry", "project:subfields", "project:site", "restored"} or any(
            topic.startswith("layout:") for topic in topics
        ):
            if topics & {"project:energy", "restored"}:
                self.update_settings(self._session.project.economics)
            stale = self._inputs_changed()
            if stale != self._stale:
                self._stale = stale
                self._pages = {key: {**page, "stale": stale} for key, page in self._pages.items()}
                for key in _KINDS:
                    getattr(self, key + "Changed").emit()
                self.stateChanged.emit()

    def attach_bridge(self, bridge):
        """Bridge provides worker failure/busy state; the session provides the year."""
        if self._bridge is bridge:
            return
        if self._bridge is not None:
            from shiboken6 import isValid
            if isValid(self._bridge):
                self._bridge.stateChanged.disconnect(self._bridge_changed)
        self._bridge = bridge
        self._bridge_error = ""
        if bridge is not None:
            self.attach_session(bridge.session)
            bridge.stateChanged.connect(self._bridge_changed)
            self._bridge_changed()

    @Slot()
    def _bridge_changed(self):
        if self._closed or self._bridge is None:
            return
        computing = bool(self._bridge.busy)
        if computing != self._computing:
            self._computing = computing
            self.stateChanged.emit()
        error = self._bridge.error
        if error != self._bridge_error:
            self._bridge_error = error
            # Bridge also reports check-job failures. They must remain visible but
            # cannot invalidate or overwrite a valid year currently being adapted.
            # The pipeline's error_sim is already part of the result page data.
            self.stateChanged.emit()

    @Slot()
    def close(self):
        """Detach listeners and ignore pending results; never block the GUI thread."""
        if self._closed:
            return
        self._closed = True
        self._adapting = self._computing = False
        self._serial += 1
        self._detach_session()
        if self._bridge is not None:
            self._bridge.stateChanged.disconnect(self._bridge_changed)
            self._bridge = None


def install_results(engine, *, bridge=None, session=None) -> ResultsController:
    """Before loading QML, register ChartBackend and expose context `results`.

    The engine owns and retains the controller. Installation is idempotent.
    Supply bridge for the current application, or session for another host.
    """
    from .charts_bridge import register
    from .controls import install_controls

    if bridge is not None and session is not None and bridge.session is not session:
        raise ValueError("Bridge and results must use the same ProjectSession")
    register()
    install_controls(engine)
    controller = getattr(engine, "_meridiana_results", None)
    if controller is None:
        controller = ResultsController(engine)
        engine._meridiana_results = controller
        engine.addImportPath(str(Path(__file__).parents[1] / "qml"))
        engine.rootContext().setContextProperty("results", controller)
        engine.destroyed.connect(controller.close)
    if bridge is not None:
        controller.attach_bridge(bridge)
    elif session is not None:
        controller.attach_session(session)
    return controller
