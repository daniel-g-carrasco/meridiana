"""Beyond the 2,5D model (study 37, format 28): a building standing at a base height (R453), a plant room on a roof
(R352), the bodies of one building (R440), a flat roof tilted on an inclined plane that stays flat (R455, R411), the
saddle-backed bands (R455). Old projects write as they were: the new fields only when they hold.

    python -m unittest nucleo.test_solids
"""
import json
import unittest

from meridiana import model, move, roofs
from meridiana import roof_vertices as rv
from meridiana.energy import system


def rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def shed(**kw) -> model.Project:
    p = model.Project(name="Solids")
    p.site = model.Site(lat=45.52, lon=9.04)
    p.buildings.append(model.Building("b1", "Capannone", rect(0, 0, 40, 20), 8.0, **kw))
    return p


class BaseHeight(unittest.TestCase):
    """R453: the walls start at the base, the shadows' solid and the 3D with them; heights stay from the ground."""

    def test_a_building_on_the_ground_writes_nothing_new(self):
        p = shed()
        raw = p.to_json()["buildings"][0]
        for key in ("base", "on", "part_of"):
            self.assertNotIn(key, raw)
        self.assertNotIn("plane", raw["roof"])
        self.assertNotIn("saddles", raw["roof"])
        self.assertEqual(p.to_json()["version"], model.FORMAT_VERSION)     # 28 the solids, 29 R523

    def test_the_base_is_written_read_and_checked(self):
        p = shed(base=4.0)
        raw = p.to_json()
        self.assertEqual(raw["buildings"][0]["base"], 4.0)
        again = model.Project.from_json(json.loads(json.dumps(raw)))
        self.assertEqual(again.buildings[0].base, 4.0)
        raw["buildings"][0]["base"] = -1.0
        with self.assertRaises(ValueError) as caught:
            model.Project.from_json(raw)
        self.assertIn("buildings[0].base", str(caught.exception))

    def test_the_shadow_solid_and_the_3d_walls_start_at_the_base(self):
        from meridiana import mesh
        p = shed(base=4.0)
        b = p.buildings[0]
        p.buildings.append(model.Building("b2", "Altro", rect(60, 0, 80, 20), 6.0))
        p.subfields.append(model.SubField("s1", "Campo", rect(61, 1, 79, 19), building="b2"))
        solids = system.obstacles_of(p, p.subfields[0])
        zs = [z for s in solids if s.name == "Capannone" for (_x, _y, z) in s.points] if hasattr(solids[0], "points") else None
        if zs is not None:
            self.assertAlmostEqual(min(zs), 4.0)
        pos, _nor, _col = mesh.building_triangles(b.footprint, b.pitches(), base=b.base)
        self.assertAlmostEqual(float(pos[:, 1].min()), 4.0)     # Qt axes: y is up
        edges = mesh.building_edges(b.footprint, b.pitches(), b.base)
        self.assertAlmostEqual(float(edges[:, :, 1].min()), 4.0)
        self.assertNotEqual(b.geometry_key(), model.Building("b1", "Capannone", rect(0, 0, 40, 20), 8.0).geometry_key())

    def test_the_geometry_key_of_a_building_on_the_ground_is_as_before(self):
        a = model.Building("b1", "A", rect(0, 0, 40, 20), 8.0)
        key = json.loads(a.geometry_key())
        self.assertNotIn("base", key)
        self.assertNotIn("plane", key["roof"])
        self.assertNotIn("saddles", key["roof"])


