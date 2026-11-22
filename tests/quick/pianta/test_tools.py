"""Drawing journeys in metres, independent of Qt (R269, R274-279, R388, R389)."""
import math
import unittest
from shapely.geometry import Polygon

from meridiana import i18n
from meridiana.app.view.measure_tool import IGNORED, LEAVE, USED, MeasureTool
from meridiana.app.view.plan_probe import PlanProbe
from meridiana.core.model import model
from meridiana.gui.backend.plan_tools import DrawingMachine


def machine(tool="building", **options):
    m = DrawingMachine(metres_per_pixel=0.001)
    m.set_tool(tool, **options)
    return m


class Measuring:
    """The measuring tool with the plan's probe, as the plan drives it (gui/backend/plan_measure.py), without Qt: the
    tool Measure left DrawingMachine for app/view/measure_tool.py (study 46)."""

    def __init__(self, project=None, metres_per_pixel=1 / 12):
        self.tool, self.probe, self.mpp = MeasureTool(), PlanProbe(project), metres_per_pixel

    def at(self, point, mods=frozenset()):
        return self.probe.probe(point, self.mpp, self.tool.wanted(mods))

    def move(self, point, mods=frozenset()):
        self.tool.move(self.at(point, mods), mods)

    def click(self, point, mods=frozenset()):
        self.tool.click(self.at(point, mods), mods)

    def double(self, point, mods=frozenset()):
        """Qt's double click: a click, then the double click on the same point."""
        self.click(point, mods)
        self.tool.double_click(None, mods)

    def points(self):
        return [p.point[:2] for p in self.tool.points]

    def lengths(self, index=-1):
        return [s.plan for s in self.tool.measures[index].spans()]

    def guides(self):
        return self.tool.display("plan")["guides"]


def write(m, text):
    for ch in text:
        m.key(ch, text=ch)


