"""The plan editor, driven with the mouse and the keyboard as the designer drives it: corners placed with
clicks, Enter closing the outline, a typed length, Esc. They need PySide6 and a display (offscreen will
do); elsewhere they say why they are skipped. No network: the background is off."""

import tempfile
import unittest
from pathlib import Path

import _setup

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class PlanCase(unittest.TestCase):
    """A plan editor alone, 800 x 600, with the pointer and the clicks told to its viewport. No test of its own: the
    classes below share it and each of their tests runs once (study 18, D 5.3: Sides(Drawing) ran eight twice)."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.ui.plan import PlanView
        self.view = PlanView(Path(tempfile.mkdtemp()))
        self.view.set_source("none")
        self.view.resize(800, 600)
        self.view.show()
        self.view.fit()
        self.app.processEvents()
        self.addCleanup(self.view.deleteLater)
        self.addCleanup(self.view.close)

    def move(self, x, y):
        """The pointer over (x, y) metres, told to the view only: QTest.mouseMove would move the real
        pointer of the desktop the tests run on."""
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent

        from meridiana.ui.plan import to_scene
        pos = QPointF(self.view.mapFromScene(to_scene(x, y)))
        event = QMouseEvent(QEvent.Type.MouseMove, pos, self.view.viewport().mapToGlobal(pos),
                            Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(self.view.viewport(), event)
        return pos.toPoint()

    def click(self, x, y, ctrl=False):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        pos = self.move(x, y)
        mods = Qt.KeyboardModifier.ControlModifier if ctrl else Qt.KeyboardModifier.NoModifier
        QTest.mouseClick(self.view.viewport(), Qt.MouseButton.LeftButton, mods, pos)


class Drawing(PlanCase):
    def test_moving_over_the_plan_while_selecting_repaints_nothing(self):
        from PySide6.QtCore import QEvent, QObject

        class Paints(QObject):
            def __init__(self):
                super().__init__()
                self.n = 0

            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.Paint:
                    self.n += 1
                return False
        paints = Paints()
        self.view.viewport().installEventFilter(paints)
        coords = []
        self.view.cursorInfo.connect(coords.append)
        self.view.set_tool("select")
        self.app.processEvents()
        paints.n = 0
        for k in range(10):
            self.move(-10.0 + 2 * k, 3.0)
            self.app.processEvents()
        self.assertEqual(paints.n, 0)                       # nothing on the plan follows the pointer
        self.assertEqual(len(coords), 10)                   # ...but its coordinates do
        from PySide6.QtTest import QTest
        if not QTest.qWaitForWindowExposed(self.view, 2000):
            self.skipTest("the plan's window is not exposed: no paint to count (said, not passed in silence)")
        self.view.set_tool("building")                      # drawing: the guides follow the pointer
        self.app.processEvents()
        paints.n = 0
        self.move(5.0, 5.0)
        self.app.processEvents()
        self.assertGreater(paints.n, 0)

    def test_a_building_is_drawn_with_clicks_and_closed_with_enter(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        drawn = []
        self.view.polygonDrawn.connect(lambda tool, ring: drawn.append((tool, ring)))
        self.view.set_tool("building")
        for x, y in ((-20, -10), (20, -10), (20, 10), (-20, 10)):
            self.click(x, y)
        QTest.keyClick(self.view, Qt.Key.Key_Return)
        self.assertEqual(len(drawn), 1)
        tool, ring = drawn[0]
        self.assertEqual(tool, "building")
        self.assertEqual(len(ring), 4)
        tolerance = 3 * self.view.metres_per_pixel()          # a click lands on a pixel
        for (x, y), (ex, ey) in zip(ring, ((-20, -10), (20, -10), (20, 10), (-20, 10)), strict=True):
            self.assertAlmostEqual(x, ex, delta=tolerance)
            self.assertAlmostEqual(y, ey, delta=tolerance)

    def test_a_typed_length_gives_the_side(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.view.set_tool("building")
        self.click(0, 0)
        self.move(10, 0)                         # pointing East
        QTest.keyClicks(self.view, "25")
        QTest.keyClick(self.view, Qt.Key.Key_Return)
        self.assertEqual(len(self.view.chain), 2)
        self.assertAlmostEqual(self.view.chain[1][0], 25.0, delta=1e-6)
        self.assertAlmostEqual(self.view.chain[1][1], 0.0, delta=1e-6)

    def test_escape_cancels_the_outline(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.view.set_tool("subfield")
        self.click(0, 0)
        self.click(10, 0)
        QTest.keyClick(self.view, Qt.Key.Key_Escape)
        self.assertEqual(self.view.chain, [])

    def test_a_rectangle_by_three_clicks(self):
        drawn = []
        self.view.polygonDrawn.connect(lambda tool, ring: drawn.append(ring))
        self.view.set_tool("building")
        self.view.toggle_rectangle()
        self.click(0, 0)
        self.click(20, 0)
        self.click(15, 8)                          # only its distance from the first side counts
        self.assertEqual(len(drawn), 1)
        ring = drawn[0]
        self.assertEqual(len(ring), 4)
        tol = 3 * self.view.metres_per_pixel()
        self.assertAlmostEqual(ring[2][0], ring[1][0], delta=tol)
        self.assertAlmostEqual(ring[2][1], 8.0, delta=tol)
        self.assertAlmostEqual(ring[3][0], ring[0][0], delta=tol)

    def test_a_small_rectangle_closes_beside_an_edge(self):
        # a chimney of 1.2 m drawn zoomed out, an edge just past its first side: the third click must give
        # the depth, not snap back onto the line of the first side where it meets the edge
        from PySide6.QtCore import QRectF
        drawn = []
        self.view.polygonDrawn.connect(lambda tool, ring: drawn.append(ring))
        self.view.fit(QRectF(-100, -75, 200, 150))
        self.app.processEvents()
        self.assertGreater(10 * self.view.metres_per_pixel(), 1.1)       # the snapping reach covers the edge
        self.view.snapper.set_references([((1.6, -50.0), (1.6, 30.0))])
        self.view.set_tool("exclusion")
        self.view.toggle_rectangle()
        self.click(0, 0, ctrl=True)
        self.click(1.2, 0, ctrl=True)
        self.click(1.2, 1.0)                   # the first corner and the edge are both within reach
        self.assertEqual(len(drawn), 1)
        depth = abs(drawn[0][2][1] - drawn[0][1][1])
        self.assertAlmostEqual(depth, 1.0, delta=3 * self.view.metres_per_pixel())

    def test_a_typed_length_and_turn(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.view.set_tool("building")
        self.click(0, 0)
        self.move(10, 0)
        QTest.keyClicks(self.view, "10")
        QTest.keyClick(self.view, Qt.Key.Key_Return)
        QTest.keyClicks(self.view, "5;90")            # 5 m, turning 90° to the left: North
        QTest.keyClick(self.view, Qt.Key.Key_Return)
        self.assertEqual(len(self.view.chain), 3)
        self.assertAlmostEqual(self.view.chain[2][0], 10.0, places=6)
        self.assertAlmostEqual(self.view.chain[2][1], 5.0, places=6)

    def test_shift_keeps_the_direction(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.view.set_tool("building")
        self.click(0, 0)
        self.move(10, 10)                          # the North-East diagonal
        QTest.keyPress(self.view, Qt.Key.Key_Shift)
        self.move(20, 5)                           # the pointer wanders off it
        p = self.view.snap.point
        self.assertAlmostEqual(p[0], p[1], delta=1e-6)   # still on the diagonal
        QTest.keyRelease(self.view, Qt.Key.Key_Shift)
        self.assertIsNone(self.view.lock_dir)


class Modules(PlanCase):
    """The modules drawn from the arrays of their layout: picked in numpy, kept while their layout is the same
    (task 18c, step 8)."""

    def project(self):
        from meridiana import jobs, model
        p = model.Project()
        p.site = model.Site(lat=45.5226, lon=9.0300, address="Rho (MI)")
        p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                          height=9.5))
        p.subfields.append(model.SubField(id="s1", name="Sud", ring=[[1, 1], [39, 1], [39, 19], [1, 19]], building="b1",
                                          params={"tilt": 15.0}, filled=True))
        results, _keys, _laid = jobs.layout_of(p)
        return p, results

    def test_a_module_is_picked_from_the_array_of_the_corners(self):
        from meridiana.ui.plan import _quad_at, to_scene
        p, results = self.project()
        self.view.show_project(p, results)
        self.view.fit()
        self.app.processEvents()
        r = results["s1"]
        keys, quads = self.view.module_corners["s1"]
        self.assertEqual(keys, [m.key for m in r.modules])
        self.assertEqual(quads.shape, (r.count, 4, 2))
        for m in (r.modules[0], r.modules[len(r.modules) // 2], r.modules[-1]):
            x, y = m.centre
            self.assertEqual(self.view._pick(to_scene(x, y)), ("module", "s1", m.key))
            self.assertEqual(_quad_at(quads, x, -y), keys.index(m.key))
        self.assertEqual(self.view._pick(to_scene(0.3, 0.3))[0], "building")       # the roof outside the area
        self.assertEqual(_quad_at(quads, -5.0, 0.0), -1)
        self.assertEqual(_quad_at(None, 0.0, 0.0), -1)
        self.view.selected_module = ("s1", r.modules[3].key)
        self.view._restyle_selection()
        self.assertEqual(len(self.view.items_by_kind["selection"]), 2)
        self.assertIsNone(self.view._module_polygon("s1", "no:such"))

    def test_the_modules_stay_while_their_layout_is_the_same(self):
        from meridiana import jobs
        p, results = self.project()
        self.view.show_project(p, results)
        [item] = self.view.items_by_kind["modules"]
        p.name = "Renamed"
        self.view.show_project(p, results)                   # a change that moved nothing: the same item
        self.assertEqual(self.view.items_by_kind["modules"], [item])
        self.assertIn(item, self.view.scene().items())
        self.view.show_project(p, results, force=True)       # new colours: drawn again
        [again] = self.view.items_by_kind["modules"]
        self.assertIsNot(again, item)
        self.assertNotIn(item, self.view.scene().items())
        p.subfields[0].params["gap"] = 0.05
        results, _keys, _laid = jobs.layout_of(p)
        self.view.show_project(p, results)                   # a new layout: drawn again, the old one gone
        [third] = self.view.items_by_kind["modules"]
        self.assertIsNot(third, again)
        self.assertNotIn(again, self.view.scene().items())
        self.assertEqual(self.view.module_corners["s1"][0], results["s1"].keys)
        self.view.show_project(p, {})                        # no layout: the modules go
        self.assertEqual(self.view.items_by_kind["modules"], [])
        self.assertNotIn(third, self.view.scene().items())
        self.assertEqual(self.view.module_corners, {})


class Sides(PlanCase):
    """A side picked on the plan, and the sides' measures of the selected outline."""

    def project(self):
        from meridiana import model
        p = model.Project()
        p.buildings.append(model.Building(id="b1", name="Casa", footprint=[[0, 0], [12, 0], [12, 8], [0, 8]],
                                          roof=model.Roof(type="gable", tilt=30.0)))
        self.view.show_project(p, {})
        self.view.fit()
        self.app.processEvents()
        return p

    def test_a_side_is_picked_with_a_click(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.project()
        picked = []
        self.view.edgePicked.connect(lambda *a: picked.append(a))
        self.view.pick_edge("ridge", "building", "b1", [[0, 0], [12, 0], [12, 8], [0, 8]])
        self.move(12.1, 4.0)                                  # near the East side
        self.assertEqual(self.view.edge_hover, 1)
        self.click(12.1, 4.0)
        self.assertEqual(picked, [("ridge", "building", "b1", 1)])
        self.assertIsNone(self.view.edge_pick)
        self.view.pick_edge("eave", "building", "b1", [[0, 0], [12, 0], [12, 8], [0, 8]])
        QTest.keyClick(self.view, Qt.Key.Key_Escape)          # given up: nothing picked
        self.assertIsNone(self.view.edge_pick)
        self.assertEqual(len(picked), 1)

    def test_the_ridge_lights_up_when_the_pointer_passes_over_the_roof(self):
        from PySide6.QtWidgets import QGraphicsLineItem
        self.project()
        self.assertEqual(len(self.view.items_by_kind["arrows"]), 2)        # a slope arrow for each face
        self.view._hover("building", "b1", "")
        lines = [it.line() for it in self.view.hover_item.childItems() if isinstance(it, QGraphicsLineItem)]
        self.assertEqual([(ln.x1(), -ln.y1(), ln.x2(), -ln.y2()) for ln in lines], [(12.0, 4.0, 0.0, 4.0)])
        self.view._hover("pitch", "b1:1", "")                  # over a pitch, the same ridge
        self.assertEqual(len([it for it in self.view.hover_item.childItems() if isinstance(it, QGraphicsLineItem)]), 1)

    def test_a_double_click_on_a_side_of_the_selection_asks_its_length(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.project()
        self.view.set_tool("select")
        # inside the South pitch (not on the ridge, which both pitches share: there the geometry decides, and a
        # pixel either side gave one or the other on Windows): a pitch, the window selects its building; the
        # pitches come in the order of the sides (task 16a), the South one first
        self.click(6.0, 2.0)
        self.assertEqual(self.view.selection, ("pitch", "b1:0"))
        self.view.set_selection("building", "b1")
        asked = []
        self.view.sideClicked.connect(lambda *a: asked.append(a))
        pos = self.move(6.0, 0.05)                            # on the South side
        QTest.mouseDClick(self.view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos)
        self.assertEqual(asked, [("building", "b1", 0)])
        self.view.grab()                                      # the measures draw without complaint

    def test_a_corner_of_the_selection_is_dragged(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.project()
        self.view.set_tool("select")
        self.view.set_selection("building", "b1")
        moved = []
        self.view.vertexMoved.connect(lambda *a: moved.append(a))
        start = self.move(12.0, 8.0)                          # the North-East corner
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, start)
        end = self.move(15.0, 11.0)
        self.assertIsNotNone(self.view.dragging)            # from the first move (the press waits for a chord)
        self.view.grab()                                      # the outline drawn while dragged
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, end)
        self.assertEqual(len(moved), 1)
        kind, oid, vertex, x, y = moved[0]
        self.assertEqual((kind, oid, vertex), ("building", "b1", 2))
        tolerance = 3 * self.view.metres_per_pixel()
        self.assertAlmostEqual(x, 15.0, delta=tolerance)
        self.assertAlmostEqual(y, 11.0, delta=tolerance)
        self.assertIsNone(self.view.dragging)


class MoveCase(PlanCase):
    """The plan with two buildings and a sub-field turned by 30 degrees, for Move; no test of its own."""

    def project(self):
        from meridiana import model
        p = model.Project()
        p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]]))
        p.subfields.append(model.SubField(id="s1", name="Sud", ring=[[10, 5], [30, 5], [30, 15], [10, 15]],
                                          building="b1", pitch=0, params={"azimuth": 30.0}))
        p.buildings.append(model.Building(id="b2", name="Uffici", footprint=[[60, 0], [80, 0], [80, 10], [60, 10]]))
        self.view.show_project(p, {})
        self.view.fit()
        self.app.processEvents()
        self.asked = []
        self.view.transformRequested.connect(lambda kind, oid, what: self.asked.append((kind, oid, dict(what))))
        return p

    def key(self, key, mods=None):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        QTest.keyClick(self.view, key, mods if mods is not None else Qt.KeyboardModifier.NoModifier)


