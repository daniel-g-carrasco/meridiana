"""Module layout in a sub-field: the area the designer drew, filled with modules the way a mounting
system allows, within the margins and the fire-brigade rules.

Everything here is plan geometry in local metres (geo.py). A layout is computed in a work frame where the
rows run along u and the modules face -v; on an inclined surface (a roof pitch, a canopy) v is measured
along the slope, so a coplanar module keeps its true size. Results go back to the plan.

Mountings (MOUNTINGS) and the sources of their rules:
- coplanar and integrated (BIPV) on a pitch: the module plane is the roof plane, as the TU FER (D.Lgs.
  190/2024 All. A sez. I a) asks for the free regime ("same tilt and orientation as the pitch");
- tilted rows on a flat roof, anchored or ballasted, south or east-west; ground rows; facade; canopy.
  CEI 82-25/3:2026 6.2 recalls NTC 2018 7.2.4: on a roof slab friction alone is not a restraint, so a
  ballast-only system gets a warning (BALLAST_WARNING);
- DCPREV 14030/2025 3.3.5.1 for activities subject to fire-brigade control: 1 m from the roof edge,
  groups of at most 20 m in every direction, 2 m corridors, 1 m around smoke vents, openings and roof
  plant (the `fire_rules` switch; exclusions carry their own clearance).
The row pitch comes from the sun (sun.row_clearance with a design window), from a value, or from a
ground cover ratio.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import MultiPolygon, Polygon, box
from shapely.ops import unary_union

from . import geo, sun
from .i18n import N_, _

# the mountings the engine knows (the names the user reads are in the interface, not here)
MOUNTINGS = frozenset({"coplanar", "integrated", "tilted_anchored", "tilted_ballasted", "east_west", "ground",
                       "canopy"})
# A facade is drawn on its elevation, not on the plan: it will have its own editor and engine.
TILTED = {"tilted_anchored", "tilted_ballasted", "ground"}
FLUSH = {"coplanar", "integrated", "canopy"}
BALLAST_WARNING = N_("Ballast alone is not a restraint on a roof slab (NTC 2018 7.2.4, recalled by CEI 82-25/3 6.2): "
                     "anchors or tie-downs are needed.")
EPS = 1e-6
LINE_TOLERANCE = 0.01           # m: rows whose front edges are this close stand on one line
DISTANCE_TOLERANCE = 0.001      # m: a distance this much short of a rule's is the rule's (rows kept to 0,1 mm)


@dataclass
class Module:
    """What the layout needs of a module; the full data sheet is in catalog.py."""
    length: float = 2.278       # m, the long side
    width: float = 1.134        # m
    power_kw: float = 0.450     # Pmax at STC


@dataclass
class Surface:
    """The plane the sub-field lies on: tilt and azimuth (CEI 82-25) of the surface itself, and its height
    at the plan point (x0, y0). A flat roof or the ground has tilt 0."""
    tilt: float = 0.0
    azimuth: float = 0.0
    z0: float = 0.0
    x0: float = 0.0
    y0: float = 0.0

    def z(self, x: float, y: float) -> float:
        if self.tilt == 0:
            return self.z0
        fx, fy = geo.facing_vector(self.azimuth)
        # the surface goes down towards the side it faces
        return self.z0 - ((x - self.x0) * fx + (y - self.y0) * fy) * math.tan(math.radians(self.tilt))

    def z_of(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """z() for arrays of plan points, the same arithmetic."""
        if self.tilt == 0:
            return np.full(np.shape(x), self.z0, dtype=float)
        fx, fy = geo.facing_vector(self.azimuth)
        return self.z0 - ((x - self.x0) * fx + (y - self.y0) * fy) * math.tan(math.radians(self.tilt))


@dataclass
class Params:
    mounting: str = "tilted_anchored"
    portrait: bool = True             # the long side up the slope (or across a tilted table)
    stack: int = 1                    # modules across a table: 2 = "2V" in portrait
    tilt: float = 10.0                # module tilt for tilted mountings; flush ones take the surface's
    azimuth: float | None = None      # None: rows along the side of the area that faces closest to South
    gap: float = 0.02                 # between modules along a row (clamps)
    stack_gap: float = 0.02           # between the modules stacked in a table
    table_modules: int = 0            # modules per table along the row; 0 = continuous rows
    table_gap: float = 0.3            # between tables along a row
    pitch_mode: str = "sun"           # "sun", "value" (pitch in m), "gcr"
    pitch: float = 0.0
    gcr: float = 0.5
    window: sun.DesignWindow = field(default_factory=sun.DesignWindow)
    flush_row_gap: float = 0.02       # between rows of a flush mounting
    ew_ridge_gap: float = 0.05        # between the two halves of an east-west ridge
    ew_aisle: float = 0.3             # between east-west ridges
    edge: float = 0.5                 # free band along the outline of the area
    fire_rules: bool = False
    fire_edge: float = 1.0
    fire_group: float = 20.0
    fire_corridor: float = 2.0
    stand_off: float = 0.15           # module bottom above the surface, for the 3D model
    shade_free: bool = False          # out of the obstacles' shadows in the design window (model.py draws them)


@dataclass
class Exclusion:
    """Something modules must keep away from: a skylight, a smoke vent, roof plant, a walkway."""
    ring: list[tuple[float, float]]
    kind: str = "other"
    clearance: float = 0.0            # extra band around it (1 m for vents, openings, plant under DCPREV 14030)
    holes: list = field(default_factory=list)       # rings left free inside it (a shadow all round a roof)


@dataclass
class Row:
    """A row of modules (task 16c; study 16, C.4): the unit the designer draws, moves, lengthens and explodes. The
    automatic layout makes them (`compute`); a sub-field laid by hand keeps them in the file (model.SubField.rows).

    Its frame is its azimuth: the modules face it and the row runs across it, as in the work frame of `compute`
    (the modules face -v, the row runs along u; on a flush plane v is measured along the slope). The origin is the
    plan point of the row's front edge where its first place starts; `places` are where each place starts, in
    metres along the row from there. A place holds one column of a table: `Params.stack` modules up the tilt, and
    on an east-west mounting the pair, front and back. The modules of the sub-field (its module, orientation,
    tilt, stack) are the sub-field's: a row keeps where its places are, not what is on them.

    Each module has a stable key: «row:slot» with the row's id (the slot is the place, two per place east-west, the
    front first), «:level» added above the lowest of the table; a row exploded out of another keeps the keys its
    modules had (`keys`, by slot), so that the strings and the modules taken out stay on them."""
    id: str
    x: float
    y: float
    azimuth: float                    # CEI 82-25: the side the modules face (the front half's, east-west)
    places: list = field(default_factory=list)
    keys: list = field(default_factory=list)     # the key of each slot where it is not «id:slot»
    turned: bool = False              # turned by 90°: the module's other side along the row (Aurora's double click)

    def slot_key(self, slot: int) -> str:
        if slot < len(self.keys) and self.keys[slot]:
            return str(self.keys[slot])
        return f"{self.id}:{slot}"

    @property
    def count(self) -> int:
        return len(self.places)

    def as_dict(self) -> dict:
        """As the file keeps it (model.SubField.rows): millimetres are enough for a place."""
        out = {"id": self.id, "x": round(float(self.x), 4), "y": round(float(self.y), 4),
               "azimuth": round(float(self.azimuth), 4), "places": [round(float(u), 4) for u in self.places]}
        if any(self.keys):
            out["keys"] = [str(k) for k in self.keys]
        if self.turned:
            out["turned"] = True
        return out

    @classmethod
    def of(cls, raw: dict) -> "Row":
        return cls(id=str(raw["id"]), x=float(raw["x"]), y=float(raw["y"]), azimuth=float(raw["azimuth"]),
                   places=[float(u) for u in raw.get("places") or []], keys=[str(k) for k in raw.get("keys") or []],
                   turned=bool(raw.get("turned", False)))


@dataclass
class PlacedModule:
    row: int                              # the line it stands on: rows on one line count as one (the strings)
    slot: int                             # its slot in its row
    group: int
    corners: list[tuple[float, float]]    # plan footprint
    centre: tuple[float, float]
    z: float                              # height of the module centre
    tilt: float                           # of the module, from the horizontal
    azimuth: float                        # CEI 82-25, the side the module faces
    level: int = 0                        # place in the table's stack, 0 the lowest
    key: str = ""                         # its id, stable while its row is (Row)
    rid: str = ""                         # the id of its row
    turned: bool = False                  # its row turned by 90°: along and across swapped

    def __post_init__(self):
        if not self.key:                  # a module made without a row (the tests' grids): «row:slot[:level]»
            self.key = f"{self.row}:{self.slot}" if self.level == 0 else f"{self.row}:{self.slot}:{self.level}"


@dataclass
class Result:
    modules: list[PlacedModule]
    usable: list[list[tuple[float, float]]]
    groups: list[list[tuple[float, float]]]
    azimuth: float                 # of the rows (the south-facing half for east-west)
    tilt: float
    pitch: float
    clearance: float               # plan gap behind a row, from the sun or the value
    limit_angle: float             # alpha_L of CEI 82-25/3 Fig. 1 for that gap
    area: float                    # of the drawn area, plan
    notes: list[str] = field(default_factory=list)
    # the modules as arrays, for the views (task 18c, step 8): their plan corners (N, 4, 2) and their keys in
    # the order of `modules`; the 3D instance table (mesh.module_table), set by the layout job (jobs.py)
    corners: object = field(default=None, repr=False, compare=False)
    keys: object = field(default=None, repr=False, compare=False)
    table: object = field(default=None, repr=False, compare=False)
    rows: list = field(default_factory=list)       # the rows the modules come from (task 16c)
    manual: bool = False           # the rows are the designer's: kept, not made again
    unmatched: list = field(default_factory=list)  # keys taken out by hand that match no module laid

    @property
    def count(self) -> int:
        return len(self.modules)


def _polys(geom) -> list[Polygon]:
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon) and not g.is_empty]


def _ring(poly: Polygon) -> list[tuple[float, float]]:
    return [(float(x), float(y)) for x, y in list(poly.exterior.coords)[:-1]]


def auto_azimuth(area: Polygon, east_west: bool = False) -> float:
    """Of the two directions of the area's minimum rotated rectangle, the one that lets the rows face
    closest to South: on a flat surface the yield matters more than the long side. For east-west pairs,
    the one closest to East (the pair then faces East and West)."""
    c = list(area.minimum_rotated_rectangle.exterior.coords)
    best = None
    for (x1, y1), (x2, y2) in ((c[0], c[1]), (c[1], c[2])):
        ax = math.atan2(y2 - y1, x2 - x1)
        nx, ny = -math.sin(ax), math.cos(ax)
        if (east_west and nx < 0) or (not east_west and ny > 0):
            nx, ny = -nx, -ny               # towards East for a pair, towards South otherwise
        alpha = geo.bearing_to_azimuth(geo.bearing(nx, ny))
        score = abs(abs(alpha) - 90.0) if east_west else abs(alpha)
        if best is None or score < best[0]:
            best = (score, alpha)
    return round(best[1], 2)


def _intervals_free(strip: Polygon, usable, u0: float, u1: float) -> list[tuple[float, float]]:
    """The u-ranges of the strip where a module spanning its whole depth stays inside `usable`: whatever
    of the strip is not usable forbids its u-projection."""
    bad = strip.difference(usable)
    cuts = sorted((g.bounds[0], g.bounds[2]) for g in _polys(bad) if g.area > EPS)
    free, start = [], u0
    for a, b in cuts:
        if a > start + EPS:
            free.append((start, min(a, u1)))
        start = max(start, b)
    if u1 > start + EPS:
        free.append((start, u1))
    return [(a, b) for a, b in free if b - a > EPS]


def mount_tilt(surface: Surface, p: Params) -> float:
    """The tilt of the modules: the surface's for a flush mounting on a pitch, the parameters' otherwise."""
    if p.mounting in ("coplanar", "integrated"):
        return surface.tilt                       # parallel to the surface, flat on a flat roof
    if p.mounting == "canopy":
        return surface.tilt if surface.tilt > 0 else p.tilt
    return p.tilt


def row_azimuth(area: Polygon, surface: Surface, p: Params) -> float:
    """The azimuth of the rows of a sub-field: the pitch's for a flush mounting on it, the one chosen, or the
    automatic one of the area (auto_azimuth)."""
    def chosen(default):
        return p.azimuth if p.azimuth is not None else default

    if p.mounting in ("coplanar", "integrated", "canopy") and surface.tilt > 0:
        return surface.azimuth
    if p.mounting == "east_west":
        return chosen(auto_azimuth(area, east_west=True))   # the front half faces alpha, the back alpha + 180
    return chosen(auto_azimuth(area))


@dataclass
class Frame:
    """The work frame of rows facing `azimuth`: the plan turned by `rot` degrees so that they face -v, and on a
    flush plane v scaled back along the slope (`slope`, the cosine of the tilt)."""
    azimuth: float
    rot: float
    slope: float

    @classmethod
    def of(cls, azimuth: float, tilt: float, flush: bool) -> "Frame":
        fx, fy = geo.facing_vector(azimuth)
        return cls(azimuth, math.degrees(-math.pi / 2 - math.atan2(fy, fx)),
                   math.cos(math.radians(tilt)) if flush and tilt > 0 else 1.0)

    def _cs(self, angle: float) -> tuple[float, float]:
        # the arithmetic of shapely.affinity.rotate, so that a point goes and comes back as the outlines do
        a = angle * math.pi / 180.0
        c, s = math.cos(a), math.sin(a)
        return (0.0 if abs(c) < 2.5e-16 else c), (0.0 if abs(s) < 2.5e-16 else s)

    def to_work(self, x: float, y: float) -> tuple[float, float]:
        c, s = self._cs(self.rot)
        return c * x - s * y, (s * x + c * y) / self.slope

    def to_plan(self, u: float, v: float) -> tuple[float, float]:
        c, s = self._cs(-self.rot)
        v = v * self.slope
        return c * u - s * v, s * u + c * v

    def along(self) -> tuple[float, float]:
        """The plan direction of +u: along the row."""
        x0, y0 = self.to_plan(0.0, 0.0)
        x1, y1 = self.to_plan(1.0, 0.0)
        return x1 - x0, y1 - y0

    def back(self) -> tuple[float, float]:
        """The plan direction of +v, a metre of v on the plan: towards the back of the row (up the slope)."""
        x0, y0 = self.to_plan(0.0, 0.0)
        x1, y1 = self.to_plan(0.0, 1.0)
        return x1 - x0, y1 - y0


@dataclass
class Sizes:
    """What a row of a sub-field is made of in its frame: the module along the row and up the tilt, the stack, the
    depth of a row on the plan (or along the slope) and the gaps."""
    along: float
    across: float
    stack: int
    depth: float
    rise: float
    flush: bool
    tilt: float
    east_west: bool
    gap: float
    stack_gap: float
    ridge_gap: float

    @classmethod
    def of(cls, module: Module, p: Params, tilt: float, turned: bool = False) -> "Sizes":
        portrait = bool(p.portrait) != bool(turned)
        along = module.width if portrait else module.length
        across = module.length if portrait else module.width
        stack = max(1, int(p.stack))
        table_across = stack * across + (stack - 1) * p.stack_gap        # slant width of a table
        flush = p.mounting in FLUSH
        if flush:
            depth, rise = table_across, 0.0
        elif p.mounting == "east_west":
            depth = 2 * table_across * math.cos(math.radians(tilt)) + p.ew_ridge_gap
            rise = table_across * math.sin(math.radians(tilt))
        else:
            depth = table_across * math.cos(math.radians(tilt))
            rise = table_across * math.sin(math.radians(tilt))
        return cls(along, across, stack, depth, rise, flush, tilt, p.mounting == "east_west", p.gap, p.stack_gap,
                   p.ew_ridge_gap)


def compute(area_ring, surface: Surface | None = None, module: Module | None = None, params: Params | None = None,
            exclusions: list[Exclusion] = (), lat: float = 45.0, lon: float = 9.0,
            removed: set[str] = frozenset(), rows: list[Row] | None = None) -> Result:
    """Fill the area (a plan ring, local metres) with modules. `lat`, `lon` place the sun for the pitch;
    `removed` are module keys the designer took out by hand. With `rows` (a sub-field laid by hand, task 16c) the
    modules are those of the rows given, wherever they are: nothing is made again, and the fire-brigade groups
    are found from the modules (`clusters`) rather than made."""
    surface = surface or Surface()
    module = module or Module()
    p = params or Params()
    if p.mounting not in MOUNTINGS:
        raise ValueError(f"unknown mounting {p.mounting!r}")
    area = Polygon(area_ring).buffer(0)
    if area.is_empty or area.area < 1.0:
        raise ValueError(_("the area encloses less than 1 m2"))
    area = max(_polys(area), key=lambda g: g.area)
    notes: list[str] = []
    if p.mounting == "tilted_ballasted":
        notes.append(BALLAST_WARNING)

    tilt = mount_tilt(surface, p)
    alpha = row_azimuth(area, surface, p)
    if rows is not None and rows:
        alpha = rows[0].azimuth                   # the rows by hand keep their own
    frame = Frame.of(alpha, tilt, p.mounting in FLUSH)
    rot, slope = frame.rot, frame.slope

    def to_work(g):
        g = affinity.rotate(g, rot, origin=(0, 0))
        return affinity.scale(g, 1.0, 1.0 / slope, origin=(0, 0)) if slope != 1.0 else g

    usable = usable_area(area, p, exclusions)
    size = Sizes.of(module, p, tilt)
    depth, rise = size.depth, size.rise
    if size.flush:
        clearance = p.flush_row_gap
    elif size.east_west:
        clearance = p.ew_aisle
    elif p.pitch_mode == "value":
        clearance = max(0.0, p.pitch - depth)
    elif p.pitch_mode == "gcr":
        table_across = size.stack * size.across + (size.stack - 1) * p.stack_gap
        clearance = max(0.0, table_across / max(p.gcr, 0.05) - depth)
    else:
        clearance = sun.row_clearance(rise, geo.azimuth_to_bearing(alpha), p.window.positions(lat, lon))
    pitch = depth + clearance
    limit = round(sun.limit_angle(rise, clearance), 2) if rise > 0 else 90.0
    manual = rows is not None
    if not manual:
        if usable.is_empty:
            return Result([], [], [], alpha, tilt, 0.0, 0.0, 90.0, round(area.area, 2),
                          notes + [N_("no room left inside the margins")], corners=np.zeros((0, 4, 2)), keys=[])
        rows, group_of = _auto_rows(to_work(usable), frame, size, p, pitch)
    placed = modules_of(rows, module, p, surface, removed)
    groups = []
    if not manual:
        for pm in placed:
            pm.group = group_of.get((pm.rid, pm.slot), 0)
        if p.fire_rules:
            members: dict[int, list[int]] = {}
            for i, pm in enumerate(placed):
                members.setdefault(pm.group, []).append(i)
            for idx in members.values():
                hull = unary_union(shapely.polygons(np.array([placed[i].corners for i in idx]))).minimum_rotated_rectangle
                groups.append(_ring(hull))
    elif p.fire_rules and placed:
        for g, members in enumerate(clusters(placed, p.fire_corridor)):
            for i in members:
                placed[i].group = g
            hull = MultiPolygon([Polygon(placed[i].corners) for i in members]).minimum_rotated_rectangle
            groups.append(_ring(hull))
    laid = {k for r in rows for k in row_keys(r, size)}
    unmatched = sorted(k for k in removed if k not in laid)
    return Result(modules=placed, usable=[_ring(g) for g in _polys(usable)], groups=groups, azimuth=round(alpha, 2),
                  tilt=tilt, pitch=round(pitch, 3), clearance=round(clearance, 3), limit_angle=limit,
                  area=round(area.area, 2), notes=notes,
                  corners=np.array([pm.corners for pm in placed], dtype=float).reshape(-1, 4, 2),
                  keys=[pm.key for pm in placed], rows=list(rows), manual=manual, unmatched=unmatched)


def usable_area(area: Polygon, p: Params, exclusions: list[Exclusion] = ()):
    """Where modules may go: the area less its edge band (1 m under the fire-brigade rules) and the exclusions
    with their clearances (1 m more for vents, openings and plant under the rules)."""
    edge = max(p.edge, p.fire_edge if p.fire_rules else 0.0)
    usable = area.buffer(-edge, join_style="mitre") if edge > 0 else area
    blocked = [Polygon(e.ring, e.holes or None).buffer(e.clearance + (p.fire_edge if p.fire_rules and e.kind in ("vent", "opening", "plant") else 0.0),
                                      join_style="mitre") for e in exclusions if len(e.ring) >= 3]
    if blocked:
        usable = usable.difference(unary_union(blocked))
    return usable


def _auto_rows(usable_w, frame: Frame, size: Sizes, p: Params, pitch: float) -> tuple[list[Row], dict]:
    """The rows of the automatic layout in the usable area (in the work frame): from the front edge, a row every
    pitch; with the fire rules, groups at most 20 m deep and 20 m wide. A row for each line, with the id «f1»,
    «f2»... in their order (a line without room keeps its number); and the fire-brigade group of each slot."""
    depth = size.depth
    minu, minv, maxu, maxv = usable_w.bounds
    rows_v: list[tuple[float, int]] = []
    v, group_start, gv = minv, minv, 0
    while v + depth <= maxv + EPS:
        if p.fire_rules and v + depth - group_start > p.fire_group + EPS:
            v = max(v, rows_v[-1][0] + depth + p.fire_corridor if rows_v else v)
            group_start, gv = v, gv + 1
            if v + depth > maxv + EPS:
                break
        rows_v.append((v, gv))
        v += pitch
    if p.fire_rules:
        cells, u = [], minu
        while u < maxu - EPS:
            cells.append((u, min(u + p.fire_group, maxu)))
            u += p.fire_group + p.fire_corridor
    else:
        cells = [(minu, maxu)]
    along = size.along
    rows: list[Row] = []
    group_of: dict = {}
    halves = 2 if size.east_west else 1
    for r, (v0, gv) in enumerate(rows_v):
        # a micrometre in from the front and back: a front edge rotated into the work frame is straight only
        # to 1e-15, and the sliver it leaves would join the strip's end pieces and forbid the whole row
        strip = box(minu - 1, v0 + EPS, maxu + 1, v0 + depth - EPS)
        us: list[float] = []
        rid = f"f{r + 1}"
        for ci, (c0, c1) in enumerate(cells):
            for a, b in _intervals_free(strip, usable_w, c0, c1):
                n = int((b - a + p.gap) // (along + p.gap) + EPS)
                if p.table_modules > 0 and n > 0:
                    # tables of table_modules, separated by table_gap: fit whole tables first
                    per = p.table_modules
                    table_len = per * along + (per - 1) * p.gap
                    tables = int((b - a + p.table_gap) // (table_len + p.table_gap) + EPS)
                    rest = (b - a) - tables * table_len - max(0, tables - 1) * p.table_gap
                    xs = []
                    start = a + rest / 2 if tables else a
                    for t in range(tables):
                        t0 = start + t * (table_len + p.table_gap)
                        xs.extend(t0 + k * (along + p.gap) for k in range(per))
                else:
                    total = n * along + max(0, n - 1) * p.gap
                    start = a + (b - a - total) / 2
                    xs = [start + k * (along + p.gap) for k in range(n)]
                for u0 in xs:
                    for h in range(halves):
                        group_of[(rid, len(us) * halves + h)] = gv * len(cells) + ci
                    us.append(u0)
        first = us[0] if us else minu
        x, y = frame.to_plan(first, v0)
        rows.append(Row(rid, x, y, frame.azimuth, [u0 - first for u0 in us]))
    return rows, group_of


def row_keys(row: Row, size: Sizes) -> list[str]:
    """The keys of every module a row holds, laid or taken out."""
    halves = 2 if size.east_west else 1
    out = []
    for slot in range(row.count * halves):
        base = row.slot_key(slot)
        out.append(base)
        out.extend(f"{base}:{k}" for k in range(1, size.stack))
    return out


def lines(rows: list[Row], tilt: float, flush: bool) -> list[int]:
    """The line each row stands on, numbered front to back: rows facing the same way whose front edges are within a
    centimetre are one line (a row exploded into its modules is still one line for the strings)."""
    marks = []
    for row in rows:
        frame = Frame.of(row.azimuth, tilt, flush)
        marks.append((round(row.azimuth % 360.0, 2), frame.to_work(row.x, row.y)[1]))
    out = [0] * len(rows)
    line, first = -1, None
    for i in sorted(range(len(rows)), key=lambda j: marks[j]):
        if first is None or marks[i][0] != first[0] or marks[i][1] - first[1] > LINE_TOLERANCE:
            line, first = line + 1, marks[i]
        out[i] = line
    return out


def modules_of(rows: list[Row], module: Module, params: Params, surface: Surface,
               removed=frozenset()) -> list[PlacedModule]:
    """The modules of the rows, row by row, place by place, the front half before the back one east-west, the table
    from its low edge up; those whose key is in `removed` are left out. Every module of a sub-field has its module,
    orientation, tilt and stack; a row turned by 90° has the module's other side along it."""
    p = params
    tilt = mount_tilt(surface, p)
    flush = p.mounting in FLUSH
    line_of = lines(rows, tilt, flush)
    batches: dict = {}               # (azimuth, turned) -> [(order, pending...)]
    order = 0
    for row, line in zip(rows, line_of, strict=True):
        size = Sizes.of(module, p, tilt, row.turned)
        frame = Frame.of(row.azimuth, tilt, flush)
        u_o, v0 = frame.to_work(row.x, row.y)
        depth, across, shrink = size.depth, size.across, (1.0 if flush else math.cos(math.radians(tilt)))
        halves = [(v0, v0 + depth)] if not size.east_west else [
            (v0, v0 + (depth - size.ridge_gap) / 2), (v0 + (depth + size.ridge_gap) / 2, v0 + depth)]
        back_alpha = round(geo.bearing_to_azimuth(geo.azimuth_to_bearing(row.azimuth) + 180.0), 2)
        batch = batches.setdefault((row.azimuth, row.turned), (frame, size, []))[2]
        for i, offset in enumerate(row.places):
            u0 = u_o + offset
            for hi, (va, vb) in enumerate(halves):
                slot = i * len(halves) + hi
                back = size.east_west and hi == 1                # its low edge is at vb
                base = row.slot_key(slot)
                for k in range(size.stack):
                    key = base if k == 0 else f"{base}:{k}"
                    if key in removed:
                        continue
                    # in the work frame v is the plan depth for tilted tables, the length along the slope for
                    # flush ones
                    start = k * (across + size.stack_gap)
                    if back:
                        hi_v = vb - start * shrink
                        lo_v = hi_v - across * shrink
                    else:
                        lo_v = va + start * shrink
                        hi_v = lo_v + across * shrink
                    lift = 0.0 if flush else (start + across / 2) * math.sin(math.radians(tilt))
                    batch.append((line, slot, 0, k, back_alpha if back else round(row.azimuth, 2), u0, lo_v, hi_v,
                                  lift, key, row.id, order))
                    order += 1
    placed: list = [None] * order
    for (_az, turned), (frame, size, pending) in batches.items():
        for pm, entry in zip(_place(pending, size.along, frame.rot, frame.slope, surface, p.stand_off, tilt),
                             pending, strict=True):
            pm.turned = bool(turned)
            placed[entry[11]] = pm
    return placed


