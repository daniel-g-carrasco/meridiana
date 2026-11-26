"""The measuring tool in the plan (study 46, package 2; state of r34-righello): the gestures given to the real window,
off screen, and what the plan draws of them, read from its items.

Daniel's choices (14/11/2026): always a path (a click adds a point, a double click or Enter ends; the simple measure
is a click and a double click on the second point); the polar guides on at the start, F8 switches them; in the plan
the large number is the length in plan, the length along the slope and the height difference below it; the
measures made stay in the session. The pills are the plan's sides' pill (M.LengthPill). And the window stays free:
no call of the tool over 5 ms at any step of the pointer, on a small project and on one of hundreds of edges.
"""
from __future__ import annotations

import math
import os
import unittest
from pathlib import Path

os.environ.setdefault("QSG_RENDER_LOOP", "basic")

import _setup
from PySide6.QtQuick import QQuickItem
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QColor, QImage, QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana import i18n
from meridiana.core.model import model
from meridiana.gui.backend.plan import PlanController
from quick.aiuti.finestra_libera import window_stays_free
from quick.aiuti.tempi import check_timing, timed

setUpModule = _setup.keep_global_state
ROOT = Path(__file__).resolve().parents[3]
SCALE, PX, PY = 12, 400, 500              # pixels per metre, where (0, 0) is in the window
T20 = math.tan(math.radians(20))


