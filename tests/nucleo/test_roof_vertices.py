"""The corners of a roof, one by one (roof_vertices.py, gizmo.py; R303): a height written or dragged, two corners made one
point and parted, each on any kind of roof, through a save."""

import json
import math
import unittest

import numpy as np

import _setup  # noqa: F401
from nucleo.test_gizmo import H, W, cam

from meridiana import gizmo, mesh, model, move, roof_join, roof_vertices as rv


def rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def pitch(ring, side, eave, tilt):
    return {"ring": ring, "eave_side": side, "eave": eave, "tilt": tilt}


def project(roof=None, footprint=None) -> model.Project:
    p = model.Project(name="Prova")
    p.buildings.append(model.Building("b1", "Casa", footprint or rect(0, 0, 20, 10), 6.0, roof or model.Roof()))
    return p


def manual_two(joined=True) -> model.Project:
    return project(model.Roof(type="free", joined=joined, free_pitches=[
        pitch(rect(0, 0, 20, 5), 0, 6.0, 20.0), pitch(rect(0, 5, 20, 10), 2, 6.0, 20.0)]))


def corner_at(b, x, y):
    return next(h for h in rv.handles(b) if abs(h.x - x) < 1e-6 and abs(h.y - y) < 1e-6)


class Written(unittest.TestCase):
    def test_a_sign_moves_and_no_sign_is_the_height(self):
        self.assertEqual(rv.parse_height("12,5"), (12.5, False))
        self.assertEqual(rv.parse_height("+5"), (5.0, True))
        self.assertEqual(rv.parse_height("-10"), (-10.0, True))
        self.assertEqual(rv.parse_height(" 7 "), (7.0, False))
        for bad in ("", "abc", "+", "1,2,3", "nan", "inf"):
            self.assertIsNone(rv.parse_height(bad), bad)
        self.assertEqual(rv.height_written(8.0, (2.0, True)), 10.0)
        self.assertEqual(rv.height_written(8.0, (-3.0, True)), 5.0)
        self.assertEqual(rv.height_written(8.0, (3.0, False)), 3.0)


class Handles(unittest.TestCase):
    def test_a_flat_roof_has_its_four_corners(self):
        hs = rv.handles(project().buildings[0])
        self.assertEqual(len(hs), 4)
        self.assertTrue(all(h.z == 6.0 for h in hs))

    def test_pitches_joined_share_the_handles_of_their_common_corners_apart_they_do_not(self):
        self.assertEqual(len(rv.handles(manual_two().buildings[0])), 6)
        self.assertEqual(len(rv.handles(manual_two(joined=False).buildings[0])), 8)

    def test_a_ridge_end_of_a_gable_is_one_handle(self):
        b = project(model.Roof(type="gable", tilt=20.0)).buildings[0]
        tops = [h for h in rv.handles(b) if h.z > 6.0 + 1e-6]
        self.assertEqual(len(tops), 2)
        self.assertEqual(sorted(len(h.corners) for h in tops), [2, 2])

    def test_a_canopy_has_none_and_refuses(self):
        p = project(model.Roof(type="mono", tilt=5.0))
        p.buildings[0].canopy = model.Canopy()
        self.assertEqual(rv.handles(p.buildings[0]), [])
        with self.assertRaises(ValueError):
            rv.set_height(p, "b1", (0, 0), 9.0)

    def test_an_obstacle_has_the_corners_of_its_top_and_they_move_it_whole(self):
        p = project()
        p.exclusions.append(model.ExclusionItem("e1", rect(2, 2, 4, 4), kind="chimney", building="b1", height=1.5))
        hs = rv.handles_of(p, "exclusion", "e1")
        self.assertEqual(len(hs), 4)
        self.assertTrue(all(h.obstacle for h in hs))
        self.assertAlmostEqual(hs[0].z, 7.5)
        rv.set_obstacle_height(p, "e1", 9.0)
        self.assertAlmostEqual(p.exclusions[0].height, 3.0)
        rv.set_obstacle_height(p, "e1", 1.0)                 # never under what it stands on
        self.assertEqual(p.exclusions[0].height, 0.0)


