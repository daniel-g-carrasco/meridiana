"""R295, R299, R300, R344, R388: pure plan editing and undo contracts."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from shapely.geometry import Polygon

from meridiana import manual, model, move
from meridiana.session import ProjectSession
from meridiana.quick.backend.plan_edit import PlanEditor


def project():
    p = model.Project()
    p.buildings.append(model.Building(id="b1", name="Shed", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]]))
    p.subfields.append(model.SubField(id="s1", name="South", building="b1", filled=True,
                                    ring=[[1, 1], [39, 1], [39, 19], [1, 19]], params={"tilt": 15.0}))
    return p


class EditorTest(unittest.TestCase):
    def setUp(self):
        self.session = ProjectSession(project())
        self.editor = PlanEditor(self.session)
        self.result = self.session.project.fill(self.session.project.subfields[0])
        self.editor.set_results({"s1": self.result})
        self.module = self.result.modules[0]

    def test_m05_an_empty_string_and_esc_go_back_to_select(self):
        e = self.editor
        e.set_tool("string")
        e.start_draft(1, 1)
        e.finish_draft()
        self.assertEqual(e.tool, "select")
        e.set_tool("string")
        e.start_draft(1, 1)
        e.key("Escape")
        self.assertIsNone(e.draft)
        self.assertEqual(e.tool, "select")

    def test_pick_twenty_thousand_modules_caches_shapes(self):
        self.editor.set_phase("plant")
        modules = [SimpleNamespace(key=str(i), corners=[(i*2, 0), (i*2+1, 0),
                                                       (i*2+1, 1), (i*2, 1)]) for i in range(20000)]
        self.editor.set_results({"s1": SimpleNamespace(modules=modules)})
        with patch("meridiana.quick.backend.plan_edit.Polygon", wraps=Polygon) as polygons:
            self.assertEqual(self.editor.pick((39998.5, .5)), ("module", "s1", "19999"))
            self.assertEqual(self.editor.pick((39998, 0)), ("module", "s1", "19999"))
            self.assertLess(polygons.call_count, 10, "Point picking must not construct every module polygon")
        index = self.editor._quad_indexes["s1"]
        self.editor.pick((39999, 1))
        self.assertIs(self.editor._quad_indexes["s1"], index)
        self.session.project.subfields[0].removed = ["19999"]
        self.assertEqual(self.editor.pick((39998.5, .5)), ("site", "", ""))
        self.editor.set_results({"s1": SimpleNamespace(modules=[])})
        self.assertEqual(self.editor.pick((39998.5, .5)), ("site", "", ""))

    def test_touchpad_pick_six_pixels_and_nearest_across_subfields(self):
        self.editor.set_phase("plant")
        e = self.editor
        first = SimpleNamespace(key="one", rid="row1", corners=[(0, 0), (1, 0), (1, 1), (0, 1)])
        second = SimpleNamespace(key="two", rid="row2", corners=[(4, 0), (5, 0), (5, 1), (4, 1)])
        self.session.project.subfields.append(model.SubField(id="s2", name="Second", ring=[[3, -1], [6, -1], [6, 2], [3, 2]]))
        e.set_results({"s1": SimpleNamespace(modules=[first]), "s2": SimpleNamespace(modules=[second])})
        for mpp in (.125, .25):
            e.pick_reach = 6*mpp
            self.assertEqual(e.pick((1+6*mpp, .5)), ("module", "s1", "one"))
            self.assertNotEqual(e.pick((-7*mpp, .5))[0], "module")
        e.pick_reach = 2
        self.assertEqual(e.pick((3, .5)), ("module", "s2", "two"))
        self.session.project.subfields[1].removed = ["two"]
        self.assertEqual(e.pick((3, .5)), ("module", "s1", "one"))

    def test_hot_grip_cycles_and_typed_commit(self):
        e = self.editor
        e.select("building", "b1")
        e.start_grip("move", (20, 10))
        self.assertTrue(e.gesture.grip)
        self.assertEqual(e.gesture.base, (20, 10))
        e.key("Space")
        self.assertEqual((e.tool, e.gesture.mode), ("rotate", "rotate"))
        e.key("Enter")
        self.assertEqual((e.tool, e.gesture.mode), ("move", "move"))
        self.assertEqual(self.session.undo.count(), 0)
        e.key("", "3;2")
        e.key("Enter", modifiers={"ctrl"})
        self.assertEqual(len(self.session.project.buildings), 2)
        self.assertEqual(self.session.undo.count(), 1)
        e.start_grip("rotate", (20, 20))
        self.assertEqual(e.gesture.mode, "rotate")
        e.key("C")
        e.key("", "90")
        e.key("Enter")
        self.assertEqual(len(self.session.project.buildings), 3)
        self.assertIsNone(e.gesture)

    def refresh(self):
        result = self.session.project.fill(self.session.project.subfields[0])
        self.editor.set_results({"s1": result})
        return result

    def test_manual_row_move_preserves_keys_and_refuses_exit(self):
        e = self.editor
        e.set_phase("plant")
        row = self.result.rows[1]
        before = {m.key: m.centre for m in self.result.modules}
        e.select("row", "s1/"+row.id)
        e.set_tool("move")
        e.key("", "0;0.2")
        e.key("Enter")
        after = self.refresh()
        self.assertEqual(set(before), {m.key for m in after.modules})
        for m in after.modules:
            self.assertAlmostEqual(m.centre[1]-before[m.key][1], .2 if m.rid == row.id else 0, places=3)
        saved = self.session.snapshot()
        e.key("", "0;-40")
        result = e.key("Enter")
        self.assertEqual(result[0]["type"], "error")
        self.assertEqual(self.session.snapshot(), saved)
        self.assertEqual(self.session.undo.count(), 1)

    def test_manual_row_resize_append_and_undo(self):
        e = self.editor
        row = next(r for r in self.result.rows if r.places)
        oid = "s1/"+row.id
        end = manual.end_point(row, manual.frame(e.project, e.project.subfields[0], self.result.rows)[1])
        e.apply_command({"type": "row_resize", "oid": oid, "point": (end[0]-3, end[1])})
        shortened = self.refresh()
        size = len([m for m in shortened.modules if m.rid == row.id])
        self.assertLess(size, row.count)
        e.apply_command({"type": "row_append", "oid": oid})
        appended = self.refresh()
        self.assertEqual(len(appended.modules), len(shortened.modules)+size)
        self.session.undo.undo()
        self.session.undo.undo()
        restored = self.refresh()
        self.assertEqual([m.key for m in restored.modules], [m.key for m in self.result.modules])
        self.assertFalse(e.project.subfields[0].manual)

    def test_row_handle_uses_core_endpoint_and_resizes_selected_row(self):
        e = self.editor
        self.assertEqual(e.row_handle(), {})
        row = next(r for r in self.result.rows if r.places)
        oid = "s1/"+row.id
        e.select("row", oid)
        handle = e.row_handle()
        end = manual.end_point(row, manual.frame(e.project, e.project.subfields[0], self.result.rows)[1])
        self.assertAlmostEqual(handle["x"], end[0], places=4)
        self.assertAlmostEqual(handle["y"], end[1], places=4)
        self.assertEqual(handle["oid"], oid)
        self.assertTrue(handle["hint"])
        e.resize_row(oid, (end[0]-3, end[1]))
        self.assertLess(len([m for m in self.refresh().modules if m.rid == row.id]), row.count)
        e.set_tool("move")
        self.assertEqual(e.row_handle(), {})
        self.session.undo.undo()
        e.set_tool("select")
        e.set_results({})
        with patch.object(model.Project, "fill", side_effect=AssertionError("UI property must not lay modules")):
            self.assertEqual(e.row_handle(), {})

    def test_manual_explode_move_turn_delete_module(self):
        e = self.editor
        row = next(r for r in self.result.rows if r.places)
        e.apply_command({"type": "row_explode", "oid": "s1/"+row.id})
        exploded = self.refresh()
        self.assertEqual(sorted(m.key for m in exploded.modules), sorted(m.key for m in self.result.modules))
        target = next(m for m in exploded.modules if m.key == self.module.key)
        e.set_phase("plant")
        e.select("module", "s1", target.key)
        e.set_tool("move")
        e.key("", "0.3;0")
        e.key("Enter")
        moved = self.refresh()
        m = next(m for m in moved.modules if m.key == target.key)
        self.assertAlmostEqual(m.centre[0]-target.centre[0], .3, places=3)
        e.double_click(m.centre)
        turned = self.refresh()
        t = next(x for x in turned.modules if x.key == target.key)
        self.assertNotEqual(t.turned, m.turned)
        self.assertAlmostEqual(t.centre[0], m.centre[0], places=3)
        self.assertAlmostEqual(t.centre[1], m.centre[1], places=3)
        e.set_tool("select")
        e.key("Delete")
        deleted = self.refresh()
        self.assertNotIn(target.key, [m.key for m in deleted.modules])
        self.assertEqual(e.project.subfields[0].removed, [])
        self.session.undo.undo()
        self.assertIn(target.key, [m.key for m in self.refresh().modules])

    def test_sweep_selected_modules_delete_once_and_undo(self):
        e = self.editor
        e.set_phase("plant")
        selected = self.result.modules[:3]
        for m in selected:
            e.click(m.centre, {"ctrl"})
        self.assertEqual(e.swept, [("s1", m.key) for m in selected])
        e.key("Delete")
        self.assertEqual(set(e.project.subfields[0].removed), {m.key for m in selected})
        self.assertEqual(self.session.undo.count(), 1)
        self.session.undo.undo()
        self.assertEqual(e.project.subfields[0].removed, [])

    def test_smallest_row_and_escape(self):
        self.editor.set_phase("plant")
        e = self.editor
        e.click(self.module.centre)
        self.assertEqual(e.selected_module, ("s1", self.module.key))
        e.click(self.module.centre)
        self.assertEqual(e.selection, ("row", "s1/" + self.module.rid))
        for target in [("subfield", "s1"), ("site", "")]:       # the Plant does not select buildings
            e.key("Escape")
            self.assertEqual(e.selection, target)

    def test_move_matches_core_and_undo(self):
        expected = model.Project.from_json(self.session.project.to_json())
        move.translate(expected, "building", "b1", 3, 2)(expected)
        self.editor.select("building", "b1")
        self.editor.set_tool("move")
        self.editor.key("", "3;2")
        self.editor.key("Enter")
        self.assertEqual(self.session.project.to_json(), expected.to_json())
        self.session.undo.undo()
        self.assertEqual(self.session.project.buildings[0].footprint[0], [0, 0])

    def test_nudge_merges_and_copy(self):
        e = self.editor
        e.select("building", "b1")
        e.set_tool("move")
        e.key("Right")
        e.key("Up", modifiers={"ctrl"})
        self.assertEqual(self.session.undo.count(), 1)
        self.assertEqual(self.session.project.buildings[0].footprint[0], [0.1, 0.01])
        e.click((0, 0))
        e.click((50, 0), {"ctrl"})
        self.assertEqual(len(self.session.project.buildings), 2)
        self.assertNotEqual(e.selection, ("building", "b1"))

    def test_plant_cannot_move_building(self):
        e = self.editor
        e.set_phase("plant")
        e.select("building", "b1")
        e.set_tool("move")
        e.key("Right")
        self.assertEqual(self.session.undo.count(), 0)
        e.click(self.module.centre, {"shift"})
        self.assertEqual(e.selected_module, ("s1", self.module.key))

    def test_window_crossing_and_shift(self):
        e = self.editor
        e.set_phase("plant")
        x, y = self.module.centre
        ring = [(x-.01, y-.01), (x+.01, y-.01), (x+.01, y+.01), (x-.01, y+.01)]
        e.select_area(ring, "window")
        self.assertEqual(e.swept, [])
        e.select_area(ring, "crossing")
        self.assertEqual(e.swept, [("s1", self.module.key)])
        e.select_area(ring, "crossing", {"ctrl"})         # R529: Ctrl takes away (it was Shift)
        self.assertEqual(e.swept, [])

    def test_the_rule_of_the_selection_r529(self):
        # Daniel 07/11/2026 sera: after a window a plain click starts again; one module more or less only with Ctrl or
        # Shift: Shift adds, Ctrl adds or takes away; a plain window starts again, Shift adds, Ctrl takes away
        e = self.editor
        e.set_phase("plant")
        a, b, c = self.result.modules[:3]

        def box(*ms):
            xs = [m.centre[0] for m in ms]
            ys = [m.centre[1] for m in ms]
            return [(min(xs) - .01, min(ys) - .01), (max(xs) + .01, min(ys) - .01), (max(xs) + .01, max(ys) + .01),
                    (min(xs) - .01, max(ys) + .01)]
        e.select_area(box(a), "crossing")
        e.select_area(box(b), "crossing", {"shift"})
        self.assertEqual(e.swept, [("s1", a.key), ("s1", b.key)])
        e.select_area(box(c), "crossing")                    # a plain window starts again
        self.assertEqual(e.swept, [("s1", c.key)])
        e.click(a.centre, {"shift"})
        e.click(a.centre, {"shift"})                         # Shift only adds
        self.assertEqual(e.swept, [("s1", c.key), ("s1", a.key)])
        e.click(c.centre, {"ctrl"})                          # Ctrl takes away what is in
        self.assertEqual(e.swept, [("s1", a.key)])
        e.click(b.centre, {"ctrl"})                          # and adds what is not
        self.assertEqual(e.swept, [("s1", a.key), ("s1", b.key)])
        e.click(c.centre)                                    # a plain click starts again: that module alone
        self.assertEqual(e.swept, [])
        self.assertEqual(e.selected_module, ("s1", c.key))
        e.click(a.centre, {"ctrl"})                          # from one module chosen, Ctrl makes two
        self.assertEqual(e.swept, [("s1", c.key), ("s1", a.key)])
        self.assertTrue("Shift" in e.hint or "Maiusc" in e.hint, e.hint)
        self.assertIn("Ctrl", e.hint)

    def test_delete_module_undo_and_drawing_guard(self):
        self.editor.set_phase("plant")
        e = self.editor
        e.click(self.module.centre)
        e.set_tool("building")
        e.key("Delete")
        self.assertEqual(self.session.undo.count(), 0)
        e.set_tool("select")
        e.key("Delete")
        self.assertIn(self.module.key, self.session.project.subfields[0].removed)
        self.session.undo.undo()
        self.assertEqual(self.session.project.subfields[0].removed, [])

    def test_vertex_invalid_does_not_mutate(self):
        before = self.session.snapshot()
        out = self.editor.apply_command({"type": "vertex", "kind": "building", "oid": "b1",
                                         "index": 0, "point": (45, 15)})
        self.assertEqual(self.session.snapshot(), before)
        self.assertEqual(out[0]["type"], "error")

    def test_manual_string_erase_and_undo(self):
        e = self.editor
        e.set_phase("plant")
        e.start_draft(1, 1)
        for m in self.result.modules[:3]:
            e.click(m.centre)
        e.key("Backspace")
        e.key("Enter")
        self.assertEqual(len(e.runs()[0]["modules"]), 2)
        e.set_tool("erase_string")
        e.click(self.module.centre)
        self.assertEqual(e.runs(), [])
        self.session.undo.undo()
        self.assertEqual(len(e.runs()[0]["modules"]), 2)

    def test_drawing_building_and_canopy(self):
        e = self.editor
        e.apply_command({"type": "polygon", "tool": "building", "ring": [(50, 0), (60, 0), (60, 10), (50, 10)]})
        e.apply_command({"type": "canopy", "point": (80, 0), "spec": {}})
        self.assertEqual(len(self.session.project.buildings), 3)
        self.assertIsNotNone(self.session.project.buildings[-1].canopy)
        self.assertEqual(self.session.undo.count(), 2)

    def test_rotation_steps_and_typed_angle(self):
        e = self.editor
        e.select("building", "b1")
        e.pointer = (21, 10)
        e.set_tool("rotate")
        e.key("C")  # Create the gesture at the starting direction.
        e.key("C")
        for mods, expected in [(set(), 15), ({"ctrl"}, 20), ({"shift"}, 0)]:
            import math
            e.move((20 + math.cos(math.radians(22)), 10 + math.sin(math.radians(22))), mods)
            self.assertEqual(e.preview["degrees"], expected)
            self.assertEqual(len(e.preview["rings"]), 2)
        e.key("", "90")
        before = model.Project.from_json(self.session.snapshot())
        move.rotate(before, "building", "b1", 20, 10, 90)(before)
        e.key("Enter")
        self.assertEqual(self.session.snapshot(), before.to_json())

    def test_invalid_move_rolls_back_whole_project(self):
        before = self.session.snapshot()
        out = self.editor.apply_command({"type": "transform", "kind": "subfield", "oid": "s1",
                                         "mode": "move", "dx": 100, "dy": 0})
        self.assertEqual(out[0]["type"], "error")
        self.assertEqual(self.session.snapshot(), before)
        self.assertEqual(self.session.undo.count(), 0)

    def test_modelling_sweep_delete_children_in_one_step(self):
        self.editor.select_area([(-1, -1), (41, -1), (41, 21), (-1, 21)])
        self.editor.key("Delete")
        self.assertEqual(self.session.project.buildings, [])
        self.assertEqual(self.session.project.subfields, [])
        self.assertEqual(self.session.undo.count(), 1)
        self.session.undo.undo()
        self.assertEqual(len(self.session.project.subfields), 1)

    def test_side_vertex_wrappers_and_undo(self):
        e = self.editor
        e.select("building", "b1")
        e.set_side_length(0, 45)
        self.assertAlmostEqual(self.session.project.buildings[0].footprint[1][0], 45)
        e.move_vertex(2, (45, 22))
        self.assertEqual(self.session.project.buildings[0].footprint[2], [45, 22])
        self.session.undo.undo()
        self.session.undo.undo()
        self.assertEqual(self.session.project.buildings[0].footprint[1], [40, 0])

    def test_string_shift_steals_and_escape_cancels(self):
        self.editor.set_phase("plant")
        e = self.editor
        e.start_draft()
        e.click(self.module.centre)
        e.finish_draft()
        e.start_draft(2, 1)
        e.click(self.module.centre)
        self.assertEqual(e.draft, [])
        e.click(self.module.centre, {"shift"})
        e.finish_draft()
        self.assertEqual(len(e.runs()), 1)
        self.assertEqual(e.runs()[0]["inverter"], 2)
        count = self.session.undo.count()
        e.start_draft()
        e.click(self.result.modules[1].centre)
        e.key("Escape")
        self.assertEqual(self.session.undo.count(), count)
        self.assertIsNone(e.draft)

    def test_inverter_erasers_match_core(self):
        from meridiana.energy import plant
        for erase_strings in (False, True):
            with self.subTest(strings=erase_strings):
                self.session.project.energy = {"inverters": [{"record": {"model": "test", "ac_power_nominal_w": 20000}, "count": 2}],
                                               "strings": {"runs": [
                                                   {"inverter": 1, "mppt": 1, "modules": [f"s1/{self.module.key}"]},
                                                   {"inverter": 2, "mppt": 1, "modules": ["s1/other"]}]}}
                before = self.session.snapshot()
                expected_entries, expected_runs = plant.remove_unit(self.session.project.energy, self.editor.runs(), 1, erase_strings)
                typ = "erase_inverter_strings" if erase_strings else "erase_inverter"
                self.editor.apply_command({"type": typ, "sfid": "s1", "key": self.module.key})
                self.assertEqual(self.editor.runs(), expected_runs)
                self.assertEqual(self.session.project.energy["inverters"], expected_entries)
                self.session.undo.undo()
                self.assertEqual(self.session.snapshot(), before)

    def test_drawing_pitch_ridge_whole_and_row(self):
        e = self.editor
        e.apply_command({"type": "ridge", "points": [(0, 10), (40, 10)], "height": None})
        self.assertEqual(self.session.project.buildings[0].roof.type, "gable")
        e.apply_command({"type": "pitch", "ring": [(0, 0), (40, 0), (40, 10), (0, 10)],
                         "spec": {"tilt": 20, "eave": 5}})
        self.assertEqual(self.session.project.buildings[0].roof.type, "free")
        e.apply_command({"type": "whole", "tool": "subfield", "point": (5, 5)})
        self.assertEqual(len(self.session.project.subfields), 2)
        e.apply_command({"type": "row", "tool": "row", "start": (5, 2), "end": (15, 2)})
        self.assertTrue(self.session.project.subfields[-1].manual)

    def test_delete_string_mode_keeps_geometry(self):
        e = self.editor
        e.set_phase("plant")
        e.start_draft()
        e.click(self.module.centre)
        e.finish_draft()
        e.set_strings_mode(True)
        e.select("building", "b1")
        e.click(self.module.centre)
        e.key("Delete")
        self.assertEqual(e.runs(), [])
        self.assertEqual(len(self.session.project.buildings), 1)

    def test_no_hint_in_results_phase(self):
        self.editor.set_phase("energy")
        self.assertEqual(self.editor.hint, "")

    def test_wiring_jumps_skip_fill_and_number_endpoints(self):
        e = self.editor
        modules = self.result.modules
        keys = [modules[i].key for i in (0, 2)]
        self.session.project.energy["strings"] = {"runs": [{"inverter": 1, "mppt": 1,
                                                           "modules": ["s1/" + k for k in keys]}]}
        e.chosen_string = 0
        scene = e.wiring_scene(.02)
        fills = [o for o in scene["objects"] if o["kind"] == "string_fill"]
        lines = [o for o in scene["objects"] if o["kind"] == "string_jump"]     # a jump: a dashed arc (R496)
        self.assertEqual(len(fills), 2)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0]["dashed"])
        self.assertEqual(lines[0]["points"][0], [modules[0].centre[0], -modules[0].centre[1]])
        self.assertEqual(lines[0]["points"][-1], [modules[2].centre[0], -modules[2].centre[1]])
        self.assertFalse([o for o in scene["objects"] if o["kind"] == "string_line"], "no plain leg over a jump")
        self.assertEqual([x["number"] for x in scene["labels"] if x["kind"] == "number"], [1, 2])
        self.assertEqual(len(scene["dots"]), 2)
        self.assertEqual(e.wiring_scene(1)["dots"], [])

    def test_wiring_draft_erase_highlight_and_missing_modules(self):
        self.editor.set_phase("plant")
        e = self.editor
        e.start_draft()
        e.click(self.module.centre)
        draft = e.wiring_scene(.02)
        self.assertEqual(len([o for o in draft["objects"] if o.get("draft") and o["kind"] == "string_fill"]), 1)
        e.finish_draft()
        e.set_tool("erase_string")
        e.move(self.module.centre)
        self.assertEqual(e.wiring_scene(.02)["highlights"], [("s1", self.module.key)])
        self.session.project.energy["strings"]["runs"][0]["modules"].append("missing/absent")
        scene = e.wiring_scene(.02)
        self.assertEqual([o for o in scene["objects"] if o["kind"] == "string_line"], [])

    def test_wiring_colour_neighbours_and_number_thinning(self):
        from meridiana.quick.backend.plan_wiring import number_indices
        e = self.editor
        self.session.project.energy["strings"] = {"runs": [
            {"inverter": 1, "mppt": 1, "modules": ["s1/" + self.result.modules[i].key]} for i in (0, 1)]}
        scene = e.wiring_scene(.02)
        self.assertNotEqual(*scene["colours"])
        self.assertEqual(number_indices([(i, 0) for i in range(12)], .01), list(range(1, 13)))
        self.assertEqual(number_indices([(i, 0) for i in range(12)], .1), [1, 5, 10, 12])
        self.assertEqual(number_indices([(i, 0) for i in range(12)], 1), [1, 10, 12])

    def test_wiring_names_use_real_state_or_unchecked_default(self):
        from meridiana import theme_colors
        e = self.editor
        self.session.project.energy["strings"] = {"runs": [
            {"inverter": 1, "mppt": 1, "modules": ["s1/"+self.module.key]}]}
        for state, colour in [(None, "warning"), ("ok", "good"), ("fail", "critical")]:
            labels = e.wiring_scene(.02, states={} if state is None else {0: state})["labels"]
            name = next(label for label in labels if label["kind"] == "name")
            self.assertEqual(name["text"], "1.1.1")
            self.assertEqual(name["state"], state or "check")
            self.assertEqual(name["statusColour"], theme_colors.STATUS[colour])


if __name__ == "__main__":
    unittest.main()
