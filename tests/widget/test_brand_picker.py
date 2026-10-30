"""The picker of a name out of many (ui/brand_picker.py, R268: the inverter makers stood in a list as tall as the
screen): the search that minds neither case nor accents, the list about eight rows tall that scrolls beyond them and
reaches every name, the favourites on top with their star, the project's name preselected, the keyboard, the
attenuated names last with their reason, the colours of both themes, and what `ask` answers. PySide6 and a display
(offscreen will do)."""

import unittest
from unittest import mock

import _setup

setUpModule = _setup.keep_global_state          # the look set here, put back after the module

try:
    from PySide6.QtCore import QEvent, QPoint, Qt
    from PySide6.QtGui import QColor, QHelpEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QDialog, QToolTip
except ImportError as error:
    raise unittest.SkipTest(f"PySide6 is not installed: {error}") from error

MAKERS = ["ABB", "Deye", "FIMER", "Fronius", "GoodWe", "Growatt", "Huawei", "Hüttinger", "SMA", "SolarEdge",
          "Sungrow", "Zeta Énergie"]


class PickerCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.theme = _setup.meridiana_look("light")

    def picker(self, names=MAKERS, **kw):
        from meridiana.ui.brand_picker import NamePicker
        p = NamePicker(names, **kw)
        p.show()
        self.app.processEvents()
        self.addCleanup(_setup.dispose, p)
        return p

    def dialog(self, names=MAKERS, **kw):
        from meridiana.ui.brand_picker import NameDialog
        d = NameDialog(None, "Pick", "Manufacturer:", names, **kw)
        d.show()
        self.app.processEvents()
        self.addCleanup(_setup.dispose, d)
        return d

    def star_of(self, picker, name) -> QPoint:
        """The centre of the star of the row of `name`, in the viewport's coordinates."""
        from meridiana.ui.brand_picker import NAME_ROLE, star_rect
        for i in range(picker.list.count()):
            item = picker.list.item(i)
            if item.data(NAME_ROLE) == name:
                return star_rect(picker.list.visualItemRect(item)).center()
        raise AssertionError(f"{name} is not in the list")


class TheSearch(PickerCase):
    def test_the_search_minds_neither_case_nor_accents_and_the_whole_list_comes_back_when_cleared(self):
        p = self.picker()
        self.assertEqual(p.shown(), MAKERS)                 # the caller's order, nothing hidden
        p.search.setText("HUTT")
        self.assertEqual(p.shown(), ["Hüttinger"])
        p.search.setText("hüt")
        self.assertEqual(p.shown(), ["Hüttinger"])
        p.search.setText("énerg")
        self.assertEqual(p.shown(), ["Zeta Énergie"])
        p.search.setText("ENERGIE")
        self.assertEqual(p.shown(), ["Zeta Énergie"])
        p.search.setText("so")
        self.assertEqual(p.shown(), ["SolarEdge"])
        p.search.setText("xyz")
        self.assertEqual(p.shown(), [])
        self.assertIsNone(p.current())
        p.search.clear()
        self.assertEqual(p.shown(), MAKERS)

    def test_the_current_name_is_kept_through_a_search_that_still_shows_it(self):
        p = self.picker(current="Sungrow")
        self.assertEqual(p.current(), "Sungrow")
        p.search.setText("s")
        self.assertEqual(p.current(), "Sungrow")            # still there: still in hand
        p.search.setText("sm")
        self.assertEqual(p.current(), "SMA")                # gone: the first shown


