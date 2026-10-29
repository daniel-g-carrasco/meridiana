"""Meridio only shows registered destinations, without changing settings or the project."""

import json
import unittest

import _setup  # noqa: F401
from _fakes import Host
from _fixtures import capannone_rho

from meridiana.assistant import tools


class Navigation(unittest.TestCase):
    def setUp(self):
        self.host = Host(capannone_rho(), lay=False)
        self.host.navigation_targets = lambda: [
            {"kind": "setting", "id": "navigation.mouse_style", "label": "Mouse style"},
            {"kind": "settings", "id": "navigation", "label": "Navigation"},
            {"kind": "property", "id": "site.pod", "label": "POD"},
        ]

    def test_the_model_can_enumerate_real_controls_before_showing_them(self):
        outcome = tools.run("list_navigation_targets", {}, self.host, tools.State())
        self.assertFalse(outcome.error)
        rows = json.loads(outcome.content)["targets"]
        self.assertIn({"kind": "setting", "id": "navigation.mouse_style", "label": "Mouse style"}, rows)
        self.assertEqual(self.host.went, [])

    def test_showing_a_registered_setting_or_property_changes_no_project_values(self):
        before = self.host.project.to_json()
        for kind, ident in (("setting", "navigation.mouse_style"), ("settings", "navigation"),
                            ("property", "site.pod")):
            with self.subTest(kind=kind):
                outcome = tools.run("go_to", {"kind": kind, "id": ident}, self.host, tools.State())
                self.assertFalse(outcome.error, outcome.content)
                self.assertEqual(self.host.went[-1], (kind, ident))
        self.assertEqual(self.host.project.to_json(), before)

    def test_an_invented_control_returns_the_real_targets_without_navigating(self):
        outcome = tools.run("go_to", {"kind": "setting", "id": "navigation.banana"}, self.host, tools.State())
        self.assertTrue(outcome.error)
        self.assertIn("navigation.mouse_style", outcome.content)
        self.assertEqual(self.host.went, [])

    def test_a_control_unavailable_in_the_window_is_reported_honestly(self):
        def unavailable(_target):
            raise ValueError("the control is unavailable in this window")
        self.host.go_to = unavailable
        outcome = tools.run("go_to", {"kind": "property", "id": "site.pod"}, self.host, tools.State())
        self.assertTrue(outcome.error)
        self.assertIn("unavailable", outcome.content)


if __name__ == "__main__":
    unittest.main()
