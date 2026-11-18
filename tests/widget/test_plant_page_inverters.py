"""The inverters of the Plant one by one (R297, study 23, I-A and A2): a card for each with the disc of its number as
the handle, renamed with F2 or from its menu, moved with Alt+Up and Alt+Down or by dragging the disc (the strings
renumbered), its datasheet, «String this inverter…», «Empty its strings», «Take out of the plant». The model's part
(plant.rename_unit, move_unit, renumber_runs) needs no display; the cards need an offscreen one."""

import unittest

import _setup

setUpModule = _setup.keep_global_state


def energy(count: int = 3) -> dict:
    from _fixtures import inverter_record
    return {"inverters": [{"record": inverter_record(), "count": count, "name": ""}],
            "strings": {"runs": [{"inverter": 1, "mppt": 1, "modules": ["a", "b"]},
                                 {"inverter": 2, "mppt": 2, "modules": ["c", "d"]},
                                 {"inverter": 3, "mppt": 1, "modules": ["e", "f"]}]}}


class TheModel(unittest.TestCase):
    def test_renaming_one_of_three_alike_splits_the_entry_and_keeps_the_numbers(self):
        from meridiana.energy import plant
        entries = plant.rename_unit(energy(), 2, "Tettoia")
        self.assertEqual([e["count"] for e in entries], [1, 1, 1])
        self.assertEqual([e["name"] for e in entries], ["", "Tettoia", ""])
        self.assertEqual([k for k in plant.unit_keys({"inverters": entries})], [(0, 0), (1, 0), (2, 0)])
        self.assertIsNone(plant.rename_unit(energy(), 7, "x"))

    def test_moving_an_inverter_renumbers_the_strings_of_those_moved(self):
        from meridiana.energy import plant
        e = energy()
        entries, mapping = plant.move_unit(e, 3, 0)                 # the third first
        self.assertEqual(len(entries), 3)
        self.assertEqual(mapping, {3: 1, 1: 2, 2: 3})
        runs = plant.renumber_runs(e["strings"]["runs"], mapping)
        self.assertEqual([r["inverter"] for r in runs], [2, 3, 1])
        self.assertEqual([r["mppt"] for r in runs], [1, 2, 1])      # the inputs stay
        self.assertEqual(plant.move_unit(e, 2, 1), (None, {}))      # nothing moves
        e2 = {"inverters": [dict(e["inverters"][0], name="Capannone", count=1),
                            dict(e["inverters"][0], name="Tettoia", count=1)]}
        entries, mapping = plant.move_unit(e2, 1, 1)
        self.assertEqual([x["name"] for x in entries], ["Tettoia", "Capannone"])
        self.assertEqual(mapping, {1: 2, 2: 1})


