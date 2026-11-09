"""The year «not up to date» right after opening a project (seen on r17-unita), and what changed when it is (R437)."""
import unittest

import _setup  # noqa: F401

from meridiana import jobs, model
from meridiana.session import ProjectSession


def project():
    p = model.Project(name="Year state")
    p.buildings.append(model.Building(id="b1", name="Shed", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]]))
    p.subfields.append(model.SubField(id="s1", name="South", building="b1", filled=True,
                                    ring=[[1, 1], [39, 1], [39, 19], [1, 19]], params={"tilt": 15.0}))
    return p


class YearState(unittest.TestCase):
    def year(self, s, before=None):
        """As the Quick shell does: the year asked at launch, the layouts of the worker, then the year."""
        generation = s.energy_asked(s._expected_keys())      # quick/bridge.py _asked_year
        if before:
            before(s)
        results, keys, _laid = jobs.layout_of(s.project, s.known_layouts())
        s.layout_done(s.generation, results, keys)
        s.energy_done(generation, {"annual_kwh": 1.0})

    def test_the_year_computed_at_opening_is_up_to_date(self):
        s = ProjectSession(project())
        self.assertEqual(s.layout_keys, {})           # opening: no layout in hand when the year is asked
        self.year(s)
        self.assertFalse(s.year_outdated())
        self.assertEqual(s.year_changes(), [])

    def test_a_change_while_the_year_is_computed_leaves_it_out_of_date_and_says_what(self):
        s = ProjectSession(project())

        def change(session):
            session.edit("tilt", lambda p: p.subfields[0].params.update(tilt=25.0))
        self.year(s, before=change)
        self.assertTrue(s.year_outdated())
        self.assertIn("the layout of the modules", s.year_changes())

    def test_out_of_date_always_says_what_changed(self):
        s = ProjectSession(project())
        self.year(s)
        s.edit("strings", lambda p: p.energy.update(losses={"soiling": 3.0}))
        self.assertTrue(s.year_outdated())
        self.assertTrue(s.year_changes())


if __name__ == "__main__":
    unittest.main()
