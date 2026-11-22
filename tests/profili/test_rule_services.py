"""Public facades dispatch by facts or project, without owning Italian policies."""
import unittest
from unittest.mock import patch

import _setup  # noqa: F401
from meridiana.core.rules import registry, rules, checks, types
from meridiana.core.model.model import Network


class RuleServices(unittest.TestCase):
    def test_legacy_types_are_shared(self):
        self.assertIs(rules.Facts, types.Facts)
        self.assertIs(rules.Rule, types.Rule)
        self.assertIs(checks.Item, types.Item)
        self.assertEqual(rules.Facts().profile_id, 'it')

    def test_fact_facades_dispatch_to_their_profile(self):
        profile = registry.get('it')
        f = rules.Facts()
        with patch.object(type(profile), 'minimum', return_value=(2.0, 3.0)):
            self.assertEqual(rules.minimum(f), (2.0, 3.0))
        with patch.object(type(profile), 'rule_items', return_value=['sentinel']):
            self.assertEqual(checks.rule_items(f), ['sentinel'])
        with patch.object(type(profile), 'technical_rule', return_value='declared'):
            self.assertEqual(Network(voltage_v=230).technical_rule(profile_id='it'), 'declared')

    def test_source_inventory_retains_all_rule_sources(self):
        profile = registry.get('it')
        refs = profile.standards()
        self.assertTrue({r.source() for r in profile.rules()} <= {r.source for r in refs})
        self.assertEqual(len({r.source for r in refs}), len(refs))
        self.assertTrue(all(r.status == 'as_implemented' for r in refs))

    def test_national_validation_keeps_structural_error_order(self):
        from meridiana.core.model import model
        p = model.Project(buildings=[model.Building(id='b1', name='Synthetic', footprint=[[0, 0], [4, 0], [4, 4]])])
        raw = p.to_json()
        raw['buildings'][0]['fire']['activity'] = 81
        raw['buildings'][0]['height'] = -1
        with self.assertRaisesRegex(ValueError, r'buildings\[0\]\.height'):
            model.Project.from_json(raw)
