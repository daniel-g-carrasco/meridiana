"""r22-ifc: the plant added to the architect's IFC (ifc_append). The file read back with IfcOpenShell: every entity of
the original identical, byte for byte up to where the plant begins and after it; the modules, the strings, the system
and the inverters new, contained in the original's storey (or building), where the modules lie in the model; stable
GlobalIds; a second round on the same file refused. IFC4 (buildingSMART's architecture sample, storeys, metres) and
IFC2X3 (the scan's sample, a building without storeys, millimetres, like the large test IFC)."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

import _setup
from meridiana import ifc_append, ifc_export, ifc_import, ifc_read, ifc_scan, ifc_worker, model
from nucleo.test_ifc_scan import SAMPLE

OWNER = """#200=IFCPERSON($,$,'x',$,$,$,$,$);
#201=IFCORGANIZATION($,'o',$,$,$);
#202=IFCPERSONANDORGANIZATION(#200,#201,$);
#203=IFCAPPLICATION(#201,'1','a','a');
#204=IFCOWNERHISTORY(#202,#203,$,.ADDED.,$,$,$,0);
ENDSEC;
END-ISO-10303-21;
"""


def imported(path: Path, folder: Path, solids: str):
    """A project made of the model: its bodies, a sub-field filled with modules on the first body with a roof big
    enough, else on the ground next to the model; the results and half of the modules in a string."""
    found = ifc_worker.read(str(path), "direct", lambda f, w: None, None, None)
    project = model.Project()
    plan = ifc_import.plan(found, project, "origin", None, name="m", source_name=path.name, solids=solids)
    ids = ifc_import.apply(project, plan)
    big = [b for b in project.buildings if b.id in ids and _area(b.footprint) > 20]
    if big:
        host = max(big, key=lambda b: _area(b.footprint))
        sf = model.SubField(id="s1", name="tetto", ring=[list(q) for q in host.footprint], building=host.id, pitch=host.pitch_ref(0),
                            params={"mounting": "coplanar"}, filled=True)
    else:
        xs = [x for b in project.buildings for x, _y in b.footprint]
        ys = [y for b in project.buildings for _x, y in b.footprint]
        x0, y0 = max(xs) + 3, min(ys)
        sf = model.SubField(id="s1", name="terra", ring=[[x0, y0], [x0 + 12, y0], [x0 + 12, y0 + 8], [x0, y0 + 8]],
                            building=None, pitch=None, params={"mounting": "ground"}, filled=True)
    project.subfields.append(sf)
    result = project.fill(sf)
    strings = {(sf.id, pm.key): "1.1.1" for pm in result.modules[: len(result.modules) // 2]}
    return project, {sf.id: result}, strings


def _area(ring) -> float:
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1], strict=True))) / 2


class Append(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ifc_read.available():
            raise unittest.SkipTest("ifcopenshell is not installed")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def check(self, source: Path, solids: str, schema: str, occurrence: str):
        import ifcopenshell
        import ifcopenshell.util.placement as placement
        project, results, strings = imported(source, self.folder / source.stem, solids)
        modules = len(results["s1"].modules)
        self.assertGreater(modules, 4)
        target = self.folder / f"{source.stem}-con-impianto.ifc"
        summary = ifc_append.append(project, results, source, target, strings)
        self.assertEqual(summary["schema"], schema)
        self.assertEqual(summary["modules"], modules)
        # the original, byte for byte, before the plant and after it
        a, b = source.read_bytes(), target.read_bytes()
        at, added = summary["insert_at"], summary["added_bytes"]
        self.assertEqual(b[:at], a[:at])
        self.assertEqual(b[-(len(a) - at):], a[at:])
        self.assertEqual(len(b), len(a) + added + (len(b) - len(a) - added))
        old, new = ifcopenshell.open(str(source)), ifcopenshell.open(str(target))
        self.assertEqual(new.schema, old.schema)
        for e in old:                                          # every entity of the architect's, unchanged
            self.assertEqual(str(new.by_id(e.id())), str(e))
        fresh = [e for e in new if e.id() >= summary["first_id"]]
        self.assertTrue(fresh)
        self.assertGreater(min(e.id() for e in fresh), max(e.id() for e in old))
        devices = [e for e in new.by_type(occurrence) if e.id() >= summary["first_id"]
                   and (e.ObjectType or "SOLARPANEL") == "SOLARPANEL" and "INVERTER" not in (e.ObjectType or "")]
        self.assertEqual(len(devices), modules)
        holders = {e.GlobalId for e in old.by_type("IfcBuildingStorey")} or \
            {e.GlobalId for e in old.by_type("IfcBuilding")}
        for d in devices:
            rel = d.ContainedInStructure
            self.assertEqual(len(rel), 1)
            self.assertIn(rel[0].RelatingStructure.GlobalId, holders)   # the architect's own storey or building
            self.assertEqual(rel[0].RelatingStructure.id(), old.by_guid(rel[0].RelatingStructure.GlobalId).id())
        circuits = new.by_type("IfcElectricalCircuit" if schema == "IFC2X3" else "IfcDistributionCircuit")
        self.assertEqual(len(circuits), 1)
        self.assertEqual(len(circuits[0].IsGroupedBy[0].RelatedObjects), modules // 2)
        # where the modules lie: the same offsets from the model as in the plan (the import put it at the plan's
        # middle, not turned), in the file's unit
        unit = summary["unit_m"]
        frame, _why = ifc_export.frame_of(project)
        by_name = {d.Name: d for d in devices}
        sf = project.subfields[0]
        world = np.array([placement.get_local_placement(by_name[f"{sf.name} {pm.key}"].ObjectPlacement)[:3, 3]
                          for pm in results["s1"].modules]) * unit
        plan = np.array([[*pm.centre] for pm in results["s1"].modules])
        mx, my = frame["move"]
        c, s = np.cos(frame["turn"]), np.sin(frame["turn"])
        expected = np.column_stack([c * plan[:, 0] - s * plan[:, 1] + mx, s * plan[:, 0] + c * plan[:, 1] + my])
        np.testing.assert_allclose(world[:, :2], expected, atol=0.05)     # world = R(turn) plan + move
        # against the model itself: the modules inside the model's plan box (on its roof) or beside it (on the ground)
        scan = ifc_scan.scan(source)
        lo = np.min([e.lo for e in scan.elements], axis=0)
        hi = np.max([e.hi for e in scan.elements], axis=0)
        if results["s1"].modules and project.subfields[0].building:
            self.assertTrue(np.all(world[:, :2] >= lo[:2] - 0.5) and np.all(world[:, :2] <= hi[:2] + 0.5))
            self.assertTrue(np.all(world[:, 2] >= lo[2]))
        else:
            self.assertTrue(np.all(world[:, 0] > hi[0]))                  # east of the model, as laid
        # stable: written again, the same GlobalIds
        again = self.folder / f"{source.stem}-di-nuovo.ifc"
        ifc_append.append(project, results, source, again, strings)
        self.assertEqual(sorted(e.GlobalId for e in ifcopenshell.open(str(again)).by_type(occurrence)),
                         sorted(e.GlobalId for e in new.by_type(occurrence)))
        self.assertEqual(again.read_bytes(), b)
        # valid as the original is
        self.assertEqual(len(ifc_export.validate(target)), len(ifc_export.validate(source)))
        # a file the plant was added to is not a starting point
        with self.assertRaises(ifc_append.AppendError):
            ifc_append.append(project, results, target, self.folder / "due-volte.ifc", strings)
        with self.assertRaises(ifc_append.AppendError):
            ifc_append.append(project, results, source, source, strings)
        return summary

    def test_ifc4_architecture_in_its_storey(self):
        summary = self.check(_setup.DATA / "ifc" / "Building-Architecture.ifc", "none", "IFC4", "IfcSolarDevice")
        self.assertEqual(summary["unit_m"], 1.0)

    def test_ifc2x3_in_millimetres_in_its_building(self):
        source = self.folder / "sample-2x3.ifc"
        source.write_text(SAMPLE.replace("ENDSEC;\nEND-ISO-10303-21;\n", OWNER), encoding="ascii", newline="\n")
        summary = self.check(source, "elements", "IFC2X3", "IfcEnergyConversionDevice")
        self.assertEqual(summary["unit_m"], 0.001)

    def test_a_project_not_imported_is_said(self):
        with self.assertRaises(ifc_append.AppendError):
            ifc_append.append(model.Project(), {}, _setup.DATA / "ifc" / "Building-Architecture.ifc",
                              self.folder / "x.ifc")


if __name__ == "__main__":
    unittest.main()
