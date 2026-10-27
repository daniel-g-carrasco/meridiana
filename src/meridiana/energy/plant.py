"""The plant (task 16d; study 16, D.5-D.7): the inverters as units with their inputs (MPPT), the strings on the
modules laid and on the inputs, and the checks of every string, input and inverter, made again at each change in a
few milliseconds. No Qt here: the window draws and edits what `build` gives, the energy job lays the same strings
on the modules for the electrical effect of the shade.

- The strings are the designer's (energy["strings"]["runs"]): each module by its id, "sub-field/row:slot" with the
  row's id (task 16c: it stays while the row does, moved or exploded); a key no longer laid is said lost, with its
  string. Nothing makes or changes them by itself (R114, R118, Daniel 25/10/2026): an inverter, a module or a
  sub-field added or changed leaves the modules it brings in no string, and the checks say so.
- Meridiana proposes them only when asked (`propose`, «Propose the strings», once): the modules of each array (one
  sub-field, one orientation) in strings by the strategy chosen, the strings of an array spread over the inputs as
  PVsyst spreads them (identical strings on an input; 10 strings on 3 MPPT, 3 + 3 + 4); a sub-field whose params
  name an inverter, or an inverter and an input, goes there. «Complete» proposes only the modules in no string,
  around the designer's strings.
- A project of before format 14 kept the proposal live (energy["strings"]["auto"], the default then): `build` still
  proposes for it, and the window writes that proposal down as the designer's strings at the first layout, so that
  nothing changes under him (format 14 says «auto» only for those).
- The checks: stringing.plan for each input with its strings (CEI 64-8/7, as stringing.py cites it), the MPP voltage
  at the hottest cell of the typical year once it is computed, before it at PVsyst's design conditions (60, 20 and
  -10 °C: Daniel's choice of 23/10/2026, a program's choice, not a standard); for each inverter the DC/AC ratio, the
  loss for overload once the year is there and the inputs loaded alike; the modules in no string, by inverter.

An inverter at a fixed string voltage (SolarEdge, task 22) has power optimizers on its modules: its inputs are its
Synergy units (one for the others), its strings are of optimizers, of any length within SolarEdge's range and of
different lengths or orientations side by side; Meridiana proposes them balanced and as few as SolarEdge's limits of
power allow, and checks them by SolarEdge's tables (energy/optimizers.py) instead of the voltages.

The year is computed on all the inverters together (system.combined): an inverter for each input in the simulation
is task 18d, step 3."""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field

from ..i18n import _, ngettext
from . import optimizers, stringing, system
from .components import InverterSpec, ModuleSpec
from .pedigree import Source

DESIGN_HOT = 60.0               # °C of the cell: the lowest MPP voltage (PVsyst's design conditions)
DESIGN_WARM = 20.0              # °C of the cell: the highest MPP voltage within the window
DESIGN_COLD = -10.0             # °C: the open-circuit voltage, when the designer gave no lowest temperature


def strategy_names() -> dict:
    """The strategies of the proposal (settings.STRATEGIES), as the window names them (PVsyst's «Auto
    Attribution»)."""
    return {"serpentine": _("Back and forth along the rows"), "rows": _("One row per string"),
            "u": _("U on two rows"), "row_per_mppt": _("One row per MPPT")}


def state_names() -> dict:
    """The traffic light of a string, a word for each colour (never the colour alone)."""
    return {"ok": _("correct"), "check": _("to be checked"), "fail": _("out of the window or without input")}


@dataclass
class Unit:
    """One inverter of the plant: its number over the whole plant (from 1), the entry of energy["inverters"] it
    comes from (-1: sized by itself), its model as one unit, the name the designer gave or the model's; for an inverter
    at a fixed string voltage (SolarEdge) what it is for the optimizers' rules and the optimizers on its modules
    (chosen, or proposed by Meridiana; None when none fits the module)."""
    number: int
    entry: int
    spec: InverterSpec
    name: str
    fixed: optimizers.FixedVoltage | None = None
    choice: optimizers.Choice | None = None

    @property
    def optimized(self) -> bool:
        return self.fixed is not None

    @property
    def inputs(self) -> int:
        """Its inputs: the MPPT, or the Synergy units of an inverter at a fixed string voltage (one for the others)."""
        if self.fixed is not None:
            return max(1, self.fixed.units)
        return max(1, int(self.spec.mppt_count or 1))

    @property
    def checkable(self) -> bool:
        """With an MPPT window to check the strings against (a record of the catalogue), or with optimizers whose
        rules SolarEdge's tables give for this inverter."""
        if self.fixed is not None:
            return self.choice is not None and self.choice.rules is not None
        return bool(self.spec.vmppt_min and self.spec.vmppt_max)


@dataclass
class Group:
    """The modules of one sub-field with one orientation (system.arrays_of's arrays, with the same keys), the
    module they are, and where the sub-field sends its strings: (unit, input), 0 for «automatic»."""
    key: str
    sfid: str
    name: str
    module: ModuleSpec
    placed: list
    target: tuple = (0, 0)


@dataclass
class String:
    """A string on the modules: the inverter (unit from 1) and the input (from 1) it goes to, 0 when none; its
    modules as (sub-field id, module key, (x, y)) in the order it runs; its place on its input (from 1); its state
    for the plan's traffic light: "ok" (green, every check passed), "check" (yellow: connected, to be checked or
    with a warning), "fail" (red: out of the window, a current too high, or no input); why, in words."""
    inverter: int
    mppt: int
    modules: list
    index: int = 0
    state: str = "check"
    why: str = ""
    lost: list = field(default_factory=list)            # module keys of the designer's string no longer laid
    run: int = -1                                       # its place in energy["strings"]["runs"] (by hand)
    plan: object = None                                 # stringing.StringPlan its state comes from

    @property
    def label(self) -> str:
        """As Sunny Design and the report name it: inverter.input.string."""
        if not (self.inverter and self.mppt):
            return f"?.{self.index or 0}"
        return f"{self.inverter}.{self.mppt}.{self.index}"

    @property
    def keys(self) -> list[str]:
        return [f"{sf}/{key}" for sf, key, _c in self.modules]


@dataclass
class Input:
    """An input (MPPT) of a unit: the strings on it, how many it takes (by the short-circuit current), the modules
    in series it takes, the plan of its checks."""
    unit: int
    mppt: int
    strings: list = field(default_factory=list)          # indices into Plant.strings
    allowed: int = 0
    series: tuple = (0, 0)
    plan: stringing.StringPlan | None = None
    level: str = "ok"                                    # the worst of its checks: "ok", "warn", "fail"
    power_w: float = 0.0                                 # its DC power at STC

    @property
    def used(self) -> bool:
        return bool(self.strings)


