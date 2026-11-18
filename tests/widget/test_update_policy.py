"""Update policy without network, installers or user configuration."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import _setup
from meridiana import updates

setUpModule = _setup.keep_global_state


class UpdatePolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from PySide6.QtCore import QObject
        from meridiana.ui.update_controller import UpdateController
        self.win = QObject()
        self.win.cfg = SimpleNamespace(pending_update={}, check_updates=True, auto_install_updates=False,
                                       last_update_check="")
        self.win.tell = Mock()
        self.win._save_config = Mock()
        self.win.show_update = Mock()
        self.win.session = SimpleNamespace(dirty=Mock(return_value=False))
        self.win.update_job = None
        self.win.pool = Mock()
        self.controller = UpdateController(self.win)
        self.release = updates.Release("99.0", "https://example.org/release", "")

    def test_notification_survives_restart_without_reusing_an_installer(self):
        self.controller.answer(self.release, "", False)
        self.assertEqual(self.win.cfg.pending_update, {"version": "99.0", "url": self.release.url})
        self.win.tell.reset_mock()
        self.controller.startup()
        self.assertIn("99.0", self.win.tell.call_args[0][0])
        self.win.show_update.assert_not_called()

    def test_automatic_install_requires_opt_in_and_clean_project(self):
        with patch("meridiana.ui.update_controller.UpdateDialog") as dialog, \
                patch.object(updates, "distribution_channel", return_value="installed"), \
                patch.object(updates, "installer_of", return_value=object()):
            self.controller.answer(self.release, "", False)
            dialog.assert_not_called()
            self.win.cfg.auto_install_updates = True
            self.win.session.dirty.return_value = True
            self.controller.answer(self.release, "", False)
            dialog.assert_not_called()
            self.win.session.dirty.return_value = False
            with patch("meridiana.ui.update_controller.QTimer.singleShot") as timer:
                self.controller.answer(self.release, "", False)
            dialog.assert_called_once()
            timer.assert_called_once()
            guard = dialog.call_args.kwargs["before_install"]
            self.win.session.dirty.return_value = True
            self.assertFalse(guard())
            self.win.session.dirty.return_value = False
            self.win.cfg.auto_install_updates = False
            self.assertFalse(guard())
            self.win.cfg.auto_install_updates = True
            self.assertTrue(guard())

    def test_flatpak_never_uses_a_github_release_as_installed_update(self):
        with patch.object(updates, "distribution_channel", return_value="flatpak"):
            self.controller.check(True)
        self.win.cfg.pending_update = {"version": "99.0"}
        with patch.object(updates, "distribution_channel", return_value="flatpak"):
            self.controller.startup()
        self.assertNotIn("99.0", self.win.tell.call_args[0][0])
        self.win.pool.start.assert_not_called()
        self.assertIn("Flatpak", self.win.tell.call_args[0][0])

    def test_new_version_clears_the_notification(self):
        self.win.cfg.pending_update = {"version": "99.0"}
        self.controller.answer(updates.Release("0.0", "", ""), "", True)
        self.assertEqual(self.win.cfg.pending_update, {})

    def test_bad_persistent_data_is_ignored(self):
        for data in (None, [], {"version": "<script>"}, {"version": 12}):
            self.assertEqual(updates.remembered_version(data), "")

    def test_manual_check_reuses_a_running_automatic_dialog(self):
        self.controller.dialog = Mock()
        self.controller.check(True)
        self.win.pool.start.assert_not_called()
        self.controller.dialog.raise_.assert_called_once()
    def test_privacy_page_fits_narrow_settings_without_horizontal_scrolling(self):
        from PySide6.QtWidgets import QCheckBox, QScrollArea
        from meridiana.config import Config
        from meridiana.ui.preferences import PrivacyPage
        _setup.meridiana_look()
        for width in (360, 600):
            with self.subTest(width=width):
                area = QScrollArea()
                area.setWidgetResizable(True)
                page = PrivacyPage(Config())
                area.setWidget(page)
                area.resize(width, 760)
                area.show()
                self.app.processEvents()
                self.assertEqual(area.horizontalScrollBar().maximum(), 0)
                for control in page.findChildren(QCheckBox):
                    self.assertLessEqual(control.sizeHint().width(), control.width())
                area.close()
                area.deleteLater()
