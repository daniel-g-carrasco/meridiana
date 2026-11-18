"""Copy, cut and paste (R432): a sub-field takes the plane of where it falls, by the rule of the moves (R426); what
cannot stand is refused with the reason; strings are not copied; one undo step."""
import unittest

from shapely.geometry import Polygon

from meridiana import checks, clipboard, layout, model, session
from meridiana.energy import plant


def project() -> model.Project:
    p = model.Project(name="Prova")
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=8.0, roof=model.Roof(type="gable", tilt=15.0)))
    p.buildings.append(model.Building(id="b2", name="Uffici", footprint=[[60, 0], [80, 0], [80, 20], [60, 20]],
                                      height=6.0))
    b = p.buildings[0]
    south = next(i for i, q in enumerate(b.pitches()) if Polygon(q.ring).centroid.y < 10)
    p.modules["mio"] = dict(model.GENERIC_MODULES["generic-550"])
    p.subfields.append(model.SubField(id="s1", name="Tetto", ring=[[10, 2], [20, 2], [20, 8], [10, 8]], building="b1",
                                      pitch=b.pitch_ref(south), filled=True, module="mio",
                                      params={"mounting": "coplanar", "inverter": 2, "mppt": 1}))
    p.exclusions.append(model.ExclusionItem(id="e1", ring=[[2, 2], [4, 2], [4, 4], [2, 4]], kind="skylight",
                                            building="b1"))
    p.props.append(model.Prop(id="o1", kind="broadleaf", at=[-20.0, -20.0]))
    return p


def paste(s, clip, point):
    made = []
    s.edit("Paste", lambda p: made.extend(clipboard.paste(p, clip, point)(p)))
    return made


class SubField(unittest.TestCase):
    def test_pasted_on_the_other_pitch_it_takes_its_plane_and_keeps_module_and_mounting(self):
        s = session.ProjectSession(project())
        clip = clipboard.take(s.project, "subfield", "s1")
        made = paste(s, clip, (15.0, 15.0))
        sf = s.subfield(made[0])
        b = s.project.building("b1")
        self.assertGreater(Polygon(b.pitches()[b.pitch_index(sf.pitch)].ring).centroid.y, 10)
        north = s.project.surface_of(sf)
        south = s.project.surface_of(s.subfield("s1"))
        self.assertAlmostEqual(abs(north.azimuth - south.azimuth), 180.0)
        self.assertEqual(sf.module, "mio")
        self.assertEqual(sf.params["mounting"], "coplanar")
        self.assertTrue(sf.filled)
        self.assertNotEqual(sf.id, "s1")
        self.assertEqual(Polygon(sf.ring).centroid.coords[0], (15.0, 15.0))

    def test_on_a_flat_roof_a_flush_mounting_cannot_stand_and_changes(self):
        s = session.ProjectSession(project())
        made = paste(s, clipboard.take(s.project, "subfield", "s1"), (70.0, 10.0))
        sf = s.subfield(made[0])
        self.assertEqual(sf.building, "b2")
        self.assertEqual(sf.params["mounting"], "tilted_anchored")
        self.assertEqual(s.project.surface_of(sf).tilt, 0.0)

    def test_on_the_ground_it_is_said(self):
        s = session.ProjectSession(project())
        clip = clipboard.take(s.project, "subfield", "s1")
        self.assertIn("ground", clipboard.where(s.project, clip, (15.0, -30.0)))
        made = paste(s, clip, (15.0, -30.0))
        sf = s.subfield(made[0])
        self.assertIsNone(sf.building)
        self.assertEqual(sf.params["mounting"], "ground")

    def test_half_off_a_roof_it_is_refused_with_the_reason_and_nothing_changes(self):
        s = session.ProjectSession(project())
        clip = clipboard.take(s.project, "subfield", "s1")
        before = s.snapshot()
        self.assertTrue(clipboard.refused(s.project, clip, (15.0, 1.0)))
        with self.assertRaises(ValueError) as caught:
            clipboard.paste(s.project, clip, (15.0, 1.0))
        self.assertIn("Capannone", str(caught.exception))
        self.assertEqual(s.snapshot(), before)

    def test_astride_a_ridge_it_lies_on_the_pitch_with_most_of_it(self):
        s = session.ProjectSession(project())
        made = paste(s, clipboard.take(s.project, "subfield", "s1"), (15.0, 11.0))
        sf = s.subfield(made[0])
        b = s.project.building("b1")
        self.assertGreater(Polygon(b.pitches()[b.pitch_index(sf.pitch)].ring).centroid.y, 10)

    def test_strings_are_not_copied_and_the_phase_says_so(self):
        p = project()
        p.energy["strings"] = {"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/f1:0", "s1/f1:1"]}]}
        s = session.ProjectSession(p)
        made = paste(s, clipboard.take(s.project, "subfield", "s1"), (15.0, 15.0))
        sf = s.subfield(made[0])
        self.assertNotIn("inverter", sf.params)
        self.assertNotIn("mppt", sf.params)
        self.assertEqual(s.project.energy["strings"]["runs"][0]["modules"], ["s1/f1:0", "s1/f1:1"])
        self.assertFalse(any(m.startswith(made[0] + "/") for r in s.project.energy["strings"]["runs"]
                             for m in r["modules"]))
        results = {x.id: s.project.fill(x) for x in s.project.subfields}
        said = [i.text for i in checks.plant_items(plant.build(s.project, results))]
        self.assertTrue(any("in no string" in text for text in said), said)

    def test_rows_by_hand_are_laid_again_on_the_new_plane(self):
        p = project()
        sf = p.subfields[0]
        sf.manual, sf.removed = True, ["f1:0"]
        sf.rows = [layout.Row("f1", 11.0, 3.0, p.surface_of(sf).azimuth, [0.0, 1.2]).as_dict()]
        s = session.ProjectSession(p)
        made = paste(s, clipboard.take(s.project, "subfield", "s1"), (15.0, 15.0))
        new = s.subfield(made[0])
        self.assertEqual((new.manual, new.rows, new.removed), (False, [], []))

    def test_the_parts_of_a_split_are_taken_together(self):
        from meridiana import move
        p = project()
        p.subfields[0].ring = [[10, 7], [20, 7], [20, 13], [10, 13]]
        move.split_on_pitches(p, "s1")(p)
        s = session.ProjectSession(p)
        clip = clipboard.take(s.project, "subfield", "s1")
        self.assertEqual(len(clip.subfields), 2)
        made = paste(s, clip, (30.0, 10.0))
        new = [s.subfield(i) for i in made]
        self.assertEqual(len(new), 2)
        self.assertTrue(new[0].group)
        self.assertEqual(new[0].group, new[1].group)
        self.assertNotEqual(new[0].group, s.subfield("s1").group)


