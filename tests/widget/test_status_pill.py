"""A level's sign and count (R328): the same geometry in the tree's rows and on the Checks' track, no container."""
import unittest

import _setup
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter

setUpModule = _setup.keep_global_state


class StatusPills(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def look(self, mode):
        """Own the theme lifetime: another module may have disposed the cached shared fixture."""
        from meridiana import config
        from meridiana.ui.theme import Theme
        theme = Theme(config.Config(theme=mode, background="none"), app=self.app)
        self.addCleanup(theme.deleteLater)
        return theme

    def test_shared_layout_keeps_compact_margins_and_centres_actual_symbol_and_number_paths(self):
        from meridiana.ui import status_pill
        from meridiana.ui.design import Text, text_font
        font = text_font(Text.LABEL)
        for text in ("0", "1", "12", "999"):
            size = status_pill.size_hint(text, font, 20)
            parts = status_pill.layout(QRectF(0, 0, size.width(), 20), text, font)
            self.assertEqual(parts.symbol_box.left(), 6)
            self.assertAlmostEqual(parts.number.boundingRect().right(), size.width() - 8)
            self.assertEqual(parts.symbol_box.width(), 12)
            self.assertAlmostEqual(parts.symbol_box.center().y(), 10)
            self.assertAlmostEqual(parts.number.boundingRect().center().y(), 10)
            self.assertGreaterEqual(parts.number.boundingRect().left() - parts.symbol_box.right(), 4)

    def picture(self, level, text, ink, off=False):
        from meridiana.ui import status_pill
        from meridiana.ui.design import Text, text_font
        image = QImage(60, 20, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        status_pill.paint(painter, QRectF(0, 0, 60, 20), level, text, text_font(Text.LABEL), ink, off)
        painter.end()
        return image

    def test_no_container_the_sign_in_its_colour_and_a_zero_grey(self):
        """R328, P5: nothing drawn round them, in both themes; the number in the ink given; the sign's hue is the
        level's, and a count of nought has it grey."""
        for mode in ("light", "dark"):
            theme = self.look(mode)
            ink = QColor(theme.tokens["text"])
            for level, red_more in (("fail", True), ("ok", False)):
                image = self.picture(level, "12", ink)
                self.assertEqual(image.pixelColor(0, 0).alpha(), 0)          # no ground, no line
                self.assertEqual(image.pixelColor(30, 10).alpha(), 0)        # between the sign and the number
                sign = image.pixelColor(8, 10)
                self.assertEqual(sign.red() > sign.green(), red_more, level)
                grey = self.picture(level, "0", QColor(theme.tokens["muted"]), off=True).pixelColor(8, 10)
                self.assertLess(abs(grey.red() - grey.green()), 12, level)

    def test_checked_filter_keeps_a_visible_state_after_the_pointer_leaves(self):
        from meridiana.ui.checks_page import CountChip
        self.look("light")
        chip = CountChip("warn")
        self.addCleanup(_setup.dispose, chip)
        from meridiana.ui.segments import Segments, tokens
        track = Segments(exclusive=False)
        self.addCleanup(_setup.dispose, track)
        chip.setText("12")
        track.add("12", "warn", segment=chip)
        track.show()
        self.app.processEvents()

        def picture():
            track.repaint()
            self.app.processEvents()
            return track.grab().toImage()
        before = picture()
        chip.setChecked(True)
        self.assertTrue(_setup.wait_until(self.app, lambda: track.fading is None, 1))
        after = picture()
        self.assertNotEqual(before, after)
        dpr, r = after.devicePixelRatio(), chip.geometry()
        self.assertEqual(after.pixelColor(round((r.left() + 3) * dpr), round(r.center().y() * dpr)),
                         QColor(tokens()["panel"]))