@dataclass
class Plant:
    units: list = field(default_factory=list)           # Unit
    strings: list = field(default_factory=list)         # String
    inputs: dict = field(default_factory=dict)          # (unit, mppt) -> Input
    left: list = field(default_factory=list)            # modules in no string, as String.modules
    left_by_unit: dict = field(default_factory=dict)    # unit (0: none) -> how many modules in no string
    checks: dict = field(default_factory=dict)          # unit -> [stringing.Check] of the inverter
    notes: list = field(default_factory=list)           # what keeps the strings from being proposed or checked
    auto: bool = False                                  # a proposal of before format 14, to be written down
    strategy: str = "serpentine"
    year: bool = False                                  # the conditions of the typical year, or PVsyst's design ones
    t_cell_max: float = DESIGN_HOT
    t_cell_cold: float = DESIGN_WARM
    t_min: float = DESIGN_COLD
    p_stc_w: float = 0.0
    lost: list = field(default_factory=list)            # (label, [keys]) of the designer's strings, modules gone
    clipping: dict = field(default_factory=dict)        # unit -> % of the year's energy cut by the inverter (R62)

    def string_of(self, sfid: str, key: str) -> int:
        """The index of the string a module is in, -1 when in none."""
        for i, s in enumerate(self.strings):
            if any(sf == sfid and k == key for sf, k, _c in s.modules):
                return i
        return -1

    def unit(self, number: int) -> Unit | None:
        return self.units[number - 1] if 0 < number <= len(self.units) else None

    @property
    def optimized(self) -> bool:
        """Whether an inverter of the plant has power optimizers (SolarEdge)."""
        return any(u.optimized for u in self.units)


# the modules of a project, as groups

_MODULES: dict = {}
_LOCK = threading.Lock()


def _module(rec: dict) -> ModuleSpec:
    """The module of a record, kept: its single-diode model is fitted once (components.py caches the fit too)."""
    import json
    key = json.dumps(rec, sort_keys=True, default=str)
    with _LOCK:
        found = _MODULES.get(key)
    if found is None:
        found = ModuleSpec.from_record(rec)
        with _LOCK:
            if len(_MODULES) > 64:
                _MODULES.clear()
            _MODULES[key] = found
    return found


def _target(sf) -> tuple:
    def whole(v):
        return v if v.__class__ is int and v > 0 else 0
    return whole(sf.params.get("inverter")), whole(sf.params.get("mppt"))


def groups_of(project, results: dict) -> list[Group]:
    """The modules laid, by sub-field and orientation, in the order and with the keys of system.arrays_of (without
    what the year needs: the obstacles, the thermal case)."""
    out = []
    for sf in project.subfields:
        r = results.get(sf.id)
        if not sf.filled or r is None or isinstance(r, Exception) or not r.modules:
            continue
        by: dict = defaultdict(list)
        for pm in r.modules:
            by[(round(pm.tilt, 1), round(pm.azimuth, 1))].append(pm)
        module = _module(project.modules.get(sf.module) or {"power_kw": project.module_of(sf).power_kw})
        for i, (_k, placed) in enumerate(sorted(by.items(), key=lambda kv: kv[0][1])):
            out.append(Group(f"{sf.id}.{i}", sf.id, sf.name, module, placed, _target(sf)))
    return out


def groups_from_arrays(project, arrays: list) -> list[Group]:
    """The groups of the energy job's arrays (simulate.ArraySpec, from system.arrays_of): the same keys."""
    targets = {sf.id: _target(sf) for sf in project.subfields}
    out = []
    for a in arrays:
        sfid = a.key.split(".")[0]
        out.append(Group(a.key, sfid, a.name, a.module, a.placed, targets.get(sfid, (0, 0))))
    return out


def unit_label(u: Unit) -> str:
    return _("Inverter {n}").format(n=u.number)


def units_of(project, p_stc_w: float, module: ModuleSpec | None = None, t_min: float | None = None) -> list[Unit]:
    """Every inverter of the plant one by one (an entry of 3 is three units), numbered from 1 in the order of the
    list; none chosen, one sized at the DC/AC ratio (system.inverters_of), without the data to check strings. An
    inverter at a fixed string voltage takes its optimizers: the entry's, or the ones Meridiana proposes for `module`
    at the lowest temperature `t_min`."""
    out: list[Unit] = []
    for i, item in enumerate(system.inverter_entries(project.energy)):
        spec = InverterSpec.from_record(item["record"], count=1)
        if spec.pac <= 0:
            continue
        name = item["name"] or f"{spec.manufacturer} {spec.model}".strip()
        fixed = optimizers.fixed_voltage(item["record"])
        chosen = optimizers.choice(item, module, fixed, t_min) if fixed is not None else None
        for _n in range(item["count"]):
            out.append(Unit(len(out) + 1, i, spec, name, fixed, chosen))
    if not out:
        (spec,) = system.inverters_of(project, p_stc_w)
        out.append(Unit(1, -1, spec, spec.model))
    return out


# the modules of a group in strings: the strategies

def _rows(placed: list) -> list[list]:
    """The rows of a group (a table of two counts as two rows, lower and upper), each along its row in the order
    the row faces, the rows in their order."""
    from .. import geo
    rows: dict = {}
    for pm in placed:
        rows.setdefault((pm.row, getattr(pm, "level", 0)), []).append(pm)
    out = []
    for key in sorted(rows):
        fx, fy = geo.facing_vector(rows[key][0].azimuth)
        out.append(sorted(rows[key], key=lambda pm: -fy * pm.centre[0] + fx * pm.centre[1]))
    return out


def order(placed: list, n: int, strategy: str = "serpentine") -> tuple[list, list, list]:
    """The modules of one group in strings of `n`: (strings, the modules left out, the row each string starts on).

    - "serpentine" (PVsyst's «going back and forth»): along a row and back along the next, the strings cut along
      that path: the ends stay close and the cables short (what Meridiana did before task 16d);
    - "rows" (one row per string, «left to right»): each row on its own, strings within it; what does not fill a
      string at the end of a row stays out;
    - "u" (PVsyst's «U-connexion»): two rows at a time, a string out along the first for half its modules and back
      along the second, so that both ends are at the same side; a row left alone goes as "rows";
    - "row_per_mppt" («same row per MPPT»): the strings as "rows", and those of one row on one input (spread).
    """
    n = max(1, int(n))
    rows = _rows(placed)
    strings: list = []
    starts: list = []
    left: list = []
    if strategy in ("rows", "row_per_mppt"):
        for r, row in enumerate(rows):
            whole = len(row) // n
            for j in range(whole):
                strings.append(row[j * n:(j + 1) * n])
                starts.append(r)
            left += row[whole * n:]
        return strings, left, starts
    if strategy == "u":
        half = n // 2
        r = 0
        while r < len(rows):
            if r + 1 < len(rows) and half > 0 and n % 2 == 0:
                a, b = rows[r], rows[r + 1]
                pairs = min(len(a), len(b)) // half
                for j in range(pairs):
                    strings.append(a[j * half:(j + 1) * half] + b[j * half:(j + 1) * half][::-1])
                    starts.append(r)
                left += a[pairs * half:] + b[pairs * half:]
                r += 2
            else:
                row = rows[r]
                whole = len(row) // n
                for j in range(whole):
                    strings.append(row[j * n:(j + 1) * n])
                    starts.append(r)
                left += row[whole * n:]
                r += 1
        return strings, left, starts
    path: list = []
    first_row: list = []
    for r, row in enumerate(rows):
        path += row if r % 2 == 0 else row[::-1]
        first_row += [r] * len(row)
    whole = len(path) // n
    for j in range(whole):
        strings.append(path[j * n:(j + 1) * n])
        starts.append(first_row[j * n])
    left = path[whole * n:]
    return strings, left, starts


# the conditions of the checks

@dataclass
class Conditions:
    t_cell_max: float
    t_cell_cold: float
    t_min: float
    year: bool
    cell_source: Source
    t_min_source: Source


