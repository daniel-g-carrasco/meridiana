import json
from types import SimpleNamespace
import unittest

import _setup  # noqa: F401


class NavigationHelp(unittest.TestCase):
    def test_uses_custom_fit_binding_and_actual_profile(self):
        from meridiana.assistant.navigation_help import snapshot
        from meridiana.assistant import tools
        host = SimpleNamespace(navigation_settings=lambda: {
            "style": "blender", "style_name": "Blender", "orbit": "trackball",
            "pivot": "selection", "bindings": {"fit": ("Ctrl+9",), "save": ()}})
        data = snapshot(host)
        self.assertEqual(data["style"], "blender")
        self.assertIn("Ctrl+9", data["gestures"][4][1])
        self.assertNotIn("F,", data["gestures"][4][1])
        self.assertEqual(next(c for c in data["commands"] if c["id"] == "save")["keys"], [])
        outcome = tools.read_navigation(host, tools.State())
        self.assertEqual(json.loads(outcome.content)["pivot"], "selection")

    def test_offline_commands_are_explicit_and_general_queries_reach_model(self):
        from meridiana.tour import local_command
        self.assertEqual(local_command("Come mi muovo in 3D?"), "navigation")
        self.assertEqual(local_command("Mostra i comandi di navigazione"), "navigation")
        self.assertEqual(local_command("Come si calcola la producibilità?"), "")
