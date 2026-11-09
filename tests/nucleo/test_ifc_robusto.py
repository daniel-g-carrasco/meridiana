"""The import of BIM models made robust (R14, on a hall whose import went wrong): the project's site never moves by
itself, a template's site is not believed; a roof of several levels comes in as bodies that meet, drawn no higher than its
pitches; what stands under a sloping roof is no obstacle; slabs under the open sky on walls are roofs. Every model here is
built by the test, with the shapes that went wrong and no client's data."""
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401
import numpy as np

from meridiana import geo, ifc_export, ifc_import, ifc_read, mesh, model, roofs
from meridiana.session import ProjectSession

HERE = {"lat": 46.0, "lon": 13.0, "address": "46.00000000, 13.00000000"}


def need_ifcopenshell():
    if not ifc_read.available():
        raise unittest.SkipTest("ifcopenshell is not installed")


def _brep(w, xy, top, thickness=0.3):
    """A slab as a faceted Brep in world metres: `xy` its outline, `top(x, y)` the height of its upper face."""
    upper = [(x, y, top(x, y)) for x, y in xy]
    lower = [(x, y, z - thickness) for x, y, z in upper]
    n = len(xy)
    vertices = upper + lower
    faces = []
    for indices in [list(range(n)), list(range(2 * n - 1, n - 1, -1))] + [
            [i, i + n, (i + 1) % n + n, (i + 1) % n] for i in range(n)]:
        loop = w.f.createIfcPolyLoop([w.point3(*vertices[i]) for i in indices])
        faces.append(w.f.createIfcFace([w.f.createIfcFaceOuterBound(loop, True)]))
    return w.f.createIfcFacetedBrep(w.f.createIfcClosedShell(faces))


def _element(w, level, cls, name, shape, predefined=None, at=(0, 0, 0)):
    e = w.element(cls, name, predefined=predefined) if predefined else w.element(cls, name)
    w.place(e, at, relative=level.ObjectPlacement)
    rep = w.f.createIfcShapeRepresentation(w.ctx_body, "Body", "Brep", [shape])
    e.Representation = w.f.createIfcProductDefinitionShape(None, None, [rep])
    return e


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def hall_model(path, site_name="Default", map_conversion=False):
    """A sports hall as the architects model it: a sloping roof with a steep face beyond its ridge, a raised strip, a low
    wing with a chimney's cap, a beam under the slope, a real chimney through it, a stair tower and a balcony that are
    floors in the model."""
    w = ifc_export.Writer(model.Project(site=model.Site(lat=44.5, lon=7.0)), {})
    w.setup()
    if not map_conversion:
        for m in list(w.f.by_type("IfcMapConversion")):
            w.f.remove(m)
    site = w.f.by_type("IfcSite")[0]
    site.Name = site_name
    site.RefLatitude, site.RefLongitude = (44, 30, 0, 0), (7, 0, 0, 0)
    level = w.element("IfcBuildingStorey", "Terra")
    w.api.run("aggregate.assign_object", w.f, products=[level], relating_object=w.building)
    w.place(level, (0, 0, 0), relative=w.building.ObjectPlacement)
    slope = lambda x, y: 8.0 + 4.0 * y / 30.0                             # noqa: E731
    steep = lambda x, y: 12.0 - (y - 30.0) * math.tan(math.radians(54.0))  # noqa: E731
    items = [
        _element(w, level, "IfcRoof", "Falda", _brep(w, _rect(0, 0, 20, 30), slope)),
        _element(w, level, "IfcRoof", "Falda ripida", _brep(w, _rect(0, 30, 20, 33), steep)),
        _element(w, level, "IfcRoof", "Corpo basso", _brep(w, _rect(0, -10, 20, 0), lambda x, y: 3.5)),
        _element(w, level, "IfcRoof", "Striscia", _brep(w, _rect(8, 5, 12, 28), lambda x, y: 11.75)),
        _element(w, level, "IfcSlab", "Cappello", _brep(w, _rect(2, -5, 3.5, -3.5), lambda x, y: 9.0), "ROOF"),
        # placed at its low end, as Revit places a beam: its high end stands above the roof at the beam's middle
        _element(w, level, "IfcMember", "Trave sotto la falda", _brep(w, [(0, 0), (0.3, 0), (0.3, 28), (0, 28)],
                                                                       lambda x, y: 8.13 + y * 4.0 / 30.0 - 0.5 - 8.0, 0.5),
                 at=(5, 1, 8.0)),
        _element(w, level, "IfcBuildingElementProxy", "Camino", _brep(w, _rect(15, 10, 16, 11), lambda x, y: 13.0, 5.0)),
        _element(w, level, "IfcSlab", "Torre", _brep(w, _rect(24, 5, 30, 11), lambda x, y: 8.0), "FLOOR"),
        _element(w, level, "IfcSlab", "Balcone", _brep(w, _rect(24, 20, 30, 23), lambda x, y: 5.0), "FLOOR"),
    ]
    for ring in (_rect(24, 5, 30, 5.2), _rect(29.8, 5, 30, 11), _rect(24, 10.8, 30, 11), _rect(24, 5, 24.2, 11)):
        items.append(_element(w, level, "IfcWall", "Muro torre", _brep(w, ring, lambda x, y: 8.4, 8.4)))
    w.contain(items, level)
    w.relationships()
    w.f.write(str(path))


