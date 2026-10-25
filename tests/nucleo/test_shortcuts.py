"""The commands and their keys (study 12, section 5; study 12a, 1.11): the map decided on 22/10/2026, the
keys never to use, and the conflicts the editor shows while the designer types."""

import unittest

import _setup  # noqa: F401

from meridiana import shortcuts as sc


class TheMap(unittest.TestCase):
    def test_the_keys_decided_in_study_12(self):
        b = sc.bindings({})
        for cid, keys in (("ortho", "F8"), ("snaps", "F3"), ("panel_checks", "Ctrl+J"), ("panel_project", "Ctrl+B"),
                          ("panel_properties", "Ctrl+P"), ("phase_model", "Ctrl+1"), ("phase_report", "Ctrl+6"), ("clean_screen", "Ctrl+0"), ("view_plan", "Ctrl+Shift+2"),
                          ("view_3d", "Ctrl+Shift+3"), ("focus_checks", "Ctrl+Shift+M"), ("shortcuts", "Ctrl+?"),
                          ("fix_check", "Ctrl+."),
                          ("tool_building", "B"), ("delete", "Del"), ("fit", "F"), ("next_phase", "Ctrl+Tab"),
                          ("previous_phase", "Ctrl+PgUp"), ("compute", "F5")):
            with self.subTest(cid):
                self.assertIn(keys, b[cid])

    def test_m_moves_d_measures_and_r_stays_the_rectangle(self):
        """Study 16, B (Daniel, 23/10/2026): M Move, D Measure; Rotate is R inside Move only (design 2.2)."""
        b = sc.bindings({})
        self.assertEqual((b["tool_move"], b["tool_measure"], b["rectangle"], b["tool_rotate"]),
                         (["M"], ["D"], ["R"], []))

    def test_no_default_is_a_key_to_avoid_and_none_is_shared(self):
        for c in sc.commands():
            for k in c.keys:
                with self.subTest(c.id, keys=k):
                    self.assertEqual(sc.problem(k), "")
                    self.assertEqual(sc.normalize(k), k)            # written as Qt writes it
        self.assertEqual(sc.conflicts(sc.bindings({})), {})

    def test_ids_are_unique_and_grouped(self):
        ids = [c.id for c in sc.commands()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(c.group in sc.groups() for c in sc.commands()))


class Keys(unittest.TestCase):
    def test_keys_are_written_one_way(self):
        for typed, written in (("shift+ctrl+p", "Ctrl+Shift+P"), ("Ctrl++", "Ctrl++"), ("ctrl+,", "Ctrl+,"),
                               ("ctrl+k, ctrl+s", "Ctrl+K, Ctrl+S"), ("v", "V"), ("delete", "Del"),
                               ("Control+escape", "Ctrl+Esc"), ("Alt+Shift+Ctrl+x", "Ctrl+Alt+Shift+X")):
            self.assertEqual(sc.normalize(typed), written)

    def test_the_keys_to_avoid_say_why(self):
        for keys, why in (("Ctrl+Alt+E", "AltGr"), ("Alt+F", "menus"), ("Alt+3", "menus"), ("Meta+A", "Super"),
                          ("Ctrl+[", "AltGr"), ("@", "AltGr"), ("Shift+?", "Shift twice"),
                          ("Ctrl+Shift+/", "Shift twice"), ("Ctrl+Space", "input method"), ("Alt+F4", "closes"),
                          ("Ctrl+Shift+U", "Unicode")):
            with self.subTest(keys):
                self.assertIn(why, sc.problem(keys))
        for fine in ("Ctrl+?", "Ctrl+.", "F8", "Ctrl+Shift+2", "Z", "Alt+F2"):
            self.assertEqual(sc.problem(fine), "", fine)

    def test_single_letters_and_f_keys(self):
        self.assertTrue(sc.single("v"))
        self.assertFalse(sc.single("Ctrl+V"))
        self.assertFalse(sc.single("F8"))
        self.assertTrue(sc.only_f_key(("F8",)))
        self.assertFalse(sc.only_f_key(("F8", "Ctrl+8")))
        self.assertFalse(sc.only_f_key(("F",)))
        self.assertFalse(sc.only_f_key(()))


class Changes(unittest.TestCase):
    def test_what_the_designer_changes_is_kept_as_differences(self):
        b = sc.bindings({"ortho": ["f9"], "nonexistent": ["Ctrl+K"], "fit": "F"})
        self.assertEqual(b["ortho"], ["F9"])
        self.assertNotIn("nonexistent", b)
        self.assertEqual(b["fit"], ["F"])                    # not a list: ignored
        self.assertEqual(sc.differences(b), {"ortho": ["F9"]})
        b["ortho"] = ["F8"]                                  # back to its default: it leaves the settings
        self.assertEqual(sc.differences(b), {})
        b["fit"] = []                                        # no key at all is a difference too
        self.assertEqual(sc.differences(b), {"fit": []})

    def test_a_key_already_taken_names_who_would_lose_it(self):
        b = sc.bindings({})
        self.assertEqual(sc.clashes(b, "ortho", "ctrl+b"), ["panel_project"])
        self.assertEqual(sc.clashes(b, "ortho", "F8"), [])   # its own key
        self.assertEqual(sc.clashes(b, "ortho", "Ctrl+K"), [])
        b["ortho"] = ["Ctrl+B"]
        self.assertEqual(sc.conflicts(b), {"Ctrl+B": ["ortho", "panel_project"]})

    def test_a_key_chosen_before_a_newer_default_took_it_stays_the_designers(self):
        keys, notes = sc.settle({"fit": ["Ctrl+L"]})        # chosen when Ctrl+L was nobody's; the assistant came later
        self.assertEqual(keys["fit"], ["Ctrl+L"])
        self.assertEqual(keys["assistant"], [])
        self.assertEqual(sc.conflicts(keys), {})
        self.assertEqual(notes, [("Ctrl+L", ["fit"], ["assistant"])])

    def test_two_commands_given_the_same_key_by_the_designer_are_said(self):
        keys, notes = sc.settle({"fit": ["Ctrl+K"], "ortho": ["Ctrl+K"]})
        self.assertEqual(notes, [("Ctrl+K", ["ortho", "fit"], [])])
        self.assertEqual(sc.settle({})[1], [])

    def test_commands_this_version_does_not_know_keep_their_keys(self):
        saved = {"fit": ["Z"], "future_command": ["Ctrl+K"]}  # written by a newer version
        keys = sc.bindings(saved)
        self.assertNotIn("future_command", keys)
        keys["ortho"] = ["F9"]
        self.assertEqual(sc.differences(keys, saved), {"fit": ["Z"], "ortho": ["F9"], "future_command": ["Ctrl+K"]})


if __name__ == "__main__":
    unittest.main()
