"""R545 in the plan: two fingers sideways move it (R189, R242: two fingers move, no rotation from the touchpad, the pinch
zooms around the pointer).

Daniel (08/11/2026, Linux): «lo scrolling laterale non funziona». The plan read the wheel with one WheelHandler, whose
`orientation` is Qt.Vertical: until it is active it refuses an event with no y, so a sideways gesture (Wayland's
pixels or Windows' WM_MOUSEHWHEEL angles) never reached it; seen on the Framework with a virtual touchpad: 24 events
of one pixel sideways, the plan still. A twin with Qt.Horizontal takes those, and only those."""
import os
import unittest
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QInputDevice, QPointingDevice, QWheelEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from meridiana import model
from meridiana.quick.backend.plan import PlanController
from quick.gestures import wait_for

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


class SidewaysPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.pad = QPointingDevice('r545 plan pad', 546, QInputDevice.DeviceType.TouchPad,
                                  QPointingDevice.PointerType.Finger,
                                  QInputDevice.Capability.Position | QInputDevice.Capability.PixelScroll, 5, 0)

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
        wait_for(lambda: self.window.findChild(QObject, 'plan') is not None, 10)
        self.plan = self.window.findChild(QObject, 'plan')
        for name, value in (('zoom', 2.), ('panX', 250.), ('panY', 250.)):
            self.plan.setProperty(name, value)
        self.time = 5000

    def tearDown(self):
        self.window.close()
        self.controller.close()
        self.engine.deleteLater()
        self.app.processEvents()

    def send(self, pixel, angle, phase, device=None, modifiers=Qt.NoModifier):
        self.time += 8
        source = Qt.MouseEventNotSynthesized if phase == Qt.NoScrollPhase else Qt.MouseEventSynthesizedBySystem
        event = QWheelEvent(QPointF(400, 300), QPointF(400, 300), QPoint(*pixel), QPoint(*angle), Qt.NoButton,
                            modifiers, phase, False, source, device or self.pad)
        event.setTimestamp(self.time)
        QGuiApplication.sendEvent(self.window, event)
        self.app.processEvents()

    def gesture(self, step, count=10):
        self.send((0, 0), (0, 0), Qt.ScrollBegin)
        for _ in range(count):
            self.send(step, (step[0] * 12, step[1] * 12), Qt.ScrollUpdate)
        self.send((0, 0), (0, 0), Qt.ScrollEnd)

    def view(self):
        return tuple(round(self.plan.property(name), 3) for name in ('panX', 'panY', 'zoom'))

    def test_wayland_two_fingers_sideways_move_the_plan(self):
        self.gesture((-3, 0))
        self.assertEqual(self.view(), (220, 250, 2))
        self.gesture((4, 0))
        self.assertEqual(self.view(), (260, 250, 2))
        self.assertFalse(self.errors, self.errors)

    def test_wayland_vertical_and_diagonal_move_once(self):
        self.gesture((0, -2))
        self.assertEqual(self.view(), (250, 230, 2))
        self.gesture((3, -1))                    # active upright handler: the twin must not move it a second time
        self.assertEqual(self.view(), (280, 220, 2))
        self.send((0, 0), (0, 0), Qt.ScrollBegin)
        self.send((0, -2), (0, -24), Qt.ScrollUpdate)
        self.send((5, 0), (60, 0), Qt.ScrollUpdate)        # sideways inside a gesture that began upright: once
        self.send((0, 0), (0, 0), Qt.ScrollEnd)
        self.assertEqual(self.view(), (285, 218, 2))

    def test_windows_sideways_angles_pan_and_the_vertical_wheel_still_zooms(self):
        mouse = QPointingDevice.primaryPointingDevice()
        self.send((0, 0), (-120, 0), Qt.NoScrollPhase, mouse)        # WM_MOUSEHWHEEL of a precision touchpad
        self.assertEqual(self.view(), (130, 250, 2))
        upright = self.window.findChild(QObject, 'uprightWheel')      # its activeTimeout ends the sideways gesture
        wait_for(lambda: not upright.property('active') and not self.window.findChild(QObject, 'sidewaysWheel').property('active'), 5)
        self.send((0, 0), (0, 120), Qt.NoScrollPhase, mouse)          # a notch of the wheel: zoom at the pointer
        self.assertAlmostEqual(self.plan.property('zoom'), 2.4)
        self.assertFalse(self.errors, self.errors)


if __name__ == '__main__':
    unittest.main()
