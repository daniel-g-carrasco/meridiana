"""R389: QML navigation must retain the Widgets' numerical and gesture behaviour."""
import dataclasses
import json
from pathlib import Path
import unittest

import _setup
import numpy as np
from PySide6.QtQml import QJSEngine

from meridiana import camera, navigation


QML = Path(__file__).resolve().parents[3] / "src/meridiana/quick/qml/Meridiana/View3D"
_app = None
setUpModule = _setup.keep_global_state


def state(cam):
    return {"position": cam.position.tolist(), "rotation": cam.rotation.tolist(),
            "target": cam.target.tolist(), "fov": cam.fov, "ortho": cam.ortho}


def style_map(style):
    result = dataclasses.asdict(style)
    for kind in ("pan", "orbit", "zoom", "select"):
        result[kind] = [[sorted(buttons), sorted(mods)] for buttons, mods in getattr(style, kind)]
    return result


class JavaScriptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global _app
        _app = _setup.qt_or_skip()

    def engine(self, file):
        engine = QJSEngine()
        code = (QML / file).read_text(encoding="utf-8").replace(".pragma library", "")
        result = engine.evaluate(code, file)
        self.assertFalse(result.isError(), result.toString())
        return engine

    def evaluate(self, engine, code):
        result = engine.evaluate(code)
        self.assertFalse(result.isError(), result.toString())
        return result.toVariant()

    def call(self, engine, name, *args):
        return self.evaluate(engine, name + "(" + ",".join(json.dumps(a) for a in args) + ")")

    def assert_state(self, actual, expected):
        for key in ("position", "rotation", "target"):
            np.testing.assert_allclose(actual[key], getattr(expected, key), atol=2e-10, rtol=2e-10)
        self.assertEqual(actual["ortho"], expected.ortho)
        self.assertEqual(actual["fov"], expected.fov)