class TheList(PickerCase):
    def test_the_list_is_about_eight_rows_tall_and_scrolls_to_every_name(self):
        from meridiana.ui.brand_picker import ROW, VISIBLE_ROWS
        many = [f"Maker {i:03d}" for i in range(120)]
        p = self.picker(many)
        self.assertEqual(VISIBLE_ROWS, 8)
        self.assertEqual(p.list.height(), VISIBLE_ROWS * ROW + 2)
        self.assertGreater(p.list.verticalScrollBar().maximum(), 0)       # it scrolls: nothing is cut off
        p.set_current(many[-1])
        p.list.scrollToItem(p.list.currentItem())
        self.app.processEvents()
        self.assertEqual(p.current(), many[-1])
        rect = p.list.visualItemRect(p.list.currentItem())
        self.assertTrue(p.list.viewport().rect().contains(rect.center()))  # the last one on screen

    def test_a_short_list_is_only_as_tall_as_it_needs(self):
        from meridiana.ui.brand_picker import ROW
        p = self.picker(["Acme", "Other"])
        self.assertEqual(p.list.height(), 3 * ROW + 2)       # never below three rows
        p = self.picker(["Acme", "Other", "Third", "Fourth", "Fifth"], favourites=["Acme"])
        self.assertEqual(p.list.height(), 7 * ROW + 2)       # five names and two headers
        self.assertEqual(p.list.verticalScrollBar().maximum(), 0)

    def test_the_favourites_come_first_under_their_header_and_the_star_adds_and_removes(self):
        p = self.picker(favourites=["SMA", "Deye"], current="Huawei")
        self.assertEqual(p.headers(), ["Favourites", "All"])
        self.assertEqual(p.shown()[:2], ["SMA", "Deye"])     # in the order they were starred
        self.assertEqual(p.shown()[2:], [m for m in MAKERS if m not in ("SMA", "Deye")])
        self.assertEqual(p.current(), "Huawei")
        changes = []
        p.favouritesChanged.connect(changes.append)
        QTest.mouseClick(p.list.viewport(), Qt.MouseButton.LeftButton, pos=self.star_of(p, "Huawei"))
        self.assertEqual(changes, [["SMA", "Deye", "Huawei"]])
        self.assertEqual(p.shown()[:3], ["SMA", "Deye", "Huawei"])
        self.assertEqual(p.current(), "Huawei")             # starred, not chosen: still the one in hand
        QTest.mouseClick(p.list.viewport(), Qt.MouseButton.LeftButton, pos=self.star_of(p, "SMA"))
        self.assertEqual(p.favourites(), ["Deye", "Huawei"])
        self.assertEqual(p.shown()[:2], ["Deye", "Huawei"])
        self.assertIn("SMA", p.shown()[2:])
        p.toggle_favourite("Deye")
        p.toggle_favourite("Huawei")
        self.assertEqual(p.favourites(), [])
        self.assertEqual(p.headers(), [])                    # no favourite, no headers
        self.assertEqual(p.shown(), MAKERS)

    def test_a_favourite_that_the_list_does_not_know_is_kept_but_not_shown(self):
        p = self.picker(favourites=["Old Maker", "SMA"])
        self.assertEqual(p.shown()[0], "SMA")
        self.assertNotIn("Old Maker", p.shown())
        self.assertEqual(p.favourites(), ["Old Maker", "SMA"])
        p.toggle_favourite("SMA")
        self.assertEqual(p.favourites(), ["Old Maker"])

    def test_a_click_on_the_name_chooses_the_row_and_a_double_click_says_so(self):
        p = self.picker(current="SMA")
        chosen = []
        p.chosen.connect(chosen.append)
        rect = p.list.visualItemRect(p.list.item(1))        # "Deye": no favourites, no headers, the second row
        at = QPoint(rect.left() + 20, rect.center().y())
        QTest.mouseClick(p.list.viewport(), Qt.MouseButton.LeftButton, pos=at)
        self.assertEqual(p.current(), "Deye")
        QTest.mouseDClick(p.list.viewport(), Qt.MouseButton.LeftButton, pos=at)
        self.assertEqual(chosen, ["Deye"])

    def test_the_attenuated_names_come_last_stay_reachable_and_say_why(self):
        from meridiana.ui.brand_picker import DIM_ROLE
        why = "No model of ABB in the catalogue has the data the sizing needs. Sizable instead: FIMER."
        p = self.picker(["ABB", "Deye", "Huawei", "SolarEdge Technologies Ltd"],
                        dimmed={"ABB": why, "SolarEdge Technologies Ltd": "CEC list"})
        self.assertEqual(p.shown(), ["Deye", "Huawei", "ABB", "SolarEdge Technologies Ltd"])
        self.assertEqual(p.current(), "Deye")               # the first proposed is one that can be used
        p.toggle_favourite("ABB")
        self.assertEqual(p.shown(), ["ABB", "Deye", "Huawei", "SolarEdge Technologies Ltd"])  # a starred one stays up
        self.assertEqual(p.current(), "Deye")               # starred, not chosen
        p.toggle_favourite("ABB")
        p.search.setText("abb")
        self.assertEqual(p.shown(), ["ABB"])                 # reachable all the same
        self.assertEqual(p.current(), "ABB")
        self.assertEqual(p.list.currentItem().data(DIM_ROLE), why)
        rect = p.list.visualItemRect(p.list.currentItem())
        at = QPoint(rect.left() + 20, rect.center().y())
        event = QHelpEvent(QEvent.Type.ToolTip, at, p.list.viewport().mapToGlobal(at))
        QApplication.sendEvent(p.list, event)
        self.assertEqual(QToolTip.text(), why)
        QToolTip.hideText()
        star = self.star_of(p, "ABB")
        QApplication.sendEvent(p.list, QHelpEvent(QEvent.Type.ToolTip, star, p.list.viewport().mapToGlobal(star)))
        self.assertEqual(QToolTip.text(), "Add to favourites (Ctrl+D)")
        QToolTip.hideText()


