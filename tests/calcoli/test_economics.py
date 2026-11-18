"""The money: the community's premium tariff as DM MASE 414/2023 writes it, the hourly balance, the rates
and paybacks on cash flows whose answer is known, and defaults that are marked as such."""

import unittest

import numpy as np
import pandas as pd

import _setup  # noqa: F401

from meridiana.energy import economics
from meridiana.energy.economics import Settings


def year_index():
    return pd.date_range("2026-01-01", periods=8760, freq="h", tz="UTC").tz_convert("Europe/Rome")


class Tariff(unittest.TestCase):
    def test_the_premium_tariff_of_dm_414(self):
        # DM MASE 414 of 07/12/2023, Allegato 1, p. 23-24 (verified on the archive: B-norme-citazioni.md, section 3):
        # up to 200 kW: 80 + max(0, 180 - Pz), at most 120; North +10 after the cap
        self.assertAlmostEqual(float(economics.tip(150.0, 50, "other")), 110.0)
        self.assertAlmostEqual(float(economics.tip(100.0, 50, "other")), 120.0)
        self.assertAlmostEqual(float(economics.tip(100.0, 50, "north")), 130.0)
        self.assertAlmostEqual(float(economics.tip(200.0, 50, "centre")), 84.0)
        # over 600 kW: 60 + ..., at most 100
        self.assertAlmostEqual(float(economics.tip(100.0, 1000, "other")), 100.0)
        self.assertAlmostEqual(float(economics.tip(170.0, 400, "other")), 80.0)
        # a capital grant of 40% halves it, 20% takes a quarter
        self.assertAlmostEqual(float(economics.tip(100.0, 50, "other", grant_pct=40)), 60.0)
        self.assertAlmostEqual(float(economics.tip(100.0, 50, "other", grant_pct=20)), 90.0)

    def test_the_zone_from_the_address(self):
        self.assertEqual(economics.zone_from_address("Rho, Città metropolitana di Milano, Lombardia, Italia"), "north")
        self.assertEqual(economics.zone_from_address("Roma, Lazio, Italia"), "centre")
        self.assertEqual(economics.zone_from_address("Palermo, Sicilia, Italia"), "other")


