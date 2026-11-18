"""The Settings come in from File as File comes in (Daniel, 30/10/2026: «avevo chiesto un'animazione semplice come
quella che compare quando premo su file ... compare per un istante breve una finestrella in sovraimpressione»): the
same entrance, not a crossfade of two pages, and read while File is still, so the click does not wait for them."""
import unittest

import _setup
from _fixtures import capannone


class SettingsEntrance(unittest.TestCase):
    def test_settings_are_read_ahead_and_enter_as_file(self):
        self.app = _setup.qt_or_skip()
        _setup.window(self, capannone())
        from meridiana.ui import motion
        motion.set_reduced(False)
        self.addCleanup(motion.set_reduced, False)
        win = self.win
        win.resize(1366, 760)
        win.show()
        _setup.turn_events(self.app, 300)
        page = win.file_page
        win.open_file_page("open")
        _setup.turn_events(self.app, 700)
        self.assertTrue(page._settings_read)                   # read once File had come in
        reads, entrances, crossfades = [], [], []
        real_populate, real_enter, real_crossfade = page.settings._populate, motion.enter, motion.crossfade
        page.settings._populate = lambda: (reads.append(1), real_populate())[1]
        motion.enter = lambda *a, **k: (entrances.append(a[0]), real_enter(*a, **k))[1]
        motion.crossfade = lambda *a, **k: (crossfades.append(a[0]), real_crossfade(*a, **k))[1]
        self.addCleanup(setattr, motion, "enter", real_enter)
        self.addCleanup(setattr, motion, "crossfade", real_crossfade)
        page.items["preferences"].click()
        _setup.turn_events(self.app, 400)
        self.assertIs(page.body.currentWidget(), page.sections["preferences"])
        self.assertEqual(reads, [])                            # nothing left to read at the click
        self.assertEqual(entrances, [page])                    # File's own entrance, over the page
        self.assertEqual(crossfades, [])
        self.assertFalse(page._settings_read)                  # used: the next visit reads them again
        # back to Open and to the Settings again: read once, on the way in
        page.show_section("open")
        _setup.turn_events(self.app, 300)
        page.show_section("preferences")
        _setup.turn_events(self.app, 300)
        self.assertEqual(len(reads), 1)
        # a new visit reads them again: the project, and its site in the maps' settings, may be another
        page.close_page()
        _setup.turn_events(self.app, 400)
        win.open_file_page("open")
        self.assertFalse(page._settings_read)

    def test_the_settings_pages_are_made_when_first_wanted_and_read_once(self):
        """They are 630 of the window's 2900 widgets and each costs 0.4 ms at every change of theme, shown or not."""
        self.app = _setup.qt_or_skip()
        _setup.window(self, capannone())
        from PySide6.QtWidgets import QWidget

        from meridiana.ui.preferences import Preferences
        win = self.win
        page = win.file_page
        self.assertIsNone(page._settings)                      # not made with the window
        self.assertEqual(page.sections["preferences"].findChildren(Preferences), [])
        self.assertLess(len(win.findChildren(QWidget)), 2600)
        from unittest import mock
        with mock.patch.object(Preferences, "_populate", autospec=True,
                               side_effect=Preferences._populate) as populated:
            settings = page.settings                           # made, and read as it is made
            self.assertEqual(populated.call_count, 1)
            self.assertIs(page.settings, settings)
            self.assertEqual(populated.call_count, 1)
        self.assertEqual(page.sections["preferences"].findChildren(Preferences), [settings])
        self.assertTrue(page._settings_read)
        win.open_file_page("preferences:privacy")              # straight to a page of them: made once, shown
        _setup.turn_events(self.app, 700)
        self.assertIs(page.settings, settings)
        self.assertEqual(settings.current_section(), "privacy")
        self.assertIs(page.body.currentWidget(), page.sections["preferences"])


if __name__ == "__main__":
    unittest.main()
