"""The light way of the near shading (study 45, package 2): the shadows of a plane cast once and the shaded shares of
rectangles read in groups give the same tables as shading() gives the modules, to the last bit; and shading() itself
is the same as before the light way was drawn out of it (its digests, recorded before)."""

import hashlib
import sys
import unittest

import numpy as np

import _setup  # noqa: F401
from _fixtures import clear_sky_meteo, mixed

from meridiana.app import jobs
from meridiana.core.compute import resources
from meridiana.core.energy import nearshade, simulate, system

# shading() of the two arrays of mixed() (the shed's rows with a parapet, a vent and a plant; a gable pitch with a
# chimney, some modules wholly shaded) on the cells of the clear sky's sun path, recorded on 13/11/2026 before the
# light way: the bytes of every table on the platform they were recorded on, the tables rounded to 1e-6 on any
# other (the trigonometry of another libm may move a last bit)
RECORDED_ON = "win32"
REFERENCE = {"s1.0": ("29f13200c6445d51", "0b202d948338e597"), "s9.0": ("a6ad410b7d520c6e", "e8b9dabad9ce4382")}


def digests(sh: nearshade.Shading) -> tuple[str, str]:
    exact, rounded = hashlib.sha256(), hashlib.sha256()
    parts = [sh.table, sh.modules, sh.blocks, sh.block_fractions]
    parts += [sh.cell_histograms[k] for k in sorted(sh.cell_histograms)]
    for a in parts:
        a = np.ascontiguousarray(a)
        exact.update(a.tobytes())
        rounded.update((np.round(a.astype(np.float64), 6) + 0.0 if a.dtype.kind == "f" else a).tobytes())
    exact.update(np.float64(sh.sky).tobytes())
    rounded.update(np.float64(round(sh.sky, 9)).tobytes())
    return exact.hexdigest()[:16], rounded.hexdigest()[:16]


class LightWay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sun = simulate.sun_path(clear_sky_meteo())
        cls.needed = nearshade.needed_cells(sun.azimuth, sun.elevation)
        project = mixed()
        cls.arrays = {a.key: a for a in system.arrays_of(project, jobs.layout_of(project)[0])}
        cls.shadings = {}
        for key, a in cls.arrays.items():
            layout = nearshade.blocks_of(a.module.cells, a.module.diodes, a.module.twin)
            cls.shadings[key] = nearshade.shading(a.placed, a.obstacles, a.tilt, a.azimuth, cls.needed, layout,
                                                  a.module.cells)

    def light_way(self, a, chunk=nearshade.SHARE_CHUNK, geos=None):
        got = np.full((len(a.placed), len(nearshade.ELEVATIONS), len(nearshade.AZIMUTHS)), np.nan, dtype=np.float32)
        casts = []
        for plane in nearshade.module_planes(a.placed, a.tilt, a.azimuth):
            c = nearshade.cast(a.obstacles, a.tilt, a.azimuth, plane.d, plane.bounds, self.needed)
            casts.append(c)
            for start, tables in nearshade.shares(c, plane.rects, chunk, geos=geos):
                got[plane.index[start:start + len(tables)]] = tables
        return got, casts

    def test_shading_is_the_same_as_before(self):
        self.assertEqual(set(self.shadings), set(REFERENCE))
        for key, sh in self.shadings.items():
            with self.subTest(array=key):
                exact, rounded = digests(sh)
                self.assertEqual(rounded, REFERENCE[key][1])
                if sys.platform == RECORDED_ON:
                    self.assertEqual(exact, REFERENCE[key][0])

    def test_the_light_way_gives_the_modules_tables(self):
        for key, a in self.arrays.items():
            for chunk in (nearshade.SHARE_CHUNK, 7):            # groups of any size: the same numbers
                with self.subTest(array=key, chunk=chunk):
                    got, casts = self.light_way(a, chunk, geos=False)
                    self.assertTrue(np.array_equal(got, self.shadings[key].modules))
                    self.assertTrue(all(c.used <= c.solids for c in casts))

    def test_geos_cuts_to_the_same_tables(self):
        # the shares differ by about 4e-13 in double precision (study 45); the tables are in single
        for key, a in self.arrays.items():
            with self.subTest(array=key):
                got, _casts = self.light_way(a, geos=True)
                self.assertTrue(np.array_equal(got, self.shadings[key].modules))

    def test_the_cases_are_there(self):
        modules = np.concatenate([sh.modules.ravel() for sh in self.shadings.values()])
        self.assertTrue((modules == 1.0).any(), "a module wholly shaded: read without cutting")
        self.assertTrue(((modules > 0) & (modules < 1)).any(), "a module partly shaded: cut")
        self.assertTrue(any(len(nearshade.module_planes(a.placed, a.tilt, a.azimuth)) > 1 for a in self.arrays.values()))

    def test_simple_shadows_are_cut_as_the_modules_are(self):
        for key, a in self.arrays.items():
            with self.subTest(array=key):
                _got, casts = self.light_way(a)
                self.assertTrue(all(0 < c.vertices <= nearshade.GEOS_VERTICES and not c.geos for c in casts))

    def test_only_the_shadows_that_reach_are_kept(self):
        a = self.arrays["s9.0"]
        far = (1000.0, 1000.0, 1001.0, 1001.0)
        c = nearshade.cast(a.obstacles, a.tilt, a.azimuth, 0.0, far, self.needed)
        self.assertEqual((c.used, len(c.cells), len(c.shadow)), (0, 0, 0))
        (start, tables), = nearshade.shares(c, np.array([far]))
        self.assertEqual((start, tables.shape), (0, (1, len(nearshade.ELEVATIONS), len(nearshade.AZIMUTHS))))
        self.assertFalse(tables.any())

    def test_a_stop_asked_stops_the_cast(self):
        a = self.arrays["s9.0"]
        plane = nearshade.module_planes(a.placed, a.tilt, a.azimuth)[0]
        resources.STOP.set()
        try:
            with self.assertRaises(resources.Stopped):
                nearshade.cast(a.obstacles, a.tilt, a.azimuth, plane.d, plane.bounds, self.needed)
        finally:
            resources.STOP.clear()


if __name__ == "__main__":
    unittest.main()
