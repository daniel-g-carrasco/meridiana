"""Phase preparation preserves current fields, delegates and commands."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import _setup
from _fixtures import mixed
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import item, pump, wait_for

def setUpModule():
    _setup.keep_global_state()


class PhasePreparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup.qt_or_skip()
        create_app()

    def test_a_ready_phase_repairs_a_missing_repeater_delegate(self):
        from PySide6.QtCore import QTimer, QUrl
        from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression, qmlContext
        from shiboken6 import delete
        from meridiana.gui.backend.controls import install_controls
        _setup.qt_or_skip()
        engine = QQmlEngine()
        install_controls(engine, {'theme': 'light', 'reducedMotion': True})
        from PySide6.QtQml import QQmlIncubationController
        incubation = QQmlIncubationController()
        engine.setIncubationController(incubation)
        component = QQmlComponent(engine)
        component.setData(b'import QtQuick\nimport Meridiana.Controls as M\n'
                          b'M.PhaseLoader { width: 300; height: 200; shown: true; '
                          b'sourceComponent: Item { '
                          b'function intact() { let n=0; for(let i=0;i<rows.count;i++) if(rows.itemAt(i)) n++; return n } '
                          b'Repeater { id: rows; model: 3; Item { required property int index; objectName: "row"+index } } } }', QUrl())
        loader = component.create()
        self.assertIsNotNone(loader, component.errorString())
        timer = QTimer()
        timer.setInterval(2)
        timer.timeout.connect(lambda: engine.incubationController() and engine.incubationController().incubateFor(1))
        # A plain QQmlEngine has no window to drive its asynchronous incubators.
        timer.start()
        try:
            wait_for(lambda: loader.property('item') is not None)
            old = loader.property('item')
            def row():
                return next((n for n in old.childItems() if n.objectName() == 'row1'), None)
            wait_for(lambda: row() is not None, seconds=3)
            delete(row())
            wait_for(lambda: loader.property('item') is not None and loader.property('item') != old, seconds=3)
            value, _ = QQmlExpression(qmlContext(loader), loader, 'item.intact()').evaluate()
            self.assertEqual(value, 3)
        finally:
            timer.stop()
            delete(loader)
            delete(engine)


    def test_stale_inspector_waits_for_the_new_phase_frame(self):
        from meridiana.app.session import ProjectSession
        from meridiana.gui.backend.charts_editor import ResultEditor
        _setup.qt_or_skip()
        session = ProjectSession(mixed())
        editor = ResultEditor(session, 'production')
        try:
            editor.shown = False
            session.edit('Change a loss', lambda p: p.energy.update({'losses': {'soiling_pct': 2}}))
            queued = []
            session.later = queued.append
            with patch.object(editor, 'refresh', wraps=editor.refresh) as refresh:
                editor.shown = True
                self.assertEqual(refresh.call_count, 0, 'Do not rebuild the inspector inside the click')
                self.assertFalse(editor.ready, 'The phase must show the common wait instead of old fields')
                self.assertEqual(len(queued), 1)
                queued.pop()()
                self.assertTrue(editor.ready)
                self.assertEqual(refresh.call_count, 1)
        finally:
            editor.close()


    def test_production_summary_is_retained_between_phases(self):
        _setup.qt_or_skip()
        create_app()
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            host = QuickWindow(mixed(), Path(folder), real_views=True)
            try:
                host.bridge.configure_background(enabled=False)
                host.window.show()
                host.window.showPhase('production')
                trailing = item(host.window, 'phaseTrailing')
                wait_for(lambda: trailing.property('item') is not None)
                original = trailing.property('item')
                host.window.showPhase('model')
                pump(200)
                host.window.showPhase('production')
                wait_for(lambda: trailing.property('item') is not None)
                self.assertEqual(trailing.property('item'), original)
            finally:
                host.close()


    def test_idle_phase_changes_keep_the_plan_geometry(self):
        from meridiana.app.session import ProjectSession
        from meridiana.gui.backend.plan import PlanController
        _setup.qt_or_skip()
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            controller = PlanController(ProjectSession(mixed()), cache=Path(folder), manage_layout=False)
            try:
                with patch.object(controller, '_overlays', wraps=controller._overlays) as rebuild:
                    for phase in ('plant', 'production', 'consumption', 'economics', 'report', 'model'):
                        controller.setPhase(phase)
                    self.assertEqual(rebuild.call_count, 0, 'An idle plan keeps its geometry across phases')
                controller.setTool('move')
                with patch.object(controller, '_overlays', wraps=controller._overlays) as rebuild:
                    controller.setPhase('plant')
                    self.assertGreater(rebuild.call_count, 0, 'An active gesture must be retired')
                self.assertEqual(controller.tool, 'select')
            finally:
                controller.close()


if __name__ == '__main__':
    unittest.main()
