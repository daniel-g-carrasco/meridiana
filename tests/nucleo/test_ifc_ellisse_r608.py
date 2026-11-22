"""R608: a profile whose outline has an arc of an ellipse (a rounded corner as Revit writes it) is read by the fast
reading: in model A a pavement of 745 m2 was missing from the 3D because one corner of its outline was an
IfcTrimmedCurve on an IfcEllipse. Sample `tests/data/ifc/profilo-ellisse.ifc`."""
import math
import unittest
from pathlib import Path

import numpy as np

import _setup  # noqa: F401  (paths and the common setup)
from meridiana.app.exchange import ifc_mesh, ifc_scan

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "ifc" / "profilo-ellisse.ifc"


class EllipseArc(unittest.TestCase):
    def test_the_pavement_with_a_rounded_corner_is_drawn_with_its_corner(self):
        mesh = ifc_mesh.build(ifc_scan.scan(SAMPLE))
        rows = [k for k, row in enumerate(mesh["elements"]) if int(row[0]) == 100]
        self.assertEqual(len(rows), 1)
        k = rows[0]
        v, f, _c = ifc_mesh.piece(mesh, int(mesh["piece_of"][k]))
        first, n = int(mesh["elements"][k][1]), int(mesh["elements"][k][2])
        tri = v[f[first:first + n]].astype(float) + mesh["centre"]
        normal = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        top = 0.5 * np.abs(normal[(tri[:, :, 2] > 0.19).all(axis=1), 2]).sum()
        self.assertAlmostEqual(top, 15.0 + math.pi / 4, delta=0.01)     # 4 x 4 less the corner, plus its quarter
        pts = tri.reshape(-1, 3)
        corner = pts[(pts[:, 0] > 3.001) & (pts[:, 1] > 3.001)]
        self.assertGreater(len(corner), 3)                               # the arc, in pieces
        np.testing.assert_allclose(np.hypot(corner[:, 0] - 3, corner[:, 1] - 3), 1.0, atol=0.001)


if __name__ == "__main__":
    unittest.main()
