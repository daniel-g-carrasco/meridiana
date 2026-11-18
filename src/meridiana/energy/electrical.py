"""Sampled single-diode circuits: parallel currents, series voltages and bypass sections.

Cells with equal irradiance are grouped into series cohorts within bypass blocks. Missing cell geometry and
internal topology are inferred and must be reported. Reverse breakdown/hotspots and firmware are not modelled.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter

import numpy as np

POINTS = 129
BYPASS_DROP = 0.5  # V: an explicit engineering assumption, not a manufacturer diode curve


@dataclass
class Curve:
    voltage: np.ndarray             # hours x samples, increasing along the last axis
    current: np.ndarray             # hours x samples, decreasing


@dataclass
class OperatingPoint:
    voltage: np.ndarray
    current: np.ndarray

    @property
    def power(self):
        return self.voltage * self.current


try:            # NumPy's compiled interpolation itself, without the checks np.interp makes around it at each call
    from numpy._core.multiarray import interp as _compiled_interp
except ImportError:             # pragma: no cover - another NumPy layout: the public function, same numbers
    _compiled_interp = np.interp


def interp(x, xp, fp):
    """Row-wise linear interpolation with bounded memory, including duplicate dark endpoints: `np.interp` on each
    row, the same numbers. NumPy's compiled search is faster than broadcast binary search at the bounded 48-hour
    batch size (0.086 vs 0.462 s for 500 batches of 48 x 129 points on the verification workstation; R266, 30/10/2026:
    one search of all rows as complex numbers 0.255 s, a stable sort 0.306 s, against 0.177 s for the loop), so the
    loop stays, calling the compiled function directly: NumPy's wrapper cost a third of each call (R266)."""
    x, xp, fp = (np.asarray(a, dtype=float) for a in (x, xp, fp))
    if x.ndim == 2 and x.shape[1] == 1 and xp.shape[1] > 1:
        point = _interp_one(x, xp, fp)
        if point is not None:
            return point
    out = np.empty(x.shape)
    for i in range(len(x)):
        out[i] = _compiled_interp(x[i], xp[i], fp[i])
    return out


def _interp_one(x, xp, fp):
    """`interp` of one value per row, all rows at once (a curve read at zero volts: half of the searches of the
    electrical network, R266), with NumPy's own rule (numpy/_core/src/multiarray/compiled_base.c, arr_interp): the
    last point not above the value, the first or last value outside, the point's value on an exact hit, the slope
    from the left point and from the right one when that is not a number. None when a row is not sorted or holds a
    NaN: the loop then does it."""
    if np.isnan(x).any() or np.isnan(xp).any() or (xp[:, 1:] < xp[:, :-1]).any():
        return None
    n = xp.shape[1]
    j = (xp <= x).sum(axis=1, keepdims=True) - 1
    k = np.clip(j, 0, n - 2)
    xl, xr = np.take_along_axis(xp, k, axis=1), np.take_along_axis(xp, k + 1, axis=1)
    fl, fr = np.take_along_axis(fp, k, axis=1), np.take_along_axis(fp, k + 1, axis=1)
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        slope = (fr - fl) / (xr - xl)
        out = slope * (x - xl) + fl
        lost = np.isnan(out)
        if lost.any():
            out = np.where(lost, slope * (x - xr) + fr, out)
            out = np.where(np.isnan(out) & (fl == fr), fl, out)
    out = np.where(x == xl, fl, out)
    out = np.where(j >= n - 1, fp[:, -1:], out)
    return np.where(j < 0, fp[:, :1], out)


def current_at(curve: Curve, voltage):
    voltage = np.asarray(voltage)
    value = interp(voltage, curve.voltage, curve.current)
    # Generation quadrant only: circulating reverse currents require protection/topology data not provided.
    return np.where(voltage > curve.voltage[:, -1:], 0.0, np.maximum(value, 0.0))


