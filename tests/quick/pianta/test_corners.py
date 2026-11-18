"""R77/R389: the plan's four corners match ui.cards.Corner, including overdraw."""
import math
from pathlib import Path
import unittest

from PySide6.QtCore import QRectF, QUrl
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest

from meridiana.quick.backend.controls import install_controls
from meridiana.ui.design import Radius
from quick.pianta import test_window as window_tests

setUpModule = window_tests.setUpModule


class Corners(unittest.TestCase):
    setUp = window_tests.WindowTest.setUp
    tearDown = window_tests.WindowTest.tearDown

    def test_all_four_corners_match_widgets_after_theme_resize_and_overdraw(self):
        # Simulate map/geometry crossing every edge, above the regular scene.
        component = QQmlComponent(self.engine)
        component.setData(b'import QtQuick\nRectangle { anchors.fill: parent; color: "#237d62"; z: 900 }', QUrl())
        cover = component.create()
        self.assertIsNotNone(cover, component.errors())
        cover.setParentItem(self.plan)
        tokens = install_controls(self.engine)
        folder = Path(__file__).resolve().parents[3]/'build/quick-foto/pianta/corners'
        folder.mkdir(parents=True, exist_ok=True)
        for theme, size in (('light', (1366, 900)), ('dark', (1600, 960))):
            with self.subTest(theme=theme):
                tokens.configure({'theme': theme})
                self.window.resize(*size)
                QTest.qWait(100)
                image = self.window.grabWindow()
                dpr, r = image.devicePixelRatio(), Radius.VIEW
                bg, ink = QColor('#237d62'), QColor(tokens.colors['panel'])
                for which in range(4):
                    right, bottom = which in (1, 3), which in (2, 3)
                    x, y = (self.plan.width()-r if right else 0), (self.plan.height()-r if bottom else 0)
                    actual = image.copy(round(x*dpr), round(y*dpr), round(r*dpr), round(r*dpr))
                    expected = QImage(actual.size(), QImage.Format_ARGB32_Premultiplied)
                    expected.setDevicePixelRatio(dpr)
                    expected.fill(bg)
                    # Same path subtraction as ui.cards.Corner.paintEvent.
                    rest, arc = QPainterPath(), QPainterPath()
                    rest.addRect(QRectF(0, 0, r, r))
                    arc.addRoundedRect(QRectF(-r if right else 0, -r if bottom else 0, 2*r, 2*r), r, r)
                    painter = QPainter(expected)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.fillPath(rest.subtracted(arc), ink)
                    painter.end()
                    for px in range(actual.width()):
                        for py in range(actual.height()):
                            cx, cy = (0 if right else r), (0 if bottom else r)
                            distance = math.hypot((px+.5)/dpr-cx, (py+.5)/dpr-cy)
                            # Different rasterisers may cover the boundary pixel differently.
                            if abs(distance-r) > 1/dpr:
                                self.assertEqual(actual.pixelColor(px, py), expected.pixelColor(px, py),
                                                 (theme, which, px, py))
                    actual.save(str(folder/f'{theme}-{which}-quick.png'))
                    expected.save(str(folder/f'{theme}-{which}-widgets.png'))
                self.assertFalse(self.warnings, self.warnings)
        cover.deleteLater()
