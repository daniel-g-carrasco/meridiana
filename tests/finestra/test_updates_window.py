"""The check for a newer version in the window (task 18f): Help > Check for updates asks in the pool and shows the
dialog of a newer release, or says the version is the latest, or why the check failed; by itself once a day only,
the date kept in the settings; the switch of Preferences > Privacy. No network: the release is a local file named
by MERIDIANA_DEV_RELEASE_API (updates.latest_release, never in a build). PySide6 and a display (offscreen will do)."""

import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import _setup
from _fixtures import capannone
from _setup import wait_until

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class UpdatesInTheWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def answer(self, version: str) -> str:
        path = Path(tempfile.mkdtemp()) / "release.json"
        path.write_text(json.dumps({"tag_name": f"v{version}", "html_url": "https://example.org/r", "body": "notes",
                                    "assets": []}), encoding="utf-8")
        return path.as_uri()

    def ask(self, win, url: str) -> None:
        self.answered = False
        with mock.patch.dict(os.environ, {"MERIDIANA_DEV_RELEASE_API": url}):     # read by the job, in the pool
            win.commands["check_updates"].trigger()
            self.assertTrue(wait_until(self.app, lambda: self.answered, 20))

    def test_help_check_for_updates_shows_a_newer_release_or_says_this_is_the_latest(self):
        _setup.window(self, capannone())
        win = self.win
        shown = []

        def show(release, **_k):
            shown.append(release)

        original = win._update_answer

        def answered(*a):
            original(*a)
            self.answered = True
        with mock.patch.object(win, "show_update", side_effect=show), \
                mock.patch.object(win, "_update_answer", side_effect=answered):
            self.ask(win, self.answer("99.0.0"))
            self.assertEqual([r.version for r in shown], ["99.0.0"])
            self.ask(win, self.answer("0.0.1"))
            self.assertEqual(len(shown), 1)
            self.assertIn("latest", win.statusBar().currentMessage())
            self.ask(win, (Path(tempfile.mkdtemp()) / "gone.json").as_uri())
            self.assertIn("failed", win.statusBar().currentMessage())

    def test_a_check_that_answers_after_the_window_is_destroyed_is_dropped(self):
        import threading

        from meridiana import updates
        _setup.window(self, capannone())
        win = self.win
        with mock.patch.object(win.pool, "start"):
            win.check_updates(manual=True)
        job = win.update_job
        _setup.dispose(win)
        errors = []
        with mock.patch("meridiana.ui.update_dialog.updates.latest_release",
                        side_effect=updates.UpdateError("offline")), \
                mock.patch("sys.excepthook", side_effect=lambda kind, value, tb:
                           errors.append(f"{kind.__name__}: {value}")):
            worker = threading.Thread(target=job.run)
            worker.start()
            worker.join(5)
            self.assertFalse(worker.is_alive())
            self.app.processEvents()
        self.assertEqual(errors, [])

    def test_by_itself_once_a_day_and_only_when_allowed(self):
        _setup.window(self, capannone())
        win = self.win
        win.cfg.check_updates, win.cfg.last_update_check = True, "2000-01-01"
        with mock.patch.object(win, "check_updates") as check, \
                mock.patch("meridiana.updates.clean_downloads") as cleaned:
            win._daily_update_check()
            win._daily_update_check()                       # the same day: once
            self.assertEqual(check.call_args_list, [mock.call(manual=False)])
            self.assertEqual(cleaned.call_count, 1)
            self.assertEqual(win.cfg.last_update_check, date.today().isoformat())
            win.cfg.check_updates, win.cfg.last_update_check = False, ""
            win._daily_update_check()                       # switched off
            self.assertEqual(check.call_count, 1)

    def test_the_switch_of_preferences_privacy(self):
        from PySide6.QtWidgets import QDialog
        _setup.window(self, capannone())
        win = self.win
        win.cfg.check_updates = True

        def untick(dialog):
            self.assertTrue(dialog.privacy.updates.isChecked())
            dialog.privacy.updates.setChecked(False)
            return QDialog.DialogCode.Accepted
        win._preferences("privacy", run=untick)
        self.assertFalse(win.cfg.check_updates)


if __name__ == "__main__":
    unittest.main()
