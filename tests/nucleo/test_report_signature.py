"""Who signs a project's report and why (R331, reports.py): the only profile signs a project that chose none, «Nobody»
chosen stays so, in the project and in the Settings, and what is written in the Settings wins over the copy saved in
the project's file, or a logo would never reach a project saved before it."""

import unittest
from types import SimpleNamespace

import _setup  # noqa: F401  puts src/ on the path

from meridiana import reports

STUDIO = {"name": "Studio", "signer": "A", "logo": "a.png"}
OTHER = {"name": "Altro", "signer": "B", "logo": ""}


def project(report=None, embedded=None):
    return SimpleNamespace(report=report or {}, resources={"report_profile": embedded} if embedded else {})


class Signature(unittest.TestCase):
    def signed(self, p, profiles=(), default=""):
        s = reports.signature(p, list(profiles), default)
        return s["name"], s["source"]

    def test_the_only_profile_signs_a_project_that_chose_none(self):
        """Daniel's case of 02/11/2026: the logo in the only profile, the default still «Nobody», no logo in the report."""
        self.assertEqual(self.signed(project(), [STUDIO]), ("Studio", "default"))
        self.assertEqual(reports.profile_for(project(), [STUDIO])["logo"], "a.png")

    def test_nobody_chosen_in_the_project_stays_so(self):
        p = project({"profile": ""})
        self.assertEqual(self.signed(p, [STUDIO], "Studio"), ("", "nobody"))
        self.assertIsNone(reports.profile_for(p, [STUDIO], "Studio"))

    def test_nobody_chosen_in_the_settings_is_not_the_same_as_nothing_chosen(self):
        self.assertEqual(self.signed(project(), [STUDIO], reports.NOBODY), ("", "none"))
        self.assertEqual(reports.default_profile([STUDIO], reports.NOBODY), "")
        self.assertEqual(reports.default_profile([STUDIO], ""), "Studio")

    def test_several_profiles_and_no_default_sign_nothing(self):
        self.assertEqual(self.signed(project(), [STUDIO, OTHER]), ("", "none"))
        self.assertEqual(self.signed(project(), [STUDIO, OTHER], "Altro"), ("Altro", "default"))

    def test_a_default_that_is_gone_falls_to_the_only_one(self):
        self.assertEqual(reports.default_profile([STUDIO], "Rimosso"), "Studio")

    def test_the_project_choice_wins_and_a_lost_one_is_said(self):
        self.assertEqual(self.signed(project({"profile": "Altro"}), [STUDIO, OTHER], "Studio"), ("Altro", "project"))
        self.assertEqual(self.signed(project({"profile": "Vecchio"}), [STUDIO], "Studio"), ("Vecchio", "missing"))

    def test_the_settings_win_over_the_copy_in_the_file_and_the_copy_serves_who_has_no_settings(self):
        saved = {"name": "Studio", "signer": "A"}                        # saved before the logo
        s = reports.signature(project({}, saved), [STUDIO])
        self.assertEqual((s["source"], s["profile"]["logo"]), ("embedded", "a.png"))
        s = reports.signature(project({}, saved), [])
        self.assertEqual((s["name"], s["source"], s["profile"]), ("Studio", "embedded", None))
        self.assertEqual(self.signed(project({"profile": "Studio"}, saved)), ("Studio", "embedded"))


if __name__ == "__main__":
    unittest.main()
