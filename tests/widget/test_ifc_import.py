"""The reading of an IFC model watched by the window (ui/ifc_import.py; study 20, section 4): the worker that reads and
tells its progress, the one that never ends stopped at the time allowed, the one that takes too much memory stopped,
the one that crashes said without touching the window, Cancel; then the dialog that shows what was found and where it
goes. PySide6 and a display (offscreen will do); the real worker needs ifcopenshell."""

import sys
import tempfile
import time
import unittest
from pathlib import Path

import _setup
from _setup import wait_until

from meridiana import ifc_import, ifc_read, model

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

SAMPLE = _setup.DATA / "ifc" / "Building-Architecture.ifc"


class Reading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def reading(self, path=SAMPLE, **more):
        from meridiana.ui.ifc_import import IfcReading
        r = IfcReading(str(path), **more)
        self.got = {"progress": [], "done": None, "failed": None}
        r.progress.connect(lambda f, w: self.got["progress"].append(f))
        r.done.connect(lambda found: self.got.__setitem__("done", found))
        r.failed.connect(lambda why: self.got.__setitem__("failed", why))
        self.addCleanup(r.cancel)
        r.start()
        return r

    def ended(self, r, seconds=60.0) -> bool:
        return wait_until(self.app, lambda: not r.running(), seconds)

    def test_the_worker_reads_tells_its_progress_and_gives_the_buildings(self):
        if not ifc_read.available():
            self.skipTest("ifcopenshell is not installed")
        r = self.reading()
        self.assertTrue(self.ended(r), "the reading did not end")
        self.assertIsNone(self.got["failed"])
        self.assertEqual(len(self.got["done"]["buildings"]), 1)
        self.assertEqual(self.got["progress"][-1], 1.0)
        self.assertGreater(self.got["done"]["read_seconds"], 0.0)

    def test_a_worker_that_never_ends_is_stopped_at_the_time_allowed(self):
        r = self.reading(budget_s=1.0, command=[sys.executable, "-c", "import time; time.sleep(60)"])
        start = time.monotonic()
        self.assertTrue(self.ended(r, 20), "the worker was not stopped")
        self.assertLess(time.monotonic() - start, 10.0)
        self.assertIn("more than 1 s", self.got["failed"])
        self.assertIsNone(self.got["done"])

    def test_a_worker_that_takes_too_much_memory_is_stopped(self):
        # 300 MB against 100 allowed: on Windows the venv's python.exe is a launcher of 4 MB and the interpreter its
        # child, so only the memory of the whole tree stops it (procmem.rss with tree)
        r = self.reading(memory=100 << 20, command=[sys.executable, "-c", "import time; x = bytearray(300 << 20); "
                                                                            "time.sleep(60)"])
        self.assertTrue(self.ended(r, 20), "the worker was not stopped")
        self.assertIn("memory", self.got["failed"])

    def test_a_worker_that_crashes_is_said_and_nothing_is_given(self):
        r = self.reading(command=[sys.executable, "-c", "import os; os._exit(139)"])
        self.assertTrue(self.ended(r, 20))
        self.assertIn("139", self.got["failed"])
        self.assertIsNone(self.got["done"])

    def test_a_worker_that_crashes_is_asked_again_in_the_simple_way_and_its_result_says_so(self):
        if not ifc_read.available():
            self.skipTest("ifcopenshell is not installed")
        from meridiana.ui.ifc_import import worker_command
        asked = []

        def command(mode):
            asked.append(mode)
            if mode == "direct":
                return [sys.executable, "-c", "import os; os._exit(139)"]
            _program, args, _env = worker_command(str(SAMPLE), mode)      # its environment is the worker's own
            return [sys.executable, *args]
        r = self.reading(command=command)
        self.assertTrue(self.ended(r), "the second try did not end")
        self.assertEqual(asked, ["direct", "simple"])
        self.assertIsNone(self.got["failed"])
        self.assertIn("139", self.got["done"]["second_try"])
        self.assertEqual(self.got["done"]["mode"], "simple")
        self.assertEqual(len(self.got["done"]["buildings"]), 1)          # the sample's shapes are all simple

    def test_cancel_kills_the_worker_and_says_nothing(self):
        r = self.reading(command=[sys.executable, "-c", "import time; time.sleep(60)"])
        self.assertTrue(wait_until(self.app, lambda: r.process.processId() > 0, 10))
        r.cancel()
        self.assertFalse(r.running())
        self.assertIsNone(self.got["failed"])
        self.assertIsNone(self.got["done"])

    def test_a_file_that_is_not_ifc_is_said_with_its_reason(self):
        if not ifc_read.available():
            self.skipTest("ifcopenshell is not installed")
        bad = Path(tempfile.mkdtemp()) / "testo.ifc"
        bad.write_text("nothing", encoding="utf-8")
        r = self.reading(bad)
        self.assertTrue(self.ended(r))
        self.assertIn("testo.ifc could not be read", self.got["failed"])


