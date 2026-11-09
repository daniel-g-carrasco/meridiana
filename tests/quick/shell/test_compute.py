"""The computation of the shell (M12, D26): a change stops the one in hand and starts at once; nothing stays «computing».

Uses a real process, on a project without modules, whose year ends at once with its remark.
"""
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

from _fixtures import capannone
from meridiana.quick.app import create_app
from meridiana.quick.backend import shell_compute
from meridiana.quick.backend.shell_compute import ShellBridge


class Compute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.folder.cleanup)
        self.bridge = ShellBridge(capannone(), Path(self.folder.name))
        self.addCleanup(self.bridge.close)

    def wait(self, condition, seconds=90):
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            self.app.processEvents()
            if condition():
                return True
            time.sleep(.01)
        return False

    def test_a_year_ends_and_nothing_stays_busy(self):
        self.bridge.recompute()
        self.assertTrue(self.bridge.busy)
        self.assertTrue(self.wait(lambda: not self.bridge.busy))
        self.assertEqual(self.bridge.error, '')

    def test_a_remark_of_the_year_is_not_an_error(self):
        # M15: «Lay the modules first» is for the result pages; the plan's hint and the errors stay free.
        self.bridge.session.project.subfields.clear()
        self.bridge.recompute()
        self.assertTrue(self.wait(lambda: not self.bridge.busy))
        self.assertEqual(self.bridge.error, '')
        self.assertTrue(self.bridge.yearNote)

    def test_a_change_stops_the_computation_in_hand_and_starts_at_once(self):
        self.bridge.recompute()
        first = self.bridge._job
        self.bridge.session.generation += 1
        self.bridge._launch()
        self.assertIsNot(self.bridge._job, first)
        self.assertTrue(first.cancelled)
        self.assertEqual(self.bridge._job.generation, self.bridge.session.generation)
        self.assertFalse(self.bridge._pending)
        self.assertTrue(self.wait(lambda: not self.bridge.busy))

    def test_a_process_is_kept_warm_for_the_next(self):
        # one process for each year, as before R478 (MERIDIANA_LIVE_COMPUTE=0): the next starts from a warm one
        with mock.patch.object(shell_compute, 'live_compute', return_value=False):
            self.bridge.recompute()
            spare = self.bridge._spare
            self.assertIsNotNone(spare)
            self.bridge.session.generation += 1
            self.bridge._launch()
            self.assertIs(self.bridge._job.process, spare)
            self.assertIsNot(self.bridge._spare, spare)
            self.assertTrue(self.wait(lambda: not self.bridge.busy))

    def test_the_years_process_is_the_same_for_the_next(self):
        # R478: the year's process stays for the session, with its caches
        self.bridge.recompute()
        process = self.bridge._job.process
        self.assertTrue(self.wait(lambda: not self.bridge.busy))
        self.bridge.recompute()             # asked again: computed, not taken from the years kept
        self.assertIs(self.bridge._job.process, process)
        self.assertTrue(self.wait(lambda: not self.bridge.busy))

    def test_closing_during_a_year_does_not_wait_for_it(self):
        self.bridge.recompute()
        start = time.perf_counter()
        self.bridge.close()
        self.assertLess(time.perf_counter() - start, 1.5)

    def test_cancel_ends_the_wait(self):
        self.bridge.recompute()
        self.bridge.cancelCompute()
        self.assertFalse(self.bridge.busy)
        self.assertEqual(self.bridge.progress, {})

    def test_a_snapshot_that_cannot_be_written_is_said_and_not_left_computing(self):
        # D26: raising in _launch left _busy on for ever.
        with mock.patch.object(shell_compute, 'Worker', side_effect=TypeError('cannot pickle')), \
                mock.patch.object(shell_compute, 'LiveWorker', side_effect=TypeError('cannot pickle')):
            self.bridge.recompute()
        self.assertFalse(self.bridge.busy)
        self.assertIn('pickle', self.bridge.error)


if __name__ == '__main__':
    unittest.main()
