"""The right zone of the Plant's bar (R298, study 23, C3): three states, one at a time, the plant's summary, the string
chosen compressed (its name and path, its modules and worst remark, the three bars) while one is chosen, the string
being drawn meanwhile; in the low bar the bars give way to the figures in a line."""

import unittest

import _setup

setUpModule = _setup.keep_global_state


class TheStrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look()

    def setUp(self):
        from PySide6.QtGui import QAction
        from widget.test_string_list import plant_of

        from meridiana.ui.plant_page import PlantPage
        actions = {key: QAction(key) for key in ("strings_auto", "strings_manual")}
        self.page = PlantPage(actions)
        self.addCleanup(_setup.dispose, self.page)
        self.plant = plant_of([{"inverter": 1, "mppt": 1, "modules": [f"s1/0:{s}" for s in range(8)]},
                               {"inverter": 1, "mppt": 2, "modules": [f"s1/1:{s}" for s in range(5)]}])
        self.page.show_inverter("1 x Acme AC-20K, 20.0 kW AC")
        self.page.show_plant(self.plant)
        self.page.strip.setFixedSize(300, 72)
        self.page.resize(320, 400)
        self.page.show()
        _setup.turn_events(self.app, 50)

    def test_three_states_one_at_a_time(self):
        page = self.page
        self.assertEqual(page.state(), "summary")
        self.assertTrue(page.texts.isVisibleTo(page.strip))
        page.show_chosen(self.plant, 1)
        self.assertEqual(page.state(), "chosen")
        self.assertTrue(page.chosen_strip.isVisibleTo(page.strip))
        self.assertFalse(page.texts.isVisibleTo(page.strip))
        self.assertTrue(page.chosen_strip.text.startswith("1.2.1 · Inverter 1"))
        self.assertIn("5 modules", page.chosen_strip.text)
        self.assertIn("Uoc", page.chosen_strip.figures)
        page.show_draft_card("String · 1.2", "3 of 6 modules", "short", "#ff8800", "Enter closes")
        self.assertEqual(page.state(), "draft")
        self.assertFalse(page.chosen_strip.isVisibleTo(page.strip))
        page.show_draft_card()
        self.assertEqual(page.state(), "chosen")
        page.show_chosen(self.plant, -1)
        self.assertEqual(page.state(), "summary")
        self.assertEqual(page.chosen_strip.text, "")

    def test_the_tall_bar_has_the_bars_and_the_low_bar_the_figures_in_a_line(self):
        page = self.page
        page.show_chosen(self.plant, 0)
        _setup.turn_events(self.app, 50)
        strip = page.chosen_strip
        self.assertTrue(strip.bars_box.isVisibleTo(strip))
        self.assertTrue(strip.bars["uoc"].isVisibleTo(strip))
        self.assertTrue(strip.bars["umpp"].isVisibleTo(strip))
        self.assertLessEqual(strip.height(), 72)
        page.strip.setFixedSize(300, 44)
        _setup.turn_events(self.app, 50)
        self.assertFalse(strip.bars_box.isVisibleTo(strip))
        self.assertIn("Uoc", strip.remark.text())
        self.assertIn("Umpp", strip.remark.text())
        self.assertLessEqual(strip.height(), 44)


if __name__ == "__main__":
    unittest.main()
