"""The roof tools of study 22 in the window (R274, R275): a free pitch drawn with its card, changed from its page and
on the plan, a ridge that makes the roof, each one step of the undo; what cannot be done is said. PySide6 and a
display (offscreen will do)."""

import math
import unittest

import _setup
from PySide6.QtCore import QPoint

from meridiana import config, model

setUpModule = _setup.keep_global_state


def house() -> model.Project:
    p = model.Project(name="Tetti")
    p.buildings.append(model.Building(id="b1", name="Casa", height=6.0,
                                      footprint=[[0, 0], [16, 0], [16, 10], [0, 10]]))
    return p


class RoofTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, house(), config.Config(background="none", theme="light"))

    def roof(self):
        return self.win.project.building("b1").roof

    def test_the_corners_of_the_roof_in_3d_each_gesture_one_step_of_the_undo(self):
        """R303, R357: with Move on a building its corners show; on a flat roof one moves the building's height; made
        pitched, a height dragged or written, each is one step, and undo takes the roof back."""
        win = self.win
        backend, field = win.view3d.backend, win.view3d.vertex_field
        win._select("building", "b1")
        win._set_tool("move")
        self.assertEqual(len(backend.vertices), 4)
        self.assertEqual(self.roof().type, "flat")
        steps = win.undo.count()
        backend.vertexClicked.emit(2)
        self.assertEqual(backend.vertex_on, 2)
        self.assertTrue(field.isVisibleTo(win.view3d))
        self.assertEqual(win.undo.count(), steps)                # taking a corner changes nothing
        field.typed.emit("+2")
        self.assertEqual(win.undo.count(), steps + 1)
        self.assertEqual(self.roof().type, "flat")               # R357
        self.assertAlmostEqual(win.project.building("b1").height, 8.0)
        self.assertEqual(backend.vertex_on, 2)                   # still the one taken
        win.undo.undo()
        self.assertAlmostEqual(win.project.building("b1").height, 6.0)
        win._vertex_make_pitched()
        self.assertEqual(self.roof().type, "free")
        steps = win.undo.count()
        backend.vertexClicked.emit(2)
        field.typed.emit("+2")
        self.assertEqual(win.undo.count(), steps + 1)
        self.assertAlmostEqual(win.vertex_handles[2].z, 8.0)
        self.assertIn("off one plane", win.hint.text())
        self.assertEqual(len(win.project.building("b1").pitches()), 2)
        backend.vertexDragged.emit(2, -1.0)
        self.assertEqual(win.undo.count(), steps + 2)
        self.assertAlmostEqual(win.vertex_handles[2].z, 7.0)
        backend.vertexClicked.emit(2)
        field.typed.emit("abc")
        self.assertEqual(win.undo.count(), steps + 2)            # what is not a number changes nothing, and says so
        field.typed.emit("3,5")                                  # without a sign: the height itself
        self.assertAlmostEqual(win.vertex_handles[2].z, 3.5)
        backend.vertexClicked.emit(2)
        field.typed.emit("-9")                                   # under the ground: refused, said
        self.assertAlmostEqual(win.vertex_handles[2].z, 3.5)
        self.assertIn("ground", win.hint.text())
        win.undo.undo()
        self.assertAlmostEqual(self.roof().free_pitches[0]["z"][2], 7.0)
        for _i in range(3):
            win.undo.undo()
        self.assertEqual(self.roof().type, "flat")

    def test_two_corners_made_one_and_parted_from_the_3d_view(self):
        win = self.win
        backend = win.view3d.backend

        def menu(at):
            win._vertex_menu(at, QPoint(0, 0))
            win.context_menu.hide()
            return {a.text(): a for a in win.context_menu.actions() if a.text()}

        def draw(p):
            r = p.building("b1").roof
            r.type, r.joined = "free", False
            r.free_pitches = [{"ring": [[0, 0], [8, 0], [8, 10], [0, 10]], "eave_side": 0, "eave": 6.0, "tilt": 0.0},
                              {"ring": [[8.5, 0], [16, 0], [16, 10], [8.5, 10]], "eave_side": 0, "eave": 7.0, "tilt": 0.0}]
        win.edit("Draw", draw)
        win._select("building", "b1")
        win._set_tool("move")
        steps = win.undo.count()
        options = menu(1)                                        # [8, 0] of the first pitch
        self.assertNotIn("Part", options)
        options["Make one with..."].trigger()
        self.assertTrue(win.vertex_merging)
        backend.vertexClicked.emit(4)                            # [8.5, 0] of the second
        self.assertEqual(win.undo.count(), steps + 1)
        self.assertEqual(self.roof().welds, [[[0, 1], [1, 0]]])
        self.assertEqual(self.roof().free_pitches[1]["ring"][0], [8.0, 0.0])
        self.assertEqual(len(win.vertex_handles), 7)
        at = next(i for i, h in enumerate(win.vertex_handles) if len(h.corners) == 2)
        menu(at)["Part"].trigger()
        self.assertEqual(win.undo.count(), steps + 2)
        self.assertEqual(self.roof().welds, [])
        self.assertEqual(len(win.vertex_handles), 8)
        win.undo.undo()
        self.assertEqual(self.roof().welds, [[[0, 1], [1, 0]]])

    def test_pitch_page_and_ridge_each_one_step_of_the_undo(self):
        win = self.win
        steps = win.undo.count()
        # R274: a pitch drawn with Tab and a ridge height in its card
        win.plan.pitchDrawn.emit([[0, 0], [16, 0], [16, 5], [0, 5]],
                                 {"swapped": True, "tilt": None, "ridge": 8.0, "eave": None})
        self.assertEqual(self.roof().type, "free")
        (pitch,) = self.roof().free_pitches
        self.assertEqual((pitch["eave_side"], pitch["eave"]), (2, 6.0))
        self.assertAlmostEqual(pitch["tilt"], math.degrees(math.atan(2.0 / 5.0)))
        self.assertEqual(win.undo.count(), steps + 1)
        self.assertEqual(win.props.kind, "building")
        # its page: the ridge written, then the eave picked on the plan
        from PySide6.QtWidgets import QDoubleSpinBox
        ridge = next(w for w in win.props.widget().findChildren(QDoubleSpinBox)
                     if w.toolTip().startswith("The height of the top of the pitch"))
        ridge.setValue(9.0)
        self.assertAlmostEqual(self.roof().free_pitches[0]["tilt"], math.degrees(math.atan(3.0 / 5.0)))
        self.assertEqual(win.undo.count(), steps + 2)
        win._edge_picked("free_eave:0", "building", "b1", 0)
        self.assertEqual(self.roof().free_pitches[0]["eave_side"], 0)
        self.assertEqual(win.undo.count(), steps + 3)
        win.undo.undo()
        self.assertEqual(self.roof().free_pitches[0]["eave_side"], 2)
        # R275: the ridge tool, off the axis, makes a gable roof on the axis and says it
        win.commands["tool_ridge"].trigger()
        self.assertEqual(win.plan.tool, "ridge")
        win.plan.ridgeDrawn.emit([[0.3, 6.5], [15.7, 6.5]], None)
        r = self.roof()
        self.assertEqual((r.type, r.edges, r.free_pitches, r.ridge_height), ("gable", ["eave", "gable", "eave", "gable"],
                                                                            [], None))
        self.assertIn("axis", win.hint.text())
        b = win.project.building("b1")
        self.assertAlmostEqual(b.ridge(), 6.0 + 5.0 * 0.35, places=6)
        win.undo.undo()
        self.assertEqual(self.roof().type, "free")
        win.undo.redo()
        win.plan.ridgeDrawn.emit([[5.0, 5.0], [11.0, 5.0]], 9.0)          # inside at both ends: a hip, at 9 m
        self.assertEqual(self.roof().type, "hip")
        self.assertAlmostEqual(win.project.building("b1").ridge(), 9.0, places=6)

    def test_a_ridge_off_the_buildings_or_on_an_outline_crossing_itself_changes_nothing(self):
        win = self.win
        before, steps = win.snapshot(), win.undo.count()
        win.plan.ridgeDrawn.emit([[40.0, 40.0], [50.0, 40.0]], None)
        self.assertIn("building", win.hint.text())

        def cross(p):
            p.building("b1").footprint = [[0, 0], [10, 10], [10, 0], [0, 10]]
        win.edit("cross", cross)
        before, steps = win.snapshot(), win.undo.count()
        win.plan.ridgeDrawn.emit([[9.0, 5.0], [9.8, 5.0]], None)            # inside its right lobe
        self.assertEqual((win.snapshot(), win.undo.count()), (before, steps))
        self.assertIn("crosses itself", win.hint.text())


if __name__ == "__main__":
    unittest.main()
