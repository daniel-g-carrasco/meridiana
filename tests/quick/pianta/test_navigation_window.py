"""Actual Qt events validate the Quick adapter, including precision touchpad identity."""

import os
import unittest
from pathlib import Path

os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QInputDevice, QKeyEvent, QNativeGestureEvent, QPointingDevice, QWheelEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana import model, navigation
from meridiana.quick.backend.plan import PlanController


class NavigationWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.controller = PlanController(model.Project(), manage_layout=False)
        self.engine = QQmlApplicationEngine()
        self.errors = []
        self.engine.warnings.connect(lambda rows: self.errors.extend(row.toString() for row in rows))
        self.controller.install(self.engine)
        self.engine.rootContext().setContextProperty('planBackend', self.controller)
        path = Path(__file__).resolve().parents[3] / 'src/meridiana/quick/qml/Meridiana/Plan/PlanWindow.qml'
        self.engine.load(QUrl.fromLocalFile(str(path)))
        self.assertTrue(self.engine.rootObjects(), self.errors)
        self.window = self.engine.rootObjects()[0]
        self.assertTrue(QTest.qWaitForWindowExposed(self.window))
        QTest.qWait(40)
        self.plan = self.window.findChild(QObject, 'plan')

    def tearDown(self):
        self.window.close()
        self.controller.close()
        self.engine.deleteLater()
        self.app.processEvents()

    def reset_view(self):
        for name, value in (('zoom', 2.), ('panX', 250.), ('panY', 250.)):
            self.plan.setProperty(name, value)
        self.controller.calls.clear()

    def test_middle_click_and_drag_in_all_styles_keep_core_semantics(self):
        for key, style in navigation.STYLES.items():
            with self.subTest(style=key):
                self.controller.setNavigation(key)
                self.reset_view()
                QTest.mouseClick(self.window, Qt.MiddleButton, Qt.NoModifier, QPoint(400, 300))
                self.assertAlmostEqual(self.plan.property('panX'),
                                       250 + self.plan.width() / 2 - 400 if style.middle_click else 250)
                self.reset_view()
                QTest.mousePress(self.window, Qt.MiddleButton, Qt.NoModifier, QPoint(400, 300))
                QTest.mouseMove(self.window, QPoint(425, 315), 5)
                QTest.mouseRelease(self.window, Qt.MiddleButton, Qt.NoModifier, QPoint(425, 315))
                kind = navigation.Navigator(style)._match({'middle'}, set())
                factor = 1.2 ** (-15 / 40)
                expected_x = self.plan.width() / 2 - (self.plan.width() / 2 - 250) * factor
                self.assertAlmostEqual(self.plan.property('panX'), 275 if kind == 'pan' else
                                       expected_x if kind == 'zoom' else 250)
                self.assertAlmostEqual(self.plan.property('zoom'), 2 * 1.2 ** (-15 / 40) if kind == 'zoom' else 2)
                self.assertEqual(self.controller.calls['pointer'], 0)
                self.assertEqual(self.controller.calls['click'], 0)
        self.assertFalse(self.errors, self.errors)

    def test_chord_release_never_selects_or_turns_into_a_new_drag_and_space_does_not_reach_python(self):
        self.controller.setNavigation('autocad')
        self.reset_view()
        QTest.mousePress(self.window, Qt.LeftButton, Qt.NoModifier, QPoint(400, 300))
        QTest.mousePress(self.window, Qt.RightButton, Qt.NoModifier, QPoint(400, 300))
        QTest.mouseMove(self.window, QPoint(420, 310), 5)
        self.assertAlmostEqual(self.plan.property('panX'), 270)
        QTest.mouseRelease(self.window, Qt.LeftButton, Qt.NoModifier, QPoint(420, 310))
        QTest.mouseMove(self.window, QPoint(440, 320), 5)
        QTest.mouseRelease(self.window, Qt.RightButton, Qt.NoModifier, QPoint(440, 320))
        self.assertAlmostEqual(self.plan.property('panX'), 270)
        self.assertEqual(self.controller.calls['click'], 0)
        QTest.keyPress(self.window, Qt.Key_Space)
        QTest.mouseMove(self.window, QPoint(460, 330), 5)
        QTest.mouseMove(self.window, QPoint(480, 340), 5)
        QTest.keyRelease(self.window, Qt.Key_Space)
        self.assertGreater(self.plan.property('panX'), 270)
        self.assertEqual(self.controller.calls['pointer'], 0)
        self.assertFalse(self.errors, self.errors)

    def test_real_wheel_pixel_phase_precision_device_and_ctrl_keep_anchor(self):
        pad = QPointingDevice('precision pad', 99, QInputDevice.DeviceType.TouchPad,
                              QPointingDevice.PointerType.Finger, QInputDevice.Capability.Position,
                              5, 0)
        mouse = QPointingDevice.primaryPointingDevice()
        for device, angle, pixel, phase, ctrl in (
                (mouse, (0, 120), (0, 0), Qt.NoScrollPhase, False),
                (pad, (0, 40), (0, 0), Qt.NoScrollPhase, False),
                (mouse, (0, 120), (0, 0), Qt.ScrollUpdate, False),
                (mouse, (0, 0), (8, -6), Qt.NoScrollPhase, False),
                (pad, (0, 60), (0, 0), Qt.NoScrollPhase, True)):
            self.reset_view()
            kind, dx, dy = navigation.wheel_action(angle, pixel, phase != Qt.NoScrollPhase, False, ctrl,
                                                  touchpad=device == pad)
            event = QWheelEvent(QPointF(400, 300), QPointF(400, 300), QPoint(*pixel), QPoint(*angle),
                                Qt.NoButton, Qt.ControlModifier if ctrl else Qt.NoModifier, phase, False,
                                Qt.MouseEventNotSynthesized, device)
            QGuiApplication.sendEvent(self.window, event)
            self.app.processEvents()
            if kind == 'pan':
                self.assertAlmostEqual(self.plan.property('panX'), 250 + dx)
                self.assertAlmostEqual(self.plan.property('panY'), 250 + dy)
                self.assertAlmostEqual(self.plan.property('zoom'), 2)
            else:
                factor = 1.2 ** dy
                self.assertAlmostEqual(self.plan.property('zoom'), 2 * factor)
                self.assertAlmostEqual(self.plan.property('panX'), 400 - 150 * factor)
                self.assertAlmostEqual(self.plan.property('panY'), 300 - 50 * factor)
            self.assertEqual(self.controller.calls['pointer'], 0)
        self.assertFalse(self.errors, self.errors)

    def test_native_pinch_keeps_anchor_and_native_rotation_is_ignored(self):
        self.reset_view()
        pad = QPointingDevice('native pad', 98, QInputDevice.DeviceType.TouchPad,
                              QPointingDevice.PointerType.Finger, QInputDevice.Capability.Position, 5, 0)
        p = QPointF(400, 300)
        for kind, value in ((Qt.BeginNativeGesture, 0), (Qt.ZoomNativeGesture, .25), (Qt.EndNativeGesture, 0)):
            event = QNativeGestureEvent(kind, pad, 2, p, p, p, value, QPointF())
            self.app.sendEvent(self.window, event)
        self.app.processEvents()
        self.assertAlmostEqual(self.plan.property('zoom'), 2.5)
        self.assertAlmostEqual(self.plan.property('panX'), 400-150*1.25)
        self.assertAlmostEqual(self.plan.property('panY'), 300-50*1.25)
        self.app.sendEvent(self.window, QNativeGestureEvent(Qt.RotateNativeGesture, pad, 2, p, p, p, 30, QPointF()))
        self.assertEqual(self.plan.property('bearing'), 0)
        self.assertEqual(self.controller.calls['pointer'], 0)

    def test_scroll_begin_update_end_moves_both_axes_without_zoom(self):
        self.reset_view()
        for phase, pixel in ((Qt.ScrollBegin, QPoint(4,-3)), (Qt.ScrollUpdate, QPoint(6,-2)), (Qt.ScrollEnd,QPoint())):
            self.app.sendEvent(self.window, QWheelEvent(QPointF(400,300), QPointF(400,300),pixel,QPoint(),
                Qt.NoButton,Qt.NoModifier,phase,False))
            self.app.processEvents()
        self.assertEqual(self.plan.property('zoom'), 2)
        self.assertEqual(self.plan.property('panX'), 260)
        self.assertEqual(self.plan.property('panY'), 245)

    def test_space_auto_repeat_and_chord_leave_a_drawing_untouched(self):
        self.controller.setTool('building')
        self.controller.setNavigation('autocad')
        self.reset_view()
        QTest.mouseMove(self.window,QPoint(400,300))
        QTest.keyPress(self.window,Qt.Key_Space)
        QTest.mouseMove(self.window,QPoint(460,330))
        for kind in (QEvent.KeyPress,QEvent.KeyRelease):
            self.app.sendEvent(self.window,QKeyEvent(kind,Qt.Key_Space,Qt.NoModifier,' ',True,1))
        self.assertTrue(self.plan.property('spaceHeld'))
        QTest.mouseMove(self.window,QPoint(470,340))
        QTest.keyRelease(self.window,Qt.Key_Space)
        self.assertFalse(self.plan.property('spaceHeld'))
        self.assertFalse(self.controller.drawing.points)
        self.assertEqual(self.plan.property('panX'),320)
        QTest.mousePress(self.window,Qt.LeftButton,Qt.NoModifier,QPoint(470,340))
        QTest.mousePress(self.window,Qt.RightButton,Qt.NoModifier,QPoint(470,340))
        QTest.mouseMove(self.window,QPoint(500,370))
        QTest.mouseRelease(self.window,Qt.RightButton,Qt.NoModifier,QPoint(500,370))
        QTest.mouseRelease(self.window,Qt.LeftButton,Qt.NoModifier,QPoint(500,370))
        self.assertFalse(self.controller.drawing.points)
        self.assertEqual(self.plan.property('panX'),350)
