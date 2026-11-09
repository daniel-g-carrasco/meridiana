"""R389: unchanged core geometry must reach the Quick scene without lost modules."""
import unittest

from meridiana import jobs, model
from meridiana.quick.backend import plan_scene


class SceneTest(unittest.TestCase):
    def test_concave_building_keeps_outline_and_north_points_up(self):
        project = model.Project()
        ring = [[0, 0], [9, 0], [9, 2], [2, 2], [2, 9], [0, 9]]
        project.buildings.append(model.Building(id='b1', name='L', footprint=ring))
        scene = plan_scene.scene_of(project, {})
        building = next(x for x in scene['objects'] if x['kind'] == 'building')
        self.assertEqual(building['points'], [[float(x), -float(y)] for x, y in ring])
        self.assertEqual(scene['bounds'], [0., -9., 9., 9.])

    def test_every_module_has_same_corners_key_and_row_as_core(self):
        project = model.Project()
        project.subfields.append(model.SubField(id='s1', name='Field', ring=[[0, 0], [40, 0], [40, 20], [0, 20]], filled=True))
        results, _, _ = jobs.layout_of(project, {})
        scene = plan_scene.scene_of(project, results)
        self.assertGreater(len(scene['modules']), 20)
        for drawn, original in zip(scene['modules'], results['s1'].modules, strict=True):
            self.assertEqual(drawn['key'], original.key)
            self.assertEqual(drawn['rid'], original.rid)
            self.assertEqual(drawn['points'], [[float(x), -float(y)] for x, y in original.corners])

    def test_batched_geometry_preserves_20000_quads_and_all_borders(self):
        modules = [{'points': [[x * 2, 0], [x * 2 + 1, 0], [x * 2 + 1, 2], [x * 2, 2]]}
                   for x in range(20000)]
        triangles, lines = plan_scene.module_geometry(modules)
        self.assertEqual(triangles.shape, (120000, 2))
        self.assertEqual(lines.shape, (160000, 2))
        self.assertEqual(triangles[-1].tolist(), [39998., 2.])
        self.assertTrue(triangles.flags.c_contiguous)


if __name__ == '__main__':
    unittest.main()
