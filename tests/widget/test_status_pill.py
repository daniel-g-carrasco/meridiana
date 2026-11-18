"""A level's sign and count (R328, R335): the same geometry in the tree's rows and in the Checks' pills."""
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

    def pill(self, theme, level, text, **state):
        from meridiana.ui import status_pill
        from meridiana.ui.design import Text, text_font
        image = QImage(60, 24, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        status_pill.paint_pill(painter, QRectF(0, 0, 60, 24), level, text, text_font(Text.LABEL), theme.tokens, **state)
        painter.end()
        return image

    def test_a_pill_is_tinted_with_its_level_stronger_when_on_and_faded_at_nought(self):
        """R335, P3: a pill of its own, ground and line in the level's tone (more of it while its filter is on, the
        line most), radius 6 so the corner is not filled, the sign in its colour; a nought faded as a whole."""
        for mode in ("light", "dark"):
            theme = self.look(mode)
            window = QColor(theme.tokens["window"])
            for level in ("fail", "warn", "info", "ok"):
                rest, on = self.pill(theme, level, "12"), self.pill(theme, level, "12", on=True)
                self.assertEqual(rest.pixelColor(0, 0).alpha(), 0, (mode, level))        # the corner is round
                ground_rest, ground_on = rest.pixelColor(30, 4), on.pixelColor(30, 4)
                self.assertNotEqual(ground_rest, window, (mode, level))                   # tinted
                self.assertNotEqual(ground_rest, ground_on, (mode, level))
                self.assertGreater(on.pixelColor(30, 0).alpha(), 0)                       # the line, on its top edge
                line_rest, line_on = rest.pixelColor(30, 0), on.pixelColor(30, 0)
                self.assertLess(sum(line_on.getRgb()[:3]) if mode == "light" else -sum(line_on.getRgb()[:3]),
                                sum(line_rest.getRgb()[:3]) if mode == "light" else -sum(line_rest.getRgb()[:3]),
                                (mode, level))                                            # the line is stronger when on
            faded = self.pill(theme, "warn", "0", off=True)
            self.assertLess(faded.pixelColor(30, 4).alpha(), 200)
            self.assertEqual(self.pill(theme, "warn", "0").pixelColor(30, 4).alpha(), 255)
            hover = self.pill(theme, "info", "3", hover=True)
            self.assertNotIn(hover.pixelColor(30, 4), (self.pill(theme, "info", "3").pixelColor(30, 4),
                                                       self.pill(theme, "info", "3", on=True).pixelColor(30, 4)))

    def test_checked_filter_keeps_a_visible_state_after_the_pointer_leaves(self):
        from meridiana.ui.checks_page import CountChip, CountRow
        theme = self.look("light")
        chip = CountChip("warn")
        self.addCleanup(_setup.dispose, chip)
        row = CountRow()
        self.addCleanup(_setup.dispose, row)
        chip.setText("12")
        row.add(chip)
        row.show()
        self.app.processEvents()

        def picture():
            chip.repaint()
            self.app.processEvents()
            return chip.grab().toImage()
        before = picture()
        chip.setChecked(True)
        after = picture()
        self.assertNotEqual(before, after)
        dpr = after.devicePixelRatio()
        middle = (round(10 * dpr), round(chip.height() / 2 * dpr))
        self.assertEqual(after.pixelColor(*middle), self.pill(theme, "warn", "12", on=True).pixelColor(
            round(10 * self.pill(theme, "warn", "12").devicePixelRatio()), 12))
