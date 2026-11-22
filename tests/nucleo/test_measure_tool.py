"""The measuring tool without its views (study 46, state r34-righello section 2): gestures and states, the arrows'
constraints, Shift, Ctrl, the pitch's plane, the number typed, the snap of the menu, the polar guides, the height
mode, the «≈», the pills of each view, the list of the measurements done and the text copied."""

import json
import math
import unittest

import _setup  # noqa: F401

from meridiana import i18n
from meridiana.app.view.measure_tool import IGNORED, LEAVE, SNAPS, USED, MeasureTool, Probe

S30, C30, T30 = (f(math.radians(30)) for f in (math.sin, math.cos, math.tan))
PITCH = (0.0, -S30, C30)                     # 30° pitch rising to the North from an eave along East at 3 m
EAVE = ((0.0, 0.0, 3.0), (10.0, 0.0, 3.0))
_before = None


def setUpModule():
    global _before
    _before = i18n._translation
    i18n.setup("en")


def tearDownModule():
    i18n._translation = _before


def P(e, n, z=0.0, **kw):
    """A probe of the plan."""
    return Probe((float(e), float(n), float(z)), **kw)


def R(point, kind="face", exact=False, eye=(0.0, -20.0, 30.0), **kw):
    """A probe of the 3D view: its point, with the pointer's ray from `eye` through it."""
    direction = tuple(point[i] - eye[i] for i in range(3))
    return Probe(tuple(map(float, point)), kind=kind, exact=exact, ray=(eye, direction), **kw)


def on_pitch(e, n):
    return (e, n, 3.0 + n * T30)


def near(test, p, q, places=6):
    for a, b in zip(p, q, strict=True):
        test.assertAlmostEqual(a, b, places=places)


def plain(value):
    """Only what a QVariant takes from Python as data: dicts of strings, lists, numbers, strings, bools, None."""
    if isinstance(value, dict):
        return all(isinstance(k, str) and plain(v) for k, v in value.items())
    if isinstance(value, list):
        return all(plain(v) for v in value)
    return value is None or isinstance(value, (bool, int, float, str))


class Gestures(unittest.TestCase):
    def setUp(self):
        self.t = MeasureTool()

    def test_a_simple_measure_is_a_click_and_a_double_click(self):
        t = self.t
        t.click(P(0, 0))
        t.click(P(4, 3))
        t.click(P(4, 3))                     # Qt's double click: a click on the same point, then the double click
        t.double_click(P(4, 3))
        self.assertEqual(t.state, "idle")
        self.assertEqual(len(t.measures), 1)
        self.assertEqual([p.point for p in t.measures[0].points], [(0, 0, 0), (4, 3, 0)])
        self.assertEqual(t.display("plan")["done"][0]["segments"][0]["pill"]["text"], "5.00 m")

    def test_a_path_of_several_segments_ends_with_enter(self):
        t = self.t
        for p in ((0, 0), (4, 0), (4, 3), (8, 3)):
            t.click(P(*p))
        self.assertEqual(t.state, "measuring")
        self.assertEqual(t.key("Enter"), USED)
        m = t.measures[0]
        self.assertEqual((len(m.points), m.closed), (4, False))
        total = t.display("plan")["done"][0]["total"]
        self.assertEqual(total["text"], "Total 11.00 m")
        self.assertEqual(total["below"], "3 segments")

    def test_a_click_on_the_first_point_closes_the_ring(self):
        t = self.t
        for p in ((0, 0), (4, 0), (4, 3), (0, 3), (0, 0)):
            t.click(P(*p))
        m = t.measures[0]
        self.assertTrue(m.closed)
        self.assertEqual(len(m.points), 4)
        total = t.display("plan")["done"][0]["total"]
        self.assertEqual(total["text"], "Total 14.00 m")
        self.assertIn("area 12.00 m²", total["below"])
        self.assertEqual(len(t.display("plan")["done"][0]["segments"]), 4)

    def test_the_first_point_does_not_close_before_three(self):
        t = self.t
        t.click(P(0, 0))
        t.click(P(4, 0))
        t.click(P(0, 0))
        self.assertEqual(len(t.points), 3)
        self.assertFalse(t.measures)

    def test_enter_with_one_point_keeps_nothing(self):
        t = self.t
        t.click(P(1, 1))
        self.assertEqual(t.key("Return"), USED)
        self.assertEqual((t.state, t.measures), ("idle", []))
        self.assertEqual(t.key("Enter"), IGNORED)

    def test_backspace_takes_the_last_point_back(self):
        t = self.t
        for p in ((0, 0), (4, 0), (4, 3)):
            t.click(P(*p))
        self.assertEqual(t.key("Backspace"), USED)
        self.assertEqual([p.point for p in t.points], [(0, 0, 0), (4, 0, 0)])
        t.key("Backspace")
        t.key("Backspace")
        self.assertEqual(t.state, "idle")
        self.assertEqual(t.key("Backspace"), IGNORED)

    def test_esc_has_two_levels(self):
        t = self.t
        t.click(P(0, 0))
        t.click(P(5, 0))
        t.key("Enter")
        t.click(P(1, 1))
        t.click(P(2, 2))
        self.assertEqual(t.key("Escape"), USED)          # the measurement in hand goes
        self.assertEqual((t.state, len(t.measures)), ("idle", 1))
        self.assertEqual(t.key("Escape"), LEAVE)         # then the tool: the caller goes back to Select
        self.assertEqual(len(t.measures), 1)

    def test_another_tool_keeps_a_measure_of_two_points_and_drops_one_point(self):
        t = self.t
        t.click(P(0, 0))
        t.click(P(3, 0))
        t.leave()
        self.assertEqual(len(t.measures), 1)
        t.click(P(9, 9))
        t.leave()
        self.assertEqual((len(t.measures), t.state), (1, "idle"))

    def test_a_measure_done_does_not_guide_the_next(self):
        t = self.t
        t.click(P(0, 0))
        t.click(P(7, 0))
        t.double_click(P(7, 0))
        self.assertEqual(t.wanted().chain, ())
        t.move(P(0.3, 12, guides=({"a": (0, 0), "b": (0, 12), "kind": "polar", "label": "0°"},)))
        near(self, t.target.point, (0.3, 12, 0))        # where the pointer is, nothing pulls it
        shown = t.display("plan")
        self.assertIsNone(shown["current"])
        self.assertEqual(shown["guides"], [])
        t.click(P(0.3, 12))
        self.assertEqual([p.point for p in t.points], [(0.3, 12, 0)])
        self.assertEqual(len(t.measures), 1)

    def test_begun_in_the_plan_and_ended_in_the_3d_view(self):
        t = self.t
        t.click(P(0, 0, 0))
        t.click(R((3, 4, 12), kind="vertex", exact=True))
        t.key("Enter")
        m = t.measures[0]
        self.assertEqual([p.point for p in m.points], [(0, 0, 0), (3, 4, 12)])
        self.assertEqual(t.display("3d")["done"][0]["segments"][0]["pill"]["text"], "13.00 m")
        self.assertEqual(t.display("plan")["done"][0]["segments"][0]["pill"]["text"], "5.00 m")

    def test_a_probe_that_is_not_finite_is_ignored(self):
        t = self.t
        t.click(P(float("nan"), 0))
        t.move(P(0, float("inf")))
        self.assertEqual((t.state, t.target), ("idle", None))