class DrawingTest(unittest.TestCase):
    def test_polygon_closes_by_first_point_and_restarts(self):
        for tool in ("building", "subfield", "exclusion"):
            with self.subTest(tool=tool):
                m = machine(tool)
                for p in [(0, 0), (10, 0), (10, 5)]:
                    self.assertEqual(m.click(p, {"ctrl"}), [])
                out = m.click((0, 0))
                expected = {"type": "polygon", "tool": tool, "ring": [(0., 0.), (10., 0.), (10., 5.)]}
                if tool == "subfield":
                    expected["spec"] = {"fill": "modules"}          # R445: a sub-field drawn is its modules
                self.assertEqual(out, [expected])
                self.assertEqual(m.points, [])
                self.assertEqual(m.tool, tool)

    def test_length_angle_decimal_comma_and_backspace(self):
        m = machine()
        m.click((0, 0))
        write(m, "10;90")
        m.key("Enter")
        self.assertAlmostEqual(m.points[-1][0], 10)
        self.assertAlmostEqual(m.points[-1][1], 0)
        write(m, "2,5;90")
        m.key("Enter")
        self.assertAlmostEqual(m.points[-1][0], 10)
        self.assertAlmostEqual(m.points[-1][1], 2.5)
        m.key("Backspace")
        self.assertEqual(len(m.points), 2)

    def test_escape_clears_number_then_draft_then_exits(self):
        m = machine()
        m.click((0, 0))
        write(m, "20")
        m.key("Escape")
        self.assertEqual(m.typed, "")
        self.assertEqual(len(m.points), 1)
        m.key("Escape")
        self.assertEqual(m.points, [])
        self.assertEqual(m.tool, "building")
        self.assertEqual(m.key("Escape"), [{"type": "tool", "tool": "select"}])

    def test_rectangle_typed_depth_respects_pointer_side(self):
        m = machine()
        m.key("R")
        m.click((0, 0), {"ctrl"}); m.click((10, 0), {"ctrl"}); m.move((7, -3), {"ctrl"})
        write(m, "4")
        out = m.key("Enter")
        self.assertEqual(out[0]["ring"], [(0, 0), (10, 0), (10, -4), (0, -4)])

    def test_invalid_number_does_not_close_existing_polygon(self):
        m = machine()
        for p in [(0, 0), (10, 0), (10, 5)]:
            m.click(p)
        write(m, "1;2;3")
        self.assertEqual(m.key("Enter"), [])
        self.assertEqual(len(m.points), 3)
        self.assertTrue(m.error)

    def test_row_and_east_west_numeric_end_then_restart(self):
        for tool in ("row", "east_west"):
            m = machine(tool)
            m.click((2, 3)); m.move((5, 7)); write(m, "10")
            out = m.key("Enter")[0]
            self.assertEqual(out, {"type": "row", "tool": tool, "start": (2., 3.), "end": (8., 11.)})
            self.assertEqual(m.points, [])

    def test_measure_persists_until_next_click(self):
        """Study 46, choice 3: a measure made stays (in the session's list) and the next click begins another one."""
        m = Measuring(metres_per_pixel=0.001)
        m.click((0, 0)); m.double((3, 4)); m.move((80, 90))
        self.assertEqual(len(m.tool.measures), 1)
        self.assertAlmostEqual(m.lengths()[0], 5)
        m.click((8, 9))
        self.assertEqual(m.points(), [(8., 9.)])
        self.assertEqual(len(m.tool.measures), 1)           # the one made stays, the new one is in hand
        with self.assertRaises(ValueError):             # the tool left the drawing machine (study 46)
            machine("measure")

    def test_second_measure_is_free_of_the_first_r563(self):
        """R563 (Daniel 13/11/2026: «la seconda riparte dalla partenza della prima»): after a measure the guides still
        left from its first point, followed the pointer and pulled the next click on to them."""
        m = Measuring()
        m.move((25, 5)); m.click((25, 5)); m.move((32, 5)); m.double((32, 5))
        self.assertEqual((m.tool.state, m.tool.points), ("idle", []))
        self.assertEqual([p.point[:2] for p in m.tool.measures[0].points], [(25., 5.), (32., 5.)])
        self.assertAlmostEqual(m.lengths()[0], 7)
        self.assertEqual(m.guides(), [])                    # the guide that led to the second point ends with it
        # 0.3 m east of the line going north from the first point, within the snaps' reach (10 px = 0.83 m)
        m.move((25.3, 12))
        pointer = m.tool.display("plan")["pointer"]
        self.assertEqual((pointer["at"][:2], m.guides(), pointer["kind"]), ([25.3, 12.], [], "free"))
        self.assertEqual(len(m.tool.display("plan")["done"]), 1)      # the measure made stays
        m.click((25.3, 12))
        self.assertEqual((m.tool.state, m.points(), m.guides()), ("measuring", [(25.3, 12.)], []))
        m.move((25.3, 2))               # the new measure has its own guides, from its own first point
        self.assertEqual({tuple(g["a"][:2]) for g in m.guides()}, {(25.3, 12.)})
        m.double((25.3, 2))
        self.assertEqual([p.point[:2] for p in m.tool.measures[-1].points], [(25.3, 12.), (25.3, 2.)])
        self.assertAlmostEqual(m.lengths()[0], 10)

    def test_measure_keys_r563(self):
        m = Measuring()
        ctrl, shift = frozenset({"ctrl"}), frozenset({"shift"})
        m.click((25, 5), ctrl); m.double((32, 5), ctrl)
        # Shift held after a measure locked a direction that the next measure then followed from its first point
        m.move((30, 9), shift)
        self.assertEqual(m.tool.key("Shift", modifiers=shift), IGNORED)      # nothing in hand: nothing to hold
        m.click((30, 9), shift | ctrl); m.move((33, 16), shift | ctrl)
        self.assertEqual(m.points(), [(30., 9.)])
        self.assertEqual(m.tool.target.point[:2], (33., 16.))
        m.click((33, 16), ctrl)
        self.assertEqual(m.tool.key("Backspace"), USED)     # one step back: the first point again, the second to be given
        self.assertEqual((m.tool.state, m.points()), ("measuring", [(30., 9.)]))
        m.double((33, 13), ctrl)
        self.assertAlmostEqual(m.lengths()[0], 5)
        m.click((40, 9), ctrl)
        self.assertEqual(m.tool.key("Escape"), USED)        # the measure in hand goes, the tool stays
        self.assertEqual((m.tool.state, m.tool.points, len(m.tool.measures)), ("idle", [], 2))
        self.assertEqual(m.tool.key("Escape"), LEAVE)       # then the tool goes (the plan gives Select back)

    def test_prop_and_linear_prop_return_to_selection(self):
        m = machine("prop", kind="tree")
        out = m.click((3, 4))
        self.assertEqual(out[0], {"type": "prop", "kind": "tree", "point": (3., 4.)})
        self.assertEqual(m.tool, "select")
        m.set_tool("prop_line", kind="hedge")
        m.click((1, 1)); m.click((4, 5))
        out = m.key("Enter")
        self.assertEqual(out[0], {"type": "prop_line", "kind": "hedge", "points": [(1., 1.), (4., 5.)]})
        self.assertEqual(m.tool, "select")

    def test_whole_pitch_double_click(self):
        m = machine("subfield")
        m.click((3, 4))
        self.assertEqual(m.double_click((3, 4)), [{"type": "whole", "tool": "subfield", "point": (3., 4.),
                                                   "spec": {"fill": "modules"}}])     # R445
        self.assertFalse(m.points)

    def test_canopy_placement_preserves_spec(self):
        m = machine("canopy", spec={"bays": 3, "tilt": 10})
        self.assertEqual(m.click((10, 20))[0], {"type": "canopy", "point": (10., 20.),
                                              "spec": {"bays": 3, "tilt": 10}})

    def test_snaps_ctrl_altgr_and_orthogonal_direction(self):
        m = machine()
        m.set_references([], [(2, 2)])
        m.move((2.005, 2.005))
        self.assertEqual(m.pointer, (2, 2))
        m.move((2.005, 2.005), {"ctrl"})
        self.assertEqual(m.pointer, (2.005, 2.005))
        m.move((2.005, 2.005), {"ctrl", "alt"})
        self.assertEqual(m.pointer, (2, 2))
        m.click((0, 0)); m.key("F8"); m.move((5, 2))
        self.assertEqual(m.pointer, (5, 0))
        self.assertTrue(m.preview["guides"])

    def test_shift_locks_direction_until_released(self):
        m = machine()
        m.click((0, 0)); m.move((3, 4), {"ctrl"}); m.key("Shift")
        m.move((10, 0), {"shift", "ctrl"})
        self.assertAlmostEqual(m.pointer[1] / m.pointer[0], 4 / 3)
        m.move((10, 0), {"ctrl"})
        self.assertEqual(m.pointer, (10, 0))

    def test_nonfinite_click_cannot_reuse_previous_pointer(self):
        m = machine()
        m.move((3, 4))
        self.assertEqual(m.click((float("nan"), 1)), [])
        self.assertFalse(m.points)

    def test_rectangle_near_baseline_uses_unsnapped_depth(self):
        m = DrawingMachine(metres_per_pixel=.1)
        m.set_tool("building"); m.key("R")
        m.click((0, 0)); m.click((10, 0))
        m.move((10, .2))
        self.assertAlmostEqual(m.pointer[1], .2)
        out = m.click((10, .2))
        self.assertAlmostEqual(Polygon(out[0]["ring"]).area, 2)

    def test_zero_and_negative_length_do_not_add_vertices(self):
        for value in ("0", "-3", "--2", "1..2"):
            m = machine(); m.click((0, 0)); write(m, value)
            self.assertEqual(m.key("Enter"), [])
            self.assertEqual(len(m.points), 1)
            self.assertTrue(m.error)

    def test_linear_path_has_no_closing_side_and_no_polygon_preview(self):
        m = machine("prop_line", kind="walkway")
        m.click((0, 0)); m.click((4, 0)); m.move((4, 3))
        self.assertEqual(m.preview["side_lengths"], [])
        out = m.double_click((4, 3))
        self.assertEqual(len(out[0]["points"]), 2)

    def test_reference_midpoint_and_snap_toggle(self):
        m = machine()
        m.set_references([((0, 0), (10, 0))])
        m.move((5.001, .001))
        self.assertEqual(m.preview["snap"], "midpoint")
        m.key("F3")
        self.assertEqual(m.pointer, (5.001, .001))
        m.key("F3")
        self.assertEqual(m.pointer, (5., 0.))

    def test_crossed_polygon_is_refused_with_draft_retained(self):
        m = machine()
        for p in [(0, 0), (10, 10), (0, 10), (10, 0)]:
            m.click(p, {"ctrl"})
        self.assertEqual(m.key("Enter"), [])
        self.assertEqual(len(m.points), 4)
        self.assertTrue(m.error)

    def test_row_preview_does_not_compute_missing_automatic_layout(self):
        from unittest.mock import patch
        project = model.Project()
        project.subfields.append(model.SubField(id="s1", name="Pending", filled=True,
                                               ring=[[0, 0], [20, 0], [20, 20], [0, 20]]))
        m = DrawingMachine(project)
        m.set_tool("row")
        m.click((3, 3)); m.move((13, 3))
        with patch.object(project, "fill", side_effect=AssertionError("A pointer must not compute a whole layout")):
            self.assertTrue(m.preview["row"]["pending"])