def conditions(project, t_cell_max_year: float | None = None, t_min_year: float | None = None) -> Conditions:
    """The temperatures the strings are checked at: the hottest cell of the typical year when it is computed (the
    MPP voltage at the coldest then at the lowest temperature, as before task 16d), else PVsyst's design conditions;
    the lowest temperature of the site the designer gave, or -10 °C."""
    from ..i18n import number
    e = project.energy or {}
    given = e.get("t_min")
    if given is not None:
        t_min, t_src = float(given), Source("input", _("given by the designer"))
    else:
        t_min = DESIGN_COLD
        seen = (_("; the typical year's is {t} °C").format(t=number(t_min_year, 1)) if t_min_year is not None else "")
        t_src = Source("default", _("Meridiana's prudent default for a minimum temperature, as PVsyst's design "
                                    "conditions; the standard asks for the lowest temperature of the site") + seen)
    if t_cell_max_year is not None:
        return Conditions(float(t_cell_max_year), t_min, t_min, True,
                          Source("computed", _("the typical year computed: its hottest cell")), t_src)
    return Conditions(DESIGN_HOT, DESIGN_WARM, t_min, False,
                      Source("default", _("PVsyst's design conditions, 60 and 20 °C of cell, until the production "
                                          "is computed (Daniel's choice of 23/10/2026, a program's choice)")), t_src)


# the plant

def _capacity(module: ModuleSpec, unit: Unit, k: int, asked: list) -> int:
    if asked:
        return max(0, int(asked[min(k, len(asked) - 1)]))
    return max(1, stringing.strings_allowed(module, unit.spec, k))


def _best_series(group: Group, units: list[Unit], cond: Conditions, strategy: str) -> int:
    """The modules in series for a group's proposal: valid on every inverter that may receive it, and leaving
    fewest modules out (the longer at a tie: fewer strings, less current)."""
    ranges = [stringing.series_range(group.module, u.spec, cond.t_min, cond.t_cell_max, cond.t_cell_cold)
              for u in units]
    if not ranges or any(not hi for _lo, hi in ranges):
        return 0
    lo, hi = max(lo for lo, _hi in ranges), min(hi for _lo, hi in ranges)
    if lo > hi:
        return 0
    rows = [len(r) for r in _rows(group.placed)]
    best = None
    for n in range(hi, lo - 1, -1):
        left = _left_out(rows, n, strategy)
        if best is None or left < best[0]:
            best = (left, n)
    return best[1] if best else 0


def _left_out(rows: list[int], n: int, strategy: str) -> int:
    """How many modules `order` leaves out, from the rows' lengths alone (a few operations for each n)."""
    if strategy in ("rows", "row_per_mppt"):
        return sum(r % n for r in rows)
    if strategy == "u":
        half, left, r = n // 2, 0, 0
        while r < len(rows):
            if r + 1 < len(rows) and half > 0 and n % 2 == 0:
                pairs = min(rows[r], rows[r + 1]) // half
                left += rows[r] + rows[r + 1] - 2 * pairs * half
                r += 2
            else:
                left += rows[r] % n
                r += 1
        return left
    return sum(rows) % n


def _allot(sizes: list[int], need: list[int], free: int) -> list[int]:
    """How many inputs each part gets out of `free`: at least what it needs while they last, the inputs to spare
    shared in proportion to its strings (never more inputs than strings)."""
    got = []
    left = free
    for want in need:
        take = min(want, left)
        got.append(take)
        left -= take
    while left > 0:
        room = [i for i, s in enumerate(sizes) if got[i] < s and got[i] > 0]
        if not room:
            break
        i = max(room, key=lambda j: (sizes[j] / got[j], -j))
        got[i] += 1
        left -= 1
    return got


def _path(placed: list, strategy: str) -> list:
    """The modules of a group in the order the strategy runs along them, for strings of any length (the optimizers):
    back and forth along the rows ("serpentine", and "u", whose turn at the end of two rows is the same path), or each
    row the same way ("rows", "row_per_mppt")."""
    rows = _rows(placed)
    if strategy in ("rows", "row_per_mppt"):
        return [pm for row in rows for pm in row]
    return [pm for r, row in enumerate(rows) for pm in (row if r % 2 == 0 else row[::-1])]


