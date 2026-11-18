"""Result tables keep units and totals visible without materializing all cells."""
import time
import unittest

from PySide6.QtCore import QPoint, QPointF, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import _setup
from meridiana.i18n import _
from meridiana.quick.backend.controls import install_controls
from meridiana.quick.backend import charts_bridge, charts_data


QML = _setup.ROOT / "src/meridiana/quick/qml"
setUpModule = _setup.keep_global_state


def visual_items(root):
    yield root
    for child in root.childItems():
        yield from visual_items(child)


def table_data(rows=12, columns=3):
    return {"headers": ["Hour"] + [f"Energy {i}" for i in range(1, columns)],
            "units": [""] + ["kWh"] * (columns - 1),
            "rows": [[f"Hour {r:04d}"] + [r + c / 10 for c in range(1, columns)]
                     for r in range(rows)],
            "totals": [None] + [sum(r + c / 10 for r in range(rows)) for c in range(1, columns)]}


class ResultTables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["result-table-tests"])
        charts_bridge.register()

    def wait(self, predicate, seconds=8):
        end = time.monotonic() + seconds
        while not predicate() and time.monotonic() < end:
            self.app.processEvents()
            QTest.qWait(10)
        self.assertTrue(predicate())

    def host(self, data, component="ResultTable", width=760, height=500):
        self.engine = QQmlApplicationEngine()
        self.theme = install_controls(self.engine)
        self.warnings = []
        self.engine.warnings.connect(lambda errors: self.warnings.extend(e.toString() for e in errors))
        self.engine.addImportPath(str(QML))
        self.engine.rootContext().setContextProperty("payload", data)
        field = "chartData" if component == "Chart" else "tableData"
        self.engine.loadData(f'''import QtQuick
import Meridiana.Theme
import Meridiana.Charts 1.0
import "Meridiana/Charts"
Window {{ visible: true; width: {width}; height: {height}; color: Theme.colors.view
    {component} {{ objectName: "subject"; anchors.fill: parent; {field}: payload }}
}}'''.encode(), QUrl.fromLocalFile(str(QML / "table-tests.qml")))
        self.assertTrue(self.engine.rootObjects(), self.warnings)
        self.window = self.engine.rootObjects()[0]
        self.subject = self.window.findChild(QQuickItem, "subject")
        self.addCleanup(self.dispose)
        QTest.qWait(150)
        return self.subject

    def dispose(self):
        self.window.close()
        self.engine.deleteLater()
        self.app.processEvents()

    def named(self, name):
        return next((x for x in visual_items(self.window.contentItem()) if x.objectName() == name), None)

    def evaluate(self, code):
        value, undefined = QQmlExpression(self.engine.rootContext(), self.subject, code).evaluate()
        self.assertFalse(undefined, code)
        return value

    def texts(self):
        return [str(x.property("text")) for x in visual_items(self.window.contentItem())
                if x.property("text") is not None]

    def click(self, name):
        item = self.named(name)
        self.assertIsNotNone(item)
        p = item.mapToScene(QPointF(item.width()/2, item.height()/2))
        QTest.mouseClick(self.window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         QPoint(round(p.x()), round(p.y())))

    def test_header_units_and_total_stay_fixed_while_rows_scroll(self):
        self.host(table_data(8760))      # r23-tabelle: one table (M.Table) for every result
        view = self.named("resultTableView")
        header = self.named("resultTableHeader")
        footer = self.named("resultTableTotal")
        self.assertIsNotNone(header)
        self.assertIsNotNone(footer)
        self.assertIn("Energy 1", self.texts())
        self.assertIn("kWh", self.texts())
        positions = (header.mapToScene(QPointF()).y(), footer.mapToScene(QPointF()).y())
        view.setProperty("contentY", 6061 * self.evaluate("rowHeight"))      # r23-tabelle: the one row height
        self.wait(lambda: "Hour 6061" in self.texts())
        visible_rows = [x.property("text") for x in visual_items(self.subject)
                        if x.property("text") is not None and header.height() <= x.mapToScene(QPointF()).y() < footer.y()]
        self.assertNotIn("Hour 0000", visible_rows)
        self.assertIn("Hour 6061", visible_rows)
        self.assertEqual(positions, (header.mapToScene(QPointF()).y(), footer.mapToScene(QPointF()).y()))
        self.assertIn(_("Total"), self.texts())
        self.assertLess(len(list(visual_items(self.subject))), 500)
        self.assertEqual(self.warnings, [])

    def test_366_columns_are_virtualized_and_header_follows_horizontal_scroll(self):
        self.host(table_data(24, 366), width=340)
        view = self.named("resultTableView")
        self.assertLess(len(list(visual_items(self.subject))), 300)
        view.setProperty("contentX", self.evaluate("columnLeft(360)"))
        self.wait(lambda: "Energy 361" in self.texts())
        self.assertNotIn("Energy 1", self.texts())
        self.assertAlmostEqual(self.named("resultTableHeader").property("contentX"), view.property("contentX"))
        self.assertAlmostEqual(self.named("resultTableTotal").property("contentX"), view.property("contentX"))
        self.assertLess(len(list(visual_items(self.subject))), 300)
        self.assertEqual(self.warnings, [])

    def test_empty_state_belongs_to_chart_even_after_selecting_table(self):
        self.host({"kind": "message", "message": "Calculate the year", "table": table_data(0)}, "Chart")
        self.click("tableButton")
        QTest.qWait(120)
        self.assertIsNone(self.named("resultTableView"))
        self.assertIn("Calculate the year", self.texts())
        self.assertTrue(self.subject.property("readyForDisplay"))
        self.assertEqual(self.warnings, [])

    def test_narrow_table_large_text_keeps_legible_cell_sizes(self):
        self.host(table_data(24, 366), width=340)
        self.theme.configure({"textSize": "large"})
        QTest.qWait(100)
        self.assertGreaterEqual(self.evaluate("columnWidth(1)"), 130)
        view = self.named("resultTableView")
        self.assertGreater(view.property("contentWidth"), view.width())
        cell = next(x for x in visual_items(view) if x.property("text") == "Hour 0000")
        font = cell.property("font")
        self.assertEqual(font.pixelSize(), self.theme.type["BODY"])
        self.assertGreater(cell.height(), font.pixelSize())
        self.assertGreaterEqual(cell.width(), cell.property("contentWidth"))
        self.assertEqual(self.warnings, [])

    @unittest.skipUnless((QML / "Meridiana/Controls/Table.qml").exists(), "Shared Controls.Table is not integrated yet")
    def test_common_table_keeps_8760_rows_virtual_and_total_fixed(self):
        self.host(table_data(8760), width=340)
        view = next(x for x in visual_items(self.subject) if x.metaObject().className().startswith("QQuickListView"))
        footer = self.named("resultTableTotal")
        self.assertIsNotNone(footer)
        position = footer.mapToScene(QPointF()).y()
        numeric = next(x for x in visual_items(view) if x.property("text") == "0")
        alignment, undefined = QQmlExpression(self.engine.rootContext(), numeric, "Number(horizontalAlignment)").evaluate()
        self.assertFalse(undefined)
        self.assertEqual(alignment, int(Qt.AlignmentFlag.AlignRight))
        self.assertEqual(numeric.property("font").family(), self.theme.fontFamily)
        self.assertEqual(numeric.property("font").pixelSize(), self.theme.type["BODY"])
        header = next(x for x in visual_items(self.subject) if x.property("text") == "Energy 1")
        # R394 uses the Widgets header: secondary text, with the total emphasized.
        self.assertEqual(header.property("font").weight(), 400)
        self.assertLess(len(list(visual_items(self.subject))), 500)
        view.setProperty("contentY", view.property("contentHeight") - view.height())
        self.wait(lambda: "Hour 8759" in self.texts())
        self.assertEqual(position, footer.mapToScene(QPointF()).y())
        self.assertIn("Energy 1", self.texts())
        self.assertIn("kWh", self.texts())
        self.assertIn(_("Total"), self.texts())
        self.assertLess(len(list(visual_items(self.subject))), 500)
        self.assertEqual(self.warnings, [])

    def test_graph_table_transition_keeps_painted_content_in_sampled_frames(self):
        chart = charts_data.bars([f"Month {i}" for i in range(12)], [("Energy", list(range(10, 22)))], "kWh").to_dict()
        self.host(chart, "Chart")
        self.wait(lambda: self.subject.property("readyForDisplay"))
        for reduced in (False, True):
            self.theme.configure({"reducedMotion": reduced})
            for button in ("tableButton", "graphButton"):
                self.click(button)
                for _frame in range(12):
                    self.app.processEvents()
                    image = self.window.grabWindow()
                    self.assertFalse(image.isNull())
                    dpr = image.devicePixelRatio()
                    background = image.pixelColor(int(5*dpr), int(300*dpr))
                    painted = 0
                    for y in range(int(100*dpr), int(420*dpr), max(1, int(3*dpr))):
                        for x in range(int(30*dpr), int(700*dpr), max(1, int(3*dpr))):
                            color = image.pixelColor(x, y)
                            painted += max(abs(color.red()-background.red()), abs(color.green()-background.green()),
                                           abs(color.blue()-background.blue())) > 35
                    self.assertGreater(painted, 50, "The graph/table transition lost all body content")
                    QTest.qWait(8)
        self.assertEqual(self.warnings, [])


if __name__ == "__main__":
    unittest.main()
