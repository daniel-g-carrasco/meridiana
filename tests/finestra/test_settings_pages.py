"""R346: every page of the Settings by one rule: the fields on the section's title and text, the same column, no scroll
area of its own (Assistant and Maps had one, with a bar in the middle of the page and the page 56 px over the section),
the commands in sight whatever scrolls, nothing cut."""
import unittest

import _setup
from _fixtures import capannone
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QAbstractScrollArea, QLabel, QScrollArea

NAMES = ("appearance", "navigation", "keyboard", "assistant", "report", "maps", "privacy")


class SettingsPages(unittest.TestCase):
    def setUp(self):
        self.app = _setup.qt_or_skip()
        _setup.window(self, capannone(), size=(1600, 900))
        page = self.win.file_page
        self.win.open_file_page("open")
        _setup.turn_events(self.app, 300)
        page.show_section("preferences")
        _setup.turn_events(self.app, 200)
        self.page, self.pref = page, page.settings

    def show(self, name):
        self.pref.show_page(name)
        _setup.turn_events(self.app, 150)
        return self.pref.pages.currentWidget()

    def test_every_page_has_the_same_left_and_width_and_no_scroll_area_of_its_own(self):
        section = self.page._settings_section
        title_x = section.widget().findChild(QLabel).mapTo(section, QPoint(0, 0)).x()
        for name in NAMES:
            widget = self.show(name)
            self.assertNotIsInstance(widget, QScrollArea, name)
            self.assertEqual(widget.findChildren(QScrollArea), [], name)
            self.assertEqual(widget.mapTo(section, QPoint(0, 0)).x(), title_x, name)
            self.assertEqual(self.pref.width(), widget.width(), name)
            self.assertEqual(widget.layout().contentsMargins().left(), 0, name)

    def test_short_pages_do_not_scroll_and_long_ones_scroll_the_section_with_the_programs_bar(self):
        section = self.page._settings_section
        bar = section.verticalScrollBar()
        heights = {}
        for name in NAMES:
            self.show(name)
            heights[name] = bar.maximum()
        self.assertEqual(heights["navigation"], 0)
        self.assertEqual(heights["privacy"], 0)
        self.assertGreater(heights["assistant"], 100)
        self.assertGreater(heights["maps"], 100)
        self.assertEqual(section.horizontalScrollBar().maximum(), 0)

    def test_the_commands_stay_in_sight_at_the_foot_while_the_page_scrolls(self):
        section = self.page._settings_section
        self.show("assistant")
        foot = self.pref.foot
        self.assertIs(foot.parentWidget(), section)
        y = foot.y()
        section.verticalScrollBar().setValue(section.verticalScrollBar().maximum())
        _setup.turn_events(self.app, 50)
        self.assertEqual(foot.y(), y)
        self.assertTrue(foot.isVisible())
        self.assertGreaterEqual(foot.y(), section.viewport().geometry().bottom())       # under what scrolls
        self.assertLessEqual(foot.geometry().bottom(), section.height())
        # the confirmation comes with the commands, not at the top of a page scrolled away
        self.pref.ask_reset()
        _setup.turn_events(self.app, 60)
        self.assertTrue(self.pref.confirmation.isVisible())
        self.assertLessEqual(foot.geometry().bottom(), section.height())
        self.assertGreaterEqual(foot.y(), section.viewport().geometry().bottom())

    def test_no_text_is_cut_at_any_page_at_a_small_window_too(self):
        for size in ((1600, 900), (1000, 640)):
            self.win.resize(*size)
            _setup.turn_events(self.app, 200)
            for name in NAMES:
                widget = self.show(name)
                self.assertLessEqual(widget.width(), self.page._settings_section.viewport().width(), name)
                for label in widget.findChildren(QLabel):
                    if label.isVisible() and label.wordWrap():
                        self.assertGreaterEqual(label.height(), label.heightForWidth(label.width()),
                                                f"{name}, {size}: {label.text()[:40]}")

    def test_inside_the_assistant_the_groups_inside_the_group_are_no_cards(self):
        self.show("assistant")
        meridio = self.pref.meridio
        self.assertTrue(meridio.locals.nested)
        self.assertEqual(meridio.locals.layout().contentsMargins().left(), 0)
        self.assertEqual([a for a in self.pref.pages.currentWidget().findChildren(QAbstractScrollArea)
                          if type(a).__name__ == "QScrollArea"], [])


if __name__ == "__main__":
    unittest.main()
