"""R389: real calculated years cross into QML without work in gestures or getters."""

import importlib
import subprocess
import sys
import threading
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import _setup
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtQml import QQmlEngine, QQmlComponent, QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QSignalSpy

from meridiana import model
from meridiana.energy.pipeline import EnergyResult
from meridiana.session import ProjectSession
from quick.grafici.fixtures import build_results


setUpModule = _setup.keep_global_state


class ResultController(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = _setup.ROOT / "src/meridiana/quick/backend/charts_controller.py"
        if not cls.path.exists():
            return
        cls.api = importlib.import_module("meridiana.quick.backend.charts_controller")
        cls.app = _setup.qt_or_skip()
        cls.real = build_results()

    def setUp(self):
        self.assertTrue(self.path.exists(), "ResultsController is not implemented")
        self.controller = self.api.ResultsController()
        self.addCleanup(self.controller.close)
        self.addCleanup(self.controller.deleteLater)

    def payload(self):
        r = self.real
        return EnergyResult(
            sim=r.sim, load=r.load, econ=r.econ, pvgis=r.pvgis, sizing=r.sizing, storage=r.storage, battery_kwh=0.0
        )

    def settled(self):
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.controller.busy))
        self.assertEqual(self.controller.error, "")

    def test_real_result_is_published_atomically_and_getters_do_no_conversion(self):
        from meridiana.quick.backend import charts_data

        published = []
        self.controller.productionChanged.connect(
            lambda: published.append(
                tuple(getattr(self.controller, kind)["empty"] for kind in ("production", "consumption", "economics"))
            )
        )
        self.controller.update_results(self.payload())
        self.assertTrue(self.controller.busy)
        self.settled()
        self.assertEqual(published, [(False, False, False)])
        self.assertEqual(
            self.controller.production, {**charts_data.production(self.real.sim, self.real.pvgis), "stale": False}
        )
        before = self.controller.revision
        with patch.object(charts_data, "production", side_effect=AssertionError("getter recalculated")):
            for _ in range(30):
                self.assertFalse(self.controller.production["empty"])
                self.assertFalse(self.controller.consumption["empty"])
                self.assertFalse(self.controller.economics["empty"])
        self.assertEqual(self.controller.revision, before)

    def test_session_receives_energy_but_selection_and_text_leave_results_untouched(self):
        session = ProjectSession(model.Project())
        self.controller.attach_session(session)
        generation = session.energy_asked()
        self.assertTrue(session.energy_done(generation, self.payload().as_dict()))
        self.settled()
        before = self.controller.revision
        pages = self.controller.production
        session.changed("selection")
        session.edit("Rename", lambda project: setattr(project, "name", "Changed name"))
        self.assertIs(self.controller.production, pages)
        self.assertEqual(self.controller.revision, before)
        session.edit("Price", lambda project: project.economics.update(buy_f1=0.42))
        self.assertTrue(self.controller.stale)
        self.assertTrue(self.controller.production["stale"])
        self.assertEqual(self.controller.revision, before)
        self.controller.close()
        self.assertNotIn(self.controller._session_changed, session.listeners)

    def test_missing_weather_preserves_available_consumption(self):
        self.controller.update_results(EnergyResult(load=self.real.load, error_sim="Recorded missing weather"))
        self.settled()
        self.assertTrue(self.controller.production["empty"])
        self.assertEqual(self.controller.production["status"], "Recorded missing weather")
        self.assertFalse(self.controller.consumption["empty"])
        self.assertTrue(self.controller.economics["empty"])

    def test_calculated_basis_survives_edits_and_is_never_read_from_live_plant(self):
        from meridiana.energy.calculation_basis import CalculationBasis
        result = self.payload()
        result.basis = CalculationBasis(('INV1', 'INV2'), 42, 50, 1, 'Battery', 8., 12.)
        session = ProjectSession(model.Project())
        self.controller.attach_session(session)
        session.energy_done(session.energy_asked(), result.as_dict())
        self.settled()
        for kind in ('production', 'consumption', 'economics'):
            self.assertIn('42', getattr(self.controller, kind)['basis']['text'])
            self.assertIn('50', getattr(self.controller, kind)['basis']['text'])
        before = self.controller.production['basis']
        session.edit('Battery removed', lambda p: p.economics.update(battery_units=0))
        self.assertEqual(self.controller.production['basis'], before)

    def test_old_async_result_cannot_repopulate_a_new_project(self):
        from meridiana.quick.backend import charts_data

        entered, release = threading.Event(), threading.Event()
        original = charts_data.production

        def delayed(sim, *args, **kwargs):
            if sim is self.real.sim:
                entered.set()
                if not release.wait(10):
                    raise TimeoutError("test did not release conversion")
            return original(sim, *args, **kwargs)

        self.addCleanup(release.set)
        session = ProjectSession(model.Project())
        self.controller.attach_session(session)
        with patch.object(charts_data, "production", side_effect=delayed):
            session.energy_done(session.energy_asked(), self.payload().as_dict())
            self.assertTrue(_setup.wait_until(self.app, entered.is_set))
            session.new()
            release.set()
            self.assertTrue(_setup.wait_until(self.app, lambda: not self.controller._jobs))
        self.assertTrue(self.controller.production["empty"])
        self.assertTrue(self.controller.consumption["empty"])
        self.assertFalse(self.controller.busy)

    def test_error_and_settings_updates_do_not_recompute_the_year(self):
        self.controller.update_results(self.payload())
        self.settled()
        before = self.controller.revision
        values = self.controller.production["tiles"]
        self.controller.update_error("Recorded worker failure")
        self.assertEqual(self.controller.error, "Recorded worker failure")
        self.assertEqual(self.controller.production["status"], "Recorded worker failure")
        self.assertEqual(self.controller.production["tiles"], values)
        self.controller.update_error("")
        self.assertEqual(self.controller.production["status"], "\n".join(self.real.sim.notes))
        self.controller.update_settings({"battery": {"manufacturer": "Example", "model": "Pack"}})
        self.assertEqual(self.controller.storage["tiles"][0]["value"], "Example Pack")
        self.assertEqual(self.controller.revision, before)

    def test_adapter_failure_reports_error_and_retains_previous_complete_snapshot(self):
        from meridiana.quick.backend import charts_data

        self.controller.update_results(self.payload())
        self.settled()
        values = self.controller.production["tiles"]
        before = self.controller.revision
        with patch.object(charts_data, "economics", side_effect=ValueError("Recorded adapter failure")):
            self.controller.update_results(self.payload())
            self.assertTrue(_setup.wait_until(self.app, lambda: not self.controller.busy))
        self.assertEqual(self.controller.error, "Recorded adapter failure")
        self.assertEqual(self.controller.production["tiles"], values)
        self.assertEqual(self.controller.revision, before)
        # A failed refresh says nothing about a change to calculation inputs (R396).
        self.assertFalse(self.controller.stale)

    def test_install_is_idempotent_and_live_qml_observes_publication_and_actions(self):
        engine = QQmlEngine()
        self.addCleanup(engine.deleteLater)
        self.controller = self.api.install_results(engine)
        self.assertIs(self.api.install_results(engine), self.controller)
        self.assertIs(engine.rootContext().contextProperty("results"), self.controller)
        component = QQmlComponent(engine)
        component.setData(
            b"""import QtQml
import Meridiana.ChartBackend 1.0
QtObject {
    property string title: results.production.title
    property bool empty: results.production.empty
    property ChartServices services: ChartServices {}
    function choose() { results.requestAction("choose_battery") }
}""",
            QUrl(),
        )
        probe = component.create()
        self.assertIsNotNone(probe, [error.toString() for error in component.errors()])
        probe.setParent(engine)
        self.assertTrue(probe.property("empty"))
        self.controller.update_results(self.payload())
        self.settled()
        self.assertFalse(probe.property("empty"))
        spy = QSignalSpy(self.controller.actionRequested)
        probe.choose()
        self.assertEqual(spy.at(0), ["battery_catalog"])

    def test_bridge_error_and_session_result_are_connected_without_private_methods(self):
        class Source(QObject):
            stateChanged = Signal()

            def __init__(self):
                super().__init__()
                self.session = ProjectSession(model.Project())
                self.error, self.busy = "", False

        bridge = Source()
        self.controller.attach_bridge(bridge)
        bridge.session.energy_done(bridge.session.energy_asked(), self.payload().as_dict())
        self.settled()
        bridge.error = "Recorded failure"
        bridge.stateChanged.emit()
        self.assertEqual(self.controller.error, "Recorded failure")

    def test_real_bridge_check_failure_does_not_cancel_a_valid_year_being_adapted(self):
        from meridiana.quick.bridge import Bridge

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        bridge = Bridge(model.Project(), Path(temporary.name))
        self.addCleanup(bridge.close)
        self.controller.attach_bridge(bridge)
        self.settled()
        entered, release = threading.Event(), threading.Event()
        original = self.api._pages

        def delayed(result):
            entered.set()
            if not release.wait(10):
                raise TimeoutError("test did not release conversion")
            return original(result)

        self.addCleanup(release.set)
        with patch.object(self.api, "_pages", side_effect=delayed):
            bridge.session.energy_done(bridge.session.energy_asked(), self.payload().as_dict())
            self.assertTrue(_setup.wait_until(self.app, entered.is_set))
            bridge._checks_finished(bridge._check_serial, [], "Recorded check failure")
            release.set()
            self.assertTrue(_setup.wait_until(self.app, lambda: not self.controller._jobs))
        self.assertIs(bridge.session.energy["sim"], self.real.sim)
        self.assertFalse(self.controller.production["empty"])
        self.assertFalse(self.controller.consumption["empty"])
        self.assertFalse(self.controller.economics["empty"])
        self.assertEqual(self.controller.error, "Recorded check failure")

    def test_real_bridge_failed_computation_retains_previous_year_and_its_input_key(self):
        from meridiana.quick.bridge import Bridge

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        bridge = Bridge(model.Project(), Path(temporary.name))
        self.addCleanup(bridge.close)
        self.controller.attach_bridge(bridge)
        bridge.session.energy_done(bridge.session.energy_asked(), self.payload().as_dict())
        self.settled()
        values = self.controller.production["tiles"]
        bridge._finished(bridge.session.generation, {}, [], {"error": "Recorded compute failure"})
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.controller.busy))
        self.assertEqual(self.controller.production["tiles"], values)
        self.assertFalse(self.controller.production["empty"])
        self.assertEqual(self.controller.error, "Recorded compute failure")
        self.assertFalse(self.controller.stale)
        bridge.session.edit("Price", lambda project: project.economics.update(buy_f1=0.42))
        self.assertTrue(self.controller.stale)

    def test_controller_import_needs_no_widgets(self):
        script = (
            "import sys; import meridiana.quick.backend.charts_controller; "
            "assert not any(n.startswith(('PySide6.QtWidgets', 'meridiana.ui', 'pyqtgraph')) for n in sys.modules)"
        )
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_shell_page_urls_load_real_results_and_forward_commands(self):
        from meridiana.quick.backend.tokens import install_theme

        directory = _setup.ROOT / "src/meridiana/quick/qml/Meridiana/Charts"
        for name in ("ProductionPage", "ConsumptionPage", "EconomicsPage", "StoragePage"):
            self.assertTrue((directory / (name + ".qml")).exists(), f"{name} URL is not implemented")
        engine = QQmlApplicationEngine()
        self.addCleanup(engine.deleteLater)
        install_theme(engine)
        self.controller = self.api.install_results(engine)
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
        source = b"""import QtQuick
import Meridiana.Charts 1.0
Window {
    width: 1366; height: 900; visible: false
    ProductionPage { objectName: "page"; anchors.fill: parent }
}"""
        engine.loadData(source, QUrl.fromLocalFile(str(directory / "controller-test.qml")))
        self.assertTrue(engine.rootObjects(), warnings)
        window = engine.rootObjects()[0]
        self.assertIsInstance(window, QQuickWindow)
        self.addCleanup(window.close)
        self.controller.update_results(self.payload())
        self.settled()

        def visual_items(item):
            yield item
            for child in item.childItems():
                yield from visual_items(child)

        value = next((item for item in visual_items(window.contentItem()) if item.objectName() == "tile-value-0"), None)
        self.assertIsNotNone(value)
        unit = next(item for item in visual_items(window.contentItem()) if item.objectName() == "tile-unit-0")
        self.assertEqual(value.property("text") + " " + unit.property("text"),
                         self.controller.production["tiles"][0]["value"])
        page = window.findChild(QObject, "page")
        spy = QSignalSpy(self.controller.actionRequested)
        page.actionRequested.emit("compute")
        self.assertEqual(spy.at(0), ["compute"])
        self.assertEqual(warnings, [])
