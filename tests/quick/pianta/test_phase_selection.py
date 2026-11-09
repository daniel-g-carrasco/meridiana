"""What the plan can take in each phase, the corners, the anchored selection, Tab, the split and the clipboard, on the
controller without a window (R426, R427, R432). The gestures in the real window are in quick/percorsi."""
import unittest

from PySide6.QtWidgets import QApplication
from shapely.geometry import Polygon

from meridiana import i18n, model
from meridiana.quick.backend.plan import PlanController
from meridiana.quick.backend.plan_edit import VERTEX_PX, nearest_vertex
from meridiana.session import ProjectSession

app = QApplication.instance() or QApplication([])


def project():
    p = model.Project(name="Prova")
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=8.0, roof=model.Roof(type="gable", tilt=15.0)))
    b = p.buildings[0]
    south = next(i for i, q in enumerate(b.pitches()) if Polygon(q.ring).centroid.y < 10)
    p.subfields.append(model.SubField(id="s1", name="Tetto", ring=[[10, 2], [30, 2], [30, 8], [10, 8]], building="b1",
                                      pitch=b.pitch_ref(south), filled=True, params={"mounting": "coplanar"}))
    p.exclusions.append(model.ExclusionItem(id="e1", ring=[[2, 2], [6, 2], [6, 6], [2, 6]], kind="skylight",
                                            building="b1"))
    p.props.append(model.Prop(id="o1", kind="broadleaf", at=[60.0, 10.0]))
    return p


class Base(unittest.TestCase):
    def setUp(self):
        self.language = i18n.language()
        i18n.setup("en")
        self.addCleanup(i18n.setup, self.language)
        self.session = ProjectSession(project())
        self.c = PlanController(self.session, manage_layout=False)
        self.e = self.c.editor
        self.lay()
        self.c.pointerScale(.02, 0.)

    def tearDown(self):
        self.c.close()

    def lay(self):
        results = {sf.id: self.session.project.fill(sf) for sf in self.session.project.subfields if sf.filled}
        self.session.results.clear()
        self.session.results.update(results)
        self.c.refresh()

    def phase(self, name):
        self.c.setPhase(name)


