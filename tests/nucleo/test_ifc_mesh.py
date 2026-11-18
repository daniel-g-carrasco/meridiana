"""The true geometry of an IFC for the 3D (ifc_mesh, r21-ifc-vista) and its place next to the import's bodies
(quick/backend/scene_context): the sample of test_ifc_scan with a colour, read, made, saved, placed."""
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

import _setup  # noqa: F401  (paths and the common setup)
from meridiana import ifc_import, ifc_mesh, ifc_scan, ifc_worker, model
from nucleo.test_ifc_scan import SAMPLE

STYLE = """#100=IFCCOLOURRGB($,1.,0.,0.);
#101=IFCSURFACESTYLERENDERING(#100,0.5,$,$,$,$,$,$,.NOTDEFINED.);
#102=IFCSURFACESTYLE('red',.BOTH.,(#101));
#103=IFCPRESENTATIONSTYLEASSIGNMENT((#102));
#104=IFCSTYLEDITEM(#51,(#103),$);
ENDSEC;
END-ISO-10303-21;
"""


class Mesh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "sample.ifc"
        text = SAMPLE.replace("ENDSEC;\nEND-ISO-10303-21;\n", STYLE)
        cls.path.write_text(text, encoding="ascii", newline="\n")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_triangles_the_colours_and_the_file(self):
        s = ifc_scan.scan(self.path)
        m = ifc_mesh.build(s)
        # A and B: the map's box, 8 points shared by 12 triangles each; the slab: an extruded rectangle, 12 triangles
        self.assertEqual(len(m["faces"]), 36)
        self.assertEqual(len(m["elements"]), 3)
        colours = {tuple(np.round(c, 3)) for c in m["colours"]}
        self.assertIn((1.0, 0.0, 0.0, 0.5), colours)                    # the style, its transparency an opacity
        grey = [c for c in m["colours"] if c[3] == 1.0]                  # the slab: its class's colour, quantized
        np.testing.assert_allclose(grey[0], ifc_mesh.CLASS_COLOURS["IfcSlab"] + (1.0,), atol=ifc_mesh.QUANTUM / 2)
        by_id = {int(e[0]): k for k, e in enumerate(m["elements"])}
        k = by_id[65]                                                     # «A»: the map moved by 5 m in x
        piece = int(m["piece_of"][k])
        v, f, colour = ifc_mesh.piece(m, piece)
        self.assertEqual(colour[3], 0.5)
        first, n = int(m["elements"][k][1]), int(m["elements"][k][2])
        pts = v[f[first:first + n].ravel()].astype(float) + m["centre"]
        np.testing.assert_allclose(pts.min(0), [5, 0, 0], atol=1e-5)
        np.testing.assert_allclose(pts.max(0), [6, 1, 2], atol=1e-5)
        self.assertEqual(len(np.unique(f[first:first + n])), 8)           # shared, not doubled
        out = Path(self.tmp.name) / "m.npz"
        ifc_mesh.save(out, m)
        back = ifc_mesh.load(out)
        self.assertEqual(set(back), set(m))
        np.testing.assert_array_equal(back["faces"], m["faces"])

    def test_the_worker_writes_it_once_and_the_3d_puts_it_on_the_bodies(self):
        folder = Path(self.tmp.name) / "context"
        found = ifc_worker.read(str(self.path), "direct", lambda f, w: None, None, str(folder))
        ctx = found["context"]
        self.assertTrue(Path(ctx["mesh"]).is_file())
        self.assertEqual(ctx["triangles"], 36)
        again = ifc_worker.read(str(self.path), "direct", lambda f, w: None, None, str(folder))
        self.assertEqual(again["context"]["mesh"], ctx["mesh"])
        self.assertEqual(again["context"]["seconds"], 0.0)                # read back, not made again
        app = _setup.qt_or_skip()
        self.assertIsNotNone(app)
        from meridiana.quick.backend import scene_context
        project = model.Project()
        plan = ifc_import.plan(found, project, "origin", None, name="t", source_name="t.ifc", solids="elements")
        ids = ifc_import.apply(project, plan)
        self.assertEqual(project.resources["ifc_reference"]["context"]["mesh"], ctx["mesh"])
        ctxs = scene_context.IfcContext(None)
        # the bodies turned and moved together, as the mouse does: the true geometry follows them
        from meridiana import move
        angle = 30.0
        for b in project.buildings:
            c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
            b.footprint = [[round(c * x - s * y + 7.0, 6), round(s * x + c * y - 3.0, 6)] for x, y in b.footprint]
        self.assertIsNotNone(move)
        entries = ctxs.entries(project)
        self.assertEqual(len(entries), ctxs.info["pieces"])
        self.assertEqual(ctxs.info["triangles"], 36)
        mesh = ifc_mesh.load(ctx["mesh"])
        # the corners of «A» in the scene, by the entries' position and turn, against the body made of «A»
        k = [int(e[0]) for e in mesh["elements"]].index(65)
        v, f, _c = ifc_mesh.piece(mesh, int(mesh["piece_of"][k]))
        first, n = int(mesh["elements"][k][1]), int(mesh["elements"][k][2])
        q = v[np.unique(f[first:first + n])].astype(float)
        e = entries[int(mesh["piece_of"][k])]
        t = math.radians(e["turn"])
        qx, qz = q[:, 0], -q[:, 1]                                        # Qt axes: x east, z south
        x = qx * math.cos(t) + qz * math.sin(t) + e["position"][0]
        z = -qx * math.sin(t) + qz * math.cos(t) + e["position"][2]
        plan_pts = np.column_stack((x, -z))
        body = next(b for b in project.buildings if b.id in ids and b.name == "A")
        ring = np.asarray(body.footprint)
        self.assertLess(np.abs(np.sort(plan_pts[:, 0]).reshape(-1)[[0, -1]] - [ring[:, 0].min(), ring[:, 0].max()]).max(),
                        0.15)
        self.assertLess(np.abs(np.sort(plan_pts[:, 1])[[0, -1]] - [ring[:, 1].min(), ring[:, 1].max()]).max(), 0.15)
        self.assertAlmostEqual(q[:, 2].max() + e["position"][1], 2.0, places=4)
        # the bodies of the import are the faint ones
        self.assertEqual(scene_context.members(project, scene_context.reference(project)), set(ids))
        self.assertEqual(scene_context.ghost_ranges([("building", ids[0], 12), ("site", "", 2), ("building", "x", 4)],
                                                    {ids[0]}), [(0, 12)])
        # an anchor reshaped: the frame is lost, nothing is drawn (the bodies stay)
        project.buildings[0].footprint = [[0, 0], [9, 0], [9, 9]]
        self.assertEqual(ctxs.entries(project), [])


if __name__ == "__main__":
    unittest.main()
