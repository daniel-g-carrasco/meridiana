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


OWNER = """
import sys
from pathlib import Path
from meridiana import model, recovery
state = Path(sys.argv[1])
mark = recovery.claim(state)
recovery.write(state, Path(sys.argv[2]), model.Project(name="Still open").to_json())
print("ready", mark, flush=True)
sys.stdin.readline()                    # until the test lets it go (or kills it: a crash)
recovery.release(state)
"""


class Instances(unittest.TestCase):
    """A copy belongs to the Meridiana that wrote it while that one runs (R07, second start): a second start never
    offers it, so «No» cannot delete it and «Yes» cannot take it. Real processes: the lock is the system's."""

    def setUp(self):
        self.state = Path(tempfile.mkdtemp())
        self.file = Path(tempfile.mkdtemp()) / "aperto.meridiana"

    def owner(self):
        import os
        import subprocess
        import sys
        src = str(Path(recovery.__file__).resolve().parents[1])
        process = subprocess.Popen([sys.executable, "-c", OWNER, str(self.state), str(self.file)],
                                   env=dict(os.environ, PYTHONPATH=src), stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: (process.kill(), process.wait(30), process.stdin.close(), process.stdout.close(),
                                 process.stderr.close()))
        line = process.stdout.readline().split()
        self.assertEqual(line[:1], ["ready"], process.stderr.read() if process.poll() is not None else "")
        process.mark = line[1]          # the venv's python.exe on Windows is a launcher: its pid is not the owner's
        return process

    def crash(self, process):
        """The process killed, and its lock waited for: Windows lets the locks of a process that ended go a moment
        later, «depending upon available system resources» (LockFileEx); until then the copy counts as still in
        use, the safe side."""
        import os
        import time
        process.kill()
        process.wait(30)
        lock = self.state / "recovery" / recovery.OWNERS / f"{process.mark}.lock"
        deadline = time.monotonic() + 10
        while True:
            fd = os.open(lock, os.O_RDWR)
            try:
                if recovery._lock(fd):
                    recovery._unlock(fd)
                    return lock
            finally:
                os.close(fd)
            self.assertLess(time.monotonic(), deadline, "the lock of the process killed was never let go")
            time.sleep(0.05)

    def test_the_copy_of_a_meridiana_still_running_is_not_offered_to_another(self):
        process = self.owner()
        copy = recovery.slot(self.state, self.file)
        self.assertTrue(copy.exists())
        self.assertEqual(recovery.pending(self.state), [])
        self.assertEqual(recovery.pending(self.state, self.file), [])
        self.assertTrue(copy.exists())
        # it stops as it should: a save or a close would have taken the copy; here it is still there and offered
        process.stdin.write("\n")
        process.stdin.flush()
        self.assertEqual(process.wait(30), 0)
        self.assertEqual([c["file"] for c in recovery.pending(self.state)], [copy])

    def test_the_copy_of_a_meridiana_that_crashed_is_offered_and_its_lock_cleared(self):
        lock = self.crash(self.owner())         # no release: the lock file stays, the system's lock goes
        copies = recovery.pending(self.state)
        self.assertEqual([model.Project.from_json(c["project"]).name for c in copies], ["Still open"])
        self.assertFalse(lock.exists())

    def test_a_new_start_clears_the_locks_of_crashed_starts_and_keeps_the_live_ones(self):
        alive = self.owner()
        self.crash(self.owner())
        folder = self.state / "recovery" / recovery.OWNERS
        self.assertEqual(len(list(folder.glob("*.lock"))), 2)
        mine = recovery.claim(self.state)
        self.addCleanup(recovery.release, self.state)
        self.assertEqual(len(list(folder.glob("*.lock"))), 2)      # the live one and mine
        self.assertTrue((folder / f"{mine}.lock").exists())
        self.assertIsNone(alive.poll())

    def test_this_process_own_copies_and_the_older_ones_are_offered(self):
        # a copy without an owner (written before R07, or by a start that could not claim) is offered as before;
        # one of this very process too (the tests make the next window in the same process)
        recovery.write(self.state, None, model.Project(name="Vecchio").to_json())
        recovery.claim(self.state)
        self.addCleanup(recovery.release, self.state)
        recovery.write(self.state, self.file, model.Project(name="Mio").to_json())
        self.assertEqual(sorted(model.Project.from_json(c["project"]).name for c in recovery.pending(self.state)),
                         ["Mio", "Vecchio"])

    def test_with_a_project_asked_for_only_its_own_copy_is_offered(self):
        recovery.write(self.state, None, model.Project(name="Nuovo").to_json())
        recovery.write(self.state, self.file, model.Project(name="Aperto").to_json())
        other = self.file.with_name("altro.meridiana")
        self.assertEqual([model.Project.from_json(c["project"]).name for c in recovery.pending(self.state, self.file)],
                         ["Aperto"])
        self.assertEqual(recovery.pending(self.state, other), [])
        self.assertEqual(len(recovery.pending(self.state)), 2)

    def test_an_owner_name_that_is_not_a_lock_of_ours_is_never_a_path(self):
        # the owner is read from a file: «../../x» must not reach outside the folder of the locks
        recovery.write(self.state, self.file, model.Project(name="Strano").to_json())
        copy = recovery.slot(self.state, self.file)
        import json
        data = json.loads(copy.read_text(encoding="utf-8"))
        data["owner"] = "../../config/config"
        copy.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(len(recovery.pending(self.state)), 1)


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
