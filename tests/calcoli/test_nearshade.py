"""Near shading from obstacles: shadows fall away from the sun and grow as it sets, an obstacle south of the
modules shades them at noon in winter and one north of them never does, the part of an obstacle behind the
plane of the modules casts nothing, and the table reads back."""

import math
import unittest

import numpy as np

import _setup  # noqa: F401

from meridiana import layout
from meridiana.energy import nearshade


def flat_modules(y0=2.0, y1=4.0, z=0.0, count=10):
    """A row of flat modules (tilt 0) from x = -5 to 5."""
    return [layout.PlacedModule(row=0, slot=k, group=0, corners=[(x, y0), (x + 1.0, y0), (x + 1.0, y1), (x, y1)],
                                centre=(x + 0.5, (y0 + y1) / 2), z=z, tilt=0.0, azimuth=0.0)
            for k, x in enumerate(np.linspace(-5.0, 4.0, count))]


def wall(y0, y1, height=3.0, z0=0.0):
    return nearshade.prism([(-6.0, y0), (6.0, y0), (6.0, y1), (-6.0, y1)], z0, z0 + height, "wall")


class Shadows(unittest.TestCase):
    def test_the_shadow_falls_away_from_the_sun_and_grows_as_it_sets(self):
        chimney = nearshade.prism([(0, 0), (1, 0), (1, 1), (0, 1)], 0.0, 2.0)
        s = nearshade.plan_shadow(chimney, 180.0, 45.0, 0.0)          # sun in the South at 45°
        self.assertAlmostEqual(s.bounds[3], 3.0, places=6)              # 2 m to the North of the top
        self.assertAlmostEqual(s.bounds[1], 0.0, places=6)
        low = nearshade.plan_shadow(chimney, 180.0, 20.0, 0.0)
        self.assertGreater(low.bounds[3], s.bounds[3])

    def test_what_is_below_the_plane_casts_nothing(self):
        self.assertIsNone(nearshade.plan_shadow(nearshade.prism([(0, 0), (1, 0), (1, 1)], 0.0, 0.5), 180.0, 30.0, 1.0))

    def test_a_concave_footprint_is_cut_into_convex_solids(self):
        ell = [(0, 0), (4, 0), (4, 1), (1, 1), (1, 4), (0, 4)]
        solids = nearshade.prism(ell, 0.0, 1.0)
        self.assertGreater(len(solids), 1)
        s = nearshade.plan_shadow(solids, 0.0, 89.9, 0.5)              # sun overhead: the footprint itself
        self.assertAlmostEqual(s.area, 7.0, places=2)

    def test_a_wall_south_shades_and_one_north_does_not(self):
        south = nearshade.shading(flat_modules(), wall(0.0, 0.5), 0.0, 0.0)
        north = nearshade.shading(flat_modules(), wall(6.0, 6.5), 0.0, 0.0)
        self.assertGreater(float(nearshade.at(south.table, 180.0, 22.0)), 0.9)    # winter noon
        self.assertLess(float(nearshade.at(south.table, 180.0, 66.0)), 0.05)      # summer noon
        self.assertEqual(float(nearshade.at(north.table, 180.0, 22.0)), 0.0)
        self.assertGreater(float(nearshade.at(north.table, 0.0, 22.0)), 0.5)      # a sun in the North, for once
        self.assertTrue(0.5 < south.sky < 1.0, south.sky)
        self.assertEqual(float(nearshade.at(south.table, 180.0, -5.0)), 0.0)

    def test_the_shaded_share_matches_the_geometry(self):
        # a 1 m wall 1 m south of the modules, sun in the South at 30°: the shadow reaches 1/tan(30°) = 1.732 m
        # from the wall's north face, 0.732 m into modules 2 m deep
        sh = nearshade.shading(flat_modules(), wall(0.5, 1.0, height=1.0), 0.0, 0.0)
        self.assertAlmostEqual(float(nearshade.at(sh.table, 180.0, 30.0)), (1.0 / math.tan(math.radians(30)) - 1.0) / 2,
                               delta=0.01)

    def test_a_tilted_plane_sees_the_shadow_on_its_slope(self):
        # modules tilted 30° facing South, their low edge at y = 4, z = 0; a 1.5 m wall at y 0..0.5.
        # the sun in the South at 20°: a point of the modules at height z is shaded when the wall hides the sun
        tilt = 30.0
        depth = 2.0 * math.cos(math.radians(tilt))
        rise = 2.0 * math.sin(math.radians(tilt))
        pm = layout.PlacedModule(row=0, slot=0, group=0, corners=[(-5, 4.0), (5, 4.0), (5, 4.0 + depth), (-5, 4.0 + depth)],
                                 centre=(0.0, 4.0 + depth / 2), z=rise / 2, tilt=tilt, azimuth=0.0)
        sh = nearshade.shading([pm], wall(0.0, 0.5, height=1.5), tilt, 0.0)
        # along the slope s (0..2 m) the point is at y = 4 + s cos30, z = s sin30; shaded while
        # z < 1.5 - (y - 0.5) tan20
        el = math.radians(20)
        s_lim = (1.5 - 3.5 * math.tan(el)) / (math.sin(math.radians(tilt)) + math.cos(math.radians(tilt)) * math.tan(el))
        self.assertAlmostEqual(float(nearshade.at(sh.table, 180.0, 18.0 + 2.0)), s_lim / 2.0, delta=0.01)

    def test_an_obstacle_behind_the_plane_casts_nothing_on_it(self):
        # a roof pitch facing South and, north of it, a lower box whose top is under the plane extended
        tilt = 30.0
        pm = layout.PlacedModule(row=0, slot=0, group=0, corners=[(-1, 0.0), (1, 0.0), (1, 1.0), (-1, 1.0)],
                                 centre=(0.0, 0.5), z=0.5 * math.tan(math.radians(tilt)), tilt=tilt, azimuth=0.0)
        box = nearshade.prism([(-1, 2.0), (1, 2.0), (1, 3.0), (-1, 3.0)], 0.0, 1.0, "box")
        sh = nearshade.shading([pm], box, tilt, 0.0)
        self.assertEqual(float(sh.table.max()), 0.0)
        self.assertEqual(sh.sky, 1.0)

    def test_each_module_has_its_shade_and_a_string_is_lost_with_its_worst(self):
        mods = flat_modules()                                   # ten modules side by side, x from -5 to 5
        chimney = nearshade.prism([(-4.6, 0.0), (-4.4, 0.0), (-4.4, 0.2), (-4.6, 0.2)], 0.0, 3.0, "chimney")
        sh = nearshade.shading(mods, chimney, 0.0, 0.0)
        i = list(nearshade.ELEVATIONS).index(30.0)
        j = list(nearshade.AZIMUTHS).index(180.0)
        each = sh.modules[:, i, j]
        self.assertGreater(each[0], 0.0)                         # the chimney's shadow falls on the first module
        self.assertTrue((each[1:] == 0.0).all())
        self.assertAlmostEqual(float(each.mean()), float(sh.table[i, j]), places=5)
        self.assertEqual(int(sh.blocks[0, i, j]), 1)            # a thin shadow up the middle strip of cells
        strings = [[m.key for m in mods[:5]], [m.key for m in mods[5:]]]
        extra = nearshade.electrical(sh, strings, [180.0], [30.0])
        expected = 5 * (1 - each[:5].mean()) * 1 / (sh.per_module * 5 + 1) / 10      # Martinez-Moreno 2010, eq. 6
        self.assertAlmostEqual(float(extra[0]), expected, places=5)
        self.assertLess(float(extra[0]), 0.1)                              # one module of five: about its share
        self.assertEqual(float(nearshade.electrical(sh, [], [180.0], [30.0])[0]), 0.0)

    def test_the_blocks_follow_how_the_module_stands(self):
        upright = nearshade.block_boxes((0.0, 0.0, 1.0, 2.0))
        self.assertEqual(len(upright), 3)
        self.assertTrue(all(math.isclose(b[3] - b[1], 2.0) for b in upright))     # strips along the long side
        flat = nearshade.block_boxes((0.0, 0.0, 2.0, 1.0))
        self.assertTrue(all(math.isclose(b[2] - b[0], 2.0) for b in flat))
        self.assertEqual(len(nearshade.block_boxes((0.0, 0.0, 1.0, 2.0), (3, 2))), 6)
        self.assertEqual(nearshade.blocks_of(120), (3, 2))
        self.assertEqual(nearshade.blocks_of(72), (3, 1))

    def test_a_shadow_from_below_touches_every_strip_and_half_cells_keep_their_upper_half(self):
        # a 1 m wall 1.5 m south of upright modules: at 30 degrees its shadow covers their lowest 23 cm
        i = list(nearshade.ELEVATIONS).index(30.0)
        j = list(nearshade.AZIMUTHS).index(180.0)
        full = nearshade.shading(flat_modules(), wall(0.0, 0.5, height=1.0), 0.0, 0.0, layout=(3, 1))
        half = nearshade.shading(flat_modules(), wall(0.0, 0.5, height=1.0), 0.0, 0.0, layout=(3, 2))
        self.assertTrue((full.blocks[:, i, j] == 3).all())
        self.assertTrue((half.blocks[:, i, j] == 3).all())
        strings = [[m.key for m in flat_modules()]]
        lost_full = float(nearshade.electrical(full, strings, [180.0], [30.0])[0])
        lost_half = float(nearshade.electrical(half, strings, [180.0], [30.0])[0])
        self.assertGreater(lost_full, 1.8 * lost_half)                      # the upper halves still work

    def test_a_row_shaded_from_below_loses_what_its_cells_stand_in(self):
        f = np.array([0.0, 0.2, 0.6])
        upright = nearshade.rows_electrical(f, 1, True, (3, 1))
        self.assertTrue(np.allclose(upright, [0.0, 0.8, 0.4]))           # every strip touched: the rest is lost
        halves = nearshade.rows_electrical(f, 1, True, (3, 2))
        self.assertTrue(np.allclose(halves, [0.0, 0.4, 0.4]))            # the upper half holds below half the height
        lying = nearshade.rows_electrical(f, 1, False, (3, 1))
        self.assertTrue(np.allclose(lying, [0.0, 0.8 / 3, 0.4 * 2 / 3]))   # the strips go one by one
        two = nearshade.rows_electrical(np.array([0.2]), 2, True, (3, 1))
        self.assertAlmostEqual(float(two[0]), 0.6 / 2, places=9)          # only the lower module of the stack

    def test_no_obstacles_no_shade(self):
        sh = nearshade.shading(flat_modules(), [], 0.0, 0.0)
        self.assertEqual(float(np.abs(sh.table).sum()), 0.0)
        self.assertEqual(sh.sky, 1.0)

    def test_the_areas_and_touches_read_on_the_rings_agree_with_shapely(self):
        # the shaded area of rectangles measured on the rings (Green's theorem, edge by edge) against
        # shapely's intersection, on hulls of random points, their unions (holes included) and random
        # rectangles; and the blocks a hull meets against shapely's intersects
        import shapely
        rng = np.random.default_rng(5)
        hulls = shapely.convex_hull(shapely.multipoints(rng.uniform(-4, 4, (300, 9, 2))))
        shifted = shapely.transform(hulls, lambda c: c + rng.uniform(-3, 3, (1, 2)))
        unions = shapely.union_all(np.stack([hulls, shifted, shapely.transform(hulls, lambda c: c * 0.5 + 2.0)]),
                                   axis=0)
        ring = shapely.polygons([(0, 0), (6, 0), (6, 6), (0, 6)], holes=[[(2, 2), (4, 2), (4, 4), (2, 4)]])
        geoms = np.concatenate([hulls, unions, np.array([ring] * 20, dtype=object)])
        n = len(geoms)
        lo = rng.uniform(-5, 4, (n, 2))
        rects = np.concatenate([lo, lo + rng.uniform(0.2, 3, (n, 2))], axis=1)
        boxes = shapely.box(rects[:, 0], rects[:, 1], rects[:, 2], rects[:, 3])
        got = nearshade._Rings(geoms).areas_in(np.arange(n), rects)
        want = shapely.area(shapely.intersection(geoms, boxes))
        self.assertTrue(np.allclose(got, want, rtol=1e-9, atol=1e-12), float(np.max(np.abs(got - want))))
        self.assertGreater(float(want[-20:].sum()), 0.0)
        blocks = np.stack([rects, rects + [0.5, 0.0, 0.5, 0.0], rects + [0.0, 1.0, 0.0, 1.0]], axis=1)
        met = nearshade._Rings(hulls).touches(np.arange(len(hulls)), blocks[:len(hulls)])
        for k in range(3):
            b = blocks[:len(hulls), k]
            want_k = shapely.intersects(hulls, shapely.box(b[:, 0], b[:, 1], b[:, 2], b[:, 3]))
            self.assertTrue((met[:, k] == want_k).all())
        self.assertTrue(met.any() and not met.all())

    def test_a_long_array_in_strings_is_read_in_chunks_and_adds_up(self):
        # many modules in many strings: the electrical loss equals the one computed string by string
        mods = flat_modules(count=300)
        sh = nearshade.shading(mods, wall(0.0, 0.5, height=1.0) + nearshade.prism(
            [(-4.6, 0.0), (-4.4, 0.0), (-4.4, 0.2), (-4.6, 0.2)], 0.0, 3.0, "chimney"), 0.0, 0.0)
        keys = [m.key for m in mods]
        strings = [keys[i:i + 7] for i in range(0, 300, 7)]
        az, el = np.array([180.0, 150.0, 210.0, 90.0]), np.array([30.0, 12.0, 50.0, -3.0])
        got = nearshade.electrical(sh, strings, az, el)
        want = np.zeros(4)
        for s in strings:
            want += nearshade.electrical(sh, [s], az, el)
        self.assertTrue(np.allclose(got, want, rtol=1e-9, atol=1e-12))
        self.assertEqual(float(got[-1]), 0.0)


