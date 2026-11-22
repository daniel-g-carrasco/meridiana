"""R389: the plan's editor of the Quick, given the gestures the Widgets plan was given, ends where the Widgets ended
(their answers recorded on 10/11/2026, when they went: quick/aiuti/riferimenti.py).

These compare semantic gestures, not screenshots or the Quick event adapter.
"""
import unittest

import _setup
from _fixtures import capannone
from meridiana.app import jobs
from meridiana.core.model import model, move
from meridiana.gui.backend.plan_edit import PlanEditor
from meridiana.app.session import ProjectSession
from quick.aiuti import riferimenti
from quick.aiuti.differential import undo_snapshot

setUpModule = _setup.keep_global_state


class WidgetsParity(unittest.TestCase):
    def setUp(self):
        self.project = capannone()
        self.results, _keys, _laid = jobs.layout_of(self.project)
        self.editor = PlanEditor(ProjectSession(model.Project.from_json(self.project.to_json())))
        self.editor.set_results(self.results)

    def test_module_row_parent_selection(self):
        self.editor.set_phase("plant")
        m = next(iter(self.results.values())).modules[0]
        self.editor.click(m.centre)
        seen = [self.editor.selected_module]
        self.editor.click(m.centre)
        seen.append(self.editor.selection)
        self.editor.key("Escape")
        seen.append(self.editor.selection)
        riferimenti.check(self, seen)
        # Decided difference (Daniel, 05/11/2026): the Plant does not select buildings, so Esc goes on to nothing.
        self.editor.key("Escape")
        self.assertEqual(self.editor.selection, ("site", ""))

    def test_pick_boundaries_match_widgets_convex_test(self):
        import numpy as np
        self.editor.set_phase("plant")
        picked = []
        for _sfid, result in self.results.items():
            for module in result.modules[:8]:
                points = list(module.corners) + [module.centre]
                points += [tuple((np.asarray(a)+b)/2) for a, b in
                           zip(module.corners, module.corners[1:]+module.corners[:1], strict=True)]
                for point in points:
                    pick = self.editor.pick(point)
                    self.assertEqual(pick[0], "module")
                    picked.append(pick)
        riferimenti.check(self, picked)

    def test_typed_move_and_rotation_commands(self):
        bid = self.project.buildings[0].id
        self.editor.select("building", bid)
        self.editor.set_tool("move")
        undo = self.editor.session.undo
        steps = [lambda: self.editor.key("", "3;2"), lambda: self.editor.key("Enter"),
                 lambda: self.editor.key("R"), lambda: self.editor.key("", "90"), lambda: self.editor.key("Enter"),
                 undo.undo, undo.redo]
        for step in steps:
            step()
            riferimenti.check(self, {"project": riferimenti.project(self.editor.project),
                                     "undo": undo_snapshot(self.editor.session)})
        self.assertEqual(self.editor.session.undo.count(), 2)

    def test_hot_grips_cycle_like_widgets(self):
        bid = self.project.buildings[0].id
        self.editor.select("building", bid)
        # the grip that moves a thing is in its middle (as the Widgets' plan put it)
        self.editor.start_grip("move", move.centre(self.editor.project, "building", bid))
        seen = []
        for name in ("Space", "Enter"):
            self.editor.key(name)
            seen.append((self.editor.gesture.mode, self.editor.gesture.base))
        self.editor.key("C")
        seen.append(self.editor.gesture.copy)
        riferimenti.check(self, seen)


if __name__ == "__main__":
    unittest.main()