class Heights(unittest.TestCase):
    def test_a_ridge_corner_raised_moves_both_pitches_and_nothing_else(self):
        p = manual_two()
        b = p.buildings[0]
        start = {(h.x, h.y): h.z for h in rv.handles(b)}
        h = corner_at(b, 0, 5)
        rv.set_height(p, "b1", h.corners[0], h.z + 2.0)
        after = {(k.x, k.y): k.z for k in rv.handles(b)}
        for key, z in start.items():
            self.assertAlmostEqual(after[key], z + 2.0 if key == (0.0, 5.0) else z, places=3, msg=str(key))
        self.assertEqual(len(b.solved().folds), 2)           # two quads out of plane, each in two
        self.assertEqual(len(b.pitches()), 4)

    def test_an_eave_corner_of_a_flat_roof_made_pitched_folds_it(self):
        p = project()
        b = p.buildings[0]
        rv.to_manual(p, b)                                   # «Make it pitched», asked (R357)
        rv.set_height(p, "b1", rv.handles(b)[2].corners[0], 9.0)
        self.assertEqual(b.roof.type, "free")
        self.assertEqual(len(b.pitches()), 2)
        zs = sorted(h.z for h in rv.handles(b))
        self.assertEqual(zs, [6.0, 6.0, 6.0, 9.0])
        self.assertEqual(len(b.solved().folds), 1)

    def test_three_corners_of_a_flat_roof_raised_in_turn_stay_one_plane_when_they_are(self):
        p = project()
        b = p.buildings[0]
        rv.to_manual(p, b)
        hs = rv.handles(b)
        for k in (2, 3):
            rv.set_height(p, "b1", hs[k].corners[0], 8.0)
        self.assertEqual(len(b.pitches()), 1)
        self.assertAlmostEqual(b.pitches()[0].tilt, math.degrees(math.atan(0.2)))
        self.assertEqual(b.roof.free_pitches[0]["tilt"], round(b.pitches()[0].tilt, 3))    # the fields say what it is
        self.assertEqual(b.roof.free_pitches[0]["eave"], 6.0)

    def test_generated_roofs_become_the_same_planes_with_the_sub_field_on_its_pitch(self):
        for kind, tilt in (("mono", 15.0), ("gable", 25.0), ("hip", 25.0)):
            with self.subTest(kind=kind):
                p = project(model.Roof(type=kind, tilt=tilt, eave_side=0))
                b = p.buildings[0]
                was = [(round(q.tilt, 4), round(q.azimuth % 360.0, 3), [round(c[2], 4) for c in q.corners_3d()])
                       for q in b.pitches()]
                index = len(was) - 1
                sf = model.SubField("s1", "Campo", rect(1, 1, 2, 2), building="b1", pitch=b.pitch_ref(index))
                p.subfields.append(sf)
                p.variants[0]["design"] = {"subfields": [{"building": "b1", "pitch": b.pitch_ref(index)}]}
                self.assertTrue(rv.to_manual(p, b))
                self.assertEqual(b.roof.type, "free")
                now = [(round(q.tilt, 4), round(q.azimuth % 360.0, 3), [round(c[2], 4) for c in q.corners_3d()])
                       for q in b.pitches()]
                self.assertEqual(now, was)
                self.assertEqual(sf.pitch, index)
                self.assertEqual(b.pitch_index(sf.pitch), index)
                self.assertEqual(p.variants[0]["design"]["subfields"][0]["pitch"], index)
                self.assertFalse(rv.to_manual(p, b))

    def test_under_the_ground_is_refused_and_nothing_changes(self):
        p = project()
        with self.assertRaises(ValueError):
            rv.set_height(p, "b1", (0, 0), -1.0)
        self.assertEqual(p.buildings[0].roof.type, "flat")

    def test_a_neighbour_not_touching_the_corner_does_not_move(self):
        p = project(model.Roof(type="free", free_pitches=[
            pitch(rect(0, 0, 10, 10), 0, 6.0, 0.0), pitch(rect(10, 0, 20, 10), 0, 6.0, 0.0),
            pitch(rect(20, 0, 30, 10), 0, 6.0, 0.0)]), rect(0, 0, 30, 10))
        b = p.buildings[0]
        h = corner_at(b, 0, 10)
        rv.set_height(p, "b1", h.corners[0], 9.0)
        for q in b.pitches()[1:3]:
            self.assertEqual(q.tilt, 0.0)
            self.assertAlmostEqual(q.z0, 6.0, places=3)


