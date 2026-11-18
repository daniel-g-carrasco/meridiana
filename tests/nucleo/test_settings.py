"""The schema of the energy settings (settings.py) is the one the energy side reads: the mirrored dataclasses
keep the same fields and defaults as energy/simulate.py, energy/consumption.py and energy/economics.py, and
from_dict says the unknown keys and refuses the wrong types with their path."""

import dataclasses
import unittest

import _setup  # noqa: F401

from meridiana import settings
from meridiana.energy import consumption, economics, simulate


def fields_of(kls, skip=()) -> dict:
    return {f.name: (f.default if f.default is not dataclasses.MISSING else f.default_factory())
            for f in dataclasses.fields(kls) if f.name not in skip}


class Mirror(unittest.TestCase):
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
