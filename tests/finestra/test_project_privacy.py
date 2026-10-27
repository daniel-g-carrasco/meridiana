"""The MainWindow applies the reserved project's consent to map loaders and PVGIS jobs."""

import datetime
import unittest
from unittest import mock

import _setup
from _fixtures import capannone

from meridiana import config

setUpModule = _setup.keep_global_state


class ReservedWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone(), cfg=config.Config(background="none", network_tiles=True,
                                                            network_pvgis=True, network_geocoding=True))
        pool_start = self.win.pool.start
        self.win.pool.start = mock.Mock()
        self.addCleanup(setattr, self.win.pool, "start", pool_start)
        self.win.plan.tile_timer.start = mock.Mock()

    def test_maps_and_weather_wait_for_consent_and_geocoding_stays_forbidden(self):
        self.win.edit("Reserve", lambda p: setattr(p, "reserved", True))
        self.assertTrue(self.win.plan.loader.offline)
        self.win._compute_energy(fetch=True)
        job = self.win.pool.start.call_args.args[0]
        self.assertFalse(job.fetch)
        self.win.pool.start.reset_mock()
        today = datetime.date.today().isoformat()
        self.win.edit("Allow weather", lambda p: setattr(p, "network_consent", {"pvgis": today}))
        self.win._compute_energy(fetch=True)
        self.assertTrue(self.win.pool.start.call_args.args[0].fetch)
        self.assertTrue(self.win.plan.loader.offline)
        self.win.edit("Allow maps", lambda p: setattr(p, "network_consent", {"pvgis": today, "tiles": today}))
        self.assertFalse(self.win.plan.loader.offline)
        self.assertTrue(self.win.project.online_allowed("pvgis", True))
        self.assertFalse(self.win.project.online_allowed("geocoding", True))

    def test_renaming_a_building_does_not_reapply_map_consent(self):
        self.win.plan.loader.offline = True
        building = self.win.project.buildings[0]
        self.win._edited("building", building.id, {"name": "Renamed"})
        self.assertTrue(self.win.plan.loader.offline)
        self.win.plan.tile_timer.start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
