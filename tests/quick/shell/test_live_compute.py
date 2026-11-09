"""R478: the process of the computation kept alive for the session of the project.

The year's process stays from one year to the next (its caches with it), a cancel stops the year and keeps the
process, a process that dies is started again and said, and nothing outlives the window: neither the process nor
the workers of its pool, when the window is closed or killed."""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from _fixtures import capannone
from meridiana.quick.app import create_app
from meridiana.quick.backend.shell_compute import Calculator, LiveWorker, ShellBridge
from meridiana.quick.sample import recorded_weather
from nucleo.test_pool_orphans import alive, wait_gone

SRC = Path(__file__).resolve().parents[3] / "src"

# a window that starts the process of the computation and its pool, says their numbers, and waits to be killed
WINDOW = r'''
import os, subprocess, sys, time
sys.path.insert(0, sys.argv[1])
env = dict(os.environ, MERIDIANA_WORKERS="2", PYTHONPATH=sys.argv[1])
serve = subprocess.Popen([sys.executable, "-m", "meridiana.quick.backend.shell_compute", "--serve",
                          "--parent", str(os.getpid())],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env)
assert serve.stdout.readline().startswith(b"ready")
serve.stdin.write(b"warm\n"); serve.stdin.flush()
line = serve.stdout.readline().split()
print(serve.pid, *[int(p) for p in line[1:]], flush=True)
time.sleep(600)
'''


class LiveCompute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.folder.cleanup)
        project = capannone()
        recorded_weather(project, Path(self.folder.name))
        self.bridge = ShellBridge(project, Path(self.folder.name))
        self.addCleanup(self.bridge.close)

    def wait(self, condition, seconds=240):
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            self.app.processEvents()
            if condition():
                return True
            time.sleep(.01)
        return False

    def year(self):
        self.bridge.recompute()
        self.assertIsInstance(self.bridge._job, LiveWorker)
        self.assertTrue(self.wait(lambda: not self.bridge.busy))
        self.assertEqual(self.bridge.error, '')
        self.assertIsNotNone(self.bridge.session.energy.get('sim'))
        return self.bridge._calculator.process.processId()

    def test_the_process_stays_from_one_year_to_the_next(self):
        first = self.year()
        kwh = self.bridge.session.energy['sim'].energy_kwh
        self.assertEqual(self.year(), first)
        self.assertEqual(self.bridge.session.energy['sim'].energy_kwh, kwh)

    def test_a_cancel_keeps_the_process_and_the_next_year_comes(self):
        first = self.year()
        self.bridge.recompute()
        self.assertTrue(self.wait(lambda: self.bridge._calculator.current is not None, 30))
        self.bridge.cancelCompute()
        self.assertFalse(self.bridge.busy)
        self.assertTrue(self.wait(lambda: self.bridge._calculator.current is None, 30))
        self.assertEqual(self.year(), first)
        self.assertEqual(self.bridge._calculator.restarts, 0)

    def test_a_process_that_dies_is_started_again_and_the_year_comes(self):
        first = self.year()
        self.bridge.recompute()
        self.assertTrue(self.wait(lambda: self.bridge._calculator.current is not None, 30))
        self.bridge._calculator.process.kill()
        self.assertTrue(self.wait(lambda: not self.bridge.busy))
        self.assertEqual(self.bridge.error, '')
        self.assertEqual(self.bridge._calculator.restarts, 1)
        self.assertNotEqual(self.bridge._calculator.process.processId(), first)
        self.assertEqual(wait_gone([first], 5), [])

    def test_closing_ends_the_process(self):
        pid = self.year()
        self.bridge.close()
        self.assertEqual(wait_gone([pid], 5), [])

    def test_nothing_outlives_a_killed_window(self):
        window = subprocess.Popen([sys.executable, "-c", WINDOW, str(SRC)], stdout=subprocess.PIPE, text=True)
        try:
            pids = [int(p) for p in window.stdout.readline().split()]
            self.assertGreaterEqual(len(pids), 2, "the process of the computation or its pool did not start")
            self.assertTrue(all(alive(p) for p in pids))
        finally:
            window.kill()
            window.wait(30)
            window.stdout.close()
        self.assertEqual(wait_gone(pids), [], "the process of the computation or its pool outlived the window")


class Unanswered(unittest.TestCase):
    def test_a_stop_not_answered_kills_and_starts_again(self):
        app = create_app()
        calculator = Calculator()
        try:
            end = time.perf_counter() + 60
            while not calculator.ready and time.perf_counter() < end:
                app.processEvents()
                time.sleep(.01)
            self.assertTrue(calculator.ready)
            first = calculator.process.processId()

            class Stuck:
                folder = Path(os.devnull)
                cancelled = retried = False

                def _cleanup(self):
                    pass

                def deleteLater(self):
                    pass
            calculator.current = Stuck()
            calculator.GRACE_MS = 50
            calculator.cancel(calculator.current)
            end = time.perf_counter() + 5
            while calculator.restarts == 0 and time.perf_counter() < end:
                app.processEvents()
                time.sleep(.01)
            self.assertEqual(calculator.restarts, 1)
            self.assertNotEqual(calculator.process.processId(), first)
        finally:
            calculator.close()


if __name__ == '__main__':
    unittest.main()
