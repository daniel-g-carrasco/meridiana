"""The times the designer feels, measured on this machine when asked (MERIDIANA_ESTERNI=1): a busy machine fails
them with the program unchanged, so they are not in the suite (study 18, D 5.2 and 7.4). The suite proves the
reasons of the speed instead: the catalogue makes the cells of the rows drawn only (test_catalog_dialog), the plan
repaints only what changes (test_plan_aids). PySide6 and a display (offscreen will do)."""

import os
import statistics
import time
import unittest

import _setup

from meridiana import catalog

ASKED = os.environ.get("MERIDIANA_ESTERNI") == "1"
FAST = 0.6          # seconds: 200 ms asked (R25), measured 130-150 ms to open and 50-80 ms to filter offscreen; a margin


@unittest.skipUnless(ASKED, "the times are measured only when asked: MERIDIANA_ESTERNI=1")
class CatalogueTimes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        catalog.prepare("modules")                          # the file read once, as at the second opening

    def setUp(self):
        from meridiana.ui import catalog_dialog
        catalog_dialog.forget_filters()
        self.addCleanup(catalog_dialog.forget_filters)

    def opened(self):
        from meridiana.ui.catalog_dialog import CatalogDialog
        start = time.perf_counter()
        dialog = CatalogDialog("modules")
        dialog.show()
        self.app.processEvents()
        self.assertTrue(_setup.wait_until(self.app, lambda: not dialog.reading, 20))
        took = time.perf_counter() - start
        self.addCleanup(_setup.dispose, dialog)
        return dialog, took

    def test_the_catalogue_opens_on_every_module_quickly(self):
        dialog, took = self.opened()
        self.assertEqual(dialog.rows.rowCount(), len(catalog.load("modules")))
        self.assertLess(took, FAST)

    def test_a_search_and_every_filter_are_quick(self):
        dialog, _took = self.opened()
        dialog.query.setText("jinko")
        start = time.perf_counter()
        dialog._search()
        self.app.processEvents()
        self.assertLess(time.perf_counter() - start, FAST)
        dialog.query.setText("")
        dialog.family.setCurrentIndex(dialog.family.findData("thin_film"))
        dialog.bifacial.setCurrentIndex(dialog.bifacial.findData("yes"))
        dialog.efficiency.setValue(30.0)
        start = time.perf_counter()
        dialog._search()
        self.app.processEvents()
        self.assertLess(time.perf_counter() - start, FAST)
        self.assertEqual(dialog.rows.rowCount(), 0)


@unittest.skipUnless(ASKED, "the times are measured only when asked: MERIDIANA_ESTERNI=1")
class PlanTimes(unittest.TestCase):
    """The modules drawn once per zoom and kept as an image (study 12, P2-B): panning 8,547 modules went from 76 to
    0,6 ms a step at the whole view (offscreen, 22/10/2026)."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_a_pan_over_thousands_of_modules_repaints_in_a_few_milliseconds(self):
        import tempfile
        from pathlib import Path

        from PySide6.QtTest import QTest

        from _fixtures import generated
        from meridiana import jobs
        from meridiana.ui.plan import PlanView
        p = generated(40, 2, 0)
        results, _keys, _laid = jobs.layout_of(p)
        modules = sum(r.count for r in results.values())
        self.assertGreater(modules, 4000)
        view = PlanView(Path(tempfile.mkdtemp()))
        self.addCleanup(view.deleteLater)
        self.addCleanup(view.close)
        view.set_source("none")
        view.resize(1200, 800)
        view.show()
        self.assertTrue(QTest.qWaitForWindowExposed(view, 2000))
        view.show_project(p, results)
        view.fit()
        view.set_tool("select")
        view.viewport().repaint()                            # the first frame makes the image of the modules
        steps = []
        bar = view.horizontalScrollBar()
        for k in range(30):
            bar.setValue(bar.value() + (5 if k % 2 == 0 else -5))
            start = time.perf_counter()
            view.viewport().repaint()
            steps.append(time.perf_counter() - start)
        self.assertLess(statistics.median(steps), 0.010, f"{modules} modules: {statistics.median(steps) * 1000:.1f} ms")


if __name__ == "__main__":
    unittest.main()