def shed(extra=0):
    """A shed 24 x 12 m, eaves at 6 m, a gable roof at 20° (ridge along East at N 6); `extra` small flat buildings
    east of it, each four sides and its roof's four (hundreds of reference edges)."""
    p = model.Project(name="Measure in the plan")
    p.buildings.append(model.Building(id="b1", name="Shed", height=6, footprint=[[0, 0], [24, 0], [24, 12], [0, 12]],
                                      roof=model.Roof(type="gable", tilt=20)))
    for k in range(extra):
        x, y = 40 + (k % 10) * 7, -20 + (k // 10) * 7
        p.buildings.append(model.Building(id=f"x{k}", name="Box", height=4,
                                          footprint=[[x, y], [x + 5, y], [x + 5, y + 5], [x, y + 5]]))
    return p


def near(points, expected):
    """Points of the tool as plain rounded tuples (a guide's point is a hair off: 2.0000000000000004)."""
    return [tuple(round(c, 6) + 0.0 for c in p) for p in points] == [tuple(float(c) for c in p) for p in expected]


def kinds_of(item):
    """The QML types an item is made of, its own and those it is built on (an inline component on M.LengthPill)."""
    out, meta = [], item.metaObject()
    while meta is not None:
        out.append(meta.className().split("_QML")[0].split("::")[-1])
        meta = meta.superClass()
    return out


def items(root):
    out, pending = [], [root]
    while pending:
        item = pending.pop()
        out.append(item)
        pending.extend(c for c in item.childItems() if isinstance(c, QQuickItem))  # on Linux PySide hands back a child typed QMetaObject now and then: items only
    return out


class MeasureInThePlan(unittest.TestCase):
    project = staticmethod(shed)

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        i18n.setup("en")
        self.controller = PlanController(model.Project.from_json(self.project().to_json()), manage_layout=False)
        self.engine = QQmlApplicationEngine()
        self.warnings = []
        self.engine.warnings.connect(lambda errors: self.warnings.extend(e.toString() for e in errors))
        self.controller.install(self.engine)
        self.engine.rootContext().setContextProperty("planBackend", self.controller)
        self.engine.load(QUrl.fromLocalFile(str(ROOT / "src/meridiana/gui/qml/Meridiana/Plan/PlanWindow.qml")))
        self.assertTrue(self.engine.rootObjects(), self.warnings)
        self.window = self.engine.rootObjects()[0]
        self.window.show()
        QTest.qWaitForWindowExposed(self.window)
        self.plan = self.window.findChild(QObject, "plan")
        self.addCleanup(self.close)
        self.measure = self.controller.measure
        self.tool = self.measure.tool
        self.frame()
        self.controller.setTool("measure")
        self.app.processEvents()

    def close(self):
        self.window.close()
        self.controller.close()
        self.engine.deleteLater()
        self.app.processEvents()

    def frame(self):
        self.app.processEvents()
        for name, value in (("zoom", SCALE), ("panX", PX), ("panY", PY), ("bearing", 0)):
            self.plan.setProperty(name, value)
        self.app.processEvents()

    # -- gestures given to the window --------------------------------------------------------------------------

    def at(self, point):
        return QPoint(round(PX + SCALE * point[0]), round(PY - SCALE * point[1]))

    def move(self, point, modifiers=Qt.NoModifier):
        QTest.mouseMove(self.window, self.at(point))
        self.app.processEvents()

    def click(self, point, modifiers=Qt.NoModifier):
        self.move(point)
        QTest.mouseClick(self.window, Qt.LeftButton, modifiers, self.at(point))
        self.app.processEvents()

    def double(self, point, modifiers=Qt.NoModifier):
        self.move(point)
        QTest.mouseDClick(self.window, Qt.LeftButton, modifiers, self.at(point))
        self.app.processEvents()

    def key(self, key, text="", modifiers=Qt.NoModifier):
        self.app.sendEvent(self.window, QKeyEvent(QEvent.KeyPress, key, modifiers, text))
        self.app.sendEvent(self.window, QKeyEvent(QEvent.KeyRelease, key, modifiers, text))
        self.app.processEvents()

    # -- what the plan draws ------------------------------------------------------------------------------------

    def drawn(self, name):
        overlay = self.window.findChild(QObject, "toolOverlay")
        return [i for i in items(overlay) if i.objectName() == name and i.isVisible()]

    def pills(self, name="measurePill"):
        """The numbers written on the drawing (R609: one line, no second one, no box)."""
        return sorted(p.property("value") for p in self.drawn(name))

    def numbers(self):
        """The hint bar's numbers (R609), once the pointer rests."""
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.measure._numbers_wait.isActive()))
        return self.measure.numbers

    def made(self, index=-1):
        return [p.point for p in self.tool.measures[index].points]

    # -- the gestures -------------------------------------------------------------------------------------------

    def test_measure_lines_use_common_strokes_dashes_and_smooth_renderer(self):
        from PySide6.QtQml import QQmlExpression, qmlContext

        self.click((30, -4))
        self.click((36, -1))
        self.move((42, 3))

        def value(obj, expression):
            expr = QQmlExpression(qmlContext(obj), obj, expression)
            result = expr.evaluate()
            self.assertFalse(expr.hasError(), expr.error().toString())
            return result[0] if isinstance(result, tuple) else result

        layer = self.window.findChild(QObject, "measureLayer")
        self.assertTrue(value(layer, "layer.enabled"))
        self.assertEqual(value(layer, "layer.samples"), 4)
        elastic = self.window.findChild(QObject, "measureElastic")
        paths = [c for c in elastic.children() if c.property("strokeWidth") is not None]
        self.assertEqual(len(paths), 2)
        self.assertEqual(paths[1].property("strokeWidth"), value(elastic, "M.ControlMetrics.planDrawStroke"))
        self.assertEqual(paths[0].property("strokeWidth"), value(elastic, "M.ControlMetrics.planDrawStroke + M.ControlMetrics.planDrawHalo"))
        self.assertEqual(value(elastic, "JSON.stringify(data[1].dashPattern)"), value(elastic, "JSON.stringify(M.ControlMetrics.planDash)"))
        guides = self.window.findChild(QObject, "measureGuides")
        self.assertEqual(value(guides, "data[0].strokeWidth"), value(guides, "M.ControlMetrics.planStroke + M.ControlMetrics.planDrawHalo"))
        self.assertFalse(self.warnings, self.warnings)

    def test_a_simple_measure_is_a_click_and_a_double_click(self):
        self.click((30, 2))
        self.assertEqual(self.tool.state, "measuring")
        self.double((37, 2))
        self.assertEqual(self.tool.state, "idle")
        self.assertTrue(near(self.made(), [(30, 2, 0), (37, 2, 0)]), self.made())
        self.assertEqual(self.pills(), ["7.00 m"])                     # one span: no total
        # R609: the number over the middle of its span, just off the line, level with it
        pill = self.drawn("measurePill")[0]
        middle = self.at((33.5, 2))
        centre = pill.mapToScene(pill.boundingRect().center())
        self.assertAlmostEqual(centre.x(), middle.x(), delta=1)
        self.assertGreater(middle.y() - centre.y(), pill.height() / 2)   # above the line, not on it
        self.assertAlmostEqual(middle.y() - centre.y(), 17, delta=2)
        self.assertAlmostEqual(pill.property("rotation"), 0, delta=0.5)
        self.assertFalse(self.warnings, self.warnings)

    def test_three_spans_end_with_enter(self):
        for p in ((30, -4), (36, -4), (36, 4)):
            self.click(p)
        self.move((42, 4))
        # in hand: the two spans placed, the one to the pointer, the total in its pill at the pointer's end (R618); the
        # direction and the count in the hint bar (R609)
        self.assertEqual(self.pills(), ["6.00 m", "6.00 m", "8.00 m"])
        self.assertEqual(self.pills("measureTotal"), ["Total 20.00 m"])
        self.assertEqual(self.numbers(), "6.00 m · direction 90.0° from North · Total 20.00 m · 3 segments")
        self.assertTrue(self.plan.property("statusText").startswith(self.numbers() + " · Click: next point"))
        self.click((42, 4))
        self.key(Qt.Key_Return)
        self.assertEqual(self.tool.state, "idle")
        self.assertTrue(near([p[:2] for p in self.made()], [(30, -4), (36, -4), (36, 4), (42, 4)]), self.made())
        self.assertEqual(self.pills(), ["6.00 m", "6.00 m", "8.00 m"])
        self.assertEqual(self.pills("measureTotal"), ["Total 20.00 m"])
        self.assertEqual(self.numbers(), "")
        self.assertEqual(len(self.drawn("measureMark")), 4)

    def test_a_measure_made_does_not_steer_the_next_r563(self):
        self.click((30, 5)); self.double((37, 5))
        # 0.3 m east of the line going north from the first point of the measure made (a pixel is 0.083 m)
        self.move((30.3, 12))
        self.assertEqual(self.drawn("measureGuides"), [])
        self.click((30.3, 12))
        start = self.tool.points[0].point
        self.assertLess(math.dist(start[:2], (30.3, 12)), 0.05)
        self.assertEqual(len(self.tool.measures), 1)
        self.assertEqual(self.pills(), ["7.00 m"])                        # the measure made stays drawn

    def test_the_polar_guides_follow_the_plans_ortho(self):
        """Daniel 14/11/2026: no entry of their own; the 15° guides follow the plan's Ortho (its bar's button, F8), one
        setting for drawing and measuring: on, they pull the next point; off, the point stays where it is clicked."""
        self.assertEqual(self.measure.polar, self.controller.drawing.orthogonal)    # as the plan's command is
        self.assertEqual(self.controller.orthoEnabled, self.controller.drawing.orthogonal)
        if not self.measure.polar:
            self.controller.viewAction("ortho")                           # the button of the plan's bar
        self.assertTrue((self.measure.polar, self.controller.drawing.orthogonal, self.controller.orthoEnabled)
                        == (True, True, True))
        self.click((30, 0))
        self.move((37, 7.3))                                              # 0.3 m off the 45° step
        self.assertTrue(self.drawn("measureGuides"))
        self.assertNotEqual(self.tool.target.point[:2], (37.0, 7.25))
        QTest.keyClick(self.window, Qt.Key_F8)
        self.app.processEvents()
        self.assertEqual((self.measure.polar, self.controller.drawing.orthogonal), (False, False))   # one setting
        self.assertFalse(self.controller.orthoEnabled)
        self.assertEqual(self.tool.points[0].point[:2], (30.0, 0.0))      # the point placed stays
        self.click((37, 7.25))                                            # a pixel's point: exactly where clicked
        self.assertEqual(self.tool.points[-1].point[:2], (37.0, 7.25))
        self.assertEqual(self.drawn("measureGuides"), [])
        self.key(Qt.Key_Return)
        self.controller.setTool("building")                               # drawing: the same setting, off
        self.assertFalse(self.controller.orthoEnabled)
        self.controller.viewAction("ortho")                               # on while drawing...
        self.controller.setTool("measure")
        self.assertTrue(self.measure.polar)                               # ...on for the ruler

    def test_snaps_to_a_vertex_and_a_midpoint_with_their_marks(self):
        self.move((24.3, 12.2))
        pointer = self.drawn("measurePointer")
        self.assertEqual([m.property("kind") for m in pointer], ["vertex"])
        self.click((24.3, 12.2))
        self.assertEqual(self.tool.points[0].point[:2], (24.0, 12.0))
        self.assertAlmostEqual(self.tool.points[0].point[2], 6.0)
        self.move((12.2, 12.3))
        self.assertEqual([m.property("kind") for m in self.drawn("measurePointer")], ["midpoint"])
        self.double((12.2, 12.3))
        self.assertEqual(sorted(m.property("kind") for m in self.drawn("measureMark")), ["midpoint", "vertex"])
        self.assertEqual(self.pills(), ["12.00 m"])

    def test_two_heights_on_a_pitch_choice_4(self):
        """In the plan the number is the length in plan; along the slope and the height difference in the hint bar
        while measuring (R609: nothing under the number)."""
        self.click((4, 1)); self.move((4, 5))
        along = 4 / math.cos(math.radians(20))
        self.assertTrue(self.numbers().startswith(f"4.00 m · along the slope {along:.2f} m · height difference "
                                                  f"{4 * T20:.2f} m"), self.numbers())
        self.double((4, 5))
        a, b = self.made()
        self.assertAlmostEqual(a[2], 6 + T20)
        self.assertAlmostEqual(b[2], 6 + 5 * T20)
        self.assertEqual(self.pills(), ["4.00 m"])

    def test_the_arrows_are_the_tools_only_with_a_point_placed(self):
        keys = self.controller.calls["key"]
        self.key(Qt.Key_Right)
        # at rest the arrow is the plan's, as before: it reached the plan and the tool took nothing of it
        self.assertEqual(self.controller.calls["key"], keys + 1)
        self.assertEqual((self.tool.constraint, self.controller.tool, self.tool.state), (None, "measure", "idle"))
        self.click((30, 0)); self.move((36, 2))
        self.key(Qt.Key_Right)                                            # with a point placed: the East axis
        self.assertEqual(self.tool.constraint, "east")
        # the pointer where it was, found again without the polar guides: on the axis, square under it
        self.assertTrue(near([self.tool.target.point[:2]], [(36, 0)]), self.tool.target)
        self.assertTrue(self.pills("measureConstraint"))
        self.key(Qt.Key_Right)                                            # the same arrow again: free
        self.assertIsNone(self.tool.constraint)

    def test_escape_backspace_and_another_tool(self):
        self.click((30, 0)); self.click((36, 0))
        self.key(Qt.Key_Backspace)
        self.assertEqual(len(self.tool.points), 1)
        self.key(Qt.Key_Escape)                                           # the measurement in hand goes
        self.assertEqual((self.tool.state, self.controller.tool), ("idle", "measure"))
        self.key(Qt.Key_Escape)                                           # then the tool: Select
        self.assertEqual(self.controller.tool, "select")
        self.controller.setTool("measure")
        self.click((30, 0)); self.click((36, 0))
        self.controller.setTool("building")                               # another tool: two points are kept
        self.assertEqual((len(self.tool.measures), self.tool.state), (1, "idle"))
        self.app.processEvents()
        self.assertEqual(self.pills(), ["6.00 m"])                  # drawn with the other tool too
        self.controller.setTool("select")
        self.app.processEvents()
        self.assertEqual(self.pills(), ["6.00 m"])
        self.assertFalse(self.warnings, self.warnings)

    # -- the path's gestures (package 3) ------------------------------------------------------------------------

    def test_a_click_on_the_first_point_closes_the_ring_with_its_area(self):
        for p in ((30, -4), (36, -4), (36, 4)):
            self.click(p)
        self.click((30, -4))                                              # the first point again: the ring closes
        self.assertEqual(self.tool.state, "idle")
        self.assertTrue(self.tool.measures[-1].closed)
        self.assertEqual(len(self.made()), 3)
        # the closing span has its number too, the total in its pill (R618); the area when the measure is chosen (R609)
        self.assertEqual(self.pills(), ["10.00 m", "6.00 m", "8.00 m"])
        self.assertEqual(self.pills("measureTotal"), ["Total 24.00 m"])
        self.tool.choose(self.tool.measures[-1].id)
        self.assertTrue(self.tool.chosen_hint.startswith("Total 24.00 m · in plan 24.00 m · area 24.00 m²"),
                        self.tool.chosen_hint)

    def test_enter_with_one_point_drops_the_measurement(self):
        self.click((30, 0))
        self.key(Qt.Key_Return)
        self.assertEqual((self.tool.state, len(self.tool.measures)), ("idle", 0))
        self.assertEqual((self.pills(), self.drawn("measureMark")), ([], []))

    def test_the_double_click_adds_no_second_point(self):
        self.click((30, 0)); self.click((36, 0)); self.double((36, 6))
        self.assertEqual(self.tool.state, "idle")
        self.assertTrue(near([p[:2] for p in self.made()], [(30, 0), (36, 0), (36, 6)]), self.made())   # two spans
        self.assertEqual(self.pills(), ["6.00 m", "6.00 m"])
        self.assertEqual(self.pills("measureTotal"), ["Total 12.00 m"])

    def test_a_number_and_enter_place_the_point_at_that_length_along_the_direction_shown(self):
        self.click((30, 0))
        self.move((36, 0))                                                # the direction shown: East
        self.key(Qt.Key_4, "4")
        self.assertEqual(self.tool.state, "typing")
        self.key(Qt.Key_Return)                                           # as a click, 4 m along it
        self.assertEqual(self.tool.state, "measuring")
        self.assertTrue(near([p.point[:2] for p in self.tool.points], [(30, 0), (34, 0)]), self.tool.points)
        self.key(Qt.Key_Return)                                           # Enter again ends it
        self.assertTrue(near([p[:2] for p in self.made()], [(30, 0), (34, 0)]), self.made())

    def test_backspace_takes_the_last_point_and_the_hint_row_follows_every_state(self):
        hints = [self.plan.property("statusText")]
        for p in ((30, -4), (36, -4), (36, 4)):
            self.click(p)
            hints.append(self.plan.property("statusText"))
            self.assertEqual(hints[-1], self.tool.hint)                   # on the point placed: no span, no numbers
        self.key(Qt.Key_Backspace)                                        # the last point goes, the others stay
        self.assertTrue(near([p.point[:2] for p in self.tool.points], [(30, -4), (36, -4)]), self.tool.points)
        self.assertEqual(len(self.drawn("measureMark")), 2)
        # the pointer is still on the point taken back: the span to it has its numbers before the gestures (R609)
        self.assertEqual(self.plan.property("statusText"),
                         "8.00 m · direction 0.0° from North · Total 14.00 m · 2 segments · " + hints[2])
        self.key(Qt.Key_5, "5")
        hints.append(self.plan.property("statusText"))
        self.key(Qt.Key_Escape)                                           # the digits go
        self.key(Qt.Key_Return)
        hints.append(self.plan.property("statusText"))                    # at rest again
        self.assertEqual(hints[0], hints[-1])
        self.assertEqual(len(set(hints[:5])), 5, hints)                   # rest, one, two, three points, typing
        self.assertTrue(all(hints), hints)

    def test_in_the_height_mode_two_clicks_give_the_height_between_the_surfaces(self):
        self.measure.setMode("height")
        self.assertEqual(self.plan.property("statusText"),
                         "Click: foot of the height · Esc: exit · Shift+right-click: snaps")
        self.click((30, 2))                                               # the ground
        self.click((4, 5))                                                # the pitch, 5 m from the eave
        self.assertEqual((self.tool.state, self.tool.measures[-1].mode), ("idle", "height"))
        foot, top = self.made()
        self.assertAlmostEqual(foot[2], 0)
        self.assertAlmostEqual(top[2], 6 + 5 * T20)
        self.assertEqual(self.pills(), [f"{6 + 5 * T20:.2f} m"])
        self.controller.setTool("select"); self.controller.setTool("measure")
        self.assertEqual(self.measure.mode, "height")                     # the mode stays until another is chosen

    def test_the_height_stays_on_the_foots_vertical_and_the_point_clicked_is_its_reference(self):
        """R35 (Daniel 14/11: «va anche in obliquo»): after the foot, wherever the pointer goes (a far corner, Shift, an
        arrow, a number being typed) the span measured has the foot's East and North and its large number is the
        height difference; the point under the pointer is drawn dotted, as the reference, and keeps the snap's mark."""
        self.measure.setMode("height")
        self.click((30, 2))
        rise = 6.0                                                         # the shed's eave, from the ground
        steps = [("the far corner", (0.2, 0.2), Qt.NoModifier), ("Shift", (24.2, 0.1), Qt.ShiftModifier)]
        for label, point, mods in steps:
            QTest.mouseMove(self.window, self.at(point))
            if mods != Qt.NoModifier:                                     # Shift held while the pointer moves
                self.app.sendEvent(self.window, QKeyEvent(QEvent.KeyPress, Qt.Key_Shift, mods))
                QTest.mouseMove(self.window, self.at((point[0] + 0.05, point[1])))
            self.app.processEvents()
            self.assertTrue(near([self.tool.target.point[:2]], [(30, 2)]), (label, self.tool.target))
            self.assertAlmostEqual(self.tool.target.point[2], rise, msg=label)
            self.assertEqual(self.pills(), [f"{rise:.2f} m"], label)
            self.assertTrue(self.drawn("measureReference"), label)         # the dotted line to the corner
            self.assertEqual([m.property("kind") for m in self.drawn("measurePointer")], ["vertex"], label)
        self.app.sendEvent(self.window, QKeyEvent(QEvent.KeyRelease, Qt.Key_Shift, Qt.NoModifier))
        self.key(Qt.Key_Right)
        self.move((4, 5))                                                 # an arrow, then the pitch
        self.assertTrue(near([self.tool.target.point[:2]], [(30, 2)]), self.tool.target)
        self.key(Qt.Key_1, "1")
        self.move((10, 2))                                                # a number being typed
        self.assertTrue(near([self.tool.target.point[:2]], [(30, 2)]), self.tool.target)
        self.key(Qt.Key_Escape)                                           # the digits go
        self.click((0.2, 0.2))                                            # the corner: the measure made
        foot, top = self.made()
        self.assertEqual(top[:2], foot[:2])
        self.assertAlmostEqual(top[2] - foot[2], rise)
        self.assertEqual(self.pills(), [f"{rise:.2f} m"])
        self.assertTrue(self.drawn("measureReference"))                   # it stays with the measure made
        self.assertEqual([m.property("kind") for m in self.drawn("measureSourceMark")], ["vertex"])
        self.assertFalse(self.warnings, self.warnings)

    # -- R609: the numbers written along the spans --------------------------------------------------------------------

    def word_of(self, value):
        found = [p for p in self.drawn("measurePill") if p.property("value") == value]
        self.assertTrue(found, (value, self.pills(), [[round(c, 2) for c in p.point] for m in self.tool.measures
                                                      for p in m.points]))
        return found[0]

    def check_along(self, word, a, b):
        """The word runs along the span a-b (plan points) within 2°, never upside down, centred on the span's middle
        and just off the line (closer than its own height); gives its centre and the screen's span."""
        pa, pb = self.at(a), self.at(b)
        angle = math.degrees(math.atan2(pb.y() - pa.y(), pb.x() - pa.x()))
        upright = angle - 180 if angle >= 90 else angle + 180 if angle < -90 else angle
        rotation = word.property("rotation")
        self.assertTrue(-90 <= rotation < 90, rotation)                 # left to right, or from the bottom up
        self.assertAlmostEqual(rotation, upright, delta=2)
        centre = word.mapToScene(word.boundingRect().center())
        mx, my = (pa.x() + pb.x()) / 2, (pa.y() + pb.y()) / 2
        dx, dy = pb.x() - pa.x(), pb.y() - pa.y()
        n = math.hypot(dx, dy)
        across = abs((centre.x() - mx) * dy - (centre.y() - my) * dx) / n      # from the line
        along = abs((centre.x() - mx) * dx + (centre.y() - my) * dy) / n       # from the middle, along it
        self.assertLess(along, 1.5)
        self.assertGreater(across, word.height() / 2)                    # off the line, not over it
        # by the line: the line's halo and two pixels, or (a span shorter than its number) the marks' half as well
        self.assertLess(across, word.height() / 2 + 11)
        return centre

    def test_each_number_is_written_along_its_span_r609(self):
        """R609 (Daniel 14/11/2026: «semplici scritte allineate con le linee di misurazione»): a level span, a diagonal
        one, one going North and one going down to the left; no box, no second line, the words are the one component
        M.SpanLabel; the diagonal's number stays by its span (it went far from it as a two-line pill)."""
        spans = {"level": ((30, -4), (36, -4)), "diagonal": ((30, 0), (36, 6)), "north": ((40, -4), (40, 4)),
                 "down": ((50, 6), (44, 1))}
        for a, b in spans.values():
            self.click(a); self.double(b)
        words = self.drawn("measurePill")
        self.assertEqual(len(words), 4)
        for w in words:
            self.assertIn("SpanLabel", kinds_of(w))
            self.assertIn("LengthPill", kinds_of(w))
            self.assertEqual(w.property("below"), "")                       # one line only
            self.assertIsNotNone(w.findChild(QObject, "lengthPillValue"))  # the common pill, one number
        for name, (a, b) in spans.items():
            length = math.dist(a, b)
            with self.subTest(name):
                self.check_along(self.word_of(f"{length:.2f} m"), a, b)
        self.assertAlmostEqual(self.word_of("8.00 m").property("rotation"), -90, delta=0.5)   # read from the bottom up

    def test_a_short_span_hides_its_number_behind_a_sign_until_it_fits(self):
        """R618: a span 6 px long has no room for its number, on it or out of it: a sign across its middle; zoomed in,
        the number is on its span again."""
        self.click((30, 2)); self.double((30.5, 2))                      # 6 px long
        self.assertEqual(self.pills(), [])
        signs = self.drawn("measureSigns")                               # one drawing for all the signs
        self.assertEqual((len(signs), signs[0].property("count")), (1, 1))
        middle = self.at((30.25, 2))
        import json

        from PySide6.QtQml import QQmlEngine, QQmlExpression
        layer = self.window.findChild(QObject, "measureLayer")
        value = QQmlExpression(QQmlEngine.contextForObject(layer), layer, "JSON.stringify(signs.plain)").evaluate()
        (a, b), = json.loads(value[0] if isinstance(value, tuple) else value)     # one stroke, across the span
        centre = layer.mapToScene(QPointF((a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2))
        self.assertLess(abs(centre.x() - middle.x()) + abs(centre.y() - middle.y()), 2)
        self.assertLess(abs(a["x"] - b["x"]), 0.01)                        # square to the level span
        self.assertAlmostEqual(abs(a["y"] - b["y"]), 8, delta=0.01)        # measureSign long
        for name, value in (("zoom", 120), ("panX", PX - 108 * 30.25), ("panY", PY + 108 * 2)):
            self.plan.setProperty(name, value)                            # 60 px long
        self.app.processEvents()
        self.assertEqual(self.pills(), ["0.50 m"])
        self.assertEqual(self.drawn("measureSigns"), [])

    def test_the_total_of_a_path_is_a_pill_at_its_end(self):
        """R618 (Daniel 14/11/2026: «non mi piace il fatto che il totale sia insieme alla riga dell'ultima misura...
        starei sul tipo pillola»): the last span has its number alone; the total is the plan's pill of a length, at the
        path's end, clear of the spans."""
        for p in ((30, -4), (36, -4), (36, 2)):
            self.click(p)
        self.double((30, 2))
        self.assertEqual(self.pills(), ["6.00 m", "6.00 m", "6.00 m"])
        totals = self.drawn("measureTotal")
        self.assertEqual([t.property("value") for t in totals], ["Total 18.00 m"])
        self.assertIn("LengthPill", kinds_of(totals[0]))
        box = totals[0].mapRectToScene(totals[0].boundingRect())
        end = self.at((30, 2))
        dx = max(box.left() - end.x(), 0, end.x() - box.right())
        dy = max(box.top() - end.y(), 0, end.y() - box.bottom())
        self.assertLess(math.hypot(dx, dy), 12)                            # by the end: half a mark and a gap
        self.assertGreater(math.hypot(dx, dy), 5)                          # clear of the end's mark

    def test_the_sides_measures_and_the_measures_words_are_apart(self):
        """The plan's sides keep their pill (M.LengthPill) for now: Daniel decides whether they too become words."""
        self.controller.setTool("select")
        self.controller.editor.select("building", "b1")
        self.controller._overlays()
        self.app.processEvents()
        sides = [i for i in items(self.plan) if i.objectName().startswith("sidePill") and i.isVisible()]
        self.assertEqual(len(sides), 4)
        for side in sides:
            self.assertIn("LengthPill", kinds_of(side))


PATH = ((30, -4), (37, -4), (37, -1.5), (44, -1.5))        # Daniel's capture: 7,00 + 2,50 + 7,00 m


class WordsThatFit(unittest.TestCase):
    """R618 (Daniel 14/11/2026: «c'è una linea corta nella quale la misura si accavalla alla linea di fianco. Bisogna
    fare in modo di evitarlo»): a word stays on its span only when it fits and touches nothing; else out of the span,
    past its freer end; else hidden behind a sign that shows it on hover; zoomed in, on its span again, without going
    back and forth at the limit. The total is a pill at the path's end."""
    project = staticmethod(shed)
    setUpClass = classmethod(MeasureInThePlan.setUpClass.__func__)
    setUp, close, frame, at = MeasureInThePlan.setUp, MeasureInThePlan.close, MeasureInThePlan.frame, MeasureInThePlan.at
    move, click, double, key = MeasureInThePlan.move, MeasureInThePlan.click, MeasureInThePlan.double, MeasureInThePlan.key
    drawn, pills = MeasureInThePlan.drawn, MeasureInThePlan.pills

    def make_path(self, path=PATH):
        for p in path[:-1]:
            self.click(p)
        self.double(path[-1])
        self.controller.setTool("select")
        self.app.processEvents()

    def zoom(self, scale, centre=(37, -2.75)):
        """The plan at `scale` pixels a metre, `centre` kept where it is at SCALE."""
        cx, cy = PX + SCALE * centre[0], PY - SCALE * centre[1]
        for name, value in (("zoom", scale), ("panX", cx - scale * centre[0]), ("panY", cy + scale * centre[1])):
            self.plan.setProperty(name, value)
        self.app.processEvents()

    def screen(self, point):
        z, x, y = (self.plan.property(k) for k in ("zoom", "panX", "panY"))
        return (x + z * point[0], y - z * point[1])

    def words(self):
        """Every word of the measures made, shown or not."""
        overlay = self.window.findChild(QObject, "toolOverlay")
        return [i for i in items(overlay) if i.objectName() == "measurePill" and i.property("measureId")]

    def mode(self, value):
        """Where the layout put the word: "on" its span, "out" of it or "hidden" (R618)."""
        return next(i for i in self.words() if i.property("value") == value).property("mode")

    def polygon(self, item):
        from PySide6.QtCore import QPointF
        from shapely.geometry import Polygon
        w, h = item.width(), item.height()
        return Polygon([(q.x(), q.y()) for q in (item.mapToScene(QPointF(*c)) for c in ((0, 0), (w, 0), (w, h), (0, h)))])

    def check_clear(self, path):
        """No word or total shown touches a span other than its own (with the span's halo, a mark's half at the
        ends) or another word; gives the values shown."""
        from shapely.geometry import LineString
        halo = 2.8                                          # (measureLine + measureHalo) / 2
        spans = [(tuple(a[:2]), tuple(b[:2]), LineString([self.screen(a), self.screen(b)]).buffer(halo))
                 for a, b in zip(path, path[1:], strict=False)]
        shown = self.drawn("measurePill") + self.drawn("measureTotal")
        boxes = [(i.property("value"), self.polygon(i), i.property("span")) for i in shown]
        for k, (value, box, span) in enumerate(boxes):
            own = (tuple(span["a"][:2]), tuple(span["b"][:2])) if span else None
            for a, b, line in spans:
                if own and math.dist(own[0], a) < 1e-6 and math.dist(own[1], b) < 1e-6:
                    continue
                self.assertFalse(box.intersects(line), (value, "touches the span", a, b))
            for j, (other, obox, _) in enumerate(boxes):
                if j != k:
                    self.assertFalse(box.intersects(obox), (value, "touches", other))
        return [v for v, _, _ in boxes]

    def test_by_the_short_span_no_word_touches_another_line_or_word(self):
        """The capture's zoom (12 px a metre): the 2,50 m span is 30 px long, its number 38: no longer beside it over
        the 7,00 m span; by rectangles and by pixels."""
        self.make_path()
        shown = self.check_clear(PATH)
        self.assertIn("Total 16.50 m", shown)
        self.assertEqual(shown.count("7.00 m"), 2)
        # by pixels: what the words change of the picture is never a pixel of a span or a mark
        import numpy as np
        draw = QColor(self.controller.planColors["draw"])

        def picture():
            QTest.qWait(40)
            from quick.aiuti.view_grab import grab_item
            image = grab_item(self.plan).convertToFormat(QImage.Format.Format_RGB32)
            a = np.frombuffer(image.constBits(), np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)
            return a[:, :image.width(), :3].astype(int)
        with_words = picture()
        hidden = self.drawn("measurePill") + self.drawn("measureTotal")
        for item in hidden:
            item.setVisible(False)
        self.app.processEvents()
        without = picture()
        ink = np.abs(without - np.array([draw.blue(), draw.green(), draw.red()])).sum(axis=2) < 60
        changed = np.abs(with_words - without).sum(axis=2) > 30
        self.assertGreater(changed.sum(), 200)                             # the words are drawn
        self.assertGreater((1 - np.minimum(np.abs(without - np.array([draw.blue(), draw.green(), draw.red()])).sum(axis=2) / 200, 1)).sum(), 100)                                 # and so are the spans
        self.assertLessEqual(int((changed & ink).sum()), 2, "a word drawn over a span")

    def test_zooming_out_and_in_the_word_goes_out_hides_and_comes_back_without_flickering(self):
        """From near to far: on the span, out of it, hidden with its sign; and back. Each change once, and the way
        back changes later than the way out (the hysteresis): no word goes back and forth at a limit."""
        self.make_path()
        scales = [40 * 0.985 ** k for k in range(200) if 40 * 0.985 ** k > 2]
        out = []
        for s in scales:
            self.zoom(s)
            out.append(self.mode("2.50 m"))
        back = []
        for s in reversed(scales):
            self.zoom(s)
            back.append(self.mode("2.50 m"))
        back.reverse()

        def changes(modes):
            return [(k, modes[k - 1], modes[k]) for k in range(1, len(modes)) if modes[k] != modes[k - 1]]
        self.assertEqual([c[1:] for c in changes(out)], [("on", "out"), ("out", "hidden")], out)
        self.assertEqual([c[1:] for c in changes(back)], [("on", "out"), ("out", "hidden")], back)
        for (k_out, *_), (k_back, *_) in zip(changes(out), changes(back), strict=True):
            self.assertLess(k_back, k_out)                                 # coming back needs a larger zoom
        # at the limit, a pixel either way changes nothing
        k = changes(out)[0][0]
        for s in (scales[k], scales[k - 1], scales[k], scales[k - 1]):
            self.zoom(s)
            self.assertEqual(self.mode("2.50 m"), "out")

    def test_the_sign_of_a_hidden_word_shows_it_under_the_pointer(self):
        self.make_path()
        self.zoom(7.8)                                     # 2,50 m: 19,5 px, under measureWordOutMin; 7,00 m on its span
        self.assertEqual(self.mode("2.50 m"), "hidden")
        signs = self.drawn("measureSigns")
        self.assertGreaterEqual(signs[0].property("count"), 1)
        self.assertEqual(self.drawn("measureReveal"), [])
        middle = self.screen(((PATH[1][0] + PATH[2][0]) / 2, (PATH[1][1] + PATH[2][1]) / 2))
        QTest.mouseMove(self.window, QPoint(round(middle[0]), round(middle[1])))
        self.app.processEvents()
        self.assertTrue(_setup.wait_until(self.app, lambda: bool(self.drawn("measureReveal"))))
        self.assertIn("2.50 m", [r.property("value") for r in self.drawn("measureReveal")])
        QTest.mouseMove(self.window, QPoint(round(middle[0]), round(middle[1] + 60)))
        self.app.processEvents()
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.drawn("measureReveal")))

    def test_the_total_pill_is_at_the_end_and_over_no_span(self):
        self.make_path()
        totals = self.drawn("measureTotal")
        self.assertEqual([t.property("value") for t in totals], ["Total 16.50 m"])
        box = self.polygon(totals[0])
        from shapely.geometry import LineString, Point
        self.assertLess(box.distance(Point(self.screen(PATH[-1]))), 12)
        last = LineString([self.screen(PATH[-2]), self.screen(PATH[-1])])
        self.assertGreater(box.distance(last), 2.8)                        # not on the last span's row
        self.assertNotIn("Total", " ".join(self.pills()))                  # nor after its number

    @timed('no call of the window over 5 ms')
    def test_twenty_spans_zoomed_keep_the_window_free(self):
        """The layout of the words is light: a path of 20 spans zoomed in and out, the time of each step of the zoom
        (the bindings, the layout among them) and the window's beat (not asserted off screen: the software renderer
        draws on the window's thread, finestra_libera.py)."""
        import time

        from quick.aiuti.finestra_libera import software_frames
        path = [(-10 + 2 * k, -8 + (1.5 if k % 2 else 0)) for k in range(21)]
        self.make_path(path)
        self.assertEqual(len(self.words()), 20, [len(m.points) for m in self.tool.measures])
        steps = []
        with window_stays_free(self.measure, call_ms=5, beat_ms=None if software_frames(self.window) else 50) as seen:
            for k in list(range(60)) + list(range(60, 0, -1)):
                scale, cx, cy = 40 * 0.96 ** k, PX, PY + SCALE * 7
                started = time.perf_counter()                    # the bindings follow the zoom at once, the layout too
                for name, value in (("zoom", scale), ("panX", cx), ("panY", cy - scale * 7)):
                    self.plan.setProperty(name, value)
                steps.append((time.perf_counter() - started) * 1000)
                self.app.processEvents()                         # the frame
        # the layout alone, the work R618 adds once the view has moved: under the threshold of a call on the window's
        # thread (finestra_libera, call_ms 5)
        from PySide6.QtCore import QMetaObject
        layer = self.window.findChild(QObject, "measureLayer")
        layout = []
        for _ in range(50):
            started = time.perf_counter()
            QMetaObject.invokeMethod(layer, "relayout")
            layout.append((time.perf_counter() - started) * 1000)
        steps.sort()
        layout.sort()
        print(f"\nR618, 20 spans, {len(steps)} zoom steps: median {steps[len(steps) // 2]:.2f} ms, "
              f"p95 {steps[int(len(steps) * 0.95)]:.2f} ms, longest {steps[-1]:.2f} ms; {seen}; the layout: median "
              f"{layout[25]:.2f} ms, longest {layout[-1]:.2f} ms")
        check_timing(layout[25] < 5, f'Layout median {layout[25]:.2f} ms (limit 5 ms)')


