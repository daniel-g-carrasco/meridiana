"""Sweep preview computes the same membership as the authoritative core at release."""

import json
import random
import unittest
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QJSEngine

from meridiana import sweep


class SelectionParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.engine = QJSEngine()
        source = Path(__file__).resolve().parents[3] / 'src/meridiana/quick/qml/Meridiana/Plan/Selection.js'
        result = self.engine.evaluate(source.read_text(encoding='utf-8').replace('.pragma library', ''))
        self.assertFalse(result.isError(), result.toString())

    def chosen(self, rings, area, kind):
        expression = 'chosen(buildIndex(' + json.dumps([{'points': r} for r in rings]) + '),'
        result = self.engine.evaluate(expression + json.dumps(area) + ',' + json.dumps(kind) + ')')
        self.assertFalse(result.isError(), result.toString())
        return result.toVariant()

    def test_window_crossing_boundaries_concavity_and_self_intersecting_lassos_match_core(self):
        rings = [[[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1]]
                 for x in range(-1, 9) for y in range(-1, 9)]
        areas = [[], [[0, 0], [6, 0], [0, 0], [0, 6]], [[0, 0], [3, 0], [6, 0]],
                 [[0, 0], [6, 0], [6, 6], [0, 6]],
                 [[0, 0], [6, 6], [6, 0], [0, 6]],
                 [[0, 0], [6, 0], [6, 6], [4, 6], [4, 2], [2, 2], [2, 6], [0, 6]],
                 [[0, 0], [6, 0], [6, 6], [0, 6], [0, 0], [2, 2], [2, 4], [4, 4], [4, 2], [2, 2]]]
        for area in areas:
            for kind in ('window', 'crossing'):
                expected = [i for i, selected in enumerate(sweep.chosen_rings(rings, area, kind)) if selected]
                self.assertEqual(self.chosen(rings, area, kind), expected, (area, kind))

    def test_seeded_rotated_quads_match_core_for_many_lassos(self):
        rng = random.Random(344)
        rings = [[[x, y], [x + .8, y + .3], [x + .5, y + 1.1], [x - .3, y + .8]]
                 for x, y in [(rng.uniform(-5, 5), rng.uniform(-5, 5)) for _ in range(80)]]
        for _ in range(20):
            area = [[rng.uniform(-6, 6), rng.uniform(-6, 6)] for _ in range(7)]
            for kind in ('window', 'crossing'):
                expected = [i for i, selected in enumerate(sweep.chosen_rings(rings, area, kind)) if selected]
                self.assertEqual(self.chosen(rings, area, kind), expected)


if __name__ == '__main__':
    unittest.main()
