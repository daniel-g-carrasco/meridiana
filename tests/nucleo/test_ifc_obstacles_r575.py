"""R575 D6: an obstacle read from an IFC has the plan of its element, not the convex hull of its points. The sample's
PARAPETTO_U (a wall in U, 20 cm thick, 5.2 m2 in plan) was an obstacle of 10 x 8 m, the whole roof; a railing around a
roof would have been the roof."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import shapely

import _setup  # noqa: F401

from meridiana.app.exchange import ifc_import, ifc_read, ifc_worker
from meridiana.core.model import model

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "ifc" / "r575-sintetico.ifc"


def box_faces(x0, y0, x1, y1, z0=0.0, z1=1.0) -> list:
    b = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return [np.array([(x, y, z0) for x, y in b]), np.array([(x, y, z1) for x, y in b])]


class Plan(unittest.TestCase):
    def test_a_wall_in_u_keeps_its_plan(self):
        faces = box_faces(0, 0, 10, 0.2) + box_faces(0, 0, 0.2, 8) + box_faces(9.8, 0, 10, 8)
        pieces = ifc_read._plan_pieces(faces, np.concatenate(faces))
        self.assertEqual(len(pieces), 1)
        self.assertAlmostEqual(pieces[0].area, 2.0 + 2 * 1.56, delta=0.05)

    def test_a_ring_around_a_roof_is_cut_into_pieces_without_holes(self):
        faces = (box_faces(0, 0, 10, 0.2) + box_faces(0, 7.8, 10, 8) + box_faces(0, 0, 0.2, 8)
                 + box_faces(9.8, 0, 10, 8))
        pieces = ifc_read._plan_pieces(faces, np.concatenate(faces))
        self.assertEqual(len(pieces), 2)
        self.assertTrue(all(not p.interiors for p in pieces))
        self.assertAlmostEqual(sum(p.area for p in pieces), 80 - 9.6 * 7.6, delta=0.05)

    def test_an_upright_pane_is_its_hull_thickened(self):
        pane = [np.array([(0, 0, 0), (1, 0, 0), (1, 0, 2), (0, 0, 2)], float)]
        pieces = ifc_read._plan_pieces(pane, pane[0])
        self.assertEqual(len(pieces), 1)
        self.assertGreater(pieces[0].area, 0.05)


class Sample(unittest.TestCase):
    def test_the_u_wall_of_the_sample_is_its_wall_not_the_roof(self):
        with tempfile.TemporaryDirectory() as tmp:
            found = ifc_worker.read(str(SAMPLE), "direct", lambda f, w: None, None, str(Path(tmp) / "cache"))
        walls = [o for o in found["obstacles"] if o["name"] == "PARAPETTO_U"]
        self.assertTrue(walls)
        area = sum(shapely.Polygon(o["ring"]).area for o in walls)
        self.assertTrue(5.0 <= area <= 6.0, area)                # before: 80 m2
        plan = ifc_import.plan(found, model.Project(), "origin", None, name="t", source_name="t.ifc")
        # it follows the roof's edge: the parapet of the building, not an exclusion over the roof
        self.assertAlmostEqual(plan.buildings[0].parapet, 1.0, places=2)
        self.assertFalse([e for e, _h in plan.exclusions if shapely.Polygon(e.ring).area > 10.0])


class Layout(unittest.TestCase):
    """A concave obstacle keeps the modules out of itself only, and casts its shadow: inside a U of 20 x 16 m on a
    roof of 60 x 40 m the modules stand where the hull would have kept them out."""

    def count(self, ring) -> int:
        from meridiana.app import jobs
        p = model.Project(name="u")
        p.buildings.append(model.Building(id="b1", name="B", footprint=[[0, 0], [60, 0], [60, 40], [0, 40]],
                                          height=6.0))
        if ring:
            p.exclusions.append(model.ExclusionItem(id="e1", ring=ring, kind="other", building="b1", height=1.0))
        p.subfields.append(model.SubField(id="s1", name="S", ring=[[1, 1], [59, 1], [59, 39], [1, 39]], building="b1",
                                          params=model.new_params("tilted_anchored"), filled=True))
        results, _keys, _laid = jobs.layout_of(p)
        self.assertNotIsInstance(results["s1"], Exception)
        return results["s1"].count

    def test_the_inside_of_a_u_takes_modules(self):
        u = [[20, 12], [40, 12], [40, 28], [39.5, 28], [39.5, 12.5], [20.5, 12.5], [20.5, 28], [20, 28]]
        hull = [[20, 12], [40, 12], [40, 28], [20, 28]]
        free, concave, convex = self.count(None), self.count(u), self.count(hull)
        self.assertLess(concave, free)
        self.assertGreater(concave, convex)


if __name__ == "__main__":
    unittest.main()
