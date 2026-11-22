"""R688 (Daniel 16/11/2026): «la rotella sulla barra dell'ora non può essere mossa con la rotella del mouse, e
muovendo premendo il pallino, non mi permette di essere molto preciso (un po' scattante)». The hour's slider counts
minutes so a drag is smooth, and rests on ten minutes when let go; the wheel moves ten minutes a notch (Daniel
17/11/2026: «io terrei 10 minuti, al minuto è troppo granulare»), and what it sets reaches the backend as hours."""

import tempfile
import unittest
from pathlib import Path

import _setup

VIEW3D = Path(__file__).resolve().parents[3] / 'src' / 'meridiana' / 'gui' / 'qml' / 'Meridiana' / 'View3D'

QML = '''
import QtQuick
import "%s" as V
Item {
    width: 700; height: 60
    QtObject {
        id: fake; objectName: "fake"
        property real asked: -1
        property var sunData: ({year: 2026, month: 12, day: 21, hour: 12.5, clock: "12:30", description: "", short: ""})
        // as the real one (scene.py): the hour told comes back in the sun's data, on ten minutes
        function setSun(y, m, d, h) { asked = h; sunData = Object.assign({}, sunData, {hour: Math.round(h * 6) / 6}) }
        function playSun(p) {}
        function stepSun() {}
        function shiftSunDay(n) {}
        function designSun() {}
    }
    V.SunBar { objectName: "bar"; anchors.fill: parent; backend: fake }
}
'''


def setUpModule():
    _setup.keep_global_state()


class HourSlider(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQuick import QQuickView
        from meridiana.gui.backend.controls import install_controls
        _setup.qt_or_skip()
        cls.app = QGuiApplication.instance()
        cls.view = QQuickView()
        install_controls(cls.view.engine(), dict(theme='light', reducedMotion=True))
        cls.file = tempfile.NamedTemporaryFile('w', suffix='.qml', delete=False, encoding='utf-8')
        cls.file.write(QML % VIEW3D.as_uri())
        cls.file.close()
        cls.view.setSource(QUrl.fromLocalFile(cls.file.name))
        assert not cls.view.errors(), cls.view.errors()
        cls.view.show()

    @classmethod
    def tearDownClass(cls):
        cls.view.close()
        cls.view.deleteLater()
        Path(cls.file.name).unlink()

    def slider(self):
        from PySide6.QtQuick import QQuickItem
        return self.view.rootObject().findChild(QQuickItem, 'sunHour')

    def wheel_on_slider(self, notches, shift=False, delta=120):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from quick.gestures import pump
        s = self.slider()
        pos = s.mapToScene(QPointF(s.width() / 2, s.height() / 2))
        modifiers = Qt.KeyboardModifier.ShiftModifier if shift else Qt.KeyboardModifier.NoModifier
        for _ in range(abs(notches)):
            dy = delta if notches > 0 else -delta
            self.app.sendEvent(self.view, QWheelEvent(pos, QPointF(self.view.mapToGlobal(pos.toPoint())), QPoint(),
                                                      QPoint(0, dy), Qt.MouseButton.NoButton, modifiers,
                                                      Qt.ScrollPhase.NoScrollPhase, False))
            pump()
        pump(200)                                   # the slider tells the backend once it rests

    def test_the_slider_counts_minutes(self):
        s = self.slider()
        self.assertEqual(s.property('to'), 1430)
        self.assertEqual(s.property('stepSize'), 10)
        self.assertEqual(s.property('value'), 750)  # 12:30

    def test_the_wheel_moves_ten_minutes_a_notch_and_a_touchpad_adds_up_to_ten(self):
        fake = self.view.rootObject().findChild(__import__('PySide6.QtCore', fromlist=['QObject']).QObject, 'fake')
        start = self.slider().property('value')
        self.wheel_on_slider(2)
        self.assertEqual(self.slider().property('value'), start + 20)
        self.assertAlmostEqual(fake.property('asked'), (start + 20) / 60)
        self.wheel_on_slider(-1, shift=True)       # Shift no longer means one minute
        self.assertEqual(self.slider().property('value'), start + 10)
        self.wheel_on_slider(3, delta=40)           # a touchpad: three thirds of a notch make one step
        self.assertEqual(self.slider().property('value'), start + 20)
        self.assertAlmostEqual(fake.property('asked'), (start + 20) / 60)


    def test_after_the_wheel_the_slider_still_follows_the_sun(self):
        """Daniel 17/11/2026: «non funziona la barra dell'ora come dovrebbe». The wheel wrote the slider's value from
        QML and cut its binding to the sun: Play, the day's arrows, a project opened, nothing moved the knob any more."""
        from PySide6.QtCore import QObject
        from quick.gestures import pump
        fake = self.view.rootObject().findChild(QObject, 'fake')
        start = fake.property('sunData').toVariant()
        try:
            self.wheel_on_slider(1)
            fake.setProperty('sunData', {**start, 'hour': 15.0})   # as Play's step, or another day chosen, brings it
            pump(50)
            self.assertEqual(self.slider().property('value'), 900)
        finally:
            fake.setProperty('sunData', start)
            pump(50)


if __name__ == '__main__':
    unittest.main()
