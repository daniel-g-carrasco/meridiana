"""The roof drawn by hand as one surface (roof_join.py, R304) and a pitch out of plane folded (R303): the planes that meet
on the drawn lines, the eaves and the flats kept, the cases that join nothing, the format and the keys."""

import copy
import json
import math
import unittest

import _setup  # noqa: F401

from meridiana import model, roof_join, roofs
from meridiana.energy import system


def rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def pitch(ring, side, eave, tilt, **more):
    return {"ring": ring, "eave_side": side, "eave": eave, "tilt": tilt, **more}


def corners(p):
    return {(round(x, 3), round(y, 3)): z for x, y, z in p.corners_3d()}


def assert_continuous(test, found, rings):
    """Every shared line has one height at both its ends, whichever pitch says it."""
    for p, q, a, b in roof_join.shared_lines([[tuple(c) for c in r] for r in rings]):
        for point in (a, b):
            test.assertAlmostEqual(found[p].z(*point), found[q].z(*point), places=4, msg=f"{p}/{q} at {point}")


TWO_GABLE = [pitch(rect(0, 0, 20, 5), 0, 6.0, 20.0), pitch(rect(0, 5, 20, 10), 2, 6.0, 20.0)]


class Gable(unittest.TestCase):
    def test_two_pitches_that_already_meet_are_left_exactly_as_they_are(self):
        found = roof_join.resolve(TWO_GABLE).pitches
        alone = [roofs.free(f["ring"], f["eave_side"], f["eave"], f["tilt"]) for f in TWO_GABLE]
        for got, was in zip(found, alone, strict=True):
            self.assertEqual((got.tilt, got.azimuth, got.z0), (was.tilt, was.azimuth, was.z0))
        self.assertEqual(roof_join.resolve(TWO_GABLE).moved, [])

    def test_two_slopes_that_do_not_meet_get_a_common_ridge_on_the_drawn_line_with_the_eaves_kept(self):
        rings = [rect(0, 0, 20, 5), rect(0, 5, 20, 10)]
        free = [pitch(rings[0], 0, 6.0, 15.0), pitch(rings[1], 2, 6.0, 30.0)]
        solved = roof_join.resolve(free)
        low, high = solved.pitches
        assert_continuous(self, solved.pitches, rings)
        ridge = low.z(0, 5)
        self.assertGreater(ridge, 6.0 + 5 * math.tan(math.radians(15.0)))
        self.assertLess(ridge, 6.0 + 5 * math.tan(math.radians(30.0)))
        self.assertAlmostEqual(low.z(0, 0), 6.0, places=3)
        self.assertAlmostEqual(high.z(20, 10), 6.0, places=3)
        self.assertAlmostEqual(low.tilt, high.tilt, places=2)          # equal runs and equal eaves: one slope
        self.assertEqual(solved.moved, [0, 1])

    def test_a_valley_is_found_as_a_ridge_is(self):
        rings = [rect(0, 0, 20, 5), rect(0, 5, 20, 10)]
        free = [pitch(rings[0], 2, 6.0, 10.0), pitch(rings[1], 0, 6.0, 10.0)]     # both go down to the middle
        found = roof_join.resolve(free).pitches
        assert_continuous(self, found, rings)
        self.assertAlmostEqual(found[0].z(3, 5), 6.0)
        self.assertGreater(found[0].z(3, 0), 6.0)

    def test_the_sides_of_the_plane_keep_the_way_water_runs(self):
        made = roofs.free(rect(0, 0, 10, 8), 3, 5.0, 25.0)
        again = roof_join.pitch_of_plane(made.ring, roof_join._plane_of(made))
        self.assertAlmostEqual(again.tilt, made.tilt)
        self.assertAlmostEqual(again.azimuth % 360.0, made.azimuth % 360.0, places=3)
        self.assertAlmostEqual(again.z(7, 3), made.z(7, 3))