class PlantRoom(unittest.TestCase):
    """R352: a building standing on another: it moves with it, its outline keeps the host's modules off."""

    def room(self) -> model.Project:
        p = shed()
        p.subfields.append(model.SubField("s1", "Campo", rect(1, 1, 39, 19), building="b1", params={"tilt": 10.0}))
        p.buildings.append(model.Building("b2", "Locale tecnico", rect(10, 5, 16, 10), 11.0, base=8.0, on="b1"))
        return p

    def test_it_keeps_the_modules_off_its_outline_and_the_layout_key_sees_it(self):
        p = self.room()
        sf = p.subfields[0]
        kinds = [e.kind for e in p.exclusions_of(sf)]
        self.assertEqual(kinds, ["other"])
        self.assertEqual(p.standing_on("b1"), [p.buildings[1]])
        key = p.layout_key(sf)
        p.buildings[1].footprint = rect(10, 5, 20, 10)
        self.assertNotEqual(p.layout_key(sf), key)
        p.buildings[1].on = ""
        self.assertEqual(p.exclusions_of(sf), [])
        self.assertEqual(p.standing_on("b1"), [])

    def test_it_moves_with_its_host_and_shades_it_from_its_base(self):
        p = self.room()
        self.assertEqual(move.members(p, "b1"), ["b1", "b2"])
        self.assertEqual(move.members(p, "b2"), ["b2"])
        solids = system.obstacles_of(p, p.subfields[0])
        self.assertTrue(solids)

    def test_a_plant_room_drawn_from_an_outline_takes_the_roof_height(self):
        p = shed()
        b = p.buildings[0]
        self.assertEqual(max(model.roof_z(b, rect(10, 5, 16, 10))), 8.0)


class OneBuilding(unittest.TestCase):
    """R440: the bodies of one building, one name, one entry; the geometries their own."""

    def test_the_whole_its_parts_and_the_names(self):
        p = shed()
        p.buildings.append(model.Building("b2", "Corpo 2", rect(40, 0, 60, 20), 6.0, part_of="b1", group="ifc1"))
        p.buildings.append(model.Building("b3", "Corpo 3", rect(60, 0, 70, 20), 6.0, part_of="b1", group="ifc1"))
        self.assertIs(p.whole_of(p.buildings[1]), p.buildings[0])
        self.assertEqual([x.id for x in p.parts_of("b1")], ["b2", "b3"])
        self.assertEqual([(w.id, [x.id for x in parts]) for w, parts in p.wholes()], [("b1", ["b2", "b3"])])
        self.assertEqual(p.shown_name(p.buildings[2]), "Capannone (body 3)")
        self.assertEqual(p.shown_name(p.buildings[0]), "Capannone")
        self.assertEqual(move.members(p, "b3"), ["b3", "b2", "b1"])
        self.assertEqual(p.to_json()["buildings"][1]["part_of"], "b1")
        p.buildings.pop(0)                      # the whole gone: the bodies stand alone
        self.assertIs(p.whole_of(p.buildings[0]), p.buildings[0])
        self.assertEqual(len(p.wholes()), 2)


