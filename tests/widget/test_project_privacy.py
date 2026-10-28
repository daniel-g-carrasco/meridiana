"""Network requests of a reserved project cannot start before the explicit per-project consent."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup

from meridiana import config, model, registry
from meridiana.paths import Paths

setUpModule = _setup.keep_global_state


class ReservedNewProject(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.ui.new_project import NewProjectPage
        root = Path(tempfile.mkdtemp())
        self.paths = Paths(root / "config", root / "state", root / "data", root / "cache")
        self.cfg = config.Config(network_tiles=True, network_geocoding=True)
        self.registry = registry.Registry(root / "registry.sqlite3")
        self.addCleanup(self.registry.close)
        self.page = NewProjectPage(self.paths, self.cfg, [], registry=self.registry)
        self.addCleanup(_setup.dispose, self.page)
        self.page.send = mock.Mock()
        self.page.preview.tile_timer.start = mock.Mock()

    def test_reserved_map_and_search_stay_offline_until_their_own_gestures(self):
        self.page.show()
        self.page.reserved.setChecked(True)
        self.assertTrue(self.page.preview.loader.offline)
        self.page.preview.tile_timer.start.assert_not_called()
        self.page.query.setText("Via Roma 1, Rho")
        self.page.search.click()
        self.page.send.assert_not_called()
        self.page.maps_consent.setChecked(True)
        self.assertFalse(self.page.preview.loader.offline)
        self.page.preview.tile_timer.start.assert_called_once()
        self.page.search.click()
        self.page.send.assert_not_called()

    def test_selecting_a_reserved_job_stops_online_search_and_tiles_before_create(self):
        client = self.registry.create_client("Example client")
        job = self.registry.create_job("00125", "Reserved example", client["id"], reserved=True)
        self.page.refresh_registry()
        self.page.job.setCurrentIndex(self.page.job.findData(job["id"]))
        self.assertTrue(self.page.reserved.isChecked())
        self.assertFalse(self.page.reserved.isEnabled())
        self.assertTrue(self.page.preview.loader.offline)
        self.page.query.setText("Via Roma 1, Rho")
        self.page.search.click()
        self.page.send.assert_not_called()
        self.page.reserved.setChecked(False)
        self.assertTrue(self.page.reserved.isChecked())

    def test_create_keeps_the_map_consent_and_never_invents_a_weather_consent(self):
        from PySide6.QtTest import QSignalSpy
        spy = QSignalSpy(self.page.created)
        self.page.reserved.setChecked(True)
        self.page.maps_consent.setChecked(True)
        self.page.query.setText("45.5226, 9.03")
        self.page.create.click()
        data = spy.at(0)[0]
        import datetime
        self.assertEqual(data["network_consent"], {"tiles": datetime.date.today().isoformat()})
        self.assertNotIn("pvgis", data["network_consent"])


class ReservedProperties(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        cls.look = _setup.meridiana_look()

    def test_consents_are_separate_and_stored_in_the_project(self):
        from meridiana.ui.properties import Properties
        project = model.Project(reserved=True)
        props = Properties()
        self.addCleanup(_setup.dispose, props)
        sent = []

        def apply(kind, oid, changes):
            sent.append(changes)
            project.network_consent = changes["network_consent"]

        props.edited.connect(apply)
        props.show_site(project, False)
        self.assertFalse(props.maps_consent.isChecked())
        self.assertFalse(props.weather_consent.isChecked())
        props.maps_consent.setChecked(True)
        self.assertEqual(list(sent[-1]["network_consent"]), ["tiles"])
        props.weather_consent.setChecked(True)
        self.assertEqual(set(sent[-1]["network_consent"]), {"tiles", "pvgis"})


class ReservedSiteDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_existing_site_dialog_cannot_geocode_a_reserved_project(self):
        from meridiana.ui.site_dialog import SiteDialog
        dialog = SiteDialog(model.Site(), network=False)
        self.addCleanup(_setup.dispose, dialog)
        dialog.net.get = mock.Mock()
        dialog.query.setText("Via Roma 1, Rho")
        dialog._search()
        dialog.net.get.assert_not_called()
        self.assertIn("Privacy", dialog.status.text())


if __name__ == "__main__":
    unittest.main()
