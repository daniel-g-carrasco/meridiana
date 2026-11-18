"""R545: two fingers on the touchpad in the areas that scroll (M.ScrollPage, M.List, M.Table).

Daniel (08/11/2026, Linux): «lo scrolling in verticale è troppo troppo lento e lo scrolling laterale non funziona».
Measured on the Framework under Niri with a virtual touchpad (docs/quick/stato/r24-finestra.md): Qt Quick moves by the
pixels Wayland gives, one to one, 2.5 times less than every GTK 4 window for the same fingers. backend/touchpad.py
multiplies them by GTK 4's 2.5 before Qt Quick delivers them; the angles of Windows and of a mouse wheel go as they are.
Here every component with the events of both systems: Wayland's (pixels in scroll phases) vertical and sideways, with
and without the pace, and Windows' (angles without phases) vertical and sideways."""
import os
import tempfile
import unittest

import _setup
from PySide6.QtCore import QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QInputDevice, QPointingDevice, QWheelEvent
from PySide6.QtQuick import QQuickView

from meridiana.quick.backend.controls import install_controls
from meridiana.quick.backend.touchpad import GTK_SCROLL_FACTOR, TouchpadPace
from quick.gestures import pump, wait_for

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

QML = b'''
import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M
Rectangle {
    width: 960; height: 400; color: Theme.colors.window
    M.ScrollPage { objectName: "page"; x: 0; width: 300; height: 400
        Repeater { model: 80; Rectangle { width: 200; height: 24; color: index % 2 ? "#ccc" : "#eee" } } }
    M.List { objectName: "list"; x: 320; width: 300; height: 400
        model: { const rows = []; for (let i = 0; i < 200; i++) rows.push({text: "Riga " + i}); return rows } }
    M.Table { objectName: "table"; x: 640; width: 300; height: 400
        columns: { const cols = []; for (let i = 0; i < 12; i++) cols.push({key: "c" + i, title: "C" + i, minWidth: 120}); return cols }
        model: { const rows = []; for (let r = 0; r < 200; r++) { const row = {}; for (let i = 0; i < 12; i++) row["c" + i] = r * i; rows.push(row) } return rows } }
}
'''

PAD = None


def pad():
    global PAD
    if PAD is None:
        PAD = QPointingDevice('r545 pad', 545, QInputDevice.DeviceType.TouchPad, QPointingDevice.PointerType.Finger,
                              QInputDevice.Capability.Position | QInputDevice.Capability.PixelScroll, 5, 0)
    return PAD


def setUpModule():
    _setup.keep_global_state()


