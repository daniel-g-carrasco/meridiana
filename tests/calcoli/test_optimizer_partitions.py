"""Editing a run preserves physical optimizer memberships, including single occupied inputs."""
import unittest
import _setup  # noqa: F401
from meridiana.energy import plant


class PhysicalGroups(unittest.TestCase):
    def setUp(self):
        self.runs = [dict(inverter=1, mppt=1, modules=list('abcde'), optimizer_group_sizes=[2, 1, 2])]

    def test_remove_shrinks_only_its_own_optimizer(self):
        runs, _ = plant.remove_module(self.runs, 'b')
        self.assertEqual(runs[0]['modules'], list('acde'))
        self.assertEqual(runs[0]['optimizer_group_sizes'], [1, 1, 2])

    def test_cut_and_reverse_preserve_memberships(self):
        runs, _ = plant.cut_run(self.runs, 'b', 'from')
        self.assertEqual(runs[0]['optimizer_group_sizes'], [1, 1, 2])
        runs = plant.reversed_run(self.runs, 0)
        self.assertEqual(runs[0]['modules'], list('edcba'))
        self.assertEqual(runs[0]['optimizer_group_sizes'], [2, 1, 2])
        unequal = [dict(self.runs[0], optimizer_group_sizes=[2, 2, 1])]
        self.assertEqual(plant.reversed_run(unequal, 0)[0]['optimizer_group_sizes'], [1, 2, 2])

    def test_add_starts_a_new_single_optimizer_and_robbery_shrinks_the_source(self):
        original = self.runs + [dict(inverter=2, mppt=1, modules=['f'], optimizer_group_sizes=[1])]
        runs, robbed = plant.add_modules(original, 1, ['b', 'x'])
        self.assertEqual(robbed, [0])
        self.assertEqual(runs[0]['optimizer_group_sizes'], [1, 1, 2])
        self.assertEqual(runs[1]['optimizer_group_sizes'], [1, 1, 1])
        self.assertEqual(self.runs[0]['optimizer_group_sizes'], [2, 1, 2])

    def test_redrawing_preserves_existing_groups_and_refuses_to_interleave_one(self):
        runs, _ = plant.set_run(self.runs, 0, list('acdex'))
        self.assertEqual(runs[0]['optimizer_group_sizes'], [1, 1, 2, 1])
        with self.assertRaisesRegex(ValueError, 'optimizer'):
            plant.set_run(self.runs, 0, list('acbde'))

    def test_runtime_and_saved_runs_use_actual_optimizer_count_and_reject_invalid_partitions(self):
        from meridiana import catalog, layout, model
        from meridiana.energy.components import ModuleSpec
        rec = next(r for r in catalog.search('inverters', manufacturer='SolarEdge', limit=None)
                   if r['model'] == 'SE50K')
        opt = next(r for r in catalog.search('optimizers', manufacturer='SolarEdge', limit=None)
                   if r['model'] == 'S1000')
        m = ModuleSpec('Fixture', '300', 300, 30, 10, 40, 10, 0, 0, 0, 60, 1, 1, _sdm={'linear': True})
        placed = [layout.PlacedModule(0, i, 0, [], (i, 0), 1, 15, 0) for i in range(28)]
        gs = [plant.Group('s1.0', 's1', 'Field', m, placed)]
        p = model.Project()
        run = dict(inverter=1, mppt=1, modules=[f's1/{pm.key}' for pm in placed], optimizer_group_sizes=[1]*28)
        p.energy = dict(inverters=[dict(record=rec, count=1, optimizer=opt, per_optimizer=2)], strings={'runs': [run]})
        out = plant.build(p, groups=gs)
        self.assertEqual(out.strings[0].plan.optimizers, 28)
        self.assertEqual(plant.runs_of(out)[0]['optimizer_group_sizes'], [1]*28)
        run['optimizer_group_sizes'] = [2]*14
        p.energy['inverters'][0]['per_optimizer'] = 1
        out = plant.build(p, groups=gs)
        self.assertEqual(out.strings[0].state, 'fail')
        self.assertIn('Invalid optimizer grouping', out.strings[0].why)
        p.energy['inverters'][0]['per_optimizer'] = 2
        del run['optimizer_group_sizes']
        out = plant.build(p, groups=gs)
        materialized = plant.materialize_optimizer_groups([run], out)
        self.assertEqual(materialized[0]['optimizer_group_sizes'], [2]*14)
        self.assertNotIn('optimizer_group_sizes', run)