class Arrows(unittest.TestCase):
    def setUp(self):
        self.t = MeasureTool()

    def test_the_arrows_are_the_tools_only_with_a_point_placed(self):
        t = self.t
        for key in ("Right", "Left", "Up", "Down"):
            self.assertEqual(t.key(key), IGNORED, key)  # at rest they stay the view's
        t.click(P(1, 1))
        self.assertEqual(t.key("Right"), USED)

    def test_right_east_left_north_up_vertical_and_again_free(self):
        t = self.t
        t.click(P(1, 1, 2))
        t.key("Right")
        t.move(P(6, 4, 2))
        near(self, t.target.point, (6, 1, 2))
        t.key("Left")
        t.move(P(6, 4, 2))
        near(self, t.target.point, (1, 4, 2))
        t.key("Left")                                    # the same arrow again: free
        t.move(P(6, 4, 2))
        near(self, t.target.point, (6, 4, 2))
        t.key("Up")
        t.move(P(6, 4, 9.5))                             # in the plan the vertical keeps the surface's height
        near(self, t.target.point, (1, 1, 9.5))
        self.assertEqual(t.display("plan")["constraint"]["text"], "Vertical")

    def test_an_arrow_on_the_ray_of_the_3d_view(self):
        t = self.t
        t.click(P(0, 0, 0))
        t.key("Up")
        # the pointer's ray passes over the vertical through the first point, at 4 m
        t.move(Probe((0.0, 10.0, 3.0), ray=((0.0, -10.0, 5.0), (0.0, 10.0, -1.0)), exact=False))
        near(self, t.target.point, (0, 0, 4))
        self.assertTrue(t.target.exact)

    def test_a_snapped_vertex_in_3d_goes_square_on_the_axis(self):
        t = self.t
        t.click(P(0, 0, 0))
        t.key("Up")
        t.move(R((5, 3, 7.25), kind="vertex", exact=True))
        near(self, t.target.point, (0, 0, 7.25))

    def test_down_perpendicular_then_parallel_then_free(self):
        t = self.t
        t.click(P(2, 0, 3, kind="edge", edge=EAVE))
        self.assertEqual(t.key("Down"), USED)
        self.assertEqual(t.constraint, "perpendicular")
        t.move(P(5, 4, 3))
        near(self, t.target.point, (2, 4, 3))
        self.assertEqual(t.display("plan")["edge"], {"a": [0, 0, 3], "b": [10, 0, 3]})
        t.key("Down")
        t.move(P(5, 4, 3))
        near(self, t.target.point, (5, 0, 3))
        self.assertEqual(t.display("plan")["constraint"]["text"], "Parallel")
        t.key("Down")
        self.assertIsNone(t.constraint)
        self.assertIsNone(t.display("plan")["edge"])

    def test_down_refers_to_the_last_edge_passed_over(self):
        t = self.t
        t.click(P(0, 0))
        t.move(P(5, 5, kind="edge", edge=((5, 0, 0), (5, 10, 0))))
        t.move(P(8, 2))
        t.key("Down")
        t.move(P(8, 2))
        near(self, t.target.point, (8, 0, 0))            # square to the North-South edge: along East

    def test_down_without_a_reference_edge_says_so(self):
        t = self.t
        t.click(P(0, 0))
        self.assertEqual(t.key("Down"), USED)
        self.assertIsNone(t.constraint)
        self.assertIn("no reference edge", t.hint)

    def test_a_constraint_is_for_one_point(self):
        t = self.t
        t.click(P(0, 0))
        t.key("Right")
        t.click(P(5, 2))
        self.assertEqual(t.points[-1].point, (5, 0, 0))
        self.assertIsNone(t.constraint)
        t.move(P(6, 4))
        near(self, t.target.point, (6, 4, 0))

    def test_shift_holds_the_direction(self):
        t = self.t
        t.click(P(0, 0))
        t.move(P(4, 4))
        t.move(P(10, 2), {"shift"})
        near(self, t.target.point, (6, 6, 0))
        self.assertEqual(t.display("plan")["constraint"]["text"], "Direction held")
        t.move(P(10, 2))
        near(self, t.target.point, (10, 2, 0))

    def test_shift_let_go_frees_the_direction_without_a_step(self):
        t = self.t
        t.click(P(0, 0))
        t.move(P(4, 4))
        t.move(P(10, 2), {"shift"})
        self.assertTrue(t.release("Shift"))
        self.assertIsNone(t.held)
        near(self, t.target.point, (10, 2, 0))                 # the pointer where it was, free
        self.assertFalse(t.release("Shift"))                   # nothing held: nothing to do
        self.assertFalse(t.release("Control"))

    def test_ctrl_switches_snaps_and_the_plane_off(self):
        t = self.t
        self.assertEqual(t.wanted({"ctrl"}).snaps, frozenset())
        self.assertEqual(t.wanted({"ctrl", "alt"}).snaps, SNAPS)     # AltGr on an Italian keyboard is not Ctrl
        t.click(P(*on_pitch(2, 0), kind="edge", edge=EAVE, normal=PITCH))
        hit = on_pitch(3, 2)
        rough = R((hit[0], hit[1], hit[2] + 0.01), normal=PITCH)
        t.move(rough, {"ctrl"})
        near(self, t.target.point, rough.point)
        self.assertFalse(t.target.exact)
        self.assertFalse(t.wanted({"ctrl"}).polar)


