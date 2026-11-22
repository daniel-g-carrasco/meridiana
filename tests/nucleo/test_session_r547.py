"""R547 «Risposta subito» (Daniel, 08/11/2026): a change that moves modules is told at once only to the listeners that
draw them (subscribed `at_once`), the others after the window's frame (session.later), in one round."""
import unittest

from meridiana.core.model import model
from meridiana.app.session import ProjectSession


def project():
    p = model.Project(name="R547")
    p.buildings.append(model.Building(id="b1", name="Capannone", height=6,
                                      footprint=[[0, 0], [40, 0], [40, 20], [0, 20]]))
    p.subfields.append(model.SubField(id="s1", name="Sud", building="b1", filled=True,
                                      ring=[[2, 2], [38, 2], [38, 18], [2, 18]], params={"tilt": 15}))
    return p


class AnswerFirstTest(unittest.TestCase):
    def setUp(self):
        self.session = ProjectSession(project())
        result = self.session.project.fill(self.session.project.subfields[0])
        self.session.results = {"s1": result}
        self.session.layout_keys = self.session.expected_layout_keys()
        self.key = result.modules[len(result.modules) // 2].key
        self.at_once, self.others, self.calls = [], [], []
        self.session.subscribe(self.at_once.append, at_once=True)
        self.session.subscribe(self.others.append)
        self.session.later = self.calls.append

    def take_out(self):
        self.session.edit("Take a module out", lambda p: p.subfields[0].removed.append(self.key))

    def test_a_module_taken_out_is_drawn_first_and_the_rest_told_after_the_frame(self):
        self.take_out()
        self.assertEqual(len(self.at_once), 1)
        self.assertEqual(self.others, [])
        self.session.select("subfield", "s1")          # what follows the gesture waits with it
        self.assertEqual(len(self.at_once), 2)
        self.assertEqual(len(self.calls), 1)
        self.calls[0]()
        self.assertEqual(len(self.others), 1, "one round for the others")
        self.assertIn("selection", self.others[0])
        self.assertTrue(self.others[0] & self.at_once[0])
        self.session.select("site", "")                 # after it, everyone at once again
        self.assertEqual(len(self.others), 2)

    def test_a_change_that_moves_no_module_is_told_to_all_at_once(self):
        self.session.edit("Name", lambda p: setattr(p, "name", "Altro"))
        self.assertEqual((len(self.at_once), len(self.others), self.calls), (1, 1, []))

    def test_undo_of_a_module_is_drawn_first_too(self):
        self.take_out()
        self.calls.pop()()
        self.session.layout_keys = self.session.expected_layout_keys()     # the layout came back
        self.session.undo.undo()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(self.others), 1)
        self.calls.pop()()
        self.assertEqual(len(self.others), 2)
        self.assertIn("restored", self.others[-1])

    def test_without_a_window_everyone_is_told_at_once(self):
        self.session.later = None
        self.take_out()
        self.assertEqual((len(self.at_once), len(self.others)), (1, 1))


