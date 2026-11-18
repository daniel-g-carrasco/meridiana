"""Where an imported IFC model goes (R454): moved and turned as one by the placement, its corners taking those of the
buildings already drawn, at coordinates with the warning beyond FAR_KM and the file's own georeferencing proposed
first, replacing a building drawn before (its sub-fields kept on the new roof), beside it or with it; one undo step;
saved and opened again; and the exports in the frame of the imported file still on the architect's model after it was
placed (exported, read again, compared). Models built by the tests, no client's data."""

import math
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401
from _fixtures import capannone, exported

from meridiana import ifc_export, ifc_import, ifc_place, ifc_read, model
from meridiana.session import ProjectSession

HERE = dict(lat=45.52, lon=9.04, address="Rho (MI)")


def found(conversion=None, site_name="Cantiere", lat=45.53, lon=9.05, ring=None):
    """A building 20 x 10 m in a model's world, 8 m high, flat, with its site."""
    ring = ring or [[100.0, 100.0], [120.0, 100.0], [120.0, 110.0], [100.0, 110.0]]
    return {"schema": "IFC4", "application": "Prova", "unit_m": 1.0, "true_north": 0.0, "map": conversion,
            "site": {"lat": lat, "lon": lon, "elevation": 0.0, "name": site_name, "placement": [0.0, 0.0, 0.0]},
            "sites": 1, "address": "", "obstacles": [], "counts": {}, "supports": [], "times": {"total": 1.0},
            "buildings": [{"name": "Palazzetto", "ifc": "x", "ground": 0.0, "source": "roof", "footprint": ring,
                           "pitches": [{"ring": ring, "normal": [0.0, 0.0, 1.0], "point": [110.0, 105.0, 8.0],
                                        "area": 200.0, "holes": 0, "owners": [1]}]}]}


def project_with_shed():
    p = model.Project(name="Prova", site=model.Site(**HERE))
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=9.5))
    p.subfields.append(model.SubField(id="s1", name="Sud", ring=[[2, 2], [18, 2], [18, 8], [2, 8]], building="b1",
                                      params={"tilt": 15.0}))
    return p


def corners(project, ids):
    return sorted((round(x, 3), round(y, 3)) for b in project.buildings if b.id in ids for x, y in b.footprint)


