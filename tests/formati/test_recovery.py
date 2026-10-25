"""Autosave and recovery, and the revisions: a copy of the unsaved changes that a save takes away and a
new start offers back, and a new revision that never writes over a file."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401

from meridiana import model, recovery


class Copies(unittest.TestCase):
    def setUp(self):
        self.state = Path(tempfile.mkdtemp())
        self.file = Path(tempfile.mkdtemp()) / "capannone.meridiana"

    def test_a_copy_is_offered_back_and_taken_away(self):
        p = model.Project(name="Capannone")
        # the clock given, not waited for (Windows's moves in steps of 15 ms): the second copy is the later one
        with mock.patch.object(recovery.time, "time", return_value=1_000_000.0):
            recovery.write(self.state, self.file, p.to_json())
        with mock.patch.object(recovery.time, "time", return_value=1_000_001.0):
            recovery.write(self.state, None, model.Project(name="Nuovo").to_json())
        copies = recovery.pending(self.state)
        self.assertEqual(len(copies), 2)
        self.assertEqual(model.Project.from_json(copies[0]["project"]).name, "Nuovo")     # the newest first
        self.assertIn(str(self.file), [c["path"] for c in copies])
        recovery.clear(self.state, self.file)
        recovery.clear(self.state, None)
        self.assertEqual(recovery.pending(self.state), [])

    def test_a_damaged_copy_is_set_aside(self):
        bad = recovery.slot(self.state, self.file)
        bad.parent.mkdir(parents=True)
        bad.write_text("{", encoding="utf-8")
        self.assertEqual(recovery.pending(self.state), [])
        self.assertTrue(bad.with_suffix(".unreadable").exists())


class Revisions(unittest.TestCase):
    def test_the_next_revision_never_writes_over_a_file(self):
        folder = Path(tempfile.mkdtemp())
        first = folder / "Capannone.meridiana"
        self.assertEqual(recovery.next_revision(first).name, "Capannone_R01.meridiana")
        self.assertEqual(recovery.next_revision(folder / "Capannone_R03.meridiana").name, "Capannone_R04.meridiana")
        (folder / "Capannone_R01.meridiana").write_text("{}", encoding="utf-8")
        self.assertEqual(recovery.next_revision(first).name, "Capannone_R02.meridiana")


if __name__ == "__main__":
    unittest.main()
