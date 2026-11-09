"""Hourly electrical network of the actual connected modules, evaluated in bounded time chunks."""
from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

from ..i18n import _
from .. import resources
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


@dataclass
class OptimizerInput:
    """The input of one power optimizer on an inverter with MPPT of its own (R456: Huawei SUN2000-P and MERC, Sungrow
    SP600S, Tigo TS4-A-O) over a chunk of hours: the module (or the two) it takes as one I/V curve, its maximum power
    within the optimizer's input limits and the current there, and for each sample of the curve the most power of the
    samples at or below its current (what a converter whose input current cannot exceed its output current may draw)."""
    curve: iv.Curve
    power: np.ndarray               # W, hour by hour
    current: np.ndarray             # A, the input current at that power
    best: np.ndarray                # W, hours x samples
    v_min: float
    v_max: float | None
    i_max: float | None


def optimizer_input(curve: iv.Curve, opt) -> OptimizerInput:
    """`curve` as the input of optimizer `opt` (optimizers.Optimizer): its maximum power point within the input's
    voltage window and current, as SolarEdge's optimizers find theirs (iv.mpp), and the samples that bound the rest."""
    v_min, v_max, i_max = opt.v_in_min or 0.0, opt.v_in_max, opt.i_in_max
    op = iv.mpp(curve, voltage_min=v_min, voltage_max=v_max, current_max=i_max)
    v, i = curve.voltage, curve.current
    inside = (v >= v_min) & (i >= 0)
    if v_max:
        inside &= v <= v_max
    if i_max:
        inside &= i <= i_max
    power = np.where(inside, v * i, 0.0)
    best = np.maximum.accumulate(power[:, ::-1], axis=1)[:, ::-1]
    return OptimizerInput(curve, op.power, op.current, best, v_min, v_max, i_max)


def available_power(u: OptimizerInput, current, rows=None):
    """W optimizer input `u` may give when its output carries `current` (A, one value per hour of `rows`, all the hours
    when None). The optimizers of these makers only lower the voltage (buck: Huawei's long strings «les optimiseurs
    abaissent la tension», guide FR 15/07/2026 p. 8; Tigo's output never above the module's Voc): their input current is
    at most their output current, so at an output current at or above the module's own the whole maximum power, below it
    the most the module gives at an input current up to the output's (the module moves above its MPP voltage)."""
    curve, power, at, best = u.curve, u.power, u.current, u.best
    if rows is not None:
        curve, power, at, best = iv.Curve(curve.voltage[rows], curve.current[rows]), power[rows], at[rows], best[rows]
    current = np.asarray(current, dtype=float)
    n = curve.current.shape[1]
    below = (curve.current <= current[:, None]).sum(axis=1)
    index = np.clip(n - below, 0, n - 1)
    sampled = np.where(below > 0, np.take_along_axis(best, index[:, None], axis=1)[:, 0], 0.0)
    voltage = iv.voltage_at(curve, current[:, None])[:, 0]
    inside = (voltage >= u.v_min) & (current >= 0)
    if u.v_max:
        inside &= voltage <= u.v_max
    if u.i_max:
        inside &= current <= u.i_max
    point = np.where(inside, np.maximum(voltage, 0.0) * current, 0.0)
    return np.where(current >= at, power, np.minimum(np.maximum(point, sampled), power))


@dataclass
class OptimizedString:
    """A string of power optimizers on an inverter's MPPT (R456): the optimizers' inputs with how many of each, their
    efficiency, their output's most voltage and current. Each optimizer gives its input's power times its efficiency at
    the string's one current, at a voltage that power over the current, never above its output's most; the inverter's
    MPPT chooses the string's voltage within its window."""
    inputs: list                    # [(OptimizerInput, count)]
    eta: float
    v_out: float | None             # V, each optimizer's most output voltage
    i_out: float | None             # A, the optimizers' most output current
    full: np.ndarray = None         # W, the string's output with every optimizer at its maximum power point
    saturation: np.ndarray = None   # A, the least string current at which it is

    def __post_init__(self):
        hours = len(self.inputs[0][0].power)
        self.full, self.saturation = np.zeros(hours), np.zeros(hours)
        for u, count in self.inputs:
            self.full = self.full + count * self.eta * u.power
            least = u.current
            if self.v_out:
                least = np.maximum(least, self.eta * u.power / self.v_out)
            self.saturation = np.maximum(self.saturation, np.where(u.power > 0, least, 0.0))

    def voltage(self, current, rows=None):
        """V of the string at `current` (A, one value per hour of `rows`)."""
        current = np.maximum(np.asarray(current, dtype=float), 1e-9)
        total = np.zeros(len(current))
        for u, count in self.inputs:
            v = self.eta * available_power(u, current, rows) / current
            if self.v_out:
                v = np.minimum(v, self.v_out)
            total += count * v
        return total

    def current_at(self, voltage, rows, top):
        """A of the string at `voltage` above its flat part (the hours `rows`), at most `top`: the voltage falls as
        the current rises, so a bisection (40 halvings of at most a few tens of amperes)."""
        low, high = np.zeros(len(rows)), np.asarray(top, dtype=float).copy()
        for _iteration in range(40):
            mid = (low + high) / 2
            above = self.voltage(mid, rows) >= voltage
            low, high = np.where(above, mid, low), np.where(above, high, mid)
        return np.where(self.voltage(high, rows) >= voltage, high, low)


