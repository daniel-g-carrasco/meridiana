"""The help next to things in the window (task 17d; design document 3.6, C3, C7 and 5.1): the box at the foot of
the right panel that follows the phase and the field with the keyboard, F1 and Shift+F1; folded and remembered,
hidden in a low panel where the «?» opens a pop-up; the links to «How it is computed» at its step, to Meridio with
the question and to the chapter of the phase; every help of the window with its text in help.py. The box, the
manual and the «?» of the pages alone are in widget/test_help_box.py. PySide6 and a display (offscreen will do)."""

import html
import unittest

import _setup
from _fixtures import capannone

from meridiana import config, model
from meridiana import help as helps

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


def sample() -> model.Project:
    p = capannone()
    p.exclusions.append(model.ExclusionItem(id=p.new_id("e"), ring=[[10, 9], [11.5, 9], [11.5, 10.5], [10, 10.5]],
                                            kind="skylight", building=p.buildings[0].id))
    return p


class HelpInTheWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, sample(), size=(1400, 1000))
        self.win.checks_dock.hide()                 # the right panel tall enough for the box (480 px)
        self.app.processEvents()
        self.box = self.win.help_box
        self.sid = self.win.project.subfields[0].id
        self.addCleanup(self.close_help)

    def close_help(self):
        from meridiana.ui.help_box import HelpPopup
        if HelpPopup.current is not None:
            HelpPopup.current.close()
        if self.box.manual_view is not None:
            self.box.manual_view.close()

    def says(self, hid: str) -> bool:
        return self.box.hid == hid and html.escape(helps.get(hid).text) in self.box.view.text.text()

    def subfield_page(self):
        self.win._select("subfield", self.sid)
        self.app.processEvents()
        return self.win.props.widget()

    def test_the_box_follows_the_phase_the_page_and_the_field_with_the_keyboard_f1_and_shift_f1(self):
        from PySide6.QtCore import QEvent, QPoint
        from PySide6.QtGui import QHelpEvent
        from PySide6.QtWidgets import QApplication, QDoubleSpinBox, QGroupBox, QLineEdit, QWhatsThis

        from meridiana.ui.help_box import help_id, whats_this
        # a card of its own under the properties (24/10/2026), shown when the column has room
        properties, card = self.win.docks[1], self.win.help_dock
        self.assertIs(card.widget(), self.box)
        self.assertEqual(card.x(), properties.x())
        self.assertGreater(card.y(), properties.y())
        self.assertTrue(self.box.room())
        self.assertTrue(self.box.isVisible())
        self.assertTrue(self.says("site"))                  # nothing selected: the site's page is shown
        self.assertIn(helps.get("site").title, self.box.subject.text())
        self.win.show_phase("production")
        self.assertTrue(self.says("phase.production"))
        self.win.show_phase("model")
        self.assertTrue(self.says("phase.model"))
        # the page shown, and the field with the keyboard: its own text, its group's, or the page's
        page = self.subfield_page()
        self.assertTrue(self.says("subfield"))
        self.box.show_help("phase.model")
        page.findChildren(QLineEdit)[0].setFocus()
        self.app.processEvents()
        self.assertTrue(self.says("subfield"))              # the page's help: the name has none of its own
        gaps = next(g for g in page.findChildren(QGroupBox) if g.title() == "Gaps and margins")
        edge = next(s for s in gaps.findChildren(QDoubleSpinBox) if help_id(s) == "subfield.edge")
        between = next(s for s in gaps.findChildren(QDoubleSpinBox) if help_id(s) == "subfield.gaps")
        self.assertEqual(edge.whatsThis(), whats_this(helps.get("subfield.edge")))
        edge.setFocus()
        self.app.processEvents()
        self.assertTrue(self.says("subfield.edge"))
        between.setFocus()
        self.app.processEvents()
        self.assertTrue(self.says("subfield.gaps"))
        # the keyboard outside the panel leaves the box as it is
        self.box.show_help("phase.model")
        self.win.checks_page.tree.setFocus()
        self.app.processEvents()
        self.assertEqual(self.box.hid, "phase.model")
        # F1: the field with the keyboard, or else the phase; in the checks, the level of the item in hand
        self.assertIn("F1", self.win.bindings["context_help"])
        self.assertIn("Shift+F1", self.win.bindings["whats_this"])
        self.assertIn("Ctrl+?", self.win.bindings["shortcuts"])     # the keys stay where they were (C7)
        page.findChildren(QLineEdit)[0].setFocus()
        self.box.show_help("phase.model")
        self.box.set_open(False)
        self.win.commands["context_help"].trigger()
        self.assertTrue(self.box.opened)
        self.assertTrue(self.says("subfield"))
        self.win.plan.setFocus()
        self.app.processEvents()
        self.win.commands["context_help"].trigger()
        self.assertTrue(self.says("phase.model"))
        self.win.checks_dock.show()
        self.win.checks_page.tree.setFocus()
        self.app.processEvents()
        self.win.commands["context_help"].trigger()
        item = self.win.checks_page.selected()
        self.assertEqual(self.box.hid, f"checks.{item.level}" if item is not None else "checks")
        self.win.checks_dock.hide()
        self.app.processEvents()
        # Shift+F1: What's This, and a click explains what it touches
        self.win.commands["whats_this"].trigger()
        self.assertTrue(QWhatsThis.inWhatsThisMode())
        QWhatsThis.leaveWhatsThisMode()
        page = self.subfield_page()
        self.assertEqual(page.whatsThis(), whats_this(helps.get("subfield")))
        self.box.show_help("phase.model")
        name = page.findChildren(QLineEdit)[0]
        QApplication.sendEvent(name, QHelpEvent(QEvent.Type.WhatsThis, QPoint(2, 2), name.mapToGlobal(QPoint(2, 2))))
        self.assertTrue(self.says("subfield"))              # the field's parent page answered

    def test_folded_and_remembered_hidden_in_a_low_panel_where_the_question_mark_opens_a_pop_up(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from meridiana.ui.help_box import HelpButton, HelpPopup
        from meridiana.ui.window import MainWindow
        # closing the card is folding the box, remembered in the settings; a window whose settings say folded
        # starts with the card closed
        self.win.help_dock.titleBarWidget().close_button.click()
        self.app.processEvents()
        self.assertFalse(self.box.opened)
        self.assertFalse(self.cfg.help_open)
        self.win.commands["panel_help"].trigger()
        self.app.processEvents()
        self.assertTrue(self.box.opened)
        self.assertTrue(self.cfg.help_open)
        other = MainWindow(self.paths, config.Config(background="none", help_open=False))
        self.addCleanup(_setup.dispose, other)
        self.assertFalse(other.help_box.opened)
        # the «?» opens the box on its text, and remembered open
        page = self.subfield_page()
        self.box.set_open(False)
        self.box.show_help("phase.model")
        button = next(b for b in page.findChildren(HelpButton) if b.hid == "subfield")
        button.click()
        self.assertTrue(self.box.opened)
        self.assertTrue(self.says("subfield"))
        self.assertEqual(button.toolTip(), helps.get("subfield").short)
        self.assertTrue(self.cfg.help_open)
        # a low column hides the card: the «?» opens a pop-up, closed by Esc; the card back with the room. The
        # window cannot get lower than its cards' minimum (about 690 px offscreen), so the threshold goes up
        self.win.checks_dock.show()
        self.box.LOWEST_PANEL = 10_000
        self.win.resize(1400, 560)
        self.app.processEvents()
        self.assertFalse(self.box.room())
        self.assertFalse(self.box.isVisible())
        button = next(b for b in page.findChildren(HelpButton) if b.hid == "subfield")
        button.click()
        popup = HelpPopup.current
        self.assertIsNotNone(popup)
        self.assertTrue(popup.isVisible())
        self.assertIn(html.escape(helps.get("subfield").text), popup.view.text.text())
        self.assertIn("manual:", popup.view.links.text())
        QTest.keyClick(popup, Qt.Key.Key_Escape)
        self.assertIsNone(HelpPopup.current)
        del self.box.LOWEST_PANEL                           # the class's threshold again
        self.win.resize(1400, 1000)
        self.win.checks_dock.hide()
        self.app.processEvents()
        self.assertTrue(self.box.isVisible())
        # the card closed: F1 opens it again (closing it is folding it)
        self.win.help_dock.close()
        self.app.processEvents()
        self.win.commands["context_help"].trigger()
        self.app.processEvents()
        self.assertTrue(self.box.isVisible())
        self.assertIsNone(HelpPopup.current)

    def test_corner_help_collapses_and_reopens_from_both_bottom_and_right_commands(self):
        from PySide6.QtCore import Qt
        for edge_dock in (self.win.docks[1], self.win.checks_dock):
            self.win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.win.help_dock)
            self.win.splitDockWidget(self.win.docks[1], self.win.help_dock, Qt.Orientation.Vertical)
            self.box.set_open(True)
            self.app.processEvents()
            button = self.win.panel_buttons.buttons[edge_dock]
            with self.subTest(command=edge_dock.windowTitle()):
                self.assertTrue(self.box.isVisible())
                button.click()
                self.app.processEvents()
                self.assertTrue(self.win.help_dock.isHidden())
                self.assertFalse(self.box.opened)
                self.assertFalse(self.cfg.help_open)
                button.click()
                self.app.processEvents()
                self.assertTrue(self.box.isVisible())
                self.assertTrue(self.box.opened)
                self.assertTrue(self.cfg.help_open)

    def test_the_links_lead_to_the_computation_to_meridio_and_to_the_chapter_of_the_phase(self):
        from meridiana.energy.pedigree import Record, Step
        # «How it is computed»: the page, its tab and the step
        record = Record("Production of the system")
        record.add(Step("ac", "AC side", "", "The AC side."))
        record.add(Step("pr", "Performance ratio", "", "The ratio."))
        view = self.win.energy_page.pedigree
        view.show_records([record])
        self.box.show_help("production.pr")
        self.assertIn("how:production:pr", self.box.view.links.text())
        self.box.view.links.linkActivated.emit("how:production:pr")
        self.app.processEvents()
        self.assertEqual(self.win.phase(), "production")
        self.assertTrue(view.isVisible())
        self.assertEqual(view.textCursor().selectedText(), "Performance ratio")
        # «Ask Meridio»: the assistant open with the question written; without Meridio, no link to him
        self.box.show_help("production.pr")                 # (the phase changed: the box said the phase's help)
        self.assertIn("ask:production.pr", self.box.view.links.text())
        self.box.follow("ask", "production.pr")
        self.app.processEvents()
        self.assertTrue(self.win.assistant.opened)
        self.assertEqual(self.win.assistant.field.text(), helps.question(helps.get("production.pr")))
        self.win._show_assistant(False)
        self.box.show_help("production.pr")
        self.assertNotIn("ask:", self.box.view.links.text())
        # Help > Manual opens the chapter of the phase, and a link of the box another one
        self.win.show_phase("economics")
        self.win.commands["manual"].trigger()
        self.assertEqual(self.box.manual_view.chapter, "5-bilancio.md")
        self.box.view.links.linkActivated.emit("manual:verifiche.md#da-sapere")
        self.assertEqual(self.box.manual_view.chapter, "verifiche.md")
        self.assertEqual(self.box.manual_view.page.textCursor().block().text(), "Da sapere")

    def test_every_help_of_the_window_has_its_text_and_the_box_follows_the_pointer_over_the_tiles(self):
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QApplication, QWidget

        from meridiana.ui.help_box import HELP, HelpButton
        known = helps.texts()
        seen = set()
        p = self.win.project
        for where in ("site", "building", "subfield tilted", "subfield flush", "exclusion"):
            {"site": lambda: self.win._select("site", ""),
             "building": lambda: self.win._select("building", p.buildings[0].id),
             "subfield tilted": lambda: self.win._select("subfield", self.sid),
             "subfield flush": lambda: (self.win._edited("subfield", self.sid, {"params.mounting": "coplanar"}),
                                        self.win._select("subfield", self.sid)),
             "exclusion": lambda: self.win._select("exclusion", p.exclusions[0].id)}[where]()
            self.app.processEvents()
            for w in self.win.findChildren(QWidget):
                hid = w.property(HELP)
                if isinstance(hid, str) and hid:
                    with self.subTest(where, widget=type(w).__name__, help=hid):
                        self.assertIn(hid, known)
                        seen.add(hid)
                if isinstance(w, HelpButton):
                    self.assertIn(w.hid, known)
        for hid in ("site", "site.rules", "building", "building.fire",
                    "sides", "subfield", "subfield.mounting", "subfield.stack", "subfield.gaps", "subfield.edge",
                    "subfield.row_gap", "subfield.pitch", "subfield.sun_window", "subfield.sun_window.day",
                    "subfield.shade_free", "exclusion", "production.energy",
                    "production.specific_yield", "production.pr", "production.power", "production.pvgis",
                    "production.losses", "consumption.year", "consumption.bands", "consumption.shape",
                    "economics.self_consumption", "economics.self_sufficiency", "economics.first_year",
                    "economics.npv", "economics.return", "economics.prices", "checks"):
            self.assertIn(hid, seen)
        # the pointer over a result tile: the box says its help; its «?» opens the box on it
        self.win.show_phase("production")
        self.app.processEvents()
        tiles = self.win.energy_page.tiles.tiles
        QApplication.sendEvent(tiles[2], QEvent(QEvent.Type.Enter))
        self.assertTrue(self.says("production.pr"))
        button = next(b for b in tiles[1].children() if isinstance(b, HelpButton))
        self.box.set_open(False)
        button.click()
        self.assertTrue(self.box.opened)
        self.assertTrue(self.says("production.specific_yield"))


if __name__ == "__main__":
    unittest.main()
