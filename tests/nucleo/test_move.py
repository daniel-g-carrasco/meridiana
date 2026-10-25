"""Move and rotate in the core (move.py; study 16, B; task 16b): what moves with a building, a sub-field, an
exclusion, a free pitch; the moves refused with their reason; the copies; the keys of the layouts that change and
those that do not; the arithmetic of the gestures (values typed, steps, the arrows)."""

import math
import unittest

import _setup  # noqa: F401

from meridiana import model, move, session


def project() -> model.Project:
    """A shed of 40 x 20 m with a single pitch down to the South side, a sub-field with its rows facing South-West
    in the middle of it, a skylight, and a second building to the East with a sub-field of its own."""
    p = model.Project(name="Prova")
    b = model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]], height=8.0,
                       roof=model.Roof(type="mono", eave_side=0, tilt=10.0))
    p.buildings.append(b)
    p.subfields.append(model.SubField(id="s1", name="Sud", ring=[[10, 5], [30, 5], [30, 15], [10, 15]],
                                      building="b1", pitch=0, params={"tilt": 15.0, "azimuth": 30.0}, filled=True))
    p.exclusions.append(model.ExclusionItem(id="e1", ring=[[2, 2], [4, 2], [4, 4], [2, 4]], kind="skylight",
                                            building="b1"))
    p.buildings.append(model.Building(id="b2", name="Uffici", footprint=[[60, 0], [80, 0], [80, 10], [60, 10]]))
    p.subfields.append(model.SubField(id="s2", name="Uffici", ring=[[61, 1], [79, 1], [79, 9], [61, 9]],
                                      building="b2", pitch=0, filled=True))
    return p


def ring(points):
    return [[round(x, 6), round(y, 6)] for x, y in points]