def voltage_at(curve: Curve, current, bypass=None):
    current = np.asarray(current)
    value = interp(current, curve.current[:, ::-1], curve.voltage[:, ::-1])
    if bypass is not None:
        value = np.where(current > curve.current[:, :1], -bypass, value)
        value = np.maximum(value, -bypass)
    return value


def parallel(curves: list[Curve], points=POINTS) -> Curve:
    if len(curves) == 1:
        return curves[0]
    end = np.maximum.reduce([c.voltage[:, -1] for c in curves])
    start = np.minimum.reduce([c.voltage[:, 0] for c in curves])
    voltage = start[:, None] + (end - start)[:, None] * np.linspace(0, 1, points)
    counts = Counter(id(c) for c in curves)
    unique = {id(c): c for c in curves}
    current = sum(current_at(c, voltage) * counts[k] for k, c in unique.items())
    return Curve(voltage, current)


def series(curves: list[Curve], points=POINTS, bypass=None) -> Curve:
    if len(curves) == 1 and bypass is None:
        return curves[0]
    counts = Counter(id(c) for c in curves)
    unique = {id(c): c for c in curves}
    end = np.maximum.reduce([current_at(c, np.zeros((len(c.voltage), 1)))[:, 0] for c in unique.values()])
    current = end[:, None] * np.linspace(1, 0, points)
    voltage = sum(voltage_at(c, current, bypass) * counts[k] for k, c in unique.items())
    return Curve(voltage, current)


def mpp(curve: Curve, *, voltage_min=0.0, voltage_max=None, current_max=None) -> OperatingPoint:
    """Global maximum of the piecewise-linear I/V curve, including limit boundaries and every local peak."""
    v, i = curve.voltage, curve.current
    dv = np.diff(v, axis=1)
    slope = np.divide(np.diff(i, axis=1), dv, out=np.zeros_like(dv), where=dv > 1e-12)
    intercept = i[:, :-1] - slope * v[:, :-1]
    floor = np.asarray(0.0 if voltage_min is None else voltage_min)
    if floor.ndim:
        floor = floor[:, None]
    low = np.maximum(v[:, :-1], floor)
    high = v[:, 1:] if voltage_max is None else np.minimum(v[:, 1:], voltage_max)
    if current_max is not None:
        crossing = np.divide(current_max - intercept, slope, out=np.full_like(slope, -np.inf), where=slope < 0)
        low = np.maximum(low, crossing)
    peak = np.divide(-intercept, 2 * slope, out=high.copy(), where=slope < 0)
    voltage = np.minimum(np.maximum(peak, low), high)
    current = np.maximum(slope * voltage + intercept, 0)
    valid = (high >= low) & (dv > 1e-12) & (voltage >= 0)
    if current_max is not None:
        valid &= current <= current_max + 1e-8
    power = np.where(valid, voltage * current, 0.0)
    best = power.argmax(axis=1)[:, None]
    on = np.take_along_axis(power, best, axis=1)[:, 0] > 0
    return OperatingPoint(np.where(on, np.take_along_axis(voltage, best, axis=1)[:, 0], 0),
                          np.where(on, np.take_along_axis(current, best, axis=1)[:, 0], 0))


@dataclass(frozen=True)
class CurvePlan:
    """What `module_curve` decides over a whole batch of hours, besides the hours themselves: whether every cell
    of every hour sees the same light (the one-diode module, `uniform`), how many cohorts a block keeps after
    packing (`count`, 0 for a single cohort), and which packed cohorts some hour occupies (`active`, per block).
    Given back with any subset of the batch's hours, `module_curve` computes each of those hours exactly as in
    the whole batch: once these are fixed, every operation works hour by hour (R266)."""
    uniform: bool
    count: int
    active: tuple

    @property
    def hourly(self) -> tuple:
        """What of the plan an hour's curve depends on, besides the hour's own light, temperature and cohorts:
        the one-diode module or not, and for each block whether it has one cohort in the batch (its curve taken
        as it is) or more (the section's series, resampled). The number of cohorts beyond one does not matter: a
        cohort an hour leaves empty has a series fraction of zero, its voltage is exactly zero at any current and
        its current at zero volts is not above the occupied ones', so it adds nothing to the section's samples;
        packing keeps the occupied cohorts first, in the same order whatever the count."""
        return self.uniform, tuple(sum(block) == 1 for block in self.active)