class Money(unittest.TestCase):
    def test_the_rate_of_a_known_flow(self):
        # -1000 now, +1100 in a year: 10%
        self.assertAlmostEqual(economics.irr(np.array([-1000.0, 1100.0])), 0.10, places=6)
        self.assertIsNone(economics.irr(np.array([-1000.0, -10.0])))
        # a tiny investment with a large return: 200% a year, which came back as None before 23/10/2026
        self.assertAlmostEqual(economics.irr(np.array([-1.0, 3.0])), 2.0, places=6)
        self.assertAlmostEqual(economics.irr(np.array([-1.0, 0.0, 0.0, 1331.0])), 10.0, places=5)   # 1000% a year

    def test_balance_and_kpis(self):
        idx = year_index()
        prod = pd.Series(np.where((idx.hour >= 10) & (idx.hour < 16), 3.0, 0.0), index=idx)
        load = pd.Series(np.full(8760, 1.0), index=idx)
        r = economics.evaluate(prod, load, 6.0, 5.0, Settings.from_dict({}))
        k = r.kpi
        self.assertAlmostEqual(k["self"], 6 * 365 * 1.0, places=3)
        self.assertAlmostEqual(k["export"], 6 * 365 * 2.0, places=3)
        self.assertAlmostEqual(k["import"], 18 * 365 * 1.0, places=3)
        self.assertAlmostEqual(k["self"] + k["export"], k["production"], places=6)
        self.assertAlmostEqual(k["self"] + k["import"], k["consumption"], places=6)
        self.assertEqual(len(r.years), 25)
        self.assertIsNotNone(k["payback"])

    def test_the_bill_month_by_month_adds_up_to_the_year(self):
        idx = year_index()
        prod = pd.Series(np.where((idx.hour >= 10) & (idx.hour < 16), 3.0, 0.0), index=idx)
        load = pd.Series(np.full(8760, 1.0), index=idx)
        r = economics.evaluate(prod, load, 6.0, 5.0, Settings.from_dict({"buy_f1": 0.30}))
        self.assertAlmostEqual(float(r.monthly.bill_before.sum()), r.kpi["bill_before"], places=6)
        self.assertAlmostEqual(float(r.monthly.bill_after.sum()), r.kpi["bill_after"], places=6)
        self.assertAlmostEqual(float(r.monthly.sale.sum()), r.kpi["sale_1"], places=6)
        self.assertTrue((r.monthly.bill_after <= r.monthly.bill_before).all())

    def test_a_cheaper_system_pays_back_sooner(self):
        idx = year_index()
        prod = pd.Series(np.where((idx.hour >= 9) & (idx.hour < 17), 4.0, 0.0), index=idx)
        load = pd.Series(np.full(8760, 1.5), index=idx)
        dear = economics.evaluate(prod, load, 6.0, 5.0, Settings.from_dict({"capex_per_kwp": 2000}))
        cheap = economics.evaluate(prod, load, 6.0, 5.0, Settings.from_dict({"capex_per_kwp": 1000}))
        self.assertLess(cheap.kpi["payback"], dear.kpi["payback"])
        self.assertGreater(cheap.kpi["npv"], dear.kpi["npv"])
        self.assertLess(cheap.kpi["lcoe"], dear.kpi["lcoe"])

    def test_the_community_adds_its_tariff_for_twenty_years(self):
        idx = year_index()
        prod = pd.Series(np.where((idx.hour >= 10) & (idx.hour < 15), 10.0, 0.0), index=idx)
        load = pd.Series(np.full(8760, 0.5), index=idx)
        r = economics.evaluate(prod, load, 20.0, 18.0, Settings.from_dict({"community": True, "zone": "north"}))
        self.assertGreater(r.years.incentive.iloc[0], 0)
        self.assertEqual(r.years.incentive.iloc[20], 0.0)
        self.assertAlmostEqual(r.kpi["tip"], 130.0)

    def test_defaults_are_marked_and_given_values_are_not(self):
        s = Settings.from_dict({"buy_f1": 0.31})
        self.assertEqual(s.source("buy_f1").kind, "input")
        self.assertEqual(s.source("buy_f2").kind, "default")


BATTERY = {"manufacturer": "Acme", "model": "B10", "usable_energy_kwh": 10.0, "max_charge_power_w": 5000,
           "max_discharge_power_w": 5000, "round_trip_efficiency_pct": 90.0}


