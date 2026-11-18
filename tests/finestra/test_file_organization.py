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
        self.assertFalse(page.items['export'].isVisible())
        page.items['preferences:navigation'].click()
        self.app.processEvents()
        self.assertIs(page.settings.pages.currentWidget(), page.settings.navigation)
        self.assertLessEqual(page.settings.width(), 860)
        page.items['settings_back'].click()
        self.app.processEvents()
        self.assertTrue(page.items['export'].isVisible())
        page.items['save'].click()
        self.assertIs(page.body.currentWidget(), page.sections['save'])
        self.assertTrue(page.isVisible())

    def test_r315_no_import_page_and_a_pvsyst_project_is_opened_from_open(self):
        """R315 (Daniel, 02/11/2026): the Import page is gone; a PVsyst project is one more way to open, with its
        Ctrl+I, and a quiet line in Open says where the other imports are."""
        from unittest import mock

        from PySide6.QtGui import QKeySequence
        from PySide6.QtWidgets import QLabel

        from meridiana.ui.file_page import Tile
        self.app = _setup.qt_or_skip()
        _setup.window(self, capannone())
        from meridiana.ui import motion
        motion.set_reduced(True)
        self.win.resize(1700, 1000)
        win, page = self.win, self.win.file_page
        self.assertNotIn('import', page.items)
        self.assertNotIn('import', page.sections)
        win.open_file_page('open')
        self.app.processEvents()
        tiles = page.sections['open'].findChildren(Tile)
        names = [t.findChild(QLabel, "ftile-name").text() for t in tiles]
        self.assertEqual(names, ["A project", "PVsyst project"])
        prj = tiles[1]
        self.assertEqual([c.text() for c in prj.findChildren(QLabel, "ftile-format")], [".PRJ"])
        self.assertEqual(tiles[0].y(), prj.y())                                # one row, as tall
        self.assertEqual(tiles[0].height(), prj.height())
        self.assertIn(QKeySequence("Ctrl+I"), win.commands["import_pvsyst"].shortcuts())    # the key stays
        line = page.elsewhere.text()
        for where in ("IFC", "Modelling", "Plant", "PVGIS", "Production", "Consumption"):
            self.assertIn(where, line)
        with mock.patch.object(win, "_import_pvsyst_project") as started:
            prj.button.click()
            self.app.processEvents()
        started.assert_called_once()
        self.assertFalse(page.isVisible())                                    # the page closes, then the file

    def test_the_open_bubble_goes_with_meridio_and_is_not_in_the_picture_of_the_entrance(self):
        """R347, R370: left there, it showed over the page for a moment, «quella finestrella», each time File opened."""
        from unittest import mock

        from meridiana.ui import motion
        self.app = _setup.qt_or_skip()
        _setup.window(self, capannone())
        win = self.win
        win.show()
        a = win.assistant
        a.show()
        if not a.opened:
            a.toggle()
        _setup.turn_events(self.app, 500)
        self.assertTrue(a.bubble.isVisible())
        seen = []
        real = motion.enter
        def spy(area, change, *rest, **more):
            seen.append((a.isVisible(), a.bubble.isVisible()))
            return real(area, change, *rest, **more)
        with mock.patch.object(motion, "enter", spy):
            win.open_file_page()
        self.assertEqual(seen, [(False, False)])
        win.file_page.close_page()
        self.assertTrue(_setup.wait_until(self.app, lambda: a.isVisible() and a.bubble.isVisible(), 5))
        self.assertTrue(a.opened)

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
        self.assertFalse(page.items['export'].isVisible())
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
        self.assertTrue(page.items['export'].isVisible())
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
