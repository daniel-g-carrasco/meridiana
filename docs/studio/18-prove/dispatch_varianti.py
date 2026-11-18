"""The decisive proof for register R31: `economics.dispatch` (the battery charged with the surplus and
discharged on the consumption, hour by hour, 8,760 hours) written in five ways, checked against each other and
timed. Nothing here enters the program: it is a measurement for Daniel's decision.

The variants:
(a) `dispatch_reference`: the function of `src/meridiana/energy/economics.py` copied as it is (pure Python loop);
(b) `dispatch_batched`: the same recurrence with a two-dimensional state, every (battery size, year) at once, one
    Python loop over the hours with numpy on the state vector. It stands in for the 156 calls of the storage
    sizing (6 battery sizes times 26 calls: the first-year balance and the 25 years of the cash flow);
(c) `dispatch_scan`: no Python loop over the hours. The recurrence is L_h = clip(L_{h-1} + d_h, 0, E): a sum with
    saturation at both ends, which a plain cumulative sum cannot give. But the maps x -> clip(x + d, lo, hi) are
    closed under composition, (d1, lo1, hi1) then (d2, lo2, hi2) = (d1 + d2, clip(lo1 + d2, lo2, hi2),
    clip(hi1 + d2, lo2, hi2)), and the composition is associative: a parallel prefix (Hillis and Steele 1986,
    log2(8760) = 14 doubling passes of numpy) gives every prefix map, applied to the empty battery;
(d) `dispatch_numba`: the reference loop under numba's @njit (only where numba is installed: the separate venv);
(e) `dispatch_rs.dispatch`: the same loop in Rust (the crate in dispatch_rs/, built with maturin in the WSL).

Why 156 calls: `economics.storage_sizing` evaluates 7 battery sizes (factors 0 to 2 of the daily energy that can be
shifted); each `evaluate` runs `balance` (one dispatch, the first year) and then 25 years of the cash flow, each with
its own dispatch on the degraded production. The size 0 has no battery: 6 x 26 = 156. The first-year balance and
the year 1 of the loop are the same computation (the degradation factor is 1): 150 distinct results.

Usage (from the repository root, any of the three interpreters):
    python docs/studio/18-prove/dispatch_varianti.py check            # every variant against the reference
    python docs/studio/18-prove/dispatch_varianti.py bench [--repeats 5] [--data file.npz]
The data are a synthetic but plausible year (seed 7): production of a 90 kWp system on a clear-sky shape with
clouds, a weekday load with a daytime plateau; `--data` loads `prod` and `cons` saved from a real project.
"""

from __future__ import annotations

import argparse
import os
import platform
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from carico import CpuMeter, describe  # noqa: E402

os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(os.environ.get("TEMP") or "/tmp") / "numba-cache-dispatch"))

HOURS = 8760
STORAGE_FACTORS = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0)      # economics.STORAGE_FACTORS without the 0
YEARS = 25
DEGRADATION = 0.4                                       # %/year, economics' default


@dataclass
class Battery:
    """economics.Battery, the fields dispatch reads."""
    usable_kwh: float
    charge_kw: float
    discharge_kw: float
    efficiency: float               # round trip, 0-1
    name: str = ""


# (a) the reference: src/meridiana/energy/economics.py, dispatch, copied verbatim (23/10/2026)

