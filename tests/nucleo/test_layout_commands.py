"""R564 (Daniel 14/11/2026): the commands that lay the modules said once, for the bar, the menus and the panel
(app/interface/layout_commands.py): «Fill» acts on a sub-field it can fill and says why it cannot otherwise, the
entries of a sub-field's menus, the canopy's own entries, and the change «Fill» and «Empty» make. No Qt."""

import unittest

import _setup  # noqa: F401

from meridiana.app.interface import layout_commands, shortcuts
from meridiana.core.layout import manual
from meridiana.core.model import model


def sub(**values):
    return model.SubField(id="s1", name="Sud", ring=[[0, 0], [10, 0], [10, 6], [0, 6]], **values)


class FillState(unittest.TestCase):
    def test_fill_acts_on_an_empty_sub_field(self):
        self.assertEqual(layout_commands.fill_state(sub()), (True, "", ""))

    def test_a_sub_field_drawn_with_layout_is_full_and_says_why(self):
        """The defect of R564: drawn with «Layout» a sub-field is by hand and laid (R445); «Fill» on it did nothing
        and said nothing. Now it is off, with a word for the menu and a sentence for the status bar."""
        can, note, why = layout_commands.fill_state(sub(filled=True, manual=True, flush=True))
        self.assertFalse(can)
        self.assertEqual(note, "already full")
        self.assertIn("«Sud» is already full", why)

    def test_fill_gives_back_the_modules_taken_out_of_an_automatic_layout(self):
        self.assertTrue(layout_commands.fill_state(sub(filled=True, removed=["0:1"]))[0])
        self.assertFalse(layout_commands.fill_state(sub(filled=True))[0])
        self.assertFalse(layout_commands.fill_state(sub(filled=True, manual=True, removed=["0:1"]))[0])

    def test_nothing_selected(self):
        can, note, why = layout_commands.fill_state(None)
        self.assertFalse(can)
        self.assertEqual(note, "")
        self.assertTrue(why)


class Entries(unittest.TestCase):
    def test_the_words_are_the_catalogue_s(self):
        words = {c.id: shortcuts.plain(c.text) for c in shortcuts.commands()}
        self.assertEqual(words["tool_subfield"], "Layout")
        self.assertEqual(layout_commands.text("fill"), words["fill"])
        self.assertEqual(layout_commands.text("fill"), "Fill")
        self.assertEqual(layout_commands.text("empty"), "Empty")
        self.assertEqual(layout_commands.text("relayout"), words["refill"])
        self.assertEqual(layout_commands.text("fill_area"), "Area with automatic layout")
        self.assertEqual(layout_commands.text("canopy_layout"), "Modules on a canopy…")

    def test_entries_of_each_kind_of_sub_field(self):
        def said(sf):
            return [(e["action"], e["enabled"], e["note"]) for e in layout_commands.entries(sf)]
        self.assertEqual(said(sub()), [("fill", True, "")])
        self.assertEqual(said(sub(filled=True)), [("fill", False, "already full"), ("explode", True, ""),
                                                  ("empty", True, "")])
        self.assertEqual(said(sub(filled=True, manual=True)), [("relayout", True, ""), ("explode", True, ""),
                                                               ("empty", True, "")])
        self.assertEqual(layout_commands.entries(None), [])

    def test_no_entry_says_the_old_names(self):
        for sf in (sub(), sub(filled=True), sub(filled=True, manual=True)):
            for e in layout_commands.entries(sf):
                self.assertNotIn(e["text"], ("Lay the modules", "Lay again", "Take the modules out", "Lay"))

    def test_the_canopy_has_its_own_entries_and_a_building_none(self):
        canopy = model.Building(id="b2", name="Pensilina 1", footprint=[[0, 0], [5, 0], [5, 10], [0, 10]],
                                canopy=model.Canopy())
        found = layout_commands.canopy_entries(canopy)
        self.assertEqual([(e["action"], e["header"]) for e in found], [("", True), ("canopy_layout", False)])
        self.assertEqual(found[0]["text"], "Canopy «Pensilina 1»")
        house = model.Building(id="b1", name="Casa", footprint=[[0, 0], [5, 0], [5, 10], [0, 10]])
        self.assertEqual(layout_commands.canopy_entries(house), [])
        self.assertEqual(layout_commands.canopy_entries(None), [])


class TheChange(unittest.TestCase):
    def project(self, **values):
        p = model.Project()
        p.subfields.append(sub(**values))
        return p

    def test_fill_and_empty(self):
        p = self.project(removed=["0:1"])
        manual.fill(p, "s1")(p)
        self.assertTrue(p.subfields[0].filled)
        self.assertEqual(p.subfields[0].removed, [])            # given back to an automatic layout
        manual.fill(p, "s1", False)(p)
        self.assertFalse(p.subfields[0].filled)
        q = self.project(manual=True, removed=["0:1"])
        manual.fill(q, "s1")(q)
        self.assertEqual(q.subfields[0].removed, ["0:1"])       # what was taken out by hand stays out
        with self.assertRaises(ValueError):
            manual.fill(p, "nobody")


if __name__ == "__main__":
    unittest.main()
