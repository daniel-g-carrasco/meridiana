"""Shared quiet status pills use the same geometry in delegates and filter buttons."""
import unittest

import _setup
from PySide6.QtCore import QPoint, QRectF, Qt
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
        for level in ("fail", "warn", "info", "ok"):
            for text in ("0", "1", "12", "999"):
                size = status_pill.size_hint(text, font, 20)
                parts = status_pill.layout(QRectF(0, 0, size.width(), 20), level, text, font)
                self.assertEqual(parts.symbol_box.left(), 6)
                self.assertAlmostEqual(parts.number.boundingRect().right(), size.width() - 10)
                self.assertEqual(parts.symbol_box.width(), 13)
                self.assertAlmostEqual(parts.symbol.boundingRect().center().x(), parts.symbol_box.center().x())
                self.assertAlmostEqual(parts.symbol.boundingRect().center().y(), 10)
                self.assertAlmostEqual(parts.number.boundingRect().center().y(), 10)
                self.assertGreaterEqual(parts.number.boundingRect().left() - parts.symbol_box.right(), 4)

    def test_pills_use_soft_status_backgrounds_with_readable_ink_and_a_quieter_zero(self):
        from meridiana.ui import status_pill
        for mode in ("light", "dark"):
            theme = self.look(mode)
            palette = self.app.palette()
            for level in ("fail", "warn", "info", "ok"):
                ground, ink, line = status_pill.colours(level, palette)
                zero_ground, zero_ink, _ = status_pill.colours(level, palette, zero=True)
                text = QColor(theme.tokens["text"])
                self.assertEqual(ink, text)
                self.assertGreater(abs(ground.lightness() - ink.lightness()), 80)
                self.assertNotEqual(ground, line)
                self.assertNotEqual(ground, zero_ground)
                self.assertLess(abs(zero_ink.lightness() - zero_ground.lightness()),
                                abs(ink.lightness() - ground.lightness()))

    def test_checked_filter_keeps_a_visible_state_after_the_pointer_leaves(self):
        from meridiana.ui.checks_page import CountChip
        self.look("light")
        chip = CountChip("warn")
        self.addCleanup(_setup.dispose, chip)
        chip.setText("12")
        chip.resize(chip.sizeHint())
        def picture():
            image = QImage(chip.size(), QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            chip.render(painter, QPoint())
            painter.end()
            return image
        before = picture()
        chip.setChecked(True)
        self.assertNotEqual(before, picture())

    def test_transparent_button_palettes_still_choose_the_real_light_surface(self):
        from PySide6.QtGui import QPalette
        from meridiana.ui import status_pill
        self.look("light")
        palette = QPalette(self.app.palette())
        for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Base):
            palette.setColor(role, QColor(0, 0, 0, 0))
        for alpha in (0, 255):
            palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, alpha))
            ground, ink, _ = status_pill.colours("info", palette)
            self.assertGreater(ground.lightness() - ink.lightness(), 100)