def mixed_curve(string: OptimizedString | None, plain: iv.Curve | None, points: int = iv.POINTS) -> iv.Curve:
    """The I/V curve of a string with optimizers on some of its modules only (R456, Daniel's answer 6 of 06/11/2026):
    at each current of the string the plain modules give the voltage of their curve (bypassed beyond their own current),
    each optimizer its input's power at that current times its efficiency over the current, never above its output's
    most voltage nor its module's open circuit voltage (they only lower the voltage). Sampled from the most current of
    either part down to zero, so that the inverter's MPPT finds its point on it as on a plain string, within its window
    and currents. A string of optimizers alone (on an inverter with some strings partial) is the same curve without the
    plain part."""
    tops = []
    if plain is not None:
        tops.append(plain.current[:, 0])
    if string is not None:
        tops.append(1.25 * string.saturation + 1e-6)
    top = np.maximum.reduce(tops)
    current = top[:, None] * np.linspace(1, 0, points)
    voltage = np.zeros_like(current)
    if plain is not None:
        voltage += iv.voltage_at(plain, current)
    if string is not None:
        for u, count in string.inputs:
            ceiling = u.curve.voltage[:, -1]
            if string.v_out:
                ceiling = np.minimum(ceiling, string.v_out)
            for j in range(points):
                at = np.maximum(current[:, j], 1e-9)
                v = string.eta * available_power(u, at) / at
                voltage[:, j] += count * np.minimum(v, ceiling)
    voltage = np.maximum.accumulate(voltage, axis=1)
    return iv.Curve(voltage, current)


def tracking(unit):
    """The optimizers (optimizer_strings.Setup) of an inverter with MPPT whose year is computed optimizer by optimizer:
    the optimizers proper (Huawei, Sungrow, Tigo TS4-A-O); None for the devices of safety alone, computed as the plain
    string they are, and for an inverter without."""
    setup = getattr(unit, 'mlpe', None)
    return setup if setup is not None and setup.family.function == "optimizer" else None


def optimized_operating_point(strings: list, v_min: float, v_max: float | None, i_limit: float | None,
                              i_connector: float | None):
    """The operating point of an MPPT whose strings all have power optimizers (R456): (voltage, [current of each
    string], [power of each string]), hour by hour. With every optimizer at its maximum power the string's output is
    the same over a span of voltages (the optimizers move the voltage, the power stays): the MPPT takes the highest
    voltage of that span within its window, the least current and the least DC wiring loss [I: the program's choice, a
    tracker on a flat curve may sit anywhere on it]; on a long string that is the inverter's own most voltage, never
    beyond. When the window or the currents (the optimizers' output, the connector, the MPPT's) leave no point of full
    power, the voltage nearest to it: there the strings' currents are solved exactly, and what the currents still
    exceed is curtailed."""
    hours = len(strings[0].full)
    caps = [min(c for c in (s.i_out, i_connector) if c) if (s.i_out or i_connector) else np.inf for s in strings]
    lit = [s.full > 0 for s in strings]
    flats = [np.where(on, s.full / np.where(s.saturation > 0, s.saturation, np.inf), np.inf) for s, on in
             zip(strings, lit, strict=True)]
    flat = np.minimum.reduce(flats)
    top = np.minimum(flat, v_max) if v_max else flat
    low = np.full(hours, float(v_min or 0.0))
    for s, cap in zip(strings, caps, strict=True):
        low = np.maximum(low, s.full / cap)
    total = sum(s.full for s in strings)
    if i_limit:
        low = np.maximum(low, total / i_limit)
    easy = low <= top
    voltage = np.where(easy, top, np.minimum(low, v_max) if v_max else low)
    voltage = np.where(np.isfinite(voltage) & (total > 0), voltage, 0.0)

    def solved(voltage, rows):
        """The strings' currents at `voltage` on the hours `rows`, uncapped: full power up to each one's flat part,
        solved on the curves beyond it."""
        out = []
        for s, cap, f in zip(strings, caps, flats, strict=True):
            current = np.divide(s.full[rows], voltage, out=np.zeros(len(rows)), where=voltage > 0)
            beyond = np.flatnonzero((voltage > f[rows]) & (voltage > 0) & np.isfinite(f[rows]))
            if beyond.size:
                at = rows[beyond]
                top_current = np.minimum(s.saturation[at], cap) if np.isfinite(cap) else s.saturation[at]
                current[beyond] = s.current_at(voltage[beyond], at, top_current)
            out.append(current)
        return out

    # where the currents (not the window's floor) push the voltage above the full power span, the lowest voltage at
    # which the strings' actual currents fit: beyond its flat part a string's current falls faster than at full power
    upper = np.minimum(low, v_max) if v_max else low
    floor = np.maximum(top, float(v_min or 0.0))
    search = np.flatnonzero(~easy & (total > 0) & np.isfinite(upper) & (upper > floor + 1e-9))
    if search.size:
        lo_v, hi_v = floor[search], upper[search]
        for _iteration in range(30):
            mid = (lo_v + hi_v) / 2
            found = solved(mid, search)
            fits = np.ones(len(search), dtype=bool)
            for current, cap in zip(found, caps, strict=True):
                fits &= current <= cap + 1e-9
            if i_limit:
                fits &= sum(found) <= i_limit + 1e-9
            lo_v, hi_v = np.where(fits, lo_v, mid), np.where(fits, mid, hi_v)
        voltage[search] = hi_v
    every = np.arange(hours)
    currents, powers = [], []
    for current, cap in zip(solved(voltage, every), caps, strict=True):
        currents.append(np.minimum(current, cap))
    if i_limit:
        summed = sum(currents)
        factor = np.minimum(1.0, np.divide(i_limit, summed, out=np.ones(hours), where=summed > 0))
        currents = [c * factor for c in currents]
    for current in currents:
        powers.append(voltage * current)
    return voltage, currents, powers