def dispatch_reference(prod: np.ndarray, cons: np.ndarray, b: Battery) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Charge with the surplus, discharge on the consumption, hour by hour, within the battery's energy and
    power; the round-trip efficiency is split half on the way in and half on the way out. The energy
    stored (kWh into the battery from the system) and given (kWh to the loads) of each hour, and the
    state of charge at the end of it."""
    eta = b.efficiency ** 0.5
    stored = np.zeros_like(prod)
    given = np.zeros_like(prod)
    soc = np.zeros_like(prod)
    level = 0.0
    surplus = prod - cons
    for h in range(len(prod)):
        x = surplus[h]
        if x > 0:
            room = (b.usable_kwh - level) / eta
            c = min(x, b.charge_kw, room)
            stored[h] = c
            level += c * eta
        elif x < 0:
            d = min(-x, b.discharge_kw, level * eta)
            given[h] = d
            level -= d / eta
        soc[h] = level
    return stored, given, soc


# the recurrence as a clamped sum: the step of each hour before the clamp

def _steps(surplus: np.ndarray, eta, charge_kw, discharge_kw) -> np.ndarray:
    """d_h: what the hour would add to the level (eta times the surplus within the charge power) or take from it
    (the shortfall within the discharge power, over eta); the clamp to [0, E] does the rest."""
    return np.where(surplus > 0, eta * np.minimum(surplus, charge_kw),
                    np.where(surplus < 0, -np.minimum(-surplus, discharge_kw) / eta, 0.0))


def _from_levels(surplus: np.ndarray, soc: np.ndarray, eta) -> tuple[np.ndarray, np.ndarray]:
    """stored and given from the levels: what went in is the rise over eta, what came out the fall times eta."""
    prev = np.concatenate([np.zeros_like(soc[..., :1]), soc[..., :-1]], axis=-1)
    delta = soc - prev
    stored = np.where(surplus > 0, delta / eta, 0.0)
    given = np.where(surplus < 0, -delta * eta, 0.0)
    return stored, given


# (b) the algorithmic variant: one pass over the hours for every (battery, year) at once

def dispatch_batched(prod: np.ndarray, cons: np.ndarray, batteries: list[Battery], factors: np.ndarray
                     ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Every battery against the production scaled by every factor (the years' degradation), in one loop over the
    hours with the state as a vector: arrays (batteries, factors, hours) of stored, given and soc."""
    factors = np.asarray(factors, dtype=float)
    nb, nf = len(batteries), len(factors)
    surplus = (factors[None, :, None] * prod[None, None, :] - cons[None, None, :])           # (1, F, H)
    surplus = np.broadcast_to(surplus, (nb, nf, len(prod))).reshape(nb * nf, -1)
    eta = np.repeat(np.array([b.efficiency ** 0.5 for b in batteries]), nf)[:, None]
    cap = np.repeat(np.array([b.usable_kwh for b in batteries]), nf)
    charge = np.repeat(np.array([b.charge_kw for b in batteries]), nf)[:, None]
    discharge = np.repeat(np.array([b.discharge_kw for b in batteries]), nf)[:, None]
    steps = np.ascontiguousarray(_steps(surplus, eta, charge, discharge).T)                   # (H, C)
    n_hours, n_combo = steps.shape
    soc_t = np.empty((n_hours, n_combo))
    level = np.zeros(n_combo)
    zero = np.zeros(n_combo)
    for h in range(n_hours):
        np.add(level, steps[h], out=level)
        np.maximum(level, zero, out=level)
        np.minimum(level, cap, out=level)
        soc_t[h] = level
    soc = np.ascontiguousarray(soc_t.T)
    stored, given = _from_levels(surplus, soc, eta)
    shape = (nb, nf, n_hours)
    return stored.reshape(shape), given.reshape(shape), soc.reshape(shape)


# (c) the numpy variant without a Python loop over the hours: a parallel prefix of clamp-add maps

def _prefix_clamp_add(d: np.ndarray, lo: float, hi) -> np.ndarray:
    """L_h = clip(L_{h-1} + d_h, lo, hi) from L_0 = lo, along the last axis, without a loop over h: each hour is
    the map x -> clip(x + d_h, lo, hi); their compositions are maps of the same kind, and a doubling scan composes
    every prefix in ceil(log2(n)) passes. `hi` may be an array over the leading axes (one capacity per row)."""
    D = np.array(d, dtype=float, copy=True)
    LO = np.full_like(D, lo)
    HI = np.empty_like(D)
    HI[...] = np.asarray(hi, dtype=float)[..., None] if np.ndim(hi) else hi
    n = D.shape[-1]
    k = 1
    while k < n:
        # F_h := F_h o F_{h-k}: the later map (g) applied after the earlier one (f)
        Df, LOf, HIf = D[..., :-k], LO[..., :-k], HI[..., :-k]
        Dg, LOg, HIg = D[..., k:], LO[..., k:], HI[..., k:]
        new_d = Df + Dg
        new_lo = np.clip(LOf + Dg, LOg, HIg)
        new_hi = np.clip(HIf + Dg, LOg, HIg)
        D[..., k:], LO[..., k:], HI[..., k:] = new_d, new_lo, new_hi
        k *= 2
    return np.clip(lo + D, LO, HI)


def dispatch_scan(prod: np.ndarray, cons: np.ndarray, b: Battery) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """dispatch without a Python loop: the levels by the prefix scan, stored and given from their changes."""
    eta = b.efficiency ** 0.5
    surplus = prod - cons
    soc = _prefix_clamp_add(_steps(surplus, eta, b.charge_kw, b.discharge_kw), 0.0, b.usable_kwh)
    stored, given = _from_levels(surplus, soc, eta)
    return stored, given, soc


