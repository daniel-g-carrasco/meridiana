"""The light on a plane before the obstacles (study 45, package 1): the first pass keeps its three parts (direct with
circumsolar, sky, ground) after the horizon and the rows, they add up to its irradiance after the rows to the last bit,
the obstacles act on them as on the year, and plane_light, the same steps on a plane without modules, gives the
year's own light."""

import unittest

import numpy as np

import _setup  # noqa: F401
from _fixtures import clear_sky_meteo, mixed

from meridiana.app import jobs
from meridiana.core.energy import system
from meridiana.core.energy.meteo import Horizon
from meridiana.core.energy.pedigree import Source
from meridiana.core.energy.simulate import Losses, _first_pass, plane_light, sun_path

METEO = clear_sky_meteo()
# a horizon that hides some sun and some sky, so that the far shading is not a factor of 1
HORIZON = Horizon(np.array([0.0, 90.0, 180.0, 270.0]), np.array([12.0, 6.0, 9.0, 4.0]), Source("input", "hills"))


class PlaneLight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        project = mixed()                       # the shed's tilted rows with obstacles, a gable pitch with a chimney
        results = jobs.layout_of(project)[0]
        cls.arrays = system.arrays_of(project, results)
        cls.losses = system.losses_of(project)
        cls.first = _first_pass(METEO, cls.arrays, None, cls.losses, HORIZON)
        cls.passes = {ap.a.key: ap for ap in cls.first.per_array}

    def test_the_cases_are_there(self):
        self.assertTrue(self.losses.use_horizon and self.losses.use_near)
        self.assertTrue(any(ap.a.rows > 1 for ap in self.first.per_array), "an array with rows")
        self.assertTrue(any(ap.a.rows <= 1 for ap in self.first.per_array), "an array without rows")
        self.assertTrue(any(ap.near is not None for ap in self.first.per_array), "an array with obstacles")

    def test_the_three_parts_add_up_to_the_light_after_the_rows(self):
        for ap in self.first.per_array:
            with self.subTest(array=ap.a.key):
                self.assertTrue(np.array_equal(ap.beam_rows + ap.sky_rows + ap.ground_rows, ap.g_rows))

    def test_the_obstacles_act_on_the_three_parts_as_on_the_year(self):
        # what the map will do with them: the direct part loses the obstacles' shade, the sky what they hide
        for ap in self.first.per_array:
            with self.subTest(array=ap.a.key):
                if ap.near is None:
                    self.assertTrue(np.array_equal(ap.g_near, ap.g_rows))
                    continue
                near = ap.beam_rows * (1.0 - ap.f_obst) + ap.sky_rows * ap.near.sky + ap.ground_rows
                self.assertTrue(np.array_equal(near, ap.g_near))
                self.assertTrue(np.array_equal(ap.beam_left, ap.beam_rows * (1.0 - ap.f_obst)))

    def test_plane_light_is_the_years_light_on_a_plane_without_rows(self):
        flat = [ap for ap in self.first.per_array if ap.a.rows <= 1]
        for ap in flat:
            for sun in (None, sun_path(METEO, HORIZON)):
                with self.subTest(array=ap.a.key, shared_sun=sun is not None):
                    light = plane_light(METEO, ap.a.tilt, ap.a.azimuth, self.losses, HORIZON, sun=sun)
                    self.assertTrue(np.array_equal(light.beam, ap.beam_rows))
                    self.assertTrue(np.array_equal(light.sky, ap.sky_rows))
                    self.assertTrue(np.array_equal(light.ground, ap.ground_rows))
                    self.assertTrue(np.array_equal(light.beam + light.sky + light.ground, ap.g_far))
                    self.assertEqual((light.dome, light.alb), (ap.dome, ap.alb))
                    self.assertLess(light.dome, 1.0)        # the horizon took part of the sky

    def test_the_rows_act_on_the_planes_light(self):
        for ap in (ap for ap in self.first.per_array if ap.a.rows > 1):
            with self.subTest(array=ap.a.key):
                light = plane_light(METEO, ap.a.tilt, ap.a.azimuth, self.losses, HORIZON)
                self.assertTrue(np.array_equal(light.beam + light.sky + light.ground, ap.g_far))
                self.assertTrue(np.array_equal(ap.beam_rows, light.beam * (1.0 - ap.shaded)))
                self.assertTrue(np.array_equal(ap.sky_rows, light.sky * (1.0 - ap.sky_mask)))
                self.assertTrue(np.all(ap.ground_rows <= light.ground))
                self.assertEqual(1.0 - ap.ground_rows.sum() / light.ground.sum(), ap.ground_lost)
                self.assertGreater(ap.ground_lost, 0.0)

    def test_without_the_horizon_in_the_losses_the_plane_sees_the_whole_sky(self):
        losses = Losses.from_dict({"use_horizon": False})
        light = plane_light(METEO, 30.0, 0.0, losses, HORIZON)
        open_sky = plane_light(METEO, 30.0, 0.0, losses)
        self.assertEqual((light.dome, light.alb), (1.0, 1.0))
        self.assertTrue(np.array_equal(light.beam, open_sky.beam))
        self.assertTrue(np.array_equal(light.beam, light.poa_beam + light.circum))


if __name__ == "__main__":
    unittest.main()
