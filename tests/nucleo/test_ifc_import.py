"""IFC in (study 20): a project exported and read back with the same outlines, roofs, heights and obstacles, as one undo
step; a model turned by its TrueNorth comes back square to the true north; buildingSMART's public samples read as the
study found them; what is not an IFC file said, never a crash of the reader's caller; the reader in a process of its
own, and the memory of a process it is watched by (procmem.py). They need ifcopenshell (an optional dependency) and say so when it is not there."""

import json
import math
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import _setup
from _fixtures import RHO, exported, mixed

from meridiana import geo, ifc_import, ifc_read, model, procmem

IFC_DATA = _setup.DATA / "ifc"


def need_ifcopenshell():
    if not ifc_read.available():
        raise unittest.SkipTest("ifcopenshell is not installed")


class Memory(unittest.TestCase):
    def test_this_process_holds_some_memory_and_its_peak_is_not_below_it(self):
        now, top = procmem.rss(), procmem.peak()
        self.assertGreater(now, 1 << 20)
        self.assertGreaterEqual(top, now)
        self.assertGreater(procmem.physical(), 1 << 30)
        self.assertLessEqual(procmem.limit(), 8 * procmem.GIB)

    def test_the_memory_of_a_process_counts_its_children_when_asked(self):
        # on Windows a venv's python.exe starts the interpreter as its child: the tree is what holds the memory
        p = subprocess.Popen([sys.executable, "-c", "import time; x = bytearray(150 << 20); time.sleep(30)"])
        self.addCleanup(p.kill)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and (procmem.rss(p.pid, tree=True) or 0) < 150 << 20:
            time.sleep(0.1)
        self.assertGreaterEqual(procmem.rss(p.pid, tree=True), 150 << 20)
        self.assertGreaterEqual(procmem.rss(p.pid, tree=True), procmem.rss(p.pid))


def by_footprint(project: model.Project):
    from shapely.geometry import Polygon
    return {round(Polygon(b.footprint).centroid.x, 1): b for b in project.buildings}