class Pitch(unittest.TestCase):
    def setUp(self):
        self.t = MeasureTool()
        self.t.click(P(*on_pitch(2, 0), kind="edge", edge=EAVE, normal=PITCH))

    def test_on_the_same_pitch_the_point_keeps_to_its_plane(self):
        t = self.t
        hit = on_pitch(3, 2)
        t.move(R((hit[0], hit[1], hit[2] + 0.01), normal=PITCH))        # the 3D view's hit is float32
        p = t.target.point
        self.assertAlmostEqual(p[2], 3.0 + p[1] * T30, places=9)
        self.assertTrue(t.target.exact)
        self.assertEqual(t.display("3d")["constraint"]["text"], "On the pitch plane")

    def test_another_face_has_no_plane(self):
        t = self.t
        t.move(R((3, 2, 9), normal=(0, 0, 1)))
        self.assertEqual(t.target.point, (3, 2, 9))
        self.assertIsNone(t.display("3d")["constraint"])

    def test_perpendicular_to_the_eave_in_the_pitch(self):
        t = self.t
        t.key("Down")
        hit = on_pitch(4.5, 2)
        t.move(R(hit, normal=PITCH))
        p = t.target.point
        self.assertAlmostEqual(p[0], 2.0, places=6)                 # straight up the slope from the eave
        self.assertAlmostEqual(p[2], 3.0 + p[1] * T30, places=6)
        self.assertEqual(t.display("3d")["constraint"]["text"], "Perpendicular · on the pitch plane")
        t.key("4", "4")
        t.key("Enter")                                               # 4 m along the slope, in the 3D view
        near(self, t.points[-1].point, (2.0, 4 * C30, 3.0 + 4 * S30))


