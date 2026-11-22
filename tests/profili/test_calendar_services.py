"""Tariff policy and geographic time are explicit, independent inputs."""
from unittest.mock import patch
import unittest

import numpy as np
import pandas as pd
import _setup  # noqa: F401
from meridiana.core.rules import registry
from meridiana.core.energy import bands, consumption, simulate


class CalendarServices(unittest.TestCase):
    def test_band_calendar_uses_the_explicit_timezone(self):
        index = pd.DatetimeIndex(['2023-01-09T00:00:00Z'])
        self.assertEqual(bands.band_of(index, profile_id='it').tolist(), ['F3'])
        self.assertEqual(bands.band_of(index, profile_id='it', timezone='Pacific/Auckland').tolist(), ['F1'])

    def test_local_year_conserves_every_utc_instant(self):
        original = simulate._local_index()
        other = simulate._local_index(timezone='Pacific/Auckland')
        np.testing.assert_array_equal(original.asi8, other.asi8)
        self.assertEqual(str(other.tz), 'Pacific/Auckland')

    def test_load_carries_explicit_context_without_changing_the_input(self):
        raw = {'annual_kwh': 1200.0, 'profile': 'flat'}
        c = consumption.Consumption.from_dict(raw, profile_id='it')
        load = consumption.build(c, profile_id='it', timezone='Pacific/Auckland')
        self.assertEqual((load.profile_id, load.timezone), ('it', 'Pacific/Auckland'))
        self.assertEqual(str(load.hourly.index.tz), 'Pacific/Auckland')
        self.assertAlmostEqual(load.annual_kwh, 1200.0, places=9)
        self.assertEqual(raw, {'annual_kwh': 1200.0, 'profile': 'flat'})

    def test_supply_identifier_validation_is_a_policy_service(self):
        policy = registry.get('it').consumption()
        with patch.object(type(policy), 'valid_supply_id', return_value=True):
            self.assertTrue(consumption.valid_pod('declared-id', profile_id='it'))

    def test_balance_uses_the_same_geographic_calendar(self):
        from meridiana.core.energy import economics
        index = pd.DatetimeIndex(['2023-01-09T00:00:00Z'])
        energy = pd.Series([1.0], index=index)
        result = economics.balance(energy, energy, profile_id='it', timezone='Pacific/Auckland')
        self.assertEqual(result['band'].tolist(), ['F1'])
