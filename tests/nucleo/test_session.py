"""The session without Qt (session.py): the undo by snapshots with its merge, its limit and its clean point;
an edit that fails leaves the project as it was; the variants; the results that are kept or dropped by
generation; what counts as modified; the files, the revisions and the recovery copies."""

import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401
from _fixtures import capannone as sample

from meridiana import model, recovery, session


def rename(name: str):
    return lambda p: setattr(p.buildings[0], "name", name)


class Undo(unittest.TestCase):
    def test_an_edit_is_one_step_back_and_forth(self):
        s = session.ProjectSession(sample())
        told = []
        s.subscribe(lambda topics: told.append(set(topics)))
        self.assertEqual(s.edit("Rename", rename("Magazzino")), {"project:text", "checks"})
        self.assertEqual(s.project.buildings[0].name, "Magazzino")
        self.assertEqual((s.undo.count(), s.undo.undo_text()), (1, "Rename"))
        s.undo.undo()
        self.assertEqual(s.project.buildings[0].name, "Capannone")
        self.assertEqual(s.undo.redo_text(), "Rename")
        s.undo.redo()
        self.assertEqual(s.project.buildings[0].name, "Magazzino")
        self.assertEqual(told, [{"project:text", "checks"}, {"restored", "project:text", "checks"},
                                {"restored", "project:text", "checks"}])

    def test_an_edit_that_changes_nothing_is_no_step_and_nobody_is_told(self):
        s = session.ProjectSession(sample())
        told = []
        s.subscribe(lambda topics: told.append(set(topics)))
        self.assertEqual(s.edit("Nothing", lambda p: None), set())
        self.assertEqual((s.undo.count(), told), (0, []))
        self.assertFalse(s.dirty())

    def test_what_the_program_writes_down_by_itself_is_no_step_and_leaves_a_saved_project_saved(self):
        """session.amend (R114): an older project's proposal of strings written down at its first layout: told as an
        edit, no step to undo, and a project that was saved still counts as saved; one with changes stays modified."""
        s = session.ProjectSession(sample())
        told = []
        s.subscribe(lambda topics: told.append(set(topics)))
        strings = {"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/f1:0"]}]}
        self.assertEqual(s.amend(lambda p: p.energy.__setitem__("strings", strings)), {"project:energy", "checks"})
        self.assertEqual((s.project.energy["strings"], s.undo.count(), s.dirty()), (strings, 0, False))
        self.assertEqual(told, [{"project:energy", "checks"}])
        s.edit("Rename", rename("Magazzino"))
        s.amend(lambda p: p.energy.__setitem__("strings", {}))
        self.assertTrue(s.dirty())
        with self.assertRaises(ZeroDivisionError):
            s.amend(lambda p: (p.energy.__setitem__("strings", None), 1 / 0))
        self.assertEqual(s.project.energy["strings"], {})                   # put back as it was

    def test_an_edit_that_fails_leaves_the_project_as_it_was(self):
        s = session.ProjectSession(sample())
        told = []
        s.subscribe(lambda topics: told.append(set(topics)))

        def half(p):
            p.buildings.append(model.Building(id="bZ", name="ghost", footprint=[[0, 0], [1, 0], [1, 1]]))
            raise ZeroDivisionError("a value impossible")
        with self.assertRaises(ZeroDivisionError):
            s.edit("Half done", half)
        self.assertEqual([b.id for b in s.project.buildings], ["b1"])
        self.assertEqual(s.undo.count(), 0)
        self.assertFalse(s.dirty())
        self.assertEqual(told, [])
        # a change of the model that raises (a variant that cannot go) is the same
        with self.assertRaises(ValueError):
            s.edit("Delete", lambda p: p.remove_variant(p.variant))
        self.assertEqual(s.project.variants, [{"id": "v1", "name": "Base", "note": ""}])

    def test_the_same_number_changed_again_within_a_moment_is_one_step(self):
        s = session.ProjectSession(sample())
        for tilt in (16.0, 17.0, 18.0):
            s.edit("Tilt", lambda p, t=tilt: p.subfields[0].params.__setitem__("tilt", t), merge=("tilt", "s1"))
        self.assertEqual(s.undo.count(), 1)
        s.edit("Gap", lambda p: p.subfields[0].params.__setitem__("gap", 0.05), merge=("gap", "s1"))
        self.assertEqual(s.undo.count(), 2)
        s.undo.undo()
        s.undo.undo()
        self.assertEqual(s.project.subfields[0].params["tilt"], 15.0)
        # not across the moment, and never across the saved state
        s.edit("Tilt", lambda p: p.subfields[0].params.__setitem__("tilt", 20.0), merge=("tilt", "s1"))
        s.undo.steps[-1].when -= 10.0
        s.edit("Tilt", lambda p: p.subfields[0].params.__setitem__("tilt", 21.0), merge=("tilt", "s1"))
        self.assertEqual(s.undo.count(), 2)
        s.mark_saved()
        s.edit("Tilt", lambda p: p.subfields[0].params.__setitem__("tilt", 22.0), merge=("tilt", "s1"))
        self.assertEqual(s.undo.count(), 3)
        s.undo.undo()
        self.assertFalse(s.dirty())

    def test_the_stack_keeps_a_stated_number_of_steps(self):
        s = session.ProjectSession(sample(), undo_limit=3)
        for k in range(5):
            s.edit(f"Rename {k}", rename(f"Name {k}"))
        self.assertEqual(s.undo.count(), 3)
        self.assertEqual([st.text for st in s.undo.steps], ["Rename 2", "Rename 3", "Rename 4"])
        for _ in range(5):
            s.undo.undo()
        self.assertEqual(s.project.buildings[0].name, "Name 1")       # the oldest steps are gone
        self.assertTrue(s.dirty())                                    # the saved state is beyond reach
        self.assertFalse(s.undo.is_clean())

    def test_a_new_step_after_an_undo_drops_what_could_be_redone(self):
        s = session.ProjectSession(sample())
        s.edit("A", rename("A"))
        s.edit("B", rename("B"))
        s.mark_saved()
        s.undo.undo()
        self.assertTrue(s.undo.can_redo())
        s.edit("C", rename("C"))
        self.assertFalse(s.undo.can_redo())
        self.assertEqual([st.text for st in s.undo.steps], ["A", "C"])
        self.assertEqual(s.undo.clean_index, -1)                      # the saved state is not on the stack
        self.assertTrue(s.dirty())

    def test_the_undo_tells_its_listeners_once_per_change(self):
        s = session.ProjectSession(sample())
        told = []
        s.undo.listeners.append(lambda: told.append((s.undo.index, s.undo.is_clean())))
        s.edit("A", rename("A"))
        s.undo.undo()
        s.undo.undo()                                                 # nothing to undo: nothing said
        s.mark_saved()
        self.assertEqual(told, [(1, False), (0, True), (0, True)])


