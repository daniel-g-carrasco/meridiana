"""The consumption side: ARERA's bands hour by hour (holidays, Easter, daylight saving time), the profiles
that keep the designer's kWh exactly, a measured curve moved onto the reference year with its weekdays,
and the CSV layouts of the distributors' portals."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

import _setup  # noqa: F401

from meridiana.energy import bands, consumption
from meridiana.energy.consumption import Consumption


def at(text: str) -> str:
    return bands.band_of(pd.DatetimeIndex([pd.Timestamp(text, tz="Europe/Rome")]))[0]


class Bands(unittest.TestCase):
    """The bands F1, F2, F3 and the holidays of ARERA's deliberation 181/06, Tab. 1, p. 1 (verified on the archive:
    B-norme-citazioni.md, section 3)."""

    def test_easter(self):
        self.assertEqual(bands.easter(2026), date(2026, 4, 5))
        self.assertEqual(bands.easter(2025), date(2025, 4, 20))
        self.assertEqual(bands.easter(2024), date(2024, 3, 31))

    def test_weekdays(self):
        # Wednesday 14 January 2026
        self.assertEqual(at("2026-01-14 06:00"), "F3")
        self.assertEqual(at("2026-01-14 07:00"), "F2")
        self.assertEqual(at("2026-01-14 08:00"), "F1")
        self.assertEqual(at("2026-01-14 18:00"), "F1")
        self.assertEqual(at("2026-01-14 19:00"), "F2")
        self.assertEqual(at("2026-01-14 22:00"), "F2")
        self.assertEqual(at("2026-01-14 23:00"), "F3")

    def test_saturday_and_sunday(self):
        self.assertEqual(at("2026-01-17 06:00"), "F3")     # Saturday night is in no other band
        self.assertEqual(at("2026-01-17 07:00"), "F2")
        self.assertEqual(at("2026-01-17 12:00"), "F2")
        self.assertEqual(at("2026-01-17 23:00"), "F3")
        self.assertEqual(at("2026-01-18 12:00"), "F3")     # Sunday

    def test_holidays_are_off_peak(self):
        self.assertEqual(at("2026-04-06 12:00"), "F3")     # Easter Monday
        self.assertEqual(at("2026-06-02 12:00"), "F3")
        self.assertEqual(at("2026-12-08 12:00"), "F3")
        self.assertEqual(at("2026-12-07 12:00"), "F1")

    def test_a_year_has_every_hour_once(self):
        idx = pd.date_range("2026-01-01", periods=8760, freq="h", tz="UTC").tz_convert("Europe/Rome")
        b = bands.band_of(idx)
        counts = {k: int((b == k).sum()) for k in bands.BANDS}
        self.assertEqual(sum(counts.values()), 8760)
        # 2026 has 261 days Monday to Friday; 7 holidays fall on them (1 and 6 January, Easter Monday, 1 May,
        # 2 June, 8 and 25 December): 254 days of 11 F1 hours
        self.assertEqual(counts["F1"], 254 * 11)


class Profiles(unittest.TestCase):
    def test_the_yearly_kwh_are_kept(self):
        load = consumption.build(Consumption(profile="office", annual_kwh=24000))
        self.assertAlmostEqual(load.annual_kwh, 24000, places=6)
        self.assertEqual(len(load.hourly), 8760)

    def test_the_bands_of_the_bill_are_kept(self):
        target = {"F1": 1000.0, "F2": 900.0, "F3": 1300.0}
        load = consumption.build(Consumption(profile="residential", bands_kwh=target))
        for k, v in load.by_band().items():
            self.assertAlmostEqual(v, target[k], places=6)

    def test_month_by_band_from_the_bills(self):
        bills = [{"F1": 100.0 + m, "F2": 80.0, "F3": 120.0} for m in range(12)]
        load = consumption.build(Consumption(profile="shop", monthly_bands_kwh=bills))
        b = bands.band_of(load.hourly.index)
        for m in range(12):
            month = load.hourly.index.month == m + 1
            self.assertAlmostEqual(float(load.hourly[month & (b == "F1")].sum()), 100.0 + m, places=6)
        self.assertAlmostEqual(load.annual_kwh, sum(sum(x.values()) for x in bills), places=6)

    def test_an_office_works_on_weekdays(self):
        load = consumption.build(Consumption(profile="office", annual_kwh=10000))
        h = load.hourly
        weekday_noon = h[(h.index.weekday == 2) & (h.index.hour == 11)].mean()
        sunday_noon = h[(h.index.weekday == 6) & (h.index.hour == 11)].mean()
        self.assertGreater(weekday_noon, 3 * sunday_noon)

    def test_the_pedigree_names_the_profile_as_synthetic(self):
        load = consumption.build(Consumption(profile="school", annual_kwh=5000))
        step = load.record.find("load")
        self.assertEqual(step.inputs[0].source.kind, "default")


class Audit(unittest.TestCase):
    def test_a_constant_load_has_its_base_at_its_peak(self):
        load = consumption.build(Consumption(profile="flat", annual_kwh=8760.0))
        f = load.figures()
        self.assertAlmostEqual(f["base_kw"], 1.0, places=6)
        self.assertAlmostEqual(f["load_factor"], 1.0, places=6)
        self.assertAlmostEqual(f["day_share"], 10 / 24, places=3)
        self.assertGreater(f["off_share"], 2 / 7)                     # weekends and the holidays
        self.assertEqual(len(load.week()), 168)

    def test_an_office_works_by_day_and_on_weekdays(self):
        load = consumption.build(Consumption(profile="office", annual_kwh=30000.0))
        f = load.figures()
        self.assertGreater(f["day_share"], 0.6)
        self.assertLess(f["off_share"], 0.25)
        week = load.week()
        self.assertGreater(week[2 * 24 + 11], 3 * week[6 * 24 + 11])     # Wednesday 11:00 against Sunday
        curve = load.duration()
        self.assertTrue((curve[:-1] >= curve[1:]).all())
        self.assertAlmostEqual(float(curve.sum()), 30000.0, places=3)


class Context(unittest.TestCase):
    def test_a_small_system_is_a_home(self):
        # 3 kW and 2.700 kWh a year: ARERA's typical household (consumption.py), not yet checked on a document of
        # the archive (B-norme-citazioni.md, section 3, marked [?]): a value to verify in the local session
        g = consumption.guess(consumption.Context(p_stc_kw=4.5))
        self.assertEqual((g.profile, g.supply, g.contract_kw, g.annual_kwh), ("residential", "domestic", 3.0, 2700.0))
        load = consumption.build(Consumption(), consumption.Context(p_stc_kw=4.5))
        self.assertAlmostEqual(load.annual_kwh, 2700.0, places=6)

    def test_a_larger_one_a_business_consuming_its_production(self):
        before = consumption.guess(consumption.Context(p_stc_kw=55.8))
        self.assertEqual((before.profile, before.supply), ("industry_1", "other_lv"))
        self.assertAlmostEqual(before.annual_kwh, 55.8 * consumption.YIELD_GUESS, delta=50)
        after = consumption.guess(consumption.Context(p_stc_kw=55.8, production_kwh=75585.0))
        self.assertEqual(after.annual_kwh, 75600.0)
        # above 100 kW the supply is in medium voltage: CEI 0-21:2026-07 6.3 Tab. 5 p. 33
        self.assertEqual(consumption.guess(consumption.Context(p_stc_kw=150.0)).supply, "mv")
        load = consumption.build(Consumption(), consumption.Context(p_stc_kw=55.8, production_kwh=75585.0))
        self.assertAlmostEqual(load.annual_kwh, 75600.0, places=6)
        step = load.record.find("load")
        self.assertIn("context", step.inputs[0].source.label)
        self.assertEqual(step.result.source.kind, "default")

    def test_what_the_designer_gives_wins(self):
        ctx = consumption.Context(p_stc_kw=55.8, production_kwh=75585.0)
        c = Consumption(profile="office", annual_kwh=30000)
        self.assertFalse(c.follows_production(ctx))
        load = consumption.build(c, ctx)
        self.assertAlmostEqual(load.annual_kwh, 30000.0, places=6)
        self.assertNotIn("context", load.record.find("load").inputs[0].source.label)
        self.assertTrue(Consumption().follows_production(ctx))
        self.assertFalse(Consumption().follows_production(consumption.Context(p_stc_kw=3.0)))


class Measured(unittest.TestCase):
    def test_a_measured_year_keeps_its_weekdays(self):
        # 2025: busy on weekdays, idle at weekends
        idx = pd.date_range("2025-01-01", periods=8760, freq="h", tz="Europe/Rome")
        values = np.where(idx.weekday < 5, 2.0, 0.5)
        load = consumption.build(Consumption(measured=[[t.isoformat(), float(v)] for t, v in zip(idx, values, strict=True)]))
        h = load.hourly
        self.assertAlmostEqual(float(h[h.index.weekday < 5].mean()), 2.0, delta=0.05)
        self.assertAlmostEqual(float(h[h.index.weekday >= 5].mean()), 0.5, delta=0.05)

    def test_a_portal_csv_with_96_quarters_a_day(self):
        days = pd.date_range("2025-03-01", periods=3, freq="D")
        header = ["Data"] + [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)]
        lines = [";".join(header)] + [";".join([d.strftime("%d/%m/%Y")] + ["0,25"] * 96) for d in days]
        path = Path(tempfile.mkdtemp()) / "curva.csv"
        path.write_text("\n".join(lines), encoding="utf-8")
        rows = consumption.read_curve(path)
        self.assertEqual(len(rows), 3 * 96)
        self.assertAlmostEqual(sum(v for _t, v in rows), 3 * 24.0)

    def test_a_csv_of_timestamps_and_kw(self):
        times = pd.date_range("2025-03-01", periods=8, freq="15min")
        lines = ["data ora;potenza kW"] + [f"{t.strftime('%d/%m/%Y %H:%M')};4,0" for t in times]
        path = Path(tempfile.mkdtemp()) / "curva.csv"
        path.write_text("\n".join(lines), encoding="utf-8")
        rows = consumption.read_curve(path, unit="kW")
        self.assertAlmostEqual(sum(v for _t, v in rows), 8 * 1.0)      # 4 kW for a quarter of an hour

    def test_pod(self):
        self.assertTrue(consumption.valid_pod("IT001E12345678"))
        self.assertTrue(consumption.valid_pod("it 001 e 12345678"))
        self.assertFalse(consumption.valid_pod("IT001E123"))


if __name__ == "__main__":
    unittest.main()
