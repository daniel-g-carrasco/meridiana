"""R547 «Risposta subito» (Daniel, 08/11/2026): a change that moves modules is told at once only to the listeners that
draw them (subscribed `at_once`), the others after the window's frame (session.later), in one round."""
import unittest

from meridiana import model
from meridiana.session import ProjectSession


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
        self.session.layout_keys = self.session._expected_keys()
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
        self.session.layout_keys = self.session._expected_keys()     # the layout came back
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


if __name__ == "__main__":
    unittest.main()
