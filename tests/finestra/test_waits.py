"""Waits made visible in the window (study 16, theme F; task 16f; design document 3.12): the values of the last
computation greyed with a mark on their phase's title while the project has changed; the arcs of the plan and of
the energy pages; the 3D's skeleton at the start; the bar with its percentage and Cancel for PVGIS and the PDF
report. The waits of a single widget are in widget/test_waits.py. Where the time itself is tested, the events are
turned for the milliseconds asked (_setup.turn_events) and the jobs slowed on purpose. PySide6 and a display
(offscreen will do)."""

import time
import unittest

import _setup
from _fixtures import capannone, clear_sky_meteo
from _setup import turn_events as spin

from meridiana import config

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


def slowed(function, seconds: float):
    """`function`, `seconds` slower: a long wait made in a test (the worker sleeps, the window does not)."""
    def slow(*args, **kwargs):
        time.sleep(seconds)
        return function(*args, **kwargs)
    return slow


class WindowWithAYear(unittest.TestCase):
    """The shed, its year computed from a weather year put in the cache: no network."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        cls.meteo = clear_sky_meteo(45.5226, 9.03)

    def setUp(self):
        _setup.window(self, capannone(), config.Config(background="none", theme="light"), size=(1400, 900),
                      cache=self.meteo)
        self.bid = self.win.project.buildings[0].id
        self.wait_until = _setup.wait_until

    def compute(self) -> dict:
        self.win.energy = {}
        self.win._compute_energy(fetch=False)
        self.assertTrue(self.wait_until(self.app, lambda: bool(self.win.energy), 60), "the year did not come back")
        return self.win.energy


class StaleValues(WindowWithAYear):
    PAGES = ("production", "consumption", "economics")

    def marked(self) -> list:
        """What says «to update»: the phases' titles, the tiles, the Checks' title."""
        from meridiana.ui import waiting
        win = self.win
        out = [pid for pid in self.PAGES if win.tabs.is_stale(pid)]
        for page in (win.energy_page, win.consumption_page, win.economics_page):
            out += [page.tiles[0].label.text()] if waiting.is_stale(page.tiles[0].value) else []
        if win.checks_dock.windowTitle().endswith(waiting.STALE_MARK):
            out.append("checks")
        return out

    def test_the_values_are_greyed_while_the_project_has_changed_and_clean_with_the_new_year_or_an_undo(self):
        win = self.win
        self.compute()
        self.assertEqual(self.marked(), [])
        # a name changed leaves the values as they are
        win._edited("building", self.bid, {"name": "Magazzino"})
        self.assertEqual(self.marked(), [])
        # a height changed marks them at once, an undo back to the state computed clears the mark at once
        win._edited("building", self.bid, {"height": 12.0})
        self.assertTrue(win.stale_shown)
        win.undo.undo()
        self.assertFalse(win.stale_shown)                       # the same key as the year in hand
        self.assertEqual(self.marked(), [])
        # changed again: the values greyed, still there to read, then clean when the new year comes by itself
        win.show_phase("production")
        value = win.energy_page.tiles[0].value

        def darkest() -> int:
            image = value.grab().toImage()
            return min(image.pixelColor(x, y).lightness() for x in range(image.width()) for y in range(image.height()))

        self.assertTrue(_setup.wait_settled(self.app, darkest, turns=3))      # the tile drawn and still
        fresh = darkest()
        before = win.energy_page.tiles[0].text()
        win._edited("building", self.bid, {"height": 12.0})
        # at once, before the layout and the year come back
        self.assertEqual(self.marked(), ["production", "consumption", "economics", "Energy a year", "Consumption a year",
                                         "Self-consumption", "checks"])
        self.assertEqual(win.tabs.tabText(win.tabs.index_of_phase("production")), "3 Production ·")
        self.assertEqual(win.energy_page.tiles[0].text(), before)          # still there to read
        self.assertGreater(darkest(), fresh + 30)               # in the theme's muted grey, under its style sheet
        self.assertIn("To update", win.energy_page.tiles[0].toolTip())
        self.assertTrue(self.wait_until(self.app, lambda: not win.stale_shown, 60), "the new year did not come")
        self.assertEqual(self.marked(), [])
        self.assertEqual(win.tabs.tabText(win.tabs.index_of_phase("production")), "3 Production")
        self.assertEqual(win.energy_page.tiles[0].toolTip(), "")
        # another project: no year, nothing to mark
        win._edited("building", self.bid, {"height": 14.0})
        self.assertTrue(win.stale_shown)
        win.open_path(self.file)
        self.assertEqual(self.marked(), [])


class Arcs(WindowWithAYear):
    def test_the_arcs_of_the_plan_and_of_the_pages_past_the_threshold_with_the_words_in_the_status_bar(self):
        from unittest import mock

        from meridiana import jobs
        from meridiana.energy import pipeline
        win = self.win
        # the plan: under the north arrow, only past the threshold, while the modules are laid
        plan = win.plan
        with mock.patch.object(jobs, "layout_of", slowed(jobs.layout_of, 0.9)):
            win._edited("building", self.bid, {"height": 13.0})
            spin(self.app, 200)
            self.assertTrue(plan.laying.isHidden())                 # under the threshold: nothing
            self.assertTrue(self.wait_until(self.app, lambda: not plan.laying.isHidden(), 2))
            self.assertTrue(plan.laying.turning())
            self.assertLess(abs(plan.laying.geometry().center().x() - plan.north.geometry().center().x()), 2)
            self.assertGreater(plan.laying.y(), plan.north.geometry().bottom())
            self.assertTrue(self.wait_until(self.app, lambda: not plan.laying_wait.waiting, 20))
        self.assertTrue(plan.laying.isHidden())                     # gone as the layout comes back
        self.assertEqual(win.project.buildings[0].height, 13.0)
        # the energy pages: in the top right corner while the year is computed, the words in the status bar
        page = win.energy_page
        with mock.patch.object(pipeline, "compute_or_say", slowed(pipeline.compute_or_say, 0.9)):
            win.energy = {}
            win.show_phase("production")                            # no year yet: computed by itself
            spin(self.app, 150)
            self.assertTrue(page.spinner.isHidden())
            self.assertTrue(win.busy.isHidden())
            self.assertTrue(self.wait_until(self.app, lambda: not page.spinner.isHidden(), 2))
            self.assertFalse(win.busy.isHidden())
            self.assertIn("Production", win.busy.text())
            area = page.centre.viewport().geometry()
            self.assertLessEqual(page.spinner.geometry().right(), area.right())
            self.assertLess(area.right() - page.spinner.geometry().right(), 16)
            self.assertLess(page.spinner.y() - area.top(), 16)
            self.assertTrue(self.wait_until(self.app, lambda: bool(win.energy), 60))
        self.assertTrue(page.spinner.isHidden())
        self.assertTrue(win.busy.isHidden())
        self.assertTrue(win.consumption_page.spinner.isHidden())

    def test_the_3d_view_has_its_skeleton_until_its_first_frame(self):
        from meridiana.ui.window import MainWindow
        win = MainWindow(self.paths, config.Config(background="none"))
        self.addCleanup(_setup.dispose, win)
        skeleton = win.skeleton
        self.assertIsNotNone(skeleton)
        gone = []
        skeleton.gone.connect(gone.append)
        win.open_path(self.file)
        self.assertEqual(len(skeleton.boxes), 1)                    # the building of the plan
        win.resize(1200, 800)
        win.show()
        if not win.view3d.drawn():
            # no graphics device here (the offscreen platform): the view will draw no frame, the skeleton goes at
            # once instead of waiting for the time limit (R120: the 3D view is a picture, not a QQuickWidget)
            self.assertTrue(self.wait_until(self.app, lambda: bool(gone), 2))
            self.assertEqual(gone, ["not drawn"])
            self.assertIsNone(win.skeleton)
            return
        self.assertTrue(skeleton.isVisible())                       # over the view, before its first frame
        self.assertEqual(skeleton.size(), win.view3d.size())
        self.assertTrue(self.wait_until(self.app, lambda: bool(gone), 5))
        self.assertEqual(gone, ["frame"])                           # by the first frame, not by the time limit
        self.assertIsNone(win.skeleton)
        win._show_3d()                                              # nothing left to feed


class Bars(WindowWithAYear):
    """The bar with its percentage and Cancel, only for PVGIS and the PDF report (study 16, F4)."""

    def fake_pvgis(self, steps: list, pause: float = 0.4):
        """compute_or_say as a PVGIS of three steps, each `pause` long, then the year from the cache; `steps` gets
        each step the window let it go past."""
        from meridiana.energy import pipeline
        real = pipeline.compute_or_say

        def fake(project, results, cache, fetch, progress=None):
            for done, what in enumerate(("the typical year", "the horizon", "PVGIS's estimate")):
                progress(done, 3, what)
                steps.append(done)
                time.sleep(pause)
            return real(project, results, cache, False)
        return fake

    def watch(self, widget, until, seconds: float = 20.0) -> list:
        """What the bar showed, (value, text), while waiting for `until`."""
        seen = []
        end = time.perf_counter() + seconds
        while time.perf_counter() < end and not until():
            self.app.processEvents()
            if not widget.isHidden() and (widget.bar.value(), widget.label.text()) not in seen:
                seen.append((widget.bar.value(), widget.label.text()))
            time.sleep(0.005)
        self.assertTrue(until(), seen)
        return seen

    def test_pvgis_moves_the_bar_step_by_step_and_cancel_half_way_leaves_the_project_as_it_was(self):
        from unittest import mock

        from meridiana.energy import pipeline
        win = self.win
        steps = []
        bar = win.pvgis_progress
        with mock.patch.object(pipeline, "compute_or_say", self.fake_pvgis(steps)):
            win._compute_energy(fetch=True)
            spin(self.app, 150)
            self.assertTrue(bar.isHidden())                         # under the threshold: nothing yet
            seen = self.watch(bar, lambda: bool(win.energy))
        self.assertEqual(steps, [0, 1, 2])
        self.assertEqual([v for v, _t in seen], [0, 33, 67])        # the bar moved step by step
        self.assertEqual(seen[1][1], "PVGIS: the horizon (2 of 3)")
        self.assertTrue(win.busy.isHidden())                        # the bar says it: not the words as well
        self.assertTrue(bar.isHidden())
        self.assertIsNotNone(win.energy.get("sim"))
        # again, and Cancel past the first request: the year in hand and the project as they were
        year = win.energy
        project = win.snapshot()
        steps.clear()
        with mock.patch.object(pipeline, "compute_or_say", self.fake_pvgis(steps)):
            win._compute_energy(fetch=True)
            self.watch(bar, lambda: bar.bar.value() >= 33)
            bar.cancel.click()
            self.assertTrue(bar.isHidden())                         # gone at once
            spin(self.app, 900)                                     # the job reaches its next step, and stops
        self.assertEqual(steps, [0, 1])                             # never asked the third
        self.assertIs(win.energy, year)
        self.assertEqual(win.snapshot(), project)
        self.assertTrue(win.energy_page.spinner.isHidden())
        self.assertIn("stopped", win.energy_page.status.text())
        self.assertFalse(win.stale_shown)

    def test_the_report_shows_its_bar_page_by_page_and_cancel_leaves_nothing(self):
        from unittest import mock

        from PySide6.QtWidgets import QFileDialog

        from meridiana.ui import report_chapters
        self.compute()
        bar = self.win.report_progress
        first = self.file.with_name("relazione.pdf")
        with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(str(first), "")), \
                mock.patch.object(report_chapters, "figure_png", slowed(report_chapters.figure_png, 0.3)):
            self.win.commands["export_report"].trigger()
            self.assertIsNotNone(self.win.report_run)               # going on: no modal window
            seen = self.watch(bar, lambda: "report" in self.win.exports, 120)
        self.assertTrue(first.read_bytes().startswith(b"%PDF"))
        self.assertFalse(first.with_name(first.name + ".part").exists())
        self.assertTrue(bar.isHidden())
        texts = [t for _v, t in seen]
        self.assertTrue(any("charts and formulas" in t for t in texts), texts)
        pages = [t for t in texts if "page" in t]
        self.assertTrue(pages and pages[-1].startswith("Report: page") and "of" in pages[-1], texts)
        values = [v for v, _t in seen]
        self.assertEqual(values, sorted(values))                    # only forwards
        # a second one, stopped half way: nothing written, the first one stays the report made
        second = self.file.with_name("seconda.pdf")
        with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(str(second), "")), \
                mock.patch.object(report_chapters, "figure_png", slowed(report_chapters.figure_png, 0.3)):
            self.win.commands["export_report"].trigger()
            self.watch(bar, lambda: not bar.isHidden())
            bar.cancel.click()
        self.assertTrue(bar.isHidden())
        self.assertIsNone(self.win.report_run)
        spin(self.app, 300)
        self.assertFalse(second.exists())
        self.assertFalse(second.with_name(second.name + ".part").exists())
        self.assertEqual(self.win.exports["report"][0], "relazione.pdf")

    def test_closing_the_window_stops_the_report_and_preview_and_removes_the_partial_file(self):
        from unittest import mock

        from PySide6.QtWidgets import QFileDialog

        from meridiana.ui import report_chapters
        self.compute()
        win = self.win
        target = self.file.with_name("chiusura.pdf")
        part = target.with_name(target.name + ".part")
        preview_closed = []

        def preview_steps():
            try:
                yield 0.5, "page"
            finally:
                preview_closed.append(True)

        win.preview_run = (preview_steps(), [], "test")
        next(win.preview_run[0])
        win.preview_soon.start()
        try:
            with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "")), \
                    mock.patch.object(report_chapters, "figure_png", slowed(report_chapters.figure_png, 0.3)):
                win.commands["export_report"].trigger()
                self.assertTrue(self.wait_until(self.app, part.exists, 120), "the partial report was not started")
                self.assertTrue(win.close())
            self.assertFalse(part.exists())
            self.assertIsNone(win.report_run)
            self.assertIsNone(win.preview_run)
            self.assertEqual(preview_closed, [True])
            self.assertFalse(win.preview_soon.isActive())
            spin(self.app, 300)
            self.assertFalse(part.exists())
        finally:
            for name in ("report_run", "preview_run"):
                run = getattr(win, name)
                if run is not None:
                    run[0].close()
                    setattr(win, name, None)
            part.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