class ScrollingAreas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        cls.view = QQuickView()
        install_controls(cls.view.engine(), dict(theme='light', reducedMotion=True))
        cls.file = tempfile.NamedTemporaryFile('wb', suffix='.qml', delete=False)
        cls.file.write(QML)
        cls.file.close()
        cls.view.setSource(QUrl.fromLocalFile(cls.file.name))
        assert cls.view.rootObject() is not None, cls.view.errors()
        cls.view.show()
        pump(300)
        cls.pace = TouchpadPace(active=True)
        cls.time = 1000

    @classmethod
    def tearDownClass(cls):
        cls.view.close()
        cls.view.deleteLater()
        pump(20)
        os.unlink(cls.file.name)

    def flick(self, name):
        root = self.view.rootObject()
        found = [item for item in root.findChildren(object) if getattr(item, 'objectName', lambda: '')() == name]
        holder = found[0]
        for candidate in [holder] + holder.findChildren(object):
            try:
                if candidate.metaObject().indexOfProperty('contentY') >= 0 and candidate.property('height') > 100:
                    return holder, candidate
            except (AttributeError, RuntimeError):
                continue
        raise AssertionError('no Flickable in ' + name)

    def send(self, at, pixel, angle, phase, device, paced):
        self.__class__.time += 8
        event = QWheelEvent(at, at, QPoint(*pixel), QPoint(*angle), Qt.NoButton, Qt.NoModifier, phase, False,
                            Qt.MouseEventSynthesizedBySystem if phase != Qt.NoScrollPhase else Qt.MouseEventNotSynthesized,
                            device)
        event.setTimestamp(self.time)
        if paced and self.pace.eventFilter(self.view, event):
            return
        QGuiApplication.sendEvent(self.view, event)

    def wayland(self, name, step, count=30, paced=True):
        """Two fingers as Wayland gives them: Begin, `count` updates of `step` pixels (angle twelve times), End."""
        holder, flick = self.flick(name)
        flick.setProperty('contentX', 0)
        flick.setProperty('contentY', 0)
        pump(30)
        at = holder.mapToScene(QPointF(holder.width() / 2, holder.height() / 2))
        self.send(at, (0, 0), (0, 0), Qt.ScrollBegin, pad(), paced)
        for _ in range(count):
            self.send(at, step, (step[0] * 12, step[1] * 12), Qt.ScrollUpdate, pad(), paced)
            pump(1)
        self.send(at, (0, 0), (0, 0), Qt.ScrollEnd, pad(), paced)
        pump(60)
        return flick.property('contentX'), flick.property('contentY')

    def windows(self, name, angle, notches=3):
        """A precision touchpad or a wheel on Windows: angles, no phase, no pixels."""
        holder, flick = self.flick(name)
        flick.setProperty('contentX', 0)
        flick.setProperty('contentY', 0)
        pump(30)
        at = holder.mapToScene(QPointF(holder.width() / 2, holder.height() / 2))
        for _ in range(notches):
            self.send(at, (0, 0), angle, Qt.NoScrollPhase, QPointingDevice.primaryPointingDevice(), True)
            pump(20)
        wait_for(lambda: not flick.property('moving'), 5)
        return flick.property('contentX'), flick.property('contentY')

    def test_vertical_pixels_move_at_the_pace_of_gtk(self):
        for name in ('page', 'list', 'table'):
            with self.subTest(name=name):
                _x, raw = self.wayland(name, (0, -2), paced=False)
                _x, paced = self.wayland(name, (0, -2))
                # one to one: 30 events of 2 px, less the first two (Flickable starts its clock on them)
                self.assertGreaterEqual(raw, 54)
                self.assertLessEqual(raw, 60)
                self.assertAlmostEqual(paced, raw * GTK_SCROLL_FACTOR, delta=3)

    def test_sideways_pixels_scroll_the_wide_table(self):
        raw, _y = self.wayland('table', (-2, 0), paced=False)
        x, y = self.wayland('table', (-2, 0))
        self.assertGreaterEqual(raw, 54)
        self.assertAlmostEqual(x, raw * GTK_SCROLL_FACTOR, delta=3)
        self.assertEqual(y, 0)

    def test_windows_angles_scroll_vertically_and_sideways(self):
        for name in ('page', 'list', 'table'):
            with self.subTest(name=name):
                _x, y = self.windows(name, (0, -120))
                self.assertGreater(y, 40)
        x, _y = self.windows('table', (-120, 0))
        self.assertGreater(x, 40)


class Pace(unittest.TestCase):
    """backend/touchpad.TouchpadPace on its own: what it changes and what it leaves."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def event(self, pixel, angle, phase):
        return QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(*pixel), QPoint(*angle), Qt.NoButton, Qt.NoModifier,
                           phase, True, Qt.MouseEventSynthesizedBySystem, pad())

    def test_pixels_in_a_phase_are_multiplied_with_the_remainder_carried(self):
        pace = TouchpadPace(active=True)
        self.assertIsNone(pace.scaled(self.event((0, 0), (0, 0), Qt.ScrollBegin)))
        moved = [pace.scaled(self.event((0, 1), (0, 13), Qt.ScrollUpdate)) for _ in range(4)]
        self.assertEqual([e.pixelDelta().y() for e in moved], [2, 3, 2, 3])          # 2.5 each, nothing lost
        self.assertEqual(moved[0].angleDelta().y(), 32)
        self.assertTrue(moved[0].inverted())
        self.assertEqual(moved[0].phase(), Qt.ScrollUpdate)
        self.assertIsNone(pace.scaled(self.event((0, 0), (0, 0), Qt.ScrollEnd)))
        self.assertEqual(pace.carry, [0.0, 0.0])

    def test_wheel_windows_and_other_platforms_go_as_they_are(self):
        pace = TouchpadPace(active=True)
        self.assertIsNone(pace.scaled(self.event((0, 0), (0, -120), Qt.NoScrollPhase)))     # a wheel, Windows
        self.assertIsNone(pace.scaled(self.event((0, 0), (0, -40), Qt.ScrollUpdate)))       # angles only
        self.assertIsNone(TouchpadPace(active=False).scaled(self.event((0, 3), (0, 36), Qt.ScrollUpdate)))


if __name__ == '__main__':
    unittest.main()
