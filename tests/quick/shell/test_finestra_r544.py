"""R544: the title bar and the frame on Meridiana's ground, in light and dark (backend/window_frame.py).

Daniel (08/11/2026): «su Linux vorrei che come prima il colore del bordo della finestra e della barra del titolo
seguano i colori di sfondo di Meridiana [...] Non so se si può fare la stessa cosa con la barra del titolo di Windows».
On Wayland Qt draws the bar with the application palette (Window, WindowText; Disabled WindowText when inactive): the
palette follows the theme. On Windows 11 the colours go to DWM, read back here from a real window never shown."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

import _setup
from PySide6.QtGui import QColor, QGuiApplication, QPalette

from meridiana.quick.backend import window_frame
from meridiana.quick.backend.tokens import ThemeTokens


def setUpModule():
    _setup.keep_global_state()


class FramePalette(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_palette_takes_ground_and_text_of_both_themes_and_nothing_else(self):
        for theme in ('light', 'dark'):
            with self.subTest(theme=theme):
                colors = ThemeTokens({'theme': theme}).colors
                before = QPalette(QGuiApplication.palette())
                palette = window_frame.frame_palette(window_frame.frame_colours(colors), before)
                for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
                    self.assertEqual(palette.color(group, QPalette.Window), QColor(colors['window']))
                self.assertEqual(palette.color(QPalette.Active, QPalette.WindowText), QColor(colors['text']))
                self.assertEqual(palette.color(QPalette.Disabled, QPalette.WindowText), QColor(colors['muted']))
                self.assertEqual(palette.color(QPalette.Active, QPalette.Base), before.color(QPalette.Active, QPalette.Base))
                self.assertEqual(palette.color(QPalette.Active, QPalette.Button), before.color(QPalette.Active, QPalette.Button))

    def test_on_wayland_the_application_palette_follows_the_theme(self):
        original = QPalette(QGuiApplication.palette())
        real = window_frame.draws_own_frame
        window_frame.draws_own_frame = lambda: True
        try:
            theme = ThemeTokens({'theme': 'light'})
            keeper = window_frame.FrameTheme(theme)
            self.assertEqual(QGuiApplication.palette().color(QPalette.Window), QColor(theme.colors['window']))
            theme.configure({'theme': 'dark'})
            self.assertEqual(QGuiApplication.palette().color(QPalette.Window), QColor(theme.colors['window']))
            self.assertEqual(QGuiApplication.palette().color(QPalette.WindowText), QColor(theme.colors['text']))
            self.assertLess(QGuiApplication.palette().color(QPalette.Window).lightness(), 60)
            keeper.deleteLater()
        finally:
            window_frame.draws_own_frame = real
            QGuiApplication.setPalette(original)

    def test_elsewhere_the_palette_is_left_alone(self):
        original = QPalette(QGuiApplication.palette())
        real = window_frame.draws_own_frame
        window_frame.draws_own_frame = lambda: False
        try:
            keeper = window_frame.FrameTheme(ThemeTokens({'theme': 'dark'}))
            self.assertEqual(QGuiApplication.palette(), original)
            keeper.deleteLater()
        finally:
            window_frame.draws_own_frame = real


@unittest.skipUnless(sys.platform == 'win32', 'DWM is Windows')
class FrameColoursOnWindows(unittest.TestCase):
    """The bar, title and border colours accepted by DWM on a window of the real platform, made and never shown. DWM
    does not give these three back (DwmGetWindowAttribute refuses them): the colours on screen are in the captures of
    docs/quick/stato/r24-finestra.md."""

    def test_caption_text_and_border_are_the_theme_s(self):
        child = '\n'.join((
            "import sys",
            "from PySide6.QtGui import QColor, QGuiApplication, QWindow",
            "app = QGuiApplication(sys.argv)",
            "from meridiana.quick.backend import window_frame as f",
            "w = QWindow(); w.create()",
            "for ground, text in (('#151515', '#ededed'), ('#f1f1f1', '#1e1e1e')):",
            "    c = {'ground': QColor(ground), 'text': QColor(text), 'quiet': QColor(text)}",
            "    done = f.set_frame_colours(w, c)",
            "    print('ROW', done)"))
        root = Path(__file__).resolve().parents[3]
        env = dict(os.environ, QT_QPA_PLATFORM='windows', PYTHONPATH=str(root / 'src'))
        done = subprocess.run([sys.executable, '-c', child], env=env, capture_output=True, text=True, timeout=60)
        rows = [line for line in done.stdout.splitlines() if line.startswith('ROW')]
        self.assertEqual(len(rows), 2, done.stderr[-1500:])
        if sys.getwindowsversion().build < 22000:
            self.assertTrue(all(row.startswith('ROW False') for row in rows))      # Windows 10: refused, bar as R482
            return
        self.assertEqual(rows, ['ROW True', 'ROW True'])


if __name__ == '__main__':
    unittest.main()
