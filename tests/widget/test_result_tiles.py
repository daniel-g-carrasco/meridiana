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

    def shown(self, tiles, width):
        self.addCleanup(_setup.dispose, tiles)
        self.addCleanup(tiles.hide)
        tiles.resize(width, 400)
        tiles.show()
        self.app.processEvents()

    def test_every_tile_has_the_same_size_at_any_width_and_a_long_detail_never_moves_the_numbers(self):
        """R309, R310: one grid for the three phases, equal columns, equal heights, the number on one line."""
        from meridiana.ui.energy_pages import Tiles
        _setup.meridiana_look()
        for width in (300, 500, 800, 1150, 1700):
            tiles = Tiles(list("abcdefghi"))
            for t in tiles.tiles:
                t.set("420.701 kWh", "typical year")
            tiles[6].set("38 %", "of the consumption, when a system produces most, and a sentence long enough to wrap")
            tiles[7].set("–")
            self.shown(tiles, width)
            self.assertEqual(len({t.height() for t in tiles.tiles}), 1, width)
            self.assertLessEqual(max(t.width() for t in tiles.tiles) - min(t.width() for t in tiles.tiles), 1, width)
            self.assertEqual(len({t.value.y() for t in tiles.tiles}), 1, width)
            self.assertEqual(tiles.height(), tiles.tiles[-1].geometry().bottom() + 1, width)
            detail = tiles[6].detail
            self.assertGreaterEqual(detail.height(), detail.heightForWidth(detail.width()), width)
            self.assertLessEqual(detail.geometry().bottom(), tiles[6].height(), width)

    def test_a_tile_is_only_as_tall_as_it_needs(self):
        """R309: 195 px for a label, a number and a line in Daniel's screenshot."""
        from meridiana.ui.energy_pages import Tiles
        _setup.meridiana_look()
        tiles = Tiles(["Energy a year", "Power"])
        tiles[0].set("420.701 kWh", "typical year")
        tiles[1].set("331,20 kWp", "200,0 kW AC, DC/AC 1,66")
        self.shown(tiles, 800)
        self.assertLess(tiles[0].height(), 110)

    def test_the_number_and_its_unit_stand_on_one_baseline(self):
        from meridiana.ui.energy_pages import Tiles
        _setup.meridiana_look()
        tiles = Tiles(["Energy a year"])
        tiles[0].set("420.701 kWh")
        self.shown(tiles, 400)
        t = tiles[0]
        value = t.value.y() + t.value.fontMetrics().ascent()
        unit = t.unit.y() + t.unit.contentsMargins().top() + t.unit.fontMetrics().ascent()
        self.assertEqual(value, unit)
        self.assertEqual(t.unit.x(), t.value.geometry().right() + 1 + t.layout().itemAt(1).layout().spacing())

    def test_the_label_wraps_without_a_tooltip_and_the_numbers_stay_on_their_line(self):
        """R309: the bubble «Potenza» over the word Potenza; a long label is whole, not cut, and the short one
        beside it keeps its number on the same line."""
        from meridiana.ui.energy_pages import Tiles
        _setup.meridiana_look()
        tiles = Tiles(["Power", "A label far too long to stand whole in a narrow tile of the grid"], key=-1)
        self.shown(tiles, 330)
        self.assertEqual([t.label.toolTip() for t in tiles.tiles], ["", ""])
        self.assertEqual(tiles[0].value.y(), tiles[1].value.y())
        long = tiles[1].label
        self.assertGreater(long.height(), long.fontMetrics().lineSpacing())
        self.assertGreaterEqual(long.height(), long.heightForWidth(long.width()))

    def test_what_the_detail_leaves_out_is_in_its_tooltip(self):
        from meridiana.ui.energy_pages import Tiles
        tiles = Tiles(["PVGIS"])
        tiles[0].set("447.191 kWh", "Meridiana -5,9%", "the whole sentence")
        self.assertEqual((tiles[0].detail.text(), tiles[0].detail.toolTip()), ("Meridiana -5,9%", "the whole sentence"))
        tiles[0].set("–")
        self.assertEqual((tiles[0].detail.text(), tiles[0].detail.toolTip()), ("", ""))

    def test_pad_fields_leaves_the_tiles_texts_to_the_grid(self):
        from meridiana.ui.energy_pages import Tiles, scrolled
        from meridiana.ui.style import pad_fields
        tiles = Tiles(["Sale and incentives, first year, long"])
        area = scrolled(tiles)
        self.addCleanup(_setup.dispose, area)
        pad_fields(area)
        self.assertFalse(hasattr(tiles[0].label, "_meridiana_growth"))
        self.assertFalse(hasattr(tiles[0].detail, "_meridiana_growth"))


if __name__ == "__main__":
    unittest.main()
