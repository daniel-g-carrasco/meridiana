"""Qt's own words in the language of the window (ui/qt_translations.py, R26): «Annulla», not «Cancel»; a second
install replaces the first; English leaves Qt's words; the catalogue is in the PySide6 wheel. The language of
Meridiana's own strings is in nucleo/test_i18n.py. PySide6 and a display (offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class QtWords(unittest.TestCase):
    """Qt's own words in the language of the window (R26): «Annulla», not «Cancel»."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def tearDown(self):
        from meridiana.ui import qt_translations
        qt_translations.install(self.app, "en")             # the other tests read Qt's English

    def cancel(self) -> str:
        from PySide6.QtWidgets import QDialogButtonBox
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.addCleanup(box.deleteLater)
        return box.button(QDialogButtonBox.StandardButton.Cancel).text().replace("&", "")

    def test_in_italian_the_standard_cancel_button_says_annulla(self):
        from meridiana.ui import qt_translations
        self.assertTrue(qt_translations.install(self.app, "it"))
        self.assertEqual(self.cancel(), "Annulla")

    def test_in_english_qt_keeps_its_words_and_a_second_install_replaces_the_first(self):
        from meridiana.ui import qt_translations
        qt_translations.install(self.app, "it")
        qt_translations.install(self.app, "it")
        self.assertEqual(len(qt_translations._INSTALLED), 1)
        self.assertFalse(qt_translations.install(self.app, "en"))
        self.assertEqual(self.cancel(), "Cancel")

    def test_the_catalogue_is_in_the_pyside6_wheel(self):
        from pathlib import Path

        from meridiana.ui import qt_translations
        self.assertTrue(any((Path(f) / "qtbase_it.qm").exists() for f in qt_translations.folders()))


if __name__ == "__main__":
    unittest.main()
