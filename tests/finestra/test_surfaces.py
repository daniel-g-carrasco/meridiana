"""The panels as cards and the views with rounded corners in the window (task 17a, step 2: study 17, A3 and R2;
design document 3.2 and 3.7), and the project's tree with its sections and the pills of the marks (study 17, T2).
The widths of the plan and the Checks panel's sections are in widget/test_plan.py and widget/test_checks_page.py,
the result tiles in widget/test_result_tiles.py. PySide6 and a display (offscreen will do)."""

import unittest

import _setup
from _fixtures import capannone

from meridiana import config

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Cards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, cfg=config.Config(background="none", theme="light", accent="bronze"), size=(1400, 900))

    def test_every_panel_is_a_card_eight_pixels_from_the_window_and_its_neighbours_with_the_views_rounded(self):
        """The target of 24/10/2026 (docs/studio/19-grafica): EDGE from the window's sides, GAP between two cards
        and from the bars; the phases' header above the panels; the right column the whole height, Properties
        and Help; the checks under the tree and the views."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDockWidget

        from meridiana.ui.cards import EDGE, GAP, VIEW_RADIUS, CardDock, CardTitle, Corner, arena
        win = self.win
        project, properties = win.docks
        checks, help_card = win.checks_dock, win.help_dock
        for dock in (project, properties, checks, help_card, win.assistant_dock):
            self.assertIsInstance(dock, CardDock)
            self.assertIsInstance(dock.titleBarWidget(), CardTitle)
        a = arena(win)
        top = win.menuWidget().layout()
        self.assertIn(win.tabs.header, [top.itemAt(i).widget() for i in range(top.count())])    # the phases above
        self.assertFalse(win.menuBar().isVisible())             # the menus hidden until Alt (R53)
        self.assertGreater(a.top(), 60)                         # under the menu bar, the phases and their bar
        self.assertLess(a.bottom(), win.height() - 10)          # above the status bar
        # the project's card: the edge on the left (the window's side), none on the right (the separator is the gap)
        card = project.card_rect()
        self.assertEqual(card.left(), EDGE)
        self.assertEqual(card.right(), project.width() - 1)
        self.assertEqual(card.top(), GAP)                       # under the bar of the phase
        self.assertEqual(project.contentsMargins().left(), EDGE + 6)
        self.assertEqual(project.contentsMargins().right(), 6)
        # the properties' card: the edge on the right, the column from the top to the bottom, the help under it
        card = properties.card_rect()
        self.assertEqual(card.right(), properties.width() - 1 - EDGE)
        self.assertEqual(card.left(), 0)
        self.assertEqual(help_card.x(), properties.x())
        self.assertGreater(help_card.y(), properties.y())
        self.assertIs(help_card.widget(), win.help_box)
        self.assertIs(properties.widget(), win.inspector)
        self.assertEqual(help_card.y() + help_card.card_rect().bottom(), a.bottom() - GAP)  # above the status bar
        # the checks' card under the tree and the views: the gap below and the edge on the left, the separator
        # above and on the right (the right column)
        card = checks.card_rect()
        self.assertEqual(card.bottom(), checks.height() - 1 - GAP)
        self.assertEqual((card.left(), card.right(), card.top()), (EDGE, checks.width() - 1, 0))
        self.assertLess(checks.x() + checks.width(), properties.x())
        # the separators of the main window are 8 px: the gap between a card and the central widget
        self.assertEqual(win.tabs.x() - (project.x() + project.width()), GAP)
        # the title inside the card, 12 px from its edge, in the text's colour
        title = project.titleBarWidget()
        self.assertEqual(title.title_font().capitalization(), title.title_font().Capitalization.MixedCase)
        self.assertEqual(title.colours["text"], win.theme.tokens["text"])
        self.assertTrue(title.close_button.isVisible())
        # the central widget keeps the edge where no card stands between it and the window's side
        tabs = win.tabs
        self.assertEqual((tabs.contentsMargins().left(), tabs.contentsMargins().right()), (0, 0))
        project.hide()
        self.app.processEvents()
        self.assertEqual(tabs.contentsMargins().left(), EDGE)
        project.show()
        self.app.processEvents()
        self.assertEqual(tabs.contentsMargins().left(), 0)
        # a card dragged out is a plain dock again, and a card once back
        project.setFeatures(project.features() | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        project.setFloating(True)
        self.app.processEvents()
        self.assertTrue(project.isFloating())
        self.assertEqual(project.contentsMargins().left(), 0)
        self.assertEqual(project.card_rect(), project.rect())
        self.assertFalse(project.grab().isNull())               # drawn as Qt draws a floating dock
        project.setFloating(False)
        self.app.processEvents()
        self.assertGreater(project.contentsMargins().left(), 0)
        # the cards follow the theme: their line on the bare floor, no shadow (Daniel, 24/10/2026)
        t = win.theme.tokens
        self.assertEqual(project.colours["bg"], t["panel"])
        self.assertEqual(project.colours["line"], t["line"])
        self.assertFalse(project.dark)
        self.app.processEvents()
        image = win.grab().toImage()
        x, y = project.x() + project.card_rect().left() - 3, project.y() + project.height() // 2
        dpr = image.devicePixelRatio()                  # on a real screen the grab is in device pixels
        x, y = int((x + 0.5) * dpr), int((y + 0.5) * dpr)   # the middle of the logical pixel
        self.assertEqual(image.pixelColor(x, y).name(), t["window"])        # the floor as it is beside the card
        win._appearance("dark", "bronze", "meridiana")
        d = win.theme.tokens
        self.assertEqual(project.colours["bg"], d["panel"])
        self.assertTrue(project.dark)
        image = win.grab().toImage()
        self.assertEqual(image.devicePixelRatio(), dpr)
        self.assertEqual(image.pixelColor(x, y).name(), d["window"])
        win._appearance("light", "bronze", "meridiana")
        # the views: their four corners rounded, drawn in the card's colour (Daniel, 24/10/2026)
        for view in (win.plan, win.view3d):
            with self.subTest(view=type(view).__name__):
                corners = view.findChildren(Corner)
                self.assertEqual(len(corners), 4)
                spots = {(c.geometry().left(), c.geometry().top()) for c in corners}
                w, h = view.width() - VIEW_RADIUS, view.height() - VIEW_RADIUS
                self.assertEqual(spots, {(0, 0), (w, 0), (0, h), (w, h)})
                self.assertTrue(all(c.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                                    for c in corners))


class Tree(unittest.TestCase):
    """The project's tree with sections (study 17, T2)."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.checks import Item
        _setup.window(self, capannone(), config.Config(background="none", theme="light", accent="bronze"),
                      size=(1300, 850))
        self.sid = self.win.project.subfields[0].id
        self.bid = self.win.project.buildings[0].id
        # the plant's strings come back after the layout and show the checks again (task 16d): before the items
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.win.plant_pending()))
        self.app.processEvents()
        self.items = [Item("warn", "layout", "a", target=("subfield", self.sid)),
                      Item("fail", "layout", "b", target=("subfield", self.sid)),
                      Item("info", "connection", "c", target=("building", self.bid))]
        self.win.checks_page.show_items(self.items)
        self.win._show_marks()
        self.app.processEvents()

    def test_three_sections_with_their_counts_never_selected_and_the_pills_of_the_marks(self):
        from PySide6.QtCore import Qt

        from meridiana.ui.marks import MARK_ROLE, MarkDelegate
        from meridiana.ui.sections import SECTION_ROLE, TAIL_ROLE, SectionDelegate
        win, tree = self.win, self.win.tree
        root = tree.topLevelItem(0)
        heads = [root.child(i) for i in range(root.childCount())]
        self.assertEqual([h.text(0) for h in heads], ["Buildings", "Sub-fields", "Exclusions"])
        self.assertEqual([h.data(0, SECTION_ROLE) for h in heads], [1, 1, 0])
        self.assertEqual([h.data(1, SECTION_ROLE) for h in heads], [1, 1, 0])
        self.assertTrue(all(not (h.flags() & Qt.ItemFlag.ItemIsSelectable) for h in heads))
        self.assertIsInstance(tree.itemDelegateForColumn(0), SectionDelegate)
        # a header is taller than an object's row by the air above it, and the object's count is a muted tail
        sub = heads[1].child(0)
        self.assertEqual(sub.text(0), "Sud · 128")
        self.assertEqual(sub.data(0, TAIL_ROLE), " · 128")
        self.assertIsNone(sub.data(0, SECTION_ROLE))
        self.assertGreater(tree.visualItemRect(heads[1]).height(), tree.visualItemRect(sub).height() + 4)
        # The pills carry the counts with the shared quiet status backgrounds.
        self.assertEqual(heads[1].data(1, MARK_ROLE), ("fail", 2))
        self.assertEqual(heads[0].data(1, MARK_ROLE), ("info", 1))
        self.assertIsNone(heads[2].data(1, MARK_ROLE))
        self.assertEqual(root.data(1, MARK_ROLE), ("fail", 3))
        self.assertIsInstance(tree.itemDelegateForColumn(1), MarkDelegate)
        self.app.processEvents()
        shot = tree.viewport().grab().toImage()
        rect = tree.visualItemRect(heads[1])
        dpr = shot.devicePixelRatio()
        row = shot.copy(round(tree.header().sectionPosition(1) * dpr), round(rect.y() * dpr),
                        round(tree.header().sectionSize(1) * dpr), round(rect.height() * dpr))
        from meridiana.ui import status_pill
        ground, ink, _ = status_pill.colours("fail", tree.palette())
        tinted = sum(1 for x in range(row.width()) for y in range(row.height()) if row.pixelColor(x, y) == ground)
        self.assertGreater(tinted, 20 * dpr * dpr)
        self.assertGreater(abs(ground.lightness() - ink.lightness()), 80)
        # a click on a header does not move the selection; a click on the object does; the views lead the tree
        win._select("subfield", self.sid)
        win._tree_clicked(heads[0], 0)
        self.assertEqual(win.selection, ("subfield", self.sid))
        self.assertEqual(tree.currentItem().data(0, Qt.ItemDataRole.UserRole), ("subfield", self.sid))
        win._tree_clicked(heads[0].child(0), 0)
        self.assertEqual(win.selection, ("building", self.bid))
        win.plan.picked.emit("subfield", self.sid)
        self.assertEqual(tree.currentItem().data(0, Qt.ItemDataRole.UserRole), ("subfield", self.sid))
        # a click on the pill of a section shows the checks of what is inside, without selecting the header
        win._tree_clicked(heads[1], 1)
        shown = [win.checks_page.items[n].text for n in range(len(self.items)) if not win.checks_page._hidden(n)]
        self.assertEqual(shown, ["a", "b"])


if __name__ == "__main__":
    unittest.main()
