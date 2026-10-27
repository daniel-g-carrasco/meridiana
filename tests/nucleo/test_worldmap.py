"""The shipped Natural Earth world map: public boundaries at known cities and the declared package weight."""

import unittest

import _setup  # noqa: F401

from meridiana import paths, worldmap


class WorldMap(unittest.TestCase):
    def test_known_cities_fall_in_their_countries(self):
        for lon, lat, expected in ((12.4964, 41.9028, "Italy"), (2.3522, 48.8566, "France"),
                                   (31.2357, 30.0444, "Egypt"), (-0.1276, 51.5072, "United Kingdom")):
            with self.subTest(city=expected):
                self.assertEqual(worldmap.country_at(lon, lat), expected)

    def test_the_compressed_data_ship_at_the_declared_weight(self):
        path = paths.shipped(*worldmap.DATA)
        self.assertIsNotNone(path)
        self.assertEqual(path.stat().st_size, worldmap.DECLARED_BYTES)
        self.assertLess(worldmap.DECLARED_BYTES, 210_000)
        self.assertEqual(len(worldmap.countries()), 177)


if __name__ == "__main__":
    unittest.main()