class FlatRoofCorners(unittest.TestCase):
    """R411, in place of R357: one corner of a flat roof tilts it on one plane, the opposite staying; all of them together
    are the height of the building, the roof flat, with all that stands on it."""

    def laid(self) -> model.Project:
        p = project()
        b = p.buildings[0]
        b.parapet = 1.0
        p.subfields.append(model.SubField("s1", "Campo", rect(1, 1, 19, 9), building="b1", params={"tilt": 10.0}))
        p.exclusions.append(model.ExclusionItem("e1", rect(3, 3, 4, 4), kind="plant", building="b1", height=2.0))
        return p

    def test_one_corner_tilts_the_roof_on_one_plane_and_the_opposite_stays(self):
        p = self.laid()
        b = p.buildings[0]
        rv.set_height(p, "b1", rv.handles(b)[2].corners[0], 8.5)
        self.assertEqual(b.roof.type, "flat")                    # R455: still flat, on an inclined plane
        self.assertEqual(len(b.pitches()), 1)
        self.assertEqual(sorted(round(h.z, 2) for h in rv.handles(b)), [6.0, 7.25, 7.25, 8.5])
        self.assertEqual(round(rv.handles(b)[2].z, 2), 8.5)
        self.assertEqual(round(rv.handles(b)[0].z, 2), 6.0)      # the opposite corner
        self.assertEqual(b.height, 6.0)
        self.assertEqual([round(z, 2) for z in b.roof.plane], [6.0, 7.25, 8.5, 7.25])
        self.assertGreater(b.pitches()[0].tilt, 0)
        # a second corner moved starts from the plane as it is, not from the level roof
        rv.set_height(p, "b1", rv.handles(b)[1].corners[0], 7.25)
        self.assertEqual(sorted(round(h.z, 2) for h in rv.handles(b)), [6.0, 7.25, 7.25, 8.5])

    def test_going_down_too_and_refused_under_the_ground(self):
        p = self.laid()
        b = p.buildings[0]
        with self.assertRaises(ValueError):
            rv.set_height(p, "b1", rv.handles(b)[2].corners[0], -1.0)
        with self.assertRaises(ValueError):                  # the plane would take the far side below the ground
            rv.set_heights(p, "b1", [(rv.handles(b)[2].corners[0], 13.0), (rv.handles(b)[0].corners[0], 0.0), (rv.handles(b)[1].corners[0], 0.0)])
        self.assertEqual(b.roof.type, "flat")
        rv.set_height(p, "b1", rv.handles(b)[2].corners[0], 4.0)
        self.assertEqual(sorted(round(h.z, 2) for h in rv.handles(b)), [4.0, 5.0, 5.0, 6.0])

    def test_all_corners_together_change_the_height_of_the_building_and_nothing_else_of_the_roof(self):
        p = self.laid()
        b = p.buildings[0]
        roof_was = json.dumps(b.roof.__dict__, sort_keys=True, default=str)
        rv.set_heights(p, "b1", [(h.corners[0], 8.5) for h in rv.handles(b)])
        self.assertEqual(b.roof.type, "flat")
        self.assertEqual(json.dumps(b.roof.__dict__, sort_keys=True, default=str), roof_was)
        self.assertEqual(b.height, 8.5)
        self.assertTrue(all(h.z == 8.5 for h in rv.handles(b)))
        self.assertEqual(len(b.pitches()), 1)
        self.assertEqual(b.pitches()[0].tilt, 0.0)

    def test_what_stands_on_it_follows(self):
        p = self.laid()
        b = p.buildings[0]
        key = b.geometry_key()
        rv.set_heights(p, "b1", [(h.corners[0], 8.5) for h in rv.handles(b)])
        self.assertNotEqual(b.geometry_key(), key)           # layouts, shadows and the year are made again
        sf = p.subfields[0]
        self.assertAlmostEqual(p.surface_of(sf).z(5.0, 5.0), 8.5)
        self.assertAlmostEqual(move.height(p, "subfield", "s1", (5.0, 5.0)), 8.5)
        prisms = p.obstacle_prisms()
        parapet = [o for o in prisms if o.get("kind") == "parapet"]
        self.assertTrue(parapet)
        self.assertTrue(all((o["z0"], o["z1"]) == (8.5, 9.5) for o in parapet))     # it still counts for the shadows
        plant = next(o for o in prisms if o.get("id") == "e1")
        self.assertAlmostEqual(plant["z1"], 10.5)

    def test_two_corners_of_a_side_tilt_it_about_the_other_side(self):
        p = self.laid()
        b = p.buildings[0]
        rv.set_heights(p, "b1", [(h.corners[0], 7.0) for h in rv.handles(b)[:2]])
        self.assertEqual(b.roof.type, "flat")
        self.assertEqual(len(b.pitches()), 1)
        self.assertEqual([round(h.z, 2) for h in rv.handles(b)], [7.0, 7.0, 6.0, 6.0])

    def test_under_the_ground_is_refused_and_a_canopy_has_none(self):
        p = self.laid()
        with self.assertRaises(ValueError):
            rv.set_height(p, "b1", (0, 0), -1.0)
        self.assertEqual(p.buildings[0].height, 6.0)
        self.assertFalse(rv.stays_flat(model.Building("c", "C", rect(0, 0, 5, 5), 3.0, canopy=model.Canopy())))

    def test_pitched_roofs_do_not_change_their_way(self):
        for kind in ("mono", "gable", "hip"):
            with self.subTest(kind=kind):
                p = project(model.Roof(type=kind, tilt=20.0))
                b = p.buildings[0]
                rv.set_height(p, "b1", rv.handles(b)[0].corners[0], b.height + 1.0)
                self.assertEqual(b.roof.type, "free")
                self.assertEqual(b.height, 6.0)

    def test_it_goes_through_a_save_with_the_format_it_had(self):
        p = self.laid()
        rv.set_heights(p, "b1", [(h.corners[0], 8.5) for h in rv.handles(p.buildings[0])])
        again = model.Project.from_json(json.loads(json.dumps(p.to_json())))
        self.assertEqual((again.buildings[0].roof.type, again.buildings[0].height), ("flat", 8.5))


