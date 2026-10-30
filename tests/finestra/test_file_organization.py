"""Document commands and settings remain reachable in separate navigation levels."""
import unittest

import _setup
from _fixtures import capannone

setUpModule = _setup.keep_global_state


class Organization(unittest.TestCase):
    def test_settings_navigation_is_separate_and_returns_to_documents(self):
        self.app = _setup.qt_or_skip()
        _setup.window(self, capannone())
        from meridiana.ui import motion
        motion.set_reduced(True)
        self.win.resize(1700, 1000)
        self.win.open_file_page('open')
        page = self.win.file_page
        self.app.processEvents()
        self.assertFalse(page.items['preferences:navigation'].isVisible())
        page.items['preferences'].click()
        self.app.processEvents()
        self.assertTrue(page.items['preferences:navigation'].isVisible())
        self.assertFalse(page.items['import'].isVisible())
        page.items['preferences:navigation'].click()
        self.app.processEvents()
        self.assertIs(page.settings.pages.currentWidget(), page.settings.navigation)
        self.assertLessEqual(page.settings.width(), 860)
        page.items['settings_back'].click()
        self.app.processEvents()
        self.assertTrue(page.items['import'].isVisible())
        page.items['save'].click()
        self.assertIs(page.body.currentWidget(), page.sections['save'])
        self.assertTrue(page.isVisible())

    def test_settings_opened_from_elsewhere_go_back_to_the_project_with_a_button_and_a_key(self):
        """R289 (Daniel, 30/10/2026): the Settings opened without passing by File (Meridio's «Settings…», their
        key) show «Back to the project», and Alt+Left (the Back key) steps back: out of the page when it was
        opened there, else to the place shown before."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.app = _setup.qt_or_skip()
        _setup.window(self, capannone())
        from meridiana.ui import motion
        motion.set_reduced(True)
        self.win.resize(1700, 1000)
        win, page = self.win, self.win.file_page
        win._preferences("assistant")                          # as Meridio's menu opens them (WindowHost.preferences)
        self.app.processEvents()
        self.assertTrue(page.isVisible())
        self.assertIs(page.body.currentWidget(), page.sections['preferences'])
        self.assertTrue(page.items['back'].isVisible())        # «Back to the project», in the settings' list too
        self.assertTrue(page.items['settings_back'].isVisible())
        self.assertFalse(page.items['import'].isVisible())
        QTest.keyClick(page, Qt.Key.Key_Left, Qt.KeyboardModifier.AltModifier)
        self.app.processEvents()
        self.assertFalse(page.isVisible())                     # opened there: one step back is the project
        # from File then Settings, one step back is File; the button closes from anywhere
        win.open_file_page('open')
        self.app.processEvents()
        page.items['preferences'].click()
        self.app.processEvents()
        page.back()
        self.app.processEvents()
        self.assertTrue(page.isVisible())
        self.assertIs(page.body.currentWidget(), page.sections['open'])
        self.assertTrue(page.items['import'].isVisible())
        page.items['preferences'].click()
        self.app.processEvents()
        page.items['back'].click()
        self.app.processEvents()
        self.assertFalse(page.isVisible())
        # a new visit starts its own trail: Settings opened again, Alt+Left closes at once
        win._preferences()
        self.app.processEvents()
        page.back()
        self.app.processEvents()
        self.assertFalse(page.isVisible())
