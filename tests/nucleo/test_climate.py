"""The site's typical year and horizon travel inside the project and refresh only when needed (R196)."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401
from _fixtures import capannone_rho, clear_sky_meteo, write_cache

from meridiana import atomic, model
from meridiana.energy import meteo, pipeline


class Climate(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.cache = self.folder / "cache"
        write_cache(clear_sky_meteo(), self.cache)
        self.raw, _ = atomic.read_json(meteo._cache_file(self.cache, "tmy", 45.5226, 9.03))

    def test_the_embedded_year_needs_no_cache_or_network(self):
        project = capannone_rho()
        project.climate = {"tmy": self.raw, "horizon": {"fetched": "2026-10-27", "azimuth": [0, 180],
                                                         "elevation": [0, 0]}}
        out = pipeline.compute(project, {}, self.folder / "empty", False)
        self.assertIn("synthetic", out.meteo_text)
        self.assertIn("Lay the modules", out.error_sim)

    def test_an_explicit_fetch_refreshes_the_embedded_data(self):
        project = capannone_rho()
        project.climate = {"tmy": self.raw}
        with mock.patch("meridiana.energy.meteo.typical_year", return_value=clear_sky_meteo()) as fetch, \
                mock.patch("meridiana.energy.meteo.horizon", return_value=meteo.Horizon.flat()):
            pipeline.compute(project, {}, self.cache, True, refresh=True)
        self.assertTrue(fetch.call_args.kwargs["refresh"])

    def test_allowing_the_network_does_not_refresh_a_valid_cache(self):
        project = capannone_rho()
        project.climate = {"tmy": self.raw}
        with mock.patch("meridiana.energy.meteo.typical_year", return_value=clear_sky_meteo()) as fetch, \
                mock.patch("meridiana.energy.meteo.horizon", return_value=meteo.Horizon.flat()):
            pipeline.compute(project, {}, self.cache, True)
        self.assertFalse(fetch.call_args.kwargs["refresh"])

    def test_a_move_over_250_metres_or_another_database_requires_new_data(self):
        self.assertTrue(meteo.usable(self.raw, 45.5226, 9.03))
        self.assertTrue(meteo.usable(self.raw, 45.5230, 9.03))
        self.assertFalse(meteo.usable(self.raw, 45.5260, 9.03))
        other = json.loads(json.dumps(self.raw))
        other["meta"]["inputs"]["meteo_data"]["radiation_db"] = "new-database"
        self.assertFalse(meteo.usable(other, 45.5226, 9.03))

    def test_the_climate_is_saved_inside_the_project(self):
        project = capannone_rho()
        project.climate = {"tmy": self.raw}
        path = self.folder / "autonomous.meridiana"
        project.save(path)
        opened, notice = model.Project.load(path)
        self.assertIsNone(notice)
        self.assertEqual(opened.climate, project.climate)
        self.assertEqual(model.FORMAT_VERSION, 17)

    def test_capture_keeps_both_downloads_in_the_project(self):
        project = capannone_rho()
        meteo.capture(project, self.cache)
        self.assertEqual(project.climate["tmy"], self.raw)
        self.assertGreater(len(json.dumps(project.climate)), 100000)


if __name__ == "__main__":
    unittest.main()
