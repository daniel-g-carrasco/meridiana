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


def interp(x, xp, fp):
    """Row-wise linear interpolation with bounded memory, including duplicate dark endpoints."""
    x, xp, fp = np.asarray(x), np.asarray(xp), np.asarray(fp)
    # NumPy's compiled search is faster than broadcast binary search at the bounded 48-hour batch size
    # (0.086 vs 0.462 s for 500 batches of 48 x 129 points on the verification workstation).
    return np.array([np.interp(row, points, values) for row, points, values in zip(x, xp, fp, strict=True)])


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


def module_curve(module, irradiance, temperature, layout=(3, 1), *, points=POINTS,
                 bypass_drop=BYPASS_DROP, cell_fractions=None) -> Curve:
    """Module I/V from irradiance cohorts of series cells, ordered strip then parallel half.

    Each bypass section comprises `pieces` parallel cell chains, and `strips` sections are in series.
    Whole-module diode parameters scale by series/parallel count; identical illumination reconstructs the
    original module. A linear module fallback gets a declared three-point datasheet curve instead.
    """
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
    if np.allclose(mean, mean[:, :1], rtol=0, atol=1e-10) and np.all(
            (fractions == 0) | (np.abs(g - mean[..., None]) < 1e-10)):
        # Identically illuminated series/parallel cell chains are exactly the original one-diode
        # module. Combine their bypass drops, avoiding six identical circuit reconstructions.
        bypass_drop *= strips
        strips, pieces = 1, 1
        g = mean[:, :1, None]
        fractions = np.ones_like(g)
    # A moving edge may visit every quantization bin during a batch while each individual hour only
    # contains a few occupied bins. Pack those cohorts independently per hour/block, without averaging
    # irradiance or dropping any cells. Series order within one bypass section cannot change its curve.
    if g.shape[2] > 1:
        count = int((fractions > 0).sum(axis=2).max())
        order = np.argsort(-fractions, axis=2)[..., :count]
        g = np.take_along_axis(g, order, axis=2)
        fractions = np.take_along_axis(fractions, order, axis=2)
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
            cohorts = []
            for c in range(g.shape[2]):
                fraction = fractions[:, b, c]
                if not fraction.any():
                    continue
                end = nvt[:, b, c] * np.log1p(il[:, b, c] / io[:, b, c])
                vd = -2 * bypass_drop + (end + 2 * bypass_drop)[:, None] * np.linspace(0, 1, points)
                current = (il[:, b, c, None] - io[:, b, c, None] * np.expm1(vd / nvt[:, b, c, None])
                           - vd / rsh[:, b, c, None])
                voltage = (vd - current * rs[:, b, c, None]) * fraction[:, None]
                # Below zero, a shaded cell chain follows its shunt resistance until the section bypass
                # conducts. The reverse sample spans the other cells' forward voltage plus the bypass drop;
                # no avalanche parameters are invented.
                current = np.where(g[:, b, c, None] > 0, np.maximum(current, 0), 0)
                reverse_v = -(end + 2)[:, None] * (fraction[:, None] > 0)
                effective_rsh = rsh[:, b, c] * np.maximum(fraction, 1e-12)
                reverse_i = ((il[:, b, c] - reverse_v[:, 0] / effective_rsh)
                             / (1 + rs[:, b, c] / rsh[:, b, c]))[:, None]
                reverse_i = np.where(fraction[:, None] > 0, np.maximum(reverse_i, current[:, :1]),
                                     il[:, b, :].max(axis=1)[:, None] + 1)
                cohorts.append(Curve(np.concatenate([reverse_v, voltage], axis=1),
                                     np.concatenate([reverse_i, current], axis=1)))
            # No diode between cohorts: bypass belongs to the entire section. A zero series fraction
            # contributes zero voltage, independent of the requested current.
            if len(cohorts) == 1:
                branches.append(cohorts[0])
            else:
                branches.append(series(cohorts, points))
        sections.append(parallel(branches, points))
    return series(sections, points, bypass=bypass_drop)
