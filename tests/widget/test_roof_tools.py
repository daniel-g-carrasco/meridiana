"""The roof tools of study 22 on the plan and in the Properties (R274, R275): the Pitch card next to the pointer
(depth, slope, ridge height, eave height; Up and Down choose the row, Tab swaps eave and ridge, Enter closes), the
Ridge tool (clicks inside a building, a typed ridge height), and the page of a free pitch. PySide6 and a display
(offscreen will do)."""

import math
import unittest

import _setup
from _fixtures import plan_view

from meridiana import model

setUpModule = _setup.keep_global_state


def house(footprint=None) -> model.Project:
    p = model.Project(name="Tetti")
    p.buildings.append(model.Building(id="b1", name="Casa", height=6.0,
                                      footprint=footprint or [[0, 0], [16, 0], [16, 10], [0, 10]]))
    return p


class PlanCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def plan(self, project=None):
        self.view, _results = plan_view(self, project or house())
        return self.view

    def move(self, x, y):
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent

        from meridiana.ui.plan import to_scene
        pos = QPointF(self.view.mapFromScene(to_scene(x, y)))
        self.app.sendEvent(self.view.viewport(), QMouseEvent(
            QEvent.Type.MouseMove, pos, self.view.viewport().mapToGlobal(pos), Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
        return pos.toPoint()

    def click(self, x, y):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        QTest.mouseClick(self.view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         self.move(x, y))

    def keys(self, *keys):
        from PySide6.QtTest import QTest
        for k in keys:
            if isinstance(k, str):
                QTest.keyClicks(self.view, k)
            else:
                QTest.keyClick(self.view, k)


class PitchCard(PlanCase):
    def test_the_card_takes_a_slope_then_a_ridge_refuses_one_under_the_eave_and_tab_swaps(self):
        from PySide6.QtCore import Qt
        view = self.plan()
        drawn, hints = [], []
        view.pitchDrawn.connect(lambda ring, card: drawn.append((ring, card)))
        view.hint.connect(hints.append)
        view.set_tool("pitch")
        self.click(0, 0)
        self.click(16, 0)
        self.move(8, 5)
        now = view.pitch_values()
        self.assertAlmostEqual(now["depth"], abs(view.snap.point[1]), places=6)   # to the pointer, snapped
        self.assertAlmostEqual(now["depth"], 5.0, delta=0.5)
        self.assertAlmostEqual(now["eave"], 6.0)                    # the building's eave
        self.assertAlmostEqual(now["tilt"], math.degrees(math.atan(0.35)), places=6)   # the covering's 35 %
        lines = view._card_lines()
        self.assertTrue(lines[1].startswith("→"))                   # the depth row first
        self.keys(Qt.Key.Key_Down, "20", Qt.Key.Key_Return)
        self.assertEqual(view.pitch_card["field"], "tilt")
        self.assertAlmostEqual(view.pitch_values()["tilt"], 20.0)
        self.assertEqual(drawn, [])                                 # a slope written does not close
        self.keys(Qt.Key.Key_Down, "5", Qt.Key.Key_Return)          # the ridge, under the eave: refused, said
        self.assertIsNone(view.pitch_card["ridge"])
        self.assertIn("eave", hints[-1])
        self.keys("9", Qt.Key.Key_Return)
        now = view.pitch_values()
        self.assertAlmostEqual(now["ridge"], 9.0)
        self.assertAlmostEqual(now["tilt"], math.degrees(math.atan(3.0 / now["depth"])))
        self.keys(Qt.Key.Key_Tab)                                   # the plan keeps Tab while a pitch is drawn
        self.assertTrue(view.pitch_card["swapped"])
        self.assertEqual(view.pitch_values()["eave_side"], 2)
        self.keys(Qt.Key.Key_Return)                                # nothing typed: closes at the pointer
        self.assertEqual(len(drawn), 1)
        ring, card = drawn[0]
        self.assertEqual(len(ring), 4)
        self.assertEqual(card, {"swapped": True, "tilt": 20.0, "ridge": 9.0, "eave": None})
        self.assertEqual(view.chain, [])
        self.assertFalse(view.pitch_card["swapped"])                # the next pitch starts afresh

    def test_a_typed_depth_closes_and_percent_gives_the_slope(self):
        from PySide6.QtCore import Qt
        view = self.plan()
        drawn = []
        view.pitchDrawn.connect(lambda ring, card: drawn.append((ring, card)))
        view.set_tool("pitch")
        self.click(0, 0)
        self.click(16, 0)
        self.move(8, 3)
        self.keys(Qt.Key.Key_Down, "30%", Qt.Key.Key_Return)
        self.assertAlmostEqual(view.pitch_card["tilt"], math.degrees(math.atan(0.30)))
        self.keys(Qt.Key.Key_Up, "7", Qt.Key.Key_Return)
        self.assertEqual(len(drawn), 1)
        ring, _card = drawn[0]
        self.assertAlmostEqual(abs(ring[2][1] - ring[1][1]), 7.0, places=6)

    def test_a_third_click_is_the_point_of_arrival_and_r_draws_corner_by_corner(self):
        from PySide6.QtCore import Qt
        view = self.plan()
        drawn = []
        view.pitchDrawn.connect(lambda ring, card: drawn.append(ring))
        view.set_tool("pitch")
        self.click(0, 0)
        self.click(16, 0)
        self.click(10, 6)                                   # only its distance from the eave counts
        self.assertEqual(len(drawn), 1)
        self.assertAlmostEqual(drawn[0][2][1], 6.0, delta=3 * view.metres_per_pixel())
        self.keys("r")
        self.assertTrue(view.pitch_points)
        self.click(0, 0)
        self.click(16, 0)
        self.click(8, 5)
        self.assertEqual(len(drawn), 1)                     # the corners go on until Enter
        self.keys(Qt.Key.Key_Return)
        self.assertEqual(len(drawn[1]), 3)

    def test_tab_without_a_pitch_drawn_is_not_taken(self):
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent
        view = self.plan()
        view.set_tool("pitch")
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier)
        view.event(event)
        self.assertFalse(view.pitch_card["swapped"])


class RidgeTool(PlanCase):
    def test_two_clicks_in_a_rectangle_give_the_ridge_and_a_typed_height_goes_with_it(self):
        from PySide6.QtCore import Qt
        view = self.plan()
        got = []
        view.ridgeDrawn.connect(lambda points, ridge: got.append((points, ridge)))
        view.set_tool("ridge")
        self.click(0.5, 5)
        lines = view._card_lines()
        self.assertIn("7.75", lines[1].replace(",", "."))          # 6 + 5 x 35 %, proposed
        self.keys("9", Qt.Key.Key_Return)                           # the height first, one point is not a ridge
        self.assertEqual(got, [])
        self.assertEqual(view.ridge_typed, 9.0)
        self.click(15.5, 5)                                         # four sides: the second click closes
        self.assertEqual(len(got), 1)
        points, ridge = got[0]
        self.assertEqual((len(points), ridge), (2, 9.0))
        self.assertIsNone(view.ridge_typed)

    def test_an_l_takes_a_bent_ridge_closed_with_enter_and_a_click_outside_is_said(self):
        from PySide6.QtCore import Qt
        view = self.plan(house([[0, 0], [20, 0], [20, 8], [8, 8], [8, 20], [0, 20]]))
        got, hints = [], []
        view.ridgeDrawn.connect(lambda points, ridge: got.append(points))
        view.hint.connect(hints.append)
        view.set_tool("ridge")
        self.click(30, 30)
        self.assertEqual(view.chain, [])
        self.assertIn("building", hints[-1])
        for x, y in ((4, 19.5), (4, 4), (19.5, 4)):
            self.click(x, y)
        self.assertEqual(got, [])
        self.keys(Qt.Key.Key_Return)
        self.assertEqual(len(got), 1)
        self.assertEqual(len(got[0]), 3)


class FreePitchPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.ui.properties import Properties
        self.b = model.Building(id="b1", name="Casa", footprint=[[0, 0], [16, 0], [16, 10], [0, 10]], height=6.0)
        self.b.roof.type = "free"
        self.b.roof.free_pitches = [{"ring": [[0, 0], [16, 0], [16, 5], [0, 5]], "eave_side": 0, "eave": 6.0,
                                     "tilt": 20.0}]
        self.props = Properties()
        self.addCleanup(_setup.dispose, self.props)
        self.props.show_building(self.b)
        self.edits, self.actions = [], []
        self.props.edited.connect(lambda kind, oid, changes: self.edits.append(changes))
        self.props.action.connect(lambda what, kind, oid: self.actions.append(what))

    def field(self, tip):
        from PySide6.QtWidgets import QDoubleSpinBox
        return next(w for w in self.props.widget().findChildren(QDoubleSpinBox) if w.toolTip().startswith(tip))

    def button(self, text):
        from PySide6.QtWidgets import QPushButton
        return [w for w in self.props.widget().findChildren(QPushButton) if w.text() == text]

    def test_the_ridge_written_sets_the_slope_and_one_under_the_eave_is_refused(self):
        ridge = self.field("The height of the top of the pitch")
        self.assertAlmostEqual(ridge.value(), 6.0 + 5.0 * math.tan(math.radians(20.0)), places=2)
        ridge.setValue(5.0)
        self.assertEqual(self.edits, [])
        self.assertTrue(self.actions[-1].startswith("refused:"))
        ridge.setValue(9.0)
        (changes,) = self.edits
        self.assertAlmostEqual(changes["roof.free_pitches"][0]["tilt"], math.degrees(math.atan(3.0 / 5.0)))

    def test_swap_and_pick_the_eave_on_the_plan(self):
        (swap,) = self.button("Swap eave and ridge")
        swap.click()
        self.assertEqual(self.edits[-1]["roof.free_pitches"][0]["eave_side"], 2)
        self.assertEqual(self.b.roof.free_pitches[0]["eave_side"], 0)     # the page sends, the window changes
        self.button("Pick on the plan")[0].click()
        self.assertEqual(self.actions[-1], "pick_free_eave:0")

    def test_a_pitch_more_builds_the_page_again(self):
        built = self.props.rebuilds
        self.b.roof.free_pitches = self.b.roof.free_pitches + [{"ring": [[16, 10], [0, 10], [0, 5], [16, 5]],
                                                                "eave_side": 0, "eave": 6.0, "tilt": 20.0}]
        self.props.show_building(self.b)
        self.assertEqual(self.props.rebuilds, built + 1)
        self.assertEqual(len(self.button("Swap eave and ridge")), 2)


if __name__ == "__main__":
    unittest.main()
