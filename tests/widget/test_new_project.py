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
        self.assertEqual(self.page.suggestions.stringList(), ["Rho, Milano"])
        self.page.choose_suggestion("Rho, Milano")
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

    def test_completion_text_is_inserted_before_activation_without_losing_the_local_point(self):
        self.page.query.setText("rh")
        completion = self.page.suggestions.stringList()[0]
        # QCompleter inserts the chosen text, emitting textChanged, before activated.
        self.page.query.setText(completion)
        self.page.query.completer().activated[str].emit(completion)
        self.assertIsNotNone(self.page.candidate)
        self.assertEqual((self.page.candidate.lat, self.page.candidate.lon), (45.53178, 9.046984))
        self.assertEqual(self.page.query.text(), "Rho, Milano")
        self.assertEqual(self.page.address, "Rho, Milano")

    def test_street_numbers_and_numbered_municipalities_are_searched_as_places(self):
        from urllib.parse import parse_qs, urlsplit
        self.cfg.network_geocoding = True
        for text in ("Via Roma 1, Rho", "San Giorgio delle Pertiche 35010", "4 Novembre, Milano"):
            with self.subTest(text=text):
                self.page.query.setText(text)
                self.page.throttle.last = -self.page.throttle.interval
                self.page.search.click()
                self.assertTrue(self.page.send.called)
                url = self.page.send.call_args.args[0].url().toString()
                self.assertEqual(parse_qs(urlsplit(url).query)["q"], [text])
                self.page.send.reset_mock()

    def test_optional_fields_stay_visible_disabled_and_keep_their_values(self):
        self.page.resize(1300, 850)
        self.page.show()
        self.app.processEvents()
        self.assertTrue(self.page.name.isVisibleTo(self.page))
        self.assertFalse(self.page.name.isEnabled())
        self.page.optional.setChecked(True)
        self.page.name.setText("Rho roof")
        self.page.optional.setChecked(False)
        self.assertTrue(self.page.name.isVisibleTo(self.page))
        self.assertFalse(self.page.name.isEnabled())
        self.page.optional.setChecked(True)
        self.assertEqual(self.page.name.text(), "Rho roof")
        self.assertTrue(self.page.name.isEnabled())

    def test_privacy_and_optional_toggles_do_not_resize_the_page_or_map(self):
        self.page.resize(1300, 850)
        self.page.show()
        self.app.processEvents()
        geometry = (self.page.size(), self.page.preview.geometry(), self.page.minimumSizeHint().width())
        for optional, reserved in ((True, False), (True, True), (False, True), (False, False)):
            self.page.optional.setChecked(optional)
            self.page.reserved.setChecked(reserved)
            self.app.processEvents()
            self.assertEqual((self.page.size(), self.page.preview.geometry(), self.page.minimumSizeHint().width()),
                             geometry)

    def test_initial_preview_draws_the_offline_map_without_fetching_tiles(self):
        self.page.resize(1300, 850)
        with mock.patch.object(self.page.preview.loader.net, "get") as get:
            self.cfg.network_tiles = True
            self.page.show()
            self.app.processEvents()
            self.assertTrue(any(item.isVisible() for item in self.page.preview.world.country_items.values()))
            self.assertFalse(self.page.preview.veil.isVisible())
            self.assertFalse(self.page.preview.site_mark.isVisible())
            self.assertTrue(self.page.preview.loader.offline)
            self.assertIn("Natural Earth", self.page.preview.attribution.full)
            get.assert_not_called()

    def test_online_tiles_start_for_a_selected_point_and_stop_when_the_page_hides(self):
        self.cfg.network_tiles = True
        self.page.show()
        with mock.patch.object(self.page.preview.loader, "request") as request:
            self.page.query.setText("45.5226, 9.03")
            self.page.preview._update_tiles()
            self.assertFalse(self.page.preview.loader.offline)
            request.assert_called()
            self.page.hide()
            self.assertTrue(self.page.preview.loader.offline)

    def test_separate_coordinates_accept_a_maps_pair_pasted_into_latitude(self):
        self.page.latitude.setText("45.5226, 9.0300")
        self.assertAlmostEqual(float(self.page.latitude.text()), 45.5226)
        self.assertAlmostEqual(float(self.page.longitude.text()), 9.03)
        self.assertAlmostEqual(self.page.candidate.lat, 45.5226)
        self.page.longitude.setText("9,05")
        self.assertAlmostEqual(self.page.candidate.lon, 9.05)
        self.page.latitude.setText("95")
        self.assertIsNone(self.page.candidate)
        self.assertFalse(self.page.create.isEnabled())

    def test_reset_clears_coordinates_entered_without_the_search_field(self):
        self.page.latitude.setText("45.5226, 9.03")
        self.page.reset()
        self.assertEqual((self.page.latitude.text(), self.page.longitude.text()), ("", ""))
        self.assertIsNone(self.page.candidate)

    def test_typing_decimal_coordinates_does_not_replace_the_edit_in_progress(self):
        from PySide6.QtTest import QTest
        self.page.latitude.setText("45")
        self.page.longitude.setText("9")
        QTest.keyClicks(self.page.longitude, ".03")
        self.assertEqual(self.page.longitude.text(), "9.03")
        self.assertAlmostEqual(self.page.candidate.lon, 9.03)

    def test_an_italian_decimal_comma_in_latitude_does_not_become_a_second_coordinate(self):
        from PySide6.QtTest import QTest
        self.page.latitude.setText("45")
        self.page.longitude.setText("9.03")
        QTest.keyClicks(self.page.latitude, ",5")
        self.assertEqual(self.page.latitude.text(), "45,5")
        self.assertEqual(self.page.longitude.text(), "9.03")
        self.assertAlmostEqual(self.page.candidate.lat, 45.5)
        self.assertAlmostEqual(self.page.candidate.lon, 9.03)

    def test_a_click_in_the_equal_earth_preview_picks_the_point_actually_shown(self):
        from PySide6.QtCore import QPointF
        from meridiana import worldmap
        self.page.preview.world.set_scale(5000)
        x, y = worldmap.equal_earth(12.5, 41.9, self.page.preview.origin.lon, self.page.preview.origin.lat)
        lat, lon = self.page.preview.coordinates_at(QPointF(x, -y))
        self.assertAlmostEqual(lat, 41.9, places=8)
        self.assertAlmostEqual(lon, 12.5, places=8)


if __name__ == "__main__":
    unittest.main()
