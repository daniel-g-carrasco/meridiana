"""The panels' layout in the real window (R294): a panel dropped on another stays reachable, a layout with open panels
out of sight is never saved and gives way to the default one at the start, «Restore the default layout» works from
any broken arrangement, from its key, the right click on the panel buttons and Appearance, and can be undone."""
import json
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QByteArray, QPoint, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDockWidget, QTabBar

setUpModule = _setup.keep_global_state
DIRECT = Qt.FindChildOption.FindDirectChildrenOnly


def broken_state() -> QByteArray:
    """The dock state Daniel's Meridiana saved on 30/10/2026 after Help was dropped on Properties: Properties open
    and parked off the window in a tab group without its bar, Help and Project closed."""
    data = json.loads(_setup.fixture_text("window-state-r294.json"))
    return QByteArray.fromBase64(data["state"].encode("ascii"))


class PanelLayout(unittest.TestCase):
    def setUp(self):
        self.app = _setup.qt_or_skip()
        _setup.meridiana_look()
        self.win = _setup.window(self, size=(1600, 1000))
        self.panels = (*self.win.docks, self.win.help_dock, self.win.checks_dock)
        self.settle()

    def settle(self):
        self.assertTrue(_setup.wait_settled(self.app, lambda: [d.geometry() for d in self.panels]))

    def in_sight(self, dock) -> bool:
        return not dock.isHidden() and not dock.isFloating() and self.win.rect().contains(dock.geometry())

    def saved_state(self) -> bytes:
        data = json.loads(Path(self.paths.window_state_file).read_text(encoding="utf-8"))
        return bytes(QByteArray.fromBase64(data["state"].encode("ascii")))

    def assert_default(self, reference):
        from meridiana.ui.dock_motion import Reflow, lost_panels
        self.settle()
        self.assertEqual(lost_panels(self.win), [])
        for dock in self.panels:
            self.assertTrue(self.in_sight(dock), dock.objectName())
            self.assertEqual(dock.geometry(), reference[dock], dock.objectName())
        self.assertEqual([layer for layer in self.win.findChildren(Reflow) if layer.isVisible()], [])
        self.assertTrue(all(dock.drag_motion.solver is None for dock in self.panels))
        self.assertEqual(sorted(d.objectName() for d in self.win.findChildren(QDockWidget, options=DIRECT)),
                         ["assistant_dock", "checks", "help", "project", "properties"])

    def reference(self):
        self.win._default_layout(offer_undo=False)
        self.settle()
        return {dock: dock.geometry() for dock in self.panels}

    def test_help_dropped_on_properties_leaves_both_one_click_away(self):
        from meridiana.ui.dock_motion import lost_panels
        source = self.win.help_dock
        anchor = self.win.findChild(QDockWidget, "properties")
        title = source.title_bar
        at = anchor.mapToGlobal(anchor.rect().center())
        QTest.mousePress(title, Qt.MouseButton.LeftButton, pos=title.rect().center())
        QTest.mouseMove(title, title.mapFromGlobal(at - QPoint(12, 12)))
        QTest.mouseMove(title, title.mapFromGlobal(at))
        self.assertTrue(source.drag_motion.target.tab)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton, pos=title.mapFromGlobal(at))
        self.settle()
        _setup.turn_events(self.app, 300)
        self.assertEqual(self.win.tabifiedDockWidgets(source), [anchor])
        self.assertEqual(lost_panels(self.win), [])
        bar = next(b for b in self.win.findChildren(QTabBar, options=DIRECT) if b.count() == 2)
        self.assertTrue(bar.isVisible())
        self.win._save_window()
        self.assertEqual(self.saved_state(), bytes(self.win.saveState()))     # a good layout is saved as it is

    def test_a_layout_with_open_panels_out_of_sight_is_never_saved(self):
        from meridiana.ui.dock_motion import lost_panels
        self.win.restoreState(broken_state())
        self.settle()
        self.assertEqual([d.objectName() for d in lost_panels(self.win)], ["properties"])
        self.win._save_window()
        self.assertEqual(self.saved_state(), bytes(self.win.factory_state))

    def test_the_default_layout_comes_back_from_broken_arrangements(self):
        reference = self.reference()
        properties = self.win.docks[1]

        def daniels():
            self.win.restoreState(broken_state())

        def floating_off_the_screens():
            properties.setFloating(True)
            properties.move(-20000, -20000)

        def a_drag_in_the_middle():
            title = self.win.help_dock.title_bar
            QTest.mousePress(title, Qt.MouseButton.LeftButton, pos=title.rect().center())
            QTest.mouseMove(title, title.mapFromGlobal(properties.mapToGlobal(properties.rect().center())))
            self.assertIsNotNone(self.win.help_dock.drag_motion.solver)

        def a_tab_group_without_its_bar():
            self.win.tabifyDockWidget(properties, self.win.help_dock)
            self.win.layout().activate()                # Qt's new bar stays hidden: the bug of R294

        for name, breaking in (("Daniel's", daniels), ("floating", floating_off_the_screens),
                               ("drag", a_drag_in_the_middle), ("tab bar", a_tab_group_without_its_bar)):
            with self.subTest(name):
                breaking()
                self.settle()
                self.win.commands["default_layout"].trigger()
                QTest.mouseRelease(self.win.help_dock.title_bar, Qt.MouseButton.LeftButton)   # the drag's button
                self.assert_default(reference)
                self.assertEqual(self.saved_state(), bytes(self.win.saveState()))         # the saved one too
                self.assertIn(self.win.statusBar().currentMessage().split(".")[0],
                              "The panels are back as at the first start")
                self.win.layout_undo = None

    def test_the_default_layout_is_undone_by_its_key_again_while_its_message_shows(self):
        from meridiana.ui.dock_motion import DockTarget, apply_target
        reference = self.reference()
        apply_target(self.win, self.win.help_dock, DockTarget(Qt.DockWidgetArea.LeftDockWidgetArea))
        self.settle()
        arranged = bytes(self.win.saveState())
        action = self.win.commands["default_layout"]
        self.assertEqual(action.shortcut(), QKeySequence("Ctrl+Shift+0"))
        action.trigger()
        self.assert_default(reference)
        self.assertIn("Ctrl+Shift+0", self.win.statusBar().currentMessage())
        action.trigger()
        self.settle()
        self.assertEqual(self.win.dockWidgetArea(self.win.help_dock), Qt.DockWidgetArea.LeftDockWidgetArea)
        self.assertEqual(bytes(self.win.saveState()), arranged)
        self.assertEqual(self.saved_state(), arranged)
        action.trigger()                                # once more: a new reset, the undo was spent
        self.assert_default(reference)
        self.win.layout_undo = (self.win.layout_undo[0], 0.0)      # its time is over: the key resets again
        action.trigger()
        self.assert_default(reference)

    def test_panels_still_lost_after_the_restore_are_put_back_one_by_one(self):
        # restoreState of the first layout was enough on Daniel's state; the window still has a way when it is not
        from unittest import mock
        from meridiana.ui import dock_motion
        reference = self.reference()
        real = dock_motion.lost_panels
        answers = iter([[], [self.win.docks[1]]])
        with mock.patch.object(dock_motion, "lost_panels", lambda w: next(answers, None) or real(w)):
            self.win._default_layout(offer_undo=False)
        self.assert_default(reference)

    def test_a_broken_state_offers_no_undo_into_it(self):
        reference = self.reference()
        self.win.restoreState(broken_state())
        self.settle()
        self.win.commands["default_layout"].trigger()
        self.assert_default(reference)
        self.assertIsNone(self.win.layout_undo)

    def test_the_way_back_is_on_the_panel_buttons_and_in_appearance(self):
        from meridiana.ui.dock_motion import DockTarget, apply_target
        reference = self.reference()
        self.assertIn(self.win.commands["default_layout"], self.win.panel_buttons.context_menu().actions())
        apply_target(self.win, self.win.checks_dock, DockTarget(Qt.DockWidgetArea.TopDockWidgetArea))
        self.settle()
        self.win._preferences("appearance")
        self.win.file_page.settings.appearance.layout_reset.click()
        self.win.file_page.hide()
        self.assert_default(reference)


