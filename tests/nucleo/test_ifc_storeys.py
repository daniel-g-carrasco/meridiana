"""r22-ifc: the storeys of a model as a choice of the import. A project of several buildings exported (Meridiana writes a
storey for each building) and read back by the worker: its roofs through IfcOpenShell, its solids by the fast scan; a
storey left out takes its roofs, obstacles, solids and true shapes with it."""
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401  (paths and the common setup)
from _fixtures import exported, mixed

from meridiana import ifc_import, ifc_read, ifc_worker, model


class Storeys(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ifc_read.available():
            raise unittest.SkipTest("ifcopenshell is not installed")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.original = mixed()
        path, _s, _r = exported(cls.original, Path(cls.tmp.name))
        cls.found = ifc_worker.read(str(path), "direct", lambda f, w: None, None, str(Path(cls.tmp.name) / "c"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_storeys_are_offered_and_one_left_out_takes_its_roofs_and_solids_with_it(self):
        names = ifc_import.storeys_of(self.found)
        self.assertTrue(set(names) >= {b.name for b in self.original.buildings})       # and «Terreno» for the loose
        self.assertGreater(len(names), 1)
        everything = ifc_import.plan(self.found, model.Project(), "origin", solids="elements")
        keep = names[:1]
        some = ifc_import.plan(self.found, model.Project(), "origin", solids="elements", storeys=keep)
        roofs = [b for b in self.found["buildings"] if b.get("storey") in keep]
        self.assertTrue(roofs)
        # the IfcOpenShell way: only the roofs of the storey kept, and the solids of that storey
        self.assertLess(len(some.buildings), len(everything.buildings))
        solids = [s for s in self.found["solids"] if s.get("storey") in keep]
        self.assertTrue(solids)
        self.assertEqual(len(some.buildings), len(roofs) + len(solids))
        # its obstacles stay on its roofs: none points to a roof left out
        hosts = {host for _e, host in some.exclusions if host is not None}
        self.assertTrue(hosts <= set(range(len(some.buildings))))
        # the true shapes of the storeys left out are not the 3D's nor the shadows'
        skip = set(some.reference["context"]["skip"])
        self.assertEqual(skip, {s["id"] for s in self.found["solids"] if s.get("storey") not in keep})
        self.assertNotIn("skip", everything.reference["context"])

    def test_every_storey_ticked_is_the_whole_model(self):
        names = ifc_import.storeys_of(self.found)
        self.assertIs(ifc_import.by_storeys(self.found, None), self.found)
        same = ifc_import.by_storeys(self.found, names)
        self.assertEqual(len(same["buildings"]), len(self.found["buildings"]))
        self.assertEqual(len(same["solids"]), len(self.found["solids"]))
        self.assertEqual(len(same["obstacles"]), len(self.found["obstacles"]))

    def test_the_3d_leaves_out_the_shapes_of_the_storeys_not_taken(self):
        from meridiana import ifc_mesh
        mesh = ifc_mesh.load(self.found["context"]["mesh"])
        names = ifc_import.storeys_of(self.found)
        skip = [s["id"] for s in self.found["solids"] if s.get("storey") != names[0]]
        whole = sum(len(ifc_mesh.piece(mesh, i)[1]) for i in range(len(mesh["pieces"])))
        left = sum(len(ifc_mesh.piece(mesh, i, skip)[1]) for i in range(len(mesh["pieces"])))
        mine = sum(int(e[2]) for e in mesh["elements"] if int(e[0]) not in set(skip))
        self.assertEqual(whole, len(mesh["faces"]))
        self.assertEqual(left, mine)
        self.assertLess(left, whole)


if __name__ == "__main__":
    unittest.main()
