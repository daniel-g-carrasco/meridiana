"""R575 D4: the model's terrain is recognised. Before, the sample's TERRENO (an IfcGeographicElement 60 x 60 m) came out
of the reader as an obstacle «tree» and, with the solids by element, as a body; it filled the preview and the 3D. Now it
is never an obstacle, a body or a shadow, and the 3D leaves it out unless the import asks for it."""

import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401

from meridiana.app.exchange import ifc_import, ifc_terrain, ifc_worker
from meridiana.core.model import model

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "ifc" / "r575-sintetico.ifc"


class Rule(unittest.TestCase):
    def test_what_is_terrain_and_what_is_not(self):
        yes = [("IfcGeographicElement", "TERRAIN", ["Solid"], [], []),
               ("IfcGeographicElement", None, ["Thing"], [], []),
               ("IfcBuildingElementProxy", None, ["Solido topografico 3"], [], []),
               ("IfcBuildingElementProxy", None, ["Proxy"], ["C-TOPO-____-OTLN"], []),
               ("IfcSlab", None, ["Slab"], [], ["Terreno"]),
               ("IfcBuildingElementProxy", None, ["Gelände Süd"], [], [])]
        no = [("IfcGeographicElement", "USERDEFINED", ["Tree"], [], []),
              ("IfcGeographicElement", ".NOTDEFINED.", ["Albero 3"], [], []),
              ("IfcWall", None, ["Muro piano terreno"], [], []),
              ("IfcRailing", None, ["Geländer"], [], []),
              ("IfcCableSegment", None, ["Cable"], ["E-POWR"], ["Earthing copper"]),
              ("IfcBuildingElementProxy", None, ["Massa 4"], ["A-MASS"], [])]
        for case in yes:
            with self.subTest(case):
                self.assertTrue(ifc_terrain.is_terrain(*case))
        for case in no:
            with self.subTest(case):
                self.assertFalse(ifc_terrain.is_terrain(*case))


class Import(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.found = ifc_worker.read(str(SAMPLE), "direct", lambda f, w: None, None, str(Path(cls.tmp.name) / "cache"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def ground_id(self) -> int:
        return next(s["id"] for s in self.found["solids"] if s["name"] == "TERRENO")

    def test_the_reader_and_the_scan_know_it(self):
        self.assertEqual([s["name"] for s in self.found["solids"] if s.get("terrain")], ["TERRENO"])
        self.assertFalse([o for o in self.found["obstacles"] if o["kind"] == "tree"])
        self.assertEqual(self.found["counts"].get("terrain"), 1)

    def test_never_a_body_nor_an_obstacle_and_left_out_of_the_3d(self):
        plan = ifc_import.plan(self.found, model.Project(), "origin", None, name="t", source_name="t.ifc",
                               solids="elements")
        areas = [abs(ifc_import._area2(b.footprint)) / 2 for b in plan.buildings]
        self.assertTrue(plan.buildings)
        self.assertLess(max(areas), 200.0)                      # the roof is 10 x 8 m, the terrain 60 x 60
        self.assertFalse([e for e, _h in plan.exclusions if e.kind == "tree"])
        ctx = plan.reference["context"]
        self.assertIn(self.ground_id(), ctx["skip"])
        self.assertEqual(ctx["terrain"], [self.ground_id()])
        self.assertTrue(any("terrain" in t for t in plan.taken))

    def test_drawn_when_asked_but_still_neither_a_body_nor_a_shadow(self):
        plan = ifc_import.plan(self.found, model.Project(), "origin", None, name="t", source_name="t.ifc",
                               solids="elements", terrain=True)
        ctx = plan.reference["context"]
        self.assertNotIn(self.ground_id(), ctx.get("skip") or [])
        self.assertEqual(ctx["terrain"], [self.ground_id()])
        self.assertLess(max(abs(ifc_import._area2(b.footprint)) / 2 for b in plan.buildings), 200.0)


if __name__ == "__main__":
    unittest.main()
