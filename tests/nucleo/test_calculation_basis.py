"""The results' plant context is a frozen snapshot of the calculation, not the edited project."""
import unittest
from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import _setup  # noqa: F401
import pandas as pd

from meridiana.energy.calculation_basis import basis_of
from meridiana.energy.economics import Battery, Settings, balance


class CalculationBasis(unittest.TestCase):
    def sim(self):
        return SimpleNamespace(arrays=[{"modules": 100, "connected_modules": 8},
                                       {"modules": 20, "connected_modules": 0}],
                               inverters=[{"number": 2, "name": "Maker INV-20", "p_ac_kw": 20}])

    def test_only_connected_modules_and_calculated_inverters_are_counted(self):
        basis = basis_of(self.sim())
        self.assertEqual((basis.inverter_count, basis.connected_modules, basis.laid_modules), (1, 8, 120))
        self.assertEqual(basis.inverters, ("Maker INV-20",))
        self.assertEqual((basis.battery_count, basis.battery_kwh, basis.supplied_kwh), (0, 0, 0))

    def test_snapshot_does_not_follow_mutated_project_or_result_containers(self):
        sim = self.sim()
        settings = Settings(battery={"manufacturer": "Maker", "model": "B10", "usable_energy_kwh": 10},
                            battery_units=2)
        battery = Battery.from_settings(settings)
        econ = SimpleNamespace(hourly=pd.DataFrame({"given": [0, 1.5, 2.0]}))
        basis = basis_of(sim, battery=battery, battery_units=settings.battery_units, econ=econ)
        settings.battery_units = 9
        settings.battery["model"] = "Changed"
        sim.arrays[0]["connected_modules"] = 99
        sim.inverters[0]["name"] = "Changed"
        econ.hourly.loc[:, "given"] = 200
        self.assertEqual((basis.battery_count, basis.battery_kwh, basis.battery_name, basis.supplied_kwh),
                         (2, 20, "Maker B10", 3.5))
        self.assertEqual((basis.connected_modules, basis.inverters), (8, ("Maker INV-20",)))
        with self.assertRaises(FrozenInstanceError):
            basis.battery_count = 1

    def test_configured_battery_with_no_dispatch_does_not_claim_supplied_energy(self):
        battery = Battery(10, 5, 5, .9, "B10")
        basis = basis_of(self.sim(), battery=battery, battery_units=1,
                         econ=SimpleNamespace(hourly=pd.DataFrame({"given": [0, 0]})))
        self.assertEqual((basis.battery_count, basis.battery_kwh, basis.supplied_kwh), (1, 10, 0))

    def test_explicit_ac_and_dc_equivalents_keep_physical_unit_count_and_real_dispatch(self):
        battery_record = dict(manufacturer="Maker", model="B", usable_energy_kwh=10,
                              max_charge_power_w=5000, max_discharge_power_w=5000,
                              coupling="dc", voltage_range_v=[200, 400], max_parallel_units=2)
        inverter = dict(type="hybrid", battery_voltage_range_v=[150, 450], battery_charge_power_max_w=3000,
                        battery_discharge_power_max_w=3000, battery_current_max_a=100,
                        storage_compatibility=[dict(battery_manufacturer="Maker", battery_model="B",
                        source="https://manufacturer.test/list.pdf", page=2, units_min=1, units_max=2)])
        index = pd.date_range("2026-01-01", periods=2, freq="h", tz="Europe/Rome")
        for coupling in ("ac", "dc"):
            settings = Settings(battery=dict(battery_record, coupling=coupling), battery_units=2,
                                storage_coupling=coupling, storage_inverter=inverter,
                                storage_efficiency_pct=81)
            battery = Battery.from_settings(settings)
            hourly = balance(pd.Series([2., 0.], index=index), pd.Series([0., 3.], index=index), battery)
            basis = basis_of(self.sim(), battery=battery, battery_units=2, econ=SimpleNamespace(hourly=hourly))
            self.assertEqual((basis.battery_count, basis.battery_kwh), (2, 20))
            self.assertAlmostEqual(basis.supplied_kwh, 1.62)

    def test_zero_connected_result_does_not_count_sized_placeholder_inverter(self):
        sim = SimpleNamespace(arrays=[{"modules": 100, "connected_modules": 0}], inverters=[])
        self.assertEqual((basis_of(sim).inverter_count, basis_of(sim).connected_modules), (0, 0))
