"""A sub-field moves freely on its roof (R426): it passes to the pitch that holds most of it, one left astride says so,
«Split on the ridge» makes one sub-field per pitch, moved together. Leaving the building stays refused."""
import unittest

from shapely.geometry import Polygon

from meridiana import checks, layout, model, move, session


def gable() -> model.Project:
    """A shed of 40 x 20 m, a gable roof with its ridge along y = 10, a sub-field on the South pitch."""
    p = model.Project(name="Prova")
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=8.0, roof=model.Roof(type="gable", tilt=15.0)))
    b = p.buildings[0]
    south = next(i for i, q in enumerate(b.pitches()) if Polygon(q.ring).centroid.y < 10)
    p.subfields.append(model.SubField(id="s1", name="Tetto", ring=[[10, 2], [20, 2], [20, 8], [10, 8]],
                                      building="b1", pitch=b.pitch_ref(south), filled=True,
                                      params={"mounting": "coplanar"}))
    return p


def on_pitch(p, sf):
    """Which way the pitch under the sub-field faces: its centroid above or below the ridge."""
    b = p.building(sf.building)
    return "north" if Polygon(b.pitches()[b.pitch_index(sf.pitch)].ring).centroid.y > 10 else "south"


class FreeOnTheRoof(unittest.TestCase):
    def test_astride_a_ridge_it_moves_and_passes_only_when_most_of_it_is_over(self):
        s = session.ProjectSession(gable())
        s.edit("Move", move.translate(s.project, "subfield", "s1", 0.0, 4.0))     # 10 to 14: 2/3 of it South... half
        sf = s.project.subfields[0]
        self.assertEqual(sf.ring[0], [10.0, 6.0])
        self.assertEqual(on_pitch(s.project, sf), "south")
        s.edit("Move", move.translate(s.project, "subfield", "s1", 0.0, 3.0))     # 9 to 15: three quarters over
        self.assertEqual(on_pitch(s.project, sf), "north")

    def test_the_undo_of_a_passage_gives_the_pitch_back(self):
        s = session.ProjectSession(gable())
        s.edit("Move", move.translate(s.project, "subfield", "s1", 0.0, 10.0))
        self.assertEqual(on_pitch(s.project, s.project.subfields[0]), "north")
        s.undo.undo()
        self.assertEqual(on_pitch(s.project, s.project.subfields[0]), "south")

    def test_a_rotation_settles_as_a_move_does(self):
        s = session.ProjectSession(gable())
        s.edit("Move", move.translate(s.project, "subfield", "s1", 0.0, 3.0))     # 5 to 11, mostly South
        s.edit("Turn", move.rotate(s.project, "subfield", "s1", 15.0, 10.0, 180.0))     # about the ridge: mostly North
        self.assertEqual(on_pitch(s.project, s.project.subfields[0]), "north")

    def test_it_stays_refused_out_of_the_building_with_the_reason(self):
        s = session.ProjectSession(gable())
        before = s.snapshot()
        with self.assertRaises(ValueError) as caught:
            s.edit("Move", move.translate(s.project, "subfield", "s1", 0.0, -8.0))
        self.assertIn("building", str(caught.exception))
        self.assertEqual(s.snapshot(), before)

    def test_on_the_ground_the_rules_are_those_of_before(self):
        p = gable()
        p.subfields.append(model.SubField(id="g1", name="Prato", ring=[[50, 0], [60, 0], [60, 10], [50, 10]]))
        s = session.ProjectSession(p)
        s.edit("Move", move.translate(s.project, "subfield", "g1", 5.0, 0.0))
        with self.assertRaises(ValueError) as caught:
            s.edit("Move", move.translate(s.project, "subfield", "g1", -30.0, 0.0))
        self.assertIn("ground", str(caught.exception))

    def test_a_flush_sub_field_lays_on_the_plane_it_passed_to(self):
        p = gable()
        move.translate(p, "subfield", "s1", 0.0, 10.0)(p)
        sf = p.subfields[0]
        b = p.building("b1")
        self.assertEqual(p.surface_of(sf).azimuth, b.pitches()[b.pitch_index(sf.pitch)].azimuth)

    def test_rows_by_hand_turn_with_the_plane_they_pass_to(self):
        p = gable()
        sf = p.subfields[0]
        before = p.surface_of(sf).azimuth
        sf.manual = True
        sf.rows = [layout.Row("f1", 11.0, 3.0, before, [0.0, 1.2]).as_dict()]
        move.translate(p, "subfield", "s1", 0.0, 10.0)(p)
        self.assertAlmostEqual(abs(sf.rows[0]["azimuth"]), abs(p.surface_of(sf).azimuth))
        self.assertNotEqual(on_pitch(p, sf), "south")
        self.assertTrue(Polygon(sf.ring).buffer(.01).covers(Polygon(sf.ring).centroid))


class Astride(unittest.TestCase):
    def test_astride_says_the_pitch_and_the_area_on_the_others(self):
        p = gable()
        move.translate(p, "subfield", "s1", 0.0, 6.0)(p)        # y 8 to 14: 2 m south, 4 m north of the ridge
        lying = move.straddle(p, p.subfields[0])
        self.assertEqual(on_pitch(p, p.subfields[0]), "north")
        self.assertAlmostEqual(lying.other_area, 20.0, places=3)

    def test_whole_on_a_pitch_or_on_the_ground_or_on_a_single_pitch_says_nothing(self):
        p = gable()
        self.assertIsNone(move.straddle(p, p.subfields[0]))
        p.subfields[0].building = None
        self.assertIsNone(move.straddle(p, p.subfields[0]))

    def test_the_checks_say_it_with_the_split_as_their_fix(self):
        p = gable()
        move.translate(p, "subfield", "s1", 0.0, 6.0)(p)
        found = [i for i in checks.gather(p, {}, None) if i.fix[:2] == ("action", "split_pitches")]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].level, "warn")
        self.assertLessEqual(len(found[0].text), checks.TEXT_LENGTH)
        self.assertEqual(found[0].target, ("subfield", "s1"))


