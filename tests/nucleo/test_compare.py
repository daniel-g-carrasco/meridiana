"""The variants side by side: the figures of one variant from the energy computation, the better value of a
row, and the table as text for a spreadsheet."""

import unittest
from types import SimpleNamespace

import _setup  # noqa: F401

from meridiana import compare


def out(kwh, npv, payback=None, near=-2.0):
    chain = [SimpleNamespace(key="near", change=near), SimpleNamespace(key="electrical", change=-0.5)]
    sim = SimpleNamespace(p_stc_kw=50.0, p_ac_kw=40.0, arrays=[{"modules": 100}], energy_kwh=kwh,
                          specific_yield=kwh / 50.0, pr=0.82, chain=chain)
    econ = SimpleNamespace(kpi={"self_ratio": 0.4, "self_sufficiency": 0.3, "export": kwh * 0.6, "capex": 50000.0,
                                "npv": npv, "payback": payback, "lcoe": 0.08})
    return {"sim": sim, "econ": econ, "battery_kwh": 0.0}


class Compare(unittest.TestCase):
    def test_the_figures_of_a_variant(self):
        s = compare.summary(out(60000.0, 30000.0, 7.5))
        self.assertEqual((s["kwp"], s["modules"], s["kwh"]), (50.0, 100, 60000.0))
        self.assertAlmostEqual(s["pr"], 82.0)
        self.assertAlmostEqual(s["shading"], 2.5)                 # near and electrical, as a positive loss
        self.assertAlmostEqual(s["self_ratio"], 40.0)
        self.assertEqual(compare.summary({"error_sim": "no weather"}), {"error": "no weather"})

    def test_the_better_one_of_each_row(self):
        a, b = compare.summary(out(60000.0, 30000.0, 7.5)), compare.summary(out(64000.0, 25000.0, None))
        self.assertEqual(compare.best([a, b], "kwh", "high"), 1)
        self.assertEqual(compare.best([a, b], "npv", "high"), 0)
        self.assertEqual(compare.best([a, b], "payback", "low"), None)     # only one pays back: no contest
        self.assertEqual(compare.best([a, b], "kwp", ""), None)            # no better on the size
        self.assertEqual(compare.best([a, dict(a)], "kwh", "high"), None)  # a tie

    def test_the_table_as_text(self):
        a, b = compare.summary(out(60000.0, 30000.0, 7.5)), {"error": "the layout failed"}
        text = compare.table_text(["Base", "Est-ovest"], [a, b])
        lines = text.splitlines()
        self.assertEqual(lines[0], "\tBase\tEst-ovest")
        self.assertTrue(any(line.startswith("Production (kWh/year)\t60,000\t") for line in lines))
        self.assertIn("the layout failed", text)
        self.assertTrue(any(line.startswith("Payback (years)\t7.5") for line in lines))


if __name__ == "__main__":
    unittest.main()
