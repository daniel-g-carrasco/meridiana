"""The window fetches missing climate data by itself and then keeps it in the project (R196)."""

import unittest
from unittest import mock

import _setup
from _fixtures import capannone, clear_sky_meteo

from meridiana import atomic, config
from meridiana.energy import meteo

setUpModule = _setup.keep_global_state


class AutomaticClimate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def window(self, cache=None, network=True):
        cfg = config.Config(background="none", network_pvgis=False)
        win = _setup.window(self, capannone(), cfg=cfg, cache=cache)
        win.cfg.network_pvgis = network
        return win

    def test_opening_a_site_without_climate_starts_only_the_background_download(self):
        win = self.window()
        with mock.patch.object(win.pool, "start"):
            win.open_path(self.file)
        self.assertIsNotNone(win.climate_job)
        self.assertEqual((win.climate_job.lat, win.climate_job.lon),
                         (win.project.site.lat, win.project.site.lon))
        self.assertIsNone(win.energy_job)

    def test_the_background_download_enters_the_project_without_an_energy_year(self):
        win = self.window(cache=clear_sky_meteo())
        raw, _ = atomic.read_json(meteo._cache_file(win.paths.cache, "tmy", win.project.site.lat,
                                                    win.project.site.lon))
        climate = {"tmy": raw, "horizon": {"fetched": "2026-10-28", "azimuth": [0, 180], "elevation": [0, 0]}}
        win.session.mark_saved()
        win._climate_done(win.project.site.lat, win.project.site.lon, climate)
        self.assertEqual(win.project.climate, climate)
        self.assertFalse(win.energy)
        # written down by the program, not by the designer: a saved project stays saved and Ctrl+Z does not take it
        # back (closing a project just opened asked to save, 30/10/2026); the next save carries it into the file
        self.assertFalse(win._dirty())
        self.assertFalse(win.session.undo.can_undo())

    def test_a_saved_project_opened_and_closed_asks_nothing_and_keeps_the_weather_at_the_next_save(self):
        """The case found on the packages (30/10/2026): a saved .mer without weather, opened with the network on,
        got the download inside it and closing asked to save. Now nothing waits; a real change and a save write
        the weather into the file too."""
        from meridiana import model
        win = self.window(cache=clear_sky_meteo())
        path = self.file.with_name("salvato.mer")
        model.Project.from_json(win.project.to_json()).save(path)
        with mock.patch.object(win.pool, "start"):
            self.assertTrue(win.open_path(path))
        raw, _ = atomic.read_json(meteo._cache_file(win.paths.cache, "tmy", win.project.site.lat,
                                                    win.project.site.lon))
        climate = {"tmy": raw, "horizon": {"fetched": "2026-10-30", "azimuth": [0, 180], "elevation": [0, 0]}}
        win._climate_done(win.project.site.lat, win.project.site.lon, climate)
        self.assertFalse(win._dirty())
        win.edit("rename", lambda p: setattr(p, "name", "Rinominato"))
        self.assertTrue(win._dirty())
        win.session.save(path)
        self.assertEqual(model.Project.load(path)[0].climate, climate)

    def test_missing_data_turns_an_offline_computation_into_a_background_fetch(self):
        win = self.window()
        with mock.patch.object(win.pool, "start"):
            win._compute_energy(fetch=False)
        self.assertTrue(win.energy_job.fetch)
        self.assertTrue(win.energy_job.refresh)

    def test_data_inside_the_project_is_not_fetched_again_at_each_opening(self):
        win = self.window(cache=clear_sky_meteo())
        meteo.capture(win.project, win.paths.cache)
        win.project.climate["horizon"] = {"fetched": "2026-10-27", "azimuth": [0, 180], "elevation": [0, 0]}
        with mock.patch.object(win.pool, "start") as start:
            win._ensure_climate()
            win._compute_energy(fetch=False)
        self.assertIsNone(win.climate_job)
        start.assert_called_once()
        self.assertFalse(win.energy_job.fetch)

    def test_an_offline_download_says_that_meridiana_keeps_what_it_has(self):
        win = self.window()
        win._climate_failed(win.project.site.lat, win.project.site.lon, "offline")
        self.assertIn("Meridiana will use the data it has", win.statusBar().currentMessage())
        self.assertIsNone(win.climate_job)

    def test_a_result_puts_the_downloads_inside_the_project(self):
        win = self.window(cache=clear_sky_meteo())
        self.assertFalse(win.project.climate)
        win.session.mark_saved()
        win._energy_done(win.session.energy_generation, {"notes": [], "meteo_text": "synthetic"})
        raw, _ = atomic.read_json(meteo._cache_file(win.paths.cache, "tmy", win.project.site.lat,
                                                    win.project.site.lon))
        self.assertEqual(win.project.climate["tmy"], raw)
        self.assertFalse(win._dirty(), "the downloads go into the file with the next save, without asking for one")


if __name__ == "__main__":
    unittest.main()
