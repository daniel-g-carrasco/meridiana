"""R442: the strings follow the modules laid, and optimizer groups follow the strings."""
import unittest

import _setup  # noqa: F401

from meridiana import jobs, model
from meridiana.energy import plant
from meridiana.session import ProjectSession


def project():
    p = model.Project(name="Realign")
    p.buildings.append(model.Building(id="b1", name="Shed", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]]))
    p.subfields.append(model.SubField(id="s1", name="South", building="b1", filled=True,
                                    ring=[[1, 1], [39, 1], [39, 19], [1, 19]], params={"tilt": 15.0}))
    return p


class Realign(unittest.TestCase):
    def test_lost_keys_leave_and_the_optimizer_groups_follow(self):
        runs = [{"inverter": 1, "mppt": 1, "modules": ["s1/a", "s1/b", "s1/c", "s1/d"], "optimizer_group_sizes": [2, 2]},
                {"inverter": 1, "mppt": 2, "modules": ["s1/x"]},
                {"inverter": 1, "mppt": 2, "modules": ["s2/q"]}]
        after, gone = plant.realign(runs, {"s1/a", "s1/c", "s1/d", "s2/q"})
        self.assertEqual(after[0]["modules"], ["s1/a", "s1/c", "s1/d"])
        self.assertEqual(after[0]["optimizer_group_sizes"], [1, 2], "each optimizer keeps the modules left on it")
        self.assertEqual(len(after), 2, "a string left empty goes")
        self.assertEqual(gone, [("1.1.1", 1, ["s1"]), ("1.2.1", 1, ["s1"])])
        kept, gone = plant.realign(runs, set(), kept={"s1", "s2"})
        self.assertEqual((kept, gone), (runs, []))

    def test_groups_that_no_longer_split_their_string_are_made_again(self):
        run = {"inverter": 1, "mppt": 1, "modules": ["a", "b", "c", "d", "e"], "optimizer_group_sizes": [2, 2]}
        self.assertEqual(plant.regrouped(run)["optimizer_group_sizes"], [2, 2, 1])
        self.assertEqual(plant.touched({}, [run])["runs"][0]["optimizer_group_sizes"], [2, 2, 1])
        fine = dict(run, optimizer_group_sizes=[1, 2, 2])
        self.assertIs(plant.regrouped(fine), fine)

    def test_the_string_of_the_energy_keeps_the_groups_of_its_modules_still_laid(self):
        self.assertEqual(plant._kept_sizes(["a", "b", "c", "d"], [2, 2], ["a", "c", "d"]), [1, 2])
        self.assertEqual(plant._kept_sizes(["a", "b", "c"], [2, 2], ["a", "b", "c"]), [])
        self.assertEqual(plant._kept_sizes(["a", "b"], [2], ["a", "b"]), [2])

    def test_a_new_layout_after_a_change_takes_the_lost_modules_out_and_says_so(self):
        s = ProjectSession(project())
        results, keys, _laid = jobs.layout_of(s.project)
        s.layout_done(s.generation, results, keys)
        mods = results["s1"].modules
        s.edit("strings", lambda p: p.energy.update(strings={"runs": [
            {"inverter": 1, "mppt": 1, "modules": [f"s1/{m.key}" for m in mods[:10]]}]}))
        self.assertEqual(s.realigned, [])
        gone = [m.key for m in mods[:3]]
        s.edit("out", lambda p: p.subfields[0].removed.extend(gone))
        results, keys, _laid = jobs.layout_of(s.project, s.known_layouts())
        s.layout_done(s.generation, results, keys)
        self.assertEqual(s.realigned, [("1.1.1", 3, ["South"])])
        self.assertEqual(s.project.energy["strings"]["runs"][0]["modules"], [f"s1/{m.key}" for m in mods[3:10]])
        text = s.realigned_text(s.realigned)
        self.assertIn("3", text)
        self.assertIn("1.1.1", text)
        self.assertIn("South", text)
        s.undo_step() if hasattr(s, "undo_step") else None

    def test_study41_the_layout_and_the_strings_realigned_on_it_told_in_one_round(self):
        # Study 41 (08/11/2026): the layout that comes back and the amend of the strings it realigns were two rounds of
        # every view; now one, with the topics of both, after both are in the project.
        s = ProjectSession(project())
        results, keys, _laid = jobs.layout_of(s.project)
        s.layout_done(s.generation, results, keys)
        mods = results["s1"].modules
        s.edit("strings", lambda p: p.energy.update(strings={"runs": [
            {"inverter": 1, "mppt": 1, "modules": [f"s1/{m.key}" for m in mods[:10]]}]}))
        s.edit("out", lambda p: p.subfields[0].removed.extend([mods[0].key]))
        told = []
        s.subscribe(lambda topics: told.append((set(topics), list(s.project.energy["strings"]["runs"][0]["modules"]))))
        results, keys, _laid = jobs.layout_of(s.project, s.known_layouts())
        s.layout_done(s.generation, results, keys)
        self.assertEqual(len(told), 1, told)
        topics, runs = told[0]
        self.assertIn("layout:s1", topics)
        self.assertIn("project:energy", topics)
        self.assertNotIn(f"s1/{mods[0].key}", runs, "the listeners see the strings already realigned")
        with s.held():
            s.changed("a")
            with s.held():
                s.changed("b")
            self.assertEqual(len(told), 1)
        self.assertEqual(told[-1][0], {"a", "b"})

    def test_a_project_just_opened_is_left_as_saved(self):
        p = project()
        p.energy["strings"] = {"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/gone:1"]}]}
        s = ProjectSession(p)
        results, keys, _laid = jobs.layout_of(s.project)
        s.layout_done(s.generation, results, keys)
        self.assertEqual(s.realigned, [])
        self.assertEqual(s.project.energy["strings"]["runs"][0]["modules"], ["s1/gone:1"])


if __name__ == "__main__":
    unittest.main()
