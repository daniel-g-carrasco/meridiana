"""R174/R389: north arrow, corner travel, and the same 1-2-5 scale as the core."""

import math
import time
import unittest
from pathlib import Path

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QPoint, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow  # noqa: F401
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication

from meridiana import viewaids
from meridiana.quick.backend.tokens import install_theme


class AidsQuick(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wait(self, condition):
        end = time.monotonic() + 5
        while not condition() and time.monotonic() < end:
            self.app.processEvents()
            time.sleep(.002)
        self.assertTrue(condition())

    def setUp(self):
        self.engine = QQmlApplicationEngine()
        self.theme = install_theme(self.engine)
        self.errors = []
        self.engine.warnings.connect(lambda errors: self.errors.extend(error.toString() for error in errors))
        layer = Path(__file__).resolve().parents[3] / 'src/meridiana/quick/qml/Meridiana/Plan'
        self.engine.loadData(('import QtQuick\nimport QtQuick.Window\nimport "' + layer.as_uri() + '"\n'
                             'Window { width: 500; height: 350; visible: true; color:"#2b2f33"; '
                             'Compass { objectName:"compass"; x:436; y:8 } '
                             'ScaleBar { objectName:"scaleBar"; x:8; y:314; metresPerPixel:.1 } }').encode(),
                            QUrl('file:///aids-test.qml'))
        self.assertTrue(self.engine.rootObjects(), self.errors)
        self.window = self.engine.rootObjects()[0]
        self.wait(lambda: self.window.isExposed())
        self.compass = self.window.findChild(QObject, 'compass')
        self.bar = self.window.findChild(QObject, 'scaleBar')

    def tearDown(self):
        self.window.close()
        self.engine.deleteLater()
        self.app.processEvents()

    def test_centre_stays_fixed_letter_follows_north_and_real_click_requests_reset(self):
        self.assertEqual((self.compass.width(), self.compass.height()), (56, 78))
        self.assertEqual(self.compass.property('headingText'), '0° N')
        for angle in (0, 45, 90, 150, 270):
            self.compass.setProperty('angle', angle)
            self.app.processEvents()
            letter = self.compass.property('letterCentre')
            self.assertAlmostEqual((letter.x() - 28) ** 2 + (letter.y() - 28) ** 2, 18.5 ** 2)
            if angle == 90:
                self.assertAlmostEqual(letter.x(), 9.5)
                self.assertAlmostEqual(letter.y(), 28)
            grab = self.window.grabWindow()
            dpr = grab.devicePixelRatio()
            self.assertGreater(grab.pixelColor(round((436 + 28) * dpr), round((8 + 28) * dpr)).lightness(), 180)
        self.compass.setProperty('angle', 30)
        self.assertEqual(self.compass.property('headingText'), '30° NE')
        spy = QSignalSpy(self.compass.north)
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, QPoint(464, 36))
        self.assertEqual(spy.count(), 1)
        folder = Path('build/quick-foto/pianta')
        folder.mkdir(parents=True, exist_ok=True)
        grab = self.window.grabWindow()
        grab.save(str(folder / f'aids-{grab.devicePixelRatio():g}x.png'))
        self.assertFalse(self.errors, self.errors)

    def place(self, x, y, lower):
        self.assertTrue(QMetaObject.invokeMethod(self.compass, 'placeAt', Q_ARG('QVariant', x),
                                                Q_ARG('QVariant', y), Q_ARG('QVariant', lower)))

    def test_corner_change_animates_once_latest_target_wins_and_reduced_motion_is_immediate(self):
        self.place(436, 8, False)
        self.place(436, 236, True)
        self.assertTrue(self.compass.property('travelling'))
        self.place(436, 236, True)
        self.place(436, 8, False)
        self.wait(lambda: not self.compass.property('travelling'))
        self.assertAlmostEqual(self.compass.y(), 8)
        self.theme.configure({'reducedMotion': True})
        self.place(436, 236, True)
        self.assertFalse(self.compass.property('travelling'))
        self.assertAlmostEqual(self.compass.y(), 236)
        self.place(400, 246, True)
        self.assertFalse(self.compass.property('travelling'))
        self.assertEqual((self.compass.x(), self.compass.y()), (400, 246))

    def test_scale_has_round_lengths_cm_m_km_and_fixed_pixel_height(self):
        for mpp in (.001, .003, .01, .1, 1, 12, 170, 1500):
            self.bar.setProperty('metresPerPixel', mpp)
            self.app.processEvents()
            length, pixels = viewaids.scale_bar(mpp)
            self.assertAlmostEqual(self.bar.property('length'), length)
            self.assertAlmostEqual(self.bar.property('pixels'), pixels)
            self.assertLessEqual(pixels, 120)
            self.assertIn(round(length / 10 ** math.floor(math.log10(length)), 9), (1, 2, 5))
            self.assertEqual(self.bar.property('text'), viewaids.length_text(length))
            self.assertEqual(self.bar.height(), 28)
        self.assertFalse(self.errors, self.errors)


if __name__ == '__main__':
    unittest.main()
