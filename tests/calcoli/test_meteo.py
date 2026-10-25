"""The weather of the site from PVGIS 5.3, read from its answers recorded once (tests/calcoli/riferimenti, with
their README) through pvlib's own parser: the typical year, the far horizon, the second opinion PVcalc, and
the errors (the 400 of a point at sea, a 403, an answer cut short, a column missing). When PVGIS 5.3 does not
answer: the typical year and the horizon from PVGIS 6, turned into what the rest of Meridiana reads (8760 hours
of 1990 in UTC, the diffuse from the global and the direct, the sun half an hour after the time stamp), with the
source said. No network: the answers of PVGIS 6 are made up here."""

import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup
import numpy as np
import pandas as pd
import requests

from meridiana.energy import meteo, pvgis

REF = _setup.REFERENCES


def recorded(name: str) -> bytes:
    data = (REF / name).read_bytes()
    return gzip.decompress(data) if name.endswith(".gz") else data


def answer(body: bytes, status: int = 200, url: str = "") -> requests.Response:
    """A requests.Response as the network gives it: its status, its bytes, JSON."""
    r = requests.Response()
    r.status_code, r._content, r.url = status, body, url
    r.reason = {200: "OK", 400: "BAD REQUEST", 403: "Forbidden"}.get(status, "")
    r.headers["Content-Type"] = "application/json" if body[:1] in (b"{", b"[") else "text/html"
    r.encoding = "utf-8"
    return r