class RoundTrip(unittest.TestCase):
    """Exported, read, placed where the file says: the same buildings within a millimetre."""

    @classmethod
    def setUpClass(cls):
        need_ifcopenshell()
        cls.folder = Path(tempfile.mkdtemp())
        cls.original = mixed()
        cls.path, _s, _r = exported(cls.original, cls.folder)
        cls.found = ifc_read.read(cls.path)
        cls.back = model.Project()
        cls.back.site = model.Site(**RHO)
        cls.plan = ifc_import.plan(cls.found, cls.back, "file")
        ifc_import.apply(cls.back, cls.plan)

    def test_the_outlines_heights_and_roof_types_come_back(self):
        from shapely.geometry import Polygon
        a, b = by_footprint(self.original), by_footprint(self.back)
        self.assertEqual(sorted(a), sorted(b))
        for k, old in a.items():
            new = b[k]
            self.assertEqual(new.name, old.name)
            self.assertLess(Polygon(old.footprint).symmetric_difference(Polygon(new.footprint)).area, 0.01)
            self.assertAlmostEqual(new.height, old.height, places=2)
            self.assertEqual(new.roof.type, old.roof.type)
            self.assertAlmostEqual(new.slope(), old.slope(), places=1)
            self.assertAlmostEqual(new.ridge(), old.ridge(), places=2)
        self.assertEqual(b[20.0].parapet, 0.8)                                 # the shed's parapet walls

        def ends(building):                     # the gable ends by where they are: the outline may start elsewhere
            ring = building.footprint
            return sorted((round((ring[i][0] + ring[(i + 1) % len(ring)][0]) / 2, 2),
                           round((ring[i][1] + ring[(i + 1) % len(ring)][1]) / 2, 2), kind)
                          for i, kind in enumerate(building.sides_kind()))
        self.assertEqual(ends(b[66.0]), ends(a[66.0]))

    def test_the_pitches_come_back_with_their_slope_and_azimuth(self):
        a, b = by_footprint(self.original), by_footprint(self.back)
        for k, old in a.items():
            mine = sorted((round(p.tilt, 1), round(p.azimuth, 1)) for p in old.pitches())
            theirs = sorted((round(p.tilt, 1), round(p.azimuth, 1)) for p in b[k].pitches())
            self.assertEqual(theirs, mine, old.name)

    def test_the_obstacles_come_back_on_their_roofs_with_their_heights_and_the_tree_on_the_ground(self):
        kinds = sorted((e.kind, round(e.height, 2)) for e in self.back.exclusions)
        self.assertEqual(kinds, [("chimney", 1.0), ("plant", 2.2), ("tree", 8.0), ("vent", 0.5)])
        homes = {e.kind: self.back.building(e.building).name if e.building else None for e in self.back.exclusions}
        self.assertEqual(homes, {"chimney": "Casa", "plant": "Capannone", "tree": None, "vent": "Capannone"})

    def test_the_summary_says_what_was_taken_and_that_the_modules_are_left_to_meridiana(self):
        text = "\n".join(self.plan.taken + self.plan.left_out)
        self.assertIn("4 buildings", text)
        self.assertIn("EPSG:32632", text)
        self.assertIn("110 solar modules", text)
        self.assertEqual(self.plan.approximated, [])

    def test_one_undo_step_and_it_is_all_gone(self):
        from meridiana.session import ProjectSession
        session = ProjectSession(model.Project())
        session.project.site = model.Site(**RHO)
        session.edit("Import", lambda p: ifc_import.apply(p, self.plan))
        self.assertEqual(len(session.project.buildings), 4)
        self.assertEqual(len(session.project.exclusions), 4)
        session.undo.undo()
        self.assertEqual(session.project.buildings, [])
        self.assertEqual(session.project.exclusions, [])

    def test_moved_site_and_origin_places_and_a_far_project(self):
        empty = model.Project()                                        # Milan's default site, nothing drawn yet
        place = ifc_import.place_of(self.found)
        self.assertEqual(ifc_import.default_how(place, empty), "site")
        moved = ifc_import.plan(self.found, empty, "site")
        self.assertAlmostEqual(moved.site.lat, RHO["lat"], places=6)
        self.assertEqual(sorted(round(b.footprint[0][0]) for b in moved.buildings),
                         sorted(round(b.footprint[0][0]) for b in self.plan.buildings))
        centred = ifc_import.plan(self.found, empty, "origin")
        xs = [x for b in centred.buildings for x, _y in b.footprint]
        self.assertAlmostEqual(min(xs) + max(xs), 0.0, places=2)


