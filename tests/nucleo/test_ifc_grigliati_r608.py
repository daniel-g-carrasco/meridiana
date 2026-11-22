"""R608 (m04, Daniel 14/11/2026: «la trattiamo come grigliati»): a grating is recognised by its name, description,
object type, type or predefined type (ifc_grating). Before, model m04's platforms («Floor:S_FL_SF_Gratings-40mm»,
IfcSlab FLOOR) were read as roofs and the columns on them were obstacles. Now a grating is drawn opaque (its shadow),
is never a roof nor a body, and what stands on it is not on a roof; it still casts its shadow, the full one of a slab
(Daniel: the shadow is wanted; the engine has no partial shadow yet), with the import's option off too. A concrete slab
beside it stays a roof. Sample `tests/data/ifc/grigliati.ifc`."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import _setup  # noqa: F401  (paths and the common setup)
from meridiana.app.exchange import ifc_grating, ifc_import, ifc_mesh, ifc_scan, ifc_shade, ifc_worker
from meridiana.core.energy import nearshade
from meridiana.core.model import model

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "ifc" / "grigliati.ifc"
SLAB, GRATING, BY_TYPE = 200, 300, 400              # the concrete slab, the grating by its name, the grating by its type
ON_SLAB, ON_GRATING, ON_TYPED = "Pilastro su solaio", "Pilastro su grigliato", "Pilastro su piattaforma"


class Rule(unittest.TestCase):
    def test_what_is_a_grating_and_what_is_not(self):
        yes = [("IfcSlab", "FLOOR", ["Floor:S_FL_SF_Gratings-40mm:758512"]),
               ("IFCSLAB", None, ["Solaio", "Grigliato metallico 30x30"]),
               ("IfcPlate", None, ["GRIGLIATO"]),
               ("IfcCovering", None, ["Pavimento", None, "Stahlgitterrost 30/30"]),
               ("IfcBuildingElementProxy", None, ["Caillebotis acier"]),
               ("IfcSlab", None, ["Rejilla electrosoldada"]),
               ("IfcSlab", None, ["Pedana tramex"]),
               ("IfcSlab", "GRATING", ["Platform"])]
        no = [("IfcSlab", "FLOOR", ["Floor:S_FL_SF_ConcreteLayer-120mm"]),
              ("IfcSlab", "ROOF", ["Integrating slab"]),                   # «grating» inside another word
              ("IfcBeam", None, ["Grating support beam"]),                 # a beam is not a floor of bars
              ("IfcColumn", None, ["Grigliato"]),
              ("IfcSlab", "USERDEFINED", [None, ""])]
        for case in yes:
            with self.subTest(case):
                self.assertTrue(ifc_grating.is_grating(*case))
        for case in no:
            with self.subTest(case):
                self.assertFalse(ifc_grating.is_grating(*case))


class Reading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.found = ifc_worker.read(str(SAMPLE), "direct", lambda f, w: None, None, str(Path(cls.tmp.name) / "cache"))
        cls.mesh = ifc_mesh.load(cls.found["context"]["mesh"])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_a_grating_is_never_a_roof_and_a_slab_is(self):
        owners = {o for b in self.found["buildings"] for p in b["pitches"] for o in p["owners"]}
        self.assertIn(SLAB, owners)
        self.assertNotIn(GRATING, owners)
        self.assertNotIn(BY_TYPE, owners)

    def test_what_stands_on_a_grating_is_no_obstacle_and_on_a_slab_it_is(self):
        names = [o["name"] for o in self.found["obstacles"]]
        self.assertEqual(names, [ON_SLAB])

    def test_the_scan_knows_the_gratings(self):
        self.assertEqual(sorted(s["id"] for s in self.found["solids"] if s.get("grating")), [GRATING, BY_TYPE])

    def imported(self, shade: str = "off"):
        project = model.Project()
        ifc_import.apply(project, ifc_import.plan(self.found, project, "origin", None, name="t", source_name="t.ifc",
                                                  shade=shade))
        return project

    def test_a_grating_has_its_shading_solid_as_the_slab(self):
        ids = ifc_shade.of_mesh(self.mesh)["ids"].tolist()
        self.assertTrue({SLAB, GRATING, BY_TYPE} <= set(ids))

    def test_the_option_off_the_gratings_alone_cast_their_shadow_and_a_full_one(self):
        project = self.imported()
        self.assertEqual(project.resources["ifc_reference"]["context"]["gratings"], [GRATING, BY_TYPE])
        solids, skip = ifc_shade.shading(project, SimpleNamespace(ring=[]))
        self.assertEqual(len(solids), 2)
        self.assertEqual(skip, set())                   # the bodies of the import cast their own shadows, as before
        for s in solids:
            self.assertAlmostEqual(float(np.ptp(s.corners[:, 2])), 0.04, delta=0.01)       # the plate, 4 cm
            # the sun high: the shadow on the ground is the whole plate, 10 x 10 m, as a slab's (no light through)
            shadow = nearshade.plan_shadow([s], 180.0, 89.0, 0.0)
            self.assertAlmostEqual(shadow.area, 100.0, delta=1.0)
        self.assertIsNotNone(ifc_shade.key(project))    # the year follows their shadows

    def test_the_option_on_the_gratings_shade_with_the_other_elements(self):
        project = self.imported("all")
        solids, skip = ifc_shade.shading(project, SimpleNamespace(ring=[]))
        self.assertEqual(len(solids), 6)                # the three slabs and the three columns
        self.assertTrue(skip)

    def test_a_grating_is_drawn_opaque_in_a_metal_grey_so_that_it_casts_its_shadow_in_the_3d(self):
        colour = {}
        for k, row in enumerate(self.mesh["elements"]):
            colour.setdefault(int(row[0]), []).append(self.mesh["colours"][int(self.mesh["piece_of"][k])].tolist())
        slab = colour[SLAB][0]
        for eid in (GRATING, BY_TYPE):
            (rgba,) = colour[eid]
            self.assertEqual(rgba[3], 1.0)                                   # opaque: Qt Quick 3D draws its shadow
            for got, want in zip(rgba[:3], ifc_grating.COLOUR, strict=True):
                self.assertAlmostEqual(got, want, delta=ifc_mesh.QUANTUM)
            self.assertNotEqual(rgba[:3], slab[:3])                          # a little apart from the slab

    def test_a_grating_keeps_its_file_colour_made_opaque(self):
        self.assertEqual(ifc_grating.shown((0.8, 0.8, 0.8, 0.3)), (0.8, 0.8, 0.8, 1.0))
        self.assertEqual(ifc_grating.shown(None), ifc_grating.COLOUR + (1.0,))

    def test_the_solids_make_no_body_of_a_grating(self):
        for way in ("elements", "groups"):
            with self.subTest(way):
                raws, _zoned = ifc_import.solid_raws(self.found, way)
                members = {o for b in raws for p in b["pitches"] for o in p["owners"]}
                self.assertIn(SLAB, members)
                self.assertFalse(members & {GRATING, BY_TYPE})

    def test_the_import_plans_no_roof_on_a_grating(self):
        plan = ifc_import.plan(self.found, model.Project(), "origin", None, name="t", source_name="t.ifc")
        self.assertTrue(plan.buildings)
        self.assertEqual(len([e for e, _h in plan.exclusions]), 1)            # the column on the slab only


class Scan(unittest.TestCase):
    def test_the_fast_reading_marks_them(self):
        scanned = ifc_scan.scan(SAMPLE)
        self.assertEqual(sorted(e.id for e in scanned.elements if e.grating), [GRATING, BY_TYPE])


if __name__ == "__main__":
    unittest.main()
