"""The render loop the Quick window asks for (06/11/2026).

Offscreen, Qt Quick draws with its software renderer: there the threaded loop crashed the program in Impianto after
about ten notches of zoom (access violation, Qt6Quick reading 0x8 from QQuickWindow::rendererInterface of a null
window, called by the software render node of a Shape on the render thread). The window asks for the basic loop on
the software renderer and keeps the threaded one on a graphics API.

    python -m unittest quick.test_render_loop
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

from meridiana.quick.app import render_loop

ROOT = Path(__file__).resolve().parents[2]


class RenderLoop(unittest.TestCase):
    def test_software_renderer_takes_the_basic_loop(self):
        self.assertEqual(render_loop('offscreen'), 'basic')
        self.assertEqual(render_loop('minimal'), 'basic')
        self.assertEqual(render_loop('windows', 'software'), 'basic')

    def test_a_screen_keeps_the_threaded_loop(self):
        self.assertEqual(render_loop('windows'), 'threaded')
        self.assertEqual(render_loop('wayland'), 'threaded')
        self.assertEqual(render_loop('xcb', ''), 'threaded')

    def test_create_app_offscreen_without_a_loop_said_chooses_basic(self):
        env = {k: v for k, v in os.environ.items() if k != 'QSG_RENDER_LOOP'}
        env.update(QT_QPA_PLATFORM='offscreen', PYTHONUTF8='1',
                   PYTHONPATH=os.pathsep.join((str(ROOT/'src'), str(ROOT/'tests'))))
        code = ('import os\nfrom meridiana.quick.app import create_app\ncreate_app()\n'
                'print("loop", os.environ.get("QSG_RENDER_LOOP"))\n')
        out = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, timeout=120,
                             cwd=ROOT)
        self.assertIn('loop basic', out.stdout, out.stderr[-800:])

    def test_a_loop_said_by_the_user_wins(self):
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QSG_RENDER_LOOP='threaded', PYTHONUTF8='1',
                   PYTHONPATH=os.pathsep.join((str(ROOT/'src'), str(ROOT/'tests'))))
        code = ('import os\nfrom meridiana.quick.app import create_app\ncreate_app()\n'
                'print("loop", os.environ.get("QSG_RENDER_LOOP"))\n')
        out = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, timeout=120,
                             cwd=ROOT)
        self.assertIn('loop threaded', out.stdout, out.stderr[-800:])


if __name__ == '__main__':
    unittest.main()
