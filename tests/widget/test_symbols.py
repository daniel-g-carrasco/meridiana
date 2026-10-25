"""The window's symbols (ui/symbols.py, R138): Spola's check, forbidden, warning and error and the cross, the stop
and the info in the same geometry, drawn as Spola draws its status on Windows (the ground in a gradient, the sign
solid and light on it, dark on the warning's yellow); the marks of the checks made of them. PySide6 and a display
(offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Symbols(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def picture(self, name: str, side: int = 64, dark: bool = False):
        from PySide6.QtCore import QRectF, Qt
        from PySide6.QtGui import QImage, QPainter

        from meridiana.ui import symbols
        image = QImage(side, side, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        p = QPainter(image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        symbols.paint(p, QRectF(0, 0, side, side), name, dark=dark)
        p.end()
        return image

    def colour(self, image, x: float, y: float):
        from PySide6.QtGui import QColor
        return QColor.fromRgba(image.pixel(int(x * image.width() / 16), int(y * image.height() / 16)))

    def test_the_seven_symbols_say_what_daniel_listed(self):
        from meridiana.ui import symbols
        self.assertEqual(set(symbols.NAMES), {"check", "cross", "forbidden", "stop", "info", "warning", "error"})
        self.assertEqual(symbols.LEVEL, {"fail": "stop", "warn": "warning", "info": "info", "ok": "check"})
        for name in symbols.NAMES:
            for dark in (False, True):
                self.assertTrue(symbols.renderer(name, dark).isValid(), (name, dark))
                self.assertFalse(symbols.icon(name).isNull())
        with self.assertRaises(KeyError):
            symbols.icon("tick")

    def test_the_sign_is_solid_and_light_on_a_ground_in_a_gradient(self):
        from meridiana import theme_colors
        from meridiana.ui import symbols
        stop = self.picture("stop")
        bar, above, below = self.colour(stop, 8, 8), self.colour(stop, 8, 3), self.colour(stop, 8, 13)
        self.assertGreater(bar.lightness(), 220)                           # the bar, light: not a hole
        self.assertEqual(bar.alpha(), 255)
        self.assertGreater(above.lightness(), below.lightness())          # lighter at the top
        red = theme_colors.STATUS["critical"]
        self.assertLess(abs(below.red() - int(red[1:3], 16)), 24)
        warning = self.picture("warning")                                  # the error's «!», light like every sign
        self.assertGreater(self.colour(warning, 8, 7.5).lightness(), 220)
        error = self.picture("error")
        self.assertLess(abs(self.colour(warning, 8, 7.5).lightness() - self.colour(error, 8, 6).lightness()), 8)
        self.assertLess(self.colour(warning, 8, 13.4).lightness(), 160)     # on the ochre: a light sign reads there
        ring = self.picture("forbidden")                                   # red, as the prohibition sign
        bar_of_ring = self.colour(ring, 8, 8)
        self.assertGreater(bar_of_ring.red(), bar_of_ring.green() + 60)     # its bar is the ring's red, not white
        self.assertEqual(self.colour(ring, 10.8, 5.2).alpha(), 0)          # the ring is a ring: «\» leaves this free
        self.assertEqual(self.colour(ring, 5.2, 10.8).alpha(), 0)
        self.assertGreater(self.colour(ring, 3.6, 3.6).alpha(), 250)       # the bar runs into the ring: no gap
        seam = [self.colour(ring, 3.2 + k * 0.1, 3.2 + k * 0.1) for k in range(10)]
        self.assertLess(max(c.red() for c in seam) - min(c.red() for c in seam), 12)    # one gradient, no seam
        self.assertNotEqual(symbols.colour("info", dark=True), symbols.colour("info"))

    def test_a_mark_of_the_checks_is_its_symbol(self):
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QColor, QImage, QPainter

        from meridiana.ui import marks
        image = QImage(64, 64, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        p = QPainter(image)
        marks.paint(p, QPointF(32, 32), "fail", 1, 60)
        p.end()
        centre, top = QColor.fromRgba(image.pixel(32, 32)), QColor.fromRgba(image.pixel(32, 12))
        self.assertGreater(centre.lightness(), 220)                         # the stop's bar
        self.assertGreater(top.red(), top.green() + 60)                     # on its red disc

    def test_the_dialogs_buttons_and_the_messages_have_the_symbols_on_every_system(self):
        """R154 (Daniel, 25/10/2026: «non hai applicato i simboli nuovi dappertutto»: on Linux OK and Cancel had the
        desktop theme's arrow and cross): the window's style answers the standard icons with the symbols."""
        from PySide6.QtGui import QImage
        from PySide6.QtWidgets import QStyle

        from meridiana.ui import symbols
        from meridiana.ui.scrollbars import ScrollStyle
        style = ScrollStyle()
        self.addCleanup(style.deleteLater)
        SP = QStyle.StandardPixmap

        def pixels(icon) -> QImage:
            return icon.pixmap(32, 32).toImage().convertToFormat(QImage.Format.Format_ARGB32)

        for standard, name in ((SP.SP_DialogOkButton, "check"), (SP.SP_DialogCancelButton, "cross"),
                               (SP.SP_MessageBoxWarning, "warning"), (SP.SP_MessageBoxCritical, "error"),
                               (SP.SP_MessageBoxInformation, "info")):
            with self.subTest(name):
                self.assertEqual(pixels(style.standardIcon(standard)), pixels(symbols.icon(name)))
        self.assertTrue(style.standardIcon(SP.SP_DialogSaveButton).isNull())      # no symbol of its own: none
        self.assertEqual(style.styleHint(QStyle.StyleHint.SH_DialogButtonBox_ButtonsHaveIcons), 1)

    def test_in_a_line_of_text_the_symbol_is_a_picture_sharp_on_every_screen(self):
        """R154 continued: the notes, the checks of the strings and the keys' dialog had the characters; in rich
        text the symbol is its picture, written at 1, 2 and 3 times its size (Qt takes the one of the screen)."""
        import re
        from pathlib import Path

        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtGui import QColor, QImage, QPainter
        from PySide6.QtWidgets import QLabel

        from meridiana.ui import symbols
        tag = symbols.html("warning")
        src = re.search(r'src="([^"]+)"', tag).group(1)
        first = Path(src)
        self.assertTrue(first.exists())
        for k in (2, 3):
            self.assertTrue(first.with_name(f"{first.stem}@{k}x.png").exists(), k)
        self.assertEqual(QImage(str(first.with_name(f"{first.stem}@2x.png"))).width(), 2 * symbols.IN_TEXT)
        label = QLabel(tag + " Da controllare")
        self.addCleanup(label.deleteLater)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.resize(label.sizeHint())
        image = QImage(label.size(), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.white)
        p = QPainter(image)
        label.render(p, QPoint(0, 0))
        p.end()
        amber = [QColor.fromRgba(image.pixel(x, y)) for x in range(symbols.IN_TEXT + 2) for y in range(image.height())]
        self.assertTrue(any(c.red() > 150 and c.blue() < 90 and c.green() > 80 for c in amber))   # the triangle drawn


if __name__ == "__main__":
    unittest.main()
