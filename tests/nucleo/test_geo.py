"""The local frame and the angle conventions: the plan must measure what the ground measures."""

import math
import unittest

import _setup  # noqa: F401

from meridiana import geo

MILANO = geo.Origin(lat=45.4642, lon=9.1900)


def meridional_radius(lat: float) -> float:
    s = math.sin(math.radians(lat))
    return geo.WGS84_A * (1 - geo.WGS84_E2) / (1 - geo.WGS84_E2 * s * s) ** 1.5


def normal_radius(lat: float) -> float:
    s = math.sin(math.radians(lat))
    return geo.WGS84_A / math.sqrt(1 - geo.WGS84_E2 * s * s)


class LocalFrame(unittest.TestCase):
    def test_the_origin_is_at_zero(self):
        x, y = MILANO.to_local(MILANO.lon, MILANO.lat)
        self.assertAlmostEqual(x, 0.0, places=6)
        self.assertAlmostEqual(y, 0.0, places=6)

    def test_a_small_step_north_measures_the_meridional_radius(self):
        dlat = 1e-5
        x, y = MILANO.to_local(MILANO.lon, MILANO.lat + dlat)
        self.assertAlmostEqual(y, meridional_radius(MILANO.lat) * math.radians(dlat), delta=1e-4)
        self.assertAlmostEqual(x, 0.0, delta=1e-6)

    def test_a_small_step_east_measures_the_parallel_radius(self):
        dlon = 1e-5
        x, y = MILANO.to_local(MILANO.lon + dlon, MILANO.lat)
        expected = normal_radius(MILANO.lat) * math.cos(math.radians(MILANO.lat)) * math.radians(dlon)
        self.assertAlmostEqual(x, expected, delta=1e-4)

    def test_points_go_and_come_back_within_a_millimetre_over_two_kilometres(self):
        for x, y in [(0.3, -0.7), (150.0, 80.0), (-950.0, 1200.0), (2000.0, -2000.0)]:
            lon, lat = MILANO.to_lonlat(x, y)
            bx, by = MILANO.to_local(lon, lat)
            self.assertAlmostEqual(bx, x, delta=1e-3)
            self.assertAlmostEqual(by, y, delta=1e-3)

    def test_a_roof_keeps_its_area(self):
        # a 40 x 30 m rectangle built on the plan, sent to the ground and back
        ring = [(10.0, 10.0), (50.0, 10.0), (50.0, 40.0), (10.0, 40.0)]
        back = MILANO.ring_to_local(MILANO.ring_to_lonlat(ring))
        area = 0.5 * abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(back, back[1:] + back[:1], strict=True)))
        self.assertAlmostEqual(area, 1200.0, delta=0.01)


class Angles(unittest.TestCase):
    def test_bearings_read_as_a_compass(self):
        self.assertAlmostEqual(geo.bearing(0, 1), 0.0)
        self.assertAlmostEqual(geo.bearing(1, 0), 90.0)
        self.assertAlmostEqual(geo.bearing(0, -1), 180.0)
        self.assertAlmostEqual(geo.bearing(-1, 0), 270.0)

    def test_the_cei_azimuth_is_zero_south_and_positive_west(self):
        self.assertAlmostEqual(geo.bearing_to_azimuth(180.0), 0.0)
        self.assertAlmostEqual(geo.bearing_to_azimuth(270.0), 90.0)
        self.assertAlmostEqual(geo.bearing_to_azimuth(90.0), -90.0)
        self.assertAlmostEqual(geo.bearing_to_azimuth(0.0), 180.0)

    def test_azimuth_and_bearing_are_inverse(self):
        for alpha in (-179.0, -90.0, -19.0, 0.0, 33.5, 90.0, 180.0):
            self.assertAlmostEqual(geo.bearing_to_azimuth(geo.azimuth_to_bearing(alpha)), alpha)

    def test_a_south_facing_surface_faces_minus_y(self):
        fx, fy = geo.facing_vector(0.0)
        self.assertAlmostEqual(fx, 0.0)
        self.assertAlmostEqual(fy, -1.0)


class Coordinates(unittest.TestCase):
    def test_as_maps_copy_them_and_as_an_italian_writes_them(self):
        for text in ("45.5226, 9.0300", "45,5226; 9,0300", "45.5226;9.03", " 45.5226 9.03 ", "45,5226 9,03"):
            lat, lon = geo.parse_coordinates(text)
            self.assertAlmostEqual(lat, 45.5226, msg=text)
            self.assertAlmostEqual(lon, 9.03, msg=text)

    def test_an_address_is_not_coordinates(self):
        for text in ("Via Roma 1, Rho", "Rho", "45.5226", "45, 9, 3", "95.0, 9.0", "45.0, 190.0", "nan, 9", ""):
            self.assertIsNone(geo.parse_coordinates(text), text)


class Tiles(unittest.TestCase):
    def test_mercator_goes_and_comes_back(self):
        mx, my = geo.lonlat_to_mercator(9.19, 45.4642)
        lon, lat = geo.mercator_to_lonlat(mx, my)
        self.assertAlmostEqual(lon, 9.19, places=9)
        self.assertAlmostEqual(lat, 45.4642, places=9)

    def test_the_tile_of_a_point_contains_it(self):
        lon, lat = 9.0300, 45.5226
        for z in (5, 12, 19):
            x, y = geo.tile_of(lon, lat, z)
            w, s, e, n = geo.tile_bounds(x, y, z)
            mx, my = geo.lonlat_to_mercator(lon, lat)
            self.assertTrue(w <= mx < e and s <= my < n, z)


if __name__ == "__main__":
    unittest.main()
