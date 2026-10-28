"""Optional grid data: one model, its technical rule from voltage, and the existing rule fields kept in sync."""

import unittest

import _setup  # noqa: F401

from meridiana import model


class NetworkData(unittest.TestCase):
    def test_optional_values_round_trip_and_voltage_selects_the_rule(self):
        project = model.Project()
        self.assertEqual(project.network.technical_rule(), "")
        project.network = model.Network(distributor="E-distribuzione", pod="IT001E12345678", voltage_v=400,
                                        phases="3", level="BT", connection="existing", available_kw=30,
                                        requested_kw=25, practice_code="PR-2026-42")
        self.assertEqual(project.network.technical_rule(), "CEI 0-21")
        project.sync_network()
        self.assertEqual(project.rules["connection"], "BT")
        self.assertEqual(project.rules["contracted_kw"], 30)
        back = model.Project.from_json(project.to_json())
        self.assertEqual(back.network, project.network)
        self.assertEqual(back.rules, project.rules)

        project.network.voltage_v = 20000
        project.network.level = "MT"
        project.sync_network()
        self.assertEqual(project.network.technical_rule(), "CEI 0-16")
        self.assertEqual(project.rules["connection"], "MT")
        project.network.level = "AT"
        project.sync_network()
        self.assertEqual(project.rules["connection"], "AT")

    def test_a_zero_voltage_does_not_invent_a_rule_or_a_connection_level(self):
        project = model.Project(rules={"connection": "MT", "contracted_kw": 80})
        project.sync_network()
        self.assertEqual(project.rules, {"connection": "MT", "contracted_kw": 80})
        project.network.available_kw = 50
        project.sync_network()
        self.assertEqual(project.rules["contracted_kw"], 50)
        self.assertEqual(project.rules["connection"], "MT")

    def test_damaged_network_data_is_refused_with_its_path(self):
        project = model.Project()
        data = project.to_json()
        data["network"] = {"voltage_v": "400"}
        with self.assertRaisesRegex(ValueError, "network.voltage_v"):
            model.Project.from_json(data)
        data = project.to_json()
        data["network"] = {"level": "XX"}
        with self.assertRaisesRegex(ValueError, "network.level"):
            model.Project.from_json(data)
        data = project.to_json()
        data["network"] = {"connection": "borrowed"}
        with self.assertRaisesRegex(ValueError, "network.connection"):
            model.Project.from_json(data)


if __name__ == "__main__":
    unittest.main()