class RoofTest(unittest.TestCase):
    def setUp(self):
        self.project = model.Project()
        self.project.buildings.append(model.Building(id="b1", name="Shed", height=6,
            footprint=[[0, 0], [20, 0], [20, 10], [0, 10]]))

    def test_pitch_swapping_keeps_next_step_hint_and_typed_slope(self):
        m = DrawingMachine(self.project, metres_per_pixel=.001)
        m.set_tool("pitch"); m.click((0, 0)); m.key("Tab"); m.click((10, 0)); m.move((10, 5))
        self.assertEqual(m.state, "depth")
        self.assertIn("Tab", m.hint)
        m.key("Down"); write(m, "20%"); m.key("Enter")
        self.assertAlmostEqual(m.preview["pitch"]["tilt"], math.degrees(math.atan(.2)))
        out = m.click((10, 5))[0]
        self.assertEqual(out["type"], "pitch")
        self.assertTrue(out["spec"]["swapped"])

    def test_ridge_requires_building_and_auto_finishes_four_sides(self):
        m = DrawingMachine(self.project, metres_per_pixel=.001)
        m.set_tool("ridge")
        self.assertEqual(m.click((-10, -10)), [])
        self.assertFalse(m.points)
        m.click((0, 5)); write(m, "8"); m.key("Enter")
        out = m.click((20, 5))[0]
        self.assertEqual(out, {"type": "ridge", "points": [(0., 5.), (20., 5.)], "height": 8.})

    def test_ridge_height_below_eave_is_rejected(self):
        m = DrawingMachine(self.project)
        m.set_tool("ridge"); m.click((0, 5)); write(m, "4")
        self.assertEqual(m.key("Enter"), [])
        self.assertIsNone(m.ridge_height)
        self.assertTrue(m.error)

    def test_pitch_corner_mode_escape_can_leave_tool(self):
        m = machine("pitch")
        m.key("R"); m.click((0, 0))
        m.key("Escape")
        self.assertEqual(m.key("Escape"), [{"type": "tool", "tool": "select"}])

    def test_pitch_eave_then_ridge_then_slope_last_value_wins(self):
        m = DrawingMachine(self.project, metres_per_pixel=.001)
        m.set_tool("pitch"); m.click((0, 0)); m.click((10, 0)); m.move((10, 5))
        m.key("Up"); write(m, "7"); m.key("Enter")
        self.assertEqual(m.preview["pitch"]["eave"], 7)
        m.key("Up"); write(m, "9"); m.key("Enter")
        self.assertEqual(m.preview["pitch"]["ridge"], 9)
        m.key("Up"); write(m, "10"); m.key("Enter")
        self.assertEqual(m.preview["pitch"]["tilt"], 10)
        self.assertIsNone(m.preview["pitch"]["spec"]["ridge"])

    def test_nonrectangular_ridge_accepts_more_than_two_points(self):
        self.project.buildings[0].footprint = [[0, 0], [20, 0], [20, 10], [10, 10], [10, 20], [0, 20]]
        m = DrawingMachine(self.project, metres_per_pixel=.001)
        m.set_tool("ridge"); m.click((0, 5)); m.click((5, 5)); m.click((5, 15))
        self.assertEqual(len(m.points), 3)
        self.assertEqual(len(m.key("Enter")[0]["points"]), 3)


