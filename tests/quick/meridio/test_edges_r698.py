"""R698: opaque overlapping contours must retain subpixel coverage after compositing.

Removing Character's sampled layer or restoring CurveRenderer makes the resting
oblique contour fail. GPU frames are read back without ever showing a window.
"""
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
import unittest

import _setup
from quick.aiuti.tempi import timed


def setUpModule():
    _setup.keep_global_state()


def render(path):
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QApplication

    from meridiana.gui.backend.assistant import QML
    from quick.meridio.edge_render import EdgeScene, edge_counts

    app = QApplication(['meridio-edges'])
    source = 'import Meridiana.Assistant\n' + (QML / 'Character.qml').read_text(encoding='utf-8')
    cases = []
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        (folder / 'ProbeCharacter.qml').write_text(source, encoding='utf-8')
        for dpr in (float(os.environ.get('QT_SCALE_FACTOR', '1')),):
            for style in ('sticker',):   # R699: the sticker is Meridio's only look
                scene = EdgeScene(folder, 'dark', style, dpr)
                try:
                    scene.root.setProperty('color', QColor('transparent'))
                    for pose, yaw, pitch in [('still', 0, 0), ('turned', 28, -18)]:
                        scene.guy.turn(yaw, pitch)
                        image = scene.grab()
                        counts = edge_counts(image)
                        cases.append(dict(dpr=dpr, style=style, pose=pose, **counts))
                    # The floating character is 46 logical pixels. Include pose publication,
                    # scene sync, GPU completion and readback in the frame budget.
                    scene.guy.setWidth(46)
                    scene.guy.setHeight(46)
                    times = []
                    for i in range(45):
                        start = time.perf_counter()
                        scene.guy.turn(10 + i * .3, -8 + i * .2)
                        scene.grab()
                        if i >= 5:
                            times.append((time.perf_counter() - start) * 1000)
                    cases[-1]['frame_median_ms'] = statistics.median(times)
                    cases[-1]['frame_p95_ms'] = sorted(times)[37]
                    cases[-1]['frame_worst_ms'] = max(times)
                    cases[-1]['api'] = str(scene.window.rendererInterface().graphicsApi())
                    app.processEvents()
                finally:
                    scene.close()
    path.write_text(json.dumps(cases, indent=2), encoding='utf-8')


class EdgesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = []
        with tempfile.TemporaryDirectory() as folder:
            for scale in ('1', '1.25', '2', '2.5'):
                path = Path(folder) / f'edges-{scale}.json'
                env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='rhi',
                           QSG_RENDER_LOOP='basic', QT_SCALE_FACTOR=scale)
                result = subprocess.run([sys.executable, '-m', 'quick.meridio.test_edges_r698', '--render', str(path)],
                                        env=env, capture_output=True, text=True, timeout=120)
                if result.returncode and 'No offscreen RHI available' in result.stderr:
                    # a machine without an OpenGL context for an offscreen RHI (the CI's runner: «QRhiGles2: Failed
                    # to create temporary context»): the edges are drawn by the RHI, there is nothing to measure
                    raise unittest.SkipTest('no offscreen RHI on this machine')
                if result.returncode:
                    raise AssertionError(result.stdout + result.stderr)
                if result.stderr:
                    raise AssertionError(result.stderr)
                cls.cases.extend(json.loads(path.read_text(encoding='utf-8')))

    def test_oblique_contours_keep_partial_pixel_coverage(self):
        for case in self.cases:
            with self.subTest(dpr=case['dpr'], style=case['style'], pose=case['pose']):
                self.assertGreater(case['soft'] + case['hard'], 100, case)
                self.assertLessEqual(case['hard'] / (case['soft'] + case['hard']), .05, case)

    @timed('a frame within 16.7 ms (60 Hz)')
    def test_moving_avatar_fits_one_60_hz_frame(self):
        # No numeric frame budget existed in quick/meridio (R619 checks frame
        # shutdown and R647 only prints times). Add a 60 Hz p95 budget, 16.67 ms.
        for case in self.cases:
            if 'frame_p95_ms' in case:
                with self.subTest(dpr=case['dpr'], style=case['style']):
                    self.assertNotIn('Software', case['api'])
                    self.assertLess(case['frame_p95_ms'], 1000 / 60, case)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--render':
        render(Path(sys.argv[2]))
    else:
        unittest.main()
