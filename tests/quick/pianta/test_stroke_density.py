"""R35/R389: cosmetic plan pens have Widgets' physical width on dense screens."""
import unittest

from PySide6.QtCore import QPointF, QUrl, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest

from quick.pianta import test_window as window_tests

setUpModule = window_tests.setUpModule


class StrokeDensity(unittest.TestCase):
    setUp = window_tests.WindowTest.setUp
    tearDown = window_tests.WindowTest.tearDown

    def test_native_outline_integrated_coverage_matches_a_cosmetic_qpainter_pen(self):
        component = QQmlComponent(self.engine)
        component.setData(b'''import QtQuick
import Meridiana.Plan
Rectangle {
    anchors.fill: parent; color: "white"; z: 900
    property real penWidth: 2.6
    PolygonLayer {
        objects: [{kind:"building", points:[Qt.point(50,100),Qt.point(450,100)],
                   stroke:"red",fill:"transparent",closed:false,width:parent.penWidth}]
    }
}''', QUrl())
        cover = component.create()
        self.assertIsNotNone(cover, component.errors())
        cover.setParentItem(self.plan)
        for width in (1.6, 2.2, 2.6, 4.6, 5):
            cover.setProperty('penWidth', width)
            QTest.qWait(30)
            actual = self.window.grabWindow()
            dpr = actual.devicePixelRatio()
            expected = QImage(actual.size(), QImage.Format_ARGB32_Premultiplied)
            expected.setDevicePixelRatio(dpr)
            expected.fill(QColor('white'))
            painter = QPainter(expected)
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor('red'), width)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawLine(QPointF(50, 100), QPointF(450, 100))
            painter.end()

            def coverage(image):
                return sum(1-image.pixelColor(round(200*dpr), y).greenF()
                           for y in range(round(90*dpr), round(110*dpr)))

            self.assertAlmostEqual(coverage(actual), coverage(expected), delta=.15,
                                   msg=f'pen {width}, DPR {dpr}')
        self.assertFalse(self.warnings, self.warnings)
        cover.deleteLater()
