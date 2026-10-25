"""The preferences and the editor of the keys alone (ui/preferences.py, ui/shortcuts_dialog.py): the dialog opens on
the page asked for, the privacy page starts with everything allowed; the editor says what is wrong with keys while
they are typed and takes keys away from the command that had them. What the window does with them (the map loader
and PVGIS stopped, the keys on its commands and in the settings file) is in finestra/test_window.py. PySide6 and a
display (offscreen will do)."""

import unittest

import _setup

from meridiana import config

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class PreferencesAlone(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.ui.theme import Theme
        self.cfg = config.Config(background="none")
        self.theme = Theme(self.cfg, app=self.app)          # as the window makes it, before its widgets
        self.addCleanup(self.theme.deleteLater)

    def dialog(self, page: str):
        from meridiana.ui.preferences import Preferences
        d = Preferences(self.cfg, {}, self.theme, None, page=page)
        self.addCleanup(_setup.dispose, d)
        return d

    def test_the_preferences_open_on_the_page_asked_for(self):
        d = self.dialog("navigation")
        self.assertIs(d.pages.currentWidget(), d.navigation)
        d = self.dialog("keyboard")
        self.assertIs(d.pages.currentWidget(), d.keys)
        d = self.dialog("a-page-of-tomorrow")               # unknown: the first page, no error
        self.assertIs(d.pages.currentWidget(), d.appearance)

    def test_the_privacy_page_starts_with_the_address_search_pvgis_and_the_map_allowed(self):
        d = self.dialog("privacy")
        self.assertIs(d.pages.currentWidget(), d.privacy)
        self.assertEqual(d.privacy.choice(), (True, True, True))


class KeysEditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_keys_typed_are_judged_and_a_key_taken_leaves_the_command_that_had_it(self):
        from meridiana import shortcuts
        from meridiana.ui.shortcuts_dialog import ShortcutsEditor
        editor = ShortcutsEditor(shortcuts.bindings({}))
        self.addCleanup(_setup.dispose, editor)
        self.assertIn("«Project»", editor.verdict("ortho", "Ctrl+B"))       # said while the keys are typed
        self.assertIn("AltGr", editor.verdict("ortho", "Ctrl+Alt+O"))
        self.assertEqual(editor.verdict("ortho", "Ctrl+K"), "")
        editor.assign("ortho", "Ctrl+B")                    # taken from the Project panel
        self.assertEqual(editor.bindings["ortho"], ["Ctrl+B"])
        self.assertEqual(editor.bindings["panel_project"], [])


if __name__ == "__main__":
    unittest.main()