class StartWithABrokenLayout(unittest.TestCase):
    def test_the_default_layout_replaces_a_saved_one_with_open_panels_out_of_sight(self):
        from meridiana.paths import Paths
        from meridiana.ui.dock_motion import lost_panels
        app = _setup.qt_or_skip()
        _setup.meridiana_look()
        first = _setup.window(self, size=(1600, 1000))
        geometry, split = first.saveGeometry(), first.split.saveState()
        root = Path(tempfile.mkdtemp())
        paths = Paths(config=root / "config", state=root / "state", data=root / "data", cache=root / "cache")
        paths.window_state_file.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(_setup.fixture_text("window-state-r294.json"))
        data.update(geometry=bytes(geometry.toBase64()).decode("ascii"),
                    split=bytes(split.toBase64()).decode("ascii"))
        paths.window_state_file.write_text(json.dumps(data), encoding="utf-8")
        win = _setup.window(self, paths=paths, size=(1600, 1000))
        self.assertTrue(win.restored)
        self.assertTrue(_setup.wait_until(app, lambda: win.statusBar().currentMessage().startswith(
            "The saved panel layout left some open panels out of sight"), 5))
        self.assertEqual(lost_panels(win), [])
        for dock in (*win.docks, win.help_dock, win.checks_dock):
            self.assertFalse(dock.isHidden(), dock.objectName())
            self.assertTrue(win.rect().contains(dock.geometry()), dock.objectName())
        saved = json.loads(paths.window_state_file.read_text(encoding="utf-8"))
        self.assertEqual(QByteArray.fromBase64(saved["state"].encode("ascii")), win.saveState())


if __name__ == "__main__":
    unittest.main()
