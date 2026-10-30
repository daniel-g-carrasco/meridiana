"""Real wiring, optimizer voltage balance and independent inverter clipping."""
import unittest
from types import SimpleNamespace

import _setup  # noqa: F401
import numpy as np

from meridiana import layout
from meridiana.energy import electrical_network as network
from meridiana.energy import electrical as iv
from meridiana.energy import plant, simulate
from meridiana.energy.components import InverterSpec, ModuleSpec, TYPICAL_450


class Network(unittest.TestCase):
    def test_parallel_optimizer_inputs_obey_each_input_limit_under_unequal_irradiance(self):
        bright = iv.Curve(np.array([[0., 30., 40.]]), np.array([[15., 14., 0.]]))
        dark = iv.Curve(np.array([[0., 30., 40.]]), np.array([[2., 1.8, 0.]]))
        op = network.parallel_input_mpp([bright, dark], current_max=10)
        self.assertLessEqual(iv.current_at(bright, op.voltage[:, None])[0, 0], 10 + 1e-8)
        wrong = iv.mpp(iv.parallel([bright, dark]), current_max=20)
        self.assertLess(op.power[0], wrong.power[0] * .9)

    def test_fixed_voltage_needs_enough_lit_optimizer_output_voltage(self):
        got = network.optimizer_string_power(np.array([[500, 500], [500, 0], [100, 100]]), 100, 60, 10)
        np.testing.assert_allclose(got, [1000, 0, 200], atol=1e-5)
        limited = network.optimizer_string_power(np.array([[500, 500]]), 100, 60, 5)
        np.testing.assert_allclose(limited, [500], atol=1e-5)

    def fixture(self):
        m = ModuleSpec.from_record(dict(TYPICAL_450, length=1.762, width=1.134))
        placed = [layout.PlacedModule(0, i, 0, [(i, 0), (i + 1, 0), (i + 1, 2), (i, 2)],
                                     (i + .5, 1), 0, 0, 0) for i in range(2)]
        a = simulate.ArraySpec('s1.0', 'Field', 0, 0, 2, m, placed=placed)
        ap = SimpleNamespace(a=a, layout=(3, 2), g_eff=np.array([1000., 0]), t_cell=np.array([25., 25]),
                             beam_clear=np.array([900., 0]), diffuse_eff=np.array([100., 0]), row_share=np.zeros(2),
                             near=None, lid=0)
        first = SimpleNamespace(hours=2, per_array=[ap], losses=simulate.Losses(quality=0, lid=0, mismatch=0,
                                                                              dc_wiring=0),
                                sun_az=np.array([180., 0]), sun_el=np.array([45., -10]))
        spec = InverterSpec.from_record({'ac_power_nominal_w':1000, 'mppt_count':1, 'mppt_voltage_min_v':1,
                                        'mppt_voltage_max_v':60, 'dc_current_max_per_mppt_a':[30]})
        unit = plant.Unit(1, 0, spec, 'Inverter')
        wiring = plant.Plant(units=[unit], strings=[plant.String(1, 1, [('s1', placed[0].key, placed[0].centre)])])
        return first, wiring, placed

    def test_an_unshaded_module_connected_to_a_real_input_generates_but_an_unconnected_one_does_not(self):
        first, wiring, _placed = self.fixture()
        result = network.solve(first, wiring)
        self.assertGreater(result.dc[1][0], 440)
        self.assertLess(result.dc[1][0], 460)
        self.assertEqual(result.dc[1][1], 0)
        np.testing.assert_allclose(result.dc[1], result.stages['s1.0']['p_dc'])
        wiring.strings.clear()
        np.testing.assert_equal(network.solve(first, wiring).stages['s1.0']['p_dc'], [0, 0])

    def test_explicit_optimizer_groups_change_the_output_voltage_balance(self):
        first, wiring, placed = self.fixture()
        unit, run = wiring.units[0], wiring.strings[0]
        unit.fixed = SimpleNamespace(units=1, v_string=100)
        opt = SimpleNamespace(parallel_inputs=False, v_in_min=1, v_in_max=100, i_in_max=20,
                              i_out_max=15, v_out_max=60, eta=.98, name='Synthetic optimizer')
        unit.choice = SimpleNamespace(per=2, optimizer=opt, rules=None)
        run.modules = [('s1', p.key, p.centre) for p in placed]
        run.optimizer_group_sizes = [2]
        np.testing.assert_equal(network.solve(first, wiring).dc[1], [0, 0])
        run.optimizer_group_sizes = [1, 1]
        result = network.solve(first, wiring)
        self.assertGreater(result.dc[1][0], 850)
        self.assertLess(result.dc[1][0], 900)
        opt.i_out_max = 0
        self.assertTrue(any('i_out_max' in n for n in network.solve(first, wiring).notes))
        unit.choice = None
        missing = network.solve(first, wiring)
        np.testing.assert_equal(missing.dc[1], [0, 0])
        self.assertTrue(any('not calculated' in n for n in missing.notes))

    def test_network_cancellation_is_observed_before_a_chunk(self):
        first, wiring, _placed = self.fixture()
        told = []

        def cancel(share):
            told.append(share)
            raise InterruptedError('stop')
        with self.assertRaises(InterruptedError):
            network.solve(first, wiring, cancel)
        self.assertEqual(told, [0.0])               # the share done, before the first chunk

    def test_shared_current_derating_is_separate_from_dc_wiring(self):
        from dataclasses import replace
        first, wiring, placed = self.fixture()
        wiring.units[0].spec = replace(wiring.units[0].spec, imax_total=10)
        wiring.strings.append(plant.String(1, 1, [('s1', placed[1].key, placed[1].centre)]))
        got = network.solve(first, wiring)
        stage = got.stages['s1.0']
        self.assertGreater(stage['p_opt'][0], stage['p_cut'][0] * 2)
        np.testing.assert_allclose(stage['p_cut'], stage['p_dc'])  # zero wiring allowance
        self.assertTrue(any('proportionally' in n for n in got.notes))

    def test_absolute_dc_voltage_also_bounds_a_missing_tracker_maximum(self):
        from dataclasses import replace
        first, wiring, _placed = self.fixture()
        ordinary = network.solve(first, wiring).dc[1][0]
        wiring.units[0].spec = replace(wiring.units[0].spec, vmppt_max=None, vdc_max=20)
        got = network.solve(first, wiring)
        self.assertLess(got.dc[1][0], ordinary * .8)
        self.assertTrue(any('not fully verified' in n for n in got.notes))

    def test_spare_capacity_on_a_second_active_inverter_does_not_absorb_clipping(self):
        specs = {1:InverterSpec('Test','Small',5000,.98), 2:InverterSpec('Test','Large',20000,.98)}
        data = network.Network(specs=specs, dc={1:np.array([10000., 0]), 2:np.array([1000., 1000.])})
        before, ac, delivered, details = simulate._network_ac(data, simulate.Losses(ac_wiring=0), 2)
        one = simulate._pvwatts_inverter(data.dc[1], 5000, .98)[1]
        two = simulate._pvwatts_inverter(data.dc[2], 20000, .98)[1]
        np.testing.assert_allclose(ac, one + two)
        np.testing.assert_allclose(delivered, ac)
        combined = simulate._pvwatts_inverter(data.dc[1] + data.dc[2], 25000, .98)[1]
        self.assertGreater(combined[0] - ac[0], 3000)
        self.assertGreater(details[0]['clipping_kwh'], 4)
        self.assertEqual(details[1]['clipping_kwh'], 0)


