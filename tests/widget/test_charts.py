"""The charts on pyqtgraph (study 17, D2; task 17c): every form drawn offscreen from the example project's year,
the table with the same numbers, the theme, the drawing that waits for the chart to be shown; then what the
pointer does, in the order of the interface design (5.2): the value under it, the legend that turns series off
and on, the zoom on the hourly and weekly series, the exports. They need PySide6 and a display (offscreen will
do); elsewhere they say why they are skipped."""

import sys
import tempfile
import time
import unittest
from pathlib import Path

import _setup
from _fixtures import capannone as project
from _fixtures import clear_sky_meteo, write_cache
from _setup import wait_until

from meridiana import jobs
from meridiana.i18n import number

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Errors:
    """The exceptions raised in Python code that Qt calls (a paint, an event), which Qt only prints."""

    def __enter__(self):
        self.seen, self._hook = [], sys.excepthook
        sys.excepthook = lambda kind, value, tb: self.seen.append(f"{kind.__name__}: {value}")
        return self

    def __exit__(self, *exc):
        sys.excepthook = self._hook
        return False


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        from meridiana.ui import charts
        cls.charts = charts
        charts.backend()                                # pyqtgraph loaded once, not timed with a chart

    def chart(self, title="A chart", width=700, height=340):
        c = self.charts.Chart(title)
        c.resize(width, height)
        c.show()
        self.addCleanup(_setup.dispose, c)
        self.app.processEvents()
        return c

    def at(self, chart, x, y):
        """Where a point of the data is in the plot's viewport."""
        from PySide6.QtCore import QPointF
        p = chart.plot
        return p.mapFromScene(p.view.mapViewToScene(QPointF(float(x), float(y))))

    def move(self, chart, x, y):
        """The pointer moved over the plot to a point of the data, as Qt delivers it."""
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtWidgets import QApplication
        vp = chart.plot.viewport()
        local = QPointF(self.at(chart, x, y))
        event = QMouseEvent(QEvent.Type.MouseMove, local, QPointF(vp.mapToGlobal(local.toPoint())),
                            Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(vp, event)

    def wheel(self, chart, x, y, notches=1):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import QApplication
        vp = chart.plot.viewport()
        local = QPointF(self.at(chart, x, y))
        event = QWheelEvent(local, QPointF(vp.mapToGlobal(local.toPoint())), QPoint(0, 0), QPoint(0, 120 * notches),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
                            False)
        event.setAccepted(True)
        QApplication.sendEvent(vp, event)
        return event.isAccepted()


class Forms(Base):
    """Step 1: the four forms and the message on pyqtgraph, from the example project."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from meridiana.energy import pipeline
        cache = Path(tempfile.mkdtemp())
        write_cache(clear_sky_meteo(45.5226, 9.03), cache)
        p = project()
        cls.out = pipeline.compute(p, jobs.layout_of(p)[0], cache, fetch=False)

    def pages(self):
        from meridiana.ui.energy_pages import ConsumptionPage, EconomicsPage, EnergyPage
        o = self.out
        energy, consumption, economics = EnergyPage(), ConsumptionPage(), EconomicsPage()
        energy.show_results(o.sim, o.pvgis)
        consumption.show_results(o.load)
        economics.show_results(o.econ)
        economics.show_sizing(o.sizing, o.storage, o.sim.p_stc_kw, o.battery_kwh or 0.0)
        for page in (energy, consumption, economics):
            page.resize(1100, 900)
            self.addCleanup(_setup.dispose, page)
        return energy, consumption, economics

    def test_every_chart_of_the_pages_draws_the_example_year_offscreen(self):
        from PySide6.QtWidgets import QTabWidget
        Chart = self.charts.Chart
        kinds, drawn = set(), 0
        with Errors() as errors:
            for page in self.pages():
                page.show()
                for tabs in page.findChildren(QTabWidget):
                    for i in range(tabs.count()):
                        tabs.setCurrentIndex(i)
                        shown = [c for c in page.findChildren(Chart) if c.isVisible()]
                        self.assertTrue(wait_until(self.app, lambda s=shown: all(c.pending is None for c in s)))
                        for c in shown:
                            started = time.perf_counter()
                            image = c.grab()
                            spent = (time.perf_counter() - started) * 1000
                            self.assertLess(spent, 50, f"{c.name}: grab {spent:.1f} ms")
                            self.assertFalse(image.isNull())
                            kinds.add(c.last[0].__name__)
                            drawn += 1
                            if c.showing == "plot":
                                self.assertEqual(type(c.canvas).__name__, "Plot")
        self.assertEqual(errors.seen, [])
        self.assertEqual(drawn, 18)                          # Production 3, Consumption 5, Balance and economics 10 (R63: the year maps)
        self.assertTrue({"bars", "changes", "heatmap", "line"} <= kinds, kinds)

    def test_the_year_as_a_carpet_has_a_column_a_day_and_the_months_on_its_axis(self):
        """R63: 24 rows of hours, a column for each day; the hours the clock changes averaged, not lost."""
        import pandas as pd

        from meridiana.energy import consumption
        from meridiana.ui.energy_pages import month_names, year_carpet
        hours = pd.date_range("2023-01-01 00:00", periods=8760, freq="h", tz="UTC").tz_convert(consumption.TIMEZONE)
        load = pd.Series(1.0, index=hours)
        carpet, cols, ticks = year_carpet(load, month_names())
        self.assertEqual(carpet.shape[0], 24)
        self.assertIn(carpet.shape[1], (365, 366))
        self.assertEqual(len(cols), carpet.shape[1])
        self.assertEqual([label for _j, label in ticks][:2], month_names()[:2])
        self.assertTrue((carpet[:, 10:300] == 1.0).all())

    def test_the_table_holds_the_same_numbers(self):
        _energy, consumption, _economics = self.pages()
        consumption.show()
        c = consumption.monthly                             # consumption by month, stacked by band
        self.assertTrue(wait_until(self.app, lambda: c.pending is None))
        self.assertEqual(c.table.rowCount(), 0)             # filled only when it is asked for
        c.toggle.setChecked(True)
        self.assertIs(c.stack.currentWidget(), c.table)
        self.assertEqual([c.table.horizontalHeaderItem(j).text() for j in range(4)], ["", "F1", "F2", "F3"])
        _m, args, _k = c.last
        months, series = args[0], args[1]
        self.assertEqual(c.table.rowCount(), 12)
        for i in range(12):
            self.assertEqual(c.table.item(i, 0).text(), months[i])
            for j, (_label, values) in enumerate(series, start=1):
                v = values[i]
                self.assertEqual(c.table.item(i, j).text(), number(v, 1 if abs(v) < 100 else 0, grouping=True))
        c.toggle.setChecked(False)
        self.assertIs(c.stack.currentWidget(), c.canvas)

    def test_a_chart_hidden_is_drawn_when_it_is_first_shown(self):
        c = self.charts.Chart("Hidden")
        self.addCleanup(_setup.dispose, c)
        c.bars(["Jan", "Feb"], [("a", [1.0, 2.0])], "kWh")
        self.assertIsNotNone(c.pending)
        self.assertIsNone(c.plot)                           # nothing made while nobody looks at it
        c.resize(500, 300)
        c.show()
        self.assertTrue(wait_until(self.app, lambda: c.pending is None))
        self.assertIsNotNone(c.plot)
        self.assertEqual(c.numbers.rows, [["Jan", 1.0], ["Feb", 2.0]])

    def test_a_message_needs_no_plot(self):
        c = self.chart()
        c.message("Nothing to compute yet.")
        self.assertIsNone(c.plot)
        self.assertIs(c.stack.currentWidget(), c.note)
        self.assertEqual(c.note.text(), "Nothing to compute yet.")
        c.bars(["Jan"], [("a", [3.0])], "kWh")
        self.assertIs(c.stack.currentWidget(), c.canvas)

    def test_a_change_of_theme_draws_again_in_the_new_colours(self):
        from PySide6.QtGui import QColor, QPalette

        from meridiana import theme_colors
        charts = self.charts
        pg = charts.backend().pg
        palette = self.app.palette()
        self.addCleanup(self.app.setPalette, QPalette(palette))
        light = theme_colors.derive(theme_colors.DEFAULT_SEED, False).tokens
        dark = theme_colors.derive(theme_colors.DEFAULT_SEED, True).tokens
        self.addCleanup(charts.set_theme, light, False)
        # the palette first and then the charts, as Theme.apply does: the charts take light or dark from the
        # palette, and the system's is dark on a Windows set to dark
        p = QPalette(palette)
        p.setColor(QPalette.ColorRole.Window, QColor(light["window"]))
        self.app.setPalette(p)
        charts.set_theme(light, False)
        c = self.chart()
        c.bars(["Jan", "Feb"], [("a", [1.0, 2.0]), ("b", [2.0, 1.0])], "kWh")
        self.assertEqual(c.plot.backgroundBrush().color().name(), charts.CHROME["light"]["surface"])
        self.assertEqual(pg.mkBrush(c.series["a"][0].opts["brush"]).color().name(), charts.SERIES["light"][0])
        p = QPalette(palette)
        p.setColor(QPalette.ColorRole.Window, QColor(dark["window"]))
        self.app.setPalette(p)
        charts.set_theme(dark, True)
        self.assertEqual(c.plot.backgroundBrush().color().name(), dark["chart"]["surface"])
        self.assertEqual(pg.mkBrush(c.series["a"][0].opts["brush"]).color().name(), charts.SERIES["dark"][0])
        self.assertEqual(c.plot.getAxis("bottom").textPen().color().name(), dark["muted"])


class Pointer(Base):
    """Step 2: the value under the pointer, the legend, the zoom, the exports."""

    MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def test_the_pointer_reads_the_bar_under_it_with_every_series(self):
        c = self.chart()
        a = [1234.4 + 100 * i for i in range(12)]
        b = [987.6 + 50 * i for i in range(12)]
        c.bars(self.MONTHS, [("with", a), ("without", b)], "kWh")
        self.move(c, 3.1, 500)                              # over April
        self.assertTrue(wait_until(self.app, lambda: c.plot.readout.isVisible(), 2))
        self.assertEqual(c.plot.readout.text(), f"Apr: with {number(a[3], 0, grouping=True)} kWh · "
                                                f"without {number(b[3], 0, grouping=True)} kWh")
        outline = c._marks[0]
        self.assertTrue(outline.isVisible())                # the bars of April outlined

    def test_the_pointer_reads_the_nearest_hour_of_a_line(self):
        c = self.chart()
        hours = list(range(168))
        load = [0.5 + 0.01 * h for h in hours]
        names = [f"h{h}" for h in hours]
        c.line(hours, [("load", load)], "kW", "", 2, names=names)
        self.move(c, 40.3, 0.6)
        self.assertTrue(wait_until(self.app, lambda: c.plot.readout.isVisible(), 2))
        self.assertEqual(c.plot.readout.text(), f"h40: {number(load[40], 2, grouping=True)} kW")
        cross = c._marks[0]
        self.assertAlmostEqual(cross.value(), 40.0)
        c._left()                                           # the pointer leaves: nothing lit, nothing read
        self.assertFalse(c.plot.readout.isVisible())
        self.assertFalse(cross.isVisible())

    def test_a_click_on_the_legend_turns_a_series_off_and_on(self):
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtTest import QTest
        c = self.chart()
        c.bars(self.MONTHS, [("with", [1.0] * 12), ("without", [2.0] * 12)], "kWh")
        self.app.processEvents()
        entry = c.entries["without"]
        centre = c.plot.mapFromScene(entry.mapToScene(QPointF(entry.w / 2, entry.h / 2)))
        QTest.mouseClick(c.plot.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre)
        self.assertFalse(c.series["without"][0].isVisible())
        self.assertFalse(entry.on)                          # dimmed in the legend
        self.assertIn("without", c.hidden)
        self.move(c, 3, 1)
        self.assertTrue(wait_until(self.app, lambda: c.plot.readout.isVisible(), 2))
        self.assertNotIn("without", c.plot.readout.text())  # a series turned off is not read
        c.bars(self.MONTHS, [("with", [1.0] * 12), ("without", [3.0] * 12)], "kWh")
        self.assertFalse(c.series["without"][0].isVisible())   # still off with the new numbers
        QTest.mouseClick(c.plot.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         c.plot.mapFromScene(c.entries["without"].mapToScene(QPointF(5, 5))))
        self.assertTrue(c.series["without"][0].isVisible())
        self.assertTrue(c.entries["without"].on)

    def test_the_wheel_zooms_an_hourly_series_on_x_only_and_a_double_click_shows_all(self):
        from PySide6.QtCore import QRectF, Qt
        from PySide6.QtTest import QTest
        c = self.chart()
        hours = list(range(168))
        c.line(hours, [("load", [1.0 + (h % 24) / 10 for h in hours])], "kW", "", 2)
        view = c.plot.view
        (x0, x1), y = view.viewRange()
        self.assertTrue(self.wheel(c, 84, 1.5, notches=2))
        (z0, z1), y_after = view.viewRange()
        self.assertLess(z1 - z0, (x1 - x0) * 0.8)            # closer on x
        self.assertGreater(z0, x0)
        self.assertEqual(y_after, y)                         # the y-axis keeps the range of the data
        view.showAxRect(QRectF(100, 0, 20, 3))              # a band dragged across: x only
        (b0, b1), y_band = view.viewRange()
        self.assertAlmostEqual(b0, 100, places=6)
        self.assertAlmostEqual(b1, 120, places=6)
        self.assertEqual(y_band, y)
        QTest.mouseDClick(c.plot.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                          self.at(c, 110, 1.5))
        (a0, a1), _y = view.viewRange()
        self.assertAlmostEqual(a0, 0.0, places=6)
        self.assertAlmostEqual(a1, 167.0, places=6)
        self.assertIn("Frame it", [a.text() for a in c.menu().actions()])

    def test_the_months_do_not_zoom_and_leave_the_wheel_to_the_page(self):
        c = self.chart()
        c.bars(self.MONTHS, [("a", [float(i) for i in range(12)])], "kWh")
        before = c.plot.view.viewRange()
        self.assertFalse(self.wheel(c, 5, 5))
        self.assertEqual(c.plot.view.viewRange(), before)
        self.assertNotIn("Frame it", [a.text() for a in c.menu().actions()])

    def test_the_context_menu_saves_the_chart_as_svg_with_its_title_and_as_png_in_light(self):
        from PySide6.QtGui import QColor, QImage, QPalette

        from meridiana import theme_colors
        charts = self.charts
        menu = [a.text() for a in self.chart().menu().actions()]
        self.assertIn("Save as SVG…", menu)
        self.assertIn("Save as PNG…", menu)
        palette = self.app.palette()
        self.addCleanup(self.app.setPalette, QPalette(palette))
        light = theme_colors.derive(theme_colors.DEFAULT_SEED, False).tokens
        dark = theme_colors.derive(theme_colors.DEFAULT_SEED, True).tokens
        self.addCleanup(charts.set_theme, light, False)
        p = QPalette(palette)
        p.setColor(QPalette.ColorRole.Window, QColor(dark["window"]))
        self.app.setPalette(p)
        charts.set_theme(dark, True)
        c = self.chart("Production month by month")
        c.bars(self.MONTHS, [("Meridiana", [100.0 * i for i in range(12)]), ("PVGIS", [90.0 * i for i in range(12)])],
               "kWh")
        folder = Path(tempfile.mkdtemp())
        self.assertTrue(c.export(str(folder / "chart.svg"), "svg"))
        svg = (folder / "chart.svg").read_text(encoding="utf-8")
        self.assertIn("Production month by month", svg)
        self.assertIn("PVGIS", svg)                          # the legend travels with it
        self.assertTrue(c.export(str(folder / "chart.png"), "png"))
        image = QImage(str(folder / "chart.png"))
        self.assertGreaterEqual(image.width(), 1600)
        self.assertEqual(image.pixelColor(2, 2).name(), charts.CHROME["light"]["surface"])
        # and the chart on screen is back in the window's theme, without the title in its plot
        self.assertEqual(c.plot.backgroundBrush().color().name(), dark["chart"]["surface"])
        self.assertFalse(c.plot.getPlotItem().titleLabel.isVisible())

    def test_the_pointer_and_the_zoom_answer_quickly_on_a_year_of_hours(self):
        """8.760 points: 1-4 ms in the study's proof (D.4); 2 px antialiased lines took 331 ms to paint, the
        bound catches that again, the measures are in the diary."""
        c = self.chart(width=900, height=360)
        hours = list(range(8760))
        c.line(hours, [("production", [float((h % 24) > 6 and (h % 24) < 18) * 10 for h in hours]),
                       ("load", [3.0] * 8760)], "kW", "", 1)
        c.grab()
        from PySide6.QtCore import QPointF
        view = c.plot.view
        moves, zooms = [], []
        for k in range(20):
            scene = view.mapViewToScene(QPointF(400.0 * k + 37, 4.0))
            started = time.perf_counter()
            c._moved((scene,))                              # what the SignalProxy hands over
            c.plot.viewport().repaint()
            moves.append((time.perf_counter() - started) * 1000)
            self.assertTrue(c.plot.readout.isVisible())
        for k in range(10):
            started = time.perf_counter()
            self.wheel(c, 4380, 4, notches=1 if k % 2 == 0 else -1)
            c.plot.viewport().repaint()
            zooms.append((time.perf_counter() - started) * 1000)
        moves.sort()
        zooms.sort()
        self.assertLess(moves[len(moves) // 2], 40, moves)
        self.assertLess(zooms[len(zooms) // 2], 40, zooms)


if __name__ == "__main__":
    unittest.main()
