"""r21-unita: a TileLoader dropped while its decoders read the cache neither stops nor crashes the process.

Before, each loader had its QThreadPool and each job a signals object connected to the loader: a loader left to
Python's collector destroyed its pool with the GIL held (~QThreadPool waits for its jobs, a job needs the GIL to
emit), so the window's thread stopped for ever (tests/quick/pianta stopped in test_map_offline, in the whole folder
only), or the job emitted to a loader half destroyed (an access violation). A probe that drops loaders while they
decode crashed in eight runs out of ten, and stopped once. Now the pool and the hub that hands the images back
belong to the process (plan_tiles._DecodeHub)."""

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

PROBE = textwrap.dedent('''
    import gc, sys, tempfile
    from pathlib import Path
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtWidgets import QApplication
    from meridiana import tiles
    from meridiana.quick.backend import plan_tiles
    app = QApplication([])
    cache = Path(sys.argv[1])
    source = tiles.Source('pcn', 'Ortho', 'wms', 'http://127.0.0.1:9/ogc', 'Ortofoto', rank=40, max_zoom=20,
                          layer='ortho')
    image = QImage(256, 256, QImage.Format.Format_RGB32)
    image.fill(QColor('#4f905c'))
    names = [('pcn', 18, 1000 + i, 2000) for i in range(48)]
    first = plan_tiles.TileLoader(cache, sources={'pcn': source})
    for t in names:
        path = first._path(*t)
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(path), 'PNG')
    first.close()
    got = []
    for n in range(int(sys.argv[2])):
        loader = plan_tiles.TileLoader(cache, sources={'pcn': source})
        loader.tileReady.connect(lambda *a: got.append(a[:4]))
        for t in names:
            loader.request(*t)
        for _ in range(n % 7):
            app.processEvents()
        del loader                  # never closed: left to the collector while it decodes
        gc.collect()
    kept = plan_tiles.TileLoader(cache, sources={'pcn': source})
    kept.tileReady.connect(lambda *a: got.append(a[:4]))
    kept.request(*names[0])
    while names[0] not in got:
        app.processEvents()
    kept.close()
    print('done', flush=True)
''')


class DroppedLoaders(unittest.TestCase):
    def test_loaders_dropped_while_they_decode_neither_stop_nor_crash_the_process(self):
        with tempfile.TemporaryDirectory() as folder:
            env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'QT_QPA_PLATFORM': 'offscreen'}
            try:
                run = subprocess.run([sys.executable, '-c', PROBE, folder, '600'], env=env, capture_output=True,
                                     text=True, timeout=180)
            except subprocess.TimeoutExpired:
                self.fail('the process stopped: a loader dropped while decoding')
        self.assertEqual(run.returncode, 0, run.stderr[-2000:])
        self.assertIn('done', run.stdout)
        self.assertNotIn('has been deleted', run.stderr)


if __name__ == '__main__':
    unittest.main()