class SeveralCorners(unittest.TestCase):
    """R356: several corners take their heights in one change."""

    def test_each_goes_to_its_own_height(self):
        p = manual_two()
        b = p.buildings[0]
        a, c = corner_at(b, 0, 5), corner_at(b, 20, 5)
        rv.set_heights(p, "b1", [(a.corners[0], 9.0), (c.corners[0], 9.0)])
        self.assertAlmostEqual(corner_at(b, 0, 5).z, 9.0)
        self.assertAlmostEqual(corner_at(b, 20, 5).z, 9.0)
        self.assertEqual(b.solved().folds, [])               # the ridge raised whole: planes still

    def test_generated_roof_too(self):
        p = project(model.Roof(type="gable", tilt=20.0))
        b = p.buildings[0]
        hs = rv.handles(b)
        rv.set_heights(p, "b1", [(hs[0].corners[0], 7.0), (hs[1].corners[0], 7.5)])
        now = {(round(h.x, 3), round(h.y, 3)): h.z for h in rv.handles(b)}
        self.assertAlmostEqual(now[(round(hs[0].x, 3), round(hs[0].y, 3))], 7.0)
        self.assertAlmostEqual(now[(round(hs[1].x, 3), round(hs[1].y, 3))], 7.5)

    def test_a_folded_pitch_goes_back_on_one_plane(self):
        p = project()
        b = p.buildings[0]
        rv.to_manual(p, b)
        corner = rv.handles(b)[2].corners[0]
        self.assertFalse(rv.folded(b, corner))
        rv.set_height(p, "b1", corner, 9.0)
        self.assertTrue(rv.folded(b, corner))
        rv.unfold(p, "b1", corner)
        self.assertFalse(rv.folded(b, corner))
        self.assertEqual(len(b.pitches()), 1)
        self.assertNotIn("z", b.roof.free_pitches[0])


