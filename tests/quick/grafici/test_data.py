"""R389/R394: the Quick result pages carry the exact Widgets numbers and sources."""

import dataclasses
import ast
import importlib
import inspect
import json
import math
import subprocess
import sys
from types import SimpleNamespace
import unittest

import _setup
import numpy as np


setUpModule = _setup.keep_global_state


def plain(value):
    """The JSON representation, including calendar holes and unavailable results."""
    if dataclasses.is_dataclass(value):
        return plain(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [plain(item) for item in value]
    if isinstance(value, np.generic):
        return plain(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


class Text:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


class Tile:
    def __init__(self):
        self.value, self.detail, self.more = "", "", ""

    def set(self, value, detail="", more=""):
        self.value, self.detail, self.more = value, detail, more


class ChartCalls:
    def __init__(self):
        self.call = None

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.call = name, args, kwargs

        return record


CHARTS = {
    "production": ("monthly", "losses_chart", "day"),
    "consumption": ("monthly", "day", "year_map", "week", "duration"),
    "economics": (
        "prod_split",
        "cons_split",
        "self_map",
        "bill",
        "cash",
        "flows",
        "size_share",
        "size_npv",
        "store_share",
        "store_npv",
    ),
}


def recipient(kind):
    out = SimpleNamespace(status=Text(), tiles=[Tile() for _ in range(10)], records=[])
    out.pedigree = SimpleNamespace(show_records=lambda records: out.records.extend(records))
    out.size_note, out.store_note = Text(), Text()
    for name in CHARTS[kind]:
        setattr(out, name, ChartCalls())
    return out


class ResultData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Delay the import so the first RED run is an explicit assertion on the missing feature.
        cls.module_name = "meridiana.quick.backend.charts_data"
        cls.module_path = _setup.ROOT / "src/meridiana/quick/backend/charts_data.py"
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
        from meridiana.ui import energy_pages
        from meridiana.ui.charts import Chart

        cls = {
            "production": energy_pages.EnergyPage,
            "consumption": energy_pages.ConsumptionPage,
            "economics": energy_pages.EconomicsPage,
        }[kind]
        expected = recipient(kind)
        cls.show_results(expected, *args)
        if kind == "economics":
            cls.show_sizing(expected, *(extra or (None, None, 0, 0)))
        kwargs = dict(zip(("sizing", "storage", "p_stc_kw", "battery_kwh"), extra, strict=True)) if extra else {}
        page = getattr(self.data, kind)(*args, **kwargs)
        self.assertEqual(page["status"], expected.status.text)
        for tile, recorded in zip(page["tiles"], expected.tiles, strict=False):
            self.assertEqual(
                [tile[k] for k in ("value", "detail", "more")], [recorded.value, recorded.detail, recorded.more]
            )
        # each record also carries its steps laid out as the report lays them out (R460, report_typst.steps.for_window):
        # the records of the Widgets plus that view, made from the same records
        from meridiana.quick.backend.charts_data import pedigree
        self.assertEqual([{k: v for k, v in record.items() if k != "view"} for record in page["records"]],
                         plain(expected.records))
        self.assertEqual(page["records"], pedigree(expected.records))
        if kind == "economics":
            self.assertEqual(page["tabs"][5]["note"], expected.size_note.text)
            self.assertEqual(page["tabs"][6]["note"], expected.store_note.text)
        available = {c["id"]: c for tab in page["tabs"] for c in tab["charts"]}
        for name in CHARTS[kind]:
            call = getattr(expected, name).call
            if call is None:
                continue
            method, values, options = call
            actual = available[name]
            self.assertEqual(actual["kind"], method)
            bound = inspect.signature(getattr(Chart, method)).bind(None, *values, **options)
            bound.apply_defaults()
            mapping = {"labels": "categories", "values": "series", "text": "message"}
            for key, value in bound.arguments.items():
                if key in ("self", "action"):
                    continue
                if key == "values":
                    self.assertEqual(actual["series"][0][1], plain(value))
                else:
                    self.assertEqual(actual[mapping.get(key, key)], plain(value), (name, key))
            # The real Chart method also provides the independent raw-table reference.
            app = _setup.qt_or_skip()
            chart = Chart()
            self.addCleanup(chart.deleteLater)
            getattr(Chart, method).__wrapped__(chart, *values, **options)
            if method == "message":
                # R394 intentionally removes the Widgets table containing just the empty-state sentence.
                self.assertEqual(actual["table"], {"headers": [], "rows": [], "units": [], "totals": []})
            else:
                self.assertEqual(actual["table"]["headers"], plain(chart.numbers.columns), name)
                self.assertEqual(actual["table"]["rows"], plain(chart.numbers.rows), name)
                self.assertEqual(actual["table"]["units"], [""] + [actual["unit"]] * (len(chart.numbers.columns) - 1))
            if method == "bars":
                totals = [None] + [float(sum(series)) for _, series in values[1]]
                self.assertEqual(actual["table"]["totals"], totals)
            else:
                self.assertEqual(actual["table"]["totals"], [])
            app.processEvents()
        json.dumps(page, allow_nan=False)
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

        source = ast.parse((_setup.ROOT / "src/meridiana/ui/energy_pages.py").read_text(encoding="utf-8"))
        for language in ("en", "it"):
            i18n.setup(language)
            for cls_name, kind in (
                ("EnergyPage", "production"),
                ("ConsumptionPage", "consumption"),
                ("EconomicsPage", "economics"),
            ):
                cls = next(n for n in source.body if isinstance(n, ast.ClassDef) and n.name == cls_name)
                constructor = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")

                def evaluate(node):
                    if isinstance(node, ast.Constant):
                        return node.value
                    if isinstance(node, ast.List):
                        return [evaluate(item) for item in node.elts]
                    return i18n._(node.args[0].value)

                chart_titles, tabs, labels = {}, [], []
                for node in constructor.body:
                    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                        call = node.value
                        if isinstance(call.func, ast.Name) and call.func.id == "Tiles":
                            labels = evaluate(call.args[0])
                        if isinstance(call.func, ast.Name) and call.func.id == "register":
                            call = call.args[0]
                        if isinstance(call.func, ast.Name) and call.func.id == "Chart":
                            chart_titles[node.targets[0].attr] = evaluate(call.args[0])
                    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                        call = node.value
                        if isinstance(call.func, ast.Attribute) and call.func.attr == "addTab":
                            tabs.append(evaluate(call.args[1]))
                page = getattr(self.data, kind)(None)
                self.assertEqual([tile["label"] for tile in page["tiles"]], labels)
                self.assertEqual([tab["title"] for tab in page["tabs"]], tabs)
                self.assertEqual({c["id"]: c["title"] for tab in page["tabs"] for c in tab["charts"]}, chart_titles)
        i18n.setup("en")

    def test_economics_and_sizing_match_all_widget_results(self):
        page = self.compare_page("economics", (self.econ,), (self.sizing, self.storage_sizing, self.sim.p_stc_kw, 5))
        self.assertEqual(len(page["tiles"]), 10)
        self.assertTrue(page["records"][0]["steps"])
        self.assertTrue(any(step["formula"] for step in page["records"][0]["steps"]))

    def test_pedigree_keeps_the_model_limits_and_translated_source_kinds(self):
        from meridiana.energy.pedigree import kind_names, limits

        for kind, result in (("production", self.sim), ("consumption", self.load), ("economics", self.econ)):
            page = getattr(self.data, kind)(result)
            self.assertEqual(page.get("limits"), limits())
            self.assertEqual(page.get("source_kinds"), kind_names())
        self.assertEqual(self.data.production(None).get("limits"), [])

    def test_battery_and_zero_production(self):
        from meridiana.energy import economics

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
            "import sys; import meridiana.quick.backend.charts_data; "
            "assert not any(n.startswith(('PySide6.QtWidgets', 'pyqtgraph', 'meridiana.ui')) "
            "for n in sys.modules)"
        )
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_storage_matches_validation_messages_and_sources(self):
        from meridiana.ui.storage_page import StoragePage

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
            expected = SimpleNamespace(
                _battery=battery,
                name=Text(),
                patch=lambda s=settings: s,
                status=Text(),
                inverter=SimpleNamespace(setEnabled=lambda value: None),
                apply_button=SimpleNamespace(setEnabled=lambda value: None),
            )
            StoragePage._refresh(expected)
            page = self.data.storage(settings)
            self.assertEqual(page["status"], expected.status.text)
            self.assertEqual(page["tiles"][0]["value"], expected.name.text)
            self.assertEqual(page["empty"], not bool(battery))
            json.dumps(page, allow_nan=False)

    def test_storage_defaults_and_documented_dc_pairing_match_the_page(self):
        from meridiana.ui.storage_page import StoragePage

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
                enabled = []
                expected = SimpleNamespace(
                    _battery=battery,
                    name=Text(),
                    status=Text(),
                    coupling=SimpleNamespace(currentData=lambda c=coupling: "dc" if c == "dc" else "ac"),
                    inverter=SimpleNamespace(currentData=lambda: inverter, setEnabled=lambda v: None),
                    units=SimpleNamespace(value=lambda n=count: n),
                    efficiency=SimpleNamespace(value=lambda: 85),
                    apply_button=SimpleNamespace(setEnabled=enabled.append),
                )
                expected.patch = lambda e=expected: StoragePage.patch(e)
                StoragePage._refresh(expected)
                page = self.data.storage(settings)
                self.assertEqual(page["status"], expected.status.text)
                self.assertEqual(page["valid"], enabled[-1])
                if coupling == "dc" and count == 1:
                    self.assertTrue(page["records"][0]["sources"])
