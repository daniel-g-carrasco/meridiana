"""The Checks panel alone (ui/checks_page.py; task 17e): the views by level, by object, by area and «ready for
delivery», the detail under a row, «Fix» and the eye on the row and what they ask, the filters «This phase» and
«This object», the counts in the head that lead to the section and never change the panel's height. The panel is
made alone with five items about the shed of _fixtures and the names the window gives it (object_names); what the
window does with what the panel asks (the views, the tree, the status bar, the settings) is in
finestra/test_checks_views.py. PySide6 and a display (offscreen will do)."""

import unittest

import _setup
from _fixtures import capannone

from meridiana.checks import Item

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

USER = 0x0100           # Qt.ItemDataRole.UserRole: the row's index into the items


class ChecksPanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        cls.look = _setup.meridiana_look()                  # the font and the sheet of the window's panels

    def setUp(self):
        from meridiana.ui.checks_page import ChecksPage, object_names
        self.project = capannone()
        self.sid, self.bid = self.project.subfields[0].id, self.project.buildings[0].id
        self.names = object_names(self.project)
        self.page = ChecksPage()
        self.addCleanup(_setup.dispose, self.page)
        self.page.resize(900, 300)
        self.page.show()
        self.items = [Item("warn", "layout", "a", target=("subfield", self.sid), detail="Why a, and what to do."),
                      Item("fail", "layout", "b", target=("subfield", self.sid), detail="Why b, and what to do."),
                      Item("info", "layout", "c", target=("building", self.bid)),
                      Item("ok", "strings", "d", target=("phase", "production")),
                      Item("warn", "connection", "e", target=("site",), detail="Why e.")]
        self.show(self.items)

    def show(self, items, extras=()):
        self.page.show_items(items, extras, self.names)
        self.app.processEvents()

    def rows(self):
        page = self.page
        return [page.tree.topLevelItem(g).child(r) for g in range(page.tree.topLevelItemCount())
                for r in range(page.tree.topLevelItem(g).childCount())]

    def shown(self):
        return sorted(self.page.all[r.data(1, USER)].text for r in self.rows()
                      if not r.isHidden() and not r.parent().isHidden())

    def row_of(self, text):
        return next(r for r in self.rows() if self.page.all[r.data(1, USER)].text == text)

    def heads(self):
        page = self.page
        return [page.tree.topLevelItem(g) for g in range(page.tree.topLevelItemCount())]

    # ----- the sections and the views

    def test_by_level_is_the_default_with_what_passed_closed(self):
        from PySide6.QtCore import Qt

        from meridiana.ui.sections import SECTION_ROLE
        page = self.page
        self.assertEqual(page.view, "level")
        self.assertEqual(page.view_button.text(), "By level")
        heads = self.heads()
        self.assertEqual([h.text(1) for h in heads], ["To fix", "To check", "To know", "Passed"])
        self.assertEqual([h.data(1, SECTION_ROLE) for h in heads], [1, 2, 1, 1])
        self.assertEqual([h.isExpanded() for h in heads], [True, True, True, False])
        self.assertEqual([h.text(0) for h in heads], ["✘", "⚠", "ℹ", "✔"])
        self.assertTrue(all(not (h.flags() & Qt.ItemFlag.ItemIsSelectable) for h in heads))      # never selectable
        self.assertEqual([self.items[r.data(1, USER)].text for r in self.rows()], ["b", "a", "e", "c", "d"])

    def test_by_object_and_by_area_from_the_menu_keep_the_item_in_hand(self):
        from meridiana.ui.sections import SECTION_ROLE
        page = self.page
        page.tree.setCurrentItem(self.row_of("e"))
        heard = []
        page.viewChanged.connect(heard.append)
        action = next(a for a in page.view_actions.actions() if a.data() == "object")
        action.trigger()
        self.assertEqual((page.view, heard), ("object", ["object"]))      # told, for the settings (the window)
        heads = self.heads()
        self.assertEqual([h.text(1) for h in heads], ["Sud", "Site: Prova", "Capannone"])  # the worst object first
        self.assertEqual([h.data(1, SECTION_ROLE) for h in heads], [2, 2, 1])
        self.assertFalse(heads[0].icon(0).isNull())                      # the icon of the kind, as in the tree
        self.assertEqual(heads[0].text(2), "✘ 1  ⚠ 1")                  # the counts by level beside the name
        self.assertEqual(page.selected().text, "e")                      # still in hand
        page.set_view("area")
        self.assertEqual([h.text(1) for h in self.heads()], ["Layout", "Strings (CEI 64-8/7)", "Connection"])
        self.assertEqual(page.selected().text, "e")
        self.assertEqual(page.view_button.text(), "By area")
        self.assertEqual([a.isChecked() for a in page.view_actions.actions()], [False, False, True, False])

    def test_ready_for_delivery_shows_what_to_look_at_before_the_report(self):
        from meridiana.ui.sections import SECTION_ROLE
        page = self.page
        extras = [Item("info", "defaults", "Price: F1 = 0,25 €/kWh", "indicative default", ("phase", "economics"),
                       detail="Check it.")]
        items = self.items + [Item("info", "consumption", "guessed", target=("phase", "consumption"))]
        self.show(items, extras)
        self.assertEqual(self.shown(), ["a", "b", "c", "d", "e", "guessed"])       # by level: no defaults
        page.set_view("delivery")
        heads = self.heads()
        self.assertEqual([h.text(1) for h in heads], ["To fix", "To check", "Values still at their default",
                                                      "Estimates in use"])
        self.assertEqual([h.data(1, SECTION_ROLE) for h in heads], [1, 2, 1, 1])
        self.assertEqual(self.shown(), ["Price: F1 = 0,25 €/kWh", "a", "b", "e", "guessed"])
        self.assertEqual(page.title("Checks"), "Checks (3)")            # the defaults are not checks
        self.assertEqual(len(page.items), 6)

    # ----- the rows: the detail, «Fix», the eye

    def test_the_arrow_opens_the_detail_as_a_row_under_the_item(self):
        from PySide6.QtCore import Qt

        from meridiana.ui.checks_page import DETAIL_ROLE
        page = self.page
        b = self.row_of("b")
        self.assertEqual(b.childCount(), 1)
        self.assertFalse(b.isExpanded())
        detail = b.child(0)
        self.assertEqual(detail.text(0), "Why b, and what to do.")
        self.assertTrue(detail.data(0, DETAIL_ROLE))
        self.assertTrue(detail.isFirstColumnSpanned())
        self.assertFalse(detail.flags() & Qt.ItemFlag.ItemIsSelectable)  # not selectable
        self.assertEqual(self.row_of("c").childCount(), 0)               # no detail, no arrow
        b.setExpanded(True)
        self.app.processEvents()
        self.assertGreater(page.tree.visualItemRect(detail).height(), 10)
        self.assertEqual(page.tree.visualItemRect(detail).width(), page.tree.viewport().width()
                         - page.tree.visualItemRect(detail).x())          # spans the columns
        self.show(self.items)                                            # new results: the detail stays open
        self.assertTrue(self.row_of("b").isExpanded())
        self.row_of("b").setExpanded(False)
        self.show(self.items)
        self.assertFalse(self.row_of("b").isExpanded())

    def test_the_arrow_only_opens_and_closes_the_detail_at_once(self):
        """R86 (Daniel, 24/10/2026): the arrow neither takes the item in hand nor moves the list or the views, and
        the detail opens at once, under the item's text."""
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        page = self.page
        self.assertFalse(page.tree.isAnimated())
        a, b = self.row_of("a"), self.row_of("b")
        page.tree.setCurrentItem(a)
        asked = []
        page.focusRequested.connect(asked.append)
        rect = page.tree.visualItemRect(b)
        arrow = QPoint(rect.left() - page.tree.indentation() // 2, rect.center().y())
        scroll = page.tree.verticalScrollBar().value()
        QTest.mouseClick(page.tree.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, arrow)
        self.assertTrue(b.isExpanded())
        self.assertIs(page.tree.currentItem(), a)                         # the item in hand stays
        self.assertEqual(asked, [])                                       # the views stay
        self.assertEqual(page.tree.verticalScrollBar().value(), scroll)
        detail = page.tree.visualItemRect(b.child(0))
        self.assertGreater(detail.height(), 10)
        QTest.mouseClick(page.tree.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, arrow)
        self.assertFalse(b.isExpanded())
        QTest.mouseClick(page.tree.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         page.tree.visualItemRect(b).center())             # on the text: in hand, as before
        self.assertIs(page.tree.currentItem(), b)

    def test_a_long_detail_wraps_to_the_width(self):
        page = self.page
        long = Item("fail", "layout", "long", target=("subfield", self.sid), detail="word " * 120)
        self.show(self.items + [long])
        row = self.row_of("long")
        row.setExpanded(True)
        self.app.processEvents()
        one_line = page.tree.fontMetrics().height()
        self.assertGreater(page.tree.visualItemRect(row.child(0)).height(), 3 * one_line)

    def test_fix_on_the_row_asks_for_the_fix_of_that_item(self):
        page = self.page
        self.items[1].fix, self.items[1].fix_label = ("compute",), "Compute"
        self.show(self.items)
        n = next(k for k, i in enumerate(self.items) if i.text == "b")
        buttons = page.row_buttons(n)
        self.assertIn("fix", buttons)
        self.assertEqual(buttons["fix"].toolTip(), "Compute")
        self.assertNotIn("fix", page.row_buttons(0))                     # «a» has no fix: no button
        heard = []
        page.fix.connect(heard.append)
        buttons["fix"].click()
        self.assertEqual([h.text for h in heard], ["b"])
        self.assertEqual(page.selected().text, "b")                      # in hand, the views follow
        self.assertTrue(page.fix_button.isEnabled())                     # the keyboard's button follows too

    def test_the_fix_of_the_item_in_hand_is_asked_or_its_absence_said(self):
        """Study 12, section 5 (VS Code's quick fix), design document 3.8: what Ctrl+. asks of the panel (the key
        itself is the window's, in finestra)."""
        page = self.page
        self.items[1].fix, self.items[1].fix_label = ("compute",), "Compute"
        self.show(self.items)
        heard = []
        page.fix.connect(heard.append)
        page.tree.setCurrentItem(self.row_of("a"))                  # no fix: said, nothing asked
        page.apply_fix()
        self.assertEqual(heard, [])
        self.assertIn("no fix", page.summary.text())
        page.tree.setCurrentItem(self.row_of("b"))
        page.apply_fix()
        self.assertEqual([h.text for h in heard], ["b"])

    def test_the_eye_asks_to_show_the_object_and_is_only_on_objects(self):
        page = self.page
        n = next(k for k, i in enumerate(self.items) if i.text == "c")
        buttons = page.row_buttons(n)
        self.assertIn("eye", buttons)
        self.assertFalse(buttons["eye"].icon().isNull())
        self.assertEqual(page.row_buttons(3), {})                        # «d» is about a page: no eye
        self.assertNotIn("eye", page.row_buttons(4))                     # «e» is about the site: no eye
        heard = []
        page.focusRequested.connect(heard.append)
        buttons["eye"].click()
        self.assertEqual(heard, [("building", self.bid)])

    def test_the_object_in_hand_has_its_items_in_bold(self):
        page = self.page
        page.show_related("subfield", self.sid)                          # what the window does at a selection
        self.assertEqual(page.selected().target, ("subfield", self.sid))
        bold = {self.items[r.data(1, USER)].text: r.font(1).bold() for r in self.rows()}
        self.assertEqual(bold, {"a": True, "b": True, "c": False, "d": False, "e": False})

    def test_a_double_click_asks_to_lead_to_the_place(self):
        page = self.page
        heard = []
        page.navigate.connect(heard.append)
        page._open(self.row_of("d"), 1)
        self.assertEqual(heard, [("phase", "production")])

    # ----- the filters: this object, this phase

    def test_the_checks_of_one_object_alone_and_back(self):
        page = self.page
        page.show_subset(("subfield", self.sid), "Sud")                  # what a mark of the tree asks
        self.assertEqual(self.shown(), ["a", "b"])
        self.assertTrue(page.object_button.isChecked())
        self.assertIn("Only the checks of Sud;", page.object_button.toolTip())   # the name without the tail
        self.assertIn("Only the checks of Sud: 2.", page.summary.text())
        self.show(self.items)                              # new results: still that object's
        self.assertEqual(self.shown(), ["a", "b"])
        page.object_button.click()                         # off: every object's
        self.assertEqual(self.shown(), ["a", "b", "c", "d", "e"])
        self.assertFalse(page.object_button.isChecked())

    def test_this_object_follows_the_object_in_hand(self):
        page = self.page
        page.show_related("building", self.bid)
        page.object_button.click()
        self.assertEqual(self.shown(), ["c"])
        self.assertIn("Only the checks of Capannone: 1.", page.summary.text())
        page.show_related("subfield", self.sid)            # another object in hand: its checks
        self.assertEqual(self.shown(), ["a", "b"])
        self.assertIn("Sud", page.object_button.toolTip())
        page.object_button.click()
        self.assertEqual(self.shown(), ["a", "b", "c", "d", "e"])

    def test_this_object_with_nothing_selected_says_so(self):
        page = self.page
        page.related = ()
        page.object_button.click()
        self.assertFalse(page.object_button.isChecked())
        self.assertIn("Select an object", page.summary.text())
        self.assertEqual(self.shown(), ["a", "b", "c", "d", "e"])

    def test_this_phase_keeps_what_is_acted_on_in_the_phase_shown(self):
        page = self.page
        page.phase_button.click()
        self.assertEqual(self.shown(), ["a", "b", "c", "e"])             # the model: objects and the site
        self.assertIn("Only this phase.", page.summary.text())
        page.set_phase("plant")                                          # the areas it declares: strings, connection
        self.assertEqual(self.shown(), ["d", "e"])
        page.set_phase("production")
        self.assertEqual(self.shown(), ["d"])
        self.assertEqual([h.isHidden() for h in self.heads()], [True, True, True, False])
        self.show(self.items + [Item("info", "import", "x")])          # of every phase: shown in each
        self.assertEqual(self.shown(), ["d", "x"])
        page.phase_button.click()
        self.assertEqual(self.shown(), ["a", "b", "c", "d", "e", "x"])

    def test_a_filter_that_hides_the_item_in_hand_moves_the_hand_to_one_shown(self):
        page = self.page
        self.items[1].fix, self.items[1].fix_label = ("compute",), "Compute"     # «b», to fix, with a fix
        self.show(self.items)
        page.tree.setCurrentItem(self.row_of("b"))
        self.assertTrue(page.fix_button.isEnabled())
        page.set_phase("production")
        page.phase_button.click()                          # «b» hidden: «Fix» must not offer its fix
        self.assertEqual(page.selected().text, "d")
        self.assertFalse(page.fix_button.isEnabled())
        self.assertEqual(page.fix_label.text(), "")
        page.set_phase("consumption")                      # nothing shown: nothing in hand
        self.assertEqual(self.shown(), [])
        self.assertIsNone(page.selected())
        self.assertFalse(page.fix_button.isEnabled())

    def test_there_are_no_filters_by_level_any_more(self):
        page = self.page
        self.assertFalse(hasattr(page, "filters"))
        self.assertFalse(hasattr(page, "levels"))
        self.assertFalse(hasattr(page, "only"))

    # ----- the counts lead to the section

    def test_new_counts_do_not_change_the_height_the_panel_asks_for(self):
        """The counts in the head are one line: wrapped, a count with its link made the card 18 px taller and
        the views jumped at each new list (found by test_viewbar; the dock in the window: finestra)."""
        page = self.page
        before = (page.sizeHint().height(), page.minimumSizeHint().height(), page.summary.sizeHint().height())
        many = [Item(lv, "layout", f"{lv} {k}", target=("subfield", self.sid)) for lv in ("fail", "warn", "info", "ok")
                for k in range(12)]
        for items in (many, [], self.items):
            self.show(items)
            self.assertEqual((page.sizeHint().height(), page.minimumSizeHint().height(),
                              page.summary.sizeHint().height()), before)

    def test_the_counts_in_the_head_are_links_to_the_sections(self):
        """The counts as pills with their mark (the target of 24/10/2026), each leading to its section."""
        page = self.page
        self.assertEqual({lv: b.text() for lv, b in page.counts.items()}, {"fail": "1", "warn": "2", "info": "1", "ok": "1"})
        self.assertEqual(page.counts["warn"].toolTip(), "2 to check")
        self.assertFalse(page.counts["fail"].icon().isNull())
        page.set_view("area")
        page.counts["ok"].click()
        self.assertEqual(page.view, "level")                             # the section is in the view by level
        passed = self.heads()[3]
        self.assertTrue(passed.isExpanded())
        self.assertEqual(page.selected().text, "d")
        self.show([])
        self.assertEqual([b.text() for b in page.counts.values()], ["0", "0", "0", "0"])
        self.assertFalse(any(b.isEnabled() for b in page.counts.values()))   # nothing to lead to

    def test_going_to_a_section_takes_its_first_item_with_nothing_hidden(self):
        page = self.page
        page.tree.setCurrentItem(self.row_of("c"))
        page.go_to("warn")                                               # what a count of the status bar asks
        self.assertEqual(self.shown(), ["a", "b", "c", "d", "e"])         # nothing hidden
        self.assertEqual(page.selected().text, "a")                      # the first of the section
        self.assertIs(page.tree.currentItem().parent(), self.heads()[1])

    def test_the_panel_has_the_sections_of_the_projects_tree(self):
        """The same delegate as the project's tree (design 3.8): the sections by level, by area with their
        counts, never selectable, the worst mark of the area on its head."""
        from PySide6.QtCore import Qt

        from meridiana.ui.sections import SECTION_ROLE, SectionDelegate
        page = self.page
        self.assertIsInstance(page.tree.itemDelegate(), SectionDelegate)
        self.show([Item("warn", "layout", "a", target=("subfield", self.sid)),
                   Item("fail", "layout", "b", target=("subfield", self.sid)),
                   Item("info", "connection", "c", target=("building", self.bid))])
        self.assertEqual([g.text(1) for g in self.heads()], ["To fix", "To check", "To know"])   # by level (F2)
        self.assertEqual([g.data(1, SECTION_ROLE) for g in self.heads()], [1, 1, 1])
        page.set_view("area")
        self.assertEqual([g.text(1) for g in self.heads()], ["Layout", "Connection"])
        self.assertEqual([g.data(1, SECTION_ROLE) for g in self.heads()], [2, 1])
        self.assertTrue(all(not (g.flags() & Qt.ItemFlag.ItemIsSelectable) for g in self.heads()))
        self.assertEqual(self.heads()[0].text(0), "✘")                 # the worst mark of the area stays


if __name__ == "__main__":
    unittest.main()