class North(unittest.TestCase):
    """A model turned by 30 degrees with its TrueNorth: the building comes back square to the true north."""

    @classmethod
    def setUpClass(cls):
        need_ifcopenshell()
        import ifcopenshell
        import ifcopenshell.api
        import numpy as np
        f = ifcopenshell.api.run("project.create_file", version="IFC4")
        project = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name="Ruotato")
        ifcopenshell.api.run("unit.assign_unit", f, units=[ifcopenshell.api.run("unit.add_si_unit", f,
                                                                                  unit_type="LENGTHUNIT")])
        model_ctx = ifcopenshell.api.run("context.add_context", f, context_type="Model")
        body = ifcopenshell.api.run("context.add_context", f, context_type="Model", context_identifier="Body",
                                    target_view="MODEL_VIEW", parent=model_ctx)
        ifcopenshell.api.run("georeference.edit_true_north", f, true_north=30.0)
        site = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSite", name="Sito")
        site.RefLatitude, site.RefLongitude = (45, 31, 21, 360000), (9, 1, 48, 0)
        ifcopenshell.api.run("aggregate.assign_object", f, products=[site], relating_object=project)
        building = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Ruotato")
        ifcopenshell.api.run("aggregate.assign_object", f, products=[building], relating_object=site)
        slab = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSlab", name="Copertura",
                                    predefined_type="ROOF")
        ifcopenshell.api.run("spatial.assign_container", f, products=[slab], relating_structure=building)
        rep = ifcopenshell.api.run("geometry.add_slab_representation", f, context=body, depth=0.3,
                                   polyline=[(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)])
        ifcopenshell.api.run("geometry.assign_representation", f, product=slab, representation=rep)
        # the model turned by 30 degrees counter-clockwise, as its TrueNorth says
        a = math.radians(30.0)
        m = np.eye(4)
        m[:2, :2] = [[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]
        m[2, 3] = 7.0
        ifcopenshell.api.run("geometry.edit_object_placement", f, product=slab, matrix=m, is_si=True)
        cls.path = Path(tempfile.mkdtemp()) / "ruotato.ifc"
        f.write(str(cls.path))

    def test_the_turned_building_comes_back_square_to_the_true_north(self):
        found = ifc_read.read(self.path)
        self.assertAlmostEqual(found["true_north"], 30.0, places=6)
        p = model.Project()
        p.site = model.Site(lat=45.5226, lon=9.03)
        plan = ifc_import.plan(found, p, "file")
        b = plan.buildings[0]
        xs, ys = sorted({round(x, 2) for x, _y in b.footprint}), sorted({round(y, 2) for _x, y in b.footprint})
        self.assertEqual(len(xs), 2)
        self.assertEqual(len(ys), 2)
        self.assertAlmostEqual(xs[1] - xs[0], 20.0, places=2)
        self.assertAlmostEqual(ys[1] - ys[0], 10.0, places=2)
        self.assertAlmostEqual(b.height, 7.3, places=2)
        self.assertEqual(b.roof.type, "flat")


class PublicSamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        need_ifcopenshell()

    def test_buildingsmart_architecture_two_planes_of_45_degrees_east_and_west_in_millimetres(self):
        found = ifc_read.read(IFC_DATA / "Building-Architecture.ifc")
        self.assertEqual(found["unit_m"], 0.001)
        self.assertIsNone(found["site"])
        self.assertEqual(found["map"]["crs"], "EPSG:32760")
        [b] = found["buildings"]
        self.assertEqual(b["name"], "Single-family house")                  # the roof hung on the other site, adopted
        p = model.Project()
        plan = ifc_import.plan(found, p, "origin", north="context")
        [house] = plan.buildings
        # not a gable that the skeleton makes again: the eaves are at 1,9 and 3,3 m, the eastern plane notched
        self.assertEqual(house.roof.type, "free")
        self.assertEqual(sorted((round(pt.tilt), round(pt.azimuth)) for pt in house.pitches()), [(45, -90), (45, 90)])
        self.assertEqual(sorted(round(f["eave"], 2) for f in house.roof.free_pitches), [1.9, 3.3])

    def test_its_map_and_its_true_north_disagree_and_the_designer_is_asked(self):
        found = ifc_read.read(IFC_DATA / "Building-Architecture.ifc")
        place = ifc_import.place_of(found)
        self.assertEqual(place.source, "map")
        self.assertTrue(place.disagree())
        self.assertAlmostEqual(place.north_context, 0.0)
        self.assertTrue(any("TrueNorth" in n for n in place.notes))

    def test_a_model_of_the_installations_alone_gives_no_building_and_says_so(self):
        found = ifc_read.read(IFC_DATA / "Building-Hvac.ifc")
        self.assertEqual(found["buildings"], [])
        plan = ifc_import.plan(found, model.Project(), "origin")
        self.assertEqual(plan.buildings, [])
        self.assertTrue(plan.left_out)


class Robustness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        need_ifcopenshell()
        cls.folder = Path(tempfile.mkdtemp())

    def test_a_text_an_empty_file_and_a_missing_one_are_said_not_raised_as_crashes(self):
        text = self.folder / "testo.ifc"
        text.write_text("Questo non è un file IFC.\n" * 20, encoding="utf-8")
        empty = self.folder / "vuoto.ifc"
        empty.write_bytes(b"")
        for path in (text, empty, self.folder / "manca.ifc"):
            with self.assertRaises(ifc_read.IfcError):
                ifc_read.read(path)

    def test_a_placement_that_refers_to_nothing_is_the_origin_not_a_crash(self):
        import numpy as np

        class Point:                                    # a point the file cut short does not have
            Coordinates = None

        class Placement:
            Location, Axis, RefDirection = Point(), None, None

            def is_a(self, kind):
                return kind == "IfcAxis2Placement3D"
        self.assertTrue(np.allclose(ifc_read._axis2(Placement()), np.eye(4)))

    def test_a_file_cut_in_half_is_said_or_read_without_crashing(self):
        data = (IFC_DATA / "Building-Architecture.ifc").read_bytes()
        cut = self.folder / "tagliato.ifc"
        cut.write_bytes(data[: len(data) // 2])
        try:
            found = ifc_read.read(cut)
        except ifc_read.IfcError:
            return
        self.assertIsInstance(found["buildings"], list)

    def test_an_ifczip_is_read_as_the_file_inside_it(self):
        import zipfile
        packed = self.folder / "casa.ifczip"
        with zipfile.ZipFile(packed, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(IFC_DATA / "Building-Architecture.ifc", "Building-Architecture.ifc")
        found = ifc_read.read(packed)
        self.assertTrue(found["lazy"])
        self.assertEqual(len(found["buildings"]), 1)
        self.assertEqual(len(found["buildings"][0]["pitches"]), 2)

    def test_the_simple_way_never_tessellates_and_counts_what_it_left_out(self):
        found = ifc_read.read(IFC_DATA / "Building-Architecture.ifc", mode="simple")
        self.assertEqual(found["counts"].get("skipped", 0), 0)               # every shape of the sample is simple
        self.assertEqual(len(found["buildings"][0]["pitches"]), 2)

    def test_the_mm_eastings_under_a_metre_unit_are_read_as_millimetres(self):
        zone, east, north, _g, _k = geo.to_utm(45.5226, 9.03)
        found = {"true_north": 0.0, "site": None,
                 "map": {"crs": "EPSG:32632", "eastings": east * 1000, "northings": north * 1000, "height": 0.0,
                         "x_axis": [1.0, 0.0], "scale": 1.0, "unit_m": 0.001, "map_unit_m": 1.0}}
        place = ifc_import.place_of(found)
        self.assertAlmostEqual(place.lat, 45.5226, places=6)
        self.assertTrue(any("millimetres" in n for n in place.notes))


class Worker(unittest.TestCase):
    """The reader in a process of its own, as the window runs it."""

    @classmethod
    def setUpClass(cls):
        need_ifcopenshell()

    def run_worker(self, path) -> tuple[int, list]:
        env = {**os.environ, "PYTHONPATH": str(_setup.ROOT / "src")}
        out = subprocess.run([sys.executable, "-m", "meridiana.ifc_worker", str(path)], capture_output=True, text=True,
                             encoding="utf-8", env=env, timeout=120, check=False)
        return out.returncode, [json.loads(line) for line in out.stdout.splitlines() if line.startswith("{")]

    def test_it_tells_its_progress_and_gives_what_it_found(self):
        code, lines = self.run_worker(IFC_DATA / "Building-Architecture.ifc")
        self.assertEqual(code, 0)
        steps = [ln["progress"] for ln in lines if "progress" in ln]
        self.assertEqual(steps, sorted(steps))
        self.assertEqual(steps[-1], 1.0)
        self.assertEqual(len(lines[-1]["result"]["buildings"]), 1)

    def test_a_file_that_is_not_ifc_ends_with_its_reason_and_code_2(self):
        bad = Path(tempfile.mkdtemp()) / "testo.ifc"
        bad.write_text("nothing", encoding="utf-8")
        code, lines = self.run_worker(bad)
        self.assertEqual(code, 2)
        self.assertEqual(lines[-1]["kind"], "file")


if __name__ == "__main__":
    unittest.main()