class Three(unittest.TestCase):
    """Daniel's case: a building in three, one monopitch and two flats."""

    RINGS = (rect(0, 0, 10, 10), rect(10, 0, 20, 10), rect(20, 0, 30, 10))

    def test_the_flat_stays_flat_and_is_lifted_to_the_top_of_the_slope(self):
        a, b, c = self.RINGS
        free = [pitch(a, 0, 6.0, 0.0), pitch(b, 3, 6.0, 10.0), pitch(c, 0, 6.0, 0.0)]      # b goes down to a
        solved = roof_join.resolve(free)
        one, two, three = solved.pitches
        assert_continuous(self, solved.pitches, self.RINGS)
        top = 6.0 + 10 * math.tan(math.radians(10.0))
        self.assertEqual((one.tilt, three.tilt), (0.0, 0.0))
        self.assertAlmostEqual(one.z0, 6.0, places=2)
        self.assertAlmostEqual(two.tilt, 10.0, places=2)                                   # the slope as written
        self.assertAlmostEqual(three.z0, top, places=2)
        self.assertEqual(solved.moved, [2])

    def test_a_slope_with_its_eave_outside_lifts_what_stands_at_its_top(self):
        a, b, c = self.RINGS
        free = [pitch(a, 3, 6.0, 15.0), pitch(b, 0, 6.0, 0.0), pitch(c, 0, 6.0, 0.0)]      # a goes down outwards
        solved = roof_join.resolve(free)
        assert_continuous(self, solved.pitches, self.RINGS)
        self.assertAlmostEqual(solved.pitches[0].z(0, 5), 6.0, places=3)                   # the eave stays
        top = 6.0 + 10 * math.tan(math.radians(15.0))
        self.assertAlmostEqual(solved.pitches[1].z0, top, places=2)
        self.assertAlmostEqual(solved.pitches[2].z0, top, places=2)


class Degenerate(unittest.TestCase):
    def test_pitches_apart_or_touching_at_a_point_are_not_neighbours(self):
        for rings in ([rect(0, 0, 10, 10), rect(20, 0, 30, 10)], [rect(0, 0, 10, 10), rect(10, 10, 20, 20)]):
            free = [pitch(rings[0], 0, 6.0, 20.0), pitch(rings[1], 0, 9.0, 5.0)]
            solved = roof_join.resolve(free)
            self.assertEqual(solved.moved, [])
            self.assertAlmostEqual(solved.pitches[1].z(rings[1][0][0], rings[1][0][1]), 9.0)
            self.assertAlmostEqual(solved.pitches[0].tilt, 20.0)

    def test_a_pitch_drawn_over_another_is_not_a_neighbour(self):
        free = [pitch(rect(0, 0, 10, 10), 0, 6.0, 20.0), pitch(rect(0, 0, 10, 5), 0, 9.0, 5.0)]
        self.assertEqual(roof_join.shared_lines([[tuple(c) for c in f["ring"]] for f in free]), [])

    def test_parallel_planes_at_different_levels_become_one_continuous_slope(self):
        rings = [rect(0, 0, 20, 5), rect(0, 5, 20, 10)]
        free = [pitch(rings[0], 0, 5.0, 20.0), pitch(rings[1], 0, 4.0, 20.0)]    # the second's eave lies on the line
        found = roof_join.resolve(free).pitches
        assert_continuous(self, found, rings)
        self.assertAlmostEqual(found[1].tilt, 20.0, places=2)
        self.assertAlmostEqual(found[0].z(3, 0), 5.0, places=3)
        self.assertAlmostEqual(found[1].z(3, 10), 5.0 + 10 * math.tan(math.radians(20.0)), delta=0.02)

    def test_three_pitches_at_a_point_meet_there(self):
        rings = [[[0, 0], [20, 0], [10, 5]], [[20, 0], [20, 10], [10, 5]], [[20, 10], [0, 10], [0, 0], [10, 5]]]
        free = [pitch(rings[0], 0, 6.0, 25.0), pitch(rings[1], 0, 6.0, 40.0), pitch(rings[2], 0, 6.0, 25.0)]
        found = roof_join.resolve(free).pitches
        assert_continuous(self, found, rings)
        at = [p.z(10, 5) for p in found]
        self.assertAlmostEqual(max(at), min(at), places=4)
        self.assertGreater(at[0], 6.0)

    def test_independent_they_stay_each_on_its_plane(self):
        free = [pitch(rect(0, 0, 20, 5), 0, 6.0, 15.0), pitch(rect(0, 5, 20, 10), 2, 7.0, 30.0)]
        found = roof_join.resolve(free, joined=False).pitches
        self.assertEqual((found[0].tilt, found[1].tilt), (15.0, 30.0))
        self.assertAlmostEqual(found[1].z(3, 10), 7.0)

    def test_a_pitch_alone_is_as_the_numbers_say(self):
        free = [pitch(rect(0, 0, 20, 5), 0, 6.0, 15.0)]
        self.assertEqual(roof_join.resolve(free).pitches[0].tilt, 15.0)


