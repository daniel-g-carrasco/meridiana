"""Reserved projects: names and addresses never go out, coordinates only after a per-project consent."""

import unittest

import _setup  # noqa: F401

from meridiana import model


class NetworkConsent(unittest.TestCase):
    def test_reserved_projects_start_offline_and_consent_is_specific(self):
        project = model.Project(reserved=True)
        self.assertFalse(project.online_allowed("geocoding", True))
        self.assertFalse(project.online_allowed("tiles", True))
        self.assertFalse(project.online_allowed("pvgis", True))
        project.network_consent = {"tiles": "2026-10-27"}
        self.assertTrue(project.online_allowed("tiles", True))
        self.assertFalse(project.online_allowed("pvgis", True))
        self.assertFalse(project.online_allowed("tiles", False))
        project.network_consent["pvgis"] = "2026-10-27"
        self.assertTrue(project.online_allowed("pvgis", True))
        self.assertFalse(project.online_allowed("geocoding", True))

    def test_consent_round_trips_and_damaged_values_are_refused(self):
        project = model.Project(reserved=True, network_consent={"tiles": "2026-10-27", "pvgis": "2026-10-27"})
        back = model.Project.from_json(project.to_json())
        self.assertEqual(back.network_consent, project.network_consent)
        for value in ({"weather": "2026-10-27"}, {"tiles": 1}, {"tiles": "not a date"}):
            data = project.to_json()
            data["network_consent"] = value
            with self.assertRaisesRegex(ValueError, "network_consent"):
                model.Project.from_json(data)

    def test_not_reserved_uses_the_global_switches_without_project_consent(self):
        project = model.Project()
        for service in ("geocoding", "tiles", "pvgis"):
            self.assertTrue(project.online_allowed(service, True))
            self.assertFalse(project.online_allowed(service, False))


if __name__ == "__main__":
    unittest.main()
