"""The sweep's light on the plan (R344): the modules lit while the pointer moves, drawn into a layer that follows the
changes; Shift takes out and the sign beside the pointer says it; a click with Ctrl or Shift on a module says the same;
the labels of the sides round at their ends again (R336). Offscreen; no network."""

import statistics
import tempfile
import time
import unittest
from pathlib import Path

import _setup

setUpModule = _setup.keep_global_state


def project(width=40.0, depth=20.0):
    from meridiana import jobs, model
    p = model.Project()
    p.site = model.Site(lat=45.5226, lon=9.0300, address="Rho (MI)")
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [width, 0], [width, depth],
                                                                            [0, depth]], height=9.5))
    p.subfields.append(model.SubField(id="s1", name="Sud", ring=[[1, 1], [width - 1, 1], [width - 1, depth - 1],
                                                                 [1, depth - 1]], building="b1",
                                      params={"tilt": 15.0}, filled=True))
    results, _keys, _laid = jobs.layout_of(p)
    return p, results


class SweepCase(unittest.TestCase):
    """A plan in the Plant phase with a layout of modules; no test of its own (the classes below share it)."""
    width, depth, size = 40.0, 20.0, (900, 600)

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.ui.plan import PlanView
        self.p, self.results = project(self.width, self.depth)
        self.plan = PlanView(Path(tempfile.mkdtemp()))
        self.plan.set_source("none")
        self.plan.resize(*self.size)
        self.plan.show()
        self.plan.set_plant_phase(True)
        self.plan.show_project(self.p, self.results)
        self.plan.fit()
        self.app.processEvents()
        self.addCleanup(self.plan.deleteLater)
        self.addCleanup(self.plan.close)

    def start(self, at, lasso=False):
        """A press at `at` (the viewport's pixels) that is already a drag, as the first move would make it."""
        from PySide6.QtCore import QPointF, Qt
        plan = self.plan
        plan._sweep_wait(QPointF(*at), Qt.KeyboardModifier.NoModifier, lambda: None)
        when = time.monotonic() * 1000.0 - (1000.0 if lasso else 0.0)
        plan.sweep_press = (plan.sweep_press[0], plan.sweep_press[1], plan.sweep_press[2], when)

    def move(self, to, mods=None):
        from PySide6.QtCore import QPointF
        self.plan.pointer_position = QPointF(*to)        # what mouseMoveEvent notes first
        if mods is None:
            self.plan._sweep_moved(QPointF(*to))
        else:
            self.plan._sweep_moved(QPointF(*to), mods)
        self.plan.viewport().repaint()

    def screen_box(self):
        """The modules on the screen: left, top, right, bottom in the viewport's pixels."""
        q = self.plan.module_corners["s1"][1]
        pts = [self.plan.mapFromScene(*c) for c in q.reshape(-1, 2).tolist()]
        return (min(p.x() for p in pts), min(p.y() for p in pts), max(p.x() for p in pts), max(p.y() for p in pts))


