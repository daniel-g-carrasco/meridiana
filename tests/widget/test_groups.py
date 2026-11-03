"""The groups of the right panel fold (R287) and the inputs of the Plant are a table (R286), offscreen:
a click on a group's header closes it to its header and opens it again with the height the layout gives it, Tab
never lands in the fields of a closed group, every group of the Properties and of the Plant inspector has its «?»,
and the inputs table has one row per MPPT with the figures of a known plant."""

import unittest

import _setup

setUpModule = _setup.keep_global_state


def plant_of(runs, count=1):
    """The plant of test_string_list: one inverter model (two MPPT) with the strings `runs` on three rows of eight."""
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
    return p, plant.build(p, groups=[plant.Group("s1.0", "s1", "s1", module, placed)])


class Folding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look()

    def setUp(self):
        from PySide6.QtWidgets import QFormLayout, QLineEdit, QScrollArea, QSpinBox, QVBoxLayout, QWidget

        from meridiana.ui import motion
        from meridiana.ui.style import Group, _FOLDED
        _FOLDED.clear()
        self.addCleanup(_FOLDED.clear)
        self.addCleanup(motion.set_reduced, False)
        self.area = QScrollArea()
        self.addCleanup(_setup.dispose, self.area)
        self.area.setWidgetResizable(True)
        page = QWidget()
        box = QVBoxLayout(page)
        self.first = Group("Prima")
        form = QFormLayout(self.first)
        self.fields = [QSpinBox() for _ in range(3)]
        for n, field in enumerate(self.fields):
            form.addRow(f"Campo {n}", field)
        self.second = Group("Seconda")
        self.edit = QLineEdit()
        QFormLayout(self.second).addRow("Nome", self.edit)
        box.addWidget(self.first)
        box.addWidget(self.second)
        box.addStretch(1)
        self.area.setWidget(page)
        self.area.resize(380, 600)
        self.area.show()
        self.app.processEvents()

    def click_header(self, group):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        QTest.mouseClick(group, Qt.MouseButton.LeftButton, pos=QPoint(60, 10))

    def settled(self, group):
        self.assertTrue(_setup.wait_until(self.app, lambda: group._fold is None or not group._fold.running))
        self.app.processEvents()

    def test_a_click_on_the_header_closes_the_group_to_its_header_and_opens_it_to_its_height(self):
        from meridiana.ui.style import MeridianaStyle
        full, below = self.first.height(), self.second.y()
        self.assertGreater(full, MeridianaStyle.head(self.first) + 40)
        self.assertIs(self.first.layout(), self.fields[0].parentWidget().layout())      # the caller's layout
        self.click_header(self.first)
        seen = set()
        while self.first._fold.running:
            self.app.processEvents()
            seen.add(self.first.height())
        self.app.processEvents()
        self.assertGreater(len(seen), 2, "the height moved through intermediate values")
        self.assertEqual(self.first.height(), MeridianaStyle.head(self.first) + 1)
        self.assertTrue(self.first.body().isHidden())
        self.assertFalse(self.first.expanded)
        self.assertEqual(self.second.y(), below - (full - self.first.height()), "no hole under a closed group")
        self.assertEqual(self.first.progress, 0.0)
        self.click_header(self.first)
        self.settled(self.first)
        self.assertEqual(self.first.height(), full)
        self.assertFalse(self.first.body().isHidden())
        self.assertEqual(self.first.progress, 1.0)
        self.assertFalse(self.first.body().layout().isEnabled() is False)

    def test_tab_never_lands_in_the_fields_of_a_closed_group(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        _setup.keyboard_or_skip(self, self.edit)
        self.first.set_expanded(False, ms=0)
        self.app.processEvents()
        self.edit.setFocus()
        self.app.processEvents()
        for _ in range(6):
            QTest.keyClick(self.area, Qt.Key.Key_Tab)
            self.app.processEvents()
            focused = self.app.focusWidget()
            self.assertFalse(focused is not None and self.first.isAncestorOf(focused),
                             f"Tab reached {focused} inside the closed group")

    def test_less_motion_closes_at_once_and_the_state_is_remembered_by_kind(self):
        from PySide6.QtWidgets import QFormLayout, QSpinBox

        from meridiana.ui import motion
        from meridiana.ui.style import Group, _FOLDED
        motion.set_reduced(True)
        self.click_header(self.first)
        self.assertTrue(self.first.body().isHidden())           # no movement to wait for
        self.assertEqual(_FOLDED, {"Prima": True})
        # the same kind of group built again comes back closed; another kind open
        again = Group("Prima")
        QFormLayout(again).addRow("Altro", QSpinBox())
        other = Group("Terza")
        QFormLayout(other).addRow("Altro", QSpinBox())
        page = self.area.widget()
        page.layout().insertWidget(2, again)
        page.layout().insertWidget(3, other)
        self.app.processEvents()
        self.assertFalse(again.expanded)
        self.assertTrue(again.body().isHidden())
        self.assertTrue(other.expanded)

    def test_a_group_that_does_not_fold_keeps_its_layout_and_ignores_the_header(self):
        from PySide6.QtWidgets import QFormLayout, QGroupBox, QSpinBox

        from meridiana.ui.style import Group
        plain = Group("Ferma", collapsible=False)
        form = QFormLayout(plain)
        form.addRow("Campo", QSpinBox())
        self.area.widget().layout().insertWidget(2, plain)
        self.app.processEvents()
        self.assertIs(QGroupBox.layout(plain), form)
        self.assertIsNone(plain.body())
        height = plain.height()
        self.click_header(plain)
        self.app.processEvents()
        self.assertEqual(plain.height(), height)


class EveryGroupHasItsHelp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look()

    def groups_without_help(self, root) -> list:
        from meridiana.ui.help_box import HelpButton
        from meridiana.ui.style import Group
        return [g.title() for g in root.findChildren(Group)
                if not [b for b in g.children() if isinstance(b, HelpButton)]]

    def test_the_properties_pages(self):
        from _fixtures import capannone

        from meridiana import model
        from meridiana.ui.properties import Properties
        p = capannone()
        p.exclusions.append(model.ExclusionItem(id="e1", ring=[[10, 9], [11.5, 9], [11.5, 10.5], [10, 10.5]],
                                                kind="skylight", building="b1"))
        props = Properties()
        self.addCleanup(_setup.dispose, props)
        props.resize(380, 1000)
        props.show()
        sf = p.subfields[0]
        for where, show in (("site", lambda: props.show_site(p, False)),
                            ("building", lambda: props.show_building(p.buildings[0])),
                            ("subfield", lambda: props.show_subfield(p, sf, p.fill(sf))),
                            ("exclusion", lambda: props.show_exclusion(p.exclusions[0]))):
            show()
            self.app.processEvents()
            with self.subTest(where):
                self.assertEqual(self.groups_without_help(props.widget()), [])

    def test_the_plant_inspector(self):
        from PySide6.QtGui import QAction

        from meridiana.ui.plant_page import PlantInspector
        actions = {key: QAction(key) for key in
                   ("inverter_catalog", "inverter_auto", "strings_auto", "strings_manual", "strings_clear")}
        panel = PlantInspector(actions)
        self.addCleanup(lambda: _setup.dispose(panel.side or panel))
        self.assertEqual(self.groups_without_help(panel), [])
        from meridiana.ui.help_box import HelpButton
        self.assertEqual(sorted(b.hid for b in panel.findChildren(HelpButton)),
                         ["plant.conditions", "plant.string", "plant.strings", "plant.subfield"])
        # the inverters have no group of their own inside the section called Inverter (R343): its header has their «?»
        from meridiana.ui.plant_page import PlantSide
        side = PlantSide(panel, actions, lambda: None)
        self.assertEqual(side.sections["inverter"].property("help"), "plant.inverters")


class InputsGridAndChosenString(unittest.TestCase):
    """The inputs of the inverter shown as cards in two columns (R298, study 23, B), the string chosen as a group at
    the top of the column with its bars and its rows parted by lines, the view menu beside the «?»."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look()

    def setUp(self):
        from PySide6.QtGui import QAction

        from meridiana.ui.plant_page import PlantInspector
        actions = {key: QAction(key) for key in
                   ("inverter_catalog", "inverter_auto", "strings_auto", "strings_manual", "strings_clear")}
        self.panel = PlantInspector(actions)
        self.addCleanup(_setup.dispose, self.panel)
        self.project, self.plant = plant_of([
            {"inverter": 1, "mppt": 1, "modules": [f"s1/0:{s}" for s in range(8)]},
            {"inverter": 1, "mppt": 1, "modules": [f"s1/1:{s}" for s in range(8)]},
            {"inverter": 1, "mppt": 2, "modules": [f"s1/2:{s}" for s in range(5)]},
        ])
        self.panel.show_plant(self.project, self.plant, chosen=0)
        self.panel.resize(380, 1100)
        self.panel.show()
        for _ in range(3):
            self.app.processEvents()

    def test_one_card_per_input_with_its_strings_its_mark_and_its_plus(self):
        grid = self.panel.list
        self.assertEqual(self.panel.view, "cards")
        self.assertEqual(sorted(grid.input_heads), [(1, 1), (1, 2)])
        first, second = grid.input_heads[(1, 1)], grid.input_heads[(1, 2)]
        slot1, slot2 = self.plant.inputs[(1, 1)], self.plant.inputs[(1, 2)]
        self.assertIn("MPPT 1", first.title.text())
        self.assertEqual(sorted(grid.rows), [0, 1, 2])
        self.assertEqual(grid.rows[0].count.text(), "8")
        self.assertEqual(grid.rows[2].count.text(), "5")
        self.assertEqual(slot2.level, "fail")                                          # 5 modules: under the window
        self.assertIn("out of limit", second.toolTip())
        self.assertEqual(first.add.isVisibleTo(first), len(slot1.strings) < slot1.allowed)   # «+» where it takes more
        self.assertTrue(grid.rows[0].selected)                                         # chosen=0
        self.assertFalse(grid.rows[1].selected)
        self.assertGreater(second.x(), first.x())                                      # two columns
        self.assertEqual(second.y(), first.y())
        self.assertLessEqual(self.panel.widget().width(), self.panel.viewport().width())
        chosen, targets = [], []
        self.panel.stringChosen.connect(chosen.append)
        grid.newString.connect(lambda *a: targets.append(a))
        grid.rows[1].clicked.emit(1)
        self.assertEqual(chosen, [1])
        self.assertTrue(grid.rows[1].selected)
        if second.add.isVisibleTo(second):
            second.add.click()
            self.assertEqual(targets, [(1, 2)])

    def test_the_string_chosen_is_a_group_at_the_top_with_bars_and_rows_parted_by_lines(self):
        from PySide6.QtWidgets import QFrame, QLabel

        from meridiana.i18n import number
        panel = self.panel
        g = panel.string_group
        self.assertFalse(g.isHidden())
        self.assertIn("1.1.1", g.identity.text())
        self.assertIn("MPPT 1", g.identity.text())
        self.assertIn("8 modules", g.detail.text())
        plan = self.plant.inputs[(1, 1)].plan
        self.assertEqual(g.bars["uoc"].text, f"{number(plan.uoc_max, 0)} / {number(plan.v_limit, 0)} V")
        self.assertTrue(g.bars["umpp"].isVisibleTo(g))
        labels = [w for w in g.row_widgets if isinstance(w, QLabel)]
        lines = [w for w in g.row_widgets if isinstance(w, QFrame) and not isinstance(w, QLabel)]
        self.assertGreaterEqual(len(labels), 3)
        self.assertEqual(len(lines), len(labels) - 1)                                  # a thin line between rows
        self.assertTrue(any("Uoc" in w.text() for w in labels))
        self.assertLess(g.y(), panel.inverters_group.y())                              # at the top of the column
        asked = []
        g.deleteAsked.connect(asked.append)
        g.delete.click()
        self.assertEqual(asked, [0])
        panel.show_string(self.plant, -1)
        self.assertTrue(g.isHidden())

    def test_the_state_of_the_string_chosen_is_the_windows_symbol_not_a_character(self):
        """R330: the traffic light of the string and the marks of its rows are the flat symbols, a picture in the rich
        text, never ✔ ⚠ ✘ in a font (the window's symbols are the only signs of a status)."""
        from PySide6.QtWidgets import QLabel
        g = self.panel.string_group
        self.assertIn("<img", g.identity.text())
        rows = [w for w in g.row_widgets if isinstance(w, QLabel)]
        self.assertTrue(rows)
        for label in [g.identity, *rows]:
            self.assertFalse(set(label.text()) & set("✔⚠✘✕"), label.text())
        self.assertTrue(any(w.text().startswith("<img") for w in rows))

    def test_the_view_menu_beside_the_help_swaps_the_cards_for_the_diagram_and_says_so(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from meridiana.ui.help_box import HelpButton
        panel = self.panel
        said = []
        panel.viewChanged.connect(said.append)
        panel.view_actions["diagram"].trigger()
        self.assertEqual(said, ["diagram"])
        self.assertEqual(panel.view, "diagram")
        d = panel.list.front()
        self.assertEqual(sorted(d.rows), [0, 1, 2])
        self.assertEqual(d.current(), 0)
        chosen = []
        panel.stringChosen.connect(chosen.append)
        QTest.mouseClick(d, Qt.MouseButton.LeftButton, pos=d.rows[1].center().toPoint())
        self.assertEqual(chosen, [1])
        q = panel.strings_group.findChildren(HelpButton)[0]
        self.assertLess(panel.view_button.x() + panel.view_button.width(), q.x())      # at the left of the «?»
        self.assertLessEqual(abs(panel.view_button.geometry().center().y() - q.geometry().center().y()), 4)
        panel.set_view("cards")
        self.assertEqual(panel.view, "cards")
        self.assertEqual(panel.list.current(), 1)                                      # the choice carried over


if __name__ == "__main__":
    unittest.main()
