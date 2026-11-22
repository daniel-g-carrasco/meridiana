"""The schema of the energy settings (settings.py) is the one the energy side reads: the mirrored dataclasses
keep the same fields and defaults as energy/simulate.py, energy/consumption.py and energy/economics.py, and
from_dict says the unknown keys and refuses the wrong types with their path."""

import dataclasses
import ast
import inspect
import pickle
import unittest

import _setup  # noqa: F401

from meridiana.core.model import settings
from meridiana.core.energy import consumption, economics, simulate


def fields_of(kls, skip=()) -> dict:
    return {f.name: (f.default if f.default is not dataclasses.MISSING else f.default_factory())
            for f in dataclasses.fields(kls) if f.name not in skip}


class Mirror(unittest.TestCase):
    def test_connection_cutoffs_keep_the_same_values_and_public_aliases(self):
        from meridiana.core.rules import rules as facade
        from meridiana.core.rules.profiles.it import checks, rules, thresholds
        expected = (11.08, 20.0, 100.0)
        self.assertEqual((thresholds.SPI_KW, thresholds.BACKUP_KW, thresholds.LV_KW), expected)
        self.assertEqual((checks.SPI_KW, checks.BACKUP_KW, checks.LV_KW), expected)
        self.assertEqual((rules.SPI_KW, rules.BACKUP_KW, rules.MV_KW), expected)
        self.assertEqual(facade.MV_KW, 100.0)

    def test_runtime_settings_do_not_redeclare_literal_defaults(self):
        for runtime, schema in ((simulate.Losses, settings.Losses),
                                (consumption.Consumption, settings.ConsumptionSettings),
                                (economics.Settings, settings.EconomicsSettings)):
            common = {f.name for f in dataclasses.fields(schema)}
            tree = ast.parse(inspect.getsource(runtime))
            duplicated = [node.target.id for node in tree.body[0].body if isinstance(node, ast.AnnAssign)
                          and node.target.id in common and isinstance(node.value, (ast.Constant, ast.Call))]
            self.assertEqual(duplicated, [], runtime.__qualname__)

    def test_runtime_types_field_order_and_serialization_stay_public(self):
        for runtime, schema, module in ((simulate.Losses, settings.Losses, 'simulate'),
                                        (consumption.Consumption, settings.ConsumptionSettings, 'consumption'),
                                        (economics.Settings, settings.EconomicsSettings, 'economics')):
            data = dataclasses.asdict(schema())
            value = runtime.from_dict(data)
            self.assertIs(type(value), runtime)
            self.assertIsNot(runtime, schema)
            self.assertEqual(runtime.__module__, f'meridiana.core.energy.{module}')
            self.assertEqual([f.name for f in dataclasses.fields(runtime) if f.name != 'defaults'], list(data))
            actual = dataclasses.asdict(pickle.loads(pickle.dumps(value)))
            actual.pop('defaults', None)
            self.assertEqual(actual, data)

    def test_mutable_defaults_are_separate_for_every_schema_and_runtime_instance(self):
        demand = consumption.Consumption()
        demand.bands_kwh['F1'] = 10.0
        demand.measured.append(['2026-01-01T00:00', 1.0])
        self.assertEqual(consumption.Consumption().bands_kwh, {})
        self.assertEqual(settings.ConsumptionSettings().measured, [])
        economic = economics.Settings()
        economic.battery['model'] = 'Sample'
        self.assertEqual(economics.Settings().battery, {})
        self.assertEqual(settings.EconomicsSettings().battery, {})

    def test_the_losses_the_consumption_and_the_economics_match_the_energy_side(self):
        self.assertEqual(fields_of(settings.Losses), fields_of(simulate.Losses))
        self.assertEqual(fields_of(settings.ConsumptionSettings), fields_of(consumption.Consumption))
        self.assertEqual(fields_of(settings.EconomicsSettings), fields_of(economics.Settings, skip=("defaults",)))

    def test_every_path_the_pages_write_is_known(self):
        energy = settings.known_paths("energy")
        for path in ("losses.use_horizon", "losses.use_near", "inverters", "dc_ac_ratio", "t_min",
                     "losses.transposition", "losses.lid", "strings", "strings.auto", "strings.runs",
                     "strings.strategy", "thermal"):
            self.assertIn(path, energy)
        self.assertNotIn("inverter", energy)                 # format 8: a list of inverters (task 16d)
        self.assertIn("battery", settings.known_paths("economics"))
        self.assertIn("measured", settings.known_paths("consumption"))


