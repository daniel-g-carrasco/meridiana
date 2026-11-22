"""Two small gesture scenarios finish in under a minute and emit usable raw streams."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[3]


class BenchmarkSmoke(unittest.TestCase):
    def test_resize_pixel_pass_can_capture_only_after_input_finishes(self):
        import _setup  # noqa: F401
        from types import SimpleNamespace
        import time
        from PySide6.QtGui import QImage
        from PySide6.QtQuick import QQuickWindow
        sys.path.insert(0, str(ROOT/'tools'))
        from gesture_bench_qt import execute
        from meridiana.gui.application import create_app
        app = create_app()
        window = QQuickWindow()
        window.resize(100, 100)
        sent, grabbed = [], []
        sender = SimpleNamespace(send=lambda _step: sent.append(time.perf_counter_ns()))
        observer = SimpleNamespace(state=lambda: {'zoom': 1}, rows=[], gui_ms=0.)
        def grab():
            grabbed.append(time.perf_counter_ns())
            return QImage(100, 100, QImage.Format_RGB32)
        try:
            execute(app, window, observer, sender, [{'at_ms': n, 'action': 'resize'} for n in (0, 40, 80)],
                    100, pixels=True, pixels_after_input=True, grab=grab)
            self.assertEqual(len(sent), 3)
            self.assertGreater(len(grabbed), 0)
            self.assertGreaterEqual(min(grabbed), sent[-1])
        finally:
            window.deleteLater()
            app.processEvents()

    def test_two_small_scenarios_have_real_input_frames_and_immutable_project(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'result.json'
            command = [sys.executable, str(ROOT/'tools/gesture_bench.py'), '--modules', '100',
                       '--views', 'plan', '--only', 'pinch', 'drag', '--backend', 'software', '--duration', '.12',
                       '--tail-ms', '120', '--out', str(output)]
            started = time.perf_counter()
            result = subprocess.run(command, env=dict(os.environ, QT_QPA_PLATFORM='offscreen',
                                    PYTHONUTF8='1'), capture_output=True, text=True, timeout=59)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertLess(time.perf_counter()-started, 60)
            report = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(len(report['cases']), 2)
            self.assertEqual({r['gesture'] for r in report['cases']}, {'pinch', 'drag'})
            for case in report['cases']:
                rows = [json.loads(line) for line in (output.parent/case['raw']).read_text(encoding='utf-8').splitlines()]
                self.assertTrue(all(r['version'] == 2 for r in rows))
                self.assertGreater(case['analysis']['events'], 5)
                self.assertGreater(case['analysis']['frames'], 0)
                self.assertTrue(case['analysis']['valid_motion'])
                self.assertEqual(case['modules'], 100)
                self.assertEqual(case['plan_modules'], 100)
                self.assertIn('gpu', case['analysis'])
                self.assertTrue(case['input_unchanged'])


if __name__ == '__main__':
    unittest.main()