class Arithmetic(unittest.TestCase):
    def setUp(self):
        self.p = project_with_shed()
        self.plan = ifc_import.plan(found(), self.p, "hand", name="Palazzetto", source_name="palazzetto.ifc")
        self.start = ifc_place.start(self.plan)

    def test_the_import_lays_it_at_the_middle_and_the_start_moves_nothing(self):
        self.assertEqual(self.plan.reference["how"], "hand")
        self.assertEqual(ifc_place.middle(self.plan), (0.0, 0.0))
        same = ifc_place.placed(self.plan, self.start)
        self.assertEqual(same.buildings[0].footprint, [[float(x), float(y)] for x, y in self.plan.buildings[0].footprint])

    def test_the_middle_follows_the_pointer_and_turns_about_itself(self):
        pl = ifc_place.follow(self.plan, self.start, (60.0, 30.0))
        self.assertEqual(ifc_place.mapping(pl)(*ifc_place.middle(self.plan)), (60.0, 30.0))
        pl = ifc_place.turned(self.plan, pl, 90.0)
        x, y = ifc_place.mapping(pl)(*ifc_place.middle(self.plan))
        self.assertAlmostEqual(x, 60.0)
        self.assertAlmostEqual(y, 30.0)
        ring = ifc_place.placed(self.plan, pl).buildings[0].footprint
        xs, ys = [q[0] for q in ring], [q[1] for q in ring]
        self.assertAlmostEqual(max(xs) - min(xs), 10.0, places=3)        # 20 x 10 turned by 90 degrees
        self.assertAlmostEqual(max(ys) - min(ys), 20.0, places=3)

    def test_a_corner_takes_the_corner_of_a_building_drawn_then_a_side(self):
        pl = ifc_place.follow(self.plan, self.start, (40.3 + 10.0, 0.2 + 5.0))   # its SW corner 0,3 m from (40, 0)
        rings = [r for k, r in ifc_place.moved(ifc_place.shapes(self.plan), pl) if k == "building"]
        s = ifc_place.snap(self.p, rings, 0.5)
        self.assertEqual(s.kind, "corner")
        self.assertEqual(s.point, (40.0, 0.0))
        self.assertAlmostEqual(s.dx, -0.3, places=6)
        self.assertAlmostEqual(s.dy, -0.2, places=6)
        pl = ifc_place.follow(self.plan, self.start, (40.3 + 10.0, 10.0))      # its west side near the shed's east one
        rings = [r for k, r in ifc_place.moved(ifc_place.shapes(self.plan), pl) if k == "building"]
        s = ifc_place.snap(self.p, rings, 0.5)
        self.assertEqual(s.kind, "side")
        self.assertAlmostEqual(s.dx, -0.3, places=6)
        self.assertAlmostEqual(s.dy, 0.0, places=6)
        self.assertEqual(ifc_place.snap(self.p, rings, 0.1), ifc_place.Snap())

    def test_on_the_shed_it_overlaps_beside_it_does_not(self):
        pl = ifc_place.follow(self.plan, self.start, (20.0, 10.0))
        self.assertEqual(ifc_place.overlaps(self.p, ifc_place.placed(self.plan, pl)), ["b1"])
        side = ifc_place.beside(self.p, self.plan, pl, ["b1"])
        out = ifc_place.placed(self.plan, side)
        self.assertEqual(ifc_place.overlaps(self.p, out), [])
        from shapely.geometry import Polygon
        gap = Polygon(out.buildings[0].footprint).distance(Polygon(self.p.buildings[0].footprint))
        self.assertAlmostEqual(gap, ifc_place.GAP, places=3)
        moved = math.dist(side.at, pl.at)
        self.assertLessEqual(moved, 16.0 + 1e-6)        # the shortest way out: across the 20 m (10 + 1 + ... ), not 40

    def test_replaced_the_shed_goes_and_its_sub_field_stays_on_the_new_roof_in_one_undo(self):
        session = ProjectSession(self.p)
        pl = ifc_place.follow(self.plan, self.start, (10.0, 5.0))
        added = []
        session.edit("Import an IFC model", lambda p: added.extend(ifc_place.apply(p, self.plan, pl, replace=["b1"])))
        p = session.project
        self.assertEqual([b.id for b in p.buildings], added)
        [sf] = p.subfields
        self.assertEqual(sf.building, added[0])
        session.undo.undo()
        self.assertEqual([b.id for b in session.project.buildings], ["b1"])
        self.assertEqual(session.project.subfields[0].building, "b1")

    def test_kept_both_stay_and_the_model_is_one_group_with_its_bases(self):
        two = found()
        two["buildings"].append({**two["buildings"][0], "ifc": "y", "name": "Torre",
                                 "footprint": [[104.0, 102.0], [108.0, 102.0], [108.0, 106.0], [104.0, 106.0]],
                                 "pitches": [{"ring": [[104.0, 102.0], [108.0, 102.0], [108.0, 106.0], [104.0, 106.0]],
                                              "normal": [0.0, 0.0, 1.0], "point": [106.0, 104.0, 12.0], "area": 16.0,
                                              "holes": 0, "owners": [2]}]})
        plan = ifc_import.plan(two, self.p, "hand")
        plan.bases = [{"base": 0.0}, {"base": 8.0}]
        pl = ifc_place.turned(plan, ifc_place.follow(plan, ifc_place.start(plan), (20.0, 10.0)), 30.0)
        ids = ifc_place.apply(self.p, plan, pl)
        self.assertEqual(len(self.p.buildings), 3)
        a, b = (self.p.building(i) for i in ids)
        self.assertTrue(a.group and a.group == b.group)
        self.assertEqual((b.base, b.on), (8.0, a.id))
        self.assertEqual(self.p.resources["ifc_reference"]["buildings"], {ids[0]: 0.0, ids[1]: 0.0})

    def test_coordinates_back_and_forth_and_the_warning_beyond_far_km(self):
        place = ifc_import.place_of(found())
        pl = ifc_place.turned(self.plan, ifc_place.follow(self.plan, self.start, (120.0, -40.0)), 20.0)
        for system in ifc_place.SYSTEMS:
            v = ifc_place.values(self.p, pl, self.plan, system, place)
            back = ifc_place.from_values(self.p, self.plan, pl, system, v["a"], v["b"], v["turn"], place)
            self.assertLess(math.dist(back.at, pl.at), 0.01, system)
            self.assertAlmostEqual(back.turn, pl.turn, places=4)
        self.assertEqual(ifc_place.far(self.plan, pl), "")
        far = ifc_place.from_values(self.p, self.plan, pl, "latlon", 45.62, 9.04, 0.0)
        self.assertIn("km", ifc_place.far(self.plan, far))
        self.assertGreater(ifc_place.distance_km(self.plan, far), ifc_import.FAR_KM)
        with self.assertRaises(ValueError):
            ifc_place.from_values(self.p, self.plan, pl, "latlon", 95.0, 9.0, 0.0)
        with self.assertRaises(ValueError):
            ifc_place.from_values(self.p, self.plan, pl, "utm", 12.0, 5_000_000.0, 0.0)
        with self.assertRaises(ValueError):
            ifc_place.from_values(self.p, self.plan, pl, "local", 2.0e6, 0.0, 0.0)

    def test_the_files_place_is_the_first_proposal_and_lands_where_the_file_says(self):
        conversion = {"crs": "EPSG:32632", "eastings": 503_100.0, "northings": 5_041_000.0, "x_axis": [1.0, 0.0],
                      "map_unit_m": 1.0, "unit_m": 1.0, "height": 0.0, "scale": 1.0}
        f = found(conversion)
        place = ifc_import.place_of(f)
        offer = ifc_place.proposal(self.p, place)
        self.assertEqual((offer["system"], offer["zone"], offer["source"]), ("utm", "32N", "map"))
        self.assertAlmostEqual(offer["a"], 503_100.0, places=2)
        plan = ifc_import.plan(f, self.p, "hand")
        pl = ifc_place.from_values(self.p, plan, ifc_place.start(plan), offer["system"], offer["a"], offer["b"],
                                   offer["turn"], place)
        by_file = ifc_import.plan(f, self.p, "file")
        self.assertLess(max(math.dist(p, q) for p, q in zip(ifc_place.placed(plan, pl).buildings[0].footprint,
                                                             by_file.buildings[0].footprint, strict=True)), 0.01)
        self.assertIsNone(ifc_place.proposal(self.p, ifc_import.place_of(found(site_name="Default"))))

    def test_saved_and_opened_again_it_is_where_it_was_placed(self):
        pl = ifc_place.turned(self.plan, ifc_place.follow(self.plan, self.start, (70.0, 40.0)), -15.0)
        ids = ifc_place.apply(self.p, self.plan, pl)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "posato.meridiana"
            self.p.save(path)
            again, _note = model.Project.load(path)
            import json
            written = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(corners(again, ids), corners(self.p, ids))
        self.assertEqual(again.resources["ifc_reference"]["shift"], self.p.resources["ifc_reference"]["shift"])
        self.assertEqual((written["version"], model.FORMAT_VERSION), (30, 30))      # no new field (29: R523, 30: R374)


