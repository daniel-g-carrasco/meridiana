"""R389 drawing gestures through real QQuickWindow events: after each, the project the Widgets' plan made of the
same gestures (recorded on 10/11/2026 from the Widgets' side, when they went: quick/aiuti/riferimenti.py).

Tool activation replaces a toolbar choice, and canopy/prop options replace the
already accepted chooser. Every point and drawing key reaches a real Qt window.
Snapshots retain the complete Project.to_json payload except modified, the BIM identity and the creation time.
"""
from __future__ import annotations

import copy
import json
import math
import os
from dataclasses import asdict
from pathlib import Path
import unittest

os.environ.setdefault("QSG_RENDER_LOOP", "basic")

import _setup
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana.core.model import canopies, model
from meridiana import i18n
from meridiana.gui.backend.plan import PlanController
from quick.aiuti import riferimenti


setUpModule = _setup.keep_global_state
ROOT = Path(__file__).resolve().parents[3]


class DrawingParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        language = "it" if os.environ.get("MERIDIANA_QUICK_TOOL_PHOTOS") else "en"
        i18n.setup(language)
        project = model.Project(name="Drawing parity")
        project.buildings.append(model.Building(id="b1", name="Shed", height=6,
                                                footprint=[[0, 0], [20, 0], [20, 20], [0, 20]]))
        project.subfields.append(model.SubField(id="s1", name="Panels", building="b1",
                                               ring=[[1, 1], [19, 1], [19, 19], [1, 19]]))
        # the project as a window opens it: saved and read again
        self.controller = PlanController(model.Project.from_json(copy.deepcopy(project.to_json())))
        self.engine = QQmlApplicationEngine()
        self.warnings = []
        self.engine.warnings.connect(lambda errors: self.warnings.extend(e.toString() for e in errors))
        self.controller.install(self.engine)
        self.engine.rootContext().setContextProperty("planBackend", self.controller)
        self.engine.load(QUrl.fromLocalFile(str(ROOT / "src/meridiana/gui/qml/Meridiana/Plan/PlanWindow.qml")))
        self.assertTrue(self.engine.rootObjects(), self.warnings)
        self.quick = self.engine.rootObjects()[0]
        self.quick.show()
        QTest.qWaitForWindowExposed(self.quick)
        self.quick_plan = self.quick.findChild(QObject, "plan")
        self.addCleanup(self.close_quick)
        self.sequence = 0
        self.scale = 12
        self.frame()

    def close_quick(self):
        self.quick.close()
        self.controller.close()
        self.engine.deleteLater()
        self.app.processEvents()

    def frame(self):
        self.app.processEvents()
        self.quick_plan.setProperty("zoom", self.scale)
        self.quick_plan.setProperty("panX", 400)
        self.quick_plan.setProperty("panY", 500)
        self.quick_plan.setProperty("fitted", True)

    def tool(self, name, **options):
        self.controller.setTool(name)
        # The pending dialog value, not a mutation or a simulated gesture.
        if options:
            self.controller.drawing.set_tool(name, **options)
        self.frame()

    def locations(self, point):
        # Reset only the viewport, never the project or the draft.
        self.frame()
        x, y = point
        return QPoint(round(400 + self.scale * x), round(500 - self.scale * y))

    def click(self, point, modifiers=Qt.NoModifier):
        QTest.mouseClick(self.quick, Qt.LeftButton, modifiers, self.locations(point))
        self.settle()

    def pointer(self, point, modifiers=Qt.NoModifier):
        p = self.locations(point)
        # No OS cursor relocation: a local event to the window.
        from PySide6.QtGui import QMouseEvent
        event = QMouseEvent(QEvent.MouseMove, QPointF(p), QPointF(p), Qt.NoButton, Qt.NoButton, modifiers)
        self.app.sendEvent(self.quick, event)
        self.app.processEvents()

    def double(self, point, modifiers=Qt.NoModifier):
        QTest.mouseDClick(self.quick, Qt.LeftButton, modifiers, self.locations(point))
        self.settle()

    def move(self, point, modifiers=Qt.NoModifier):
        """The pointer through the application, as a real one (a move sent to the window alone is dropped by Qt Quick
        after a double click); no OS cursor moves."""
        QTest.mouseMove(self.quick, self.locations(point))
        self.app.processEvents()

    def drawn(self, name):
        """The items of the plan's overlay named `name` and shown (a Repeater's delegates are items only)."""
        def walk(item):
            for child in item.childItems():
                yield child
                yield from walk(child)
        overlay = self.quick.findChild(QObject, "toolOverlay")
        return [i for i in walk(overlay) if i.objectName() == name and i.isVisible()]

    def key(self, key, text="", modifiers=Qt.NoModifier):
        self.app.sendEvent(self.quick, QKeyEvent(QEvent.KeyPress, key, modifiers, text))
        self.app.sendEvent(self.quick, QKeyEvent(QEvent.KeyRelease, key, modifiers, text))
        self.settle()

    def text(self, text):
        for char in text:
            key = ord(char.upper())
            self.key(key, char)

    def settle(self):
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.controller.busy, 15))
        self.app.processEvents()

    def same(self, label):
        self.sequence += 1
        right = riferimenti.project(self.controller.session.project)
        folder = ROOT / "build/quick-foto/pianta/tools-states" / self._testMethodName
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{self.sequence:02d}-{label}-quick.json").write_text(
            json.dumps(right, ensure_ascii=False, indent=2), encoding="utf-8")
        riferimenti.check(self, right, name=f"{self.sequence:02d}-{label}")
        self.assertFalse(self.controller.error, self.controller.error)
        self.assertFalse(self.warnings, self.warnings)

    def capture(self, label):
        if not os.environ.get("MERIDIANA_QUICK_TOOL_PHOTOS"):
            return
        folder = ROOT / "build/quick-foto/pianta/tools"
        folder.mkdir(parents=True, exist_ok=True)
        QTest.qWait(80)
        image = self.quick.grabWindow()
        self.assertFalse(image.isNull())
        self.assertTrue(image.save(str(folder / f"{self._testMethodName}-{label}-quick.png")))
        if os.environ.get("MERIDIANA_QUICK_TOOL_MATRIX"):
            from meridiana.gui.backend.tokens import install_theme
            original = self.quick.size()
            for width, height in ((1600, 960), (1920, 1080)):
                for theme in ("light", "dark"):
                    install_theme(self.engine, {"theme": theme})
                    self.quick.resize(width, height)
                    QTest.qWait(80)
                    image = self.quick.grabWindow()
                    self.assertFalse(image.isNull())
                    scale = image.devicePixelRatio()
                    destination = folder / f"{width}x{height}-{theme}@{scale:g}"
                    destination.mkdir(exist_ok=True)
                    self.assertTrue(image.save(str(destination / f"{self._testMethodName}-{label}.png")))
            self.quick.resize(original)
            install_theme(self.engine, {"theme": "system"})
            self.app.processEvents()

    def card_visible(self):
        self.app.processEvents()
        card = self.quick.findChild(QObject, "toolCard")
        self.assertIsNotNone(card, "The drawing values must be presented in the QML overlay")
        self.assertTrue(card.property("visible"))
        label = self.quick.findChild(QObject, "toolCardText")
        self.assertTrue(label.property("text"))
        anchor = self.controller.drawing.preview["card"]["anchor"]
        if anchor and self.quick.width() > 1000:
            # R550: beside the pointer as every tooltip (ControlMetrics.besidePointer: 2 right, 21 below, 8 inside)
            at_x, at_y = 400+12*anchor[0], 500-12*anchor[1]
            expected_x = at_x+2 if at_x+2+card.width() <= self.quick_plan.width()-8 else at_x-2-card.width()
            expected_y = at_y+21 if at_y+21+card.height() <= self.quick_plan.height()-8 else at_y-4-card.height()
            expected_x = max(8, min(self.quick_plan.width()-card.width()-8, expected_x))
            expected_y = max(8, min(self.quick_plan.height()-card.height()-8, expected_y))
            self.assertAlmostEqual(card.x(), expected_x, places=5)
            self.assertAlmostEqual(card.y(), expected_y, places=5)
        return label.property("text")

    def test_building_vertices_numbers_and_rectangle(self):
        self.tool("building")
        self.click((25, 2)); self.pointer((35, 2)); self.text("10;90"); self.key(Qt.Key_Return)
        self.same("typed-side")
        self.text("5;90"); self.key(Qt.Key_Return)
        self.click((25, 7)); self.capture("outline"); self.key(Qt.Key_Return)
        self.same("polygon")
        self.key(Qt.Key_R, "r"); self.click((25, 10)); self.click((35, 10)); self.pointer((35, 15))
        self.text("5"); self.key(Qt.Key_Return)
        self.same("rectangle")

    def test_subfield_and_exclusion_polygons(self):
        # R445: the outline becomes the occupied modules, not the drawn polygon.
        # Four 1.134 m modules with three 0.02 m gaps span 4.596 m, centred at x=5.5;
        # the 2.278 m length projects to 2.2434 m at the default ten-degree tilt.
        # The following exclusion snaps to the new outline's x coordinates.
        for tool in ("subfield", "exclusion"):
            self.tool(tool)
            for index, point in enumerate([(3, 3), (8, 3), (8, 8), (3, 8)], 1):
                self.click(point)
                self.capture(f"{tool}-point-{index}")
            self.key(Qt.Key_Return)
            if tool == "subfield":
                sf = self.controller.session.project.subfields[-1]
                self.assertTrue(sf.filled and sf.manual and sf.flush)
                self.assertEqual(sf.params['alignment'], 'aligned')
                self.assertEqual(len(sf.rows), 1)
                self.assertEqual(len(sf.rows[0]['places']), 4)
                self.assertAlmostEqual(min(p[0] for p in sf.ring), 3.202)
                self.assertAlmostEqual(max(p[0] for p in sf.ring), 7.798)
                self.assertAlmostEqual(max(p[1] for p in sf.ring), 5.2434)
            else:
                exclusion = self.controller.session.project.exclusions[-1]
                self.assertEqual(exclusion.kind, 'skylight')
                for point, expected in zip(exclusion.ring, [[3.202, 3.0], [7.798, 3.0], [7.798, 8.0], [3.202, 8.0]], strict=True):
                    self.assertAlmostEqual(point[0], expected[0])
                    self.assertAlmostEqual(point[1], expected[1])
            self.same(tool)
            self.capture(f"{tool}-closed")

    def test_pitch_fields_swap_and_close(self):
        self.tool("pitch")
        self.click((0, 0)); self.capture("first-point"); self.key(Qt.Key_Tab); self.capture("tab")
        self.click((20, 0)); self.pointer((20, 10)); self.capture("depth")
        self.key(Qt.Key_Down); self.text("20%"); self.key(Qt.Key_Return)
        self.card_visible()
        self.capture("slope")
        self.same("draft")
        self.click((20, 10)); self.same("pitch")

    def test_ridge_height_and_automatic_second_point(self):
        self.tool("ridge")
        self.click((0, 10))
        self.assertAlmostEqual(self.controller.drawing.preview["ridge"]["ridge"], 9.5)
        self.assertFalse(self.controller.drawing.preview["ridge"]["typed"])
        self.capture("proposed-height"); self.text("9"); self.key(Qt.Key_Return)
        self.card_visible()
        self.same("height")
        self.capture("height")
        self.click((20, 10)); self.same("ridge")

    def test_rows_and_east_west_typed_length(self):
        for tool in ("row", "east_west"):
            self.tool(tool)
            self.click((3, 5)); self.pointer((13, 5)); self.text("10"); self.capture(tool)
            row = self.controller.drawing.preview["row"]
            riferimenti.check(self, [len(row["quads"]), row["bad"]])
            self.card_visible()
            self.key(Qt.Key_Return)
            self.same(tool)

    def test_prop_and_linear_object(self):
        self.tool("prop", kind="conifer"); self.pointer((25, 5)); self.capture("prop-place")
        self.click((25, 5)); self.same("prop"); self.capture("prop-placed")
        self.tool("prop_line", kind="walkway")
        self.click((25, 10)); self.pointer((35, 10)); self.capture("path-first-point")
        self.click((35, 10)); self.capture("path-second-point"); self.key(Qt.Key_Return)
        self.same("path"); self.capture("path-placed")

    def test_canopy_point_after_accepted_parameters(self):
        self.tool("canopy", spec=asdict(canopies.Spec(rows=2)))
        self.pointer((25, 5)); self.capture("canopy-place")
        self.click((25, 5)); self.same("canopy"); self.capture("canopy-placed")

    def test_measure_and_escape_three_levels(self):
        # study 46: a simple measure is a click and a double click; its pill on the span, the project untouched
        self.tool("measure")
        self.click((3, 3), Qt.ControlModifier); self.double((6, 7), Qt.ControlModifier); self.move((10, 10))
        measures = self.controller.measure.tool.measures
        self.assertEqual(len(measures), 1)
        self.assertAlmostEqual(measures[0].spans()[0].plan, 5)
        self.assertEqual([p.property("value") for p in self.drawn("measurePill")], ["5.00 m"])
        self.capture("measurement"); self.same("measurement")
        self.tool("building"); self.click((25, 5)); self.text("12"); self.capture("esc-typed")
        self.key(Qt.Key_Escape)
        riferimenti.check(self, [self.controller.drawing.typed, len(self.controller.drawing.points)])
        self.capture("esc-number-cleared")
        self.key(Qt.Key_Escape)
        self.assertFalse(self.controller.drawing.points)
        self.capture("esc-draft-cleared")
        self.key(Qt.Key_Escape)
        self.assertEqual(self.controller.tool, "select")
        self.capture("esc-select")
        self.same("escaped")

    def test_two_measures_one_after_the_other_r563(self):
        """R563: the clicks Daniel made (13/11/2026), with the snaps on: a measure, then another one that starts by
        the first. What the overlay draws is read from the window (the measures' layer, study 46)."""
        def at(point):
            self.move(point); self.click(point)

        tool = self.controller.measure.tool
        self.tool("measure")
        at((25, 5))
        # the first click shows where the measure starts: its mark, and the one that follows the pointer
        self.assertEqual((len(self.drawn("measureMark")), len(self.drawn("measurePointer"))), (1, 1))
        self.move((32, 5)); self.double((32, 5))
        self.assertEqual((tool.state, [p.point[:2] for p in tool.measures[0].points]), ("idle", [(25., 5.), (32., 5.)]))
        self.assertEqual([p.property("value") for p in self.drawn("measurePill")], ["7.00 m"])
        # towards the second measure, 4 px beside the line going north from the first point of the first one
        self.move((25.3, 12))
        self.assertEqual(self.drawn("measureGuides"), [])
        self.assertEqual(len(self.drawn("measureMark")), 2)     # the measure made is still there
        self.assertEqual([p.property("value") for p in self.drawn("measurePill")], ["7.00 m"])
        at((25.3, 12))
        start = tool.points[0].point[:2]
        self.assertEqual(len(tool.points), 1)
        self.assertLess(math.dist(start, (25.3, 12)), 0.05)     # where the click was (a pixel is 0.083 m), not 25.0
        self.assertGreater(abs(start[0] - 25), 0.2)
        self.assertEqual((self.drawn("measureGuides"), len(self.drawn("measureMark"))), ([], 3))
        self.move((25.3, 2)); self.double((25.3, 2))
        second = tool.measures[-1]
        self.assertEqual((tool.state, len(tool.measures), second.points[0].point[:2]), ("idle", 2, start))
        self.assertAlmostEqual(second.spans()[0].plan, math.dist(start, second.points[1].point[:2]))
        self.assertAlmostEqual(second.spans()[0].plan, 10, delta=0.1)
        self.assertFalse(self.warnings, self.warnings)

    def test_pitch_polygon_and_backspace(self):
        self.tool("pitch"); self.key(Qt.Key_R, "r")
        self.click((0, 0)); self.click((20, 0)); self.click((20, 10)); self.click((0, 10))
        self.key(Qt.Key_Backspace)
        self.assertEqual(len(self.controller.drawing.points), 3)
        self.capture("backspace")
        self.click((0, 10)); self.key(Qt.Key_Return)
        self.same("pitch-corners")

    def test_reference_snap_on_click_without_prior_hover(self):
        self.tool("building")
        # At 12 px/m this is 5 pixels from a known corner, inside the common 10 px reach.
        # No pointer() call is sent: a pen or touch press need not have a hover.
        self.click((20 + 5 / 12, 20))
        self.assertEqual(self.controller.drawing.points, [(20., 20.)])
        self.same("snap-touch")

    def test_function_key_reaches_orthogonal_switch(self):
        self.tool("building")
        self.click((25, 2)); self.pointer((30, 4))
        self.quick.requestActivate()
        self.app.processEvents()
        QTest.keyClick(self.quick, Qt.Key_F8)
        self.assertTrue(self.controller.drawing.orthogonal)
        self.click((30, 4))
        self.assertEqual(self.controller.drawing.points[-1], (30., 2.))
        self.same("ortho")

    def test_row_preview_outside_area_stays_visible(self):
        self.tool("row")
        self.click((15, 5)); self.pointer((25, 5)); self.text("10")
        row = self.controller.drawing.preview["row"]
        self.assertTrue(row["bad"])
        self.assertGreater(len(row["quads"]), 0)
        riferimenti.check(self, len(row["quads"]))
        self.card_visible(); self.capture("outside")
        self.key(Qt.Key_Return)
        self.same("outside-row-kept")

    def test_pitch_card_stays_in_narrow_view_with_large_text(self):
        from meridiana.gui.backend.tokens import install_theme
        self.tool("pitch"); self.click((0, 0)); self.click((20, 0)); self.pointer((20, 10))
        install_theme(self.engine, {"textSize": "large"})
        self.quick.resize(480, 400)
        self.app.processEvents()
        self.card_visible()
        card = self.quick.findChild(QObject, "toolCard")
        self.assertGreaterEqual(card.x(), 0)
        self.assertGreaterEqual(card.y(), 0)
        self.assertLessEqual(card.x()+card.width(), self.quick_plan.width())
        self.assertLessEqual(card.y()+card.height(), self.quick_plan.height()-38)
        self.capture("narrow-large")

    def test_rectangle_three_clicks_and_small_depth_beside_edge(self):
        self.tool("building"); self.key(Qt.Key_R, "r")
        self.click((25, 2)); self.click((35, 2)); self.click((30, 10))
        self.same("three-click-rectangle")
        ring = self.controller.session.project.buildings[-1].footprint
        self.assertEqual(len(ring), 4)
        self.assertEqual(ring[2][0], ring[1][0])
        self.assertEqual(ring[3][0], ring[0][0])
        self.assertAlmostEqual(ring[2][1], 10., delta=3/self.scale)
        self.scale = 8
        self.tool("exclusion")
        if not self.controller.drawing.rectangle:
            self.key(Qt.Key_R, "r")
        references = [((5.6, -50.), (5.6, 30.))]
        self.controller.drawing.set_references(references)
        self.click((4, 4), Qt.ControlModifier); self.click((5.25, 4), Qt.ControlModifier)
        self.pointer((5.25, 5)); self.capture("small-depth")
        self.click((5.25, 5)); self.same("small-rectangle")
        ring = self.controller.session.project.exclusions[-1].ring
        self.assertAlmostEqual(abs(ring[2][1]-ring[1][1]), 1.)

    def test_shift_press_holds_direction_and_release_unlocks(self):
        self.tool("building"); self.click((25, 0)); self.pointer((30, 5))
        self.app.sendEvent(self.quick, QKeyEvent(QEvent.KeyPress, Qt.Key_Shift, Qt.ShiftModifier))
        self.pointer((35, 2), Qt.ShiftModifier)
        p = self.controller.drawing.pointer
        self.assertAlmostEqual(p[0]-25, p[1])
        self.capture("shift-locked")
        self.app.sendEvent(self.quick, QKeyEvent(QEvent.KeyRelease, Qt.Key_Shift, Qt.NoModifier))
        self.assertIsNone(self.controller.drawing.lock_direction)
        self.pointer((35, 2)); self.click((35, 2))
        riferimenti.check(self, self.controller.drawing.points[-1])
        self.assertNotAlmostEqual(self.controller.drawing.pointer[0]-25, self.controller.drawing.pointer[1])
        self.same("shift-release")

    def test_pitch_refuses_low_ridge_then_accepts_height_and_tab(self):
        self.tool("pitch"); self.key(Qt.Key_Tab)
        self.assertFalse(self.controller.drawing.pitch_card["swapped"])
        self.click((0, 0)); self.click((20, 0)); self.pointer((10, 5))
        self.key(Qt.Key_Down); self.text("20"); self.key(Qt.Key_Return)
        self.key(Qt.Key_Down); self.text("5"); self.key(Qt.Key_Return)
        self.assertIsNone(self.controller.drawing.pitch_card["ridge"])
        self.assertTrue(self.controller.drawing.error)
        self.capture("low-ridge-refused")
        self.text("9"); self.key(Qt.Key_Return)
        self.assertAlmostEqual(self.controller.drawing.pitch_values()["ridge"], 9.)
        self.capture("ridge-accepted")
        self.key(Qt.Key_Tab)
        self.assertEqual(self.controller.drawing.pitch_values()["eave_side"], 2)
        self.capture("eave-swapped")
        self.key(Qt.Key_Return); self.same("height-and-tab")
        self.assertFalse(self.controller.drawing.pitch_card["swapped"])

    def test_pitch_typed_depth_closes_after_percent(self):
        self.tool("pitch"); self.click((0, 0)); self.click((20, 0)); self.pointer((10, 3))
        self.key(Qt.Key_Down); self.text("30%"); self.key(Qt.Key_Return)
        self.assertAlmostEqual(self.controller.drawing.pitch_card["tilt"], math.degrees(math.atan(.3)))
        self.key(Qt.Key_Up); self.text("7"); self.capture("typed-depth")
        self.key(Qt.Key_Return); self.same("typed-depth-closed")
        ring = self.controller.session.project.buildings[0].roof.free_pitches[-1]["ring"]
        self.assertAlmostEqual(abs(ring[2][1]-ring[1][1]), 7.)

    def test_l_building_bent_ridge_and_outside_refusal(self):
        def shape(project):
            project.buildings[0].footprint = [[0, 0], [20, 0], [20, 8], [8, 8], [8, 20], [0, 20]]
            project.subfields.clear()
        self.controller.session.edit("L fixture", shape)
        self.settle(); self.tool("ridge")
        self.click((25, 20))
        self.assertEqual(self.controller.drawing.points, [])
        self.assertTrue(self.controller.drawing.error)
        self.capture("outside-refused")
        for point in ((4, 19.5), (4, 4), (19.5, 4)):
            self.click(point)
        self.assertEqual(len(self.controller.drawing.points), 3)
        self.capture("bent-ridge")
        self.key(Qt.Key_Return); self.same("bent-ridge")


if __name__ == "__main__":
    unittest.main()
