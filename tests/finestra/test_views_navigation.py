"""The navigation of the views and the gizmo of Move through the window (study 15, 2.6; task 16b, steps 5-7): the
preferences reach the 3D view and the plan and are kept, the system's wish for less motion reaches the 3D view, and
what the gizmo hands over (a drag, a turn, a copy, the values typed, the arrows, Esc) moves the selection in one step
of the undo each. What the 3D view and the plan do by themselves is in widget/test_view3d_navigation.py and
widget/test_plan.py. PySide6 and a display (offscreen will do)."""

import html
import unittest

import numpy as np

import _setup
from _fixtures import capannone

from meridiana import config, move, navigation

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

MIDDLE, SHIFT = 4, 0x02000000


class Navigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone())
        self.backend = self.win.view3d.backend
        self.backend.reduced_motion = True

    def drag(self, button, mods, start, end, steps=5):
        b = self.backend
        b.press(button, mods, *start, False, 0, 0, 0, "", -1)
        for i in range(1, steps + 1):
            b.move(mods, start[0] + (end[0] - start[0]) * i / steps, start[1] + (end[1] - start[1]) * i / steps)
        b.release(button, mods, *end)

    def test_the_preferences_of_the_navigation_reach_the_3d_view_and_the_plan_and_are_kept(self):
        from PySide6.QtWidgets import QApplication, QDialog

        from meridiana.ui.theme import SystemAccent
        b = self.backend

        def choose(dialog):
            page = dialog.navigation
            before = (page.audience.text(), page.gestures.text())
            self.assertIn("AutoCAD", before[0])                 # the default, explained
            self.assertTrue(page.hint.isChecked())
            self.assertIn("Shift", page.hint_keys.text())       # AutoCAD's key to hold, in words
            page.style.setCurrentIndex(page.style.findData("opencascade"))
            self.assertIn("Ctrl", page.hint_keys.text())
            page.style.setCurrentIndex(page.style.findData("blender"))
            self.assertFalse(page.hint.isEnabled())             # nothing to hold in that style
            self.assertNotIn("Shift", page.hint_keys.text())
            page.orbit.setCurrentIndex(page.orbit.findData("arcball"))
            page.pivot.setCurrentIndex(page.pivot.findData("selection"))
            self.assertIn("Blender", page.audience.text())
            self.assertNotEqual(page.gestures.text(), before[1])
            for what, how in navigation.table("blender"):          # the table of navigation.py, as it is
                self.assertIn(html.escape(what), page.gestures.text())
                self.assertIn(html.escape(how), page.gestures.text())
            return QDialog.DialogCode.Accepted
        self.win._preferences("navigation", run=choose)
        self.assertEqual((b.navigator.style.name, b.orbit_mode, b.pivot_mode), ("Blender", "arcball", "selection"))
        self.assertEqual(self.win.plan.navigator.style.name, "Blender")         # the plan follows
        saved = config.load(self.paths.config_file)
        self.assertEqual((saved.navigation, saved.orbit, saved.pivot), ("blender", "arcball", "selection"))
        self.win._select("building", self.win.project.buildings[0].id)
        self.assertIsNotNone(b.selection_centre)
        self.drag(MIDDLE, 0, (300, 300), (330, 300))        # Blender: the middle orbits, around the selection
        self.assertTrue(np.allclose(b._pivot, b.selection_centre))
        # the cross-hair on passing over: switched off in the page, kept in the settings; a style without a key to
        # hold leaves the choice as it is
        self.win._navigation("autocad", "turntable", "cursor", True)

        def no_hint(dialog):
            dialog.navigation.hint.setChecked(False)
            return QDialog.DialogCode.Accepted
        self.win._preferences("navigation", run=no_hint)
        self.assertFalse(b.pivot_hint)
        self.assertFalse(self.cfg.pivot_hint)
        self.assertFalse(config.load(self.paths.config_file).pivot_hint)
        self.win._navigation("autocad", "turntable", "cursor", True)
        self.win._navigation("blender", "turntable", "cursor")
        self.assertTrue(self.cfg.pivot_hint)
        # less motion asked by the system: the 3D view animates no more, and again when allowed
        system = SystemAccent.of(QApplication.instance())
        system.motion.emit(False)
        self.assertFalse(b.reduced_motion)
        system.motion.emit(True)
        self.assertTrue(b.reduced_motion)