class MeridioKnowsIt(unittest.TestCase):
    def test_design_rules_explains_the_place_mode_with_the_programs_numbers(self):
        from meridiana.assistant import design_rules
        [first, *_rest] = design_rules.search("come posiziono il modello IFC importato con le coordinate?")["rules"]
        self.assertEqual(first["id"], "ifc.place")
        for words in ("Esc", "Shift", "UTM", f"{ifc_import.FAR_KM:g} km", "Replace", "Beside", "Ctrl+Z"):
            self.assertIn(words, first["text"])


class ExportsLieOnTheArchitectsModel(unittest.TestCase):
    """The architect's shed with its north turned by 35 degrees and its building 500 m East and 200 m North in its file,
    imported by hand, placed by the mouse 80 m away and turned by 25 degrees: the whole model written again and read back
    has the walls where the architect's are, the plant alone has its modules on the architect's roof, the DXF in the
    file's frame has the outline at the architect's coordinates."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        if importlib.util.find_spec("ifcopenshell") is None:
            raise unittest.SkipTest("ifcopenshell is not installed")
        import ifcopenshell
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        folder = Path(cls.folder.name)
        shed = capannone()
        shed.subfields = []
        source, _s, _r = exported(shed, folder, "architetto.ifc")
        f = ifcopenshell.open(str(source))
        ctx = next(c for c in f.by_type("IfcGeometricRepresentationContext")
                   if not c.is_a("IfcGeometricRepresentationSubContext"))
        a = math.radians(35.0)
        ctx.TrueNorth = f.createIfcDirection((-math.sin(a), math.cos(a)))
        f.by_type("IfcBuilding")[0].ObjectPlacement.RelativePlacement.Location.Coordinates = (500.0, 200.0, 0.0)
        f.write(str(source))
        cls.found = ifc_read.read(source)
        p = project_with_shed()
        plan = ifc_import.plan(cls.found, p, "hand", north="context", source_name=source.name)
        pl = ifc_place.turned(plan, ifc_place.follow(plan, ifc_place.start(plan), (80.0, 60.0)), 25.0)
        cls.ids = ifc_place.apply(p, plan, pl)
        house = p.building(cls.ids[0])
        from shapely.geometry import Polygon
        ring = Polygon(house.footprint).buffer(-1.0, join_style="mitre")
        p.subfields.append(model.SubField(id=p.new_id("s"), name="Tetto", ring=[list(q) for q in ring.exterior.coords[:-1]],
                                          building=house.id, filled=True, params={"tilt": 15.0}))
        cls.project, cls.house = p, house

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_the_frame_maps_the_placed_outline_on_the_architects(self):
        ref, note = ifc_export.frame_of(self.project)
        self.assertEqual(note, "")
        c, s = math.cos(ref["turn"]), math.sin(ref["turn"])
        mine = [(c * x - s * y + ref["move"][0], s * x + c * y + ref["move"][1]) for x, y in self.house.footprint]
        [raw] = self.found["buildings"]
        for q in mine:
            self.assertLess(min(math.dist(q, r) for r in raw["footprint"]), 0.002, q)

    def test_the_whole_model_written_and_read_again_has_the_walls_where_the_architects_are(self):
        path, out, _r = exported(self.project, Path(self.folder.name), "di-nuovo.ifc")
        self.assertEqual(out["frame"], "imported")
        again = ifc_read.read(path)
        [raw] = self.found["buildings"]
        from shapely.geometry import Polygon
        theirs = Polygon(raw["footprint"])
        mine = [b for b in again["buildings"] if Polygon(b["footprint"]).buffer(0).intersection(theirs).area > 1.0]
        self.assertEqual(len(mine), 1)
        self.assertLess(Polygon(mine[0]["footprint"]).symmetric_difference(theirs).area, 0.05)

    def test_the_plant_alone_lies_on_the_architects_roof(self):
        from shapely.geometry import Point, Polygon
        import ifcopenshell
        import ifcopenshell.util.placement
        path, out, _r = exported(self.project, Path(self.folder.name), "impianto.ifc", what="plant")
        self.assertEqual(out["frame"], "imported")
        f = ifcopenshell.open(str(path))
        at = [ifcopenshell.util.placement.get_local_placement(m.ObjectPlacement)[:3, 3] for m in f.by_type("IfcSolarDevice")]
        self.assertGreater(len(at), 4)
        [raw] = self.found["buildings"]
        outline = Polygon(raw["footprint"]).buffer(0.01)
        self.assertTrue(all(outline.contains(Point(float(x), float(y))) for x, y, _z in at))

    def test_the_dxf_in_the_files_frame_has_the_outline_at_the_architects_coordinates(self):
        from meridiana import dxf_export, jobs
        if not dxf_export.available():
            self.skipTest("ezdxf is not installed")
        import ezdxf
        results, _k, _l = jobs.layout_of(self.project)
        path = Path(self.folder.name) / "pianta.dxf"
        dxf_export.export(self.project, results, path, frame="imported", parts=("buildings",))
        outlines = [e for e in ezdxf.readfile(str(path)).modelspace().query("LWPOLYLINE") if e.dxf.layer == "FV-EDIFICI"]
        [raw] = self.found["buildings"]
        near = [o for o in outlines if all(min(math.dist(p[:2], r) for r in raw["footprint"]) < 0.002
                                           for p in o.get_points("xy"))]
        self.assertEqual(len(near), 1)


if __name__ == "__main__":
    unittest.main()
