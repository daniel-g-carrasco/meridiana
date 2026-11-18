"""«Add a module»: one module where the designer points, never a whole row (06/11/2026)."""
import math
import unittest

import _setup  # noqa: F401
from _fixtures import laid
from _fixtures import tetto_con_lucernario as project

from meridiana import manual


class AddModule(unittest.TestCase):
    def setUp(self):
        self.p = project()
        self.p.subfields[0].filled = True
        self.auto = laid(self.p)
        self.rows = [r for r in self.auto.rows if r.places]
        self.sf = self.p.subfields[0]

    def size(self):
        return manual.frame(self.p, self.sf, self.rows)[1]

    def test_past_the_end_of_a_row_one_module_comes_not_a_row(self):
        row = self.rows[0]
        last = max((m for m in self.auto.modules if m.rid == row.id), key=lambda m: m.slot)
        manual.take(self.p, "s1", self.auto)(self.p)
        self.sf.rows[0]["places"] = self.sf.rows[0]["places"][:-3]        # the row three modules shorter
        before = laid(self.p)
        # the point where the last module was: one step past the end of the shorter row and one more
        manual.add_module(self.p, "s1", last.centre, before)(self.p)
        after = laid(self.p)
        self.assertEqual(after.count, before.count + 1)
        self.assertEqual(sum(1 for m in after.modules if m.rid == row.id), row.count - 3 + 1)
        old = {m.key for m in before.modules}
        new = [m for m in after.modules if m.key not in old]
        self.assertEqual(len(new), 1)
        self.assertLess(math.dist(new[0].centre, last.centre), 0.05)
        # the modules that were there keep their keys and their places
        kept = {m.key: m.centre for m in after.modules}
        for m in before.modules:
            self.assertLess(math.dist(kept[m.key], m.centre), 1e-3)

    def test_a_module_taken_out_comes_back_where_it_was(self):
        first = self.auto.modules[3]
        self.sf.removed = [first.key]
        before = laid(self.p)
        manual.add_module(self.p, "s1", first.centre, before)(self.p)
        self.assertEqual(self.sf.removed, [])
        self.assertEqual(laid(self.p).count, before.count + 1)

    def test_on_a_module_already_there_nothing_is_added(self):
        with self.assertRaises(ValueError):
            manual.add_module(self.p, "s1", self.auto.modules[0].centre, self.auto)

    def test_a_gap_in_a_row_takes_one_module_and_the_keys_of_the_others_stay(self):
        manual.take(self.p, "s1", self.auto)(self.p)
        row = self.rows[0]
        raw = self.sf.rows[0]
        self.assertEqual(raw["id"], row.id)
        step = row.places[1] - row.places[0]
        raw["places"] = [u for k, u in enumerate(raw["places"]) if k != 2]
        raw["keys"] = [row.slot_key(k) for k in range(row.count) if k != 2]
        before = laid(self.p)
        gone = next(m for m in self.auto.modules if m.rid == row.id and m.slot == 2)
        manual.add_module(self.p, "s1", gone.centre, before)(self.p)
        after = laid(self.p)
        self.assertEqual(after.count, before.count + 1)
        kept = {m.key: m.centre for m in after.modules}
        for m in before.modules:
            self.assertLess(math.dist(kept[m.key], m.centre), 1e-3, m.key)
        new = [m for m in after.modules if m.key not in {b.key for b in before.modules}]
        self.assertEqual(len(new), 1)
        self.assertLess(math.dist(new[0].centre, gone.centre), 0.05)
        self.assertGreater(step, 0)

    def test_outside_the_sub_field_it_is_refused(self):
        with self.assertRaises(ValueError):
            manual.add_module(self.p, "s1", (-500.0, -500.0), self.auto)


if __name__ == "__main__":
    unittest.main()
