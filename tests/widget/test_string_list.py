"""The list of the strings in the right panel of the Plant phase (ui/plant_page.StringList, R115, Daniel 25/10/2026:
«se seleziono una stringa non mi porta alla stringa, se premo Canc non me la cancella, il + non fa nulla, ha i bordi
deformi»): a section for each input with a tool button «+» of the design system, the strings under it with their
colour, modules and state; a row chosen, double clicked or with the right button says so; as tall as its rows.
PySide6 and a display (offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


def plant_of(runs, count=1):
    """A plant of one inverter with two inputs (energy/plant.build) with the strings `runs` on three rows of eight."""
    from _fixtures import inverter_record

    from meridiana import layout, model
    from meridiana.energy import plant
    from meridiana.energy.components import ModuleSpec
    p = model.Project(name="Prova")
    p.energy = {"inverters": [{"record": inverter_record(), "count": count, "name": ""}],
                "strings": {"runs": runs}}
    placed = []
    for r in range(3):
        for s in range(8):
            x, y = 1.2 * s, 3.0 * r
            placed.append(layout.PlacedModule(r, s, 0, [(x - 0.5, y - 1), (x + 0.5, y - 1), (x + 0.5, y + 1),
                                                        (x - 0.5, y + 1)], (x, y), 1.0, 15.0, 0.0))
    module = ModuleSpec.from_record({"manufacturer": "Acme", "model": "450", "pmax": 450, "vmp": 33.6, "imp": 13.4,
                                     "voc": 40.1, "isc": 14.1, "beta_voc": -0.25, "alpha_isc": 0.046,
                                     "gamma_pmax": -0.30, "cells": 108, "length": 1.762, "width": 1.134,
                                     "max_system_voltage_v": 1500, "max_series_fuse_a": 25})
    return plant.build(p, groups=[plant.Group("s1.0", "s1", "s1", module, placed)])


class TheList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look()

    def setUp(self):
        from meridiana.ui.plant_page import StringList
        self.list = StringList()
        self.addCleanup(self.list.deleteLater)
        self.list.resize(320, 400)
        self.runs = [{"inverter": 1, "mppt": 1, "modules": [f"s1/0:{s}" for s in range(8)]},
                     {"inverter": 1, "mppt": 1, "modules": [f"s1/1:{s}" for s in range(8)]}]
        self.plant = plant_of(self.runs)
        self.list.show_plant(self.plant, ["#ff8800", "#0088ff"], {"ok": "#0a0", "check": "#fa0", "fail": "#d00"})
        self.list.show()
        self.app.processEvents()

    def test_each_input_is_a_section_with_its_plus_and_the_strings_under_it(self):
        from PySide6.QtWidgets import QToolButton

        from meridiana.ui.sections import SECTION_ROLE, TAIL_ROLE
        lst = self.list
        heads = [lst.topLevelItem(i) for i in range(lst.topLevelItemCount())]
        self.assertEqual([h.text(0) for h in heads], ["Inverter 1 · MPPT 1", "Inverter 1 · MPPT 2"])
        self.assertEqual([h.data(0, SECTION_ROLE) for h in heads], ["", ""])
        self.assertEqual(sorted(lst.rows), [0, 1])
        self.assertTrue(lst.rows[0].text(0).startswith("1.1.1"))
        self.assertIn("8 modules", lst.rows[0].text(0))
        self.assertIsNone(lst.rows[0].data(0, TAIL_ROLE))                   # standard painting follows a live theme
        self.assertFalse(lst.rows[0].icon(0).isNull())                      # its colour, as on the plan
        self.assertFalse(lst.rows[0].icon(1).isNull())                      # its state, a mark
        self.assertTrue(heads[1].child(1).text(0).startswith("free"))      # an input without strings says so
        self.assertFalse(heads[1].child(1).flags() & heads[1].child(1).flags().ItemIsSelectable)
        for key, add in lst.adders.items():
            self.assertIsInstance(add, QToolButton)                          # the design system's tool button
            self.assertTrue(add.autoRaise())
            self.assertFalse(add.icon().isNull())                            # Lucide's «plus», no «+» drawn as text
            self.assertEqual(add.text(), "")
            self.assertIn(f"input {key[1]} of inverter {key[0]}", add.toolTip())
            self.assertEqual(add.styleSheet(), "")                           # no border of its own (R115)
        self.assertGreaterEqual(lst.height(), sum(lst.visualItemRect(r).height() for r in lst.rows.values()))

    def test_every_input_shows_its_range_parallel_limit_power_state_and_reason(self):
        first = self.list.input_info[(1, 1)].text(0)
        second = self.list.input_info[(1, 2)].text(0)
        self.assertIn("6-25 in series", first)
        self.assertIn("max 1 in parallel", first)
        self.assertIn("\n", first)
        self.assertIn("7.20 kWp", first)
        self.assertIn("2 strings", first)
        self.assertNotIn("⚠", first)
        self.assertFalse(self.list.input_info[(1, 1)].icon(1).isNull())
        self.assertIn("to be checked", first)
        self.assertEqual(len(first.splitlines()), 5)
        self.assertIn("Physical input count not specified", first)
        self.assertEqual(self.list.input_info[(1, 1)].foreground(0).style(),
                         self.list.input_info[(1, 1)].foreground(0).style().NoBrush)
        self.assertIn("current", self.list.input_info[(1, 1)].toolTip(0))
        self.assertIn("0.00 kWp", second)
        self.assertIn("empty", second)
        self.assertFalse(self.list.input_info[(1, 2)].icon(1).isNull())
        self.assertIn("Activate input 2", self.list.adders[(1, 2)].toolTip())
        self.assertIn("parallel", self.list.adders[(1, 2)].toolTip())

    def test_the_input_being_drawn_is_highlighted_until_the_draft_ends(self):
        from meridiana.ui.sections import ACTIVE_ROLE

        lst = self.list
        first, second = (lst.topLevelItem(i) for i in range(2))
        self.assertFalse(first.data(0, ACTIVE_ROLE))
        lst.show_draft(1, 2)
        self.assertFalse(first.data(0, ACTIVE_ROLE))
        self.assertTrue(second.data(0, ACTIVE_ROLE))
        self.assertTrue(second.data(1, ACTIVE_ROLE))
        self.assertEqual(second.background(0), lst.palette().brush(lst.palette().ColorRole.Highlight))
        lst.show_draft()
        self.assertFalse(second.data(0, ACTIVE_ROLE))
        self.assertFalse(second.data(1, ACTIVE_ROLE))
        self.assertEqual(second.background(0).style(), second.background(0).style().NoBrush)

    def test_plus_a_choice_a_double_click_and_the_right_button_say_so(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        lst = self.list
        got = []
        lst.newString.connect(lambda n, k: got.append(("new", n, k)))
        lst.chosen.connect(lambda i: got.append(("chosen", i)))
        lst.redraw.connect(lambda i: got.append(("redraw", i)))
        lst.menuAsked.connect(lambda i, _w: got.append(("menu", i)))
        QTest.mouseClick(lst.adders[(1, 2)], Qt.MouseButton.LeftButton)
        rect = lst.visualItemRect(lst.rows[1])
        QTest.mouseClick(lst.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, rect.center())
        QTest.mouseDClick(lst.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, rect.center())
        lst.customContextMenuRequested.emit(QPoint(rect.center()))
        self.assertEqual(got[:3], [("new", 1, 2), ("chosen", 1), ("redraw", 1)])
        self.assertIn(("menu", 1), got)
        self.assertEqual(lst.current(), 1)
        got.clear()
        lst.choose(0)                                                        # chosen on the plan: no signal back
        self.assertEqual((lst.current(), got), (0, []))
        lst.choose(-1)
        self.assertEqual(lst.current(), -1)

    def test_a_string_whose_inverter_was_removed_remains_available_for_correction(self):
        broken = plant_of([{"inverter": 99, "mppt": 1, "modules": [f"s1/0:{s}" for s in range(8)]}])
        self.list.show_plant(broken, [], {})
        self.assertIn(0, self.list.rows)
        self.list.choose(0)
        self.assertEqual(self.list.current(), 0)

    def test_larger_text_keeps_the_last_input_row_inside_the_list(self):
        larger = self.list.font()
        larger.setPixelSize(20)
        self.list.setFont(larger)
        self.app.processEvents()
        last = self.list.topLevelItem(1).child(1)
        self.assertLessEqual(self.list.visualItemRect(last).bottom(), self.list.viewport().height())


class WorkingInverter(unittest.TestCase):
    """A physical inverter is the workspace; changing it must never edit or renumber the plant."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look()

    def setUp(self):
        from PySide6.QtGui import QAction
        from _fixtures import inverter_record

        from meridiana import model
        from meridiana.ui.plant_page import PlantInspector
        from meridiana.ui.style import pad_fields
        self.actions = {key: QAction(key) for key in
                        ("inverter_catalog", "inverter_auto", "strings_auto", "strings_complete", "strings_clear")}
        self.panel = PlantInspector(self.actions)
        self.addCleanup(self.panel.deleteLater)
        self.project = model.Project(name="Prova")
        self.project.energy = {"inverters": [{"record": inverter_record(), "count": 3, "name": ""}]}
        self.plant = plant_of([
            {"inverter": 1, "mppt": 1, "modules": [f"s1/0:{s}" for s in range(8)]},
            {"inverter": 2, "mppt": 2, "modules": [f"s1/1:{s}" for s in range(8)]},
        ], count=3)
        self.panel.show_plant(self.project, self.plant)
        pad_fields(self.panel)
        self.panel.resize(320, 800)
        self.panel.show()
        self.app.processEvents()

    def test_default_workspace_shows_one_inverter_with_every_input_including_free_ones(self):
        self.assertEqual(set(self.panel.list.input_heads), {(1, 1), (1, 2)})
        self.assertEqual(set(self.panel.list.rows), {0})
        self.assertEqual(self.panel.working_inverter.currentData(), 1)
        self.assertEqual([self.panel.working_inverter.itemData(i) for i in range(3)], [1, 2, 3])
        self.assertTrue(self.panel.inverters_group.isHidden())
        self.panel.manage_inverters.click()
        self.assertFalse(self.panel.inverters_group.isHidden())
        self.assertEqual(self.panel.entry_rows[0][1].value(), 3)

    def test_choosing_a_workspace_keeps_global_string_indices_and_the_new_string_target(self):
        changes, targets, choices = [], [], []
        self.panel.edited.connect(lambda *args: changes.append(args))
        self.panel.list.newString.connect(lambda *args: targets.append(args))
        self.panel.stringChosen.connect(choices.append)
        self.panel.list.choose(0)
        self.panel.working_inverter.setCurrentIndex(1)
        self.assertEqual(set(self.panel.list.input_heads), {(2, 1), (2, 2)})
        self.assertEqual(set(self.panel.list.rows), {1})
        self.panel.list.adders[(2, 1)].click()
        self.assertEqual(targets, [(2, 1)])
        self.assertEqual(changes, [])
        self.assertEqual(choices, [-1])
        self.assertEqual([s.inverter for s in self.plant.strings], [1, 2])

    def test_plan_choice_switches_workspace_without_emitting_a_selection_back(self):
        choices = []
        self.panel.stringChosen.connect(choices.append)
        self.panel.show_string(self.plant, 1)
        self.panel.list.choose(1)
        self.assertEqual(self.panel.working_inverter.currentData(), 2)
        self.assertEqual(self.panel.list.current(), 1)
        self.assertEqual(choices, [])
        self.panel.show_plant(self.project, self.plant, chosen=1)
        self.assertEqual(self.panel.working_inverter.currentData(), 2)

    def test_draw_uses_the_working_inverter_unless_a_string_is_explicitly_chosen(self):
        from types import SimpleNamespace
        from meridiana.ui.window import MainWindow

        self.panel.working_inverter.setCurrentIndex(1)
        host = SimpleNamespace(plant_state=self.plant, chosen_string=-1, plant_inspector=self.panel)
        before = [(s.inverter, s.mppt) for s in self.plant.strings]
        self.assertEqual(MainWindow._input_for_new_string(host), (2, 1))
        host.chosen_string = 0
        self.assertEqual(MainWindow._input_for_new_string(host), (1, 1))
        self.assertEqual([(s.inverter, s.mppt) for s in self.plant.strings], before)

    def test_refresh_preserves_workspace_and_falls_back_when_its_unit_is_removed(self):
        self.panel.working_inverter.setCurrentIndex(2)
        self.panel.show_plant(self.project, self.plant)
        self.assertEqual(self.panel.working_inverter.currentData(), 3)
        self.panel.show_plant(self.project, None)
        self.panel.show_plant(self.project, self.plant)
        self.assertEqual(self.panel.working_inverter.currentData(), 3)
        smaller = plant_of([], count=1)
        self.panel.show_plant(self.project, smaller)
        self.assertEqual(self.panel.working_inverter.currentData(), 1)
        self.assertEqual(set(self.panel.list.input_heads), {(1, 1), (1, 2)})

    def test_automatic_commands_still_use_the_original_plant_actions(self):
        calls = []
        self.panel.working_inverter.setCurrentIndex(1)
        for key in ("strings_auto", "strings_complete", "strings_clear"):
            self.actions[key].triggered.connect(lambda _checked=False, k=key: calls.append(k))
            self.panel.string_buttons[key].click()
        self.assertEqual(calls, ["strings_auto", "strings_complete", "strings_clear"])

    def test_narrow_inspector_keeps_the_workspace_and_manage_button_inside_the_viewport(self):
        self.panel.resize(240, 800)
        self.app.processEvents()
        self.assertLessEqual(self.panel.widget().width(), self.panel.viewport().width())


if __name__ == "__main__":
    unittest.main()
