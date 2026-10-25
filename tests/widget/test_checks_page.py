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
        from meridiana.ui.checks_page import SYMBOL_ROLE           # the window's symbols (R138), not characters
        self.assertEqual([h.data(0, SYMBOL_ROLE) for h in heads], ["stop", "warning", "info", "check"])
        self.assertFalse(any(h.icon(0).isNull() for h in heads))
        self.assertEqual([r.data(0, SYMBOL_ROLE) for r in self.rows()], ["stop", "warning", "warning", "info", "check"])
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

    def test_a_click_on_the_row_or_its_arrow_only_opens_and_closes_the_detail_at_once(self):
        """R86 (Daniel, 24/10/2026) and R125 (25/10: «togli la possibilità di poterle selezionare»): the arrow and the
        row's text open and close the detail at once, under the item's text, and do nothing else: nothing selected,
        the list and the views where they were; a double click opens it once."""
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QAbstractItemView
        page = self.page
        self.assertFalse(page.tree.isAnimated())
        self.assertEqual(page.tree.selectionMode(), QAbstractItemView.SelectionMode.NoSelection)
        b = self.row_of("b")
        asked = []
        page.focusRequested.connect(asked.append)
        page.navigate.connect(asked.append)
        rect = page.tree.visualItemRect(b)
        arrow = QPoint(rect.left() - page.tree.indentation() // 2, rect.center().y())
        scroll = page.tree.verticalScrollBar().value()
        QTest.mouseClick(page.tree.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, arrow)
        self.assertTrue(b.isExpanded())
        self.assertEqual(page.tree.verticalScrollBar().value(), scroll)
        detail = page.tree.visualItemRect(b.child(0))
        self.assertGreater(detail.height(), 10)
        QTest.mouseClick(page.tree.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, arrow)
        self.assertFalse(b.isExpanded())
        text = page.tree.visualItemRect(b).center()
        QTest.mouseClick(page.tree.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, text)
        self.assertTrue(b.isExpanded())                                   # the text opens it too
        QTest.mouseClick(page.tree.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, text)
        self.assertFalse(b.isExpanded())
        # a double click as the widgets get it (QTBUG-25831: press, release, double click, release; QTest's own
        # sends a second press)
        from PySide6.QtCore import QEvent, QPointF
        from PySide6.QtGui import QMouseEvent
        QTest.mouseClick(page.tree.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, text)
        at = QPointF(text)
        self.app.sendEvent(page.tree.viewport(), QMouseEvent(
            QEvent.Type.MouseButtonDblClick, at, page.tree.viewport().mapToGlobal(at), Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        self.assertTrue(b.isExpanded())                                   # a double click: opened once
        self.assertEqual(page.tree.selectedItems(), [])                   # nothing ever selected
        self.assertEqual(asked, [])                                       # the views stay
        a = self.row_of("a")                                              # no detail: a click does nothing
        QTest.mouseClick(page.tree.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         page.tree.visualItemRect(self.row_of("c")).center())
        self.assertEqual((page.tree.selectedItems(), asked, a.isExpanded()), ([], [], False))

    def test_the_item_under_the_pointer_is_tinted_whole_and_a_click_on_its_detail_does_nothing(self):
        """R153 (Daniel, 25/10/2026: «di modo che cambia solo leggermente colore di tutto il suo contenitore ... quando
        clicco nel testo della sua espansione è come se un pezzetto a sinistra dell'evidenziatura si cancellasse»):
        the row and its open detail are one container under the pointer; a click on the detail moves nothing."""
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtGui import QColor
        from PySide6.QtTest import QTest
        page = self.page
        b = self.row_of("b")
        b.setExpanded(True)
        self.app.processEvents()
        detail = page.tree.visualItemRect(b.child(0))
        QTest.mouseMove(page.tree.viewport(), detail.center())
        self.app.processEvents()
        self.assertIs(page.tree.hover_item, b)                               # the detail counts as its item
        grab = page.tree.viewport().grab().toImage()
        ratio = page.tree.viewport().devicePixelRatioF()
        at = lambda p: QColor(grab.pixel(int(p.x() * ratio), int(p.y() * ratio)))      # noqa: E731
        row = page.tree.visualItemRect(b)
        left = QPoint(14, row.center().y())                                 # the card's left, not a pill's
        other = page.tree.visualItemRect(self.row_of("e"))
        self.assertNotEqual(at(left).name(), at(QPoint(14, other.center().y())).name())
        self.assertEqual(at(left).name(), at(QPoint(14, detail.center().y())).name())    # row and detail alike
        current = page.tree.currentItem()
        QTest.mouseClick(page.tree.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         detail.center())
        self.assertIs(page.tree.currentItem(), current)
        self.assertTrue(b.isExpanded())

    def test_the_rows_are_tall_enough_for_their_buttons(self):
        """R124 (Daniel, 25/10/2026: «il tasto Correggi è tagliato in basso? please, dai maggiore altezza alle
        singole righe»): every item's row is ROW_HEIGHT at least, and «Fix…» and the eye stand inside it."""
        from meridiana.ui.checks_page import ROW_HEIGHT
        page = self.page
        self.items[1].fix, self.items[1].fix_label = ("compute",), "Compute"
        self.show(self.items)
        for r in self.rows():
            if not r.isHidden() and not r.parent().isHidden() and r.parent().isExpanded():
                self.assertGreaterEqual(page.tree.visualItemRect(r).height(), ROW_HEIGHT)
        n = next(k for k, i in enumerate(self.items) if i.text == "b")
        rect = page.tree.visualItemRect(page.rows[n])
        for b in page.row_buttons(n).values():
            top = b.mapTo(page.tree.viewport(), b.rect().topLeft()).y()
            self.assertGreaterEqual(top, rect.top() + 2, b.objectName())
            self.assertLessEqual(top + b.height(), rect.bottom() - 1, b.objectName())

    def test_the_source_is_measured_on_every_row_the_closed_sections_too(self):
        """R128 (Daniel, 25/10/2026: «si vedono solo le lettere iniziali con puntini puntini»): Qt measured only the
        rows shown, none while the sections were closed, and the sources came out as «C…»."""
        from PySide6.QtGui import QFontMetrics
        page = self.page
        page.resize(1400, 300)
        source = "DM 37/2008 (testo integrato DM 130/2025) art. 5 c. 2"
        self.show(self.items + [Item("ok", "layout", "p", source=source, target=("site",))])   # PASSED, closed
        self.assertFalse(self.heads()[3].isExpanded())
        row = self.row_of("p")
        self.assertGreaterEqual(page.tree.header().sectionSize(2),
                                QFontMetrics(row.font(2)).horizontalAdvance(source))

    def test_an_open_detail_wraps_at_a_measure_not_at_the_panels_edge(self):
        """R129 (Daniel, 25/10/2026: «ci sta che i testi nelle righe espanse vadano a capo a un certo punto»)."""
        from PySide6.QtGui import QFontMetrics

        from meridiana.ui.checks_page import DETAIL_CHARS, ChecksDelegate
        page = self.page
        page.resize(2600, 400)
        self.show(self.items + [Item("fail", "layout", "long", target=("subfield", self.sid), detail="word " * 120)])
        row = self.row_of("long")
        row.setExpanded(True)
        self.app.processEvents()
        detail = page.tree.indexFromItem(row.child(0))
        option = page.tree.viewOptions() if hasattr(page.tree, "viewOptions") else None
        from PySide6.QtWidgets import QStyleOptionViewItem
        option = option or QStyleOptionViewItem()
        option.initFrom(page.tree)
        option.rect = page.tree.visualRect(detail)
        delegate = page.tree.itemDelegate()
        width = delegate._detail_rect(detail, option).width()
        measure = QFontMetrics(ChecksDelegate.detail_font(page.tree.font())).averageCharWidth() * DETAIL_CHARS
        self.assertLessEqual(width, measure)
        self.assertLess(width, page.tree.viewport().width() * 0.6)

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
        self.assertEqual(buttons["fix"].text(), "Fix…")                  # «…»: shown before it is kept (R126)
        self.assertTrue(buttons["fix"].toolTip().startswith("Compute: shown first"))
        self.assertNotIn("fix", page.row_buttons(0))                     # «a» has no fix: no button
        heard = []
        page.fix.connect(heard.append)
        buttons["fix"].click()
        self.assertEqual([h.text for h in heard], ["b"])
        self.assertEqual(page.selected().text, "b")                      # the keyboard goes on from it
        self.assertEqual(page.tree.selectedItems(), [])                  # but nothing is selected (R125)
        self.assertFalse(hasattr(page, "fix_button"))                    # no button below for a row unseen

    def test_a_fix_is_shown_before_it_is_kept(self):
        """R126 (Daniel, 25/10/2026: «"correggi" dovrebbe presentare le correzioni proposte prima di applicarle
        all'istante»): the window makes it as a preview and the panel asks; Keep and Take back are heard."""
        page = self.page
        self.assertFalse(page.previewing())
        page.show_preview("Lay the modules", applied=True)
        self.assertTrue(page.previewing())
        self.assertIn("Lay the modules", page.preview_text.text())
        self.assertEqual((page.preview_keep.text(), page.preview_drop.text()), ("Keep", "Take back"))
        heard = []
        page.previewAnswered.connect(heard.append)
        page.preview_drop.click()
        page.preview_keep.click()
        self.assertEqual(heard, [False, True])
        page.show_preview("Compute", applied=False)                      # not an edit: it waits for Apply
        self.assertEqual((page.preview_keep.text(), page.preview_drop.text()), ("Apply", "Cancel"))
        page.end_preview()
        self.assertFalse(page.previewing())

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

    def test_the_eye_asks_to_show_where_the_problem_is(self):
        """R127 (Daniel, 25/10/2026: «l'occhio non porta direttamente alla vista 2d / 3d dove si trova il
        problema»): on every item with a place, an object, a phase or the site; Enter on a row asks the same."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        page = self.page
        heard = []
        page.focusRequested.connect(heard.append)
        for text in ("c", "d", "e"):
            n = next(k for k, i in enumerate(self.items) if i.text == text)
            eye = page.row_buttons(n)["eye"]
            self.assertFalse(eye.icon().isNull())
            eye.click()
        self.assertEqual(heard, [("building", self.bid), ("phase", "production"), ("site",)])
        self.assertIn("Production", page.row_buttons(3)["eye"].toolTip())
        self.assertEqual(page.tree.selectedItems(), [])
        page.tree.setFocus()
        page.tree.setCurrentItem(self.row_of("c"))
        QTest.keyClick(page.tree, Qt.Key.Key_Return)
        self.assertEqual(heard[-1], ("building", self.bid))

    def test_the_object_in_hand_has_its_items_in_bold(self):
        page = self.page
        page.show_related("subfield", self.sid)                          # what the window does at a selection
        self.assertEqual(page.selected().target, ("subfield", self.sid))
        bold = {self.items[r.data(1, USER)].text: r.font(1).bold() for r in self.rows()}
        self.assertEqual(bold, {"a": True, "b": True, "c": False, "d": False, "e": False})

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
        page.set_phase("production")
        page.phase_button.click()                          # «b» hidden: Ctrl+. must not ask its fix
        self.assertEqual(page.selected().text, "d")
        page.set_phase("consumption")                      # nothing shown: nothing under the keyboard
        self.assertEqual(self.shown(), [])
        self.assertIsNone(page.selected())

    def test_the_counts_are_filters_that_stay_pressed(self):
        """R130 (Daniel, 24/10/2026: «se ne seleziono uno non rimane schiacciato visibilmente»; 25/10: «non avevi
        applicato le correzioni ai tasti ... sia di estetica che di funzione»): a count pressed keeps its level,
        with the others pressed; none pressed, every level."""
        page = self.page
        page.counts["warn"].click()
        self.assertTrue(page.counts["warn"].isChecked())
        self.assertEqual(self.shown(), ["a", "e"])
        page.counts["fail"].click()
        self.assertEqual(self.shown(), ["a", "b", "e"])
        page.counts["warn"].click()
        self.assertEqual(self.shown(), ["b"])
        self.assertIn("a click shows every level again", page.counts["fail"].toolTip())
        self.show(self.items)                              # new results: still pressed
        self.assertEqual(self.shown(), ["b"])
        page.counts["fail"].click()
        self.assertEqual(self.shown(), ["a", "b", "c", "d", "e"])
        self.assertFalse(any(b.isChecked() for b in page.counts.values()))

    def test_the_counts_have_their_mark_left_and_their_number_right_all_as_wide(self):
        """R130, R51 (24/10/2026: «uno deve stare a destra e l'altro a sinistra»): the same room on both sides, the
        same width for the four, the number at the right edge."""
        from PySide6.QtGui import QColor
        page = self.page
        widths = {b.sizeHint().width() for b in page.counts.values()}
        self.assertEqual(len(widths), 1)
        b = page.counts["info"]
        image = b.grab().toImage()
        ground = QColor(image.pixel(image.width() // 2, 1))
        ink = [x for x in range(image.width()) if any(QColor(image.pixel(x, y)) != ground and
                                                      QColor(image.pixel(x, y)).alpha() == 255 and
                                                      abs(QColor(image.pixel(x, y)).lightness() - ground.lightness()) > 60
                                                      for y in range(4, image.height() - 4))]
        left, right = ink[0], image.width() - 1 - ink[-1]
        self.assertLessEqual(abs(left - right), 3 * b.devicePixelRatioF() + 2, (left, right))

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

    def test_the_counts_in_the_head_show_their_section_open(self):
        """The counts as pills with their mark (the target of 24/10/2026); pressed, the section of their level is
        opened and brought to the top (R130)."""
        page = self.page
        self.assertEqual({lv: b.text() for lv, b in page.counts.items()}, {"fail": "1", "warn": "2", "info": "1", "ok": "1"})
        self.assertTrue(page.counts["warn"].toolTip().startswith("2 to check: a click shows only these"))
        self.assertFalse(page.counts["fail"].icon().isNull())
        page.counts["ok"].click()
        passed = self.heads()[3]
        self.assertTrue(passed.isExpanded())                             # closed by default, opened
        self.assertEqual(self.shown(), ["d"])
        self.show([])
        self.assertEqual([b.text() for b in page.counts.values()], ["0", "0", "0", "0"])
        self.assertEqual([lv for lv, b in page.counts.items() if b.isEnabled()], ["ok"])   # pressed: can be let go

    def test_going_to_a_section_takes_its_first_item_with_nothing_hidden(self):
        page = self.page
        page.tree.setCurrentItem(self.row_of("c"))
        page.counts["fail"].click()                                      # a level the counts were hiding
        page.go_to("warn")                                               # what a count of the status bar asks
        self.assertFalse(any(b.isChecked() for b in page.counts.values()))
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
        from meridiana.ui.checks_page import SYMBOL_ROLE
        self.assertEqual(self.heads()[0].data(0, SYMBOL_ROLE), "stop")     # the worst mark of the area stays

    def test_a_headers_icon_is_drawn_once(self):
        """The by-object headers carry the kind's icon in the column before the name: the ground was drawn with it
        and then the icon again under the air (found by the template's alignment, 25/10/2026)."""
        from PySide6.QtGui import QColor, QIcon, QPixmap
        from PySide6.QtWidgets import QTreeWidget

        from meridiana.ui.sections import SectionDelegate, section
        tree = QTreeWidget()
        self.addCleanup(_setup.dispose, tree)
        tree.setColumnCount(2)
        tree.setHeaderHidden(True)
        tree.setItemDelegate(SectionDelegate(tree, column=1, air=16))
        green = QPixmap(16, 16)
        green.fill(QColor("#00ff00"))
        head = section(tree, "Capannone", 2, columns=2, column=1)
        head.setIcon(0, QIcon(green))
        tree.resize(300, 120)
        tree.show()
        self.app.processEvents()
        image = tree.viewport().grab().toImage()
        ratio = tree.viewport().devicePixelRatioF()
        lit = sum(1 for x in range(image.width()) for y in range(image.height())
                  if QColor(image.pixel(x, y)).name() == "#00ff00")
        self.assertGreater(lit, 0)
        self.assertLessEqual(lit, 16 * 16 * ratio * ratio)


if __name__ == "__main__":
    unittest.main()
