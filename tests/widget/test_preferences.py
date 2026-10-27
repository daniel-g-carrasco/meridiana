"""The settings and the editor of the keys alone (ui/preferences.py, ui/shortcuts_dialog.py): the page opens on
the section asked for, the privacy section starts with everything allowed; the editor says what is wrong with keys
while they are typed and takes keys away from the command that had them. What the window does with them (the map
loader and PVGIS stopped, the keys on its commands and in the settings file) is in finestra/test_window.py. PySide6
and a display (offscreen will do)."""

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

    def settings(self, page: str):
        from meridiana.ui.preferences import Preferences
        d = Preferences(self.cfg, {}, self.theme, None, page=page)
        self.addCleanup(_setup.dispose, d)
        return d

    def test_the_settings_open_on_the_page_asked_for(self):
        d = self.settings("navigation")
        self.assertIs(d.pages.currentWidget(), d.navigation)
        d = self.settings("keyboard")
        self.assertIs(d.pages.currentWidget(), d.keys)
        d = self.settings("a-page-of-tomorrow")               # unknown: the first page, no error
        self.assertIs(d.pages.currentWidget(), d.appearance)

    def test_the_privacy_page_starts_with_the_address_search_pvgis_and_the_map_allowed(self):
        d = self.settings("privacy")
        self.assertIs(d.pages.currentWidget(), d.privacy)
        self.assertEqual(d.privacy.choice(), (True, True, True))

    def test_a_change_is_emitted_at_once_and_undo_restores_the_controls(self):
        d = self.settings("navigation")
        changes = []
        d.changed.connect(changes.append)
        d.navigation.orbit.setCurrentIndex(d.navigation.orbit.findData("arcball"))
        self.assertEqual(changes, ["navigation"])
        self.assertEqual(d.navigation.choice()[1], "arcball")
        d.undo_last()
        self.assertEqual(d.navigation.choice()[1], "turntable")
        self.assertIs(d.pages.currentWidget(), d.navigation)
        self.assertEqual(changes, ["navigation", "all"])
        self.assertFalse(d.undo.isEnabled())

    def test_defaults_are_confirmed_in_the_page_and_undo_restores_the_section(self):
        from PySide6.QtWidgets import QDialog
        d = self.settings("privacy")
        self.assertNotIsInstance(d, QDialog)
        d.privacy.tiles.setChecked(False)
        d.cfg.network_tiles = False                  # what the window applies on d.changed
        d.ask_reset()
        self.assertTrue(d.confirmation.isVisibleTo(d))
        self.assertFalse(d.privacy.tiles.isChecked())
        d.restore_defaults()
        self.assertTrue(d.privacy.tiles.isChecked())
        self.assertFalse(d.confirmation.isVisibleTo(d))
        d.undo_last()
        self.assertFalse(d.privacy.tiles.isChecked())
        self.assertIs(d.pages.currentWidget(), d.privacy)


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
