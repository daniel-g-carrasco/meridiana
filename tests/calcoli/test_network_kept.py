"""R478: the network keeps what each group of strings gave over each chunk of hours, by what it was made of.

A year computed again with the parts kept is the same to the last digit as one computed from nothing; a change of
one array computes again only the strings with modules on it, a change of an inverter only its strings."""
import unittest
from dataclasses import replace
from types import SimpleNamespace

import _setup  # noqa: F401
import numpy as np

from meridiana import layout
from meridiana.energy import electrical_network as network
from meridiana.energy import plant, simulate
from meridiana.energy.components import InverterSpec, ModuleSpec, TYPICAL_450

SPEC = {'ac_power_nominal_w': 20000, 'mppt_count': 2, 'mppt_voltage_min_v': 1, 'mppt_voltage_max_v': 1000,
        'dc_current_max_per_mppt_a': [30, 30]}


def array(key, light):
    m = ModuleSpec.from_record(dict(TYPICAL_450, length=1.762, width=1.134))
    placed = [layout.PlacedModule(row, i, 0, [(i, 3 * row), (i + 1, 3 * row), (i + 1, 3 * row + 2), (i, 3 * row + 2)],
                                  (i + .5, 3 * row + 1), 0, 10, 0, level=level)
              for row in range(2) for level in range(2) for i in range(4)]
    a = simulate.ArraySpec(key, key, 10, 0, len(placed), m, rows=2, pitch=3, slant=2, stack=2, placed=placed)
    hours = np.arange(120)
    sun = np.clip(np.sin((hours % 24 - 6) / 12 * np.pi), 0, None)
    return SimpleNamespace(a=a, layout=(3, 2), g_eff=light * 900 * sun, t_cell=15 + 25 * sun,
                           beam_clear=light * 800 * sun, diffuse_eff=100 * sun, row_share=.5 * sun, near=None, lid=0)


def year(arrays, specs=(SPEC, SPEC)):
    hours = 120
    first = SimpleNamespace(hours=hours, per_array=arrays, losses=simulate.Losses(quality=0, lid=0, mismatch=1,
                                                                                    dc_wiring=1),
                            sun_az=np.linspace(90, 270, hours), sun_el=np.full(hours, 30.))
    strings = []
    for n, ap in enumerate(arrays, start=1):
        sid = ap.a.key.split('.')[0]
        for mppt, level in ((1, 0), (2, 1)):
            refs = [(sid, pm.key, pm.centre) for pm in ap.a.placed if pm.level == level]
            strings.append(plant.String(n, mppt, refs))
    units = [plant.Unit(n, 0, InverterSpec.from_record(spec), f'Inverter {n}') for n, spec in enumerate(specs, 1)]
    return first, plant.Plant(units=units, strings=strings)


def same(a, b):
    for name in ('reference', 'at25', 'nominal', 'dc'):
        x, y = getattr(a, name), getattr(b, name)
        assert x.keys() == y.keys(), name
        for k in x:
            np.testing.assert_array_equal(x[k], y[k], err_msg=f'{name} {k}')
    for k in a.stages:
        for stage in a.stages[k]:
            np.testing.assert_array_equal(a.stages[k][stage], b.stages[k][stage], err_msg=f'{k} {stage}')
    assert a.notes == b.notes


class Kept(unittest.TestCase):
    def setUp(self):
        network._PARTS.clear()
        self.addCleanup(network._PARTS.clear)

    def solve(self, first, wiring, fresh=False):
        if fresh:
            network._PARTS.clear()
        before = dict(network._STATS)
        out = network.solve(first, wiring, workers=1)
        return out, network._STATS['kept'] - before['kept'], network._STATS['made'] - before['made']

    def test_a_year_again_is_found_and_the_same(self):
        first, wiring = year([array('s1.0', 1.0), array('s2.0', .7)])
        made, kept, count = self.solve(first, wiring)
        self.assertEqual(kept, 0)
        again, kept, none = self.solve(first, wiring)
        self.assertEqual((kept, none), (count, 0))
        same(made, again)

    def test_a_change_of_one_array_computes_its_strings_only(self):
        first, wiring = year([array('s1.0', 1.0), array('s2.0', .7)])
        _out, _kept, count = self.solve(first, wiring)
        changed = array('s2.0', .7)
        changed.diffuse_eff = changed.diffuse_eff * 1.01
        first2, wiring2 = year([array('s1.0', 1.0), changed])
        out, kept, made = self.solve(first2, wiring2)
        self.assertEqual((kept, made), (count // 2, count // 2))
        fresh, _k, _m = self.solve(first2, wiring2, fresh=True)
        same(out, fresh)

    def test_a_change_of_an_inverter_computes_its_strings_only(self):
        first, wiring = year([array('s1.0', 1.0), array('s2.0', .7)])
        _out, _kept, count = self.solve(first, wiring)
        first2, wiring2 = year([array('s1.0', 1.0), array('s2.0', .7)],
                               (SPEC, dict(SPEC, dc_current_max_per_mppt_a=[8, 8])))
        out, kept, made = self.solve(first2, wiring2)
        self.assertEqual((kept, made), (count // 2, count // 2))
        fresh, _k, _m = self.solve(first2, wiring2, fresh=True)
        same(out, fresh)

    def test_parts_merged_are_the_single_computation(self):
        # the chunk made inverter by inverter and merged gives what one computation of it gives: kept or not
        first, wiring = year([array('s1.0', 1.0), array('s2.0', .7)])
        whole = network.solve(first, wiring, workers=1)
        network._PARTS.clear()
        units = {u.number: u for u in wiring.units}
        alone = [network.solve(first, replace(wiring, strings=[s for s in wiring.strings if s.inverter == n]),
                               workers=1) for n in units]
        for n, out in zip(units, alone, strict=True):
            np.testing.assert_array_equal(out.dc[n], whole.dc[n])


if __name__ == '__main__':
    unittest.main()
