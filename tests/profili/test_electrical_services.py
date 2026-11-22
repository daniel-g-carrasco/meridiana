"""Electrical decisions and market qualifications are supplied by the profile."""
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import _setup  # noqa: F401
from meridiana.core.rules import registry
from meridiana.core.energy import stringing, optimizers
from profili.fixtures import module as module_spec, inverter as inverter_spec


class ElectricalServices(unittest.TestCase):
    def test_legacy_fallbacks_have_one_provider(self):
        policy = registry.get('it').electrical()
        self.assertEqual((policy.voc_fallback, policy.voltage_fallback, policy.ki_default), (1.2, 1000.0, 1.25))
        self.assertTrue(policy.allow_auto)

    def test_fallback_and_selv_are_dispatched(self):
        profile = registry.get('it')
        policy = profile.electrical()
        with patch.object(type(profile), 'electrical', return_value=replace(policy, voc_fallback=1.7)):
            self.assertEqual(stringing.ku(module_spec(), None, profile_id='it'), 1.7)
        marker = stringing.Check('policy_marker', 'Scope', False, '', 'info')
        with patch.object(type(policy), 'selv', return_value=[marker]):
            plan = stringing.plan(module_spec(), inverter_spec(), 10, [1, 0], -10, 65, profile_id='it')
        self.assertEqual([c.key for c in plan.checks[:2]], ['uoc', 'policy_marker'])

    def test_market_qualification_is_not_in_the_common_table(self):
        profile = registry.get('it')
        opt = SimpleNamespace(manufacturer='SolarEdge', model='S1200', name='Synthetic optimizer')
        inv = SimpleNamespace(unit_model='SE33.3K', model='Synthetic inverter')
        with patch.object(type(profile), 'market_rules', return_value=(None, 'scope'), create=True):
            self.assertEqual(optimizers.rules_for(opt, inv, profile_id='it'), (None, 'scope'))

    def test_catalog_context_copies_records_and_keeps_scope_separate(self):
        from meridiana.app.profiles.it.catalog import context
        records = {'x': {'market_scope': 'it', 'values': [1]}, 'y': {'source': 'Italian datasheet'}}
        prepared = context(records)
        self.assertEqual(prepared['records'], records)
        self.assertEqual(prepared['market_scope'], {'x': 'it', 'y': None})
        prepared['records']['x']['values'].append(2)
        self.assertEqual(records['x']['values'], [1])