def _prepared(module, irradiance, temperature, layout, bypass_drop, cell_fractions, plan):
    g = np.clip(np.asarray(irradiance, dtype=float), 0, None)
    temp = np.broadcast_to(np.asarray(temperature, dtype=float), (len(g),))
    strips, pieces = layout
    if g.shape[:2] != (len(temp), strips * pieces):
        raise ValueError('irradiance must supply each bypass block')
    if cell_fractions is not None:
        fractions = np.asarray(cell_fractions, dtype=float)
        if fractions.shape != g.shape or g.ndim != 3:
            raise ValueError('each cell irradiance cohort needs its series fraction')
        if not np.allclose(fractions.sum(axis=2), 1):
            raise ValueError('cell fractions must sum to one within every bypass block')
    else:
        g = g[..., None]
        fractions = np.ones_like(g)
    mean = (g * fractions).sum(axis=2)
    uniform = plan.uniform if plan is not None else bool(
        np.allclose(mean, mean[:, :1], rtol=0, atol=1e-10)
        and np.all((fractions == 0) | (np.abs(g - mean[..., None]) < 1e-10)))
    if uniform:
        # Identically illuminated series/parallel cell chains are exactly the original one-diode
        # module. Combine their bypass drops, avoiding six identical circuit reconstructions.
        bypass_drop *= strips
        strips, pieces = 1, 1
        g = mean[:, :1, None]
        fractions = np.ones_like(g)
    # A moving edge may visit every quantization bin during a batch while each individual hour only
    # contains a few occupied bins. Pack those cohorts independently per hour/block, without averaging
    # irradiance or dropping any cells. Series order within one bypass section cannot change its curve.
    count = 0
    if g.shape[2] > 1:
        count = plan.count if plan is not None else int((fractions > 0).sum(axis=2).max())
        order = np.argsort(-fractions, axis=2)[..., :count]
        g = np.take_along_axis(g, order, axis=2)
        fractions = np.take_along_axis(fractions, order, axis=2)
    active = plan.active if plan is not None else tuple(
        tuple(bool(fractions[:, b, c].any()) for c in range(g.shape[2])) for b in range(g.shape[1]))
    return g, temp, fractions, strips, pieces, bypass_drop, CurvePlan(uniform, count, active)


def curve_plan(module, irradiance, temperature, layout=(3, 1), *, cell_fractions=None) -> CurvePlan:
    """The decisions `module_curve` takes over this batch of hours (CurvePlan), without computing the curve."""
    return _prepared(module, irradiance, temperature, layout, BYPASS_DROP, cell_fractions, None)[-1]


def _series_stacked(voltages, currents, points=POINTS) -> Curve:
    """`series` of the curves stacked along the middle axis (hours x curves x samples), each curve once: the same
    searches row by row and the same sum in the same order, one call for all of them (R266)."""
    hours, many, samples = voltages.shape
    flat = Curve(voltages.reshape(hours * many, samples), currents.reshape(hours * many, samples))
    end = current_at(flat, np.zeros((hours * many, 1)))[:, 0].reshape(hours, many).max(axis=1)
    current = end[:, None] * np.linspace(1, 0, points)
    each = voltage_at(flat, np.repeat(current, many, axis=0)).reshape(hours, many, points)
    voltage = 0
    for c in range(many):
        voltage = voltage + each[:, c]
    return Curve(voltage, current)


