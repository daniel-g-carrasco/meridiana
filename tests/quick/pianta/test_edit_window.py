"""R389/R295/R299/R300: edit gestures on a real Quick window and D3D pixels."""
import os
import json
import math
import time
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault("QSG_RENDER_LOOP", "basic")
os.environ.setdefault("QSG_RHI_BACKEND", "d3d11")
os.environ["QML_DISABLE_DISK_CACHE"] = "1"

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QMouseEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from meridiana import i18n, model, move
from meridiana.quick.backend.plan import PlanController
from meridiana.session import ProjectSession

APP = None
ROOT = Path(__file__).resolve().parents[3]
PHOTOS = ROOT / "build/quick-foto/pianta/edit"


def setUpModule():
    global APP
    APP = QApplication.instance() or QApplication(["plan-edit-test"])
    i18n.setup("it")


class EditWindowTest(unittest.TestCase):
    def setUp(self):
        p = model.Project(name="Verifica pianta Quick")
        p.buildings.append(model.Building(id="b1", name="Capannone", height=6,
                                         footprint=[[0, 0], [40, 0], [40, 20], [0, 20]]))
        p.subfields.append(model.SubField(id="s1", name="Sud", building="b1", filled=True,
                                        ring=[[2, 2], [38, 2], [38, 18], [2, 18]], params={"tilt": 15}))
        self.session = ProjectSession(p)
        self.result = p.fill(p.subfields[0])
        self.session.results = {"s1": self.result}
        self.controller = PlanController(self.session)
        self.engine = QQmlApplicationEngine()
        self.warnings = []
        self.engine.warnings.connect(lambda es: self.warnings.extend(e.toString() for e in es))
        self.controller.install(self.engine)
        self.engine.rootContext().setContextProperty("planBackend", self.controller)
        self.engine.load(QUrl.fromLocalFile(str(ROOT / "src/meridiana/quick/qml/Meridiana/Plan/PlanWindow.qml")))
        self.assertTrue(self.engine.rootObjects(), self.warnings)
        self.window = self.engine.rootObjects()[0]
        self.window.resize(1366, 900)
        self.window.show()
        self.assertTrue(QTest.qWaitForWindowExposed(self.window))
        QTest.qWait(70)
        self.plan = self.window.findChild(QObject, "plan")
        self.layer = self.window.findChild(QObject, "worldLayer")
        self.plan.forceActiveFocus()

    def tearDown(self):
        self.window.close()
        self.controller.close()
        self.engine.deleteLater()
        APP.processEvents()
        # now, as QuickWindow.close does: processEvents() never delivers it, the engine went in the middle of the next
        # test's qWait, and the last one stayed alive until the process ended (tests/_setup.end_qt)
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def screen(self, point):
        return self.layer.mapToScene(QPointF(point[0], -point[1])).toPoint()

    def click(self, point, mods=Qt.NoModifier):
        QTest.mouseClick(self.window, Qt.LeftButton, mods, self.screen(point))
        APP.processEvents()

    def click_side(self, side):
        pill = self.visual("sidePill"+str(side))
        self.assertIsNotNone(pill, "The side must have a visible pill")
        point = pill.mapToScene(QPointF(pill.width()/2, pill.height()/2)).toPoint()
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, point)
        APP.processEvents()

    def visual(self, name):
        def descendants(item):
            for child in item.childItems():
                yield child
                yield from descendants(child)
        return next((item for item in descendants(self.plan) if item.objectName() == name), None)

    def key(self, key, mods=Qt.NoModifier):
        QTest.keyClick(self.window, key, mods)
        APP.processEvents()

    def test_grip_hover_cursor_disc_reach_and_active_gesture(self):
        self.controller.editor.select('building', 'b1')
        self.controller.setTool('move')
        APP.processEvents()
        for name, point in (('move', (20, 10)), ('rotate', (20, 20))):
            mouse = self.visual('transformGripMouse'+name)
            self.assertIsNotNone(mouse)
            QTest.mouseMove(self.window, self.screen(point))
            APP.processEvents()
            self.assertTrue(mouse.property('containsMouse'))
            self.assertEqual(mouse.cursor().shape(), Qt.SizeAllCursor if name == 'move' else Qt.BitmapCursor)
            self.assertEqual(self.plan.property('localHint'), self.controller.texts['grip'+name.title()])
            centre = mouse.mapToScene(QPointF(mouse.width()/2, mouse.height()/2))
            QTest.mouseMove(self.window, (centre+QPointF(mouse.width()/2-1, 0)).toPoint())
            APP.processEvents()
            self.assertTrue(mouse.property('containsMouse'), 'The edge of the disc must be sensitive')
            QTest.mouseMove(self.window, (centre+QPointF(mouse.width()/2-1, mouse.height()/2-1)).toPoint())
            APP.processEvents()
            self.assertFalse(mouse.property('containsMouse'), 'The square corner is outside the disc')
        self.click((3, 3))
        self.assertIsNotNone(self.controller.editor.gesture.base)
        for name in ('move', 'rotate'):
            self.assertFalse(self.visual('transformGripMouse'+name).property('enabled'))
        self.key(Qt.Key_Escape)
        self.assertFalse(self.warnings, self.warnings)

    def text(self, text):
        # QTest.keyClicks is QWidget-only; send QWindow keys one at a time.
        for char in text:
            QTest.keyClick(self.window, ord(char))
        APP.processEvents()

    def drag(self, points, mods=Qt.NoModifier, hold=0, release_mods=None):
        from PySide6.QtCore import QEvent
        start = self.screen(points[0])
        QTest.mousePress(self.window, Qt.LeftButton, mods, start)
        if hold:
            QTest.qWait(hold)
        for point in points[1:]:
            pos = QPointF(self.screen(point))
            event = QMouseEvent(QEvent.MouseMove, pos, pos, self.window.mapToGlobal(pos.toPoint()),
                                Qt.NoButton, Qt.LeftButton, mods)
            APP.sendEvent(self.window, event)
            APP.processEvents()
        QTest.mouseRelease(self.window, Qt.LeftButton, mods if release_mods is None else release_mods,
                           self.screen(points[-1]))
        APP.processEvents()

    def capture(self, name):
        for _attempt in range(200):
            if not getattr(self.controller, "busy", False):
                break
            QTest.qWait(25)
        self.assertFalse(getattr(self.controller, "busy", False), "Layout did not settle before capture")
        PHOTOS.mkdir(parents=True, exist_ok=True)
        self.window.update()
        QTest.qWait(60)
        shot = self.window.grabWindow()
        self.assertFalse(shot.isNull())
        suffix = f"@{shot.devicePixelRatio():g}x"
        self.assertTrue(shot.save(str(PHOTOS / (name + suffix + ".png"))))
        api = str(self.window.rendererInterface().graphicsApi())
        (PHOTOS / (name + suffix + ".json")).write_text(json.dumps(
            dict(api=api, platform=APP.platformName(), dpr=shot.devicePixelRatio(),
                 width=shot.width(), height=shot.height(), calls=dict(self.controller.calls)), indent=2), encoding="utf-8")
        if APP.platformName() == "windows":
            self.assertIn("Direct3D11", api)
        self.assertFalse(self.warnings, self.warnings)

    def select_building(self):
        self.click((.6, .6))
        # A roof is an inner selection level; Esc takes its building.
        if self.controller.editor.selection[0] == "pitch":
            self.key(Qt.Key_Escape)
        self.assertEqual(self.controller.editor.selection, ("building", "b1"))

    def test_selection_row_escape_delete(self):
        self.controller.setPhase("plant")
        m = self.result.modules[0]
        self.click(m.centre)
        self.assertEqual(self.controller.editor.selected_module, ("s1", m.key))
        self.capture("01-modulo")
        self.click(m.centre)
        self.assertEqual(self.controller.editor.selection, ("row", "s1/" + m.rid))
        self.capture("01b-fila")
        # Widgets selects one enclosing row outline, not each of its modules.
        from shapely.geometry import MultiPoint, Polygon
        row_points = [p for x in self.result.modules if x.rid == m.rid for p in x.corners]
        expected = MultiPoint(row_points).minimum_rotated_rectangle
        contour = self.controller.highlights[-1]['points']
        self.assertLess(Polygon([(p.x(), -p.y()) for p in contour]).symmetric_difference(expected).area, 1e-8)
        self.assertFalse(self.controller.moduleHighlights)
        for target in [("subfield", "s1"), ("site", "")]:       # the Plant does not select buildings
            self.key(Qt.Key_Escape)
            self.assertEqual(self.controller.editor.selection, target)
        self.click(m.centre)
        self.key(Qt.Key_Delete)
        self.assertIn(m.key, self.session.project.subfields[0].removed)
        self.key(Qt.Key_Z, Qt.ControlModifier)
        self.assertEqual(self.session.project.subfields[0].removed, [])

    def test_row_end_handle_drag_resizes_and_undo_restores_keys(self):
        self.controller.setPhase("plant")
        module = self.result.modules[0]
        row = next(row for row in self.result.rows if row.id == module.rid)
        self.click(module.centre)
        self.click(module.centre)
        handle = self.window.findChild(QObject, "rowHandle")
        self.assertIsNotNone(handle)
        self.assertTrue(handle.isVisible())
        spec = self.controller.rowHandle
        self.assertEqual(spec["oid"], "s1/"+row.id)
        end = (spec["x"], spec["y"])
        self.drag([end, (end[0]-1, end[1]), (end[0]-3, end[1])])
        self.capture("17-fila-accorciata")
        result = self.session.results["s1"]
        self.assertLess(len([m for m in result.modules if m.rid == row.id]), row.count)
        self.assertTrue(self.session.project.subfields[0].manual)
        self.assertEqual(self.session.undo.count(), 1)
        self.key(Qt.Key_Z, Qt.ControlModifier)
        self.capture("17b-fila-ripristinata")
        self.assertEqual([m.key for m in self.session.results["s1"].modules], [m.key for m in self.result.modules])

    def test_touchpad_six_pixels_seven_pixels_and_double_tap(self):
        self.controller.setPhase("plant")
        module = max(self.result.modules, key=lambda m: m.centre[0])
        edge = self.layer.mapToScene(QPointF(max(p[0] for p in module.corners), -module.centre[1]))
        x, y = math.floor(edge.x()), round(edge.y())
        for _attempt in range(50):
            if math.isclose(self.controller.editor.pick_reach, 6/self.plan.property("zoom")):
                break
            QTest.qWait(10)
        self.assertAlmostEqual(self.controller.editor.pick_reach, 6/self.plan.property("zoom"), places=6)
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, QPoint(x+6, y))
        APP.processEvents()
        self.assertEqual(self.controller.editor.selected_module, ("s1", module.key))
        self.key(Qt.Key_Escape)
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, QPoint(x+7, y))
        APP.processEvents()
        self.assertEqual(self.controller.editor.selected_module, ("", ""))
        self.click(module.centre)
        QTest.mouseDClick(self.window, Qt.LeftButton, Qt.NoModifier, self.screen(module.centre))
        APP.processEvents()
        self.assertEqual(self.controller.editor.selection, ("row", "s1/"+module.rid))
        self.assertEqual(self.controller.calls["doubleClick"], 1)

    def test_move_nudge_copy_rotate_typed(self):
        self.select_building()
        self.key(Qt.Key_M)
        self.key(Qt.Key_Right)
        self.key(Qt.Key_Up, Qt.ControlModifier)
        self.key(Qt.Key_Right, Qt.ShiftModifier)
        self.assertEqual(self.session.project.buildings[0].footprint[0], [1.1, .01])
        self.key(Qt.Key_C)
        self.text("3;2")
        self.key(Qt.Key_Return)
        self.assertEqual(len(self.session.project.buildings), 2, self.controller.error)
        copied = self.controller.editor.selection[1]
        self.assertNotEqual(copied, "b1")
        expected = model.Project.from_json(self.session.snapshot())
        centre = move.centre(expected, "building", copied)
        move.rotate(expected, "building", copied, *centre, 90)(expected)
        self.key(Qt.Key_R)
        self.text("90")
        self.key(Qt.Key_Return)
        self.assertEqual(self.session.snapshot(), expected.to_json(), self.controller.error)
        self.key(Qt.Key_Escape)
        self.key(Qt.Key_F)
        self.capture("02-copia-ruotata")

    def test_side_length_focus_escape_and_commit(self):
        self.select_building()
        self.click_side(0)
        self.assertTrue(self.controller.sideEditing)
        self.text("45")
        self.capture("03-lato-input")
        self.key(Qt.Key_Escape)
        self.assertFalse(self.controller.sideEditing)
        self.assertTrue(self.plan.hasActiveFocus())
        self.assertEqual(self.session.project.buildings[0].footprint[1], [40, 0])
        self.click_side(0)
        self.text("45")
        self.key(Qt.Key_Return)
        self.assertFalse(self.controller.sideEditing, self.controller.error)
        self.assertTrue(self.plan.hasActiveFocus())
        self.assertAlmostEqual(self.session.project.buildings[0].footprint[1][0], 45)

    def test_mouse_ctrl_copy_and_rotation_steps(self):
        self.select_building()
        self.key(Qt.Key_M)
        self.click((20, 10))
        self.click((22, 12), Qt.ControlModifier)
        self.assertEqual(len(self.session.project.buildings), 2)
        oid = self.controller.editor.selection[1]
        for mods, angle in [(Qt.NoModifier, 15), (Qt.ControlModifier, 20), (Qt.ShiftModifier, 0)]:
            with self.subTest(step=angle):
                self.controller.setTool("rotate")
                g = self.controller.editor.gesture
                about = g.about or g.middle
                start = math.atan2(g.start[1] - about[1], g.start[0] - about[0])
                theta = start + math.radians(22)
                point = (about[0] + 4 * math.cos(theta), about[1] + 4 * math.sin(theta))
                expected = model.Project.from_json(self.session.snapshot())
                move.rotate(expected, "building", oid, *about, angle)(expected)
                self.click(point, mods)
                self.assertEqual(self.session.snapshot(), expected.to_json(), self.controller.error)

    def test_side_invalid_keeps_focus_and_selection(self):
        self.select_building()
        self.click_side(0)
        before = self.session.snapshot()
        self.text("abc")
        self.key(Qt.Key_Return)
        self.assertTrue(self.controller.sideEditing)
        self.assertTrue(self.controller.error)
        self.assertFalse(self.plan.hasActiveFocus(), "Invalid length must keep focus in the field for correction")
        self.assertEqual(self.session.snapshot(), before)
        self.capture("11-lato-invalido")
        self.text("0")
        self.key(Qt.Key_Return)
        self.assertTrue(self.controller.sideEditing)
        self.key(Qt.Key_Escape)
        self.assertEqual(self.controller.editor.selection, ("building", "b1"))
        self.assertFalse(self.controller.sideEditing)

    def test_rotated_side_label_is_clickable(self):
        self.select_building()
        self.plan.setProperty("bearing", 25)
        self.plan.setProperty("zoom", self.plan.property("zoom")*.65)
        self.plan.setProperty("panX", 250)
        self.plan.setProperty("panY", 430)
        APP.processEvents()
        self.click_side(0)
        self.assertTrue(self.controller.sideEditing)
        self.text("41")
        self.key(Qt.Key_Return)
        self.assertAlmostEqual(self.session.project.buildings[0].footprint[1][0], 41)
        self.capture("12-lato-vista-ruotata")

    def test_side_pills_notch_outside_nonoverlap_and_widgets_geometry(self):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPolygonF
        from meridiana.ui.plan import PlanView
        ring = [[0, 0], [12, 0], [12, 8], [6.3, 8], [6.3, 7.7], [6, 7.7], [6, 8], [0, 8]]

        def fixture(project):
            project.buildings[0].footprint = ring
            project.subfields = []
        self.session.edit("Fixture: notched footprint", fixture)
        self.select_building()
        for angle in (0, 25):
            self.plan.setProperty("zoom", 60)
            self.plan.setProperty("panX", 250)
            self.plan.setProperty("panY", 530)
            self.plan.setProperty("bearing", angle)
            APP.processEvents()
            pill = self.visual("sidePill0")
            self.assertIsNotNone(pill)
            raw = pill.parentItem().property("pills")
            actual = raw.toVariant() if hasattr(raw, "toVariant") else raw
            font = next(child.property("font") for child in pill.childItems() if child.property("font") is not None)
            receiver = SimpleNamespace(font=lambda font=font: font,
                                       mapFromScene=lambda point: self.layer.mapToScene(point).toPoint())
            reference = PlanView._side_pills(receiver, ring)
            self.assertEqual([p["side"] for p in actual], [p[0] for p in reference])
            shape = QPolygonF([self.layer.mapToScene(QPointF(x, -y)) for x, y in ring])
            boxes = []
            for got, (side, expected, whole, text) in zip(actual, reference, strict=True):
                box = QRectF(got["x"], got["y"], got["width"], got["height"])
                self.assertEqual(got["whole"], whole, (angle, side))
                self.assertEqual(got["text"], text)
                self.assertLessEqual(abs(box.center().x()-expected.center().x()), 1)
                self.assertLessEqual(abs(box.center().y()-expected.center().y()), 1)
                self.assertLessEqual(abs(box.width()-expected.width()), 1)
                self.assertLessEqual(abs(box.height()-expected.height()), 1)
                self.assertFalse(shape.containsPoint(box.center(), Qt.OddEvenFill), (angle, side))
                self.assertFalse(any(box.intersects(other) for other in boxes))
                if side in (3, 4, 5):
                    self.assertFalse(whole)
                boxes.append(box)
            self.capture("18-quote-tacca-"+str(angle))

    def test_double_click_selected_edge_opens_length(self):
        self.select_building()
        edge = (20, -1/self.plan.property('zoom'))
        self.click(edge)
        self.assertEqual(self.controller.editor.selection, ('building', 'b1'))
        QTest.mouseDClick(self.window, Qt.LeftButton, Qt.NoModifier, self.screen(edge))
        QTest.mouseRelease(self.window, Qt.LeftButton, Qt.NoModifier, self.screen(edge))
        APP.processEvents()
        QTest.qWait(200)
        self.assertTrue(self.controller.sideEditing)
        self.text("42")
        self.key(Qt.Key_Return)
        self.assertAlmostEqual(self.session.project.buildings[0].footprint[1][0], 42)

    def test_move_tab_direction_and_r_uses_clicked_pivot(self):
        self.select_building()
        self.key(Qt.Key_M)
        self.click((5, 5))
        self.text("3")
        self.key(Qt.Key_Tab)
        self.text("90")
        self.key(Qt.Key_Return)
        self.assertEqual(self.session.project.buildings[0].footprint[0], [3, 0])
        self.click((5, 5))
        base = self.controller.editor.gesture.base
        self.key(Qt.Key_R)
        self.assertEqual(self.controller.editor.gesture.about, base)
        self.assertAlmostEqual(base[0], 5, delta=.04)
        self.assertAlmostEqual(base[1], 5, delta=.04)
        expected = model.Project.from_json(self.session.snapshot())
        move.rotate(expected, "building", "b1", *base, 30)(expected)
        self.text("30")
        self.key(Qt.Key_Return)
        self.assertEqual(self.session.snapshot(), expected.to_json())
        self.key(Qt.Key_Escape)
        self.key(Qt.Key_F)
        self.capture("13-ruota-punto-base")

    def test_transform_grip_drag_ctrl_release_then_hot_cycle(self):
        self.select_building()
        self.key(Qt.Key_M)
        self.assertEqual({g["grip"] for g in self.controller.transformGrips}, {"move", "rotate"})
        self.drag([(20, 10), (21, 11), (22, 12)], release_mods=Qt.ControlModifier)
        self.assertEqual(len(self.session.project.buildings), 2, self.controller.error)
        self.assertEqual(self.session.project.buildings[0].footprint[0], [0, 0])
        copy = self.session.project.buildings[1]
        self.assertAlmostEqual(copy.footprint[0][0], 2, delta=.05)
        self.assertAlmostEqual(copy.footprint[0][1], 2, delta=.05)
        self.assertIsNone(self.controller.editor.gesture)
        centre = move.centre(self.session.project, "building", copy.id)
        self.click(centre)
        self.assertTrue(self.controller.hotGrip)
        self.assertEqual(self.controller.editor.gesture.mode, "move")
        self.key(Qt.Key_Space)
        self.assertEqual(self.controller.editor.gesture.mode, "rotate")
        self.assertFalse(self.plan.property("spaceHeld"))
        self.key(Qt.Key_Return)
        self.assertEqual(self.controller.editor.gesture.mode, "move")
        self.assertEqual(self.session.undo.count(), 1)
        self.capture("14-presa-attiva")
        self.key(Qt.Key_Escape)
        self.assertFalse(self.controller.hotGrip)

    def test_rotation_grip_drag_about_middle(self):
        self.select_building()
        self.key(Qt.Key_M)
        expected = model.Project.from_json(self.session.snapshot())
        move.rotate(expected, "building", "b1", 20, 10, 90)(expected)
        self.drag([(20, 20), (13, 17), (10, 10)])
        self.assertEqual(self.session.snapshot(), expected.to_json(), self.controller.error)
        self.key(Qt.Key_Escape)
        self.key(Qt.Key_F)
        self.capture("15-presa-ruota")

    def test_vertex_drag(self):
        self.select_building()
        self.assertTrue(self.controller.grips)
        self.drag([(40, 20), (39, 19), (38, 18)])
        point = self.session.project.buildings[0].footprint[2]
        self.assertAlmostEqual(point[0], 38, delta=.08)
        self.assertAlmostEqual(point[1], 18, delta=.08)
        self.assertEqual(self.session.undo.count(), 1)
        self.capture("04-vertice")

    def test_hover_roof_lights_its_ridge_without_python_pointer_calls(self):
        def roof(p):
            p.subfields.clear()
            p.buildings[0].roof = model.Roof(type='gable', tilt=25)
        self.session.edit('Roof', roof)
        self.controller.refresh()
        self.controller.setTool('select')
        self.controller.calls.clear()
        QTest.mouseMove(self.window, self.screen((20, 4)))
        QTest.qWait(80)
        overlay = self.visual('selectionOverlay')
        ridges = overlay.property('hoveredRidges').toVariant()
        self.assertEqual(len(ridges), 1)
        self.assertEqual(self.controller.calls['pointer'], 0)
        self.assertEqual(ridges[0]['width'], 3.8)
        self.capture('20-colmo-hover')

    def test_move_from_empty_selection_cancel_copy_and_return_from_rotate(self):
        self.controller.editor.select('site', '')
        self.controller._overlays()
        before = self.session.snapshot()
        self.key(Qt.Key_M)
        self.click((0, 10))
        self.assertEqual(self.controller.editor.selection, ('building', 'b1'))
        self.click((5, 5))
        self.key(Qt.Key_C)
        self.key(Qt.Key_R)
        self.assertEqual(self.controller.editor.gesture.mode, 'rotate')
        self.key(Qt.Key_R)
        self.assertEqual(self.controller.editor.gesture.mode, 'move')
        self.key(Qt.Key_Escape)
        self.assertEqual(self.session.snapshot(), before)
        self.assertEqual(self.session.undo.count(), 0)

    def test_side_field_closes_on_pan_without_applying_a_number(self):
        self.select_building()
        before = self.session.snapshot()
        self.click_side(0)
        self.text('42')
        p = QPoint(1100, 600)
        QTest.mousePress(self.window, Qt.MiddleButton, Qt.NoModifier, p)
        QTest.mouseMove(self.window, p+QPoint(40, 30))
        QTest.mouseRelease(self.window, Qt.MiddleButton, Qt.NoModifier, p+QPoint(40, 30))
        self.assertFalse(self.controller.sideEditing)
        self.assertEqual(self.session.snapshot(), before)

    def test_vertex_grips_follow_camera(self):
        self.select_building()

        def descendants(item):
            for child in item.childItems():
                yield child
                yield from descendants(child)

        grips = [item for item in descendants(self.plan) if item.objectName().startswith('vertexGrip')]
        self.assertEqual(len(grips), 4)
        for grip in grips:
            self.assertEqual((grip.width(), grip.height(), grip.property('radius')), (10, 10, 5))
            self.assertEqual(grip.property('color').alpha(), 0)
        for prop, value in [("panX", self.plan.property("panX")+73),
                            ("zoom", self.plan.property("zoom")*.8), ("bearing", 25)]:
            self.plan.setProperty(prop, value)
            APP.processEvents()
            expected = [self.layer.mapToScene(QPointF(x, -y))
                        for x, y in self.session.project.buildings[0].footprint]
            for grip in grips:
                actual = grip.mapToScene(QPointF(5, 5))
                self.assertLess(min(math.hypot(actual.x()-p.x(), actual.y()-p.y()) for p in expected), .01, prop)

    def test_box_crossing_lasso_shift(self):
        self.controller.setPhase("plant")
        m = self.result.modules[0]
        x, y = m.centre
        self.drag([(x-.3, y+.3), (x+.3, y-.3)])          # R529: past the click slop of 6 px
        self.assertEqual(self.controller.editor.swept, [])
        self.drag([(x+.3, y+.3), (x-.3, y-.3)])
        self.assertIn(("s1", m.key), self.controller.editor.swept)
        self.drag([(x+.4, y+.4), (x-.4, y+.4), (x-.4, y-.4), (x+.4, y-.4)], Qt.ControlModifier, hold=370)   # R529: Ctrl takes away
        self.assertEqual(self.controller.editor.swept, [], self.controller.error)
        self.assertFalse(self.controller.error)
        self.capture("05-lasso")

    def test_string_finish_and_erase_inverters(self):
        self.session.project.energy = {"inverters": [{"record": {"model": "Prova", "ac_power_nominal_w": 20000}, "count": 1}]}
        self.controller.setPhase("plant")
        self.controller.setTool("string")
        for m in self.result.modules[:3]:
            self.click(m.centre)
        self.key(Qt.Key_Return)
        self.assertEqual(len(self.controller.editor.runs()[0]["modules"]), 3)
        self.assertTrue([w for w in self.controller.wires if w["kind"] == "string_line"])
        self.assertTrue([label for label in self.controller.labels if label.get("kind") == "number"])
        self.capture("06-stringa")
        self.controller.setTool("erase_inverter")
        self.click(self.result.modules[0].centre)
        self.assertEqual(self.controller.editor.runs()[0]["inverter"], 0)
        self.assertEqual(self.session.project.energy.get("inverters", []), [])
        self.key(Qt.Key_Z, Qt.ControlModifier)
        self.controller.setTool("erase_inverter_strings")
        self.click(self.result.modules[0].centre)
        self.assertEqual(self.controller.editor.runs(), [])
        self.assertEqual(self.session.project.energy.get("inverters", []), [])
        self.capture("07-stringhe-eliminate")

    def test_string_drag_includes_pressed_module(self):
        self.controller.setPhase("plant")
        self.controller.setTool("string")
        modules = self.result.modules[:4]
        self.drag([m.centre for m in modules])
        self.assertEqual(self.controller.editor.draft, [("s1", m.key) for m in modules])
        self.capture("08-stringa-trascinata")
        self.key(Qt.Key_Return)
        self.assertEqual(len(self.controller.editor.runs()[0]["modules"]), 4)

    def test_string_transfer_backspace_cancel_and_single_erase(self):
        self.controller.setPhase("plant")
        self.controller.setTool("string")
        modules = self.result.modules[:4]
        for m in modules[:2]:
            self.click(m.centre)
        self.key(Qt.Key_Return)
        self.controller.setTool("string")
        self.click(modules[0].centre)
        self.assertEqual(self.controller.editor.draft, [])
        self.click(modules[0].centre, Qt.ShiftModifier)
        self.click(modules[2].centre)
        self.key(Qt.Key_Return)
        runs = self.controller.editor.runs()
        self.assertEqual([len(run["modules"]) for run in runs], [1, 2])
        self.assertIn("s1/"+modules[0].key, runs[1]["modules"])
        self.controller.setTool("string")
        self.click(modules[3].centre)
        self.key(Qt.Key_Backspace)
        self.assertEqual(self.controller.editor.draft, [])
        self.click(modules[3].centre)
        saved = self.session.snapshot()
        self.key(Qt.Key_Escape)
        self.assertIsNone(self.controller.editor.draft)
        self.assertEqual(self.session.snapshot(), saved)
        self.capture("16-stringhe-trasferimento")
        self.controller.setTool("erase_string")
        self.click(modules[2].centre)
        self.assertEqual(len(self.controller.editor.runs()), 1)
        self.assertEqual(self.controller.editor.runs()[0]["modules"], ["s1/"+modules[1].key])
        self.assertEqual(self.session.project.subfields[0].removed, [])

    def test_r410_a_ridge_belongs_to_the_building_drawn_over_another(self):
        # 06/11/2026: a building drawn over a larger one, C and two clicks inside it: the ridge went to the larger
        # building below (the first under the first point) and the second click seemed to select another building.
        def over(project):
            project.buildings.append(model.Building(id="b2", name="Sopra", height=4,
                                                    footprint=[[10, 4], [30, 4], [30, 16], [10, 16]]))
        self.session.edit("Fixture: a building over the other", over)
        APP.processEvents()
        self.key(Qt.Key_C)
        self.assertEqual(self.controller.tool, "ridge")
        self.click((11, 13))
        self.click((29, 13))
        APP.processEvents()
        upper, lower = self.session.project.building("b2"), self.session.project.building("b1")
        self.assertEqual(lower.roof.type, "flat")
        self.assertNotEqual(upper.roof.type, "flat")
        self.assertEqual(self.controller.editor.selection, ("building", "b2"))
        if upper.roof.type == "free":                   # off the axis: the top where it was drawn, 3/4 of the depth
            tops = [q for f in upper.roof.free_pitches for q, z in zip(f["ring"], f.get("z") or [], strict=False)
                    if z == max(f.get("z") or [0])]
            self.assertAlmostEqual(tops[0][1], 13, delta=.3)

    def test_string_name_chip_matches_widgets_and_culls_collisions(self):
        from PySide6.QtGui import QColor
        from meridiana.ui.plan import ChipItem
        self.controller.setPhase("plant")

        def fixture(project):
            project.energy["strings"] = {"runs": [
                {"inverter": 1, "mppt": 1, "modules": ["s1/"+m.key]} for m in self.result.modules[:2]]}
        self.session.edit("Fixture: neighbouring strings", fixture)
        self.controller.chooseString(0)
        label = self.visual("stringLabel-name-0")
        self.assertIsNotNone(label)
        # R467: the neighbour's name finds another side of its module instead of being culled; never one on the other
        other = self.visual("stringLabel-name-1")
        self.assertIsNotNone(other)
        self.assertFalse(label.mapRectToScene(label.boundingRect()).intersects(other.mapRectToScene(other.boundingRect())))
        text = next(child for child in label.childItems() if child.property("text") is not None)
        font = text.property("font")
        colour = self.controller.editor.wiring_scene(.02)["colours"][0]
        expected = ChipItem("1.1.1", font, colour, "check", self.controller.planColors, swatch=True)
        self.assertEqual(text.property("text"), expected.text)
        self.assertTrue(font.bold())
        self.assertAlmostEqual(label.property("radius"), label.height()/2)
        # R514: the ends alike (the dot and the state's disc each (h - 14) / 2 from their end), no longer the Widgets'
        # width: the text between them with Theme.space.XS on each side
        gap = (label.height() - 14) / 2
        self.assertAlmostEqual(label.width(), 2 * gap + 8 + 14 + 2 * 4 + text.property('contentWidth'), delta=1)
        self.assertLessEqual(abs(label.width()-expected.rect.width()), 4)
        self.assertLessEqual(abs(label.height()-expected.rect.height()), 1)
        dot = next(child for child in label.childItems() if child.width() == child.height() == 8)
        self.assertAlmostEqual(dot.x()+4, ((label.height()-14)/2+4))      # R514: the dot as far from its end as the state disc
        self.assertAlmostEqual(dot.y()+4, label.height()/2)
        self.assertEqual(dot.property("color"), QColor(colour))
        symbol = next(child for child in label.childItems() if child.property("size") == 14)
        self.assertEqual(symbol.property("name"), expected.symbol_name)
        self.assertAlmostEqual(symbol.x()+symbol.width()/2, label.width()-label.height()/2)
        self.assertAlmostEqual(symbol.y()+symbol.height()/2, label.height()/2)
        self.capture("19-stringa-etichetta")
        self.controller.chooseString(1)
        self.assertIsNotNone(self.visual("stringLabel-name-1"))
        self.assertIsNotNone(self.visual("stringLabel-name-0"))

    def test_a_click_on_a_string_label_reaches_the_module_under_it(self):
        # 06/11/2026: the name label took the click and chose its string; the module under it could not be selected.
        self.controller.setPhase("plant")

        def fixture(project):
            project.energy["strings"] = {"runs": [
                {"inverter": 1, "mppt": 1, "modules": ["s1/"+m.key for m in self.result.modules[:6]]}]}
        self.session.edit("Fixture: one string", fixture)
        self.controller.chooseString(0)
        APP.processEvents()
        label = self.visual("stringLabel-name-0")
        self.assertIsNotNone(label)
        centre = label.mapToScene(QPointF(label.width()/2, label.height()/2))
        world = self.layer.mapFromScene(centre)
        under = self.controller.editor.pick((world.x(), -world.y()))
        self.assertEqual(under[0], "module", under)
        self.assertTrue(under[2], "the label must lie over a module for the proof: "+str(under))
        self.controller.editor.select("", "")
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, centre.toPoint())
        APP.processEvents()
        self.assertEqual(self.controller.editor.selected_module, (under[1], under[2]))

    def test_move_snaps_base_and_destination(self):
        self.select_building()
        self.key(Qt.Key_M)
        self.click((.07, .04))
        self.assertEqual(self.controller.editor.gesture.base, (0, 0))
        self.click((.05, 20.06))
        self.assertEqual(self.session.project.buildings[0].footprint[0], [0, 20])
        self.key(Qt.Key_Escape)
        self.key(Qt.Key_F)
        self.capture("09-sposta-agganciato")

    def test_phase_changes_keep_geometry_and_hint_scope(self):
        counts = []
        self.controller.sceneChanged.connect(lambda: counts.append((len(self.controller.objects), len(self.controller.modules))))
        self.controller.overlayChanged.connect(lambda: counts.append((len(self.controller.objects), len(self.controller.modules))))
        for phase in ("model", "plant", "model"):
            self.controller.setPhase(phase)
            QTest.qWait(25)
            self.assertTrue(self.controller.objects)
            self.assertEqual(len(self.controller.modules), len(self.result.modules))
            self.assertTrue(self.controller.hint)
            self.capture("10-fase-" + phase)
        self.assertTrue(counts)
        self.assertTrue(all(objects and modules for objects, modules in counts))
        self.controller.setPhase("energy")
        self.assertEqual(self.controller.hint, "")

    def test_native_phase_frames_keep_modules_visible(self):
        from quick.parity.realwindow import FrameRecorder, wait_frames
        left = self.screen(self.result.modules[0].centre)
        right = self.screen(self.result.modules[4].centre)
        region = [left.x()-10, left.y()-10, right.x()-left.x()+20, 20]
        with FrameRecorder(self.window, names=("plan", "compass")) as frames:
            wait_frames(frames, 2)
            for phase in ("plant", "model", "plant", "model"):
                before = len(frames.frames)
                self.controller.setPhase(phase)
                wait_frames(frames, before+2)
        frames.assert_valid(stable={"plan": 0, "compass": 0}, regions={"modules": region})
        frames.save(PHOTOS / f"phase-frames-{self.window.devicePixelRatio():g}x-{time.time_ns()}")


if __name__ == "__main__":
    unittest.main()
