"""A saved project carries the catalogue records and the external resources it uses (R150)."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401
from _fixtures import capannone, clear_sky_meteo, inverter_record, write_cache

from meridiana import atomic, catalog, jobs, model, paths, portability
from meridiana.energy import meteo, pipeline


class AutonomousProject(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())

    def test_custom_products_attachments_logo_and_weather_survive_an_empty_profile(self):
        source = self.folder / "source"
        cache = self.folder / "first-cache"
        source.mkdir(parents=True)
        p = capannone("Portable design")
        custom_module = {"manufacturer": "Acme", "model": "Custom module", "length": 2.0, "width": 1.1,
                         "power_kw": 0.555, "pmax": 555.0, "vmp": 34.0, "imp": 16.3, "voc": 41.0,
                         "isc": 17.0, "cells": 108}
        p.modules = {"custom-module": custom_module}
        p.subfields[0].module = "custom-module"
        custom_inverter = inverter_record(manufacturer="Acme", model="Custom inverter")
        custom_optimizer = {"manufacturer": "Acme", "model": "Custom optimizer", "efficiency_pct": 99.0,
                            "max_input_current_a": 18.0, "max_input_isc_a": 20.0, "max_system_voltage_v": 60.0,
                            "max_power_w": 700.0}
        p.energy["inverters"] = [{"record": custom_inverter, "count": 1, "name": "",
                                  "optimizer": custom_optimizer, "per_optimizer": 1}]
        p.energy["strings"] = {"runs": [{"inverter": 1, "mppt": 1,
                                          "modules": [f"s1/{pm.key}" for pm in jobs.layout_of(p)[0]["s1"].modules[:12]]}]}
        attachment = source / "custom-sheet.pdf"
        attachment.write_bytes(b"%PDF-1.4\n% invented test attachment\n")
        logo = source / "studio.png"
        logo.write_bytes(b"invented image bytes")
        p.report = {"profile": "Studio", "attachments": [{"path": str(attachment), "title": "Custom sheet"}]}
        profile = {"name": "Studio", "signer": "A. Designer", "logo": str(logo)}
        write_cache(clear_sky_meteo(), cache)
        horizon = {"fetched": "2026-10-21", "azimuth": [0.0, 180.0], "elevation": [1.0, 2.0]}
        atomic.write_json(meteo._cache_file(cache, "horizon", p.site.lat, p.site.lon), horizon, keep_backup=False)
        file = self.folder / "portable.meridiana"
        p.save(file, cache_dir=cache, report_profile=profile)

        attachment.unlink()
        logo.unlink()
        empty = paths.Paths.from_env({"HOME": str(self.folder / "empty-home"),
                                      "XDG_CACHE_HOME": str(self.folder / "empty-cache")}).cache
        with mock.patch.object(catalog, "load", side_effect=AssertionError("the catalogue must not be needed")), \
                mock.patch("requests.get", side_effect=AssertionError("the network must not be needed")):
            q, notice = model.Project.load(file, cache_dir=empty)
            results, _keys, _laid = jobs.layout_of(q)
            out = pipeline.compute(q, results, empty, fetch=False)
        self.assertIsNone(notice)
        self.assertEqual(q.modules["custom-module"], custom_module)
        self.assertEqual(q.energy["inverters"][0]["record"], custom_inverter)
        self.assertEqual(q.energy["inverters"][0]["optimizer"], custom_optimizer)
        self.assertEqual(Path(q.report["attachments"][0]["path"]).read_bytes(), b"%PDF-1.4\n% invented test attachment\n")
        embedded_profile = portability.profile(q, empty)
        self.assertEqual(embedded_profile["signer"], "A. Designer")
        self.assertEqual(Path(embedded_profile["logo"]).read_bytes(), b"invented image bytes")
        self.assertIsNone(out.error_sim)
        self.assertGreater(out.sim.energy_kwh, 1000)
        self.assertEqual(json.loads(file.read_text(encoding="utf-8"))["version"], model.FORMAT_VERSION)

    def test_an_external_attachment_left_out_is_said_when_the_project_opens(self):
        p = capannone()
        p.report = {"attachments": [{"path": str(self.folder / "gone.pdf"), "title": "Missing sheet"}]}
        file = self.folder / "missing.meridiana"
        p.save(file)
        _q, notice = model.Project.load(file, cache_dir=self.folder / "empty")
        self.assertIn("Missing sheet", notice)
        self.assertIn("without an embedded copy", notice)

    def test_resaving_keeps_embedded_attachment_bytes_when_the_cache_is_gone(self):
        attachment = self.folder / "sheet.pdf"
        attachment.write_bytes(b"invented attachment bytes")
        p = capannone()
        p.report = {"attachments": [{"path": str(attachment), "title": "Sheet"}]}
        first = self.folder / "first.meridiana"
        p.save(first)
        attachment.unlink()
        q, _notice = model.Project.load(first, cache_dir=self.folder / "cache")
        Path(q.report["attachments"][0]["path"]).unlink()
        second = self.folder / "second.meridiana"
        q.save(second)
        raw = json.loads(second.read_text(encoding="utf-8"))
        self.assertIn("data", raw["report"]["attachments"][0])
        loaded, _notice = model.Project.load(second, cache_dir=self.folder / "empty")
        self.assertEqual(Path(loaded.report["attachments"][0]["path"]).read_bytes(), b"invented attachment bytes")

    def test_new_site_weather_does_not_keep_the_old_site_horizon(self):
        p = capannone()
        first_cache = self.folder / "first-cache"
        write_cache(clear_sky_meteo(), first_cache)
        atomic.write_json(meteo._cache_file(first_cache, "horizon", p.site.lat, p.site.lon),
                          {"azimuth": [0.0], "elevation": [30.0]}, keep_backup=False)
        p.resources = {"weather": {"tmy": clear_sky_meteo(), "horizon": {"azimuth": [0.0], "elevation": [30.0]}}}
        p.site = model.Site(lat=40.0, lon=14.0)
        second_cache = self.folder / "second-cache"
        write_cache(clear_sky_meteo(lat=40.0, lon=14.0), second_cache)
        file = self.folder / "mixed.meridiana"
        p.save(file, cache_dir=second_cache)
        q, _notice = model.Project.load(file, cache_dir=self.folder / "empty")
        self.assertNotIn("horizon", q.resources["weather"])

    def test_weather_embedded_for_another_site_is_not_used(self):
        cache = self.folder / "cache"
        p = capannone()
        write_cache(clear_sky_meteo(), cache)
        file = self.folder / "weather.meridiana"
        p.save(file, cache_dir=cache)
        q, _notice = model.Project.load(file, cache_dir=self.folder / "empty")
        q.site = model.Site(lat=40.0, lon=14.0)
        out = pipeline.compute(q, jobs.layout_of(q)[0], self.folder / "no-cache", fetch=False)
        self.assertIsNone(out.sim)
        self.assertIn("Fetch the weather", out.error_sim)


if __name__ == "__main__":
    unittest.main()
