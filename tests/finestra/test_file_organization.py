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