class Phases(Base):
    def test_in_plant_only_what_the_modules_are_made_of_is_taken(self):
        self.phase("plant")
        self.assertEqual(self.c.clickKinds, ["module", "subfield"])
        self.c.click(4.0, 4.0, 0)       # an exclusion
        self.assertEqual(self.e.selection, ("site", ""))
        self.assertIn("Modelling", self.e.hint)
        self.c.click(35.0, 15.0, 0)     # a roof
        self.assertEqual(self.e.selection, ("site", ""))
        self.assertEqual(self.e.pick((60.0, 10.0))[0], "site")   # an object
        module = self.session.results["s1"].modules[0]
        self.c.click(*module.centre, 0)
        self.assertEqual(self.e.selection, ("subfield", "s1"))

    def test_in_modelling_the_model_is_taken_and_modules_do_not_catch(self):
        self.phase("model")
        self.assertEqual(self.c.clickKinds, ["building", "exclusion", "prop"])
        module = self.session.results["s1"].modules[0]
        self.c.click(*module.centre, 0)
        self.assertEqual(self.e.selection, ("building", "b1"))
        self.assertEqual(self.e.selected_module, ("", ""))
        self.c.key("Escape", "", 0)
        self.c.click(4.0, 4.0, 0)
        self.assertEqual(self.e.selection, ("exclusion", "e1"))

    def test_a_click_on_a_sub_field_on_the_ground_in_modelling_says_where_it_is_changed(self):
        self.session.edit("Ground", lambda p: p.subfields.append(model.SubField(
            id="g1", name="Prato", ring=[[50, -20], [70, -20], [70, -10], [50, -10]])))
        self.phase("model")
        self.c.click(60.0, -15.0, 0)
        self.assertEqual(self.e.selection, ("site", ""))
        self.assertIn("Plant", self.e.hint)

    def test_changing_phase_drops_what_the_new_phase_cannot_take(self):
        self.phase("model")
        self.c.click(4.0, 4.0, 0)
        self.phase("plant")
        self.assertEqual(self.e.selection, ("site", ""))
        self.assertEqual(self.c.grips, [])
        self.c.click(*self.session.results["s1"].modules[0].centre, 0)
        self.phase("model")
        self.assertEqual(self.e.selection, ("site", ""))

    def test_esc_in_plant_goes_up_to_nothing_not_to_the_building(self):
        self.phase("plant")
        self.c.click(*self.session.results["s1"].modules[0].centre, 0)
        self.c.key("Escape", "", 0)
        self.assertEqual(self.e.selection, ("subfield", "s1"))
        self.c.key("Escape", "", 0)
        self.assertEqual(self.e.selection, ("site", ""))

    def test_an_object_chosen_in_the_tree_is_lit_without_corners_and_does_not_move(self):
        self.phase("plant")
        self.session.select("building", "b1")
        self.c._overlays()
        self.assertTrue(self.c.highlights)
        self.assertEqual(self.c.grips, [])
        self.assertFalse(self.e._movable())

    def test_a_sweep_in_each_phase_takes_what_the_phase_takes(self):
        area = [[-5, -5], [45, -5], [45, 25], [-5, 25]]
        self.phase("model")
        self.c.sweep(area, "window", 0)
        self.assertEqual(sorted(k for k, _oid in self.e.swept_things), ["building", "exclusion"])
        self.assertEqual(self.e.swept, [])
        self.phase("plant")
        self.c.sweep(area, "window", 0)
        self.assertEqual(self.e.swept_things, [])
        self.assertEqual(len(self.e.swept), len(self.session.results["s1"].modules))

    def test_ways_of_working_stay_open(self):
        # Plant: a sub-field on each pitch from a building that cannot be selected.
        self.phase("plant")
        self.c.contextAt(35.0, 15.0)
        commands = [row["command"] for row in self.c.contextItems]
        self.assertIn("pitches", commands)
        self.c.contextCommand("pitches")
        self.assertEqual(len(self.session.project.subfields), 3)
        # Modelling: Move on a building takes its sub-fields along.
        self.phase("model")
        self.c.click(35.0, 15.0, 0)
        self.c.setTool("move")
        self.assertTrue(self.e._movable())
        # Plant: Move on a sub-field.
        self.phase("plant")
        self.e.select("subfield", "s1")
        self.c.setTool("move")
        self.assertTrue(self.e._movable())


