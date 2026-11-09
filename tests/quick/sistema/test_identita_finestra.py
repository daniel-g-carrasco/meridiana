"""The Quick window tells the desktop who it is (r23-unita): r22-flatpak saw it under Niri as «python3», without
Meridiana's icon, because quick/app.create_app set neither the desktop file's name (the Wayland app_id) nor the
application's name (the X11 window class). The Widgets window had both (app.py)."""

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

PROBE = """
from meridiana.quick import app
qt = app.create_app()
print(qt.desktopFileName())
print(qt.applicationName())
"""


class WindowIdentityTests(unittest.TestCase):
    def test_the_quick_app_has_the_desktop_file_name_and_the_class_of_meridiana(self):
        from meridiana import APP_ID, APP_NAME
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONPATH=os.pathsep.join([str(ROOT / 'src')]))
        out = subprocess.run([sys.executable, '-c', PROBE], capture_output=True, text=True, env=env, timeout=120,
                             cwd=str(ROOT))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        lines = out.stdout.strip().splitlines()[-2:]
        self.assertEqual(lines, [APP_ID, APP_NAME])

    def test_the_desktop_file_of_that_name_carries_the_icon(self):
        from meridiana import APP_ID
        desktop = list(ROOT.glob(f'**/{APP_ID}.desktop'))
        desktop = [p for p in desktop if '.venv' not in p.parts and 'build' not in p.parts]
        self.assertTrue(desktop, f'{APP_ID}.desktop: the compositor finds the icon through it')
        text = desktop[0].read_text(encoding='utf-8')
        self.assertIn(f'Icon={APP_ID}', text)


if __name__ == '__main__':
    unittest.main()
