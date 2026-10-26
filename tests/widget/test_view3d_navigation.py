"""The mouse in the 3D view alone, as the navigation style says (study 15, 2.6): the camera of camera.py driven by
navigation.py and bound in QML, the pivot under the cursor shown while orbiting and on passing over with the orbit's
key held, the wheel towards the cursor, the middle click that recentres, the double click that fits, the animation;
the gizmo of Move and Rotate, its handles, its drags and what it hands to the window. The 3D view is made alone with
the shed of _fixtures, as the window shows it (_fixtures.view3d): what the window does with the preferences and with
the gizmo's moves is in finestra/test_views_navigation.py, the plan's navigation in widget/test_plan.py. PySide6 and
a display (offscreen will do)."""

import unittest

import numpy as np

import _setup
from _fixtures import view3d
from _setup import wait_until

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

LEFT, RIGHT, MIDDLE = 1, 2, 4
SHIFT = 0x02000000
CTRL = 0x04000000


class Navigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.view, self.results = view3d(self)
        self.backend = self.view.backend
        self.wait = wait_until

    def drag(self, button, mods, start, end, steps=5):
        b = self.backend
        b.press(button, mods, *start, False, 0, 0, 0, "", -1)
        for i in range(1, steps + 1):
            b.move(mods, start[0] + (end[0] - start[0]) * i / steps, start[1] + (end[1] - start[1]) * i / steps)
        b.release(button, mods, *end)

    def test_shift_and_middle_orbit_around_the_point_under_the_cursor(self):
        b = self.backend
        w, h = b.size
        seen = []
        b.cameraChanged.connect(lambda: seen.append(b.orbiting))
        bearing = b.camera.bearing()
        start = (w * 0.6, h * 0.7)
        ground = b.camera.ground(*start, w, h)
        self.drag(MIDDLE, SHIFT, start, (start[0] + 40, start[1]))      # AutoCAD: Shift + middle orbits
        self.assertAlmostEqual(b.camera.bearing(), (bearing + 40 * 0.35) % 360, places=4)
        self.assertTrue(np.allclose(b._pivot, ground))
        self.assertIn(True, seen)                           # the indicator shown while orbiting
        self.assertFalse(b.orbiting)                        # and gone after
        self.assertAlmostEqual(abs(b.camera.right()[1]), 0.0, places=9)    # turntable: the vertical stays

    # the pivot's cross-hair (task 16g, study 16 G): three rings and a dot on the pivot, PIVOT_PX pixels wide

    def marker(self):
        """The cross-hair's node in the scene and the view that holds it."""
        from PySide6.QtCore import QObject
        root = self.view.rootObject()
        return root.findChild(QObject, "pivotMarker"), root.findChild(QObject, "crossHair")

    def test_the_cross_hair_shows_on_the_pivot_during_the_orbit_and_not_after(self):
        b = self.backend
        w, h = b.size
        seen = []
        b.markerChanged.connect(lambda: seen.append(b.pivotVisible))
        node, view = self.marker()
        self.assertFalse(b.pivotVisible)
        self.assertFalse(node.property("visible"))
        self.assertFalse(view.property("visible"))                 # not drawn at all at rest
        start = (w * 0.6, h * 0.7)
        ground = b.camera.ground(*start, w, h)
        b.press(MIDDLE, SHIFT, *start, False, 0, 0, 0, "", -1)
        self.assertFalse(b.pivotVisible)                           # a press is not yet an orbit
        b.move(SHIFT, start[0] + 30, start[1])
        self.assertTrue(b.pivotVisible)
        p = b.pivot
        self.assertTrue(np.allclose((p.x(), p.y(), p.z()), ground, atol=1e-4))      # on the pivot of the orbit
        at = node.property("position")
        self.assertTrue(np.allclose((at.x(), at.y(), at.z()), ground, atol=1e-4))   # and the scene follows
        self.assertTrue(node.property("visible") and view.property("visible"))
        b.release(MIDDLE, SHIFT, start[0] + 30, start[1])
        self.assertFalse(b.pivotVisible)
        self.assertFalse(node.property("visible"))
        self.assertFalse(view.property("visible"))
        self.assertIn(True, seen)

    def test_the_cross_hair_is_as_wide_on_the_screen_wherever_the_pivot_is(self):
        from meridiana.ui import view3d
        b = self.backend
        w, h = b.size
        node, _view = self.marker()
        for ortho in (False, True):
            b.set_ortho(ortho)
            for start, steps in (((w * 0.5, h * 0.5), 0.0), ((w * 0.2, h * 0.8), 0.0), ((w * 0.7, h * 0.4), 3.0)):
                b.wheel(steps, 0, w / 2, h / 2, False, 0, 0, 0)         # nearer, then the view as it was framed
                b.press(MIDDLE, SHIFT, *start, False, 0, 0, 0, "", -1)
                b.move(SHIFT, start[0] + 10, start[1])
                with self.subTest(ortho=ortho, start=start, steps=steps):
                    s = node.property("scale")
                    self.assertEqual((s.x(), s.y(), s.z()), (s.x(), s.x(), s.x()))
                    p = b.pivot
                    centre = np.array((p.x(), p.y(), p.z()))
                    x0, y0 = b.camera.project(centre, w, h)
                    x1, y1 = b.camera.project(centre + b.camera.right() * s.x(), w, h)
                    self.assertAlmostEqual(x1 - x0, view3d.PIVOT_PX, places=3)      # the ring's radius, in pixels
                    self.assertAlmostEqual(y1, y0, places=3)
                b.release(MIDDLE, SHIFT, start[0] + 10, start[1])
        b.set_ortho(False)

    def test_the_cross_hair_is_three_rings_a_halo_and_a_dot_that_nothing_picks_and_no_shadow_falls_on(self):
        from PySide6.QtCore import QObject
        view = self.view
        root = view.rootObject()
        rings = view.pivot_rings.vertexData().size() // 40       # the stride of BuildingsGeometry
        halo = view.pivot_halo.vertexData().size() // 40
        self.assertEqual(rings, 3 * 48 * 8 * 3)                  # three rings of 48 segments, square tubes
        self.assertEqual(halo, 3 * 48 * 6)                       # and the three bands under them
        for name in ("pivotRings", "pivotHalo", "pivotDot"):
            model = root.findChild(QObject, name)
            with self.subTest(name=name):
                self.assertFalse(model.property("pickable"))
                self.assertFalse(model.property("castsShadows"))
                self.assertFalse(model.property("receivesShadows"))
        self.assertAlmostEqual(self.backend.pivotHaloOpacity, 0.7)
        self.assertEqual(self.backend.pivotColor, "#7dff6a")

    def test_a_pivot_that_left_the_view_comes_back_to_the_middle_at_its_depth(self):
        b = self.backend
        w, h = b.size
        b.pivot_mode = "selection"
        far = b.camera.target + b.camera.right() * 900.0 - b.camera.forward() * 15.0     # far to the right
        b.selection_centre = far
        self.assertFalse(0 <= b.camera.project(far, w, h)[0] <= w)
        depth = float(np.dot(far - b.camera.position, b.camera.forward()))
        self.drag(MIDDLE, SHIFT, (300, 300), (330, 300))
        # the orbit turned the camera about the pivot, which therefore stayed at the middle of the view and as far
        # from the camera as the point was deep before: the same depth, on the axis
        self.assertAlmostEqual(float(np.linalg.norm(b._pivot - b.camera.position)), depth, places=6)
        self.assertTrue(np.allclose(b.camera.project(b._pivot, w, h), (w / 2, h / 2), atol=1e-3))

    def test_a_pivot_in_the_view_is_left_where_it_is(self):
        b = self.backend
        b.pivot_mode = "selection"
        b.selection_centre = b.camera.target + b.camera.up() * 2.0
        self.drag(MIDDLE, SHIFT, (300, 300), (330, 300))
        self.assertTrue(np.allclose(b._pivot, b.selection_centre))

    # the pivot shown on passing over, with the orbit's key held (task 16g, study 16 G2)

    def pass_over(self, mods, x, y, hit=None):
        """What QML does at a move with no button held: the move, the pick when the backend asks for one, the
        hover of the pivot. `hit` is the point the pick would give."""
        b = self.backend
        b.move(mods, x, y)
        if hit is not None and b.pivotPick(mods):
            b.pivotHover(mods, x, y, True, *hit)
        else:
            b.pivotHover(mods, x, y, False, 0.0, 0.0, 0.0)

    def seen_at(self):
        p = self.backend.pivot
        return np.array((p.x(), p.y(), p.z()))

    def test_with_shift_held_the_cross_hair_follows_the_pointer_to_the_ground_under_it(self):
        b = self.backend
        w, h = b.size
        node, view = self.marker()
        for at in ((w * 0.4, h * 0.75), (w * 0.7, h * 0.6)):
            self.pass_over(SHIFT, *at)
            with self.subTest(at=at):
                self.assertTrue(b.pivotVisible)
                self.assertTrue(np.allclose(self.seen_at(), b.camera.ground(*at, w, h), atol=1e-4))
        self.assertTrue(node.property("visible") and view.property("visible"))
        self.assertFalse(b.orbiting)                                # it is not an orbit

    def test_over_the_model_it_stands_on_the_point_of_the_model(self):
        b = self.backend
        w, h = b.size
        at = (w * 0.5, h * 0.55)
        origin, direction = b.camera.ray(*at, w, h)
        roof = origin + direction * 25.0                            # what the pick would say is under the pointer
        self.pass_over(SHIFT, *at, hit=roof)
        self.assertTrue(np.allclose(self.seen_at(), roof, atol=1e-4))

    def test_without_the_key_or_with_another_it_does_not_show(self):
        b = self.backend
        w, h = b.size
        CTRL = 0x04000000
        for mods in (0, CTRL, SHIFT | CTRL):
            self.pass_over(mods, w * 0.4, h * 0.75)
            with self.subTest(mods=mods):
                self.assertFalse(b.pivotVisible)
                self.assertFalse(b.pivotPick(mods))                 # and no pick is asked for
        self.assertTrue(b.pivotPick(SHIFT))                         # the key of AutoCAD's orbit: asked

    def test_the_cross_hair_goes_when_the_key_is_let_go_or_the_pointer_leaves(self):
        b = self.backend
        w, h = b.size
        self.pass_over(SHIFT, w * 0.4, h * 0.75)
        self.assertTrue(b.pivotVisible)
        self.pass_over(0, w * 0.41, h * 0.75)                      # the key up, the pointer moving
        self.assertFalse(b.pivotVisible)
        self.pass_over(SHIFT, w * 0.4, h * 0.75)
        b.pivotHover(0, 0, 0, False, 0, 0, 0)                      # what QML says on leaving the view
        self.assertFalse(b.pivotVisible)

    def test_with_the_pointer_still_the_keyboard_is_asked_and_the_cross_hair_goes_with_the_key(self):
        from PySide6.QtCore import Qt
        b = self.backend
        w, h = b.size
        self.assertFalse(b._keys.isActive())
        self.pass_over(SHIFT, w * 0.4, h * 0.75)
        self.assertTrue(b._keys.isActive())                         # asked a few times a second, from now on
        self.assertEqual(b._keys.interval(), 100)
        b.key_modifiers = lambda: Qt.KeyboardModifier.ShiftModifier
        b._poll_keys()
        self.assertTrue(b.pivotVisible)                             # the key is still down
        b.key_modifiers = lambda: Qt.KeyboardModifier.NoModifier
        b._poll_keys()                                              # let go with the pointer still
        self.assertFalse(b.pivotVisible)
        self.assertFalse(b._keys.isActive())                        # and nothing is asked any more

    def test_a_button_held_with_the_key_keeps_the_cross_hair_until_the_orbit_begins(self):
        from PySide6.QtCore import Qt
        b = self.backend
        w, h = b.size
        at = (w * 0.4, h * 0.75)
        self.pass_over(SHIFT, *at)
        shown = self.seen_at()
        b.press(MIDDLE, SHIFT, *at, False, 0, 0, 0, "", -1)
        b.key_modifiers = lambda: Qt.KeyboardModifier.ShiftModifier
        b._poll_keys()
        self.assertTrue(b.pivotVisible)                             # pressed, not yet moved: still the same cross-hair
        b.move(SHIFT, at[0] + 20, at[1])                            # the orbit begins: it stops on the pivot
        self.assertTrue(b.orbiting)
        self.assertIsNone(b._hint)
        self.assertTrue(np.allclose(self.seen_at(), shown, atol=1e-4))
        self.assertTrue(np.allclose(b._pivot, shown, atol=1e-4))
        b.release(MIDDLE, SHIFT, at[0] + 20, at[1])
        self.assertFalse(b.pivotVisible)                            # and goes at the release
        self.pass_over(SHIFT, at[0] + 20, at[1])
        self.assertTrue(b.pivotVisible)                             # to come back with the next move, the key down

    def test_a_wheel_or_a_pan_takes_it_away_until_the_pointer_moves_again(self):
        b = self.backend
        w, h = b.size
        at = (w * 0.4, h * 0.75)
        self.pass_over(SHIFT, *at)
        b.wheel(1.0, SHIFT, *at, False, 0, 0, 0)                    # the ground under the pointer is not the same now
        self.assertFalse(b.pivotVisible)
        self.pass_over(SHIFT, *at)
        self.assertTrue(b.pivotVisible)
        self.assertTrue(np.allclose(self.seen_at(), b.camera.ground(*at, w, h), atol=1e-4))

    def test_the_preference_switches_it_off_and_a_style_without_a_key_has_none(self):
        b = self.backend
        w, h = b.size
        self.view.set_navigation("autocad", "turntable", "cursor", False)
        self.assertFalse(b.pivot_hint)
        self.pass_over(SHIFT, w * 0.4, h * 0.75)
        self.assertFalse(b.pivotVisible)
        self.assertFalse(b.pivotPick(SHIFT))
        self.view.set_navigation("autocad", "turntable", "cursor", True)
        self.pass_over(SHIFT, w * 0.4, h * 0.75)
        self.assertTrue(b.pivotVisible)
        self.view.set_navigation("blender", "turntable", "cursor")      # a button alone orbits: no key to hold
        self.assertFalse(b.pivotVisible)                            # the old style's cross-hair went
        self.pass_over(SHIFT, w * 0.4, h * 0.75)
        self.assertFalse(b.pivotVisible)
        self.assertTrue(b.pivot_hint)                               # the choice itself is kept (the window's: finestra)

    def test_with_the_selection_or_the_middle_as_the_centre_the_pointer_does_not_choose_it(self):
        b = self.backend
        w, h = b.size
        b.set_pivot("centre", True)
        self.pass_over(SHIFT, w * 0.4, h * 0.75)
        self.assertFalse(b.pivotPick(SHIFT))                        # no pick for what the pointer does not decide
        self.assertTrue(np.allclose(self.seen_at(), b.camera.target, atol=1e-4))
        b.set_pivot("selection", True)
        self.assertTrue(b.pivotPick(SHIFT))                         # no selection: it is the point under the cursor
        b.selection_centre = b.camera.target + b.camera.up() * 2.0
        self.assertFalse(b.pivotPick(SHIFT))
        self.pass_over(SHIFT, w * 0.4, h * 0.75)
        self.assertTrue(np.allclose(self.seen_at(), b.selection_centre, atol=1e-4))

    # «Fix the pivot here»: the short middle click leaves the cross-hair for a second; with the middle of the view
    # as the pivot it stays on the target always, because there it truly is the pivot

    def click_middle(self, at):
        b = self.backend
        b.press(MIDDLE, 0, *at, False, 0, 0, 0, "", -1)
        b.release(MIDDLE, 0, *at)

    def test_a_short_middle_click_leaves_the_cross_hair_on_the_point_for_a_second(self):
        b = self.backend
        w, h = b.size
        node, view = self.marker()
        at = (w * 0.65, h * 0.7)
        point = b.camera.ground(*at, w, h)
        self.assertFalse(b.pivotVisible)
        self.click_middle(at)
        self.assertTrue(b.pivotVisible)
        self.assertTrue(np.allclose(self.seen_at(), point, atol=1e-4))             # on the point recentred on
        self.assertTrue(np.allclose(b.camera.target, point))
        self.assertTrue(node.property("visible") and view.property("visible"))
        self.assertTrue(b._flash.isActive())
        self.assertEqual(b._flash.interval(), 1000)                                 # a second
        self.assertTrue(b._flash.isSingleShot())
        b._flash.timeout.emit()                                                     # the second is over
        self.assertFalse(b.pivotVisible)                                            # under the cursor it does not stay
        self.assertFalse(node.property("visible"))

    def test_the_flash_does_not_move_anything_with_less_motion_or_without(self):
        b = self.backend
        w, h = b.size
        for reduced in (True, False):
            b.reduced_motion = reduced
            self.click_middle((w * 0.3, h * 0.8))
            with self.subTest(reduced=reduced):
                self.assertTrue(b.pivotVisible)
                first = self.seen_at()
                self.app.processEvents()
                self.assertTrue(np.array_equal(self.seen_at(), first))              # no fade, no slide: it is there
            b._flash.timeout.emit()
        b.reduced_motion = True

    def test_a_wheel_or_an_orbit_ends_the_flash_at_once(self):
        b = self.backend
        w, h = b.size
        self.click_middle((w * 0.3, h * 0.8))
        self.assertTrue(b.pivotVisible)
        b.wheel(1.0, 0, w / 2, h / 2, False, 0, 0, 0)
        self.assertFalse(b.pivotVisible)                                            # the target is not that point now
        self.assertFalse(b._flash.isActive())
        self.click_middle((w * 0.3, h * 0.8))
        self.drag(MIDDLE, SHIFT, (300, 300), (330, 300))
        self.assertFalse(b.pivotVisible)                                            # nor is the orbit's
        self.assertFalse(b._flash.isActive())

    def test_with_the_middle_of_the_view_as_the_pivot_the_cross_hair_stays_on_the_target(self):
        b = self.backend
        w, h = b.size
        node, view = self.marker()
        self.assertFalse(b.pivotVisible)                                            # under the cursor: nothing at rest
        self.view.set_navigation("autocad", "turntable", "centre")
        self.assertTrue(b.pivotVisible)
        self.assertTrue(np.allclose(self.seen_at(), b.camera.target, atol=1e-4))
        self.assertTrue(node.property("visible") and view.property("visible"))
        self.assertTrue(np.allclose(b.camera.project(b.camera.target, w, h), (w / 2, h / 2), atol=1e-3))
        self.drag(MIDDLE, 0, (300, 300), (360, 320))                               # a pan: the target moves with it
        self.assertTrue(np.allclose(self.seen_at(), b.camera.target, atol=1e-4))
        self.drag(MIDDLE, SHIFT, (300, 300), (330, 300))                           # an orbit about it: it stays
        self.assertTrue(b.pivotVisible)
        self.assertTrue(np.allclose(self.seen_at(), b.camera.target, atol=1e-4))
        self.assertTrue(np.allclose(b._pivot, b.camera.target, atol=1e-6))
        self.click_middle((w * 0.3, h * 0.8))                                       # a recentre: on the new target
        b._flash.timeout.emit()
        self.assertTrue(b.pivotVisible)                                             # and it stays when the second is over
        self.assertTrue(np.allclose(self.seen_at(), b.camera.target, atol=1e-4))
        self.view.set_navigation("autocad", "turntable", "cursor")
        self.assertFalse(b.pivotVisible)                                            # and goes with the preference

    def test_at_rest_with_the_middle_of_the_view_it_does_not_depend_on_the_preference_for_the_key(self):
        b = self.backend
        self.view.set_navigation("autocad", "turntable", "centre", False)
        self.assertTrue(b.pivotVisible)                                             # that one is about the key held
        self.view.set_navigation("autocad", "turntable", "cursor", True)
        self.assertFalse(b.pivotVisible)

    def test_the_camera_of_the_scene_is_bound_to_the_backend(self):
        from PySide6.QtCore import QObject
        cam = self.view.rootObject().findChild(QObject, "camera")
        self.drag(MIDDLE, 0, (300, 300), (360, 320))        # AutoCAD: the middle pans
        p = cam.property("position")
        self.assertTrue(np.allclose((p.x(), p.y(), p.z()), self.backend.camera.position, atol=1e-4))

    def test_the_wheel_zooms_towards_the_cursor_and_a_middle_click_recentres(self):
        b = self.backend
        w, h = b.size
        point = b.camera.zoom_point(200, 500, w, h)
        before = np.linalg.norm(b.camera.position - point)
        b.wheel(1.0, 0, 200, 500, False, 0, 0, 0)
        self.assertAlmostEqual(np.linalg.norm(b.camera.position - point), before * 0.8, places=4)
        target = b.camera.ground(500, 400, w, h)
        b.press(MIDDLE, 0, 500, 400, False, 0, 0, 0, "", -1)
        b.release(MIDDLE, 0, 500, 400)
        self.assertTrue(np.allclose(b.camera.project(target, w, h), (w / 2, h / 2), atol=1e-3))

    def test_a_double_middle_click_fits_in_autocad_and_not_in_revit(self):
        b = self.backend
        b.wheel(5.0, 0, 100, 100, False, 0, 0, 0)
        moved = b.camera.position.copy()
        b.doubleClick(MIDDLE, 0, 100, 100)
        self.assertFalse(np.allclose(b.camera.position, moved))
        self.view.set_navigation("revit", "turntable", "cursor")
        b.wheel(5.0, 0, 100, 100, False, 0, 0, 0)
        moved = b.camera.position.copy()
        b.doubleClick(MIDDLE, 0, 100, 100)
        self.assertTrue(np.allclose(b.camera.position, moved))

    def test_a_double_middle_click_as_qt_sends_it_ends_fitted(self):
        b = self.backend
        b.reduced_motion = False
        b.wheel(5.0, 0, 100, 100, False, 0, 0, 0)
        b.press(MIDDLE, 0, 100, 100, False, 0, 0, 0, "", -1)                # press, release, press, double, release
        b.release(MIDDLE, 0, 100, 100)
        b.press(MIDDLE, 0, 100, 100, False, 0, 0, 0, "", -1)
        b.doubleClick(MIDDLE, 0, 100, 100)
        b.release(MIDDLE, 0, 100, 100)
        self.assertTrue(self.wait(self.app, lambda: b._animation.state() == b._animation.State.Stopped, 2))
        ended = b.camera.position.copy()
        b.frame(*b.scene, animate=False)                   # the scene framed from there: nothing moves
        self.assertTrue(np.allclose(b.camera.position, ended, atol=1e-6))

    def test_the_animation_takes_a_quarter_of_a_second(self):
        b = self.backend
        b.reduced_motion = False
        b.wheel(4.0, 0, 100, 100, False, 0, 0, 0)
        moved = b.camera.position.copy()
        b.doubleClick(MIDDLE, 0, 100, 100)
        self.assertTrue(np.allclose(b.camera.position, moved))          # not at once
        target = b._to.position.copy()
        # the clock of the animation driven by hand: on its way at 125 ms and at 200, there at 250 ms (study 15, 2.6;
        # the constant itself is not the test, the camera's way is)
        for ms in (125, 200):
            b._animation.setCurrentTime(ms)
            self.assertFalse(np.allclose(b.camera.position, moved), ms)
            self.assertFalse(np.allclose(b.camera.position, target), ms)
        b._animation.setCurrentTime(250)
        self.assertTrue(np.allclose(b.camera.position, target))
        self.assertEqual(b._animation.state(), b._animation.State.Stopped)

    def test_a_left_click_picks_and_a_right_click_asks_for_the_menu(self):
        b = self.backend
        picked, menus = [], []
        b.picked.connect(lambda name, i: picked.append((name, i)))
        b.menuRequested.connect(lambda x, y: menus.append((x, y)))
        b.press(LEFT, 0, 50, 60, True, 1, 2, 3, "modules", 7)
        b.release(LEFT, 0, 50, 60)
        b.press(RIGHT, 0, 70, 80, False, 0, 0, 0, "", -1)
        b.release(RIGHT, 0, 70, 80)
        self.assertEqual((picked, menus), ([("modules", 7)], [(70, 80)]))

    def native(self, kind, value=0.0, modifiers=None):
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QNativeGestureEvent, QPointingDevice
        from PySide6.QtWidgets import QApplication
        at = QPointF(300, 250)
        event = QNativeGestureEvent(kind, QPointingDevice.primaryPointingDevice(), 2, at, at,
                                    QPointF(self.view.mapToGlobal(at.toPoint())), value, QPointF())
        event.setModifiers(modifiers or Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(self.view, event)
        return event

    def wheel(self, dx, dy, modifiers=None):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import QApplication
        at = QPointF(300, 250)
        event = QWheelEvent(at, QPointF(self.view.mapToGlobal(at.toPoint())), QPoint(dx, dy), QPoint(),
                            Qt.MouseButton.NoButton, modifiers or Qt.KeyboardModifier.NoModifier,
                            Qt.ScrollPhase.ScrollUpdate, False)
        QApplication.sendEvent(self.view, event)
        return event

    def test_a_mouse_wheel_goes_on_to_the_scene_which_zooms_towards_the_point_under_the_pointer(self):
        """Only a touchpad's scroll (pixels in the phases of a scroll) is the view's own: a mouse's wheel goes on to
        the scene, where the model's point under the pointer is picked (QuickImage.wheelEvent, Scene.qml)."""
        from unittest import mock

        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import QApplication

        from meridiana.ui.quick_image import QuickImage
        at = QPointF(300, 250)
        for pixel, phase in ((QPoint(), Qt.ScrollPhase.NoScrollPhase), (QPoint(0, 12), Qt.ScrollPhase.NoScrollPhase)):
            with mock.patch.object(QuickImage, "wheelEvent") as forwarded:
                event = QWheelEvent(at, QPointF(self.view.mapToGlobal(at.toPoint())), pixel, QPoint(0, 120),
                                    Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, phase, False)
                QApplication.sendEvent(self.view, event)
                self.assertEqual(forwarded.call_count, 1, pixel)
        target = self.backend.camera.target.copy()
        with mock.patch.object(QuickImage, "wheelEvent") as forwarded:
            self.wheel(25, -15)                                 # a touchpad: the view's own pan
            self.assertEqual(forwarded.call_count, 0)
        self.assertFalse(np.allclose(self.backend.camera.target, target))

    def test_touchpad_scroll_pinch_shift_orbit_and_native_rotation(self):
        from PySide6.QtCore import Qt
        b = self.backend
        target = b.camera.target.copy()
        event = self.wheel(25, -15)
        self.assertTrue(event.isAccepted())
        self.assertFalse(np.allclose(b.camera.target, target))
        point = b.camera.zoom_point(300, 250, *b.size)
        distance = np.linalg.norm(b.camera.position - point)
        self.native(Qt.NativeGestureType.ZoomNativeGesture, 0.25)
        self.assertLess(np.linalg.norm(b.camera.position - point), distance)
        bearing = b.camera.bearing()
        self.wheel(30, 0, Qt.KeyboardModifier.ShiftModifier)
        self.assertAlmostEqual(b.camera.bearing(), (bearing + 30 * 0.35) % 360)
        bearing = b.camera.bearing()
        self.native(Qt.NativeGestureType.RotateNativeGesture, 12.0)
        self.assertAlmostEqual(b.camera.bearing(), (bearing + 12.0) % 360)


class Gizmo(unittest.TestCase):
    """The gizmo of Move and Rotate in the 3D view alone (task 16b, steps 5-7): where it stands and how big, the
    handle under the pointer lit, an arrow dragged along it only by what the ray says, the ring turned by the angle
    expected, the steps of the snaps, Ctrl at the release, the values typed beside it, the arrows of the keyboard,
    Esc; nothing without it. The handles are chosen on the screen in Python (gizmo.py), so this runs offscreen, where
    Qt Quick 3D draws nothing (study 16, B4). The gizmo is put where the window puts it with Move on the shed, on its
    middle at its roof (MainWindow._show_gizmo); what the window does with what it hands over (gizmoDone, gizmoTyped,
    nudged, escaped) is in finestra/test_views_navigation.py."""

    CENTRE = (20.0, 9.5, -10.0)                 # Qt's axes: x East, y up, z South

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        Navigation.setUp(self)
        self.done, self.typed, self.nudged, self.escaped = [], [], [], []
        self.backend.gizmoDone.connect(lambda *a: self.done.append(a))
        self.view.gizmoTyped.connect(lambda *a: self.typed.append(a))
        self.view.nudged.connect(lambda *a: self.nudged.append(a))
        self.view.escaped.connect(lambda: self.escaped.append(True))

    drag = Navigation.drag

    def start(self, snaps=True):
        """Move on the shed, as the window does it: the gizmo on its middle, the snaps of the plan as said."""
        self.backend.gizmo_snaps = snaps
        self.backend.set_gizmo(np.array(self.CENTRE))
        self.view.setFocus()

    def pixel(self, point):
        b = self.backend
        return b.camera.project(np.asarray(point, dtype=float), *b.size)

    def ring_pixel(self, degrees):
        import math

        from meridiana import gizmo, mesh
        b = self.backend
        r = math.radians(degrees)
        return self.pixel(b.gizmo_centre + (gizmo.EAST * math.cos(r) + gizmo.NORTH * math.sin(r))
                          * mesh.GIZMO_RING[0] * b.gizmo_size())

    def along_east(self, px, py):
        """Where the ray through the pixel passes closest to the East line through the gizmo: worked out here from the
        camera alone, as the proof of study 16 does it."""
        b = self.backend
        o, d = b.camera.ray(px, py, *b.size)
        a, p = np.array([1.0, 0.0, 0.0]), b.gizmo_centre
        n = np.cross(a, d)
        n2 = np.cross(d, n)
        return float(np.dot(o - p, n2) / np.dot(a, n2))

    def node(self, name):
        from PySide6.QtCore import QObject
        return self.view.rootObject().findChild(QObject, name)

    def test_the_gizmo_stands_where_it_is_put_as_large_as_the_screen_wants_and_goes_when_taken_away(self):
        from meridiana import gizmo
        b = self.backend
        self.assertFalse(b.gizmo_on)
        self.assertFalse(self.node("gizmo").property("visible"))
        self.start()
        self.assertTrue(np.allclose(b.gizmo_centre, self.CENTRE))
        self.assertTrue(self.node("gizmo").property("visible"))
        self.assertTrue(self.node("gizmoView").property("visible"))
        self.assertAlmostEqual(b.gizmoScale, gizmo.length(b.camera, b.gizmo_centre, b.size[1]))
        self.assertAlmostEqual(self.node("gizmo").property("scale").x(), b.gizmoScale, places=5)
        b.set_gizmo(None)
        self.assertFalse(b.gizmo_on)
        self.assertFalse(self.node("gizmo").property("visible"))

    def test_the_handle_under_the_pointer_is_lit(self):
        from meridiana import gizmo
        self.start()
        b = self.backend
        b.move(0, *self.pixel(b.gizmo_centre + gizmo.EAST * 0.6 * b.gizmo_size()))
        self.assertEqual(b.gizmoHot, "x")
        b.move(0, 3.0, 3.0)
        self.assertEqual(b.gizmoHot, "")

    def test_the_east_arrow_dragged_50_pixels_asks_for_a_move_east_only_by_what_the_ray_says(self):
        from meridiana import gizmo
        self.start(snaps=False)
        b = self.backend
        start = self.pixel(b.gizmo_centre + gizmo.EAST * 0.6 * b.gizmo_size())
        end = (start[0] + 50.0, start[1])
        want = self.along_east(*end) - self.along_east(*start)
        self.assertGreater(abs(want), 0.5)
        seen = []
        b.gizmoChanged.connect(lambda: seen.append((b.previewVisible, self.node("gizmoPreview").property("visible"))))
        self.drag(1, 0, start, end)
        self.assertIn((True, True), seen)                      # the preview went with the drag
        [(east, north, degrees, copy)] = self.done             # one move, at the release
        self.assertAlmostEqual(east, want, delta=0.001)        # to the millimetre
        self.assertEqual((north, degrees, copy), (0.0, 0.0, False))      # and East only
        self.assertFalse(b.previewVisible)

    def test_the_ring_dragged_asks_for_a_turn_about_the_middle_by_the_angle_expected(self):
        self.start(snaps=False)
        b = self.backend
        self.drag(1, 0, self.ring_pixel(135.0), self.ring_pixel(165.0))
        [(east, north, degrees, copy)] = self.done
        self.assertEqual((east, north, copy), (0.0, 0.0, False))
        self.assertAlmostEqual(degrees, 30.0, delta=0.1)      # 30° to 0.1°: 4 cm at most over a radius of 22 m
        self.assertTrue(np.allclose(b.gizmo_centre, self.CENTRE, atol=1e-6))

    def test_values_typed_next_to_the_gizmo_are_handed_over_east_north_and_the_angle(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.start()
        view = self.view
        QTest.keyClick(view, Qt.Key.Key_2)
        field = view.field
        self.assertTrue(field.isVisible())
        self.assertEqual(field.edits["x"].text(), "2")
        QTest.keyClick(field.edits["x"], Qt.Key.Key_Tab)
        QTest.keyClicks(field.edits["y"], "-3")
        QTest.keyClick(field.edits["y"], Qt.Key.Key_Return)
        self.assertFalse(field.isVisible())
        self.assertEqual(self.typed, [(2.0, -3.0, None)])
        QTest.keyClick(view, Qt.Key.Key_9)
        QTest.keyClick(field.edits["x"], Qt.Key.Key_Backspace)
        QTest.keyClick(field.edits["x"], Qt.Key.Key_Backtab)          # back from East to the angle
        QTest.keyClicks(field.edits["rz"], "90")
        QTest.keyClick(field.edits["rz"], Qt.Key.Key_Return)
        self.assertEqual(self.typed[1], (None, None, 90.0))

    def test_with_the_snaps_the_steps_are_ten_centimetres_and_one_with_shift(self):
        from meridiana import gizmo
        for mods, size in ((0, 0.1), (SHIFT, 0.01)):
            with self.subTest(mods=mods):
                self.start(snaps=True)
                b = self.backend
                start = self.pixel(b.gizmo_centre + gizmo.EAST * 0.6 * b.gizmo_size())
                end = (start[0] + 50.0, start[1])
                want = round((self.along_east(*end) - self.along_east(*start)) / size) * size
                self.drag(1, mods, start, end)
                self.assertAlmostEqual(self.done[-1][0], want, delta=1e-6)

    def test_ctrl_held_at_the_release_asks_for_a_copy(self):
        from meridiana import gizmo
        self.start()
        b = self.backend
        start = self.pixel(b.gizmo_centre + gizmo.NORTH * 0.6 * b.gizmo_size())
        b.press(1, 0, *start, False, 0, 0, 0, "", -1)
        b.move(0, start[0], start[1] - 40.0)
        b.release(1, CTRL, start[0], start[1] - 40.0)
        [(east, north, degrees, copy)] = self.done
        self.assertTrue(copy)
        self.assertGreater(north, 0.0)                         # up the screen is North from this camera
        self.assertEqual((east, degrees), (0.0, 0.0))

    def test_the_arrows_of_the_keyboard_nudge_by_ten_centimetres_a_metre_with_shift_a_centimetre_with_ctrl(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.start()
        view = self.view
        QTest.keyClick(view, Qt.Key.Key_Right)
        QTest.keyClick(view, Qt.Key.Key_Up, Qt.KeyboardModifier.ShiftModifier)
        QTest.keyClick(view, Qt.Key.Key_Left, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(len(self.nudged), 3)
        for (dx, dy), (ex, ey) in zip(self.nudged, ((0.1, 0.0), (0.0, 1.0), (-0.01, 0.0)), strict=True):
            self.assertAlmostEqual(dx, ex, places=9)
            self.assertAlmostEqual(dy, ey, places=9)

    def test_esc_puts_a_drag_back_and_esc_again_leaves_move(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from meridiana import gizmo
        self.start()
        b = self.backend
        start = self.pixel(b.gizmo_centre + gizmo.EAST * 0.6 * b.gizmo_size())
        b.press(1, 0, *start, False, 0, 0, 0, "", -1)
        b.move(0, start[0] + 60.0, start[1])
        self.assertTrue(b.previewVisible)
        QTest.keyClick(self.view, Qt.Key.Key_Escape)
        self.assertFalse(b.gizmo_dragging())
        self.assertFalse(b.previewVisible)
        b.release(1, 0, start[0] + 60.0, start[1])
        self.assertEqual((self.done, self.escaped), ([], []))   # nothing moved, and Move still on
        QTest.keyClick(self.view, Qt.Key.Key_Escape)
        self.assertEqual(self.escaped, [True])                  # the window goes back to Select

    def test_nothing_moves_without_the_gizmo(self):
        from meridiana import gizmo
        self.start()
        b = self.backend
        start = self.pixel(b.gizmo_centre + gizmo.EAST * 0.6 * b.gizmo_size())
        b.set_gizmo(None)                                       # the window takes it away with Select
        self.drag(1, 0, start, (start[0] + 50.0, start[1]))
        self.assertEqual(self.done, [])
        self.assertFalse(b.gizmo_dragging())


if __name__ == "__main__":
    unittest.main()
