"""IFC in the window (studies 15 and 20): File > Export the model as IFC4 written in a job with its bar, File > Import
an IFC model read in a process of its own and added as one change that Ctrl+Z takes away, Cancel on the bar, the File
page's tiles. One journey on one window (study 18, D 7.1). PySide6, a display (offscreen will do) and ifcopenshell."""

import sys
import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import capannone as sample
from _setup import wait_until

from meridiana import ifc_import, ifc_read

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class IfcInTheWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        if not ifc_read.available():
            raise unittest.SkipTest("ifcopenshell is not installed")

    def setUp(self):
        _setup.window(self, sample())
        self.folder = Path(tempfile.mkdtemp())

    def the_file_menu_and_the_file_page_have_the_two_commands(self):
        texts = [a.text() for a in self.win.menuBar().actions()[0].menu().actions()]
        self.assertIn(self.win.commands["import_ifc"].text(), texts)
        self.assertIn(self.win.commands["export_ifc"].text(), texts)
        from PySide6.QtWidgets import QLabel
        page = self.win.file_page
        words = [w.text() for w in page.sections["import"].findChildren(QLabel)]
        self.assertIn("IFC model", words)
        words = [w.text() for w in page.sections["export"].findChildren(QLabel)]
        self.assertIn("IFC4 model", words)

    def the_project_is_written_as_ifc4_in_a_job_and_said(self):
        from meridiana import ifc_export
        target = self.folder / "capannone.ifc"
        self.win._export_ifc(str(target))
        self.assertIsNotNone(self.win.ifc_job)
        self.assertTrue(wait_until(self.app, lambda: self.win.ifc_job is None, 60), "the export did not end")
        self.assertTrue(target.exists())
        self.assertEqual(ifc_export.validate(target), [])
        self.assertIn("IFC4 written: capannone.ifc", self.win.statusBar().currentMessage())
        from meridiana import phases                        # the Report phase's deliverable, made
        made = {d.id: d for d in phases.deliverables(False, self.win.exports, self.win._state_key())}
        self.assertEqual(made["ifc"].state, "done")
        return target

    def a_model_is_read_apart_shown_and_added_as_one_change(self, path):
        before = len(self.win.project.buildings)
        seen = []

        def confirm(found):
            seen.append(found)
            return ifc_import.plan(found, self.win.project, "origin", "context")
        self.win._import_ifc(str(path), confirm=confirm)
        self.assertIsNotNone(self.win.ifc_reading)                     # the window goes on while it is read
        self.assertTrue(wait_until(self.app, lambda: self.win.ifc_reading is None, 60), "the reading did not end")
        self.assertEqual(len(seen), 1)
        self.assertEqual(len(self.win.project.buildings), before + 1)
        self.assertEqual(self.win.selection[0], "building")
        self.assertIn("Ctrl+Z", self.win.hint.text())
        self.win.undo.undo()
        self.assertEqual(len(self.win.project.buildings), before)

    def cancel_on_the_bar_stops_the_reading_and_adds_nothing(self):
        before = len(self.win.project.buildings)
        self.win._import_ifc(str(self.folder / "x.ifc"), confirm=lambda found: None,
                             command=[sys.executable, "-c", "import time; time.sleep(60)"])
        self.assertTrue(self.win.ifc_reading is not None and self.win.ifc_reading.running())
        self.win._cancel_ifc()
        self.assertIsNone(self.win.ifc_reading)
        self.assertIn("nothing added", self.win.statusBar().currentMessage())
        self.assertEqual(len(self.win.project.buildings), before)

    def a_reading_that_fails_is_said_in_a_dialog(self):
        bad = self.folder / "testo.ifc"
        bad.write_text("nothing", encoding="utf-8")
        self.win._import_ifc(str(bad), confirm=lambda found: None)
        self.assertTrue(wait_until(self.app, lambda: self.win.ifc_reading is None, 60))
        self.assertEqual(self.dialogs[-1][0], "warning")
        self.assertIn("testo.ifc could not be read", self.dialogs[-1][1][1])

    def test_an_export_that_answers_after_the_window_is_destroyed_is_dropped(self):
        import threading
        from unittest import mock
        win = self.win
        with mock.patch.object(win.pool, "start"):
            win._export_ifc(str(self.folder / "late.ifc"))
        job = win.ifc_job
        _setup.dispose(win)

        def answer():
            job.signals.step.emit(0.5, "write")
            job.signals.done.emit(None)

        errors = []
        with mock.patch("sys.excepthook", side_effect=lambda kind, value, tb:
                        errors.append(f"{kind.__name__}: {value}")):
            worker = threading.Thread(target=answer)
            worker.start()
            worker.join(5)
            self.assertFalse(worker.is_alive())
            self.app.processEvents()
        self.assertEqual(errors, [])

    def test_exported_read_back_added_undone_cancelled_and_a_bad_file_said(self):
        self.the_file_menu_and_the_file_page_have_the_two_commands()
        target = self.the_project_is_written_as_ifc4_in_a_job_and_said()
        self.a_model_is_read_apart_shown_and_added_as_one_change(target)
        self.a_model_is_read_apart_shown_and_added_as_one_change(_setup.DATA / "ifc" / "Building-Architecture.ifc")
        self.cancel_on_the_bar_stops_the_reading_and_adds_nothing()
        self.a_reading_that_fails_is_said_in_a_dialog()


if __name__ == "__main__":
    unittest.main()
