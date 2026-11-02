"""What a sweep selects (sweep.py, R300) and the core of the commands that use it: the inverter taken out with or
without its strings (energy/plant.remove_unit, R299), a module moved alone and many deleted (manual.py, R295, R300)."""

import unittest

import numpy as np
from _fixtures import capannone, inverter_record, laid

from meridiana import manual, sweep
from meridiana.energy import plant


class Sweep(unittest.TestCase):
    QUADS = np.array([[[0, 0], [1, 0], [1, 1], [0, 1]], [[2, 0], [3, 0], [3, 1], [2, 1]]], dtype=float)

    def test_the_way_of_the_drag_says_window_or_crossing(self):
        self.assertEqual(sweep.kind_of(10, 20), sweep.WINDOW)
        self.assertEqual(sweep.kind_of(10, 10), sweep.WINDOW)
        self.assertEqual(sweep.kind_of(10, 5), sweep.CROSSING)

    def test_a_window_wants_all_inside_a_crossing_a_touch(self):
        ring = [(-1, -1), (2.5, -1), (2.5, 2), (-1, 2)]          # the first all inside, the second cut
        self.assertEqual(sweep.chosen_quads(self.QUADS, ring, sweep.WINDOW).tolist(), [True, False])
        self.assertEqual(sweep.chosen_quads(self.QUADS, ring, sweep.CROSSING).tolist(), [True, True])
        far = [(10, 10), (11, 10), (11, 11)]
        self.assertEqual(sweep.chosen_quads(self.QUADS, far, sweep.CROSSING).tolist(), [False, False])

    def test_a_free_shape_that_crosses_itself_still_selects_and_too_few_points_select_nothing(self):
        bow = [(-1, -1), (2.5, 2), (2.5, -1), (-1, 2)]           # a bow tie
        self.assertEqual(len(sweep.chosen_quads(self.QUADS, bow, sweep.CROSSING)), 2)
        self.assertTrue(sweep.chosen_quads(self.QUADS, bow, sweep.CROSSING).any())
        self.assertFalse(sweep.chosen_quads(self.QUADS, [(0, 0), (1, 1)], sweep.CROSSING).any())

    def test_the_outlines_follow_the_same_rule(self):
        ring = [(-1, -1), (1.5, -1), (1.5, 2), (-1, 2)]
        rings = [[(0, 0), (1, 0), (1, 1)], [(1, 0), (2, 0), (2, 1)], [(5, 5), (6, 5), (6, 6)]]
        self.assertEqual(sweep.chosen_rings(rings, ring, sweep.WINDOW), [True, False, False])
        self.assertEqual(sweep.chosen_rings(rings, ring, sweep.CROSSING), [True, True, False])


class RemoveUnit(unittest.TestCase):
    RUNS = [{"inverter": 1, "mppt": 1, "modules": ["a"]}, {"inverter": 2, "mppt": 1, "modules": ["b"]},
            {"inverter": 3, "mppt": 2, "modules": ["c"]}, {"inverter": 0, "mppt": 0, "modules": ["d"]}]

    def energy(self, *counts):
        return {"inverters": [{"record": inverter_record(), "count": c, "name": ""} for c in counts]}

    def test_with_its_strings_they_go_and_the_next_inverters_move_up(self):
        entries, runs = plant.remove_unit(self.energy(2, 1), self.RUNS, 2, True)
        self.assertEqual([e["count"] for e in entries], [1, 1])
        self.assertEqual([(r["inverter"], r["modules"]) for r in runs], [(1, ["a"]), (2, ["c"]), (0, ["d"])])

    def test_alone_its_strings_stay_on_no_inverter_with_their_modules(self):
        entries, runs = plant.remove_unit(self.energy(2, 1), self.RUNS, 2, False)
        self.assertEqual(len(entries), 2)
        self.assertEqual([(r["inverter"], r["mppt"], r["modules"]) for r in runs],
                         [(1, 1, ["a"]), (0, 0, ["b"]), (2, 2, ["c"]), (0, 0, ["d"])])

    def test_the_last_of_an_entry_takes_the_entry_with_it(self):
        entries, runs = plant.remove_unit(self.energy(2, 1), self.RUNS, 3, True)
        self.assertEqual([e["count"] for e in entries], [2])
        self.assertEqual(len(runs), 3)

    def test_with_no_inverter_chosen_there_is_none_to_take_out_and_the_numbers_stay(self):
        entries, runs = plant.remove_unit({}, self.RUNS, 1, True)
        self.assertIsNone(entries)
        self.assertEqual([r["inverter"] for r in runs], [2, 3, 0])


class ModulesByHand(unittest.TestCase):
    def setUp(self):
        self.project = capannone()
        self.result = laid(self.project)
        self.sf = self.project.subfields[0]

    def test_a_module_moved_alone_explodes_its_row_and_keeps_its_key(self):
        row = self.result.modules[0].rid
        key = self.result.modules[0].key
        others = [m.key for m in self.result.modules if m.rid == row and m.key != key]
        change = manual.move_module(self.project, self.sf.id, key, 0.0, -0.01, self.result)
        change(self.project)
        rows = self.sf.hand_rows()
        alone = next(r for r in rows if key in r.keys)
        self.assertEqual(alone.count, 1)
        kept = {k for r in rows if r is not alone for k in r.keys}
        self.assertTrue(set(others) <= kept)

    def test_a_module_that_would_leave_the_sub_field_is_refused(self):
        key = self.result.modules[0].key
        with self.assertRaises(ValueError):
            manual.move_module(self.project, self.sf.id, key, 500.0, 0.0, self.result)
        with self.assertRaises(ValueError):
            manual.move_module(self.project, self.sf.id, "not there", 0.0, 0.0, self.result)

    def test_many_deleted_at_once_are_taken_out_one_on_its_own_goes_with_its_row(self):
        keys = [m.key for m in self.result.modules[:3]]
        manual.delete_modules(self.project, self.sf.id, keys, self.result)(self.project)
        self.assertEqual(sorted(self.sf.removed), sorted(keys))
        self.sf.removed = []
        key = keys[0]
        manual.move_module(self.project, self.sf.id, key, 0.0, -0.01, self.result)(self.project)
        rows = self.sf.hand_rows()
        alone = next(r for r in rows if key in r.keys)
        other = next(r for r in rows if r.count > 1)            # a row of more: a module of it is taken out
        keep = other.slot_key(0)
        manual.delete_modules(self.project, self.sf.id, [key, keep], self.result)(self.project)
        self.assertNotIn(alone.id, [r.id for r in self.sf.hand_rows()])
        self.assertIn(other.id, [r.id for r in self.sf.hand_rows()])
        self.assertEqual(self.sf.removed, [keep])


if __name__ == "__main__":
    unittest.main()
