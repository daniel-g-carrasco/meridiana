"""The sun where NREL's SPA puts it, and rows far enough apart not to shade each other."""

import json
import math
import unittest
from datetime import date, datetime

import _setup

from meridiana import geo, sun

REFERENCE = json.loads(_setup.fixture_text("sun_reference.json"))["rows"]


class Position(unittest.TestCase):
    def test_elevation_agrees_with_spa_within_a_hundredth_of_a_degree(self):
        worst = 0.0
        for r in REFERENCE:
            p = sun.position(r["lat"], r["lon"], datetime.fromisoformat(r["utc"]))
            worst = max(worst, abs(p.elevation - r["elevation"]))
        self.assertLess(worst, 0.01)

    def test_bearing_agrees_with_spa_when_the_sun_is_up_and_not_overhead(self):
        worst = 0.0
        for r in REFERENCE:
            if not 1.0 < r["elevation"] < 85.0:
                continue
            p = sun.position(r["lat"], r["lon"], datetime.fromisoformat(r["utc"]))
            d = (p.bearing - r["azimuth"] + 180.0) % 360.0 - 180.0
            worst = max(worst, abs(d))
        self.assertLess(worst, 0.02)

    def test_refraction_lifts_the_low_sun_as_spa_does(self):
        worst = 0.0
        for r in REFERENCE:
            if r["elevation"] < 3.0:
                continue
            p = sun.position(r["lat"], r["lon"], datetime.fromisoformat(r["utc"]))
            worst = max(worst, abs(p.apparent - r["apparent_elevation"]))
        self.assertLess(worst, 0.05)

    def test_a_time_without_zone_is_refused(self):
        with self.assertRaises(ValueError):
            sun.position(45.0, 9.0, datetime(2026, 6, 21, 12))

    def test_at_solar_noon_the_sun_is_south_in_italy(self):
        when = sun.utc_at_solar_time(9.19, date(2026, 12, 21), 12.0)
        p = sun.position(45.4642, 9.19, when)
        self.assertAlmostEqual(p.bearing, 180.0, delta=0.05)
        self.assertAlmostEqual(p.azimuth, 0.0, delta=0.05)
        # 90 - latitude - 23.44: the winter solstice noon in Milan
        self.assertAlmostEqual(p.elevation, 90 - 45.4642 - 23.44, delta=0.05)


class RowSpacing(unittest.TestCase):
    def test_the_noon_criterion_matches_the_limit_angle_of_the_guide(self):
        # one position at solar noon, rows facing South: d = h / tan(elevation)
        when = sun.utc_at_solar_time(9.19, date(2026, 12, 21), 12.0)
        p = sun.position(45.4642, 9.19, when)
        rise = 2.278 * math.sin(math.radians(10))
        d = sun.row_clearance(rise, 180.0, [p])
        self.assertAlmostEqual(d, rise / math.tan(math.radians(p.elevation)), places=9)
        self.assertAlmostEqual(sun.limit_angle(rise, d), p.elevation, places=6)

    def test_a_window_asks_more_than_noon_alone(self):
        lat, lon = 45.4642, 9.19
        rise = 2 * 1.134 * math.sin(math.radians(15))
        noon = sun.row_clearance(rise, 180.0, sun.DesignWindow(start=12, end=12).positions(lat, lon))
        window = sun.row_clearance(rise, 180.0, sun.DesignWindow().positions(lat, lon))
        self.assertGreater(window, noon)

    def test_rows_turned_away_from_south_need_the_cosine_of_the_guide(self):
        p = sun.SunPosition(elevation=20.0, apparent=20.0, bearing=180.0)
        straight = sun.row_clearance(1.0, 180.0, [p])
        turned = sun.row_clearance(1.0, 180.0 + 30.0, [p])
        self.assertAlmostEqual(turned, straight * math.cos(math.radians(30)), places=9)

    def test_a_sun_behind_the_rows_needs_no_clearance(self):
        p = sun.SunPosition(elevation=30.0, apparent=30.0, bearing=0.0)
        self.assertEqual(sun.row_clearance(1.0, 180.0, [p]), 0.0)

    def test_the_window_runs_from_start_to_end_in_steps(self):
        positions = sun.DesignWindow(start=10, end=14, step_minutes=60).positions(45.46, 9.19)
        self.assertEqual(len(positions), 5)
        self.assertLess(positions[0].bearing, 180.0)       # morning: South-East
        self.assertGreater(positions[-1].bearing, 180.0)   # afternoon: South-West

    def test_the_azimuth_of_a_position_follows_the_cei_convention(self):
        p = sun.SunPosition(elevation=10.0, apparent=10.0, bearing=240.0)
        self.assertAlmostEqual(p.azimuth, geo.bearing_to_azimuth(240.0))


if __name__ == "__main__":
    unittest.main()
