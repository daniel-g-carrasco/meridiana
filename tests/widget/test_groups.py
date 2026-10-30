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
                   ("inverter_catalog", "inverter_auto", "strings_auto", "strings_complete", "strings_clear")}
        panel = PlantInspector(actions)
        self.addCleanup(_setup.dispose, panel)
        self.assertEqual(self.groups_without_help(panel), [])
        from meridiana.ui.help_box import HelpButton
        self.assertEqual(sorted(b.hid for b in panel.findChildren(HelpButton)),
                         ["plant.inverters", "plant.overview", "plant.proposal", "plant.string", "plant.strings",
                          "plant.subfield", "plant.working"])


class InputsTable(unittest.TestCase):
    """One row per input of the working inverter, with the figures of the plan of each input (R286)."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look()

    def setUp(self):
        from PySide6.QtGui import QAction

        from meridiana.ui.plant_page import PlantInspector
        actions = {key: QAction(key) for key in
                   ("inverter_catalog", "inverter_auto", "strings_auto", "strings_complete", "strings_clear")}
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

    def test_one_row_per_input_with_the_figures_of_its_plan(self):
        from meridiana.i18n import number
        table = self.panel.inputs
        self.assertEqual(table.topLevelItemCount(), 2)
        self.assertEqual(sorted(table.rows), [(1, 1), (1, 2)])
        first, second = table.rows[(1, 1)], table.rows[(1, 2)]
        slot1, slot2 = self.plant.inputs[(1, 1)], self.plant.inputs[(1, 2)]
        self.assertEqual(first.text(0), "MPPT 1")
        self.assertEqual(first.text(1), f"2/{slot1.allowed}")
        self.assertEqual(first.text(2), "8")
        self.assertEqual(second.text(1), f"1/{slot2.allowed}")
        self.assertEqual(second.text(2), "5")
        plan = slot1.plan
        self.assertEqual(first.text(3), f"{number(plan.uoc_max, 0)}/{number(plan.v_limit, 0)}")
        self.assertEqual(first.text(4), f"{number(plan.vmp_hot, 0)}-{number(plan.vmp_cold, 0)}")
        self.assertRegex(first.text(5), r"^\d+([.,]\d+)?/\d+([.,]\d+)?$")           # Isc of the input's limit
        self.assertEqual(first.data(6, 0x0100), slot1.level)                           # UserRole: the state
        self.assertEqual(second.data(6, 0x0100), slot2.level)
        self.assertEqual(slot2.level, "fail")                                          # 5 modules: under the window
        self.assertFalse(second.icon(6).isNull())
        self.assertIn("out of limit", second.toolTip(6))
        # as tall as its header and rows, no scroll bar of its own, inside the group's width
        self.assertGreaterEqual(table.height(), table.header().height() + 2 * table.visualItemRect(first).height())
        self.assertLessEqual(table.header().length(), table.viewport().width())

    def test_the_string_chosen_is_in_three_blocks(self):
        panel = self.panel
        self.assertFalse(panel.string_group.isHidden())
        self.assertIn("1.1.1", panel.string_identity.text())
        self.assertIn("MPPT 1", panel.string_identity.text())
        self.assertIn("8 modules", panel.string_identity.text())
        electrical = panel.string_blocks["electrical"].text()
        self.assertIn("Uoc", electrical)
        self.assertIn("Umpp", electrical)
        self.assertGreaterEqual(electrical.count("<br>"), 2, "one figure per line")
        self.assertNotIn("Uoc", panel.string_checks.text().split("<br>")[0].split(":")[0])

    def test_a_narrow_panel_drops_the_rightmost_figures_instead_of_running_past_the_edge(self):
        table = self.panel.inputs
        self.panel.resize(240, 1100)
        for _ in range(3):
            self.app.processEvents()
        header = table.header()
        self.assertLessEqual(header.length(), table.viewport().width())
        self.assertTrue(header.isSectionHidden(5))
        self.assertFalse(header.isSectionHidden(0))
        self.assertFalse(header.isSectionHidden(6))