class Typed(unittest.TestCase):
    def setUp(self):
        self.t = MeasureTool()

    def test_digits_only_with_a_point(self):
        t = self.t
        self.assertEqual(t.key("2", "2"), IGNORED)
        t.click(P(0, 0))
        self.assertEqual(t.key("2", "2"), USED)
        self.assertEqual(t.key("Comma", ","), USED)
        self.assertEqual(t.state, "typing")
        self.assertEqual(t.display("plan")["typed"]["text"], "length: 2,_")
        self.assertEqual(t.key("Backspace"), USED)
        self.assertEqual(t.typed, "2")
        self.assertEqual(t.key("Escape"), USED)
        self.assertEqual((t.typed, t.state), ("", "measuring"))

    def test_a_length_along_the_direction_shown_is_a_click(self):
        t = self.t
        t.click(P(0, 0))
        t.move(P(3, 4))
        for c in "2,5":
            t.key(c, c)
        t.key("Enter")
        self.assertEqual(len(t.points), 2)
        near(self, t.points[-1].point, (1.5, 2.0, 0.0))

    def test_a_length_along_the_constraint(self):
        t = self.t
        t.click(P(1, 1))
        t.key("Right")
        t.move(P(-5, 3))                                  # towards West: the length goes West
        t.key("3", "3")
        t.key("Return")
        near(self, t.points[-1].point, (-2, 1, 0))

    def test_in_the_plan_the_length_is_in_plan_in_3d_the_true_one(self):
        t = self.t
        t.click(P(*on_pitch(2, 0), normal=PITCH))
        t.move(P(*on_pitch(2, 3), normal=PITCH))
        t.key("6", "6")
        t.key("Enter")
        self.assertAlmostEqual(t.points[-1].point[1], 6.0)          # 6 m in plan, as the plan's number
        u = MeasureTool()
        u.click(P(*on_pitch(2, 0), normal=PITCH))
        u.move(R(on_pitch(2, 3), normal=PITCH))
        u.key("6", "6")
        u.key("Enter")
        self.assertAlmostEqual(math.dist(u.points[0].point, u.points[1].point), 6.0)

    def test_a_wrong_length_says_so_and_places_nothing(self):
        t = self.t
        t.click(P(0, 0))
        t.move(P(3, 0))
        t.key("0", "0")
        t.key("Enter")
        self.assertEqual(len(t.points), 1)
        self.assertIn("greater than zero", t.hint)

    def test_a_click_while_typing_applies_the_number(self):
        t = self.t
        t.click(P(0, 0))
        t.move(P(0, 9))
        t.key("2", "2")
        t.click(P(7, 7))
        near(self, t.points[-1].point, (0, 2, 0))


class Snaps(unittest.TestCase):
    def setUp(self):
        self.t = MeasureTool()

    def test_the_menu_snap_holds_for_one_point(self):
        t = self.t
        self.assertEqual(t.wanted().snaps, SNAPS)
        t.set_snap("midpoint")
        self.assertEqual(t.wanted().snaps, {"midpoint"})
        self.assertEqual(t.display("plan")["snap"], "midpoint")
        t.move(P(1, 1, kind="midpoint"))
        self.assertEqual(t.display("plan")["request"]["text"], "Midpoint")
        t.click(P(1, 1, kind="midpoint"))
        self.assertEqual(t.wanted().snaps, SNAPS)
        t.set_snap("none")
        self.assertEqual(t.wanted().snaps, frozenset())
        t.click(P(4, 4))
        self.assertEqual(t.wanted().snaps, SNAPS)
        with self.assertRaises(ValueError):
            t.set_snap("centre")

    def test_the_menus_entries_are_every_snap_of_the_menu_with_none_apart(self):
        from meridiana.app.view import measure_text
        from meridiana.app.view.measure_tool import MENU
        entries = measure_text.snap_menu()
        kinds = [e["kind"] for e in entries]
        self.assertEqual(kinds, ["vertex", "midpoint", "edge", "intersection", "perpendicular", "", "none"])
        self.assertEqual(set(kinds) - {""}, MENU)                    # each one the tool takes, no other
        self.assertTrue(entries[5]["separator"])
        for kind in kinds[:5] + ["none"]:
            self.t.set_snap(kind)                                  # none raises
        self.assertNotIn("Shift+right-click", measure_text.hint("distance", 1, typed=True))   # typing: Enter, Esc

    def test_perpendicular_is_the_foot_from_the_previous_point(self):
        t = self.t
        t.click(P(4, 5))
        t.set_snap("perpendicular")
        self.assertEqual(t.wanted().snaps, {"perpendicular"})
        t.move(P(7, 0.1, kind="edge", edge=((0, 0, 0), (10, 0, 0))))
        near(self, t.target.point, (4, 0, 0))
        self.assertEqual(t.target.kind, "perpendicular")
        self.assertIsNotNone(t.display("plan")["edge"])
        t.click(P(7, 0.1, kind="edge", edge=((0, 0, 0), (10, 0, 0))))
        self.assertEqual(t.points[-1].point, (4, 0, 0))
        self.assertEqual(t.wanted().snaps, SNAPS)

    def test_polar_guides_follow_the_setting_given_and_f8_is_not_the_tools(self):
        """The 15° guides are the plan's Ortho (Daniel, 14/11/2026): the tool is told (set_polar), F8 is not its key."""
        t = self.t
        self.assertTrue(t.polar)
        self.assertFalse(t.wanted().polar)                # nothing to start from
        t.click(P(0, 0))
        self.assertTrue(t.wanted().polar)
        self.assertEqual(t.wanted().chain, ((0, 0, 0),))
        self.assertEqual(t.key("F8"), IGNORED)            # the window's Ortho, not the tool's
        self.assertTrue(t.wanted().polar)
        t.set_polar(False)
        self.assertFalse(t.wanted().polar)
        t.set_polar(True)
        self.assertTrue(t.wanted().polar)
        t.key("Right")
        self.assertFalse(t.wanted().polar)               # an axis is on: no polar pull
        t.leave()
        self.assertTrue(t.polar)                          # one state for the session and both views

    def test_the_plans_guides_are_drawn_in_the_plan_only(self):
        t = self.t
        t.click(P(0, 0, 2))
        t.move(P(5, 5, 2, guides=({"a": (0, 0), "b": (5, 5), "kind": "polar", "label": "45°"},)))
        self.assertEqual(t.display("plan")["guides"], [{"a": [0, 0, 2], "b": [5, 5, 2], "kind": "polar", "label": "45°"}])
        self.assertEqual(t.display("3d")["guides"], [])