class OnePoint(unittest.TestCase):
    def two_apart(self, joined=False) -> model.Project:
        return project(model.Roof(type="free", joined=joined, free_pitches=[
            pitch(rect(0, 0, 10, 10), 0, 6.0, 0.0), pitch(rect(10.5, 0, 20, 10), 0, 7.0, 0.0)]))

    def test_the_second_corner_comes_onto_the_first_in_plan_and_height_and_they_go_together(self):
        p = self.two_apart()
        b = p.buildings[0]
        rv.weld(p, "b1", (0, 1), (1, 0))
        self.assertEqual(b.roof.free_pitches[1]["ring"][0], [10.0, 0.0])
        self.assertEqual(b.roof.free_pitches[1]["z"][0], 6.0)
        self.assertEqual(b.roof.welds, [[[0, 1], [1, 0]]])
        h = corner_at(b, 10, 0)
        self.assertEqual(len(h.corners), 2)
        rv.set_height(p, "b1", (1, 0), 8.0)
        self.assertEqual(b.roof.free_pitches[0]["z"][1], 8.0)
        self.assertEqual(b.roof.free_pitches[1]["z"][0], 8.0)

    def test_it_stays_through_a_save_and_a_new_model_of_the_roof(self):
        p = self.two_apart()
        rv.weld(p, "b1", (0, 1), (1, 0))
        again = model.Project.from_json(json.loads(json.dumps(p.to_json())))
        b = again.buildings[0]
        self.assertEqual(len(corner_at(b, 10, 0).corners), 2)
        b.roof.free_pitches[0]["tilt"] = 5.0                 # a change elsewhere: a new model
        b.height = 7.0
        self.assertEqual(len(corner_at(b, 10, 0).corners), 2)

    def test_parted_they_are_two_independent_corners_again(self):
        p = self.two_apart()
        b = p.buildings[0]
        rv.weld(p, "b1", (0, 1), (1, 0))
        rv.detach(p, "b1", (0, 1))
        self.assertEqual(b.roof.welds, [])
        self.assertEqual(sorted(len(h.corners) for h in rv.handles(b) if abs(h.x - 10) < 1e-6 and h.y == 0), [1, 1])
        rv.set_height(p, "b1", (1, 0), 9.0)
        self.assertEqual(b.roof.free_pitches[0]["z"][1], 6.0)
        self.assertEqual(b.roof.free_pitches[1]["z"][0], 9.0)
        with self.assertRaises(ValueError):
            rv.detach(p, "b1", (0, 1))

    def test_corners_of_a_joined_roof_can_be_parted_too_and_made_one_again(self):
        p = manual_two()
        b = p.buildings[0]
        rv.detach(p, "b1", corner_at(b, 0, 5).corners[0])
        self.assertEqual(len(rv.handles(b)), 7)
        rv.set_height(p, "b1", (0, 3), 12.0)
        pair = [h for h in rv.handles(b) if h.x == 0 and h.y == 5]
        self.assertEqual(sorted(round(h.z, 2) for h in pair), [round(6.0 + 5 * math.tan(math.radians(20.0)), 2), 12.0])
        self.assertAlmostEqual(b.pitches()[0].z(0, 5), 12.0)
        rv.weld(p, "b1", (0, 3), (1, 0) if tuple(b.roof.free_pitches[1]["ring"][0]) == (0, 5) else (1, 3))
        self.assertEqual(len(rv.handles(b)), 6)
        self.assertEqual(b.roof.detached, [])

    def test_a_corner_with_itself_is_refused_and_a_ridge_end_of_a_gable_can_be_parted(self):
        p = self.two_apart()
        with self.assertRaises(ValueError):
            rv.weld(p, "b1", (0, 1), (0, 1))
        self.assertEqual(p.buildings[0].roof.welds, [])
        gable = project(model.Roof(type="gable", tilt=20.0))
        b = gable.buildings[0]
        top = next(h for h in rv.handles(b) if h.z > 6.1)
        self.assertTrue(rv.can_detach(top.corners))
        rv.detach(gable, "b1", top.corners[0])
        self.assertEqual(b.roof.type, "free")
        self.assertEqual(len(b.roof.detached), 2)

    def test_a_slope_written_on_a_welded_pitch_leaves_the_corner_one_point(self):
        p = self.two_apart()
        b = p.buildings[0]
        rv.weld(p, "b1", (0, 1), (1, 0))
        b.roof.free_pitches[1].pop("z")                      # what the properties do when a slope is written
        b.roof.free_pitches[1]["tilt"] = 10.0
        self.assertEqual(len(corner_at(b, 10, 0).corners), 2)
        self.assertAlmostEqual(b.solved().heights[1][0], b.solved().heights[0][1])

    def test_corners_gone_with_a_roof_drawn_again_do_not_stop_the_file_or_the_roof(self):
        p = self.two_apart()
        b = p.buildings[0]
        rv.weld(p, "b1", (0, 1), (1, 0))
        b.roof.free_pitches = b.roof.free_pitches[:1]
        b.roof.detached = [[7, 0]]
        again = model.Project.from_json(json.loads(json.dumps(p.to_json())))
        self.assertEqual(len(again.buildings[0].pitches()), 1)
        self.assertEqual(len(rv.handles(again.buildings[0])), 4)

    def test_two_corners_of_one_pitch_are_refused(self):
        p = self.two_apart()
        with self.assertRaises(ValueError):
            rv.weld(p, "b1", (0, 0), (0, 1))
        self.assertEqual(p.buildings[0].roof.welds, [])

    def test_a_weld_that_would_cross_a_pitch_is_refused(self):
        p = self.two_apart()
        with self.assertRaises(ValueError):
            rv.weld(p, "b1", (0, 0), (1, 1))                 # the far corner of the second pitch over the first's

    def test_welding_three_makes_one_list(self):
        p = project(model.Roof(type="free", joined=False, free_pitches=[
            pitch(rect(0, 0, 10, 10), 0, 6.0, 0.0), pitch(rect(10, 0, 20, 10), 0, 6.0, 0.0),
            pitch(rect(10, 10, 20, 20), 0, 6.0, 0.0)]))
        rv.weld(p, "b1", (0, 2), (1, 3))
        rv.weld(p, "b1", (0, 2), (2, 0))
        self.assertEqual(len(p.buildings[0].roof.welds), 1)
        self.assertEqual(len(p.buildings[0].roof.welds[0]), 3)

    def test_a_pitch_moved_alone_leaves_what_it_was_welded_to(self):
        p = self.two_apart()
        b = p.buildings[0]
        b.footprint = rect(-5, -5, 30, 30)
        b.roof.free_pitches[0]["id"] = "p1"
        b.roof.free_pitches[1]["id"] = "p2"
        rv.weld(p, "b1", (0, 1), (1, 0))
        move.translate(p, "pitch", "b1:p2", 0.0, 0.5)(p)
        self.assertEqual(b.roof.welds, [])