class TheKeyboard(PickerCase):
    def test_the_projects_name_is_preselected_and_the_arrows_move_from_the_search_box(self):
        d = self.dialog(current="fronius", favourites=["SMA"])           # as the project wrote it, any case
        p = d.picker
        self.assertEqual(p.current(), "Fronius")
        _setup.keyboard_or_skip(self, p.search)
        QTest.keyClick(p.search, Qt.Key.Key_Down)
        self.assertEqual(p.current(), "GoodWe")
        QTest.keyClick(p.search, Qt.Key.Key_Up)
        QTest.keyClick(p.search, Qt.Key.Key_Up)
        self.assertEqual(p.current(), "FIMER")
        QTest.keyClick(p.search, Qt.Key.Key_PageUp)
        self.assertEqual(p.current(), "SMA")                 # the first name: the header above it is skipped
        QTest.keyClick(p.search, Qt.Key.Key_Up)
        self.assertEqual(p.current(), "SMA")
        QTest.keyClick(p.search, Qt.Key.Key_Down)
        self.assertEqual(p.current(), "ABB")                 # over the second header
        QTest.keyClick(p.search, Qt.Key.Key_End)
        self.assertEqual(p.current(), "ABB")                 # End is the list's: the box keeps it
        QTest.keyClick(p.search, Qt.Key.Key_PageDown)
        self.assertEqual(p.current(), "Hüttinger")           # seven names down, the header not counted
        self.assertTrue(p.search.hasFocus())                # the box kept the keyboard throughout

    def test_enter_chooses_escape_clears_the_search_then_closes_and_ctrl_f_goes_back_to_the_box(self):
        d = self.dialog(current="SMA")
        p = d.picker
        _setup.keyboard_or_skip(self, p.search)
        QTest.keyClicks(p.search, "sun")
        self.assertEqual(p.current(), "Sungrow")
        QTest.keyClick(p.search, Qt.Key.Key_Return)
        self.assertEqual((d.result(), d.chosen()), (QDialog.DialogCode.Accepted, "Sungrow"))
        d = self.dialog(current="SMA")
        p = d.picker
        _setup.keyboard_or_skip(self, p.search)
        QTest.keyClicks(p.search, "xyz")
        self.assertIsNone(p.current())
        self.assertFalse(d.buttons.button(d.buttons.StandardButton.Ok).isEnabled())
        QTest.keyClick(p.search, Qt.Key.Key_Return)         # nothing to choose: nothing happens
        self.assertTrue(d.isVisible())
        QTest.keyClick(p.search, Qt.Key.Key_Escape)
        self.assertEqual((p.query(), p.current()), ("", "SMA"))
        self.assertTrue(d.isVisible())
        p.list.setFocus()
        self.app.processEvents()
        QTest.keyClick(p.list, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
        self.assertTrue(p.search.hasFocus())
        QTest.keyClick(p.search, Qt.Key.Key_Escape)
        self.assertEqual(d.result(), QDialog.DialogCode.Rejected)

    def test_in_the_list_enter_chooses_space_and_ctrl_d_star_and_a_letter_goes_to_the_box(self):
        d = self.dialog(current="Deye")
        p = d.picker
        _setup.keyboard_or_skip(self, p.list)
        QTest.keyClick(p.list, Qt.Key.Key_Space)
        self.assertEqual(p.favourites(), ["Deye"])
        self.assertEqual(p.current(), "Deye")
        QTest.keyClick(p.list, Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(p.favourites(), [])
        QTest.keyClick(p.list, Qt.Key.Key_Down)
        self.assertEqual(p.current(), "FIMER")
        QTest.keyClick(p.list, Qt.Key.Key_G)
        self.assertTrue(p.search.hasFocus())
        self.assertEqual(p.query(), "g")
        self.assertEqual(p.shown(), ["GoodWe", "Growatt", "Hüttinger", "SolarEdge", "Sungrow", "Zeta Énergie"])
        p.list.setFocus()
        self.app.processEvents()
        QTest.keyClick(p.list, Qt.Key.Key_Return)
        self.assertEqual((d.result(), d.chosen()), (QDialog.DialogCode.Accepted, "GoodWe"))


class TheLook(PickerCase):
    def test_a_list_opened_on_a_name_far_down_shows_no_hover_pill_on_its_top_row(self):
        """Opened on a name far down the list, the view scrolls to it and marks the row at its top as hovered with
        the pointer nowhere near it (found in the template's gallery, 30/10/2026: «Deye» with the hover pill and the
        outline star): the pill is drawn only while the pointer is really over the list."""
        from PySide6.QtCore import QPoint
        names = [f"Maker {i:02d}" for i in range(30)]
        p = self.picker(names, current="Maker 20")
        p.window().move(400, 300)                           # the pointer, wherever it is, not over the list
        self.app.processEvents()
        self.assertGreater(p.list.verticalScrollBar().value(), 0)
        self.assertFalse(p.list.viewport().underMouse())
        top = p.list.itemAt(QPoint(5, 5))
        self.assertNotEqual(top.text(), "Maker 20")
        image = p.list.viewport().grab().toImage()
        rect = p.list.visualItemRect(top)
        ground = QColor(image.pixel(rect.center().x() + 30, rect.center().y() + 8))
        self.assertEqual(ground.name(), QColor(self.theme.tokens["card"]).name())

    def test_the_rows_take_the_colours_of_the_theme_in_light_and_in_dark(self):
        for theme in ("light", "dark"):
            with self.subTest(theme=theme):
                look = _setup.meridiana_look(theme)
                p = self.picker(["Acme", "Other", "Third"], current="Other", dimmed={"Third": "why"})
                p.resize(300, p.sizeHint().height())
                self.app.processEvents()
                image = p.list.viewport().grab().toImage()
                rows = [p.list.visualItemRect(p.list.item(i)) for i in range(3)]
                # a row at rest has no ground of its own: the card's; the one in hand the selection's
                ground = QColor(image.pixel(rows[0].center().x() + 30, rows[0].center().y() + 8))
                self.assertEqual(ground.name(), QColor(look.tokens["card"]).name())
                selected = QColor(image.pixel(rows[1].center().x() + 30, rows[1].center().y() + 8))
                self.assertEqual(selected.name(), QColor(look.tokens["select_bg"]).name())
                # the attenuated name is drawn in the faded ink, the plain one in the text's: the darkest pixel of
                # each name's strip tells (anti-aliasing shades the rest)
                from meridiana import theme_colors

                def darkest_or_lightest(picture, rect, dark):
                    best = None
                    for x in range(rect.left() + 8, rect.left() + 48):
                        for y in range(rect.top() + 6, rect.bottom() - 5):
                            c = QColor(picture.pixel(x, y))
                            if best is None or (c.lightness() > best.lightness()) == dark:
                                best = c
                    return best
                dark = theme == "dark"
                ink = darkest_or_lightest(image, rows[0], dark)
                faded = darkest_or_lightest(image, rows[2], dark)
                self.assertEqual(ink.name(), QColor(look.tokens["text"]).name())
                self.assertEqual(faded.name(), QColor(theme_colors.faded_text(look.tokens)).name())
                _setup.dispose(p)


class Ask(PickerCase):
    def test_ask_answers_the_name_whether_ok_was_pressed_and_the_favourites_as_they_stand(self):
        from meridiana.ui.brand_picker import NameDialog

        def accept(dialog):
            dialog.picker.search.setText("huaw")
            dialog.picker.toggle_favourite("Huawei")
            return QDialog.DialogCode.Accepted

        def cancel(dialog):
            dialog.picker.toggle_favourite("SMA")             # starred, then the window cancelled
            return QDialog.DialogCode.Rejected
        with mock.patch.object(NameDialog, "exec", accept):
            self.assertEqual(NameDialog.ask(None, "Pick", "Manufacturer:", MAKERS, current="Deye", favourites=["SMA"]),
                             ("Huawei", True, ["SMA", "Huawei"]))
        with mock.patch.object(NameDialog, "exec", cancel):
            self.assertEqual(NameDialog.ask(None, "Pick", "Manufacturer:", MAKERS, current="Deye", favourites=["SMA"]),
                             ("", False, []))
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


if __name__ == "__main__":
    unittest.main()