class WordsOnTheDrawingAndInTheHint(unittest.TestCase):
    """R609 (Daniel 14/11/2026): the drawing writes only each span's number, the path's total after its last number;
    the rest (along the slope, height difference, slope, direction, total) is in the hint bar while measuring and when
    a measure is chosen."""

    def test_the_span_to_the_pointer_gives_its_numbers_to_the_hint_bar(self):
        t = MeasureTool()
        self.assertEqual(t.numbers, "")
        t.click(P(0, 0))
        t.move(P(4, 3))
        self.assertEqual(t.numbers, "5.00 m · direction 53.1° from North")
        self.assertTrue(t.hint.startswith("Click: next point"))           # the gestures, without the numbers
        t.click(P(4, 3))
        t.move(P(4, 9, 2))
        self.assertEqual(t.numbers, "6.00 m · along the slope 6.32 m · height difference 2.00 m · direction 0.0° from "
                                    "North · Total 11.00 m · 2 segments · along the slope 11.32 m")
        shown = t.display("plan")["current"]
        # R618: the number alone; the total is the view's pill at the path's end
        self.assertEqual(shown["elastic"]["pill"]["label"], "6.00 m")
        self.assertEqual((shown["total"]["text"], shown["total"]["at"]), ("Total 11.00 m", [4.0, 9.0, 2.0]))
        self.assertEqual([s["pill"]["label"] for s in shown["segments"]], ["5.00 m"])
        t.key("2", "2")
        self.assertEqual(t.numbers, "")                                    # a number being typed: its own pill
        t.key("Escape")
        t.click(P(4, 9, 2))
        t.key("Enter")
        self.assertEqual(t.numbers, "")
        made = t.display("plan")["done"][0]
        self.assertEqual([s["pill"]["label"] for s in made["segments"]], ["5.00 m", "6.00 m"])
        self.assertEqual(made["total"]["text"], "Total 11.00 m")

    def test_nothing_under_the_pointer_takes_its_mark_and_span_away(self):
        """The 3D view's sky has no point (the probe gives None): the mark and the span to the pointer go (they stayed
        where the last point was found); the points placed stay."""
        t = MeasureTool()
        t.click(R((0, 0, 6), kind="vertex", exact=True))
        t.move(R((5, 0, 6), kind="vertex", exact=True))
        self.assertIsNotNone(t.display("3d")["pointer"])
        t.move(None)
        shown = t.display("3d")
        self.assertEqual((shown["pointer"], shown["current"]["elastic"], t.numbers), (None, None, ""))
        self.assertEqual(len(t.points), 1)

    def test_a_measure_chosen_says_its_numbers_in_the_hint_bar(self):
        t = MeasureTool()
        t.click(P(0, 0)); t.click(P(4, 0, 3)); t.key("Enter")
        t.click(P(10, 0)); t.click(P(12, 0)); t.key("Enter")
        t.choose(1)
        self.assertEqual(t.chosen_hint, "5.00 m · in plan 4.00 m · height difference 3.00 m · 36.9° · Delete: remove · "
                                        "Ctrl+C: copy · Shift+click: add a measure · Esc: let go")
        t.choose(2, {"shift"})
        self.assertTrue(t.chosen_hint.startswith("2 measures chosen · Delete: remove"))

    def test_a_path_chosen_says_each_span_too_r618(self):
        """R618: the drawing may hide a short span's number behind a sign; chosen, the hint bar reads every span."""
        t = MeasureTool()
        for p in ((0, 0), (7, 0), (7, 2.5), (14, 2.5)):
            t.click(P(*p))
        t.key("Enter")
        t.choose(1)
        self.assertTrue(t.chosen_hint.startswith("Total 16.50 m · in plan 16.50 m · 7.00 m + 2.50 m + 7.00 m · "
                                                 "Delete: remove"), t.chosen_hint)


