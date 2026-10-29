"""Global attribution solves full electrical assignments and distinguishes proof from an interrupted search."""
import itertools
import time
import unittest

import _setup  # noqa: F401
from meridiana import layout, model
from meridiana.energy import plant, sizing, stringing
from meridiana.energy.components import ModuleSpec


def module(name='M', imp=5):
    return ModuleSpec('Fixture', name, 50, 10, imp, 12, imp, 0, 0, 0, 20, 1, 1,
                      max_series_fuse=25, _sdm={'linear': True})


def inverter(name='I', trackers=2, **changes):
    rec = dict(manufacturer='Fixture', model=name, ac_power_nominal_w=1000, mppt_count=trackers,
               dc_voltage_max_v=120, mppt_voltage_min_v=60, mppt_voltage_max_v=120,
               dc_current_max_per_mppt_a=[10]*trackers, dc_isc_max_per_mppt_a=[20]*trackers,
               strings_per_mppt=[1]*trackers, source='curated')
    rec.update(changes)
    return rec


def group(n, sf='s1', azimuth=0, mod=None):
    placed = [layout.PlacedModule(i//10, i%10, 0, [], (i%10, i//10), 1, 15, azimuth) for i in range(n)]
    return plant.Group(sf+'.0', sf, sf, mod or module(), placed)


def project(entries):
    p = model.Project()
    p.energy = dict(inverters=[dict(record=rec, count=count) for rec, count in entries], strings={'auto': True})
    return p


class Global(unittest.TestCase):
    def test_two_lengths_on_distinct_mppts_connect_a_prime_module_count(self):
        out = plant.build(project([(inverter(), 1)]), groups=[group(19)])
        self.assertFalse(out.left)
        self.assertEqual(sorted(len(s.modules) for s in out.strings), [9, 10])
        self.assertTrue(out.search_complete)

    def test_constrained_module_reserves_the_only_input_that_can_take_its_current(self):
        entries = [(inverter('high', 1), 1), (inverter('low', 1, dc_current_max_per_mppt_a=[6]), 1)]
        out = plant.build(project(entries), groups=[group(10, mod=module('flexible', 5)),
                                                    group(10, 's2', mod=module('demanding', 9))])
        self.assertFalse(out.left)
        self.assertEqual({s.modules[0][0]: s.inverter for s in out.strings}, {'s1': 2, 's2': 1})

    def test_equal_planes_can_join_small_subfields_to_form_one_string(self):
        out = plant.build(project([(inverter(trackers=1), 1)]), groups=[group(3), group(3, 's2')])
        self.assertFalse(out.left)
        self.assertEqual(len(out.strings), 1)
        self.assertEqual(len(out.strings[0].modules), 6)

    def test_shared_current_redistributes_strings_over_two_units(self):
        rec = inverter(dc_current_max_a=8)
        result = sizing.choose(project([]), [group(10), group(10, 's2', 90)], [rec], 1)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.entries[0]['count'], 2)
        self.assertEqual({s.inverter for s in result.plant.strings}, {1, 2})

    def test_assignment_budget_is_explicit_and_never_claims_electrical_impossibility(self):
        budget = stringing.SearchBudget(limit=1)
        out = plant.build(project([(inverter(), 1)]), groups=[group(19)], search=budget)
        self.assertFalse(out.search_complete)
        self.assertIn('limit', out.search_reason)
        self.assertLessEqual(budget.nodes, 1)

    def test_cancellation_reaches_inside_assignment(self):
        checks = []
        def cancelled():
            checks.append(1)
            return len(checks) > 3
        budget = stringing.SearchBudget(limit=10000, cancelled=cancelled)
        out = plant.build(project([(inverter(), 1)]), groups=[group(19)], search=budget)
        self.assertFalse(out.search_complete)
        self.assertIn('cancelled', out.search_reason)

    def test_small_space_matches_independent_exhaustive_slot_oracle(self):
        rec = inverter(dc_voltage_max_v=48, mppt_voltage_min_v=20, mppt_voltage_max_v=48)
        possible = {sum(values) for values in itertools.product((0, 2, 3, 4), repeat=2)}
        for count in range(2, 11):
            with self.subTest(count=count):
                out = plant.build(project([(rec, 1)]), groups=[group(count)])
                self.assertEqual(not out.left, count in possible)
                self.assertTrue(out.search_complete)

    def test_optimizer_family_is_searched_and_the_chosen_hardware_is_persistable(self):
        from meridiana import catalog
        rec = next(r for r in catalog.search('inverters', manufacturer='SolarEdge', limit=None)
                   if r['model'] == 'SE3000H')
        out = plant.proposal(project([(rec, 1)]), groups=[group(6)])
        self.assertFalse(out.left)
        self.assertTrue(out.entries)
        self.assertNotIn(out.units[0].choice.optimizer.model, ('S440', 'S500'))
        saved = project([])
        saved.energy = dict(inverters=out.entries, strings={'runs': plant.runs_of(out)})
        back = plant.build(saved, groups=[group(6)])
        self.assertTrue(all(s.state == 'ok' for s in back.strings))

    def test_two_orientations_match_an_independent_exhaustive_three_tracker_oracle(self):
        rec = inverter(trackers=3, dc_voltage_max_v=48, mppt_voltage_min_v=20, mppt_voltage_max_v=48)
        options = [(0, 0)] + [(kind, n) for kind in (1, 2) for n in (2, 3, 4)]
        possible = {(sum(n for kind, n in values if kind == 1), sum(n for kind, n in values if kind == 2))
                    for values in itertools.product(options, repeat=3)}
        for a, b in itertools.product(range(1, 9), repeat=2):
            with self.subTest(a=a, b=b):
                out = plant.build(project([(rec, 1)]), groups=[group(a), group(b, 's2', 90)])
                self.assertEqual(not out.left, (a, b) in possible)
                self.assertTrue(out.search_complete)

    def test_conditional_current_is_checked_with_the_final_string_count(self):
        rec = inverter(trackers=1, strings_per_mppt=[2], dc_current_max_per_mppt_a=[12],
                       dc_current_max_per_mppt_by_strings_a=[{'1': 4, '2': 12}])
        p = project([(rec, 1)])
        p.energy['strings']['n_series'] = 6
        out = plant.build(p, groups=[group(12)])
        self.assertFalse(out.left)
        self.assertTrue(all(s.state == 'ok' for s in out.strings))
        self.assertEqual(len(out.strings), 2)

    def test_a_physical_connector_rating_cannot_be_replaced_by_the_tracker_rating(self):
        rec = inverter(dc_current_max_per_input_a=[4, 4])
        out = plant.build(project([(rec, 1)]), groups=[group(10)])
        self.assertTrue(out.left)
        self.assertTrue(out.search_complete)

    def test_sizing_does_not_accept_a_feasible_candidate_from_an_incomplete_assignment_search(self):
        result = sizing.choose(project([]), [group(19)], [inverter()], 1,
                               search=stringing.SearchBudget(limit=2))
        self.assertFalse(result.ok)
        self.assertFalse(result.search_complete)
        self.assertEqual(result.entries, [])

    def test_ratio_distance_is_measured_on_dc_ac_not_on_absolute_ac_watts(self):
        self.assertLess(next(sizing._combinations([{'_sizing_pac': 110, '_sizing_record': {}}], 1, 1, 100))[0],
                        next(sizing._combinations([{'_sizing_pac': 90, '_sizing_record': {}}], 1, 1, 100))[0])

    def test_large_prime_pool_and_mid_search_cancellation_use_bounded_states(self):
        p = project([(inverter(), 96)])
        budget = stringing.SearchBudget(limit=10000)
        started = time.perf_counter()
        out = plant.build(p, groups=[group(1901)], search=budget)
        self.assertFalse(out.left)
        self.assertTrue(out.search_complete)
        self.assertLess(budget.nodes, 10000)
        self.large_seconds = time.perf_counter() - started
        calls = []
        def cancelled():
            calls.append(1)
            return len(calls) > 20
        budget = stringing.SearchBudget(cancelled=cancelled)
        out = plant.build(p, groups=[group(1901)], search=budget)
        self.assertFalse(out.search_complete)
        self.assertLessEqual(budget.nodes, 20)

    def test_global_lengths_preserve_row_and_u_routing_geometry(self):
        p = project([(inverter(), 1)])
        p.energy['strings']['strategy'] = 'rows'
        out = plant.build(p, groups=[group(19)])
        self.assertFalse(out.left)
        for s in out.strings:
            self.assertEqual(len({key.split(':')[0] for _sf, key, _c in s.modules}), 1)
        g = group(22)
        for i, pm in enumerate(g.placed):
            pm.row, pm.slot = divmod(i, 11)
            pm.key = f'{pm.row}:{pm.slot}'
            pm.centre = (pm.slot, pm.row)
        p = project([(inverter(strings_per_mppt=[2, 2]), 1)])
        p.energy['strings']['strategy'] = 'u'
        out = plant.build(p, groups=[g])
        self.assertFalse(out.left)
        for s in out.strings:
            self.assertEqual(len(s.modules) % 2, 0)
            self.assertEqual(s.modules[0][2][0], s.modules[-1][2][0])

    def test_overload_uses_supplied_unit_power_without_redistributing_the_aggregate(self):
        gs = [group(10), group(10, 's2', 90)]
        p = project([(inverter(), 2)])
        p.energy['strings'] = {'runs': [dict(inverter=i+1, mppt=1,
            modules=[f'{g.sfid}/{pm.key}' for pm in g.placed]) for i,g in enumerate(gs)]}
        out = plant.build(p, groups=gs, p_dc_hourly=[5050, 5050],
                          p_dc_by_inverter={1: [5000, 5000], 2: [50, 50]})
        self.assertGreater(out.clipping[1], 50)
        self.assertEqual(out.clipping[2], 0)

    def test_optional_conditional_rows_are_tolerated_and_plain_proposals_keep_hardware(self):
        rec = inverter(dc_current_max_per_mppt_by_strings_a=[None, {'1': 10}])
        p = project([(rec, 1)])
        out = plant.proposal(p, groups=[group(19)])
        self.assertFalse(out.left)
        self.assertIsNone(out.entries)
        self.assertTrue(all(s.state == 'ok' for s in out.strings))

    def test_automatic_and_explicit_compatible_targets_can_share_one_homogeneous_string(self):
        a, b = group(3), group(3, 's2')
        b.target = (1, 1)
        out = plant.build(project([(inverter(), 1)]), groups=[a, b])
        self.assertFalse(out.left)
        self.assertEqual([(s.inverter, s.mppt, len(s.modules)) for s in out.strings], [(1, 1, 6)])

    def test_every_explicit_target_is_respected_and_an_unavailable_one_does_not_move_silently(self):
        for target in ((0, 2), (1, 2), (2, 1), (9, 1)):
            with self.subTest(target=target):
                g = group(10)
                g.target = target
                out = plant.proposal(project([(inverter(), 2)]), groups=[g])
                if target[0] == 9:
                    self.assertTrue(out.left)
                else:
                    self.assertFalse(out.left)
                    for s in out.strings:
                        self.assertTrue(not target[0] or s.inverter == target[0])
                        self.assertEqual(s.mppt, target[1])

    def test_completing_keeps_manual_preallocation_and_joins_only_compatible_new_targets(self):
        existing, a, b = group(6, 'old'), group(3, 'auto'), group(3, 'target')
        a.target = (1, 0)
        b.target = (1, 2)
        keep = [dict(inverter=1, mppt=1, modules=[f'old/{pm.key}' for pm in existing.placed])]
        out = plant.proposal(project([(inverter(), 1)]), groups=[existing, a, b], keep=keep)
        self.assertFalse(out.left)
        self.assertEqual(plant.runs_of(out)[0], keep[0])
        self.assertEqual([(s.inverter, s.mppt, len(s.modules)) for s in out.strings], [(1, 1, 6), (1, 2, 6)])


if __name__ == '__main__':
    unittest.main()