def _row_key(ap, pm, front=None):
    """What the row shade of a module depends on besides the hours: None for a module the rows leave clear (a
    single row, the front row), else its level in the stack. Modules with the same key share their cohorts."""
    if ap.a.rows <= 1 or ap.row_share is None:
        return None
    if pm.row == (front if front is not None else min(p.row for p in ap.a.placed)):
        return None
    return getattr(pm, 'level', 0)


def _row_cohorts(ap, pm, hours, front=None):
    """Cell-row shade of an infinite row approximation, preserving the actual module stack level."""
    nb = ap.layout[0] * ap.layout[1]
    result = np.zeros((len(hours), nb, nearshade.CELL_LEVELS))
    result[..., 0] = 1
    if _row_key(ap, pm, front) is None:
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


def _obstacle_index(ap, pm, indices=None):
    """The module's index in the obstacles' shading table, or None when the obstacles never shade it: not in the
    table, or without a cell histogram where the cells are resolved (cell_cohorts then gives the clear cohort,
    exactly the one `_row_cohorts` starts from). `indices` is the table's key -> index, made once per array."""
    if ap.near is None:
        return None
    if indices is not None:
        index = indices.get(pm.key)
    else:
        index = ap.near.keys.index(pm.key) if pm.key in ap.near.keys else None
    if index is None:
        return None
    if index not in ap.near.cell_histograms and (ap.near.cell_resolved or ap.near.block_fractions is None):
        return None
    return index


def _cohorts(ap, pm, hours, first, front=None, indices=None):
    result = _row_cohorts(ap, pm, hours, front)
    index = _obstacle_index(ap, pm, indices)
    if index is None:
        return result
    obstacle = nearshade.cell_cohorts(ap.near, index, first.sun_az[hours], first.sun_el[hours])
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


def _module_curve(a, irradiance, temperature, layout, fractions, known):
    """iv.module_curve of a module over a chunk of hours, each hour another module of the array already had taken
    from it (R266, under the obstacles' shade: a module is in a chimney's shadow a few hours of a chunk, and the
    other hours are those of its neighbours in the same row of the table).

    Exact: module_curve decides a few things over the whole chunk (iv.CurvePlan) and then works hour by hour; an
    hour's curve depends only on the hour's light and temperature (the same for every module of an array), its
    cohorts and `CurvePlan.hourly`. `known` keeps, for each array and `hourly`, the hours computed in this chunk by
    their cohorts; the hours not found are computed together, with this module's own plan."""
    plan = iv.curve_plan(a.module, irradiance, temperature, layout, cell_fractions=fractions)
    store = known.setdefault((a.key, plan.hourly), {})
    keys = [(h, fractions[h].tobytes()) for h in range(len(fractions))]
    todo = [h for h, key in enumerate(keys) if key not in store]
    if len(todo) == len(keys):
        curve = iv.module_curve(a.module, irradiance, temperature, layout, cell_fractions=fractions, plan=plan)
    elif todo:
        curve = iv.module_curve(a.module, irradiance[todo], temperature[todo], layout, cell_fractions=fractions[todo],
                                plan=plan)
    else:
        curve = None
    if curve is not None:
        for i, h in enumerate(todo):
            store[keys[h]] = curve.voltage[i], curve.current[i]
        if len(todo) == len(keys):
            return curve
    return iv.Curve(np.stack([store[key][0] for key in keys]), np.stack([store[key][1] for key in keys]))


@dataclass
class _Year:
    """What of the first pass the chunks read: its arrays, the losses, the sun. Not the weather nor the calendar
    (pandas, half a second to import in each worker process, R435)."""
    per_array: list
    losses: object
    sun_az: np.ndarray
    sun_el: np.ndarray
    hours: int


@dataclass
class _Job:
    """What a chunk of hours needs of the year and the plant, found once in `solve` and written once for the
    worker processes (R435): the first pass, the inverters and strings that generate, where each module is, and
    what makes two modules' hours alike (`shapes_of`)."""
    first: _Year
    units: dict
    runs: list
    location: dict
    shapes_of: dict
    front: dict
    indices: dict
    groups: list = field(default_factory=list)      # the runs in the groups a part is made of (`_groups_of`, R478)

    def __post_init__(self):
        if not self.groups:
            self.groups = _groups_of(self)


@dataclass
class _Chunk:
    """What one chunk of hours gives back, for its hours only: merged into the year by `solve`."""
    take: np.ndarray
    stages: dict = field(default_factory=dict)       # array key -> stage -> power of the chunk's hours
    reference: dict = field(default_factory=dict)
    at25: dict = field(default_factory=dict)
    nominal: dict = field(default_factory=dict)
    dc: dict = field(default_factory=dict)           # inverter number -> power of the chunk's hours
    notes: list = field(default_factory=list)


