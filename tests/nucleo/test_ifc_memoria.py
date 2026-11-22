"""R34: whether a model has the whole reading (its roofs through IfcOpenShell) depends on the memory, not on a size
fixed once (400 MB): the reading is tried when the file's size times ROOFS_MEMORY fits the memory allowed (the
worker's limit and the program's budget of memory, the lower). A model that does not fit comes in as the scan's
solids, and the import says why; before, a model past the limit came in as solids and nobody said it. During the
whole reading a guard watches the memory (and the time, when the caller gives one): past it the reading is left
cleanly and the scan's solids answer, said, never a crash; that answer is not kept as the model's.

A small sample stands for a large model: the memory allowed and the guards are forced."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401

from meridiana.app.exchange import ifc_import, ifc_worker
from meridiana.core.model import model

SAMPLE = str(Path(__file__).resolve().parents[1] / "data" / "ifc" / "parapetto-parziale.ifc")


def summary(found: dict) -> list[str]:
    return ifc_import.plan(found, model.Project(), "origin", None, name="t", source_name="t.ifc").left_out


def read(budget=None, folder=None) -> dict:
    return ifc_worker.read(SAMPLE, "direct", lambda f, w: None, budget, folder)


class Memory(unittest.TestCase):
    def test_with_the_memory_of_a_pc_it_comes_with_its_roofs(self):
        found = read()
        self.assertEqual(found["mode"], "direct")
        self.assertTrue(found["buildings"])
        self.assertNotIn("roofs_skipped", found["counts"])
        self.assertNotIn("roofs_stopped", found["counts"])
        fit, need, allowed = ifc_worker.fits(SAMPLE)
        self.assertTrue(fit)
        self.assertEqual(need, int(Path(SAMPLE).stat().st_size * ifc_worker.ROOFS_MEMORY))
        self.assertGreater(allowed, need)

    def test_too_little_memory_comes_as_solids_and_is_said(self):
        with mock.patch.object(ifc_worker, "allowed_memory", return_value=1000, create=True):
            found = read()
        self.assertEqual(found["mode"], "scan")
        self.assertFalse(found["buildings"])
        self.assertTrue(found["solids"])
        self.assertIn("large", found["notes"])
        self.assertEqual(found["counts"].get("roofs_skipped"), "memory")
        said = [line for line in summary(found) if "too large for the memory" in line]
        self.assertEqual(len(said), 1, summary(found))

    def test_the_memory_allowed_is_the_lower_of_the_two(self):
        from meridiana.core.compute import procmem, resources
        with mock.patch.object(procmem, "limit", return_value=5 << 30), \
                mock.patch.object(resources.Budget, "bytes", return_value=3 << 30):
            self.assertEqual(ifc_worker.allowed_memory(), 3 << 30)
        with mock.patch.object(procmem, "limit", return_value=2 << 30), \
                mock.patch.object(resources.Budget, "bytes", return_value=3 << 30):
            self.assertEqual(ifc_worker.allowed_memory(), 2 << 30)


class Guard(unittest.TestCase):
    def check_solids(self, found: dict, why: str) -> None:
        self.assertEqual(found["mode"], "scan")
        self.assertTrue(found["solids"])
        self.assertFalse(found["buildings"])
        self.assertEqual(found["counts"].get("roofs_stopped"), why)
        self.assertFalse(found.get("errors"))

    def test_past_the_memory_the_whole_reading_is_left(self):
        with mock.patch.object(ifc_worker, "MEMORY_GUARD", 0.0):
            found = read()
        self.check_solids(found, "memory")
        said = [line for line in summary(found) if "more memory than allowed" in line]
        self.assertEqual(len(said), 1, summary(found))

    def test_a_raised_signal_leaves_it(self):
        with mock.patch.object(ifc_worker.Guard, "check_memory", lambda self: self.over.set()):
            found = read()
        self.check_solids(found, "memory")

    def test_past_the_time_the_whole_reading_is_left(self):
        with mock.patch.object(ifc_worker, "TIME_GUARD", 0.0):
            found = read(budget=1000.0)
        self.check_solids(found, "time")
        self.assertTrue([line for line in summary(found) if "taking longer than the time" in line], summary(found))

    def test_without_a_budget_the_time_does_not_stop_it(self):
        with mock.patch.object(ifc_worker, "TIME_GUARD", 0.0):
            found = read()
        self.assertEqual(found["mode"], "direct")

    def test_a_scan_past_half_the_budget_does_not_start_it(self):
        found = read(budget=1e-6)
        self.assertEqual(found["mode"], "scan")
        self.assertEqual(found["counts"].get("roofs_skipped"), "time")
        self.assertTrue(found["solids"])
        self.assertTrue([line for line in summary(found) if "half the time" in line], summary(found))

    def test_a_stopped_reading_is_not_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = str(Path(tmp) / "c")
            with mock.patch.object(ifc_worker, "allowed_memory", return_value=1000), \
                    mock.patch.object(ifc_worker, "MEMORY_GUARD", 0.0):
                # the memory allowed so low that a kept answer would be used, the guard forced
                with mock.patch.object(ifc_worker, "fits", return_value=(True, 0, 1000)):
                    found = ifc_worker.read(SAMPLE, "direct", lambda f, w: None, None, folder)
                self.assertEqual(found["counts"].get("roofs_stopped"), "memory")
                self.assertFalse(Path(ifc_worker.result_file(folder, SAMPLE)).exists())
                self.assertIsNone(ifc_worker.cached_result(SAMPLE, folder))
                # and the one of a model too large for the memory is
                kept = ifc_worker.read(SAMPLE, "direct", lambda f, w: None, None, folder)
                self.assertEqual(kept["counts"].get("roofs_skipped"), "memory")
                self.assertTrue(Path(ifc_worker.result_file(folder, SAMPLE)).exists())


if __name__ == "__main__":
    unittest.main()
