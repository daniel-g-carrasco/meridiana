"""The irradiance map (study 45, package 3): the same numbers as the engine. The tiles of a roof read by the map are
those shading() gives when the tiles are laid as modules; the modules' figures average to the year's irradiance of
their array; a coarse tile is the mean of the fine ones it holds; the cap on the tiles raises the step; the key moves
with what makes the figures and only with that; a stop asked stops the reading."""

import unittest

import numpy as np

import _setup  # noqa: F401
from _fixtures import capannone, clear_sky_meteo, mixed

from meridiana.app import jobs
from meridiana.core.compute import resources
from meridiana.core.energy import irradiance_map as im
from meridiana.core.energy import nearshade, system
from meridiana.core.energy.simulate import _first_pass

METEO = clear_sky_meteo()


class Tile:
    """A tile laid as a module (layout.PlacedModule's fields that nearshade reads)."""

    def __init__(self, c3, key, tilt, azimuth):
        self.corners = [(float(x), float(y)) for x, y in c3[:, :2]]
        m = c3.mean(axis=0)
        self.centre, self.z, self.tilt, self.azimuth, self.key = (float(m[0]), float(m[1])), float(m[2]), tilt, azimuth, key


def as_modules(surface, grid):
    n, e1, e2 = nearshade.plane_axes(surface.tilt, surface.azimuth)
    out = []
    for i, (u0, v0, u1, v1) in enumerate(grid.rects):
        c3 = np.array([u * e1 + v * e2 + surface.d * n for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))])
        out.append(Tile(c3, str(i), surface.tilt, surface.azimuth))
    return out


class IrradianceMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = mixed()
        cls.results = jobs.layout_of(cls.project)[0]
        cls.losses = system.losses_of(cls.project)
        cls.light = im.prepare(METEO, cls.losses)
        cls.surfaces = {s.id: s for s in im.surfaces_of(cls.project, cls.results)}
        cls.roof = cls.surfaces["b1:0"]             # the shed's flat roof: parapet, smoke vent, plant

    def test_the_surfaces(self):
        # the shed (flat), the house (gable), the villa (hip), the shelter (mono-pitch)
        self.assertEqual(set(self.surfaces), {"b1:0", "b10:0", "b10:1", "b10:2", "b10:3", "b11:0", "b9:0", "b9:2"})
        self.assertEqual({k for k, s in self.surfaces.items() if s.modules}, {"b1:0", "b9:0"})
        self.assertIsNotNone(self.roof.under)                   # the plant stands on it
        self.assertTrue(all(s.solids and s.weight > 0 for s in self.surfaces.values()))

    def test_the_map_reads_what_the_engine_gives_the_tiles(self):
        for sid in ("b1:0", "b9:0"):
            with self.subTest(surface=sid):
                s = self.surfaces[sid]
                grid = im.grid_of(s, 1.0)
                shadows = im.cast_surface(self.light, s, grid)
                ref = nearshade.shading(as_modules(s, grid), s.solids, s.tilt, s.azimuth, self.light.needed, (1, 1), 0)
                got = np.concatenate([t for _start, t in nearshade.shares(shadows, grid.rects)])
                self.assertGreater(float(ref.modules.max()), 0.5)
                # shading() makes the rectangles again from the tiles' corners in space, a few 1e-15 m from the
                # grid's: the shares differ by 8e-15 at most (b1:0, 789 values of 1,2 million); with shading()'s own
                # rectangles the light way is identical to the bit (test_nearshade_cast)
                self.assertLessEqual(float(np.abs(got.astype(float) - ref.modules.astype(float)).max()), 1e-12)
                reader = im.surface_reader(self.light, s)
                level = im.read(self.light, reader, shadows, grid)
                for name, value in zip(("year", "loss", "hours"), reader.read(ref.modules), strict=True):
                    np.testing.assert_allclose(getattr(level, name).ravel()[grid.index], value, rtol=1e-6, atol=1e-6)
                self.assertTrue(np.isnan(level.year.ravel()[np.setdiff1d(np.arange(level.year.size), grid.index)]).all())

    def test_the_modules_average_to_the_years_irradiance(self):
        first = _first_pass(METEO, system.arrays_of(self.project, self.results), None, self.losses, None)
        for ap in first.per_array:
            with self.subTest(array=ap.a.key):
                values = im.module_values(self.light, ap)
                year = float(ap.g_near.sum()) / 1000.0
                self.assertIsNotNone(ap.near)
                self.assertEqual(len(values.year), len(ap.near.keys))
                self.assertLess(abs(float(values.year.astype(float).mean()) - year) / year, 0.0005)    # study 45: 0,05 %
                self.assertAlmostEqual(values.free, float(ap.g_rows.sum()) / 1000.0, places=6)
                self.assertGreater(float(values.loss.max()), 0.0)

    def test_without_obstacles_the_modules_are_the_year(self):
        project = capannone()
        results = jobs.layout_of(project)[0]
        first = _first_pass(METEO, system.arrays_of(project, results), None, system.losses_of(project), None)
        ap = first.per_array[0]
        self.assertIsNone(ap.near)
        values = im.module_values(self.light, ap)
        np.testing.assert_allclose(values.year, float(ap.g_near.sum()) / 1000.0, rtol=1e-12)
        self.assertFalse(values.loss.any())

    def test_a_coarse_tile_is_the_mean_of_its_fine_tiles(self):
        coarse, fine = im.grid_of(self.roof, 2.0), im.grid_of(self.roof, 0.5)
        shadows = im.cast_surface(self.light, self.roof, coarse)            # one cast for both steps
        reader = im.surface_reader(self.light, self.roof)
        big, small = (im.read(self.light, reader, shadows, g) for g in (coarse, fine))
        ri, ci = coarse.iv * 4 - fine.iv, coarse.iu * 4 - fine.iu         # where the coarse grid starts in the fine
        checked = 0
        for i, j in zip(*np.nonzero(np.isfinite(big.year)), strict=True):
            block = (slice(ri + 4 * i, ri + 4 * i + 4), slice(ci + 4 * j, ci + 4 * j + 4))
            years = small.year[block]
            if years.shape != (4, 4) or not np.isfinite(years).all():
                continue                    # on the border or under an obstacle: not every fine tile is computed
            checked += 1
            for name in ("year", "loss", "hours"):
                self.assertAlmostEqual(float(getattr(big, name)[i, j]), float(getattr(small, name)[block].astype(float).mean()),
                                       delta=1e-6 * max(1.0, abs(float(getattr(big, name)[i, j]))) * 4)
        self.assertGreater(checked, 100)
        self.assertGreater(float(np.nanmax(big.loss)), 1.0)

    def test_the_cap_raises_the_step(self):
        grid = im.grid_of(self.roof, 0.5, cap=500)
        self.assertGreater(grid.step, 0.5)
        self.assertEqual(grid.step % 0.5, 0.0)
        self.assertLessEqual(int(grid.inside.sum()), 500)
        self.assertGreater(int(im.grid_of(self.roof, grid.step / 2.0).inside.sum()), 500)

    def test_the_key_moves_with_what_makes_the_figures(self):
        s, grid = self.roof, im.grid_of(self.roof, 1.0)
        key = im.key_of(self.light, s, grid)
        again = im.surfaces_of(self.project, self.results)
        self.assertEqual(im.key_of(self.light, next(x for x in again if x.id == s.id), grid), key)
        far = nearshade.prism([(5000, 5000), (5001, 5000), (5001, 5001)], 0.0, 3.0, "far")
        near = nearshade.prism([(10, 25), (12, 25), (12, 27)], 0.0, 30.0, "tower")
        from dataclasses import replace
        self.assertEqual(im.key_of(self.light, replace(s, solids=s.solids + far), grid), key)
        self.assertNotEqual(im.key_of(self.light, replace(s, solids=s.solids + near), grid), key)
        self.assertNotEqual(im.key_of(self.light, s, im.grid_of(s, 0.5)), key)
        self.assertNotEqual(im.key_of(im.with_day(self.light, (6, 21)), s, grid), key)
        self.assertNotEqual(im.key_of(im.prepare(METEO, system.Losses.from_dict({"albedo": 0.3})), s, grid), key)

    def test_another_day_reuses_the_cast(self):
        grid = im.grid_of(self.roof, 2.0)
        shadows = im.cast_surface(self.light, self.roof, grid)
        june = im.with_day(self.light, (6, 21))
        december = im.read(self.light, im.surface_reader(self.light, self.roof), shadows, grid)
        summer = im.read(june, im.surface_reader(june, self.roof), shadows, grid)
        self.assertGreater(summer.day_free, december.day_free + 5.0)
        self.assertTrue(np.array_equal(summer.year, december.year, equal_nan=True))

    def test_a_stop_asked_stops_the_reading(self):
        grid = im.grid_of(self.roof, 2.0)
        shadows = im.cast_surface(self.light, self.roof, grid)
        reader = im.surface_reader(self.light, self.roof)
        seen = []

        def progress(done, total):
            seen.append((done, total))
            resources.STOP.set()
        try:
            with self.assertRaises(resources.Stopped):
                im.read(self.light, reader, shadows, grid, chunk=10, progress=progress)
        finally:
            resources.STOP.clear()
        self.assertEqual(seen, [(10, len(grid.rects))])

    def test_the_classes(self):
        loss = np.array([0.0, 1.99, 2.0, 4.9, 5.1, 10.0, 19.9, 39.0, 40.0, 99.0, 100.0, np.nan, -1e-12, 3.0])
        inside = np.ones(len(loss), dtype=bool)
        inside[-2] = False
        under = np.zeros(len(loss), dtype=bool)
        under[-1] = True
        got = im.classes(loss, inside, under)
        self.assertEqual(got.dtype, np.uint8)
        self.assertEqual(got.tolist(), [0, 0, 1, 1, 2, 3, 3, 4, 5, 5, 5, im.OUTSIDE, im.OUTSIDE, im.UNDER])


if __name__ == "__main__":
    unittest.main()