class WhatMovesWithWhat(unittest.TestCase):
    def test_a_building_turned_90_degrees_about_its_middle_takes_its_sub_fields_and_exclusions_and_keeps_its_eave(self):
        p = project()
        azimuth = p.building("b1").pitches()[0].azimuth
        cx, cy = move.centre(p, "building", "b1")
        self.assertEqual((cx, cy), (20.0, 10.0))
        move.rotate(p, "building", "b1", cx, cy, 90.0)(p)
        b = p.building("b1")
        self.assertEqual(ring(b.footprint), [[30, -10], [30, 30], [10, 30], [10, -10]])
        self.assertEqual(b.roof.eave_side, 0)                     # the same side, turned with the outline
        self.assertAlmostEqual(b.pitches()[0].azimuth, move.turned_azimuth(azimuth, 90.0), places=3)
        self.assertEqual(ring(p.subfields[0].ring), [[25, 0], [25, 20], [15, 20], [15, 0]])
        self.assertEqual(ring(p.exclusions[0].ring), [[28, -8], [28, -6], [26, -6], [26, -8]])
        self.assertEqual(p.exclusions[0].building, "b1")
        self.assertEqual(p.subfields[0].params["azimuth"], -60.0)     # 30° towards West, turned 90° to the left
        self.assertEqual(ring(p.subfields[1].ring), [[61, 1], [79, 1], [79, 9], [61, 9]])   # the other building's

    def test_a_sub_field_with_its_own_azimuth_turns_it_and_an_automatic_one_stays_automatic(self):
        p = project()
        move.rotate(p, "subfield", "s1", 20.0, 10.0, 30.0)(p)
        self.assertEqual(p.subfields[0].params["azimuth"], 0.0)
        move.rotate(p, "subfield", "s2", 70.0, 5.0, 2.0)(p)
        self.assertNotIn("azimuth", p.subfields[1].params)

    def test_the_rows_by_hand_move_and_turn_with_their_sub_field_and_building(self):
        p = project()
        sf = p.subfields[0]
        before = p.fill(sf)
        sf.rows, sf.manual = [r.as_dict() for r in before.rows if r.places], True
        hand = p.fill(sf)
        move.translate(p, "subfield", "s1", 1.5, -0.5)(p)
        moved = p.fill(sf)
        self.assertEqual([m.key for m in moved.modules], [m.key for m in hand.modules])
        for a, b in zip(hand.modules, moved.modules, strict=True):
            self.assertAlmostEqual(b.centre[0] - a.centre[0], 1.5, delta=1e-3)
            self.assertAlmostEqual(b.centre[1] - a.centre[1], -0.5, delta=1e-3)
        cx, cy = move.centre(p, "building", "b1")
        move.rotate(p, "building", "b1", cx, cy, 90.0)(p)
        turned = p.fill(sf)
        self.assertEqual([m.key for m in turned.modules], [m.key for m in hand.modules])
        self.assertEqual({m.azimuth for m in turned.modules}, {round(move.turned_azimuth(m.azimuth, 90.0), 2)
                                                                for m in hand.modules})
        f = move.turn(cx, cy, 90.0)
        for a, b in zip(moved.modules, turned.modules, strict=True):
            x, y = f(*a.centre)
            self.assertAlmostEqual(b.centre[0], x, delta=1e-3)
            self.assertAlmostEqual(b.centre[1], y, delta=1e-3)

    def test_the_azimuth_turns_the_other_way_round_the_plan(self):
        self.assertEqual(move.turned_azimuth(0.0, 90.0), -90.0)        # facing South, turned left: facing East
        self.assertEqual(move.turned_azimuth(-90.0, -90.0), 0.0)
        self.assertEqual(move.turned_azimuth(170.0, -20.0), -170.0)
        self.assertEqual(move.turned_azimuth(-170.0, 10.0), 180.0)

    def test_a_building_moved_takes_the_sub_fields_of_the_other_variants_too(self):
        p = project()
        p.add_variant("Variante")                     # a copy of the design, worked on from now
        p.switch_variant("v1")
        move.translate(p, "building", "b1", 5.0, -2.0)(p)
        self.assertEqual(p.subfields[0].ring[0], [15.0, 3.0])
        other = p.design_of("v2")["subfields"][0]
        self.assertEqual(other["ring"][0], [15.0, 3.0])
        self.assertEqual(other["params"], {"tilt": 15.0, "azimuth": 30.0})       # moved, not turned
        self.assertEqual(p.design_of("v2")["subfields"][1]["ring"][0], [61, 1])  # the other building's stays

    def test_the_pitches_drawn_by_hand_move_with_their_building_and_one_moves_with_its_sub_fields(self):
        p = project()
        b = p.building("b1")
        b.roof = model.Roof(type="free", free_pitches=[
            {"id": "p1", "ring": [[0, 0], [20, 0], [20, 20], [0, 20]], "eave_side": 0, "eave": 8.0, "tilt": 15.0},
            {"id": "p2", "ring": [[20, 0], [40, 0], [40, 20], [20, 20]], "eave_side": 0, "eave": 8.0, "tilt": 15.0}])
        p.subfields[0].ring, p.subfields[0].pitch = [[2, 2], [8, 2], [8, 8], [2, 8]], 0
        move.translate(p, "building", "b1", 1.0, 1.0)(p)
        self.assertEqual(b.roof.free_pitches[1]["ring"][0], [21.0, 1.0])
        move.translate(p, "pitch", "b1:p1", 0.5, 0.0)(p)              # still on the building
        self.assertEqual(b.roof.free_pitches[0]["ring"][0], [1.5, 1.0])
        self.assertEqual(p.subfields[0].ring[0], [3.5, 3.0])           # the sub-field on it went too

    def test_an_exclusion_that_leaves_its_building_is_on_the_ground_and_one_that_comes_onto_another_is_its(self):
        p = project()
        move.translate(p, "exclusion", "e1", -10.0, 0.0)(p)
        self.assertIsNone(p.exclusions[0].building)
        move.translate(p, "exclusion", "e1", 70.0, 0.0)(p)
        self.assertEqual(p.exclusions[0].building, "b2")

    def test_what_moves_with_the_object_is_what_the_plan_shows_moving(self):
        p = project()
        rings = move.moving(p, "building", "b1")
        self.assertEqual(len(rings), 3)                                # the building, s1, e1
        self.assertEqual(rings[0][1], (40.0, 0.0))
        self.assertEqual(len(move.moving(p, "subfield", "s1")), 1)
        self.assertEqual(move.moving(p, "subfield", "nothing"), [])