class Height(unittest.TestCase):
    def setUp(self):
        self.t = MeasureTool()
        self.t.set_mode("height")

    def test_in_the_plan_two_points_and_the_height_between_the_surfaces(self):
        """R35 (Daniel 14/11: «non mantiene la misura sull'asse Z, va anche in obliquo»): the second point gives only its
        surface's height; the measure is on the foot's vertical, the point clicked is its reference, dotted."""
        t = self.t
        t.click(P(0, 0, 3))
        t.click(P(5, 5, 7.5, kind="vertex"))
        m = t.measures[0]
        self.assertEqual((m.mode, [p.point for p in m.points]), ("height", [(0, 0, 3), (0, 0, 7.5)]))
        made = t.display("plan")["done"][0]
        seg = made["segments"][0]
        self.assertEqual((seg["a"][:2], seg["b"][:2]), ([0, 0], [0, 0]))
        self.assertEqual(seg["style"], "height")
        self.assertEqual(seg["pill"]["text"], "4.50 m")
        self.assertEqual(seg["pill"]["below"], "from the foot · elevation 7.50")
        self.assertIsNone(made["total"])
        self.assertEqual(made["sources"], [{"a": [5, 5, 7.5], "b": [0, 0, 7.5], "kind": "vertex"}])
        self.assertEqual([k["kind"] for k in made["marks"]], ["free", "free"])   # the vertex's mark is on the source
        self.assertEqual(t.copy_text(1), "4.50 m; elevation 7.50 m")

    def test_the_span_keeps_to_the_foots_vertical_wherever_the_pointer_goes(self):
        """Whatever the pointer does after the foot (a far vertex, an arrow, Shift, a number being typed), in the plan
        and in the 3D view the span in hand has the foot's East and North and its large number is the rise."""
        foot = (2.0, 3.0, 1.0)
        for view, probe in (("plan", lambda p, **kw: P(*p, **kw)), ("3d", lambda p, **kw: R(p, **kw))):
            with self.subTest(view=view):
                t = MeasureTool()
                t.set_mode("height")
                t.click(probe(foot, kind="vertex", exact=True))

                def check(point, label, t=t, view=view):
                    shown = t.display(view)
                    elastic = shown["current"]["elastic"]
                    self.assertEqual((elastic["a"][:2], elastic["b"][:2]), ([2, 3], [2, 3]), label)
                    # «≈» on a free point of the 3D view's hit, not the number's business here
                    self.assertEqual(elastic["pill"]["text"].lstrip("≈"), f"{abs(point[2] - foot[2]):.2f} m", label)
                    self.assertEqual(shown["follow"], {"a": [2, 3, 1], "b": [2, 3, 2]}, label)
                    near(self, t.target.point, (2, 3, point[2]))
                    if math.dist(point[:2], foot[:2]) > 1e-6:
                        self.assertEqual(shown["source"]["a"], list(point), label)
                        self.assertEqual(shown["pointer"]["at"], list(point), label)     # the snap's mark there

                far = (40.0, -25.0, 9.5)
                t.move(probe(far, kind="vertex", exact=True))
                check(far, "a far vertex")
                t.move(probe((7.0, 3.5, 4.25)), {"shift"})
                check((7.0, 3.5, 4.25), "Shift")
                for key in ("Right", "Up", "Down", "Left"):
                    t.key(key)
                t.move(probe((9.0, 9.0, 6.0)))
                check((9.0, 9.0, 6.0), "the arrows")
                t.key("2", "2")
                t.move(probe((-4.0, 1.0, 3.0)))
                check((-4.0, 1.0, 3.0), "a number being typed")
                t.key("Enter")                                 # the number typed: 2 m up from the foot
                m = t.measures[-1]
                self.assertEqual([p.point for p in m.points], [foot, (2, 3, 3)])
                self.assertEqual(t.display(view)["done"][0]["segments"][0]["pill"]["text"], "2.00 m")

    def test_in_3d_the_top_stays_on_the_foots_vertical(self):
        t = self.t
        t.click(R((2, 2, 0), kind="vertex", exact=True))
        t.move(R((10, 3, 6.2), kind="vertex", exact=True))
        near(self, t.target.point, (2, 2, 6.2))
        source = t.display("3d")["source"]
        self.assertEqual((source["a"], source["b"]), ([10, 3, 6.2], [2, 2, 6.2]))
        # the height has its own vertical: the arrows constrain nothing, but with the foot placed they are not the
        # view's either (the view never moves under a measurement in hand)
        for key in ("Up", "Down", "Left", "Right"):
            self.assertEqual(t.key(key), USED, key)
        self.assertIsNone(t.constraint)
        t.click(R((10, 3, 6.2), kind="vertex", exact=True))
        self.assertEqual(t.state, "idle")
        self.assertEqual(t.display("3d")["done"][0]["segments"][0]["pill"]["text"], "6.20 m")

    def test_a_height_typed(self):
        t = self.t
        t.click(P(1, 1, 2))
        t.key("3", "3")
        self.assertEqual(t.display("plan")["typed"]["text"], "height: 3_")
        t.key("Enter")
        self.assertEqual(t.measures[0].points[-1].point, (1, 1, 5))

    def test_a_mode_change_ends_the_measure_in_hand(self):
        t = self.t
        t.click(P(0, 0, 0))
        t.set_mode("distance")
        self.assertEqual((t.mode, t.state, t.measures), ("distance", "idle", []))
        with self.assertRaises(ValueError):
            t.set_mode("area")


