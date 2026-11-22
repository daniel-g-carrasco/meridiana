"""App profile composition preserves source identity across reports and assistance."""
import unittest
from types import SimpleNamespace
from meridiana.core.model.model import Project
from meridiana.core.rules.types import Facts

class AppProfiles(unittest.TestCase):
    def test_registries_match_and_unknown_profiles_fail(self):
        from meridiana.app.profiles import registry
        from meridiana.core.rules import registry as core
        self.assertEqual(registry.ids(), core.ids())
        with self.assertRaises(ValueError): registry.get('unknown')

    def test_report_rejects_facts_of_another_profile(self):
        from meridiana.app.report.compose import with_notes
        with self.assertRaisesRegex(ValueError, 'profile'):
            with_notes({'rules_facts': Facts(profile_id='other')}, Project())

    def test_unknown_fragment_is_an_error_and_italy_adds_no_scope(self):
        from meridiana.app.profiles import registry
        profile = registry.get('it')
        self.assertEqual(profile.report_fragment('scope', None), [])
        with self.assertRaises(KeyError): profile.report_fragment('unknown', None)

    def test_read_rules_uses_the_selected_repertoire_even_for_an_explicit_id(self):
        from unittest.mock import patch
        from meridiana.app.assistant import tools
        from meridiana.core.rules import registry
        host = SimpleNamespace(project=Project(), rules_facts=lambda: Facts())
        with patch.object(type(registry.get('it')), 'rules', return_value=()):
            outcome = tools.read_rules(host, tools.State(), 'N01')
        self.assertTrue(outcome.error)
        self.assertNotIn('CEI', outcome.content)

    def test_source_inventory_covers_frozen_source_fields(self):
        import re
        from pathlib import Path
        from profili.reference_storage import unpack
        from profili.snapshot import BANKS
        from meridiana.core.rules import registry
        sources = {ref.source for ref in registry.get("it").standards()}
        def visit(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in {"source", "reference"} and isinstance(item, str) and re.search(r"CEI|DCPREV|VVF|DPR|DM |MASE|ARERA|GSE|NTC|DGR|D.Lgs", item):
                        self.assertIn(item, sources)
                    visit(item)
            elif isinstance(value, list):
                for item in value: visit(item)
        files = list((Path(__file__).parent / "riferimenti/it").glob("*.json.gz"))
        self.assertEqual(len(files), 2 * len(BANKS))
        for file in files:
            visit(unpack(file.read_bytes()))

    def test_national_search_keywords_belong_to_the_profile(self):
        from meridiana.app.assistant import design_rules
        from meridiana.app.profiles import registry
        self.assertNotIn("fire", design_rules.KEYWORDS)
        self.assertIn("vvf", registry.get("it").design_keywords()["fire"])
        self.assertTrue(any(p["id"].startswith("fire.") for p in design_rules.search("vigili fuoco")['rules']))