class HintTest(unittest.TestCase):
    def test_real_catalogue_translates_every_drawing_message(self):
        import ast
        from pathlib import Path
        from meridiana.gui.backend import plan_tools, plan_locale
        main = i18n.translation_for("it")              # one catalogue since r21-f7: the plan's short forms in "plan"
        plan = {k.split("\x04", 1)[1] for k in main._catalog
                if isinstance(k, str) and k.startswith(plan_locale.CONTEXT + "\x04")}
        folder = Path(plan_tools.__file__).parent
        for filename in ("plan_tools.py", "plan_edit.py", "plan.py", "plan_collect.py", "plan_sources.py"):
            tree = ast.parse((folder / filename).read_text(encoding="utf-8"))
            messages = [n.args[0].value for n in ast.walk(tree) if isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Name) and n.func.id == "_"
                        and n.args and isinstance(n.args[0], ast.Constant)]
            for message in messages:
                with self.subTest(file=filename, message=message):
                    # Unit-only messages legitimately have identical Italian text.
                    self.assertTrue(message in plan or message in main._catalog)

    def test_italian_hint_tracks_escape_and_placed_object(self):
        previous = i18n.language()
        i18n.setup("it")
        try:
            m = machine()
            self.assertIn("Esc: esci", m.hint)
            m.click((0, 0)); write(m, "3")
            self.assertIn("Esc: svuota", m.hint)
            m.key("Escape")
            self.assertIn("Esc: annulla", m.hint)
            m.set_tool("prop", kind="tree"); m.click((3, 4))
            self.assertIn("seleziona", m.hint)
            self.assertNotIn("posizione", m.hint)
        finally:
            i18n.setup(previous)


if __name__ == "__main__":
    unittest.main()