class Moving(MoveCase):
    """Move on the plan (task 16b): the base point and the second point snapped, a value typed, Ctrl at the click that
    copies, R that turns, the arrows, Esc. The plan says what to do; the window applies it (test_window)."""

    def test_two_clicks_give_the_move_from_the_base_point_to_the_second(self):
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("building", "b1")
        self.view.snaps_on = False
        self.click(10.0, 10.0)
        self.assertEqual(self.asked, [])
        self.assertIsNotNone(self.view.gesture.base)
        self.move(13.0, 14.0)
        self.view.grab()                                     # the outlines drawn where they would go
        self.assertEqual(len(self.view._moved_rings()), 2)   # the building and its sub-field
        self.click(13.0, 14.0)
        (kind, oid, what), = self.asked
        tol = 3 * self.view.metres_per_pixel()
        self.assertEqual((kind, oid, what["mode"], what["copy"]), ("building", "b1", "move", False))
        self.assertAlmostEqual(what["dx"], 3.0, delta=tol)
        self.assertAlmostEqual(what["dy"], 4.0, delta=tol)
        self.assertIsNone(self.view.gesture)                 # ready for the next one

    def test_the_points_snap_to_the_corners(self):
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("building", "b1")
        self.click(40.2, 0.1)                                # near the South-East corner of the shed
        self.assertEqual(self.view.gesture.base, (40.0, 0.0))
        self.click(60.1, 0.2)                                # near the South-West corner of the offices
        self.assertEqual(self.asked[0][2]["dx"], 20.0)
        self.assertEqual(self.asked[0][2]["dy"], 0.0)

    def test_a_value_typed_moves_by_it_east_and_north(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("subfield", "s1")
        QTest.keyClicks(self.view, "3;2")
        self.key(Qt.Key.Key_Return)
        self.assertEqual(self.asked, [("subfield", "s1", {"mode": "move", "dx": 3.0, "dy": 2.0, "copy": False})])

    def test_a_distance_typed_goes_along_the_pointer_and_tab_gives_the_direction(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("building", "b1")
        self.view.snaps_on = False
        self.click(10.0, 10.0)
        self.move(10.0, 30.0)                                # pointing North
        QTest.keyClicks(self.view, "5")
        self.view.grab()                                     # the value next to the pointer
        self.key(Qt.Key.Key_Return)
        self.assertAlmostEqual(self.asked[-1][2]["dx"], 0.0, places=6)
        self.assertAlmostEqual(self.asked[-1][2]["dy"], 5.0, places=6)
        self.click(10.0, 10.0)
        QTest.keyClicks(self.view, "2")
        self.key(Qt.Key.Key_Tab)                             # Tab: the direction, a bearing from North
        QTest.keyClicks(self.view, "90")
        self.key(Qt.Key.Key_Return)
        self.assertAlmostEqual(self.asked[-1][2]["dx"], 2.0, places=6)
        self.assertAlmostEqual(self.asked[-1][2]["dy"], 0.0, places=6)

    def test_ctrl_held_at_the_click_makes_a_copy(self):
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("building", "b1")
        self.view.snaps_on = False
        self.click(10.0, 10.0)
        self.click(10.0, -15.0, ctrl=True)
        self.assertTrue(self.asked[0][2]["copy"])

    def test_c_makes_a_copy_too_and_esc_leaves_without_a_move(self):
        from PySide6.QtCore import Qt
        self.project()
        left = []
        self.view.toolLeft.connect(lambda: left.append(True))
        self.view.set_tool("move")
        self.view.set_selection("building", "b1")
        self.view.snaps_on = False
        self.click(10.0, 10.0)
        self.key(Qt.Key.Key_C)
        self.assertTrue(self.view.gesture.copy)
        self.move(12.0, 12.0)
        self.key(Qt.Key.Key_Escape)
        self.assertEqual((self.asked, left), ([], [True]))
        self.assertIsNone(self.view.gesture)

    def test_with_nothing_selected_a_click_picks_what_to_move(self):
        self.project()
        picked = []
        self.view.picked.connect(lambda kind, oid: picked.append((kind, oid)))
        self.view.set_tool("move")
        self.click(70.0, 5.0)
        self.assertEqual(picked, [("building", "b2")])
        self.assertEqual(self.asked, [])

    def test_the_arrows_nudge_the_selection(self):
        from PySide6.QtCore import Qt
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("building", "b2")
        self.key(Qt.Key.Key_Right)
        self.key(Qt.Key.Key_Up, Qt.KeyboardModifier.ShiftModifier)
        self.key(Qt.Key.Key_Left, Qt.KeyboardModifier.ControlModifier)
        moves = [(w["dx"], w["dy"], w["nudge"]) for _k, _o, w in self.asked]
        self.assertEqual(moves, [(0.1, 0.0, True), (0.0, 1.0, True), (-0.01, 0.0, True)])
        self.view.set_tool("select")                         # outside Move the arrows nudge nothing
        self.key(Qt.Key.Key_Right)
        self.assertEqual(len(self.asked), 3)


class Turning(MoveCase):
    """Rotate in the same tool (task 16b, step 3): R inside Move or the Rotate button, about the middle or the base
    point clicked, in steps of 15°, 5° with Ctrl, 90° with Shift, or an angle typed."""

    def point_at(self, cx, cy, degrees, r=10.0):
        import math
        a = math.radians(degrees)
        return cx + r * math.cos(a), cy + r * math.sin(a)

    def test_turning_a_sub_field_by_30_degrees_writes_30_and_asks_for_30(self):
        from PySide6.QtCore import Qt
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("subfield", "s1")
        self.move(30.0, 10.0)                               # East of its middle (20, 10)
        self.key(Qt.Key.Key_R)
        g = self.view.gesture
        self.assertEqual((g.mode, g.about), ("rotate", (20.0, 10.0)))
        self.move(*self.point_at(20.0, 10.0, 32.0))
        self.assertEqual(self.view._move_labels()[0], "rotation 30°")
        self.view.grab()                                    # the turn drawn: the outline, the centre, the two lines
        self.click(*self.point_at(20.0, 10.0, 32.0))
        (kind, oid, what), = self.asked
        self.assertEqual((kind, oid), ("subfield", "s1"))
        self.assertEqual(what, {"mode": "rotate", "cx": 20.0, "cy": 10.0, "degrees": 30.0, "copy": False})

    def test_ctrl_gives_steps_of_5_degrees_and_shift_of_90(self):
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent

        from meridiana.ui.plan import to_scene
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("subfield", "s1")
        self.move(30.0, 10.0)
        self.key(Qt.Key.Key_R)
        for mods, degrees, want in ((Qt.KeyboardModifier.ControlModifier, 32.0, 30.0),
                                    (Qt.KeyboardModifier.ControlModifier, 34.0, 35.0),
                                    (Qt.KeyboardModifier.ShiftModifier, 50.0, 90.0)):
            pos = QPointF(self.view.mapFromScene(to_scene(*self.point_at(20.0, 10.0, degrees))))
            self.app.sendEvent(self.view.viewport(), QMouseEvent(QEvent.Type.MouseMove, pos,
                                                                 self.view.viewport().mapToGlobal(pos),
                                                                 Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, mods))
            with self.subTest(degrees=degrees):
                self.assertEqual(self.view._transform_now()["degrees"], want)

    def test_an_angle_typed_and_enter(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("building", "b2")
        self.key(Qt.Key.Key_R)
        QTest.keyClicks(self.view, "-12,5")
        self.key(Qt.Key.Key_Return)
        self.assertEqual(self.asked, [("building", "b2", {"mode": "rotate", "cx": 70.0, "cy": 5.0, "degrees": -12.5,
                                                          "copy": False})])

    def test_r_after_the_base_point_turns_about_it_and_r_again_goes_back_to_the_move(self):
        from PySide6.QtCore import Qt
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("building", "b1")
        self.click(40.1, 0.1)                                # the South-East corner, snapped
        self.key(Qt.Key.Key_R)
        self.assertEqual(self.view.gesture.about, (40.0, 0.0))
        self.click(40.0, 10.0)                               # North of it: a quarter turn from East
        self.assertEqual(self.asked[0][2]["degrees"], 90.0)
        self.assertEqual((self.asked[0][2]["cx"], self.asked[0][2]["cy"]), (40.0, 0.0))
        self.key(Qt.Key.Key_R)
        self.key(Qt.Key.Key_R)
        self.assertEqual(self.view.gesture.mode, "move")

    def test_the_rotate_button_starts_turning_the_next_object_picked(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.project()
        modes = []
        self.view.moveModeChanged.connect(modes.append)
        self.view.set_tool("move")
        self.view.start_rotate()
        self.click(70.0, 5.0)                                # nothing selected: this picks the offices
        self.view.set_selection("building", "b2")            # as the window does
        QTest.keyClicks(self.view, "90")
        self.key(Qt.Key.Key_Return)
        self.assertEqual(self.asked[0][2]["degrees"], 90.0)
        self.assertEqual(modes[0], "rotate")

    def test_c_copies_a_turn(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("building", "b2")
        self.key(Qt.Key.Key_R)
        self.key(Qt.Key.Key_C)
        QTest.keyClicks(self.view, "45")
        self.key(Qt.Key.Key_Return)
        self.assertTrue(self.asked[0][2]["copy"])


class Grips(MoveCase):
    """The grips of the selection in Move (task 16b, step 4; study 16, B3): in the middle one that moves it, on the
    outline one that turns it; Enter or Space go round the modes, as AutoCAD's grips."""

    def drag(self, start, end, mods=None):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        mods = mods if mods is not None else Qt.KeyboardModifier.NoModifier
        pos = self.move(*start)
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton, mods, pos)
        self.move((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        pos = self.move(*end)
        self.view.grab()                                     # the grips and the outline drawn while dragged
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton, mods, pos)

    def test_the_grips_are_in_the_middle_and_on_the_northern_side_only_with_move(self):
        self.project()
        self.view.set_selection("building", "b1")
        self.assertEqual(self.view._grips(), {})             # Select: none (study 16, B8: only with the tool)
        self.view.set_tool("move")
        self.assertEqual(self.view._grips(), {"move": (20.0, 10.0), "rotate": (20.0, 20.0)})

    def test_dragging_the_middle_grip_is_a_move(self):
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("building", "b1")
        self.view.snaps_on = False
        self.drag((20.0, 10.0), (23.0, 14.0))
        (kind, oid, what), = self.asked
        tol = 3 * self.view.metres_per_pixel()
        self.assertEqual((kind, oid, what["mode"], what["copy"]), ("building", "b1", "move", False))
        self.assertAlmostEqual(what["dx"], 3.0, delta=tol)
        self.assertAlmostEqual(what["dy"], 4.0, delta=tol)
        self.assertIsNone(self.view.gesture)

    def test_ctrl_held_at_the_release_of_a_grip_copies(self):
        from PySide6.QtCore import Qt
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("building", "b1")
        self.drag((20.0, 10.0), (20.0, -20.0), Qt.KeyboardModifier.ControlModifier)
        self.assertTrue(self.asked[0][2]["copy"])

    def test_dragging_the_grip_on_the_outline_turns_about_the_middle(self):
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("building", "b1")
        self.drag((20.0, 20.0), (10.0, 10.0))                # from North of the middle to West of it: 90° left
        (_kind, _oid, what), = self.asked
        self.assertEqual(what, {"mode": "rotate", "cx": 20.0, "cy": 10.0, "degrees": 90.0, "copy": False})

    def test_a_grip_clicked_is_hot_and_enter_or_space_go_round_the_modes(self):
        from PySide6.QtCore import Qt
        self.project()
        self.view.set_tool("move")
        self.view.set_selection("building", "b1")
        self.click(20.0, 10.0)
        g = self.view.gesture
        self.assertEqual((g.grip, g.mode, g.base), (True, "move", (20.0, 10.0)))
        self.key(Qt.Key.Key_Return)
        self.assertEqual((g.mode, g.about), ("rotate", (20.0, 10.0)))
        self.key(Qt.Key.Key_Space)
        self.assertEqual(g.mode, "move")
        self.view.snaps_on = False
        self.click(25.0, 10.0)                               # the next click ends it
        self.assertAlmostEqual(self.asked[0][2]["dx"], 5.0, delta=3 * self.view.metres_per_pixel())


class Widths(unittest.TestCase):
    """The strokes of the plan and of the 3D view's outline (R35: «un buono spessore a tutto»; view_colours)."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_plan_draws_with_the_widths_of_view_colours(self):
        from PySide6.QtCore import Qt

        from _fixtures import plan_view
        from meridiana import view_colours
        from meridiana.ui.view3d import View3D
        plan, _results = plan_view(self)
        widths = {kind: plan.items_by_kind[kind][0].pen().widthF() for kind in ("building", "subfield")}
        self.assertEqual(widths, {"building": view_colours.WIDTHS["building"],
                                  "subfield": view_colours.WIDTHS["subfield"]})
        plan.set_selection("subfield", "s1")                # what the window does at a selection
        line = max(it.pen().widthF() for it in plan.items_by_kind["selection"]
                   if it.brush().style() == Qt.BrushStyle.NoBrush)
        self.assertEqual(line, view_colours.WIDTHS["select"])
        self.assertEqual(View3D.WIDTHS, view_colours.RIBBONS)


class PlanNavigation(unittest.TestCase):
    """The plan's navigation with the same style as the 3D view (study 15, 2.6): the middle pans and a short middle
    click recentres, the right click asks for the menu, AutoCAD's orbit does nothing on a plan; left then right
    together pan without selecting or drawing, a left click held still acts after a moment. The plan alone with the
    shed (_fixtures.plan_view); the window's style chosen in the preferences is in finestra/test_views_navigation."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from _fixtures import plan_view
        self.plan, self.results = plan_view(self)
        self.picked = []                                    # what the window would select: an object or a module
        self.plan.picked.connect(lambda kind, oid: self.picked.append((kind, oid)))
        self.plan.moduleClicked.connect(lambda sid, key: self.picked.append(("subfield", sid)))
        self.modules = []
        self.plan.moduleClicked.connect(lambda sid, key: self.modules.append((sid, key)))

    def send(self, kind, button, pos, buttons=None):
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtWidgets import QApplication
        vp = self.plan.viewport()
        e = QMouseEvent(kind, QPointF(pos), QPointF(vp.mapToGlobal(pos)), button,
                        buttons if buttons is not None else button, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(vp, e)

    def test_the_plan_pans_zooms_and_recentres_with_the_same_style(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtGui import QMouseEvent
        plan, send = self.plan, self.send
        vp = plan.viewport()
        menus = []
        plan.menuRequested.connect(menus.append)
        centre = plan.mapToScene(vp.rect().center())
        send(QMouseEvent.Type.MouseButtonPress, Qt.MouseButton.MiddleButton, QPoint(200, 200))
        send(QMouseEvent.Type.MouseMove, Qt.MouseButton.NoButton, QPoint(260, 230), Qt.MouseButton.MiddleButton)
        send(QMouseEvent.Type.MouseButtonRelease, Qt.MouseButton.MiddleButton, QPoint(260, 230),
             Qt.MouseButton.NoButton)
        moved = plan.mapToScene(vp.rect().center())
        self.assertAlmostEqual((centre - moved).x(), 60 * plan.metres_per_pixel(), delta=plan.metres_per_pixel())
        here = plan.mapToScene(QPoint(100, 120))
        send(QMouseEvent.Type.MouseButtonPress, Qt.MouseButton.MiddleButton, QPoint(100, 120))
        send(QMouseEvent.Type.MouseButtonRelease, Qt.MouseButton.MiddleButton, QPoint(100, 120),
             Qt.MouseButton.NoButton)
        now = plan.mapToScene(vp.rect().center())
        self.assertLessEqual((now - here).manhattanLength(), 2 * plan.metres_per_pixel() + 1e-9)     # recentred
        send(QMouseEvent.Type.MouseButtonPress, Qt.MouseButton.RightButton, QPoint(50, 50))
        send(QMouseEvent.Type.MouseButtonRelease, Qt.MouseButton.RightButton, QPoint(50, 50), Qt.MouseButton.NoButton)
        self.assertEqual(menus, [QPoint(50, 50)])
        scale = plan.metres_per_pixel()
        send(QMouseEvent.Type.MouseButtonPress, Qt.MouseButton.RightButton, QPoint(50, 50))       # AutoCAD: orbit
        send(QMouseEvent.Type.MouseMove, Qt.MouseButton.NoButton, QPoint(120, 50), Qt.MouseButton.RightButton)
        send(QMouseEvent.Type.MouseButtonRelease, Qt.MouseButton.RightButton, QPoint(120, 50), Qt.MouseButton.NoButton)
        self.assertEqual(plan.metres_per_pixel(), scale)    # the orbit does nothing on the plan
        self.assertEqual(len(menus), 1)

    def test_in_the_plan_left_then_right_pans_without_selecting_or_drawing(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtGui import QMouseEvent
        plan, send = self.plan, self.send
        vp = plan.viewport()
        L, R, NONE = Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton, Qt.MouseButton.NoButton

        def chord(at, to):
            send(QMouseEvent.Type.MouseButtonPress, L, at, L)               # the left one a moment first
            send(QMouseEvent.Type.MouseButtonPress, R, at, L | R)
            send(QMouseEvent.Type.MouseMove, NONE, to, L | R)
            send(QMouseEvent.Type.MouseButtonRelease, L, to, R)
            send(QMouseEvent.Type.MouseButtonRelease, R, to, NONE)

        def on_it():
            return plan.mapFromScene(plan.items_by_kind["subfield"][0].sceneBoundingRect().center())
        sid = "s1"
        plan.set_selection("site", "")
        centre = plan.mapToScene(vp.rect().center())
        chord(on_it(), on_it() + QPoint(80, 0))
        self.assertEqual(self.picked, [])                       # nothing selected by the left press
        self.assertAlmostEqual((centre - plan.mapToScene(vp.rect().center())).x(), 80 * plan.metres_per_pixel(),
                               delta=plan.metres_per_pixel())
        plan.set_tool("subfield")
        chord(on_it(), on_it() + QPoint(0, 60))
        self.assertEqual(plan.chain, [])                        # no corner drawn by it
        plan.set_tool("select")
        at = on_it()                                            # moved by the pans
        send(QMouseEvent.Type.MouseButtonPress, L, at, L)       # a plain click selects, as before
        send(QMouseEvent.Type.MouseButtonRelease, L, at, NONE)
        self.assertEqual(self.picked, [("subfield", sid)])
        self.picked.clear()
        plan.set_selection("site", "")
        self.app.processEvents()
        send(QMouseEvent.Type.MouseButtonPress, L, on_it(), L)  # held still: it acts after a moment
        self.assertTrue(_setup.wait_until(self.app, lambda: self.picked == [("subfield", sid)], 1))
        send(QMouseEvent.Type.MouseButtonRelease, L, on_it(), NONE)

    def test_a_touchpad_tap_takes_a_module_within_six_logical_pixels(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QMouseEvent

        from meridiana.ui.plan import to_scene
        plan, send = self.plan, self.send
        r = self.results["s1"]
        m = max(r.modules, key=lambda pm: pm.centre[0])
        mpp = plan.metres_per_pixel()
        x = max(c[0] for c in m.corners) + 3 * mpp

        def tap():
            at = plan.mapFromScene(to_scene(x, m.centre[1]))
            send(QMouseEvent.Type.MouseButtonPress, Qt.MouseButton.LeftButton, at)
            send(QMouseEvent.Type.MouseButtonRelease, Qt.MouseButton.LeftButton, at, Qt.MouseButton.NoButton)

        tap()
        self.assertEqual(self.modules, [("s1", m.key)])
        self.modules.clear()
        plan.selected_module = ("", "")
        plan.set_selection("site", "")
        x = max(c[0] for c in m.corners) + 7 * mpp
        tap()
        self.assertEqual(self.modules, [])

    def test_two_taps_select_the_row_and_escape_goes_to_the_container(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtTest import QTest

        from meridiana.ui.plan import to_scene
        plan, send = self.plan, self.send
        m = next(pm for pm in self.results["s1"].modules if pm.rid and pm.level == 0)
        at = plan.mapFromScene(to_scene(*m.centre))
        for _click in range(2):
            send(QMouseEvent.Type.MouseButtonPress, Qt.MouseButton.LeftButton, at)
            send(QMouseEvent.Type.MouseButtonRelease, Qt.MouseButton.LeftButton, at, Qt.MouseButton.NoButton)
        self.assertEqual(plan.selection, ("row", f"s1/{m.rid}"))
        QTest.keyClick(plan, Qt.Key.Key_Escape)
        self.assertEqual(plan.selection, ("subfield", "s1"))
        QTest.keyClick(plan, Qt.Key.Key_Escape)
        self.assertEqual(plan.selection, ("building", "b1"))
        QTest.keyClick(plan, Qt.Key.Key_Escape)
        self.assertEqual(plan.selection, ("site", ""))

    def test_escape_leaves_a_module_for_its_subfield(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtTest import QTest

        from meridiana.ui.plan import to_scene
        plan, send = self.plan, self.send
        m = self.results["s1"].modules[0]
        at = plan.mapFromScene(to_scene(*m.centre))
        send(QMouseEvent.Type.MouseButtonPress, Qt.MouseButton.LeftButton, at)
        send(QMouseEvent.Type.MouseButtonRelease, Qt.MouseButton.LeftButton, at, Qt.MouseButton.NoButton)
        self.assertEqual(plan.selected_module, ("s1", m.key))
        QTest.keyClick(plan, Qt.Key.Key_Escape)
        self.assertEqual((plan.selection, plan.selected_module), (("subfield", "s1"), ("", "")))

    def test_a_double_tap_selects_the_row_and_still_reports_the_double_click(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QMouseEvent

        from meridiana.ui.plan import to_scene
        plan, send = self.plan, self.send
        m = next(pm for pm in self.results["s1"].modules if pm.rid and pm.level == 0)
        at = plan.mapFromScene(to_scene(*m.centre))
        doubled = []
        plan.moduleDoubleClicked.connect(lambda sfid, key: doubled.append((sfid, key)))
        L, NONE = Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton
        for kind, buttons in ((QMouseEvent.Type.MouseButtonPress, L), (QMouseEvent.Type.MouseButtonRelease, NONE),
                              (QMouseEvent.Type.MouseButtonPress, L), (QMouseEvent.Type.MouseButtonDblClick, L),
                              (QMouseEvent.Type.MouseButtonRelease, NONE)):
            send(kind, L, at, buttons)
        self.assertEqual(plan.selection, ("row", f"s1/{m.rid}"))
        self.assertEqual(doubled, [("s1", m.key)])

    def native(self, kind, value=0.0, modifiers=None):
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QNativeGestureEvent, QPointingDevice
        from PySide6.QtWidgets import QApplication
        at = QPointF(self.plan.viewport().rect().center())
        event = QNativeGestureEvent(kind, QPointingDevice.primaryPointingDevice(), 2, at, at,
                                    QPointF(self.plan.viewport().mapToGlobal(at.toPoint())), value, QPointF())
        event.setModifiers(modifiers or Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(self.plan.viewport(), event)
        return event

    def test_native_pinch_two_finger_scroll_and_ctrl_scroll_drive_the_plan(self):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import QApplication
        plan = self.plan
        scale = plan.transform().m11()
        event = self.native(Qt.NativeGestureType.ZoomNativeGesture, 0.25)
        self.assertTrue(event.isAccepted())
        self.assertAlmostEqual(plan.transform().m11(), scale * 1.25)
        centre = plan.mapToScene(plan.viewport().rect().center())
        at = QPointF(300, 250)
        wheel = QWheelEvent(at, QPointF(plan.viewport().mapToGlobal(at.toPoint())), QPoint(18, -12), QPoint(),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                            Qt.ScrollPhase.ScrollUpdate, False)
        QApplication.sendEvent(plan.viewport(), wheel)
        self.assertLess((plan.mapToScene(plan.viewport().rect().center()) - centre).manhattanLength(), 200)
        self.assertNotEqual(plan.mapToScene(plan.viewport().rect().center()), centre)
        scale = plan.transform().m11()
        wheel = QWheelEvent(at, QPointF(plan.viewport().mapToGlobal(at.toPoint())), QPoint(0, 30), QPoint(),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.ControlModifier,
                            Qt.ScrollPhase.ScrollUpdate, False)
        QApplication.sendEvent(plan.viewport(), wheel)
        self.assertAlmostEqual(plan.transform().m11(), scale * 1.2 ** 0.5)

    def test_string_chips_use_the_design_radius_font_and_drawn_symbols(self):
        from meridiana.ui import design
        from meridiana.ui.plan import ChipItem
        chip = ChipItem("1.3.1", design.font(design.Type.SMALL, design.Type.BOLD, self.plan.font()),
                        "#06d6a0", "check", self.plan.colours)
        self.assertEqual(chip.text, "1.3.1")
        self.assertEqual(chip.symbol_name, "warning")
        self.assertEqual(chip.radius, design.Radius.INNER)
        self.assertEqual(chip.font().family(), self.plan.font().family())
        self.assertTrue(chip.boundingRect().width() > 16)
        self.assertFalse(chip.childItems())


if __name__ == "__main__":
    unittest.main()
