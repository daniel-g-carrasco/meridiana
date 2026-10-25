"""The list of the strings in the right panel of the Plant phase (ui/plant_page.StringList, R115, Daniel 25/10/2026:
«se seleziono una stringa non mi porta alla stringa, se premo Canc non me la cancella, il + non fa nulla, ha i bordi
deformi»): a section for each input with a tool button «+» of the design system, the strings under it with their
colour, modules and state; a row chosen, double clicked or with the right button says so; as tall as its rows.
PySide6 and a display (offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


def plant_of(runs):
    """A plant of one inverter with two inputs (energy/plant.build) with the strings `runs` on three rows of eight."""
    from _fixtures import inverter_record

    from meridiana import layout, model
    from meridiana.energy import plant
    from meridiana.energy.components import ModuleSpec
    p = model.Project(name="Prova")
    p.energy = {"inverters": [{"record": inverter_record(), "count": 1, "name": ""}],
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

        from meridiana.ui.sections import SECTION_ROLE
        lst = self.list
        heads = [lst.topLevelItem(i) for i in range(lst.topLevelItemCount())]
        self.assertEqual([h.text(0) for h in heads], ["Inverter 1 · Input 1", "Inverter 1 · Input 2"])
        self.assertEqual([h.data(0, SECTION_ROLE) for h in heads], ["2 strings", "0 strings"])
        self.assertEqual(sorted(lst.rows), [0, 1])
        self.assertTrue(lst.rows[0].text(0).startswith("1.1.1"))
        self.assertIn("8 modules", lst.rows[0].text(0))
        self.assertFalse(lst.rows[0].icon(0).isNull())                      # its colour, as on the plan
        self.assertFalse(lst.rows[0].icon(1).isNull())                      # its state, a mark
        self.assertTrue(heads[1].child(0).text(0).startswith("free"))      # an input without strings says so
        self.assertFalse(heads[1].child(0).flags() & heads[1].child(0).flags().ItemIsSelectable)
        for key, add in lst.adders.items():
            self.assertIsInstance(add, QToolButton)                          # the design system's tool button
            self.assertTrue(add.autoRaise())
            self.assertFalse(add.icon().isNull())                            # Lucide's «plus», no «+» drawn as text
            self.assertEqual(add.text(), "")
            self.assertIn(f"input {key[1]} of inverter {key[0]}", add.toolTip())
            self.assertEqual(add.styleSheet(), "")                           # no border of its own (R115)
        self.assertGreaterEqual(lst.height(), sum(lst.visualItemRect(r).height() for r in lst.rows.values()))

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


if __name__ == "__main__":
    unittest.main()
