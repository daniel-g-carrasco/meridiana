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

    def test_equal_earth_has_the_published_dimensions_and_the_site_at_its_centre(self):
        west = worldmap.equal_earth(-180, 0)
        east = worldmap.equal_earth(180, 0)
        north = worldmap.equal_earth(0, 90)
        south = worldmap.equal_earth(0, -90)
        self.assertAlmostEqual(east[0] - west[0], 34_487_918.228, places=3)
        self.assertAlmostEqual(north[1] - south[1], 16_785_855.247, places=3)
        self.assertAlmostEqual((east[0] - west[0]) / (north[1] - south[1]), 2.05458213, places=8)
        sample = worldmap.equal_earth(122, 47)
        self.assertEqual((round(sample[0] / worldmap.EQUAL_EARTH_RADIUS, 2),
                          round(sample[1] / worldmap.EQUAL_EARTH_RADIUS, 2)), (1.55, 0.89))
        self.assertEqual(worldmap.equal_earth(9.19, 45.4642, 9.19, 45.4642), (0.0, 0.0))
        self.assertAlmostEqual(worldmap.equal_earth(9.19, 45.4642)[0], 752_019.112287203, places=6)
        self.assertAlmostEqual(worldmap.equal_earth(9.19, 45.4642)[1], 5_529_850.137352033, places=6)

    def test_equal_earth_is_symmetric_and_wraps_the_central_meridian(self):
        for lon, lat in ((-73, 12), (9.19, 45.4642), (145, -35)):
            with self.subTest(lon=lon, lat=lat):
                left = worldmap.equal_earth(-lon, lat)
                right = worldmap.equal_earth(lon, lat)
                self.assertAlmostEqual(left[0], -right[0], places=9)
                self.assertAlmostEqual(left[1], right[1], places=9)
        at_site = worldmap.equal_earth(-170.81, 45.4642, 9.19, 45.4642)
        opposite = worldmap.equal_earth(189.19, 45.4642, 9.19, 45.4642)
        self.assertAlmostEqual(at_site[0], -opposite[0], places=9)
        self.assertAlmostEqual(at_site[1], opposite[1], places=9)
        self.assertGreater(abs(at_site[0]), 1_000_000)


if __name__ == "__main__":
    unittest.main()