class Storage(unittest.TestCase):
    def day_and_evening(self):
        idx = year_index()
        prod = pd.Series(np.where((idx.hour >= 9) & (idx.hour < 16), 4.0, 0.0), index=idx)
        load = pd.Series(np.where((idx.hour >= 18) & (idx.hour < 23), 2.0, 0.3), index=idx)
        return prod, load

    def test_energy_is_kept_and_limits_hold(self):
        prod, load = self.day_and_evening()
        b = economics.Battery.from_settings(Settings.from_dict({"battery": BATTERY}))
        hb = economics.balance(prod, load, b)
        self.assertTrue(np.allclose(hb.production, hb.direct + hb.stored + hb.export))
        self.assertTrue(np.allclose(hb.consumption, hb.direct + hb.given + hb["import"]))
        self.assertLessEqual(float(hb.soc.max()), 10.0 + 1e-9)
        self.assertLessEqual(float(hb.stored.max()), 5.0 + 1e-9)
        self.assertLessEqual(float(hb.given.max()), 5.0 + 1e-9)
        # what comes out is what went in, less the losses (and what is left at the end of the year)
        self.assertAlmostEqual(float(hb.given.sum()), 0.9 * float(hb.stored.sum()) - 0.9 ** 0.5 * float(hb.soc.iloc[-1]),
                               delta=1e-6)

    def test_a_battery_raises_self_consumption_and_costs(self):
        prod, load = self.day_and_evening()
        without = economics.evaluate(prod, load, 6.0, 5.0, Settings.from_dict({}))
        with_b = economics.evaluate(prod, load, 6.0, 5.0, Settings.from_dict({"battery": BATTERY}))
        self.assertGreater(with_b.kpi["self_sufficiency"], without.kpi["self_sufficiency"] + 0.2)
        self.assertAlmostEqual(with_b.kpi["capex"] - without.kpi["capex"], 10.0 * 650.0)
        self.assertIsNotNone(with_b.record.find("battery"))

    def test_an_export_limit_curtails_and_zero_export_feeds_nothing(self):
        prod, load = self.day_and_evening()
        free = economics.evaluate(prod, load, 6.0, 5.0, Settings.from_dict({}))
        zero = economics.evaluate(prod, load, 6.0, 5.0, Settings.from_dict({"export_limit_kw": 0.0}))
        capped = economics.evaluate(prod, load, 6.0, 5.0, Settings.from_dict({"export_limit_kw": 2.0}))
        self.assertAlmostEqual(zero.kpi["export"], 0.0)
        self.assertAlmostEqual(zero.kpi["curtailed"], free.kpi["export"], places=6)
        self.assertLessEqual(float(capped.hourly["export"].max()), 2.0 + 1e-9)
        hb = capped.hourly
        self.assertTrue(np.allclose(hb.production, hb.direct + hb.stored + hb.export + hb.curtailed))
        self.assertLess(zero.kpi["sale_1"], free.kpi["sale_1"])
        self.assertIsNotNone(zero.record.find("export_limit"))

    def test_a_larger_system_self_consumes_less_and_covers_more(self):
        prod, load = self.day_and_evening()
        s = Settings.from_dict({})
        sweep = economics.sizing(prod, load, 6.0, 5.0, s)
        self.assertEqual(len(sweep), len(economics.SIZE_FACTORS))
        self.assertTrue((sweep.self_ratio.diff().dropna() <= 1e-9).all())
        self.assertTrue((sweep.self_sufficiency.diff().dropna() >= -1e-9).all())
        same = sweep[sweep.factor == 1.0].iloc[0]
        self.assertAlmostEqual(same.npv, economics.evaluate(prod, load, 6.0, 5.0, s).kpi["npv"], places=6)
        offer = economics.sizing(prod, load, 6.0, 5.0, Settings.from_dict({"capex_total": 9000.0}))
        self.assertAlmostEqual(offer[offer.factor == 2.0].iloc[0].capex, 18000.0)

    def test_a_larger_battery_covers_more_until_the_surplus_ends(self):
        prod, load = self.day_and_evening()
        frame, what = economics.storage_sizing(prod, load, 6.0, 5.0, Settings.from_dict({}))
        self.assertEqual(frame.kwh.iloc[0], 0.0)
        self.assertTrue((frame.self_sufficiency.diff().dropna() >= -1e-9).all())
        self.assertGreater(frame.self_sufficiency.iloc[-1], frame.self_sufficiency.iloc[0] + 0.2)
        self.assertAlmostEqual(frame.capex.iloc[2] - frame.capex.iloc[0], frame.kwh.iloc[2] * 650.0, places=6)
        self.assertIn("650", what)

    def test_the_dispatch_of_many_pairs_at_once_equals_the_dispatch_of_each(self):
        # short years, odd batteries (tiny, huge, no power), hours with no surplus at all: every (battery, row)
        # of dispatch_many within 1e-9 of dispatch on that pair, the first-year balance included
        rng = np.random.default_rng(1)
        worst = 0.0
        for i in range(40):
            n = int(rng.integers(1, 400))
            prod = np.clip(rng.normal(20, 15, n), 0, None) * rng.choice([0.0, 1.0], p=[0.1, 0.9], size=n)
            cons = prod.copy() if i % 7 == 0 else np.clip(rng.normal(15, 10, n), 0, None)
            kwh = float(rng.choice([0.5, 5.0, 40.0, 500.0]))
            batteries = [economics.Battery(kwh, float(rng.choice([0.2, kwh / 2, 1e6])),
                                           float(rng.choice([0.1, kwh / 2, 1e6])), float(rng.choice([0.5, 0.9, 1.0]))),
                         economics.Battery(kwh * 3, kwh, kwh, 0.8)]
            factors = np.array([1.0, 0.9, 0.5])
            got = economics.dispatch_many(prod[None, :] * factors[:, None] - cons[None, :], batteries)
            for bi, b in enumerate(batteries):
                for fi, f in enumerate(factors):
                    ref = economics.dispatch(prod * f, cons, b)
                    for g, r in zip(got, ref, strict=True):
                        self.assertTrue(np.allclose(g[bi, fi], r, rtol=1e-9, atol=1e-9), (i, bi, fi))
                        worst = max(worst, float(np.max(np.abs(g[bi, fi] - r))))
        self.assertLess(worst, 1e-9)
        # a whole year with the generic batteries of the storage sizing: the same, and the batch is one call
        prod, load = self.day_and_evening()
        p, c = prod.to_numpy(), load.to_numpy()
        batteries = [economics.Battery(k, k / 2, k / 2, 0.9) for k in (2.0, 5.5, 11.0)]
        k = economics._year_factors(0.4, 25)
        got = economics.dispatch_many(economics._surplus_years(p, c, k), batteries)
        for bi, b in enumerate(batteries):
            for fi in (0, 12, 24):
                ref = economics.dispatch(p * k[fi], c, b)
                for g, r in zip(got, ref, strict=True):
                    self.assertTrue(np.allclose(g[bi, fi], r, rtol=1e-9, atol=1e-9))
            self.assertTrue(np.allclose(got[2][bi, 0], economics.balance(prod, load, b).soc.to_numpy(), atol=1e-9))

    def test_the_sweeps_give_what_evaluating_each_case_gives(self):
        prod, load = self.day_and_evening()
        s = Settings.from_dict({"battery": BATTERY, "capex_total": 12000.0})
        sweep = economics.sizing(prod, load, 6.0, 5.0, s, factors=(0.5, 1.0, 2.0))
        for f, row in zip((0.5, 1.0, 2.0), sweep.itertuples(), strict=True):
            sf = Settings(**{**s.__dict__, "capex_total": s.capex_total * f})
            one = economics.evaluate(prod * f, load, 6.0 * f, 5.0 * f, sf)
            self.assertAlmostEqual(row.npv, one.kpi["npv"], places=6)
            self.assertAlmostEqual(row.self_sufficiency, one.kpi["self_sufficiency"], places=9)
        frame, _what = economics.storage_sizing(prod, load, 6.0, 5.0, s, factors=(0.0, 1.0))
        hb = economics.balance(prod, load, None)
        kwh = round(max(1.0, min(float(hb.export.sum()), float(hb.consumption.sum())) / 365.0), 1)
        generic = {"usable_energy_kwh": kwh, "max_charge_power_w": kwh * 500.0, "max_discharge_power_w": kwh * 500.0,
                   "round_trip_efficiency_pct": 90.0}
        one = economics.evaluate(prod, load, 6.0, 5.0, Settings(**{**s.__dict__, "battery": generic, "battery_units": 1,
                                                                   "capex_total": 12000.0 - 10.0 * 650.0 + kwh * 650.0}))
        self.assertAlmostEqual(frame.npv.iloc[1], one.kpi["npv"], places=6)
        self.assertAlmostEqual(frame.self_sufficiency.iloc[1], one.kpi["self_sufficiency"], places=9)

    def test_every_formula_can_be_drawn(self):
        from matplotlib.mathtext import MathTextParser
        parser = MathTextParser("path")
        prod, load = self.day_and_evening()
        r = economics.evaluate(prod, load, 6.0, 5.0, Settings.from_dict({"battery": BATTERY, "community": True,
                                                                        "export_limit_kw": 1.0}))
        for step in r.record.steps:
            if step.formula:
                parser.parse(f"${step.formula}$")
            for q in step.inputs + ([step.result] if step.result else []):
                if q.symbol:
                    parser.parse(f"${q.symbol}$")


if __name__ == "__main__":
    unittest.main()
