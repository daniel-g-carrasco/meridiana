"""Typing in the fields of the Settings (R329, Daniel 02/11/2026: «digitando in questi campi la digitazione va a
rallentatore»): every key saved the settings and drew the Report phase's panel again, 40-60 ms a key on a small project
in that phase. A key now only keeps the text; what is heavy waits for a pause or for leaving the field, and closing at
once loses nothing. PySide6 and a display (offscreen will do)."""

import json
import time
import unittest
from statistics import median
from unittest import mock

import _setup
from _fixtures import capannone

from meridiana import config

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

KEY_MS = 20                     # a key in a field, offscreen: 40-60 ms before R329, 1-3 ms after, wide for a slow runner
KEYS = 20


class Typing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone(), config.Config(background="none", theme="light"), size=(1400, 900))
        self.win.show_phase("report")
        self.app.processEvents()
        self.win._preferences("report")
        self.app.processEvents()
        self.settings = self.win.file_page.settings
        self.settings.report._add()
        self.app.processEvents()

    def keys(self, edit, count: int = KEYS) -> list[float]:
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        edit.setFocus()
        times = []
        for _n in range(count):
            start = time.perf_counter()
            QTest.keyClick(edit, Qt.Key.Key_A)
            times.append((time.perf_counter() - start) * 1000)
        return times

    def saved(self) -> dict:
        return json.loads(self.paths.config_file.read_text(encoding="utf-8"))

    def test_a_key_in_the_profile_costs_little_and_neither_saves_nor_draws_the_panel(self):
        win = self.win
        with mock.patch.object(win, "_save_config", wraps=win._save_config) as save, \
                mock.patch.object(win, "_show_inspector", wraps=win._show_inspector) as panel:
            times = self.keys(self.settings.report.fields["signer"])
            self.assertEqual((save.call_count, panel.call_count), (0, 0))
        self.assertLess(median(times), KEY_MS, times)

    def test_the_text_is_kept_at_once_and_saved_after_a_pause(self):
        page = self.settings.report
        self.keys(page.fields["signer"], 3)
        self.assertEqual(page.profiles[page.current]["signer"], "aaa")   # in memory, key by key
        self.assertTrue(_setup.wait_until(self.app, lambda: self.win.cfg.report_profiles[0]["signer"] == "aaa"))
        self.assertEqual(self.saved()["report_profiles"][0]["signer"], "aaa")

    def test_a_burst_of_keys_is_one_step_of_undo(self):
        settings = self.settings
        before = len(settings.history)
        self.keys(settings.report.fields["signer"], 5)
        settings.flush_typing()
        self.assertEqual(len(settings.history), before + 1)
        settings.undo_last()
        self.assertEqual(self.win.cfg.report_profiles[0]["signer"], "")

    def test_leaving_the_field_saves_at_once(self):
        field = self.settings.report.fields["signer"]
        self.keys(field, 2)
        field.editingFinished.emit()
        self.assertEqual(self.win.cfg.report_profiles[0]["signer"], "aa")
        self.assertEqual(self.saved()["report_profiles"][0]["signer"], "aa")

    def test_closing_the_file_page_at_once_keeps_the_text(self):
        self.keys(self.settings.report.fields["signer"], 2)
        self.win.file_page.hide()
        self.assertEqual(self.win.cfg.report_profiles[0]["signer"], "aa")

    def test_closing_the_window_at_once_saves_the_text(self):
        self.keys(self.settings.report.fields["firm"], 4)
        self.win.close()
        self.assertEqual(self.saved()["report_profiles"][0]["firm"], "aaaa")

    def test_undo_and_restore_do_not_lose_what_was_just_typed(self):
        settings = self.settings
        self.keys(settings.report.fields["signer"], 2)
        settings.undo_last()                                              # what was typed was the last change
        self.assertEqual(self.win.cfg.report_profiles[0]["signer"], "")
        self.assertEqual(settings.report.profiles[0]["signer"], "")

    def test_the_other_fields_of_the_settings_wait_too(self):
        win, settings = self.win, self.settings
        win._preferences("assistant")
        self.app.processEvents()
        with mock.patch.object(win, "_save_config", wraps=win._save_config) as save:
            times = self.keys(settings.meridio.url)
            self.assertEqual(save.call_count, 0)
        self.assertLess(median(times), KEY_MS, times)
        settings.flush_typing()
        self.assertTrue(win.cfg.assistant_local_url.endswith("a" * KEYS))
        win._preferences("maps")
        self.app.processEvents()
        settings.maps._add()
        self.app.processEvents()
        with mock.patch.object(win, "_save_config", wraps=win._save_config) as save:
            times = self.keys(settings.maps.attribution)
            self.assertEqual(save.call_count, 0)
        self.assertLess(median(times), KEY_MS, times)
        settings.flush_typing()
        self.assertTrue(win.cfg.map_sources[-1]["attribution"].endswith("a" * KEYS))

    def test_the_report_is_not_made_while_the_file_page_covers_it(self):
        """Its pages are not in sight, and a page of Typst holds the keys for as long as it takes: made on closing."""
        win = self.win
        win.energy = {"sim": object()}                                     # as ready
        with mock.patch("meridiana.ui.report.preview_steps") as steps:
            win._preview_report()
            steps.assert_not_called()


class Properties(unittest.TestCase):
    """Sample of the panel: its fields answer at the end of the edit, never at each key."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_a_key_in_the_properties_costs_little(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        _setup.window(self, capannone(), config.Config(background="none", theme="light"), size=(1400, 900))
        win = self.win
        win._navigate(("site",))
        self.app.processEvents()
        win.props.pod.setFocus()
        times = []
        for _n in range(KEYS):
            start = time.perf_counter()
            QTest.keyClick(win.props.pod, Qt.Key.Key_A)
            times.append((time.perf_counter() - start) * 1000)
        self.assertLess(median(times), KEY_MS, times)


if __name__ == "__main__":
    unittest.main()