class Refused(unittest.TestCase):
    def test_a_sub_field_that_would_leave_its_pitch_is_refused_with_the_reason_and_the_project_stays(self):
        s = session.ProjectSession(project())
        before = s.snapshot()
        with self.assertRaises(ValueError) as caught:
            s.edit("Move", move.translate(s.project, "subfield", "s1", 15.0, 0.0))
        self.assertIn("pitch", str(caught.exception))
        self.assertEqual(s.snapshot(), before)
        self.assertEqual(s.undo.count(), 0)
        s.edit("Move", move.translate(s.project, "subfield", "s1", 5.0, 0.0))     # on its pitch still: fine
        self.assertEqual(s.project.subfields[0].ring[0], [15.0, 5.0])

    def test_a_sub_field_drawn_a_hair_over_the_eave_can_still_move_along_it(self):
        p = project()
        p.subfields[0].ring = [[10, -0.05], [30, -0.05], [30, 10], [10, 10]]
        move.translate(p, "subfield", "s1", 2.0, 0.0)(p)
        self.assertEqual(p.subfields[0].ring[0], [12.0, -0.05])

    def test_a_sub_field_on_the_ground_does_not_go_onto_a_building(self):
        p = project()
        p.subfields.append(model.SubField(id="s3", name="Terra", ring=[[0, -30], [10, -30], [10, -25], [0, -25]]))
        move.translate(p, "subfield", "s3", 5.0, -5.0)(p)
        with self.assertRaises(ValueError) as caught:
            move.translate(p, "subfield", "s3", 10.0, 40.0)(p)
        self.assertIn("building", str(caught.exception))

    def test_a_free_pitch_that_would_leave_its_building_is_refused(self):
        p = project()
        p.building("b1").roof = model.Roof(type="free", free_pitches=[
            {"id": "p1", "ring": [[0, 0], [20, 0], [20, 20], [0, 20]], "eave_side": 0, "eave": 8.0, "tilt": 15.0}])
        with self.assertRaises(ValueError) as caught:
            move.translate(p, "pitch", "b1:p1", -5.0, 0.0)(p)
        self.assertIn("building", str(caught.exception))

    def test_nothing_to_move_says_so(self):
        p = project()
        for kind, oid in (("building", "b9"), ("subfield", "s9"), ("site", ""), ("pitch", "b1:p9"), ("row", "s1/f99")):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                move.translate(p, kind, oid, 1.0, 0.0)

    def test_a_row_moves_within_its_sub_field_and_does_not_turn(self):
        p = project()
        rid = next(r.id for r in p.fill(p.subfields[0]).rows if r.places)
        oid = f"s1/{rid}"
        ring = move.outline(p, "row", oid)
        self.assertEqual(len(ring), 4)
        cx, cy = move.centre(p, "row", oid)
        self.assertGreater(move.height(p, "row", oid, (cx, cy)), 7.0)          # on its roof
        move.translate(p, "row", oid, 0.3, 0.0)(p)
        self.assertTrue(p.subfields[0].manual)
        moved = move.outline(p, "row", oid)
        self.assertAlmostEqual(min(q[0] for q in moved) - min(q[0] for q in ring), 0.3, delta=1e-3)
        for refused in (lambda: move.rotate(p, "row", oid, cx, cy, 90.0), lambda: move.copy(p, "row", oid, 1.0, 0.0)):
            with self.assertRaises(ValueError):
                refused()


