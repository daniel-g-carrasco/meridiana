"""Closing the workbench cancels computation instead of waiting for the year."""
import tempfile
import time
import unittest
from pathlib import Path

from PySide6.QtCore import QProcess
from _fixtures import capannone
from meridiana.quick.app import create_app
from meridiana.quick.backend.shell_compute import ShellBridge
from meridiana.quick.sample import recorded_weather
from quick.gestures import wait_for


class ShutdownTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def test_close_cancels_live_worker_and_prevents_relaunch(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = ShellBridge(capannone(), Path(tmp))
            bridge.recompute()
            process = bridge._job.process
            wait_for(lambda: process.state() == QProcess.ProcessState.Running)
            start = time.perf_counter()
            bridge.close()
            self.assertLess(time.perf_counter()-start, 0.75)
            self.assertEqual(process.state(), QProcess.ProcessState.NotRunning)
            bridge.recompute()
            self.assertFalse(bridge.busy)
            bridge.close()

    def test_result_returns_to_the_shared_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = ShellBridge(capannone(), Path(tmp))
            try:
                bridge.recompute()
                wait_for(lambda: not bridge.busy, seconds=45)
                self.assertGreater(bridge.moduleCount, 0)
                self.assertTrue(bridge.session.good_results())
                self.assertFalse(bridge._error and 'Traceback' in bridge._error)
            finally:
                bridge.close()

    def test_close_after_layout_while_the_recorded_year_is_computing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = capannone()
            recorded_weather(project, Path(tmp))
            bridge = ShellBridge(project, Path(tmp))
            try:
                bridge.recompute()
                wait_for(lambda: bool(bridge.session.results), seconds=45)
                process = bridge._job.process
                self.assertTrue(bridge.busy)
                self.assertEqual(process.state(), QProcess.ProcessState.Running)
                start = time.perf_counter()
                bridge.close()
                self.assertLess(time.perf_counter()-start, .75)
                self.assertEqual(process.state(), QProcess.ProcessState.NotRunning)
            finally:
                bridge.close()


CLOSE_CHILD = r'''
import sys, tempfile
from pathlib import Path
from PySide6.QtCore import QTimer, qInstallMessageHandler
from _fixtures import capannone
from meridiana.quick.app import QuickWindow, create_app
from meridiana.quick.sample import recorded_weather

def said(kind, context, text):
    if 'TypeError' in text or 'ReferenceError' in text:
        sys.stderr.write('QML-ERROR ' + text + '\n')

app = create_app()
qInstallMessageHandler(said)
folder = tempfile.mkdtemp(prefix='meridiana-close-')
project = capannone()
recorded_weather(project, Path(folder))
host = QuickWindow(project, Path(folder))
host.window.resize(1200, 800)
host.window.show()
QTimer.singleShot(1500, host.window.close)
app.exec()
host.close()
sys.stderr.write('CLOSED\n')
'''


class CloseQuietTest(unittest.TestCase):
    """R451: closing the window as main() does, then the interpreter's end, says nothing in the log."""

    def test_no_binding_reads_a_freed_backend_after_the_window_closes(self):
        import os
        import subprocess
        import sys
        root = Path(__file__).resolve().parents[3]
        env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(root / 'tests'), str(root / 'src')]),
                   QT_QPA_PLATFORM='offscreen', QSG_RENDER_LOOP='basic', PYTHONUTF8='1')
        done = subprocess.run([sys.executable, '-c', CLOSE_CHILD], cwd=root, env=env, capture_output=True,
                              text=True, encoding='utf-8', errors='replace', timeout=180)
        self.assertIn('CLOSED', done.stderr, done.stderr[-2000:])
        errors = [line for line in done.stderr.splitlines() if line.startswith('QML-ERROR')]
        self.assertEqual(errors[:5], [], f'{len(errors)} QML errors at close')