class Pills(unittest.TestCase):
    def test_choice_4_the_large_number_by_view(self):
        t = MeasureTool()
        t.click(P(*on_pitch(2, 0)))
        t.click(P(*on_pitch(2, 6)))
        t.key("Enter")
        plan = t.display("plan")["done"][0]["segments"][0]["pill"]
        self.assertEqual(plan["text"], "6.00 m")
        self.assertEqual(plan["below"], "along the slope 6.93 m · height difference 3.46 m")
        three = t.display("3d")["done"][0]["segments"][0]["pill"]
        self.assertEqual(three["text"], "6.93 m")
        self.assertEqual(three["below"], "in plan 6.00 · height difference 3.46 · 30.0° (57.7 %)")
        near(self, plan["at"], on_pitch(2, 3))

    def test_a_level_segment_has_nothing_below(self):
        t = MeasureTool()
        t.click(P(0, 0, 4))
        t.click(P(3, 0, 4))
        t.key("Enter")
        for view in ("plan", "3d"):
            self.assertEqual(t.display(view)["done"][0]["segments"][0]["pill"]["below"], "")

    def test_approx_when_an_end_is_not_exact(self):
        t = MeasureTool()
        t.click(P(0, 0, 0))
        t.click(R((3, 4, 0)))
        t.click(R((3, 8, 0), kind="vertex", exact=True))
        t.click(P(0, 8, 0))
        t.key("Enter")
        segs = t.display("3d")["done"][0]["segments"]
        self.assertEqual([s["pill"]["text"] for s in segs], ["≈5.00 m", "≈4.00 m", "3.00 m"])
        self.assertEqual([s["pill"]["approx"] for s in segs], [True, True, False])
        self.assertTrue(t.display("3d")["done"][0]["total"]["text"].startswith("≈Total"))

    def test_the_elastic_segment_says_its_direction_and_the_total_follows_it(self):
        t = MeasureTool()
        t.click(P(0, 0))
        t.click(P(0, 4))
        t.move(P(3, 4))
        current = t.display("plan")["current"]
        self.assertEqual(current["elastic"]["pill"]["text"], "3.00 m")
        self.assertIn("direction 90.0° from North", current["elastic"]["pill"]["below"])
        self.assertEqual(current["total"]["text"], "Total 7.00 m")
        self.assertEqual(current["total"]["at"], [3, 4, 0])

    def test_the_total_on_a_slope_by_view(self):
        t = MeasureTool()
        for n in (0, 3, 6):
            t.click(P(*on_pitch(2, n)))
        t.key("Enter")
        plan = t.display("plan")["done"][0]["total"]
        self.assertEqual((plan["text"], plan["below"]), ("Total 6.00 m", "2 segments · along the slope 6.93 m"))
        three = t.display("3d")["done"][0]["total"]
        self.assertEqual((three["text"], three["below"]), ("Total 6.93 m", "2 segments · in plan 6.00 m"))

    def test_the_marks_keep_their_snap(self):
        t = MeasureTool()
        t.click(P(0, 0, kind="vertex"))
        t.click(R((3, 0, 0), kind="midpoint", exact=True))
        t.move(P(3, 3))
        shown = t.display("plan")
        self.assertEqual([(m["kind"], m["exact"]) for m in shown["current"]["marks"]],
                         [("vertex", True), ("midpoint", True)])
        self.assertEqual(shown["pointer"]["kind"], "free")

    def test_the_display_is_plain_data(self):
        t = MeasureTool()
        t.click(P(0, 0, 3, edge=EAVE, normal=PITCH))
        t.click(P(4, 4, 3))
        t.key("Enter")
        t.click(P(0, 0, 3, edge=EAVE, normal=PITCH))
        t.key("Down")
        t.set_snap("vertex")
        t.move(R((1, 2, 4), normal=PITCH, guides=({"a": (0, 0), "b": (1, 2), "kind": "polar", "label": ""},)))
        t.key("5", "5")
        t.select([1])
        for view in ("plan", "3d"):
            shown = t.display(view)
            self.assertTrue(plain(shown), view)
            json.dumps(shown)
        with self.assertRaises(ValueError):
            t.display("section")


