"""The checks on the views through the window (study 12, C1, C3, C4; task 17e): a mark on each object with its level
and number in the plan, over the 3D view and in the tree rising to the parents; the list and the views linked both
ways; the view chosen kept in the settings, the counts of the status bar, Ctrl+., the phase shown; the defaults and
the names the window gives the panel. The panel alone is in widget/test_checks_page.py. PySide6 and a display
(offscreen will do)."""

import unittest

import _setup
from _fixtures import capannone, clear_sky_meteo

from meridiana import config
from meridiana.checks import Item

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

USER = 0x0100           # Qt.ItemDataRole.UserRole: the row's index into the items


class ChecksOnTheViews(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone())
        self.sid = self.win.project.subfields[0].id
        self.bid = self.win.project.buildings[0].id
        self.items = [Item("warn", "layout", "a", target=("subfield", self.sid), detail="Why a, and what to do."),
                      Item("fail", "layout", "b", target=("subfield", self.sid), detail="Why b, and what to do."),
                      Item("info", "layout", "c", target=("building", self.bid)),
                      Item("ok", "strings", "d", target=("phase", "production")),
                      Item("warn", "connection", "e", target=("site",), detail="Why e.")]
        self.show(self.items)
        self.win._show_marks()

    def show(self, items, extras=()):
        from meridiana.ui.checks_page import object_names
        self.win.checks_page.show_items(items, extras, object_names(self.win.project))

    def rows(self):
        page = self.win.checks_page
        return [page.tree.topLevelItem(g).child(r) for g in range(page.tree.topLevelItemCount())
                for r in range(page.tree.topLevelItem(g).childCount())]

    def shown(self):
        return sorted(self.win.checks_page.all[r.data(1, USER)].text for r in self.rows()
                      if not r.isHidden() and not r.parent().isHidden())

    def row_of(self, text):
        return next(r for r in self.rows() if self.win.checks_page.all[r.data(1, USER)].text == text)

    def test_a_mark_on_each_object_in_the_views_and_the_tree_rising_to_the_parents_with_what_it_counts(self):
        from meridiana.ui.marks import MARK_ROLE
        win = self.win
        plan = {it.data(1): (it.level, it.count) for it in win.plan.mark_items}
        self.assertEqual(plan, {("subfield", self.sid): ("fail", 2), ("building", self.bid): ("info", 1)})
        in_3d = {m[3]: (m[1], m[2]) for m in win.view3d.marks.marks}
        self.assertEqual(in_3d, plan)
        self.assertTrue(win.view3d.marks.where())          # on screen where the camera shows them
        root = win.tree.topLevelItem(0)
        subfields = root.child(1)
        self.assertEqual(root.data(1, MARK_ROLE), ("fail", 4))  # the site gathers everything (second column)
        self.assertEqual(subfields.data(1, MARK_ROLE), ("fail", 2))
        self.assertEqual(subfields.child(0).data(1, MARK_ROLE), ("fail", 2))
        self.assertIsNone(root.child(2).data(1, MARK_ROLE))  # no exclusion, no mark
        self.assertTrue(root.toolTip(1).startswith("1 to fix, 2 to check, 1 to know in this object and inside"))
        sub = root.child(1).child(0)
        self.assertTrue(sub.toolTip(1).startswith("1 to fix, 1 to check about this object"))
        self.assertIn("A click", sub.toolTip(1))
        self.assertEqual(root.child(0).child(0).toolTip(1).split("\n")[0], "1 to know about this object")
        self.assertEqual(root.child(2).toolTip(1), "")
        # a mark on the plan selects its object and opens the list
        win.checks_dock.hide()
        win.plan.markClicked.emit("building", self.bid)
        self.assertEqual(win.selection, ("building", self.bid))
        self.assertTrue(win.checks_dock.isVisible())

    def test_the_list_and_the_views_follow_each_other_both_ways(self):
        win, page = self.win, self.win.checks_page
        plan = win.plan
        building, subfield = plan.items_by_kind["building"][0], plan.items_by_kind["subfield"][0]
        # a click on an item shows its object and dims the rest; the list stays on the item clicked
        row = self.row_of("b")
        page.tree.setCurrentItem(row)
        self.assertEqual(win.selection, ("subfield", self.sid))
        self.assertEqual((building.opacity(), subfield.opacity()), (0.3, 1.0))
        self.assertIs(page.tree.currentItem(), row)
        win._select("building", self.bid)                   # another selection: nothing dimmed
        self.assertEqual(building.opacity(), 1.0)
        # the eye on a row: the object shown in the views, the rest dimmed
        n = next(k for k, i in enumerate(self.items) if i.text == "c")
        page.row_buttons(n)["eye"].click()
        self.assertEqual(win.selection, ("building", self.bid))
        self.assertEqual((building.opacity(), subfield.opacity()), (1.0, 0.3))
        # from the object selected to its items, in bold
        win._select("subfield", self.sid)
        bold = {self.items[r.data(1, USER)].text: r.font(1).bold() for r in self.rows()}
        self.assertEqual(bold, {"a": True, "b": True, "c": False, "d": False, "e": False})
        # «This object» follows the selection
        win._select("building", self.bid)
        page.object_button.click()
        self.assertEqual(self.shown(), ["c"])
        win._select("subfield", self.sid)
        self.assertEqual(self.shown(), ["a", "b"])
        page.object_button.click()
        # a double click leads to the place
        page._open(self.row_of("d"), 1)
        self.assertEqual(win.phase(), "production")
        win.show_phase("model")
        # a click on a mark of the tree: that object's checks, the list opened; the name alone selects; a group
        win.checks_dock.hide()
        sub = win.tree.topLevelItem(0).child(1).child(0)
        win._tree_clicked(sub, 1)
        self.assertEqual(win.selection, ("subfield", self.sid))
        self.assertTrue(win.checks_dock.isVisible())
        self.assertEqual(self.shown(), ["a", "b"])
        self.assertIn("Only the checks of Sud;", page.object_button.toolTip())
        page.object_button.click()
        win._tree_clicked(sub, 0)                           # the name: selected, the list as it is
        self.assertEqual(self.shown(), ["a", "b", "c", "d", "e"])
        win._tree_clicked(win.tree.topLevelItem(0).child(1), 1)          # a group: everything inside
        self.assertEqual(self.shown(), ["a", "b"])
        self.assertTrue(page.object_button.isChecked())

    def test_the_view_chosen_the_counts_of_the_status_bar_ctrl_dot_and_the_phase_reach_the_panel(self):
        win, page = self.win, self.win.checks_page
        # the view chosen in the panel is kept in the settings
        next(a for a in page.view_actions.actions() if a.data() == "object").trigger()
        self.assertEqual(self.cfg.checks_view, "object")
        self.assertEqual(config.load(self.paths.config_file).checks_view, "object")
        page.set_view("level")
        # «This phase»: the phase the window shows
        page.phase_button.click()
        win.show_phase("plant")
        self.assertEqual(self.shown(), ["d", "e"])
        win.show_phase("model")
        page.phase_button.click()
        # Ctrl+. applies the fix of the item in hand
        self.items[1].fix, self.items[1].fix_label = ("compute",), "Compute"
        self.show(self.items)
        heard = []
        page.fix.connect(heard.append)
        command = win.commands["fix_check"]
        self.assertEqual(command.shortcut().toString(), "Ctrl+.")
        page.tree.setCurrentItem(self.row_of("b"))
        command.trigger()
        self.assertEqual([h.text for h in heard], ["b"])
        # the counts of the status bar lead to the section, the panel opened
        fail, warn = win.count_buttons["fail"], win.count_buttons["warn"]
        self.assertTrue(fail.isVisibleTo(win) and warn.isVisibleTo(win))
        self.assertTrue(warn.text().endswith("2"))
        self.assertIn("section", warn.toolTip())
        win.checks_dock.hide()
        page.tree.setCurrentItem(self.row_of("c"))
        warn.click()
        self.assertTrue(win.checks_dock.isVisible())
        self.assertEqual(page.selected().text, "a")                      # the first of the section
        # new counts do not resize the panel in the window
        dock = win.checks_dock
        self.app.processEvents()
        before = (dock.sizeHint().height(), dock.minimumSizeHint().height(), dock.height())
        many = [Item(lv, "layout", f"{lv} {k}", target=("subfield", self.sid)) for lv in ("fail", "warn", "info", "ok")
                for k in range(12)]
        for items in (many, [], self.items):
            self.show(items)
            self.app.processEvents()
            self.assertEqual((dock.sizeHint().height(), dock.minimumSizeHint().height(), dock.height()), before)
        self.show([Item("info", "layout", "only info")])
        win._show_marks()
        self.assertFalse(fail.isVisibleTo(win) or warn.isVisibleTo(win))

    def test_the_window_gives_the_panel_the_defaults_and_the_names(self):
        from _fixtures import write_cache
        page = self.win.checks_page
        write_cache(clear_sky_meteo(45.5226, 9.03), self.paths.cache)   # a weather year without the network
        self.win.energy = {}
        self.win._compute_energy(fetch=False)
        self.assertTrue(_setup.wait_until(self.app, lambda: self.win.energy and self.win.energy.get("sim") is not None,
                                          60))
        self.assertTrue(_setup.wait_until(self.app, lambda: page.extras))
        self.assertTrue(all(e.area == "defaults" for e in page.extras))
        self.assertIn(("subfield", self.sid), page.names)
        self.assertEqual(page.names[("subfield", self.sid)], "Sud")
        self.assertTrue(all(len(i.text) <= 90 for i in page.items))


if __name__ == "__main__":
    unittest.main()
