"""The shared help row and File tile retain their application-specific roles."""
import unittest
from unittest import mock
import _setup
from meridiana import config
from meridiana.ui import file_page, help_box
from meridiana.ui.design import Button, Icon, Size
from meridiana.ui.theme import Theme
setUpModule = _setup.keep_global_state

class SharedControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_row_help_is_round_but_title_help_stays_small_and_both_route_to_the_box(self):
        small = help_box.HelpButton("site")
        row = help_box.RowHelpButton("site")
        self.addCleanup(_setup.dispose, small)
        self.addCleanup(_setup.dispose, row)
        self.assertEqual(small.width(), Button.HELP[0])
        self.assertEqual(row.width(), Size.CONTROL)
        self.assertEqual(row.height(), row.width())
        self.assertTrue(row.accessibleName())
        with mock.patch.object(help_box, "request") as request:
            row.click()
            request.assert_called_once_with("site", row)

    def test_file_tile_icon_has_a_fixed_column_and_refreshes_when_theme_changes(self):
        tile = file_page.Tile("folder-open", "Open", "An invented project", (), "Open", lambda: None)
        self.addCleanup(_setup.dispose, tile)
        icon = tile.findChild(file_page.TileIcon)
        self.assertIsNotNone(icon)
        self.assertEqual((icon.width(), icon.height()), (Icon.TILE, Icon.TILE))
        before = icon.pixmap().cacheKey()
        theme = Theme(config.Config(theme="dark"), app=self.app)
        self.app.processEvents()
        self.assertNotEqual(icon.pixmap().cacheKey(), before)
        self.assertFalse(icon.pixmap().isNull())
        self.assertIsNotNone(theme)

    def test_small_question_mark_centres_its_visible_ink_inside_the_circle(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtGui import QImage, QPainter
        _setup.meridiana_look("light")
        button = help_box.HelpButton("site")
        button.setStyleSheet("QToolButton {border: none; color: #000000; background: transparent; padding: 0;}")
        self.addCleanup(_setup.dispose, button)
        button.show()
        self.app.processEvents()
        for scale in (1, 2, 2.5):
            image = QImage(round(button.width() * scale), round(button.height() * scale),
                           QImage.Format.Format_ARGB32_Premultiplied)
            image.setDevicePixelRatio(scale)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            button.render(painter, QPoint())
            painter.end()
            points = [(x, y) for x in range(image.width()) for y in range(image.height())
                      if image.pixelColor(x, y).alpha() > 128 and image.pixelColor(x, y).lightness() < 170]
            self.assertTrue(points)
            xs, ys = zip(*points, strict=True)
            with self.subTest(scale=scale):
                self.assertAlmostEqual((min(xs) + max(xs) + 1) / (2 * scale), button.width() / 2,
                                       delta=0.5 / scale + 0.01)
                self.assertAlmostEqual((min(ys) + max(ys) + 1) / (2 * scale), button.height() / 2,
                                       delta=0.5 / scale + 0.01)

if __name__ == "__main__":
    unittest.main()
