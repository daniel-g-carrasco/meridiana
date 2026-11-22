"""R602: an imported model stood on Meridiana's lawn at its ground floor; on a site whose ground is elsewhere its
parking places flew over the lawn or sank under it, and its basement was buried in the lawn. The model's zero now comes
from its terrain at the foot of the buildings, else from its pavings at the ground, else the ground floor as before
(app/exchange/ifc_ground.py); on the site the lawn is the model's terrain, joined by a slope to the flat lawn around,
and outside a terrain the flat lawn opens on the basement.

The samples (made by hand, no data of any real model, tests/data/ifc/README.md): `terreno-interrato.ifc`, a building
of 20 x 10 m with its ground floor at 0, a flat roof at 6 m, a basement down to -3.2 m, a terrain at -0.6 m around it
(dug under the building) and a parking slab flush with the terrain; `terreno-pavimenti.ifc`, the same without the
terrain; `piani-pari.ifc`, a roof with nothing at the ground."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
from shapely.geometry import Point, Polygon, box

import _setup  # noqa: F401

from meridiana.app.exchange import ifc_export, ifc_ground, ifc_import, ifc_worker
from meridiana.core.model import model

DATA = Path(__file__).resolve().parents[1] / "data" / "ifc"
BASEMENT = box(0, 0, 20, 10)            # the basement's plan in the model's world
TERRAIN = box(-20, -20, 40, 30)         # the terrain's plan


def imported(name: str, terrain: bool = False):
    """(reading, plan, project) of a sample read and imported as the window does (the worker, the plan, apply)."""
    with tempfile.TemporaryDirectory() as folder:
        found = ifc_worker.read(str(DATA / name), "direct", lambda f, w: None, None, folder)
    project = model.Project()
    plan = ifc_import.plan(found, project, "origin", None, name="t", source_name="t.ifc", terrain=terrain)
    ifc_import.apply(project, plan)
    return found, plan, project


def solid(found, name):
    return next(s for s in found["solids"] if s["name"] == name)


def lawn_of(project, half=100.0):
    """The lawn of the 3D for the project, in its plan, about the middle of its buildings."""
    ref = project.resources["ifc_reference"]
    frame, _why = ifc_export.frame_of(project)
    return ifc_ground.lawn(ref, float(frame["turn"]), frame["move"], (0.0, 0.0), half)


def in_plan(project, geometry):
    """A plan in the model's world brought to the project's plan (ifc_export.frame_of)."""
    frame, _why = ifc_export.frame_of(project)
    c, s = np.cos(frame["turn"]), np.sin(frame["turn"])
    p = np.asarray(geometry.exterior.coords, float) - frame["move"]
    return Polygon(np.column_stack((c * p[:, 0] + s * p[:, 1], -s * p[:, 0] + c * p[:, 1])))


def height_at(tris, x, y):
    """The height of the lawn's triangles (n, 3, 3) at the plan point (x, y): the highest face over it."""
    found = []
    for t in tris:
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = t
        d = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if abs(d) < 1e-12:
            continue
        a = ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / d
        b = ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / d
        if min(a, b, 1 - a - b) >= -1e-9:
            found.append(a * z1 + b * z2 + (1 - a - b) * z3)
    return max(found) if found else None


def same(a, b, share=0.97) -> bool:
    return a.intersection(b).area >= share * max(a.area, b.area)


