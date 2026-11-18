"""R346/R378/R392: the File page keeps the Widgets navigation and form geometry."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from quick.parity.realwindow import native_app


def find_item(root, name):
    if root.objectName() == name:
        return root
    for child in root.childItems():
        found = find_item(child, name)
        if found is not None:
            return found
    return None


class FileFidelityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = native_app()

    def setUp(self):
        from meridiana.quick.backend.files_page import build_page
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.host = build_page('settings', folder=Path(self.temp.name), width=1600, height=960)
        self.addCleanup(self.host.close)
        self.window = self.host.window
        QTest.qWait(100)

    def item(self, name):
        item = find_item(self.window.contentItem(), name)
        self.assertIsNotNone(item, name)
        return item

    def click(self, name):
        item = self.item(name)
        point = item.mapToScene(item.boundingRect().center()).toPoint()
        QTest.mouseClick(self.window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
        QTest.qWait(220)

    def test_settings_keep_both_returns_and_escape(self):
        back = self.item('fileNav_back')
        self.assertTrue(back.isVisible())
        self.assertEqual('Esc', back.property('keyHint'))
        self.click('fileNav_settingsBack')
        self.assertEqual('open', self.host.files.section)
        self.assertFalse(self.host.warnings, self.host.warnings)

    def test_appearance_uses_widgets_column_and_comboboxes(self):
        self.assertEqual(760, self.item('settingsPage').width())
        theme = self.item('setting_theme')
        self.assertIsNotNone(theme.property('currentIndex'))
        self.assertEqual(28, theme.height())
        self.assertLess(self.item('settingsAppearancePreview').mapToScene(QPoint(0, 0)).y(), 450)
        self.assertTrue(self.item('settingsPreviewSelection').isVisible())
        self.assertTrue(self.item('settingsPreviewWarning').isVisible())
        self.click('setting_theme')
        QTest.keyClick(self.window, Qt.Key.Key_Down)
        QTest.keyClick(self.window, Qt.Key.Key_Return)
        QTest.qWait(60)
        self.assertEqual('dark', self.host.cfg.theme)
        self.click('settingsUndo')
        self.assertEqual('light', self.host.cfg.theme)
        self.assertFalse(self.host.warnings, self.host.warnings)


if __name__ == '__main__':
    unittest.main()
