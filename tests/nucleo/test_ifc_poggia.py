"""What stands on a roof comes in as before R34: base 0, the prism from the roof to its top. Every obstacle of the
samples made for the other IFC tests stands on its roof (a chimney, walls at the edge, units on a roof, a window in a
slope, a pane leaning on a roof); the base of an obstacle (ifc_read.BASE_MIN) is only for what hangs above it
(test_ifc_sospesi)."""

import unittest
from pathlib import Path

import _setup  # noqa: F401

from meridiana.app.exchange import ifc_import, ifc_read
from meridiana.core.model import model

DATA = Path(__file__).resolve().parents[1] / "data" / "ifc"
SAMPLES = ("finestra-facciata.ifc", "mappato-ripetuto.ifc", "parapetto-parziale.ifc", "r575-falda-montante.ifc",
           "r575-sintetico.ifc", "tirante-inclinato.ifc", "vetrata-inclinata.ifc")


class Standing(unittest.TestCase):
    def test_every_obstacle_standing_on_a_roof_has_no_base_and_its_prism_from_the_roof(self):
        seen = 0
        for name in SAMPLES:
            with self.subTest(sample=name):
                found = ifc_read.read(str(DATA / name), mode="direct")
                self.assertTrue(found["obstacles"])
                self.assertEqual([o["base"] for o in found["obstacles"]], [0.0] * len(found["obstacles"]))
                self.assertFalse(found["counts"].get("raised"))
                project = model.Project()
                plan = ifc_import.plan(found, project, "origin", None, name="t", source_name=name)
                ifc_import.apply(project, plan)
                self.assertFalse(any("raised" in s for s in plan.approximated), plan.approximated)
                for e in project.exclusions:
                    self.assertEqual(e.base, 0.0)
                    self.assertNotIn("base", e.as_dict())          # the file and the keys as before format 32
                    prism = project.obstacle_prism(e)
                    if prism is None:
                        continue
                    seen += 1
                    # from the lowest point of the roof under its outline, as every obstacle before the base
                    b = project.building(e.building)
                    roof = model.roof_z(b, prism["ring"]) if b is not None else [0.0]
                    self.assertAlmostEqual(prism["z0"], min(roof), places=6)
                    self.assertAlmostEqual(prism["z1"], max(roof) + e.obstacle_height(), places=6)
        self.assertGreater(seen, 10)


if __name__ == "__main__":
    unittest.main()
