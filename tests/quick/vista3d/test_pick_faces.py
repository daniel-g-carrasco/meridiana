"""R488: a click in the 3D view takes what the ray met first. A wall, a gable end, a corner, a free pitch are the
building's even under a sub-field as wide as its roof (flush with the eaves); the roof under the sub-field and the
modules are the sub-field's. The points are on the faces the view draws, rounded to float32 as the view gives them."""
from pathlib import Path
import tempfile
import time
import unittest

import _setup
import numpy as np
from shapely.geometry import Point, Polygon

from meridiana import jobs, model
from meridiana.quick.backend.scene import SceneBackend
from meridiana.session import ProjectSession


setUpModule = _setup.keep_global_state


def qt(east, north, height):
    """A plan point and a height in the view's axes, as the view's pick gives them (float32)."""
    return tuple(float(v) for v in np.float32((east, height, -north)))


class PickFacesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = model.Project()
        flat = model.Building('flat', 'Flat', [[0, 0], [30, 0], [30, 20], [0, 20]], height=6)
        gable = model.Building('gable', 'Gable', [[40, 0], [60, 0], [60, 12], [40, 12]], height=5,
                               roof=model.Roof(type='gable', tilt=25))
        p.buildings = [flat, gable]
        self.pitches = gable.pitches()
        self.assertEqual(len(self.pitches), 2)
        south = min(self.pitches, key=lambda q: Polygon(q.ring).centroid.y)
        self.free = max(self.pitches, key=lambda q: Polygon(q.ring).centroid.y)
        self.south = south
        # both sub-fields flush with the eaves: their rings are the roof's own outline
        p.subfields = [model.SubField('sf', 'Flat roof', [list(q) for q in flat.footprint], building='flat',
                                      filled=True),
                       model.SubField('g', 'South pitch', [list(map(float, q)) for q in south.ring],
                                      building='gable', filled=True)]
        self.session = ProjectSession(p)
        results, keys, _ = jobs.layout_of(p, {})
        self.session.layout_done(self.session.generation, results, keys)
        self.scene = SceneBackend(self.session, Path(self.tmp.name))
        self.addCleanup(self.scene.close)

    def picked(self, point):
        self.session.select('site', '')
        self.scene.pick('buildings', -1, *point)
        hover = self.scene._point_target('buildings', *point)
        selection = self.session.selection
        self.assertEqual((hover[0] if hover[0] != 'module' else 'subfield', hover[1]), selection, point)
        return selection

    def test_walls_corners_and_gable_ends_take_the_building(self):
        cases = {
            # flat roof, sub-field flush with all four eaves
            'south wall middle': qt(15, 0, 3), 'east wall under the eave': qt(30, 10, 5.97),
            'north wall low': qt(12, 20, 0.3), 'west wall': qt(0, 7, 4),
            'corner': qt(30, 0, 3), 'corner under the eave': qt(0, 20, 5.98),
            # gable roof, sub-field on the south pitch, flush with its eave and gable ends
            'gable south wall': qt(50, 0, 2.5), 'gable south wall under the eave': qt(47, 0, 4.97),
            'gable end under the sub-field': qt(40, 3, 5.5), 'gable end other side': qt(60, 9, 5.5),
            'gable corner': qt(60, 0, 4.0),
        }
        for name, point in cases.items():
            with self.subTest(name):
                kind, oid = self.picked(point)
                self.assertEqual(kind, 'building', name)
                self.assertEqual(oid, 'flat' if point[0] <= 30 else 'gable', name)

    def test_roof_under_the_sub_field_takes_it_and_a_free_pitch_the_building(self):
        modules = self.session.good_results()['sf'].modules
        # the flat roof right inside the eave, outside every module: the sub-field
        gap = next((e, n) for e, n in ((0.02, 10), (15, 19.98), (29.98, 3))
                   if not any(Polygon(m.corners).buffer(0.01).covers(Point(e, n)) for m in modules))
        self.assertEqual(self.picked(qt(*gap, 6)), ('subfield', 'sf'))
        # the south pitch near its eave: the sub-field; the north pitch: the building
        sx, sy = Polygon(self.south.ring).representative_point().coords[0]
        self.assertEqual(self.picked(qt(sx, sy, self.south.z(sx, sy))), ('subfield', 'g'))
        eave = qt(52, 0.03, self.south.z(52, 0.03))
        self.assertEqual(self.picked(eave), ('subfield', 'g'))
        fx, fy = Polygon(self.free.ring).representative_point().coords[0]
        self.assertEqual(self.picked(qt(fx, fy, self.free.z(fx, fy))), ('building', 'gable'))
        self.assertEqual(self.picked(qt(55, 11.97, self.free.z(55, 11.97))), ('building', 'gable'))
        # a module itself, by its instance: the sub-field with that module
        self.scene.pick('modules', 0, 0, 0, 0)
        self.assertEqual(self.session.selected_module[0], 'sf')
        self.assertEqual(self.session.selection, ('subfield', 'sf'))

    def test_obstacle_parapet_and_esc_still_climb(self):
        p = self.session.project
        p.exclusions.append(model.ExclusionItem('chimney', [[50, 8], [51, 8], [51, 9], [50, 9]], building='gable',
                                                kind='chimney', height=1.5))
        flat = p.building('flat')
        flat.parapet = 1.0
        self.scene.rebuild()
        z = self.free.z(50, 8.5)
        self.assertEqual(self.picked(qt(50, 8.5, z + 0.5)), ('exclusion', 'chimney'))
        self.assertEqual(self.picked(qt(15, 0, 6.5)), ('building', 'flat'))       # the parapet's outer face
        self.picked(qt(15, 0, 3))
        self.assertEqual(self.scene.escapeSelection(), 'selection')
        self.assertEqual(self.session.selection, ('site', ''))

    def test_lookup_is_quick(self):
        point = qt(15, 0, 3)
        self.scene._hit_at(*point)                    # the first ask builds the table
        start = time.perf_counter()
        for _ in range(50):
            self.scene._point_target('buildings', *point)
        self.assertLess((time.perf_counter() - start) / 50, 0.01)


if __name__ == '__main__':
    unittest.main()
