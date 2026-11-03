"""The window that arranges itself for its size (R334, study 27): arrangement.py decides (tests/nucleo/test_arrangement.py),
here it is seen carried out, with what the user chose winning, what changes said with its Undo, and what was left on a
shape of the window back when the window has that shape again. Daniel: «nessun cambio a sorpresa»."""

import json
import unittest

import _setup
from _fixtures import capannone

from PySide6.QtCore import Qt

from meridiana import config
from meridiana.ui.design import Bar

setUpModule = _setup.keep_global_state


class Arrange(unittest.TestCase):
    SIZE = (1920, 1080)

    def setUp(self):
        self.app = _setup.qt_or_skip()
        _setup.window(self, capannone(), config.Config(background="none", theme="light"), size=self.SIZE, auto_checks=True)
        _setup.wait_settled(self.app, lambda: self.win.size().toTuple())

    def go(self, w, h):
        win = self.win
        for _twice in range(2):     # the window's least size is the one of the arrangement it had: as a drag, by steps
            win.resize(w, h)
            self.assertTrue(_setup.wait_until(self.app, lambda: not win.arrange_timer.isActive()))
            self.app.processEvents()
        self.assertEqual(win.size().toTuple(), (w, h))
        self.assertTrue(_setup.wait_settled(self.app, lambda: win.centralWidget().size().toTuple()))

    def bar_mode(self):
        return self.win.bars["model"].mode


