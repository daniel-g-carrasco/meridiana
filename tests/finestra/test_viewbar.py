"""The commands of the views inside the views (Daniel, 23/10/2026, R14 and R27): a bar in the top left corner of
the plan and of the 3D view with the selector plan / 3D / side by side and «Fit», on the plan the snaps and the
ortho as switches; the toolbar and the status bar no longer have them, the keys are the same; the status bar has
margins. The bars hold the window's commands: they are tested through it. PySide6 and a display (offscreen will
do)."""

import unittest

import _setup
from _fixtures import capannone

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

VIEW_COMMANDS = ("view_plan", "view_3d", "view_both", "fit", "zoom_in", "zoom_out")
PLAN_COMMANDS = VIEW_COMMANDS + ("snaps", "ortho")


class ViewBars(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone())
        self.win.activateWindow()
        # the plant's strings come back after the layout and show the checks again (task 16d): the window settles
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.win.plant_pending()))
        self.app.processEvents()

    def commands_of(self, bar) -> list:
        ids = {a: cid for cid, a in self.win.commands.items()}
        return [ids.get(b.defaultAction()) for b in bar.buttons.values()]

    def test_each_view_has_its_bar_in_its_corner_with_the_commands_that_left_the_toolbar_and_their_keys(self):
        from PySide6.QtGui import QKeySequence
        from PySide6.QtWidgets import QToolBar, QToolButton
        win = self.win
        plan, view3d = win.plan, win.view3d
        self.assertEqual(self.commands_of(plan.viewbar), [*PLAN_COMMANDS, None])
        self.assertIs(list(plan.viewbar.buttons)[-1], win.background_action)     # and the background (R21)
        self.assertEqual(self.commands_of(view3d.viewbar), list(VIEW_COMMANDS))
        for view, bar in ((plan, plan.viewbar), (view3d, view3d.viewbar)):
            self.assertIs(bar.parentWidget(), view)
            self.assertTrue(bar.isVisible())
            self.assertLess(bar.x(), 20)
        self.assertLess(plan.viewbar.y(), 20)
        self.assertFalse(plan.viewbar.geometry().intersects(plan.north.geometry()))
        self.assertFalse(view3d.viewbar.geometry().intersects(view3d.cube.geometry()))
        # in a narrow view the bar goes below the cube, and back up when there is room (side by side the 3D bar
        # holds only Fit, 24/10/2026: narrow is about the cube's width)
        for width, up in ((view3d.cube.width() + 20, False), (700, True)):
            view3d.resize(width, 500)
            self.app.processEvents()
            with self.subTest(width=width):
                self.assertFalse(view3d.viewbar.geometry().intersects(view3d.cube.geometry()))
                self.assertEqual(view3d.viewbar.y() < 20, up)
                self.assertLess(view3d.viewbar.x(), 20)
        # the commands of the views are no longer in the toolbar or the status bar
        moved = {win.commands[cid] for cid in PLAN_COMMANDS}
        for bar in win.findChildren(QToolBar):
            self.assertFalse(moved & set(bar.actions()), bar.objectName())
        self.assertFalse(moved & {b.defaultAction() for b in win.statusBar().findChildren(QToolButton)})
        # each command one action, with the same keys said in its tip
        for cid, key in (("snaps", "F3"), ("ortho", "F8"), ("view_plan", "Ctrl+Shift+2"), ("fit", "F")):
            action = win.commands[cid]
            self.assertEqual(action.shortcut(), QKeySequence(key), cid)
            self.assertIn(action.shortcut().toString(QKeySequence.SequenceFormat.NativeText), action.toolTip())
            self.assertIs(plan.viewbar.buttons[action].defaultAction(), action)
        # the status bar keeps a margin from the sides and between its items
        m = win.statusBar().contentsMargins()
        self.assertGreaterEqual(min(m.left(), m.right()), 6)
        self.assertGreaterEqual(win.coords.contentsMargins().left(), 4)

    def test_zoom_buttons_and_keys_move_both_views_and_say_the_key(self):
        from PySide6.QtGui import QKeySequence
        win = self.win
        for cid, key in (("zoom_in", "+"), ("zoom_out", "-")):
            action = win.commands[cid]
            self.assertEqual(action.shortcuts()[0], QKeySequence(key))
            self.assertIn(key, win.plan.viewbar.buttons[action].toolTip())
            self.assertFalse(win.plan.viewbar.buttons[action].icon().isNull())
            self.assertIn(action, win.view3d.viewbar.buttons)
        plan_scale = win.plan.transform().m11()
        camera = win.view3d.backend.camera
        distance = (camera.position - camera.target).dot(camera.position - camera.target)
        win.plan.viewbar.buttons[win.commands["zoom_in"]].click()
        self.assertAlmostEqual(win.plan.transform().m11(), plan_scale * 1.2)
        self.assertLess((camera.position - camera.target).dot(camera.position - camera.target), distance)
        win.commands["zoom_out"].trigger()
        self.assertAlmostEqual(win.plan.transform().m11(), plan_scale)

    def test_the_keys_and_the_switches_the_selector_of_the_views_and_the_colours_of_the_theme(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        win = self.win
        snaps, ortho = win.snaps_action, win.ortho_action
        buttons = win.plan.viewbar.buttons
        win.plan.setFocus()
        self.assertTrue(snaps.isChecked())
        QTest.keyClick(win.plan, Qt.Key.Key_F3)
        self.assertFalse(snaps.isChecked())
        self.assertFalse(win.plan.snaps_on)
        self.assertFalse(buttons[snaps].isChecked())
        QTest.keyClick(win.plan, Qt.Key.Key_F8)
        self.assertTrue(ortho.isChecked())
        self.assertTrue(win.plan.ortho)
        self.assertTrue(buttons[ortho].isChecked())
        buttons[ortho].click()                              # the button is the same switch
        self.assertFalse(win.plan.ortho)
        # the selector of the views shows which is on, in both bars
        win.view_actions["plan"].trigger()
        self.assertEqual(win.current_view, "plan")
        self.assertTrue(buttons[win.view_actions["plan"]].isChecked())
        self.assertFalse(win.view3d_box.isVisible())
        win.view_actions["both"].trigger()
        bar3d = win.view3d.viewbar
        self.assertTrue(bar3d.buttons[win.view_actions["both"]].isChecked())
        self.assertFalse(bar3d.buttons[win.view_actions["3d"]].isChecked())
        # the bars take the colours of the theme: a switch on in the pressed layer, as every tool (R158, R160)
        from meridiana import theme_colors
        win._appearance("dark", "plum", "meridiana")
        self.assertIn(theme_colors.qt_hex(win.theme.tokens["press"]), win.plan.viewbar.styleSheet())
        win._appearance("light", "bronze", "meridiana")
        self.assertIn(theme_colors.qt_hex(win.theme.tokens["press"]), win.view3d.viewbar.styleSheet())


if __name__ == "__main__":
    unittest.main()
