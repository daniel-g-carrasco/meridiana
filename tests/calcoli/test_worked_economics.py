"""R661 (Daniel 15/11/2026: «come mai per ogni formula dopo quella con i simboli sotto non c'è quella con i valori
sostituiti??»): the money's steps (saving, sale, NPV, IRR, LCOE) have their formula again with the numbers
(energy/worked.py, as the energy's since R479). The numbers are the table's of the step at its decimals, or the
calculation's (the cash flows): the line's result is the table's, and the arithmetic of the numbers shown gives it
within the rounding of what is shown."""

import unittest

import numpy as np
import pandas as pd

import _setup  # noqa: F401

from meridiana.core.energy import economics, worked
from meridiana.core.energy.economics import Settings


def record():
    idx = pd.date_range("2026-01-01", periods=8760, freq="h", tz="UTC").tz_convert("Europe/Rome")
    prod = pd.Series(np.where((idx.hour >= 10) & (idx.hour < 16), 3.0, 0.0), index=idx)
    load = pd.Series(np.full(8760, 1.0), index=idx)
    return economics.evaluate(prod, load, 6.0, 5.0, Settings.from_dict({}), detail=True).record


class WorkedMoney(unittest.TestCase):
    def setUp(self):
        self.rec = record()

    def test_every_money_step_has_its_line(self):
        for key in ("saving", "sale", "npv", "irr", "lcoe"):
            with self.subTest(step=key):
                step = self.rec.find(key)
                self.assertIsNotNone(step)
                self.assertEqual(len(step.worked), 1)
                self.assertIn("=", step.worked[0])

    def test_the_line_ends_in_the_table_s_result(self):
        for key in ("saving", "sale", "npv", "lcoe"):
            with self.subTest(step=key):
                step = self.rec.find(key)
                q = step.result                             # the table's number, at the decimals it is shown with
                digits = worked.V(q.value, q.decimals, q.unit).digits()
                self.assertTrue(step.worked[0].endswith(r"\mathbf{" + digits + "}" + worked.unit_tex(q.unit)),
                                step.worked[0])

    def test_the_sale_s_arithmetic_with_the_numbers_shown(self):
        step = self.rec.find("sale")
        e, p = (q.value for q in step.inputs)
        shown = [q for q in step.inputs]
        product = round(float(e), shown[0].decimals) * round(float(p), shown[1].decimals)
        self.assertLessEqual(abs(product - float(step.result.value)), 0.5 + 10 ** -shown[1].decimals * 0.5 * float(e))

    def test_the_sums_over_the_years_show_first_terms_dots_and_last(self):
        line = self.rec.find("npv").worked[0]
        self.assertIn(r"\dots", line)
        self.assertEqual(line.count(r"\frac"), 3, 'the first two years and the last')
        self.assertIn("^{25}", line)


if __name__ == "__main__":
    unittest.main()
