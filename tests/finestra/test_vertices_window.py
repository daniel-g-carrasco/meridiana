"""The corners of a roof in the window (R354-R357, 03/11/2026): a small field and a menu, shown with Select in the Modelling,
several chosen together as one step of the undo, a flat roof that stays flat. PySide6 and a display (offscreen will do)."""

import unittest
from unittest import mock

import numpy as np
import _setup
from _fixtures import capannone
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from meridiana import config, gizmo, model, roof_vertices

setUpModule = _setup.keep_global_state


def project() -> model.Project:
    p = capannone()
    b = p.buildings[0]
    b.parapet = 1.0
    p.buildings.append(model.Building(id="g1", name="Casa", footprint=[[60, 0], [76, 0], [76, 10], [60, 10]], height=6.0,
                                      roof=model.Roof(type="gable", tilt=25.0)))
    return p


class Corners(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, project(), config.Config(background="none", theme="light"))
        self.win.show_phase("model")
        self.back = self.win.view3d.backend
        self.field = self.win.view3d.vertex_field
        self.flat = self.win.project.buildings[0].id

    def gable(self):
        return self.win.project.building("g1")

    def menu_of(self, at):
        self.win._vertex_menu(at, QPoint(0, 0))
        menu = self.win.context_menu
        menu.hide()
        return {a.text(): a for a in menu.actions() if a.text()}

    # R354

    def test_the_field_is_small_as_the_field_of_a_side_and_has_no_commands(self):
        from PySide6.QtWidgets import QAbstractButton

        from meridiana.ui.plan import SideEditor
        win = self.win
        win._select("building", "g1")
        self.back.vertexClicked.emit(0)
        field = self.field
        self.assertIsInstance(field, SideEditor)
        self.assertTrue(field.isVisibleTo(win.view3d))
        self.assertEqual(field.findChildren(QAbstractButton), [])
        side = win.plan.side_editor
        self.assertEqual(field.height(), side.pill_height())
        self.assertLess(field.width(), 120)
        field.grab()

    def test_enter_applies_esc_leaves_a_sign_is_relative_and_nothing_written_is_no_step(self):
        win = self.win
        win._select("building", "g1")
        self.back.vertexClicked.emit(0)
        steps = win.undo.count()
        z = win.vertex_handles[0].z
        QTest.keyClick(self.field.field, Qt.Key.Key_Return)                 # what it showed: nothing to do
        self.assertEqual(win.undo.count(), steps)
        self.assertFalse(self.field.isVisibleTo(win.view3d))
        self.back.vertexClicked.emit(0)
        self.field.field.setText("99")
        QTest.keyClick(self.field.field, Qt.Key.Key_Escape)
        self.assertFalse(self.field.isVisibleTo(win.view3d))
        self.assertEqual(win.undo.count(), steps)
        self.assertEqual(self.gable().roof.type, "gable")
        self.back.vertexClicked.emit(0)
        self.field.field.setText("+2")
        QTest.keyClick(self.field.field, Qt.Key.Key_Return)
        self.assertEqual(win.undo.count(), steps + 1)
        self.assertAlmostEqual(win.vertex_handles[0].z, z + 2.0)
        self.back.vertexClicked.emit(0)
        self.field.field.setText("7,5")
        QTest.keyClick(self.field.field, Qt.Key.Key_Return)
        self.assertAlmostEqual(win.vertex_handles[0].z, 7.5)

    def test_the_options_are_on_the_menu_of_the_right_button(self):
        win = self.win
        win._select("building", "g1")
        names = self.menu_of(0)
        for wanted in ("Height above the ground…", "Raise or lower by…", "Make one with...", "Choose all the corners"):
            self.assertIn(wanted, names)
        self.assertNotIn("Make it pitched", names)
        names["Raise or lower by…"].trigger()
        self.assertEqual(self.field.field.text(), "+")
        self.field.hide()
        ridge = next(i for i, h in enumerate(win.vertex_handles) if len(h.corners) > 1)
        names = self.menu_of(ridge)
        self.assertIn("Part", names)

    def test_the_right_button_on_a_corner_opens_its_menu_elsewhere_the_objects(self):
        win = self.win
        win._select("building", "g1")
        b = self.back
        b.resized(800.0, 600.0)
        x, y = b.camera.project(b.vertices[1], *b.size)
        win._view3d_menu(float(x), float(y))
        self.assertIn("Height above the ground…", [a.text() for a in win.context_menu.actions()])
        win.context_menu.hide()
        self.assertEqual(b.vertex_on, 1)
        far = max(b.size) * 5
        self.assertEqual(b.vertex_at(far, far), -1)

    def test_a_folded_pitch_has_the_way_back_on_one_plane_in_one_step(self):
        win = self.win
        win._select("building", self.flat)
        self.menu_of(0)["Make it pitched"].trigger()
        self.back.vertexClicked.emit(2)
        self.field.typed.emit("+2")
        self.assertIn("off one plane", win.hint.text())
        steps = win.undo.count()
        self.menu_of(2)["Back on one plane"].trigger()
        self.assertEqual(win.undo.count(), steps + 1)
        self.assertEqual(len(win.project.buildings[0].pitches()), 1)

    # R355

    def test_with_select_in_the_modelling_a_building_shows_its_corners_and_nothing_else_does(self):
        win, b = self.win, self.back
        win._set_tool("select")
        win._select("building", "g1")
        self.assertEqual(len(b.vertices), len(win.vertex_handles))
        self.assertGreater(len(b.vertices), 0)
        self.assertEqual(b.vertex_reach, gizmo.VERTEX_TOLERANCE_SELECT)    # not to take the clicks of what is around them
        win._select("subfield", win.project.subfields[0].id)
        self.assertEqual(b.vertices, [])
        win._select("site", "")
        self.assertEqual(b.vertices, [])

    def test_in_the_other_phases_only_with_move(self):
        win, b = self.win, self.back
        win._select("building", "g1")
        self.assertTrue(b.vertices)
        win.show_phase("plant")
        self.assertEqual(win.plan.tool, "select")
        self.assertEqual(b.vertices, [])
        win._set_tool("move")
        self.assertEqual(b.vertex_reach, gizmo.VERTEX_TOLERANCE)

    def test_a_click_beside_a_corner_stays_a_click_of_the_selection(self):
        win, b = self.win, self.back
        win._select("building", "g1")
        b.resized(800.0, 600.0)
        picks = []
        b.picked.connect(lambda *a: picks.append(a))
        x, y = b.camera.project(b.vertices[0], *b.size)
        off = gizmo.VERTEX_TOLERANCE_SELECT + 2
        b.press(1, 0, x + off, y, False, 0.0, 0.0, 0.0, "", -1)
        b.release(1, 0, x + off, y)
        self.assertEqual(len(picks), 1)
        self.assertEqual(b.vertex_on, -1)

    def test_the_status_bar_and_the_cursor_say_what_a_corner_is_and_go_back(self):
        win, b = self.win, self.back
        win._select("building", "g1")
        b.resized(800.0, 600.0)
        win.hint.setText("before")
        x, y = b.camera.project(b.vertices[0], *b.size)
        b.move(0, x, y)
        self.assertIn("Right button", win.hint.text())
        self.assertEqual(win.view3d.cursor().shape(), Qt.CursorShape.SizeVerCursor)
        self.assertIn("Right button", win.view3d.toolTip())
        b.move(0, x + 200, y + 200)
        self.assertEqual(win.hint.text(), "before")
        self.assertEqual(win.view3d.toolTip(), "")

    def test_the_field_keeps_off_the_cube_and_the_bar(self):
        win, view = self.win, self.win.view3d
        win._select("building", "g1")
        b = self.back
        self.back.vertexClicked.emit(0)
        cube = view.cube.geometry()
        at = np.array([cube.left() - 2.0, cube.bottom() - 10.0])
        with mock.patch.object(b.camera, "project", return_value=(float(at[0]), float(at[1]))):
            view.place_vertex_field()
        self.assertFalse(self.field.geometry().intersects(cube))

    def test_corners_taken_on_one_roof_do_not_pass_to_another(self):
        win, b = self.win, self.back
        win._select("building", "g1")
        b.vertexClicked.emit(0)
        win._select("building", self.flat)
        self.assertEqual(b.vertex_on, -1)
        self.assertEqual(b.vertices_on, set())

    def _dragged_up(self, metres):
        """A corner of the gable pressed and dragged up by `metres`: the meshes the 3D view was given, and where."""
        win, b = self.win, self.back
        b.resized(800.0, 600.0)
        win._select("building", "g1")
        shown = []
        real = win.view3d.geometry_.set_mesh

        def spy(pos, nor, col):
            shown.append(np.array(pos))
            real(pos, nor, col)
        patch = mock.patch.object(win.view3d.geometry_, "set_mesh", spy)
        patch.start()
        self.addCleanup(patch.stop)
        x, y = b.camera.project(b.vertices[1], *b.size)
        tx, ty = b.camera.project(b.vertices[1] + np.array([0.0, metres, 0.0]), *b.size)
        b.press(1, 0, x, y, False, 0.0, 0.0, 0.0, "", -1)
        b.move(0, tx, ty)
        _setup.turn_events(self.app, 60)
        return shown, tx, ty

    def test_the_model_follows_the_corner_dragged_and_only_the_release_changes_the_project(self):
        win, b = self.win, self.back
        steps = win.undo.count()
        shown, tx, ty = self._dragged_up(4.0)
        self.assertTrue(shown, "the model was not drawn during the drag")
        real = win._scene_mesh(win.project)[0]
        self.assertFalse(np.array_equal(shown[-1], real))                   # the corner went, in the view
        tried = roof_vertices.handles_of(win.vertex_trial, "building", "g1")
        before = roof_vertices.handles_of(win.project, "building", "g1")
        self.assertAlmostEqual(tried[1].z, before[1].z + 4.0, delta=0.5)
        self.assertEqual(win.undo.count(), steps)                           # not done yet
        self.assertEqual(self.gable().roof.type, "gable")
        b.release(1, 0, tx, ty)
        _setup.turn_events(self.app, 60)
        self.assertEqual(win.undo.count(), steps + 1)
        self.assertIsNone(win.vertex_trial)

    def test_esc_during_the_drag_brings_the_model_back(self):
        win, b = self.win, self.back
        shown, tx, ty = self._dragged_up(4.0)
        steps = win.undo.count()
        self.assertFalse(np.array_equal(shown[-1], win._scene_mesh(win.project)[0]))
        self.assertTrue(b.cancel_vertex())
        b.release(1, 0, tx, ty)
        _setup.turn_events(self.app, 60)
        self.assertIsNone(win.vertex_trial)
        self.assertTrue(np.array_equal(shown[-1], win._scene_mesh(win.project)[0]))
        self.assertEqual(win.undo.count(), steps)
        self.assertEqual(self.gable().roof.type, "gable")

    # R356

    def test_ctrl_or_shift_choose_more_and_a_drag_takes_them_in_one_step(self):
        win, b = self.win, self.back
        win._select("building", "g1")
        b.resized(800.0, 600.0)
        for at, flag in ((0, 0x04000000), (1, 0x02000000)):                # Ctrl, Shift
            x, y = b.camera.project(b.vertices[at], *b.size)
            b.press(1, flag, x, y, False, 0.0, 0.0, 0.0, "", -1)
            b.release(1, flag, x, y)
        self.assertEqual(b.vertices_on, {0, 1})
        self.assertEqual(self.field.mark, "2")
        was = [h.z for h in win.vertex_handles]
        steps = win.undo.count()
        b.vertexDragged.emit(1, 1.5)
        self.assertEqual(win.undo.count(), steps + 1)
        now = [h.z for h in win.vertex_handles]
        self.assertAlmostEqual(now[0], was[0] + 1.5)
        self.assertAlmostEqual(now[1], was[1] + 1.5)
        self.assertEqual(self.back.vertices_on, {0, 1})                    # still chosen
        win.undo.undo()
        self.assertEqual(self.gable().roof.type, "gable")

    def test_a_ctrl_click_again_takes_it_out_and_a_plain_click_leaves_one(self):
        win, b = self.win, self.back
        win._select("building", "g1")
        b.vertexToggled.emit(0)
        b.vertexToggled.emit(1)
        b.vertexToggled.emit(1)
        self.assertEqual(b.vertices_on, {0})
        b.vertexToggled.emit(0)
        self.assertEqual(b.vertices_on, set())
        self.assertFalse(self.field.isVisibleTo(win.view3d))
        b.vertexToggled.emit(0)
        b.vertexToggled.emit(1)
        b.vertexClicked.emit(2)
        self.assertEqual(b.vertices_on, {2})

    def test_written_with_a_sign_each_keeps_its_own_without_one_they_are_one_height(self):
        win, b = self.win, self.back
        win._select("building", "g1")
        ridge = max(range(len(win.vertex_handles)), key=lambda i: win.vertex_handles[i].z)
        eave = min(range(len(win.vertex_handles)), key=lambda i: win.vertex_handles[i].z)
        b.vertexToggled.emit(eave)
        b.vertexToggled.emit(ridge)
        self.assertEqual(self.field.field.text(), "+0")                    # two heights: nothing to show as one
        steps = win.undo.count()
        self.field.typed.emit("+0")
        self.assertEqual(win.undo.count(), steps)
        hi, lo = win.vertex_handles[ridge].z, win.vertex_handles[eave].z
        win._vertex_open()
        self.field.typed.emit("+1")
        self.assertEqual(win.undo.count(), steps + 1)
        self.assertAlmostEqual(win.vertex_handles[ridge].z, hi + 1.0, places=2)
        self.assertAlmostEqual(win.vertex_handles[eave].z, lo + 1.0, places=2)
        win._vertex_open()
        self.field.typed.emit("9")
        self.assertEqual(win.undo.count(), steps + 2)
        self.assertAlmostEqual(win.vertex_handles[ridge].z, 9.0)
        self.assertAlmostEqual(win.vertex_handles[eave].z, 9.0)

    def test_one_refused_refuses_them_all(self):
        win, b = self.win, self.back
        win._select("building", "g1")
        b.vertexToggled.emit(0)
        b.vertexToggled.emit(1)
        steps = win.undo.count()
        self.field.typed.emit("-50")
        self.assertEqual(win.undo.count(), steps)
        self.assertIn("ground", win.hint.text())
        self.assertEqual(self.gable().roof.type, "gable")

    def test_a_drag_on_a_corner_not_chosen_moves_it_alone(self):
        win, b = self.win, self.back
        win._select("building", "g1")
        b.vertexToggled.emit(0)
        was = [h.z for h in win.vertex_handles]
        b.vertexDragged.emit(1, 1.0)
        now = [h.z for h in win.vertex_handles]
        self.assertAlmostEqual(now[1], was[1] + 1.0)
        self.assertAlmostEqual(now[0], was[0])

    def test_the_box_adds_ctrl_takes_out_and_a_click_stays_a_click(self):
        win, b = self.win, self.back
        win._select("building", "g1")
        b.resized(800.0, 600.0)
        at = [b.camera.project(p, *b.size) for p in b.vertices]
        x0, x1 = min(q[0] for q in at) - 5, max(q[0] for q in at) + 5
        y0, y1 = min(q[1] for q in at) - 5, max(q[1] for q in at) + 5
        ring = x0 - 300 if x0 > 300 else x1 + 300

        def box(mods):
            b.press(1, mods, x0, y0, False, 0.0, 0.0, 0.0, "", -1)
            b.move(mods, (x0 + x1) / 2, (y0 + y1) / 2)
            self.assertTrue(b.vertexBox["on"])
            self.assertEqual(b.vertexBox["remove"], bool(mods))
            b.move(mods, x1, y1)
            b.release(1, mods, x1, y1)
            self.assertFalse(b.vertexBox["on"])

        picks = []
        b.picked.connect(lambda *a: picks.append(a))
        steps = win.undo.count()
        box(0)
        self.assertEqual(b.vertices_on, set(range(len(b.vertices))))
        self.assertEqual(picks, [])                                        # a box is not a click
        box(0x04000000)
        self.assertEqual(b.vertices_on, set())
        self.assertEqual(win.undo.count(), steps)                          # choosing changes nothing
        b.press(1, 0, ring, y0, False, 0.0, 0.0, 0.0, "", -1)
        b.release(1, 0, ring, y0)
        self.assertEqual(len(picks), 1)

    def test_with_a_style_that_uses_the_left_button_there_is_no_box(self):
        win, b = self.win, self.back
        win._select("building", "g1")
        b.navigator.set_style("openscad")
        b.resized(800.0, 600.0)
        b.press(1, 0, 10.0, 10.0, False, 0.0, 0.0, 0.0, "", -1)
        b.move(0, 200.0, 200.0)
        self.assertFalse(b.vertexBox["on"])
        b.release(1, 0, 200.0, 200.0)

    # R357

    def test_a_flat_roof_stays_flat_and_its_building_changes_height_one_step(self):
        win, b = self.win, self.back
        win._select("building", self.flat)
        building = win.project.buildings[0]
        roof_type, height = building.roof.type, building.height
        self.assertEqual(roof_type, "flat")
        steps = win.undo.count()
        b.vertexClicked.emit(2)
        self.field.typed.emit("+2")
        self.assertEqual(win.undo.count(), steps + 1)
        building = win.project.buildings[0]
        self.assertEqual(building.roof.type, "flat")
        self.assertAlmostEqual(building.height, height + 2.0)
        self.assertTrue(all(abs(h.z - (height + 2.0)) < 1e-6 for h in win.vertex_handles))
        self.assertNotIn("parapet", win.hint.text())
        self.assertIn("flat roof", win.hint.text())
        self.assertEqual(b.vertex_on, 2)
        win.undo.undo()
        self.assertAlmostEqual(win.project.buildings[0].height, height)

    def test_the_modules_and_the_outline_go_with_it(self):
        win, b = self.win, self.back
        win._select("building", self.flat)
        sf = win.project.subfields[0]
        self.assertTrue(_setup.wait_until(self.app, lambda: sf.id in win.results, 30))
        before = win.results[sf.id]
        win.vertex_taken = None
        b.vertexClicked.emit(0)
        self.field.typed.emit("+3")
        self.assertTrue(_setup.wait_until(self.app, lambda: win.results.get(sf.id) is not before, 30))
        self.assertEqual(sum(m.rid is not None for m in win.results[sf.id].modules),
                         sum(m.rid is not None for m in before.modules))
        tops = [o["z1"] for o in win.project.obstacle_prisms() if o.get("kind") == "parapet"]
        self.assertTrue(all(abs(t - (9.5 + 3.0 + 1.0)) < 1e-6 for t in tops))

    def test_make_it_pitched_is_asked_for_and_says_what_it_does(self):
        win, b = self.win, self.back
        win._select("building", self.flat)
        steps = win.undo.count()
        names = self.menu_of(0)
        self.assertNotIn("Part", names)
        names["Make it pitched"].trigger()
        self.assertEqual(win.undo.count(), steps + 1)
        self.assertEqual(win.project.buildings[0].roof.type, "free")
        self.assertIn("drawn by hand", win.hint.text())
        self.assertIn("parapet", win.hint.text())
        b.vertexClicked.emit(2)
        self.field.typed.emit("+2")
        self.assertIn("off one plane", win.hint.text())
        win.undo.undo()
        win.undo.undo()
        self.assertEqual(win.project.buildings[0].roof.type, "flat")


if __name__ == "__main__":
    unittest.main()
