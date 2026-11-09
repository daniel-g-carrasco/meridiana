"""R410, R413 (Daniel, 05/11/2026): a ridge drawn off the axis stands where it is drawn; the ridge kept when the slope or
the eave is written, as the default, with the eave kept as the choice."""
import math
import unittest

from meridiana import model, roof_vertices, roofs


def rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


class RidgeOffTheAxis(unittest.TestCase):
    def pitches(self, points, ridge=None):
        return roofs.off_axis_pitches(rect(0, 0, 40, 20), points, 6.0, ridge, 20.0)

    def ridge_line(self, faces):
        return {(round(x, 2), round(y, 2)) for f in faces for (x, y), z in zip(f["ring"], f["z"], strict=True) if z == max(f["z"])}

    def test_from_side_to_side_two_pitches_with_the_ridge_where_it_is_drawn(self):
        faces = self.pitches([(1, 14), (39, 14)], 10.0)
        self.assertEqual(len(faces), 2)
        self.assertEqual(self.ridge_line(faces), {(0.0, 14.0), (40.0, 14.0)})

    def test_an_outline_drawn_clockwise_too(self):
        faces = roofs.off_axis_pitches(rect(0, 0, 40, 20)[::-1], [(1, 14), (39, 14)], 6.0, 10.0, 20.0)
        self.assertEqual(self.ridge_line(faces), {(0.0, 14.0), (40.0, 14.0)})

    def test_it_ends_inside_with_a_hip(self):
        faces = self.pitches([(8, 14), (32, 14)], 10.0)
        self.assertEqual(len(faces), 4)
        self.assertEqual(self.ridge_line(faces), {(8.0, 14.0), (32.0, 14.0)})

    def test_a_real_building_takes_them_each_with_its_slope_and_one_ridge(self):
        b = model.Building("b1", "B", rect(0, 0, 40, 20), 6.0)
        faces = self.pitches([(1, 14), (39, 14)], 10.0)
        b.roof.type, b.roof.free_pitches = "free", faces
        roof_vertices.settled(b, range(len(faces)))
        found = b.pitches()
        self.assertEqual(len(found), 2)
        self.assertEqual(len(b.solved().folds), 0)
        tilts = sorted(round(p.tilt, 2) for p in found)
        self.assertEqual(tilts, [round(math.degrees(math.atan(4/6)), 2), round(math.degrees(math.atan(4/14)), 2)][::-1])
        self.assertAlmostEqual(b.ridge(), 10.0, places=2)

    def test_from_ridge_says_it_is_off_and_on_the_axis_nothing_changes(self):
        ring = rect(0, 0, 40, 20)
        self.assertTrue(roofs.from_ridge(ring, [(1, 14), (39, 14)], 6.0, 20.0).off_axis)
        self.assertFalse(roofs.from_ridge(ring, [(1, 10), (39, 10)], 6.0, 20.0).off_axis)

    def test_an_l_keeps_the_axis_rule(self):
        ring = [[0, 0], [20, 0], [20, 10], [10, 10], [10, 20], [0, 20]]
        self.assertIsNone(roofs.off_axis_pitches(ring, [(2, 5), (18, 5)], 6.0, None, 20.0))


class RidgeKept(unittest.TestCase):
    def test_free_pitch_eave_written_slope_follows(self):
        ring = rect(0, 0, 10, 10)
        eave, tilt = roofs.free_keeping_ridge(ring, 0, 6.0, 30.0, new_eave=7.0)
        self.assertEqual(eave, 7.0)
        self.assertAlmostEqual(roofs.free_ridge(ring, 0, eave, tilt), roofs.free_ridge(ring, 0, 6.0, 30.0))
        self.assertLess(tilt, 30.0)

    def test_free_pitch_slope_written_eave_follows(self):
        ring = rect(0, 0, 10, 10)
        eave, tilt = roofs.free_keeping_ridge(ring, 0, 6.0, 30.0, new_tilt=20.0)
        self.assertEqual(tilt, 20.0)
        self.assertAlmostEqual(roofs.free_ridge(ring, 0, eave, tilt), roofs.free_ridge(ring, 0, 6.0, 30.0), places=2)
        self.assertGreater(eave, 6.0)

    def test_free_pitch_refused_when_they_cannot_meet(self):
        ring = rect(0, 0, 10, 10)
        with self.assertRaises(ValueError):
            roofs.free_keeping_ridge(ring, 0, 6.0, 30.0, new_eave=30.0)
        with self.assertRaises(ValueError):
            roofs.free_keeping_ridge(ring, 0, 2.0, 10.0, new_tilt=60.0)

    def test_a_pitch_lying_flat_has_no_ridge_to_keep(self):
        ring = rect(0, 0, 10, 10)
        self.assertEqual(roofs.free_keeping_ridge(ring, 0, 6.0, 0.0, new_eave=7.0), (7.0, 0.0))
        self.assertEqual(roofs.free_keeping_ridge(ring, 0, 6.0, 0.0, new_tilt=7.0), (6.0, 7.0))

    def building(self, kind):
        b = model.Building("b1", "B", rect(0, 0, 40, 20), 6.0)
        b.roof.type, b.roof.tilt = kind, 20.0
        return b

    def apply(self, b, changes):
        for path, value in changes.items():
            head, _, tail = path.partition(".")
            setattr(getattr(b, head), tail, value) if tail else setattr(b, head, value)

    def test_generated_roofs_keep_their_ridge_by_default(self):
        for kind in ("mono", "gable", "hip"):
            with self.subTest(kind=kind):
                b = self.building(kind)
                top = b.ridge()
                self.apply(b, b.eave_written(7.5))
                self.assertEqual(b.height, 7.5)
                self.assertAlmostEqual(b.ridge(), top, places=2)
                self.assertLess(b.slope(), 20.0)
                self.apply(b, b.slope_written(15.0))
                self.assertAlmostEqual(b.slope(), 15.0, places=2)
                self.assertAlmostEqual(b.ridge(), top, places=2)

    def test_with_the_eave_kept_as_before(self):
        for kind in ("mono", "gable", "hip"):
            with self.subTest(kind=kind):
                b = self.building(kind)
                b.roof.keep_eave = True
                top = b.ridge()
                self.assertEqual(b.eave_written(7.5), {"height": 7.5})
                self.apply(b, b.slope_written(30.0))
                self.assertEqual(b.height, 6.0)
                self.assertGreater(b.ridge(), top)

    def test_a_flat_roof_and_a_canopy_change_only_their_height(self):
        b = model.Building("b1", "B", rect(0, 0, 40, 20), 6.0)
        self.assertEqual(b.eave_written(7.5), {"height": 7.5})

    def test_the_choice_is_not_a_shape_and_goes_through_a_save(self):
        b = self.building("gable")
        key = b.geometry_key()
        b.roof.keep_eave = True
        self.assertEqual(b.geometry_key(), key)
        p = model.Project()
        p.buildings.append(b)
        again = model.Project.from_json(p.to_json())
        self.assertTrue(again.buildings[0].roof.keep_eave)


if __name__ == "__main__":
    unittest.main()