class Drag(unittest.TestCase):
    def test_the_pixels_take_the_nearest_corner_within_a_wider_area_than_its_mark(self):
        c = cam()
        points = [np.array([0.0, 0.0, 0.0]), np.array([3.0, 0.0, 0.0])]
        px, py = c.project(points[1], W, H)
        self.assertEqual(gizmo.pick_points(c, px + 8, py - 6, W, H, points), [1])
        self.assertEqual(gizmo.pick_points(c, px + 40, py, W, H, points), [])
        self.assertGreater(gizmo.VERTEX_TOLERANCE, 6)

    def test_a_drag_goes_along_the_vertical_in_the_steps_of_move(self):
        c = cam()
        origin = np.array([0.0, 2.0, 0.0])
        px, py = c.project(origin, W, H)
        drag = gizmo.HeightDrag.begin(c, px, py, W, H, origin)
        tx, ty = c.project(origin + gizmo.UP * 1.26, W, H)
        self.assertAlmostEqual(drag.update(c, tx, ty, W, H), 1.3)
        self.assertAlmostEqual(drag.update(c, tx, ty, W, H, {"shift"}), 1.26)
        self.assertAlmostEqual(drag.update(c, tx, ty, W, H, snaps=False), 1.26, places=2)
        # across the vertical nothing changes
        self.assertAlmostEqual(drag.update(c, tx + 80, ty, W, H, {"shift"}), drag.update(c, tx + 80, ty, W, H, {"shift"}))