def clusters(placed: list[PlacedModule], corridor: float) -> list[list[int]]:
    """The modules in groups as the fire-brigade rules see them: modules closer than `corridor` (2 m) belong to one
    group (DCPREV 14030/2025, 3.3.5.1: groups apart by corridors of 2 m), as indices, in the order of their first
    module."""
    if not placed:
        return []
    polys = shapely.polygons(np.array([pm.corners for pm in placed], dtype=float))
    # the pairs closer than the corridor, from the tree of the modules (exact distances, no buffers), joined into
    # groups; a millimetre of tolerance: rows kept to 0,1 mm in the file stand 1,9999 m apart across 2 m
    tree = shapely.STRtree(polys)
    near = tree.query(polys, predicate="dwithin", distance=corridor - DISTANCE_TOLERANCE)
    parent = list(range(len(placed)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b in zip(near[0].tolist(), near[1].tolist(), strict=True):
        ra, rb = root(a), root(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    out: dict = {}
    for i in range(len(placed)):
        out.setdefault(root(i), []).append(i)
    return sorted(out.values(), key=lambda m: m[0])


def _boxes(placed: list[PlacedModule], members: list[int], frame: Frame) -> list[tuple]:
    """The modules' rectangles in the work frame: (u0, u1, v0, v1, line, row id)."""
    if not members:
        return []
    xy = np.array([placed[i].corners for i in members], dtype=float)          # (n, 4, 2)
    c, s = frame._cs(frame.rot)
    u = c * xy[:, :, 0] - s * xy[:, :, 1]
    v = (s * xy[:, :, 0] + c * xy[:, :, 1]) / frame.slope
    lo_u, hi_u, lo_v, hi_v = (a.tolist() for a in (u.min(axis=1), u.max(axis=1), v.min(axis=1), v.max(axis=1)))
    return [(lo_u[k], hi_u[k], lo_v[k], hi_v[k], placed[i].row, placed[i].rid) for k, i in enumerate(members)]


def extent(placed: list[PlacedModule], members: list[int], frame: Frame) -> float:
    """How far a group of modules reaches, the longer of its two sides along and across the rows (in the work frame:
    along the slope on a pitch), as DCPREV 14030/2025 3.3.5.1 measures its 20 m «in every direction»."""
    boxes = _boxes(placed, members, frame)
    if not boxes:
        return 0.0
    return max(max(b[1] for b in boxes) - min(b[0] for b in boxes), max(b[3] for b in boxes) - min(b[2] for b in boxes))


CORRIDOR_SLACK = 0.1            # m: a gap this much wider than the layout's own is a corridor left on purpose


def narrow_gaps(placed: list[PlacedModule], members: list[int], frame: Frame, along: float, p: Params,
                clearance: float) -> list[float]:
    """The gaps left on purpose between the rows of a group that are narrower than a fire-brigade corridor: between
    two rows side by side on a line, wider than the gap of the layout (the modules' or the tables'); between two lines,
    wider than the clear gap behind a row (`clearance`). The gap of a module taken away (its place empty) is not one.
    In metres, the widest first."""
    boxes = _boxes(placed, members, frame)
    if not boxes:
        return []
    out = []
    corridor = p.fire_corridor - DISTANCE_TOLERANCE
    normal_u = max(p.gap, p.table_gap if p.table_modules else 0.0)
    step = along + p.gap
    by_line: dict = {}
    for b in boxes:
        by_line.setdefault(b[4], []).append(b)
    for line in by_line.values():
        columns = sorted({(round(b[0], 3), round(b[1], 3), b[5]) for b in line})
        reach, last = columns[0][1], columns[0][2]          # how far the columns so far go, and the row there
        for b0, b1, rb in columns[1:]:
            gap = b0 - reach
            places = (gap - p.gap) / step
            empty = round(places) >= 1 and abs(places - round(places)) * step < 0.02
            if rb != last and normal_u + CORRIDOR_SLACK < gap < corridor and not empty:
                out.append(gap)
            if b1 >= reach:
                reach, last = b1, rb
    order = sorted(by_line)
    for la, lb in zip(order, order[1:], strict=False):
        front, back = by_line[la], by_line[lb]
        u_overlap = min(max(b[1] for b in front), max(b[1] for b in back)) - max(min(b[0] for b in front),
                                                                                 min(b[0] for b in back))
        if u_overlap <= 0:
            continue
        gap = min(b[2] for b in back) - max(b[3] for b in front)
        if clearance + CORRIDOR_SLACK < gap < corridor:
            out.append(gap)
    return sorted(out, reverse=True)


def _place(pending: list[tuple], along: float, rot: float, slope: float, surface: Surface, stand_off: float,
           tilt: float) -> list[PlacedModule]:
    """The placed modules from their work-frame rectangles (u0, lo_v, hi_v), all at once: the corners of
    box(u0, lo_v, u0 + along, hi_v) as shapely draws them (from (u1, lo_v), counter-clockwise), brought to
    the plan by the scale back along the slope and the rotation of the work frame, with the arithmetic of
    shapely.affinity; the centre is the mean of the corners. Each entry is (line, slot, group, level, azimuth,
    u0, lo_v, hi_v, lift, key, row id, ...)."""
    if not pending:
        return []
    cols = list(zip(*pending, strict=True))
    rows, slots, groups, levels, alphas, u0, lo_v, hi_v, lifts = (np.array(c) for c in cols[:9])
    keys, rids = cols[9], cols[10]
    u1 = u0 + along
    x = np.stack([u1, u1, u0, u0], axis=1)
    y = np.stack([lo_v, hi_v, hi_v, lo_v], axis=1)
    if slope != 1.0:
        y = slope * y
    angle = -rot * math.pi / 180.0
    cosp, sinp = math.cos(angle), math.sin(angle)
    if abs(cosp) < 2.5e-16:
        cosp = 0.0
    if abs(sinp) < 2.5e-16:
        sinp = 0.0
    px = cosp * x + (-sinp) * y
    py = sinp * x + cosp * y
    cx, cy = px.mean(axis=1), py.mean(axis=1)
    z = (surface.z_of(cx, cy) + stand_off + lifts).tolist()
    corners = np.stack([px, py], axis=2).tolist()
    return [PlacedModule(row=r, slot=s, group=g, corners=[tuple(c) for c in corners[i]], centre=(cx_i, cy_i),
                         z=z[i], tilt=tilt, azimuth=a, level=k, key=keys[i], rid=rids[i])
            for i, (r, s, g, k, a, cx_i, cy_i) in enumerate(zip(rows.tolist(), slots.tolist(), groups.tolist(),
                                                                levels.tolist(), alphas.tolist(), cx.tolist(),
                                                                cy.tolist(), strict=True))]
