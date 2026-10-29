"""Quantitative circuit tests, independent of the project's annual irradiance pipeline."""
import unittest

import _setup  # noqa: F401
import numpy as np

from meridiana.energy import electrical
from meridiana.energy.components import ModuleSpec, TYPICAL_450
from meridiana.energy.dependencies import load_pvlib


def module():
    return ModuleSpec.from_record(dict(TYPICAL_450, length=1.762, width=1.134, bypass_diodes=3))


class Circuit(unittest.TestCase):
    def test_uniform_module_matches_independent_pvlib_mpp_at_actual_temperature(self):
        m = module()
        g, t = np.array([200, 600, 1000]), np.array([5, 25, 60])
        curve = electrical.module_curve(m, np.broadcast_to(g[:, None], (3, 3)), t, (3, 1))
        got = electrical.mpp(curve)
        expected = load_pvlib().pvsystem.max_power_point(*m.diode_params(g, t), method='chandrupatla')
        np.testing.assert_allclose(got.power, expected['p_mp'], rtol=0.003)

    def test_bypass_keeps_two_lit_sections_and_order_has_no_downstream_effect(self):
        m = module()
        lit = electrical.module_curve(m, np.array([[1000, 1000, 1000]]), [25], (3, 1))
        shaded = electrical.module_curve(m, np.array([[1000, 100, 1000]]), [25], (3, 1))
        whole, part = electrical.mpp(lit).power[0], electrical.mpp(shaded).power[0]
        self.assertGreater(part / whole, 0.60)
        self.assertLess(part / whole, 0.68)
        a = electrical.series([lit, shaded, lit])
        b = electrical.series([shaded, lit, lit])
        np.testing.assert_allclose(electrical.mpp(a).power, electrical.mpp(b).power, rtol=1e-12)
        self.assertGreater(electrical.mpp(a).power[0], 2.5 * whole)

    def test_half_cell_parallel_branches_share_voltage(self):
        m = module()
        bright = electrical.module_curve(m, np.full((1, 6), 1000), [25], (3, 2))
        half = electrical.module_curve(m, np.array([[1000, 100, 1000, 100, 1000, 100]]), [25], (3, 2))
        ratio = electrical.mpp(half).power / electrical.mpp(bright).power
        self.assertGreater(ratio[0], 0.50)
        self.assertLess(ratio[0], 0.58)

    def test_parallel_strings_use_one_voltage_and_limits_constrain_the_operating_point(self):
        m = module()
        a = electrical.series([electrical.module_curve(m, np.full((1, 3), 1000), [25], (3, 1))] * 10)
        b = electrical.series([electrical.module_curve(m, np.array([[1000, 100, 1000]]), [25], (3, 1))] * 10)
        shared = electrical.mpp(electrical.parallel([a, b]))
        independent = electrical.mpp(a).power + electrical.mpp(b).power
        self.assertLess(shared.power[0], 0.98 * independent[0])
        limited = electrical.mpp(a, current_max=5, voltage_min=200, voltage_max=350)
        self.assertLessEqual(limited.current[0], 5.00001)
        self.assertLessEqual(limited.voltage[0], 350)
        self.assertLess(limited.power[0], electrical.mpp(a).power[0])

    def test_darkness_gives_finite_zero(self):
        curve = electrical.module_curve(module(), np.zeros((2, 3)), [25, 40], (3, 1))
        np.testing.assert_equal(electrical.mpp(curve).power, [0, 0])

    def test_iv_sampling_converges_on_multiple_bypass_peaks(self):
        g = np.array([[1000., 100., 800.], [500., 1000., 250.], [100., 100., 1000.]])
        powers = [electrical.mpp(electrical.module_curve(module(), g, [25] * 3, (3, 1), points=n)).power
                  for n in (129, 513)]
        np.testing.assert_allclose(powers[0], powers[1], rtol=.025)

    def test_shaded_bypass_matches_independent_pvlib_voltage_at_current_sweep(self):
        from pvlib.pvsystem import v_from_i
        m = module()
        g = np.array([1000., 100., 1000.])
        il, io, rs, rsh, a = [np.broadcast_to(z, g.shape) for z in m.diode_params(g, 25.)]
        current = np.linspace(0, float(il.max()), 10001)[:, None]
        voltage = v_from_i(current, il, io, rs / 3, rsh / 3, a / 3)
        reference = np.nanmax(np.maximum(voltage, -.5).sum(axis=1) * current[:, 0])
        actual = electrical.mpp(electrical.module_curve(m, g[None, :], [25], (3, 1))).power[0]
        self.assertAlmostEqual(actual / reference, 1, delta=.003)

    def test_same_area_on_one_cell_costs_more_than_even_shade_on_all_cells(self):
        m = module()
        g = np.array([[[1000, 100], [1000, 100], [1000, 100]]])
        fractions = np.array([[[0.95, 0.05], [1, 0], [1, 0]]])
        concentrated = electrical.module_curve(m, g, [25], (3, 1), cell_fractions=fractions)
        distributed = electrical.module_curve(m, np.array([[955, 1000, 1000]]), [25], (3, 1))
        self.assertLess(electrical.mpp(concentrated).power[0], 0.80 * electrical.mpp(distributed).power[0])


