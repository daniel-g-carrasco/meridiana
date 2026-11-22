"""Financial accounting consumes profile cash flows and retains explicit-input markers."""
from unittest.mock import patch
import unittest

import numpy as np
import pandas as pd
import _setup  # noqa: F401
from meridiana.core.rules import registry
from meridiana.core.rules.types import PolicyFlows
from meridiana.core.energy import economics, simulate
from meridiana.core.model import settings


class EconomyServices(unittest.TestCase):
    def test_defaults_are_copied_and_explicit_zero_is_not_a_default(self):
        profile = registry.get('it')
        defaults = profile.defaults('economics')
        self.assertEqual(defaults['buy_f1'], 0.25)
        defaults['battery']['changed'] = True
        self.assertEqual(profile.defaults('economics')['battery'], {})
        service = economics.Settings.from_dict({'buy_f1': 0.0}, profile_id='it')
        self.assertNotIn('buy_f1', service.defaults)
        self.assertIn('buy_f2', service.defaults)
        typed = settings.from_dict(settings.EconomicsSettings, {}, profile_id='it')
        for key, value in profile.defaults('economics').items():
            with self.subTest(key=key):
                self.assertEqual(getattr(typed, key), value)

    def test_shared_finance_uses_the_policy_flows(self):
        policy = registry.get('it').economics()
        s = economics.Settings.from_dict({'years': 2, 'capex_total': 0.0, 'capex_per_kwp': 0.0,
                                         'opex_per_kwp': 0.0, 'inverter_year': 999}, profile_id='it')
        index = simulate._local_index()
        production = pd.Series(np.ones(len(index)), index=index)
        load = pd.Series(np.full(len(index), 0.5), index=index)
        flows = PolicyFlows(np.array([123.0, 456.0]), np.zeros(2), np.zeros(2), np.zeros(2), '', 0.0)
        with patch.object(type(policy), 'flows', return_value=flows):
            result = economics.evaluate(production, load, 1.0, 1.0, s, profile_id='it')
        np.testing.assert_array_equal(result.years['saving'].to_numpy(), flows.saving)
        np.testing.assert_array_equal(result.years['flow'].to_numpy(), flows.saving)

    def test_optional_efficiency_preserves_null_and_rejects_text(self):
        from meridiana.core.model.settings import EconomicsSettings, from_dict
        self.assertIsNone(from_dict(EconomicsSettings, {"storage_efficiency_pct": None}).storage_efficiency_pct)
        with self.assertRaises(ValueError):
            from_dict(EconomicsSettings, {"storage_efficiency_pct": "unknown"})

    def test_address_zone_and_tariff_are_dispatched(self):
        policy = registry.get('it').economics()
        with patch.object(type(policy), 'zone_from_address', return_value='scope'):
            self.assertEqual(economics.zone_from_address('address', profile_id='it'), 'scope')
        with patch.object(type(policy), 'tip', return_value=12.0):
            self.assertEqual(economics.tip(110, 100, '', profile_id='it'), 12.0)