class InclinedFlatRoof(unittest.TestCase):
    """R455: a flat roof on an inclined plane is still a flat roof."""

    def test_the_plane_is_one_pitch_and_the_height_its_lowest_corner(self):
        p = shed()
        b = p.buildings[0]
        rv.set_height(p, "b1", rv.handles(b)[2].corners[0], 9.0)
        self.assertEqual(b.roof.type, "flat")
        self.assertEqual(b.height, 8.0)
        self.assertEqual(len(b.roof.plane), 4)
        pitch = b.pitches()[0]
        self.assertEqual(len(b.pitches()), 1)
        self.assertGreater(pitch.tilt, 0)
        self.assertAlmostEqual(pitch.z(40, 20), 9.0, places=3)
        self.assertAlmostEqual(pitch.z(0, 0), 8.0, places=3)
        self.assertAlmostEqual(b.ridge(), 9.0, places=3)
        self.assertAlmostEqual(b.wall_top(), 8.0, places=3)
        raw = p.to_json()["buildings"][0]["roof"]
        self.assertEqual(len(raw["plane"]), 4)
        again = model.Project.from_json(json.loads(json.dumps(p.to_json())))
        self.assertEqual(again.buildings[0].roof.plane, b.roof.plane)

    def test_the_eave_written_moves_the_whole_plane_and_level_again_forgets_it(self):
        p = shed()
        b = p.buildings[0]
        rv.set_height(p, "b1", rv.handles(b)[2].corners[0], 9.0)
        changes = b.eave_written(10.0)
        self.assertEqual(changes["height"], 10.0)
        self.assertEqual([round(z, 2) for z in changes["roof.plane"]], [10.0, 10.5, 11.0, 10.5])
        rv.set_heights(p, "b1", [(h.corners[0], 8.0) for h in rv.handles(b)])
        self.assertIsNone(b.roof.plane)
        self.assertEqual(b.height, 8.0)

    def test_a_corner_under_the_base_is_refused_and_a_changed_outline_levels_it(self):
        p = shed(base=5.0)
        b = p.buildings[0]
        with self.assertRaises(ValueError):
            rv.set_height(p, "b1", rv.handles(b)[2].corners[0], 4.0)
        self.assertIsNone(b.roof.plane)
        rv.set_height(p, "b1", rv.handles(b)[2].corners[0], 9.0)
        b.footprint = [[0, 0], [40, 0], [40, 20], [20, 25], [0, 20]]
        self.assertIsNone(b.plane())                      # five corners, four heights: level until moved again
        self.assertEqual(b.pitches()[0].tilt, 0.0)
        raw = p.to_json()
        with self.assertRaises(ValueError):
            model.Project.from_json(raw)                  # the file says so too

    def test_the_parapet_follows_the_plane(self):
        p = shed(parapet=1.0)
        b = p.buildings[0]
        rv.set_height(p, "b1", rv.handles(b)[2].corners[0], 9.0)
        prisms = [o for o in p.obstacle_prisms() if o["kind"] == "parapet"]
        self.assertEqual(len(prisms), 4)
        self.assertGreater(max(o["z1"] for o in prisms), 9.5)
        self.assertLess(min(o["z0"] for o in prisms), 8.1)


class SaddleRoof(unittest.TestCase):
    """R455: parallel bands, two pitches each, level channels between them."""

    def test_bands_and_channels_across_a_shed(self):
        spec = {"direction": 90.0, "band": 2.5, "tilt": 10.0, "channel": 0.5, "depth": 0.1}
        found = roofs.saddles(rect(0, 0, 30, 12), 8.0, spec)
        bands = [p for p in found if p.tilt > 0]
        channels = [p for p in found if p.tilt == 0]
        self.assertEqual(len(bands), 8)                   # 4 bands of 2,5 m across 12 m
        self.assertEqual(len(channels), 4)
        self.assertEqual({round(p.azimuth) for p in bands}, {0, 180})       # facing south and north
        self.assertEqual({p.z0 for p in bands}, {8.0})
        drop = 1.25 * __import__("math").tan(__import__("math").radians(10.0))
        self.assertAlmostEqual(channels[0].z0, 8.0 - drop - 0.1, places=6)
        edge = min(z for p in bands for _x, _y, z in p.corners_3d())
        self.assertAlmostEqual(edge, 8.0 - drop, places=3)
        area = sum(__import__("shapely").geometry.Polygon(p.ring).area for p in found)
        self.assertAlmostEqual(area, 360.0, places=3)     # the whole roof, once

    def test_as_a_roof_type_with_its_defaults_and_in_the_file(self):
        p = shed(roof=model.Roof(type="saddles"))
        b = p.buildings[0]
        self.assertGreater(len(b.pitches()), 4)
        self.assertLess(b.wall_top(), 8.0)
        self.assertEqual(b.ridge(), 8.0)
        changes = model.Building("b9", "X", rect(0, 0, 30, 12), 8.0).retyped("saddles")
        self.assertEqual(changes["roof.saddles"]["direction"], 90.0)        # along the longest side
        raw = p.to_json()
        self.assertEqual(raw["buildings"][0]["roof"]["type"], "saddles")
        again = model.Project.from_json(json.loads(json.dumps(raw)))
        self.assertEqual(len(again.buildings[0].pitches()), len(b.pitches()))
        raw["buildings"][0]["roof"]["saddles"] = {"band": "wide"}
        with self.assertRaises(ValueError):
            model.Project.from_json(raw)

    def test_a_sub_field_on_a_band_lays_modules_on_its_slope(self):
        p = shed(roof=model.Roof(type="saddles", saddles={"direction": 90.0, "band": 8.0, "tilt": 8.0, "channel": 0.6}))
        b = p.buildings[0]
        band = next(i for i, q in enumerate(b.pitches()) if q.tilt > 0)
        ring = [list(q) for q in b.pitches()[band].ring]
        p.subfields.append(model.SubField("s1", "Fascia", ring, building="b1", pitch=band,
                                          params=model.new_params("coplanar")))
        surf = p.surface_of(p.subfields[0])
        self.assertAlmostEqual(surf.tilt, 8.0, places=3)
        result = p.fill(p.subfields[0])
        self.assertGreater(len(result.modules), 5)


