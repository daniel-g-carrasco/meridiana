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
        def cancel():
            raise InterruptedError('stop')
        with self.assertRaises(InterruptedError):
            network.solve(first, wiring, cancel)

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