class MeasuresThatStay(unittest.TestCase):
    """Study 46, 3.6 (Daniel's choice 3): the measures made stay in the session until removed. With Select a click on
    a pill chooses (Shift adds, Ctrl adds or takes away), Delete removes the chosen, Ctrl+C copies their text, Esc or
    a click elsewhere lets them go; with Measure in hand the click measures through the pills. Never in the project:
    no undo step, nothing to save; another project in hand takes them away."""
    project = staticmethod(shed)
    setUpClass = classmethod(MeasureInThePlan.setUpClass.__func__)
    # the window and the gestures of MeasureInThePlan (not inherited: its tests would run twice)
    setUp, close, frame, at = MeasureInThePlan.setUp, MeasureInThePlan.close, MeasureInThePlan.frame, MeasureInThePlan.at
    move, click, double, key = MeasureInThePlan.move, MeasureInThePlan.click, MeasureInThePlan.double, MeasureInThePlan.key
    drawn = MeasureInThePlan.drawn

    def make_two(self):
        """A measure on the ground (7 m) and one up the south pitch (4 m in plan), then Select."""
        self.click((30, 2)); self.double((37, 2))
        self.click((4, 1)); self.double((4, 5))
        self.assertEqual(len(self.tool.measures), 2)
        self.controller.setTool("select")
        self.app.processEvents()
        return [m.id for m in self.tool.measures]

    def pill(self, value):
        return next(p for p in self.drawn("measurePill") if p.property("value") == value)

    def pill_click(self, value, modifiers=Qt.NoModifier):
        pill = self.pill(value)
        centre = pill.mapToScene(pill.boundingRect().center()).toPoint()
        QTest.mouseMove(self.window, centre)
        QTest.mouseClick(self.window, Qt.LeftButton, modifiers, centre)
        self.app.processEvents()

    def chosen(self):
        return sorted(self.tool.selected)

    def test_a_click_on_a_pill_with_select_chooses_by_the_rule_of_the_selection(self):
        ground, pitch = self.make_two()
        self.pill_click("7.00 m")
        self.assertEqual(self.chosen(), [ground])
        self.assertEqual([m["selected"] for m in self.measure.done("plan")], [True, False])
        sel = QColor(self.controller.planColors["sel"])
        self.assertEqual(self.pill("7.00 m").property("ink"), sel)       # the measure chosen in the selection's colour
        self.assertNotEqual(self.pill("4.00 m").property("ink"), sel)
        # R609: the numbers of the measure chosen, then the gestures
        self.assertEqual(self.controller.hint, "7.00 m · Delete: remove · Ctrl+C: copy · Shift+click: add a measure · "
                                               "Esc: let go")
        self.pill_click("4.00 m")                                        # alone: only that one
        self.assertEqual(self.chosen(), [pitch])
        self.pill_click("7.00 m", Qt.ShiftModifier)                      # Shift adds
        self.assertEqual(self.chosen(), [ground, pitch])
        self.pill_click("7.00 m", Qt.ShiftModifier)                      # already there: it stays
        self.assertEqual(self.chosen(), [ground, pitch])
        self.pill_click("4.00 m", Qt.ControlModifier)                    # Ctrl takes away what is there...
        self.assertEqual(self.chosen(), [ground])
        self.pill_click("4.00 m", Qt.ControlModifier)                    # ...and adds what is not
        self.assertEqual(self.chosen(), [ground, pitch])
        self.key(Qt.Key_Escape)                                          # Esc lets them go
        self.assertEqual(self.chosen(), [])
        self.assertNotIn("Delete: remove · Ctrl+C: copy", self.controller.hint)
        self.pill_click("4.00 m")
        self.click((50, -10))                                            # a click elsewhere lets it go too
        self.assertEqual(self.chosen(), [])
        self.assertEqual(len(self.tool.measures), 2)
        self.assertFalse(self.warnings, self.warnings)

    def test_delete_removes_only_the_measures_chosen_and_otherwise_does_what_it_did(self):
        ground, pitch = self.make_two()
        self.controller.editor.select("building", "b1")
        self.controller._overlays()
        self.app.processEvents()
        self.pill_click("7.00 m")
        self.key(Qt.Key_Delete)
        self.assertEqual([m.id for m in self.tool.measures], [pitch])    # the measure chosen, not the shed selected
        self.assertEqual([b.id for b in self.controller.session.project.buildings], ["b1"])
        self.assertEqual(self.controller.session.selection, ("building", "b1"))
        self.key(Qt.Key_Delete)                                          # none chosen: Delete is the plan's again
        self.assertEqual(self.controller.session.project.buildings, [])
        self.assertEqual([m.id for m in self.tool.measures], [pitch])

    def test_ctrl_c_copies_the_text_of_the_measure_chosen(self):
        ground, pitch = self.make_two()
        clipboard = self.app.clipboard()
        clipboard.setText("before")
        self.key(Qt.Key_C, "\x03", Qt.ControlModifier)                   # none chosen: not the measures'
        self.assertEqual(clipboard.text(), "before")
        self.pill_click("4.00 m")
        self.key(Qt.Key_C, "\x03", Qt.ControlModifier)
        along = 4 / math.cos(math.radians(20))
        self.assertEqual(clipboard.text(), f"{along:.2f} m; in plan 4.00 m; height difference {4 * T20:.2f} m; 20.0°")
        self.assertEqual(clipboard.text(), "4.26 m; in plan 4.00 m; height difference 1.46 m; 20.0°")

    def test_with_measure_in_hand_a_click_on_a_pill_places_a_point(self):
        self.make_two()
        centre = self.pill("7.00 m").mapToScene(self.pill("7.00 m").boundingRect().center()).toPoint()
        self.controller.setTool("measure")
        self.app.processEvents()
        QTest.mouseMove(self.window, centre)
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, centre)
        self.app.processEvents()
        self.assertEqual((self.tool.state, len(self.tool.points), self.chosen()), ("measuring", 1, []))

    def test_never_in_the_project_and_gone_with_another_project(self):
        session = self.controller.session
        session.mark_saved()
        steps = (len(session.undo.steps), session.undo.index)
        ground, pitch = self.make_two()
        self.pill_click("7.00 m")
        self.key(Qt.Key_Delete)
        self.assertFalse(session.dirty())                                # the title takes no asterisk from it
        self.assertEqual((len(session.undo.steps), session.undo.index), steps)
        # they stay with another tool, in the Plant phase and back
        self.controller.setTool("measure"); self.controller.setPhase("plant"); self.controller.setPhase("model")
        self.assertEqual([m.id for m in self.tool.measures], [pitch])
        self.controller.setTool("measure")
        self.app.processEvents()
        self.click((10, -5))                                           # one in hand too: it goes as well
        self.assertEqual(self.tool.state, "measuring")
        session.take(shed(), None, saved=True)                           # what an open, a new or an import does
        self.app.processEvents()
        self.assertEqual((self.tool.measures, self.tool.points, self.measure.count), ([], [], 0))
        self.assertEqual(self.drawn("measurePill"), [])
        self.assertFalse(self.warnings, self.warnings)