class CameraParityTest(JavaScriptTest):
    def setUp(self):
        self.js = self.engine("CameraMath.js")

    def test_math_and_projection_including_top_and_orthographic(self):
        for ortho in (False, True):
            for bearing, elevation in ((30, -35), (176, -90), (42, 90), (270, 0), (5, -0.001)):
                cam = camera.Camera(rotation=camera.look(bearing, elevation), ortho=ortho)
                cam.fit([4, 3, -7], 31, 1.7)
                s = state(cam)
                for name, python_name in (("forward", "forward"), ("right", "right"), ("up", "up"),
                                          ("bearing", "bearing"), ("elevation", "elevation"),
                                          ("halfHeight", "half_height")):
                    np.testing.assert_allclose(self.call(self.js, name, s), getattr(cam, python_name)(), atol=2e-10)
                for x, y in ((0, 0), (850, 500), (1700, 1000), (1220, 120)):
                    for name, pyname in (("ray", "ray"), ("ground", "ground"), ("pivot", "pivot"),
                                         ("zoomPoint", "zoom_point")):
                        expected = getattr(cam, pyname)(x, y, 1700, 1000)
                        actual = self.call(self.js, name, s, x, y, 1700, 1000)
                        if expected is None:
                            self.assertIsNone(actual)
                        else:
                            np.testing.assert_allclose(actual, expected, atol=2e-8, rtol=2e-10)
                for point in ([4, 3, -7], [1000, -400, 600], (cam.position - cam.forward()).tolist()):
                    expected = cam.project(point, 1700, 1000)
                    actual = self.call(self.js, "project", s, point, 1700, 1000)
                    if expected is None:
                        self.assertIsNone(actual)
                    else:
                        np.testing.assert_allclose(actual, expected, atol=2e-8, rtol=2e-10)
                    np.testing.assert_allclose(self.call(self.js, "keepInView", s, point, 1700, 1000),
                                               cam.keep_in_view(point, 1700, 1000), atol=2e-8)
                    self.assertAlmostEqual(self.call(self.js, "pixelSize", s, point, 1000), cam.pixel_size(point, 1000))

    def test_moves_match_core_in_long_sequences_and_do_not_mutate_input(self):
        for mode in ("turntable", "arcball"):
            for ortho in (False, True):
                cam = camera.Camera(ortho=ortho)
                actual = state(cam)
                for index in range(80):
                    dx, dy = (index % 13 - 6) * 13.7, (index % 7 - 3) * 19.2
                    pivot = [6, 2, -4]
                    actual = self.call(self.js, "orbit", actual, dx, dy, pivot, mode)
                    cam.orbit(dx, dy, pivot, mode)
                    actual = self.call(self.js, "pan", actual, 2.3, -1.7, 1600, 900, pivot)
                    cam.pan(2.3, -1.7, 1600, 900, pivot)
                    actual = self.call(self.js, "zoom", actual, 0.2 if index % 2 else -0.3, pivot)
                    cam.zoom(0.2 if index % 2 else -0.3, pivot)
                    self.assert_state(actual, cam)
                self.evaluate(self.js, "var source = " + json.dumps(actual))
                before = self.evaluate(self.js, "JSON.stringify(source)")
                self.evaluate(self.js, "orbit(source,40,20,[0,0,0],'arcball')")
                self.assertEqual(before, self.evaluate(self.js, "JSON.stringify(source)"))

    def test_views_fit_recentre_orient_and_animation(self):
        cam = camera.Camera()
        for name in camera.VIEWS:
            actual = self.call(self.js, "view", state(cam), name, [2, 4, 6], 13, 0.6)
            cam.view(name, [2, 4, 6], 13, 0.6)
            self.assert_state(actual, cam)
        initial = cam.copy()
        actual = self.call(self.js, "recentre", state(cam), [-12, 2, 9])
        cam.recentre([-12, 2, 9])
        self.assert_state(actual, cam)
        cam.ortho = True
        for t in (-1, 0, 0.2, 0.5, 0.99, 1, 2):
            self.assert_state(self.call(self.js, "between", state(initial), state(cam), t), camera.between(initial, cam, t))
        actual = self.call(self.js, "orient", state(cam), 123, -67)
        distance = np.linalg.norm(cam.position - cam.target)
        cam.rotation = camera.look(123, -67)
        cam.position = cam.target - cam.forward() * distance
        self.assert_state(actual, cam)

    def test_cursor_anchor_minimum_distance_clip_and_top_orbit(self):
        for ortho in (False, True):
            cam = camera.Camera(ortho=ortho)
            cam.view("top", [0, 0, 0], 30, 1.6)
            point = cam.zoom_point(1120, 240, 1600, 1000)
            for steps in (1, -2.7, 0, 200):
                result = self.call(self.js, "zoom", state(cam), steps, point.tolist())
                expected = cam.copy()
                expected.zoom(steps, point)
                self.assert_state(result, expected)
                projected = self.call(self.js, "project", result, point.tolist(), 1600, 1000)
                np.testing.assert_allclose(projected, expected.project(point, 1600, 1000), atol=3e-9)
                if steps != 200:
                    np.testing.assert_allclose(projected, cam.project(point, 1600, 1000), atol=3e-9)
                else:
                    self.assertAlmostEqual(np.linalg.norm(np.array(result["position"]) - point), camera.MIN_DISTANCE)
            for mode in ("turntable", "arcball"):
                for dx, dy in ((0, 0), (100, 0), (0, 1000), (-300, -1000)):
                    result = self.call(self.js, "orbit", state(cam), dx, dy, point.tolist(), mode)
                    expected = cam.copy()
                    expected.orbit(dx, dy, point, mode)
                    self.assert_state(result, expected)
            if ortho:
                for depth in (-20001, -1, 20001):
                    point = (cam.position + cam.forward() * depth).tolist()
                    expected = cam.project(point, 1600, 1000)
                    actual = self.call(self.js, "project", state(cam), point, 1600, 1000)
                    if expected is None:
                        self.assertIsNone(actual)
                    else:
                        np.testing.assert_allclose(actual, expected, atol=2e-10)