class TerrainZero(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.found, cls.plan, cls.project = imported("terreno-interrato.ifc")
        cls.ref = cls.project.resources["ifc_reference"]

    def test_the_zero_comes_from_the_terrain_at_the_foot_of_the_building(self):
        site = self.found["site_ground"]
        self.assertEqual(site["from"], "terrain")
        self.assertAlmostEqual(site["height"], -0.6, places=2)
        self.assertAlmostEqual(self.found["solids_ground"], 0.0, places=2)        # the ground floor, kept
        # the reference the 3D stands the model on, and the body's height above the lawn (before: 0.0 and 6.0)
        self.assertAlmostEqual(ifc_export.context_ground(self.ref), -0.6, places=2)
        self.assertAlmostEqual(self.project.buildings[0].height, 6.6, places=2)
        self.assertTrue(any("from the model's terrain at the foot of the buildings" in t for t in self.plan.taken))

    def test_the_parking_is_flush_with_the_lawn(self):
        top = solid(self.found, "PARCHEGGIO")["z1"] - ifc_export.context_ground(self.ref)
        self.assertLess(abs(top), 0.03)

    def test_on_the_site_the_lawn_is_the_terrain(self):
        # the terrain left out of the 3D (the default): the lawn on the site is made of its top, DROP under it
        self.assertIn("lawn", self.ref["context"])
        self.assertTrue(any("the lawn follows the model's terrain" in t for t in self.plan.taken))
        tris = ifc_ground.lawn_triangles(self.project, (0.0, 0.0), 100.0)
        self.assertEqual(tris.shape[1:], (3, 3))
        parking = in_plan(self.project, box(22, 0, 34, 10)).centroid
        under = height_at(tris, parking.x, parking.y)
        self.assertAlmostEqual(under, -ifc_ground.DROP, delta=0.005)        # the parking's top is at 0: on top
        # the basement is not buried: the lawn over its plan is at the dig's floor, under the basement's slab
        body = Polygon(self.project.buildings[0].footprint).buffer(-0.3)
        middle = tris.mean(axis=1)
        inside = [i for i, m in enumerate(middle) if body.contains(Point(m[0], m[1]))]
        self.assertTrue(inside)
        self.assertLessEqual(tris[inside][:, :, 2].max(), -3.2 + 0.6 + 0.01)

    def test_the_flat_lawn_opens_on_the_site_and_its_slope(self):
        lawn = lawn_of(self.project)
        self.assertEqual(len(lawn.interiors), 1)
        hole = Polygon(lawn.interiors[0])
        site = in_plan(self.project, TERRAIN)
        self.assertTrue(hole.contains(site.buffer(-0.1)))
        # the terrain at the zero all round: the slope has its shortest run
        self.assertTrue(same(hole, site.buffer(ifc_ground.RAMP_MIN, join_style="mitre"), 0.95))
        self.assertTrue(hole.contains(Polygon(self.project.buildings[0].footprint)))

    def test_the_lawn_follows_the_bodies_moved(self):
        def move(p, dx, dy):
            for b in p.buildings:
                b.footprint = [[x + dx, y + dy] for x, y in b.footprint]
        before = Polygon(lawn_of(self.project).interiors[0])
        move(self.project, 30.0, -12.0)
        try:
            after = Polygon(lawn_of(self.project).interiors[0])
            self.assertAlmostEqual(after.centroid.x - before.centroid.x, 30.0, delta=0.05)
            self.assertAlmostEqual(after.centroid.y - before.centroid.y, -12.0, delta=0.05)
        finally:
            move(self.project, -30.0, 12.0)

    def test_with_the_terrain_drawn_the_model_draws_it(self):
        _found, _plan, project = imported("terreno-interrato.ifc", terrain=True)
        tris = ifc_ground.lawn_triangles(project, (0.0, 0.0), 100.0)
        site = in_plan(project, TERRAIN).buffer(-0.1)
        middle = tris.mean(axis=1)
        self.assertFalse(any(site.contains(Point(m[0], m[1])) for m in middle))     # only the slope and the flat lawn
        self.assertEqual(len(lawn_of(project).interiors), 1)


class PavingZero(unittest.TestCase):
    def test_without_a_terrain_the_zero_comes_from_the_pavings(self):
        found, plan, project = imported("terreno-pavimenti.ifc")
        self.assertEqual(found["site_ground"]["from"], "paving")
        ref = project.resources["ifc_reference"]
        self.assertAlmostEqual(ifc_export.context_ground(ref), -0.6, places=2)
        self.assertLess(abs(solid(found, "PARCHEGGIO")["z1"] - ifc_export.context_ground(ref)), 0.03)
        self.assertNotIn("terrain_outline", ref["context"])
        self.assertNotIn("lawn", ref["context"])
        self.assertTrue(any("from the pavings at the foot of the buildings" in t for t in plan.taken))

    def test_without_a_terrain_the_lawn_opens_on_the_basement(self):
        _found, _plan, project = imported("terreno-pavimenti.ifc")
        ref = project.resources["ifc_reference"]
        rings = ref["context"]["open"]
        self.assertEqual(len(rings), 1)
        self.assertTrue(same(Polygon(rings[0]), BASEMENT))
        lawn = lawn_of(project)
        self.assertEqual(len(lawn.interiors), 1)
        self.assertTrue(same(Polygon(lawn.interiors[0]), Polygon(project.buildings[0].footprint)))
        self.assertAlmostEqual(lawn.area, 200.0 ** 2 - BASEMENT.area, delta=1.0)
        triangles = ifc_ground.lawn_triangles(project, (0.0, 0.0), 100.0)
        self.assertTrue(np.allclose(triangles[:, :, 2], 0.0))
        area = sum(Polygon(t[:, :2]).area for t in triangles)
        self.assertAlmostEqual(area, lawn.area, delta=1.0)


class GroundFloorZero(unittest.TestCase):
    def test_with_nothing_at_the_ground_the_zero_is_the_ground_floor_as_before(self):
        found, plan, project = imported("piani-pari.ifc")
        self.assertIsNone(found["site_ground"])
        ref = project.resources["ifc_reference"]
        self.assertAlmostEqual(ifc_export.context_ground(ref), 0.0, places=3)
        self.assertAlmostEqual(project.buildings[0].height, 6.0, places=2)
        self.assertEqual(ref["context"]["open"], [])
        self.assertIsNone(ifc_ground.lawn_triangles(project, (0.0, 0.0), 100.0))
        self.assertTrue(any("from the storey" in t for t in plan.taken))

    def test_a_project_imported_before_keeps_its_plain_lawn(self):
        _found, _plan, project = imported("terreno-interrato.ifc")
        for key in ("open", "terrain_outline", "lawn"):
            project.resources["ifc_reference"]["context"].pop(key, None)
        self.assertIsNone(ifc_ground.lawn_triangles(project, (0.0, 0.0), 100.0))
        # and a reading made before (no `site_ground`) is planned on its ground floor
        old = {"buildings": [{"ground": 1.0}], "solids_ground": 1.0}
        self.assertEqual(ifc_ground.grounded(old), old)


class TheRule(unittest.TestCase):
    """ifc_ground.zero on triangles made here: a terrain sloping along x by 0.1 (from -2 to +4 m over 60 m), and a
    building of 20 x 10 m in it with a dig under it."""

    def terrain(self, dig=-3.0):
        tris = []
        for x0 in range(-20, 40, 2):
            for y0 in range(-20, 30, 2):
                q = [(x0, y0), (x0 + 2, y0), (x0 + 2, y0 + 2), (x0, y0 + 2)]
                under = 0 <= x0 < 20 and 0 <= y0 < 10
                z = [dig if under else 0.1 * x for x, _y in q]
                p = [(x, y, zz) for (x, y), zz in zip(q, z, strict=True)]
                tris += [[p[0], p[1], p[2]], [p[0], p[2], p[3]]]
        return [np.asarray(tris, float)]

    def test_the_median_at_the_foot_and_the_slope(self):
        building = [{"footprint": [[0, 0], [20, 0], [20, 10], [0, 10]]}]
        site = ifc_ground.zero(0.5, building, [], self.terrain())
        self.assertEqual(site["from"], "terrain")
        self.assertAlmostEqual(site["height"], 1.0, delta=0.15)           # the middle of the band, x = 10
        self.assertLess(site["low"], 0.0)
        self.assertGreater(site["high"], 1.8)
        self.assertGreater(site["high"] - site["low"], ifc_ground.SLOPE)

    def test_the_dig_under_the_building_does_not_count(self):
        building = [{"footprint": [[0, 0], [20, 0], [20, 10], [0, 10]]}]
        a = ifc_ground.zero(0.5, building, [], self.terrain(dig=-3.0))
        b = ifc_ground.zero(0.5, building, [], self.terrain(dig=-9.0))
        self.assertAlmostEqual(a["height"], b["height"], places=6)

    def test_the_lawn_on_a_sloping_site(self):
        surface = ifc_ground.top_surface(self.terrain())
        made = ifc_ground.lawn_surface(surface, 1.0)
        drape = np.asarray(made["drape"]).reshape(-1, 3, 3)
        self.assertAlmostEqual(drape[:, :, 2].max(), 4.0 - ifc_ground.DROP, places=3)
        self.assertAlmostEqual(drape[:, :, 2].min(), -3.0 - ifc_ground.DROP, places=3)     # the dig's floor
        ramp = np.asarray(made["ramp"]).reshape(-1, 3, 3)
        points = ramp.reshape(-1, 3)
        outer = points[np.abs(points[:, 2] - 1.0) < 1e-9]
        self.assertTrue(len(outer))
        # the highest edge (x = 40, 4 m) is 3 m over the zero: the slope runs 5 times that
        run = max(ifc_ground.RAMP_MIN, ifc_ground.RAMP_SLOPE * 3.0)
        self.assertAlmostEqual(outer[:, 0].max(), 40.0 + run, delta=0.01)
        self.assertTrue(same(Polygon(made["hole"][0]), box(-20 - run, -20 - run, 40 + run, 30 + run), 0.95))

    def test_a_terrain_with_too_many_faces_keeps_the_flat_lawn(self):
        old = ifc_ground.SURFACE_MAX
        ifc_ground.SURFACE_MAX = 10
        try:
            self.assertEqual(set(ifc_ground.top_surface(self.terrain())), {"faces"})
        finally:
            ifc_ground.SURFACE_MAX = old

    def test_pavings_over_the_ground_floor_do_not_raise_the_zero(self):
        building = [{"footprint": [[0, 0], [20, 0], [20, 10], [0, 10]]}]

        def slab(top):
            return [{"id": 1, "cls": "IfcSlab", "z0": top - 0.2, "z1": top,
                     "hull": [[21, 0], [26, 0], [26, 10], [21, 10]]}]
        # a terrace 1 m over the ground floor (two models of the bench): the ground floor stays the zero
        self.assertIsNone(ifc_ground.zero(0.0, building, slab(1.0), []))
        low = ifc_ground.zero(0.0, building, slab(-0.5), [])
        self.assertEqual(low["from"], "paving")
        self.assertAlmostEqual(low["height"], -0.5, places=3)

    def test_a_terrain_far_from_the_building_is_not_its_ground(self):
        building = [{"footprint": [[0, 0], [20, 0], [20, 10], [0, 10]]}]
        far = [t + np.array([0.0, 0.0, 40.0]) for t in self.terrain()]
        self.assertIsNone(ifc_ground.zero(0.5, building, [], far))


if __name__ == "__main__":
    unittest.main()
