"""R277 (study 22, 3.1-3.3; Daniel, 30/10/2026): the first phase is the Modelling, the model alone; the modules are
laid in the Plant, before the inverters and the storage. The tools of the plan open the phase whose bar has them and
the Plant's plan draws with them; the Plant's right panel is one page of three sections, Panels (the selected
sub-field's card, the Properties lent), Inverter, Storage, the command used opening its own; a planned command comes
into its bar once the window has its action. PySide6 and a display (offscreen will do)."""

import unittest

import _setup
from _fixtures import capannone

from meridiana import config, phases

setUpModule = _setup.keep_global_state


class ModellingAndPlant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone(), config.Config(background="none", theme="light"), size=(1400, 960))
        self.sid = self.win.project.subfields[0].id

    def test_the_layout_tools_open_the_plant_and_draw_there_the_outlines_go_back_to_the_modelling(self):
        win = self.win
        self.assertEqual(win.phase(), "model")
        self.assertNotIn("tool_subfield", win.bars["model"].buttons())
        self.assertEqual([c for c in win.bars["plant"].buttons() if c != "canopy_layout"][:5],   # R281 in between
                         ["tool_subfield", "tool_row", "layout_east_west", "fill", "empty"])
        win.commands["tool_subfield"].trigger()                 # S in the Modelling
        self.assertEqual(win.phase(), "plant")
        self.assertIs(win.plan.parentWidget(), win.plant_page.host)
        self.assertEqual(win.plan.tool, "subfield")
        self.assertFalse(win.plan.strings_mode)                 # the clicks draw, they do not choose strings
        win.commands["tool_select"].trigger()                   # Select stays in the Plant
        self.assertEqual((win.phase(), win.plant_side.current), ("plant", "panels"))
        self.assertFalse(win.plan.strings_mode)                 # Panels open: a click selects modules and rows
        win.plant_side.open("inverter", ms=0)
        self.assertTrue(win.plan.strings_mode)                  # Inverter open: a click chooses a string
        win.plant_side.open("storage", ms=0)
        self.assertTrue(win.plan.strings_mode)
        win.commands["delete"].trigger()                        # Del with the strings: a string or nothing
        self.assertEqual(len(win.project.subfields), 1)
        win.commands["layout_east_west"].trigger()
        self.assertEqual((win.phase(), win.plan.tool, win.plan.strings_mode), ("plant", "east_west", False))
        win.commands["tool_building"].trigger()                 # an outline: the Modelling, the plan at home
        self.assertEqual((win.phase(), win.plan.tool), ("model", "building"))
        self.assertEqual(win.split.indexOf(win.plan), 0)
        win.commands["tool_row"].trigger()
        self.assertEqual(win.phase(), "plant")
        win.show_phase("model")                                 # Ctrl+1 with Row: back to Select, Row is the Plant's
        self.assertEqual(win.plan.tool, "select")
        self.assertTrue(win.commands["tool_select"].isChecked())
        win.commands["tool_measure"].trigger()                  # measuring stays where the plan is
        self.assertEqual(win.phase(), "model")

    def test_the_plant_panel_has_panels_inverter_storage_and_the_sub_field_card(self):
        win = self.win
        side = win.plant_side
        win.show_phase("plant")
        self.assertIs(win.inspector.currentWidget(), side)
        self.assertEqual(win.docks[1].windowTitle(), "Plant")
        self.assertEqual([s.title() for s in side.sections.values()], ["Panels", "Inverter", "Storage"])
        self.assertIs(side.inverters, win.plant_inspector)
        # the Properties lent to Panels: the selected sub-field's card
        self.assertIs(side.properties, win.props)
        self.assertEqual(win.inspector.indexOf(win.props), -1)
        win._select("subfield", self.sid)
        _setup.turn_events(self.app, 50)
        self.assertEqual(side.current, "panels")
        self.assertTrue(side.props_holder.isVisibleTo(side))
        self.assertFalse(side.panels_hint.isVisibleTo(side))
        self.assertEqual((win.props.kind, win.props.oid), ("subfield", self.sid))
        # one section open at a time; the command used opens its own
        side.open("storage", ms=0)
        self.assertEqual(side.current, "storage")
        self.assertEqual([s.expanded for s in side.sections.values()], [False, False, True])
        win.commands["tool_row"].trigger()
        self.assertEqual(side.current, "panels")
        self.assertEqual(side.command_section["inverter_catalog"], "inverter")
        self.assertEqual(side.command_section["strings_auto"], "inverter")
        self.assertEqual(side.command_section["battery_catalog"], "storage")
        self.assertEqual(side.command_section["fill"], "panels")
        self.assertEqual(side.storage_text.text(), "No battery")
        # «Configure»'s dialog closed: the storage's line read again as its section opens
        win.project.economics.update({"battery": {"manufacturer": "Acme", "model": "B10"}, "battery_units": 2,
                                      "storage_coupling": "dc"})
        side.open("storage", ms=0)
        self.assertEqual(side.storage_text.text(), "2 × Acme B10\nDC: hybrid inverter")
        win._select("site", "")
        self.assertTrue(side.panels_hint.isVisibleTo(side))
        # back to the Modelling: the Properties at home again
        win.show_phase("model")
        self.assertIsNone(side.properties)
        self.assertIs(win.inspector.currentWidget(), win.props)
        self.assertEqual(win.docks[1].windowTitle(), "Properties")

    def test_a_planned_command_comes_into_its_bar_once_the_action_exists(self):
        from PySide6.QtGui import QAction

        from meridiana.ui.phasebar import PhaseBar
        action = QAction("On canopy", self.win)                 # the canopy's task brings it (R281)
        bar = PhaseBar(phases.by_id("plant"), {**self.win.commands, "canopy_layout": action})
        without = PhaseBar(phases.by_id("plant"), {k: a for k, a in self.win.commands.items() if k != "canopy_layout"})
        self.addCleanup(without.deleteLater)
        self.assertNotIn("canopy_layout", without.buttons())
        self.addCleanup(bar.deleteLater)
        self.assertEqual(list(bar.buttons())[:6],
                         ["tool_subfield", "tool_row", "layout_east_west", "canopy_layout", "fill", "empty"])
        self.assertEqual(bar.groups[0].title.text(), "Panels")
        model = PhaseBar(phases.by_id("model"), self.win.commands)
        self.addCleanup(model.deleteLater)
        # Obstacles: the exclusions now, the 3D objects when they come
        self.assertEqual([g.title.text() for g in model.groups], ["Edit", "Draw", "Obstacles", "Precision"])


if __name__ == "__main__":
    unittest.main()
