import unittest

from meridiana import model
from meridiana.quick.backend.plan_shadows import shadow_paths


class ShadowTest(unittest.TestCase):
    def test_cube_at_45_degrees_has_one_height_of_shadow_to_north(self):
        p=model.Project()
        p.buildings.append(model.Building(id='b1',name='Cube',height=10,
                           footprint=[[0,0],[10,0],[10,10],[0,10]]))
        paths=shadow_paths(p,180,45)
        self.assertEqual(len(paths),1)
        self.assertAlmostEqual(paths[0]['area'],200.)
        self.assertAlmostEqual(paths[0]['bounds'][3],20.)
        self.assertIn('-20',paths[0]['path'])
        self.assertEqual(shadow_paths(p,180,0),[])

    def test_non_finite_solar_position_is_refused(self):
        with self.assertRaises(ValueError):
            shadow_paths(model.Project(),0,float('nan'))


if __name__=='__main__':
    unittest.main()