class Topics(unittest.TestCase):
    """What an edit is told by, so that each view follows only what it reads."""

    def topics(self, change) -> set:
        s = session.ProjectSession(sample())
        return s.edit("x", change)

    def test_each_change_has_its_topic(self):
        cases = {
            "a name": (rename("X"), {"project:text", "checks"}),
            "the project's name": (lambda p: setattr(p, "name", "Y"), {"project:text", "checks"}),
            "a height": (lambda p: setattr(p.buildings[0], "height", 12.0), {"project:geometry", "checks"}),
            "a building added": (lambda p: p.buildings.append(model.Building(id="b2", name="B", footprint=[[50, 0], [60, 0], [60, 5]])),
                                 {"project:geometry", "checks"}),
            "the fire data": (lambda p: setattr(p.buildings[0].fire, "category", "C"), {"project:fire", "checks"}),
            "an exclusion": (lambda p: p.exclusions.append(model.ExclusionItem(id="e1", ring=[[1, 1], [2, 1], [2, 2]])),
                             {"project:geometry", "checks"}),
            "a sub-field's name": (lambda p: setattr(p.subfields[0], "name", "Nord"), {"project:text", "checks"}),
            "a sub-field's tilt": (lambda p: p.subfields[0].params.__setitem__("tilt", 20.0),
                                   {"project:subfields", "checks"}),
            "the site": (lambda p: setattr(p.site, "lat", 44.0), {"project:site", "checks"}),
            "the losses": (lambda p: p.energy.__setitem__("losses", {"soiling": 5.0}), {"project:energy", "checks"}),
            "the rules": (lambda p: p.rules.__setitem__("obligation", "new"), {"project:rules", "checks"}),
            "a variant": (lambda p: p.add_variant("B"), {"project:variants", "checks"}),
            "the project reserved": (lambda p: setattr(p, "reserved", True),
                                     {"project:text", "project:privacy", "checks"}),
            "a network consent": (lambda p: setattr(p, "network_consent", {"tiles": "2026-10-27"}),
                                  {"project:privacy"}),
        }
        for what, (change, expected) in cases.items():
            with self.subTest(what):
                self.assertEqual(self.topics(change), expected)

    def test_only_what_can_move_a_module_asks_for_a_layout(self):
        self.assertFalse(session.needs_layout({"project:text", "checks"}))
        self.assertFalse(session.needs_layout({"project:rules", "project:underlays", "restored"}))
        for topic in ("project:geometry", "project:subfields", "project:fire", "project:site", "project:energy",
                      "project:variants"):
            self.assertTrue(session.needs_layout({topic}), topic)
        self.assertFalse(session.needs_layout({"layout:s1", "energy", "selection"}))

    def test_a_layout_that_came_back_tells_the_sub_fields_that_changed(self):
        s = session.ProjectSession(sample())
        told = []
        s.subscribe(lambda topics: told.append(set(topics)))
        kept = object()
        s.results, s.layout_keys = {"s1": kept, "s2": object()}, {"s1": "k1", "s2": "k2"}
        s.layout_done(0, {"s1": kept, "s3": object()}, {"s1": "k1", "s3": "k3"})
        self.assertEqual(told, [{"layout:s2", "layout:s3", "checks"}])
        s.layout_done(0, dict(s.results), dict(s.layout_keys))         # the same layouts: nobody is told
        self.assertEqual(len(told), 1)
        s.select("subfield", "s1", ("s1", "r1:3"))
        self.assertEqual((s.selection, s.selected_module, told[-1]), (("subfield", "s1"), ("s1", "r1:3"), {"selection"}))

    def test_the_year_is_stale_only_when_its_inputs_changed(self):
        s = session.ProjectSession(sample())
        s.layout_keys = {"s1": "k1"}
        self.assertFalse(s.energy_stale())                            # no year yet
        generation = s.energy_asked()
        s.energy_done(generation, {"sim": "year"})
        self.assertFalse(s.energy_stale())
        s.edit("Rename", rename("X"))
        s.edit("Rules", lambda p: p.rules.__setitem__("obligation", "new"))
        self.assertFalse(s.energy_stale())
        s.edit("Losses", lambda p: p.energy.__setitem__("losses", {"soiling": 5.0}))
        self.assertTrue(s.energy_stale())
        s.energy_done(s.energy_asked(), {"sim": "year 2"})
        self.assertFalse(s.energy_stale())
        s.layout_keys = {"s1": "k2"}                                  # a layout made again
        self.assertTrue(s.energy_stale())


