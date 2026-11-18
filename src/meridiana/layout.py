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

import bisect
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
# How the places of the rows stand to each other (R418). LEGACY_ALIGNMENT is what a sub-field saved before keeps until
# the designer changes it (its params say nothing): every row centred on its own room, from the front edge.
ALIGNMENTS = ("aligned", "staggered", "free")
LEGACY_ALIGNMENT = "legacy"
NEW_ALIGNMENT = "aligned"       # of a sub-field drawn now (model.new_params)
# Where the modules of a power asked (R417) are taken from: "best" the rows least in shadow, of those alike the front
# ones; "front" whole rows from the front edge (the eave on a pitch); "back" whole rows from the back (the ridge). In
# all three the rows are next to each other and only the last one is in part.
TARGET_FROM = ("best", "front", "back")
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
    alignment: str = LEGACY_ALIGNMENT  # or one of ALIGNMENTS (R418)
    target_kwp: float = 0.0           # the power asked of the sub-field, 0 none: how many modules it lays (R417)
    target_from: str = "best"         # one of TARGET_FROM: where the rows of the power asked start


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
    # degrees about its own normal (right hand, facing out) from the place where its `along` side is level: a row
    # on a pitch that does not run level (R278, R280); 0 for every module of a level row
    spin: float = 0.0

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
    capacity: int = 0              # the modules the sub-field can hold, whatever the power asked
    target_missing: int = 0        # the modules short of the power asked
    # R445: the modules of a sub-field that is its modules set aside because they lie on an obstacle (with its
    # clearance) or off the roof: drawn red, not counted, put back with a click (SubField.kept)
    blocked: list = field(default_factory=list)

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


TIE = 1e-5          # relative: two rectangles whose areas differ by less are the same minimum (R551): a point drawn
                    # and rounded to 0.1 mm moves a 20 m triangle's rectangles by some millionths, a hand's wobble by more


def _least_rectangles(area: Polygon) -> list[float]:
    """The directions (radians) of the hull's edges whose rectangle around the area is the least, all of them when two
    or more are equal to TIE: a right isosceles triangle has two, along its legs and along its hypotenuse, and which
    one shapely's minimum_rotated_rectangle gave turned on the last digits of the points (R551)."""
    hull = list(area.convex_hull.exterior.coords)
    sizes = []
    for (x1, y1), (x2, y2) in zip(hull, hull[1:]):
        if math.hypot(x2 - x1, y2 - y1) < EPS:
            continue
        ax = math.atan2(y2 - y1, x2 - x1)
        c, s = math.cos(ax), math.sin(ax)
        us = [x * c + y * s for x, y in hull]
        vs = [-x * s + y * c for x, y in hull]
        sizes.append(((max(us) - min(us)) * (max(vs) - min(vs)), ax))
    if not sizes:
        return [0.0]
    least = min(size for size, _ax in sizes)
    return [ax for size, ax in sizes if size <= least * (1 + TIE) + 1e-12]


def auto_azimuth(area: Polygon, east_west: bool = False) -> float:
    """Of the two directions of the area's minimum rotated rectangle, the one that lets the rows face
    closest to South: on a flat surface the yield matters more than the long side. For east-west pairs,
    the one closest to East (the pair then faces East and West). R551 (Daniel 08/11/2026: «la preview di come
    verranno posati i moduli non è corretta»): when two rectangles are the least alike, the rule chooses among all
    their directions, so the answer no longer turns on the last digits of the points (the preview of an area drawn
    as modules laid a right isosceles triangle along its hypotenuse, the layout of the same triangle along its legs)."""
    best = None
    for edge in _least_rectangles(area):
        for ax in (edge, edge + math.pi / 2):
            nx, ny = -math.sin(ax), math.cos(ax)
            if (east_west and nx < 0) or (not east_west and ny > 0):
                nx, ny = -nx, -ny               # towards East for a pair, towards South otherwise
            alpha = geo.bearing_to_azimuth(geo.bearing(nx, ny))
            score = abs(abs(alpha) - 90.0) if east_west else abs(alpha)
            if best is None or score < best[0] - 1e-9:
                best = (score, alpha)
    return round(best[1], 2)


def _intervals_free(strip: Polygon, usable, u0: float, u1: float) -> list[tuple[float, float]]:
    """The u-ranges of the strip where a module spanning its whole depth stays inside `usable`: whatever
    of the strip is not usable forbids its u-projection."""
    bad = strip.difference(usable)
    return _free_between(sorted((g.bounds[0], g.bounds[2]) for g in _polys(bad) if g.area > EPS), u0, u1)


