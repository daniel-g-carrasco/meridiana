"""R608: a body of one mono pitch among the other roofs of an IFC building falls the way the file's plane falls. Its
outline is made by the import (the union of its pitches, turned one way) and starts elsewhere than the pitch's ring:
the eave was looked up by the index of the pitch's side in the body's outline, and a roof falling north came in falling
east (model m14: a 2.6 degree canopy, 0.16 m the wrong way). Sample `tests/data/ifc/falda-mono-separata.ifc`."""
import unittest
from pathlib import Path

import _setup  # noqa: F401  (paths and the common setup)
from meridiana.app.exchange import ifc_import, ifc_read, ifc_worker
from meridiana.core.model import model

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "ifc" / "falda-mono-separata.ifc"


class MonoAmongOthers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ifc_read.available():
            raise unittest.SkipTest("ifcopenshell is not installed")
        found = ifc_worker.read(str(SAMPLE), "direct", lambda f, w: None, None, None)
        cls.project = model.Project()
        plan = ifc_import.plan(found, cls.project, "origin", None, name="t", source_name="t.ifc")
        ifc_import.apply(cls.project, plan)

    def test_the_canopy_falls_north_as_in_the_file(self):
        mono = [b for b in self.project.buildings if b.roof.type == "mono"]
        self.assertEqual(len(mono), 1)
        (pitch,) = mono[0].pitches()
        self.assertAlmostEqual(pitch.tilt, 2.86, places=1)
        self.assertAlmostEqual(abs(pitch.azimuth), 180.0, places=0)      # facing north (CEI 82-25: 0 is south)
        corners = pitch.corners_3d()
        south = max(z for _x, y, z in corners if y < min(c[1] for c in corners) + 0.1)
        north = max(z for _x, y, z in corners if y > max(c[1] for c in corners) - 0.1)
        self.assertAlmostEqual(south, 3.6, places=2)
        self.assertAlmostEqual(north, 3.4, places=2)


if __name__ == "__main__":
    unittest.main()