class OutOfPlane(unittest.TestCase):
    RING = rect(0, 0, 10, 10)

    def test_corners_on_one_plane_stay_one_pitch(self):
        z = [5.0, 5.0, 7.0, 7.0]
        self.assertEqual(len(roof_join.fold(self.RING, z)), 1)
        solved = roof_join.resolve([pitch(self.RING, 0, 5.0, 0.0, z=z)])
        self.assertEqual(len(solved.pitches), 1)
        self.assertAlmostEqual(solved.pitches[0].tilt, math.degrees(math.atan(0.2)))
        self.assertEqual(solved.folds, [])

    def test_a_raised_corner_folds_along_the_ridge_through_it_with_every_corner_exact(self):
        z = [5.0, 5.0, 8.0, 5.0]
        solved = roof_join.resolve([pitch(self.RING, 0, 5.0, 0.0, z=z)])
        self.assertEqual(len(solved.pitches), 2)
        self.assertEqual([p.whole for p in solved.pitches], [0, 0])
        for p in solved.pitches:
            for x, y, h in p.corners_3d():
                self.assertAlmostEqual(h, z[[tuple(c) for c in self.RING].index((x, y))])
            self.assertGreater(p.tilt, 0.0)
        self.assertEqual(len(solved.folds), 1)
        (a, b), = solved.folds[0].lines
        self.assertIn((10.0, 10.0), (a, b))                      # through the corner raised: water runs off both ways

    def test_a_lowered_corner_folds_across_it(self):
        z = [5.0, 5.0, 2.0, 5.0]
        solved = roof_join.resolve([pitch(self.RING, 0, 5.0, 0.0, z=z)])
        (a, b), = solved.folds[0].lines
        self.assertNotIn((10.0, 10.0), (a, b))
        self.assertEqual({a, b}, {(10.0, 0.0), (0.0, 10.0)})

    def test_an_l_folds_in_the_least_parts_and_keeps_its_place_first(self):
        ring = [[0, 0], [10, 0], [10, 5], [5, 5], [5, 10], [0, 10]]
        z = [5.0, 5.0, 5.0, 5.0, 8.0, 5.0]
        parts = roof_join.fold(ring, z)
        self.assertEqual(len(parts), 2)
        others = pitch(rect(20, 0, 30, 10), 0, 4.0, 10.0)
        found = roof_join.resolve([pitch(ring, 0, 5.0, 0.0, z=z), others]).pitches
        self.assertEqual(len(found), 3)
        self.assertEqual(found[0].whole, 0)                       # the largest part in the pitch's place
        self.assertAlmostEqual(found[1].tilt, 10.0)               # the next pitch stays where it was
        self.assertEqual(found[2].whole, 0)
        self.assertGreater(roof_join._area(found[0].ring), roof_join._area(found[2].ring))

    def test_a_pitch_between_frozen_ones_follows_them_and_folds_if_it_must(self):
        rings = [rect(0, 0, 10, 10), rect(10, 0, 20, 10), rect(20, 0, 30, 10)]
        free = [pitch(rings[0], 0, 5.0, 0.0, z=[5.0, 5.0, 8.0, 5.0]),
                pitch(rings[1], 0, 5.0, 0.0),
                pitch(rings[2], 0, 5.0, 0.0, z=[6.0, 5.0, 5.0, 5.0])]
        found = roof_join.resolve(free).pitches
        z = {(x, y): h for p in found if p.whole == 1 or p is found[1] for x, y, h in p.corners_3d()}
        self.assertAlmostEqual(z[(10.0, 10.0)], 8.0)
        self.assertAlmostEqual(z[(20.0, 0.0)], 6.0)
        self.assertEqual(sum(1 for p in found if p.whole == 1), 2)

    def test_a_corner_parted_lets_the_neighbours_differ_there(self):
        rings = [rect(0, 0, 10, 10), rect(10, 0, 20, 10)]
        free = [pitch(rings[0], 0, 5.0, 0.0, z=[5.0, 5.0, 8.0, 8.0]), pitch(rings[1], 0, 5.0, 0.0, z=[5.0, 5.0, 5.0, 5.0])]
        solved = roof_join.resolve(free, detached=[[0, 2], [1, 3]])
        self.assertAlmostEqual(solved.pitches[0].z(10, 10), 8.0)
        self.assertAlmostEqual(solved.pitches[1].z(10, 10), 5.0)