class Gizmo(unittest.TestCase):
    """What the window does with the gizmo of the 3D view: shown on the middle of the selection with Move only, and
    each thing it hands over applied to the project in one step of the undo, the sub-field going with its building."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    setUp = Navigation.setUp
    drag = Navigation.drag

    def tearDown(self):
        self.win.session.mark_saved()                   # moved, not to be saved: no question at the close

    def test_the_gizmo_in_the_window_moves_turns_copies_and_nudges_the_selection_one_step_each(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from meridiana import gizmo
        b, win = self.backend, self.win
        bid = win.project.buildings[0].id
        footprint = [list(map(float, q)) for q in win.project.building(bid).footprint]
        win._select("building", bid)
        self.assertFalse(b.gizmo_on)                     # only with Move
        win._set_tool("move")
        self.assertTrue(np.allclose(b.gizmo_centre, (20.0, 9.5, -10.0)))     # the middle of the shed, on its roof
        win._select("site", "")
        self.assertFalse(b.gizmo_on)
        win._select("building", bid)
        self.assertTrue(b.gizmo_on)
        win._snaps(False)
        self.assertFalse(b.gizmo_snaps)                  # the snaps of the plan are the gizmo's steps too
        # a real drag of the East arrow: the building and its sub-field, East only, in one step
        start = b.camera.project(b.gizmo_centre + gizmo.EAST * 0.6 * b.gizmo_size(), *b.size)
        done = []
        b.gizmoDone.connect(lambda *a: done.append(a))
        steps = win.undo.index()
        self.drag(1, 0, start, (start[0] + 50.0, start[1]))
        [(east, _n, _d, _c)] = done
        for (x, y), (x0, y0) in zip(win.project.building(bid).footprint, footprint, strict=True):
            self.assertAlmostEqual(x - x0, east, delta=1e-6)
            self.assertEqual(y, y0)
        self.assertAlmostEqual(win.project.subfields[0].ring[0][0], 1.0 + east, delta=1e-6)
        self.assertEqual(win.undo.index(), steps + 1)
        win.undo.undo()
        # the ring: a turn about the middle, said «Rotate», the gizmo still on the middle
        b.gizmoDone.emit(0.0, 0.0, 30.0, False)
        turned = move.moved(footprint, move.turn(20.0, 10.0, 30.0))
        for (x, y), (ex, ey) in zip(win.project.building(bid).footprint, turned, strict=True):
            self.assertAlmostEqual(x, ex, places=6)
            self.assertAlmostEqual(y, ey, places=6)
        self.assertEqual(win.undo.undoText(), "Rotate")
        self.assertTrue(np.allclose(b.gizmo_centre, (20.0, 9.5, -10.0), atol=1e-6))
        win.undo.undo()
        # Ctrl at the release: a copy, selected, the building as it was
        b.gizmoDone.emit(0.0, 30.0, 0.0, True)
        self.assertEqual(len(win.project.buildings), 2)
        self.assertEqual(win.project.building(bid).footprint, footprint)
        self.assertEqual(win.selection, ("building", win.project.buildings[1].id))
        self.assertEqual(win.undo.undoText(), "Copy")
        win.undo.undo()
        win._select("building", bid)
        # the values typed: East and North, then the turn about the middle where it has gone
        win.view3d.gizmoTyped.emit(2.0, -3.0, None)
        self.assertEqual(win.project.building(bid).footprint[0], [2.0, -3.0])
        win.view3d.gizmoTyped.emit(None, None, 90.0)
        self.assertEqual(win.project.building(bid).footprint[1], [32.0, 27.0])    # turned left about (22, 7)
        win.undo.undo()
        win.undo.undo()
        # the arrows of the keyboard on the 3D view: one step for the three
        steps = win.undo.index()
        view = win.view3d
        QTest.keyClick(view, Qt.Key.Key_Right)
        QTest.keyClick(view, Qt.Key.Key_Up, Qt.KeyboardModifier.ShiftModifier)
        QTest.keyClick(view, Qt.Key.Key_Left, Qt.KeyboardModifier.ControlModifier)
        x, y = win.project.building(bid).footprint[0]
        self.assertAlmostEqual(x, 0.09, places=6)
        self.assertAlmostEqual(y, 1.0, places=6)
        self.assertEqual(win.undo.index(), steps + 1)
        # Esc with no drag going on leaves Move, and without the tool nothing moves
        QTest.keyClick(view, Qt.Key.Key_Escape)
        self.assertEqual(win.plan.tool, "select")
        self.assertFalse(b.gizmo_on)
        before = win.snapshot()
        self.drag(1, 0, start, (start[0] + 50.0, start[1]))
        self.assertEqual(win.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