def solve(first, plant, progress=None, workers: int | None = None) -> Network:
    """Return electrical stages and DC by inverter; disconnected or invalid references never generate.
    `progress(share)` is called before each chunk of hours with the share already done (0 to 1); it may raise to
    stop the computation there. The chunks of hours are independent: on a plant large enough they are computed
    by `workers` processes at once (`resources.workers_for` when None, R435), each with the same operations on the
    same numbers as one after the other. What each inverter gives over each chunk is kept (`_PARTS`, R478) by what
    it was made of: the next year computes again only the inverters whose strings, modules, light or shade changed."""
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
    # What makes two modules' hours alike, found once for the year (R266: the front row of each array was
    # searched again for every module of every chunk, quadratic in the modules): the row shade depends only on
    # the module's level in the stack behind the front row, the obstacles' only on the module itself. Modules
    # with the same shape share one computation of their cohorts in each chunk; nothing is averaged.
    front = {ap.a.key: min((p.row for p in ap.a.placed), default=0) for ap in first.per_array}
    indices = {ap.a.key: {k: i for i, k in enumerate(ap.near.keys)} for ap in first.per_array if ap.near is not None}

    def shape_of(ap, pm):
        index = _obstacle_index(ap, pm, indices.get(ap.a.key))
        return (ap.a.key, 'obstacle', index) if index is not None else (
            ap.a.key, 'rows', _row_key(ap, pm, front[ap.a.key]))
    shapes_of = {key: shape_of(ap, pm) for key, (ap, pm) in location.items()}
    year = _Year(first.per_array, first.losses, first.sun_az, first.sun_el, first.hours)
    job = _Job(year, units, runs, location, shapes_of, front, indices)
    takes = [daylight[start:start + CHUNK_HOURS] for start in range(0, len(daylight), CHUNK_HOURS)]
    # each group's mark: its inverter, its runs, its modules and everything their arrays' first pass gives them
    # (light, shade, temperature, the module): the same mark, the same part of each chunk (R478)
    import time
    started = time.perf_counter()
    marks = _group_marks(job)
    _STATS['marks_s'] += time.perf_counter() - started
    keys = [{number: resources.fingerprint(take.tobytes(), mark) for number, mark in marks.items()} for take in takes]
    found = [{} for _take in takes]
    todo = []
    for t, take_keys in enumerate(keys):
        for number, key in take_keys.items():
            part = _PARTS.get(key)
            if part is not None:
                found[t][number] = part
        missing = [number for number in take_keys if number not in found[t]]
        if missing:
            todo.append((t, missing))
    _STATS['kept'] += sum(len(f) for f in found)
    _STATS['made'] += sum(len(m) for _t, m in todo)
    if workers is None:
        weight = len(todo) * sum(len(runs[i].modules) for index in {n for _t, m in todo for n in m}
                                 for i in job.groups[index][2])
        workers = resources.workers_for(len(todo), weight=weight)
    if progress is not None:
        progress(0.0)
    made = _parts_in_order(job, takes, list(todo), max(1, workers))
    waiting = {t for t, _missing in todo}
    try:
        for count, take in enumerate(takes, start=1):
            if count - 1 in waiting:
                parts, seconds = next(made)
                _STATS['parts_s'] += seconds
                for number, part in parts.items():
                    _PARTS.put(keys[count - 1][number], part, cost=seconds / max(1, len(parts)))
                    found[count - 1][number] = part
            merging = time.perf_counter()
            chunk = _merge(job, take, found[count - 1])
            _STATS['merge_s'] += time.perf_counter() - merging
            if progress is not None and count < len(takes):
                progress(count / len(takes))
            take = chunk.take
            for key, stages in chunk.stages.items():
                for stage, power in stages.items():
                    out.stages[key][stage][take] += power
            for name in ('reference', 'at25', 'nominal'):
                for key, value in getattr(chunk, name).items():
                    getattr(out, name)[key][take] += value
            for number, dc in chunk.dc.items():
                out.dc[number][take] = dc
            for note in chunk.notes:
                if note not in out.notes:
                    out.notes.append(note)
    finally:
        made.close()
    return out


_STATS = {'kept': 0, 'made': 0, 'marks_s': 0.0, 'parts_s': 0.0, 'merge_s': 0.0, 'job_s': 0.0, 'job_mb': 0.0}          # parts of chunks found kept, and made, since the process started (R478)


def _group_marks(job: _Job) -> dict:
    """group index -> what that group's part of a chunk is made of, as a digest: the hours of the year (sun,
    losses), the inverter, the group's runs, their modules found in the arrays, and those arrays' whole first pass
    (their light, shade, cohorts' tables, temperatures, module, placement). A change of one sub-field changes the
    marks of the strings with modules on it, not the others'; a change of an inverter, the marks of its strings."""
    first = job.first
    # the language too: the notes of a part are in the language of when it was made
    year = resources.fingerprint(_MARK_VERSION, _("{name}: hourly limits unavailable: {fields}; those limits are not "
                                                  "enforced."), first.sun_az, first.sun_el, first.losses, first.hours)
    digests = {}
    marks = {}
    for index, (number, kind, indices) in enumerate(job.groups):
        runs = [job.runs[i] for i in indices]
        refs = [[tuple(ref[:2]) for ref in run.modules if tuple(ref[:2]) in job.location] for run in runs]
        touched = sorted({job.location[k][0].a.key for r in refs for k in r})
        for key in touched:
            if key not in digests:
                ap = next(ap for ap in first.per_array if ap.a.key == key)
                digests[key] = resources.fingerprint(ap, job.front.get(key))
        marks[index] = resources.fingerprint(year, job.units[number], kind, runs, refs,
                                             [(key, digests[key]) for key in touched])
    return marks


_MARK_VERSION = 'r478-2'        # changed with the computation of a part, so that nothing kept before answers