class Building(unittest.TestCase):
    def house(self, **roof) -> model.Building:
        return model.Building("b1", "Casa", rect(0, 0, 20, 10), 6.0, model.Roof(type="free", **roof))

    def test_the_default_joins_and_the_option_leaves_them_apart(self):
        free = [pitch(rect(0, 0, 20, 5), 0, 6.0, 15.0), pitch(rect(0, 5, 20, 10), 2, 6.0, 30.0)]
        joined = self.house(free_pitches=copy.deepcopy(free))
        self.assertAlmostEqual(joined.pitches()[0].z(3, 5), joined.pitches()[1].z(3, 5), places=4)
        joined.roof.joined = False
        self.assertAlmostEqual(joined.pitches()[0].tilt, 15.0)
        self.assertAlmostEqual(joined.pitches()[1].tilt, 30.0)

    def test_the_keys_say_it_only_when_it_matters(self):
        flat = model.Building("b1", "Casa", rect(0, 0, 20, 10), 6.0)
        self.assertNotIn("joined", flat.geometry_key())
        self.assertNotIn("welds", flat.geometry_key())
        apart = self.house(free_pitches=[], joined=False)
        self.assertNotIn("joined", apart.geometry_key())
        self.assertIn("joined", self.house(free_pitches=[]).geometry_key())

    def test_heights_change_the_key_of_the_shadows_and_of_the_year(self):
        p = model.Project(name="Prova")
        b = self.house(free_pitches=[pitch(rect(0, 0, 20, 10), 0, 6.0, 0.0)])
        p.buildings.append(b)
        from meridiana import session
        s = session.ProjectSession(p)
        before = s.energy_key()
        b.roof.free_pitches[0]["z"] = [6.0, 6.0, 9.0, 6.0]
        self.assertNotEqual(s.energy_key(), before)
        before = s.energy_key()
        b.roof.free_pitches[0].pop("z")
        b.roof.joined = False
        self.assertNotEqual(s.energy_key(), before)

    def test_a_flat_part_lifted_casts_its_shadow_and_a_corner_lowered_leaves_no_wall_above_the_roof(self):
        a, b, c = rect(0, 0, 10, 10), rect(10, 0, 20, 10), rect(20, 0, 30, 10)
        house = model.Building("b1", "Casa", rect(0, 0, 30, 10), 6.0, model.Roof(
            type="free", free_pitches=[pitch(a, 0, 6.0, 0.0), pitch(b, 3, 6.0, 15.0), pitch(c, 0, 6.0, 0.0)]))
        lifted = house.pitches()[2]
        self.assertTrue(system._stands_up(lifted, house))
        self.assertFalse(system._stands_up(house.pitches()[0], house))
        low = model.Building("b2", "Bassa", rect(0, 0, 20, 10), 6.0, model.Roof(
            type="free", free_pitches=[pitch(rect(0, 0, 20, 10), 0, 6.0, 0.0, z=[3.0, 6.0, 6.0, 6.0])]))
        self.assertAlmostEqual(low.wall_top(), 3.0)
        self.assertEqual(model.Building("b3", "Piana", rect(0, 0, 9, 9), 6.0).wall_top(), 6.0)

    def test_a_sub_field_on_a_folded_pitch_is_laid_on_its_part_only(self):
        p = model.Project(name="Prova")
        ring = rect(0, 0, 20, 20)
        p.buildings.append(model.Building("b1", "Casa", ring, 6.0, model.Roof(
            type="free", free_pitches=[pitch(ring, 0, 6.0, 0.0, z=[6.0, 6.0, 9.0, 6.0])])))
        sf = model.SubField("s1", "Campo", ring, building="b1", pitch=0)
        p.subfields.append(sf)
        part = p._ring_on_its_part(sf)
        from shapely.geometry import Polygon
        self.assertAlmostEqual(Polygon(part).area, 200.0, places=3)
        self.assertAlmostEqual(Polygon(p._ring_on_its_part(model.SubField("s2", "Altro", ring))).area, 400.0)


