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


class CoordinateReader(unittest.TestCase):
    """Official reference: Roma Monte Mario, published by SISEF with its Roma40, ED50 and WGS84 coordinates:
    https://foresta.sisef.org/contents/?id=0228-0010128 . Projection and datum parameters:
    https://epsg.io/3003.proj4 , https://epsg.io/3004.proj4 , https://epsg.io/23032.proj4 ."""

    WGS = (41 + 55 / 60 + 27.851 / 3600, 12 + 27 / 60 + 7.658 / 3600)

    def assert_monte_mario(self, point, metres=3.0):
        dlat = (point.lat - self.WGS[0]) * 111320.0
        dlon = (point.lon - self.WGS[1]) * 111320.0 * math.cos(math.radians(self.WGS[0]))
        self.assertLess(math.hypot(dlat, dlon), metres)

    def test_decimal_degrees_degrees_minutes_and_seconds(self):
        for text, kind in (("45.5226, 9.0300", "decimal"), ("45,5226; 9,0300", "decimal"),
                           ('45°31\'21,36"N 9°01\'48,00"E', "dms"), ("45°31,356'N 9°1,800'E", "ddm")):
            with self.subTest(text=text):
                point = geo.read_coordinates(text)
                self.assertAlmostEqual(point.lat, 45.5226, places=9)
                self.assertAlmostEqual(point.lon, 9.03, places=9)
                self.assertEqual(point.format, kind)
                self.assertEqual(point.datum, "WGS84")

    def test_google_openstreetmap_and_apple_links_without_opening_them(self):
        links = (
            "https://www.google.com/maps/@45.5226,9.0300,17z",
            "https://www.google.com/maps/search/?api=1&query=45.5226%2C9.0300",
            "https://www.openstreetmap.org/?mlat=45.5226&mlon=9.0300#map=17/45.5226/9.0300",
            "https://www.openstreetmap.org/#map=17/45.5226/9.0300",
            "https://maps.apple.com/?ll=45.5226,9.0300",
        )
        for link in links:
            with self.subTest(link=link):
                point = geo.read_coordinates(link)
                self.assertAlmostEqual(point.lat, 45.5226, places=9)
                self.assertAlmostEqual(point.lon, 9.03, places=9)
                self.assertEqual(point.format, "link")

    def test_google_degrees_with_a_comma_between_axes_and_pin_links(self):
        samples = (
            '45°31\'21.36"N, 9°01\'48.00"E',
            "https://www.google.com/maps/place/Rho/@45.5,9.0,14z/data=!4m2!3m1!1s0x0!3d45.5226!4d9.03",
            "https://www.google.com/maps?destination=45.5226%2C9.03",
        )
        for text in samples:
            with self.subTest(text=text):
                point = geo.read_coordinates(text)
                self.assertAlmostEqual(point.lat, 45.5226, places=8)
                self.assertAlmostEqual(point.lon, 9.03, places=8)

    def test_utm_wgs84_ed50_and_gauss_boaga_with_their_datums(self):
        point = geo.read_coordinates("UTM WGS84 33N 288734.086 4644522.480")
        self.assert_monte_mario(point, metres=0.01)
        self.assertEqual((point.datum, point.zone), ("WGS84", "33N"))

        point = geo.read_coordinates("EPSG:23033 288803.139 4644714.664")
        self.assertEqual(point.datum, "ED50")
        self.assertEqual(point.zone, "33N")
        self.assert_monte_mario(point, metres=4.0)

        point = geo.read_coordinates("Gauss-Boaga Roma40 Ovest 1786287.015 4647159.219")
        self.assert_monte_mario(point, metres=4.0)
        self.assertEqual((point.datum, point.zone), ("Roma40", "Ovest"))

    def test_ambiguous_or_impossible_text_says_why(self):
        cases = {
            "45, 9, 3": "two coordinates",
            '45°31\'21" 9°01\'48"': "hemisphere",
            '45°31\'61"N 9°01\'48"E': "60",
            "UTM 33N 500000 4644522": "datum",
            "UTM WGS84 61N 500000 4644522": "zone",
            "EPSG:3003 1644522": "easting and northing",
            "https://www.google.com/maps/place/Roma": "coordinates",
            "95, 9": "latitude",
        }
        for text, reason in cases.items():
            with self.subTest(text=text):
                with self.assertRaisesRegex(geo.CoordinateError, reason):
                    geo.read_coordinates(text)


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
