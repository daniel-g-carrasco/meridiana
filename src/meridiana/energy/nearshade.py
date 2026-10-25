"""Near shading from the scene, as PVsyst's 3D near shadings do: the obstacles (a chimney, roof plant, a
parapet, a tree, the other buildings) cast their shadows on the planes of the modules for a grid of sun
positions; the shaded share of the modules' area, read hour by hour, takes the direct and circumsolar light,
and the part of the sky the obstacles hide, integrated over the dome as the horizon's is, takes the diffuse.

An obstacle is a set of convex solids given by their corners: a vertical prism on a convex footprint, the
volume under a roof pitch; a footprint that is not convex is cut into triangles. The shadow of a convex
solid on a plane, along the sun's rays, is the convex hull of the shadows of its corners, once the solid is
cut by the plane: what lies behind the plane of the modules cannot shade their face. The modules of an
array lie on parallel planes (one for a roof, one per row of tilted tables), each with its own shadows.

The linear loss is the shaded share of the area. The electrical effect, once the modules are laid in strings,
follows the experimental model of Martinez-Moreno, Munoz and Lorenzo (Solar Energy Materials and Solar Cells
94, 2010, 2298-2303; pvlib.shading.direct_martinez): the direct light of a string is cut by its shaded share
and again by the share of its blocks (the cells behind one bypass diode) that the shadow touches. The blocks
are drawn on each module as pvlib's notes describe them: three strips along the long side, one per diode,
split in two halves in a module of half cells (its junction boxes apart). A module standing upright and
shaded from below has all its blocks touched; one of half cells keeps its upper half. PVsyst's partition
model, which loses a whole string for one shaded row of cells and then scales by a fraction, is an upper
bound by its own help's account: a parapet along the ends of the rows would cost half the direct light.
"""

from __future__ import annotations

import hashlib
import math
import threading
from dataclasses import dataclass, field

import numpy as np

AZ_STEP, EL_STEP = 5.0, 4.0
AZIMUTHS = np.arange(0.0, 360.0, AZ_STEP)            # of the sun, from North clockwise
ELEVATIONS = np.arange(2.0, 90.0, EL_STEP)


@dataclass
class Solid:
    corners: np.ndarray             # (k, 3): x East, y North, z up, local metres
    name: str = ""


@dataclass
class Shading:
    """What the simulation needs of an array's near shading."""
    table: np.ndarray               # shaded share of the modules: rows ELEVATIONS, columns AZIMUTHS
    sky: float                      # share of the isotropic sky the modules still see past the obstacles
    obstacles: list[str] = field(default_factory=list)
    keys: list = field(default_factory=list)          # the modules' keys, in the order of `modules`
    modules: np.ndarray | None = None                 # each module's shaded share, (modules, rows, columns)
    blocks: np.ndarray | None = None                  # the blocks of each module the shadow touches, same shape
    per_module: int = 3                               # blocks a module has


def _pieces(ring) -> list[list[int]]:
    """The ring itself when it is convex, else its triangles; as indices into the ring."""
    n = len(ring)
    turns = set()
    for i in range(n):
        (ax, ay), (bx, by), (cx, cy) = ring[i - 1], ring[i], ring[(i + 1) % n]
        cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if abs(cross) > 1e-12:
            turns.add(cross > 0)
    if len(turns) <= 1:
        return [list(range(n))]
    from ..mesh import triangulate
    return [list(t) for t in triangulate([tuple(p) for p in ring])]


def prism(ring, z0: float, z1: float, name: str = "") -> list[Solid]:
    """A vertical prism on a plan ring, from z0 up to z1."""
    ring = [(float(x), float(y)) for x, y in ring]
    if len(ring) < 3 or z1 <= z0:
        return []
    return [Solid(np.array([(*ring[i], z) for z in (z0, z1) for i in idx]), name) for idx in _pieces(ring)]


def under(ring3d, z_bottom: float, name: str = "") -> list[Solid]:
    """The volume between a plane polygon in space (a roof pitch) and the horizontal plane z_bottom."""
    pts = [(float(x), float(y), float(z)) for x, y, z in ring3d]
    if len(pts) < 3 or max(p[2] for p in pts) <= z_bottom + 1e-6:
        return []
    out = []
    for idx in _pieces([(x, y) for x, y, _z in pts]):
        top = [pts[i] for i in idx]
        out.append(Solid(np.array(top + [(x, y, z_bottom) for x, y, _z in top]), name))
    return out