class Corners(Base):
    def select_s1(self):
        self.phase("plant")
        self.c.setTool("select")
        self.e.select("subfield", "s1")
        self.c._overlays()

    def test_the_reach_is_between_twelve_and_fourteen_logical_pixels(self):
        self.assertGreaterEqual(VERTEX_PX, 12)
        self.assertLessEqual(VERTEX_PX, 14)

    def test_at_every_zoom_the_reach_is_the_same_in_pixels(self):
        self.select_s1()
        for pixels_per_metre in (2.0, 50.0, 400.0):
            mpp = 1/pixels_per_metre
            self.assertEqual(self.c.vertexAt(10.0+12*mpp, 2.0, mpp), 0)
            self.assertEqual(self.c.vertexAt(10.0+14*mpp, 2.0, mpp), -1)

    def test_of_two_corners_in_reach_the_nearer_wins(self):
        ring = [(0.0, 0.0), (1.0, 0.0)]
        self.assertEqual(nearest_vertex(ring, (.6, 0.), 2.), 1)
        self.assertEqual(nearest_vertex(ring, (.4, 0.), 2.), 0)
        self.assertEqual(nearest_vertex(ring, (9., 0.), 2.), -1)

    def test_a_module_selected_keeps_the_corners_of_its_sub_field_a_row_has_none(self):
        self.phase("plant")
        modules = self.session.results["s1"].modules
        self.c.click(*modules[0].centre, 0)
        self.assertEqual(self.e.selected_module[0], "s1")
        self.assertEqual(len(self.c.grips), 4)
        self.assertEqual(self.c.vertexAt(10.0, 2.0, .02), 0)
        self.c.click(*modules[0].centre, 0)
        self.assertEqual(self.e.selection[0], "row")
        self.assertEqual(self.c.grips, [])

    def test_a_linear_object_has_the_corners_of_its_path(self):
        self.session.edit("Hedge", lambda p: p.props.append(model.Prop(
            id="o2", kind="hedge", at=[60.0, 30.0], path=[[60.0, 30.0], [70.0, 30.0], [70.0, 35.0]])))
        self.phase("model")
        self.e.select("prop", "o2")
        self.c._overlays()
        self.assertEqual([(g["x"], g["y"]) for g in self.c.grips], [(60.0, 30.0), (70.0, 30.0), (70.0, 35.0)])
        self.c.vertex(1, 72.0, 30.0)
        self.assertEqual(self.session.project.prop("o2").path[1], [72.0, 30.0])

    def test_a_free_pitch_has_its_corners(self):
        ring = [[0, 0], [20, 0], [20, 20], [0, 20]]
        from meridiana import roofs

        def free(p):
            b = p.building("b1")
            b.roof = model.Roof(type="free", free_pitches=[{**roofs.free_spec(ring, False, 8.0, 15.0), "ring": ring}])
            p.subfields.clear()
        self.session.edit("Free", free)
        self.lay()
        self.phase("model")
        self.e.cycle((10.0, 10.0))      # exclusion is not under it: pitch first
        self.assertEqual(self.e.selection[0], "pitch")
        self.c._overlays()
        self.assertEqual(len(self.c.grips), 4)


    def test_a_corner_does_not_snap_onto_a_side_of_its_own(self):
        self.select_s1()
        near_own_side = self.c.snapCorner(0, 20.0, 7.9, 0, .1)      # the side y = 8 is a pixel away
        self.assertEqual((near_own_side.x(), near_own_side.y()), (20.0, 7.9))
        elsewhere = self.c.snapVertex(20.0, 7.9, 0, .1)
        self.assertEqual(elsewhere.y(), 8.0)

    def test_a_refusal_goes_with_the_next_gesture(self):
        self.select_s1()
        self.c.vertex(0, 20.0, 8.0)
        self.assertTrue(self.c.error)
        self.c.click(*self.session.results["s1"].modules[0].centre, 0)
        self.assertEqual(self.c.error, "")


class Anchored(Base):
    def test_a_click_inside_what_is_selected_stays_on_it(self):
        self.phase("model")
        self.c.click(35.0, 15.0, 0)
        self.assertEqual(self.e.selection, ("building", "b1"))
        self.c.click(4.0, 4.0, 0)       # on the skylight, inside the building
        self.assertEqual(self.e.selection, ("building", "b1"))

    def test_a_click_outside_lets_go(self):
        self.phase("model")
        self.c.click(4.0, 4.0, 0)
        self.assertEqual(self.e.selection, ("exclusion", "e1"))
        self.c.click(35.0, 15.0, 0)
        self.assertEqual(self.e.selection, ("building", "b1"))
        self.c.click(-30.0, -30.0, 0)
        self.assertEqual(self.e.selection, ("site", ""))

    def test_esc_lets_go(self):
        self.phase("model")
        self.c.click(35.0, 15.0, 0)
        self.c.key("Escape", "", 0)
        self.c.click(4.0, 4.0, 0)
        self.assertEqual(self.e.selection, ("exclusion", "e1"))

    def test_in_plant_the_click_stays_on_the_modules_of_the_sub_field(self):
        self.phase("plant")
        modules = self.session.results["s1"].modules
        self.c.click(*modules[0].centre, 0)
        self.assertEqual(self.e.selected_module, ("s1", modules[0].key))
        self.c.click(*modules[-1].centre, 0)
        self.assertEqual(self.e.selected_module, ("s1", modules[-1].key))

    def test_the_anchor_tells_the_overlay_what_a_click_would_do(self):
        self.phase("model")
        self.c.click(35.0, 15.0, 0)
        self.assertEqual(self.c.anchor["oid"], "b1")
        self.assertEqual(self.c.anchor["ring"][1], [40.0, -0.0])