class Variants(unittest.TestCase):
    def test_a_variant_kept_apart_and_the_switch_undone(self):
        s = session.ProjectSession(sample())
        s.edit("New variant", lambda p: p.add_variant("Inclinati"))
        s.edit("Tilt", lambda p: p.subfields[0].params.__setitem__("tilt", 30.0))
        s.edit("Switch", lambda p: p.switch_variant("v1"))
        self.assertEqual(s.project.subfields[0].params["tilt"], 15.0)
        s.undo.undo()
        self.assertEqual((s.project.variant, s.project.subfields[0].params["tilt"]), ("v2", 30.0))


class Results(unittest.TestCase):
    def test_a_layout_of_an_older_generation_is_dropped(self):
        s = session.ProjectSession(sample())
        s.generation = 3
        self.assertFalse(s.layout_done(2, {"s1": "old"}, {"s1": "k"}))
        self.assertEqual(s.results, {})
        self.assertTrue(s.layout_done(3, {"s1": ValueError("no room")}, {"s1": "k"}))
        self.assertEqual(s.good_results(), {})
        self.assertEqual(s.known_layouts(), {"s1": ("k", s.results["s1"])})
        self.assertEqual(s.layout_state(s.project.subfields[0]), "stale")      # "k" is not the key of today
        s.energy_generation = 2
        self.assertFalse(s.energy_done(1, {"sim": None}))
        self.assertTrue(s.energy_done(2, {"sim": "year"}))
        self.assertEqual(s.energy["sim"], "year")

    def test_another_project_takes_the_place_of_everything(self):
        s = session.ProjectSession(sample())
        s.edit("A", rename("A"))
        s.results, s.energy, s.selection = {"s1": "r"}, {"sim": "x"}, ("building", "b1")
        told = []
        s.subscribe(lambda topics: told.append(set(topics)))
        s.new()
        self.assertEqual((s.results, s.energy, s.selection, s.undo.count()), ({}, {}, ("site", ""), 0))
        self.assertFalse(s.dirty())
        self.assertEqual(told, [{"file", "project"}])