def _part_bytes(part) -> int:
    total = 64 * (len(part.events) + len(part.flows) + len(part.currents) + sum(map(len, part.calls)))
    total += sum(e[3].nbytes for e in part.events) + sum(c[1].nbytes for c in part.currents)
    total += sum(f[2].nbytes + f[3].nbytes + sum(s.nbytes for _k, s in f[1]) for f in part.flows)
    total += sum(sum(v.nbytes for v in values) for values in part.values.values())
    return total


_PARTS = resources.Cache(lambda: resources.cache_limit("network"), _part_bytes)


def _parts_in_order(job: _Job, takes: list, todo: list, workers: int):
    """For each (chunk, inverters) of `todo`, in order: ({number: part}, seconds). Here, or from `workers` processes
    (`resources.pool`, kept for the next computation) that each read the job once from a file (R435: a file read by
    every worker costs less than a pickle sent to each through its pipe). A stop asked by the caller (an exception
    out of `progress`) closes the iterator: the chunks not started are cancelled, the workers end the ones in hand."""
    if not todo:
        return
    if workers <= 1 or len(todo) <= 1:
        for t, numbers in todo:
            yield _timed_parts(job, takes[t], numbers)
        return
    import pickle
    import tempfile
    import time
    started = time.perf_counter()
    with tempfile.NamedTemporaryFile(prefix='meridiana-rete-', suffix='.pkl', delete=False) as f:
        data = pickle.dumps(job, protocol=5)
        f.write(data)
        path = f.name
    _STATS['job_s'] += time.perf_counter() - started
    _STATS['job_mb'] += len(data) / 1e6
    del data
    try:
        pool = resources.pool(min(workers, len(todo)))
        yield from pool.map(_parts_of_file, [(path, takes[t], numbers) for t, numbers in todo])
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


_JOBS: dict = {}


def _parts_of_file(args):
    path, take, numbers = args
    job = _JOBS.get(path)
    if job is None:
        import pickle
        _JOBS.clear()
        with open(path, 'rb') as f:
            job = _JOBS[path] = pickle.load(f)
    return _timed_parts(job, take, numbers)


def _timed_parts(job, take, numbers):
    import time
    start = time.perf_counter()
    parts = _parts(job, take, numbers)
    return parts, time.perf_counter() - start


def _chunk(job: _Job, take) -> _Chunk:
    """The electrical network over one chunk of daylight hours, every inverter: the same operations on the same
    numbers as the loop of `solve` before R435, the sums kept apart for the chunk's hours."""
    return _merge(job, take, _parts(job, take, range(len(job.groups))))


def _point_powers(a, mean, temperature, store):
    """The maximum power of the one-diode module (every cell in the same light) at each hour's mean irradiance
    and temperature, hour by hour as `iv.mpp(iv.module_curve(...))` gives it: an hour already found in `store` for
    the same light and temperature is read from it (R435: a module shaded a few hours of the chunk shares the
    other hours' with every unshaded module of its array)."""
    keys = [(a.key, mean[h].tobytes(), temperature[h].tobytes()) for h in range(len(mean))]
    todo = [h for h, key in enumerate(keys) if key not in store]
    if todo:
        power = iv.mpp(iv.module_curve(a.module, mean[todo, None], temperature[todo], (1, 1))).power
        for i, h in enumerate(todo):
            store[keys[h]] = power[i]
    return np.array([store[key] for key in keys])


class _Part:
    """What one group of strings gives over one chunk of hours (R478): a string on optimizers at a fixed voltage, or
    the strings of one MPPT. Kept from one year to the next while what it is made of stays the same, and merged with
    the other groups in the order of the whole plant (`_merge`): every addition the chunk's computation made for these
    strings, with where it stood in that computation, so that the merge makes the same additions in the same order.
    `order` is (phase, sub-phase, the group's own run, sequence): `_merge` puts the run of the plant in its place.
    What the inverter's current limit cuts waits in `flows` and `currents`: it needs the inverter's other groups."""
    __slots__ = ('calls', 'values', 'events', 'flows', 'currents', 'notes')

    def __init__(self, runs):
        self.calls = [[] for _run in range(runs)]   # per run of the group: (module, array key, signature)
        self.values = {}                            # signature -> (reference, at25, nominal) of the chunk
        self.events = []                            # (order, array key, stage, power): p_el, p_opt
        self.flows = []                             # (order, shares, power, dc): to p_cut and p_dc
        self.currents = []                          # (order, current): to the inverter's current
        self.notes = []                             # (order, text)


class _Memo:
    """What the groups of one chunk share while it is computed: the cohorts, curves and operating points of modules,
    strings and trackers alike (pure: shared only to compute them once)."""

    def __init__(self):
        self.cache, self.module_data, self.sig_of, self.values_of = {}, {}, {}, {}
        self.shapes, self.known, self.points = {}, {}, {}
        self.trackers, self.strings_of, self.inputs_of = {}, {}, {}


def _groups_of(job) -> list:
    """The plant's runs in the groups a part is made of: (inverter, 'run', [run]) for a string at a fixed voltage,
    (inverter, 'mppt', [runs]) for the strings of one MPPT; runs without a module laid are in none."""
    groups, at = [], {}
    for i, run in enumerate(job.runs):
        if not any(tuple(ref[:2]) in job.location for ref in run.modules):
            continue
        if job.units[run.inverter].optimized:
            groups.append((run.inverter, 'run', [i]))
            continue
        key = (run.inverter, run.mppt)
        if key not in at:
            at[key] = len(groups)
            groups.append((run.inverter, 'mppt', []))
        groups[at[key]][2].append(i)
    return groups


