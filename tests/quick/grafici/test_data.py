"""R389/R394: the Quick result pages carry the numbers and sources the Widgets showed (recorded on 10/11/2026,
quick/aiuti/riferimenti.py)."""

import dataclasses
import importlib
import json
import subprocess
import sys
import unittest

import _setup
from quick.aiuti import riferimenti


setUpModule = _setup.keep_global_state


class ResultData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Delay the import so the first RED run is an explicit assertion on the missing feature.
        cls.module_name = "meridiana.gui.backend.charts_data"
        cls.module_path = _setup.ROOT / "src/meridiana/gui/backend/charts_data.py"
        if not cls.module_path.exists():
            return
        cls.data = importlib.import_module(cls.module_name)
        from quick.grafici.fixtures import build_results

        results = build_results()
        for name in ("sim", "load", "econ", "pvgis", "sizing", "settings"):
            setattr(cls, name, getattr(results, name))
        cls.storage_sizing = results.storage

    def setUp(self):
        self.assertTrue(self.module_path.exists(), "Quick result adapter is not implemented")

    def compare_page(self, kind, args, extra=None):
        """The page of `kind` against its record (once the Widgets' own page, filled with the same results)."""
        kwargs = dict(zip(("sizing", "storage", "p_stc_kw", "battery_kwh"), extra, strict=True)) if extra else {}
        page = getattr(self.data, kind)(*args, **kwargs)
        json.dumps(page, allow_nan=False)
        riferimenti.check(self, page)
        return page

    def test_production_and_pvgis_match_every_widget_series_and_table(self):
        self.assertEqual(len(self.sim.hourly), 8760)
        self.assertGreater(self.sim.energy_kwh, 0)
        self.compare_page("production", (self.sim, self.pvgis))
        self.compare_page("production", (self.sim, None))

    def test_consumption_matches_calendar_week_and_duration(self):
        page = self.compare_page("consumption", (self.load,))
        self.assertEqual(len(page["tiles"]), 9)

    def test_zero_consumption_and_zero_pvgis_remain_numbers(self):
        load = dataclasses.replace(self.load, hourly=self.load.hourly * 0)
        self.compare_page("consumption", (load,))
        estimate = dataclasses.replace(self.pvgis, yearly_kwh=0.0, monthly_kwh=[0.0] * 12)
        self.compare_page("production", (self.sim, estimate))

    def test_titles_tiles_and_tab_order_match_widgets_in_both_languages(self):
        from meridiana import i18n

        for language in ("en", "it"):
            i18n.setup(language)
            for kind in ("production", "consumption", "economics"):
                page = getattr(self.data, kind)(None)
                riferimenti.check(self, {"tiles": [tile["label"] for tile in page["tiles"]],
                                         "tabs": [tab["title"] for tab in page["tabs"]],
                                         "charts": {c["id"]: c["title"] for tab in page["tabs"] for c in tab["charts"]}})
        i18n.setup("en")

    def test_economics_and_sizing_match_all_widget_results(self):
        page = self.compare_page("economics", (self.econ,), (self.sizing, self.storage_sizing, self.sim.p_stc_kw, 5))
        self.assertEqual(len(page["tiles"]), 10)
        self.assertTrue(page["records"][0]["steps"])
        self.assertTrue(any(step["formula"] for step in page["records"][0]["steps"]))

    def test_pedigree_keeps_the_model_limits_and_translated_source_kinds(self):
        from meridiana.core.energy.pedigree import kind_names, limits

        for kind, result in (("production", self.sim), ("consumption", self.load), ("economics", self.econ)):
            page = getattr(self.data, kind)(result)
            self.assertEqual(page.get("limits"), limits())
            self.assertEqual(page.get("source_kinds"), kind_names())
        self.assertEqual(self.data.production(None).get("limits"), [])

    def test_battery_and_zero_production(self):
        from meridiana.core.energy import economics

        settings = dataclasses.replace(
            self.settings,
            battery={
                "usable_energy_kwh": 5,
                "max_charge_power_w": 2500,
                "max_discharge_power_w": 2500,
                "round_trip_efficiency_pct": 90,
            },
        )
        for factor in (1, 0):
            econ = economics.evaluate(
                self.sim.hourly.e_kwh * factor, self.load.hourly, self.sim.p_stc_kw, self.sim.p_ac_kw, settings
            )
            self.compare_page("economics", (econ,))

    def test_empty_and_error_states_offer_a_command_without_fake_table(self):
        for kind in ("production", "consumption", "economics"):
            for error in ("", "Recorded failure"):
                page = getattr(self.data, kind)(None, error=error)
                self.assertTrue(page["empty"])
                self.assertTrue(page["action"])
                self.assertEqual(page["status"], error)
                for tab in page["tabs"]:
                    for chart in tab["charts"]:
                        self.assertEqual(chart["kind"], "message")
                        self.assertEqual(chart["table"]["rows"], [])

    def test_line_zoom_threshold_and_meaningful_totals(self):
        for n in (100, 101):
            chart = self.data.line(list(range(n)), [("load", [0.0] * n)], "kW")
            self.assertEqual(chart.to_dict()["zoomable"], n > 100)
            self.assertEqual(chart.table()["totals"], [])
        self.assertEqual(self.data.changes(["one", "two"], [-10, -20]).table()["totals"], [])
        self.assertEqual(self.data.bars(["a", "b"], [("share", [10, 20])], "%").table()["totals"], [])

    def test_missing_bar_addend_makes_only_its_total_unavailable(self):
        for missing in (None, float("nan"), float("inf"), -float("inf")):
            for factory in (
                self.data.bars,
                lambda categories, series, unit: self.data.ChartData(
                    kind="bars", categories=categories, series=series, unit=unit
                ),
            ):
                with self.subTest(missing=missing, factory=factory):
                    chart = factory(
                        ["Jan", "Feb"],
                        [("incomplete", [1.0, missing]), ("complete", [2.0, 3.0]), ("zero", [0.0, 0.0])],
                        "kWh",
                    )
                    table = chart.table()
                    self.assertEqual(table["rows"], [["Jan", 1.0, 2.0, 0.0], ["Feb", None, 3.0, 0.0]])
                    self.assertEqual(table["totals"], [None, None, 5.0, 0.0])
                    payload = chart.to_dict()
                    self.assertEqual(payload["table"], table)
                    json.dumps(payload, allow_nan=False)

    def test_adapter_import_does_not_load_widgets_or_pyqtgraph(self):
        script = (
            "import sys; import meridiana.gui.backend.charts_data; "
            "assert not any(n.startswith(('PySide6.QtWidgets', 'pyqtgraph')) "
            "for n in sys.modules)"
        )
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_storage_matches_validation_messages_and_sources(self):
        for battery in (
            {},
            {
                "manufacturer": "Example",
                "model": "5",
                "usable_energy_kwh": 5,
                "max_charge_power_w": 2500,
                "max_discharge_power_w": 2500,
                "round_trip_efficiency_pct": 90,
            },
        ):
            settings = {
                "battery": battery,
                "battery_units": 1,
                "storage_coupling": "ac",
                "storage_inverter": {},
                "storage_efficiency_pct": None,
            }
            page = self.data.storage(settings)
            riferimenti.check(self, {"status": page["status"], "name": page["tiles"][0]["value"]})
            self.assertEqual(page["empty"], not bool(battery))
            json.dumps(page, allow_nan=False)

    def test_storage_defaults_and_documented_dc_pairing_match_the_page(self):
        battery = {
            "manufacturer": "Maker",
            "model": "B",
            "usable_energy_kwh": 10,
            "max_charge_power_w": 5000,
            "max_discharge_power_w": 5000,
            "round_trip_efficiency_pct": 90,
            "coupling": "dc",
            "voltage_range_v": [200, 400],
        }
        inverter = {
            "type": "hybrid",
            "battery_voltage_range_v": [150, 450],
            "battery_charge_power_max_w": 3000,
            "battery_discharge_power_max_w": 3000,
            "battery_current_max_a": 100,
            "storage_compatibility": [
                {
                    "battery_manufacturer": "Maker",
                    "battery_model": "B",
                    "source": "https://manufacturer.test/list.pdf",
                    "page": 2,
                    "units_min": 1,
                    "units_max": 2,
                }
            ],
        }
        for coupling in ("dc", "", "ac"):
            for count in (1, 3):
                settings = dict(
                    battery=battery,
                    battery_units=count,
                    storage_coupling=coupling,
                    storage_inverter=inverter,
                    storage_efficiency_pct=85,
                )
                page = self.data.storage(settings)
                riferimenti.check(self, {"status": page["status"], "valid": page["valid"]})
                if coupling == "dc" and count == 1:
                    self.assertTrue(page["records"][0]["sources"])