class BlockGeometry(unittest.TestCase):
    def test_missing_cell_count_preserves_block_shadow_and_declares_lower_resolution(self):
        from meridiana import layout
        from meridiana.energy import nearshade
        pm = layout.PlacedModule(0, 0, 0, [(0, 0), (1, 0), (1, 2), (0, 2)], (0.5, 1), 0, 0, 0)
        solid = nearshade.prism([(0, -1), (.4, -1), (.4, .5), (0, .5)], 0, 2)
        sh = nearshade.shading([pm], solid, 0, 0, layout=(3, 2))
        self.assertFalse(sh.cell_resolved)
        actual = nearshade.cell_cohorts(sh, 0, [180], [30])[0] @ np.linspace(0, 1, nearshade.CELL_LEVELS)
        expected = nearshade.block_shares(sh, [0], [180], [30])[0, 0]
        np.testing.assert_allclose(actual, expected)

    def test_block_areas_conserve_the_module_shadow_area(self):
        from meridiana import layout
        from meridiana.energy import nearshade
        pm = layout.PlacedModule(0, 0, 0, [(0, 0), (1, 0), (1, 2), (0, 2)], (0.5, 1), 0, 0, 0)
        solids = nearshade.prism([(0, -1), (0.4, -1), (0.4, 0.5), (0, 0.5)], 0, 2)
        sh = nearshade.shading([pm], solids, 0, 0, layout=(3, 2), cell_count=108)
        block = nearshade.block_shares(sh, [0], [180], [30])[0, 0]
        area = nearshade.at(sh.modules[0], [180], [30])[0]
        self.assertAlmostEqual(float(block.mean()), area, delta=2e-5)
        self.assertGreater(float(block.max()), float(block.min()))
        cohorts = nearshade.cell_cohorts(sh, 0, [180], [30])[0]
        np.testing.assert_allclose(cohorts @ np.linspace(0, 1, nearshade.CELL_LEVELS), block, atol=4e-5)

    def test_cell_shadow_quantization_converges_on_concentrated_and_distributed_patterns(self):
        from meridiana.energy import nearshade
        m = module()
        patterns = np.array([[0] * 17 + [.13, .53, .81], [.21] * 20, [0] * 19 + [1.]])
        powers = {}
        for levels in (5, 9, 17, 65):
            fractions = np.tile(nearshade.cell_histogram(patterns, levels)[:, None, :], (1, 3, 1))
            g = np.broadcast_to(100 + 900 * (1 - np.linspace(0, 1, levels)), fractions.shape)
            powers[levels] = electrical.mpp(electrical.module_curve(m, g, [25] * 3, (3, 1),
                                                                   cell_fractions=fractions)).power
        np.testing.assert_allclose(powers[17], powers[65], rtol=.03)
        self.assertEqual(nearshade.CELL_LEVELS, 17)
        self.assertGreater(abs(powers[9][0] / powers[17][0] - 1), .10)  # rejects an insufficient default resolution