def module_curve(module, irradiance, temperature, layout=(3, 1), *, points=POINTS,
                 bypass_drop=BYPASS_DROP, cell_fractions=None, plan: CurvePlan | None = None) -> Curve:
    """Module I/V from irradiance cohorts of series cells, ordered strip then parallel half.

    Each bypass section comprises `pieces` parallel cell chains, and `strips` sections are in series.
    Whole-module diode parameters scale by series/parallel count; identical illumination reconstructs the
    original module. A linear module fallback gets a declared three-point datasheet curve instead. `plan`, the
    decisions of a larger batch these hours belong to (curve_plan), makes each hour what it is in that batch.
    """
    g, temp, fractions, strips, pieces, bypass_drop, plan = _prepared(
        module, irradiance, temperature, layout, bypass_drop, cell_fractions, plan)
    if module.sdm().get('linear'):
        mean = (g * fractions).sum(axis=2).mean(axis=1)
        voc = module.voc * (1 + module.beta_voc / 100 * (temp - 25))
        isc = module.isc * mean / 1000 * (1 + module.alpha_isc / 100 * (temp - 25))
        voltage = voc[:, None] * np.array([0, module.vmp / module.voc, 1])
        current = isc[:, None] * np.array([1, module.imp / module.isc, 0])
        return Curve(voltage, np.maximum(current, 0))
    il, io, rs, rsh, nvt = (np.broadcast_to(np.asarray(p, dtype=float), g.shape)
                           for p in module.diode_params(np.maximum(g, 0.01), temp[:, None, None]))
    il, io = il / pieces, io / pieces
    rs, rsh, nvt = rs * pieces / strips, rsh * pieces / strips, nvt / strips
    sections = []
    for strip in range(strips):
        branches = []
        for piece in range(pieces):
            b = strip * pieces + piece
            # The cohorts these hours leave empty add nothing (CurvePlan.hourly): only whether the batch has more
            # than one counts, so one of them is kept for that. Packed, the empty ones are the last (R266).
            used = [c for c in range(g.shape[2]) if plan.active[b][c]]
            occupied = [c for c in used if fractions[:, b, c].any()]
            if len(used) > 1 and len(occupied) < 2:
                occupied = used[:2]
            # All the cohorts of the block at once, cohort after cohort along a middle axis: the same operations
            # on the same numbers as one cohort at a time, without a Python turn for each (R266).
            k = occupied
            fraction = fractions[:, b, k]
            il_k, io_k, rs_k, rsh_k, nvt_k = il[:, b, k], io[:, b, k], rs[:, b, k], rsh[:, b, k], nvt[:, b, k]
            end = nvt_k * np.log1p(il_k / io_k)
            vd = -2 * bypass_drop + (end + 2 * bypass_drop)[..., None] * np.linspace(0, 1, points)
            current = (il_k[..., None] - io_k[..., None] * np.expm1(vd / nvt_k[..., None])
                       - vd / rsh_k[..., None])
            voltage = (vd - current * rs_k[..., None]) * fraction[..., None]
            # Below zero, a shaded cell chain follows its shunt resistance until the section bypass
            # conducts. The reverse sample spans the other cells' forward voltage plus the bypass drop;
            # no avalanche parameters are invented.
            current = np.where(g[:, b, k, None] > 0, np.maximum(current, 0), 0)
            reverse_v = -(end + 2)[..., None] * (fraction[..., None] > 0)
            effective_rsh = rsh_k * np.maximum(fraction, 1e-12)
            reverse_i = ((il_k - reverse_v[..., 0] / effective_rsh) / (1 + rs_k / rsh_k))[..., None]
            reverse_i = np.where(fraction[..., None] > 0, np.maximum(reverse_i, current[..., :1]),
                                 il[:, b, :].max(axis=1)[:, None, None] + 1)
            voltages = np.concatenate([reverse_v, voltage], axis=2)
            currents = np.concatenate([reverse_i, current], axis=2)
            # No diode between cohorts: bypass belongs to the entire section. A zero series fraction
            # contributes zero voltage, independent of the requested current.
            if len(k) == 1:
                branches.append(Curve(voltages[:, 0], currents[:, 0]))
            else:
                branches.append(_series_stacked(voltages, currents, points))
        sections.append(parallel(branches, points))
    return series(sections, points, bypass=bypass_drop)
