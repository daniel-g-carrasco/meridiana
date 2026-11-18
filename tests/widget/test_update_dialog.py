"""The dialog of a newer version (ui/update_dialog.py; task 18f): the release page for a build that cannot install
itself; for the installed build the installer downloaded in the pool, checked against its SHA-256 and the project's
signature, and Setup started silent, after the window has had its say about the project; a download that fails or
a project not saved says so and leaves the button ready again. No network: the files are file:// URLs, signed with
the tests' own key (_fixtures). PySide6 and a display (offscreen will do)."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup
from _fixtures import PAYLOAD, PUBLIC_KEY, SIGNED_V9
from _setup import wait_until

from meridiana import updates

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

NAME = "spola-setup-v9-windows-x64.exe"         # the name the test signatures give
RELEASE = updates.Release("9.0.0", "https://github.com/daniel-g-carrasco/meridiana/releases/tag/v9.0.0",
                          "## What is new\n\n- a **thing**")


@mock.patch.object(updates, "PUBLIC_KEY", PUBLIC_KEY)
class UpdateDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "setup.exe").write_bytes(PAYLOAD)
        (self.tmp / "setup.exe.minisig").write_text(SIGNED_V9)
        self.addCleanup(updates.release_held)          # the verified installer is kept open
        self.started: list = []

    def asset(self, **changes) -> updates.Asset:
        fields = {"name": NAME, "url": (self.tmp / "setup.exe").as_uri(), "size": len(PAYLOAD),
                  "sha256": hashlib.sha256(PAYLOAD).hexdigest(),
                  "signature_url": (self.tmp / "setup.exe.minisig").as_uri()}
        return updates.Asset(**{**fields, **changes})

    def dialog(self, installer=None, before=None):
        from meridiana.ui.update_dialog import UpdateDialog
        d = UpdateDialog(RELEASE, installer=installer, before_install=before, start=self.started.append)
        self.addCleanup(d.deleteLater)
        return d

    def test_a_build_that_cannot_install_itself_opens_the_release_page(self):
        d = self.dialog()
        self.assertIn("9.0.0", d.findChildren(type(d.status))[0].text())
        self.assertIn(RELEASE.url, d.page.text())
        with mock.patch("meridiana.ui.update_dialog.QDesktopServices.openUrl") as opened:
            d.action.click()
        self.assertEqual(opened.call_args[0][0].toString(), RELEASE.url)

    def test_the_installed_build_downloads_checks_and_starts_setup_silent(self):
        d = self.dialog(self.asset(), before=lambda: True)
        with mock.patch.object(updates, "per_user_install", return_value=True):
            d.action.click()
            self.assertTrue(wait_until(self.app, lambda: bool(self.started), 20), d.status.text())
        args = self.started[0]
        self.assertTrue(args[0].endswith(NAME))
        self.assertEqual(Path(args[0]).read_bytes(), PAYLOAD)
        self.assertEqual(args[1:], ["/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER"])

    def test_a_project_not_saved_keeps_setup_from_starting(self):
        d = self.dialog(self.asset(), before=lambda: False)
        d.action.click()
        self.assertTrue(wait_until(self.app, lambda: d.action.isEnabled(), 20))
        self.assertEqual(self.started, [])
        self.assertIn("Save", d.status.text())

    def test_downloaded_update_can_be_retried_after_saving_without_downloading_again(self):
        clean = False
        d = self.dialog(self.asset(), before=lambda: clean)
        d.action.click()
        self.assertTrue(wait_until(self.app, lambda: d.action.isEnabled(), 20))
        self.assertTrue(d.downloaded_path)
        clean = True
        with mock.patch("meridiana.ui.update_dialog.DownloadJob") as download:
            d.action.click()
        download.assert_not_called()
        self.assertEqual(len(self.started), 1)

    def test_revoked_then_restored_consent_allows_retry_of_verified_download(self):
        allowed = False
        d = self.dialog(self.asset(), before=lambda: allowed)
        d.action.click()
        self.assertTrue(wait_until(self.app, lambda: d.action.isEnabled(), 20))
        self.assertEqual(self.started, [])
        d.action.click()
        self.assertEqual(self.started, [])
        allowed = True
        with mock.patch("meridiana.ui.update_dialog.DownloadJob") as download:
            d.action.click()
        download.assert_not_called()
        self.assertEqual(len(self.started), 1)

    def test_verified_retry_starts_setup_only_once_even_with_reentrant_or_duplicate_callbacks(self):
        import threading
        from types import SimpleNamespace
        allowed = False
        d = self.dialog(self.asset(), before=lambda: allowed)
        d.job = SimpleNamespace(cancelled=threading.Event())
        # A completed verified download represented only by an inert path and memory callback.
        d.downloaded_path = "verified-test-placeholder.exe"
        calls = []

        def start(args):
            calls.append(args)
            d._download()
            d._downloaded(d.downloaded_path)
        d.start = start
        d._download()
        self.assertTrue(d.action.isEnabled())
        self.assertEqual(calls, [])
        allowed = True
        d.action.click()
        d.action.click()
        d._downloaded(d.downloaded_path)
        self.assertEqual(len(calls), 1)
        self.assertTrue(d.start_requested)
        self.assertFalse(d.action.isEnabled())

    def test_failed_setup_start_can_be_retried_without_a_permanent_latch(self):
        import threading
        from types import SimpleNamespace
        d = self.dialog(self.asset(), before=lambda: True)
        d.job = SimpleNamespace(cancelled=threading.Event())
        d.downloaded_path = "verified-test-placeholder.exe"
        d.start = mock.Mock(side_effect=OSError("test failure"))
        d._download()
        self.assertFalse(d.start_requested)
        self.assertTrue(d.action.isEnabled())
        d.start = self.started.append
        d.action.click()
        self.assertEqual(len(self.started), 1)
        self.assertTrue(d.start_requested)

    def test_an_installer_that_does_not_match_is_never_started(self):
        d = self.dialog(self.asset(sha256="0" * 64), before=lambda: True)
        d.action.click()
        self.assertTrue(wait_until(self.app, lambda: d.action.isEnabled(), 20))
        self.assertEqual(self.started, [])
        self.assertIn("does not match", d.status.text())

    def test_later_during_the_download_starts_nothing(self):
        d = self.dialog(self.asset(), before=lambda: True)
        d.action.click()
        d.reject()
        self.assertTrue(d.job.cancelled.is_set())
        from PySide6.QtCore import QThreadPool
        self.assertTrue(QThreadPool.globalInstance().waitForDone(20000))        # the job ended, its signal queued
        self.app.processEvents()
        self.assertEqual(self.started, [])


if __name__ == "__main__":
    unittest.main()