class Files(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.file = self.root / "prova.meridiana"
        sample().save(self.file)

    def test_opened_edited_saved_and_a_revision_next_to_it(self):
        s = session.ProjectSession()
        self.assertIsNone(s.open(self.file))
        self.assertEqual((s.path, s.project.name, s.dirty()), (self.file, "Prova", False))
        s.edit("Rename", lambda p: setattr(p, "name", "Revisione"))
        self.assertTrue(s.dirty())
        before = self.file.read_text(encoding="utf-8")
        target = s.save_revision()
        self.assertEqual(target.name, "prova_R01.meridiana")
        self.assertEqual((s.path, s.dirty()), (target, False))
        self.assertEqual(self.file.read_text(encoding="utf-8"), before)   # the previous one stays as it was
        self.assertEqual(model.Project.load(target)[0].name, "Revisione")
        s.undo.undo()
        self.assertTrue(s.dirty())
        s.undo.redo()
        self.assertFalse(s.dirty())

    def test_a_project_without_a_file_cannot_be_saved_in_place(self):
        s = session.ProjectSession()
        with self.assertRaises(ValueError):
            s.save()
        with self.assertRaises(ValueError):
            s.save_revision()
        s.save(self.root / "nuovo.meridiana")
        self.assertEqual(s.path, self.root / "nuovo.meridiana")

    def test_a_damaged_file_leaves_the_project_in_hand(self):
        s = session.ProjectSession(sample())
        bad = self.root / "rotto.meridiana"
        bad.write_text('{"format": "meridiana-project", "version": 6, "buildings": [{"id": "b1"}]}', encoding="utf-8")
        with self.assertRaises(ValueError):
            s.open(bad)
        self.assertEqual((s.path, s.project.name), (None, "Prova"))

    def test_the_recovery_copy_follows_the_unsaved_changes(self):
        state = self.root / "state"
        s = session.ProjectSession()
        s.open(self.file)
        self.assertIsNone(s.autosave(state))                          # nothing to keep aside
        s.edit("Rename", lambda p: setattr(p, "name", "Da recuperare"))
        written = s.autosave(state)
        self.assertEqual(written, recovery.slot(state, self.file))
        self.assertTrue(written.exists())
        copies = recovery.pending(state)
        self.assertEqual(copies[0]["project"]["name"], "Da recuperare")
        s.save()
        s.drop_autosave(state)
        self.assertFalse(written.exists())
        self.assertIsNone(s.autosaved)

    def test_the_state_key_counts_an_image_without_writing_it_whole(self):
        from meridiana.underlay import Underlay
        s = session.ProjectSession(sample())
        image = "A" * 4000
        s.project.underlays.append(Underlay(id="u1", name="plan.png", image=image, width=20, height=15))
        key = s.state_key()
        self.assertNotIn(image[60:-60], key)                # 38 ms at each step with an image of 8 MB
        s.project.underlays[0].image = image[:-4] + "BBB="
        self.assertNotEqual(s.state_key(), key)
        s.project.underlays[0].image = image
        self.assertEqual(s.state_key(), key)
        s.project.underlays[0].opacity = 0.2                # what is not the image counts as before
        self.assertNotEqual(s.state_key(), key)


class Outdated(unittest.TestCase):
    """session.energy_outdated, without Qt: the year against the project as it is, the layouts on their way
    counted."""

    def test_the_year_is_outdated_from_the_change_itself_and_clean_again_with_the_same_inputs(self):
        from meridiana import jobs, model
        from meridiana.session import ProjectSession
        p = model.Project(name="Prova")
        b = model.Building(id=p.new_id("b"), name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                           height=9.5)
        p.buildings.append(b)
        p.subfields.append(model.SubField(id=p.new_id("s"), name="Sud", ring=[[1, 1], [39, 1], [39, 19], [1, 19]],
                                          building=b.id, params={"tilt": 15.0}, filled=True))
        s = ProjectSession(p)
        self.assertFalse(s.energy_outdated())                   # no year: nothing to update
        results, keys, _laid = jobs.layout_of(s.project)
        self.assertTrue(s.layout_done(s.generation, results, keys))
        s.energy_done(s.energy_asked(), {"notes": []})
        self.assertFalse(s.energy_outdated())
        s.edit("height", lambda q: setattr(q.building(b.id), "height", 12.0))
        self.assertFalse(s.energy_stale())                      # the layout in hand is still the one computed
        self.assertTrue(s.energy_outdated())                    # the year no longer answers for the project
        s.undo.undo()
        self.assertFalse(s.energy_outdated())                   # back to the inputs of the year
        s.edit("name", lambda q: setattr(q.building(b.id), "name", "Magazzino"))
        self.assertFalse(s.energy_outdated())                   # a name moves nothing
        s.edit("losses", lambda q: q.energy.update({"losses": {"soiling": 3.0}}))
        self.assertTrue(s.energy_outdated())


if __name__ == "__main__":
    unittest.main()
