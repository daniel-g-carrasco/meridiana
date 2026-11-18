"""R389: the Widgets plan receives Qt events; the pure editor the same intent.

These compare semantic gestures, not screenshots or the Quick event adapter.
"""
import unittest
import json
from pathlib import Path
from types import SimpleNamespace

import _setup
from _fixtures import capannone, plan_view
from meridiana import model, move
from meridiana.quick.backend.plan_edit import PlanEditor
from meridiana.session import ProjectSession
from quick.parity.differential import Adapter, canonical_project, run_scenario, undo_snapshot

setUpModule = _setup.keep_global_state


class WidgetsParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.project = capannone()
        self.view, self.results = plan_view(self, self.project)
        self.editor = PlanEditor(ProjectSession(model.Project.from_json(self.project.to_json())))
        self.editor.set_results(self.results)

    def click(self, point):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from meridiana.ui.plan import to_scene
        pos = self.view.mapFromScene(to_scene(*point))
        QTest.mouseClick(self.view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos)
        self.app.processEvents()
        self.editor.click(point)

    def test_module_row_parent_selection(self):
        self.editor.set_phase("plant")
        m = next(iter(self.results.values())).modules[0]
        self.click(m.centre)
        self.assertEqual(self.editor.selected_module, self.view.selected_module)
        self.click(m.centre)
        self.assertEqual(self.editor.selection, self.view.selection)
        self.view.selection_back()
        self.editor.key("Escape")
        self.assertEqual(self.editor.selection, self.view.selection)
        # Decided difference (Daniel, 05/11/2026): the Plant does not select buildings, so Esc goes on to nothing.
        self.editor.key("Escape")
        self.assertEqual(self.editor.selection, ("site", ""))

    def test_pick_boundaries_match_widgets_convex_test(self):
        self.editor.set_phase("plant")
        import numpy as np
        from meridiana.ui.plan import _quad_at
        for sfid, result in self.results.items():
            quads = np.asarray([m.corners for m in result.modules])
            for module in result.modules[:8]:
                points = list(module.corners) + [module.centre]
                points += [tuple((np.asarray(a)+b)/2) for a, b in
                           zip(module.corners, module.corners[1:]+module.corners[:1], strict=True)]
                for point in points:
                    at = _quad_at(quads, *point)
                    self.assertGreaterEqual(at, 0)
                    self.assertEqual(self.editor.pick(point), ("module", sfid, result.modules[at].key))

    def test_typed_move_and_rotation_commands(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from meridiana.ui.window import MainWindow
        commands = []
        self.view.transformRequested.connect(lambda k, oid, what: commands.append((k, oid, what)))
        old = ProjectSession(self.project)
        receiver = SimpleNamespace(project=self.project, edit=old.edit,
                                   hint=SimpleNamespace(setText=lambda message: self.fail(message)),
                                   view3d=SimpleNamespace(backend=SimpleNamespace()),
                                   _centre_3d=lambda kind, oid: move.centre(old.project, kind, oid))

        def apply(kind, oid, what):
            MainWindow._transform(receiver, kind, oid, what)
            self.view.show_project(old.project, {})
        self.view.transformRequested.connect(apply)
        bid = self.project.buildings[0].id
        self.view.set_selection("building", bid)
        self.view.set_tool("move")
        self.editor.select("building", bid)
        self.editor.set_tool("move")
        keys = {"Enter": Qt.Key_Return, "R": Qt.Key_R}
        widgets = Adapter("Widgets", {
            "type": lambda text: QTest.keyClicks(self.view, text),
            "key": lambda key: QTest.keyClick(self.view, keys[key]),
            "undo": old.undo.undo, "redo": old.undo.redo},
            lambda: {"project": canonical_project(old.project), "undo": undo_snapshot(old)}, self.app.processEvents)
        quick = Adapter("Quick", {
            "type": lambda text: self.editor.key("", text), "key": self.editor.key,
            "undo": self.editor.session.undo.undo, "redo": self.editor.session.undo.redo},
            lambda: {"project": canonical_project(self.editor.project), "undo": undo_snapshot(self.editor.session)})
        scenario = {"id": "pianta-edit-move-rotate-undo", "steps": [
            {"command": "type", "args": {"text": "3;2"}}, {"command": "key", "args": {"key": "Enter"}},
            {"command": "key", "args": {"key": "R"}}, {"command": "type", "args": {"text": "90"}},
            {"command": "key", "args": {"key": "Enter"}}, {"command": "undo"}, {"command": "redo"}]}
        result = run_scenario(scenario, widgets, quick)
        destination = Path(__file__).resolve().parents[3] / "build/quick-foto/pianta/edit"
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "differential-move-rotate.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        self.assertEqual(result["status"], "equal", result)
        self.assertEqual(commands[0], ("building", bid, {"mode": "move", "dx": 3.0, "dy": 2.0, "copy": False}))
        self.assertEqual(commands[-1][2]["degrees"], 90)
        self.assertEqual(self.editor.session.undo.count(), 2)
        self.assertEqual(self.editor.session.snapshot(), old.snapshot())

    def test_hot_grips_cycle_like_widgets(self):
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtTest import QTest
        from meridiana.ui.plan import to_scene
        bid = self.project.buildings[0].id
        self.view.set_selection("building", bid)
        self.view.set_tool("move")
        self.editor.select("building", bid)
        point = self.view._grips()["move"]
        self.view._grip_press("move", QPointF(self.view.mapFromScene(to_scene(*point))))
        self.editor.start_grip("move", point)
        for key, name in [(Qt.Key_Space, "Space"), (Qt.Key_Return, "Enter")]:
            QTest.keyClick(self.view, key)
            self.editor.key(name)
            self.assertEqual(self.editor.gesture.mode, self.view.gesture.mode)
            self.assertEqual(self.editor.gesture.base, self.view.gesture.base)
        QTest.keyClick(self.view, Qt.Key_C)
        self.editor.key("C")
        self.assertEqual(self.editor.gesture.copy, self.view.gesture.copy)


if __name__ == "__main__":
    unittest.main()