class Format(unittest.TestCase):
    def old(self) -> dict:
        data = json.loads((_setup.FORMATS / "progetto-v22.meridiana").read_text(encoding="utf-8"))
        data["buildings"][0]["roof"] = {"type": "free", "free_pitches": [
            pitch(rect(0, 0, 20, 5), 0, 6.0, 15.0), pitch(rect(0, 5, 20, 10), 2, 7.0, 30.0)]}
        return data

    def test_a_roof_drawn_before_keeps_its_planes_and_is_told_of_the_option(self):
        notes: list[str] = []
        p = model.Project.from_json(self.old(), notes=notes)
        b = p.buildings[0]
        self.assertFalse(b.roof.joined)
        self.assertEqual([round(q.tilt, 3) for q in b.pitches()], [15.0, 30.0])
        self.assertEqual(len(notes), 1)
        self.assertIn(b.name, notes[0])
        self.assertEqual(p.to_json()["version"], model.FORMAT_VERSION)

    def test_the_key_of_a_roof_of_before_stays_the_one_of_format_22(self):
        data = self.old()
        p = model.Project.from_json(data)
        shape = {"footprint": data["buildings"][0]["footprint"], "height": data["buildings"][0]["height"],
                 "roof": {"type": "free", "eave_side": 0, "ridge_along": None, "tilt": 0.0, "edges": [],
                          "free_pitches": data["buildings"][0]["roof"]["free_pitches"], "ridge_height": None,
                          "covering": ""}, "parapet": data["buildings"][0].get("parapet", 0.0)}
        self.assertEqual(p.buildings[0].geometry_key(), json.dumps(shape, sort_keys=True, default=str))

    def test_what_is_new_goes_through_a_save_and_a_bad_file_is_refused(self):
        data = self.old()
        data["version"] = model.FORMAT_VERSION
        roof = data["buildings"][0]["roof"]
        roof.update(joined=True, welds=[[[0, 2], [1, 1]]], detached=[[0, 3]])
        roof["free_pitches"][0]["z"] = [6.0, 6.0, 8.0, 8.0]
        again = model.Project.from_json(json.loads(json.dumps(model.Project.from_json(data).to_json())))
        self.assertEqual(again.buildings[0].roof.welds, [[[0, 2], [1, 1]]])
        self.assertEqual(again.buildings[0].roof.detached, [[0, 3]])
        self.assertEqual(again.buildings[0].roof.free_pitches[0]["z"], [6.0, 6.0, 8.0, 8.0])
        for key, bad in (("welds", [["a", 0], [0, 0]]), ("welds", [[[0, 0]]]), ("detached", [[0, -1]]), ("joined", 1)):
            broken = copy.deepcopy(data)
            broken["buildings"][0]["roof"][key] = bad
            with self.assertRaises(ValueError, msg=key):
                model.Project.from_json(broken)
        broken = copy.deepcopy(data)
        broken["buildings"][0]["roof"]["free_pitches"][0]["z"] = [1.0]
        with self.assertRaises(ValueError):
            model.Project.from_json(broken)


if __name__ == "__main__":
    unittest.main()