class NavigatorParityTest(JavaScriptTest):
    def setUp(self):
        self.js = self.engine("Navigation.js")

    def sequence(self, style, events):
        nav = navigation.Navigator(style)
        self.evaluate(self.js, "var nav = create(" + json.dumps(style_map(style)) + ")")
        for method, args in events:
            expected = []
            for action in getattr(nav, "double" if method == "doubleClick" else method)(*args):
                record = dataclasses.asdict(action)
                record["mods"] = sorted(record["mods"])
                expected.append(record)
            actual = self.evaluate(self.js, method + "(nav," + ",".join(json.dumps(a) for a in args) + ")")
            for record in actual:
                record["mods"].sort()
            self.assertEqual(actual, expected, (style.name, method, args))

    def test_all_fourteen_styles_every_gesture_click_chord_and_modifier_transition(self):
        self.assertEqual(len(navigation.STYLES), 14)
        for style in navigation.STYLES.values():
            for kind in ("pan", "orbit", "zoom"):
                for buttons, mods in navigation.gestures(style, kind):
                    buttons, mods = sorted(buttons), sorted(mods)
                    events = [("move", [100, 100, []])]
                    events += [("press", [b, mods, 100, 100]) for b in buttons]
                    events += [("move", [102, 101, mods]), ("move", [120, 135, mods]),
                               ("move", [133, 145, []]), ("move", [140, 150, mods])]
                    events += [("release", [b, mods, 140, 150]) for b in buttons]
                    events += [("move", [150, 160, []])]
                    self.sequence(style, events)
            for button in navigation.BUTTONS:
                for mods in ([], ["ctrl"], ["shift"], ["alt"]):
                    self.sequence(style, [("press", [button, mods, 1, 2]), ("release", [button, mods, 1, 2]),
                                          ("press", [button, mods, 1, 2]), ("doubleClick", [button, mods, 1, 2]),
                                          ("release", [button, mods, 1, 2]), ("wheel", [1.5, mods, 4, 7])])
            self.sequence(style, [("move", [100, 100, []]), ("move", [120, 130, ["space"]]),
                                  ("move", [125, 135, ["space"]]), ("move", [125, 135, []])])

    def test_touchpad_wheel_routing(self):
        for angle, pixel, phased, synthesized, ctrl, touchpad in (
                ([0, 120], [0, 0], False, False, False, False),
                ([0, 120], [0, 0], False, False, True, False),
                ([5, 14], [0, 0], False, False, False, False),
                ([0, 120], [0, 0], True, False, False, False),
                ([0, 0], [3.5, -4.2], False, False, False, False),
                ([0, 70], [0, 0], False, False, False, True),
                ([0, 0], [0, 30], False, True, True, False)):
            expected = navigation.wheel_action(tuple(angle), tuple(pixel), phased, synthesized, ctrl, touchpad=touchpad)
            self.assertEqual(self.call(self.js, "wheelAction", angle, pixel, phased, synthesized, ctrl, touchpad),
                             list(expected))

    def test_chord_released_in_either_order_never_starts_an_unwanted_gesture(self):
        for style in navigation.STYLES.values():
            for kind in ("pan", "orbit", "zoom"):
                for buttons, mods in getattr(style, kind):
                    if len(buttons) < 2:
                        continue
                    for order in (sorted(buttons), sorted(buttons, reverse=True)):
                        events = [("press", [button, sorted(mods), 10, 20]) for button in sorted(buttons)]
                        events += [("move", [40, 50, sorted(mods)]), ("release", [order[0], sorted(mods), 40, 50]),
                                   ("move", [50, 70, sorted(mods)]), ("release", [order[1], sorted(mods), 50, 70]),
                                   ("move", [80, 90, []])]
                        self.sequence(style, events)

    def test_preview_and_chord_detection_use_style_gestures(self):
        for style in navigation.STYLES.values():
            nav = navigation.Navigator(style)
            self.evaluate(self.js, "var nav = create(" + json.dumps(style_map(style)) + ")")
            for button in navigation.BUTTONS:
                self.assertEqual(self.evaluate(self.js, "chorded(nav," + json.dumps(button) + ")"), nav.chorded(button))
            for mods in ([], ["shift"], ["ctrl"], ["alt"], ["space"], ["ctrl", "shift"]):
                self.assertEqual(self.evaluate(self.js, "previewsOrbit(nav," + json.dumps(mods) + ")"),
                                 nav.previews_orbit(mods))


if __name__ == "__main__":
    unittest.main()