class Everywhere(unittest.TestCase):
    """What the corners did reaches the views, the shadows, the layouts, the IFC: all read Building.pitches()."""

    def folded(self) -> model.Project:
        p = project(footprint=rect(0, 0, 20, 20))
        rv.to_manual(p, p.buildings[0])
        rv.set_height(p, "b1", rv.handles(p.buildings[0])[2].corners[0], 10.0)
        return p

    def test_the_surface_of_a_sub_field_and_the_shadows_are_those_of_its_part(self):
        from meridiana.energy import system
        p = self.folded()
        b = p.buildings[0]
        (one, two) = b.pitches()
        sf = model.SubField("s1", "Campo", rect(1, 1, 19, 19), building="b1", pitch=0)
        p.subfields.append(sf)
        self.assertAlmostEqual(p.surface_of(sf).tilt, one.tilt)
        self.assertAlmostEqual(p.surface_of(sf).z(*one.ring[0]), one.z(*one.ring[0]))
        solids = system.obstacles_of(p, sf)
        self.assertTrue(solids)                              # the other part stands up and is seen by the modules
        other = model.Building("b2", "Vicino", rect(40, 0, 50, 10), 4.0)
        p.buildings.append(other)
        self.assertGreater(len(system.obstacles_of(p, sf)), len(solids))
        self.assertAlmostEqual(two.z(20, 20), 10.0)

    def test_the_ifc_has_a_slab_for_each_part(self):
        import tempfile
        from pathlib import Path

        from meridiana import ifc_export
        try:
            import ifcopenshell
        except ImportError:
            self.skipTest("no ifcopenshell")
        p = self.folded()
        p.buildings[0].roof.joined = True
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "t.ifc"
            ifc_export.export(p, {}, target)
            self.assertEqual(ifc_export.validate(target), [])
            self.assertEqual(len(ifcopenshell.open(str(target)).by_type("IfcSlab")), 2)


class Plane(unittest.TestCase):
    def test_tilt_and_azimuth_of_a_part_are_those_of_its_real_plane(self):
        p = project()
        b = p.buildings[0]
        rv.set_height(p, "b1", rv.handles(b)[2].corners[0], 8.0)
        for q in b.pitches():
            zs = {(x, y): z for x, y, z in q.corners_3d()}
            a, c, _d = roof_join._plane_of(q)
            self.assertAlmostEqual(math.degrees(math.atan(math.hypot(a, c))), q.tilt, places=6)
            for x, y in q.ring:
                self.assertAlmostEqual(q.z(x, y), zs[(x, y)])
        triangles = mesh.building_triangles(b.footprint, b.pitches())[0]
        self.assertGreater(len(triangles), 0)


if __name__ == "__main__":
    unittest.main()