class Model(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        need_ifcopenshell()
        folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(folder.cleanup)
        path = Path(folder.name) / "palazzetto.ifc"
        hall_model(path)
        cls.found = json.loads(json.dumps(ifc_read.read(path), default=float))
        cls.project = model.Project(site=model.Site(**HERE))
        cls.plan = ifc_import.plan(cls.found, cls.project, ifc_import.default_how(ifc_import.place_of(cls.found), cls.project))

    def test_a_site_nobody_set_is_not_believed_and_the_project_stays_where_it_is(self):
        place = ifc_import.place_of(self.found)
        self.assertEqual(place.trust, "default")
        self.assertEqual(ifc_import.offers(place, self.project), ("origin",))
        self.assertEqual(ifc_import.default_how(place, self.project), "hand")
        session = ProjectSession(model.Project(site=model.Site(**HERE)))
        session.edit("Import", lambda p: ifc_import.apply(p, self.plan))
        site = session.project.site
        self.assertEqual((site.lat, site.lon, site.address), (HERE["lat"], HERE["lon"], HERE["address"]))

    def test_the_buildings_stand_at_the_middle_of_the_plan(self):
        xs = [x for b in self.plan.buildings for x, _y in b.footprint]
        ys = [y for b in self.plan.buildings for _x, y in b.footprint]
        self.assertLess(abs(min(xs) + max(xs)), 0.2)
        self.assertLess(abs(min(ys) + max(ys)), 0.2)
        moved = ifc_import.plan(self.found, self.project, "origin", at=(100.0, -50.0))
        xs = [x for b in moved.buildings for x, _y in b.footprint]
        self.assertAlmostEqual((min(xs) + max(xs)) / 2, 100.0, delta=0.1)

    def test_an_empty_project_is_not_moved_either(self):
        empty = model.Project()
        before = (empty.site.lat, empty.site.lon)
        place = ifc_import.place_of(self.found)
        self.assertEqual(ifc_import.default_how(place, empty), "hand")
        out = ifc_import.plan(self.found, empty, ifc_import.default_how(place, empty))
        self.assertIsNone(out.site)
        ifc_import.apply(empty, out)
        self.assertEqual((empty.site.lat, empty.site.lon), before)

    def test_the_summary_says_the_template_site_was_not_used(self):
        said = " ".join(self.plan.approximated)
        self.assertIn("Default", said)
        self.assertIn("44", said)

    def test_the_bodies_of_a_model_with_a_long_name_go_by_a_number_and_their_storey(self):
        found = json.loads(json.dumps(self.found))
        for raw in found["buildings"]:
            raw["name"] = "A TOWN SOMEWHERE -              ITS SPORTS HALL"
            raw["storey"] = "XY_+1 - Top floor - As built"
        names = [b.name for b in ifc_import.plan(found, self.project).buildings]
        self.assertGreater(len(names), 1)
        self.assertEqual(len(set(names)), len(names))
        self.assertEqual(names[1], "Body 2, Top floor")
        self.assertEqual(ifc_import._short_storey("Roof plan- As built"), "Roof plan")
        self.assertEqual(ifc_import._short_storey("Ground floor"), "Ground floor")
        self.assertEqual(ifc_import._short_storey(None), "")

    def test_the_walls_are_never_higher_than_the_pitches_of_the_file(self):
        for b in self.plan.buildings:
            pos, _n, _c = mesh.building_triangles(b.footprint, b.pitches())
            top = max(z for p in b.pitches() for _x, _y, z in p.corners_3d())
            self.assertLessEqual(float(pos[:, 1].max()), top + 0.01, b.name)
        self.assertLess(max(float(mesh.building_triangles(b.footprint, b.pitches())[0][:, 1].max())
                            for b in self.plan.buildings), 12.1)

    def test_the_levels_are_bodies_of_their_own(self):
        heights = sorted(round(b.ridge(), 1) for b in self.plan.buildings)
        self.assertEqual(heights, [3.5, 8.0, 11.8, 12.0])
        hall = next(b for b in self.plan.buildings if b.ridge() > 11.9)
        self.assertEqual(hall.roof.type, "free")
        self.assertEqual(len(hall.pitches()), 2)
        strip = next(b for b in self.plan.buildings if b.roof.type == "flat" and b.height > 11)
        self.assertAlmostEqual(strip.height, 11.75, delta=0.01)

    def test_a_small_cap_above_a_low_roof_is_an_obstacle_with_its_height(self):
        wing = next(i for i, b in enumerate(self.plan.buildings) if abs(b.ridge() - 3.5) < 0.05)
        capped = [e for e, host in self.plan.exclusions if host == wing and e.height and e.height > 5]
        self.assertEqual(len(capped), 1)
        self.assertAlmostEqual(capped[0].height, 5.5, delta=0.05)

    def test_a_beam_under_the_slope_is_not_an_obstacle_and_a_chimney_through_it_is(self):
        rows = [o for o in self.found["obstacles"]]
        self.assertFalse([o for o in rows if "Trave" in o["name"]])
        self.assertTrue([o for o in rows if "Camino" in o["name"]])
        self.assertGreaterEqual(self.found["counts"]["under_roof"], 1)

    def test_a_floor_under_the_open_sky_on_walls_is_a_roof_and_a_balcony_is_not(self):
        sources = [b["source"] for b in self.found["buildings"]]
        self.assertIn("terrace", sources)
        tower = next(b for b in self.plan.buildings if abs(b.height - 8.0) < 0.05)
        self.assertEqual(tower.roof.type, "flat")
        self.assertAlmostEqual(tower.parapet, 0.4, delta=0.05)
        self.assertEqual(self.found["counts"].get("balconies"), 1)
        self.assertFalse([b for b in self.plan.buildings if abs(b.height - 5.0) < 0.05])


class Bases(unittest.TestCase):
    """Where each body stands is read and kept, though Building has no base height yet (R352)."""

    def test_a_body_on_a_higher_storey_keeps_its_base_and_is_said(self):
        need_ifcopenshell()
        found = {"site": None, "map": None, "true_north": 0.0, "buildings": [
            {"name": "A", "ifc": "x", "ground": 0.0, "source": "roof", "footprint": _rect(0, 0, 20, 20),
             "pitches": [{"ring": _rect(0, 0, 20, 20), "normal": [0, 0, 1], "point": [5, 5, 10], "area": 400.0, "owners": [1],
                          "base": 0.0, "base_from": "walls"}]},
            {"name": "B", "ifc": "x", "ground": 0.0, "source": "roof", "footprint": _rect(30, 0, 36, 6), "storey": "Primo",
             "pitches": [{"ring": _rect(30, 0, 36, 6), "normal": [0, 0, 1], "point": [33, 3, 8], "area": 36.0, "owners": [2],
                          "base": 4.7, "base_from": "storey"}]}]}
        out = ifc_import.plan(found, model.Project())
        self.assertEqual([x["base"] for x in out.bases], [0.0, 4.7])
        self.assertEqual(out.bases[1]["from"], "storey")
        self.assertEqual(len(out.buildings), 2)
        self.assertTrue([t for t in out.approximated if "4" in t and "base" in t.lower()])

    def test_the_hall_read_from_a_file_knows_the_foot_of_its_walls(self):
        need_ifcopenshell()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "palazzetto.ifc"
            hall_model(path)
            found = json.loads(json.dumps(ifc_read.read(path), default=float))
        tower = next(b for b in found["buildings"] if b["source"] == "terrace")
        self.assertEqual(tower["pitches"][0]["base_from"], "walls")
        self.assertAlmostEqual(tower["pitches"][0]["base"], 0.0, delta=0.01)


def _double_pitch():
    """A building with two free pitches meeting on a ridge that ends on two sides of its outline, turned by 18 degrees and
    rounded to the 0,1 mm, as a drawing is: the ridge's ends lie a hair off the sides. (outline, pitches, a ridge's end)."""
    turn = math.radians(18.0)

    def t(x, y):
        return (round(x * math.cos(turn) - y * math.sin(turn), 4), round(x * math.sin(turn) + y * math.cos(turn), 4))
    footprint = [t(32, 38), t(32, 0), t(0, 0), t(0, 38)]
    steep = roofs.free([t(0, 38), t(32, 38), t(32, 32.4), t(0, 32.4)], 0, 4.1, 54.76)
    gentle = roofs.free([t(32, 32.4), t(32, 0), t(0, 0), t(0, 32.4)], 1, 6.0, 10.3)
    return footprint, [steep, gentle], t(32, 32.4)


class Trust(unittest.TestCase):
    def found(self, name="Cantiere", lat=45.5, lon=9.1, conversion=None):
        return {"site": {"lat": lat, "lon": lon, "name": name, "placement": [0, 0, 0]}, "map": conversion, "true_north": 0.0}

    def test_the_names_of_templates_and_the_zero_are_not_a_place(self):
        for name in ("Default", " default ", "", "Site", "Sito", "Surface"):
            self.assertEqual(ifc_import.place_of(self.found(name)).trust, "default", name)
        self.assertEqual(ifc_import.place_of(self.found("Cantiere", 0.0, 0.0)).trust, "default")

    def test_a_named_site_and_a_map_may_be_proposed_and_only_proposed(self):
        project = model.Project()
        place = ifc_import.place_of(self.found())
        self.assertEqual(place.trust, "site")
        self.assertEqual(ifc_import.offers(place, project), ("origin", "file", "site"))
        self.assertEqual(ifc_import.default_how(place, project), "hand")
        lat, lon = geo.from_utm(32, 500000.0, 5000000.0, False)
        mapped = ifc_import.place_of(self.found("Default", conversion={
            "crs": "EPSG:32632", "eastings": 500000.0, "northings": 5000000.0, "height": 0.0, "x_axis": [1.0, 0.0],
            "scale": 1.0, "unit_m": 1.0, "map_unit_m": 1.0, "description": ""}))
        self.assertEqual(mapped.trust, "map")
        self.assertAlmostEqual(mapped.lat, lat, places=6)
        self.assertEqual(ifc_import.default_how(mapped, project), "hand")

    def test_once_something_is_drawn_the_site_cannot_be_proposed(self):
        project = model.Project()
        project.buildings.append(model.Building(id="b1", name="x", footprint=_rect(0, 0, 5, 5)))
        self.assertEqual(ifc_import.offers(ifc_import.place_of(self.found()), project), ("origin", "file"))

    def test_a_map_conversion_without_coordinates_says_nothing(self):
        place = ifc_import.place_of(self.found("Default", conversion={
            "crs": "EPSG:32632", "eastings": 0.0, "northings": 0.0, "height": 0.0, "x_axis": [1.0, 0.0],
            "scale": 1.0, "unit_m": 1.0, "map_unit_m": 1.0, "description": ""}))
        self.assertEqual(place.trust, "default")

    def test_a_site_moved_by_choice_comes_back_with_the_undo(self):
        found = {"site": {"lat": 45.5, "lon": 9.1, "name": "Cantiere", "placement": [0, 0, 0]}, "map": None,
                 "true_north": 0.0, "buildings": [{"name": "A", "ifc": "x", "ground": 0.0, "source": "roof",
                                                   "footprint": _rect(0, 0, 10, 10),
                                                   "pitches": [{"ring": _rect(0, 0, 10, 10), "normal": [0, 0, 1],
                                                                "point": [5, 5, 6], "area": 100.0, "owners": [1]}]}]}
        session = ProjectSession(model.Project(site=model.Site(**HERE)))
        out = ifc_import.plan(found, session.project, "site")
        session.edit("Import", lambda p: ifc_import.apply(p, out))
        self.assertAlmostEqual(session.project.site.lat, 45.5)
        session.undo.undo()
        self.assertAlmostEqual(session.project.site.lat, HERE["lat"])
        self.assertEqual(session.project.buildings, [])


class Mesh(unittest.TestCase):
    def test_a_steep_pitch_is_not_prolonged_past_its_outline(self):
        # the outline a little off the pitches, as the reader's simplified union is: the 54 degrees pitch prolonged would
        # stand tens of metres high at the far corners
        gentle = roofs.free(_rect(0, 0, 20, 30), 0, 8.0, 7.6)
        steep = roofs.free(_rect(0, 30, 20, 33), 2, 7.87, 54.0)
        footprint = [(0.03, 0.0), (20.0, -0.03), (20.03, 33.0), (0.0, 33.03)]
        pos, _n, _c = mesh.building_triangles(footprint, [gentle, steep])
        self.assertLess(float(pos[:, 1].max()), 12.2)

    def test_a_point_no_pitch_reaches_takes_the_nearest_pitch_at_its_closest_point(self):
        steep = roofs.free(_rect(0, 0, 10, 3), 0, 5.0, 54.0)
        self.assertLessEqual(mesh._roof_z([steep], 5.0, 40.0), max(z for _x, _y, z in steep.corners_3d()) + 1e-6)

    def test_a_ridge_ending_a_hair_off_the_side_leaves_no_sky_under_it(self):
        # R408: the wall ran straight under the ridge and left a triangle open
        footprint, pitches, end = _double_pitch()
        self.assertLess(mesh.wall_gap(footprint, pitches), 0.02)
        pos, _n, _c = mesh.building_triangles(footprint, pitches)
        on_side = np.isclose(pos[:, 0], end[0], atol=1e-3) & np.isclose(pos[:, 2], -end[1], atol=1e-3)
        self.assertAlmostEqual(float(pos[on_side, 1].max()), max(p.z(*end) for p in pitches), delta=0.02)

    def test_a_side_crossing_a_pitch_edge_with_no_corner_near_also_closes(self):
        # a ridge that runs out past the outline: the side is crossed between the pitch's corners
        footprint = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
        low = roofs.free([(-1.0, -1.0), (11.0, -1.0), (11.0, 5.0), (-1.0, 5.0)], 0, 3.0, 30.0)
        high = roofs.free([(-1.0, 5.0), (11.0, 5.0), (11.0, 11.0), (-1.0, 11.0)], 2, 3.0, 30.0)
        self.assertLess(mesh.wall_gap(footprint, [low, high]), 0.02)

    def test_the_gap_is_measured_where_a_wall_really_stops_short(self):
        # the check itself: the same drawing, the wall made straight under the ridge as it was before R408, shows the hole
        footprint, pitches, _end = _double_pitch()
        with mock.patch.object(mesh, "_roof_stops", return_value=[]):
            self.assertGreater(mesh.wall_gap(footprint, pitches), 5.0)
        pitches = [roofs.flat(_rect(0, 0, 10, 10), 6.0)[0]]
        self.assertEqual(mesh.wall_gap(_rect(0, 0, 10, 10), pitches), 0.0)
        self.assertEqual(mesh.wall_gap(_rect(0, 0, 10, 10), []), 0.0)

    def test_a_step_between_two_pitches_is_closed_by_a_wall(self):
        low = roofs.flat(_rect(0, 0, 10, 10), 3.0)[0]
        high = roofs.flat(_rect(10, 0, 20, 10), 8.0)[0]
        bands = mesh.step_walls([low, high])
        self.assertEqual(len(bands), 1)
        a, b, low0, low1, top0, top1, nx, _ny = bands[0]
        self.assertEqual((low0, low1, top0, top1), (3.0, 3.0, 8.0, 8.0))
        self.assertEqual(nx, -1.0)              # facing the lower roof
        pos, _n, _c = mesh.building_triangles(_rect(0, 0, 20, 10), [low, high])
        foot_of_step = np.isclose(pos, [10.0, 3.0, 0.0]).all(axis=1)      # (x, z, -y): the band starts on the lower roof
        self.assertTrue(foot_of_step.any())
        self.assertAlmostEqual(float(pos[np.isclose(pos[:, 0], 10.0), 1].max()), 8.0)

    def test_a_cut_of_a_centimetre_between_them_does_not_open_the_step(self):
        low = roofs.flat(_rect(0, 0, 9.99, 10), 3.0)[0]
        high = roofs.flat(_rect(10, 0, 20, 10), 8.0)[0]
        self.assertEqual(len(mesh.step_walls([low, high])), 1)

    def test_pitches_that_meet_have_no_step(self):
        for found in (roofs.gable(_rect(0, 0, 12, 8), 6.0, 30.0), roofs.hip(_rect(0, 0, 15, 10), 7.0, 25.0)):
            self.assertEqual(mesh.step_walls(found), [])


class Curves(unittest.TestCase):
    """A slab of a stair tower with rounded corners: Revit's arcs read directly, so that its extent is not lost."""

    def test_an_arc_through_three_points_goes_through_the_middle_one(self):
        pts = ifc_read._arc_through((1.0, 0.0), (0.0, 1.0), (-1.0, 0.0))
        self.assertGreater(max(y for _x, y in pts), 0.99)
        self.assertEqual(pts[0], (1.0, 0.0))
        self.assertEqual(pts[-1], (-1.0, 0.0))
        for x, y in pts:
            self.assertAlmostEqual(math.hypot(x, y), 1.0, places=6)

    def test_a_circle_trimmed_by_degrees_and_a_composite_curve(self):
        need_ifcopenshell()
        import ifcopenshell
        f = ifcopenshell.file(schema="IFC2X3")
        degree = f.createIfcConversionBasedUnit(f.createIfcDimensionalExponents(0, 0, 0, 0, 0, 0, 0), "PLANEANGLEUNIT",
                                                "DEGREE", f.createIfcMeasureWithUnit(
                                                    f.create_entity("IfcPlaneAngleMeasure", math.pi / 180.0),
                                                    f.createIfcSIUnit(None, "PLANEANGLEUNIT", None, "RADIAN")))
        self.assertIsNotNone(degree)
        origin = f.createIfcCartesianPoint((0.0, 0.0))
        circle = f.createIfcCircle(f.createIfcAxis2Placement2D(origin, None), 2.0)
        arc = f.createIfcTrimmedCurve(circle, (f.create_entity("IfcParameterValue", 0.0),),
                                      (f.create_entity("IfcParameterValue", 90.0),), True, "PARAMETER")
        pts = ifc_read._segment_points(arc)
        self.assertAlmostEqual(pts[0][0], 2.0)
        self.assertAlmostEqual(pts[-1][1], 2.0)
        self.assertGreater(len(pts), 3)
        back = f.createIfcPolyline([f.createIfcCartesianPoint((0.0, 2.0)), f.createIfcCartesianPoint((0.0, 0.0)),
                                    f.createIfcCartesianPoint((2.0, 0.0))])
        whole = f.createIfcCompositeCurve([f.createIfcCompositeCurveSegment("CONTINUOUS", True, arc),
                                           f.createIfcCompositeCurveSegment("CONTINUOUS", True, back)], False)
        ring = ifc_read._curve_points(whole)
        area = 0.5 * abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1], strict=True)))
        self.assertAlmostEqual(area, math.pi, delta=0.05)


