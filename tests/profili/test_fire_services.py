"""Geometry consumes effective fire values and never chooses a national policy."""
import copy
import unittest
from unittest.mock import patch

import _setup  # noqa: F401
from profili.fixtures import projects
from meridiana.core.rules import registry
from meridiana.core.rules.types import FirePolicy
from meridiana.core.layout import layout


class FireServices(unittest.TestCase):
    def test_explicit_values_and_host_subjection_are_preserved(self):
        p = next(p for name, p in projects() if name == 'fire_shed')
        sf = p.subfields[0]
        sf.params.update(fire_edge=0.75, fire_group=18.0, fire_corridor=2.5)
        original = copy.deepcopy(sf.params)
        policy = registry.for_project(p).fire(p, sf)
        self.assertTrue(policy.enabled)
        self.assertEqual((policy.edge, policy.group, policy.corridor), (0.75, 18.0, 2.5))
        effective = p.fill_params(sf)
        self.assertEqual((effective.fire_edge, effective.fire_group, effective.fire_corridor), (0.75, 18.0, 2.5))
        self.assertEqual(sf.params, original)

    def test_disabled_policy_controls_parameters_guides_and_automatic_bands(self):
        p = next(p for name, p in projects() if name == 'fire_shed')
        sf = p.subfields[0]
        sf.params['fire_rules'] = True
        original = copy.deepcopy(sf.params)
        neutral = FirePolicy(False, 0.0, 0.0, 0.0, 0.0, '', '')
        with patch.object(type(registry.for_project(p)), 'fire', return_value=neutral, create=True):
            effective = p.fill_params(sf)
            self.assertFalse(effective.fire_rules)
            self.assertEqual((effective.fire_edge, effective.fire_group, effective.fire_corridor), (0, 0, 0))
            self.assertEqual(p.fire_guides(), [])
            self.assertEqual(p.fire_bands(), [])
        self.assertEqual(sf.params, original)

    def test_geometry_does_not_ask_a_profile_for_fire_policy(self):
        p = next(p for name, p in projects() if name == 'shed')
        sf = p.subfields[0]
        effective = p.fill_params(sf)
        with patch.object(type(registry.for_project(p)), 'fire', side_effect=AssertionError('geometry chose policy'),
                          create=True):
            result = layout.compute(sf.ring, p.surface_of(sf), p.module_of(sf), effective)
        self.assertGreater(result.count, 0)

    def test_policy_warning_is_supplied_to_geometry(self):
        p = next(p for name, p in projects() if name == 'shed')
        sf = p.subfields[0]
        sf.params.update(mounting='tilted_ballasted', shade_free=False)
        neutral = FirePolicy(False, 0, 0, 0, 0, '', '')
        with patch.object(type(registry.for_project(p)), 'fire', return_value=neutral, create=True):
            result = p.fill(sf)
        self.assertEqual(result.notes, [])

    def test_structural_validation_does_not_construct_national_defaults(self):
        from meridiana.core.model import model
        with patch.object(type(registry.get('it')), 'defaults', side_effect=AssertionError('national defaults')):
            model._check_fields(layout.Params, {'fire_edge': 0.25, 'fire_group': 12.0}, 'params', [])
