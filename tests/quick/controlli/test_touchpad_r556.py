"""R556: two fingers on a precision touchpad under Windows taken as on Linux (backend/touchpad.py, WindowsTouchpad).

Daniel (08/11/2026, Windows): «la navigazione con il touchpad non è il massimo [...] troppo sensibile, e lo scrolling
verticale con due dita fa zoom al posto di spostare». Windows gives Qt the touchpad as wheel angles without pixels or
phases: the plan and the 3D zoomed. Here synthetic events of both kinds: a mouse wheel's notches (120) go as they are,
a touchpad's small steps come out as pixels in scroll phases (begin, update, end), the pinch (Ctrl) goes as it is."""
import os
import tempfile
import unittest

import _setup
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QWheelEvent
from PySide6.QtQuick import QQuickView

from meridiana.quick.backend.touchpad import (WINDOWS_PIXELS_PER_UNIT, WINDOWS_STREAM_MS, WheelKind,
                                              WindowsTouchpad)
from quick.gestures import pump, wait_for

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

QML = b'''
import QtQuick
Rectangle {
    width: 400; height: 300
    property var seen: []
    WheelHandler {
        target: null
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: function(event) {
            seen.push([event.phase, event.angleDelta.x, event.angleDelta.y, event.pixelDelta.x, event.pixelDelta.y,
                       !!(event.modifiers & Qt.ControlModifier)])
            event.accepted = true
        }
    }
}
'''

class Recorder(QObject):
    def __init__(self, rows):
        super().__init__()
        self.rows = rows

    def eventFilter(self, _obj, event):
        if event.type() == QEvent.Type.Wheel:
            a, p = event.angleDelta(), event.pixelDelta()
            self.rows.append([int(event.phase().value), a.x(), a.y(), p.x(), p.y(),
                              bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)])
        return False


BEGIN, UPDATE, END, NONE = (int(p.value) for p in (Qt.ScrollPhase.ScrollBegin, Qt.ScrollPhase.ScrollUpdate,
                                                   Qt.ScrollPhase.ScrollEnd, Qt.ScrollPhase.NoScrollPhase))


def setUpModule():
    _setup.keep_global_state()


class Kind(unittest.TestCase):
    def test_notches_are_a_mouse_and_small_steps_a_touchpad(self):
        kind = WheelKind()
        self.assertFalse(kind.touchpad(0, 120, 1000))
        self.assertFalse(kind.touchpad(0, -240, 1020))          # a wheel spun fast: two notches at once
        self.assertTrue(kind.touchpad(0, 16, 2000))
        self.assertTrue(kind.touchpad(0, 120, 2010))            # within the gesture: the touchpad's too
        self.assertFalse(kind.touchpad(0, 120, 2010 + WINDOWS_STREAM_MS + 1))   # after a quiet: a notch again
        self.assertTrue(kind.touchpad(-37, 0, 4000))            # sideways too

    def test_what_windows_says_comes_first(self):
        kind = WheelKind()
        self.assertFalse(kind.touchpad(0, 15, 1000, 'mouse'))   # a high resolution wheel that Windows calls a mouse
        self.assertTrue(kind.touchpad(0, 120, 5000, 'touchpad'))


class Window(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        cls.view = QQuickView()
        cls.file = tempfile.NamedTemporaryFile('wb', suffix='.qml', delete=False)
        cls.file.write(QML)
        cls.file.close()
        cls.view.setSource(QUrl.fromLocalFile(cls.file.name))
        assert cls.view.rootObject() is not None, cls.view.errors()
        cls.view.show()
        pump(200)
        cls.time = 10000

    @classmethod
    def tearDownClass(cls):
        cls.view.close()
        cls.view.deleteLater()
        pump(20)
        os.unlink(cls.file.name)

    def setUp(self):
        self.rows = []
        self.recorder = Recorder(self.rows)
        self.view.installEventFilter(self.recorder)            # what reaches the window after the filter
        self.pad = WindowsTouchpad(active=True, source=lambda: None)
        self.view.installEventFilter(self.pad)                  # the last installed runs first
        self.addCleanup(self.view.removeEventFilter, self.pad)
        self.addCleanup(self.view.removeEventFilter, self.recorder)

    def wheel(self, dy, dx=0, mods=Qt.KeyboardModifier.NoModifier, gap=12):
        Window.time += gap
        point = QPointF(200, 150)
        event = QWheelEvent(point, QPointF(self.view.mapToGlobal(point.toPoint())), QPoint(), QPoint(dx, dy),
                            Qt.MouseButton.NoButton, mods, Qt.ScrollPhase.NoScrollPhase, False)
        event.setTimestamp(Window.time)
        self.app.sendEvent(self.view, event)

    def seen(self):
        return list(self.rows)

    def test_a_mouse_wheel_goes_as_it_is(self):
        self.wheel(120, gap=1000)
        self.wheel(-120, gap=300)
        self.assertEqual(self.seen(), [[NONE, 0, 120, 0, 0, False], [NONE, 0, -120, 0, 0, False]])

    def test_two_fingers_come_out_as_pixels_in_scroll_phases(self):
        self.wheel(16, gap=1000)
        self.wheel(24)
        self.wheel(120)                                         # a big step in the same gesture
        self.wheel(0, dx=-30)                                   # and sideways
        rows = self.seen()
        self.assertEqual([r[0] for r in rows], [BEGIN, UPDATE, UPDATE, UPDATE, UPDATE])
        self.assertEqual([r[4] for r in rows[1:4]], [round(16 * WINDOWS_PIXELS_PER_UNIT), 20, 100])
        self.assertEqual(rows[4][3], round(-30 * WINDOWS_PIXELS_PER_UNIT))
        wait_for(lambda: self.pad.gesture is None, 2)           # the quiet ends the gesture
        self.assertEqual(self.seen()[-1], [END, 0, 0, 0, 0, False])

    def test_the_pinch_with_ctrl_goes_as_it_is_and_ends_a_gesture(self):
        self.wheel(16, gap=1000)
        self.wheel(18, mods=Qt.KeyboardModifier.ControlModifier)
        rows = self.seen()
        self.assertEqual([r[0] for r in rows], [BEGIN, UPDATE, END, NONE])
        self.assertEqual(rows[-1], [NONE, 0, 18, 0, 0, True])


class Navigation(unittest.TestCase):
    """What the plan and the 3D do with them: their Navigation.js, the same function on Linux and Windows."""

    def test_the_plan_and_the_3d_pan_for_two_fingers_and_zoom_for_a_notch_or_a_pinch(self):
        from pathlib import Path
        from PySide6.QtQml import QJSEngine
        _setup.qt_or_skip()
        qml = Path(__file__).resolve().parents[3] / 'src/meridiana/quick/qml/Meridiana'
        for name in ('Plan/Navigation.js', 'View3D/Navigation.js'):
            engine = QJSEngine()
            source = (qml / name).read_text(encoding='utf-8').replace('.pragma library', '')
            engine.evaluate(source)
            act = engine.globalObject().property('wheelAction')

            def call(*args):
                return act.call([engine.toScriptValue(a) for a in args]).toVariant()
            # two fingers, as WindowsTouchpad gives them: pixels in a phase
            self.assertEqual(call([0, 16], [0, 13], True, False, False, False)[:3], ['pan', 0, 13], name)
            # a mouse wheel's notch: zoom
            self.assertEqual(call([0, 120], [0, 0], False, False, False, False)[0], 'wheel', name)
            # the pinch (Ctrl): zoom
            self.assertEqual(call([0, 18], [0, 0], False, False, True, False)[0], 'zoom', name)


if __name__ == '__main__':
    unittest.main()
