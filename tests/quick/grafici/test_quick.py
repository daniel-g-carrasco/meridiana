"""Real Qt input on retained charts; no desktop mouse or keyboard control."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from PySide6.QtCore import QPoint, QPointF, QUrl, Qt, QObject
from PySide6.QtGui import QWheelEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow  # noqa: F401
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import _setup
from meridiana import i18n
from meridiana.quick.backend import charts_bridge, charts_data
from meridiana.quick.backend import charts_scene

ROOT = Path(__file__).resolve().parents[3]
QML = ROOT / "src/meridiana/quick/qml"
setUpModule = _setup.keep_global_state


def item_named(item, name):
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = item_named(child, name)
        if found is not None:
            return found
    return None


def theme_class():
    try:
        from meridiana.quick.backend.tokens import ThemeTokens
        return ThemeTokens, QML
    except ModuleNotFoundError:
        sibling = ROOT.parent / "meridiana-wt-r12-sistema/src/meridiana/quick"
        spec = importlib.util.spec_from_file_location("quick_theme_for_chart_tests", sibling / "backend/tokens.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ThemeTokens, sibling / "qml"


class QuickTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        i18n.setup("it")
        charts_bridge.register()

    def setUp(self):
        self.engine = QQmlApplicationEngine()
        from meridiana.quick.backend.controls import install_controls
        self.theme = install_controls(self.engine)
        self.engine.addImportPath(str(QML))
        self.engine.rootContext().setContextProperty("themeTokens", self.theme)
        self.data = charts_data.line(list(range(168)), [("load", [i%24+2 for i in range(168)])], "kW",
                                     title="Weekly load").to_dict()
        self.engine.rootContext().setContextProperty("testData", self.data)
        self.warnings = []
        self.engine.warnings.connect(lambda errors: self.warnings.extend(e.toString() for e in errors))
        self.engine.loadData(b'''import QtQuick
import Meridiana.Charts
Window { width: 1000; height: 600; visible: true
 Chart { objectName: "chart"; anchors.fill: parent; chartData: testData }
}''', QUrl.fromLocalFile(str(QML / "test.qml")))
        self.assertTrue(self.engine.rootObjects(), self.warnings)
        self.window = self.engine.rootObjects()[0]
        self.chart = self.window.findChild(QObject, "chart")
        QTest.qWait(250)

    def tearDown(self):
        if hasattr(self, "window"):
            self.window.close()
        self.engine.deleteLater()
        self.app.processEvents()

    def test_ground_is_the_cards_and_grid_and_text_follow_the_theme_r494(self):
        # R494 (Daniel 06/11/2026, style B): no ground of the chart's own, the card's shows through; grid, axes, text,
        # band and card from the theme's tokens, so they read in light and dark on any card.
        from PySide6.QtGui import QColor
        engine = QQmlApplicationEngine()
        from meridiana.quick.backend.controls import install_controls
        theme = install_controls(engine)
        engine.addImportPath(str(QML))
        data = charts_data.bars(["gen", "feb", "mar"], [("F1", [10, 20, 15]), ("F2", [5, 4, 6])], "kWh",
                                stacked=True).to_dict()
        engine.rootContext().setContextProperty("cardData", data)
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
        engine.loadData(b'''import QtQuick
import Meridiana.Theme
import Meridiana.Charts
Window { width: 900; height: 520; visible: true; color: Theme.colors.window
 Rectangle { objectName: "card"; anchors.fill: parent; anchors.margins: 20; color: Theme.colors.panel
  Chart { objectName: "chart"; anchors.fill: parent; anchors.margins: 12; chartData: cardData } }
}''', QUrl.fromLocalFile(str(QML / "test-ground.qml")))
        self.assertTrue(engine.rootObjects(), warnings)
        window = engine.rootObjects()[0]
        self.addCleanup(lambda: (window.close(), engine.deleteLater(), self.app.processEvents()))
        chart, card = window.findChild(QObject, "chart"), window.findChild(QObject, "card")
        inks = {}
        for dark in (False, True):
            theme.configure({"dark": dark, "reducedMotion": True})
            QTest.qWait(150)
            colors = chart.property("colors")
            drawing = item_named(chart, "chartDrawing")
            self.assertEqual(drawing.property("color").alpha(), 0, "the chart paints no ground of its own")
            ground = card.property("color").name()
            self.assertEqual(chart.property("ground").name(), ground)
            plot = item_named(chart, "plotArea")
            image = window.grabWindow()
            ratio = image.devicePixelRatio()
            corner = plot.mapToScene(QPointF(plot.width() - 6, 6))        # above the bars, under no grid line
            self.assertEqual(image.pixelColor(int(corner.x()*ratio), int(corner.y()*ratio)).name(), ground)
            self.assertEqual(chart.property("ink").name(), QColor(colors["text"]).name())
            self.assertEqual(chart.property("ink2").name(), QColor(colors["text2"]).name())
            self.assertEqual(chart.property("muted").name(), QColor(colors["muted"]).name())
            grid = (colors.get("chart") or {}).get("grid") or colors["line_soft"]
            self.assertEqual(chart.property("grid").name(), QColor(grid).name())
            inks[dark] = QColor(colors["text"]).lightnessF()
            series = chart.property("seriesColors")
            self.assertEqual([QColor(c).name() for c in series[:3]],
                             charts_scene.SERIES[dark][:3])
        self.assertLess(inks[False], .3)
        self.assertGreater(inks[True], .7)
        self.assertEqual(warnings, [])

    def test_hover_zoom_reset_legend_and_table(self):
        QTest.mouseMove(self.window, QPoint(420, 220))
        QTest.qWait(30)
        self.assertIn("kW", self.chart.property("readout"))
        wheel = QWheelEvent(QPointF(420, 220), QPointF(420, 220), QPoint(0, 0), QPoint(0, 120),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        self.app.sendEvent(self.window, wheel)
        # One notch has the same sensitivity as the Widgets view, centred on the pointer.
        self.assertAlmostEqual(self.chart.property("viewEnd")-self.chart.property("viewStart"), 1.02**-15)
        QTest.mouseDClick(self.window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(420, 220))
        self.assertEqual(self.chart.property("viewStart"), 0)
        self.assertEqual(self.chart.property("viewEnd"), 1)
        button = item_named(self.window.contentItem(), "tableButton")
        at = button.mapToScene(QPointF(button.width()/2, button.height()/2))
        QTest.mouseClick(self.window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, at.toPoint())
        QTest.qWait(150)
        self.assertTrue(self.chart.property("tableMode"))
        self.assertFalse(self.warnings, self.warnings)

    def change_data(self, data):
        self.data = data
        self.engine.rootContext().setContextProperty("testData", data)
        QTest.qWait(80)

    def test_legend_click_changes_pixels_without_rebuilding_series(self):
        data = charts_data.bars(["A", "B"], [("one", [10, 20]), ("two", [20, 10])], "kWh").to_dict()
        self.change_data(data)
        QTest.mouseMove(self.window, QPoint(420, 220))
        self.assertIn("one", self.chart.property("readout"))
        before = self.window.grabWindow()
        # The Widgets legend stands below the plot, with the same clickable entries.
        entry = item_named(self.window.contentItem(), "legend-entry-0")
        pos = entry.mapToScene(QPointF(entry.width()/2, entry.height()/2)).toPoint()
        with patch.object(charts_scene, "prepare", wraps=charts_scene.prepare) as prepare:
            QTest.mouseClick(self.window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                             pos)
            QTest.qWait(60)
            self.assertEqual(prepare.call_count, 0)
        hidden = self.chart.property("hiddenSeries")
        hidden = hidden.toVariant() if hasattr(hidden, "toVariant") else hidden
        self.assertEqual(hidden, ["one"])
        self.assertEqual(self.chart.property("readout"), "")
        self.assertNotEqual(before, self.window.grabWindow())
        QTest.mouseMove(self.window, QPoint(430, 220))
        self.assertNotIn("one", self.chart.property("readout"))
        self.change_data(charts_data.bars(["A"], [("new", [3000])], "kWh").to_dict())
        # Qt can send a fresh hover after replacing the item under the pointer.
        self.assertNotIn("two", self.chart.property("readout"))
        if self.chart.property("readout"):
            self.assertIn("3000", self.chart.property("readout").replace("\u00a0", "").replace(".", ""))
        self.assertFalse(self.warnings, self.warnings)

    def test_band_pan_and_export_range_remain_in_domain(self):
        with patch.object(charts_scene, "prepare", wraps=charts_scene.prepare) as prepare:
            QTest.mousePress(self.window, Qt.MouseButton.LeftButton, pos=QPoint(250, 240))
            QTest.mouseMove(self.window, QPoint(650, 240), 20)
            QTest.mouseRelease(self.window, Qt.MouseButton.LeftButton, pos=QPoint(650, 240))
            span = self.chart.property("viewEnd")-self.chart.property("viewStart")
            self.assertGreater(span, .3)
            self.assertLess(span, .6)
            start = self.chart.property("viewStart")
            QTest.mousePress(self.window, Qt.MouseButton.MiddleButton, pos=QPoint(450, 240))
            QTest.mouseMove(self.window, QPoint(350, 240), 20)
            QTest.mouseRelease(self.window, Qt.MouseButton.MiddleButton, pos=QPoint(350, 240))
            self.assertGreater(self.chart.property("viewStart"), start)
            self.assertAlmostEqual(self.chart.property("viewEnd")-self.chart.property("viewStart"), span)
            self.assertEqual(prepare.call_count, 0)
        self.assertFalse(self.warnings, self.warnings)

    def test_nonzoom_chart_leaves_wheel_to_the_page(self):
        self.change_data(charts_data.bars(["A"], [("one", [10])], "kWh").to_dict())
        wheel = QWheelEvent(QPointF(420, 220), QPointF(420, 220), QPoint(), QPoint(0, -120),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        self.app.sendEvent(self.window, wheel)
        self.assertFalse(wheel.isAccepted())
        self.assertEqual(self.chart.property("viewEnd")-self.chart.property("viewStart"), 1)

    def test_resize_keeps_geometry_and_hover_values(self):
        builds = self.chart.property("pathBuilds")
        self.assertGreater(builds, 0)
        with patch.object(charts_scene, "prepare", wraps=charts_scene.prepare) as prepare:
            for step in range(40):
                self.window.resize(1001+step*2, 601+step)
                self.app.processEvents()
            self.assertEqual(prepare.call_count, 0)
            self.assertEqual(self.chart.property("pathBuilds"), builds)
        QTest.qWait(40)
        QTest.mouseMove(self.window, QPoint(10, 10))
        QTest.mouseMove(self.window, QPoint(440, 220))
        QTest.qWait(30)
        self.assertIn("kW", self.chart.property("readout"))
        self.assertFalse(self.window.grabWindow().isNull())

    def test_map_holes_empty_state_and_context_menu(self):
        data = charts_data.heatmap([[1, None], [2, 3]], ["Jan", "Feb"], ["0", "1"], "kW").to_dict()
        self.change_data(data)
        QTest.mouseMove(self.window, QPoint(800, 160))
        QTest.qWait(20)
        self.assertIn("Jan, 1: –", self.chart.property("readout"))
        QTest.mouseClick(self.window, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, QPoint(440, 220))
        QTest.qWait(40)
        self.assertGreater(len(self.window.findChildren(QObject, "Menu")), 0)
        QTest.keyClick(self.window, Qt.Key.Key_Escape)
        self.change_data(charts_data.ChartData(message="No results", action="compute").to_dict())
        self.assertTrue(self.chart.property("isEmpty"))
        self.assertFalse(self.warnings, self.warnings)

    def test_zoom_keeps_vertical_line_one_pixel_instead_of_scaling_stroke(self):
        data = charts_data.line([0, 1, 1, 2], [("edge", [0, 0, 10, 10])], "kW", area=False).to_dict()
        self.change_data(data)
        plot = self.window.findChild(QObject, "plotArea")
        middle = plot.mapToScene(QPointF(plot.width()/2, plot.height()/2+8))

        def blue_width():
            image = self.window.grabWindow()
            ratio = image.devicePixelRatio()
            x, y = int(middle.x()*ratio), int(middle.y()*ratio)
            def series(color):     # the line's colour, never the grey of grid and text (R494: not blue any more)
                return max(color.red(), color.green(), color.blue()) - min(color.red(), color.green(), color.blue()) > 50
            return sum(series(image.pixelColor(px, y)) for px in range(x-30, x+31))
        before = blue_width()
        self.assertLessEqual(before, 3, 'The cosmetic two-pixel stroke grew with screen density')
        self.chart.setProperty("viewStart", .45)
        self.chart.setProperty("viewEnd", .55)
        QTest.qWait(50)
        self.assertGreater(before, 0)
        self.assertLessEqual(abs(blue_width()-before), 1)


if __name__ == "__main__":
    unittest.main()