class Split(unittest.TestCase):
    def astride(self):
        s = session.ProjectSession(gable())
        s.edit("Move", move.translate(s.project, "subfield", "s1", 0.0, 6.0))
        return s

    def test_one_sub_field_per_pitch_each_on_its_own_and_one_undo(self):
        s = self.astride()
        undos = s.undo.count()
        s.edit("Split", move.split_on_pitches(s.project, "s1"))
        self.assertEqual(s.undo.count(), undos + 1)
        made = s.project.subfields
        self.assertEqual(len(made), 2)
        self.assertEqual({on_pitch(s.project, x) for x in made}, {"north", "south"})
        self.assertEqual(sum(Polygon(x.ring).area for x in made), 60.0)
        self.assertTrue(all(move.straddle(s.project, x) is None for x in made))
        self.assertEqual(made[0].group, made[1].group)
        self.assertTrue(made[0].group)
        self.assertEqual(made[0].id, "s1")                 # the largest keeps the id, so the selection stays valid
        self.assertEqual(made[1].params, made[0].params)
        self.assertTrue(made[1].filled)
        s.undo.undo()
        self.assertEqual([x.id for x in s.project.subfields], ["s1"])
        self.assertEqual(s.project.subfields[0].group, "")
        s.undo.redo()
        self.assertEqual(len(s.project.subfields), 2)

    def test_the_parts_move_and_turn_together_with_one_undo(self):
        s = self.astride()
        s.edit("Split", move.split_on_pitches(s.project, "s1"))
        rings = [list(map(list, x.ring)) for x in s.project.subfields]
        undos = s.undo.count()
        s.edit("Move", move.translate(s.project, "subfield", "s1", 5.0, 0.0))
        self.assertEqual(s.undo.count(), undos + 1)
        for x, ring in zip(s.project.subfields, rings, strict=True):
            self.assertEqual(x.ring[0][0], ring[0][0] + 5.0)
        s.undo.undo()
        self.assertEqual([list(map(list, x.ring)) for x in s.project.subfields], rings)

    def test_what_moves_shows_the_whole_group_and_turns_about_its_middle(self):
        s = self.astride()
        s.edit("Split", move.split_on_pitches(s.project, "s1"))
        self.assertEqual(len(move.moving(s.project, "subfield", "s1")), 2)
        self.assertEqual(move.centre(s.project, "subfield", "s1"), (15.0, 11.0))

    def test_a_group_refused_whole_when_one_part_would_leave(self):
        s = self.astride()
        s.edit("Split", move.split_on_pitches(s.project, "s1"))
        before = s.snapshot()
        with self.assertRaises(ValueError):
            s.edit("Move", move.translate(s.project, "subfield", "s1", 0.0, 7.0))
        self.assertEqual(s.snapshot(), before)

    def test_a_sub_field_whole_on_a_pitch_has_nothing_to_split(self):
        p = gable()
        with self.assertRaises(ValueError):
            move.split_on_pitches(p, "s1")

    def test_a_sliver_makes_no_sub_field(self):
        p = gable()
        p.subfields[0].ring = [[10, 2], [20, 2], [20, 10.01], [10, 10.01]]
        with self.assertRaises(ValueError):
            move.split_on_pitches(p, "s1")

    def test_rows_by_hand_give_way_to_the_layout_and_the_undo_brings_them_back(self):
        s = self.astride()
        def by_hand(p):
            sf = p.subfields[0]
            sf.manual, sf.removed = True, ["f1:0"]
            sf.rows = [layout.Row("f1", 11.0, 9.0, p.surface_of(sf).azimuth, [0.0, 1.2]).as_dict()]
        s.edit("Rows", by_hand)
        s.edit("Split", move.split_on_pitches(s.project, "s1"))
        for x in s.project.subfields:
            self.assertEqual((x.manual, x.rows, x.removed), (False, [], []))
        s.undo.undo()
        self.assertTrue(s.project.subfields[0].manual)
        self.assertEqual(len(s.project.subfields[0].rows), 1)

    def test_a_copy_of_a_part_stands_on_its_own(self):
        s = self.astride()
        s.edit("Split", move.split_on_pitches(s.project, "s1"))
        made = []
        s.edit("Copy", lambda p: made.append(p.duplicate("subfield", "s1", (0.0, 0.0))))
        self.assertEqual(s.project.subfields[-1].group, "")

    def test_leaving_the_group_lets_a_part_move_alone(self):
        s = self.astride()
        s.edit("Split", move.split_on_pitches(s.project, "s1"))
        other = s.project.subfields[1].ring[0][0]
        s.edit("Apart", move.leave_group(s.project, "s1"))
        s.edit("Move", move.translate(s.project, "subfield", "s1", 1.0, 0.0))
        self.assertEqual(s.project.subfields[1].ring[0][0], other)


if __name__ == "__main__":
    unittest.main()