class TheCards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look()

    def setUp(self):
        from PySide6.QtGui import QAction
        from widget.test_string_list import plant_of

        from meridiana import model
        from meridiana.ui.plant_page import PlantInspector
        actions = {key: QAction(key) for key in
                   ("inverter_catalog", "inverter_auto", "strings_auto", "strings_manual", "strings_clear")}
        self.panel = PlantInspector(actions)
        self.addCleanup(_setup.dispose, self.panel)
        self.project = model.Project(name="Prova")
        self.project.energy = energy()
        self.plant = plant_of([{"inverter": 1, "mppt": 1, "modules": [f"s1/0:{s}" for s in range(8)]},
                               {"inverter": 2, "mppt": 2, "modules": [f"s1/1:{s}" for s in range(8)]}], count=3)
        self.panel.show_plant(self.project, self.plant)
        self.panel.resize(360, 900)
        self.panel.show()
        _setup.turn_events(self.app, 50)

    def test_a_card_for_each_inverter_with_its_disc_name_model_and_strings(self):
        cards = self.panel.units.cards
        self.assertEqual(sorted(cards), [1, 2, 3])
        self.assertEqual([c.disc.number for c in cards.values()], [1, 2, 3])
        self.assertIn("AC-20K", cards[1].name.text())
        self.assertIn("20.0 kW", cards[1].what.text())
        self.assertIn("2 MPPT", cards[1].what.text())
        self.assertIn("1 string on 1 input", cards[1].strings.text())
        self.assertIn("8 modules", cards[1].strings.text())
        self.assertEqual(cards[3].strings.text(), "no strings")
        self.assertTrue(cards[1].current)                           # the one the Strings show
        self.assertLess(cards[1].y(), cards[2].y())
        self.assertEqual(cards[1].disc.width(), cards[1].disc.height())

    def test_a_click_on_a_card_shows_its_strings_and_outlines_it(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        cards = self.panel.units.cards
        QTest.mouseClick(cards[2], Qt.MouseButton.LeftButton)
        self.assertEqual(self.panel.working_inverter.currentData(), 2)
        self.assertEqual(self.panel.list.working_unit, 2)
        self.assertTrue(cards[2].current)
        self.assertFalse(cards[1].current)

    def test_f2_renames_in_place_and_escape_gives_up(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        card = self.panel.units.cards[2]
        renamed = []
        self.panel.renamed.connect(lambda *a: renamed.append(a))
        card.setFocus()
        QTest.keyClick(card, Qt.Key.Key_F2)
        self.assertFalse(card.editor.isHidden())
        self.assertTrue(card.name.isHidden())
        card.editor.setText("Tettoia")
        QTest.keyClick(card.editor, Qt.Key.Key_Return)
        self.assertEqual(renamed, [(2, "Tettoia")])
        self.assertTrue(card.editor.isHidden())
        card.rename()
        card.editor.setText("altro")
        QTest.keyClick(card.editor, Qt.Key.Key_Escape)
        self.assertEqual(renamed, [(2, "Tettoia")])                 # given up: nothing more
        self.assertTrue(card.editor.isHidden())

    def test_alt_arrows_and_the_menu_move_the_inverter_and_a_drop_says_where(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        units = self.panel.units
        moved = []
        self.panel.moved.connect(lambda *a: moved.append(a))
        card = units.cards[1]
        card.setFocus()
        QTest.keyClick(card, Qt.Key.Key_Up, Qt.KeyboardModifier.AltModifier)       # already first: nothing
        QTest.keyClick(card, Qt.Key.Key_Down, Qt.KeyboardModifier.AltModifier)
        self.assertEqual(moved, [(1, 1)])
        units._menu(3, units.cards[3].mapToGlobal(units.cards[3].rect().center()))
        menu = units.menu
        self.addCleanup(menu.close)
        texts = [a.text() for a in menu.actions() if not a.isSeparator()]
        self.assertEqual(texts, ["Rename", "Move up", "Move down", "Datasheet…", "String this inverter…",
                                 "Empty its strings", "Take out of the plant"])
        self.assertFalse(menu.actions()[2].isEnabled())             # the last cannot go down
        menu.actions()[1].trigger()
        self.assertEqual(moved[-1], (3, 1))
        # a drop at the middle of the third card puts the dragged one in its place
        self.assertEqual(units.position_at(units.cards[3].geometry().center().y() + 1), 3)
        self.assertEqual(units.position_at(units.cards[1].geometry().top()), 0)

    def test_the_menu_asks_the_datasheet_the_stringing_the_emptying_and_the_removal(self):
        units = self.panel.units
        got = {}
        for name in ("datasheetAsked", "stringAsked", "emptied", "removed"):
            getattr(self.panel, name).connect(lambda n, key=name: got.setdefault(key, []).append(n))
        units._menu(2, units.cards[2].mapToGlobal(units.cards[2].rect().center()))
        self.addCleanup(units.menu.close)
        for a in units.menu.actions()[4:]:
            if not a.isSeparator():
                a.trigger()
        self.assertEqual(got, {"datasheetAsked": [2], "stringAsked": [2], "emptied": [2], "removed": [2]})

    def test_the_datasheet_window_shows_the_record_and_the_strip_of_the_popup_lists_the_scopes(self):
        from meridiana.ui.plant_page import DatasheetSheet, StringingPopup
        sheet = DatasheetSheet(self.plant.units[0], self.project.energy["inverters"][0]["record"])
        self.addCleanup(_setup.dispose, sheet)
        self.assertIn("AC-20K", sheet.view.toPlainText() + sheet.windowTitle() + sheet.findChildren(type(sheet.view))[0].toPlainText())
        self.assertIn("1100", sheet.view.toPlainText())
        popup = StringingPopup()
        self.addCleanup(_setup.dispose, popup)
        popup.prepare(self.plant, 12, 2, {"strategy": "rows", "n_series": 7}, 1.25)
        self.assertEqual(popup.scope.count(), 5)                    # the plant, the selection, three inverters
        self.assertEqual(popup.scope.currentData(), ("unit", 2))
        asked = []
        popup.asked.connect(asked.append)
        popup.go.click()
        self.assertEqual(asked, [{"scope": "unit", "unit": 2, "replace": True, "strategy": "rows", "n_series": 7,
                                  "dc_ac": 1.25}])
        popup.prepare(self.plant, 0, 0, {}, 1.1)
        self.assertEqual(popup.scope.currentData(), ("all", 0))
        self.assertFalse(popup.scope.model().item(1).isEnabled())   # no module selected


if __name__ == "__main__":
    unittest.main()