class SweepLight(SweepCase):
    def test_the_layer_that_follows_the_changes_is_the_one_made_whole(self):
        plan = self.plan
        left, top, right, bottom = self.screen_box()
        self.start((left - 20, top - 20))
        steps = [(left + (right - left) * f, top + (bottom - top) * f) for f in (0.2, 0.5, 0.8, 1.1, 0.6, 0.3, 0.9)]
        item = None
        for point in steps:
            self.move((point[0] + 30, point[1] + 30))
            item = plan.sweep_item
            self.assertIsNotNone(item)
            kept = item.layer.copy()
            item.layer = None                       # the same modules, made whole
            item._rebuild()
            self.assertEqual(kept, item.layer, "the patched layer is not the one made whole")
        self.assertGreater(len(item.order), 0)
        plan._sweep_cancel()
        self.assertIsNone(plan.sweep_item)

    def test_the_index_takes_the_modules_the_plain_function_took(self):
        import numpy as np
        from PySide6.QtCore import QPointF

        from meridiana import sweep
        plan = self.plan
        left, top, right, bottom = self.screen_box()
        quads = plan.module_corners["s1"][1]
        for kind, a, b in ((sweep.WINDOW, (left - 5, top - 5), (right - 40, bottom + 5)),
                           (sweep.CROSSING, (right - 40, bottom + 5), (left + 40, top + 30)),
                           (sweep.WINDOW, (left + 30, top + 20), (right - 30, bottom - 20))):
            self.start(a)
            plan.sweep_kind = kind
            plan.sweep_points = [plan.sweep_press[0], QPointF(*b)]
            plan.sweep_lasso = False
            plain = np.flatnonzero(sweep.chosen_quads(quads, plan._sweep_ring(), kind)).tolist()
            taken = [key for _sf, key in plan._swept_modules()]
            self.assertEqual(taken, [plan.module_corners["s1"][0][i] for i in plain])
            self.assertEqual(plan._sweep_order().tolist(), plain)
            plan._sweep_cancel()

    def test_shift_lights_the_modules_in_the_red_of_the_removal_and_says_so_at_once(self):
        from PySide6.QtCore import Qt
        plan = self.plan
        left, top, right, bottom = self.screen_box()
        self.start((left - 10, top - 10))
        self.move((right + 10, bottom + 10), Qt.KeyboardModifier.NoModifier)
        self.assertFalse(plan.sweep_remove)
        add = plan.sweep_item.ink.color().name()
        self.move((right + 12, bottom + 10), Qt.KeyboardModifier.ShiftModifier)
        self.assertTrue(plan.sweep_remove)
        out = plan.sweep_item.ink.color().name()
        self.assertEqual(out, plan.colours["sweep_remove"])
        self.assertNotEqual(add, out)
        plan._modifiers_changed(Qt.KeyboardModifier.NoModifier)         # Shift let go: back at once
        self.assertFalse(plan.sweep_remove)
        self.assertEqual(plan.sweep_item.ink.color().name(), add)
        plan._modifiers_changed(Qt.KeyboardModifier.ShiftModifier)
        self.assertTrue(plan.sweep_remove)
        plan._sweep_cancel()
        self.assertFalse(plan.sweep_remove)

    def test_the_sign_beside_the_pointer_is_a_plus_then_a_minus_in_the_colour_of_the_lit_modules(self):
        from PySide6.QtCore import Qt
        plan = self.plan
        left, top, right, bottom = self.screen_box()
        self.start((left - 10, top - 10))
        self.move((left + 100, top + 80), Qt.KeyboardModifier.NoModifier)

        def ink_in_box():
            """The pixels of the sign's box that are in the colour of the sign: the plus has more than the minus."""
            box = plan._action_rect().toAlignedRect()
            image = plan.viewport().grab().toImage()
            want = plan.colours["sweep_remove"] if plan.sweep_remove else plan.sweep_item.ink.color().name()
            from PySide6.QtGui import QColor
            target = QColor(want)
            return sum(1 for x in range(box.left(), box.right() + 1) for y in range(box.top(), box.bottom() + 1)
                       if _near(QColor(image.pixelColor(x, y)), target))
        plus = ink_in_box()
        self.move((left + 100, top + 80), Qt.KeyboardModifier.ShiftModifier)
        minus = ink_in_box()
        self.assertGreater(plus, 10)
        self.assertGreater(minus, 5)
        self.assertGreater(plus, minus * 1.3)
        plan._sweep_cancel()

    def test_the_red_of_the_removal_reads_on_the_plans_ground_and_on_the_sign(self):
        from meridiana import theme_colors, view_colours
        for colours in (view_colours.PHOTO, view_colours.PAPER):
            self.assertGreaterEqual(theme_colors.contrast(colours["sweep_remove"], colours["bg"]), 4.5)
        self.assertGreaterEqual(theme_colors.contrast(view_colours.PHOTO["sweep_remove"],
                                                      view_colours.PHOTO["label_bg"][:7]), 4.5)

    def test_a_click_with_ctrl_or_shift_on_a_module_has_its_sign_and_its_colour(self):
        from PySide6.QtCore import Qt
        plan = self.plan
        keys = plan.module_corners["s1"][0]
        plan.set_swept([("s1", keys[0])])
        none, ctrl, shift = (Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.ControlModifier,
                             Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(plan._module_action(("s1", keys[0]), ctrl), "remove")
        self.assertEqual(plan._module_action(("s1", keys[1]), shift), "add")
        self.assertEqual(plan._module_action(("s1", keys[1]), none), "")
        self.assertEqual(plan._module_action(None, ctrl), "")
        plan.set_swept([])
        self.assertEqual(plan._module_action(("s1", keys[1]), ctrl), "")
        plan.set_swept([("s1", keys[0])])
        at = plan.mapFromScene(_centre(plan, 0))
        plan.pointer_position = _point(at)
        plan.pointer_mods = ctrl
        plan._update_cursor(at)
        self.assertEqual(plan.module_action, "remove")
        self.assertTrue(plan.hover_out)
        plan.pointer_mods = none
        plan._update_cursor(at)
        self.assertEqual((plan.module_action, plan.hover_out), ("", False))
        plan.pointer_position = _point(plan.mapFromScene(_centre(plan, 1)))
        plan.pointer_mods = ctrl
        plan._update_cursor(plan.mapFromScene(_centre(plan, 1)))
        self.assertEqual((plan.module_action, plan.hover_out), ("add", False))
        plan._set_module_action("")

    def test_the_labels_of_the_sides_are_round_at_their_ends_again(self):
        from PySide6.QtGui import QColor

        from meridiana.ui import design
        plan = self.plan
        plan.set_selection("building", "b1")
        plan.set_tool("select")
        self.app.processEvents()
        plan.viewport().repaint()
        pills = plan._side_pills(plan.rings[plan.selection])
        self.assertTrue(pills)
        _side, box, _whole, _text = pills[0]
        self.assertGreaterEqual(design.Radius.PLAN_LABEL, box.height() / 2)      # round ends: half the height
        image = plan.viewport().grab().toImage()
        inside = QColor(image.pixelColor(int(box.left() + box.height() / 2), int(box.center().y())))
        corner = QColor(image.pixelColor(int(box.left() + 2.3), int(box.top() + 2.3)))
        self.assertNotEqual(inside.rgb(), corner.rgb(), "the corner of the label is still filled: it is a rectangle")


def _near(a, b, tolerance=40):
    return abs(a.red() - b.red()) + abs(a.green() - b.green()) + abs(a.blue() - b.blue()) < tolerance


def _centre(plan, index):
    from PySide6.QtCore import QPointF
    q = plan.module_corners["s1"][1][index]
    return QPointF(float(q[:, 0].mean()), float(q[:, 1].mean()))


def _point(p):
    from PySide6.QtCore import QPointF
    return QPointF(p)


class SweepSpeed(SweepCase):
    """3,700 modules, as Daniel's plan has: the move with its repaint stays far under what it cost (100 ms and more
    before R344, 5 ms after). The bound is wide so that a slow machine does not break it."""
    width, depth, size = 182.0, 100.0, (1400, 900)

    def test_a_move_draws_only_what_came_or_went(self):
        plan = self.plan
        left, top, right, bottom = self.screen_box()
        self.start((left - 10, top - 10))
        self.move((left + (right - left) * 0.5, bottom + 10))
        item = plan.sweep_item
        self.assertGreater(len(item.order), 1500)
        self.move((left + (right - left) * 0.5 + 12, bottom + 10))        # one more column, or less
        self.assertLess(item.drawn, len(item.order))

    def test_a_sweep_over_thousands_of_modules_moves_in_a_few_milliseconds(self):
        plan = self.plan
        self.assertGreater(len(plan.module_corners["s1"][0]), 3000)
        left, top, right, bottom = self.screen_box()
        self.start((left - 20, top - 20))
        times = []
        for i in range(1, 61):
            f = i / 60
            t0 = time.perf_counter()
            self.move((left - 20 + (right - left + 60) * f, top - 20 + (bottom - top + 60) * f))
            times.append((time.perf_counter() - t0) * 1000)
        self.assertGreater(len(plan._swept_modules()), 3000)
        self.assertLess(statistics.median(times), 40, times)
        plan._sweep_cancel()


if __name__ == "__main__":
    unittest.main()