class TheCases(Arrange):
    def test_the_monitor_turned_puts_the_plan_above_the_3d(self):
        """V1: at 1080 x 1920 the plan was 186 px wide, in an area three times higher than wide."""
        self.go(1080, 1920)
        win = self.win
        self.assertEqual(win.split.orientation(), Qt.Orientation.Vertical)
        self.assertGreater(win.plan.width(), 450)
        self.assertGreater(win.view3d_box.height(), 400)
        self.go(1920, 1080)
        self.assertEqual(win.split.orientation(), Qt.Orientation.Horizontal)

    def test_a_low_window_closes_the_checks_and_says_so_with_the_count_a_click_away(self):
        """H: at 1366 x 768 the plan goes from 363 px of height to much more; the sign with the count stays, and clicking
        it opens them."""
        win = self.win
        win.count_buttons["warn"].setVisible(True)
        plan_before = None
        self.go(1366, 900)
        plan_before = win.plan.height()
        self.go(1366, 768)
        self.assertTrue(win.checks_dock.isHidden())
        self.assertGreater(win.plan.height(), plan_before)
        self.assertIn("Checks closed", win.statusBar().currentMessage())
        self.assertTrue(win.arrange_undo_button.isVisible())
        win.count_buttons["warn"].click()
        self.assertFalse(win.checks_dock.isHidden())

    def test_who_opens_the_checks_finds_them_open(self):
        """Not reopened nor closed against the user's choice, across a change of height within the shape."""
        win = self.win
        self.go(1366, 768)
        self.assertTrue(win.checks_dock.isHidden())
        win.commands["panel_checks"].trigger()
        self.assertFalse(win.checks_dock.isHidden())
        self.go(1366, 700)
        self.assertFalse(win.checks_dock.isHidden())
        self.go(1366, 780)
        self.assertFalse(win.checks_dock.isHidden())

    def test_who_closed_the_checks_in_a_tall_window_finds_them_closed(self):
        win = self.win
        win.commands["panel_checks"].trigger()
        self.assertTrue(win.checks_dock.isHidden())
        self.go(1800, 1000)
        self.go(1920, 1080)
        self.assertTrue(win.checks_dock.isHidden())

    def test_the_bar_changes_mode_and_no_group_is_lost(self):
        win = self.win
        for size, mode in (((1920, 1080), Bar.UNDER), ((1366, 768), Bar.BESIDE), ((1080, 1920), Bar.UNDER),
                           ((800, 1280), Bar.ICONS), ((960, 1080), Bar.ICONS)):
            self.go(*size)
            self.assertEqual(self.bar_mode(), mode, size)
            for pid in ("model", "plant", "report"):
                win.show_phase(pid)
                self.app.processEvents()
                bar = win.bars[pid]
                self.assertTrue(_setup.wait_until(self.app, lambda b=bar: all(g.isVisible() and g.geometry().right() <= b.width()
                                                                              for g in b.groups)),
                                (size, pid, [g.group.id for g in bar.groups if not g.isVisible()]))
            win.show_phase("model")

    def test_the_heights_of_the_modes(self):
        self.assertEqual(self.win.tabs.bars.height(), 69)
        self.go(1366, 768)
        self.assertEqual(self.win.tabs.bars.height(), 31)
        self.go(800, 700)
        self.assertEqual(self.win.tabs.bars.height(), 47)

    def test_the_plants_strip_leaves_the_bar_when_the_groups_need_the_room_and_comes_back(self):
        win = self.win
        win.show_phase("plant")
        strip = win.plant_page.strip
        self.assertTrue(win.bars["plant"].isAncestorOf(strip))
        self.go(1366, 768)
        self.assertFalse(win.bars["plant"].isAncestorOf(strip))
        self.assertTrue(strip.isVisible())
        self.go(1920, 1080)
        self.assertTrue(win.bars["plant"].isAncestorOf(strip))
        self.assertTrue(strip.isVisible())

    def test_the_plants_strip_is_never_put_out_of_sight_by_the_bar(self):
        """A QToolBar does not squeeze what does not fit, it hides it: a string being drawn takes more than the summary,
        and its card was gone at 1400 x 960 (the strip's widest is what counts, not what it says now)."""
        win = self.win
        self.go(1400, 960)
        win.show_phase("plant")
        self.app.processEvents()
        page = win.plant_page
        self.assertFalse(win.bars["plant"].isAncestorOf(page.strip))
        self.assertTrue(_setup.wait_settled(self.app, lambda: win.plan.size().toTuple()))
        plan_before = win.plan.size().toTuple()
        page.show_draft_card("New string 1.2 · Inverter 1 · Acme AC-20K · Input 2", "3 modules", "short", "", "Enter or Esc")
        self.addCleanup(page.show_draft_card)
        self.assertTrue(page.draft_card.isVisibleTo(win))
        # and the plan under the strip stays as it is: it would frame itself again at the first click of a string
        self.assertTrue(_setup.wait_settled(self.app, lambda: win.plan.size().toTuple()))
        self.assertEqual(win.plan.size().toTuple(), plan_before)
        self.go(1920, 1080)
        self.assertTrue(win.bars["plant"].isAncestorOf(page.strip))
        self.assertTrue(page.draft_card.isVisibleTo(win))

    def test_the_row_of_the_phases_goes_to_numbers_with_the_name_of_the_phase_open(self):
        win = self.win
        bar = win.tabs.tab_bar
        self.assertFalse(bar.compact)
        named = bar.tabRect(1).width()
        self.go(800, 1280)
        self.assertTrue(bar.compact)
        self.assertLess(bar.tabRect(1).width(), named)
        current = bar.tabRect(bar.currentIndex()).width()
        self.assertGreater(current, bar.tabRect(1).width())
        self.assertIn("Plant", bar.tip_of(1))
        self.assertLessEqual(bar.width() + win.tabs.header.file_button.width() + win.variant_bar.width(), 800)
        # the other phase takes the name, and the tab of the first one is a number again
        win.show_phase("plant")
        self.app.processEvents()
        self.assertGreater(bar.tabRect(1).width(), bar.tabRect(0).width())
        self.assertEqual(bar.tip_of(1), bar.tabToolTip(1))
        win.show_phase("model")
        self.go(1920, 1080)
        self.assertFalse(bar.compact)
        self.assertEqual(bar.tabRect(1).width(), named)

    def test_one_view_at_a_time_and_the_buttons_choose(self):
        """V2, with the buttons there are; asking for both keeps both."""
        win = self.win
        self.go(700, 800)
        self.assertTrue(win.view_actions["plan"].isChecked())
        self.assertTrue(win.auto_plan)
        win._view_toggle("both")
        self.assertTrue(win.view_actions["both"].isChecked())
        self.go(720, 800)
        self.assertTrue(win.view_actions["both"].isChecked())
        self.assertFalse(win.auto_plan)

    def test_the_area_the_function_reckons_is_the_area_there_is(self):
        """The numbers it decides on are not measured, so that they cannot depend on what it changes: they must be near."""
        from meridiana.arrangement import arrangement
        win = self.win
        for size in ((1920, 1080), (1366, 768), (1080, 1920)):
            self.go(*size)
            c = win._choices()
            self.assertEqual(arrangement(*size, win.phase(), c).views, win.arranged.views)
            left, right = c.columns
            w, h = size
            bar = c.bar_heights[win.arranged.bar]
            checks = c.checks if win.arranged.checks_open else 0
            area = win.centralWidget().size()
            self.assertAlmostEqual(w - c.sides[0] - left - right, area.width(), delta=40, msg=size)
            self.assertAlmostEqual(h - c.sides[1] - bar - checks, area.height(), delta=40, msg=size)


