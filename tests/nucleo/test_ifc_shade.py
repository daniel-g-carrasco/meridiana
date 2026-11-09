"""r22-ifc: the true shapes of an imported IFC cast the shadows of the calculation (ifc_shade), on the safe side, chosen
near the modules, kept on disk; off, nothing changes. The sample of test_ifc_scan («A» a 1 x 1 x 2 m box at x 5..6,
«B» the same map elsewhere, a slab)."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

import _setup  # noqa: F401  (paths and the common setup)
from meridiana import ifc_import, ifc_shade, ifc_worker, model
from meridiana.energy import nearshade, system
from nucleo.test_ifc_scan import SAMPLE


def inside(points, corners, tol=1e-9) -> bool:
    """Whether every point lies in the convex hull of `corners`."""
    from scipy.spatial import ConvexHull
    h = ConvexHull(corners)
    return bool(np.all(points @ h.equations[:, :3].T + h.equations[:, 3] <= tol))


class Hulls(unittest.TestCase):
    def test_a_hull_holds_the_element_and_a_large_one_becomes_a_box_of_26_sides(self):
        rng = np.random.default_rng(4)
        ball = rng.normal(size=(4000, 3))
        ball /= np.linalg.norm(ball, axis=1)[:, None]                       # a sphere: thousands of hull corners
        corners = ifc_shade._hull_corners(ball)
        self.assertLessEqual(len(corners), ifc_shade.MAX_CORNERS)
        self.assertTrue(inside(ball, corners))                               # never less shadow than the true one
        cube = np.array([[x, y, z] for x in (0, 1) for y in (0, 2) for z in (0, 3)], float)
        few = ifc_shade._hull_corners(np.vstack([cube, [[0.5, 1, 1.5]]]))   # a point inside is not a corner
        self.assertEqual(len(few), 8)
        np.testing.assert_allclose(np.sort(few, axis=0), np.sort(cube, axis=0), atol=2 * ifc_shade.GROW)
        self.assertTrue(inside(cube, few))
        flat = ifc_shade._hull_corners(np.array([[0, 0, 1], [4, 0, 1], [4, 3, 1], [0, 3, 1.0]]))
        self.assertEqual(len(flat), 8)                                       # a plate: its box


class Shadows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "sample.ifc"
        cls.path.write_text(SAMPLE, encoding="ascii", newline="\n")
        cls.found = ifc_worker.read(str(cls.path), "direct", lambda f, w: None, None, str(Path(cls.tmp.name) / "c"))

    @classmethod
    def tearDownClass(cls):
        ifc_shade._LOADED.clear()
        cls.tmp.cleanup()

    def project(self, shade="off"):
        """The sample imported by element, and a low roof of modules east of «A» (1 m high, 3 m away)."""
        project = model.Project()
        plan = ifc_import.plan(self.found, project, "origin", None, name="t", source_name="t.ifc", solids="elements",
                               shade=shade)
        ids = ifc_import.apply(project, plan)
        a = next(b for b in project.buildings if b.id in ids and b.name == "A")
        x1 = max(x for x, _y in a.footprint)
        y0 = min(y for _x, y in a.footprint)
        roof = model.Building(id="roof", name="Roof", footprint=[[x1 + 3, y0], [x1 + 9, y0], [x1 + 9, y0 + 4],
                                                                 [x1 + 3, y0 + 4]], height=1.0)
        project.buildings.append(roof)
        sf = model.SubField(id="s1", name="s1", ring=[list(q) for q in roof.footprint], building="roof", pitch=0)
        project.subfields.append(sf)
        return project, sf, ids

    def test_off_nothing_changes(self):
        project, sf, ids = self.project("off")
        self.assertNotIn("shade", project.resources["ifc_reference"])
        self.assertEqual(ifc_shade.shading(project, sf), ([], set()))
        names = sorted(s.name for s in system.obstacles_of(project, sf))
        self.assertEqual(names, sorted(b.name for b in project.buildings if b.id in ids))   # the bodies, as before
        self.assertIsNone(ifc_shade.key(project))

    def test_on_the_elements_cast_them_instead_of_the_bodies(self):
        project, sf, ids = self.project("20")
        self.assertEqual(project.resources["ifc_reference"]["shade"], {"on": True, "reach": 20.0})
        solids = system.obstacles_of(project, sf)
        self.assertEqual({s.name for s in solids}, {"t"})                  # the model's shapes, not the bodies
        self.assertEqual(len(solids), 2)                                   # «A» and «B»; the slab lies under the roof
        a = next(b for b in project.buildings if b.id in ids and b.name == "A")
        box = np.asarray(a.footprint)
        tower = min(solids, key=lambda s: np.abs(s.corners[:, :2].mean(0) - box.mean(0)).sum())
        np.testing.assert_allclose(tower.corners[:, 2].max(), 2.0, atol=0.01)
        np.testing.assert_allclose(tower.corners[:, :2].min(0), box.min(0), atol=0.15)
        # the sun low in the west: «A» throws its shadow east, on the roof
        shadow = nearshade.plan_shadow([tower], 270.0, 15.0, 1.0)
        roof = np.asarray(sf.ring)
        from shapely.geometry import Polygon
        self.assertGreater(shadow.intersection(Polygon(roof)).area, 0.5)
        self.assertEqual(ifc_shade.key(project)["reach"], 20.0)           # the year's key knows the option

    def test_near_and_above_only(self):
        project, sf, _ids = self.project("20")
        everything = ifc_shade.placed(project)
        self.assertEqual(len(everything[0]["ids"]), 3)
        self.assertEqual(len(ifc_shade.chosen(project, sf)), 2)            # the slab is under the modules
        far = model.SubField(id="far", name="far", ring=[[500, 500], [510, 500], [510, 510], [500, 510]],
                             building="roof", pitch=0)
        self.assertEqual(len(ifc_shade.chosen(project, far)), 0)           # beyond the reach
        project.resources["ifc_reference"]["shade"]["reach"] = None
        self.assertEqual(len(ifc_shade.chosen(project, far)), 2)           # the whole model
        receiver = model.SubField(id="r", name="", ring=[])
        self.assertEqual(len(ifc_shade.chosen(project, receiver)), 3)      # the plan's shadows: all of it

    def test_too_many_go_together_and_still_hold_each_element(self):
        project, sf, _ids = self.project("all")
        one_by_one = ifc_shade.solids_for(project, sf)
        self.assertEqual(len(one_by_one), 2)
        limit = ifc_shade.MAX_SOLIDS
        ifc_shade.MAX_SOLIDS = 1
        try:
            together = ifc_shade.solids_for(project, sf)
        finally:
            ifc_shade.MAX_SOLIDS = limit
        self.assertEqual(len(together), 1)
        self.assertTrue(inside(np.concatenate([s.corners for s in one_by_one]), together[0].corners, tol=1e-6))

    def test_kept_on_disk_and_lost_with_the_frame(self):
        project, sf, _ids = self.project("50")
        mesh = project.resources["ifc_reference"]["context"]["mesh"]
        ifc_shade._LOADED.clear()
        first = ifc_shade.load(mesh)
        target = ifc_shade.file_of(mesh)
        self.assertTrue(target.is_file())
        stamp = target.stat().st_mtime_ns
        ifc_shade._LOADED.clear()
        again = ifc_shade.load(mesh)
        self.assertEqual(target.stat().st_mtime_ns, stamp)                 # read back, not made again
        np.testing.assert_array_equal(first["corners"], again["corners"])
        # the anchor reshaped: the frame is lost, the bodies cast the shadows again
        anchor = project.building(project.resources["ifc_reference"]["anchor"]["building"])
        anchor.footprint = [[0, 0], [9, 0], [9, 9]]
        self.assertEqual(ifc_shade.shading(project, sf), ([], set()))
        self.assertNotIn("t", {s.name for s in system.obstacles_of(project, sf)})

    def test_the_storeys_left_out_cast_nothing(self):
        project = model.Project()
        plan = ifc_import.plan(self.found, project, "origin", None, name="t", source_name="t.ifc", solids="elements",
                               shade="all", storeys=[])
        self.assertEqual(plan.buildings, [])
        self.assertEqual(len(plan.reference["context"]["skip"]), 3)


if __name__ == "__main__":
    unittest.main()