def _free_between(cuts: list[tuple[float, float]], u0: float, u1: float) -> list[tuple[float, float]]:
    """What the cuts (sorted u-ranges) leave of the range from u0 to u1."""
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
    flush plane v scaled back along the slope (`slope`, the cosine of the tilt). On the plane of a pitch whose rows
    do not run level (`on_plane`, R278, R280) the frame is the plane's own, in true metres on it: `m` is the plan to
    work linear map (a, b, c, d), u along the row, v square to it on the plane, towards the back."""
    azimuth: float
    rot: float
    slope: float
    m: tuple | None = None

    @classmethod
    def on_plane(cls, azimuth: float, plane_tilt: float, plane_azimuth: float) -> "Frame":
        """The frame of a row facing `azimuth` (its plan direction, the side its front edge looks to) on the plane
        of tilt and azimuth given: the plan turned so that the plane faces -v, v scaled back along the slope (the
        plane's own metres), then turned so that the row's plan direction lifted onto the plane runs along u."""
        first = cls.of(plane_azimuth, plane_tilt, True)
        level = cls.of(azimuth, 0.0, False)
        ax, ay = level.along()
        cu, cv = first.to_work(ax, ay)
        phi = math.atan2(cv, cu)
        c1, s1 = first._cs(first.rot)
        k = 1.0 / first.slope
        cp, sp = math.cos(-phi), math.sin(-phi)
        # M = R(-phi) . S(1, k) . R(rot)
        a, b, c, d = c1, -s1, k * s1, k * c1
        return cls(azimuth, level.rot, 1.0, (cp * a - sp * c, cp * b - sp * d, sp * a + cp * c, sp * b + cp * d))

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
        if self.m is not None:
            a, b, c, d = self.m
            return a * x + b * y, c * x + d * y
        c, s = self._cs(self.rot)
        return c * x - s * y, (s * x + c * y) / self.slope

    def to_plan(self, u: float, v: float) -> tuple[float, float]:
        if self.m is not None:
            a, b, c, d = self.m
            det = a * d - b * c
            return (d * u - b * v) / det, (a * v - c * u) / det
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
    plane: tuple | None = None        # (tilt, azimuth) of the pitch the rows stand on, None on a level surface

    @classmethod
    def of(cls, module: Module, p: Params, tilt: float, turned: bool = False,
           surface: Surface | None = None) -> "Sizes":
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
        plane = (surface.tilt, surface.azimuth) if surface is not None and surface.tilt > 0 else None
        return cls(along, across, stack, depth, rise, flush, tilt, p.mounting == "east_west", p.gap, p.stack_gap,
                   p.ew_ridge_gap, plane)


def row_frame(azimuth: float, size: Sizes) -> Frame:
    """The work frame of a row facing `azimuth` with the sizes of its sub-field: on a pitch, the plane's own for
    east-west pairs (their feet on it, R278) and for flush rows that do not run level (R280); else Frame.of."""
    plane = size.plane
    if plane is not None and (size.east_west or size.flush):
        level = abs((azimuth - plane[1] + 180.0) % 360.0 - 180.0) < 1e-6
        if size.east_west or not level:
            return Frame.on_plane(azimuth, plane[0], plane[1])
    return Frame.of(azimuth, size.tilt, size.flush)


def compute(area_ring, surface: Surface | None = None, module: Module | None = None, params: Params | None = None,
            exclusions: list[Exclusion] = (), lat: float = 45.0, lon: float = 9.0,
            removed: set[str] = frozenset(), rows: list[Row] | None = None, shaded=(),
            host=None, kept: set[str] = frozenset()) -> Result:
    """Fill the area (a plan ring, local metres) with modules. `lat`, `lon` place the sun for the pitch;
    `removed` are module keys the designer took out by hand. With `rows` (a sub-field laid by hand, task 16c) the
    modules are those of the rows given, wherever they are: nothing is made again, and the fire-brigade groups
    are found from the modules (`clusters`) rather than made. `shaded`, (weight, exclusions) pairs, are the areas in
    shadow that the places for a power asked keep away from (`_fit_target`). With `host` (a plan ring: the roof the
    sub-field lies on, R445) the modules of the rows that lie on an exclusion with its clearance or off the host are set
    aside in `Result.blocked`, drawn red, unless their key is in `kept`: the designer's call."""
    surface = surface or Surface()
    module = module or Module()
    p = params or Params()
    if p.mounting not in MOUNTINGS:
        raise ValueError(f"unknown mounting {p.mounting!r}")
    if p.alignment != LEGACY_ALIGNMENT and p.alignment not in ALIGNMENTS:
        raise ValueError(f"unknown alignment {p.alignment!r}")
    if p.target_from not in TARGET_FROM:
        raise ValueError(f"unknown start of the power asked {p.target_from!r}")
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
    size = Sizes.of(module, p, tilt, surface=surface)
    frame = row_frame(alpha, size)
    rot, slope = frame.rot, frame.slope

    def to_work(g):
        if frame.m is not None:
            return affinity.affine_transform(g, [*frame.m, 0.0, 0.0])
        g = affinity.rotate(g, rot, origin=(0, 0))
        return affinity.scale(g, 1.0, 1.0 / slope, origin=(0, 0)) if slope != 1.0 else g

    usable = usable_area(area, p, exclusions)
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
        usable_w = to_work(usable)
        rows, group_of = (_auto_rows(usable_w, frame, size, p, pitch) if p.alignment == LEGACY_ALIGNMENT else
                          _arranged_rows(usable_w, frame, size, p, pitch))
    else:
        group_of = {}
    whole = rows
    capacity, missing = 0, 0
    # a sub-field drawn as its modules (host given, R445) keeps its rows whole in the file and lays the power asked
    # out of them; rows laid by hand on an area stay the designer's
    if p.target_kwp > 0 and (not manual or host is not None):
        out = set(removed)
        if manual:          # the modules set aside on an obstacle do not count for the power asked
            out |= {pm.key for pm in set_aside(modules_of(rows, module, p, surface, removed), host, p, exclusions,
                                               kept)[1]}
        costs = _shade_costs(rows, frame, size, [(w, to_work(_exclusion_union(e))) for w, e in shaded if e])
        rows, group_of, capacity, missing = _fit_target(rows, group_of, frame, size, p, module, out, costs)
    placed = modules_of(rows, module, p, surface, removed)
    blocked_out: list[PlacedModule] = []
    if manual and host is not None and placed:
        placed, blocked_out = set_aside(placed, host, p, exclusions, kept)
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
    laid = {k for r in whole for k in row_keys(r, size)}
    unmatched = sorted(k for k in removed if k not in laid)
    return Result(modules=placed, usable=[_ring(g) for g in _polys(usable)], groups=groups, azimuth=round(alpha, 2),
                  tilt=tilt, pitch=round(pitch, 3), clearance=round(clearance, 3), limit_angle=limit,
                  area=round(area.area, 2), notes=notes,
                  corners=np.array([pm.corners for pm in placed], dtype=float).reshape(-1, 4, 2),
                  keys=[pm.key for pm in placed], rows=list(rows), manual=manual, unmatched=unmatched,
                  capacity=capacity or len(placed), target_missing=missing, blocked=blocked_out)


def blocked_zones(p: Params, exclusions: list[Exclusion] = ()) -> list[Polygon]:
    """The exclusions with their clearances (1 m more for vents, openings and plant under the fire-brigade rules)."""
    return [Polygon(e.ring, e.holes or None).buffer(e.clearance + (p.fire_edge if p.fire_rules and e.kind in ("vent", "opening", "plant") else 0.0),
                                       join_style="mitre") for e in exclusions if len(e.ring) >= 3]


def usable_area(area: Polygon, p: Params, exclusions: list[Exclusion] = ()):
    """Where modules may go: the area less its edge band (1 m under the fire-brigade rules) and the exclusions
    with their clearances (1 m more for vents, openings and plant under the rules)."""
    edge = max(p.edge, p.fire_edge if p.fire_rules else 0.0)
    usable = area.buffer(-edge, join_style="mitre") if edge > 0 else area
    blocked = blocked_zones(p, exclusions)
    if blocked:
        usable = usable.difference(unary_union(blocked))
    return usable


def set_aside(placed: list[PlacedModule], host, p: Params, exclusions: list[Exclusion] = (),
              kept: set[str] = frozenset()) -> tuple[list[PlacedModule], list[PlacedModule]]:
    """The modules that may stay and those set aside (R445, decision 3): a module on an exclusion with its clearance
    or more than a hair off `host` (the roof's plan ring) goes aside, unless its key is in `kept`. The band from the
    roof edge is not a reason: the fire-brigade rules are a guide and a check there (decision 2)."""
    zone = Polygon(host).buffer(0)
    blocked = blocked_zones(p, exclusions)
    if blocked:
        zone = zone.difference(unary_union(blocked))
    polys = shapely.polygons(np.array([pm.corners for pm in placed], dtype=float))
    off = shapely.area(shapely.difference(polys, zone.buffer(DISTANCE_TOLERANCE))) > 1e-4
    stay, aside = [], []
    for pm, out in zip(placed, off.tolist(), strict=True):
        (aside if out and pm.key not in kept else stay).append(pm)
    return stay, aside


def _row_lines(start: float, maxv: float, depth: float, pitch: float, p: Params) -> list[tuple[float, int]]:
    """The front edges of regular rows from `start`, a pitch apart, with their fire-brigade band across the rows."""
    lines_v: list[tuple[float, int]] = []
    v, group_start, gv = start, start, 0
    while v + depth <= maxv + EPS:
        if p.fire_rules and v + depth - group_start > p.fire_group + EPS:
            v = max(v, lines_v[-1][0] + depth + p.fire_corridor if lines_v else v)
            group_start, gv = v, gv + 1
            if v + depth > maxv + EPS:
                break
        lines_v.append((v, gv))
        v += pitch
    return lines_v


def _fire_cells(minu: float, maxu: float, p: Params) -> list[tuple[float, float]]:
    """The stretches along the rows a group may take: the whole width, or 20 m with 2 m corridors under the rules."""
    if not p.fire_rules:
        return [(minu, maxu)]
    cells, u = [], minu
    while u < maxu - EPS:
        cells.append((u, min(u + p.fire_group, maxu)))
        u += p.fire_group + p.fire_corridor
    return cells


def _auto_rows(usable_w, frame: Frame, size: Sizes, p: Params, pitch: float) -> tuple[list[Row], dict]:
    """The rows of the automatic layout in the usable area (in the work frame): from the front edge, a row every
    pitch; with the fire rules, groups at most 20 m deep and 20 m wide. A row for each line, with the id «f1»,
    «f2»... in their order (a line without room keeps its number); and the fire-brigade group of each slot."""
    depth = size.depth
    minu, minv, maxu, maxv = usable_w.bounds
    rows_v = _row_lines(minv, maxv, depth, pitch, p)
    cells = _fire_cells(minu, maxu, p)
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


def _exclusion_union(exclusions: list[Exclusion]):
    return unary_union([Polygon(e.ring, e.holes or None).buffer(0) for e in exclusions if len(e.ring) >= 3])


MAX_ROW_SEEDS = 24              # origins of the rows tried, across them
MIN_ROW_SEEDS = 6               # on a roof so wide that this many rows are enough for a row's worth of gain
MAX_STRIPS = 1200               # rows looked at in all: they are what costs most, 0,1-0,4 ms each in GEOS
MAX_COARSE_ORIGINS = 48         # origins of the columns tried per origin of the rows; all of them for the best one
ORIGIN_CHUNK = 64               # origins of the columns counted at a time


def _row_seeds(usable_w, minv: float, pitch: float, depth: float) -> list[float]:
    """Where the rows may start, from the front edge and within a pitch: against each height of the outline with their
    front or their back (a corner of the shape is where a row gains or loses most), and regularly between."""
    heights = shapely.get_coordinates(usable_w)[:, 1]
    found = np.concatenate([(heights - minv) % pitch, (heights - depth - minv) % pitch, np.arange(1, 12) * pitch / 12])
    found = np.unique(np.round(found, 3))
    found = found[(found > 0.0005) & (found < pitch - 0.0005)]
    rows = max(1.0, (float(heights.max()) - minv) / pitch)
    seeds = int(min(MAX_ROW_SEEDS, max(MIN_ROW_SEEDS, MAX_STRIPS / rows)))
    if len(found) > seeds - 1:
        found = found[np.linspace(0, len(found) - 1, seeds - 1).round().astype(int)]
    return [0.0, *found.tolist()]


class _Strips:
    """What is free along the rows at each front edge, each edge computed once, all at a time in GEOS."""

    def __init__(self, usable_w, depth: float, cells: list[tuple[float, float]]):
        self.usable, self.depth, self.cells = usable_w, depth, cells
        self.minu, self.maxu = usable_w.bounds[0], usable_w.bounds[2]
        self.free: dict[float, list[list[tuple[float, float]]]] = {}

    def load(self, edges) -> None:
        todo = sorted({v for v in edges if v not in self.free})
        if not todo:
            return
        at = np.array(todo, dtype=float)
        strips = shapely.box(self.minu - 1, at + EPS, self.maxu + 1, at + self.depth - EPS)
        parts, owner = shapely.get_parts(shapely.difference(strips, self.usable), return_index=True)
        keep = (shapely.get_type_id(parts) == 3) & (shapely.area(parts) > EPS)
        cuts: list[list[tuple[float, float]]] = [[] for _ in todo]
        for k, b in zip(owner[keep].tolist(), shapely.bounds(parts[keep]).tolist(), strict=True):
            cuts[k].append((b[0], b[2]))
        for v, row_cuts in zip(todo, cuts, strict=True):
            row_cuts.sort()
            self.free[v] = [_free_between(row_cuts, c0, c1) for c0, c1 in self.cells]

    def stretches(self, lines_v: list, cell: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """The free stretches of the rows given in a cell, as arrays: starts, ends, the row of each."""
        found = [(lo, hi, r) for r, (v, _gv) in enumerate(lines_v) for lo, hi in self.free[v][cell]]
        if not found:
            return np.zeros(0), np.zeros(0), np.zeros(0, dtype=int)
        a, b, owners = zip(*found, strict=True)
        return np.array(a), np.array(b), np.array(owners, dtype=int)


@dataclass
class _Unit:
    """What a row is made of along it: a place, or a whole table of `per` places."""
    length: float
    step: float
    per: int
    place_step: float

    @classmethod
    def of(cls, size: Sizes, p: Params) -> "_Unit":
        place_step = size.along + p.gap
        if p.table_modules > 0:
            length = p.table_modules * size.along + (p.table_modules - 1) * p.gap
            return cls(length, length + p.table_gap, p.table_modules, place_step)
        return cls(size.along, place_step, 1, place_step)

    @property
    def half(self) -> float:
        """Half a module along the row: how far a staggered row moves."""
        return self.place_step / 2

    def places(self, start: float) -> list[float]:
        return [start + k * self.place_step for k in range(self.per)]

    def fits(self, lo: float, hi: float) -> int:
        return int((hi - lo + self.step - self.length) // self.step + EPS)


def _grid_counts(a: np.ndarray, b: np.ndarray, origins: np.ndarray, unit: _Unit) -> tuple:
    """How many units of the grids of the origins given fit in each free stretch, a unit at origin + k * step: the
    counts and the k of the first and of the last, (origins, stretches) arrays."""
    first = np.ceil((a[None, :] - origins[:, None]) / unit.step - 1e-9)
    last = np.floor((b[None, :] - unit.length - origins[:, None]) / unit.step + 1e-9)
    return np.maximum(last - first + 1.0, 0.0), first, last


def _origins(a: np.ndarray, b: np.ndarray, unit: _Unit, staggered: bool) -> np.ndarray:
    """The origins of the columns worth trying. A grid that lays most can slide back until a unit starts where a free
    stretch does, so those are enough for the count; those that centre the units in the longest stretches are there
    for the choice among equals (a rectangle lays as it always did). One per millimetre."""
    n = np.floor((b - a + unit.step - unit.length) / unit.step + 1e-9)
    centred = (a + (b - a - (n * unit.step - (unit.step - unit.length))) / 2)[np.argsort(a - b)[:8]]
    found = np.concatenate([a, centred, a - unit.half, centred - unit.half] if staggered else [a, centred]) % unit.step
    _rounded, index = np.unique(np.round(found, 3), return_index=True)
    return found[index]


def _best_grid(a: np.ndarray, b: np.ndarray, owners: np.ndarray, unit: _Unit, staggered: bool, span: tuple,
               limit: int | None = None) -> tuple[float, float]:
    """The origin of the columns that lays most over the free stretches (a, b) of the rows `owners`, and how many: one
    grid; staggered, for each row the better of that grid and of the one half a module on. Of the origins that lay as
    many, the one whose modules stand most in the middle of `span`."""
    if not len(a):
        return span[0], 0.0
    origins = _origins(a, b, unit, staggered)
    if limit is not None and len(origins) > limit:
        origins = origins[np.linspace(0, len(origins) - 1, limit).round().astype(int)]
    starts = np.flatnonzero(np.r_[True, owners[1:] != owners[:-1]])
    best_count, best_edge, best = -1.0, math.inf, float(origins[0])
    for at in range(0, len(origins), ORIGIN_CHUNK):
        chunk = origins[at:at + ORIGIN_CHUNK]
        counts, first, last = _grid_counts(a, b, chunk, unit)
        total = counts.sum(axis=1)
        if staggered:
            other = _grid_counts(a, b, chunk + unit.half, unit)[0]
            total = np.maximum(np.add.reduceat(counts, starts, axis=1), np.add.reduceat(other, starts, axis=1)).sum(axis=1)
        top = float(total.max())
        if top < best_count - 0.5:
            continue
        for i in np.flatnonzero(total >= top - 0.5).tolist():
            edge = math.inf
            full = counts[i] > 0
            if full.any():
                low = float((chunk[i] + first[i][full] * unit.step).min())
                high = float((chunk[i] + last[i][full] * unit.step + unit.length).max())
                edge = abs((low - span[0]) - (span[1] - high))
            if top > best_count + 0.5 or edge < best_edge - 1e-6:
                best_count, best_edge, best = top, edge, float(chunk[i])
    return best, best_count


def _free_start(lo: float, hi: float, unit: _Unit, origin: float) -> tuple[int, float]:
    """A free row in a stretch: as many units as fit, on the columns of `origin` where its room lets them, else as
    close to them as it can, so that the rows do not shift from each other for nothing."""
    n = unit.fits(lo, hi)
    slack = max(0.0, hi - lo - (n * unit.step - (unit.step - unit.length)))
    near = origin + round((lo + slack / 2 - origin) / unit.step) * unit.step
    return n, min(max(near, lo), lo + slack)


def _free_lines(strips: _Strips, seeds: list[float], minv: float, maxv: float, depth: float, pitch: float,
                unit: _Unit, p: Params) -> list[tuple[float, int]]:
    """The rows of the free way without fire-brigade groups: the front edges that lay most, at least a pitch apart. The
    edges tried are the runs from each seed (`_row_seeds`), each keeping the pitch exact; of the choices that lay as
    many, the one with the rows closest from the front."""
    edges = sorted({v for seed in seeds for v, _gv in _row_lines(minv + seed, maxv, depth, pitch, p)})
    strips.load(edges)
    counts = [sum(unit.fits(lo, hi) for lo, hi in strips.free[v][0]) for v in edges]
    n = len(edges)
    following = [bisect.bisect_left(edges, v + pitch - 1e-9) for v in edges]
    best, chosen = [0] * (n + 1), [n] * (n + 1)     # from each edge on: the most it can lay, and the edge to start on
    for i in range(n - 1, -1, -1):
        taken = counts[i] + best[following[i]]
        if counts[i] > 0 and taken >= best[i + 1]:
            best[i], chosen[i] = taken, i
        else:
            best[i], chosen[i] = best[i + 1], chosen[i + 1]
    out: list[tuple[float, int]] = []
    i = chosen[0]
    while i < n:
        out.append((edges[i], 0))
        i = chosen[following[i]]
    return out


def _arranged_rows(usable_w, frame: Frame, size: Sizes, p: Params, pitch: float) -> tuple[list[Row], dict]:
    """The rows of a sub-field that says how its places stand (ALIGNMENTS, R418), as `_auto_rows` gives them:
    - aligned: one grid, the columns straight whatever the outline, its origin along and across the rows the one that
      lays most;
    - staggered: two grids half a module apart, each row on the one that holds more of it, staying on the grid of the
      row before when they hold as many: a row moves from the next by half a module or not at all (two such moves are
      a whole place, so nothing but these two grids can come out);
    - free: each row takes all its room, a row stands on the columns of the grid where that room lets it, and without
      fire-brigade groups the rows may stand further than the pitch where that lays more."""
    depth = size.depth
    minu, minv, maxu, maxv = usable_w.bounds
    cells = _fire_cells(minu, maxu, p)
    unit = _Unit.of(size, p)
    strips = _Strips(usable_w, depth, cells)
    seeds = _row_seeds(usable_w, minv, pitch, depth)
    mode = p.alignment
    if mode == "free" and not p.fire_rules:
        lines_v = _free_lines(strips, seeds, minv, maxv, depth, pitch, unit, p)
    else:
        runs = [_row_lines(minv + seed, maxv, depth, pitch, p) for seed in seeds]
        strips.load([v for run in runs for v, _gv in run])

        def holds(run):
            total = 0.0
            for ci, span in enumerate(cells):
                a, b, owners = strips.stretches(run, ci)
                total += (sum(unit.fits(lo, hi) for lo, hi in zip(a.tolist(), b.tolist(), strict=True)) if mode == "free"
                          else _best_grid(a, b, owners, unit, mode == "staggered", span, MAX_COARSE_ORIGINS)[1])
            return total
        totals = [holds(run) for run in runs]
        lines_v = runs[totals.index(max(totals))]           # of those alike the first: rows from the front edge
    found: list[list[tuple[float, int]]] = [[] for _ in lines_v]        # (where the place starts, its cell) per row
    for ci, span in enumerate(cells):
        a, b, owners = strips.stretches(lines_v, ci)
        if not len(a):
            continue
        origin, _count = _best_grid(a, b, owners, unit, mode == "staggered", span)
        if mode == "free":
            for r, lo, hi in zip(owners.tolist(), a.tolist(), b.tolist(), strict=True):
                n, start = _free_start(lo, hi, unit, origin)
                for k in range(n):
                    found[r] += [(u, ci) for u in unit.places(start + k * unit.step)]
            continue
        grids = [(origin, _grid_counts(a, b, np.array([origin]), unit))]
        if mode == "staggered":
            grids.append((origin + unit.half, _grid_counts(a, b, np.array([origin + unit.half]), unit)))
        on = 0
        for r in np.unique(owners).tolist():
            mine = np.flatnonzero(owners == r)
            holding = [float(g[1][0][0][mine].sum()) for g in grids]
            if holding[on] < max(holding):
                on = holding.index(max(holding))
            base, (counts, first, last) = grids[on]
            for s in mine.tolist():
                if counts[0][s] > 0:
                    for k in range(int(first[0][s]), int(last[0][s]) + 1):
                        found[r] += [(u, ci) for u in unit.places(base + k * unit.step)]
    rows: list[Row] = []
    group_of: dict = {}
    halves = 2 if size.east_west else 1
    for r, ((v0, gv), row_places) in enumerate(zip(lines_v, found, strict=True)):
        row_places.sort()
        rid = f"f{r + 1}"
        for i, (_u, ci) in enumerate(row_places):
            for h in range(halves):
                group_of[(rid, i * halves + h)] = gv * len(cells) + ci
        first_u = row_places[0][0] if row_places else minu
        x, y = frame.to_plan(first_u, v0)
        rows.append(Row(rid, x, y, frame.azimuth, [u - first_u for u, _ci in row_places]))
    return rows, group_of


def target_modules(target_kwp: float, power_kw: float) -> int:
    """The number of modules nearest to the power asked, above it too; on equal distance the one that does not exceed
    it (Daniel, 05/11/2026); at least one."""
    ratio = target_kwp / power_kw
    low = math.floor(ratio + 1e-9)
    return max(1, low if ratio - low <= low + 1 - ratio + 1e-9 else low + 1)


def _shade_costs(rows: list[Row], frame: Frame, size: Sizes, shaded: list) -> dict:
    """How much in shadow each place is: (row id, place) -> the part of the place in each area, weighted and summed. No
    hourly calculation: only the areas `Project.fill` draws from the shadows of the obstacles."""
    costs: dict = {}
    boxes, owners = [], []
    if shaded:
        for row in rows:
            u_o, v0 = frame.to_work(row.x, row.y)
            for i, offset in enumerate(row.places):
                boxes.append((u_o + offset, v0, u_o + offset + size.along, v0 + size.depth))
                owners.append((row.id, i))
    if not boxes:
        return costs
    polys = shapely.box(*np.array(boxes, dtype=float).T)
    whole = shapely.area(polys)
    for weight, area in shaded:
        parts = shapely.area(shapely.intersection(polys, area)) / whole
        for i in np.flatnonzero(parts > 1e-6).tolist():
            costs[owners[i]] = costs.get(owners[i], 0.0) + weight * float(parts[i])
    return costs


def _fit_target(rows: list[Row], group_of: dict, frame: Frame, size: Sizes, p: Params, module: Module, removed,
                costs: dict) -> tuple[list[Row], dict, int, int]:
    """The places that hold the power asked (R417), out of the rows laid: rows next to each other, only the last row
    in part, a run of its places; the set least in shadow and of those alike the frontmost ("best"), or the one
    starting on the front row ("front") or on the back row ("back", p.target_from). A table stays whole, and so
    do a place's stack and pair, so the count is the nearest these allow. The modules keep the keys they have in the
    whole layout, so that those taken out by hand and the strings stay on them. Gives the rows, their groups, the
    modules the whole layout holds and those short of the power asked."""
    halves = 2 if size.east_west else 1
    per = max(1, p.table_modules)
    lines_u = []                        # per row with places: (its index, its units)
    capacity = 0
    for r, row in enumerate(rows):
        if not row.places:
            continue
        u_o = frame.to_work(row.x, row.y)[0]
        units = []                      # (modules, how much in shadow, where its middle is along the row)
        for start in range(0, row.count, per):
            taken = range(start, min(start + per, row.count))
            count = len(taken) * halves * size.stack
            if removed:
                count = sum((row.slot_key(slot) if k == 0 else f"{row.slot_key(slot)}:{k}") not in removed
                            for i in taken for slot in range(i * halves, (i + 1) * halves) for k in range(size.stack))
            units.append((count, sum(costs.get((row.id, i), 0.0) for i in taken),
                          u_o + (row.places[taken[0]] + row.places[taken[-1]] + size.along) / 2))
        lines_u.append((frame.to_work(row.x, row.y)[1], r, units))
        capacity += sum(u[0] for u in units)
    want = target_modules(p.target_kwp, module.power_kw)
    if capacity <= want:
        return rows, group_of, capacity, want - capacity
    aim = max(p.target_kwp / module.power_kw, 1.0)
    # front to back (rows by hand may be in any order), from the back for "back"; "front" and "back" start on the
    # first row, "best" tries every start (TARGET_FROM)
    lines_u = [(r, units) for _v, r, units in sorted(lines_u, key=lambda line: line[0],
                                                       reverse=p.target_from == "back")]
    best = None
    for start in range(len(lines_u) if p.target_from == "best" else 1):
        total, cost, chosen, middle = 0, 0.0, {}, None
        for r, units in lines_u[start:]:
            held = sum(u[0] for u in units)
            if total + held <= aim:
                total += held
                cost += sum(u[1] for u in units)
                chosen[r] = (0, len(units))
                middle = (units[0][2] + units[-1][2]) / 2
                if total == aim:
                    break
                continue
            run = _run_of_units(units, aim - total, middle)
            if run is not None:
                chosen[r] = run[:2]
                total, cost = total + run[2], cost + run[3]
            break
        candidate = (round(abs(total - aim), 6), total, round(cost, 6), start)
        if best is None or candidate < best[0]:
            best = (candidate, chosen)
    return (*_cut_rows(rows, group_of, frame, best[1], per, halves), capacity, 0)


def _run_of_units(units: list[tuple], wanted: float, middle: float | None) -> tuple | None:
    """A run of units of a row holding the modules nearest to `wanted`, fewer on equal distance: (first, past the last,
    modules, shadow). Of the runs alike the one least in shadow, then the one closest to `middle` (of the row before; of
    its own row without one). None if no unit at all is nearest."""
    counts = np.r_[0.0, np.cumsum([u[0] for u in units])]
    shade = np.r_[0.0, np.cumsum([u[1] for u in units])]
    length = int(np.argmin(np.abs(counts - wanted) + 1e-9 * np.arange(len(counts))))
    if length == 0:
        return None
    if middle is None:
        middle = (units[0][2] + units[-1][2]) / 2
    best, out = None, None
    for s in range(len(units) - length + 1):
        modules = counts[s + length] - counts[s]
        cost = shade[s + length] - shade[s]
        place = abs((units[s][2] + units[s + length - 1][2]) / 2 - middle)
        candidate = (round(abs(modules - wanted), 6), modules, round(float(cost), 6), round(place, 3), s)
        if best is None or candidate < best:
            best, out = candidate, (s, s + length, int(modules), float(cost))
    return out


def _cut_rows(rows: list[Row], group_of: dict, frame: Frame, chosen: dict, per: int, halves: int) -> tuple[list, dict]:
    """The rows left with the units chosen, (first, past the last) by row index; a row left without any stays, empty,
    to keep its number. Its slots keep the keys they had."""
    out, groups = [], {}
    for r, row in enumerate(rows):
        first, past = chosen.get(r, (0, 0))
        i0, i1 = first * per, min(past * per, row.count)
        u_o, v0 = frame.to_work(row.x, row.y)
        offset = row.places[i0] if i1 > i0 else 0.0
        x, y = frame.to_plan(u_o + offset, v0) if i0 else (row.x, row.y)
        keys = [row.slot_key(slot) for slot in range(i0 * halves, i1 * halves)] if i0 else list(row.keys)
        out.append(Row(row.id, x, y, row.azimuth, [u - offset for u in row.places[i0:i1]], keys, row.turned))
        for i in range(i0, i1):
            for h in range(halves):
                groups[(row.id, (i - i0) * halves + h)] = group_of.get((row.id, i * halves + h), 0)
    return out, groups


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
        size = Sizes.of(module, p, tilt, row.turned, surface)
        frame = row_frame(row.azimuth, size)
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
                    # the heights above the surface of the module's edges at lo_v and at hi_v (on a plane, R278)
                    low, high = (0.0, 0.0) if flush else (start * math.sin(math.radians(tilt)),
                                                          (start + across) * math.sin(math.radians(tilt)))
                    batch.append((line, slot, 0, k, back_alpha if back else round(row.azimuth, 2), u0, lo_v, hi_v,
                                  lift, key, row.id, order, *((high, low) if back else (low, high))))
                    order += 1
    placed: list = [None] * order
    for (_az, turned), (frame, size, pending) in batches.items():
        made = (_place_on_plane(pending, size.along, frame, surface, p.stand_off, flush) if frame.m is not None else
                _place(pending, size.along, frame.rot, frame.slope, surface, p.stand_off, tilt))
        for pm, entry in zip(made, pending, strict=True):
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
    if frame.m is not None:
        a, b, c, d = frame.m
        u, v = a * xy[:, :, 0] + b * xy[:, :, 1], c * xy[:, :, 0] + d * xy[:, :, 1]
    else:
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


def _place_on_plane(pending: list[tuple], along: float, frame: Frame, surface: Surface,
                    stand_off: float, flush: bool) -> list[PlacedModule]:
    """The placed modules of rows in the frame of a pitch's plane (Frame.on_plane; R278, R280): each rectangle
    (u0, lo_v, hi_v) is on the plane, in its metres, and its edges at lo_v and hi_v stand the heights given above
    it along its normal (an east-west pair's foot and ridge), the stand-off added along the normal too; a flush row
    stands its stand-off straight up, as `_place` lays the level rows beside it. The corners are those of the
    module in space brought down to the plan, in the order of `_place`; the tilt and the azimuth are those of the
    module's own plane, the spin turns it about its normal to lie along the row."""
    if not pending:
        return []
    cols = list(zip(*pending, strict=True))
    u0, lo_v, hi_v = (np.array(c, dtype=float) for c in cols[5:8])
    low, high = np.array(cols[12], dtype=float), np.array(cols[13], dtype=float)
    u1 = u0 + along
    us = np.stack([u1, u1, u0, u0], axis=1)
    vs = np.stack([lo_v, hi_v, hi_v, lo_v], axis=1)
    hs = np.stack([low, high, high, low], axis=1) + (0.0 if flush else stand_off)
    a, b, c, d = frame.m
    det = a * d - b * c
    x, y = (d * us - b * vs) / det, (a * vs - c * us) / det
    fx, fy = geo.facing_vector(surface.azimuth)
    beta = math.radians(surface.tilt)
    n = np.array([math.sin(beta) * fx, math.sin(beta) * fy, math.cos(beta)])
    pts = np.stack([x, y, surface.z_of(x, y) + (stand_off if flush else 0.0)], axis=2) + hs[..., None] * n
    out = []
    for i, entry in enumerate(pending):
        p0, p1, _p2, p3 = pts[i]
        side = p0 - p3
        side /= np.linalg.norm(side)
        normal = np.cross(side, p1 - p0)
        normal /= np.linalg.norm(normal)
        if normal[2] < 0:
            normal = -normal
        # to a millionth of a degree: the halves of a row read as one orientation, a corner off its place by less
        # than a micrometre
        tilt = round(math.degrees(math.acos(min(1.0, float(normal[2])))), 6)
        azimuth = (round(geo.bearing_to_azimuth(math.degrees(math.atan2(normal[0], normal[1]))), 6) if tilt > 1e-6
                   else entry[4])
        bb = math.radians(geo.azimuth_to_bearing(azimuth))
        level = np.array([-math.cos(bb), math.sin(bb), 0.0])
        t = math.radians(tilt)
        facing = np.array([math.sin(t) * math.sin(bb), math.sin(t) * math.cos(bb), math.cos(t)])
        spin = round(math.degrees(math.atan2(float(np.cross(level, side) @ facing), float(level @ side))), 6)
        centre = pts[i].mean(axis=0)
        out.append(PlacedModule(row=entry[0], slot=entry[1], group=entry[2],
                                corners=[(float(q[0]), float(q[1])) for q in pts[i]],
                                centre=(float(centre[0]), float(centre[1])), z=float(centre[2]), tilt=tilt,
                                azimuth=azimuth, level=entry[3], key=entry[9], rid=entry[10],
                                spin=0.0 if abs(spin) < 1e-6 else spin))
    return out
