"""The window's symbols (ui/symbols.py, R138): Spola's check, forbidden, warning and error and the cross, the stop
and the info in the same geometry, flat (R330: the ground of one tone; R464: the sign cut out of it); the marks of
the checks made of them, in a disc of the plan's pills on the views (R464). PySide6 and a display
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

    def test_the_symbols_say_what_daniel_listed(self):
        from meridiana.ui import symbols
        self.assertEqual(set(symbols.NAMES), {"check", "cross", "forbidden", "stop", "info", "warning", "error",
                                              "trash", "back", "update"})
        self.assertEqual(symbols.LEVEL, {"fail": "stop", "warn": "warning", "info": "info", "ok": "check"})
        for name in symbols.NAMES:
            for dark in (False, True):
                self.assertTrue(symbols.renderer(name, dark).isValid(), (name, dark))
                self.assertFalse(symbols.icon(name).isNull())
        with self.assertRaises(KeyError):
            symbols.icon("tick")

    def test_the_warning_is_as_wide_as_the_disc(self):
        """R330 (Daniel, 02/11/2026): «in larghezza sia uguale al diametro del cerchio»."""
        from meridiana.ui import symbols
        disc, triangle = symbols._parse(symbols.DISC).boundingRect(), symbols._parse(symbols.TRIANGLE).boundingRect()
        self.assertAlmostEqual(triangle.width(), disc.width(), delta=0.05)
        self.assertAlmostEqual(triangle.center().x(), disc.center().x(), delta=0.01)
        self.assertLessEqual(triangle.bottom(), disc.bottom())
        self.assertGreaterEqual(triangle.top(), disc.top())

    def test_the_sign_is_cut_out_of_a_ground_of_one_tone(self):
        """R464 (Daniel 06/11/2026: «vai con i trasparenti»): the sign is a hole, what is under it shows through."""
        from PySide6.QtCore import QRectF, Qt
        from PySide6.QtGui import QPainter

        from meridiana import theme_colors
        from meridiana.ui import symbols
        stop = self.picture("stop")
        bar, above, below = self.colour(stop, 8, 8), self.colour(stop, 8, 3), self.colour(stop, 8, 13)
        self.assertEqual(bar.alpha(), 0)                                   # the bar: a hole
        self.assertEqual(above.name(), below.name())                      # one tone, top to bottom
        self.assertEqual(above.alpha(), 255)
        red = theme_colors.STATUS["critical"]
        self.assertLess(abs(below.red() - int(red[1:3], 16)), 24)
        warning = self.picture("warning")                                  # the error's «!», a hole like every sign
        self.assertEqual(self.colour(warning, 8, 7.5).alpha(), 0)
        self.assertEqual(self.colour(self.picture("error"), 8, 6).alpha(), 0)
        self.assertEqual(self.colour(self.picture("info"), 8, 9.5).alpha(), 0)
        self.assertEqual(self.colour(self.picture("check"), 6.9, 11.2).alpha(), 0)
        self.assertLess(self.colour(warning, 8, 13.4).lightness(), 160)     # the ochre around it
        self.assertEqual(self.colour(warning, 8, 13.4).alpha(), 255)
        # an off symbol (a level with nothing in it) is cut the same way, in the grey
        image = self.picture("stop")
        image.fill(Qt.GlobalColor.transparent)
        p = QPainter(image)
        symbols.paint(p, QRectF(0, 0, 64, 64), "stop", dark=False, off=True)
        p.end()
        self.assertEqual(self.colour(image, 8, 8).alpha(), 0)
        self.assertEqual(self.colour(image, 8, 3).name(), symbols.TONES["neutral"])
        ring = self.picture("forbidden")                                   # red, as the prohibition sign
        bar_of_ring = self.colour(ring, 8, 8)
        self.assertGreater(bar_of_ring.red(), bar_of_ring.green() + 60)     # its bar is the ring's red, not white
        self.assertEqual(self.colour(ring, 10.8, 5.2).alpha(), 0)          # the ring is a ring: «\» leaves this free
        self.assertEqual(self.colour(ring, 5.2, 10.8).alpha(), 0)
        self.assertGreater(self.colour(ring, 3.6, 3.6).alpha(), 250)       # the bar runs into the ring: no gap
        seam = [self.colour(ring, 3.2 + k * 0.1, 3.2 + k * 0.1) for k in range(10)]
        self.assertLess(max(c.red() for c in seam) - min(c.red() for c in seam), 12)    # one tone, no seam
        self.assertNotEqual(symbols.colour("info", dark=True), symbols.colour("info"))

    def test_discard_is_a_bin_on_the_red_and_cancel_an_arrow_back_on_the_grey(self):
        """R169 (Daniel, 26/10/2026: «il pulsante scarta vorrei che avesse un bel cestino. Mentre l'annulla un simbolo
        di tornare indietro»): the bin's lid and body light on the red, the gap between them the red; the arrow's
        head on the left, its shaft turning on the right, the middle of the turn the grey."""
        from PySide6.QtCore import QRectF

        from meridiana.ui import symbols
        trash = self.picture("trash")
        lid, body, gap = self.colour(trash, 8, 5.3), self.colour(trash, 8, 9.5), self.colour(trash, 8, 6.4)
        self.assertEqual(lid.alpha(), 0)                                      # R464: lid and body cut out
        self.assertEqual(body.alpha(), 0)
        self.assertGreater(gap.red(), gap.green() + 60)                       # the red between lid and body
        self.assertGreater(self.colour(trash, 4.5, 10).red(), self.colour(trash, 4.5, 10).green() + 60)  # narrows
        back = self.picture("back")
        self.assertEqual(self.colour(back, 4.6, 6.6).alpha(), 0)            # the head
        self.assertEqual(self.colour(back, 11.5, 9.1).alpha(), 0)           # the turn, on the right
        self.assertEqual(self.colour(back, 7, 11.6).alpha(), 0)             # the shaft back under the head
        inside = self.colour(back, 9.4, 9.1)
        self.assertLess(inside.lightness(), 160)                              # inside the turn: the grey
        self.assertLess(abs(inside.red() - inside.blue()), 20)
        # the sign alone (for a pill) follows the half circles, not two whole dots
        sign = symbols.sign("back", QRectF(0, 0, 16, 16))
        self.assertTrue(sign.contains(QRectF(11.4, 9.0, 0.2, 0.2).center()))
        self.assertFalse(sign.contains(QRectF(9.3, 9.0, 0.2, 0.2).center()))
        self.assertFalse(sign.contains(QRectF(6.0, 9.0, 0.2, 0.2).center()))   # the left of the turn stays open

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
        self.assertEqual(centre.alpha(), 0)                                 # the stop's bar, cut out (R464)
        self.assertGreater(top.red(), top.green() + 60)                     # on its red disc

    def test_on_the_views_a_mark_stands_in_a_disc_of_the_plans_pills(self):
        """R464 (Daniel 06/11/2026: «lo metti dentro un pallino con lo stile grafico delle pillole in pianta»): on the
        plan and the 3D view the symbol is in a disc of the pills' colour, 22 for 18, and its sign shows the pill."""
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QColor, QImage, QPainter

        from meridiana import theme_colors, view_colours
        from meridiana.ui import marks
        image = QImage(80, 80, QImage.Format.Format_ARGB32)
        image.fill(QColor("#3c8f3c"))                                          # a green roof or field under it
        p = QPainter(image)
        marks.paint(p, QPointF(40, 40), "warn", 1, 54, views=True)            # 54 for 18: a disc of 66
        p.end()
        pill = QColor(theme_colors.qt_hex(view_colours.PHOTO["label_bg"]))
        a = pill.alphaF()
        expected = QColor(round(pill.red() * a + 0x3c * (1 - a)), round(pill.green() * a + 0x8f * (1 - a)),
                          round(pill.blue() * a + 0x3c * (1 - a)))

        def near(c, e):
            return max(abs(c.red() - e.red()), abs(c.green() - e.green()), abs(c.blue() - e.blue())) <= 3

        def at(x, y):
            return QColor.fromRgba(image.pixel(x, y))
        self.assertTrue(near(at(40, 10), expected), at(40, 10).name())        # the disc above the triangle
        self.assertTrue(near(at(40, 38), expected), at(40, 38).name())        # the «!»: the pill shows through
        self.assertEqual(at(40, 76).name(), "#3c8f3c")                         # outside the disc: the roof
        ochre = at(40, 58)
        self.assertGreater(ochre.red(), ochre.blue() + 60)                    # the triangle in its tone

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

        for standard, name in ((SP.SP_DialogOkButton, "check"), (SP.SP_DialogCancelButton, "back"),
                               (SP.SP_DialogDiscardButton, "trash"), (SP.SP_DialogNoButton, "cross"),
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
