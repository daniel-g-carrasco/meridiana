"""The plant alone as IFC4 (R453, first step): the modules, the canopies' structure, the strings and the inverters, without
the buildings, in the coordinates and with the georeferencing of the whole model, so that it lies on the architect's
model in a federated model; and a project whose buildings came from an IFC written in that model's frame, its site, its
north and its map conversion, so that the modules stand on the roofs of the file they came from."""

import math
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401
from _fixtures import capannone, exported, mixed

from meridiana import ifc_export, ifc_import, ifc_read, jobs, model
from meridiana.energy import plant as plants

def need_ifcopenshell():
    import importlib.util
    if importlib.util.find_spec("ifcopenshell") is None:
        raise unittest.SkipTest("ifcopenshell is not installed")


def written(project, folder: Path, name: str, what: str):
    results, _keys, _laid = jobs.layout_of(project)
    pl = plants.build(project, results, check=False)
    strings = {(sf, key): s.label for s in pl.strings for sf, key, _c in s.modules}
    path = folder / name
    return path, ifc_export.export(project, results, path, strings=strings, what=what, plant=pl), results


def modules_in_the_world(path) -> dict:
    """Each module of a file by its GlobalId: its placement's origin in the world, metres."""
    import ifcopenshell
    import ifcopenshell.util.placement
    f = ifcopenshell.open(str(path))
    return {m.GlobalId: ifcopenshell.util.placement.get_local_placement(m.ObjectPlacement)[:3, 3]
            for m in f.by_type("IfcSolarDevice")}


def conversion(path):
    import ifcopenshell
    f = ifcopenshell.open(str(path))
    found = f.by_type("IfcMapConversion")
    if not found:
        return None
    m = found[0]
    return (m.TargetCRS.Name, round(m.Eastings, 6), round(m.Northings, 6), round(m.OrthogonalHeight, 6),
            round(m.XAxisAbscissa or 1.0, 9), round(m.XAxisOrdinate or 0.0, 9), round(m.Scale or 1.0, 9))