class Tab(Base):
    def test_tab_walks_what_lies_under_the_pointer_and_says_it(self):
        self.phase("model")
        seen = []
        for _step in range(4):
            self.e.pointer = (4.0, 4.0)
            self.c.key("Tab", "", 0)
            seen.append(self.e.selection)
        self.assertEqual(seen[0], ("exclusion", "e1"))
        self.assertEqual(seen[1][0], "pitch")
        self.assertEqual(seen[2], ("building", "b1"))
        self.assertEqual(seen[3], ("exclusion", "e1"))
        self.assertIn("Tab", self.e.hint)
        self.assertIn("3", self.e.hint)

    def test_shift_tab_walks_back(self):
        self.phase("model")
        self.e.pointer = (4.0, 4.0)
        self.c.key("Backtab", "", 2)
        self.assertEqual(self.e.selection, ("building", "b1"))

    def test_tab_reaches_a_sub_field_under_another_in_plant(self):
        self.session.edit("Other", lambda p: p.subfields.append(model.SubField(
            id="s2", name="Altro", ring=[[10, 2], [30, 2], [30, 8], [10, 8]], building="b1", pitch=p.subfields[0].pitch)))
        self.phase("plant")
        self.e.pointer = (12.0, 2.5)
        stack = self.e.pick_stack((12.0, 2.5))
        self.assertIn(("subfield", "s2", ""), stack)
        for _step in stack:
            self.c.key("Tab", "", 0)
            if self.e.selection == ("subfield", "s2"):
                break
        self.assertEqual(self.e.selection, ("subfield", "s2"))

    def test_the_hint_says_tab(self):
        for name in ("model", "plant"):
            self.phase(name)
            self.assertIn("Tab", self.e.hint)


class Split(Base):
    def astride(self):
        self.phase("plant")
        self.e.select("subfield", "s1")
        self.c.setTool("move")
        self.e.apply_command(dict(type="transform", kind="subfield", oid="s1", mode="move", dx=0.0, dy=6.0))
        self.c.setTool("select")

    def test_a_move_astride_says_the_plane_it_is_computed_on(self):
        self.phase("plant")
        self.e.apply_command(dict(type="transform", kind="subfield", oid="s1", mode="move", dx=0.0, dy=6.0))
        self.assertIn("computed on the plane", self.e.hint)
        self.assertEqual(self.e.last_error, "")

    def test_a_move_over_says_the_new_pitch(self):
        self.phase("plant")
        self.e.apply_command(dict(type="transform", kind="subfield", oid="s1", mode="move", dx=0.0, dy=10.0))
        self.assertIn("Now on pitch", self.e.hint)

    def test_the_menu_offers_the_split_only_when_astride(self):
        self.phase("plant")
        self.e.select("subfield", "s1")
        self.assertNotIn("split_pitches", [r["command"] for r in self.c.contextItems])
        self.astride()
        self.e.select("subfield", "s1")
        self.assertIn("split_pitches", [r["command"] for r in self.c.contextItems])

    def test_split_from_the_menu_one_undo_then_redo(self):
        self.astride()
        self.e.select("subfield", "s1")
        self.c.contextCommand("split_pitches")
        self.assertEqual(len(self.session.project.subfields), 2)
        self.assertEqual(self.e.selection, ("subfield", "s1"))
        self.assertIn("leave_group", [r["command"] for r in self.c.contextItems])
        self.session.undo.undo()
        self.assertEqual(len(self.session.project.subfields), 1)
        self.session.undo.redo()
        self.assertEqual(len(self.session.project.subfields), 2)

    def test_leaving_the_group_from_the_menu(self):
        self.astride()
        self.e.select("subfield", "s1")
        self.c.contextCommand("split_pitches")
        self.c.contextCommand("leave_group")
        self.assertEqual(self.session.subfield("s1").group, "")

    def test_the_check_fix_splits(self):
        from types import SimpleNamespace

        from meridiana.quick.backend.checks import ChecksBackend
        self.astride()
        fake = SimpleNamespace(session=self.session)
        item = SimpleNamespace(fix=("action", "split_pitches", "subfield", "s1"), fix_label="Split")
        ChecksBackend._apply_fix(fake, item)
        self.assertEqual(len(self.session.project.subfields), 2)