class SnapsAndConstraints(unittest.TestCase):
    """Package 5 on the plan (Daniel's choice 2): Shift + right button opens the snaps' menu, the program's menu, and
    the snap chosen holds for the point being placed, then they are all back; the arrows (Right East, Left North, Up
    vertical), Down (perpendicular, then parallel to the edge passed over), Shift (the direction held) and a number with
    Enter reach the tool from the window, the small pill beside the pointer says the constraint, and the plan does not
    move under the arrows while a point is placed. The logic is the core's (tests/nucleo/test_measure_tool.py)."""
    project = staticmethod(shed)
    setUpClass = classmethod(MeasureInThePlan.setUpClass.__func__)
    setUp, close, frame, at = MeasureInThePlan.setUp, MeasureInThePlan.close, MeasureInThePlan.frame, MeasureInThePlan.at
    move, click, double, key = MeasureInThePlan.move, MeasureInThePlan.click, MeasureInThePlan.double, MeasureInThePlan.key
    drawn, pills = MeasureInThePlan.drawn, MeasureInThePlan.pills

    def held_move(self, point, modifiers=Qt.ShiftModifier):
        """A step of the pointer with a modifier held (QTest.mouseMove gives none)."""
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QMouseEvent
        at = QPointF(self.at(point))
        self.app.sendEvent(self.window, QMouseEvent(QEvent.MouseMove, at, at, at, Qt.NoButton, Qt.NoButton, modifiers))
        self.app.processEvents()

    def target(self):
        return [round(c, 6) + 0.0 for c in self.tool.target.point[:2]]

    def menu(self):
        return self.window.findChild(QObject, "measureSnapMenu")

    def open_snaps(self, point):
        self.move(point)
        QTest.mouseClick(self.window, Qt.RightButton, Qt.ShiftModifier, self.at(point))
        self.app.processEvents()
        self.assertTrue(_setup.wait_until(self.app, lambda: self.menu().property("opened")))
        return self.menu()

    def entries(self):
        """The menu's commands from the top: (kind, text, checked)."""
        found = [e for e in self.window.findChildren(QObject) if e.objectName().startswith("measureSnap-")]
        found.sort(key=lambda e: e.mapToScene(e.boundingRect().topLeft()).y())
        return [(e.objectName().removeprefix("measureSnap-"), e.property("text"), e.property("checked")) for e in found]

    def choose(self, kind):
        entry = self.window.findChild(QObject, "measureSnap-" + kind)
        centre = entry.mapToScene(entry.boundingRect().center()).toPoint()
        QTest.mouseMove(self.window, centre)
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, centre)
        self.app.processEvents()
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.menu().property("opened")))

    def beside(self, name):
        return [p.property("value") for p in self.drawn(name)]

    def test_shift_and_the_right_button_open_the_snaps_menu_for_one_point(self):
        self.move((24.3, 12.2))
        self.assertEqual([m.property("kind") for m in self.drawn("measurePointer")], ["vertex"])
        self.assertIn("Shift+right-click: snaps", self.plan.property("statusText"))     # the hint row names it
        menu = self.open_snaps((24.3, 12.2))
        self.assertIn("Menu", kinds_of(menu))                                             # the program's menu
        self.assertIn("MenuEntry", kinds_of(self.window.findChild(QObject, "measureSnap-vertex")))   # its entries
        self.assertFalse(self.window.findChild(QObject, "planContextMenu").property("opened"))    # not the plan's menu
        self.assertEqual(self.entries(), [("vertex", "Vertex", False), ("midpoint", "Midpoint", False),
                                          ("edge", "Edge", False), ("intersection", "Intersection", False),
                                          ("perpendicular", "Perpendicular", False), ("none", "None", False)])
        self.assertTrue(self.window.findChild(QObject, "measureSnapRule"))                 # «None» apart, under a rule
        self.choose("none")
        self.assertEqual((self.measure.snap, self.tool.state), ("none", "idle"))
        self.move((24.3, 12.2))
        self.assertEqual([m.property("kind") for m in self.drawn("measurePointer")], ["free"])
        self.assertEqual(self.beside("measureRequest"), ["None"])                         # the pill says it
        self.click((24.3, 12.2))                                                           # the point where clicked
        self.assertLess(math.dist(self.tool.points[0].point[:2], (24.3, 12.2)), 0.05)
        self.assertEqual(self.measure.snap, "")                                            # then all back
        self.assertEqual(self.beside("measureRequest"), [])
        self.move((0.2, 11.8))
        self.assertEqual([m.property("kind") for m in self.drawn("measurePointer")], ["vertex"])
        self.assertFalse(self.warnings, self.warnings)

    def test_the_snap_chosen_is_the_only_one_and_is_checked(self):
        self.click((30, 6))
        self.open_snaps((30, 6))
        self.choose("perpendicular")
        self.move((24.2, 3))                                       # over the shed's east side: the foot from (30, 6)
        self.assertEqual(self.target(), [24, 6])
        self.assertEqual(self.tool.target.kind, "perpendicular")
        self.click((24.2, 3))
        self.assertTrue(near([p.point[:2] for p in self.tool.points], [(30, 6), (24, 6)]), self.tool.points)
        self.open_snaps((24, 6))
        self.choose("midpoint")
        self.open_snaps((24, 6))
        self.assertEqual([k for k, _, checked in self.entries() if checked], ["midpoint"])
        self.key(Qt.Key_Escape)                                    # Esc closes the menu, the measure stays
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.menu().property("opened")))
        self.assertEqual(len(self.tool.points), 2)
        self.move((23.6, 0.3))                                     # near the corner (24, 0): only midpoints asked
        self.assertNotEqual(self.tool.target.kind, "vertex")
        self.move((12.3, 0.2))
        self.assertEqual((self.target(), self.tool.target.kind), ([12, 0], "midpoint"))

    def test_the_arrows_give_the_axes_and_the_plan_stays_where_it_is(self):
        self.click((30, 0))
        view = [self.plan.property(k) for k in ("zoom", "panX", "panY", "bearing")]
        self.move((31, 6))
        self.key(Qt.Key_Left)                                      # North
        self.assertEqual((self.tool.constraint, self.target()), ("north", [30, 6]))
        self.assertEqual(self.beside("measureConstraint"), ["North"])
        self.key(Qt.Key_Right)                                     # East
        self.assertEqual((self.tool.constraint, self.target()), ("east", [31, 0]))
        self.assertEqual(self.beside("measureConstraint"), ["East"])
        self.key(Qt.Key_Up)                                        # vertical
        self.assertEqual(self.tool.constraint, "up")
        self.assertEqual(self.beside("measureConstraint"), ["Vertical"])
        self.key(Qt.Key_Up)                                        # the same arrow again: free
        self.assertIsNone(self.tool.constraint)
        self.assertEqual(self.beside("measureConstraint"), [])
        self.assertEqual([self.plan.property(k) for k in ("zoom", "panX", "panY", "bearing")], view)
        self.key(Qt.Key_Right)
        self.key(Qt.Key_5, "5")                                    # a number along the axis, Enter: as a click
        self.assertEqual(self.beside("measureTyped"), ["length: 5_"])
        self.key(Qt.Key_Return)
        self.assertTrue(near([p.point[:2] for p in self.tool.points], [(30, 0), (35, 0)]), self.tool.points)
        self.assertIsNone(self.tool.constraint)                    # the arrow is free again after the point

    def test_down_is_perpendicular_then_parallel_to_the_edge_passed_over(self):
        self.click((30, 0))
        self.move((36, 2))
        self.key(Qt.Key_Down)                                      # no edge passed over yet: it says so
        self.assertIsNone(self.tool.constraint)
        self.assertIn("no reference edge", self.plan.property("statusText"))
        self.move((24.2, 3))                                       # over the shed's east side (North-South)
        self.move((36, 9))
        self.key(Qt.Key_Down)
        self.assertEqual((self.tool.constraint, self.target()), ("perpendicular", [36, 0]))
        self.assertEqual(self.beside("measureConstraint"), ["Perpendicular"])
        self.key(Qt.Key_Down)
        self.assertEqual((self.tool.constraint, self.target()), ("parallel", [30, 9]))
        self.assertEqual(self.beside("measureConstraint"), ["Parallel"])
        self.key(Qt.Key_Down)
        self.assertIsNone(self.tool.constraint)

    def test_shift_holds_the_direction(self):
        self.click((30, 0))
        self.move((36, 6))                                         # 45°
        self.held_move((36.5, 6.5))                    # Shift pressed on the way (Qt gives no move for the same point)
        self.assertEqual(self.beside("measureConstraint"), ["Direction held"])
        self.held_move((40, 2))                                    # elsewhere, Shift held: on the 45° line
        self.assertTrue(near([self.tool.target.point[:2]], [(36, 6)]), self.tool.target)
        # Shift let go: free at once, the pointer still where it was
        self.app.sendEvent(self.window, QKeyEvent(QEvent.KeyRelease, Qt.Key_Shift, Qt.NoModifier))
        self.app.processEvents()
        self.assertIsNone(self.tool.held)
        self.assertEqual(self.beside("measureConstraint"), [])
        self.assertLess(math.dist(self.tool.target.point[:2], (40, 2)), 0.9)


