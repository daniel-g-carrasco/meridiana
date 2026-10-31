"""Parking canopies as structures (R281, study 22, 3.7): placed with columns, beams and a roof and no module; the
modules laid after on the slopes; the canopies of format 20 turned into structures by the migration."""
import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

import _setup
from meridiana import canopies, mesh, model, move, session


def corners_z(b, ring):
    return [canopies.roof_at(b.pitches(), x, y) for x, y in ring]


class Structure(unittest.TestCase):
    def test_one_row_is_a_slope_down_to_its_first_side_on_columns_and_beams_with_no_module(self):
        p = model.Project()
        bid = canopies.add(p, canopies.Spec(stalls=4, rows=1, clearance=2.7, tilt=8, turn=30), (10, 5))
        b = p.building(bid)
        self.assertEqual(p.subfields, [])                                   # nothing laid in Modelling
        self.assertEqual((b.roof.type, b.height, b.canopy.bays, b.canopy.rows), ("mono", 2.7, 4, 1))
        zs = corners_z(b, b.footprint)
        self.assertAlmostEqual(min(zs), 2.7)
        self.assertAlmostEqual(max(zs), 2.7 + 5 * math.tan(math.radians(8)))
        self.assertAlmostEqual(b.pitches()[0].azimuth, -30)                 # the first side faces the slope
        parts = canopies.structure(b)
        columns = [s for s in parts if s["kind"] == "column"]
        beams = [s for s in parts if s["kind"] == "beam"]
        self.assertEqual(len(columns), 3)                    # one every two spaces, the ends included
        self.assertEqual(len(beams), 2)                      # the front edge and the line of the columns
        for s in parts:                                      # every box under the roof, never through it
            self.assertLessEqual(s["z1"], min(corners_z(b, s["ring"])) + 1e-9)
            self.assertGreaterEqual(s["z0"], 0.0)
        back = [s for s in beams if s["z1"] > 3.0]
        self.assertEqual(len(back), 1)                       # cantilever: the columns under the high edge
        self.assertAlmostEqual(columns[0]["z1"], back[0]["z0"])

    def test_two_rows_meet_at_a_ridge_and_two_lines_of_columns_stand_at_the_long_edges(self):
        spec = canopies.Spec(stalls=6, rows=2, depth=5, clearance=2.5, tilt=5, pillars="two_rows", columns=4)
        b = canopies.building(spec, (0, 0))
        self.assertEqual(b.roof.type, "gable")
        self.assertEqual(sorted(p.side for p in b.pitches()), [0, 2])
        ridge = canopies.roof_at(b.pitches(), 7.5, 5.0)
        self.assertAlmostEqual(ridge, 2.5 + 5 * math.tan(math.radians(5)))
        self.assertAlmostEqual(canopies.roof_at(b.pitches(), 7.5, 0.0), 2.5)
        self.assertAlmostEqual(canopies.roof_at(b.pitches(), 7.5, 10.0), 2.5)
        columns, beams = canopies.lines(b)
        self.assertEqual(columns, [canopies.COLUMN / 2, 10 - canopies.COLUMN / 2])
        self.assertEqual(len(beams), 3)                      # both edges and the ridge
        self.assertEqual(sum(1 for s in canopies.structure(b) if s["kind"] == "column"), 8)
        cantilever = canopies.building(canopies.Spec(stalls=6, rows=2, tilt=5), (0, 0))
        self.assertEqual(canopies.lines(cantilever)[0], [5.0])     # one line, under the ridge

    def test_the_structure_follows_a_move_and_a_turn_and_is_one_with_the_shadows(self):
        p = model.Project()
        bid = canopies.add(p, canopies.Spec(), (0, 0))
        before = [s["ring"] for s in p.obstacle_prisms() if s["id"] == bid]
        self.assertTrue(before)
        s = session.ProjectSession(p)
        s.edit("Move", move.translate(s.project, "building", bid, 3.0, 4.0))
        after = [s_["ring"] for s_ in s.project.obstacle_prisms() if s_["id"] == bid]
        self.assertAlmostEqual(after[0][0][0], before[0][0][0] + 3.0)
        self.assertAlmostEqual(after[0][0][1], before[0][0][1] + 4.0)
        s.edit("Turn", move.rotate(s.project, "building", bid, 0.0, 0.0, 90.0))
        b = s.project.building(bid)
        self.assertAlmostEqual(b.pitches()[0].azimuth, -90.0)
        self.assertEqual(len([o for o in s.project.obstacle_prisms() if o["kind"] == "column"]), 3)

    def test_the_canopy_round_trips_and_a_copy_has_a_structure_of_its_own(self):
        p = model.Project()
        bid = canopies.add(p, canopies.Spec(rows=2, pillars="two_rows"), (0, 0))
        back = model.Project.from_json(json.loads(json.dumps(p.to_json())))
        self.assertEqual(back.building(bid).canopy, p.building(bid).canopy)
        self.assertIsInstance(back.building(bid).canopy, model.Canopy)
        copy = p.building(p.duplicate("building", bid))
        copy.canopy.bays = 9
        self.assertEqual(p.building(bid).canopy.bays, 4)

    def test_a_damaged_canopy_is_refused_with_its_path(self):
        p = model.Project()
        canopies.add(p, canopies.Spec(), (0, 0))
        for key, value in (("rows", 3), ("pillars", "wall"), ("bays", 0), ("columns", True)):
            data = p.to_json()
            data["buildings"][0]["canopy"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError) as caught:
                model.Project.from_json(data)
            self.assertIn(f"buildings[0].canopy.{key}", str(caught.exception))

    def test_invalid_specs_are_rejected_before_they_reach_the_project(self):
        for values in ({'rows': 3}, {'stalls': 0}, {'clearance': -1}, {'tilt': 90}, {'depth': math.nan},
                       {'pillars': 'x'}, {'columns': -1}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                canopies.building(canopies.Spec(**values), (0, 0))


class Mesh(unittest.TestCase):
    def test_a_canopy_has_no_walls_and_its_roof_is_seen_from_under_too(self):
        b = canopies.building(canopies.Spec(), (0, 0))
        pos, nor, _col = mesh.building_triangles(b.footprint, b.pitches())
        self.assertEqual(len(pos), 12)                        # two triangles, both faces
        self.assertEqual(sorted(np.sign(np.round(nor[:, 1], 6)).tolist()), [-1.0] * 6 + [1.0] * 6)
        self.assertEqual(len(mesh.building_edges(b.footprint, b.pitches())), 4)    # the roof's outline only
        house = model.Building(id="h", name="h", footprint=b.footprint)
        self.assertGreater(len(mesh.building_triangles(house.footprint, house.pitches())[0]), 12)   # walls

    def test_the_report_scene_has_the_columns_and_beams(self):
        p = model.Project()
        canopies.add(p, canopies.Spec(), (0, 0))
        tri, _table, _segs = mesh.project_scene(p, {})
        boxes = len(canopies.structure(p.buildings[0]))
        self.assertEqual(len(tri[0]), 12 + boxes * 10 * 3)    # the roof both ways, each box its top and sides


class Lay(unittest.TestCase):
    def test_on_a_canopy_lays_a_filled_sub_field_on_each_slope_in_one_step(self):
        p = model.Project()
        bid = canopies.add(p, canopies.Spec(stalls=4, rows=2, tilt=10, turn=37), (30, -20))
        s = session.ProjectSession(p)
        ids: list = []
        s.edit("On a canopy", lambda q: ids.extend(canopies.lay(q, bid, portrait=True, gap=0.02, overhang=0.2,
                                                                 edge=0.1)))
        self.assertEqual(len(ids), 2)
        b = s.project.building(bid)
        for sf in s.project.subfields:
            self.assertEqual((sf.building, sf.support, sf.filled), (bid, None, True))
            surface = s.project.surface_of(sf)
            result = s.project.fill(sf)
            self.assertTrue(result.modules)
            pitch = b.pitches()[b.pitch_index(sf.pitch)]
            for pm in result.modules:
                self.assertAlmostEqual(pm.tilt, 10)
                self.assertAlmostEqual(pm.azimuth, pitch.azimuth)
            heights = [surface.z(*q) for q in sf.ring]
            self.assertAlmostEqual(min(heights), 2.7 - 0.2 * math.tan(math.radians(10)), places=5)   # 20 cm beyond
        s.undo.undo()
        self.assertEqual(s.project.subfields, [])
        s.undo.redo()
        again: list = []
        s.edit("Again", lambda q: again.extend(canopies.lay(q, bid, portrait=False)))
        self.assertEqual(len(s.project.subfields), 2)                     # replaced, not added
        self.assertTrue(all(sf.params["portrait"] is False for sf in s.project.subfields))

    def test_moving_the_canopy_takes_its_modules_along(self):
        p = model.Project()
        bid = canopies.add(p, canopies.Spec(), (0, 0))
        canopies.lay(p, bid)
        ring = [list(q) for q in p.subfields[0].ring]
        move.translate(p, "building", bid, 5.0, 0.0)(p)
        self.assertAlmostEqual(p.subfields[0].ring[0][0], ring[0][0] + 5.0)

    def test_values_out_of_range_and_a_building_that_is_no_canopy_are_refused(self):
        p = model.Project()
        p.buildings.append(model.Building(id="b1", name="House", footprint=[[0, 0], [9, 0], [9, 9], [0, 9]]))
        bid = canopies.add(p, canopies.Spec(), (20, 0))
        for args in (("b1",), ("nope",), (bid, True, -1.0), (bid, True, 0.02, 5.0), (bid, True, 0.02, 0.0,
                                                                                           math.nan)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                canopies.lay(p, *args)
        self.assertEqual(p.subfields, [])


class Migration(unittest.TestCase):
    """Decision 8 of study 22: the canopies of format 20 become structures; those changed by hand stay
    sub-fields. The fixture was written by the dialog of format 20 (canopies.fields up to 30/10/2026)."""

    def test_the_canopies_of_format_20_become_structures_and_lay_the_same_modules(self):
        path = _setup.FORMATS / "pensiline-v20.meridiana"
        raw = json.loads(path.read_text(encoding="utf-8"))
        old = model.Project()                                      # the slopes as format 20 laid them
        old.subfields = [model.SubField(**s) for s in raw["variants"][0]["design"]["subfields"]]
        p, notice = model.Project.load(path)
        self.assertEqual(len(notice.splitlines()), 2)              # two canopies made, one slope left
        self.assertEqual([(b.roof.type, b.canopy.rows, b.canopy.pillars) for b in p.buildings],
                         [("mono", 1, "cantilever"), ("gable", 2, "cantilever")])
        self.assertEqual([b.canopy.bays for b in p.buildings], [4, 6])
        self.assertEqual([round(b.height, 6) for b in p.buildings], [2.7, 2.5])
        self.assertEqual([(s.building, s.pitch, s.support is None) for s in p.subfields],
                         [("b1", 0, True), ("b2", 0, True), ("b2", 2, True), (None, None, False)])
        for before, after in zip(old.subfields, p.subfields, strict=True):
            a, b = old.fill(before), p.fill(after)
            self.assertEqual(len(a.modules), len(b.modules), after.id)
            for m, n in zip(a.modules, b.modules, strict=True):
                self.assertAlmostEqual(m.tilt, n.tilt)
                self.assertAlmostEqual((m.azimuth - n.azimuth + 180) % 360 - 180, 0)
        second = next(v for v in p.variants if v["id"] == "v2")["design"]["subfields"]
        self.assertEqual([(s["building"], s["pitch"]) for s in second], [("b1", 0), ("b2", 0), ("b2", 2)])
        self.assertEqual(len(p.buildings), 2)                      # the same canopy in two variants: one

    def test_a_file_saved_in_21_opens_again_the_same(self):
        p, _notice = model.Project.load(_setup.FORMATS / "pensiline-v20.meridiana")
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "p.meridiana"
            p.save(target)
            again, notice = model.Project.load(target)
        self.assertIsNone(notice)
        self.assertEqual(again.buildings, p.buildings)
        self.assertEqual(again.subfields, p.subfields)


class Ifc(unittest.TestCase):
    def test_columns_beams_and_roof_go_to_the_ifc_model_and_no_wall(self):
        try:
            import ifcopenshell
        except ImportError:
            self.skipTest("ifcopenshell missing")
        from _fixtures import RHO, exported
        p = model.Project(site=model.Site(**RHO))
        bid = canopies.add(p, canopies.Spec(stalls=4, rows=2, pillars="two_rows"), (0, 0))
        canopies.lay(p, bid)
        with tempfile.TemporaryDirectory() as folder:
            path, _summary, _results = exported(p, Path(folder), "pensilina.ifc")
            f = ifcopenshell.open(str(path))
            self.assertEqual(len(f.by_type("IfcColumn")), 6)
            self.assertEqual(len(f.by_type("IfcBeam")), 3)
            self.assertEqual(len(f.by_type("IfcWall")), 0)
            self.assertEqual(len(f.by_type("IfcRoof")), 1)
            self.assertEqual(len(f.by_type("IfcSlab")), 2)
            self.assertTrue(f.by_type("IfcSolarDevice"))


if __name__ == "__main__":
    unittest.main()