class PlantAlone(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        need_ifcopenshell()
        cls.folder = Path(tempfile.mkdtemp())
        cls.project = mixed()
        cls.whole, cls.whole_out, _r = written(cls.project, cls.folder, "tutto.ifc", "all")
        cls.alone, cls.alone_out, _r = written(cls.project, cls.folder, "impianto.ifc", "plant")

    def test_both_files_are_valid_ifc4(self):
        self.assertEqual(ifc_export.validate(self.whole), [])
        self.assertEqual(ifc_export.validate(self.alone), [])

    def test_the_modules_coincide_within_a_millimetre_and_the_georeferencing_is_the_same(self):
        whole, alone = modules_in_the_world(self.whole), modules_in_the_world(self.alone)
        self.assertGreater(len(whole), 50)
        self.assertEqual(set(whole), set(alone))                     # the same modules, by their GlobalId
        worst = max(float(sum((whole[g] - alone[g]) ** 2) ** 0.5) for g in whole)
        self.assertLess(worst, 0.001)
        self.assertIsNotNone(conversion(self.whole))
        self.assertEqual(conversion(self.whole), conversion(self.alone))

    def test_the_plant_alone_has_no_building_of_its_own_and_its_strings_and_inverters(self):
        import ifcopenshell
        f = ifcopenshell.open(str(self.alone))
        for kind in ("IfcWall", "IfcRoof", "IfcSlab", "IfcChimney", "IfcWindow", "IfcGeographicElement"):
            self.assertFalse(f.by_type(kind), kind)
        circuits = f.by_type("IfcDistributionCircuit")
        self.assertEqual(len(circuits), self.alone_out["classes"]["strings"])
        self.assertTrue(all(c.Name.startswith("Stringa ") and c.PredefinedType == "ELECTRICAL" for c in circuits))
        [system] = f.by_type("IfcDistributionSystem", include_subtypes=False)
        self.assertEqual(system.PredefinedType, "POWERGENERATION")
        inverters = f.by_type("IfcTransformer")
        self.assertTrue(inverters)
        self.assertTrue(all(i.PredefinedType == "INVERTER" for i in inverters))
        self.assertEqual(self.alone_out["what"], "plant")
        self.assertEqual(self.alone_out["frame"], "site")
        self.assertLess(self.alone_out["bytes"], self.whole_out["bytes"])


class FromTheArchitectsModel(unittest.TestCase):
    """An architect's model: a shed written by Meridiana without modules, then its true north turned by 35 degrees and
    its building moved 500 m east and 200 m north in the file, as another program would have it. Imported at the middle
    of the plan, modules laid on its roof, the plant alone written: its modules stand on that roof in the file's own
    world, with the file's site and map conversion."""

    @classmethod
    def setUpClass(cls):
        need_ifcopenshell()
        import ifcopenshell
        cls.folder = Path(tempfile.mkdtemp())
        shed = capannone()
        shed.subfields = []
        cls.source, _s, _r = exported(shed, cls.folder, "architetto.ifc")
        f = ifcopenshell.open(str(cls.source))
        ctx = next(c for c in f.by_type("IfcGeometricRepresentationContext")
                   if not c.is_a("IfcGeometricRepresentationSubContext"))
        a = math.radians(35.0)
        ctx.TrueNorth = f.createIfcDirection((-math.sin(a), math.cos(a)))
        f.by_type("IfcBuilding")[0].ObjectPlacement.RelativePlacement.Location.Coordinates = (500.0, 200.0, 0.0)
        f.write(str(cls.source))
        cls.found = ifc_read.read(cls.source)
        p = model.Project()
        plan = ifc_import.plan(cls.found, p, "origin", north="context", source_name=cls.source.name)
        cls.theta = plan.reference["theta"]
        ids = ifc_import.apply(p, plan)
        house = next(b for b in p.buildings if b.id == ids[0])
        from shapely.geometry import Polygon
        ring = Polygon(house.footprint).buffer(-1.0, join_style="mitre")
        p.subfields.append(model.SubField(id=p.new_id("s"), name="Tetto", ring=[list(q) for q in ring.exterior.coords[:-1]],
                                          building=house.id, filled=True, params={"tilt": 15.0}))
        cls.project, cls.house = p, house
        cls.alone, cls.out, cls.results = written(p, cls.folder, "impianto.ifc", "plant")

    def test_the_frame_is_kept_with_the_project_and_is_a_real_turn(self):
        ref = self.project.resources["ifc_reference"]
        self.assertEqual(ref["file"], "architetto.ifc")
        self.assertGreater(abs(self.theta), 1.0)                       # the map's north: not a frame that does nothing
        self.assertEqual(ref["anchor"]["building"], self.house.id)
        self.assertEqual(self.out["frame"], "imported")
        self.assertEqual(ifc_export.validate(self.alone), [])

    def test_the_modules_stand_on_the_pitch_of_the_file_in_its_own_world(self):
        from shapely.geometry import Point, Polygon
        [raw] = self.found["buildings"]
        outline = Polygon(raw["footprint"])
        at = modules_in_the_world(self.alone)
        self.assertGreater(len(at), 4)
        planes = set()
        for g, (x, y, z) in at.items():
            self.assertTrue(outline.buffer(0.01).contains(Point(x, y)), (g, x, y))
            under = [q for q in raw["pitches"] if Polygon([c[:2] for c in q["ring"]]).buffer(0.05).contains(Point(x, y))]
            self.assertTrue(under, (g, x, y))
            (nx, ny, nz), (ax, ay, az) = under[0]["normal"], under[0]["point"]
            roof = az - (nx * (x - ax) + ny * (y - ay)) / nz
            self.assertTrue(roof - 0.05 < z < roof + 1.5, (g, z, roof))       # on its rows, over the roof
            planes.add(id(under[0]))
        self.assertEqual(len(planes), 1)                                 # all on the one pitch they were laid on

    def test_the_site_and_the_map_conversion_are_the_files(self):
        import ifcopenshell
        theirs, mine = ifcopenshell.open(str(self.source)), ifcopenshell.open(str(self.alone))
        a, b = theirs.by_type("IfcMapConversion")[0], mine.by_type("IfcMapConversion")[0]
        unit = self.found["unit_m"]
        self.assertEqual(a.TargetCRS.Name, b.TargetCRS.Name)
        self.assertAlmostEqual(a.Eastings * (self.found["map"]["map_unit_m"]), b.Eastings, places=6)
        self.assertAlmostEqual(a.Northings * (self.found["map"]["map_unit_m"]), b.Northings, places=6)
        self.assertAlmostEqual(a.XAxisAbscissa, b.XAxisAbscissa, places=9)
        self.assertAlmostEqual(a.XAxisOrdinate, b.XAxisOrdinate, places=9)
        self.assertAlmostEqual((a.Scale or 1.0) * self.found["map"]["map_unit_m"] / unit, b.Scale or 1.0, places=9)

    def test_moved_and_turned_since_the_import_the_modules_still_land_on_the_file(self):
        """The buildings moved together on the plan (move.members): the frame follows them; reshaped, it is given up."""
        ref, _note = ifc_export.frame_of(self.project)
        x, y = self.house.footprint[0]

        def world(frame, px, py):
            c, s = math.cos(frame["turn"]), math.sin(frame["turn"])
            return c * px - s * py + frame["move"][0], s * px + c * py + frame["move"][1]
        before = world(ref, x, y)
        moved = model.Project.from_json(self.project.to_json(), check=False)
        a, tx, ty = math.radians(30.0), 12.5, -40.0
        b = next(q for q in moved.buildings if q.id == self.house.id)
        b.footprint = [[math.cos(a) * u - math.sin(a) * v + tx, math.sin(a) * u + math.cos(a) * v + ty]
                       for u, v in b.footprint]
        again, note = ifc_export.frame_of(moved)
        self.assertEqual(note, "")
        u, v = b.footprint[0]
        after = world(again, u, v)
        self.assertAlmostEqual(before[0], after[0], places=6)
        self.assertAlmostEqual(before[1], after[1], places=6)
        b.footprint[0] = [b.footprint[0][0] + 1.0, b.footprint[0][1]]
        self.assertEqual(ifc_export.frame_of(moved), (None, "changed"))


if __name__ == "__main__":
    unittest.main()
