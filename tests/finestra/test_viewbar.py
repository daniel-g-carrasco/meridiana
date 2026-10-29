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
PLAN_COMMANDS = VIEW_COMMANDS + ("view_align", "snaps", "ortho")      # turning the plan: R174, R183


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
        from PySide6.QtCore import QAbstractAnimation
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
        # The bar stays at the top; the compass animates to the lower corner when they cannot fit side by side.
        room = plan.viewport().width() - plan.north.width() - 3 * 8
        self.assertLess(plan.viewbar.y(), 20)
        self.assertTrue(_setup.wait_until(
            self.app, lambda: plan.north._travel.state() == QAbstractAnimation.State.Stopped))
        if plan.viewbar.width() <= room:
            self.assertLess(plan.north.y(), 20)
        else:
            self.assertGreater(plan.north.y(), plan.viewport().height() / 2)
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

    def test_with_their_words_the_buttons_are_as_wide_as_their_words(self):
        """Daniel, 26/10/2026, on the wider screens of the studio: «le scritte e alcuni elementi ora si visualizzano
        deformati più stretti», then «non è solo il testo ma anche elementi come questi tasti»: the buttons of the
        views' bars had been held 24 px wide (36 with a menu), the words cut down to nothing beside the icon and the
        icons squeezed in grounds taller than wide. As wide as they ask, words or not. Align stays icon-only (R183)."""
        from PySide6.QtCore import Qt
        win = self.win
        win.plan.resize(540, 500)
        self.app.processEvents()
        bar = win.plan.viewbar
        for on in (True, False):
            bar.set_words(on)
            self.app.processEvents()
            for _action, button in bar.buttons.items():
                if button.isVisible():
                    self.assertGreaterEqual(button.width(), button.sizeHint().width(), (on, button.text()))
                    self.assertGreaterEqual(button.width(), button.height(), (on, button.text()))   # never taller
            align = bar.buttons[win.commands["view_align"]]
            self.assertEqual(align.toolButtonStyle(), Qt.ToolButtonStyle.ToolButtonIconOnly)
            self.assertFalse(align.icon().isNull())
            self.assertIn("A", align.toolTip())
            self.assertFalse(bar.geometry().intersects(win.plan.north.geometry()))
        bar.set_words(False)

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

    def test_aligning_the_view_to_a_side_and_returning_north_up(self):
        win = self.win
        bid = win.project.buildings[0].id
        before = win.project.to_json()
        win._select("building", bid)
        win.commands["view_align"].trigger()
        self.assertEqual(win.plan.edge_pick[0], "align")
        win._edge_picked("align", "building", bid, 1)
        self.assertAlmostEqual(win.plan.view_rotation(), 90.0)
        self.assertEqual(win.project.to_json(), before)
        win.commands["view_north"].trigger()
        self.assertAlmostEqual(win.plan.view_rotation(), 0.0)
        self.assertIsNone(win.plan.edge_pick)

    def test_turning_the_plan_without_the_menus_buttons_keys_compass_and_right_click(self):
        """R174 (Daniel, 26/10/2026: «non bisognerebbe andare sul menu su alt per aprirlo. mi piacciono i tuoi
        consigli»), revised by R183: Align is the only rotation command in the plan's bar, with A in its tooltip;
        North up keeps N, the compass click and the right-click menu, but no button."""
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QKeySequence

        from meridiana.ui.plan import to_scene
        win = self.win
        align = win.commands["view_align"]
        self.assertIn(align, win.plan.viewbar.buttons)
        self.assertIn(QKeySequence("A"), align.shortcuts())
        self.assertIn("A", win.plan.viewbar.buttons[align].toolTip())
        north = win.commands["view_north"]
        self.assertNotIn(north, win.plan.viewbar.buttons)
        self.assertIn(QKeySequence("N"), north.shortcuts())
        building = win.project.buildings[0]
        before = win.project.to_json()
        win.plan.rotate_view(37.0)
        win.plan.north.clicked.emit()                               # what a click on the compass sends
        self.assertAlmostEqual(win.plan.view_rotation(), 0.0)
        # a right click on the middle of side 1 of the building
        a, b = building.footprint[1], building.footprint[2]
        middle = win.plan.mapFromScene(to_scene((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
        win._plan_menu(QPoint(middle.x(), middle.y()))
        texts = [x.text() for x in win.context_menu.actions()]
        self.assertIn("Align the view to this side", texts)
        self.assertNotIn("North up", texts)                         # North is up already
        align = next(x for x in win.context_menu.actions() if x.text() == "Align the view to this side")
        win.context_menu.close()
        align.trigger()
        p, q = win.plan.mapFromScene(to_scene(*a)), win.plan.mapFromScene(to_scene(*b))
        self.assertAlmostEqual(p.y(), q.y(), delta=1.0)             # that side lies level on the screen
        self.assertNotAlmostEqual(win.plan.view_rotation() % 360.0, 0.0, places=1)
        self.assertEqual(win.project.to_json(), before)             # the project never turns
        middle = win.plan.mapFromScene(to_scene((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))     # where the side is now
        win._plan_menu(QPoint(middle.x(), middle.y()))              # turned: the menu offers North up too
        self.assertIn("North up", [x.text() for x in win.context_menu.actions()])
        win.context_menu.close()
        win.commands["view_north"].trigger()
        self.assertAlmostEqual(win.plan.view_rotation(), 0.0)

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
