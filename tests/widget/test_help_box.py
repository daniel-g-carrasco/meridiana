"""The help next to things, without the window (ui/help_box.py, task 17d): the box alone shows three lines at most and
folds to its title, saying so; the manual opens inside the program at the heading; the «?» of the properties' groups
on the titles' row, the phrases under the fields that do not explain themselves, the lists that do not repeat their
choice in a tooltip, the «?» of the result tiles; a «?» in a dialog without the box opens the pop-up with the manual
only; an id that help.py does not have is refused. The box in the window (the phase, the keyboard, F1, the links to
the window, the low panel) is in finestra/test_help_box.py. PySide6 and a display (offscreen will do)."""

import html
import unittest

import _setup
from _fixtures import capannone

from meridiana import help as helps
from meridiana import model

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class TheBoxAlone(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        cls.look = _setup.meridiana_look()

    def setUp(self):
        from meridiana.ui.help_box import HelpBox
        self.box = HelpBox()
        self.addCleanup(_setup.dispose, self.box)
        self.box.resize(340, 300)
        self.box.show()

    def says(self, hid: str) -> bool:
        return self.box.hid == hid and html.escape(helps.get(hid).text) in self.box.view.text.text()

    def test_at_most_three_lines_of_text_the_rest_scrolled(self):
        self.box.show_help("subfield.row_gap")              # one of the longest texts
        self.app.processEvents()
        self.assertTrue(self.says("subfield.row_gap"))
        line = self.box.view.fontMetrics().lineSpacing()
        self.assertLessEqual(self.box.view.scroll.height(), 3 * line + 4)
        self.assertGreater(self.box.view.text.heightForWidth(self.box.view.scroll.viewport().width()),
                           self.box.view.scroll.height())

    def test_folding_shows_the_title_alone_and_says_so(self):
        heard = []
        self.box.openedChanged.connect(heard.append)        # what the window keeps in the settings
        self.box.show_help("site")
        self.assertIn(helps.get("site").title, self.box.head.text())
        self.box.head.click()
        self.assertFalse(self.box.opened)
        self.assertFalse(self.box.view.isVisible())
        self.assertTrue(self.box.head.isVisible())
        self.box.head.click()
        self.assertTrue(self.box.view.isVisible())
        self.assertEqual(heard, [False, True])
        self.box.set_open(False)
        self.box.request("subfield")                        # a «?», F1: open again on its text
        self.assertTrue(self.box.opened)
        self.assertTrue(self.says("subfield"))

    def test_the_manual_opens_inside_the_program_at_the_heading(self):
        from PySide6.QtCore import QUrl
        view = self.box.open_manual("1-modello.md#tra-le-file")
        self.addCleanup(view.close)
        self.app.processEvents()
        self.assertTrue(view.isVisible())
        self.assertFalse(view.isModal())
        self.assertEqual(view.chapter, "1-modello.md")
        self.assertEqual(view.page.textCursor().block().text(), "Tra le file")
        self.assertEqual(view.chapters.count(), len(helps.CHAPTERS))
        view._follow(QUrl("3-producibilita.md#indice-di-prestazione"))       # a link between chapters
        self.assertEqual(view.chapter, "3-producibilita.md")
        self.assertEqual(view.page.textCursor().block().text(), "Indice di prestazione")
        self.assertEqual(view.chapters.currentItem().data(0x0100), "3-producibilita.md")

    def test_without_the_window_the_links_are_the_manuals_only(self):
        self.box.show_help("production.pr")
        links = self.box.view.links.text()
        self.assertIn("manual:", links)
        self.assertNotIn("how:", links)                     # «How it is computed» and Meridio need the window
        self.assertNotIn("ask:", links)


class QuestionMarks(unittest.TestCase):
    """The «?» beside the titles of the groups and the result tiles, the phrases under the fields that do not
    explain themselves (task 17d, step 4), on the pages of the properties alone, as the window shows them."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        cls.look = _setup.meridiana_look()

    def setUp(self):
        from meridiana.ui.properties import Properties
        self.p = capannone()
        self.p.exclusions.append(model.ExclusionItem(id="e1", ring=[[10, 9], [11.5, 9], [11.5, 10.5], [10, 10.5]],
                                                     kind="skylight", building="b1"))
        self.props = Properties()
        self.addCleanup(_setup.dispose, self.props)
        self.props.resize(380, 1000)                        # the width of the right panel
        self.props.show()

    def pages(self):
        """Every page of the properties, the sub-field both in tilted rows and flush."""
        p, props = self.p, self.props
        sf = p.subfields[0]
        props.show_site(p, False)
        yield "site"
        props.show_building(p.buildings[0])
        yield "building"
        props.show_subfield(p, sf, p.fill(sf))
        yield "subfield tilted"
        sf.params["mounting"] = "coplanar"
        props.show_subfield(p, sf, p.fill(sf))
        yield "subfield flush"
        props.show_exclusion(p.exclusions[0])
        yield "exclusion"

    def test_the_groups_have_their_question_mark_on_the_titles_row(self):
        from PySide6.QtWidgets import QGroupBox

        from meridiana.ui.help_box import HelpButton
        wanted = {"site": {"Row pitch from the sun": "site.sun_window", "Connection and obligations": "site.rules"},
                  "building": {"Fire brigade": "building.fire", "Sides": "sides"},
                  "subfield tilted": {"Gaps and margins": "subfield.gaps", "Row pitch": "subfield.pitch",
                                      "Sides": "sides"}}
        found = 0
        for where in self.pages():
            self.app.processEvents()
            page = self.props.widget()
            for group in page.findChildren(QGroupBox):
                hid = wanted.get(where, {}).get(group.title())
                if hid is None:
                    continue
                found += 1
                buttons = [b for b in group.children() if isinstance(b, HelpButton)]
                with self.subTest(where, group=group.title()):
                    self.assertEqual([b.hid for b in buttons], [hid])
                    b = buttons[0]
                    self.assertTrue(b.isVisible())
                    self.assertLessEqual(b.geometry().right(), group.width())
                    self.assertGreater(b.x(), group.width() // 2)                  # on the right
                    self.assertLess(b.y() + b.height() // 2, 22)                   # on the title's row
        self.assertEqual(found, 7)

    def test_the_fields_that_do_not_explain_themselves_have_their_phrase_under_them(self):
        from meridiana.ui.help_box import HintLabel
        for where in self.pages():
            self.app.processEvents()
            found = self.props.widget().findChildren(HintLabel)
            with self.subTest(where):
                expected = {"subfield tilted": ["subfield.shade_free"],
                            "subfield flush": ["subfield.row_gap", "subfield.shade_free"]}.get(where, [])
                self.assertEqual(sorted(h.hid for h in found), expected)
                for hint in found:
                    self.assertEqual(hint.text(), helps.get(hint.hid).short)

    def test_the_lists_do_not_repeat_their_choice_in_a_tooltip(self):
        from PySide6.QtWidgets import QComboBox
        for where in self.pages():
            self.app.processEvents()
            for c in self.props.widget().findChildren(QComboBox):
                with self.subTest(where, choice=c.currentText()):
                    self.assertNotEqual(c.toolTip(), c.currentText())
        c = next(c for c in self.props.widget().findChildren(QComboBox))
        c.setCurrentIndex((c.currentIndex() + 1) % c.count())
        self.assertNotEqual(c.toolTip(), c.currentText())

    def test_the_result_tiles_have_their_question_mark_on_the_right(self):
        from meridiana.ui.energy_pages import EnergyPage
        from meridiana.ui.help_box import HelpButton, help_id
        page = EnergyPage()
        self.addCleanup(_setup.dispose, page)
        page.resize(1000, 700)
        page.show()
        self.app.processEvents()
        tiles = page.tiles.tiles
        for tile in tiles:
            buttons = [b for b in tile.children() if isinstance(b, HelpButton)]
            self.assertEqual(len(buttons), 1)
            self.assertEqual(buttons[0].hid, help_id(tile))
            self.assertGreater(buttons[0].x(), tile.width() // 2)
        self.assertEqual(help_id(tiles[2]), "production.pr")
        self.assertEqual(help_id(tiles[1]), "production.specific_yield")


class Elsewhere(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_a_question_mark_in_a_window_without_the_box_opens_the_pop_up_with_the_manual_only(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout

        from meridiana.ui.help_box import HelpButton, HelpPopup
        dialog = QDialog()
        button = HelpButton("subfield.edge")
        QVBoxLayout(dialog).addWidget(button)
        dialog.show()
        self.app.processEvents()
        button.click()
        popup = HelpPopup.current
        self.addCleanup(dialog.deleteLater)
        self.addCleanup(lambda: HelpPopup.current and HelpPopup.current.close())
        self.assertIsNotNone(popup)
        links = popup.view.links.text()
        self.assertIn("manual:1-modello.md#dal-bordo-dellarea", links)
        self.assertNotIn("how:", links)
        self.assertNotIn("ask:", links)
        self.assertIn("DCPREV 14030/2025", popup.view.text.text())        # the source, from rules.py (N15)

    def test_an_id_that_help_py_does_not_have_is_refused(self):
        from PySide6.QtWidgets import QWidget

        from meridiana.ui.help_box import HelpButton, register
        with self.assertRaises(ValueError):
            HelpButton("no.such.help")
        with self.assertRaises(ValueError):
            register(QWidget(), "no.such.help")


if __name__ == "__main__":
    unittest.main()
