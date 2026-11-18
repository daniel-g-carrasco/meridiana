"""Storage compatibility and AC equivalent regression cases."""
import unittest
from meridiana.energy.storage import check_storage, operating_battery


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.b = dict(manufacturer="Maker", model="B", usable_energy_kwh=10,
                      max_charge_power_w=5000, max_discharge_power_w=5000,
                      round_trip_efficiency_pct=90, coupling="dc", voltage_range_v=[200, 400])
        self.i = dict(type="hybrid", battery_voltage_range_v=[150, 450],
                      battery_charge_power_max_w=3000, battery_discharge_power_max_w=3000,
                      battery_current_max_a=100,
                      storage_compatibility=[dict(battery_manufacturer="Maker", battery_model="B",
                      source="https://manufacturer.test/list.pdf", page=2, units_min=1, units_max=2)])

    def test_exact_model_only(self):
        self.assertEqual(check_storage(self.b, self.i, "dc", 1).status, "compatible")
        self.b["model"] = "B plus"
        self.assertEqual(check_storage(self.b, self.i, "dc", 1).status, "unknown")

    def test_limits(self):
        self.assertEqual(check_storage(self.b, self.i, "dc", 3).status, "incompatible")
        self.b["voltage_range_v"] = [100, 500]
        self.assertEqual(check_storage(self.b, self.i, "dc", 1).status, "incompatible")

    def test_ac_requires_ac_system_not_matching_pv_brand(self):
        self.b["coupling"] = "ac"
        self.assertEqual(check_storage(self.b, {}, "ac", 1).status, "compatible")
        self.b["coupling"] = "dc"
        self.assertEqual(check_storage(self.b, {}, "ac", 1).status, "incompatible")

    def test_explicit_efficiency_and_shared_converter_limit(self):
        settings = dict(battery=self.b, battery_units=2, storage_coupling="dc",
                        storage_inverter=self.i, storage_efficiency_pct=85)
        b = operating_battery(settings)
        self.assertEqual((b.usable_kwh, b.charge_kw, b.discharge_kw, b.efficiency), (20, 3, 3, .85))
        settings["storage_efficiency_pct"] = None
        with self.assertRaises(ValueError):
            operating_battery(settings)

    def test_nan_rejected(self):
        self.assertEqual(check_storage(self.b, self.i, "dc", float("nan")).status, "incompatible")

    def test_deleted_inverter_invalidates_binding(self):
        from meridiana.energy.storage import validate_connection
        settings = dict(battery=self.b, storage_coupling="dc", storage_inverter=self.i)
        validate_connection(settings, [{"record": self.i}])
        with self.assertRaises(ValueError):
            validate_connection(settings, [])

    def test_round_trip_applied_once(self):
        import numpy as np
        from meridiana.energy.economics import dispatch
        settings = dict(battery=self.b, battery_units=1, storage_coupling="dc",
                        storage_inverter=self.i, storage_efficiency_pct=81)
        battery = operating_battery(settings)
        stored, given, soc = dispatch(np.array([2., 0.]), np.array([0., 3.]), battery)
        self.assertAlmostEqual(stored.sum(), 2)
        self.assertAlmostEqual(given.sum(), 1.62)
        self.assertAlmostEqual(soc[-1], 0)

    def test_audit_does_not_promote_url_to_verified(self):
        from meridiana.catalog.audit import audit_record
        result = audit_record(dict(model="bad", imp=10, isc=9, datasheet_url="https://example.test"), "modules")
        self.assertIn("imp > isc", result["issues"])
        self.assertEqual(result["fields"]["imp"], "source_declared")

    def test_model_pairing_without_limits_cannot_be_calculated(self):
        settings = dict(battery=self.b, battery_units=1, storage_coupling="dc",
                        storage_inverter=self.i, storage_efficiency_pct=90)
        for key in ("battery_current_max_a", "battery_voltage_range_v", "battery_charge_power_max_w",
                    "battery_discharge_power_max_w"):
            with self.subTest(key=key):
                incomplete = dict(self.i)
                incomplete.pop(key)
                settings["storage_inverter"] = incomplete
                with self.assertRaises(ValueError):
                    operating_battery(settings)

    def test_unknown_parallel_limit_does_not_authorize_100_units(self):
        self.i["storage_compatibility"][0].pop("units_max")
        settings = dict(battery=self.b, battery_units=100, storage_coupling="dc",
                        storage_inverter=self.i, storage_efficiency_pct=90)
        with self.assertRaises(ValueError):
            operating_battery(settings)
        settings["battery_units"] = 1
        with self.assertRaises(ValueError):
            operating_battery(settings)

    def test_ac_parallel_limit_is_required_for_multiple_complete_systems(self):
        self.b["coupling"] = "ac"
        settings = dict(battery=self.b, battery_units=2, storage_coupling="ac", storage_efficiency_pct=90)
        with self.assertRaises(ValueError):
            operating_battery(settings)
        self.b["max_parallel_units"] = 2
        self.assertEqual(operating_battery(settings).usable_kwh, 20)

    def test_dc_voltage_range_missing_is_not_replaced_by_nominal(self):
        self.b.pop("voltage_range_v")
        self.b["nominal_voltage_v"] = 300
        with self.assertRaises(ValueError):
            operating_battery(dict(battery=self.b, storage_coupling="dc", storage_inverter=self.i,
                                   storage_efficiency_pct=90))

    def test_invalid_quantity_evidence_never_opens_unlimited_capacity(self):
        for value in (float("nan"), 0, -1, 1.5, None):
            with self.subTest(value=value):
                self.i["storage_compatibility"][0]["units_max"] = value
                with self.assertRaises(ValueError):
                    operating_battery(dict(battery=self.b, storage_coupling="dc", storage_inverter=self.i,
                                           storage_efficiency_pct=90))

    def test_zero_rating_and_ambiguous_legacy_power_do_not_remove_limit(self):
        self.i["battery_charge_power_max_w"] = 0
        self.i["battery_power_max_w"] = 999999
        with self.assertRaises(ValueError):
            operating_battery(dict(battery=self.b, storage_coupling="dc", storage_inverter=self.i,
                                   storage_efficiency_pct=90))


if __name__ == "__main__":
    unittest.main()
