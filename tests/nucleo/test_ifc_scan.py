"""The fast reading of large IFC files (R400, ifc_scan): the same boxes as IfcOpenShell on the files of the tests, the
same elements read in one process or in several pieces by several, mapped items made once and moved, the text of the
records parsed; then the worker that gives the solids with the result, and the import of the solids as bodies with
their outlines and heights, by group or by element, in a zone, the pieces of a group parts of its first body.

The long trial on the large test IFC's model (1.6 GB, a client's, only on Daniel's PC) runs with MERIDIANA_LONG_IFC=1."""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import _setup  # noqa: F401

from meridiana import ifc_import, ifc_scan, model, procmem

DATA = Path(__file__).resolve().parents[1] / "data" / "ifc"
LONG_IFC = Path(os.environ.get("MERIDIANA_LONG_IFC_FILE", "-"))

# a cube of 1 m by 2 m in millimetres as a faceted Brep of quadrilaterals (one face with an inner bound), a
# representation map used by two proxies of one assembly (one moved 5 m, one placed 3 m up), and an extruded slab
SAMPLE = r"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION((''),'2;1');
FILE_NAME('t','2026-11-07T00:00:00',(''),(''),'','','');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
#1=IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);
#2=IFCUNITASSIGNMENT((#1));
#3=IFCPROJECT('0000000000000000000001',$,'P',$,$,$,$,$,#2);
#4=IFCCARTESIANPOINT((0.,0.,0.));
#5=IFCAXIS2PLACEMENT3D(#4,$,$);
#6=IFCLOCALPLACEMENT($,#5);
#7=IFCBUILDING('0000000000000000000002',$,'Hall',$,$,#6,$,$,.ELEMENT.,$,$,$);
#8=IFCRELAGGREGATES('0000000000000000000003',$,$,$,#3,(#7));
#10=IFCCARTESIANPOINT((0.,0.,0.));
#11=IFCCARTESIANPOINT((1000.,0.,0.));
#12=IFCCARTESIANPOINT((1000.,1000.,0.));
#13=IFCCARTESIANPOINT((0.,1000.,0.));
#14=IFCCARTESIANPOINT((0.,0.,2000.));
#15=IFCCARTESIANPOINT((1000.,0.,2000.));
#16=IFCCARTESIANPOINT((1000.,1000.,2000.));
#17=IFCCARTESIANPOINT((0.,1000.,2000.));
#20=IFCPOLYLOOP((#10,#13,#12,#11));
#21=IFCPOLYLOOP((#14,#15,#16,#17));
#22=IFCPOLYLOOP((#10,#11,#15,#14));
#23=IFCPOLYLOOP((#11,#12,#16,#15));
#24=IFCPOLYLOOP((#12,#13,#17,#16));
#25=IFCPOLYLOOP((#13,#10,#14,#17));
#26=IFCPOLYLOOP((#10,#11,#12));
#30=IFCFACEOUTERBOUND(#20,.T.);
#31=IFCFACEOUTERBOUND(#21,.T.);
#32=IFCFACEOUTERBOUND(#22,.T.);
#33=IFCFACEOUTERBOUND(#23,.T.);
#34=IFCFACEOUTERBOUND(#24,.T.);
#35=IFCFACEOUTERBOUND(#25,.T.);
#36=IFCFACEBOUND(#26,.F.);
#40=IFCFACE((#30));
#41=IFCFACE((#31));
#42=IFCFACE((#32));
#43=IFCFACE((#33));
#44=IFCFACE((#34));
#45=IFCFACE((#35,#36));
#50=IFCCLOSEDSHELL((#40,#41,#42,#43,#44,#45));
#51=IFCFACETEDBREP(#50);
#52=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#5,$);
#53=IFCSHAPEREPRESENTATION(#52,'Body','Brep',(#51));
#54=IFCREPRESENTATIONMAP(#5,#53);
#60=IFCCARTESIANPOINT((5000.,0.,0.));
#61=IFCCARTESIANTRANSFORMATIONOPERATOR3D($,$,#60,1.,$);
#62=IFCMAPPEDITEM(#54,#61);
#63=IFCSHAPEREPRESENTATION(#52,'Body','MappedRepresentation',(#62));
#64=IFCPRODUCTDEFINITIONSHAPE($,$,(#63));
#65=IFCBUILDINGELEMENTPROXY('0000000000000000000004',$,'A',$,$,#6,#64,$,$);
#70=IFCCARTESIANPOINT((0.,10000.,3000.));
#71=IFCAXIS2PLACEMENT3D(#70,$,$);
#72=IFCLOCALPLACEMENT(#6,#71);
#73=IFCCARTESIANTRANSFORMATIONOPERATOR3D($,$,#4,1.,$);
#74=IFCMAPPEDITEM(#54,#73);
#75=IFCSHAPEREPRESENTATION(#52,'Body','MappedRepresentation',(#74));
#76=IFCPRODUCTDEFINITIONSHAPE($,$,(#75));
#77=IFCBUILDINGELEMENTPROXY('0000000000000000000005',$,'B',$,$,#72,#76,$,$);
#80=IFCCARTESIANPOINT((0.,0.));
#81=IFCAXIS2PLACEMENT2D(#80,$);
#82=IFCRECTANGLEPROFILEDEF(.AREA.,$,#81,2000.,4000.);
#83=IFCDIRECTION((0.,0.,1.));
#84=IFCEXTRUDEDAREASOLID(#82,#5,#83,500.);
#85=IFCSHAPEREPRESENTATION(#52,'Body','SweptSolid',(#84));
#86=IFCPRODUCTDEFINITIONSHAPE($,$,(#85));
#87=IFCCARTESIANPOINT((20000.,0.,0.));
#88=IFCAXIS2PLACEMENT3D(#87,$,$);
#89=IFCLOCALPLACEMENT(#6,#88);
#90=IFCSLAB('0000000000000000000006',$,'Soletta \X2\00E8\X0\ l''ultima',$,$,#89,#86,$,.FLOOR.);
#95=IFCELEMENTASSEMBLY('0000000000000000000007',$,'Skid',$,$,#6,$,$,.NOTDEFINED.,.NOTDEFINED.);
#96=IFCRELAGGREGATES('0000000000000000000008',$,$,$,#95,(#65,#77));
#97=IFCRELCONTAINEDINSPATIALSTRUCTURE('0000000000000000000009',$,$,$,(#95,#90),#7);
ENDSEC;
END-ISO-10303-21;
"""


def need_ifcopenshell():
    import importlib.util
    if importlib.util.find_spec("ifcopenshell") is None:
        raise unittest.SkipTest("ifcopenshell is not installed")


class Sample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "sample.ifc"
        cls.path.write_text(SAMPLE, encoding="ascii", newline="\n")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_boxes_the_groups_and_the_maps(self):
        s = ifc_scan.scan(self.path)
        by = {e.name: e for e in s.elements}
        self.assertEqual(set(by), {"A", "B", "Soletta è l'ultima"})
        self.assertEqual(s.unit_m, 0.001)
        self.assertEqual((by["A"].lo, by["A"].hi), ((5.0, 0.0, 0.0), (6.0, 1.0, 2.0)))
        self.assertEqual((by["B"].lo, by["B"].hi), ((0.0, 10.0, 3.0), (1.0, 11.0, 5.0)))
        self.assertEqual((by["Soletta è l'ultima"].lo, by["Soletta è l'ultima"].hi), ((19.0, -2.0, 0.0), (21.0, 2.0, 0.5)))
        self.assertEqual(by["A"].group, 95)
        self.assertEqual(by["A"].group_name, "Skid")
        self.assertEqual(by["B"].group, 95)
        self.assertEqual(by["A"].triangles, 12)                 # six quadrilaterals as fans; the hole left out
        self.assertEqual((s.maps, s.instances), (1, 2))
        self.assertEqual(by["A"].cls, "IfcBuildingElementProxy")
        self.assertEqual(sorted(map(tuple, by["A"].hull)), [(5.0, 0.0), (5.0, 1.0), (6.0, 0.0), (6.0, 1.0)])
        listing = s.listing()
        self.assertEqual(listing["elements"], 3)
        self.assertEqual(listing["groups"], 2)
        self.assertEqual(listing["buildings"], ["Hall"])
        self.assertEqual(json.loads(json.dumps(listing))["schema"], "IFC2X3")
        self.assertEqual(s.triangles(65).shape, (12, 3, 3))

    def test_in_pieces_by_several_processes_the_same(self):
        one = ifc_scan.scan(self.path, workers=1)
        old = ifc_scan.PIECE, ifc_scan.SMALL_FILE
        ifc_scan.PIECE, ifc_scan.SMALL_FILE = 600, 0           # pieces of a few records, two processes
        try:
            seen = []
            many = ifc_scan.scan(self.path, progress=lambda f, w: seen.append((f, w)), workers=2)
        finally:
            ifc_scan.PIECE, ifc_scan.SMALL_FILE = old
        self.assertGreater(len(ifc_scan._pieces(str(self.path), self.path.stat().st_size, 600)), 3)
        self.assertEqual(many.workers, 2)
        self.assertEqual([(e.id, e.lo, e.hi, e.triangles) for e in one.elements],
                         [(e.id, e.lo, e.hi, e.triangles) for e in many.elements])
        self.assertEqual(one.counts, many.counts)
        fractions = [f for f, _w in seen]
        self.assertEqual(fractions, sorted(fractions))
        self.assertEqual(fractions[-1], 1.0)

    def test_the_text_of_the_records(self):
        a = ifc_scan.parse_args(b"'a''b \\X2\\00E8\\X0\\',$,*,.T.,(#1,#2),IFCLABEL('x'),1.5E-3,-2,((1.,2.),(3.,4.)));")
        self.assertEqual(a[:4], ["a'b è", None, None, ".T."])
        self.assertEqual(a[4], [1, 2])
        self.assertIsInstance(a[4][0], ifc_scan.Ref)
        self.assertEqual((a[5].name, a[5].value), ("IFCLABEL", "x"))
        self.assertEqual(a[6:8], [0.0015, -2])
        self.assertEqual(a[8], [[1.0, 2.0], [3.0, 4.0]])

    def test_not_an_ifc_file(self):
        bad = Path(self.tmp.name) / "bad.ifc"
        bad.write_text("hello", encoding="ascii")
        with self.assertRaises(ifc_scan.ScanError):
            ifc_scan.scan(bad)

    def test_the_solids_made_bodies(self):
        found = self._found()
        project = model.Project()
        self.assertEqual(ifc_import.default_solids(found), "groups")
        p = ifc_import.plan(found, project, "origin", solids="groups")
        self.assertEqual(len(p.buildings), 3)                   # the skid in two pieces apart, the slab
        names = [b.name for b in p.buildings]
        self.assertEqual(sorted(n for n in names if n.startswith("Skid")), ["Skid", "Skid 2"])
        k = [names.index("Skid"), names.index("Skid 2")]
        self.assertEqual(p.parts[k[1]], k[0])                    # the second piece a part of the first
        self.assertEqual(sorted(round(b.wall_top(), 2) for b in p.buildings), [0.5, 2.0, 5.0])
        raised = [i for i, w in enumerate(p.bases) if (w.get("base") or 0) > 1]
        self.assertEqual(len(raised), 1)
        ids = ifc_import.apply(project, p)
        made = [project.building(i) for i in ids]
        self.assertEqual(sorted(b.base for b in made), [0.0, 0.0, 3.0])
        self.assertEqual(sum(1 for b in made if b.part_of), 1)
        self.assertTrue(any("solids" in a for a in p.approximated))
        # by element, only the building's, and a zone
        self.assertEqual(len(ifc_import.plan(found, model.Project(), "origin", solids="elements").buildings), 3)
        self.assertEqual(len(ifc_import.plan(found, model.Project(), "origin", solids="groups", kinds="building")
                             .buildings), 1)
        self.assertEqual(len(ifc_import.plan(found, model.Project(), "origin", solids="none").buildings), 0)
        whole = ifc_import.plan(found, model.Project(), "origin", solids="elements")
        slab = next(b for b in whole.buildings if b.wall_top() < 1)
        xs = [q[0] for q in slab.footprint]
        ys = [q[1] for q in slab.footprint]
        zone = (min(xs) - 0.5, min(ys) - 0.5, max(xs) + 0.5, max(ys) + 0.5)
        zoned = ifc_import.plan(found, model.Project(), "origin", solids="elements", zone=zone)
        self.assertEqual(len(zoned.buildings), 1)
        self.assertEqual(len(zoned.zone_rings), 2)

    def _found(self) -> dict:
        from meridiana import ifc_worker
        s = ifc_scan.scan(self.path)
        return {"schema": s.schema, "buildings": [], "obstacles": [], "supports": [], "counts": {}, "site": None,
                "true_north": 0.0, "map": None, "solids": [ifc_worker.compact(e) for e in s.elements],
                "solids_ground": 0.0}


class Files(unittest.TestCase):
    def test_the_same_boxes_as_ifcopenshell(self):
        need_ifcopenshell()
        import ifcopenshell
        import ifcopenshell.geom
        import numpy as np
        for name in ("Building-Architecture.ifc", "Building-Hvac.ifc"):
            s = ifc_scan.scan(DATA / name)
            f = ifcopenshell.open(str(DATA / name))
            st = ifcopenshell.geom.settings()
            st.set("use-world-coords", True)
            st.set("disable-opening-subtractions", True)
            products = [e for e in f.by_type("IfcProduct") if e.Representation is not None
                        and not e.is_a("IfcOpeningElement") and not e.is_a("IfcSpatialStructureElement")
                        and not e.is_a("IfcSpatialZone")]
            self.assertEqual(sorted(e.id() for e in products), sorted(e.id for e in s.elements), name)
            for e in s.elements:
                v = np.asarray(ifcopenshell.geom.create_shape(st, f.by_id(e.id)).geometry.verts).reshape(-1, 3)
                self.assertLess(max(np.abs(v.min(0) - e.lo).max(), np.abs(v.max(0) - e.hi).max()), 0.02,
                                f"{name} #{e.id}")

    def test_the_worker_gives_the_solids(self):
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}
        out = subprocess.run([sys.executable, "-m", "meridiana.ifc_worker", str(DATA / "Building-Hvac.ifc")],
                             capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
        lines = [json.loads(x) for x in out.stdout.splitlines() if x.strip()]
        result = next(x["result"] for x in lines if "result" in x)
        self.assertEqual(result["mode"], "scan")                  # no roof, no slab, no wall: the solids
        self.assertEqual(len(result["solids"]), 5)
        self.assertIn("scan", {x.get("what") for x in lines})
        p = ifc_import.plan(result, model.Project(), "origin")
        self.assertGreater(len(p.buildings), 0)
        out = subprocess.run([sys.executable, "-m", "meridiana.ifc_worker", str(DATA / "Building-Architecture.ifc")],
                             capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
        result = json.loads(out.stdout.strip().splitlines()[-1])["result"]
        self.assertEqual(result["mode"], "direct")                # the roofs as before, the solids with them
        self.assertEqual(len(result["solids"]), 11)
        self.assertEqual(ifc_import.default_solids(result), "none")


@unittest.skipUnless(os.environ.get("MERIDIANA_LONG_IFC") and LONG_IFC.is_file(), "the long trial on the large test IFC's model")
class GeAvio(unittest.TestCase):
    def test_read_and_made_bodies_in_time(self):
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}
        t0 = time.monotonic()
        p = subprocess.Popen([sys.executable, "-m", "meridiana.ifc_worker", str(LONG_IFC)], stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, env=env)
        peak = 0
        try:
            import threading
            done = threading.Event()

            def watch():
                nonlocal peak
                while not done.wait(0.25):          # a sample of the memory every 250 ms until the reader ends
                    peak = max(peak, procmem.rss(p.pid, tree=True) or 0)
            threading.Thread(target=watch, daemon=True).start()
            data, _err = p.communicate(timeout=300)
            done.set()
        finally:
            if p.poll() is None:
                p.kill()
        seconds = time.monotonic() - t0
        result = json.loads(data.decode("utf-8").strip().splitlines()[-1])["result"]
        print(f"\nthe large test IFC: {seconds:.1f} s, {peak / 2**30:.2f} GiB, {len(result['solids'])} solids", file=sys.stderr)
        self.assertGreater(len(result["solids"]), 13000)
        self.assertLess(seconds, 150)
        self.assertLess(peak, 7 * 2 ** 30)
        t = time.monotonic()
        plan = ifc_import.plan(result, model.Project(), "origin")
        print(f"the large test IFC plan by group: {time.monotonic() - t:.1f} s, {len(plan.buildings)} bodies", file=sys.stderr)
        self.assertGreater(len(plan.buildings), 50)


if __name__ == "__main__":
    unittest.main()