class Bar(unittest.TestCase):
    def test_the_bar_moves_without_a_percentage_while_the_file_is_opened_then_counts(self):
        _setup.qt_or_skip()
        from meridiana.ui.waiting import Progress
        bar = Progress()
        self.addCleanup(_setup.dispose, bar)
        bar.unknown("IFC: opening the file")
        self.assertEqual((bar.bar.minimum(), bar.bar.maximum()), (0, 0))
        self.assertEqual(bar.label.text(), "IFC: opening the file")
        bar.set(0.4, "IFC: the roofs")
        self.assertEqual((bar.bar.maximum(), bar.bar.value()), (100, 40))


class Dialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        if not ifc_read.available():
            raise unittest.SkipTest("ifcopenshell is not installed")
        _setup.meridiana_look()
        cls.found = ifc_read.read(SAMPLE)
        cls.found["read_seconds"] = 0.3

    def test_the_places_offered_the_north_asked_and_the_plan_of_the_choices(self):
        from PySide6.QtWidgets import QRadioButton

        from meridiana.ui.ifc_import import IfcImportDialog
        d = IfcImportDialog(self.found, model.Project(), "Building-Architecture.ifc")
        self.addCleanup(_setup.dispose, d)
        hows = [b.property("how") for b in d.findChildren(QRadioButton) if b.property("how")]
        self.assertEqual(hows, ["file", "site", "origin"])
        norths = [b.property("north") for b in d.findChildren(QRadioButton) if b.property("north")]
        self.assertEqual(norths, ["map", "context"])        # the map and the TrueNorth disagree: the designer chooses
        self.assertEqual(d.choice()[0], "site")             # an empty project: its site goes to the model
        self.assertEqual(len(d.plan().buildings), 1)
        next(b for b in d.findChildren(QRadioButton) if b.property("how") == "origin").setChecked(True)
        next(b for b in d.findChildren(QRadioButton) if b.property("north") == "context").setChecked(True)
        self.assertEqual(d.choice(), ("origin", "context"))
        self.assertIsNone(d.plan().site)
        xs = [x for x, _y in d.plan().buildings[0].footprint]
        self.assertAlmostEqual(min(xs) + max(xs), 0.0, places=2)
        self.assertTrue(d.buttons.button(d.buttons.StandardButton.Ok).isEnabled())

    def test_a_model_without_a_building_cannot_be_added(self):
        from meridiana.ui.ifc_import import IfcImportDialog
        found = ifc_read.read(_setup.DATA / "ifc" / "Building-Hvac.ifc")
        d = IfcImportDialog(found, model.Project(), "Building-Hvac.ifc")
        self.addCleanup(_setup.dispose, d)
        self.assertFalse(d.buttons.button(d.buttons.StandardButton.Ok).isEnabled())
        self.assertIn("Nothing to add", d.problem.text())

    def test_the_preview_draws_the_outline(self):
        from PySide6.QtGui import QImage

        from meridiana.ui.ifc_import import IfcImportDialog
        d = IfcImportDialog(self.found, model.Project(), "Building-Architecture.ifc")
        self.addCleanup(_setup.dispose, d)
        d.preview.resize(320, 220)
        image = d.preview.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
        ink = d.preview.palette().text().color()
        drawn = sum(1 for y in range(0, image.height(), 2) for x in range(0, image.width(), 2)
                    if abs(image.pixelColor(x, y).lightness() - ink.lightness()) < 40)
        self.assertGreater(drawn, 30)
        self.assertEqual(len(ifc_import.plan(self.found, model.Project(), *d.choice()).buildings), 1)


if __name__ == "__main__":
    unittest.main()
