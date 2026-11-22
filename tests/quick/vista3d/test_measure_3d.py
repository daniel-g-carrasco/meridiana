"""The measuring tool in the 3D view (study 46, package 4; state of r34-righello sections 2.5 and 2.6): the gestures given
to the real window, off screen, and what the view draws of them, read from its items.

Two clicks on two corners of the shed give its true length, exact (no «≈»); a free point on a pitch is «circa»; the
large number is the true length and the line under it the length in plan, the height difference and the slope
(Daniel's choice 4). With a point placed the arrows are the tool's and the camera does not move. While the pointer
moves nothing is looked for: no probe, no pick, no call of the bridge; at rest the point is found. A measure begun in
the plan ends in the 3D view: the bridge is one. Off screen Qt Quick 3D neither draws nor picks: the probe casts the
ray on the project's triangles itself (app/view/scene_probe.py), so these gestures are the real ones.
"""
from __future__ import annotations

import math
import re
import tempfile
import time
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtTest import QTest

from meridiana import i18n
from meridiana.core.model import model
from quick.aiuti.finestra_libera import window_stays_free
from ._fidelity_support import data, js
from quick.aiuti.tempi import timed

setUpModule = _setup.keep_global_state
T20 = math.tan(math.radians(20))
RIDGE = 6 + 6 * T20
LEFT = Qt.MouseButton.LeftButton
NONE = Qt.MouseButton.NoButton


def shed():
    p = model.Project(name="Measure in the 3D view")
    p.buildings.append(model.Building(id="b1", name="Shed", height=6, footprint=[[0, 0], [24, 0], [24, 12], [0, 12]],
                                      roof=model.Roof(type="gable", tilt=20)))
    return p


def qt(p):
    """(East, North, height) as the view's axes."""
    return [p[0], p[2], -p[1]]