class LightWork(unittest.TestCase):
    """The window stays free: no call of the tool over 5 ms while the pointer moves with a point placed."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def run_moves(self, extra):
        case = MeasureInThePlan("test_a_simple_measure_is_a_click_and_a_double_click")
        case.app = self.app
        case.project = staticmethod(lambda: shed(extra))
        case.setUp()
        try:
            segments = len(case.controller.measuring.probe.snapper.segments)
            case.click((30, 2)); case.double((37, 2))            # a measure made, drawn while the pointer moves
            case.click((2, 3))                                   # a point placed on the pitch
            path = [(2 + 30 * k / 250, 3 + 5 * math.sin(k / 9)) for k in range(250)]
            path += [(40 + (k % 10) * 7 + 2.5 + (k % 3), -20 + (k // 10) * 7) for k in range(min(extra, 100))]
            with window_stays_free(case.measure, call_ms=5, beat_ms=None) as seen:
                for point in path:
                    case.move(point)
            print(f"\nmeasure, {segments} reference edges, {len(path)} moves: {seen}")
            self.assertGreaterEqual(seen.calls, 200)
            self.assertFalse(case.warnings, case.warnings)
        finally:
            case.doCleanups()

    @timed('no call of the window over 5 ms')
    def test_a_small_project(self):
        self.run_moves(0)

    @timed('no call of the window over 5 ms')
    def test_a_project_of_hundreds_of_edges(self):
        self.run_moves(80)


if __name__ == "__main__":
    unittest.main()