class Others(unittest.TestCase):
    def test_a_building_comes_with_what_stands_on_it(self):
        s = session.ProjectSession(project())
        made = paste(s, clipboard.take(s.project, "building", "b1"), (20.0, 60.0))
        b = s.project.building(made[0])
        self.assertEqual(b.footprint[0], [0.0, 50.0])
        self.assertEqual(len([x for x in s.project.subfields if x.building == b.id]), 1)
        self.assertEqual(len([x for x in s.project.exclusions if x.building == b.id]), 1)
        self.assertEqual([x for x in s.project.subfields if x.building == b.id][0].ring[0], [10.0, 52.0])

    def test_an_exclusion_belongs_to_where_it_falls(self):
        s = session.ProjectSession(project())
        made = paste(s, clipboard.take(s.project, "exclusion", "e1"), (70.0, 10.0))
        self.assertEqual(next(e for e in s.project.exclusions if e.id == made[0]).building, "b2")

    def test_a_3d_object_belongs_to_where_it_falls(self):
        s = session.ProjectSession(project())
        made = paste(s, clipboard.take(s.project, "prop", "o1"), (70.0, 10.0))
        self.assertEqual(s.project.prop(made[0]).building, "b2")

    def test_nothing_else_can_be_taken(self):
        with self.assertRaises(ValueError):
            clipboard.take(project(), "site", "")
        with self.assertRaises(ValueError):
            clipboard.take(project(), "subfield", "nope")


class Cut(unittest.TestCase):
    def test_cut_takes_it_off_with_its_references_in_the_strings_and_undo_brings_it_back(self):
        p = project()
        p.energy["strings"] = {"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/f1:0"]},
                                        {"inverter": 1, "mppt": 2, "modules": ["s9/f1:0"]}]}
        s = session.ProjectSession(p)
        clip = clipboard.take(s.project, "subfield", "s1")
        s.edit("Cut", clipboard.cut(clip))
        self.assertIsNone(s.subfield("s1"))
        self.assertEqual([r["modules"] for r in s.project.energy["strings"]["runs"]], [["s9/f1:0"]])
        s.undo.undo()
        self.assertIsNotNone(s.subfield("s1"))
        self.assertEqual(len(s.project.energy["strings"]["runs"]), 2)

    def test_a_cut_and_its_paste_join_in_one_undo(self):
        s = session.ProjectSession(project())
        before = s.snapshot()
        clip = clipboard.take(s.project, "subfield", "s1")
        s.edit("Cut", clipboard.cut(clip))
        paste(s, clip, (15.0, 15.0))
        self.assertTrue(s.undo.join_last())
        self.assertEqual(s.undo.count(), 1)
        s.undo.undo()
        self.assertEqual(s.snapshot(), before)
        s.undo.redo()
        self.assertEqual(len(s.project.subfields), 1)
        self.assertNotEqual(s.project.subfields[0].id, "")


if __name__ == "__main__":
    unittest.main()
