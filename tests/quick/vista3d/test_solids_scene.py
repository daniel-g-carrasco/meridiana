"""The solids in the 3D scene's backend (study 37): a corner of a flat roof dragged tilts it and it stays flat (R455),
a plant room's walls stand from its base (R453), a saddle roof is drawn with all its pitches.

    python -m unittest quick.vista3d.test_solids_scene
"""
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import QApplication

from meridiana import model
from meridiana.quick.backend.scene import SceneBackend
from meridiana.session import ProjectSession


def project():
    p = model.Project(name='Solids')
    p.site = model.Site(lat=45.52, lon=9.04)
    p.buildings.append(model.Building('b1', 'Capannone', [[0, 0], [40, 0], [40, 20], [0, 20]], 8.0))
    p.buildings.append(model.Building('b2', 'Locale', [[10, 5], [16, 5], [16, 10], [10, 10]], 11.0, base=8.0, on='b1'))
    return p


class SolidsScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.session = ProjectSession(project())
        self.scene = SceneBackend(self.session, Path(self.tmp.name))
        self.addCleanup(self.scene.close)

    def test_a_corner_dragged_tilts_the_flat_roof_and_it_stays_flat(self):
        self.session.select('building', 'b1')
        self.assertEqual(len(self.scene.vertices), 4)
        self.scene.beginVertex(2)
        self.scene.previewVertex(1.5)
        self.scene.commitVertex(1.5)
        b = self.session.project.buildings[0]
        self.assertEqual(b.roof.type, 'flat')
        self.assertEqual([round(z, 2) for z in b.roof.plane], [8.0, 8.75, 9.5, 8.75])
        self.assertEqual(sorted(round(v['point'][1], 2) for v in self.scene.vertices), [8.0, 8.75, 8.75, 9.5])
        self.session.undo.undo()
        self.assertIsNone(self.session.project.buildings[0].roof.plane)

    def test_the_room_walls_stand_from_its_base_and_the_saddles_have_their_pitches(self):
        def lowest(bid):
            positions = self.scene.triangles[0]
            at = 0
            for part, oid, run in self.scene._owners:
                n = run * 3                                            # triangles, three corners each
                if part == 'building' and oid == bid:
                    return float(np.min(positions[at:at + n, 1]))      # Qt axes: y up
                at += n
            raise AssertionError(bid)
        self.assertAlmostEqual(lowest('b2'), 8.0)                       # the room's walls from its base
        self.assertAlmostEqual(lowest('b1'), 0.0)
        self.session.edit('saddles', lambda p: setattr(p.buildings[0].roof, 'type', 'saddles'))
        self.session.select('building', 'b1')
        self.assertGreater(len(self.scene.vertices), 8)
        self.assertLess(lowest('b1'), 0.001)


if __name__ == '__main__':
    unittest.main()