class OwnRoof(unittest.TestCase):
    """The other pitches of a sub-field's own building cast their shadows whatever the roof (task 16a): on an L
    the long arm shades the pitch of the other arm that faces East, on a winter morning."""

    def test_one_arm_of_an_l_shades_the_other_on_a_winter_morning(self):
        from datetime import date

        from meridiana import model, sun
        from meridiana.energy import system
        p = model.Project(name="L")
        p.site = model.Site(lat=45.5226, lon=9.03)
        p.buildings.append(model.Building(id="b1", name="Casa", footprint=[[0, 0], [20, 0], [20, 8], [8, 8], [8, 18],
                                                                        [0, 18]],
                                          height=6.0, roof=model.Roof(type="gable", tilt=30.0)))
        # on the pitch of side 4, the one facing East on the arm that runs North
        sf = model.SubField(id="s1", name="Est", ring=[[4.3, 8.2], [7.9, 8.2], [7.9, 17.0], [4.3, 17.0]],
                            building="b1", pitch=3, params={"mounting": "coplanar"}, filled=True)
        p.subfields.append(sf)
        result = p.fill(sf)
        self.assertGreater(result.count, 0)
        self.assertAlmostEqual(result.azimuth, -90.0, places=6)
        solids = system.obstacles_of(p, sf)
        names = {s.name for s in solids}
        self.assertIn("Casa, pitch of side 1", names)          # the long arm, facing South
        self.assertNotIn("Casa, pitch of side 4", names)       # not its own
        self.assertTrue(all(n.startswith("Casa, pitch of side") for n in names))   # nothing else stands there
        pos = sun.position(45.5226, 9.03, sun.utc_at_solar_time(9.03, date(2026, 12, 21), 9.0))
        self.assertLess(pos.elevation, 12.0)
        sh = nearshade.shading(result.modules, solids, result.tilt, result.azimuth)
        self.assertGreater(float(nearshade.at(sh.table, pos.bearing, pos.elevation)), 0.1)     # 12 % at 9:00
        # at noon the sun is South, over the long arm's own ridge: the East pitch sees no shade from it
        noon = sun.position(45.5226, 9.03, sun.utc_at_solar_time(9.03, date(2026, 12, 21), 12.0))
        self.assertLess(float(nearshade.at(sh.table, noon.bearing, noon.elevation)),
                        float(nearshade.at(sh.table, pos.bearing, pos.elevation)))


if __name__ == "__main__":
    unittest.main()