class Copies(unittest.TestCase):
    def test_a_copy_moved_is_a_new_object_and_the_original_stays(self):
        p = project()
        made = move.copy(p, "subfield", "s1", 2.0, 1.0)(p)
        self.assertEqual(made, "s3")
        self.assertEqual(p.subfields[0].ring[0], [10, 5])
        new = p.subfields[-1]
        self.assertEqual((new.ring[0], new.filled, new.building), ([12.0, 6.0], False, "b1"))

    def test_a_copy_turned_turns_its_azimuth(self):
        p = project()
        made = move.copy(p, "subfield", "s1", about=(20.0, 10.0), degrees=-30.0)(p)
        new = next(s for s in p.subfields if s.id == made)
        self.assertEqual(new.params["azimuth"], 60.0)
        self.assertEqual(p.subfields[0].params["azimuth"], 30.0)

    def test_a_building_copied_is_the_building_alone(self):
        p = project()
        made = move.copy(p, "building", "b1", 0.0, -30.0)(p)
        self.assertEqual(p.building(made).footprint[0], [0.0, -30.0])
        self.assertEqual(sum(s.building == made for s in p.subfields), 0)


class Layouts(unittest.TestCase):
    def test_only_the_layouts_of_what_moved_are_made_again(self):
        """A building moved changes the keys of its sub-fields and not those of the other building's (study 18,
        A 9.2: the window lays out again only what the key says changed)."""
        p = project()
        keys = {sf.id: p.layout_key(sf) for sf in p.subfields}
        move.translate(p, "building", "b1", 3.0, 0.0)(p)
        after = {sf.id: p.layout_key(sf) for sf in p.subfields}
        self.assertNotEqual(after["s1"], keys["s1"])
        self.assertEqual(after["s2"], keys["s2"])

    def test_a_sub_field_moved_changes_its_key_alone(self):
        p = project()
        keys = {sf.id: p.layout_key(sf) for sf in p.subfields}
        move.translate(p, "subfield", "s1", 1.0, 0.0)(p)
        self.assertNotEqual(p.layout_key(p.subfields[0]), keys["s1"])
        self.assertEqual(p.layout_key(p.subfields[1]), keys["s2"])

    def test_one_undo_puts_everything_back(self):
        s = session.ProjectSession(project())
        before = s.snapshot()
        topics = s.edit("Rotate", move.rotate(s.project, "building", "b1", 20.0, 10.0, 45.0))
        self.assertIn("project:geometry", topics)
        self.assertIn("project:subfields", topics)
        self.assertEqual(s.undo.count(), 1)
        s.undo.undo()
        self.assertEqual(s.snapshot(), before)


