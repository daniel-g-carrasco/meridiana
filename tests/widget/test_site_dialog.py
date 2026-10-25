"""The dialog of the site (ui/site_dialog.py) without the network: the places found listed and the chosen one in
the site, an answer unreadable or late said, the coordinates typed taken when the search is off (Privacy). The
request and the answer of Nominatim themselves are in nucleo/test_geocoding.py. PySide6 and a display (offscreen
will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Dialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_places_found_are_listed_and_the_chosen_one_fills_the_site(self):
        from meridiana import model
        from meridiana.ui.site_dialog import SiteDialog
        dialog = SiteDialog(model.Site(), network=False)
        self.addCleanup(dialog.deleteLater)
        dialog.show_answer(b'[{"display_name": "Rho, Milano", "lat": "45.5226", "lon": "9.03"}]')
        self.assertEqual(dialog.found.count(), 1)
        self.assertIn("1 place found", dialog.status.text())
        dialog.found.setCurrentRow(0)
        site = dialog.result()
        self.assertEqual((site.lat, site.lon, site.address), (45.5226, 9.03, "Rho, Milano"))
        dialog.show_answer(b"nonsense")
        self.assertIn("unreadable", dialog.status.text())
        dialog.show_answer(None, "timed out")
        self.assertIn("timed out", dialog.status.text())
        # the search is off: the coordinates typed still work
        dialog.query.setText("45,5; 9,1")
        dialog._search()
        self.assertEqual((dialog.lat.value(), dialog.lon.value()), (45.5, 9.1))
        dialog.query.setText("via Roma")
        dialog._search()
        self.assertIn("Privacy", dialog.status.text())


if __name__ == "__main__":
    unittest.main()