def _parts(job: _Job, take, indices) -> dict:
    """group index -> _Part over the chunk `take`, for the groups `indices` of job.groups."""
    memo = _Memo()
    t_at25 = np.full(len(take), 25.)
    return {g: _part(job, take, job.groups[g], memo, t_at25) for g in indices}


def _part(job: _Job, take, group, memo: _Memo, t_at25) -> _Part:
    """One group over one chunk of daylight hours: the computation of `_chunk` before R478 for its runs, each addition
    recorded with its place instead of made."""
    import hashlib
    import itertools
    first, units, location = job.first, job.units, job.location
    arrays = {ap.a.key: ap for ap in first.per_array}
    losses = first.losses
    number, kind, indices = group
    runs = [job.runs[i] for i in indices]
    unit = units[number]
    part = _Part(len(runs))
    cache, module_data, sig_of, shapes, known, points = (memo.cache, memo.module_data, memo.sig_of, memo.shapes,
                                                         memo.known, memo.points)
    sequence = itertools.count()
    here = [0]                              # the group's run in hand

    def get_module(ref, optimized_single=False):
        key = tuple(ref[:2])
        memo_key = (key, optimized_single)
        if memo_key in module_data:
            part.calls[here[0]].append((key, module_data[memo_key][2], sig_of[memo_key]))
            return module_data[memo_key]
        ap, pm = location[key]
        a = ap.a
        shape = job.shapes_of[key]
        if shape not in shapes:
            fractions = _cohorts(ap, pm, take, first, job.front[a.key], job.indices.get(a.key))
            shapes[shape] = fractions, fractions.tobytes()
        fractions, raw = shapes[shape]
        signature = (a.key, optimized_single, raw)
        named = (a.key, optimized_single, hashlib.blake2b(raw, digest_size=16).digest())
        if signature not in cache:
            shade = np.linspace(0, 1, fractions.shape[2])
            beam, diffuse = ap.beam_clear[take], ap.diffuse_eff[take]
            irradiance = np.broadcast_to(diffuse[:, None, None] + beam[:, None, None] * (1 - shade),
                                         fractions.shape)
            # The comparison switch attenuates contrast toward the legacy array-mean irradiance.
            strength = np.clip(losses.electrical_fraction / 100, 0, 1) if losses.electrical_shading else 0
            if strength < 1:
                irradiance = strength * irradiance + (1 - strength) * ap.g_eff[take, None, None]
            curve = _module_curve(a, irradiance, ap.t_cell[take], ap.layout, fractions, known)
            mean = (irradiance * fractions).sum(axis=2).mean(axis=1)
            independent = iv.mpp(curve).power
            uniform_cells = np.all((fractions == 0) | (np.abs(irradiance - mean[:, None, None]) < 1e-10))
            reference = independent if uniform_cells else _point_powers(a, mean, ap.t_cell[take], points)
            at25 = _point_powers(a, mean, t_at25, points)
            mismatch = 0 if optimized_single else losses.mismatch
            factor = (1 - losses.quality / 100) * (1 - ap.lid / 100) * (1 - mismatch / 100)
            curve = iv.Curve(curve.voltage, curve.current * max(0, factor))
            cache[signature] = curve, independent * max(0, factor), reference, at25, a.module.pmax * mean / 1000
            memo.values_of[named] = (reference, at25, a.module.pmax * mean / 1000)
        curve, ideal, _reference, _at25, _nominal = cache[signature]
        sig_of[memo_key] = named
        module_data[memo_key] = (curve, ideal, a.key)
        part.calls[here[0]].append((key, a.key, named))
        return module_data[memo_key]

    allocations = {}

    def shares_of(data, power):
        """The modules of `data` by their ideal power, summed by array first (the modules' shares of one array add
        up to the array's), once for each list of modules."""
        found = allocations.get(id(data))
        if found is None:
            denominator = sum(d[1] for d in data)
            weights = {}
            for _curve, weight, key in data:
                weights[key] = weights[key] + weight if key in weights else weight
            found = allocations[id(data)] = (data, [(key, np.divide(weight, denominator, out=np.zeros_like(power),
                                                                    where=denominator > 0))
                                                    for key, weight in weights.items()])
        return found[1]

    def allocate(data, power, stage, place):
        for key, share in shares_of(data, power):
            part.events.append(((*place, next(sequence)), key, stage, power * share))

    def flow(place, data, power, dc):
        part.flows.append(((*place, next(sequence)), shares_of(data, power), power, dc))

    strings_of = memo.strings_of

    def series_of(curves):
        """A string's curve; strings of the same module curves in the same order are the same string."""
        key = tuple(map(id, curves))
        if key not in strings_of:
            strings_of[key] = iv.series(curves), curves
        return strings_of[key][0]

    def note(text, place):
        part.notes.append(((*place, next(sequence)), text))

    strings = []                        # the MPPT's strings: (string, data)
    inputs_of = memo.inputs_of
    tracked = kind == 'mppt' and tracking(unit) is not None
    # R456: with optimizers on some modules of a string the MPPT's strings are curves (mixed_curve), found as plain ones
    partial = tracked and any(getattr(run, 'optimized', None) is not None for run in runs)
    safety = None                       # efficiency of devices of safety alone (Tigo TS4-A-S, F, 2F)
    for j, run in enumerate(runs):
        here[0] = j
        refs = [ref for ref in run.modules if tuple(ref[:2]) in location]
        if not refs:
            continue
        if unit.optimized and (unit.choice is None or not unit.fixed or not unit.fixed.v_string):
            note(_("{name}: optimizer or fixed-voltage data are missing; this inverter's electrical "
                   "production is not calculated and contributes zero.").format(name=unit.name), (0, 0, j))
            continue
        if unit.optimized and unit.choice is not None:
            choice = unit.choice
            opt = choice.optimizer
            groups = optimizers.module_groups(refs, choice.per, getattr(run, 'optimizer_group_sizes', None))
            powers, data = [], []
            for group_refs in groups:
                group_data = [get_module(ref, len(group_refs) == 1) for ref in group_refs]
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
                allocate(data, value, stage, (0, 0, j))
            flow((4, 0, j), data, cut, dc)
            part.currents.append(((0, 0, j, next(sequence)), cut / unit.fixed.v_string))
            missing = [label for name, label in (('v_in_min', _("minimum input voltage")),
                                                 ('v_in_max', _("maximum input voltage")),
                                                 ('v_out_max', _("maximum output voltage")),
                                                 ('i_in_max', _("maximum input current")),
                                                 ('i_out_max', _("maximum output current")))
                       if not getattr(opt, name)]
            if missing:
                note(_("{name}: hourly limits unavailable: {fields}; those limits are not enforced.").format(
                    name=opt.name, fields=', '.join(missing)), (0, 0, j))
        elif tracked and partial and not getattr(run, 'optimized', None):
            # R456: a string of this inverter without optimizers
            data = [get_module(ref) for ref in refs]
            strings.append((series_of([d[0] for d in data]), data))
        elif tracked:
            # power optimizers on an inverter with MPPT (R456): every module of the string on one, the optimizer of
            # the inverter's entry; on some modules only when the string names them (`optimized`, partial use)
            setup = unit.mlpe
            opt = setup.optimizer
            chosen = getattr(run, 'optimized', None)
            plain_refs = []
            if chosen is not None:
                named = set(chosen)
                plain_refs = [ref for ref in refs if f"{ref[0]}/{ref[1]}" not in named]
                refs = [ref for ref in refs if f"{ref[0]}/{ref[1]}" in named]
            groups = optimizers.module_groups(refs, setup.per, getattr(run, 'optimizer_group_sizes', None)
                                              if chosen is None else None)
            data, inputs = [], {}
            for group_refs in groups:
                group_data = [get_module(ref, len(group_refs) == 1) for ref in group_refs]
                data.extend(group_data)
                curves = [d[0] for d in group_data]
                key = (tuple(map(id, curves)), opt.name)
                if key not in inputs_of:
                    curve = (curves[0] if len(curves) == 1 else
                             iv.parallel(curves) if opt.parallel_inputs else iv.series(curves))
                    inputs_of[key] = optimizer_input(curve, opt)
                found = inputs_of[key]
                inputs[id(found)] = (found, inputs[id(found)][1] + 1 if id(found) in inputs else 1)
            string = OptimizedString(list(inputs.values()), opt.eta, opt.v_out_max, opt.i_out_max or None)
            if partial:
                plain_data = [get_module(ref) for ref in plain_refs]
                data.extend(plain_data)
                plain = series_of([d[0] for d in plain_data]) if plain_data else None
                key = ('mixed', id(string), id(plain))
                if key not in inputs_of:
                    inputs_of[key] = mixed_curve(string, plain), string, plain
                strings.append((inputs_of[key][0], data))
            else:
                strings.append((string, data))
        else:
            data = [get_module(ref) for ref in refs]
            strings.append((series_of([d[0] for d in data]), data))
            setup = getattr(unit, 'mlpe', None)
            if setup is not None and setup.family.function == "safety":
                safety = setup.optimizer.eta
    part.values = {call[2]: memo.values_of[call[2]] for calls in part.calls for call in calls}
    if not strings:
        return part
    mppt = runs[0].mppt
    spec = unit.spec
    limit = spec.current_limit(mppt - 1, len(strings))
    maximum = min(v for v in (spec.vmppt_max, spec.vdc_max) if v) if (spec.vmppt_max or spec.vdc_max) else None
    connector_limit = spec.connector_current_limit(mppt - 1)
    ports = spec._limit(spec.inputs_per_mppt, mppt - 1)
    if not tracked or partial:
        place = (2, 0, 0)
        missing = [label for label, value in (('MPPT minimum voltage', spec.vmppt_min),
                                              ('MPPT maximum voltage', spec.vmppt_max),
                                              ('MPPT operating current', limit)) if value is None]
        if missing:
            note(_("{name}, MPPT {mppt}: operating limits unavailable: {fields}; the available bounds are "
                   "applied, but this operating window is not fully verified.").format(
                name=unit.name, mppt=mppt, fields=', '.join(missing)), place)
        if connector_limit and ports and len(strings) > ports:
            limit = min(limit or np.inf, ports * connector_limit)
            note(_("{name}, MPPT {mppt}: external parallel strings have no connector mapping. The aggregate "
                   "connector capacity is enforced, but current sharing among physical connectors is "
                   "not verified.").format(name=unit.name, mppt=mppt), place)
        # the operating point depends only on the strings' curves and the tracker's limits: trackers with the
        # same strings and limits (identical inverters) share it
        key = (tuple(id(string) for string, _data in strings), spec.vmppt_min or 0., connector_limit, maximum,
               limit)
        trackers = memo.trackers
        if key not in trackers:
            floor = np.full(len(take), spec.vmppt_min or 0.)
            if connector_limit:
                for string, _data in strings:
                    floor = np.maximum(floor, iv.voltage_at(string, np.full((len(take), 1),
                                                                            connector_limit))[:, 0])
            curve = iv.parallel([s[0] for s in strings])
            trackers[key] = iv.mpp(curve, voltage_min=floor, voltage_max=maximum, current_max=limit), {}
        op, at_op = trackers[key]
        part.currents.append(((*place, next(sequence)), op.current))
        for string, data in strings:
            if id(string) not in at_op:
                at_op[id(string)] = iv.current_at(string, op.voltage[:, None])[:, 0]
            current = at_op[id(string)]
            power = op.voltage * current
            if safety is None:
                for stage in ('p_el', 'p_opt'):
                    allocate(data, power, stage, place)
            else:
                # a device of safety alone passes the module's power through, with its small loss (R456)
                allocate(data, power, 'p_el', place)
                power = power * safety
                allocate(data, power, 'p_opt', place)
            stc = sum(arrays[d[2]].a.module.pmax for d in data)
            imp = max(arrays[d[2]].a.module.imp for d in data)
            dc = np.maximum(power - losses.dc_wiring / 100 * stc * (current / max(imp, 1e-9)) ** 2, 0)
            flow((4, 2, 0), data, power, dc)
        return part
    place = (3, 0, 0)
    if connector_limit and ports and len(strings) > ports:
        limit = min(limit or np.inf, ports * connector_limit)
    if unit.mlpe.long_string:
        # Huawei's long strings: the optimizers hold the string's voltage within the inverter's (guide DE
        # 10/11/2025 p. 9, FR 15/07/2026 p. 8); the MPPT still works within its window
        note(_("{name}: long strings of optimizers; the inverter's MPPT works within its own window, the optimizers "
               "lower each module's voltage to stay in it.").format(name=unit.name), place)
    _voltage, string_currents, string_powers = optimized_operating_point(
        [s for s, _data in strings], spec.vmppt_min or 0.0, maximum, limit, connector_limit)
    for (string, data), current, power in zip(strings, string_currents, string_powers, strict=True):
        part.currents.append(((*place, next(sequence)), current))
        allocate(data, power / max(string.eta, 1e-9), 'p_el', place)
        allocate(data, power, 'p_opt', place)
        stc = sum(arrays[d[2]].a.module.pmax for d in data)
        imp = max(arrays[d[2]].a.module.imp for d in data)
        # the DC wiring as for a plain string: its share at STC with the module's current, here the string's
        # current that the optimizers set (higher on a long string held at the inverter's voltage)
        dc = np.maximum(power - losses.dc_wiring / 100 * stc * (current / max(imp, 1e-9)) ** 2, 0)
        flow((4, 3, 0), data, power, dc)
    return part


