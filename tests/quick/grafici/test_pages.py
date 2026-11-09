"""R389/R381/R395: lazy result pages, full provenance and responsive text."""
import time
import unittest

from PySide6.QtCore import QMetaObject, QPoint, QPointF, Q_ARG, QUrl, Qt
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import _setup
from meridiana.quick.backend.controls import install_controls
from meridiana.quick.backend import charts_bridge, charts_data


QML = _setup.ROOT / "src/meridiana/quick/qml"
setUpModule = _setup.keep_global_state


def items(root):
    yield root
    for child in root.childItems():
        yield from items(child)


def sample_page():
    chart = charts_data.bars(["January", "February"], [("Energy", [10, 20])], "kWh").to_dict()
    records = []
    for i in range(2):
        records.append({"title": f"Record {i}", "steps": [{
            "key": f"step-{i}", "title": f"Step {i}", "formula": r"E=P\cdot t",
            "explanation": f"Explanation {i}", "reference": f"Reference {i}",
            "inputs": [{"symbol": "P", "label": f"Power {i}", "value": 10.5, "unit": "kW", "decimals": 1,
                        "source": {"kind": "data", "label": f"Datasheet {i}", "ref": f"Edition {i}"}}],
            "result": {"symbol": "E", "label": f"Energy {i}", "value": 21, "unit": "kWh", "decimals": 0,
                       "source": {"kind": "computed", "label": f"Calculated {i}", "ref": f"Result reference {i}"}},
            "worked": [r"E = 10.5\,\mathrm{kW} \cdot 2\,\mathrm{h} = \mathbf{21}\,\mathrm{kWh}"],
            "example": f"Example {i}: 14 July, 13:00 standard time (UTC+1).",
        }]})
    records = charts_data.pedigree(records)          # laid out as the report lays it out (R460)
    return {"title": "Production", "tiles": [
        {"label": "Energy a year", "value": "18 000 kWh", "detail": "typical year", "more": "All modules"},
        {"label": "Power", "value": "10.00 kWp", "detail": "9 kW AC", "more": ""}],
        "tabs": [{"title": "Balance", "charts": [{"id": "first", **chart}, {"id": "second", **chart}]},
                 {"title": "Unused", "charts": [{"id": "unused", **chart}]},
                 {"title": "How it is computed", "charts": [], "records": records}],
        "records": records, "status": "Recorded weather", "empty": False, "action": "",
        "source_kinds": {"data": "data", "computed": "computed"}, "limits": ["Limit one", "Limit two"],
        "limits_title": "Model limits", "limits_intro": "Read these limitations"}


class ResultPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["result-page-tests"])
        charts_bridge.register()

    def wait(self, predicate, seconds=5):
        end = time.monotonic() + seconds
        while not predicate() and time.monotonic() < end:
            self.app.processEvents()
            QTest.qWait(10)
            time.sleep(0.005)  # Let Python formula workers acquire the GIL between Qt event turns.
        self.assertTrue(predicate())

    def host(self, data=None, component="ResultsPage", width=760, height=600, properties="pageData: pagePayload"):
        self.assertTrue((QML / "Meridiana/Charts" / f"{component}.qml").exists(),
                        f"{component} is not implemented")
        engine = QQmlApplicationEngine()
        self.engine = engine
        self.theme = install_controls(engine)
        self.warnings = []
        engine.warnings.connect(lambda errors: self.warnings.extend(e.toString() for e in errors))
        engine.addImportPath(str(QML))
        engine.rootContext().setContextProperty("pagePayload", data or sample_page())
        source = f'''import QtQuick
import Meridiana.Theme
import Meridiana.Charts 1.0
Window {{ visible: true; width: {width}; height: {height}; color: Theme.colors.view
    {component} {{ objectName: "subject"; anchors.fill: parent; {properties} }}
}}'''
        engine.loadData(source.encode(), QUrl.fromLocalFile(str(QML / "test-pages.qml")))
        self.assertTrue(engine.rootObjects(), "\n".join(self.warnings))
        self.window = engine.rootObjects()[0]
        self.subject = self.window.findChild(QQuickItem, "subject")
        self.addCleanup(self.dispose)
        QTest.qWait(150)
        return self.subject

    def dispose(self):
        self.window.close()
        self.engine.deleteLater()
        self.app.processEvents()

    def named(self, name):
        return next((item for item in items(self.window.contentItem()) if item.objectName() == name), None)

    def texts(self):
        return [str(item.property("text")) for item in items(self.window.contentItem())
                if item.property("text") is not None]

    def click(self, item):
        self.assertIsNotNone(item)
        pos = item.mapToScene(QPointF(item.width()/2, item.height()/2))
        QTest.mouseClick(self.window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         QPoint(round(pos.x()), round(pos.y())))

    def test_tabs_and_charts_are_created_only_on_first_use(self):
        # Two 160 px canvases cannot both intersect this viewport below the tiles.
        self.host(height=350)
        self.wait(lambda: self.named("chart-first") is not None)
        self.assertIsNone(self.named("chart-second"))
        self.assertIsNone(self.named("chart-unused"))
        self.assertNotIn("Explanation 0", self.texts())
        scroll = self.subject
        scroll.setProperty("contentY", 500)
        self.wait(lambda: self.named("chart-second") is not None)
        scroll.setProperty("contentY", 0)
        self.click(self.named("result-tab-1"))
        self.wait(lambda: self.named("chart-unused") is not None)
        self.assertEqual(self.subject.property("currentIndex"), 1)
        self.assertIsNotNone(self.named("chart-first"))
        self.assertEqual(self.warnings, [])

    def test_tall_viewport_creates_both_visible_charts(self):
        self.host(height=900)
        self.wait(lambda: self.named("chart-second") is not None)
        second = self.named("chart-second")
        self.assertLess(second.mapToScene(QPointF()).y(), self.window.height())
        self.assertIsNone(self.named("chart-unused"))
        self.assertEqual(self.warnings, [])

    def test_pedigree_contains_every_record_quantity_source_and_limit(self):
        self.host()
        self.click(self.named("result-tab-2"))
        self.wait(lambda: self.subject.property("displayedIndex") == 2)
        self.wait(lambda: any("Limit two" in text for text in self.texts()))
        self.wait(lambda: self.subject.property("contentHeight") > self.window.height())   # laid out, next frame
        text = "\n".join(self.texts())
        for i in range(2):
            for prefix in ("Record", "Step", "Explanation", "Reference", "Power", "Datasheet", "Edition",
                           "Energy", "Calculated", "Result reference"):
                self.assertIn(f"{prefix} {i}", text)
        for value in ("kW", "kWh", "data", "computed", "Limit one", "Limit two", "Read these limitations"):
            self.assertIn(value, text)
        self.assertGreater(self.subject.property("contentHeight"), self.window.height())
        self.assertEqual(self.warnings, [])

    def test_steps_are_laid_out_as_the_report_lays_them_out_r460(self):
        # the formula numbered on from one record to the next, «where:», the value split on its separator so the
        # digits line up, the result in evidence; then the hour of the example and the formula again with the numbers
        # (R479), no list «symbol = value»
        self.host()
        self.click(self.named("result-tab-2"))
        self.wait(lambda: self.subject.property("displayedIndex") == 2)
        self.wait(lambda: any("Limit two" in text for text in self.texts()))
        texts = self.texts()
        self.assertIn("(1)", texts)
        self.assertIn("(2)", texts)
        self.assertGreaterEqual(texts.count("where:"), 2)
        self.assertEqual(texts.count("With the values:"), 0)
        self.assertIn("Example 0: 14 July, 13:00 standard time (UTC+1).", texts)
        self.assertIn(" kW", texts)                   # the unit in the column after the whole number
        worked = self.named("pedigree-worked")
        example = self.named("pedigree-example")
        equation = self.named("pedigree-equation-0-0")
        self.assertTrue(worked.isVisible())
        self.assertGreater(example.mapToScene(QPointF()).y(), equation.mapToScene(QPointF()).y())
        self.assertGreater(worked.mapToScene(QPointF()).y(), example.mapToScene(QPointF()).y())
        self.assertEqual(self.warnings, [])

    def test_narrow_large_text_keeps_tiles_and_all_copy_inside_page(self):
        self.host(width=340, height=700)
        self.theme.configure({"textSize": "large"})
        QTest.qWait(100)
        for item in items(self.subject):
            if item.objectName().startswith("result-tile-"):
                self.assertLessEqual(item.width(), self.subject.width())
                self.assertGreater(item.height(), 80)
        # Widgets keeps the extra explanation in the detail tooltip (R309).
        self.assertEqual(self.named("tile-detail-0").property("more"), "All modules")
        self.assertEqual(self.warnings, [])

    def test_tiles_keep_five_columns_and_shared_number_baseline_r309_r310(self):
        page = sample_page()
        page["tiles"] = page["tiles"] * 5
        page["tiles"][0] = dict(page["tiles"][0], label="A very long explanatory label " * 5)
        self.host(page, width=1920, height=1080)
        tiles = [self.named(f"result-tile-{index}") for index in range(10)]
        self.assertEqual(len({tile.y() for tile in tiles}), 2)
        self.assertGreater(tiles[5].y(), tiles[0].y())
        self.assertEqual(len({tile.height() for tile in tiles}), 1)
        values = [self.named(f"tile-value-{index}") for index in range(5)]
        self.assertTrue(all(value is not None for value in values))
        self.assertEqual(len({value.mapToScene(QPointF()).y() for value in values}), 1)

    def test_empty_storage_exposes_action_and_compatibility_explanation(self):
        page = charts_data.storage({})
        self.host(page)
        actions = []
        self.subject.actionRequested.connect(actions.append)
        self.click(self.named("results-empty-action"))
        self.assertEqual(actions, ["choose_battery"])
        self.assertIn(page["records"][0]["explanation"], self.texts())
        self.assertIn(page["status"], self.texts())
        self.assertNotIn("unknown", self.texts())
        self.assertEqual(self.warnings, [])

    def test_properties_is_an_explicit_empty_slot_not_unsaved_controls(self):
        self.host(component="ResultProperties")
        self.assertEqual(self.subject.property("implicitHeight"), 0)
        self.assertEqual(self.warnings, [])

    def test_formula_waits_for_viewport_and_replaces_old_theme_image(self):
        self.host(component="Formula", properties='tex: "E=P*t"; inViewport: false')
        self.assertEqual(self.subject.property("requestedKey"), "")
        self.assertFalse(self.subject.property("ready"))
        self.subject.setProperty("inViewport", True)
        self.wait(lambda: self.subject.property("ready"), seconds=15)
        self.assertEqual(self.subject.property("error"), "")
        self.assertGreater(self.named("formula-image").width(), 20)
        before = self.subject.property("imageUrl")
        self.subject.setProperty("inViewport", False)
        self.theme.configure({"theme": "dark", "textSize": "large"})
        self.app.processEvents()
        self.assertEqual(self.subject.property("imageUrl"), "")
        self.subject.setProperty("inViewport", True)
        self.wait(lambda: self.subject.property("ready"), seconds=15)
        self.assertNotEqual(self.subject.property("imageUrl"), before)
        self.assertEqual(self.warnings, [])

    def test_invalid_formula_keeps_readable_fallback_and_explicit_error(self):
        self.host(component="Formula", properties='tex: "\\\\not_a_mathtext_command"')
        self.wait(lambda: bool(self.subject.property("error")), seconds=15)
        self.assertFalse(self.subject.property("ready"))
        self.assertTrue(self.named("formula-fallback").isVisible())
        self.assertTrue(self.named("formula-error").isVisible())
        self.assertEqual(self.warnings, [])

    def test_pedigree_formulas_outside_viewport_are_not_requested(self):
        self.host(height=350)
        self.click(self.named("result-tab-2"))
        self.wait(lambda: self.subject.property("displayedIndex") == 2)
        QTest.qWait(150)
        second = self.named("pedigree-step-1-0")
        formulas = [item for item in items(second) if item.property("tex") is not None]
        self.assertTrue(formulas)
        self.assertGreater(second.mapToScene(QPointF()).y(), self.window.height())
        self.assertTrue(all(item.property("requestedKey") == "" for item in formulas))
        self.subject.setProperty("contentY", second.mapToScene(QPointF()).y())
        self.wait(lambda: any(item.property("ready") for item in formulas), seconds=15)
        self.assertEqual(self.warnings, [])

    def test_real_year_pages_keep_all_tabs_charts_and_pedigree(self):
        from quick.grafici.fixtures import build_results

        real = build_results()
        pages = [charts_data.production(real.sim, real.pvgis), charts_data.consumption(real.load),
                 charts_data.economics(real.econ, sizing=real.sizing, storage=real.storage,
                                       p_stc_kw=real.sim.p_stc_kw, battery_kwh=5)]
        for page in pages:
            with self.subTest(page=page["title"]):
                self.host(page, width=1366, height=900)
                for index, tab in enumerate(page["tabs"]):
                    self.subject.setProperty("contentY", 0)
                    self.click(self.named(f"result-tab-{index}"))
                    self.wait(lambda i=index: self.subject.property("displayedIndex") == i
                              and self.subject.property("displayedPage") is not None, seconds=10)
                    # Inactive tabs never replace the old page with a null item.
                    self.assertIsNotNone(self.subject.property("displayedPage"))
                    if tab.get("charts"):
                        for chart in tab["charts"]:
                            self.subject.setProperty("contentY", self.subject.property("contentHeight") - 650)
                            self.wait(lambda name=chart["id"]: self.named("chart-" + name) is not None)
                    else:
                        record_count = len(page["records"])
                        self.wait(lambda expected=record_count: len([item for item in items(self.subject)
                                              if item.objectName().startswith("pedigree-record-")]) == expected)
                        text = "\n".join(self.texts())
                        for record in page["records"]:
                            self.assertIn(record["title"], text)
                            for step in record["steps"]:
                                self.assertIn(step["title"], text)
                                self.assertIn(step["explanation"], text)
                                self.assertIn(step["reference"], text)
                                for quantity in step["inputs"] + ([step["result"]] if step["result"] else []):
                                    self.assertIn(quantity["label"], text)
                                    if quantity["source"]:
                                        self.assertIn(quantity["source"]["label"], text)
                                        self.assertIn(quantity["source"]["ref"], text)
                        for limit in page["limits"]:
                            self.assertIn(limit, text)
                self.assertEqual(self.warnings, [])
                self.doCleanups()

    def test_tab_transition_keeps_painted_chart_in_every_sampled_frame(self):
        self.host()
        self.wait(lambda: self.subject.property("displayedPage") is not None)
        for reduced in (False, True):
            self.theme.configure({"reducedMotion": reduced})
            for target in (1, 0):
                self.click(self.named(f"result-tab-{target}"))
                for _ in range(12):
                    self.app.processEvents()
                    image = self.window.grabWindow()
                    self.assertFalse(image.isNull())
                    scale = image.devicePixelRatio()
                    colored = 0
                    for y in range(int(300 * scale), image.height() - 10, max(1, int(6 * scale))):
                        for x in range(int(45 * scale), image.width() - 45, max(1, int(6 * scale))):
                            color = image.pixelColor(x, y)
                            channels = (color.red(), color.green(), color.blue())
                            colored += max(channels) - min(channels) > 60
                    self.assertGreater(colored, 20, "A transition frame lost the painted series")
                    QTest.qWait(8)
                self.assertEqual(self.subject.property("displayedIndex"), target)
        self.assertEqual(self.warnings, [])

    def test_loss_steps_keep_readable_rows_in_a_short_page(self):
        page = sample_page()
        chart = charts_data.changes([f'Loss {i}' for i in range(24)], [-1.] * 24).to_dict()
        page['tabs'][0]['charts'] = [{'id': 'losses', **chart}]
        self.host(page, width=900, height=450)
        self.wait(lambda: self.named('chart-losses') is not None)
        # The chart's own minimum arrives with its item (an asynchronous Loader): wait for the layout, then measure.
        self.wait(lambda: self.named('plotArea') is not None and self.named('plotArea').height()/24 >= 16)
        plot = self.named('plotArea')
        # A chart must scroll rather than squeeze 24 text labels into 150 pixels (R313).
        self.assertGreaterEqual(plot.height()/24, 16)
        self.wait(lambda: self.subject.property('contentHeight') > self.subject.height())   # the column, next frame
        self.assertGreater(self.subject.property('contentHeight'), self.subject.height())
        self.assertEqual(self.warnings, [])

    def test_charts_fill_the_page_and_scroll_only_under_their_minimum_r495(self):
        # R495 (Daniel 06/11/2026): however tall the window, the Consumption page kept its bar for a few pixels of
        # play: the charts took the room under the tabs without the card's top margin (4 px over, always).
        from quick.grafici.fixtures import build_results

        real = build_results()
        pages = [charts_data.consumption(real.load),
                 charts_data.economics(real.econ, sizing=real.sizing, storage=real.storage,
                                       p_stc_kw=real.sim.p_stc_kw, battery_kwh=5)]
        heights = (480, 760, 1250)
        for page in pages:
            grown, short_scrolls = {}, False
            for height in heights:
                with self.subTest(page=page["title"], height=height):
                    self.host(page, width=1366, height=height)
                    for index, tab in enumerate(page["tabs"]):
                        if not tab.get("charts"):
                            continue
                        self.subject.setProperty("contentY", 0)
                        QMetaObject.invokeMethod(self.subject, "select", Q_ARG("QVariant", index))
                        names = ["chart-" + chart["id"] for chart in tab["charts"]]
                        self.wait(lambda i=index, wanted=names: self.subject.property("displayedIndex") == i
                                  and all(self.named(name) is not None for name in wanted)
                                  # the Loader holds its item: the chart's own minimum is in the page's height now
                                  and all(self.named(name).parentItem().property("item") is not None for name in wanted),
                                  seconds=10)
                        settled, last = 0, None   # the layout settles first (text, the second chart arriving)
                        for _ in range(200):
                            self.app.processEvents()
                            QTest.qWait(10)
                            now = round(self.subject.property("contentHeight"), 3)
                            settled = settled + 1 if now == last else 0
                            last = now
                            if settled >= 5:
                                break
                        measures = set()
                        for _ in range(8):       # then no measure that feeds itself: the height stays put
                            self.app.processEvents()
                            QTest.qWait(15)
                            measures.add(round(self.subject.property("contentHeight"), 3))
                        self.assertEqual(len(measures), 1, (tab["title"], measures))
                        charts = [self.named(name) for name in names]
                        above = all(chart.height() > chart.property("minimumHeight") + .5 for chart in charts)
                        over = self.subject.property("contentHeight") - self.subject.height()
                        if above:        # room enough: the charts take it all and no bar is shown
                            self.assertLessEqual(over, 0, (tab["title"], over))
                            self.assertGreater(over, -len(charts) - 1, (tab["title"], over))
                        else:            # under the charts' minimum the page scrolls, and only then
                            self.assertGreater(over, 0, (tab["title"], over))
                            short_scrolls = True
                        if height == heights[-1]:
                            self.assertTrue(above, tab["title"])
                        grown.setdefault(tab["title"], []).append(charts[0].height())
                    self.assertEqual(self.warnings, [])
                    self.doCleanups()
            self.assertTrue(short_scrolls, page["title"])
            for title, sizes in grown.items():     # the chart follows the window, never a fixed size
                self.assertGreater(sizes[-1] - sizes[1], (heights[-1] - heights[1]) / len(
                    next(tab for tab in page["tabs"] if tab["title"] == title)["charts"]) - 2, (title, sizes))


if __name__ == "__main__":
    unittest.main()