class FineRoof(unittest.TestCase):
    def test_a_roof_modelled_tile_by_tile_gives_its_planes_in_a_moment(self):
        # a plane of 40 x 40 m in small faces and a big face above it: more faces than are looked at
        faces, owners = [], []
        for i in range(160):
            for j in range(160):
                x, y = i * 0.25, j * 0.25
                faces.append(np.array([(x, y, 5.0), (x + 0.25, y, 5.0), (x + 0.25, y + 0.25, 5.0), (x, y + 0.25, 5.0)]))
                owners.append(1)
        faces.append(np.array([(100.0, 0.0, 9.0), (120.0, 0.0, 9.0), (120.0, 20.0, 9.0), (100.0, 20.0, 9.0)]))
        owners.append(2)
        with mock.patch.object(ifc_read, "MAX_ROOF_FACES", 10000):
            planes, left = ifc_read.roof_planes(faces, owners)
        self.assertEqual(left["fine_faces"], len(faces) - 10000)
        self.assertEqual(len([p for p in planes if abs(p["point"][2] - 9.0) < 0.01]), 1)
        self.assertTrue([p for p in planes if abs(p["point"][2] - 5.0) < 0.01])

    def test_past_its_time_the_reading_still_answers_with_what_it_has(self):
        faces = [np.array([(0.0, 0.0, 5.0), (10.0, 0.0, 5.0), (10.0, 10.0, 5.0), (0.0, 10.0, 5.0)]),
                 np.array([(5.0, 5.0, 8.0), (15.0, 5.0, 8.0), (15.0, 15.0, 8.0), (5.0, 15.0, 8.0)])]
        planes, left = ifc_read.roof_planes(faces, [1, 2], deadline=0.0)
        self.assertEqual(left["uncut"], 2)
        self.assertEqual(len(planes), 2)


class Rise(unittest.TestCase):
    def test_how_far_points_rise_above_the_roof_under_each_of_them(self):
        from shapely.geometry import Polygon
        pitch = {"normal": [0.0, -math.sin(math.radians(10)), math.cos(math.radians(10))], "point": [0, 0, 5.0]}
        shape = Polygon(_rect(-10, -10, 10, 10))
        slope = math.tan(math.radians(10))
        under = np.array([(0.0, y, 5.0 + y * slope - 0.2) for y in (-9.0, 0.0, 9.0)])
        self.assertAlmostEqual(ifc_read._rise(under, [(shape, pitch)]), -0.2, places=6)
        through = np.vstack([under, (0.0, 0.0, 6.5)])
        self.assertAlmostEqual(ifc_read._rise(through, [(shape, pitch)]), 1.5, places=6)
        self.assertIsNone(ifc_read._rise(np.array([(50.0, 50.0, 1.0)]), [(shape, pitch)]))


if __name__ == "__main__":
    unittest.main()