class RoundInPiecesTest(unittest.TestCase):
    """R598: the round after the frame a listener per piece on the window's turns (session.pieces = Center.piece);
    whatever comes while it is half done (another edit, a selection, an undo, the layout) finds every listener told
    of the changes before, in their order, on the project they were made on."""

    def setUp(self):
        from meridiana.app.work.center import Center
        self.center = Center(lambda: None)
        self.addCleanup(self.center.close)
        self.session = ProjectSession(project())
        result = self.session.project.fill(self.session.project.subfields[0])
        self.session.results = {"s1": result}
        self.session.layout_keys = self.session.expected_layout_keys()
        self.keys = [m.key for m in result.modules]
        self.heard, self.frames = [], []
        self.session.subscribe(lambda t: self.hear("plan", t), at_once=True)
        for name in ("a", "b", "c"):
            self.session.subscribe(lambda t, name=name: self.hear(name, t))
        self.session.later = self.frames.append
        self.session.pieces = self.center.piece

    def hear(self, name, topics):
        """Who heard what, and the project and the selection it found when told."""
        s = self.session
        self.heard.append((name, frozenset(topics), len(s.project.subfields[0].removed), s.selection))

    def take_out(self, key):
        self.session.edit("Take a module out", lambda p: p.subfields[0].removed.append(key))

    def told(self, name):
        return [h for h in self.heard if h[0] == name]

    def pump_all(self):
        while self.center.pump(budget=0.0):
            pass

    def test_the_round_after_the_frame_is_a_listener_per_piece(self):
        self.take_out(self.keys[3])
        self.frames.pop()()                            # the frame drawn: the round starts
        self.assertEqual([h[0] for h in self.heard], ["plan"], "nobody else told before the window's turn")
        self.assertTrue(self.session.telling())
        self.center.pump(budget=0.0)
        self.assertEqual([h[0] for h in self.heard], ["plan", "a"], "one listener in a turn")
        self.pump_all()
        self.assertEqual([h[0] for h in self.heard], ["plan", "a", "b", "c"])
        self.assertFalse(self.session.telling())
        self.assertEqual(sorted(self.center.stats()["by_name"]), ["tell:RoundInPiecesTest.setUp.<locals>.<lambda>"])

    def test_without_pieces_the_round_is_told_at_once(self):
        self.session.pieces = None
        self.take_out(self.keys[3])
        self.frames.pop()()
        self.assertEqual([h[0] for h in self.heard], ["plan", "a", "b", "c"])

    def test_an_edit_half_way_finds_every_listener_told_of_the_one_before_on_its_project(self):
        self.take_out(self.keys[3])
        self.frames.pop()()
        self.center.pump(budget=0.0)                    # "a" told, "b" and "c" wait
        self.take_out(self.keys[4])
        for name in ("b", "c"):
            first = self.told(name)[0]
            self.assertEqual(first[2], 1, f"{name} heard the first deletion on the project of the first deletion")
        self.frames.pop()()
        self.pump_all()
        for name in ("a", "b", "c"):
            self.assertEqual([h[2] for h in self.told(name)], [1, 2], f"{name} heard both, in order")
        self.assertEqual(len(self.told("plan")), 2)

    def test_a_selection_half_way_comes_after_the_change_before(self):
        self.take_out(self.keys[3])
        self.frames.pop()()
        self.center.pump(budget=0.0)
        self.session.select("subfield", "s1")
        for name in ("b", "c"):
            change, selection = self.told(name)
            self.assertNotIn("selection", change[1])
            self.assertEqual(change[3], ("site", ""), f"{name} heard the deletion before the selection was made")
            self.assertIn("selection", selection[1])
        self.pump_all()
        self.assertEqual([len(self.told(n)) for n in ("a", "b", "c")], [2, 2, 2], "nobody told twice")

    def test_an_undo_half_way_comes_after_the_change_it_takes_back(self):
        self.take_out(self.keys[3])
        self.frames.pop()()
        self.center.pump(budget=0.0)
        self.session.layout_keys = self.session.expected_layout_keys()     # the layout came back
        self.session.undo.undo()
        for name in ("b", "c"):
            self.assertEqual(self.told(name)[0][2], 1, f"{name} heard the deletion before the undo")
        if self.frames:
            self.frames.pop()()
        self.pump_all()
        for name in ("a", "b", "c"):
            heard = self.told(name)
            self.assertEqual([h[2] for h in heard], [1, 0], f"{name}: the deletion, then the undo")
            self.assertIn("restored", heard[-1][1])

    def test_a_layout_half_way_is_told_after_the_round_in_order(self):
        from meridiana.app import jobs
        self.take_out(self.keys[3])
        self.frames.pop()()
        self.center.pump(budget=0.0)
        results, keys, _laid = jobs.layout_of(self.session.project)
        self.session.layout_done(self.session.generation, results, keys, pieces=True)
        self.pump_all()
        for name in ("a", "b", "c"):
            heard = self.told(name)
            self.assertEqual(len(heard), 2, name)
            self.assertFalse(any(t.startswith("layout:") for t in heard[0][1]), f"{name}: the change first")
            self.assertIn("layout:s1", heard[1][1], f"{name}: then the layout")
        self.assertFalse(self.session.telling())


if __name__ == "__main__":
    unittest.main()
