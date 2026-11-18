"""Catalogue constraints keep physical inputs distinct from independent MPPTs."""
import unittest

import _setup  # noqa: F401
from meridiana import catalog
from meridiana.energy.components import InverterSpec
from meridiana.energy.optimizers import Optimizer, module_groups


class InputTopology(unittest.TestCase):
    def test_single_string_does_not_receive_two_string_current_allowance(self):
        record = next(r for r in catalog.search('inverters', manufacturer='Huawei', limit=None)
                      if r['model'] == 'SUN2000-20K-MB0')
        spec = InverterSpec.from_record(record)
        self.assertEqual(spec.current_limit(0, 1), 20)
        self.assertEqual(spec.current_limit(0, 2), 30)
        self.assertEqual(spec.inputs_per_mppt, [2, 2])
        self.assertEqual(spec.current_limit(1, 1), 20)

    def test_missing_limits_are_not_invented_from_total(self):
        spec = InverterSpec.from_record({'mppt_count': 2, 'dc_current_max_a': 25})
        self.assertIsNone(spec.current_limit(0, 1))
        self.assertIsNone(spec.connector_current_limit(0))
        self.assertIsNone(spec.connector_isc_limit(0))
        self.assertEqual(spec.imax_total, 25)

    def test_explicit_scalar_per_mppt_rating_applies_to_each_tracker(self):
        spec = InverterSpec.from_record({'mppt_count': 2, 'dc_current_max_per_mppt_a': 30})
        self.assertEqual(spec.current_limit(1, 1), 30)
        short = InverterSpec.from_record({'mppt_count': 2, 'dc_current_max_per_mppt_a': [30]})
        self.assertIsNone(short.current_limit(1, 1))

    def test_conditional_and_physical_limits_are_separate(self):
        spec = InverterSpec.from_record({
            'mppt_count': 2, 'dc_current_max_per_mppt_a': [30, 24],
            'dc_current_max_per_mppt_by_strings_a': [{'1': 20, '2': 30}, {}],
            'dc_current_max_per_input_a': [20, 16], 'dc_isc_max_per_input_a': [25, 20]})
        self.assertEqual(spec.current_limit(0, 1), 20)
        self.assertEqual(spec.current_limit(1, 1), 24)
        self.assertEqual(spec.connector_current_limit(1), 16)
        self.assertEqual(spec.connector_isc_limit(0), 25)

    def test_malformed_optional_tables_do_not_create_limits(self):
        spec = InverterSpec.from_record({'mppt_count': 2,
                                         'dc_current_max_per_mppt_by_strings_a': {'1': 20}})
        self.assertIsNone(spec.current_limit(0, 1))
        opt = Optimizer.from_record({'max_output_voltage_v': float('nan')})
        self.assertIsNone(opt.v_out_max)

    def test_optimizer_voltage_window_is_preserved(self):
        record = next(r for r in catalog.search('optimizers', manufacturer='SolarEdge', limit=None)
                      if r['model'] == 'S500B')
        spec = Optimizer.from_record(record)
        self.assertEqual((spec.v_in_min, spec.v_in_max, spec.v_out_max), (12.5, 105, 80))

    def test_explicit_optimizer_groups_preserve_single_among_pairs(self):
        self.assertEqual(module_groups(list('abcde'), 2, [2, 1, 2]), [list('ab'), ['c'], list('de')])
        self.assertEqual(module_groups(list('abcde'), 2), [list('ab'), list('cd'), ['e']])
        for sizes in ([2, 2], [3, 2], [2, 0, 1, 2], [True, 2, 2]):
            with self.subTest(sizes=sizes), self.assertRaises(ValueError):
                module_groups(list('abcde'), 2, sizes)

    def test_explicit_single_groups_count_as_separate_optimizers(self):
        from meridiana.energy import optimizers
        from meridiana.energy.components import ModuleSpec
        opt = Optimizer.from_record(next(r for r in catalog.search('optimizers', manufacturer='SolarEdge', limit=None)
                                        if r['model'] == 'S1000'))
        inv = optimizers.fixed_voltage(next(r for r in catalog.search('inverters', manufacturer='SolarEdge', limit=None)
                                           if r['model'] == 'SE50K'))
        rules, _why = optimizers.rules_for(opt, inv)
        plan = optimizers.string_plan(ModuleSpec.from_record({}), opt, 2, inv, rules, 3, 1, 0, -10,
                                      group_sizes=[1, 1, 1])
        self.assertEqual(plan.optimizers, 3)