def sun_vectors(azimuth, elevation) -> np.ndarray:
    """Towards the sun (N x 3), x East, y North, z up; azimuth from North clockwise, degrees."""
    a, e = np.radians(np.asarray(azimuth, dtype=float)), np.radians(np.asarray(elevation, dtype=float))
    return np.stack([np.sin(a) * np.cos(e), np.cos(a) * np.cos(e), np.sin(e)], axis=-1)


def plane_axes(tilt: float, azimuth: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The normal of a plane of modules and two axes on it: e1 level along the rows, e2 up the slope.
    `azimuth` is CEI 82-25's: from South, + towards West."""
    from .. import geo
    fx, fy = geo.facing_vector(azimuth)
    b = math.radians(tilt)
    n = np.array([math.sin(b) * fx, math.sin(b) * fy, math.cos(b)])
    e1 = np.array([-fy, fx, 0.0])
    e2 = np.cross(n, e1)
    return n, e1, e2


def module_corners(pm) -> np.ndarray:
    """The four corners in space of a placed module (layout.PlacedModule): its plan footprint lifted to the
    plane through its centre with its tilt."""
    return modules_corners([pm])[0]


def modules_corners(modules: list) -> np.ndarray:
    """module_corners for every module at once, (modules, corners, 3); the modules all have the same number
    of corners (a placed module has four)."""
    from .. import geo
    xy = np.array([pm.corners for pm in modules], dtype=float)
    centre = np.array([pm.centre for pm in modules], dtype=float)
    z = np.array([pm.z for pm in modules], dtype=float)
    seen: dict = {}
    facing = np.array([seen.setdefault((pm.azimuth, pm.tilt), (*geo.facing_vector(pm.azimuth),
                                                                 math.tan(math.radians(pm.tilt))))
                       for pm in modules], dtype=float)
    fx, fy, t = facing[:, 0:1], facing[:, 1:2], facing[:, 2:3]
    zc = z[:, None] - ((xy[..., 0] - centre[:, 0:1]) * fx + (xy[..., 1] - centre[:, 1:2]) * fy) * t
    return np.concatenate([xy, zc[..., None]], axis=2)


def _hulls(solid: Solid, n, d: float, axes: np.ndarray, suns: np.ndarray):
    """The shadow of a convex solid on the plane n.x = d, in the plane's coordinates, for each sun
    direction (all in front of the plane): an array of polygons, or None when nothing is in front."""
    import shapely
    v = solid.corners
    dist = v @ n - d
    front = dist > 1e-9
    if not front.any():
        return None
    vf, df = v[front], dist[front]
    back = ~front
    cross = np.zeros((0, 3))
    if back.any():
        vb, db = v[back], dist[back]
        t = df[:, None] / (df[:, None] - db[None, :])                    # (front, back)
        cross = (vf[:, None, :] + (vb[None, :, :] - vf[:, None, :]) * t[..., None]).reshape(-1, 3)
    ns = suns @ n                                                         # > 0 for every sun given
    proj = vf[None, :, :] - suns[:, None, :] * (df[None, :, None] / ns[:, None, None])
    uv = proj @ axes.T                                                    # (suns, front, 2)
    if len(cross):
        on_plane = np.broadcast_to(cross @ axes.T, (len(suns), len(cross), 2))
        uv = np.concatenate([uv, on_plane], axis=1)
    # the hull of the points as a line's vertices: the same polygon as from a multipoint, without a point
    # geometry for each corner
    return shapely.convex_hull(shapely.linestrings(uv) if uv.shape[1] >= 2 else shapely.multipoints(uv))


def _runs(rects: np.ndarray, gap: float = 0.1) -> tuple[np.ndarray, np.ndarray]:
    """The modules of a plane (rectangles umin, vmin, umax, vmax on the plane's axes) merged into runs of
    modules side by side: the runs' rectangles and, for each, the share of it the modules cover (the gaps
    for the clamps are left out of the area)."""
    out, cover = [], []
    order = np.lexsort((rects[:, 0], np.round(rects[:, 3], 3), np.round(rects[:, 1], 3)))
    cur = None
    for umin, vmin, umax, vmax in rects[order]:
        if (cur is not None and abs(vmin - cur[1]) < 1e-3 and abs(vmax - cur[3]) < 1e-3
                and umin - cur[2] <= gap):
            cur[2] = max(cur[2], umax)
            cur[4] += (umax - umin) * (vmax - vmin)
            continue
        if cur is not None:
            out.append(cur[:4])
            cover.append(cur[4] / ((cur[2] - cur[0]) * (cur[3] - cur[1])))
        cur = [umin, vmin, umax, vmax, (umax - umin) * (vmax - vmin)]
    out.append(cur[:4])
    cover.append(cur[4] / ((cur[2] - cur[0]) * (cur[3] - cur[1])))
    return np.array(out), np.array(cover)


def needed_cells(azimuth, elevation) -> np.ndarray:
    """The cells of the grid that the hourly sun positions given read (at() interpolates between four),
    and every other cell of the whole dome for the diffuse: the rest of the table is not computed."""
    mask = np.zeros((len(ELEVATIONS), len(AZIMUTHS)), dtype=bool)
    mask[::2, ::2] = True
    az = np.mod(np.asarray(azimuth, dtype=float), 360.0)
    el = np.asarray(elevation, dtype=float)
    up = el > 0
    az, el = az[up], el[up]
    j0 = np.floor(az / AZ_STEP).astype(int) % len(AZIMUTHS)
    i0 = np.floor(np.clip((el - ELEVATIONS[0]) / EL_STEP, 0.0, len(ELEVATIONS) - 1.0)).astype(int)
    for di in (0, 1):
        for dj in (0, 1):
            mask[np.minimum(i0 + di, len(ELEVATIONS) - 1), (j0 + dj) % len(AZIMUTHS)] = True
    return mask


def block_boxes(rect, layout: tuple[int, int] = (3, 1)) -> list[tuple[float, float, float, float]]:
    """The blocks of a module drawn on its rectangle (u0, v0, u1, v1): `layout` strips across the short side
    (one per bypass diode), each split into as many pieces along the long side (two for half cells)."""
    return [tuple(float(x) for x in b) for b in _block_rects(np.array([rect], dtype=float), layout)[0]]


def _block_rects(rects: np.ndarray, layout: tuple[int, int] = (3, 1)) -> np.ndarray:
    """block_boxes for many rectangles at once: (modules, blocks, 4), the blocks in block_boxes' order
    (strip by strip, each strip's pieces in turn)."""
    rects = np.asarray(rects, dtype=float).reshape(-1, 4)
    u0, v0, u1, v1 = (rects[:, c:c + 1] for c in range(4))
    strips, pieces = layout
    i = np.repeat(np.arange(strips), pieces)[None, :]
    j = np.tile(np.arange(pieces), strips)[None, :]
    du, dv = u1 - u0, v1 - v0
    # upright: the long side goes up the slope, the strips side by side along u; lying: the strips stacked
    upright = np.stack([u0 + du * i / strips, v0 + dv * j / pieces,
                        u0 + du * (i + 1) / strips, v0 + dv * (j + 1) / pieces], axis=-1)
    lying = np.stack([u0 + du * j / pieces, v0 + dv * i / strips,
                      u0 + du * (j + 1) / pieces, v0 + dv * (i + 1) / strips], axis=-1)
    return np.where((du <= dv)[..., None], upright, lying)


def blocks_of(cells: int, diodes: int | None = None, twin: bool | None = None) -> tuple[int, int]:
    """The blocks of a module: its bypass diodes and whether its half cells stand in two halves, when the
    source says (a PVsyst file does); otherwise three diodes, and half cells when it has more than 96."""
    halves = twin if twin is not None else bool(cells and cells > 96)
    return (int(diodes) if diodes else 3, 2 if halves else 1)


# The shaded area of a rectangle on the plane (a module, a run of modules) is measured in numpy from the
# shadow's rings, without cutting a polygon: by Green's theorem the area of a ring's region inside the slab
# va <= v <= vb and left of u = x is the sum over its edges of the integral of (u - x) dv along the part of
# the edge that lies in the slab and left of x (the pieces of the boundary on the slab's sides have dv = 0,
# those on u = x have u - x = 0, so only the edges count), in closed form for each edge; the area inside
# [a, b] x [va, vb] is the difference at b and at a, holes counted negative. Whether a shadow touches a block
# of cells is read on the convex hull of each solid: its u-range inside the block's slab against the block's.
# Many (ring, rectangle) pairs go through together, padded to the longest ring of their group.

CLIP_BUDGET = 100_000         # edge x rectangle terms held at once: bounds the memory of the measuring


class _Rings:
    """The rings of an object array of geometries, flat: the coordinates of every ring one after the other,
    each ring's start, length and sign (+1 an outer ring, -1 a hole), and for each geometry where its rings
    start and how many it has (contiguous). Parts that are not polygons (the hull of collinear points)
    have no area and are left out."""

    def __init__(self, geoms: np.ndarray):
        import shapely
        parts, owner = shapely.get_parts(geoms, return_index=True)
        poly = shapely.get_type_id(parts) == 3
        parts, owner = parts[poly], owner[poly]
        rings = [shapely.get_exterior_ring(parts)]
        owners = [owner]
        signs = [np.ones(len(parts))]
        holes = shapely.get_num_interior_rings(parts)
        if holes.any():
            which = np.repeat(np.arange(len(parts)), holes)
            nth = np.arange(int(holes.sum())) - np.repeat(np.cumsum(holes) - holes, holes)
            rings.append(shapely.get_interior_ring(parts[which], nth))
            owners.append(owner[which])
            signs.append(-np.ones(len(which)))
        rings, owner, sign = np.concatenate(rings), np.concatenate(owners), np.concatenate(signs)
        order = np.argsort(owner, kind="stable")
        rings, owner, self.sign = rings[order], owner[order], sign[order]
        self.coords, ring_of = shapely.get_coordinates(rings, return_index=True)
        self.length = np.bincount(ring_of, minlength=len(rings))
        self.start = np.cumsum(self.length) - self.length
        self.count = np.bincount(owner, minlength=len(geoms))
        self.first = np.cumsum(self.count) - self.count

    def expand(self, geom: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """For a list of geometry indices, every (position in the list, ring) pair."""
        cnt = self.count[geom]
        at = np.repeat(np.arange(len(geom)), cnt)
        nth = np.arange(int(cnt.sum())) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        return at, self.first[geom][at] + nth

    def _groups(self, ring: np.ndarray, width: int):
        """The rings in groups of one length, in chunks within the budget: (indices into `ring`, points)."""
        lengths = self.length[ring]
        for k in np.unique(lengths):
            sel = np.flatnonzero(lengths == k)
            step = max(1, CLIP_BUDGET // (int(k) * width))
            for s in range(0, len(sel), step):
                part = sel[s:s + step]
                yield part, self.coords[self.start[ring[part]][:, None] + np.arange(k)[None, :]]

    def areas_in(self, geom: np.ndarray, rects: np.ndarray) -> np.ndarray:
        """The area of each geometry `geom[i]` inside the rectangle `rects[i]` (umin, vmin, umax, vmax)."""
        at, ring = self.expand(geom)
        out = np.zeros(len(geom))
        if not len(ring):
            return out
        area = np.empty(len(ring))
        for part, pts in self._groups(ring, 2):
            r = rects[at[part]]
            left = _area_left(pts, r[:, 1], r[:, 3], r[:, [0, 2]])
            area[part] = np.abs(left[:, 1] - left[:, 0])
        np.add.at(out, at, self.sign[ring] * area)
        return out

    def touches(self, geom: np.ndarray, rects: np.ndarray) -> np.ndarray:
        """Whether each convex geometry `geom[i]` meets each of the rectangles `rects[i]` (several a row,
        (n, m, 4)): the geometry's u-range inside the rectangle's slab of v against the rectangle's."""
        at, ring = self.expand(geom)
        out = np.zeros(rects.shape[:2], dtype=bool)
        # the blocks of a module side by side share one slab: then the u-range is read once a row
        one_slab = bool(np.all(rects[..., 1] == rects[:, :1, 1]) and np.all(rects[..., 3] == rects[:, :1, 3]))
        for part, pts in self._groups(ring, 1 if one_slab else rects.shape[1]):
            r = rects[at[part]]                                                # (rows, m, 4)
            lo, hi = _u_range(pts, r[..., 1], r[..., 3]) if not one_slab else _u_range(pts, r[:, :1, 1], r[:, :1, 3])
            out[at[part]] |= (lo <= r[..., 2]) & (hi >= r[..., 0])
        return out


def _area_left(pts: np.ndarray, va: np.ndarray, vb: np.ndarray, u: np.ndarray) -> np.ndarray:
    """For each ring (rows, vertices, 2; padded with repeated vertices) the signed area of its region
    inside the slab va <= v <= vb (rows) and left of u = x, for each x of `u` (rows, m): (rows, m)."""
    x1, y1 = pts[..., 0], pts[..., 1]
    x2, y2 = np.roll(x1, -1, axis=1), np.roll(y1, -1, axis=1)
    dx, dy = x2 - x1, y2 - y1
    # the part of each edge inside the slab, as a parameter range [s0, s1] (empty when s1 <= s0); a level
    # or a vertical edge divides by one and takes the other branch of the choice
    level = dy == 0
    dy_safe = np.where(level, 1.0, dy)
    ta, tb = (va[:, None] - y1) / dy_safe, (vb[:, None] - y1) / dy_safe
    in_slab = (y1 >= va[:, None]) & (y1 <= vb[:, None])
    s0 = np.where(level, np.where(in_slab, 0.0, 1.0), np.minimum(ta, tb))
    s1 = np.where(level, np.where(in_slab, 1.0, 0.0), np.maximum(ta, tb))
    s0, s1 = np.clip(s0, 0.0, 1.0)[..., None], np.clip(s1, 0.0, 1.0)[..., None]
    # and left of each x: a further range
    flat = (dx == 0)[..., None]
    tx = (u[:, None, :] - x1[..., None]) / np.where(flat, 1.0, dx[..., None])
    at_left = (x1[..., None] <= u[:, None, :])
    l0 = np.where(flat, np.where(at_left, 0.0, 1.0), np.where(dx[..., None] > 0, 0.0, tx))
    l1 = np.where(flat, np.where(at_left, 1.0, 0.0), np.where(dx[..., None] > 0, tx, 1.0))
    t0 = np.maximum(s0, np.clip(l0, 0.0, 1.0))
    t1 = np.minimum(s1, np.clip(l1, 0.0, 1.0))
    t1 = np.maximum(t1, t0)
    # the integral of (x(t) - u) dy over [t0, t1]: dy ((x1 - u)(t1 - t0) + dx (t1^2 - t0^2) / 2)
    terms = dy[..., None] * ((x1[..., None] - u[:, None, :]) * (t1 - t0) + dx[..., None] * (t1 * t1 - t0 * t0) / 2.0)
    return terms.sum(axis=1)


def _u_range(pts: np.ndarray, va: np.ndarray, vb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The u-range of each convex ring (rows, vertices, 2) inside each slab va <= v <= vb (rows, m): the
    vertices inside the slab and the crossings of the edges with its sides; (inf, -inf) when none."""
    x1, y1 = pts[..., 0][:, None, :], pts[..., 1][:, None, :]                # (rows, 1, vertices)
    x2, y2 = np.roll(x1, -1, axis=2), np.roll(y1, -1, axis=2)
    dx, dy = x2 - x1, y2 - y1
    va, vb = va[..., None], vb[..., None]
    inside = (y1 >= va) & (y1 <= vb)
    lo = np.where(inside, x1, np.inf).min(axis=2)
    hi = np.where(inside, x1, -np.inf).max(axis=2)
    level = dy == 0
    dy_safe = np.where(level, 1.0, dy)
    for side in (va, vb):
        t = (side - y1) / dy_safe
        valid = ~level & (t >= 0.0) & (t <= 1.0)
        xc = x1 + dx * t
        lo = np.minimum(lo, np.where(valid, xc, np.inf).min(axis=2))
        hi = np.maximum(hi, np.where(valid, xc, -np.inf).max(axis=2))
    return lo, hi


def shading(modules: list, solids: list[Solid], tilt: float, azimuth: float,
            needed: np.ndarray | None = None, layout: tuple[int, int] = (3, 1)) -> Shading:
    """The near shading of an array: `modules` are its placed modules (layout.PlacedModule), all with
    `tilt` and `azimuth`; `solids` what can shade them; `needed` the cells of the grid to compute
    (needed_cells), all of them when not given; `layout` the blocks of a module (block_boxes).

    For each plane of modules the shadows of every cell of the sun grid are built together (one convex
    hull per solid and cell, the union where several solids shade), the (cell, run) and (cell, module)
    pairs that meet come from one query of a spatial index, and the shaded areas of the runs, the
    modules and their blocks are cut in numpy (_Rings): no Python loop over the cells, and shapely only
    for the hulls, the unions and the index."""
    import shapely
    table = np.zeros((len(ELEVATIONS), len(AZIMUTHS)))
    names = sorted({s.name for s in solids if s.name})
    if not modules or not solids:
        return Shading(table, 1.0, names)
    n, e1, e2 = plane_axes(tilt, azimuth)
    axes = np.stack([e1, e2])
    ee, aa = np.meshgrid(ELEVATIONS, AZIMUTHS, indexing="ij")
    suns_all = sun_vectors(aa.ravel(), ee.ravel())
    # the sun in front of the plane: behind it there is no direct light to lose
    lit = suns_all @ n > 1e-6
    if needed is not None:
        lit &= needed.ravel()
    suns = suns_all[lit]
    # the modules on each plane (one for a roof, one per row of tilted tables), as rectangles on its axes
    corners = modules_corners(modules)                                   # (modules, 4, 3)
    uv = corners @ axes.T
    rects_all = np.concatenate([uv.min(axis=1), uv.max(axis=1)], axis=1)   # umin, vmin, umax, vmax
    planes: dict[float, list[int]] = {}
    for i, d in enumerate(corners.mean(axis=1) @ n):
        planes.setdefault(round(float(d), 3), []).append(i)
    total = float(((rects_all[:, 2] - rects_all[:, 0]) * (rects_all[:, 3] - rects_all[:, 1])).sum())
    shaded = np.zeros(len(suns))
    per_module = np.zeros((len(modules), len(suns)), dtype=np.float32)
    touched = np.zeros((len(modules), len(suns)), dtype=np.float32)
    nb = layout[0] * layout[1]
    inset = np.array([1e-3, 1e-3, -1e-3, -1e-3])
    for d, idx in planes.items():
        mods_index = np.array(idx)
        rects_a = rects_all[mods_index]
        runs, cover = _runs(rects_a)
        boxes = shapely.box(runs[:, 0], runs[:, 1], runs[:, 2], runs[:, 3])
        mods = shapely.box(rects_a[:, 0], rects_a[:, 1], rects_a[:, 2], rects_a[:, 3])
        mods_area = shapely.area(mods)
        tree = shapely.STRtree(mods)
        runs_tree = shapely.STRtree(boxes)
        # each module's blocks, a millimetre inside their edges: a shadow that only grazes a block's edge
        # does not count it
        blocks = _block_rects(rects_a, layout) + inset                   # (modules, blocks, 4)
        reach = shapely.box(*shapely.total_bounds(boxes))
        hulls, hits = [], []
        for s in solids:
            h = _hulls(s, n, d, axes, suns)
            if h is None:
                continue
            hit = shapely.intersects(h, reach)
            if hit.any():
                hulls.append(h)
                hits.append(hit)
        if not hulls:
            continue
        hulls_a, hits_a = np.array(hulls), np.array(hits)
        # the shadow of each cell: the one solid's hull, or the union of the solids that reach the modules
        count = hits_a.sum(axis=0)
        cells = np.flatnonzero(count > 0)
        one = count[cells] == 1
        shadow = np.empty(len(cells), dtype=object)
        shadow[one] = hulls_a[hits_a[:, cells[one]].argmax(axis=0), cells[one]]
        if not one.all():
            many = cells[~one]
            shadow[~one] = shapely.union_all(np.where(hits_a[:, many], hulls_a[:, many], None), axis=0)
        rings = _Rings(shadow)
        # the linear share: every (cell, run) pair the index finds, measured at once
        ci, ri = runs_tree.query(shadow, predicate="intersects")
        if len(ci):
            area = rings.areas_in(ci, runs[ri])
            shaded[cells] += np.bincount(ci, weights=area * cover[ri], minlength=len(cells))
        # each module's share, from every (cell, module) pair; and the blocks the shadow touches, read on
        # the hulls of the solids that reach the cell (the union touches a block when one of them does)
        ci, mi = tree.query(shadow, predicate="intersects")
        if len(ci):
            share = rings.areas_in(ci, rects_a[mi]) / mods_area[mi]
            per_module[mods_index[mi], cells[ci]] = np.clip(share, 0.0, 1.0)
            pi, hi = np.nonzero(hits_a[:, cells[ci]].T)                    # (pair, solid) where it reaches
            hull_rings = _Rings(hulls_a.ravel())
            met = hull_rings.touches(hi * hits_a.shape[1] + cells[ci][pi], blocks[mi[pi]])
            hit_blocks = np.bincount((pi[:, None] * nb + np.arange(nb)[None, :]).ravel(), weights=met.ravel(),
                                     minlength=len(ci) * nb) > 0
            touched[mods_index[mi], cells[ci]] = hit_blocks.reshape(-1, nb).sum(axis=1)
    flat = np.zeros(len(suns_all))
    flat[lit] = np.clip(shaded / total, 0.0, 1.0) if total > 0 else 0.0
    table = flat.reshape(len(ELEVATIONS), len(AZIMUTHS))
    each = np.zeros((len(modules), len(suns_all)), dtype=np.float32)
    each[:, lit] = per_module
    hit = np.zeros((len(modules), len(suns_all)), dtype=np.float32)
    hit[:, lit] = touched
    shape = (len(modules), len(ELEVATIONS), len(AZIMUTHS))
    return Shading(table, diffuse_factor(table, tilt, azimuth, coarse=needed is not None), names,
                   [pm.key for pm in modules], each.reshape(shape), hit.reshape(shape), nb)


_CACHE: dict = {}
_CACHE_LOCK = threading.Lock()


def cached_shading(modules: list, solids: list[Solid], tilt: float, azimuth: float,
                   needed: np.ndarray | None = None, layout: tuple[int, int] = (3, 1)) -> Shading:
    """shading(), kept for the same scene: a change of the money or of the losses does not cast the
    shadows again."""
    h = hashlib.sha1(np.array([tilt, azimuth, *layout], dtype=float).tobytes())
    for pm in modules:
        h.update(np.array([*np.ravel(pm.corners), pm.z, pm.tilt, pm.azimuth], dtype=float).tobytes())
    for sol in solids:
        h.update(sol.corners.tobytes())
        h.update(sol.name.encode())
    if needed is not None:
        h.update(needed.tobytes())
    key = h.hexdigest()
    with _CACHE_LOCK:
        if key in _CACHE:
            return _CACHE[key]
    out = shading(modules, solids, tilt, azimuth, needed, layout)
    with _CACHE_LOCK:
        while len(_CACHE) >= 16:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = out
    return out


def at(table: np.ndarray, azimuth, elevation) -> np.ndarray:
    """The shaded share for the sun positions given (bilinear on the grid, round the circle)."""
    az = np.mod(np.asarray(azimuth, dtype=float), 360.0)
    el = np.asarray(elevation, dtype=float)
    fj = az / AZ_STEP
    j0 = np.floor(fj).astype(int) % len(AZIMUTHS)
    j1 = (j0 + 1) % len(AZIMUTHS)
    tj = fj - np.floor(fj)
    fi = np.clip((el - ELEVATIONS[0]) / EL_STEP, 0.0, len(ELEVATIONS) - 1.0)
    i0 = np.floor(fi).astype(int)
    i1 = np.minimum(i0 + 1, len(ELEVATIONS) - 1)
    ti = fi - i0
    v = (1 - ti) * ((1 - tj) * table[i0, j0] + tj * table[i0, j1]) + ti * ((1 - tj) * table[i1, j0] + tj * table[i1, j1])
    return np.where(el > 0, v, 0.0)




def _corners(azimuth, elevation):
    """The four cells of the grid around each sun position, and the weights, as at() reads them."""
    az = np.mod(np.asarray(azimuth, dtype=float), 360.0)
    el = np.asarray(elevation, dtype=float)
    fj = az / AZ_STEP
    j0 = np.floor(fj).astype(int) % len(AZIMUTHS)
    j1 = (j0 + 1) % len(AZIMUTHS)
    tj = fj - np.floor(fj)
    fi = np.clip((el - ELEVATIONS[0]) / EL_STEP, 0.0, len(ELEVATIONS) - 1.0)
    i0 = np.floor(fi).astype(int)
    i1 = np.minimum(i0 + 1, len(ELEVATIONS) - 1)
    return i0, i1, j0, j1, fi - i0, tj, el > 0


READ_CHUNK = 256                # modules whose tables are read at the hours together: 256 x 8,760 x 8 bytes


def electrical(sh: Shading, strings: list[list[str]], azimuth, elevation) -> np.ndarray:
    """For each hour, the share of the array's direct light the strings lose beyond the linear shade:
    Martinez-Moreno's (1 - F_ES) = (1 - F_GS) (1 - N_SB / (N_TB + 1)) for each string, F_GS its shaded share,
    N_SB the blocks of its modules the shadow touches, N_TB all its blocks. Modules in no string add
    nothing. The strings' modules are read from the tables a few hundred at a time and summed per string."""
    hours = len(np.atleast_1d(azimuth))
    if sh.modules is None or sh.blocks is None or not strings:
        return np.zeros(hours)
    index = {k: i for i, k in enumerate(sh.keys)}
    groups = [g for g in ([index[k] for k in keys if k in index] for keys in strings) if g]
    weights = _weights(_corners(azimuth, elevation))
    extra = np.zeros(hours)
    chunk: list[list[int]] = []
    for g in groups:
        chunk.append(g)
        if sum(len(x) for x in chunk) >= READ_CHUNK or g is groups[-1]:
            lens = np.array([len(x) for x in chunk])
            starts = np.concatenate([[0], np.cumsum(lens)[:-1]])
            rows = np.concatenate(chunk)
            f = np.clip(_read(sh.modules, rows, weights), 0.0, 1.0)
            f_mean = np.add.reduceat(f, starts, axis=0) / lens[:, None]
            shaded_blocks = np.add.reduceat(_read(sh.blocks, rows, weights), starts, axis=0)
            total_blocks = sh.per_module * lens
            extra += (lens[:, None] * (1.0 - f_mean) * shaded_blocks / (total_blocks[:, None] + 1.0)).sum(axis=0)
            chunk = []
    return extra / len(sh.keys)


def rows_electrical(shaded, stack: int = 1, upright: bool = True, layout: tuple[int, int] = (3, 1)) -> np.ndarray:
    """The electrical effect of the shade of a row on the next, as a share of the shaded rows' direct light
    beyond the linear loss, for strings running along the rows (their modules all alike). The row in front
    shades a table from below over the share `shaded` of its height: the lowest module of a stack first.
    An upright module touched has all its strips touched (in a module of half cells, the lower half first);
    one lying down has its strips touched from the lowest. Martinez-Moreno's (1 - F_ES) = (1 - F_GS)
    (1 - N_SB / N_TB), the +1 of a long string left out."""
    f = np.clip(np.asarray(shaded, dtype=float), 0.0, 1.0)
    strips, pieces = layout
    out = np.zeros_like(f)
    for k in range(max(1, stack)):
        fk = np.clip(f * stack - k, 0.0, 1.0)
        if upright:
            touched = strips * np.ceil(pieces * fk - 1e-9).clip(0, pieces)
        else:
            touched = pieces * np.ceil(strips * fk - 1e-9).clip(0, strips)
        out += (1.0 - fk) * touched / (strips * pieces)
    return out / max(1, stack)


def _weights(corners):
    """The bilinear reading of at() as a sparse matrix (cells of the grid x hours): four weights an hour,
    none for the hours with the sun below the horizon."""
    from scipy.sparse import csc_matrix
    i0, i1, j0, j1, ti, tj, up = corners
    w = len(AZIMUTHS)
    hours = len(np.atleast_1d(i0))
    cells = np.stack([i0 * w + j0, i0 * w + j1, i1 * w + j0, i1 * w + j1]).ravel()
    weights = np.stack([(1 - ti) * (1 - tj), (1 - ti) * tj, ti * (1 - tj), ti * tj]) * up[None, :]
    hour = np.tile(np.arange(hours), 4)
    return csc_matrix((weights.ravel(), (cells, hour)), shape=(len(ELEVATIONS) * w, hours))


def _read(table: np.ndarray, rows, corners) -> np.ndarray:
    """The values of some modules' tables at the sun positions of `corners` (_corners or _weights):
    (modules, hours), each module's grid as a row of cells times the weights of the hours."""
    weights = corners if not isinstance(corners, tuple) else _weights(corners)
    return np.asarray(table.reshape(len(table), -1)[rows] @ weights)


def diffuse_factor(table: np.ndarray, tilt: float, azimuth: float, coarse: bool = False) -> float:
    """The share of the isotropic sky the modules still see past the obstacles: the shaded share of each
    direction of the dome, weighted by cos(theta) on the plane and by the solid angle, as for the horizon.
    `coarse`: only every other cell, the ones needed_cells always asks for."""
    n, _e1, _e2 = plane_axes(tilt, azimuth)
    ee, aa = np.meshgrid(ELEVATIONS, AZIMUTHS, indexing="ij")
    if coarse:
        ee, aa, table = ee[::2, ::2], aa[::2, ::2], table[::2, ::2]
    s = sun_vectors(aa, ee)
    w = np.clip(s @ n, 0.0, None) * np.cos(np.radians(ee))
    total = float(w.sum())
    return float(1.0 - (w * table).sum() / total) if total > 0 else 1.0


def plan_shadow(solids: list[Solid], azimuth: float, elevation: float, z: float):
    """The shadow of the solids on the horizontal plane at height z, for the plan (one geometry, or None)."""
    import shapely
    if elevation <= 0 or not solids:
        return None
    sun = sun_vectors([azimuth], [elevation])
    flat = (np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]))
    hulls = [h[0] for s in solids if (h := _hulls(s, flat[0], z, np.stack(flat[1:]), sun)) is not None]
    return shapely.union_all(np.array(hulls, dtype=object)) if hulls else None