class SharedShapes(unittest.TestCase):
    """R266: on a large plant the network computes each shape of module once per chunk of hours (the row in front,
    each level of the stack behind it, each module the obstacles shade) and each string, tracker and operating point
    once for identical ones; nothing is averaged, so every string gets what it gets computed alone."""

    def plant(self, slots=4):
        m = ModuleSpec.from_record(dict(TYPICAL_450, length=1.762, width=1.134))
        placed = [layout.PlacedModule(row, i, 0, [(i, 3 * row), (i + 1, 3 * row), (i + 1, 3 * row + 2), (i, 3 * row + 2)],
                                      (i + .5, 3 * row + 1), 0, 10, 0, level=level)
                  for row in range(2) for level in range(2) for i in range(slots)]
        a = simulate.ArraySpec('s1.0', 'Field', 10, 0, len(placed), m, rows=2, pitch=3, slant=2, stack=2,
                               placed=placed)
        hours = 3
        ap = SimpleNamespace(a=a, layout=(3, 2), g_eff=np.array([900., 500., 300.]), t_cell=np.array([40., 30., 20.]),
                             beam_clear=np.array([800., 400., 150.]), diffuse_eff=np.array([100., 100., 150.]),
                             row_share=np.array([.2, .6, 0.]), near=None, lid=0)
        first = SimpleNamespace(hours=hours, per_array=[ap], losses=simulate.Losses(quality=0, lid=0, mismatch=1,
                                                                                    dc_wiring=1),
                                sun_az=np.array([150., 180., 210.]), sun_el=np.array([20., 30., 10.]))
        spec = InverterSpec.from_record({'ac_power_nominal_w': 20000, 'mppt_count': 2, 'mppt_voltage_min_v': 1,
                                         'mppt_voltage_max_v': 1000, 'dc_current_max_per_mppt_a': [30, 30]})
        # one string for each place: the front row and the row behind, each level of the stack; two more like the
        # first two on a second inverter, so that identical strings and trackers are met again
        groups = {}
        for pm in placed:
            groups.setdefault((pm.row, pm.level), []).append(('s1', pm.key, pm.centre))
        strings = [plant.String(1 + n // 2, 1 + n % 2, refs) for n, refs in enumerate(groups.values())]
        units = [plant.Unit(n, 0, spec, f'Inverter {n}') for n in (1, 2, 3)]
        return first, plant.Plant(units=units, strings=strings), strings

    def test_each_string_gets_what_it_gets_alone(self):
        first, wiring, strings = self.plant()
        together = network.solve(first, wiring)
        alone = {}
        for s in strings:
            one = network.solve(first, plant.Plant(units=wiring.units, strings=[s]))
            alone.setdefault(s.inverter, np.zeros(first.hours))
            alone[s.inverter] += one.dc[s.inverter]
        for number, dc in alone.items():
            np.testing.assert_allclose(together.dc[number], dc, rtol=1e-12, atol=1e-9)
        # the shapes are really different: the rows behind lose to the row in front, the lower level more
        front, behind_low, behind_high = (network.solve(first, plant.Plant(units=wiring.units, strings=[s])).dc[s.inverter]
                                          for s in (strings[0], strings[2], strings[3]))
        self.assertLess(behind_low[1], behind_high[1] - 1)
        self.assertLess(behind_high[1], front[1] - 1)
        stage = together.stages['s1.0']['p_dc']
        np.testing.assert_allclose(stage, sum(together.dc.values()), rtol=1e-12)

    def test_the_curves_computed_do_not_grow_with_the_modules(self):
        from unittest import mock

        from meridiana.energy import nearshade
        counts = []
        for slots in (4, 24):           # 16 and 96 modules, the same four places in the rows
            first, wiring, _strings = self.plant(slots)
            with mock.patch.object(iv, 'module_curve', wraps=iv.module_curve) as curves, \
                    mock.patch.object(nearshade, 'cell_histogram', wraps=nearshade.cell_histogram) as cohorts:
                network.solve(first, wiring)
            counts.append((curves.call_count, cohorts.call_count))
        self.assertEqual(counts[0], counts[1])


class HoursOfAnotherModule(unittest.TestCase):
    """R266, under the obstacles' shade: a module's hours already computed for another module of the array (the same
    light, temperature and cohorts) are taken from it; the curve is the one the module gets computed alone."""

    def test_a_module_takes_the_hours_it_shares_and_gets_its_own_curve(self):
        from meridiana.energy import nearshade
        m = ModuleSpec.from_record(dict(TYPICAL_450, length=1.762, width=1.134))
        a = SimpleNamespace(key='s1.0', module=m)
        rng = np.random.default_rng(11)
        hours, blocks, levels = 10, 6, nearshade.CELL_LEVELS
        shade = np.linspace(0, 1, levels)
        light = np.broadcast_to((60 + 800 * (1 - shade))[None, None, :] * np.linspace(.3, 1.1, hours)[:, None, None],
                                (hours, blocks, levels))
        temperature = np.linspace(5, 45, hours)

        def module(shaded, spread):
            f = np.zeros((hours, blocks, levels))
            f[..., 0] = 1
            for h in shaded:
                share = rng.uniform(0, 1, (blocks, spread))
                share /= share.sum(axis=1, keepdims=True)
                f[h] = 0
                f[h, :, rng.choice(levels, spread, replace=False)] = share.T
            return f
        first, second = module((2, 3, 6), 3), module((1, 6, 8), 6)    # different plans: 3 and 6 cohorts
        known = {}
        network._module_curve(a, light, temperature, (3, 2), first, known)
        computed = []
        real = iv.module_curve

        def counting(*args, **kwargs):
            computed.append(len(args[1]))
            return real(*args, **kwargs)
        from unittest import mock
        with mock.patch.object(iv, 'module_curve', counting):
            got = network._module_curve(a, light, temperature, (3, 2), second, known)
        # its three shaded hours and the two clear ones the first module had in a shadow (2, 3); the five clear
        # hours of both were known
        self.assertEqual(computed, [5])
        alone = iv.module_curve(m, light, temperature, (3, 2), cell_fractions=second)
        np.testing.assert_allclose(got.voltage, alone.voltage, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(got.current, alone.current, rtol=1e-12, atol=1e-12)
