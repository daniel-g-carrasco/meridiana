"""Hourly electrical network of the actual connected modules, evaluated in bounded time chunks."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

from ..i18n import _
from . import electrical as iv
from . import nearshade, optimizers

CHUNK_HOURS = 48


@dataclass
class Network:
    reference: dict = field(default_factory=dict)
    nominal: dict = field(default_factory=dict)
    at25: dict = field(default_factory=dict)
    stages: dict = field(default_factory=dict)
    dc: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    specs: dict = field(default_factory=dict)


def parallel_input_mpp(curves, voltage_min=0, voltage_max=None, current_max=None):
    """Enforce the current limit on each physical input at their shared voltage."""
    floor = np.full(len(curves[0].voltage), voltage_min)
    if current_max:
        for curve in curves:
            crossing = iv.voltage_at(curve, np.full((len(floor), 1), current_max))[:, 0]
            floor = np.maximum(floor, crossing)
    return iv.mpp(iv.parallel(curves), voltage_min=floor, voltage_max=voltage_max)


def optimizer_string_power(power, voltage, voltage_max=None, current_max=None):
    """Maximum common string current at fixed inverter voltage, subject to each optimizer's available power.

    At current I, optimizer j can supply at most min(Pj/I, Vj,max). Bisection finds the highest common current
    for which their available voltages reach the inverter's fixed voltage. Dark units cannot supply voltage.
    """
    power = np.maximum(np.asarray(power, dtype=float), 0)
    if voltage <= 0:
        return np.zeros(len(power))
    high = power.sum(axis=1) / voltage
    if current_max:
        high = np.minimum(high, current_max)
    if voltage_max is None:
        return high * voltage
    cap = np.broadcast_to(np.asarray(voltage_max), power.shape)
    possible = np.where(power > 1e-9, cap, 0).sum(axis=1) >= voltage
    low = np.zeros_like(high)
    for _iteration in range(32):
        current = (low + high) / 2
        available = np.minimum(np.divide(power, current[:, None], out=np.zeros_like(power),
                                         where=current[:, None] > 0), cap).sum(axis=1)
        fits = available >= voltage
        low, high = np.where(fits, current, low), np.where(fits, high, current)
    return np.where(possible, low * voltage, 0)


def _row_cohorts(ap, pm, hours):
    """Cell-row shade of an infinite row approximation, preserving the actual module stack level."""
    nb = ap.layout[0] * ap.layout[1]
    result = np.zeros((len(hours), nb, nearshade.CELL_LEVELS))
    result[..., 0] = 1
    if ap.a.rows <= 1 or pm.row == min(p.row for p in ap.a.placed) or ap.row_share is None:
        return result
    fraction = np.clip(ap.row_share[hours] * ap.a.stack - getattr(pm, 'level', 0), 0, 1)
    if not fraction.any():
        return result
    m = ap.a.module
    width, height = (m.width, m.length) if ap.a.upright else (m.length, m.width)
    blocks = nearshade._block_rects(np.array([[0., 0., width, height]]), ap.layout)[0]
    count = max(1, m.cells // nb)
    for b, rect in enumerate(blocks):
        cells = nearshade.cell_boxes(rect[None, :], count)[0]
        fractions = np.clip((fraction[:, None] * height - cells[None, :, 1])
                            / (cells[None, :, 3] - cells[None, :, 1]), 0, 1)
        result[:, b] = nearshade.cell_histogram(fractions)
    return result


def _cohorts(ap, pm, hours, first):
    result = _row_cohorts(ap, pm, hours)
    if ap.near is None or pm.key not in ap.near.keys:
        return result
    obstacle = nearshade.cell_cohorts(ap.near, ap.near.keys.index(pm.key), first.sun_az[hours], first.sun_el[hours])
    if np.all(result[..., 0] == 1):
        return obstacle
    if np.all(obstacle[..., 0] == 1):
        return result
    # Geometry of the two shadow sources is not jointly available in the old row model. Independent
    # overlap of their cell cohorts is explicit, and their union can never remove diffuse irradiance.
    n = nearshade.CELL_LEVELS
    pairs = (result[..., :, None] * obstacle[..., None, :]).reshape(-1, n * n)
    return (pairs @ _overlap_matrix(n)).reshape(result.shape)


@lru_cache(maxsize=2)
def _overlap_matrix(n):
    levels = np.linspace(0, 1, n)
    position = (levels[:, None] + levels[None, :] - levels[:, None] * levels[None, :]).ravel() * (n - 1)
    low = np.floor(position).astype(int)
    high = np.minimum(low + 1, n - 1)
    matrix = np.zeros((n * n, n))
    np.add.at(matrix, (np.arange(n * n), low), 1 - position + low)
    np.add.at(matrix, (np.arange(n * n), high), position - low)
    return matrix


def solve(first, plant, progress=None) -> Network:
    """Return electrical stages and DC by inverter; disconnected or invalid references never generate."""
    hours = first.hours
    out = Network()
    arrays = {ap.a.key: ap for ap in first.per_array}
    location = {(ap.a.key.split('.')[0], pm.key): (ap, pm) for ap in first.per_array for pm in ap.a.placed}
    units = {u.number: u for u in plant.units if u.entry >= 0 and u.spec.pac > 0}
    runs = [s for s in plant.strings if s.inverter in units and 1 <= s.mppt <= units[s.inverter].inputs]
    for key in arrays:
        out.reference[key] = np.zeros(hours)
        out.nominal[key] = np.zeros(hours)
        out.at25[key] = np.zeros(hours)
        out.stages[key] = {k: np.zeros(hours) for k in ('p_el', 'p_opt', 'p_cut', 'p_dc')}
    for run in runs:
        if run.modules:
            out.dc.setdefault(run.inverter, np.zeros(hours))
            out.specs[run.inverter] = units[run.inverter].spec
    if not out.dc:
        return out
    out.notes.append(_("Electrical production uses sampled cell-cohort I/V curves, bypass sections and common "
                       "string/MPPT operating points. Cell layout is inferred from module dimensions and cell count "
                       "unless documented; bypass forward drop is assumed to be 0.5 V. Reverse breakdown, hot spots "
                       "and inverter tracking dynamics are not simulated."))
    if not first.losses.electrical_shading or first.losses.electrical_fraction != 100:
        out.notes.append(_("The electrical-shading setting attenuates irradiance contrasts toward the array's "
                           "mean irradiance before recombining I/V curves; it is not a linear fraction of lost energy."))
    if any(ap.a.rows > 1 and ap.near is not None for ap in first.per_array):
        out.notes.append(_("Row shadows and obstacle shadows overlap statistically at cell level; their exact joint "
                           "shadow geometry is not available in the row approximation."))
    for ap in first.per_array:
        if ap.near is not None and not ap.near.cell_resolved:
            out.notes.append(_("{name}: cell geometry is unavailable; obstacle shading uses the mean irradiance "
                               "of each bypass block and may overestimate output for localized shadows.").format(name=ap.a.name))
        if ap.a.module.sdm().get('linear'):
            out.notes.append(_("{name}: no valid single-diode parameters; a three-point datasheet I/V approximation "
                               "is used and cell mismatch is not resolved.").format(name=ap.a.name))
    daylight = np.flatnonzero(np.maximum.reduce([ap.g_eff for ap in first.per_array]) > 0.1)
    losses = first.losses
    for start in range(0, len(daylight), CHUNK_HOURS):
        if progress is not None:
            progress()
        take = daylight[start:start + CHUNK_HOURS]
        cache = {}
        module_data = {}
        counted = set()

        def get_module(ref, optimized_single=False, *, module_data=module_data, take=take, cache=cache, counted=counted):
            key = tuple(ref[:2])
            memo = (key, optimized_single)
            if memo in module_data:
                return module_data[memo]
            ap, pm = location[key]
            a = ap.a
            fractions = _cohorts(ap, pm, take, first)
            shade = np.linspace(0, 1, fractions.shape[2])
            beam, diffuse = ap.beam_clear[take], ap.diffuse_eff[take]
            irradiance = np.broadcast_to(diffuse[:, None, None] + beam[:, None, None] * (1 - shade), fractions.shape)
            # The comparison switch attenuates contrast toward the legacy array-mean irradiance.
            strength = np.clip(losses.electrical_fraction / 100, 0, 1) if losses.electrical_shading else 0
            if strength < 1:
                irradiance = strength * irradiance + (1 - strength) * ap.g_eff[take, None, None]
            signature = (a.key, optimized_single, fractions.tobytes())
            if signature not in cache:
                curve = iv.module_curve(a.module, irradiance, ap.t_cell[take], ap.layout, cell_fractions=fractions)
                mean = (irradiance * fractions).sum(axis=2).mean(axis=1)
                independent = iv.mpp(curve).power
                uniform_cells = np.all((fractions == 0) | (np.abs(irradiance - mean[:, None, None]) < 1e-10))
                reference = independent if uniform_cells else iv.mpp(
                    iv.module_curve(a.module, mean[:, None], ap.t_cell[take], (1, 1))).power
                at25 = iv.mpp(iv.module_curve(a.module, mean[:, None], np.full(len(take), 25.), (1, 1))).power
                mismatch = 0 if optimized_single else losses.mismatch
                factor = (1 - losses.quality / 100) * (1 - ap.lid / 100) * (1 - mismatch / 100)
                curve = iv.Curve(curve.voltage, curve.current * max(0, factor))
                cache[signature] = curve, independent * max(0, factor), reference, at25, a.module.pmax * mean / 1000
            curve, ideal, reference, at25, nominal = cache[signature]
            if key not in counted:
                out.reference[a.key][take] += reference
                out.at25[a.key][take] += at25
                out.nominal[a.key][take] += nominal
                counted.add(key)
            module_data[memo] = (curve, ideal, a.key)
            return module_data[memo]

        def allocate(data, power, stage, *, take=take):
            denominator = sum(d[1] for d in data)
            for _curve, weight, key in data:
                out.stages[key][stage][take] += power * np.divide(weight, denominator, out=np.zeros_like(power),
                                                                 where=denominator > 0)

        ordinary = defaultdict(list)
        dc_chunks = defaultdict(lambda take=take: np.zeros(len(take)))
        currents = defaultdict(lambda take=take: np.zeros(len(take)))
        contributions = []
        for run in runs:
            unit = units[run.inverter]
            refs = [ref for ref in run.modules if tuple(ref[:2]) in location]
            if not refs:
                continue
            if unit.optimized and (unit.choice is None or not unit.fixed or not unit.fixed.v_string):
                note = _("{name}: optimizer or fixed-voltage data are missing; this inverter's electrical "
                          "production is not calculated and contributes zero.").format(name=unit.name)
                if note not in out.notes:
                    out.notes.append(note)
                continue
            if unit.optimized and unit.choice is not None:
                choice = unit.choice
                opt = choice.optimizer
                groups = optimizers.module_groups(refs, choice.per, getattr(run, 'optimizer_group_sizes', None))
                powers, data = [], []
                for group in groups:
                    group_data = [get_module(ref, len(group) == 1) for ref in group]
                    data.extend(group_data)
                    curves = [d[0] for d in group_data]
                    if opt.parallel_inputs:
                        op = parallel_input_mpp(curves, opt.v_in_min or 0, opt.v_in_max, opt.i_in_max)
                    else:
                        op = iv.mpp(iv.series(curves), voltage_min=opt.v_in_min or 0,
                                    voltage_max=opt.v_in_max, current_max=opt.i_in_max)
                    powers.append(op.power)
                raw = np.stack(powers, axis=1)
                converted = raw * opt.eta
                cap_i = opt.i_out_max or None
                if choice.rules is not None and choice.rules.p_cont and unit.fixed.v_string:
                    cap_i = min(cap_i or np.inf, choice.rules.p_cont / unit.fixed.v_string)
                cut = optimizer_string_power(converted, unit.fixed.v_string, opt.v_out_max, cap_i)
                stc = sum(location[tuple(ref[:2])][0].a.module.pmax for ref in refs)
                dc = np.maximum(cut - losses.dc_wiring / 100 * cut ** 2 / max(stc, 1e-9), 0)
                for stage, value in (('p_el', raw.sum(axis=1)), ('p_opt', converted.sum(axis=1))):
                    allocate(data, value, stage)
                contributions.append((run.inverter, data, cut, dc))
                dc_chunks[run.inverter] += dc
                currents[run.inverter] += cut / unit.fixed.v_string
                missing = [name for name in ('v_in_min', 'v_in_max', 'v_out_max', 'i_in_max', 'i_out_max')
                           if not getattr(opt, name)]
                if missing:
                    note = _("{name}: hourly limits unavailable: {fields}; those limits are not enforced.").format(
                        name=opt.name, fields=', '.join(missing))
                    if note not in out.notes:
                        out.notes.append(note)
            else:
                data = [get_module(ref) for ref in refs]
                ordinary[(run.inverter, run.mppt)].append((iv.series([d[0] for d in data]), data))
        for (number, mppt), strings in ordinary.items():
            spec = units[number].spec
            curve = iv.parallel([s[0] for s in strings])
            limit = spec.current_limit(mppt - 1, len(strings))
            maximum = min(v for v in (spec.vmppt_max, spec.vdc_max) if v) if (spec.vmppt_max or spec.vdc_max) else None
            missing = [label for label, value in (('MPPT minimum voltage', spec.vmppt_min),
                                                  ('MPPT maximum voltage', spec.vmppt_max),
                                                  ('MPPT operating current', limit)) if value is None]
            if missing:
                note = _("{name}, MPPT {mppt}: operating limits unavailable: {fields}; the available bounds are "
                          "applied, but this operating window is not fully verified.").format(
                    name=units[number].name, mppt=mppt, fields=', '.join(missing))
                if note not in out.notes:
                    out.notes.append(note)
            floor = np.full(len(take), spec.vmppt_min or 0.)
            connector_limit = spec.connector_current_limit(mppt - 1)
            ports = spec._limit(spec.inputs_per_mppt, mppt - 1)
            if connector_limit and ports and len(strings) > ports:
                limit = min(limit or np.inf, ports * connector_limit)
                note = _("{name}, MPPT {mppt}: external parallel strings have no connector mapping. The aggregate "
                          "connector capacity is enforced, but current sharing among physical connectors is "
                          "not verified.").format(name=units[number].name, mppt=mppt)
                if note not in out.notes:
                    out.notes.append(note)
            if connector_limit:
                for string, _data in strings:
                    floor = np.maximum(floor, iv.voltage_at(string, np.full((len(take), 1), connector_limit))[:, 0])
            op = iv.mpp(curve, voltage_min=floor, voltage_max=maximum, current_max=limit)
            currents[number] += op.current
            for string, data in strings:
                current = iv.current_at(string, op.voltage[:, None])[:, 0]
                power = op.voltage * current
                for stage in ('p_el', 'p_opt'):
                    allocate(data, power, stage)
                stc = sum(arrays[d[2]].a.module.pmax for d in data)
                imp = max(arrays[d[2]].a.module.imp for d in data)
                dc = np.maximum(power - losses.dc_wiring / 100 * stc * (current / max(imp, 1e-9)) ** 2, 0)
                contributions.append((number, data, power, dc))
                dc_chunks[number] += dc
        for number, data, power, dc in contributions:
            total = units[number].spec.imax_total
            factor = np.minimum(1, total / np.maximum(currents[number], 1e-9)) if total else 1
            allocate(data, power * factor, 'p_cut')
            allocate(data, dc * factor, 'p_dc')
        for number, dc in dc_chunks.items():
            total = units[number].spec.imax_total
            factor = np.minimum(1, total / np.maximum(currents[number], 1e-9)) if total else 1
            out.dc[number][take] = dc * factor
            if total and np.any(factor < 1):
                note = _("A shared inverter DC-current limit curtails its MPPT powers proportionally; optimal "
                          "redistribution between trackers is not simulated.")
                if note not in out.notes:
                    out.notes.append(note)
    return out