class FromDict(unittest.TestCase):
    def test_storage_fields_survive_typed_read_without_unknown_keys(self):
        for eta in (None, 90.0):
            with self.subTest(efficiency=eta):
                data = {"storage_coupling": "dc", "storage_inverter": {"model": "Hybrid"},
                        "storage_efficiency_pct": eta}
                unknown = []
                read = settings.from_dict(settings.EconomicsSettings, data, "economics", unknown)
                self.assertEqual(unknown, [])
                self.assertEqual(read.storage_inverter, data["storage_inverter"])
                self.assertEqual(read.storage_coupling, "dc")
                self.assertEqual(read.storage_efficiency_pct, eta)
        with self.assertRaisesRegex(ValueError, "storage_efficiency_pct"):
            settings.from_dict(settings.EconomicsSettings, {"storage_efficiency_pct": True}, "economics")

    def test_the_known_keys_are_read_and_the_unknown_said(self):
        unknown: list = []
        e = settings.from_dict(settings.EnergySettings, {"dc_ac_ratio": 1.2, "losses": {"soiling": 3.0, "soilng": 1},
                                                         "strings": {"n_series": 12, "per_mppt": [2, 2]}, "foo": 1},
                               "energy", unknown)
        # format 14: without «auto» the strings are the designer's (R114)
        self.assertEqual((e.dc_ac_ratio, e.losses.soiling, e.strings.n_series, e.strings.auto), (1.2, 3.0, 12, False))
        self.assertEqual(unknown, ["energy.losses.soilng", "energy.foo"])
        self.assertEqual(settings.from_dict(settings.EconomicsSettings, None), settings.EconomicsSettings())

    def test_a_wrong_type_is_refused_with_its_path(self):
        for kls, data, words in ((settings.EnergySettings, {"losses": {"use_near": 1}}, "energy.losses.use_near"),
                                 (settings.EnergySettings, {"t_min": "cold"}, "energy.t_min"),
                                 (settings.EnergySettings, {"losses": "none"}, "energy.losses"),
                                 (settings.EnergySettings, {"inverters": {}}, "energy.inverters"),
                                 (settings.EnergySettings, {"strings": {"auto": 1}}, "energy.strings.auto"),
                                 (settings.ConsumptionSettings, {"monthly_kwh": {}}, "energy.monthly_kwh"),
                                 (settings.EconomicsSettings, {"years": 25.0}, "energy.years")):
            with self.subTest(data=data), self.assertRaises(ValueError) as caught:
                settings.from_dict(kls, data, "energy")
            self.assertIn(words, str(caught.exception))
        with self.assertRaises(ValueError):
            settings.check("economics", "cheap", [])

    def test_the_inverters_and_the_strings_are_checked_entry_by_entry(self):
        good = {"inverters": [{"record": {"model": "X"}, "count": 2, "name": ""}],
                "strings": {"auto": False, "runs": [{"inverter": 1, "mppt": 2, "modules": ["s1/0:1"]}]}}
        settings.check("energy", good, [])
        for data, words in (({"inverters": [3]}, "energy.inverters[0]"),
                            ({"inverters": [{"record": [], "count": 1}]}, "energy.inverters[0].record"),
                            ({"inverters": [{"record": {}, "count": 0}]}, "energy.inverters[0].count"),
                            ({"strings": {"strategy": "spiral"}}, "energy.strings.strategy"),
                            ({"strings": {"runs": [{"inverter": "1"}]}}, "energy.strings.runs[0].inverter"),
                            ({"strings": {"runs": [{"modules": [1, 2]}]}}, "energy.strings.runs[0].modules")):
            with self.subTest(data=data), self.assertRaises(ValueError) as caught:
                settings.check("energy", data, [])
            self.assertIn(words, str(caught.exception))

    def test_a_measured_curve_may_be_a_list_or_a_table(self):
        for value in ([["2026-01-01T00:00", 1.0]], {"start": "2026-01-01T00:00", "values": [1.0]}):
            settings.from_dict(settings.ConsumptionSettings, {"measured": value})


if __name__ == "__main__":
    unittest.main()
