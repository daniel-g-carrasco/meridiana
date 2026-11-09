"""R389/R302/R303: compare QML gizmo picking and drag maths with the core."""
import json
from pathlib import Path
import unittest

import _setup
import numpy as np
from PySide6.QtQml import QJSEngine

from meridiana import camera, gizmo, mesh


setUpModule = _setup.keep_global_state
QML = Path(__file__).resolve().parents[3] / "src/meridiana/quick/qml/Meridiana/View3D"
W, H = 1600, 1000


def state(cam):
    return {"position": cam.position.tolist(), "rotation": cam.rotation.tolist(),
            "target": cam.target.tolist(), "fov": cam.fov, "ortho": cam.ortho}


class GizmoParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.js = QJSEngine()
        source = (QML / "CameraMath.js").read_text(encoding="utf-8").replace(".pragma library", "")
        names = ("ray", "project", "pixelSize", "add", "sub", "scale", "dot", "norm")
        self.evaluate("var Cam = (function(){" + source + "\nreturn {" +
                      ",".join(f"{n}:{n}" for n in names) + "};})()")
        source = (QML / "GizmoMath.js").read_text(encoding="utf-8")
        self.evaluate("\n".join(line for line in source.splitlines() if not line.startswith(".")))

    def evaluate(self, source):
        result = self.js.evaluate(source)
        self.assertFalse(result.isError(), result.toString())
        return result.toVariant()

    def call(self, name, *args):
        return self.evaluate(name + "(" + ",".join(json.dumps(a) for a in args) + ")")

    def optional(self, actual, expected):
        if expected is None:
            self.assertIsNone(actual)
        else:
            np.testing.assert_allclose(actual, expected, rtol=2e-10, atol=2e-9)

    def cameras(self):
        for ortho in (False, True):
            for name in ("home", "top", "east", "south"):
                cam = camera.Camera(ortho=ortho)
                cam.view(name, [0, 0, 0], 15, W / H)
                yield cam

    def test_shared_dimensions_and_shape_points(self):
        self.assertEqual(self.evaluate("PIXELS"), gizmo.PIXELS)
        self.assertEqual(self.evaluate("TOLERANCE"), gizmo.TOLERANCE)
        self.assertEqual(self.evaluate("RING_SEGMENTS"), mesh.RING_SEGMENTS)
        self.assertEqual(self.evaluate("ACTIVE"), list(gizmo.ACTIVE))
        for centre in ([0, 0, 0], [4, 7, -9]):
            for size in (0.2, 3.7, 20):
                self.optional(self.call("ringPoints", centre, size), gizmo.ring_points(centre, size))
                self.optional(self.call("squarePoints", centre, size), gizmo.square_points(centre, size))
            for cam in self.cameras():
                self.assertAlmostEqual(self.call("length", state(cam), centre, H), gizmo.length(cam, centre, H))

    def test_rounding_preserves_python_half_even_and_negative_steps(self):
        for kind in ("move", "angle"):
            for mods in ([], ["shift"], ["ctrl", "shift"]):
                for snaps in (False, True):
                    size = gizmo.step(kind, mods, snaps)
                    self.assertEqual(self.call("step", kind, mods, snaps), size)
                    for value in (-2.5 * size, -1.5 * size, -0.5 * size, 0, 0.5 * size,
                                  1.5 * size, 2.5 * size, 1.234567, -179.949):
                        self.assertEqual(self.call("stepped", value, size), gizmo.stepped(value, size))

    def test_rays_planes_and_angles_including_degenerate_views(self):
        for cam in self.cameras():
            for x, y in ((800, 500), (1, 1), (1200, 730), (320, 900)):
                for axis in (gizmo.EAST, gizmo.NORTH, gizmo.UP):
                    args = [state(cam), x, y, W, H, [2, 1, -3], axis.tolist()]
                    self.optional(self.call("along", *args), gizmo.along(cam, x, y, W, H, [2, 1, -3], axis))
                    self.optional(self.call("onPlane", *args), gizmo.on_plane(cam, x, y, W, H, [2, 1, -3], axis))
                self.optional(self.call("angleOn", state(cam), x, y, W, H, [0, 0, 0], [1, 0, 0]),
                              gizmo.angle_on(cam, x, y, W, H, [0, 0, 0], gizmo.EAST))

    def test_screen_picking_all_handles_and_vertices(self):
        for cam in self.cameras():
            centre = [0, 0, 0]
            size = gizmo.length(cam, centre, H)
            points = [*gizmo.ring_points(centre, size), *gizmo.square_points(centre, size),
                      gizmo.EAST * size * 0.5, gizmo.NORTH * size * 0.5, gizmo.UP * size * 0.5]
            for point in points:
                pixel = cam.project(point, W, H)
                if pixel is None:
                    continue
                x, y = pixel
                for dx, dy in ((0, 0), (4, -3), (13, 18)):
                    self.assertEqual(self.call("pick", state(cam), x + dx, y + dy, W, H, centre, size),
                                     gizmo.pick(cam, x + dx, y + dy, W, H, centre, size))
            # Roof corners include exact coincident points. Circle samples are not
            # corners: their symmetric distances differ only by trig rounding.
            corners = [[0, 0, 0], [0, 0, 0], [0.127, 0.29, -0.217], [1.87, 1.12, -1.31], [-3, 2, 4]]
            for point in corners:
                x, y = cam.project(point, W, H)
                for dx, dy in ((0, 0), (4, -3), (13, 18)):
                    self.assertEqual(self.call("pickPoints", state(cam), x + dx, y + dy, W, H, corners),
                                     gizmo.pick_points(cam, x + dx, y + dy, W, H, corners))

    def test_all_drag_handles_keep_core_values_across_modifiers_and_camera_changes(self):
        for cam in self.cameras():
            for handle in (*gizmo.ACTIVE, "z", "unknown"):
                centre = [1, 2, -3]
                args = [handle, state(cam), 1000, 400, W, H, centre]
                drag = gizmo.Drag.begin(handle, cam, 1000, 400, W, H, centre)
                actual = self.call("begin", *args)
                if drag is None:
                    self.assertIsNone(actual)
                    continue
                self.evaluate("var drag = " + json.dumps(actual))
                for x, y, mods, snaps in ((1100, 440, [], True), (720, 230, ["shift"], True),
                                         (932, 612, [], False), (800, 500, ["ctrl"], False)):
                    expected = drag.update(cam, x, y, W, H, mods, snaps)
                    actual = self.evaluate("update(drag," + ",".join(json.dumps(a) for a in
                                           (state(cam), x, y, W, H, mods, snaps)) + ")")
                    self.assertEqual(actual, list(expected))
                    self.optional(self.evaluate("offset(drag)"), drag.offset())
                # A new camera can make the drag degenerate; the last value survives.
                blocked = camera.Camera(ortho=True)
                blocked.view("east" if handle == "x" else "south", centre, 20, W / H)
                expected = drag.update(blocked, 800, 500, W, H)
                actual = self.evaluate("update(drag," + json.dumps(state(blocked)) + ",800,500,1600,1000,[],true)")
                self.assertEqual(actual, list(expected))

    def test_height_drag_and_top_view_degeneracy(self):
        for cam in self.cameras():
            origin = [2, 3, -4]
            drag = gizmo.HeightDrag.begin(cam, 800, 500, W, H, origin)
            actual = self.call("beginHeight", state(cam), 800, 500, W, H, origin)
            if drag is None:
                self.assertIsNone(actual)
                continue
            self.evaluate("var drag = " + json.dumps(actual))
            for x, y, mods, snaps in ((900, 400, [], True), (400, 300, ["shift"], True), (1100, 120, [], False)):
                actual = self.evaluate("updateHeight(drag," + ",".join(json.dumps(a) for a in
                                       (state(cam), x, y, W, H, mods, snaps)) + ")")
                self.assertEqual(actual, drag.update(cam, x, y, W, H, mods, snaps))
        for angle in (-180, -76.3, 0, 90, 360):
            self.optional(self.call("rotation", angle), gizmo.rotation(angle))


if __name__ == "__main__":
    unittest.main()
