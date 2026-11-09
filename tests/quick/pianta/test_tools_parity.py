"""R389 drawing gestures through real Widgets and QQuickWindow events.

Tool activation replaces a toolbar choice, and canopy/prop options replace the
already accepted chooser. Every point and drawing key reaches a real Qt window.
Snapshots retain the complete Project.to_json payload except modified.
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
from PySide6.QtGui import QKeyEvent, QTransform
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana import canopies, config, i18n, model
from meridiana.quick.backend.plan import PlanController
from quick.parity.differential import canonical_project, compare


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
        self.widgets = _setup.window(self, project, cfg=config.Config(background="none", network_pvgis=False,
                                                                     language=language),
                                     size=(1366, 900))
        self.widgets._view_mode("plan")
        self.widgets.energy_timer.stop()
        self.controller = PlanController(copy.deepcopy(self.widgets.project))
        self.engine = QQmlApplicationEngine()
        self.warnings = []
        self.engine.warnings.connect(lambda errors: self.warnings.extend(e.toString() for e in errors))
        self.controller.install(self.engine)
        self.engine.rootContext().setContextProperty("planBackend", self.controller)
        self.engine.load(QUrl.fromLocalFile(str(ROOT / "src/meridiana/quick/qml/Meridiana/Plan/PlanWindow.qml")))
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
        self.widgets.plan.setTransform(QTransform.fromScale(self.scale, self.scale))
        self.widgets.plan.centerOn(15, -10)
        self.quick_plan.setProperty("zoom", self.scale)
        self.quick_plan.setProperty("panX", 400)
        self.quick_plan.setProperty("panY", 500)
        self.quick_plan.setProperty("fitted", True)

    def tool(self, name, **options):
        if name == "prop":
            self.widgets.place_prop(options["kind"])
        elif name == "prop_line":
            self.widgets.place_prop(options["kind"])
        elif name == "canopy":
            self.widgets.place_carport(canopies.Spec(**options["spec"]))
        else:
            self.widgets._set_tool(name)
        self.controller.setTool(name)
        # The pending dialog value, not a mutation or a simulated gesture.
        if options:
            self.controller.drawing.set_tool(name, **options)
        self.frame()

    def locations(self, point):
        # Widgets may fit the plan after a phase is lent to Plant or a layout returns.
        # Reset only the viewport transform, never the project or the draft.
        self.frame()
        x, y = point
        widgets = self.widgets.plan.mapFromScene(QPointF(x, -y))
        self.assertTrue(self.widgets.plan.viewport().rect().contains(widgets), (point, widgets))
        scene = self.widgets.plan.mapToScene(widgets)
        self.assertAlmostEqual(scene.x(), x, places=7)
        self.assertAlmostEqual(-scene.y(), y, places=7)
        quick = QPoint(round(400 + self.scale * x), round(500 - self.scale * y))
        return widgets, quick

    def click(self, point, modifiers=Qt.NoModifier):
        widgets, quick = self.locations(point)
        QTest.mouseClick(self.widgets.plan.viewport(), Qt.LeftButton, modifiers, widgets)
        QTest.mouseClick(self.quick, Qt.LeftButton, modifiers, quick)
        self.settle()

    def pointer(self, point, modifiers=Qt.NoModifier):
        widgets, quick = self.locations(point)
        # No OS cursor relocation: these are local events to each receiving surface.
        from PySide6.QtGui import QMouseEvent
        for target, p in ((self.widgets.plan.viewport(), widgets), (self.quick, quick)):
            event = QMouseEvent(QEvent.MouseMove, QPointF(p), QPointF(p), Qt.NoButton, Qt.NoButton, modifiers)
            self.app.sendEvent(target, event)
        self.app.processEvents()

    def key(self, key, text="", modifiers=Qt.NoModifier):
        for target in (self.widgets.plan, self.quick):
            self.app.sendEvent(target, QKeyEvent(QEvent.KeyPress, key, modifiers, text))
            self.app.sendEvent(target, QKeyEvent(QEvent.KeyRelease, key, modifiers, text))
        self.settle()

    def text(self, text):
        for char in text:
            key = ord(char.upper())
            self.key(key, char)

    def settle(self):
        self.widgets.energy_timer.stop()
        self.assertTrue(_setup.wait_until(self.app, lambda: self.widgets._layouts_settled(), 15))
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.controller.busy, 15))
        self.widgets.energy_timer.stop()
        self.app.processEvents()

    def same(self, label):
        self.sequence += 1
        left, right = canonical_project(self.widgets.project), canonical_project(self.controller.session.project)
        folder = ROOT / "build/quick-parity/tools" / self._testMethodName
        folder.mkdir(parents=True, exist_ok=True)
        for name, value in (("widgets", left), ("quick", right)):
            (folder / f"{self.sequence:02d}-{label}-{name}.json").write_text(
                json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        self.assertEqual(compare(left, right), [], label)
        self.assertFalse(self.controller.error, self.controller.error)
        self.assertFalse(self.warnings, self.warnings)

    def capture(self, label):
        if not os.environ.get("MERIDIANA_QUICK_TOOL_PHOTOS"):
            return
        folder = ROOT / "build/quick-foto/pianta/tools"
        folder.mkdir(parents=True, exist_ok=True)
        self.widgets.plan.viewport().repaint()
        QTest.qWait(80)
        image = self.quick.grabWindow()
        self.assertFalse(image.isNull())
        self.assertTrue(image.save(str(folder / f"{self._testMethodName}-{label}-quick.png")))
        self.assertTrue(self.widgets.plan.grab().save(str(folder / f"{self._testMethodName}-{label}-widgets.png")))
        if os.environ.get("MERIDIANA_QUICK_TOOL_MATRIX"):
            from meridiana.quick.backend.tokens import install_theme
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
        for tool in ("subfield", "exclusion"):
            self.tool(tool)
            for index, point in enumerate([(3, 3), (8, 3), (8, 8), (3, 8)], 1):
                self.click(point)
                self.capture(f"{tool}-point-{index}")
            self.key(Qt.Key_Return)
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
            expected, bad = self.widgets._row_preview((3, 5), (13, 5))
            row = self.controller.drawing.preview["row"]
            self.assertEqual(len(row["quads"]), len(expected))
            self.assertEqual(row["bad"], bad)
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
        self.tool("measure")
        self.click((3, 3), Qt.ControlModifier); self.click((6, 7), Qt.ControlModifier); self.pointer((10, 10))
        self.assertAlmostEqual(math.dist(*self.widgets.plan.measure), 5)
        self.assertAlmostEqual(self.controller.drawing.preview["length"], 5)
        self.assertIn("5", self.card_visible())
        self.capture("measurement"); self.same("measurement")
        self.tool("building"); self.click((25, 5)); self.text("12"); self.capture("esc-typed")
        self.key(Qt.Key_Escape)
        self.assertEqual(self.widgets.plan.typed, self.controller.drawing.typed)
        self.assertEqual(len(self.widgets.plan.chain), len(self.controller.drawing.points))
        self.capture("esc-number-cleared")
        self.key(Qt.Key_Escape)
        self.assertFalse(self.widgets.plan.chain)
        self.assertFalse(self.controller.drawing.points)
        self.capture("esc-draft-cleared")
        self.key(Qt.Key_Escape)
        self.assertEqual(self.widgets.plan.tool, self.controller.tool)
        self.capture("esc-select")
        self.same("escaped")

    def test_pitch_polygon_and_backspace(self):
        self.tool("pitch"); self.key(Qt.Key_R, "r")
        self.click((0, 0)); self.click((20, 0)); self.click((20, 10)); self.click((0, 10))
        self.key(Qt.Key_Backspace)
        self.assertEqual(len(self.widgets.plan.chain), 3)
        self.assertEqual(len(self.controller.drawing.points), 3)
        self.capture("backspace")
        self.click((0, 10)); self.key(Qt.Key_Return)
        self.same("pitch-corners")

    def test_reference_snap_on_click_without_prior_hover(self):
        self.tool("building")
        # At 12 px/m this is 5 pixels from a known corner, inside the common 10 px reach.
        # No pointer() call is sent: a pen or touch press need not have a hover.
        self.click((20 + 5 / 12, 20))
        self.assertEqual(self.widgets.plan.chain, [(20., 20.)])
        self.assertEqual(self.controller.drawing.points, [(20., 20.)])
        self.same("snap-touch")

    def test_function_key_reaches_orthogonal_switch(self):
        self.tool("building")
        self.click((25, 2)); self.pointer((30, 4))
        self.widgets.activateWindow()
        self.widgets.plan.setFocus()
        self.app.processEvents()
        QTest.keyClick(self.widgets.plan, Qt.Key_F8)
        self.quick.requestActivate()
        self.app.processEvents()
        QTest.keyClick(self.quick, Qt.Key_F8)
        self.assertTrue(self.widgets.plan.ortho)
        self.assertTrue(self.controller.drawing.orthogonal)
        self.click((30, 4))
        self.assertEqual(self.widgets.plan.chain[-1], (30., 2.))
        self.assertEqual(self.controller.drawing.points[-1], (30., 2.))
        self.same("ortho")

    def test_row_preview_outside_area_stays_visible(self):
        self.tool("row")
        self.click((15, 5)); self.pointer((25, 5)); self.text("10")
        expected, bad = self.widgets._row_preview((15, 5), (25, 5))
        self.assertTrue(bad)
        row = self.controller.drawing.preview["row"]
        self.assertTrue(row["bad"])
        self.assertEqual(len(row["quads"]), len(expected))
        self.assertGreater(len(expected), 0)
        self.card_visible(); self.capture("outside")
        self.key(Qt.Key_Return)
        self.same("outside-row-kept")

    def test_pitch_card_stays_in_narrow_view_with_large_text(self):
        from meridiana.quick.backend.tokens import install_theme
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
        self.widgets.plan.snapper.set_references(references)
        self.controller.drawing.set_references(references)
        self.click((4, 4), Qt.ControlModifier); self.click((5.25, 4), Qt.ControlModifier)
        self.pointer((5.25, 5)); self.capture("small-depth")
        self.click((5.25, 5)); self.same("small-rectangle")
        ring = self.controller.session.project.exclusions[-1].ring
        self.assertAlmostEqual(abs(ring[2][1]-ring[1][1]), 1.)

    def test_shift_press_holds_direction_and_release_unlocks(self):
        self.tool("building"); self.click((25, 0)); self.pointer((30, 5))
        for target in (self.widgets.plan, self.quick):
            self.app.sendEvent(target, QKeyEvent(QEvent.KeyPress, Qt.Key_Shift, Qt.ShiftModifier))
        self.pointer((35, 2), Qt.ShiftModifier)
        p = self.controller.drawing.pointer
        self.assertAlmostEqual(p[0]-25, p[1])
        self.assertEqual(self.widgets.plan.snap.point, p)
        self.capture("shift-locked")
        for target in (self.widgets.plan, self.quick):
            self.app.sendEvent(target, QKeyEvent(QEvent.KeyRelease, Qt.Key_Shift, Qt.NoModifier))
        self.assertIsNone(self.widgets.plan.lock_dir)
        self.assertIsNone(self.controller.drawing.lock_direction)
        self.pointer((35, 2)); self.click((35, 2))
        self.assertEqual(self.widgets.plan.chain[-1], self.controller.drawing.points[-1])
        self.assertNotAlmostEqual(self.controller.drawing.pointer[0]-25, self.controller.drawing.pointer[1])
        self.same("shift-release")

    def test_pitch_refuses_low_ridge_then_accepts_height_and_tab(self):
        self.tool("pitch"); self.key(Qt.Key_Tab)
        self.assertFalse(self.controller.drawing.pitch_card["swapped"])
        self.assertFalse(self.widgets.plan.pitch_card["swapped"])
        self.click((0, 0)); self.click((20, 0)); self.pointer((10, 5))
        self.key(Qt.Key_Down); self.text("20"); self.key(Qt.Key_Return)
        self.key(Qt.Key_Down); self.text("5"); self.key(Qt.Key_Return)
        self.assertIsNone(self.controller.drawing.pitch_card["ridge"])
        self.assertIsNone(self.widgets.plan.pitch_card["ridge"])
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
        self.widgets.edit("L fixture", shape)
        self.controller.session.edit("L fixture", shape)
        self.settle(); self.tool("ridge")
        self.click((25, 20))
        self.assertEqual(self.widgets.plan.chain, [])
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
