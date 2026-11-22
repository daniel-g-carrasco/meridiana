"""R608: an element drawn as several items of different colours keeps each item's colour in the 3D (ifc_mesh). In
model A a wall is three face sets, a dark core between two light skins: the whole wall came out dark, the colour of
its first item, and showed as a grey slab between light walls. Sample `tests/data/ifc/muro-strati.ifc`."""
import unittest
from pathlib import Path

import numpy as np

import _setup  # noqa: F401  (paths and the common setup)
from meridiana.app.exchange import ifc_mesh, ifc_scan, ifc_shade

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "ifc" / "muro-strati.ifc"
DARK, LIGHT = 0.47, 0.93


def rows_of(mesh, eid):
    """[(colour, points of the row)...] of an element."""
    out = []
    for k, row in enumerate(mesh["elements"]):
        if int(row[0]) != eid:
            continue
        v, f, colour = ifc_mesh.piece(mesh, int(mesh["piece_of"][k]))
        first, n = int(row[1]), int(row[2])
        tri = v[f[first:first + n]].astype(float) + mesh["centre"]
        out.append((colour, tri))
    return sorted(out, key=lambda r: r[0][0])


class Layers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mesh = ifc_mesh.build(ifc_scan.scan(SAMPLE))

    def test_a_wall_of_a_dark_core_and_light_skins_is_drawn_in_both_colours(self):
        rows = rows_of(self.mesh, 100)
        self.assertEqual(len(rows), 2)
        (dark, core), (light, skins) = rows
        self.assertAlmostEqual(dark[0], DARK, delta=ifc_mesh.QUANTUM)
        self.assertAlmostEqual(light[0], LIGHT, delta=ifc_mesh.QUANTUM)
        # the core inside, the skins outside: the faces seen from outside the wall are light
        np.testing.assert_allclose(core.reshape(-1, 3)[:, 1].min(), 0.02, atol=1e-5)
        np.testing.assert_allclose(core.reshape(-1, 3)[:, 1].max(), 0.28, atol=1e-5)
        np.testing.assert_allclose(skins.reshape(-1, 3)[:, 1].min(), 0.0, atol=1e-5)
        np.testing.assert_allclose(skins.reshape(-1, 3)[:, 1].max(), 0.30, atol=1e-5)
        self.assertEqual(len(skins), 24)                                 # two boxes of 12 triangles

    def test_the_layers_keep_their_colours_when_an_opening_is_cut(self):
        rows = rows_of(self.mesh, 200)
        self.assertEqual([round(c[0], 1) for c, _t in rows], [0.5, 0.9])
        for _c, tri in rows:
            middle = tri.mean(axis=1)
            # nothing left in the opening (x 2..3, z 0.5..2.5), on any layer
            inside = (middle[:, 0] > 2.05) & (middle[:, 0] < 2.95) & (middle[:, 2] > 0.55) & (middle[:, 2] < 2.45)
            self.assertFalse(inside.any())

    def test_a_mapped_window_has_its_frame_and_its_glass(self):
        rows = rows_of(self.mesh, 300)
        self.assertEqual(len(rows), 2)
        (glass, _g), (frame, _f) = rows
        self.assertAlmostEqual(glass[3], 0.4, delta=ifc_mesh.QUANTUM)
        self.assertAlmostEqual(frame[0], LIGHT, delta=ifc_mesh.QUANTUM)
        self.assertEqual(frame[3], 1.0)

    def test_the_shadow_of_an_element_of_two_colours_is_still_one_solid(self):
        hulls = ifc_shade.of_mesh(self.mesh)
        self.assertEqual(sorted(hulls["ids"].tolist()), [100, 200, 300])
        k = hulls["ids"].tolist().index(100)
        np.testing.assert_allclose(hulls["lo"][k], [0, 0, 0], atol=1e-4)
        np.testing.assert_allclose(hulls["hi"][k], [5, 0.3, 3], atol=1e-4)


if __name__ == "__main__":
    unittest.main()
