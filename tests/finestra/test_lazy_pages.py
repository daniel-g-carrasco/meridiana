"""The results pages are made when their phase is first shown (ui/lazy_page.py), and what the window told them before
is there when they are: the year computed, the status, the basis, the form's values, the reference to the Plant in
Production. PySide6 and a display (offscreen will do)."""

import unittest

import _setup
from _fixtures import capannone, clear_sky_meteo
from _setup import wait_until

from meridiana import config

setUpModule = _setup.keep_global_state


class LazyPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone(), cfg=config.Config(background="none", theme="light"),
                      cache=clear_sky_meteo(45.5226, 9.03))
        self.pages = (self.win.energy_page, self.win.consumption_page, self.win.economics_page)

    def test_the_window_starts_without_them_and_the_year_computed_meanwhile_is_there_at_the_first_visit(self):
        from PySide6.QtWidgets import QWidget
        win = self.win
        self.assertEqual([p.is_built() for p in self.pages], [False, False, False])
        self.assertLess(len(win.findChildren(QWidget)), 1600)       # 2,300 with them made
        win._compute_energy(fetch=False)
        self.assertTrue(wait_until(self.app, lambda: bool(win.energy), 60), "the energy job did not come back")
        self.assertEqual([p.is_built() for p in self.pages], [False, False, False])   # the year came, nothing made
        win.show_phase("production")
        _setup.turn_events(self.app, 200)
        page = win.energy_page
        self.assertTrue(page.is_built())
        self.assertEqual([p.is_built() for p in self.pages[1:]], [False, False])
        tiles = page.tiles.tiles
        self.assertNotEqual(tiles[0].value.text(), "–")             # the figures of the year, not an empty page
        self.assertIsNotNone(page.calculation_basis)                  # the basis told before it was there
        self.assertTrue(page.plant_context.isVisibleTo(page))
        # the reference to the Plant, put in the form when the page was made, says the plant told before
        self.assertIn("Plant:", win.inverter_reference.label.text())
        self.assertIs(win.inspector.currentWidget(), page.side_slot)
        self.assertIs(page.side.parentWidget(), page.side_slot)
        # the other two, at their first visit, have theirs
        win.show_phase("economics")
        _setup.turn_events(self.app, 200)
        self.assertNotEqual(win.economics_page.tiles.tiles[0].value.text(), "–")
        win.show_phase("consumption")
        _setup.turn_events(self.app, 200)
        self.assertTrue(win.consumption_page.is_built())

    def test_the_stale_mark_told_before_is_there_at_the_visit(self):
        from unittest import mock
        win = self.win
        with mock.patch.object(win.session, "energy_outdated", return_value=True):
            win._show_stale()                                         # told to pages that are not there
        self.assertEqual([p.is_built() for p in self.pages], [False, False, False])
        self.assertTrue(win.tabs.is_stale("production"))
        win.show_phase("consumption")
        _setup.turn_events(self.app, 100)
        self.assertTrue(win.consumption_page.stale)                   # and there when it is
        self.assertFalse(win.economics_page.is_built())

    def test_a_widget_asked_of_a_page_makes_only_that_page(self):
        win = self.win
        self.assertFalse(win.consumption_page.is_built())
        self.assertIsNotNone(win.consumption_page.mode)               # asked: made
        self.assertEqual([p.is_built() for p in self.pages], [False, True, False])

if __name__ == "__main__":
    unittest.main()
