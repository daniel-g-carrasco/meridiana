"""R575 D9: the fast reading cuts the openings and the clippings of an element. It drew a wall without its window, a
wall under a sloping roof as its whole box and a beam without the notch at its end; a model's walls beside inclined
windows looked like full rectangles. The values here are exact (and IfcOpenShell's) for a sample written by hand."""

import unittest
from pathlib import Path

import numpy as np

import _setup  # noqa: F401

from meridiana.app.exchange import ifc_mesh, ifc_scan
from meridiana.core.geometry import solidcut

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "ifc" / "r575-d9-tagli.ifc"
# name -> (area m2, volume m3, top of the box m)
EXPECTED = {"Muro con finestra": (26.0, 3.0, 3.0), "Muro sotto la falda": (15.33693, 1.8, 2.0),
            "Trave con la testa intagliata": (5.02, 0.28, 0.3)}


def _area_volume(tris: np.ndarray) -> tuple[float, float]:
    cross = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    area = 0.5 * float(np.linalg.norm(cross, axis=1).sum())
    volume = float(np.einsum("ij,ij->i", tris[:, 0], np.cross(tris[:, 1], tris[:, 2])).sum()) / 6
    return area, volume


def _open_edges(tris: np.ndarray) -> int:
    """Edges used by one triangle only, the corners welded at 0.1 mm: 0 for a closed surface (the faces of the cut
    meet the faces they close corner to corner)."""
    _u, inv = np.unique(np.round(tris.reshape(-1, 3) / 1e-4).astype(np.int64), axis=0, return_inverse=True)
    f = inv.reshape(-1, 3)
    f = f[(f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])]
    e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    return int((np.unique(e, axis=0, return_counts=True)[1] == 1).sum())


def _box(lo, hi) -> np.ndarray:
    p = np.array([[lo[0], lo[1], lo[2]], [hi[0], lo[1], lo[2]], [hi[0], hi[1], lo[2]], [lo[0], hi[1], lo[2]],
                  [lo[0], lo[1], hi[2]], [hi[0], lo[1], hi[2]], [hi[0], hi[1], hi[2]], [lo[0], hi[1], hi[2]]], float)
    f = [[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7],
         [2, 7, 6], [3, 0, 4], [3, 4, 7]]
    return p[np.array(f)]


class Cuts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scan = ifc_scan.scan(SAMPLE, workers=1)
        cls.by_name = {e.name: e for e in cls.scan.elements}

    def test_an_opening_a_sloping_plane_and_a_bounded_half_space(self):
        self.assertEqual(set(self.by_name), set(EXPECTED))
        for name, (area, volume, top) in EXPECTED.items():
            e = self.by_name[name]
            a, v = _area_volume(self.scan.triangles(e.id))
            self.assertAlmostEqual(a, area, delta=0.01 * area, msg=name)
            self.assertAlmostEqual(v, volume, delta=0.01 * volume, msg=name)
            # the box of the fast reading is the cut solid's (the wall under the slope ends at 2 m, not 3 m)
            self.assertAlmostEqual(e.hi[2], top, delta=0.001, msg=name)
            self.assertEqual(_open_edges(self.scan.triangles(e.id)), 0, msg=name)
        self.assertEqual(self.scan.left_out, {})

    def test_the_3d_geometry_is_cut_the_same_way(self):
        mesh = ifc_mesh.build(self.scan)
        names = {e.id: e.name for e in self.scan.elements}
        verts, faces = mesh["vertices"].astype(float), mesh["faces"]
        seen = set()
        for k, (eid, first, n) in enumerate(mesh["elements"]):
            v0, _nv, f0, _nf = mesh["pieces"][mesh["piece_of"][k]]
            tris = verts[v0 + faces[f0 + first:f0 + first + n].astype(np.int64)]
            area, volume, _top = EXPECTED[names[int(eid)]]
            a, v = _area_volume(tris)            # around the model's middle: a closed solid's volume is the same
            self.assertAlmostEqual(a, area, delta=0.01 * area, msg=names[int(eid)])
            self.assertAlmostEqual(v, volume, delta=0.01 * volume, msg=names[int(eid)])
            seen.add(names[int(eid)])
        self.assertEqual(seen, set(EXPECTED))


class Subtract(unittest.TestCase):
    def test_an_opening_already_carved_is_not_carved_again(self):
        """A Reference View model writes its walls with the openings already in their faces."""
        wall = _box((0, 0, 0), (4, 0.3, 3))
        window = solidcut.convex_hull_piece(_box((1, 0, 0.5), (2, 0.3, 2.5)), 1e-6)
        carved, used = solidcut.subtract(wall, [window], 1e-6)
        self.assertEqual(used, 1)
        self.assertAlmostEqual(_area_volume(carved)[1], 3.0, places=6)
        again, used = solidcut.subtract(carved, [window], 1e-6)
        self.assertEqual(used, 0)
        self.assertEqual(len(again), len(carved))

    def test_a_concave_opening_in_convex_parts(self):
        ring = np.array([[1, 0.5], [3, 0.5], [3, 1.5], [2, 1.5], [2, 2.5], [1, 2.5]], float)
        parts = solidcut.convex_parts([ring])
        self.assertEqual(len(parts), 2)
        frame = np.array([[1, 0, 0, 0], [0, 0, -1, -0.5], [0, 1, 0, 0], [0, 0, 0, 1]], float)
        pieces = [solidcut.prism(r, frame, np.array([0, 1.3, 0])) for r in parts]
        cut, used = solidcut.subtract(_box((0, 0, 0), (4, 0.3, 3)), pieces, 1e-6)
        self.assertEqual(used, 2)
        area, volume = _area_volume(cut)
        self.assertAlmostEqual(volume, 3.6 - 0.3 * 3, places=4)
        self.assertAlmostEqual(area, 28.2 - 2 * 3 + 0.3 * 8, places=4)


if __name__ == "__main__":
    unittest.main()