class PVGIS53(unittest.TestCase):
    """The answers of PVGIS 5.3 of 24/10/2026 for Rho (MI), as recorded."""

    def setUp(self):
        self.cache = Path(tempfile.mkdtemp())
        self.asked = []

    def network(self, *bodies):
        """requests.get answering with these, in turn, and noting what was asked."""
        queue = list(bodies)

        def get(url, params=None, **kwargs):
            self.asked.append((url, dict(params or {})))
            return queue.pop(0)
        return mock.patch.object(requests, "get", side_effect=get)

    def test_the_typical_year_of_rho_is_read_as_pvgis_wrote_it(self):
        raw = json.loads(recorded("pvgis53-tmy-rho.json.gz"))
        with self.network(answer(recorded("pvgis53-tmy-rho.json.gz"))):
            m = meteo.typical_year(45.5226, 9.03, self.cache)
        url, params = self.asked[0]
        self.assertEqual(url, meteo.PVGIS_URL + "tmy")
        self.assertEqual(params, {"lat": 45.5226, "lon": 9.03, "outputformat": "json", "usehorizon": 0})
        self.assertEqual(len(m.data), 8760)
        self.assertEqual(m.data.index[0], pd.Timestamp("1990-01-01 00:00", tz="UTC"))
        self.assertEqual((m.elevation, m.time_offset_h), (151.0, 0.1767))
        self.assertEqual(m.source.label, "PVGIS 5.3, typical year from PVGIS-SARAH3 + ERA5, 2005-2023")
        rows = raw["outputs"]["tmy_hourly"]
        self.assertAlmostEqual(m.summary["ghi_kwh_m2"], sum(r["G(h)"] for r in rows) / 1000, places=6)   # 1449,8
        self.assertAlmostEqual(m.summary["t_mean"], 13.0708, places=4)
        for hour in (0, 12, 4000, 8759):                    # PVGIS's columns under pvlib's names, hour by hour
            r = rows[hour]
            self.assertEqual([m.data.ghi.iloc[hour], m.data.dni.iloc[hour], m.data.dhi.iloc[hour],
                              m.data.temp_air.iloc[hour], m.data.wind_speed.iloc[hour], m.data.pressure.iloc[hour],
                              m.data.relative_humidity.iloc[hour]],
                             [r["G(h)"], r["Gb(n)"], r["Gd(h)"], r["T2m"], r["WS10m"], r["SP"], r["RH"]])
        with self.network():                                 # from the cache: nothing asked
            again = meteo.typical_year(45.5226, 9.03, self.cache)
        self.assertEqual(len(self.asked), 1)
        self.assertEqual(again.source.label, m.source.label)
        self.assertTrue((again.data == m.data).all().all())

    def test_the_horizon_of_rho_comes_from_the_terrain_model_with_north_at_zero(self):
        with self.network(answer(recorded("pvgis53-printhorizon-rho.json"))):
            h = meteo.horizon(45.5226, 9.03, self.cache)
        self.assertEqual(self.asked[0][0], meteo.PVGIS_URL + "printhorizon")
        self.assertIn("PVGIS 5.3, horizon from the terrain model", h.source.label)
        self.assertEqual(len(h.azimuth), 48)                 # 49 directions, North written twice
        # PVGIS counts from the South (A = -180 is North); Meridiana from the North, clockwise
        self.assertAlmostEqual(float(h.at(0.0)), 1.5)        # A = -180
        self.assertAlmostEqual(float(h.at(30.0)), 1.9)       # A = -150, the highest: the Alps to the NNE
        self.assertAlmostEqual(float(h.at(180.0)), 0.8)      # A = 0, the South
        self.assertAlmostEqual(float(h.at(26.25)), (1.1 + 1.9) / 2)    # between 22,5 and 30 degrees, interpolated
        self.assertGreater(h.diffuse_factor(15.0, 180.0), 0.99)        # a horizon this low hides little sky

    def test_a_damaged_horizon_profile_speaks_italian(self):
        from meridiana import i18n
        path = meteo._cache_file(self.cache, "horizon", 45.5226, 9.03)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"fetched": "2026-10-25", "azimuth": [0.0], "elevation": [1.0]}), encoding="utf-8")
        before = i18n._translation
        self.addCleanup(lambda: setattr(i18n, "_translation", before))
        i18n.setup("it")
        with self.assertRaises(meteo.MeteoError) as caught:
            meteo.horizon(45.5226, 9.03, self.cache)
        self.assertEqual(str(caught.exception), "profilo dell'orizzonte danneggiato")

    def test_a_point_at_sea_is_said_with_pvgis_s_own_words(self):
        with self.network(answer(recorded("pvgis53-tmy-mare-400.json"), 400)), \
                mock.patch.object(meteo, "_get_json", side_effect=requests.ConnectionError("no network")):
            with self.assertRaises(meteo.MeteoError) as caught:
                meteo.typical_year(40.0, -30.0, self.cache)
        self.assertIn("Location over the sea", str(caught.exception))
        self.assertIn("PVGIS 6", str(caught.exception))

    def test_a_blocked_address_goes_to_pvgis_6(self):
        with self.network(answer(b"This url is blocked", 403)), \
                mock.patch.object(meteo, "_get_json", side_effect=fake_get):
            m = meteo.typical_year(45.5, 9.2, self.cache)
        self.assertIn("PVGIS 6 (beta)", m.source.label)

    def test_an_answer_cut_short_or_without_a_column_is_said_and_not_kept(self):
        raw = json.loads(recorded("pvgis53-tmy-rho.json.gz"))
        short = {**raw, "outputs": {**raw["outputs"], "tmy_hourly": raw["outputs"]["tmy_hourly"][:100]}}
        without = {**raw, "outputs": {**raw["outputs"], "tmy_hourly": [
            {k: v for k, v in r.items() if k != "Gd(h)"} for r in raw["outputs"]["tmy_hourly"]]}}
        for broken, words, gone in ((short, "answered 100 hours", "'IR(h)'"),
                                    (without, "8760 hours with columns", "'dhi'")):
            with self.subTest(words=words), self.network(answer(json.dumps(broken).encode())):
                with self.assertRaises(meteo.MeteoError) as caught:
                    meteo.typical_year(45.5226, 9.03, self.cache)
                self.assertIn(words, str(caught.exception))
                self.assertEqual(gone in str(caught.exception), broken is short)    # the column missing, not listed
                self.assertFalse(meteo.cached(45.5226, 9.03, self.cache))     # nothing damaged in the cache

    def test_the_second_opinion_is_pvgis_s_own_estimate_and_stays_in_the_cache(self):
        with self.network(answer(recorded("pvgis53-pvcalc-rho.json"))):
            e = pvgis.pvcalc(45.5226, 9.03, 10.0, 15.0, 0.0, 14.0, self.cache)
        url, _params = self.asked[0]
        self.assertTrue(url.startswith(meteo.PVGIS_URL + "PVcalc?lat=45.52260&lon=9.03000&peakpower=10.000&loss=14.00"))
        self.assertIn("pvtechchoice=crystSi2025", url)
        self.assertAlmostEqual(e.yearly_kwh, 13220.71, places=2)
        self.assertEqual(len(e.monthly_kwh), 12)
        self.assertAlmostEqual(e.monthly_kwh[6], 1742.24, places=2)               # July
        self.assertAlmostEqual(sum(e.monthly_kwh), e.yearly_kwh, delta=1.0)
        self.assertIn("PVGIS 5.3 PVcalc (PVGIS-SARAH3), system losses 14%", e.source.label)
        with self.network():                                 # the cache, and no network needed for it
            again = pvgis.pvcalc(45.5226, 9.03, 10.0, 15.0, 0.0, 14.0, self.cache, network=False)
        self.assertEqual((again.yearly_kwh, len(self.asked)), (e.yearly_kwh, 1))

    def test_the_second_opinion_refused_or_strange_is_said(self):
        with self.assertRaises(meteo.MeteoError) as caught:
            pvgis.pvcalc(45.5226, 9.03, 10.0, 15.0, 0.0, 14.0, self.cache, network=False)
        self.assertIn("not in the cache yet", str(caught.exception))
        with self.network(answer(b"This url is blocked", 403)), self.assertRaises(meteo.MeteoError) as caught:
            pvgis.pvcalc(45.5226, 9.03, 10.0, 15.0, 0.0, 14.0, self.cache)
        self.assertIn("403", str(caught.exception))
        strange = json.loads(recorded("pvgis53-pvcalc-rho.json"))
        del strange["outputs"]["totals"]
        with self.network(answer(json.dumps(strange).encode())), self.assertRaises(meteo.MeteoError) as caught:
            pvgis.pvcalc(45.5226, 9.03, 10.0, 15.0, 0.0, 14.0, self.cache)
        self.assertIn("answered something unexpected", str(caught.exception))