def _optimized_sizes(modules: int, unit: Unit, pmax: float, slots: int = 1) -> list[int]:
    """The modules of each string for `modules` modules on the optimizers of `unit`, spread over `slots` inputs
    (Synergy units): as few strings as SolarEdge's limits allow, as alike as they go (strings of different lengths
    are allowed, every table: «Stringhe parallele di lunghezze o orientamenti diversi: Sì»). The limits: the fewest
    and the most optimizers (and modules), the power a string may have connected with the strings each input gets.
    First within what a string carries continuously when the inverter's AC power is above it, so that nothing is
    cut at the peaks (SolarEdge advises it for the residential optimizers: Single String Design Guidelines v1.1,
    p. 5; the commercial tables allow more connected than carried, which is kept for when the fewest optimizers ask
    for it), then within the table's limit alone; the fewest optimizers are never given up for the peaks. A single
    module on the last optimizer of two."""
    ch = unit.choice
    r, per, inv = ch.rules, ch.per, unit.fixed
    n_opt = optimizers.optimizer_count(modules, per)
    if n_opt <= 0:
        return []
    advised = inv.unit_pac > r.p_cont

    def sizes_of(count: int) -> list[int]:
        mods = [per * n for n in stringing.spread(n_opt, count)]
        mods[-1] -= per * n_opt - modules
        return mods

    def fits(count: int, cap_advised: bool, shortest: bool) -> bool:
        sizes = stringing.spread(n_opt, count)
        mods = sizes_of(count)
        if max(sizes) > r.opt_max or (r.mod_max and max(mods) > r.mod_max):
            return False
        if shortest and (min(sizes) < r.opt_min or (r.mod_min and min(mods) < r.mod_min)):
            return False
        powers = [m * pmax for m in mods]
        on_each = max(1, count // max(1, slots))
        cap = optimizers.connected_limit(r, on_each, max(powers) - min(powers))[0]
        if cap_advised:
            cap = min(cap, r.p_cont)
        return max(powers) <= cap + 1e-6

    for cap_advised, shortest in ((advised, True), (False, True), (False, False)):
        for count in range(1, n_opt + 1):
            if fits(count, cap_advised, shortest):
                return sizes_of(count)
    return [per] * (n_opt - 1) + [modules - per * (n_opt - 1)]


def _propose_optimized(units: list[Unit], groups: list[Group], s: dict, out: Plant, loaded: dict | None = None) -> None:
    """Meridiana's strings on the inverters with optimizers: each sub-field's modules along the strategy's path in
    strings as few and as alike as SolarEdge's limits allow; a sub-field too small for a string of its own joins the
    others going to the same inverter (a string over two pitches is allowed, though SolarEdge says it may lose more
    than 2 %: Single String Design Guidelines v1.1, p. 1); the strings spread over the inverters and their Synergy
    units, the least loaded first for its AC power (with the power of the designer's strings already on them,
    `loaded`, when completing). An inverter whose optimizers are not known lays nothing: its modules stay out, said."""
    strategy = s.get("strategy") or "serpentine"
    usable = [u for u in units if u.checkable]
    if not usable:
        for g in groups:
            out.left += [(g.sfid, pm.key, tuple(pm.centre)) for pm in g.placed]
        return
    by_target: dict = defaultdict(list)                 # (unit number or 0, input or 0) -> groups
    for g in groups:
        unit_no, mppt = g.target
        u = units_by_number(units, unit_no)
        if u is None or not u.checkable:
            unit_no, mppt = 0, 0
        elif not 0 < mppt <= u.inputs:
            mppt = 0
        by_target[(unit_no, mppt)].append(g)
    loads: dict = defaultdict(float, loaded or {})     # (unit, input) -> W at STC already on it
    for (unit_no, mppt), mine in sorted(by_target.items()):
        unit = units_by_number(units, unit_no) or usable[0]
        need = unit.choice.rules.opt_min * unit.choice.per
        pieces = [(g, _path(g.placed, strategy)) for g in mine if len(g.placed) >= need]
        small = [(g, _path(g.placed, strategy)) for g in mine if len(g.placed) < need]
        if small:
            pieces.append((None, [(g, pm) for g, path in small for pm in path]))
        slots = ([(unit.number, mppt)] if unit_no and mppt else
                 [(unit.number, k + 1) for k in range(unit.inputs)] if unit_no else
                 [(u.number, k + 1) for u in usable for k in range(u.inputs)])
        for g, path in pieces:
            pairs = [(g, pm) for pm in path] if g is not None else path
            pmax = pairs[0][0].module.pmax if pairs else 0.0
            sizes = _optimized_sizes(len(pairs), unit, pmax, len(slots))
            at = 0
            for n in sizes:
                chunk = pairs[at:at + n]
                at += n
                slot = min(slots, key=lambda sl: (loads[sl] / max(1.0, units_by_number(units, sl[0]).fixed.unit_pac),
                                                  slots.index(sl)))
                loads[slot] += sum(gg.module.pmax for gg, _pm in chunk)
                out.strings.append(String(slot[0], slot[1], [(gg.sfid, pm.key, tuple(pm.centre)) for gg, pm in chunk]))


def units_by_number(units: list[Unit], number: int) -> Unit | None:
    return next((u for u in units if u.number == number), None)


def _propose(units: list[Unit], groups: list[Group], s: dict, cond: Conditions, out: Plant, busy: dict | None = None,
             loaded: dict | None = None, lengths: dict | None = None) -> None:
    """Meridiana's strings: each group in strings by the strategy, on the inputs its sub-field names or on the free
    ones in order, spread as PVsyst spreads them; what does not fit stays out, said. The groups going to an inverter
    with optimizers (or to any, when every inverter has them) are strung by _propose_optimized. `busy` are the strings
    the designer has on each input already (completing): an input with none comes first, then those with room for
    more strings as long as his (`lengths`, the modules of his strings on each input: PVsyst's identical strings on
    an MPPT, so that completing adds no warning); `loaded` their power, for the optimizers."""
    busy = busy or {}
    lengths = lengths or {}

    def alike(slot, n) -> bool:
        return not busy.get(slot) or lengths.get(slot) == {n}
    strategy = s.get("strategy") or "serpentine"
    asked_n = int(s.get("n_series") or 0)
    asked_per = [int(x) for x in (s.get("per_mppt") or [])]
    if any(u.optimized for u in units):
        plain = [u for u in units if not u.optimized]
        mine = [g for g in groups if (u := units_by_number(units, g.target[0])) is not None and u.optimized
                or (units_by_number(units, g.target[0]) is None and not plain)]
        _propose_optimized([u for u in units if u.optimized], mine, s, out, loaded)
        groups = [g for g in groups if g not in mine]
        if not groups:
            return
    inputs = [(u.number, k + 1) for u in units if not u.optimized for k in range(u.inputs)]
    used: dict = defaultdict(int, busy)                 # (unit, mppt) -> strings on it
    taken: set = set()                                  # inputs given to a group
    parts = []                                          # (group, strings, starts, n)
    first_plain = next((u for u in units if not u.optimized), units[0])
    for g in groups:
        targeted = 0 < g.target[0] <= len(units)
        unit = units[g.target[0] - 1] if targeted else first_plain
        destinations = [unit] if targeted else [u for u in units if not u.optimized and u.checkable]
        if not unit.checkable and not asked_n:
            out.left += [(g.sfid, pm.key, tuple(pm.centre)) for pm in g.placed]
            continue
        n = asked_n or _best_series(g, destinations, cond, strategy)
        if n <= 0:
            out.left += [(g.sfid, pm.key, tuple(pm.centre)) for pm in g.placed]
            continue
        strings, left, starts = order(g.placed, n, strategy)
        out.left += [(g.sfid, pm.key, tuple(pm.centre)) for pm in left]
        parts.append((g, strings, starts, n))

    def place(g, chunk, slot):
        for pms in chunk:
            used[slot] += 1
            out.strings.append(String(slot[0], slot[1], [(g.sfid, pm.key, tuple(pm.centre)) for pm in pms],
                                      used[slot]))

    automatic = []
    for g, strings, starts, n in parts:
        unit_no, mppt = g.target
        if unit_no and 0 < unit_no <= len(units):
            mine = [(unit_no, mppt)] if 0 < mppt <= units[unit_no - 1].inputs else \
                [(unit_no, k + 1) for k in range(units[unit_no - 1].inputs)]
            taken.update(mine)
            for slot, count in zip(mine, stringing.spread(len(strings), len(mine)), strict=True):
                room = max(0, _capacity(g.module, units[slot[0] - 1], slot[1] - 1, asked_per) - used[slot])
                count = min(count, room) if alike(slot, n) else 0
                place(g, strings[:count], slot)
                strings = strings[count:]
            out.left += [(g.sfid, pm.key, tuple(pm.centre)) for pms in strings for pm in pms]
            continue
        if strategy == "row_per_mppt":
            by_row: dict = defaultdict(list)
            for pms, r in zip(strings, starts, strict=True):
                by_row[r].append(pms)
            automatic += [(g, rows, n) for _r, rows in sorted(by_row.items())]
        else:
            automatic.append((g, strings, n))
    if not automatic:
        return
    module = automatic[0][0].module
    free = ([slot for slot in inputs if slot not in taken and not busy.get(slot)]
            + [slot for slot in inputs if slot not in taken and busy.get(slot)
               and _capacity(module, units[slot[0] - 1], slot[1] - 1, asked_per) > busy[slot]])
    first = units[free[0][0] - 1] if free else units[0]
    caps = [_capacity(g.module, first, 0, asked_per) for g, _strings, _n in automatic]
    if asked_per:
        # the strings on each input asked by the designer (as before task 16d): filled in order, nothing spread
        k = 0
        for g, strings, _n in automatic:
            for pms in strings:
                while k < len(free) and (used[free[k]] >= _capacity(g.module, units[free[k][0] - 1], free[k][1] - 1,
                                                                     asked_per) or not alike(free[k], len(pms))):
                    k += 1
                if k >= len(free):
                    out.left += [(g.sfid, pm.key, tuple(pm.centre)) for pm in pms]
                    continue
                place(g, [pms], free[k])
        return
    need = [max(1, -(-len(strings) // max(1, c))) for (_g, strings, _n), c in zip(automatic, caps, strict=True)]
    got = _allot([len(strings) for _g, strings, _n in automatic], need, len(free))
    at = 0
    for (g, strings, n), m in zip(automatic, got, strict=True):
        slots = free[at:at + m]
        at += m
        if not slots:
            out.left += [(g.sfid, pm.key, tuple(pm.centre)) for pms in strings for pm in pms]
            continue
        room = [max(0, _capacity(g.module, units[u - 1], k - 1, asked_per) - busy.get((u, k), 0))
                if alike((u, k), n) else 0 for u, k in slots]
        counts = stringing.spread(min(len(strings), sum(room)), len(slots))
        # an input that takes fewer than its share keeps its room, the rest goes to the next ones
        for i in range(len(counts)):
            if counts[i] > room[i]:
                spare = counts[i] - room[i]
                counts[i] = room[i]
                for j in range(len(counts)):
                    if spare and counts[j] < room[j] and j != i:
                        add = min(spare, room[j] - counts[j])
                        counts[j] += add
                        spare -= add
        for slot, count in zip(slots, counts, strict=True):
            place(g, strings[:count], slot)
            strings = strings[count:]
        out.left += [(g.sfid, pm.key, tuple(pm.centre)) for pms in strings for pm in pms]


def _number_strings(out: Plant) -> None:
    """Each string's place on its input, from 1, in the order of the list."""
    seen: dict = defaultdict(int)
    for s in out.strings:
        if s.inverter and s.mppt:
            seen[(s.inverter, s.mppt)] += 1
            s.index = seen[(s.inverter, s.mppt)]
        else:
            seen[(0, 0)] += 1
            s.index = seen[(0, 0)]


def build(project, results: dict | None = None, groups: list | None = None, t_cell_max_year: float | None = None,
          t_min_year: float | None = None, p_dc_hourly=None, check: bool = True) -> Plant:
    """The plant of `project` on its layouts (`results`: sub-field id -> layout.Result) or on the energy job's
    groups (groups_from_arrays): the units, the strings (proposed, or the designer's), the modules in no string, and
    with `check` the checks at the conditions of the year (when given: its hottest cell, its lowest temperature, the
    DC power of each hour for the overload) or at the design ones."""
    if groups is None:
        groups = groups_of(project, results or {})
    p_stc = sum(len(g.placed) * g.module.pmax for g in groups)
    e = project.energy or {}
    s = e.get("strings") if (e.get("strings") or {}).__class__ is dict else {}
    s = s or {}
    cond = conditions(project, t_cell_max_year, t_min_year)
    module = groups[0].module if groups else None
    out = Plant(units=units_of(project, p_stc, module, cond.t_min), auto=bool(s.get("auto", False)),
                strategy=s.get("strategy") or "serpentine", year=cond.year, t_cell_max=cond.t_cell_max,
                t_cell_cold=cond.t_cell_cold, t_min=cond.t_min, p_stc_w=p_stc)
    if not groups:
        return out
    if out.auto:
        _propose(out.units, groups, s, cond, out)
    else:
        _runs(groups, s.get("runs") or [], out)
    _number_strings(out)
    if not any(u.checkable for u in out.units if not u.optimized) and not any(u.optimized for u in out.units):
        out.notes.append(_("Choose an inverter from the catalogue to check the strings: its MPPT window and "
                           "currents are needed."))
    seen_entries: set = set()
    for u in out.units:
        if u.optimized and not u.checkable and u.entry not in seen_entries:
            seen_entries.add(u.entry)
            out.notes.append(u.choice.why if u.choice is not None else
                             _("{name}: none of SolarEdge's optimizers in the catalogue takes this module; choose one "
                               "in the Plant").format(name=u.name))
    _by_unit(groups, out)
    if check:
        _check(project, groups, cond, out, p_dc_hourly)
    return out


# the designer's strings: the edits of the stringing by hand, as plain data (energy["strings"]["runs"])

def runs_of(plant: Plant) -> list[dict]:
    """The strings of a plant as the file keeps them."""
    return [{"inverter": s.inverter, "mppt": s.mppt, "modules": s.keys} for s in plant.strings]


def propose(project, results: dict | None = None, groups: list | None = None, strategy: str = "",
            keep: list[dict] | None = None, t_cell_max_year: float | None = None) -> list[dict]:
    """Meridiana's strings as the file keeps them, made once when the designer asks («Propose the strings», PVsyst's
    «Auto Attribution»): every module laid in strings by `strategy` (the project's when ""), on the inputs as `build`
    spread them when the proposal was live. With `keep` (the designer's strings, «Complete») those stay as they are,
    first in the list, and only the modules in none of them are proposed: on the inputs that have no string first,
    then on those that take more; what does not fit stays out, and the checks say so."""
    import dataclasses
    if groups is None:
        groups = groups_of(project, results or {})
    if not groups:
        return [dict(r) for r in keep or []]
    e = project.energy or {}
    s = dict(e.get("strings") or {}) if (e.get("strings") or {}).__class__ is dict else {}
    if strategy:
        s["strategy"] = strategy
    cond = conditions(project, t_cell_max_year)
    p_stc = sum(len(g.placed) * g.module.pmax for g in groups)
    units = units_of(project, p_stc, groups[0].module, cond.t_min)
    kept = [dict(r, modules=list(r.get("modules") or [])) for r in keep or [] if r.__class__ is dict]
    taken = {k for r in kept for k in r["modules"]}
    busy: dict = defaultdict(int)
    loaded: dict = defaultdict(float)
    lengths: dict = defaultdict(set)
    power = {f"{g.sfid}/{pm.key}": g.module.pmax for g in groups for pm in g.placed}
    for r in kept:
        slot = (r.get("inverter", 0), r.get("mppt", 0))
        busy[slot] += 1
        loaded[slot] += sum(power.get(k, 0.0) for k in r["modules"])
        lengths[slot].add(len(r["modules"]))
    if taken:
        groups = [dataclasses.replace(g, placed=[pm for pm in g.placed if f"{g.sfid}/{pm.key}" not in taken])
                  for g in groups]
        groups = [g for g in groups if g.placed]
    out = Plant(units=units, strategy=s.get("strategy") or "serpentine")
    if groups:
        _propose(units, groups, s, cond, out, dict(busy), dict(loaded), dict(lengths))
    return kept + runs_of(out)


def unit_keys(energy: dict | None) -> list[tuple[int, int]]:
    """Each unit of the plant as (its entry in energy["inverters"], which one of the entry's count), in the order
    units_of numbers them."""
    out = []
    for i, item in enumerate(system.inverter_entries(energy)):
        if InverterSpec.from_record(item["record"], count=1).pac <= 0:
            continue
        out += [(i, k) for k in range(item["count"])]
    return out


def renumber(runs: list[dict], before: list, after: list, moved: dict) -> list[dict]:
    """The strings' inverters after the list of the inverters changed (R118: the strings stay where they are):
    `before` and `after` the units as unit_keys gives them, `moved` an entry's place before -> after. A string keeps
    its inverter, the same one of the same entry, under its new number; one whose inverter is gone is on none (the
    checks say so). With no inverter chosen before or after (one sized by itself) nothing is renumbered."""
    if not before or not after:
        return [dict(r) for r in runs]
    number = {key: n + 1 for n, key in enumerate(after)}
    out = []
    for r in runs:
        r = dict(r)
        inv = r.get("inverter", 0)
        if inv.__class__ is int and 0 < inv <= len(before):
            e, k = before[inv - 1]
            new = number.get((moved.get(e, -1), k), 0)
            r["inverter"] = new
            if not new:
                r["mppt"] = 0
        out.append(r)
    return out


def delete_run(runs: list[dict], index: int) -> list[dict]:
    """The strings without string `index`: its modules in no string."""
    return [dict(r, modules=list(r.get("modules") or [])) for i, r in enumerate(runs) if i != index]


def set_run(runs: list[dict], index: int, keys: list[str]) -> tuple[list[dict], list[int]]:
    """String `index` made of the modules `keys`, in their order (a string drawn again by hand); a module of another
    string is taken from it: the new runs and the indices of the strings that lost one."""
    out = [dict(r, modules=list(r.get("modules") or [])) for r in runs]
    out[index]["modules"] = []
    return add_modules(out, index, keys)


def run_label(runs: list[dict], index: int) -> str:
    """The name of run `index` as String.label gives it once laid: inverter.input.place on the input."""
    if not 0 <= index < len(runs):
        return "?"
    inv, mppt = runs[index].get("inverter", 0), runs[index].get("mppt", 0)
    place = sum(1 for r in runs[:index + 1] if (r.get("inverter", 0), r.get("mppt", 0)) == (inv, mppt))
    return f"{inv}.{mppt}.{place}" if inv and mppt else f"?.{place}"


def touched(strings: dict | None, runs: list[dict]) -> dict:
    """energy["strings"] with the strings `runs` (the empty ones left out), the designer's: a proposal of before
    format 14 is no longer to be written down; the rest kept (the strategy and the modules in series of the next
    proposal)."""
    out = {k: v for k, v in (strings or {}).items() if k != "auto"}
    out["runs"] = [r for r in runs if r.get("modules")]
    return out


def add_modules(runs: list[dict], index: int, keys: list[str]) -> tuple[list[dict], list[int]]:
    """The modules `keys` at the end of string `index`, in their order; a module of another string is taken
    from it (said: the indices of the strings that lost one). A module already in string `index` stays where it
    is. Returns the new runs and those indices."""
    out = [dict(r, modules=list(r.get("modules") or [])) for r in runs]
    mine = out[index]["modules"]
    robbed: list[int] = []
    for key in keys:
        if key in mine:
            continue
        for i, r in enumerate(out):
            if i != index and key in r["modules"]:
                r["modules"].remove(key)
                if i not in robbed:
                    robbed.append(i)
        mine.append(key)
    return out, robbed


def remove_module(runs: list[dict], key: str) -> tuple[list[dict], int]:
    """The module `key` out of the string it is in: the new runs and that string's index (-1: in none)."""
    out = [dict(r, modules=list(r.get("modules") or [])) for r in runs]
    for i, r in enumerate(out):
        if key in r["modules"]:
            r["modules"].remove(key)
            return out, i
    return out, -1


def cut_run(runs: list[dict], key: str, keep: str) -> tuple[list[dict], int]:
    """The string with module `key` made to start there (`keep` "from") or to end there ("to"): the modules cut off
    are left in no string. The new runs and that string's index (-1: `key` in none)."""
    out = [dict(r, modules=list(r.get("modules") or [])) for r in runs]
    for i, r in enumerate(out):
        mods = r["modules"]
        if key in mods:
            at = mods.index(key)
            r["modules"] = mods[at:] if keep == "from" else mods[:at + 1]
            return out, i
    return out, -1


def optimizer_per(plant: Plant, s: String) -> int:
    """The modules on each optimizer of string `s` (1 or 2), 0 when its inverter has none."""
    u = plant.unit(s.inverter)
    return u.choice.per if u is not None and u.optimized and u.choice is not None else 0


def optimizers_of(plant: Plant, arrays: list):
    """The power optimizers of the year (simulate.Optimizers) from the plant's strings on the energy job's arrays: for
    each array the share of its modules in a string of optimizers and of those alone on one, the optimizers'
    efficiency (weighted by the modules) and the inverter's string voltage; each string of optimizers with its
    modules by array and the power it carries at most. None without optimizers."""
    from .simulate import ArrayOptimizers, Optimizers
    if plant is None or not plant.optimized:
        return None
    where = {}
    for a in arrays:
        sfid = a.key.split(".")[0]
        for pm in a.placed:
            where[(sfid, pm.key)] = a.key
    count: dict = defaultdict(int)
    single: dict = defaultdict(int)
    eta: dict = defaultdict(float)
    about: dict = {}
    strings = []
    for s in plant.strings:
        u = plant.unit(s.inverter)
        if u is None or not u.optimized or u.choice is None or not s.modules:
            continue
        ch = u.choice
        counts: dict = defaultdict(int)
        for sf, k, _c in s.modules:
            key = where.get((sf, k))
            if key is not None:
                counts[key] += 1
        label = _("datasheet of {name}").format(name=ch.optimizer.name)
        if ch.suggested:
            label += " " + _("(proposed by Meridiana)")
        for key, n in counts.items():
            count[key] += n
            eta[key] += n * ch.optimizer.eta
            about[key] = (u.fixed.v_string, ch.optimizer.name, Source("data", label, ch.optimizer.datasheet))
            if ch.per == 1:
                single[key] += n
        if ch.per > 1 and len(s.modules) % ch.per:
            last = where.get(s.modules[-1][:2])
            if last is not None:
                single[last] += 1
        p_cont = s.plan.continuous_w if isinstance(s.plan, optimizers.OptimizedPlan) else (
            ch.rules.p_cont if ch.rules is not None else 0.0)
        strings.append((dict(counts), p_cont))
    out = Optimizers(strings=strings)
    for a in arrays:
        n = count.get(a.key, 0)
        if n and a.modules:
            v, name, source = about[a.key]
            out.arrays[a.key] = ArrayOptimizers(share=min(1.0, n / a.modules), single=min(1.0, single[a.key] / a.modules),
                                                eta=eta[a.key] / n, v_string=v, name=name, source=source)
    return out if out.arrays else None


def dcac(plant: Plant) -> tuple[float, float | None]:
    """The plant's DC/AC ratio and the share of the year's energy its inverters cut, weighted by their DC power
    (None before the year is computed)."""
    ac = sum(u.spec.pac for u in plant.units if u.spec.pac)
    ratio = plant.p_stc_w / ac if ac else 0.0
    if not plant.clipping:
        return ratio, None
    dc: dict = {}
    for (n, _k), slot in plant.inputs.items():
        dc[n] = dc.get(n, 0.0) + slot.power_w
    total = sum(dc.get(n, 0.0) for n in plant.clipping)
    if total <= 0:
        return ratio, max(plant.clipping.values())
    return ratio, sum(loss * dc.get(n, 0.0) for n, loss in plant.clipping.items()) / total


def voltages(s: String) -> str:
    """What a string reaches against its limits (R57), in one line: its modules against the fewest and the most
    the input takes, the open-circuit voltage on the coldest morning against the maximum, the MPP voltage at the
    hottest and the coldest cell against the MPPT window."""
    p = s.plan
    n = len(s.modules)
    if p is None:
        return ngettext("{n} module", "{n} modules", n).format(n=n)
    if isinstance(p, optimizers.OptimizedPlan):
        return optimized_line(p)
    parts = []
    lo, hi = p.n_series_min, p.n_series_max
    if lo and n < lo:
        parts.append(_("{n} modules: {k} short of the {lo} the input needs").format(n=n, k=lo - n, lo=lo))
    elif hi and n > hi:
        parts.append(_("{n} modules: {k} over the {hi} the input takes").format(n=n, k=n - hi, hi=hi))
    elif lo and hi:
        parts.append(_("{n} modules (from {lo} to {hi})").format(n=n, lo=lo, hi=hi))
    else:
        parts.append(ngettext("{n} module", "{n} modules", n).format(n=n))
    if p.uoc_max and p.v_limit:
        parts.append(_("Uoc cold {u} V of {lim} V").format(u=f"{p.uoc_max:.0f}", lim=f"{p.v_limit:.0f}"))
    lo_v, hi_v = p.window
    if p.vmp_hot and (lo_v or hi_v):
        parts.append(_("Umpp {hot}-{cold} V, window {lo}-{hi} V").format(
            hot=f"{p.vmp_hot:.0f}", cold=f"{p.vmp_cold:.0f}", lo=f"{lo_v:.0f}", hi=f"{hi_v:.0f}"))
    return " · ".join(parts)


def optimized_line(p: optimizers.OptimizedPlan) -> str:
    """What a string of optimizers reaches against SolarEdge's limits, in one line (the voltages' place, R57): its
    optimizers against the fewest and the most, its modules with two on an optimizer, its power against what may be
    connected and what it carries, the inverter's fixed string voltage."""
    from ..i18n import number
    n, (lo, hi) = p.optimizers, p.opt_range
    if lo and n < lo:
        parts = [_("{n} optimizers: {k} short of the {lo} SolarEdge asks").format(n=n, k=lo - n, lo=lo)]
    elif hi and n > hi:
        parts = [_("{n} optimizers: {k} over the {hi} SolarEdge allows").format(n=n, k=n - hi, hi=hi)]
    else:
        parts = [_("{n} optimizers (from {lo} to {hi})").format(n=n, lo=lo, hi=hi)]
    if p.per > 1:
        parts.append(ngettext("{n} module", "{n} modules", p.n_series).format(n=p.n_series))
    limit = number(p.limit_w / 1000.0, 1) if p.limit_w != float("inf") else "∞"
    parts.append(_("{p} kW of {lim} kW, {c} kW carried").format(
        p=number(p.power_w / 1000.0, 1), lim=limit, c=number(p.continuous_w / 1000.0, 1)))
    parts.append(f"{number(p.v_string, 0)} V")
    return " · ".join(parts)


def new_run(runs: list[dict], inverter: int, mppt: int, keys: list[str]) -> tuple[list[dict], int]:
    """A new string on input `mppt` of inverter `inverter` with the modules `keys` (taken from the strings they
    were in): the new runs and its index."""
    out = [dict(r, modules=list(r.get("modules") or [])) for r in runs] + [
        {"inverter": int(inverter), "mppt": int(mppt), "modules": []}]
    out, _robbed = add_modules(out, len(out) - 1, keys)
    return out, len(out) - 1


def reversed_run(runs: list[dict], index: int) -> list[dict]:
    """String `index` the other way round: its first module becomes its end, where the drag goes on."""
    out = [dict(r, modules=list(r.get("modules") or [])) for r in runs]
    out[index]["modules"].reverse()
    return out


def _runs(groups: list[Group], runs: list, out: Plant) -> None:
    """The designer's strings on today's layout: each key found among the modules laid, or lost."""
    laid = {}
    for g in groups:
        for pm in g.placed:
            laid[f"{g.sfid}/{pm.key}"] = (g.sfid, pm.key, tuple(pm.centre))
    seen: set = set()
    for i, run in enumerate(runs):
        if run.__class__ is not dict:
            continue
        mods, lost = [], []
        for key in run.get("modules") or []:
            if key in laid and key not in seen:
                mods.append(laid[key])
                seen.add(key)
            elif key not in laid:
                lost.append(key)
        inv, mppt = run.get("inverter", 0), run.get("mppt", 0)
        s = String(inv if inv.__class__ is int else 0, mppt if mppt.__class__ is int else 0, mods, run=i, lost=lost)
        out.strings.append(s)
    out.left += [v for k, v in laid.items() if k not in seen]


def _by_unit(groups: list[Group], out: Plant) -> None:
    """The modules in no string, by the inverter their sub-field sends them to, or the one the other strings of
    their sub-field went to; 0 when none."""
    of_sf: dict = {}
    for s in out.strings:
        if s.inverter and s.modules:
            of_sf.setdefault(s.modules[0][0], s.inverter)
    targets = {g.sfid: g.target[0] for g in groups}
    counts: dict = defaultdict(int)
    for sfid, _k, _c in out.left:
        unit = targets.get(sfid) or of_sf.get(sfid, 0)
        counts[unit if out.unit(unit) is not None else 0] += 1
    out.left_by_unit = dict(counts)


def _module_key(m: ModuleSpec) -> tuple:
    return (m.manufacturer, m.model, m.pmax, m.voc, m.isc, m.vmp)


_PLANS: dict = {}               # the checks of an input, kept by what they are made of (task 16d, step 7)
PLANS_KEPT = 512


def _plan(module: ModuleSpec, unit: Unit, k: int, n: int, strings: int, cond: Conditions) -> stringing.StringPlan:
    """stringing.plan for `strings` strings of `n` modules on input `k` of `unit`, kept by everything it reads:
    a change of the strings computes again only the inputs it touched (a few milliseconds each, four single-diode
    solutions), every other input takes the plan it had."""
    spec = unit.spec
    key = ((_module_key(module), module.beta_voc, module.max_series_fuse, module.max_system_voltage, module.imp),
           (spec.manufacturer, spec.model, spec.vdc_max, spec.vmppt_min, spec.vmppt_max, unit.inputs,
            tuple(spec.imax_per_mppt or ()), tuple(spec.iscmax_per_mppt or ())),
           k, n, strings, cond.t_min, cond.t_cell_max, cond.t_cell_cold, cond.cell_source.label,
           cond.t_min_source.label)
    with _LOCK:
        found = _PLANS.get(key)
    if found is not None:
        return found
    per = [0] * unit.inputs
    per[k - 1] = strings
    out = stringing.plan(module, spec, n, per, cond.t_min, cond.t_cell_max, t_min_source=cond.t_min_source,
                         t_cell_cold=cond.t_cell_cold, t_cell_source=cond.cell_source)
    with _LOCK:
        if len(_PLANS) >= PLANS_KEPT:
            _PLANS.clear()
        _PLANS[key] = out
    return out


def _check(project, groups: list[Group], cond: Conditions, out: Plant, p_dc_hourly) -> None:
    modules = {g.sfid: g.module for g in groups}
    plans: dict = {}
    for u in out.units:
        for k in range(u.inputs):
            out.inputs[(u.number, k + 1)] = Input(u.number, k + 1)
    for i, s in enumerate(out.strings):
        if s.lost:
            out.lost.append((s.label, list(s.lost)))
        slot = out.inputs.get((s.inverter, s.mppt))
        if slot is None:
            s.state, s.why = "fail", _("no input: choose an inverter's input for it")
            continue
        slot.strings.append(i)
    for u in out.units:
        if u.optimized:
            _check_optimized(u, out, modules, cond)
    for (unit_no, k), slot in out.inputs.items():
        unit = out.unit(unit_no)
        if unit.optimized:
            continue
        first = next((modules.get(out.strings[i].modules[0][0]) for i in slot.strings if out.strings[i].modules), None)
        module = first or next(iter(modules.values()))
        slot.allowed = max(0, stringing.strings_allowed(module, unit.spec, k - 1))
        if unit.checkable:
            slot.series = stringing.series_range(module, unit.spec, cond.t_min, cond.t_cell_max, cond.t_cell_cold)
        if not slot.strings:
            continue
        mine = [out.strings[i] for i in slot.strings]
        slot.power_w = sum(len(x.modules) * modules[x.modules[0][0]].pmax for x in mine if x.modules)
        if not unit.checkable:
            for x in mine:
                x.state, x.why = "check", _("to be checked: the inverter has no MPPT window (choose one from the "
                                            "catalogue)")
            continue
        alike = len({(len(x.modules), _module_key(modules[x.modules[0][0]])) for x in mine if x.modules}) <= 1
        worst_input = "ok"
        for x in mine:
            if not x.modules:
                x.state, x.why = "fail", _("no module left in it")
                worst_input = "fail"
                continue
            m = modules[x.modules[0][0]]
            n = len(x.modules)
            key = (unit_no, k, n, _module_key(m), len(mine))
            if key not in plans:
                plans[key] = _plan(m, unit, k, n, len(mine), cond)
            p = plans[key]
            slot.plan = slot.plan or p
            x.plan = p
            bad = [c for c in p.checks if c.level == "fail"]
            warn = [c for c in p.checks if c.level == "warn"]
            if bad:
                x.state, x.why = "fail", "; ".join(f"{c.label}: {c.detail}" for c in bad)
            elif warn or not alike or x.lost:
                x.state = "check"
                x.why = "; ".join([f"{c.label}: {c.detail}" for c in warn]
                                  + ([_("strings not alike on this input (PVsyst asks for identical strings on an "
                                        "MPPT)")] if not alike else [])
                                  + ([_("{n} of its modules are no longer laid").format(n=len(x.lost))] if x.lost
                                     else []))
            else:
                x.state, x.why = "ok", _("every check passed")
            worst_input = max(worst_input, {"ok": "ok", "check": "warn", "fail": "fail"}[x.state],
                              key=("ok", "warn", "fail").index)
        slot.level = worst_input
    # the inverters
    total = sum(len(x.modules) * modules[x.modules[0][0]].pmax for x in out.strings if x.modules) or 0.0
    for u in out.units:
        checks = []
        name = unit_label(u)
        dc = sum(slot.power_w for (n, _k), slot in out.inputs.items() if n == u.number)
        if dc > 0:
            checks.append(stringing.Check("dcac", _("{name}: DC/AC ratio").format(name=name), True,
                                          _("{dc} kWp on {ac} kW: {r}").format(dc=f"{dc / 1000:.2f}",
                                                                              ac=f"{u.spec.pac / 1000:.1f}",
                                                                              r=f"{dc / u.spec.pac:.2f}"), "info"))
            if p_dc_hourly is not None and total > 0 and out.p_stc_w > 0:
                import numpy as np
                share = dc / out.p_stc_w
                loss = stringing.overload_loss(np.asarray(p_dc_hourly, dtype=float) * share, u.spec.pac, u.spec.eta)
                out.clipping[u.number] = loss
                checks.append(stringing.overload_check(name, loss))
            powers = [slot.power_w for (n, _k), slot in sorted(out.inputs.items()) if n == u.number]
            balance = stringing.imbalance_check(name, powers)
            if balance is not None:
                checks.append(balance)
        if u.optimized:
            checks += _optimized_unit_checks(u, out, modules, dc)
        out.checks[u.number] = checks


def _string_power(x: String, modules: dict) -> float:
    return sum(modules[sf].pmax for sf, _k, _c in x.modules if sf in modules)


def _check_optimized(unit: Unit, out: Plant, modules: dict, cond: Conditions) -> None:
    """The strings of an inverter with optimizers, input (Synergy unit) by input: each string's plan by SolarEdge's
    table for its optimizer and this inverter (energy/optimizers.py), its state as the traffic light reads it."""
    ch = unit.choice
    for k in range(1, unit.inputs + 1):
        slot = out.inputs[(unit.number, k)]
        if ch is not None and ch.rules is not None:
            slot.series = (ch.rules.opt_min, ch.rules.opt_max)
        slot.allowed = unit.fixed.pairs
        mine = [out.strings[i] for i in slot.strings]
        slot.power_w = sum(_string_power(x, modules) for x in mine)
        if not mine:
            continue
        if ch is None or ch.rules is None:
            for x in mine:
                x.state, x.why = "check", (ch.why if ch is not None else
                                           _("to be checked: no optimizer chosen that takes this module"))
            slot.level = "warn"
            continue
        powers = [_string_power(x, modules) for x in mine if x.modules]
        spread = (max(powers) - min(powers)) if powers else 0.0
        worst = "ok"
        for x in mine:
            if not x.modules:
                x.state, x.why = "fail", _("no module left in it")
                worst = "fail"
                continue
            m = modules[x.modules[0][0]]
            p = optimizers.string_plan(m, ch.optimizer, ch.per, unit.fixed, ch.rules, len(x.modules), len(mine),
                                       spread, cond.t_min, cond.t_min_source, _string_power(x, modules))
            x.plan = p
            slot.plan = slot.plan or p
            bad = [c for c in p.checks if c.level == "fail"]
            warn = [c for c in p.checks if c.level == "warn"]
            if bad:
                x.state, x.why = "fail", "; ".join(f"{c.label}: {c.detail}" for c in bad)
            elif warn or x.lost:
                x.state = "check"
                x.why = "; ".join([f"{c.label}: {c.detail}" for c in warn]
                                  + ([_("{n} of its modules are no longer laid").format(n=len(x.lost))] if x.lost
                                     else []))
            else:
                x.state, x.why = "ok", _("every check passed")
            worst = max(worst, {"ok": "ok", "check": "warn", "fail": "fail"}[x.state], key=("ok", "warn", "fail").index)
        slot.level = worst


def _optimized_unit_checks(unit: Unit, out: Plant, modules: dict, dc_w: float) -> list:
    """The checks of an inverter with optimizers beyond its strings: which optimizers (proposed, or not fitting), for
    each Synergy unit the difference between its strings, for the inverter its maximum DC power and the least of the
    commercial ones, the Home Hub's 1:1."""
    ch = unit.choice
    name = unit_label(unit)
    if ch is None:
        return [stringing.Check("opt_none", _("{name}: power optimizers").format(name=name), False,
                                _("none of SolarEdge's optimizers in the catalogue takes this module: choose one"), "",
                                optimizers.RES)]
    found = []
    if ch.rules is None:
        found.append(stringing.Check("opt_rules", _("{name}: the optimizers and the inverter").format(name=name),
                                     False, ch.why, "", ch.optimizer.datasheet))
    elif ch.suggested:
        found.append(stringing.Check(
            "opt_suggested", _("{name}: power optimizers").format(name=name), True,
            ngettext("{opt}, {n} module on each, proposed by Meridiana: choose them in the Plant to confirm",
                     "{opt}, {n} modules on each, proposed by Meridiana: choose them in the Plant to confirm",
                     ch.per).format(opt=ch.optimizer.name, n=ch.per), "info", ch.rules.source))
    for k in range(1, unit.inputs + 1):
        slot = out.inputs[(unit.number, k)]
        mine = [out.strings[i] for i in slot.strings if out.strings[i].modules]
        where = name if unit.inputs == 1 else _("{name}, Synergy unit {k}").format(name=name, k=k)
        counts = [optimizers.optimizer_count(len(x.modules), ch.per) for x in mine]
        found += optimizers.unit_checks(where, unit.fixed, ch.optimizer, ch.per,
                                        [_string_power(x, modules) for x in mine], counts, 0.0, ch.rules)
    found += optimizers.unit_checks(name, unit.fixed, ch.optimizer, ch.per, [], [], dc_w, ch.rules)
    return found
