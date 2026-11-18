"""The logo from the Report phase (R331, Daniel 02/11/2026: «non c'è un modo in relazione di mettere direttamente da lì
il logo»): the two commands of the bar, where the logo goes, the first profile as the default, the offer when the
profile with the logo is not the project's, the formats. PySide6 and a display (offscreen will do)."""

import unittest
from pathlib import Path
from unittest import mock

import _setup
from _fixtures import capannone

from meridiana import config, reports

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="60" height="30"><rect width="60" height="30" fill="#369"/></svg>'


def profile(name: str, logo: str = "") -> dict:
    return {k: "" for k in reports.PROFILE_KEYS} | {"name": name, "signer": f"Firma {name}", "logo": logo}


class Logo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def start(self, profiles=(), default="", report=None):
        cfg = config.Config(background="none", network_pvgis=False, theme="light", report_profiles=list(profiles),
                            report_profile=default)
        _setup.window(self, capannone(), cfg, size=(1400, 900))
        if report is not None:
            self.win.project.report = report
        self.win.show_phase("report")
        self.app.processEvents()
        self.logo = self.paths.cache / "logo.svg"
        self.logo.parent.mkdir(parents=True, exist_ok=True)
        self.logo.write_text(SVG, encoding="utf-8")

    def test_the_bar_has_the_two_commands_in_a_group_of_their_own(self):
        self.start()
        bar = self.win.bars["report"]
        group = next(g for g in bar.groups if "report_logo" in g.buttons)
        self.assertEqual(sorted(group.buttons), ["report_logo", "report_profile"])
        with mock.patch("meridiana.ui.window.QFileDialog.getOpenFileName", return_value=("", "")) as chooser:
            bar.button_of("report_logo").click()
        chooser.assert_called_once()
        self.assertIn("*.svg", chooser.call_args[0][3])
        bar.button_of("report_profile").click()
        self.app.processEvents()
        self.assertTrue(self.win.file_page.isVisible())
        self.assertEqual(self.win.file_page.settings.current_section(), "report")

    def test_with_no_profile_one_is_made_the_default_and_opened(self):
        self.start()
        win = self.win
        win._put_report_logo(self.logo)
        self.app.processEvents()
        name = win.cfg.report_profiles[0]["name"]
        self.assertEqual(win.cfg.report_profile, name)
        self.assertTrue(Path(win._report_profile()["logo"]).is_file())
        self.assertTrue(win.file_page.isVisible())
        page = win.file_page.settings.report
        self.assertEqual(page.profiles[page.current]["name"], name)
        self.assertEqual(page.default.currentData(), name)
        win.file_page.back()                                               # R289: back to the project
        self.assertTrue(_setup.wait_until(self.app, lambda: not win.file_page.isVisible()))

    def test_the_only_profile_takes_the_logo_and_signs_a_project_that_chose_none(self):
        """Daniel's case: a profile, «Nobody» in the Settings because nobody ever chose, no logo in the report."""
        self.start([profile("Studio")])
        win = self.win
        with mock.patch.object(win, "_preview_report") as preview:
            win._put_report_logo(self.logo)
        preview.assert_called_once()                                       # at once, not after the usual pause
        self.assertEqual(win._report_signature()["name"], "Studio")
        self.assertTrue(Path(win._report_profile()["logo"]).is_file())
        self.assertFalse(win.report_side.offer.isVisible())
        self.assertFalse(win.file_page.isVisible())
        self.assertEqual(win.report_side.profile.itemText(0), "Default: Studio")

    def test_a_logo_reaches_a_project_saved_with_the_profile_before_it(self):
        self.start([profile("Studio")], "Studio")
        win = self.win
        win.project.resources = {"report_profile": {"name": "Studio", "signer": "Firma Studio"}}
        self.assertEqual(win._report_profile()["logo"], "")
        win._put_report_logo(self.logo)
        self.assertTrue(Path(win._report_profile()["logo"]).is_file())

    def test_a_project_with_nobody_keeps_it_until_the_offer_is_taken(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtWidgets import QScrollArea
        self.start([profile("Studio")], "Studio", {"profile": ""})
        win = self.win
        win._put_report_logo(self.logo)
        self.assertTrue(win.cfg.report_profiles[0]["logo"])
        self.assertEqual(win.project.report["profile"], "")                # not changed by itself
        self.assertIsNone(win._report_profile())
        self.assertTrue(win.report_side.offer.isVisible())
        self.assertIn("Studio", win.report_side.offer.line.text())
        self.assertIn("Studio", win.statusBar().currentMessage())
        win.report_side.offer.use.setText("Usalo per questo progetto")     # the longest of the languages
        win.report_side.offer.later.setText("Non ora")
        self.app.processEvents()
        area = win.report_side.parentWidget()
        while not isinstance(area, QScrollArea):
            area = area.parentWidget()
        for button in (win.report_side.offer.use, win.report_side.offer.later, win.report_side.manage):
            right = button.mapTo(area.viewport(), QPoint(button.width(), 0)).x()
            self.assertLessEqual(right, area.viewport().width(), button.text())    # not cut by the panel's edge
        # side by side they held the panel wider than the dock in Italian, seen on the picture only
        self.assertGreater(win.report_side.offer.later.y(), win.report_side.offer.use.y())
        win.report_side.offer.use.click()
        self.assertEqual(win.project.report["profile"], "Studio")
        self.assertTrue(Path(win._report_profile()["logo"]).is_file())
        self.assertFalse(win.report_side.offer.isVisible())
        win.undo.undo()                                                    # an edit of the project, undoable
        self.assertEqual(win.project.report["profile"], "")

    def test_the_offer_can_be_refused_and_does_not_follow_to_another_project(self):
        self.start([profile("Studio")], "Studio", {"profile": ""})
        win = self.win
        win._put_report_logo(self.logo)
        win.report_side.offer.later.click()
        self.assertFalse(win.report_side.offer.isVisible())
        self.assertEqual(win.project.report["profile"], "")
        win.report_offer = ("Studio", "un altro file")
        self.assertEqual(win._report_offer_text(), "")

    def test_a_logo_in_the_settings_on_a_profile_the_project_does_not_use_is_said_there(self):
        self.start([profile("Studio"), profile("Altro")], "Studio", {"profile": "Studio"})
        win = self.win
        win._preferences("report")
        self.app.processEvents()
        page = win.file_page.settings.report
        page.select_profile("Altro")
        page._set_logo(str(self.logo))
        self.assertEqual(win.project.report["profile"], "Studio")
        self.assertTrue(page.offer.isVisible())
        self.assertIn("Altro", page.offer.line.text())
        page.offer.use.click()
        self.assertEqual(win.project.report["profile"], "Altro")
        self.assertFalse(page.offer.isVisible())

    def test_several_profiles_and_none_in_use_ask_to_choose_first(self):
        self.start([profile("Studio"), profile("Altro")])
        win = self.win
        win._put_report_logo(self.logo)
        self.assertEqual([p["logo"] for p in win.cfg.report_profiles], ["", ""])
        self.assertIn("Signed by", win.statusBar().currentMessage())

    def test_the_logo_goes_in_the_profile_in_use_not_in_the_default(self):
        self.start([profile("Studio"), profile("Altro")], "Studio", {"profile": "Altro"})
        win = self.win
        win._put_report_logo(self.logo)
        logos = {p["name"]: p["logo"] for p in win.cfg.report_profiles}
        self.assertEqual(logos["Studio"], "")
        self.assertTrue(logos["Altro"])

    def test_what_is_not_an_image_is_refused_with_a_clear_message(self):
        self.start([profile("Studio")])
        win = self.win
        for name, content in (("note.txt", "ciao"), ("rotto.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="6"')):
            bad = self.logo.parent / name
            bad.write_text(content, encoding="utf-8")
            win._put_report_logo(bad)
            self.assertEqual(win.cfg.report_profiles[0]["logo"], "")
            self.assertEqual(self.dialogs[-1][0], "warning")
            self.assertIn(name, self.dialogs[-1][1][1])
        win._put_report_logo(self.logo.parent / "non-esiste.png")
        self.assertEqual(win.cfg.report_profiles[0]["logo"], "")
        self.assertEqual(self.dialogs[-1][0], "warning")

    def test_the_first_profile_made_in_the_settings_is_the_default(self):
        self.start()
        win = self.win
        win._preferences("report")
        self.app.processEvents()
        page = win.file_page.settings.report
        page._add()
        first = win.cfg.report_profiles[0]["name"]
        self.assertEqual(win.cfg.report_profile, first)
        page._add()
        self.assertEqual(win.cfg.report_profile, first)                    # the second one does not take its place

    def test_nobody_chosen_in_the_settings_is_kept_and_stays_when_read_again(self):
        self.start([profile("Studio")])
        win = self.win
        win._preferences("report")
        self.app.processEvents()
        page = win.file_page.settings.report
        self.assertEqual(page.default.currentData(), "Studio")             # what a project without a choice gets
        page.default.setCurrentIndex(0)
        self.assertEqual(win.cfg.report_profile, reports.NOBODY)
        self.assertIsNone(win._report_profile())
        win.file_page.settings._populate()                                 # read again from the settings
        self.assertEqual(win.file_page.settings.report.default.currentIndex(), 0)

    def test_saving_a_profile_again_makes_no_other_copy_of_its_logo(self):
        self.start([profile("Studio")])
        win = self.win
        win._preferences("report")
        self.app.processEvents()
        settings = win.file_page.settings
        page = settings.report
        page._set_logo(str(self.logo))
        page.fields["signer"].setText("Nuovo")
        page._typed("signer")
        settings._edited("report")
        self.assertEqual(len(list((self.paths.data / "logos").iterdir())), 1)
        self.assertEqual(win.cfg.report_profiles[0]["signer"], "Nuovo")

    def test_a_choice_that_names_no_profile_is_shown_as_such(self):
        self.start([profile("Studio")], "Studio", {"profile": "Vecchio"})
        combo = self.win.report_side.profile
        self.assertIn("Vecchio", combo.currentText())
        self.assertEqual(combo.currentData(), "Vecchio")


if __name__ == "__main__":
    unittest.main()
