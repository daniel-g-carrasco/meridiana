"""The commands of the bars and of the plan asked on 02/11/2026: Select, Move and Rotate in the Plant (R295); the commands
of the views while a tool is in hand (R301); deleting strings and inverters from their modules (R299); the sweep of
modules (R300); the buttons with a menu (R306). Through the window, with the events told to the plan's viewport (the real
pointer stays where it is). PySide6 and a display (offscreen will do)."""

import unittest

import _setup
from _fixtures import capannone

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


if __name__ == "__main__":
    unittest.main()