class Hints(unittest.TestCase):
    def test_a_hint_for_every_state(self):
        t = MeasureTool()
        self.assertEqual(t.hint, "Click: first point · Esc: exit · Shift+right-click: snaps")
        t.click(P(0, 0))
        self.assertIn("Arrows", t.hint)
        self.assertIn("Number", t.hint)
        self.assertIn("Backspace", t.hint)
        t.click(P(1, 0))
        self.assertIn("Enter or double-click: finish", t.hint)
        t.click(P(1, 1))
        self.assertIn("first to close", t.hint)
        t.key("2", "2")
        self.assertTrue(t.hint.startswith("Enter: apply length"))
        t.key("Escape")
        t.key("Escape")
        t.set_mode("height")
        self.assertIn("foot", t.hint)
        t.click(P(0, 0))
        self.assertIn("Number: height", t.hint)


class List(unittest.TestCase):
    def setUp(self):
        self.t = MeasureTool()
        for a, b in (((0, 0, 0), (6.4, 0, 2.24)), ((0, 0, 0), (3, 0, 0)), ((0, 0, 0), (0, 2, 0))):
            self.t.click(P(*a))
            self.t.click(P(*b))
            self.t.key("Enter")

    def test_stable_ids_selection_and_removal(self):
        t = self.t
        self.assertEqual([m.id for m in t.measures], [1, 2, 3])
        t.select([1, 3])
        self.assertEqual([d["selected"] for d in t.display("plan")["done"]], [True, False, True])
        self.assertEqual(t.remove_selected(), 2)
        self.assertEqual([m.id for m in t.measures], [2])
        t.click(P(9, 9))
        t.click(P(9, 10))
        t.key("Enter")
        self.assertEqual([m.id for m in t.measures], [2, 4])
        t.select([4])
        t.select([2], add=True)
        t.select([99], add=True)                         # an id that is not there is not chosen
        self.assertEqual(t.selected, {2, 4})
        self.assertEqual(t.key("Delete"), USED)
        self.assertEqual(t.measures, [])

    def test_remove_all(self):
        self.assertEqual(self.t.remove_all(), 3)
        self.assertEqual(self.t.display("3d")["done"], [])

    def test_a_click_chooses_by_the_rule_of_the_selection(self):
        """docs/quick/regole.md, R529: alone only that one, Shift adds (and keeps), Ctrl adds or takes away."""
        t = self.t
        self.assertEqual(t.chosen_hint, "")
        t.choose(2)
        self.assertEqual(t.selected, {2})
        self.assertIn("Delete", t.chosen_hint)
        t.choose(3, {"shift"})
        t.choose(3, {"shift"})
        self.assertEqual(t.selected, {2, 3})
        t.choose(2, {"ctrl"})
        self.assertEqual(t.selected, {3})
        t.choose(2, {"ctrl"})
        self.assertEqual(t.selected, {2, 3})
        t.choose(1)
        self.assertEqual(t.selected, {1})
        t.choose(99)                                    # not a measurement made: nothing changes
        self.assertEqual(t.selected, {1})

    def test_reset_takes_the_one_in_hand_and_those_made(self):
        t = self.t
        t.select([1])
        t.click(P(5, 5))
        t.reset()
        self.assertEqual((t.measures, t.selected, t.points, t.state), ([], set(), [], "idle"))

    def test_the_text_copied(self):
        t = self.t
        self.assertEqual(t.copy_text(1), "6.78 m; in plan 6.40 m; height difference 2.24 m; 19.3°")
        self.assertEqual(t.copy_text(2), "3.00 m")
        self.assertEqual(t.copy_text(42), "")
        t.select([2, 3])
        self.assertEqual(t.copy_selected(), "3.00 m\n\n2.00 m")

    def test_the_text_copied_of_a_ring_and_of_a_height(self):
        t = MeasureTool()
        for p in ((0, 0), (4, 0), (4, 3), (0, 0)):
            t.click(P(*p))
        self.assertEqual(t.copy_text(1).splitlines(),
                         ["Total 12.00 m; in plan 12.00 m; area 6.00 m²", "4.00 m", "3.00 m", "5.00 m"])
        t.set_mode("height")
        t.click(P(0, 0, 1))
        t.click(R((0, 0, 3.5)))
        self.assertEqual(t.copy_text(2), "≈2.50 m; elevation 3.50 m")

    def test_in_italian_the_decimal_comma(self):
        before = i18n._translation
        try:
            i18n.setup("it")
            if i18n.language() != "it":
                self.skipTest("the Italian catalogue is not compiled")
            self.assertTrue(self.t.copy_text(1).startswith("6,78 m; "))
            self.assertIn("19,3°", self.t.copy_text(1))
            self.assertEqual(self.t.display("plan")["done"][1]["segments"][0]["pill"]["text"], "3,00 m")
        finally:
            i18n._translation = before


if __name__ == "__main__":
    unittest.main()
