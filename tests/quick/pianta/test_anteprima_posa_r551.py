"""R551 (Daniel 08/11/2026: «la preview di come verranno posati i moduli non è corretta»): while an area is drawn as
modules, the yellow preview is the layout the drawing makes, the same rows, the same direction, the same modules.

The cause: the rows of a flat roof face the direction of the area's least rectangle closest to South
(layout.auto_azimuth). A right isosceles triangle has two least rectangles, along its legs and along its hypotenuse,
and shapely chose by the last digits of the points: the preview laid the triangle as drawn (the pointer's floats) along
its hypotenuse, the drawing laid it rounded to 0.1 mm (plan_edit._polygon) along its legs. Now the rule chooses among
both rectangles, and the preview lays the ring the drawing keeps (move.drawn_ring).

    python -m unittest quick.pianta.test_anteprima_posa_r551
"""
import math
import unittest

import _setup
from shapely.geometry import Polygon

from meridiana import layout, manual, model, move
from meridiana.quick.backend.plan_edit import PlanEditor
from meridiana.quick.backend.plan_tools import DrawingMachine
from meridiana.session import ProjectSession

setUpModule = _setup.keep_global_state

LEG = 19.66 / math.sqrt(2) * math.sqrt(2)


def project():
    p = model.Project(name='Prova anteprima')
    p.site = model.Site(lat=45.52, lon=9.04, address='Rho (MI)')
    p.buildings.append(model.Building(id='b1', name='Capannone', footprint=[[0, 0], [60, 0], [60, 40], [0, 40]],
                                      height=8.0))
    return p


# as the pointer leaves them: floats with their last digits, the turn of 90° snapped
TRIANGLE = [(20.123456789, 35.0000000001), (20.123456789 + LEG, 35.0000000001), (20.123456789 + LEG + 3e-9, 35.0 - LEG)]
ELLE = [(5.02000001, 3.0), (31.0000003, 3.0), (31.0000003, 13.0), (17.0, 13.0), (17.0, 27.00000002), (5.02000001, 27.00000002)]


def directions(quads):
    return sorted({round(math.degrees(math.atan2(q[1][1] - q[0][1], q[1][0] - q[0][0])) % 180, 3) for q in quads})


def corners(quads):
    return sorted(tuple(round(c, 3) for corner in q for c in corner) for q in quads)


class PreviewIsTheLayout(unittest.TestCase):
    def same_modules(self, shown, made):
        """The same modules in the same places, to 2 mm (the rows the drawing keeps are stored to the millimetre)."""
        self.assertEqual(len(shown), len(made))
        left = [tuple(c for corner in q for c in corner) for q in made]
        for q in shown:
            a = tuple(c for corner in q for c in corner)
            near = min(left, key=lambda b: max(abs(x - y) for x, y in zip(a, b, strict=True)))
            self.assertLessEqual(max(abs(x - y) for x, y in zip(a, near, strict=True)), .002, (a, near))
            left.remove(near)

    def preview_and_drawn(self, ring):
        drawing = DrawingMachine(project())
        drawing.set_tool('subfield')
        shown = drawing.grid_values(ring)
        editor = PlanEditor(ProjectSession(project()))
        editor.apply_command(dict(type='polygon', tool='subfield', ring=[list(q) for q in ring], spec={}))
        p = editor.project
        sf = p.subfields[-1]
        self.assertTrue(sf.flush)
        made = manual.corners(p, sf, manual.rows_now(p, sf, None))
        return shown, made

    def test_a_right_isosceles_triangle_lays_in_the_preview_as_it_is_laid(self):
        shown, made = self.preview_and_drawn(TRIANGLE)
        self.assertGreater(shown['count'], 10)
        self.assertEqual(shown['count'], len(made))
        self.assertEqual(directions(shown['quads']), directions(made))
        self.assertTrue(all(d % 90 == 0 for d in directions(made)), 'along the legs, facing South (the rule of the layout)')
        self.same_modules(shown['quads'], made)

    def test_an_l_shaped_area_lays_in_the_preview_as_it_is_laid(self):
        shown, made = self.preview_and_drawn(ELLE)
        self.assertGreater(shown['count'], 10)
        self.same_modules(shown['quads'], made)

    def test_the_rule_does_not_turn_on_the_last_digits(self):
        raw = Polygon(TRIANGLE)
        kept = Polygon(move.drawn_ring(TRIANGLE))
        self.assertEqual(layout.auto_azimuth(raw), layout.auto_azimuth(kept))
        self.assertEqual(layout.auto_azimuth(raw), 0.0)
        # a triangle that is not isosceles keeps its one least rectangle
        self.assertEqual(layout.auto_azimuth(Polygon([(0, 0), (40, 0), (40, -20)])),
                         layout.auto_azimuth(Polygon([(0, 0), (40.00001, 0), (40.00001, -20)])))


if __name__ == '__main__':
    unittest.main()
