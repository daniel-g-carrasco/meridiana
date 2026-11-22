"""Static GUI profile composition at existing schema boundaries."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from meridiana.core.model.model import Project

class GuiProfiles(unittest.TestCase):
    def test_registry_is_strict_and_matches_core(self):
        from meridiana.core.rules import registry as core
        from meridiana.gui.backend.profiles import registry as gui
        self.assertEqual(gui.ids(), core.ids())
        self.assertEqual(gui.get('it').bill_columns(Project()), ('F1', 'F2', 'F3'))
        with self.assertRaises(ValueError):
            gui.get('unknown')

    def test_chart_builder_uses_project_profile_fragment(self):
        from meridiana.gui.backend import charts_schema
        from meridiana.gui.backend.profiles import registry
        editor = SimpleNamespace(session=SimpleNamespace(project=Project()))
        policy = registry.get('it')
        with patch.object(type(policy), 'append_chart_fields') as append:
            charts_schema.economics(editor)
        self.assertEqual(append.call_args.args[0], 'economics')
        self.assertIs(append.call_args.args[1].editor, editor)

    def test_property_fragments_run_at_the_original_section(self):
        from meridiana.gui.backend.properties_schema import Schema, site_schema
        from meridiana.gui.backend.profiles import registry
        policy = registry.get('it')
        schema = Schema()
        with patch.object(type(policy), 'append_fields') as append:
            site_schema(schema, Project())
        self.assertEqual(append.call_args.args[0], 'site')
        self.assertEqual(schema.sections[-1]['key'], 'site_actions')

    def test_core_fields_are_presentation_free_and_return_copies(self):
        from meridiana.core.rules import registry
        policy = registry.get("it")
        for section in ("site", "network", "building", "layout", "consumption", "economics"):
            self.assertTrue(policy.fields(section))
        obligation = next(f for f in policy.fields("site") if f.path == "rules.obligation")
        self.assertEqual(obligation.choices, ("", "none", "new", "renovation"))
        battery = next(f for f in policy.fields("economics") if f.path == "battery")
        battery.default["test"] = True
        self.assertEqual(next(f.default for f in policy.fields("economics") if f.path == "battery"), {})
        with self.assertRaises(KeyError):
            policy.fields("unknown")

    def test_the_help_of_a_mark_reads_the_project_profile(self):
        # R597: one backend for every «?» (help_part.HelpBook): its tooltip and its bubble by the project's profile
        from meridiana.gui.backend.help_part import HelpBook
        from meridiana.app.interface import help as helps
        owner = SimpleNamespace(session=SimpleNamespace(project=Project()))
        with patch.object(helps, "get", return_value=SimpleNamespace(short="hint")) as get:
            self.assertEqual(HelpBook.tip(owner, "site"), "hint")
        get.assert_called_once_with("site", profile_id="it")
