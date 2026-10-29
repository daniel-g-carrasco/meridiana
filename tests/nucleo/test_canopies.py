"""Parking canopies retain the actual inclined placement geometry, not just a 2D outline."""
import math
import unittest

import _setup  # noqa: F401
from meridiana import canopies, model, session


class Canopies(unittest.TestCase):
    def test_two_opposed_rows_keep_clearance_and_a_common_ridge_after_rotation(self):
        p = model.Project()
        spec = canopies.Spec(stalls=4, rows=2, bay_width=2.5, depth=5, clearance=2.7, tilt=10, turn=37)
        fields = canopies.fields(spec, (30, -20))
        self.assertEqual(len(fields), 2)
        p.subfields = fields
        self.assertEqual(len({sf.id for sf in fields}), 2)
        self.assertAlmostEqual(abs(fields[0].support.azimuth - fields[1].support.azimuth), 180)
        for sf in fields:
            surface = p.surface_of(sf)
            heights = [surface.z(*point) for point in sf.ring]
            self.assertAlmostEqual(min(heights), 2.7)
            self.assertAlmostEqual(max(heights), 2.7 + 5 * math.tan(math.radians(10)))
            result = p.fill(sf)
            self.assertTrue(result.modules)
            for pm in result.modules:
                self.assertAlmostEqual(pm.tilt, 10)
                self.assertAlmostEqual(pm.azimuth, sf.support.azimuth)
        for left, right in zip(fields[0].ring[2:], [fields[1].ring[1], fields[1].ring[0]], strict=True):
            self.assertEqual(left, right)

    def test_add_is_one_undo_step_and_round_trips_with_unique_ids(self):
        p = model.Project()
        p.subfields = canopies.fields(canopies.Spec(), (0, 0))
        s = session.ProjectSession(p)
        s.edit('Carport', lambda project: canopies.add(project, canopies.Spec(rows=2), (100, 50)))
        self.assertEqual(len(s.project.subfields), 3)
        self.assertEqual(len({sf.id for sf in s.project.subfields}), 3)
        back = model.Project.from_json(s.project.to_json())
        self.assertEqual(back.subfields, s.project.subfields)
        s.undo.undo()
        self.assertEqual(len(s.project.subfields), 1)
        s.undo.redo()
        self.assertEqual(len(s.project.subfields), 3)

    def test_invalid_geometry_is_rejected_before_it_reaches_the_project(self):
        for values in ({'rows': 3}, {'stalls': 0}, {'clearance': -1}, {'tilt': 90}, {'depth': math.nan}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                canopies.fields(canopies.Spec(**values), (0, 0))
