"""The commands of the bars and of the plan asked on 02/11/2026: Select, Move and Rotate in the Plant (R295); the commands
of the views while a tool is in hand (R301); deleting strings and inverters from their modules (R299); the sweep of
modules (R300); the buttons with a menu (R306). Through the window, with the events told to the plan's viewport (the real
pointer stays where it is). PySide6 and a display (offscreen will do)."""

import unittest

import _setup
from _fixtures import capannone, inverter_record
from _setup import wait_until

from meridiana import config

setUpModule = _setup.keep_global_state


class WindowCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone(), config.Config(background="none", theme="light"), size=(1400, 960))
        self.plan = self.win.plan

    def scene_point(self, x, y):
        from PySide6.QtCore import QPointF

        from meridiana.ui.plan import to_scene
        return QPointF(self.plan.mapFromScene(to_scene(x, y)))

    def send(self, kind, pos, button=None, buttons=None, mods=None):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QMouseEvent
        event = QMouseEvent(kind, pos, self.plan.viewport().mapToGlobal(pos), button or Qt.MouseButton.NoButton,
                            buttons if buttons is not None else Qt.MouseButton.NoButton,
                            mods or Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(self.plan.viewport(), event)

    def hover(self, x, y):
        from PySide6.QtCore import QEvent
        self.send(QEvent.Type.MouseMove, self.scene_point(x, y))

    def click(self, x, y, mods=None):
        from PySide6.QtCore import QEvent, Qt
        pos = self.scene_point(x, y)
        self.send(QEvent.Type.MouseMove, pos)
        left = Qt.MouseButton.LeftButton
        self.send(QEvent.Type.MouseButtonPress, pos, left, left, mods)
        self.send(QEvent.Type.MouseButtonRelease, pos, left, Qt.MouseButton.NoButton, mods)

    def module_centre(self, sfid=None, index=0):
        from PySide6.QtCore import QPointF

        from meridiana.ui.plan import from_scene
        sfid = sfid or self.win.project.subfields[0].id
        keys, quads = self.plan.module_corners[sfid]
        c = quads[index].mean(axis=0)
        return sfid, keys[index], from_scene(QPointF(float(c[0]), float(c[1])))


class EditInThePlant(WindowCase):
    """R295: «come mai in fase impianto non ci sono i comandi per selezionare / spostare / ruotare?»"""

    def test_select_move_and_rotate_are_on_the_bar_of_the_plant_and_stay_there(self):
        win = self.win
        win.show_phase("plant")
        buttons = win.bars["plant"].buttons()
        for cid, tool in (("tool_select", "select"), ("tool_move", "move"), ("tool_rotate", "move")):
            self.assertIn(cid, buttons)
            win.commands[cid].trigger()
            self.assertEqual(win.phase(), "plant", cid)
            self.assertEqual(self.plan.tool, tool, cid)
        self.assertTrue(win.commands["tool_rotate"].isChecked())
        win.show_phase("model")                                 # Move stays Move going back to the Modelling
        self.assertEqual(self.plan.tool, "move")

    def test_a_click_in_move_takes_the_row_with_shift_the_module_and_the_module_moves_with_its_keys(self):
        from PySide6.QtCore import Qt
        win = self.win
        win.show_phase("plant")
        win.commands["tool_move"].trigger()
        sfid, key, (x, y) = self.module_centre()
        rid = self.plan.rid_of(sfid, key)
        self.click(x, y)
        self.assertEqual(self.plan.selection, ("row", f"{sfid}/{rid}"))
        self.assertTrue(self.plan._movable())
        win._set_tool("select")
        win._select("site", "")
        win.commands["tool_move"].trigger()
        self.click(x, y, Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(self.plan._move_thing(), ("module", f"{sfid}/{key}"))
        self.assertTrue(self.plan._movable())
        self.assertFalse(win.project.subfields[0].manual)
        # a small move inside the sub-field: the base point, then where it goes; the module alone, its key kept
        moved = []
        self.plan.transformRequested.connect(lambda *a: moved.append(a))
        self.click(x, y)
        self.click(x, y - 0.01)
        self.assertEqual([m[:2] for m in moved], [("module", f"{sfid}/{key}")])
        sf = win.project.subfields[0]
        self.assertTrue(sf.manual)
        self.assertTrue(any(key in r.keys and r.count == 1 for r in sf.hand_rows()))
        win.commands["undo"].trigger()                          # one step
        self.assertFalse(win.project.subfields[0].manual)

    def test_with_rotate_a_click_on_a_module_takes_its_sub_field_and_a_building_is_not_moved_here(self):
        win = self.win
        win.show_phase("model")
        win._select("building", win.project.buildings[0].id)
        win.show_phase("plant")
        win.commands["tool_move"].trigger()
        self.assertFalse(self.plan._movable())                  # chosen in the Modelling: not what moves here
        win.commands["tool_rotate"].trigger()
        sfid, _key, (x, y) = self.module_centre()
        self.click(x, y)
        self.assertEqual(self.plan.selection, ("subfield", sfid))
        self.assertEqual(self.plan._gesture().mode, "rotate")


class ViewCommandsDuringATool(WindowCase):
    """R301: «se si selezionano alcuni tasti / funzioni di controllo, tipo l'allinea ad un lato, mentre si è selezionata
    una delle funzioni di modellazione, non la lascia utilizzare». Why: with a drawing tool in hand nothing can be
    selected (a click draws), and Align wanted an outline selected first; then Esc went to the tool, and with a string
    being drawn the sides did not light."""

    TOOLS = ("tool_building", "tool_pitch", "tool_ridge", "tool_exclusion", "tool_measure", "tool_move", "tool_rotate")
    COMMANDS = ("view_align", "view_north", "zoom_in", "zoom_out", "fit", "view_plan", "view_3d", "view_both", "snaps",
                "ortho", "strings")

    def side_middle(self):
        ring = self.win.project.buildings[0].footprint
        (ax, ay), (bx, by) = ring[1], ring[2]
        return (ax + bx) / 2, (ay + by) / 2

    def test_every_command_of_the_views_leaves_every_tool_as_it_was_even_with_a_drawing_begun(self):
        win, plan = self.win, self.plan
        for cid in self.TOOLS:
            for command in self.COMMANDS:
                win._set_tool("select")
                win._select("site", "")
                win.commands[cid].trigger()
                tool = plan.tool
                if tool in ("building", "exclusion", "pitch"):
                    self.click(-50.0, -50.0)
                chain = list(plan.chain)
                win.commands[command].trigger()
                self.assertEqual(plan.tool, tool, (cid, command))
                self.assertEqual(plan.chain, chain, (cid, command))
                self.assertTrue(win.commands[cid].isChecked(), (cid, command))
                self.assertEqual(win.phase(), "model", (cid, command))
                plan._end_pick()
                win._view_mode("both")

    def test_align_with_a_drawing_begun_and_nothing_selected_takes_a_side_of_any_outline(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        win, plan = self.win, self.plan
        win._select("site", "")
        win.commands["tool_building"].trigger()
        self.click(-50.0, -50.0)
        self.assertEqual(len(plan.chain), 1)
        button = plan.viewbar.buttons[win.commands["view_align"]]
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)     # the button itself, on the bar in the view
        self.assertIsNotNone(plan.edge_pick)
        x, y = self.side_middle()
        self.click(x, y)
        self.assertIsNone(plan.edge_pick)
        self.assertAlmostEqual(abs(plan.view_rotation()) % 90.0, 0.0)
        self.assertAlmostEqual(abs(plan.view_rotation()), 90.0)
        self.assertEqual(plan.tool, "building")                 # the tool and its corner as they were
        self.assertEqual(len(plan.chain), 1)
        self.assertEqual(plan.cursor().shape(), Qt.CursorShape.CrossCursor)
        self.click(-40.0, -50.0)                                # and it goes on drawing
        self.assertEqual(len(plan.chain), 2)

    def test_esc_gives_up_the_side_and_nothing_else(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        win, plan = self.win, self.plan
        for cid, tool in (("tool_building", "building"), ("tool_move", "move")):
            win._select("building", win.project.buildings[0].id)
            win.commands[cid].trigger()
            if tool == "building":
                self.click(-50.0, -50.0)
            chain = list(plan.chain)
            win.commands["view_align"].trigger()
            self.assertIsNotNone(plan.edge_pick)
            QTest.keyClick(plan, Qt.Key.Key_Escape)
            self.assertIsNone(plan.edge_pick)
            self.assertEqual((plan.tool, plan.chain), (tool, chain))
            plan.cancel_outline()

    def test_a_double_click_on_the_side_closes_no_outline(self):
        from PySide6.QtCore import QEvent, Qt
        win, plan = self.win, self.plan
        win._select("building", win.project.buildings[0].id)
        win.commands["tool_building"].trigger()
        for x, y in ((-50.0, -50.0), (-40.0, -50.0), (-40.0, -40.0)):
            self.click(x, y)
        win.commands["view_align"].trigger()
        x, y = self.side_middle()
        self.click(x, y)
        pos = self.scene_point(x, y)
        left = Qt.MouseButton.LeftButton
        self.send(QEvent.Type.MouseButtonDblClick, pos, left, left)
        self.assertEqual(len(plan.chain), 3)

    def test_with_a_string_being_drawn_the_side_lights_and_the_click_aligns(self):
        win, plan = self.win, self.plan
        win.show_phase("plant")
        win._select("subfield", win.project.subfields[0].id)
        sfid, key, _centre = self.module_centre()
        plan.set_strings_mode(True)
        plan.start_draft([(sfid, key)])
        ring = win.project.subfields[0].ring
        (ax, ay), (bx, by) = ring[0], ring[1]
        win.commands["view_align"].trigger()
        self.hover((ax + bx) / 2, (ay + by) / 2)
        self.assertEqual(plan.edge_hover, 0)
        self.click((ax + bx) / 2, (ay + by) / 2)
        self.assertIsNone(plan.edge_pick)
        self.assertEqual(plan.draft, [(sfid, key)])             # the string goes on


class StringsDeletedFromTheirModules(WindowCase):
    """R299: «elimina stringa [...] (durante selezione evidenzia tutti i moduli della stringa in modo decente), e magari un
    elimina inverter + stringhe [...] e un elimina inverter»."""

    def setUp(self):
        super().setUp()
        win = self.win
        win._add_inverter(inverter_record(), "Add")
        win._inverter_count(0, 3)
        keys = self.plan.module_corners[win.project.subfields[0].id][0]
        sfid = win.project.subfields[0].id
        self.parts = [keys[0:10], keys[10:20], keys[20:30], keys[30:40]]
        self.sfid = sfid
        # inverter 1: two strings; inverter 2: one; inverter 3: one
        where = [(1, 1), (1, 2), (2, 1), (3, 1)]
        win._strings_put("Strings", [{"inverter": u, "mppt": m, "modules": [f"{sfid}/{k}" for k in part]}
                                     for (u, m), part in zip(where, self.parts, strict=True)])
        win.show_phase("plant")
        self.wired()

    def wired(self):
        win = self.win
        expected = len(win.project.energy["strings"]["runs"])
        self.assertTrue(wait_until(self.app, lambda: not win.plant_pending() and win.plant_state is not None
                                   and len(win.plan.wiring.strings) == expected, 60))

    def centre_of(self, key):
        from PySide6.QtCore import QPointF

        from meridiana.ui.plan import from_scene
        keys, quads = self.plan.module_corners[self.sfid]
        c = quads[keys.index(key)].mean(axis=0)
        return from_scene(QPointF(float(c[0]), float(c[1])))

    def test_delete_string_lights_the_whole_string_and_a_click_deletes_it_with_one_undo_esc_leaves(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        win, plan = self.win, self.plan
        win.commands["tool_erase_string"].trigger()
        self.assertEqual(win.phase(), "plant")
        self.assertEqual(plan.tool, "erase_string")
        self.assertFalse(plan.strings_mode)
        x, y = self.centre_of(self.parts[1][3])
        self.hover(x, y)
        self.assertEqual(sorted(k for _s, k in plan.erase_lit), sorted(self.parts[1]))
        self.assertIsNotNone(plan.erase_item)
        self.hover(*self.centre_of(self.parts[0][0]))           # another string: the light moves
        self.assertEqual(sorted(k for _s, k in plan.erase_lit), sorted(self.parts[0]))
        self.hover(x, y)
        self.click(x, y)
        runs = win.project.energy["strings"]["runs"]
        self.assertEqual(len(runs), 3)
        self.assertNotIn(f"{self.sfid}/{self.parts[1][0]}", [m for r in runs for m in r["modules"]])
        self.assertEqual(len(win.project.subfields[0].removed), 0)      # the modules stay laid
        self.wired()
        self.assertEqual(plan.erase_lit, [])                    # what it lit is gone, the tool stays
        self.assertEqual(plan.tool, "erase_string")
        win.commands["undo"].trigger()                          # one undo for the click
        self.assertEqual(len(win.project.energy["strings"]["runs"]), 4)
        self.wired()
        QTest.keyClick(plan, Qt.Key.Key_Escape)
        self.assertEqual(plan.tool, "select")
        self.assertTrue(win.tool_actions["select"].isChecked())

    def test_a_module_in_no_string_lights_nothing_and_says_so(self):
        win, plan = self.win, self.plan
        keys = plan.module_corners[self.sfid][0]
        win.commands["tool_erase_string"].trigger()
        x, y = self.centre_of(keys[-1])
        self.hover(x, y)
        self.assertEqual(plan.erase_lit, [])
        self.click(x, y)
        self.assertEqual(len(win.project.energy["strings"]["runs"]), 4)
        self.assertIn("no string", win.hint.text())

    def test_inverter_and_strings_goes_with_all_its_strings_and_the_next_inverters_move_up(self):
        win, plan = self.win, self.plan
        win.commands["tool_erase_inverter_strings"].trigger()
        x, y = self.centre_of(self.parts[0][0])
        self.hover(x, y)
        self.assertEqual(sorted(k for _s, k in plan.erase_lit), sorted(self.parts[0] + self.parts[1]))
        self.click(x, y)
        energy = win.project.energy
        self.assertEqual(energy["inverters"][0]["count"], 2)
        self.assertEqual([(r["inverter"], len(r["modules"])) for r in energy["strings"]["runs"]], [(1, 10), (2, 10)])
        win.commands["undo"].trigger()
        self.assertEqual(win.project.energy["inverters"][0]["count"], 3)
        self.assertEqual(len(win.project.energy["strings"]["runs"]), 4)

    def test_inverter_alone_leaves_its_strings_on_no_inverter_and_says_so(self):
        win = self.win
        said = []
        original = win.tell
        win.tell = lambda text, *a: (said.append(text), original(text, *a))
        win.commands["tool_erase_inverter"].trigger()
        x, y = self.centre_of(self.parts[2][0])
        self.hover(x, y)
        self.assertEqual(sorted(k for _s, k in self.plan.erase_lit), sorted(self.parts[2]))
        self.click(x, y)
        energy = win.project.energy
        self.assertEqual(energy["inverters"][0]["count"], 2)
        self.assertEqual([r["inverter"] for r in energy["strings"]["runs"]], [1, 1, 0, 2])
        self.assertEqual(len(energy["strings"]["runs"][2]["modules"]), 10)
        self.assertTrue(any("on no inverter" in s for s in said), said)
        self.wired()
        self.assertEqual(sum(1 for s in self.plan.wiring.strings if not s.inverter), 1)
        self.click(x, y)                                        # now on none: nothing to delete, it says why
        self.assertEqual(win.project.energy["inverters"][0]["count"], 2)
        self.assertIn("no inverter", win.hint.text())

    def test_the_commands_are_in_the_menu_of_one_button_with_start_again(self):
        win = self.win
        bar = win.bars["plant"]
        button = bar.button_of("tool_erase_inverter")
        self.assertIs(bar.button_of("strings_clear"), button)
        self.assertIs(bar.buttons()["tool_erase_string"], button)
        win.commands["tool_erase_inverter"].trigger()
        self.assertEqual(button.text(), "Delete inverter")
        self.assertTrue(button.isChecked())


class ButtonsWithAMenu(WindowCase):
    """R306: «molti dei comandi negli strumenti sopra possono essere raggruppati, un po' come succede in autocad»."""

    def menu_of(self, button, trigger, after=50):
        """What the menu of `button` shows when `trigger` opens it (the menu runs its own loop): its words, and it is
        closed again."""
        from PySide6.QtCore import QTimer
        seen = []

        def look():
            if button.commands.isVisible():
                seen.append([a.text() for a in button.commands.actions()])
                button.commands.grab().save(self.photo) if getattr(self, "photo", "") else None
            button.commands.close()
        QTimer.singleShot(after, look)
        trigger()
        self.app.processEvents()
        return seen

    def test_building_holds_the_templates_and_pitch_the_ridge_with_their_keys(self):
        from PySide6.QtGui import QKeySequence
        from meridiana.ui.phasebar import ToolMenuButton
        win = self.win
        bar = win.bars["model"]
        self.assertEqual(list(bar.buttons()), ["tool_select", "tool_move", "tool_rotate", "tool_building", "carport",
                                               "tool_pitch", "tool_exclusion", "object_3d", "tool_measure", "square",
                                               "rectangle"])
        building, pitch = bar.button_of("tool_building"), bar.button_of("tool_ridge")
        self.assertIsInstance(building, ToolMenuButton)
        self.assertIs(bar.button_of("building_template"), building)
        self.assertIs(pitch, bar.buttons()["tool_pitch"])
        self.assertIn(QKeySequence("C"), win.commands["tool_ridge"].shortcuts())      # the keys are as they were
        self.assertIn(QKeySequence("B"), win.commands["tool_building"].shortcuts())
        self.assertIn("(B)", building.toolTip())

    def test_the_arrow_and_the_long_press_open_the_menu_and_the_click_runs_the_one_on_the_button(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        win = self.win
        bar = win.bars["model"]
        win.show_phase("model")
        self.app.processEvents()
        button = bar.button_of("tool_pitch")
        self.assertIs(button.defaultAction(), win.commands["tool_pitch"])
        words = [win.commands["tool_pitch"].text(), win.commands["tool_ridge"].text()]
        arrow = button.arrow_rect().center()
        self.assertEqual(self.menu_of(button, lambda: QTest.mouseClick(button, Qt.MouseButton.LeftButton, pos=arrow)),
                         [words])
        self.assertNotEqual(win.plan.tool, "pitch")             # the arrow only opens the menu
        # held down over the icon: the menu after Qt's delay
        middle = QPoint(button.width() // 2 - button.ARROW, button.height() // 2)
        delay = button.style().styleHint(button.style().StyleHint.SH_ToolButton_PopupDelay)
        self.assertEqual(self.menu_of(button, lambda: (QTest.mousePress(button, Qt.MouseButton.LeftButton, pos=middle),
                                                       QTest.qWait(delay + 300)), after=delay + 100),
                         [words])
        QTest.mouseRelease(button, Qt.MouseButton.LeftButton, pos=middle)
        self.assertNotEqual(win.plan.tool, "pitch")
        # a click on the button: the command on it
        QTest.mouseClick(button, Qt.MouseButton.LeftButton, pos=middle)
        self.assertEqual(win.plan.tool, "pitch")
        self.assertTrue(button.isChecked())
        # the other one, from the menu or with its key, comes on the button with its word and its tooltip
        width = button.width()
        win.commands["tool_ridge"].trigger()
        self.assertEqual(win.plan.tool, "ridge")
        self.assertIs(button.defaultAction(), win.commands["tool_ridge"])
        self.assertEqual(button.text(), "Ridge")
        self.assertEqual(button.property("tool"), "tool_ridge")
        self.assertEqual(button.toolTip(), win.commands["tool_ridge"].toolTip())
        self.assertEqual(button.width(), width)                 # the bar does not move
        self.assertTrue(button.isChecked())
        win._set_tool("select")
        self.assertFalse(button.isChecked())
        QTest.mouseClick(button, Qt.MouseButton.LeftButton, pos=middle)
        self.assertEqual(win.plan.tool, "ridge")                # the last one used

    def test_a_command_gone_disabled_gives_way_so_that_the_button_still_opens(self):
        win = self.win
        button = win.bars["model"].button_of("tool_building")
        win.commands["building_template"].setEnabled(True)
        button.use("building_template")
        win.commands["building_template"].setEnabled(False)
        self.assertIs(button.defaultAction(), win.commands["tool_building"])
        self.assertTrue(button.isEnabled())
        win.commands["building_template"].setEnabled(True)

    def test_the_section_of_the_plant_follows_the_commands_in_the_menus_too(self):
        win = self.win
        win.show_phase("plant")
        win.plant_side.open("inverter", ms=0)
        win.commands["layout_east_west"].trigger()
        self.assertEqual(win.plant_side.current, "panels")


if __name__ == "__main__":
    unittest.main()
