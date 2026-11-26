"""Camera gestures keep their GUI event budget with a large, wired layout (R701)."""
import statistics
import time
import unittest
from pathlib import Path

import _setup
from _fixtures import generated, inverter_record
from PySide6.QtCore import QCoreApplication, QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QInputDevice, QMouseEvent, QNativeGestureEvent, QPointingDevice
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana.app import jobs
from meridiana.gui.application import create_app
from meridiana.gui.backend.plan import PlanController
from quick.aiuti.puntini import assert_dots_follow
from quick.aiuti.tempi import check_timing, timed

setUpModule = _setup.keep_global_state


class MotionBudget(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        project = generated(12, 1, 0)
        project.energy['inverters'] = [{'record': inverter_record(), 'count': 12}]
        results, keys, _ = jobs.layout_of(project)
        runs = []
        for sfid, result in results.items():
            modules = [f'{sfid}/{module.key}' for module in result.modules]
            runs.extend({'inverter': 1, 'mppt': 1, 'modules': modules[i:i+18]}
                        for i in range(0, len(modules), 18))
        project.energy['strings'] = {'runs': runs}
        self.controller = PlanController(project, manage_layout=False)
        self.controller.session.layout_done(self.controller.session.generation, results, keys)
        self.controller.setPhase('plant')
        self.controller.setNavigation('autocad')
        self.engine = QQmlApplicationEngine()
        self.errors = []
        self.engine.warnings.connect(lambda rows: self.errors.extend(r.toString() for r in rows))
        self.controller.install(self.engine)
        self.engine.rootContext().setContextProperty('planBackend', self.controller)
        self.engine.load(QUrl.fromLocalFile(str(Path(_setup.ROOT) /
                                             'src/meridiana/gui/qml/Meridiana/Plan/PlanWindow.qml')))
        self.assertTrue(self.engine.rootObjects(), self.errors)
        self.window = self.engine.rootObjects()[0]
        self.window.resize(1000, 740)
        self.window.show()
        self.plan = self.window.findChild(QObject, 'plan')
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.plan.property('startingUp'), 60))
        # R707: a dot on each module shows from 40 px a module: the scale of the expensive dots
        self.plan.setProperty('zoom', 1.05*self.controller.levels['module']/self.controller.moduleSize)
        self.plan.setProperty('panX', 250.)
        self.plan.setProperty('panY', 500.)
        self.assertTrue(_setup.wait_until(self.app, lambda: self.plan.property('zoom') ==
                                         self.plan.property('settledZoom') and bool(self.controller.dots), 30))
        self.assertGreaterEqual(self.plan.property('paintedModules'), 700)
        self.assertGreaterEqual(len(self.controller.dots), 700, 'the expensive string dots must be present')
        self.pad = QPointingDevice('budget touchpad', 9701, QInputDevice.DeviceType.TouchPad,
                                  QPointingDevice.PointerType.Finger, QInputDevice.Capability.Position, 5, 0)

    def tearDown(self):
        self.window.close()
        self.controller.close()
        self.engine.deleteLater()
        self.app.processEvents()

    def assert_budget(self, events):
        geometry = self.window.findChild(QObject, 'moduleGeometry')
        uploads = geometry.uploads
        self.controller.calls.clear()
        handled = []
        for event in events:
            start = time.perf_counter()
            QCoreApplication.sendEvent(self.window, event)
            handled.append((time.perf_counter() - start) * 1000)
            self.app.processEvents()
        median = statistics.median(handled)
        print(f'{self.id()}: {self.plan.property("paintedModules")} modules, event median {median:.3f} ms', flush=True)
        check_timing(median < 2., f'Camera event median {median:.3f} ms (limit 2 ms)')
        self.assertEqual(geometry.uploads, uploads, 'navigation must retain module geometry')
        self.assertEqual(self.controller.calls['pointer'], 0)
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.plan.property('annotationPending') and
                                         self.plan.property('pendingMotion') is None, 10))
        # R706: the dots are a layer of the drawing (they were 700 items moved at every frame): all of them there,
        # as wide as a point, and the drawing at the camera in hand once the hand rests
        self.assertGreaterEqual(len(self.controller.dots), 700)
        assert_dots_follow(self, self.plan, self.controller.dots)
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.plan.property('motionActive'), 5))
        drawn = self.plan.property('renderCamera')
        drawn = drawn.toVariant() if hasattr(drawn, 'toVariant') else drawn
        for name, key in (('panX', 'x'), ('panY', 'y'), ('zoom', 'zoom')):
            self.assertAlmostEqual(drawn[key], self.plan.property(name), places=6, msg='no stale camera after the gesture')
        self.assertFalse(self.errors, self.errors)

    @timed('an event of the camera within 2 ms')
    def test_middle_drag_event_median_under_two_ms(self):
        at = QPoint(400, 350)
        QTest.mouseMove(self.window, at)
        QTest.mousePress(self.window, Qt.MiddleButton, Qt.NoModifier, at)
        start_x = self.plan.property('panX')
        events = []
        for i in range(1, 61):
            point = QPointF(400+i*6, 350+i*3)
            events.append(QMouseEvent(QMouseEvent.Type.MouseMove, point, point,
                                      QPointF(self.window.mapToGlobal(point.toPoint())),
                                      Qt.NoButton, Qt.MiddleButton, Qt.NoModifier))
        try:
            self.assert_budget(events)
            self.assertAlmostEqual(self.plan.property('panX'), start_x+360)
        finally:
            QTest.mouseRelease(self.window, Qt.MiddleButton, Qt.NoModifier, QPoint(760, 530))

    @timed('an event of the camera within 2 ms')
    def test_pinch_event_median_under_two_ms(self):
        point = QPointF(400, 350)
        def pinch(kind, value):
            return QNativeGestureEvent(kind, self.pad, 2, point, point,
                                       QPointF(self.window.mapToGlobal(point.toPoint())), value, QPointF())
        QCoreApplication.sendEvent(self.window, pinch(Qt.BeginNativeGesture, 0))
        before = self.plan.property('zoom')
        try:
            self.assert_budget([pinch(Qt.ZoomNativeGesture, .003) for _ in range(60)])
            self.assertAlmostEqual(self.plan.property('zoom'), before*1.003**60)
        finally:
            QCoreApplication.sendEvent(self.window, pinch(Qt.EndNativeGesture, 0))

    def test_native_events_accumulate_until_the_frame_without_losing_the_anchor(self):
        point = QPointF(400, 350)
        before = self.plan.property('zoom')
        x, y = self.plan.property('panX'), self.plan.property('panY')
        for kind, value in ((Qt.BeginNativeGesture, 0), (Qt.ZoomNativeGesture, .01),
                            (Qt.ZoomNativeGesture, .01), (Qt.EndNativeGesture, 0)):
            QCoreApplication.sendEvent(self.window, QNativeGestureEvent(
                kind, self.pad, 2, point, point, point, value, QPointF()))
        self.assertEqual(self.plan.property('zoom'), before, 'camera work belongs to the frame')
        self.assertTrue(_setup.wait_until(self.app, lambda: self.plan.property('zoom') != before, 10))
        self.assertAlmostEqual(self.plan.property('zoom'), before*1.01**2)
        self.assertAlmostEqual(self.plan.property('panX'), 400+(x-400)*1.01**2)
        self.assertAlmostEqual(self.plan.property('panY'), 350+(y-350)*1.01**2)

    def test_frame_command_supersedes_device_motion_queued_for_the_same_frame(self):
        point = QPointF(400, 350)
        for kind, value in ((Qt.BeginNativeGesture, 0), (Qt.ZoomNativeGesture, .1), (Qt.EndNativeGesture, 0)):
            QCoreApplication.sendEvent(self.window, QNativeGestureEvent(
                kind, self.pad, 2, point, point, point, value, QPointF()))
        self.plan.fit()
        fitted = tuple(self.plan.property(name) for name in ('panX', 'panY', 'zoom'))
        self.assertTrue(_setup.wait_until(self.app, lambda: self.plan.property('pendingMotion') is None and
                                         not self.plan.property('annotationPending'), 10))
        self.assertEqual(tuple(self.plan.property(name) for name in ('panX', 'panY', 'zoom')), fitted)
