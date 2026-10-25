"""Study 18, part B.5: the balance, the battery, the money, the bands and the load profiles of
src/meridiana/energy (economics.py, bands.py, consumption.py) against cases done by hand.

A. economics.dispatch on one day of 24 hours with a small battery (5 kWh usable, 2 kW in and out, 81 %
   round trip, so 90 % each way): every hour's charge, discharge and state of charge written out by hand
   from the rule the docstring states, the limits, and the energy balance over the day.
B. economics.balance with an export limit: what the grid may not take is curtailed, nothing else moves.
C. economics.evaluate on a year whose balance is known in closed form (a constant load of 1 kWh/h, 2 kWh/h
   of production from 10 to 16): the cash flows, the net present value, the internal rate, the simple and
   discounted payback and the LCOE recomputed here from their definitions:
   VAN = sum over y = 0..N of F_y / (1 + r)^y with F_0 = -I_0 (the discounted cash flow of corporate
   finance, e.g. Brealey, Myers, Allen, Principles of Corporate Finance, ch. 2); TIR: the r for which
   VAN = 0; payback: the first year in which the cumulative flow is no longer negative, interpolated within
   the year; LCOE = (I_0 + sum of discounted running costs) / sum of discounted energy.
D. bands.band_of against the bands of ARERA's resolution 181/06, Table 1 (read in the local archive,
   reference/laws, "fasce orarie con decorrenza 1 gennaio 2007"): F1 Monday to Friday 8-19; F2 Monday to
   Friday 7-8 and 19-23, Saturday 7-23; F3 Monday to Friday 23-7, Sundays and holidays all day; holidays
   1 and 6 January, Easter Monday, 25 April, 1 May, 2 June, 15 August, 1 November, 8, 25 and 26 December.
   Written again here from that text and compared hour by hour on 2024-2027, daylight saving included.
E. consumption.py: where the profiles come from (the module's own words), and whether they are plausible:
   the yearly sum kept, the shares by band, the daily shape, the weekend, the seasons, the load factor.

The results go to economia_a_mano-risultati.txt beside this script. Run from the repository root:
    PYTHONPATH=src QT_QPA_PLATFORM=offscreen python docs/studio/18-prove/economia_a_mano.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))

from meridiana.energy import bands, consumption, economics  # noqa: E402
from meridiana.energy.consumption import Consumption  # noqa: E402
from meridiana.energy.economics import Battery, Settings  # noqa: E402

OUT = HERE / "economia_a_mano-risultati.txt"
TZ = "Europe/Rome"
LINES: list[str] = []


def say(text: str = "") -> None:
    print(text)
    LINES.append(text)


def ok(flag: bool) -> str:
    return "OK" if flag else "DIVERSO"


# ---- the bands, written again from ARERA 181/06 Table 1

def easter_sunday(year: int) -> date:
    """Gregorian Easter by the Meeus/Jones/Butcher algorithm (Astronomical Algorithms, ch. 8)."""
    a = year % 19
    b, c = year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    day = (h + l_ - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def is_holiday(d: date) -> bool:
    fixed = {(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)}
    return (d.month, d.day) in fixed or d == easter_sunday(d.year) + timedelta(days=1)


def band_by_hand(ts: pd.Timestamp) -> str:
    """The band of the hour starting at the local time ts, from the text of Table 1."""
    d, hour, wd = ts.date(), ts.hour, ts.weekday()
    if wd == 6 or is_holiday(d):
        return "F3"
    if wd <= 4:
        if 8 <= hour < 19:
            return "F1"
        if 7 <= hour < 8 or 19 <= hour < 23:
            return "F2"
        return "F3"
    return "F2" if 7 <= hour < 23 else "F3"           # Saturday


def main() -> None:
    # ---- A. the battery on one day
    say("A. economics.dispatch: un giorno di 24 ore, batteria 5 kWh utili, 2 kW in carica e scarica, 81 % andata e ritorno")
    prod = np.array([0.0] * 8 + [3.0, 4.0, 4.0, 4.0, 4.0, 4.0, 3.0, 2.0] + [0.0] * 8)
    cons = np.ones(24)
    b = Battery(usable_kwh=5.0, charge_kw=2.0, discharge_kw=2.0, efficiency=0.81, name="prova")
    eta = 0.9                                           # each way: sqrt(0.81)
    stored, given, soc = economics.dispatch(prod, cons, b)
    # by hand, hour by hour: surplus 2,3,3,3,3,3,2,1 from 8 to 15, shortfall 1 from 16 to 23
    exp_stored = np.zeros(24)
    exp_given = np.zeros(24)
    exp_soc = np.zeros(24)
    level = 0.0
    for h in range(24):
        x = prod[h] - cons[h]
        if x > 0:
            c = min(x, 2.0, (5.0 - level) / eta)
            exp_stored[h] = c
            level += c * eta
        elif x < 0:
            g = min(-x, 2.0, level * eta)
            exp_given[h] = g
            level -= g / eta
        exp_soc[h] = level
    say("   ora  prod  cons  carica  scarica  SOC    (a mano: carica, scarica, SOC)")
    for h in range(24):
        say(f"   {h:3d}  {prod[h]:4.1f}  {cons[h]:4.1f}  {stored[h]:6.3f}  {given[h]:7.3f}  {soc[h]:5.3f}    "
            f"{exp_stored[h]:6.3f} {exp_given[h]:7.3f} {exp_soc[h]:6.3f}")
    literal = {"stored_8": 2.0, "stored_9": 2.0, "stored_10": (5.0 - 3.6) / 0.9, "soc_10": 5.0, "given_16": 1.0,
               "soc_16": 5.0 - 1.0 / 0.9, "given_20": 0.5, "soc_20": 0.0}
    checks = [stored[8] == literal["stored_8"], stored[9] == literal["stored_9"],
              abs(stored[10] - literal["stored_10"]) < 1e-12, abs(soc[10] - 5.0) < 1e-12, given[16] == 1.0,
              abs(soc[16] - literal["soc_16"]) < 1e-12, abs(given[20] - 0.5) < 1e-12, abs(soc[20]) < 1e-12]
    say(f"   valori letterali attesi: carica ore 8-10 = 2, 2, {literal['stored_10']:.4f}; SOC ora 10 = 5; scarica ora 16 = 1; "
        f"SOC ora 16 = {literal['soc_16']:.4f}; scarica ora 20 = 0,5; SOC ora 20 = 0: {ok(all(checks))}")
    say(f"   confronto ora per ora con il calcolo a mano: {ok(np.allclose(stored, exp_stored) and np.allclose(given, exp_given) and np.allclose(soc, exp_soc))}")
    say(f"   limiti: carica max {stored.max():.3f} <= 2, scarica max {given.max():.3f} <= 2, SOC max {soc.max():.3f} <= 5: "
        f"{ok(stored.max() <= 2 and given.max() <= 2 and soc.max() <= 5 + 1e-12)}")
    say(f"   bilancio: data {given.sum():.4f} = 0,81 x caricata {stored.sum():.4f} - 0,9 x SOC finale {soc[-1]:.4f} = "
        f"{0.81 * stored.sum() - 0.9 * soc[-1]:.4f}: {ok(abs(given.sum() - (0.81 * stored.sum() - 0.9 * soc[-1])) < 1e-9)}")
    say("   nota: il passo e' l'ora e i kW valgono come kWh (nessun passo diverso e' previsto); la batteria parte vuota, non si carica "
        "dalla rete, nessuna autoscarica, nessun limite di SOC oltre l'energia utile (lo dice la pedigree)")
    say()

    # ---- B. the balance with an export limit
    say("B. economics.balance con un limite di immissione di 1 kW (mercoledi 14/01/2026, ore locali)")
    idx = pd.date_range("2026-01-14 00:00", periods=24, freq="h", tz=TZ)
    hb = economics.balance(pd.Series(prod, index=idx), pd.Series(cons, index=idx), b, export_limit_kw=1.0)
    raw_export = prod - np.minimum(prod, cons) - stored
    exp_curt = np.clip(raw_export - 1.0, 0.0, None)
    say(f"   immissione max {hb.export.max():.3f} <= 1: {ok(hb.export.max() <= 1.0 + 1e-12)}; tagliata {hb.curtailed.sum():.3f} kWh "
        f"(a mano {exp_curt.sum():.3f}): {ok(np.allclose(hb.curtailed, exp_curt))}")
    say(f"   produzione = diretta + accumulata + immessa + tagliata: {ok(np.allclose(hb.production, hb.direct + hb.stored + hb.export + hb.curtailed))}; "
        f"consumo = diretta + dalla batteria + prelevata: {ok(np.allclose(hb.consumption, hb.direct + hb.given + hb['import']))}")
    say(f"   fasce del giorno: {''.join(x[1] for x in hb.band)} (F3 fino alle 7, F2 7-8, F1 8-19, F2 19-23, F3 23)")
    say()

    # ---- C. the money on a year known in closed form
    say("C. economics.evaluate contro VAN, TIR, tempo di ritorno e LCOE ricalcolati dalla definizione")
    year = pd.date_range("2026-01-01 00:00", periods=8760, freq="h", tz="UTC").tz_convert(TZ)
    production = pd.Series(np.where((year.hour >= 10) & (year.hour < 16), 2.0, 0.0), index=year)
    load = pd.Series(np.ones(8760), index=year)
    s = Settings.from_dict({"buy_f1": 0.30, "buy_f2": 0.25, "buy_f3": 0.20, "sell": 0.10, "capex_per_kwp": 1300.0,
                            "opex_per_kwp": 20.0, "inverter_year": 12, "inverter_per_kw": 150.0, "years": 25,
                            "discount": 4.0, "escalation": 2.0, "opex_escalation": 2.0, "degradation": 0.5,
                            "deduction_pct": 50.0})
    p_stc, p_ac = 6.0, 5.0
    r = economics.evaluate(production, load, p_stc, p_ac, s)
    hand_band = np.array([band_by_hand(t) for t in year])
    sun_hours = (year.hour >= 10) & (year.hour < 16)
    n_band = {k: int((hand_band[sun_hours] == k).sum()) for k in ("F1", "F2", "F3")}
    prices = {"F1": 0.30, "F2": 0.25, "F3": 0.20}
    say(f"   ore 10-16 dell'anno per fascia (a mano): {n_band}; autoconsumo 1 kWh in ognuna; immissione (2k - 1) kWh in ognuna")
    capex = 1300.0 * p_stc
    flows = [-capex]
    rows = []
    for y in range(1, 26):
        k = (1 - 0.005) ** (y - 1)
        esc = 1.02 ** (y - 1)
        self_kwh = sum(n_band.values())                                  # 1 kWh in every hour of sun, 2k >= 1
        saving = sum(n_band[b_] * prices[b_] for b_ in n_band) * esc
        export = (2.0 * k - 1.0) * self_kwh
        sale = export * 0.10 * esc
        opex = 20.0 * p_stc * 1.02 ** (y - 1)
        repl = 150.0 * p_ac if y == 12 else 0.0
        ded = capex * 0.50 / 10.0 if y <= 10 else 0.0
        flow = saving + sale + ded - opex - repl
        flows.append(flow)
        rows.append((y, self_kwh, export, saving, sale, opex, repl, ded, flow))
    flows = np.array(flows)
    disc = flows / 1.04 ** np.arange(26)
    npv = disc.sum()

    def npv_at(rate: float) -> float:
        return float((flows / (1 + rate) ** np.arange(26)).sum())

    lo, hi = 0.0, 1.0
    for _ in range(200):                                                 # bisection for the rate: VAN(TIR) = 0
        mid = (lo + hi) / 2
        if npv_at(mid) > 0:
            lo = mid
        else:
            hi = mid
    irr = (lo + hi) / 2

    def payback(cum: np.ndarray) -> float | None:
        for y in range(1, len(cum)):
            if cum[y] >= 0 > cum[y - 1]:
                return y - 1 + (-cum[y - 1]) / (cum[y] - cum[y - 1])
        return None

    pb, pbd = payback(np.cumsum(flows)), payback(np.cumsum(disc))
    _years = np.arange(1, 26)
    lcoe = (capex + sum((row[5] + row[6]) / 1.04 ** row[0] for row in rows)) / sum(
        (2.0 * sum(n_band.values()) * (1 - 0.005) ** (row[0] - 1)) / 1.04 ** row[0] for row in rows)
    k = r.kpi
    say(f"   investimento {capex:.0f} €; anno 1: risparmio {rows[0][3]:.2f} € (evaluate {r.years.saving.iloc[0]:.2f}), vendita {rows[0][4]:.2f} € "
        f"(evaluate {r.years.sale.iloc[0]:.2f}), detrazione {rows[0][7]:.2f} (evaluate {r.years.deduction.iloc[0]:.2f}), "
        f"gestione {rows[0][5]:.2f} (evaluate {r.years.opex.iloc[0]:.2f})")
    say(f"   anno 12: sostituzione inverter {rows[11][6]:.2f} (evaluate {r.years.replacement.iloc[11]:.2f}); anno 25: flusso {rows[24][8]:.2f} "
        f"(evaluate {r.years.flow.iloc[24]:.2f}), produzione {2.0 * sum(n_band.values()) * 0.995 ** 24:.1f} kWh (evaluate {r.years.production.iloc[24]:.1f})")
    say(f"   flussi dei 25 anni uguali: {ok(np.allclose(r.years.flow.to_numpy(), flows[1:]))}; cumulato: "
        f"{ok(np.allclose(r.years.cumulative.to_numpy(), np.cumsum(flows)[1:]))}")
    say(f"   VAN: a mano {npv:.2f} €, evaluate {k['npv']:.2f} €: {ok(abs(npv - k['npv']) < 1e-6)}")
    say(f"   TIR: a mano {100 * irr:.4f} %, evaluate {100 * k['irr']:.4f} %; VAN al TIR di evaluate {npv_at(k['irr']):+.6f} €: {ok(abs(irr - k['irr']) < 1e-6)}")
    say(f"   tempo di ritorno semplice: a mano {pb:.4f} anni, evaluate {k['payback']:.4f}: {ok(abs(pb - k['payback']) < 1e-9)}; "
        f"attualizzato: a mano {pbd:.4f}, evaluate {k['payback_discounted']:.4f}: {ok(abs(pbd - k['payback_discounted']) < 1e-9)}")
    say(f"   LCOE: a mano {lcoe:.5f} €/kWh, evaluate {k['lcoe']:.5f}: {ok(abs(lcoe - k['lcoe']) < 1e-9)} "
        f"(costi di gestione e sostituzione attualizzati, senza detrazione ne' incentivi; l'energia e' quella prodotta, non quella venduta)")
    say(f"   bolletta prima {k['bill_before']:.2f} €, dopo {k['bill_after']:.2f} €, risparmio anno 1 {k['saving_1']:.2f}: "
        f"prima - dopo = {k['bill_before'] - k['bill_after']:.2f}: {ok(abs(k['bill_before'] - k['bill_after'] - k['saving_1']) < 1e-6)}")
    say(f"   kpi: autoconsumo {k['self']:.0f} kWh = {sum(n_band.values())}: {ok(abs(k['self'] - sum(n_band.values())) < 1e-6)}; "
        f"immissione {k['export']:.0f} = {sum(n_band.values())}: {ok(abs(k['export'] - sum(n_band.values())) < 1e-6)}; "
        f"quota autoconsumata {100 * k['self_ratio']:.1f} %, autosufficienza {100 * k['self_sufficiency']:.1f} %")
    # payback edge cases
    say(f"   _payback: mai positivo -> {economics._payback(np.array([-10.0, -5.0, -1.0]))}; senza investimento -> "
        f"{economics._payback(np.array([0.0, 1.0]))}; esattamente a fine anno 2 -> {economics._payback(np.array([-10.0, -5.0, 0.0]))}")
    say(f"   irr: flussi -100, +250 (TIR 150 %) -> {economics.irr(np.array([-100.0, 250.0]))} (brentq cerca solo fra -99 % e 100 %)")
    say()

    # ---- D. the bands
    say("D. bands.band_of contro la Tabella 1 della delibera ARERA 181/06 riscritta qui dal testo")
    for y, known in ((2024, date(2024, 3, 31)), (2025, date(2025, 4, 20)), (2026, date(2026, 4, 5)), (2027, date(2027, 3, 28))):
        say(f"   Pasqua {y}: bands.easter {bands.easter(y)}, a mano {easter_sunday(y)}, nota {known}: "
            f"{ok(bands.easter(y) == easter_sunday(y) == known)}")
    total_diff = 0
    for y in (2024, 2025, 2026, 2027):
        idx_y = pd.date_range(f"{y}-01-01 00:00", f"{y}-12-31 23:00", freq="h", tz=TZ)
        got = bands.band_of(idx_y)
        hand = np.array([band_by_hand(t) for t in idx_y])
        diff = int((got != hand).sum())
        total_diff += diff
        counts = {k_: int((got == k_).sum()) for k_ in bands.BANDS}
        say(f"   {y}: {len(idx_y)} ore locali (ora legale compresa), ore diverse {diff}, conteggio {counts}")
    say(f"   ore diverse in tutto: {total_diff}: {ok(total_diff == 0)}")
    for text, want in (("2026-01-14 06:00", "F3"), ("2026-01-14 07:00", "F2"), ("2026-01-14 08:00", "F1"), ("2026-01-14 18:00", "F1"),
                       ("2026-01-14 19:00", "F2"), ("2026-01-14 22:00", "F2"), ("2026-01-14 23:00", "F3"),
                       ("2026-01-17 06:00", "F3"), ("2026-01-17 07:00", "F2"), ("2026-01-17 22:00", "F2"), ("2026-01-17 23:00", "F3"),
                       ("2026-01-18 12:00", "F3"), ("2026-04-06 12:00", "F3"), ("2026-04-25 12:00", "F3"), ("2026-12-26 12:00", "F3"),
                       ("2026-03-29 03:00", "F3")):
        got = bands.band_of(pd.DatetimeIndex([pd.Timestamp(text, tz=TZ)]))[0]
        say(f"   {text} -> {got} (atteso {want}): {ok(got == want)}")
    # the doubled hour of the end of summer time (Sunday 25/10/2026, 02:00 CEST then 02:00 CET), built from UTC
    for utc_text in ("2026-10-25 00:30", "2026-10-25 01:30"):
        ts = pd.Timestamp(utc_text, tz="UTC").tz_convert(TZ)
        got = bands.band_of(pd.DatetimeIndex([ts]))[0]
        say(f"   {ts.isoformat()} (ora doppia di fine ora legale) -> {got} (atteso F3, domenica): {ok(got == 'F3')}")
    monday = pd.date_range("2026-10-26 00:00", periods=24, freq="h", tz=TZ)
    say(f"   lunedi 26/10/2026, il giorno dopo: {''.join(x[1] for x in bands.band_of(monday))}")
    naive = bands.band_of(pd.DatetimeIndex([pd.Timestamp("2026-07-15 12:00")]))[0]
    utc = bands.band_of(pd.DatetimeIndex([pd.Timestamp("2026-07-15 12:00", tz="UTC")]))[0]
    say(f"   indice senza fuso: 15/07 12:00 -> {naive} (letto come ora locale); in UTC -> {utc} (12 UTC = 14 locali, F1)")
    say()

    # ---- E. the profiles
    say("E. consumption.py: i profili")
    say("   origine: il modulo dice che sono «Meridiana's own synthetic shapes ... not measured curves» (docstring, righe 6-7) e la "
        "pedigree li marca come default sintetici; nessuna fonte esterna (ARERA, GSE, distributori) e' citata")
    say("   profilo           kWh/anno  F1 %  F2 %  F3 %  picco h  min/picco  sab/fer  dom/fer  mese max/min  fattore di carico  ore 8-18 %  media forma")
    for name in consumption.PROFILES:
        c = Consumption(profile=name, annual_kwh=consumption.STARTING_KWH[name])
        load_ = consumption.build(c)
        h = load_.hourly
        by = load_.by_band()
        tot = load_.annual_kwh
        wd = h[(h.index.weekday <= 4)].groupby(h[(h.index.weekday <= 4)].index.hour).mean()
        sat = h[h.index.weekday == 5].mean() / h[h.index.weekday <= 4].mean()
        sun_ = h[h.index.weekday == 6].mean() / h[h.index.weekday <= 4].mean()
        months = h.groupby(h.index.month).mean()
        f = load_.figures()
        shape_mean = float(consumption.shape(name).mean())
        say(f"   {name:16} {tot:9.0f}  {100 * by['F1'] / tot:4.0f}  {100 * by['F2'] / tot:4.0f}  {100 * by['F3'] / tot:4.0f}  "
            f"{int(wd.idxmax()):6d}   {wd.min() / wd.max():8.2f}  {sat:7.2f}  {sun_:7.2f}  {months.max() / months.min():12.2f}  "
            f"{f['load_factor']:17.2f}  {100 * f['day_share']:9.0f}  {shape_mean:10.2f}")
    g_small = consumption.guess(consumption.Context(p_stc_kw=4.5))
    g_big = consumption.guess(consumption.Context(p_stc_kw=55.8))
    g_big2 = consumption.guess(consumption.Context(p_stc_kw=55.8, production_kwh=75585.0))
    say(f"   guess(4,5 kWp): {g_small.profile}, {g_small.supply}, {g_small.contract_kw} kW, {g_small.annual_kwh} kWh")
    say(f"   guess(55,8 kWp): {g_big.profile}, {g_big.supply}, {g_big.contract_kw} kW, {g_big.annual_kwh} kWh (1200 kWh/kWp); con la produzione nota: {g_big2.annual_kwh} kWh")
    say("   lettura: le forme sono plausibili nel verso (casa serale, ufficio e scuola diurni e feriali, industria a turni, albergo estivo), "
        "ma i pesi sono inventati: nessun confronto con curve misurate o con i profili convenzionali di prelievo; «its mean is about 1» "
        "(docstring di shape) non e' vero per i profili residenziali e d'ufficio, senza effetto perche' si riscalano sempre")
    OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print(f"\nscritto {OUT}")


if __name__ == "__main__":
    main()