class Clipboard(Base):
    def test_copy_paste_under_the_pointer_with_a_preview_and_one_undo(self):
        self.phase("plant")
        self.e.select("subfield", "s1")
        self.c.key("C", "", 1)
        self.assertEqual(self.e.clip.kind, "subfield")
        self.c.pointer(20.0, 15.0, 0, .02)
        self.c.key("V", "", 1)
        self.assertEqual(self.c.tool, "paste")
        self.assertEqual(len(self.c.preview["rings"]), 1)
        self.assertEqual(self.c.preview["refused"], "")
        self.assertIn("pitch", self.c.hint)
        self.assertTrue(self.c.draftObjects)
        undos = self.session.undo.count()
        self.c.click(20.0, 15.0, 0)
        self.assertEqual(self.c.tool, "select")
        self.assertEqual(len(self.session.project.subfields), 2)
        new = self.session.project.subfields[1]
        self.assertEqual(self.e.selection, ("subfield", new.id))
        self.assertEqual(self.session.undo.count(), undos + 1)
        self.assertIn("in no string", self.e.hint)
        self.session.undo.undo()
        self.assertEqual(len(self.session.project.subfields), 1)

    def test_a_paste_off_the_roof_is_refused_and_said_and_the_tool_stays(self):
        self.phase("plant")
        self.e.select("subfield", "s1")
        self.c.key("C", "", 1)
        self.c.pointer(20.0, 1.0, 0, .02)
        self.c.key("V", "", 1)
        self.assertIn("off its roof", self.c.preview["refused"])
        self.assertIn("off its roof", self.c.hint)
        self.c.click(20.0, 1.0, 0)
        self.assertEqual(len(self.session.project.subfields), 1)
        self.assertIn("off its roof", self.c.error)
        self.assertEqual(self.c.tool, "paste")
        self.c.key("Escape", "", 0)
        self.assertEqual(self.c.tool, "select")

    def test_cut_and_paste_are_one_undo(self):
        self.phase("plant")
        self.e.select("subfield", "s1")
        undos = self.session.undo.count()
        before = self.session.snapshot()
        self.c.key("X", "", 1)
        self.assertEqual(len(self.session.project.subfields), 0)
        self.assertEqual(self.e.selection, ("site", ""))
        self.c.pointer(20.0, 15.0, 0, .02)
        self.c.key("V", "", 1)
        self.c.click(20.0, 15.0, 0)
        self.assertEqual(len(self.session.project.subfields), 1)
        self.assertEqual(self.session.undo.count(), undos + 1)
        self.session.undo.undo()
        self.assertEqual(self.session.snapshot(), before)

    def test_each_phase_pastes_its_own(self):
        self.phase("plant")
        self.e.select("subfield", "s1")
        self.c.key("C", "", 1)
        self.phase("model")
        self.c.key("V", "", 1)
        self.assertIn("Plant", self.c.error)
        self.assertEqual(self.c.tool, "select")
        self.c.click(4.0, 4.0, 0)
        self.c.key("C", "", 1)
        self.c.pointer(30.0, 15.0, 0, .02)
        self.c.key("V", "", 1)
        self.c.click(30.0, 15.0, 0)
        self.assertEqual(len(self.session.project.exclusions), 2)

    def test_a_module_selected_is_not_a_sub_field_to_cut(self):
        self.phase("plant")
        self.c.click(*self.session.results["s1"].modules[0].centre, 0)
        self.c.key("X", "", 1)
        self.assertEqual(len(self.session.project.subfields), 1)
        self.assertTrue(self.c.error)

    def test_nothing_to_paste_is_said(self):
        self.phase("plant")
        self.c.key("V", "", 1)
        self.assertTrue(self.c.error)
        self.assertEqual(self.c.tool, "select")

    def test_the_menu_has_them(self):
        self.phase("plant")
        self.e.select("subfield", "s1")
        names = [r["command"] for r in self.c.contextItems]
        self.assertIn("copy", names)
        self.assertIn("cut", names)
        self.assertNotIn("paste", names)
        self.c.contextCommand("copy")
        self.assertIn("paste", [r["command"] for r in self.c.contextItems])


if __name__ == "__main__":
    unittest.main()