class TheSameSizes(Arrange):
    def test_the_controls_on_the_rows_of_the_bar_have_the_sizes_of_the_system(self):
        """R333: «?» with the other buttons of the status bar, a tool button's size; the «+» of the variants square."""
        from meridiana.ui.design import Button
        win = self.win
        self.assertEqual({b.size().toTuple() for b in win.panel_buttons.buttons.values()},
                         {(Button.TOOL[0], Button.TOOL[0])})
        self.assertEqual(win.variant_bar.plus.size().toTuple(), (Button.CHIP[0], Button.CHIP[0]))
        self.assertEqual(win.tabs.header.file_button.height(), Button.PUSH[0])

    def test_the_modes_have_the_same_names_on_both_sides(self):
        from meridiana import arrangement
        self.assertEqual((arrangement.UNDER, arrangement.BESIDE, arrangement.ICONS), (Bar.UNDER, Bar.BESIDE, Bar.ICONS))


class NoSurprise(Arrange):
    def test_undo_brings_everything_back_and_it_stays_for_this_shape(self):
        win = self.win
        self.go(1366, 768)
        self.assertTrue(win.checks_dock.isHidden())
        self.assertEqual(self.bar_mode(), Bar.BESIDE)
        win.arrange_undo_button.click()
        self.assertTrue(_setup.wait_until(self.app, lambda: not win.checks_dock.isHidden()))
        self.assertEqual(self.bar_mode(), Bar.UNDER)
        self.assertFalse(win.arrange_undo_button.isVisible())
        self.assertIn("Restore the default layout", win.statusBar().currentMessage())
        self.go(1366, 800)                                      # the same shape: not again
        self.assertFalse(win.checks_dock.isHidden())
        self.assertEqual(self.bar_mode(), Bar.UNDER)

    def test_the_undo_goes_after_a_few_seconds(self):
        win = self.win
        self.go(1366, 768)
        self.assertTrue(win.arrange_undo_button.isVisible())
        win._drop_arrange_undo()
        self.assertFalse(win.arrange_undo_button.isVisible())
        win._undo_arrangement()                                 # nothing to undo: nothing happens
        self.assertTrue(win.checks_dock.isHidden())

    def test_no_message_when_nothing_moved(self):
        win = self.win
        self.go(1800, 1000)
        self.assertFalse(win.arrange_undo_button.isVisible())

    def test_near_a_threshold_nothing_goes_to_and_fro(self):
        """Over the line and back by 30 px, three times: once only."""
        win = self.win
        self.go(1500, 905)
        before = win.arranged
        self.assertTrue(before.checks_open)
        self.go(1500, 895)
        low = win.arranged
        self.assertFalse(low.checks_open)
        for h in (925, 895, 930, 899):
            self.go(1500, h)
            self.assertEqual(win.arranged, low, h)
            self.assertTrue(win.checks_dock.isHidden(), h)

    def test_a_resize_waits_until_it_rests(self):
        win = self.win
        win.arrange_timer.setInterval(10_000)
        win.resize(1366, 768)
        self.app.processEvents()
        self.assertEqual(self.bar_mode(), Bar.UNDER)            # still resizing
        self.assertFalse(win.checks_dock.isHidden())
        win.arrange_timer.setInterval(0)
        win.arrange_timer.start()
        self.assertTrue(_setup.wait_until(self.app, lambda: self.bar_mode() == Bar.BESIDE))

    def test_with_the_drawing_alone_or_file_open_it_waits(self):
        win = self.win
        win.clean_action.trigger()
        self.go(1366, 768)
        self.assertEqual(win.arranged.bar, Bar.UNDER)
        win.clean_action.trigger()
        self.assertTrue(_setup.wait_until(self.app, lambda: win.arranged.bar == Bar.BESIDE and not win.arrange_timer.isActive()))
        win.open_file_page()
        self.go(1920, 1080)
        self.assertEqual(win.arranged.bar, Bar.BESIDE)
        win.file_page.close_page()
        self.assertTrue(_setup.wait_until(self.app, lambda: win.arranged.bar == Bar.UNDER))

    def test_the_preference_for_icons_wins_over_everything_and_over_an_undo(self):
        win = self.win
        self.go(1366, 768)
        win.arrange_undo_button.click()
        self.assertTrue(_setup.wait_until(self.app, lambda: self.bar_mode() == Bar.UNDER))
        win._toolbar_style("icons")
        self.assertEqual(self.bar_mode(), Bar.ICONS)
        win._toolbar_style("text")
        self.assertEqual(self.bar_mode(), Bar.BESIDE)