class Gestures(unittest.TestCase):
    def test_a_number_typed_is_metres_along_the_pointer_and_two_are_east_and_north(self):
        self.assertEqual(move.typed_offset("3", "", (4.0, 0.0)), (3.0, 0.0))
        dx, dy = move.typed_offset("5", "", (3.0, 4.0))
        self.assertAlmostEqual(dx, 3.0)
        self.assertAlmostEqual(dy, 4.0)
        self.assertEqual(move.typed_offset("3;2", "", (9.0, 9.0)), (3.0, 2.0))
        self.assertEqual(move.typed_offset("2,5;-1", "", (0.0, 0.0)), (2.5, -1.0))
        self.assertEqual(move.typed_offset(";2", "", (0.0, 0.0)), (0.0, 2.0))
        self.assertEqual(move.typed_offset("4", "", (0.0, 0.0)), (4.0, 0.0))     # no direction yet: East
        self.assertIsNone(move.typed_offset("-", "", (1.0, 0.0)))

    def test_tab_gives_the_direction_as_a_bearing_from_north(self):
        dx, dy = move.typed_offset("2", "90", (0.0, 5.0))
        self.assertAlmostEqual(dx, 2.0)
        self.assertAlmostEqual(dy, 0.0)
        g = move.Gesture("building", "b1", (0.0, 0.0), base=(0.0, 0.0))
        for c in "10":
            g.type(c)
        g.tab()
        g.type("180")
        dx, dy = g.offset((3.0, 3.0))
        self.assertAlmostEqual(dx, 0.0)
        self.assertAlmostEqual(dy, -10.0)
        self.assertFalse(g.type("x"))
        g.tab()
        self.assertTrue(g.type(";"))
        self.assertTrue(g.label().startswith("distance"))

    def test_the_offset_follows_the_pointer_from_the_base_point(self):
        g = move.Gesture("building", "b1", (20.0, 10.0), base=(1.0, 1.0))
        self.assertEqual(g.offset((4.0, -1.0)), (3.0, -2.0))

    def test_the_angle_turns_from_where_the_rotation_began_in_steps(self):
        g = move.Gesture("subfield", "s1", (0.0, 0.0))
        g.to_rotate((10.0, 0.0), 0.1)
        self.assertEqual((g.about, g.start), ((0.0, 0.0), (10.0, 0.0)))
        r = math.radians(32.0)
        pointer = (math.cos(r) * 5, math.sin(r) * 5)
        self.assertEqual(g.angle(pointer, move.angle_step(set())), 30.0)
        self.assertEqual(g.angle(pointer, move.angle_step({"ctrl"})), 30.0)
        self.assertEqual(g.angle((0.0, 5.0), move.angle_step({"shift"})), 90.0)
        self.assertEqual(g.angle(pointer, 0.0), 32.0)                     # without snaps, to 0,1°
        g.type("-12,5")
        self.assertEqual(g.angle(pointer, 15.0), -12.5)                   # a value typed wins
        self.assertEqual(g.label(), "angle: -12,5_°")

    def test_r_turns_about_the_base_point_clicked_and_from_east_when_the_pointer_is_on_it(self):
        g = move.Gesture("building", "b1", (20.0, 10.0), base=(0.0, 0.0))
        g.to_rotate((0.0, 0.0), 0.5)
        self.assertEqual((g.about, g.start), ((0.0, 0.0), (1.0, 0.0)))
        self.assertEqual(g.angle((0.0, 3.0), 15.0), 90.0)
        g.cycle((0.0, 0.0), 0.5)                                          # Enter on a grip: back to the move
        self.assertEqual((g.mode, g.base), ("move", (0.0, 0.0)))

    def test_the_arrows_move_by_ten_centimetres_a_metre_with_shift_a_centimetre_with_ctrl(self):
        self.assertEqual(move.nudge("right", set()), (0.1, 0.0))
        self.assertEqual(move.nudge("up", {"shift"}), (0.0, 1.0))
        self.assertEqual(move.nudge("left", {"ctrl"}), (-0.01, 0.0))
        self.assertEqual(move.nudge("down", set()), (0.0, -0.1))
        self.assertIsNone(move.nudge("home", set()))

    def test_the_host_is_the_building_under_the_middle(self):
        p = project()
        b, pitch = move.host(p, [[62, 2], [64, 2], [64, 4], [62, 4]])
        self.assertEqual((b.id, pitch), ("b2", 0))
        self.assertEqual(move.host(p, [[-10, -10], [-8, -10], [-8, -8]]), (None, None))

    def test_heights_for_the_gizmo(self):
        p = project()
        self.assertAlmostEqual(move.height(p, "building", "b1", (20.0, 0.0)), 8.0, places=6)
        self.assertGreater(move.height(p, "subfield", "s1", (20.0, 10.0)), 8.0)    # up the single pitch
        p.exclusions[0].building = None
        self.assertEqual(move.height(p, "exclusion", "e1", (3.0, 3.0)), 0.0)


if __name__ == "__main__":
    unittest.main()
