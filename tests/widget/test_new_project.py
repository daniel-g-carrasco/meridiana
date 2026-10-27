"""The New Project page: local suggestions and coordinate parsing while typing, Nominatim only on Search,
a point confirmed on the map before Create and draw. No real network request."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup

from meridiana import config, places
from meridiana.paths import Paths

setUpModule = _setup.keep_global_state


class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.ui.new_project import NewProjectPage
        root = Path(tempfile.mkdtemp())
        self.paths = Paths(root / "config", root / "state", root / "data", root / "cache")
        self.cfg = config.Config(network_geocoding=False, network_tiles=False)
        local = [places.PlaceSuggestion("Rho", "Milano", "Lombardia", 45.53178, 9.046984, "015182", "ISTAT")]
        self.page = NewProjectPage(self.paths, self.cfg, local)
        self.addCleanup(_setup.dispose, self.page)
        self.page.send = mock.Mock()

    def test_typing_coordinates_and_local_suggestions_never_calls_a_service(self):
        self.page.query.setText("rh")
        self.assertEqual(self.page.suggestions.stringList(), ["Rho, Milano · ISTAT"])
        self.page.choose_suggestion("Rho, Milano · ISTAT")
        self.assertAlmostEqual(self.page.candidate.lat, 45.53178)
        self.assertTrue(self.page.create.isEnabled())
        self.page.query.setText('45°31\'21,36"N 9°01\'48,00"E')
        self.assertAlmostEqual(self.page.candidate.lat, 45.5226)
        self.assertAlmostEqual(self.page.candidate.lon, 9.03)
        self.assertIn("DMS", self.page.status.text())
        self.page.send.assert_not_called()
        self.assertTrue(self.page.preview.loader.offline)

    def test_an_ambiguous_coordinate_text_is_refused_with_the_reason(self):
        self.page.query.setText('45°31\'21" 9°01\'48"')
        self.assertIsNone(self.page.candidate)
        self.assertFalse(self.page.create.isEnabled())
        self.assertIn("hemisphere", self.page.status.text())
        self.page.send.assert_not_called()

    def test_nominatim_goes_only_from_search_and_the_answer_becomes_the_candidate(self):
        self.cfg.network_geocoding = True
        self.page.query.setText("Rho, Milano")
        self.page.search.click()
        self.page.send.assert_called_once()
        request = self.page.send.call_args.args[0]
        self.assertIn("nominatim.openstreetmap.org", request.url().toString())
        self.page.show_answer(b'[{"display_name":"Rho, Milano","lat":"45.5226","lon":"9.03"}]')
        self.page.found.setCurrentRow(0)
        self.assertEqual(self.page.candidate.lat, 45.5226)
        self.assertTrue(self.page.create.isEnabled())

    def test_create_and_draw_emits_the_site_and_optional_choices(self):
        from PySide6.QtTest import QSignalSpy
        spy = QSignalSpy(self.page.created)
        self.page.query.setText("45.5226, 9.03")
        self.page.name.setText("Impianto Rho")
        self.page.reserved.setChecked(True)
        self.page.distributor.setText("E-distribuzione")
        self.page.pod.setText("IT001E12345678")
        self.page.voltage.setValue(400)
        self.page.available.setValue(30)
        self.page.requested.setValue(25)
        self.page.practice.setText("PR-2026-42")
        self.page.create.click()
        self.assertEqual(spy.count(), 1)
        data = spy.at(0)[0]
        self.assertEqual((data["name"], data["reserved"]), ("Impianto Rho", True))
        self.assertEqual((data["site"].lat, data["site"].lon), (45.5226, 9.03))
        self.assertEqual(data["site"].address, "45.5226, 9.03")
        self.assertEqual(data["network"].distributor, "E-distribuzione")
        self.assertEqual(data["network"].technical_rule(), "CEI 0-21")
        self.assertEqual(data["network"].available_kw, 30)
        self.assertEqual(data["network"].requested_kw, 25)


if __name__ == "__main__":
    unittest.main()