def v6_answer(lat=45.5, lon=9.2):
    """A PVGIS 6 typical year as the service gives it: months from different years, one of them a leap
    February with its 29th, a few hours missing."""
    years = {1: 2015, 2: 2020, 3: 2019, 4: 2021, 5: 2017, 6: 2022, 7: 2020, 8: 2016, 9: 2022, 10: 2014, 11: 2022,
             12: 2019}
    stamps = []
    for month, year in years.items():
        start = pd.Timestamp(year=year, month=month, day=1)
        stamps += list(pd.date_range(start, start + pd.offsets.MonthEnd(1) + pd.Timedelta(hours=23), freq="h"))
    index = pd.DatetimeIndex(stamps)
    hours = index.hour.to_numpy() + 0.5
    day = np.clip(np.sin((hours - 6.0) / 12.0 * np.pi), 0.0, None)
    ghi = 700.0 * day
    dni = 600.0 * day
    ghi[100:103] = np.nan
    values = {"mean_global_horizontal_irradiance": ghi, "mean_direct_normal_irradiance": dni,
              "mean_dry_bulb_temperature": np.full(len(index), 12.0), "mean_wind_velocity": np.full(len(index), 2.0),
              "mean_surface_pressure": np.full(len(index), 101000.0),
              "mean_relative_humidity": np.full(len(index), 70.0)}
    times = [t.strftime("%Y-%m-%d %H:%M:%S") for t in index]
    tmy = {k: {"time": times, "values": [None if np.isnan(v) else float(v) for v in vals]} for k, vals in values.items()}
    return {"source_years": {pd.Timestamp(2000, m, 1).strftime("%B"): y for m, y in years.items()},
            "typical_meteorological_year": tmy}


def fake_get(url, params, timeout):
    if url.endswith("typical-meteorological-year"):
        return v6_answer()
    if url.endswith("topography/elevation"):
        return {"latitude": 0.79, "longitude": 0.16, "elevation": 140.0}
    if url.endswith("topography/horizon-profile"):
        return {"horizon_profile": {"azimuth": [0.0, 90.0, 180.0, 270.0], "horizon_height": [1.0, 2.0, 3.0, 2.0]}}
    raise AssertionError(url)


class PVGIS6(unittest.TestCase):
    def setUp(self):
        self.cache = Path(tempfile.mkdtemp())

    def test_the_typical_year_comes_from_pvgis_6_when_5_3_does_not_answer(self):
        blocked = requests.HTTPError("403 Client Error: Forbidden")
        with mock.patch("pvlib.iotools.get_pvgis_tmy", side_effect=blocked), \
                mock.patch.object(meteo, "_get_json", side_effect=fake_get):
            m = meteo.typical_year(45.5, 9.2, self.cache)
        self.assertEqual(len(m.data), 8760)
        self.assertEqual(m.data.index[0], pd.Timestamp("1990-01-01 00:00", tz="UTC"))
        self.assertEqual(m.time_offset_h, 0.5)                   # the mean of the hour after the stamp
        self.assertEqual(m.elevation, 140.0)
        self.assertIn("PVGIS 6 (beta)", m.source.label)
        self.assertIn("2014-2022", m.source.label)
        d = m.data
        self.assertFalse(d.isna().any().any())                   # the missing hours filled
        self.assertTrue((d.dhi <= d.ghi + 1e-9).all())
        self.assertTrue((d.dhi >= 0).all())
        self.assertGreater(d.dhi.sum(), 0)
        again = meteo.typical_year(45.5, 9.2, self.cache)       # from the cache, the same source
        self.assertEqual(again.source.label, m.source.label)

    def test_when_neither_answers_both_are_said(self):
        with mock.patch("pvlib.iotools.get_pvgis_tmy", side_effect=requests.HTTPError("403")), \
                mock.patch.object(meteo, "_get_json", side_effect=requests.ConnectionError("no network")):
            with self.assertRaises(meteo.MeteoError) as caught:
                meteo.typical_year(45.5, 9.2, self.cache)
        self.assertIn("PVGIS 5.3", str(caught.exception))
        self.assertIn("PVGIS 6", str(caught.exception))

    def test_the_horizon_comes_from_pvgis_6_too(self):
        with mock.patch("pvlib.iotools.get_pvgis_horizon", side_effect=requests.HTTPError("403")), \
                mock.patch.object(meteo, "_get_json", side_effect=fake_get):
            h = meteo.horizon(45.5, 9.2, self.cache)
        self.assertIn("PVGIS 6 (beta)", h.source.label)
        self.assertAlmostEqual(float(h.at(180.0)), 3.0)


if __name__ == "__main__":
    unittest.main()