def dispatch_scan_batched(prod: np.ndarray, cons: np.ndarray, batteries: list[Battery], factors: np.ndarray
                          ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The scan on the two-dimensional state: every (battery, year) in the same 14 passes."""
    factors = np.asarray(factors, dtype=float)
    nb, nf = len(batteries), len(factors)
    surplus = np.broadcast_to(factors[None, :, None] * prod[None, None, :] - cons[None, None, :],
                              (nb, nf, len(prod))).reshape(nb * nf, -1)
    eta = np.repeat(np.array([b.efficiency ** 0.5 for b in batteries]), nf)[:, None]
    cap = np.repeat(np.array([b.usable_kwh for b in batteries]), nf)
    charge = np.repeat(np.array([b.charge_kw for b in batteries]), nf)[:, None]
    discharge = np.repeat(np.array([b.discharge_kw for b in batteries]), nf)[:, None]
    soc = _prefix_clamp_add(_steps(surplus, eta, charge, discharge), 0.0, cap)
    stored, given = _from_levels(surplus, soc, eta)
    shape = (nb, nf, len(prod))
    return stored.reshape(shape), given.reshape(shape), soc.reshape(shape)


# (d) numba, where it is installed

def _kernel(prod, cons, usable_kwh, charge_kw, discharge_kw, efficiency):
    eta = efficiency ** 0.5
    n = prod.shape[0]
    stored = np.zeros(n)
    given = np.zeros(n)
    soc = np.zeros(n)
    level = 0.0
    for h in range(n):
        x = prod[h] - cons[h]
        if x > 0.0:
            room = (usable_kwh - level) / eta
            c = min(x, charge_kw, room)
            stored[h] = c
            level += c * eta
        elif x < 0.0:
            d = min(-x, discharge_kw, level * eta)
            given[h] = d
            level -= d / eta
        soc[h] = level
    return stored, given, soc


try:
    import numba
    _numba_kernel = numba.njit(cache=os.environ.get("DISPATCH_NUMBA_CACHE") == "1")(_kernel)

    def dispatch_numba(prod, cons, b: Battery):
        return _numba_kernel(np.ascontiguousarray(prod, dtype=float), np.ascontiguousarray(cons, dtype=float),
                             float(b.usable_kwh), float(b.charge_kw), float(b.discharge_kw), float(b.efficiency))
except ImportError:
    numba = None
    dispatch_numba = None


# (e) Rust, where the extension is built (dispatch_rs/, maturin develop --release)

try:
    import dispatch_rs
    if not hasattr(dispatch_rs, "dispatch"):
        raise ImportError("dispatch_rs/ is the crate's folder, not the extension built from it")

    def dispatch_rust(prod, cons, b: Battery):
        return dispatch_rs.dispatch(np.ascontiguousarray(prod, dtype=float), np.ascontiguousarray(cons, dtype=float),
                                    float(b.usable_kwh), float(b.charge_kw), float(b.discharge_kw), float(b.efficiency))
except ImportError:
    dispatch_rs = None
    dispatch_rust = None


# the data

def synthetic_year(seed: int = 7, kwp: float = 90.0) -> tuple[np.ndarray, np.ndarray]:
    """A plausible year: production with a clear-sky bell by day and a seasonal swing, dimmed by random clouds;
    a weekday load with a daytime plateau. kWh per hour, 8,760 values each."""
    rng = np.random.default_rng(seed)
    h = np.arange(HOURS)
    hour = h % 24
    day = h // 24
    season = 0.55 + 0.45 * np.cos(2 * np.pi * (day - 172) / 365.0)              # longest days around 21 June
    daylight = 6.0 + 2.5 * season                                                # half the day length, in hours
    bell = np.clip(np.cos(np.pi * (hour - 12.5) / (2 * daylight)), 0.0, None) ** 1.3
    clouds = np.repeat(rng.beta(5, 2, size=365), 24)
    prod = kwp * 0.75 * season * bell * clouds * (0.85 + 0.3 * rng.random(HOURS))
    weekday = (day % 7) < 5
    base = 6.0 + 1.5 * np.sin(2 * np.pi * (day - 200) / 365.0)
    plateau = np.where((hour >= 7) & (hour < 19), 28.0, 0.0) * np.where(weekday, 1.0, 0.25)
    cons = (base + plateau) * (0.9 + 0.2 * rng.random(HOURS))
    return prod.astype(float), cons.astype(float)


def storage_batteries(prod: np.ndarray, cons: np.ndarray) -> list[Battery]:
    """The six generic batteries of economics.storage_sizing: a share of the daily energy that can be shifted (the
    lesser of the surplus and the consumption, on an average day), power half the capacity, 90% round trip."""
    export = np.clip(prod - cons, 0.0, None).sum()
    scale = max(1.0, min(float(export), float(cons.sum())) / 365.0)
    out = []
    for f in STORAGE_FACTORS:
        kwh = round(scale * f, 1)
        out.append(Battery(kwh, kwh / 2.0, kwh / 2.0, 0.9, f"{kwh:g} kWh"))
    return out


def year_factors() -> np.ndarray:
    return np.array([(1.0 - DEGRADATION / 100.0) ** (y - 1) for y in range(1, YEARS + 1)])


# the checks

def _same(a, b, what: str, atol: float = 1e-9) -> float:
    worst = 0.0
    for x, y, name in zip(a, b, ("stored", "given", "soc"), strict=True):
        if not np.allclose(x, y, rtol=1e-9, atol=atol):
            raise AssertionError(f"{what}: {name} differs, max |diff| = {np.max(np.abs(x - y)):.3e}")
        worst = max(worst, float(np.max(np.abs(x - y))) if x.size else 0.0)
    return worst


def check(args) -> None:
    rng = np.random.default_rng(1)
    singles = {"scan": dispatch_scan}
    if dispatch_numba is not None:
        singles["numba"] = dispatch_numba
    if dispatch_rust is not None:
        singles["rust"] = dispatch_rust
    print("variants present:", ", ".join(["reference", "batched", "scan_batched", *singles]))
    worst = {k: 0.0 for k in (*singles, "batched", "scan_batched")}
    cases = 0
    # random cases: short years, odd batteries (tiny, huge, no power), hours with no surplus at all
    for i in range(60):
        n = int(rng.integers(1, 400))
        prod = np.clip(rng.normal(20, 15, n), 0, None) * rng.choice([0.0, 1.0], p=[0.1, 0.9], size=n)
        cons = np.clip(rng.normal(15, 10, n), 0, None)
        if i % 7 == 0:
            cons = prod.copy()                                     # surplus exactly zero everywhere
        kwh = float(rng.choice([0.5, 5.0, 40.0, 500.0]))
        b = Battery(kwh, float(rng.choice([0.2, kwh / 2, 1e6])), float(rng.choice([0.1, kwh / 2, 1e6])),
                    float(rng.choice([0.5, 0.9, 1.0])))
        ref = dispatch_reference(prod, cons, b)
        for name, fn in singles.items():
            worst[name] = max(worst[name], _same(fn(prod, cons, b), ref, f"{name} case {i}"))
        facs = np.array([1.0, 0.9])
        refs = [[dispatch_reference(prod * f, cons, bb) for f in facs] for bb in (b, Battery(kwh * 3, kwh, kwh, 0.8))]
        for name, fn in (("batched", dispatch_batched), ("scan_batched", dispatch_scan_batched)):
            got = fn(prod, cons, [b, Battery(kwh * 3, kwh, kwh, 0.8)], facs)
            for bi in range(2):
                for fi in range(2):
                    worst[name] = max(worst[name], _same(tuple(g[bi, fi] for g in got), refs[bi][fi],
                                                         f"{name} case {i} b{bi} f{fi}"))
        cases += 1
    # the year: 156 reference calls as storage_sizing makes them, against every variant
    prod, cons = load_data(args.data)
    batteries = storage_batteries(prod, cons)
    factors = year_factors()
    refs = {}
    for bi, b in enumerate(batteries):
        balance = dispatch_reference(prod, cons, b)
        for fi, f in enumerate(factors):
            refs[(bi, fi)] = dispatch_reference(prod * f, cons, b)
        _same(refs[(bi, 0)], balance, f"balance of battery {bi} against its year 1", atol=0.0)
    for name, fn in singles.items():
        for (bi, fi), ref in refs.items():
            worst[name] = max(worst[name], _same(fn(prod * factors[fi], cons, batteries[bi]), ref, f"{name} year {fi}"))
    for name, fn in (("batched", dispatch_batched), ("scan_batched", dispatch_scan_batched)):
        got = fn(prod, cons, batteries, factors)
        for (bi, fi), ref in refs.items():
            worst[name] = max(worst[name], _same(tuple(g[bi, fi] for g in got), ref, f"{name} b{bi} f{fi}"))
    print(f"{cases} random cases and the 8,760-hour year (6 batteries x 25 years): every variant equals the "
          f"reference (numpy.allclose, rtol 1e-9, atol 1e-9).")
    for name, w in worst.items():
        print(f"  largest |difference| {name:13s} {w:.2e} kWh")
    print("the first-year balance equals year 1 of the loop exactly: 150 distinct results among the 156 calls.")


# the timing

def load_data(path: str | None) -> tuple[np.ndarray, np.ndarray]:
    if path:
        z = np.load(path)
        return np.asarray(z["prod"], dtype=float), np.asarray(z["cons"], dtype=float)
    return synthetic_year()


def bench(args) -> None:
    prod, cons = load_data(args.data)
    batteries = storage_batteries(prod, cons)
    factors = year_factors()
    b1 = batteries[3]                                   # the factor 1.0 battery for the single call
    rows = []
    print(f"{platform.python_implementation()} {platform.python_version()} on {platform.system()} "
          f"{platform.machine()}, numpy {np.__version__}" + (f", numba {numba.__version__}" if numba else "")
          + (", dispatch_rs built" if dispatch_rs else ""))
    print(f"data: {'file ' + args.data if args.data else 'synthetic year (seed 7)'}; production {prod.sum():,.0f} kWh, "
          f"consumption {cons.sum():,.0f} kWh; batteries {[b.name for b in batteries]}")
    meter = CpuMeter().start()

    def time_single(fn, inner: int):
        samples = []
        for _ in range(args.repeats):
            t = time.perf_counter()
            for _ in range(inner):
                fn(prod, cons, b1)
            samples.append((time.perf_counter() - t) / inner)
        return samples

    def time_156(fn):
        samples = []
        for _ in range(args.repeats):
            t = time.perf_counter()
            for b in batteries:
                fn(prod, cons, b)                       # balance
                for f in factors:
                    fn(prod * f, cons, b)
            samples.append(time.perf_counter() - t)
        return samples

    def time_batched(fn):
        samples = []
        for _ in range(args.repeats):
            t = time.perf_counter()
            fn(prod, cons, batteries, factors)
            samples.append(time.perf_counter() - t)
        return samples

    ref_one = time_single(dispatch_reference, 3)
    ref_156 = time_156(dispatch_reference)
    rows.append(("(a) reference, pure Python", ref_one, ref_156, ""))
    rows.append(("(b) batched state, numpy loop over hours", None, time_batched(dispatch_batched),
                 "one call for all 150 results"))
    rows.append(("(c) numpy prefix scan, no Python loop", time_single(dispatch_scan, 20), time_156(dispatch_scan), ""))
    rows.append(("(c') numpy prefix scan, batched 2-D", None, time_batched(dispatch_scan_batched),
                 "one call for all 150 results"))
    if dispatch_numba is not None:
        t = time.perf_counter()
        dispatch_numba(prod, cons, b1)
        first = time.perf_counter() - t
        rows.append(("(d) numba @njit, warm", time_single(dispatch_numba, 50), time_156(dispatch_numba),
                     f"first call {first * 1e3:.0f} ms ({'cache on' if os.environ.get('DISPATCH_NUMBA_CACHE') == '1' else 'compiled'})"))
    if dispatch_rust is not None:
        rows.append(("(e) Rust, PyO3 + maturin", time_single(dispatch_rust, 50), time_156(dispatch_rust), ""))
    busy = meter.stop()
    ref_156_m = statistics.median(ref_156)
    print(f"\nCPU busy during the timing: {busy:.0f}% of all logical processors over {meter.seconds:.0f} s; "
          f"repeats {args.repeats} (median; one call is the mean of some consecutive calls)")
    print(f"{'variant':44s} {'one call (ms)':>14s} {'156 calls (ms)':>15s} {'x faster':>9s}  note")
    for name, one, many, note in rows:
        one_s = f"{statistics.median(one) * 1e3:14.3f}" if one else f"{'-':>14s}"
        many_m = statistics.median(many)
        print(f"{name:44s} {one_s} {many_m * 1e3:15.1f} {ref_156_m / many_m:9.1f}  {note}")
    print("\nspread of the samples:")
    for name, one, many, _note in rows:
        print(f"  {name:44s} 156 calls: {describe(many)}" + (f"; one call: {describe(one, digits=3)}" if one else ""))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("what", choices=("check", "bench"))
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--data", default=None, help="an .npz with prod and cons (kWh per hour, 8760 values)")
    args = p.parse_args()
    (check if args.what == "check" else bench)(args)


if __name__ == "__main__":
    main()