class TheMemory(Arrange):
    def test_the_shape_of_before_comes_back_as_it_was_left(self):
        """A monitor turned: what was left upright is back upright, and what was left wide is back wide."""
        win = self.win
        win.commands["panel_project"].trigger()                 # wide: no Project
        self.assertTrue(win.docks[0].isHidden())
        self.go(1080, 1920)                                     # upright for the first time: as the rules say
        win.docks[0].show()
        win.commands["panel_checks"].trigger()                  # upright: Project yes, Checks no
        self.assertTrue(win.checks_dock.isHidden())
        self.go(1920, 1080)
        self.assertTrue(_setup.wait_until(self.app, lambda: win.docks[0].isHidden()))
        self.assertFalse(win.checks_dock.isHidden())
        self.assertIn("arrangement you left", win.statusBar().currentMessage())
        self.go(1080, 1920)
        self.assertTrue(_setup.wait_until(self.app, lambda: not win.docks[0].isHidden()))
        self.assertTrue(win.checks_dock.isHidden())

    def test_the_default_layout_forgets_it_all(self):
        win = self.win
        self.go(1366, 768)
        win.commands["panel_checks"].trigger()
        self.go(1366, 780)
        self.assertTrue(win.shape_pins.get("medium"))
        win._default_layout(offer_undo=False)
        self.assertEqual(win.shape_memory, {})
        self.assertFalse(win.shape_pins.get("medium"))
        self.assertTrue(win.checks_dock.isHidden())             # as at a first start at this height

    def test_it_is_saved_with_the_window_and_read_back(self):
        win = self.win
        self.go(1366, 768)
        win.arrange_undo_button.click()
        self.assertTrue(_setup.wait_until(self.app, lambda: not win.checks_dock.isHidden()))
        self.go(1920, 1080)
        win._save_window()
        data = json.loads(win.paths.window_state_file.read_text(encoding="utf-8"))
        self.assertTrue(data["shapes"]["medium"]["pins"]["checks_open"])
        self.assertIn("layout", data["shapes"]["medium"])
        self.assertIn("arranged", data["shapes"]["wide"])
        again = type(win)(win.paths, win.cfg)
        self.addCleanup(_setup.dispose, again)
        self.assertEqual(again.shape_pins["medium"]["checks_open"], True)
        self.assertIn("medium", again.shape_memory)

    def test_a_state_of_before_this_version_and_a_broken_one_are_read(self):
        win = self.win
        win._read_shapes(None)
        win._read_shapes("nothing")
        win._read_shapes({"wide": "x", "medium": {"pins": {"bar": "huge", "checks_open": False}, "layout": {"state": 1},
                                                  "arranged": {}}})
        self.assertEqual(win.shape_pins["medium"], {"checks_open": False})
        self.assertNotIn("medium", win.shape_memory)


class TheStart(unittest.TestCase):
    def setUp(self):
        self.app = _setup.qt_or_skip()

    def test_a_low_first_start_closes_the_checks_and_offers_undo(self):
        _setup.window(self, capannone(), config.Config(background="none", theme="light"), size=(1366, 768), auto_checks=True)
        self.assertTrue(self.win.checks_dock.isHidden())
        self.assertTrue(self.win.arrange_undo_button.isVisible())

    def test_a_tall_first_start_says_nothing(self):
        _setup.window(self, capannone(), config.Config(background="none", theme="light"), size=(1600, 1000), auto_checks=True)
        self.assertFalse(self.win.checks_dock.isHidden())
        self.assertFalse(self.win.arrange_undo_button.isVisible())


class TheReckoning(unittest.TestCase):
    """A saved window that opens as it was left (the shape known) and one saved by a version before this."""

    def setUp(self):
        self.app = _setup.qt_or_skip()

    def saved_then_opened(self, edit=None):
        from meridiana.ui.window import MainWindow
        _setup.window(self, capannone(), config.Config(background="none", theme="light"), size=(1366, 768), auto_checks=True)
        win = self.win
        win.commands["panel_checks"].trigger()                  # open, by hand
        self.assertFalse(win.checks_dock.isHidden())
        _setup.turn_events(self.app, 50)
        win._hand_choices(win.arranged)
        win._save_window()
        if edit:
            data = json.loads(win.paths.window_state_file.read_text(encoding="utf-8"))
            edit(data)
            win.paths.window_state_file.write_text(json.dumps(data), encoding="utf-8")
        again = MainWindow(win.paths, win.cfg)
        self.addCleanup(_setup.dispose, again)
        again.arrange_timer.setInterval(0)
        again.resize(1366, 768)
        again.show()
        self.assertTrue(_setup.wait_settled(self.app, lambda: again.size().toTuple()))
        return again

    def test_a_window_opens_as_it_was_left(self):
        again = self.saved_then_opened()
        self.assertFalse(again.checks_dock.isHidden())
        self.assertFalse(again.arrange_undo_button.isVisible())

    def test_a_state_saved_before_this_version_has_the_low_window_decided_once_with_undo(self):
        again = self.saved_then_opened(lambda data: data.pop("shapes"))
        self.assertTrue(again.checks_dock.isHidden())
        self.assertTrue(again.arrange_undo_button.isVisible())


if __name__ == "__main__":
    unittest.main()
