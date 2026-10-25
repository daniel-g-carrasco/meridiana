"""Panels and commands of the window (study 12, N2-N5, V3): Lucide's icons in the theme's colour, the project's tree
with names by kind, icons and the selection of the views, the right panel that follows the tab, the quick measure of
the selection in the status bar; the context menus of the plan, the 3D view and the tree, duplicate and rename as
edits like any other. PySide6 and a display (offscreen will do)."""

import unittest

import _setup
from _fixtures import capannone

from meridiana import config, model

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Panels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        p = capannone()
        b = p.buildings[0].id
        for i, kind in enumerate(("skylight", "vent", "skylight")):
            p.exclusions.append(model.ExclusionItem(id=p.new_id("e"), ring=[[5 + 3 * i, 12], [6 + 3 * i, 12],
                                                                             [6 + 3 * i, 13], [5 + 3 * i, 13]],
                                                    kind=kind, building=b))
        _setup.window(self, p, config.Config(background="none", theme="light"))
        self.sid = self.win.project.subfields[0].id

    def test_the_icons_the_tree_the_right_panel_and_the_quick_measure_follow_the_theme_the_selection_and_the_tab(self):
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QPalette
        win = self.win

        # the icons take the colour of the theme: the same icon, drawn again in the new colour
        def ink():
            img = win.tool_actions["building"].icon().pixmap(QSize(48, 48)).toImage()
            seen = [img.pixelColor(x, y) for x in range(48) for y in range(48) if img.pixelColor(x, y).alpha() == 255]
            return seen[0].name() if seen else ""
        self.assertEqual(ink(), self.app.palette().color(QPalette.ColorRole.ButtonText).name())
        light = ink()
        win._appearance("dark", "bronze", "meridiana")
        self.assertNotEqual(ink(), light)
        win._appearance("light", "bronze", "meridiana")
        # the tree names the exclusions by kind and follows the selection, also when it is made again
        root = win.tree.topLevelItem(0)
        names = [root.child(2).child(i).text(0) for i in range(root.child(2).childCount())]
        self.assertEqual(names, ["Skylight 1", "Smoke vent (EFC) 1", "Skylight 2"])
        self.assertFalse(root.child(0).child(0).icon(0).isNull())      # the building's kind
        win._select("subfield", self.sid)
        self.assertEqual(win.tree.currentItem().data(0, 0x0100), ("subfield", self.sid))
        win._show_tree()
        self.assertEqual(win.tree.currentItem().data(0, 0x0100), ("subfield", self.sid))
        # the quick measure of the selection in the status bar
        r = win.results[self.sid]
        text = win.measure_label.text()
        self.assertIn(f"{r.count} modules", text)
        self.assertIn("kWp", text)
        self.assertIn("area 684.0 m²", text)                # 38 x 18 m
        win._select("site", "")
        self.assertEqual(win.measure_label.text(), "")
        # the right panel follows the tab
        dock = win.docks[1]
        self.assertIs(win.inspector.currentWidget(), win.props)
        win.show_phase("production")                       # what is typed in the phase (the drafts, 24/10/2026)
        self.assertIs(win.inspector.currentWidget(), win.energy_page.side)
        self.assertEqual(dock.windowTitle(), "Data")
        self.assertEqual(win.inspector.results.variant.count(), len(win.project.variants))
        win.show_phase("model")
        self.assertIs(win.inspector.currentWidget(), win.props)
        self.assertEqual(dock.windowTitle(), "Properties")

    def test_the_context_menus_offer_what_the_object_allows_and_duplicate_and_rename_are_edits(self):
        from meridiana.ui.plan import to_scene
        win = self.win
        texts = [e[0] for e in win.context_actions("subfield", self.sid) if e]
        for wanted in ("Properties", "Frame it", "Lay again", "Take the modules out", "Rename…", "Duplicate",
                       "Square the corners", "Delete"):
            self.assertIn(wanted, texts)
        self.assertIn("Take this module out", [e[0] for e in win.context_actions("subfield", self.sid, "r1c1") if e])
        eid = win.project.exclusions[0].id
        self.assertNotIn("Rename…", [e[0] for e in win.context_actions("exclusion", eid) if e])
        self.assertEqual([e[0] for e in win.context_actions("site", "") if e], ["Properties", "Frame it"])
        # a right click on the plan selects and opens the menu
        plan = win.plan
        plan.fit()
        self.app.processEvents()
        win._plan_menu(plan.mapFromScene(to_scene(0.4, 19.6)))        # the roof, by its corner
        self.assertEqual(win.selection, ("building", win.project.buildings[0].id))
        self.assertIn("Duplicate", [a.text() for a in win.context_menu.actions()])
        win.context_menu.close()
        # duplicate and rename are edits like any other: selected, undone
        steps = win.undo.index()
        win._duplicate("subfield", self.sid)
        self.assertEqual(len(win.project.subfields), 2)
        copy = win.project.subfields[1]
        self.assertEqual(win.selection, ("subfield", copy.id))
        win._rename("subfield", copy.id, "Nord")
        self.assertEqual(win.project.subfields[1].name, "Nord")
        self.assertEqual(win.undo.index(), steps + 2)
        win.undo.undo()
        win.undo.undo()
        self.assertEqual(len(win.project.subfields), 1)


if __name__ == "__main__":
    unittest.main()