class Exports(unittest.TestCase):
    """The base in the exports: the IFC walls stand from it, the DXF says it; the import reads it."""

    def test_the_ifc_import_gives_a_raised_body_its_base_and_the_body_under_it(self):
        from meridiana import ifc_import
        plan = ifc_import.Plan()
        plan.buildings = [model.Building("", "Corpo 1", rect(0, 0, 40, 20), 8.0),
                          model.Building("", "Corpo 2", rect(10, 5, 30, 10), 11.0),
                          model.Building("", "Corpo 3", rect(60, 0, 70, 10), 4.0)]
        plan.bases = [{"base": 0.02, "from": "walls", "storey": ""}, {"base": 8.0, "from": "walls", "storey": ""},
                      {"base": None, "from": "", "storey": ""}]
        p = model.Project(name="IFC")
        ids = ifc_import.apply(p, plan)
        self.assertEqual(len(ids), 3)
        a, b, c = p.buildings
        self.assertEqual((a.base, a.on), (0.0, ""))
        self.assertEqual((b.base, b.on), (8.0, a.id))
        self.assertEqual((c.base, c.on), (0.0, ""))
        self.assertTrue(all(x.group == "ifc1" for x in p.buildings))
        self.assertEqual(move.members(p, a.id)[:2], [a.id, b.id])

    def test_the_ifc_walls_stand_from_the_base(self):
        import tempfile
        from pathlib import Path
        try:
            import ifcopenshell
            from ifcopenshell import geom
        except ImportError:
            self.skipTest("no ifcopenshell")
        from _fixtures import exported
        p = shed(base=4.0)
        with tempfile.TemporaryDirectory() as folder:
            path, _summary, _results = exported(p, Path(folder), "base.ifc")
            f = ifcopenshell.open(str(path))
            walls = [w for w in f.by_type("IfcWall") if w.PredefinedType == "SOLIDWALL"]
            self.assertEqual(len(walls), 4)
            settings = geom.settings()
            settings.set(settings.USE_WORLD_COORDS, True)
            lows = []
            for w in walls:
                shape = geom.create_shape(settings, w)
                verts = shape.geometry.verts
                lows.append(min(verts[2::3]))
            self.assertTrue(all(abs(z - 4.0) < 0.05 for z in lows), lows)

    def test_the_dxf_says_the_base(self):
        import tempfile
        from pathlib import Path
        from meridiana import dxf_export
        if not dxf_export.available():
            self.skipTest("no ezdxf")
        p = shed(base=4.0)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "base.dxf"
            dxf_export.export(p, {}, path)
            text = path.read_text(encoding="utf-8", errors="replace")
            self.assertIn("4", text)
            self.assertTrue("from 4" in text or "da quota 4" in text, "the base beside the height")


if __name__ == "__main__":
    unittest.main()
