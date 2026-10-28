"""The status bar reports manual and automatic saves, and keeps a failure visible (R195)."""

import unittest
from unittest import mock

import _setup
from _fixtures import capannone

setUpModule = _setup.keep_global_state


class SaveStatus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.win = _setup.window(self, capannone())

    def test_ctrl_s_shows_activity_then_the_saved_time(self):
        original = self.win.session.save

        def watch(path):
            self.assertEqual(self.win.save_status.label.text(), "Saving…")
            self.assertTrue(self.win.save_status.spinner.isVisible())
            return original(path)

        with mock.patch.object(self.win.session, "save", side_effect=watch), \
                mock.patch("meridiana.ui.save_status.time.strftime", return_value="10:42"):
            self.assertTrue(self.win._save())
        self.assertEqual(self.win.save_status.label.text(), "Saved at 10:42")
        self.assertTrue(self.win.save_status.isVisibleTo(self.win))
        self.assertGreater(self.win.save_status.label.width(), 0)
        self.assertFalse(self.win.save_status.spinner.isVisible())

    def test_the_recovery_copy_says_it_was_saved_automatically(self):
        self.win._edited("project", "", {"name": "Autosaved"})
        with mock.patch("meridiana.ui.save_status.time.strftime", return_value="10:42"):
            self.win._autosave()
        self.assertEqual(self.win.save_status.label.text(), "Saved automatically at 10:42")

    def test_a_failed_automatic_save_keeps_the_existing_error(self):
        self.win._edited("project", "", {"name": "Not saved"})
        with mock.patch("meridiana.recovery.write", side_effect=PermissionError(13, "Permission denied")):
            self.win._autosave()
        self.assertIn("The recovery copy could not be written", self.win.statusBar().currentMessage())
        self.assertFalse(self.win.save_status.spinner.isVisible())


if __name__ == "__main__":
    unittest.main()