def numbers(text):
    return [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", text or "")]


def items(root):
    out, pending = [], [root]
    while pending:
        item = pending.pop()
        out.append(item)
        pending.extend(item.childItems())
    return out


class MeasureInThe3DView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        from meridiana.gui.application import create_app
        create_app()

    def setUp(self):
        from meridiana.gui.application import QuickWindow
        i18n.setup("en")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.host = QuickWindow(shed(), Path(self.tmp.name), real_views=True)
        self.window = self.host.window
        self.window.show()
        self.window.setProperty("viewMode", "3d")
        self.assertTrue(_setup.wait_until(self.app, lambda: self.window.findChild(QObject, "viewport3d") is not None))
        self.view = self.window.findChild(QObject, "viewport3d")
        self.view.setProperty("reducedMotion", True)
        # the scene made, framed once, and the camera left where it is (a scene made later frames it again)
        scene = self.host.scene
        self.assertTrue(_setup.wait_until(self.app, lambda: len(getattr(scene, "triangles", ((),))[0]) > 0
                                          and not scene.drawing))
        js(self.view, "fitScene()")
        self.view.setProperty("userMoved", True)
        self.bridge = self.host.measure
        self.host.plan.setTool("measure")
        self.assertTrue(_setup.wait_until(self.app, lambda: self.view.property("measuring")))
        self.layer = self.view.findChild(QObject, "sceneMeasures")
        self.view.forceActiveFocus()
        # the window's panels settle after it shows (the 3D view went from 213 to 468 px wide some 200 ms later, 14/11):
        # a gesture sent before at the points of the smaller view hit something else under load
        seen = {"size": None, "since": time.monotonic()}

        def settled():                                  # the same size for 400 ms
            size = (self.view.width(), self.view.height())
            if size != seen["size"]:
                seen.update(size=size, since=time.monotonic())
            return time.monotonic() - seen["since"] > 0.4

        self.assertTrue(_setup.wait_until(self.app, settled))

    def tearDown(self):
        warnings = self.host.warnings[:]
        self.host.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.assertFalse(warnings)

    # -- gestures -------------------------------------------------------------------------------------------------

    def screen(self, point):
        at = data(self.view, f"projectPoint({qt(point)})")
        self.assertTrue(0 < at[0] < self.view.width() and 0 < at[1] < data(self.view, "sceneHeight"), at)
        return at

    def mouse(self, kind, x, y, button=NONE, buttons=NONE):
        at = self.view.mapToScene(QPointF(x, y))
        QCoreApplication.sendEvent(self.window, QMouseEvent(kind, at, at, at, button, buttons,
                                                            Qt.KeyboardModifier.NoModifier))

    def click(self, point):
        x, y = self.screen(point)
        revision = self.bridge.revision
        self.mouse(QEvent.Type.MouseMove, x, y)
        self.mouse(QEvent.Type.MouseButtonPress, x, y, LEFT, LEFT)
        self.mouse(QEvent.Type.MouseButtonRelease, x, y, LEFT)
        self.assertTrue(_setup.wait_until(self.app, lambda: self.bridge.revision != revision))

    def double(self, point):
        """A double click as Qt gives it: a click, then a press, the double click and a release on the same point."""
        self.click(point)
        x, y = self.screen(point)
        self.mouse(QEvent.Type.MouseButtonPress, x, y, LEFT, LEFT)
        self.mouse(QEvent.Type.MouseButtonDblClick, x, y, LEFT, LEFT)
        self.mouse(QEvent.Type.MouseButtonRelease, x, y, LEFT)
        self.app.processEvents()

    def key(self, key, text=""):
        for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            QCoreApplication.sendEvent(self.window, QKeyEvent(kind, key, Qt.KeyboardModifier.NoModifier, text))
        self.app.processEvents()

    def pills(self):
        return [item for item in items(self.layer) if item.objectName() == "measurePill" and item.isVisible()]

    # -- what the tool does in the 3D view -------------------------------------------------------------------------

    def test_two_corners_give_the_true_length_exact(self):
        a, b = (0, 0, 6), (24, 6, RIDGE)
        self.click(a)
        self.assertTrue(self.bridge.inHand)
        self.rest(b)
        # R609: the length in plan, the height difference and the slope are in the hint bar, the drawing has the number
        self.assertTrue(_setup.wait_until(self.app, lambda: self.bridge.numbers != ""))
        hint = numbers(self.bridge.numbers)
        span = (math.dist(a, b), math.dist(a[:2], b[:2]), b[2] - a[2])
        self.assertAlmostEqual(hint[0], round(span[0], 2), places=2)
        self.assertAlmostEqual(hint[1], round(span[1], 2), places=2)
        self.assertAlmostEqual(hint[2], round(span[2], 2), places=2)
        self.double(b)
        self.assertFalse(self.bridge.inHand)              # the double click ended it and began no other
        self.assertEqual(self.bridge.count, 1)
        made = self.bridge.tool.measures[-1]
        self.assertEqual([p.kind for p in made.points], ["vertex", "vertex"])
        self.assertTrue(all(p.exact for p in made.points))
        span = made.spans()[0]
        self.assertAlmostEqual(span.length, math.dist(a, b), places=4)
        self.assertTrue(_setup.wait_until(self.app, lambda: len(self.pills()) == 1))
        pill = self.pills()[0]
        self.assertFalse(pill.property("approx"))
        self.assertNotIn("≈", pill.property("value"))
        # Daniel's choice 4: in the 3D view the number is the true length (R609: alone, written along the span as the
        # screen shows it, never upside down)
        self.assertEqual(pill.property("value"), f"{span.length:.2f} m")
        sa, sb = self.screen(a), self.screen(b)
        angle = math.degrees(math.atan2(sb[1] - sa[1], sb[0] - sa[0]))
        upright = angle - 180 if angle >= 90 else angle + 180 if angle < -90 else angle
        self.assertAlmostEqual(pill.property("rotation"), upright, delta=2)
        kinds, meta = [], pill.metaObject()
        while meta is not None:
            kinds.append(meta.className().split("_QML")[0])
            meta = meta.superClass()
        self.assertIn("SpanLabel", kinds)                               # the plan's words, the one component

    def test_a_path_has_its_total_in_a_pill_at_its_end_r618(self):
        """R618: the plan's rule in the 3D view, the one component: the last span's number alone, the total a pill at
        the path's end; no word or pill over another."""
        for p in ((0, 0, 6), (24, 0, 6)):
            self.click(p)
        self.click((24, 6, RIDGE))
        self.key(Qt.Key.Key_Return)
        self.assertEqual(self.bridge.count, 1)
        self.mouse(QEvent.Type.MouseMove, 5, 5)                         # the pointer off the path's end
        totals = lambda: [i for i in items(self.layer) if i.objectName() == "measureTotal" and i.isVisible()]  # noqa: E731
        self.assertTrue(_setup.wait_until(self.app, lambda: len(totals()) == 1))
        self.assertTrue(totals()[0].property("value").startswith("Total "))
        self.assertNotIn("Total", " ".join(p.property("value") for p in self.pills()))
        end = self.screen((24, 6, RIDGE))
        box = totals()[0].mapRectToItem(self.view, totals()[0].boundingRect())
        dx = max(box.left() - end[0], 0, end[0] - box.right())
        dy = max(box.top() - end[1], 0, end[1] - box.bottom())
        self.assertLess(math.hypot(dx, dy), 12)                         # at the end, clear of its mark
        from shapely.geometry import Polygon
        shown = [Polygon([(q.x(), q.y()) for q in (w.mapToItem(self.view, QPointF(x, y)) for x, y in
                          ((0, 0), (w.width(), 0), (w.width(), w.height()), (0, w.height())))])
                 for w in self.pills() + totals()]                         # turned as drawn
        for i, r in enumerate(shown):
            for s in shown[i + 1:]:
                self.assertFalse(r.intersects(s), (r.bounds, s.bounds, data(self.layer, "JSON.stringify(places)"),
                                                   [(w.property("value"), w.property("mode"),
                                                     w.property("x"), w.property("y"), w.property("rotation"))
                                                    for w in self.pills()]))

    def test_a_free_point_on_a_pitch_is_circa(self):
        # from a corner at the ground: a point on a wall, so the second one is not held in the pitch's plane (that
        # point, the ray met with the plane of an exact point, is exact: measure_tool._resolve)
        self.click((0, 0, 0))
        self.click((12, 3, 6 + 3 * T20))
        self.key(Qt.Key.Key_Return)
        made = self.bridge.tool.measures[-1]
        self.assertEqual(made.points[1].kind, "face")
        self.assertFalse(made.points[1].exact)
        self.assertTrue(_setup.wait_until(self.app, lambda: len(self.pills()) == 1))
        self.assertTrue(self.pills()[0].property("approx"))

    def test_the_arrows_are_the_tools_while_a_point_is_placed(self):
        camera = data(self.view, "cameraState")
        self.key(Qt.Key.Key_Left)                          # at rest: not the tool's
        self.assertIsNone(self.bridge.tool.constraint)
        self.click((0, 0, 6))
        camera = data(self.view, "cameraState")
        for key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.key(key)
            self.assertEqual(data(self.view, "cameraState"), camera)
        self.key(Qt.Key.Key_Right)
        self.assertEqual(self.bridge.tool.constraint, "east")
        self.key(Qt.Key.Key_Escape)                        # Esc takes the measure in hand back, then the tool
        self.assertFalse(self.bridge.inHand)
        self.key(Qt.Key.Key_Escape)
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.view.property("measuring")))
        self.assertEqual(self.host.plan.tool, "select")

    @timed('no call of the window over its few ms')
    def test_nothing_is_looked_for_while_the_pointer_moves(self):
        self.click((0, 0, 6))
        x, y = self.screen((24, 0, 6))
        asked, picks = self.host.parts.controllers["sceneControls"].measure.asked, self.view.property("picks")
        with window_stays_free(self.bridge, call_ms=5, beat_ms=None) as seen:
            for i in range(200):                       # no turn of the events between them: no timer can fire
                self.mouse(QEvent.Type.MouseMove, x - 60 + (i % 50), y + (i % 7))
            calls = self.bridge.stats()["calls"]
            self.assertTrue(self.view.property("measureFollows"))
            self.assertTrue(self.layer.findChild(QObject, "measureElastic").isVisible())
        print(f"\n200 steps of the pointer with a point placed: {seen}")
        self.assertEqual(calls, 0)
        self.assertEqual(self.host.parts.controllers["sceneControls"].measure.asked, asked)
        self.assertEqual(self.view.property("picks"), picks)
        # at rest the point is found and the span has its numbers
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.view.property("measureFollows")))
        self.assertEqual(self.host.parts.controllers["sceneControls"].measure.asked, asked + 1)
        self.assertTrue(_setup.wait_until(self.app, lambda: any(p.property("value") for p in self.pills())))

    # -- package 5: the snaps' menu and the constraints, from the view's gestures ---------------------------------

    def rest(self, point, modifiers=Qt.KeyboardModifier.NoModifier):
        """The pointer on `point` and still: the view finds the point under it (Theme.motion.REST later)."""
        x, y = self.screen(point)
        probe = self.host.parts.controllers["sceneControls"].measure
        asked = probe.asked
        at = self.view.mapToScene(QPointF(x, y))
        QCoreApplication.sendEvent(self.window, QMouseEvent(QEvent.Type.MouseMove, at, at, at, NONE, NONE, modifiers))
        self.assertTrue(_setup.wait_until(self.app, lambda: probe.asked > asked
                                          and not self.view.property("measureFollows")))
        self.app.processEvents()
        QTest.qWait(1)
        self.assertTrue(_setup.wait_until(self.app, lambda: not probe.annotationPending))

    def beside(self, name):
        return [i.property("value") for i in items(self.layer) if i.objectName() == name and i.isVisible()]

    def said(self, start):
        """The constraint's pill begins with `start` (on a pitch it adds «on the pitch plane»)."""
        return any(v.startswith(start) for v in self.beside("measureConstraint"))

    def key_up(self, key):
        QCoreApplication.sendEvent(self.window, QKeyEvent(QEvent.Type.KeyRelease, key, Qt.KeyboardModifier.NoModifier))
        self.app.processEvents()

    def snap_menu(self):
        return self.view.findChild(QObject, "measureSnapMenu")

    def choose(self, kind):
        entry = self.view.findChild(QObject, "measureSnap-" + kind)
        at = entry.mapToScene(entry.boundingRect().center())
        for kind_, button, buttons in ((QEvent.Type.MouseMove, NONE, NONE), (QEvent.Type.MouseButtonPress, LEFT, LEFT),
                                       (QEvent.Type.MouseButtonRelease, LEFT, NONE)):
            QCoreApplication.sendEvent(self.window, QMouseEvent(kind_, at, at, at, button, buttons,
                                                                Qt.KeyboardModifier.NoModifier))
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.snap_menu().property("opened")))

    def target(self):
        return [round(c, 3) + 0.0 for c in self.bridge.tool.target.point]

    def test_shift_and_the_right_button_open_the_snaps_menu_for_one_point(self):
        self.rest((0, 0, 6))
        self.assertEqual(self.bridge.tool.target.kind, "vertex")
        x, y = self.screen((0, 0, 6))
        at = self.view.mapToScene(QPointF(x, y))
        shift, right = Qt.KeyboardModifier.ShiftModifier, Qt.MouseButton.RightButton
        QCoreApplication.sendEvent(self.window, QMouseEvent(QEvent.Type.MouseButtonPress, at, at, at, right, right, shift))
        QCoreApplication.sendEvent(self.window, QMouseEvent(QEvent.Type.MouseButtonRelease, at, at, at, right, NONE, shift))
        self.assertTrue(_setup.wait_until(self.app, lambda: self.snap_menu().property("opened")))
        self.assertFalse(self.view.findChild(QObject, "sceneContextMenu").property("opened"))    # not the view's menu
        texts = [self.view.findChild(QObject, "measureSnap-" + k).property("text")
                 for k in ("vertex", "midpoint", "edge", "intersection", "perpendicular", "none")]
        self.assertEqual(texts, ["Vertex", "Midpoint", "Edge", "Intersection", "Perpendicular", "None"])
        self.choose("none")
        self.assertEqual(self.bridge.snap, "none")
        self.assertNotEqual(self.bridge.tool.target.kind, "vertex")    # found again at once without the snaps
        self.assertTrue(_setup.wait_until(self.app, lambda: self.beside("measureRequest") == ["None"]))
        self.click((0, 0, 6))
        self.assertNotEqual(self.bridge.tool.points[0].kind, "vertex")
        self.assertEqual(self.bridge.snap, "")                         # one point only, then all back
        self.rest((24, 0, 0))                                           # a corner at the foot of a wall (on the
        # pitch the point would keep to the plane of the first one, a free point: measure_tool._resolve)
        self.assertEqual(self.bridge.tool.target.kind, "vertex")

    def test_the_arrows_and_a_number_reach_the_tool_and_the_pill_says_the_axis(self):
        self.click((0, 0, 6))
        self.rest((12, 3, 6 + 3 * T20))
        self.key(Qt.Key.Key_Up)                                         # vertical: on the vertical of the corner
        self.assertEqual(self.bridge.tool.constraint, "up")
        self.assertEqual(self.target()[:2], [0, 0])
        self.assertTrue(_setup.wait_until(self.app, lambda: self.beside("measureConstraint") == ["Vertical"]))
        self.key(Qt.Key.Key_Right)                                      # East: along the eave
        self.assertEqual(self.bridge.tool.constraint, "east")
        self.assertEqual(self.target()[1:], [0, 6])
        self.assertTrue(_setup.wait_until(self.app, lambda: self.beside("measureConstraint") == ["East"]))
        self.key(Qt.Key.Key_Left)                                       # North
        self.assertEqual((self.bridge.tool.constraint, self.target()[0], self.target()[2]), ("north", 0, 6))
        self.key(Qt.Key.Key_Right)
        self.key(Qt.Key.Key_5, "5")
        self.assertTrue(_setup.wait_until(self.app, lambda: self.beside("measureTyped") == ["length: 5_"]))
        self.key(Qt.Key.Key_Return)                                     # 5 m east, the true length in the 3D view
        self.assertEqual([round(c, 4) for c in self.bridge.tool.points[-1].point], [5, 0, 6])
        self.assertIsNone(self.bridge.tool.constraint)

    def test_down_and_shift_reach_the_tool(self):
        self.click((0, 0, 6))
        self.rest((12, 0, 6))                                           # over the eave: the reference edge
        self.rest((12, 3, 6 + 3 * T20))
        self.key(Qt.Key.Key_Down)
        self.assertEqual(self.bridge.tool.constraint, "perpendicular")
        self.assertTrue(_setup.wait_until(self.app, lambda: self.said("Perpendicular")), self.beside("measureConstraint"))
        self.key(Qt.Key.Key_Down)
        self.assertEqual(self.bridge.tool.constraint, "parallel")
        self.assertTrue(_setup.wait_until(self.app, lambda: self.said("Parallel")), self.beside("measureConstraint"))
        self.key(Qt.Key.Key_Down)
        self.assertIsNone(self.bridge.tool.constraint)
        self.rest((13, 3, 6 + 3 * T20), Qt.KeyboardModifier.ShiftModifier)      # Shift: the direction held
        self.assertIsNotNone(self.bridge.tool.held)
        self.assertTrue(_setup.wait_until(self.app, lambda: self.said("Direction held")), self.beside("measureConstraint"))
        self.key_up(Qt.Key.Key_Shift)                                   # let go: free at once
        self.assertIsNone(self.bridge.tool.held)
        # only the pitch's plane is said now, if anything
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.said("Direction held")), self.beside("measureConstraint"))

    def test_the_height_mode_from_the_views_gestures(self):
        self.bridge.setMode("height")
        self.click((0, 0, 0))                                           # the foot, the shed's corner on the ground
        self.rest((12, 6, RIDGE))                                       # the pointer over the ridge
        self.assertEqual(self.target()[:2], [0, 0])                     # the top on the vertical of the foot
        x, y = self.screen((12, 6, RIDGE))
        self.mouse(QEvent.Type.MouseButtonPress, x, y, LEFT, LEFT)
        self.mouse(QEvent.Type.MouseButtonRelease, x, y, LEFT)
        self.assertTrue(_setup.wait_until(self.app, lambda: self.bridge.count == 1))
        made = self.bridge.tool.measures[-1]
        self.assertEqual((made.mode, len(made.points)), ("height", 2))
        self.assertTrue(_setup.wait_until(self.app, lambda: len(self.pills()) == 1))
        rise = abs(made.spans()[0].rise)
        self.assertAlmostEqual(numbers(self.pills()[0].property("value"))[0], round(rise, 2), places=2)
        self.assertEqual(self.pills()[0].property("below"), "")           # R609: one line, the rest in the hint bar

    def off_the_vertical(self, foot, end):
        """How far (pixels) the screen point `end` is from the screen's image of the vertical through `foot`."""
        a, b = self.screen(foot), self.screen((foot[0], foot[1], foot[2] + 4))
        dx, dy = b[0] - a[0], b[1] - a[1]
        return abs((end[0] - a[0]) * dy - (end[1] - a[1]) * dx) / math.hypot(dx, dy)

    def elastic_end(self):
        ends = self.layer.findChild(QObject, "measureElastic").property("ends")
        ends = ends.toVariant() if hasattr(ends, "toVariant") else ends
        return [ends[-1].x(), ends[-1].y()]

    def test_the_height_stays_on_the_foots_vertical_wherever_the_pointer_goes(self):
        """R35 (Daniel 14/11: «non mantiene perfettamente la misura sull'asse Z, ma va anche in obliquo»): after the
        foot, while the pointer moves (no point looked for) the span drawn keeps to the foot's vertical, and the line to
        the pointer is the dotted reference; at rest on a far vertex the top takes its height and the large number is
        the height difference. Also with Shift, after an arrow, with a number being typed."""
        self.bridge.setMode("height")
        foot = (0, 0, 0)
        self.click(foot)                                                # the shed's corner on the ground
        far = (24, 6, RIDGE)                                            # the ridge's east end, far from the vertical
        x, y = self.screen(far)
        self.assertGreater(self.off_the_vertical(foot, (x, y)), 100)   # the pointer well off the vertical
        self.mouse(QEvent.Type.MouseMove, x, y)                          # moving: no point looked for
        self.assertTrue(self.view.property("measureFollows"))
        self.assertLess(self.off_the_vertical(foot, self.elastic_end()), 1.0)
        reference = self.layer.findChild(QObject, "measureReference")
        self.assertTrue(reference.isVisible())                          # from the pointer to the span's end, dotted
        self.rest(far)
        self.assertEqual(self.target()[:2], [0, 0])
        self.assertAlmostEqual(self.bridge.tool.target.point[2], RIDGE, places=4)
        self.assertLess(self.off_the_vertical(foot, self.elastic_end()), 1.0)
        self.assertTrue(reference.isVisible())                          # from the vertex to the top
        pointer = self.layer.findChild(QObject, "measurePointer")
        self.assertEqual(pointer.property("kind"), "vertex")            # the snap's mark on the vertex, not the top
        centre, (x, y) = pointer.property("centre"), self.screen(far)
        self.assertLess(math.hypot(centre.x() - x, centre.y() - y), 1.5, (centre, x, y))
        self.assertTrue(_setup.wait_until(self.app, lambda: any(p.property("value") for p in self.pills())))
        self.assertIn(f"{RIDGE:.2f}", [p.property("value") for p in self.pills()][0])
        # Shift, an arrow, a number being typed: still on the vertical
        self.rest((12, 3, 6 + 3 * T20), Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(self.target()[:2], [0, 0])
        self.key(Qt.Key.Key_Right)
        self.rest((20, 0, 6))
        self.assertEqual(self.target()[:2], [0, 0])
        self.key(Qt.Key.Key_3, "3")
        x, y = self.screen((6, 0, 6))
        self.mouse(QEvent.Type.MouseMove, x, y)
        self.assertLess(self.off_the_vertical(foot, self.elastic_end()), 1.0)
        self.key(Qt.Key.Key_Return)                                     # 3 m up from the foot
        made = self.bridge.tool.measures[-1]
        self.assertEqual([[round(c, 4) for c in p.point] for p in made.points], [[0, 0, 0], [0, 0, 3]])

    def test_f8_in_the_3d_view_switches_the_plans_ortho_and_the_ruler_follows(self):
        """Daniel 14/11/2026: one setting, the plan's Ortho (F8, the window's shortcut), for drawing and measuring; the
        ruler's 15° guides follow it from the 3D view too."""
        plan = self.host.plan
        before = plan.drawing.orthogonal
        self.assertEqual(self.bridge.polar, before)
        self.view.forceActiveFocus()
        QTest.keyClick(self.window, Qt.Key.Key_F8)                      # through the window's shortcuts
        self.assertTrue(_setup.wait_until(self.app, lambda: plan.drawing.orthogonal != before))
        self.assertEqual((self.bridge.polar, plan.orthoEnabled), (not before, not before))
        QTest.keyClick(self.window, Qt.Key.Key_F8)
        self.assertTrue(_setup.wait_until(self.app, lambda: plan.drawing.orthogonal == before))
        self.assertEqual(self.bridge.polar, before)

    def test_the_3d_view_shows_the_tools_cross_and_the_snaps_mark_as_the_plan(self):
        """Daniel 14/11/2026: «sul 2d il puntatore diventa una croce e mi mostra un quadratino in centro, ma sul 3d non
        vedo nessun cambio». With Measure in hand the 3D view's pointer is the plan's cross (one rule, Controls/
        ToolCursor.js), before any click; at rest on the model the snap's mark is under it (square on a vertex, rhombus
        on a face); Select gives the arrow back."""
        scene_input = self.view.findChild(QObject, "sceneInput")
        plan_input = self.window.findChild(QObject, "planMouse")
        self.assertEqual(scene_input.property("cursorShape"), Qt.CursorShape.CrossCursor)
        if plan_input is not None:
            self.assertEqual(scene_input.property("cursorShape"), plan_input.property("cursorShape"))
        pointer = self.layer.findChild(QObject, "measurePointer")
        self.rest((0, 0, 6))                                            # a corner: the square
        self.assertTrue(pointer.isVisible())
        self.assertEqual(pointer.property("kind"), "vertex")
        self.rest((12, 3, 6 + 3 * T20))                                 # the pitch: the face's rhombus
        self.assertTrue(pointer.isVisible())
        self.assertEqual(pointer.property("kind"), "face")
        # the sky (nothing under the ray, the probe gives None) takes the mark away: tests/nucleo/test_measure_tool.py;
        # in this framing even the view's top edge looks at the ground, a point at height 0
        self.assertEqual(scene_input.property("cursorShape"), Qt.CursorShape.CrossCursor)
        self.host.plan.setTool("select")
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.view.property("measuring")))
        self.assertEqual(scene_input.property("cursorShape"), Qt.CursorShape.ArrowCursor)

    def test_with_select_a_click_on_a_pill_chooses_the_measure_and_delete_removes_it(self):
        """Study 46, 3.6 in the 3D view too: the pills of the measures made take a click with Select (they lay under
        the view's input before); Delete removes only the measure chosen, a click elsewhere lets it go."""
        self.click((0, 0, 6))
        self.double((24, 0, 6))
        self.host.plan.setTool("select")
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.view.property("measuring")))
        self.assertTrue(_setup.wait_until(self.app, lambda: len(self.pills()) == 1))

        def press(at):
            for kind, button, buttons in ((QEvent.Type.MouseMove, NONE, NONE), (QEvent.Type.MouseButtonPress, LEFT, LEFT),
                                          (QEvent.Type.MouseButtonRelease, LEFT, NONE)):
                QCoreApplication.sendEvent(self.window, QMouseEvent(kind, at, at, at, button, buttons,
                                                                    Qt.KeyboardModifier.NoModifier))
            self.app.processEvents()

        pill = self.pills()[0]
        press(pill.mapToScene(pill.boundingRect().center()))
        self.assertEqual(self.bridge.chosen, 1)
        press(self.view.mapToScene(QPointF(self.view.width() * 0.3, data(self.view, "sceneHeight") * 0.8)))
        # a click elsewhere lets it go
        self.assertEqual(self.bridge.chosen, 0)
        pill = self.pills()[0]                                          # drawn again when the choice changed
        press(pill.mapToScene(pill.boundingRect().center()))
        self.assertEqual(self.bridge.chosen, 1)
        self.key(Qt.Key.Key_Delete)
        self.assertEqual(self.bridge.count, 0)                          # the measure, not the shed
        self.assertEqual(len(self.host.bridge.session.project.buildings), 1)

    def test_a_measure_begun_in_the_plan_ends_in_the_3d_view(self):
        self.bridge.click("plan", 0.0, 0.0, 0, 0.05)
        self.assertTrue(self.bridge.inHand)
        self.click((24, 0, 6))
        self.key(Qt.Key.Key_Return)
        made = self.bridge.tool.measures[-1]
        self.assertEqual(len(made.points), 2)
        self.assertEqual([round(c, 4) for c in made.points[1].point], [24, 0, 6])
        self.assertTrue(_setup.wait_until(self.app, lambda: len(self.pills()) == 1))


if __name__ == "__main__":
    unittest.main()
