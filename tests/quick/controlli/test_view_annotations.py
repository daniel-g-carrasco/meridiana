"""The common view annotations keep their screen-space contract."""
import unittest

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from _setup import quick_app
from meridiana.gui.backend.tokens import install_theme
from quick.aiuti.view_grab import grab_item


def setUpModule():
    quick_app()


class ViewAnnotations(unittest.TestCase):
    def setUp(self):
        self.engine = QQmlEngine()
        install_theme(self.engine)

    def make(self, source):
        component = QQmlComponent(self.engine)
        component.setData(('import QtQuick\nimport Meridiana.Controls\n' + source).encode(), QUrl())
        obj = component.create()
        self.assertIsNotNone(obj, '\n'.join(e.toString() for e in component.errors()))
        QObject.setParent(obj, self.engine)
        self.addCleanup(obj.deleteLater)
        return obj

    def test_counter_round_for_one_digit_and_grows_for_two(self):
        obj = self.make('CountBadge { count: 8 }')
        self.assertEqual(obj.property('width'), obj.property('height'))
        obj.setProperty('count', 88)
        self.assertGreater(obj.property('width'), obj.property('height'))

    def test_pill_readable_for_any_direction(self):
        obj = self.make('LengthPill { value: "12 m" }')
        for direction in range(-720, 721, 15):
            obj.setProperty('direction', direction)
            self.assertGreaterEqual(obj.property('rotation'), -90)
            self.assertLess(obj.property('rotation'), 90)

    def test_stroke_has_uniform_light_halo_and_theme_dash(self):
        obj = self.make('ViewStroke { points: [Qt.point(0,0), Qt.point(100,0)] }')
        self.assertEqual(obj.property('thickness'), 1.5)
        self.assertAlmostEqual(obj.property('haloInk').alphaF(), .14, delta=.005)
        self.assertEqual(obj.property('haloExtra'), 2)

    def render(self, source):
        from PySide6.QtQuick import QQuickWindow
        from PySide6.QtTest import QTest
        window = QQuickWindow()
        window.resize(300, 200)
        item = self.make(source)
        item.setParent(window.contentItem())
        item.setParentItem(window.contentItem())
        self.addCleanup(window.deleteLater)
        self.addCleanup(window.close)
        window.show()
        QTest.qWaitForWindowExposed(window)
        return grab_item(item)

    def test_stroke_coverage_is_one_and_a_half_logical_pixels(self):
        picture = self.render('''Rectangle {
            width: 300; height: 200; color: "white"
            ViewStroke { anchors.fill: parent; ink: "red"
                points: [Qt.point(30,100),Qt.point(270,100)] }
        }''')
        dpr = picture.devicePixelRatio()
        coverage = sum((picture.pixelColor(round(150*dpr), y).redF()
                        - picture.pixelColor(round(150*dpr), y).greenF())
                       for y in range(round(90*dpr), round(110*dpr)))
        self.assertAlmostEqual(coverage/dpr, 1.5, delta=.15)

    def test_dash_rhythm_is_six_on_four_off_at_world_zoom(self):
        picture = self.render('''Rectangle {
            width: 300; height: 200; color: "white"
            Item { width: 30; height: 20; scale: 10; transformOrigin: Item.TopLeft
                ViewStroke { anchors.fill: parent; ink: "red"; dashed: true; viewScale: 10
                    points: [Qt.point(2,10),Qt.point(28,10)] }
            }
        }''')
        dpr = picture.devicePixelRatio()
        def red_at(px):
            return sum(picture.pixelColor(round(px*dpr), y).redF()
                       - picture.pixelColor(round(px*dpr), y).greenF()
                       for y in range(round(90*dpr), round(110*dpr))) / dpr
        for x in range(22, 252, 10):
            self.assertGreater(red_at(x), .8, x)
            self.assertLess(red_at(x+6), .2, x+6)

    def test_production_polygon_keeps_its_width_at_world_zoom(self):
        picture = self.render('''import Meridiana.Plan as MeridianaPlan
        import Meridiana.Theme
        Rectangle {
            width: 300; height: 200; color: "white"; clip: true
            Item { anchors.fill: parent
                layer.enabled: GraphicsInfo.api !== GraphicsInfo.Software
                layer.samples: Theme.annotation.SAMPLES
            Item { x:317.5; y:207; scale: 2.675; transformOrigin: Item.TopLeft
                MeridianaPlan.PolygonLayer {
                    halo: true
                    patternTransform: Qt.matrix4x4(.3738318,0,0,-118.69,0,.3738318,0,-77.38,0,0,1,0,0,0,0,1)
                    objects: [{kind:"building",points:[Qt.point(-100,-40),Qt.point(-20,-40),
                                                       Qt.point(-20,-20),Qt.point(-100,-20)],
                               stroke:"red",fill:"#280000ff",closed:true}]
                }
            }
            }
        }''')
        dpr = picture.devicePixelRatio()
        coverage = sum((picture.pixelColor(round(150*dpr), y).redF()
                        - picture.pixelColor(round(150*dpr), y).greenF())
                       for y in range(round(90*dpr), round(110*dpr)))
        self.assertAlmostEqual(coverage/dpr, 1.5, delta=.15)
