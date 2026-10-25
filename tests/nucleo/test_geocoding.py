"""The geocoding without the network (services/geocoding.py): the request as Nominatim wants it, its answer
read, the rule of one request a second; and the dialog that shows the places (ui/site_dialog.py)."""

import unittest

import _setup

from meridiana.services import geocoding

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Geocoding(unittest.TestCase):
    def test_the_request_asks_nominatim_for_italian_places_as_json(self):
        url = geocoding.search_url("via Roma 1, Rho")
        self.assertTrue(url.startswith("https://nominatim.openstreetmap.org/search?"))
        for piece in ("q=via+Roma+1%2C+Rho", "format=jsonv2", "limit=8", "countrycodes=it"):
            self.assertIn(piece, url)

    def test_the_answer_gives_the_places_with_their_coordinates(self):
        found = geocoding.places(b'[{"display_name": "Rho, Milano", "lat": "45.5226", "lon": "9.03"}]')
        self.assertEqual(found, [geocoding.Place("Rho, Milano", 45.5226, 9.03)])
        self.assertEqual(geocoding.places(b"[]"), [])

    def test_an_answer_that_is_not_what_nominatim_gives_is_refused(self):
        for payload in (b"<html>", b'{"a": 1}', b"[1]", b'[{"display_name": "x"}]', b'[{"lat": "north", "lon": "1"}]'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                geocoding.places(payload)

    def test_one_request_a_second(self):
        t = geocoding.Throttle()
        self.assertTrue(t.allow(100.0))
        self.assertFalse(t.allow(100.5))
        self.assertTrue(t.allow(101.0))


if __name__ == "__main__":
    unittest.main()