def _merge(job: _Job, take, parts: dict) -> _Chunk:
    """The chunk of the whole plant out of its groups' parts (R478): the counts of the modules in the order of the
    plant's runs; each inverter's current, its limit and what that cuts; then every addition of every part in the
    order the single computation made them."""
    out = _Chunk(take)
    counted, tally, values = set(), {}, {}
    for _g, which, j in sorted((g, i, j) for i in parts for j, g in enumerate(job.groups[i][2])):
        part = parts[which]
        for key, array_key, signature in part.calls[j]:
            if key not in counted:
                counted.add(key)
                tally[(array_key, signature)] = tally.get((array_key, signature), 0) + 1
                values.setdefault(signature, part.values[signature])
    for (array_key, signature), n in tally.items():
        reference, at25, nominal = values[signature]
        for name, value in (('reference', reference), ('at25', at25), ('nominal', nominal)):
            store = getattr(out, name)
            store[array_key] = store[array_key] + n * value if array_key in store else n * value

    def placed(order, runs):
        return (order[0], order[1], runs[order[2]], order[3])
    events, notes, flows, currents = [], [], defaultdict(list), defaultdict(list)
    for index, part in parts.items():
        number, _kind, runs = job.groups[index]
        events.extend((placed(o, runs), key, stage, power) for o, key, stage, power in part.events)
        notes.extend((placed(o, runs), text) for o, text in part.notes)
        flows[number].extend((placed(o, runs), shares, power, dc) for o, shares, power, dc in part.flows)
        currents[number].extend((placed(o, runs), current) for o, current in part.currents)
    for number, items in flows.items():
        items.sort(key=lambda f: f[0])
        current = np.zeros(len(take))
        for _order, value in sorted(currents[number], key=lambda c: c[0]):
            current += value
        total = job.units[number].spec.imax_total
        factor = np.minimum(1, total / np.maximum(current, 1e-9)) if total else 1
        dc_sum = np.zeros(len(take))
        for order, shares, power, dc in items:
            cut, kept = power * factor, dc * factor
            for key, share in shares:
                events.append((order, key, 'p_cut', cut * share))
            for key, share in shares:
                events.append((order, key, 'p_dc', kept * share))
            dc_sum += dc
        out.dc[number] = dc_sum * factor
        if total and np.any(factor < 1):
            notes.append(((5, 0, 0, 0), _("A shared inverter DC-current limit curtails its MPPT powers "
                                          "proportionally; optimal redistribution between trackers is not simulated.")))
    events.sort(key=lambda e: e[0])
    for _order, key, stage, power in events:
        stages = out.stages.setdefault(key, {})
        if stage in stages:
            stages[stage] += power
        else:
            stages[stage] = power.copy()
    notes.sort(key=lambda n: n[0])
    for _order, text in notes:
        if text not in out.notes:
            out.notes.append(text)
    return out
