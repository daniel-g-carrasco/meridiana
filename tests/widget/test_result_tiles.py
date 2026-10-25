"""The tiles of the results (ui/energy_pages.py, task 17a): a number split from its unit and a sentence not, cards
without borders, the first one the key one. PySide6 and a display (offscreen will do)."""

import unittest

import _setup

from meridiana import theme_colors

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Tiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_a_number_is_split_from_its_unit_and_a_sentence_is_not(self):
        from meridiana.ui.energy_pages import split_unit
        self.assertEqual(split_unit("92.410 kWh"), ("92.410", "kWh"))
        self.assertEqual(split_unit("1.247 kWh/kWp"), ("1.247", "kWh/kWp"))
        self.assertEqual(split_unit("82,6 %"), ("82,6", "%"))
        self.assertEqual(split_unit("1,5 years"), ("1,5", "years"))
        self.assertEqual(split_unit("not within the years"), ("not within the years", ""))
        self.assertEqual(split_unit("–"), ("–", ""))
        self.assertEqual(split_unit("48.300"), ("48.300", ""))

    def test_the_tiles_are_cards_without_borders_and_the_first_is_the_key_one(self):
        from PySide6.QtWidgets import QFrame

        from meridiana.ui.energy_pages import Tiles
        tiles = Tiles(["Energy a year", "Specific yield", "Performance ratio"])
        self.assertEqual([t.property("key") for t in tiles.tiles], [True, False, False])
        self.assertTrue(all(t.objectName() == "tile" and t.frameShape() == QFrame.Shape.NoFrame for t in tiles.tiles))
        tiles[0].set("92.410 kWh", "typical year")
        self.assertEqual((tiles[0].value.text(), tiles[0].unit.text(), tiles[0].detail.text()),
                         ("92.410", "kWh", "typical year"))
        self.assertEqual(tiles[0].text(), "92.410 kWh")
        tiles[1].set("–")
        self.assertEqual((tiles[1].value.text(), tiles[1].unit.text()), ("–", ""))
        self.assertTrue(tiles[1].unit.isHidden())
        none = Tiles(["a", "b"], key=-1)
        self.assertEqual([t.property("key") for t in none.tiles], [False, False])
        t = theme_colors.derive("#8b5a12", True).tokens
        self.assertGreaterEqual(theme_colors.contrast(t["field"], t["panel"]), 1.05)      # R2: tiles on the sink


if __name__ == "__main__":
    unittest.main()
