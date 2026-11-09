"""Execute the QML navigation state machine against the pure core for every style."""

import dataclasses
import itertools
import json
import random
import unittest
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QJSEngine

from meridiana import navigation


def style_data(style):
    return {name: [[sorted(buttons), sorted(mods)] for buttons, mods in getattr(style, name)]
            for name in ('pan', 'orbit', 'zoom', 'select')} | {
        name: getattr(style, name) for name in ('middle_click', 'middle_double', 'right_click')}


def actions(rows):
    return [dataclasses.asdict(row) | {'mods': sorted(row.mods)} for row in rows]


class NavigationParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.engine = QJSEngine()
        source = Path(__file__).resolve().parents[3] / 'src/meridiana/quick/qml/Meridiana/Plan/Navigation.js'
        result = self.engine.evaluate(source.read_text(encoding='utf-8').replace('.pragma library', ''))
        self.assertFalse(result.isError(), result.toString())

    def evaluate(self, expression):
        result = self.engine.evaluate(expression)
        self.assertFalse(result.isError(), result.toString())
        return result.toVariant()

    def compare(self, core, method, *args):
        expected = actions(getattr(core, method)(*args))
        actual = self.evaluate('nav.' + method + '(' + ','.join(json.dumps(arg) for arg in args) + ')')
        self.assertEqual(actual, expected, (core.style.name, method, args))
        for name in ('gesture', 'moved', 'swallow', 'before', 'spent'):
            self.assertEqual(self.evaluate('nav.' + name), getattr(core, name), name)
        self.assertEqual(self.evaluate('nav.held.slice().sort()'), sorted(core.held))

    def start(self, style):
        self.evaluate('var nav = create(' + json.dumps(style_data(style)) + '); true')
        return navigation.Navigator(style)

    def test_all_style_gestures_clicks_thresholds_modifiers_and_doubles(self):
        for style in navigation.STYLES.values():
            for buttons, mods in sum((navigation.gestures(style, kind) for kind in ('pan', 'orbit', 'zoom')), ()):
                core = self.start(style)
                for button in sorted(buttons):
                    self.compare(core, 'press', button, sorted(mods), 10, 20)
                self.compare(core, 'move', 12, 22, sorted(mods))
                self.compare(core, 'move', 13, 22, sorted(mods))
                self.compare(core, 'move', 40, 50, [])
                self.compare(core, 'move', 45, 30, sorted(mods))
                for button in sorted(buttons):
                    self.compare(core, 'release', button, sorted(mods), 45, 30)
            for button in navigation.BUTTONS:
                for mods in ([], ['ctrl'], ['shift'], ['alt'], ['space']):
                    core = self.start(style)
                    self.compare(core, 'press', button, mods, 10, 20)
                    self.compare(core, 'release', button, mods, 10, 20)
                    self.compare(core, 'press', button, mods, 10, 20)
                    self.compare(core, 'double', button, mods, 10, 20)
                    self.compare(core, 'release', button, mods, 10, 20)

    def test_chord_switch_swallow_and_seeded_traces_match_every_state(self):
        rng = random.Random(23026)
        for style in navigation.STYLES.values():
            core = self.start(style)
            for _ in range(250):
                mods = [name for name in navigation.MODIFIERS if rng.randrange(5) == 0]
                x, y = rng.randrange(50), rng.randrange(50)
                method = rng.choice(('press', 'move', 'move', 'release', 'double', 'wheel'))
                button = rng.choice(navigation.BUTTONS)
                if method == 'press' and button in core.held:
                    method = 'release'
                args = (x, y, mods) if method == 'move' else (
                    rng.choice((-.5, 0, .25, 1, 4)), mods, x, y) if method == 'wheel' else (button, mods, x, y)
                self.compare(core, method, *args)

    def test_wheel_precision_touchpad_wayland_zero_pixels_and_ctrl_pinch(self):
        for angle, pixel, phased, synthesized, ctrl, touchpad in itertools.product(
                ((0, 0), (0, 120), (0, -60), (12, 36)), ((0, 0), (.25, -.5), (0, 60)),
                (False, True), (False, True), (False, True), (False, True)):
            expected = navigation.wheel_action(angle, pixel, phased, synthesized, ctrl, touchpad=touchpad)
            args = (angle, pixel, phased, synthesized, ctrl, touchpad)
            actual = self.evaluate('wheelAction(' + ','.join(json.dumps(arg) for arg in args) + ')')
            self.assertEqual(actual, list(expected), args)

    def test_gesture_queries_reset_and_style_changes_match_core(self):
        for key, style in navigation.STYLES.items():
            core = self.start(style)
            for button in navigation.BUTTONS:
                self.assertEqual(self.evaluate('nav.chorded(' + json.dumps(button) + ')'), core.chorded(button))
            for count in range(5):
                for mods in itertools.combinations(navigation.MODIFIERS, count):
                    args = json.dumps(list(mods))
                    self.assertEqual(self.evaluate('nav.previewsOrbit(' + args + ')'), core.previews_orbit(mods))
                    for buttons in ([], ['left'], ['middle'], ['right'], ['left', 'middle'], ['left', 'right']):
                        self.assertEqual(self.evaluate('nav.drags(' + json.dumps(buttons) + ',' + args + ')'),
                                         core.drags(buttons, mods))
            self.compare(core, 'press', 'middle', [], 2, 3)
            self.compare(core, 'move', 50, 60, [])
            core.set_style(key)
            self.evaluate('nav.setStyle(' + json.dumps(style_data(style)) + '); true')
            self.compare(core, 'move', 4, 8, [])
            core.reset()
            self.evaluate('nav.reset(); true')
            self.compare(core, 'press', 'left', [], 0, 0)
            self.compare(core, 'release', 'left', [], 0, 0)


if __name__ == '__main__':
    unittest.main()
