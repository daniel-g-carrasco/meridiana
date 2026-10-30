"""Geometry for the 3D view, without Qt: triangles for buildings and roof pitches, and the instance table
of the modules. The view (ui/view3d.py) only uploads what comes out of here.

Axes: the model has x East, y North, z up (geo.py); Qt Quick 3D has y up and looks down -z, so a model
point (x, y, z) is drawn at (x, z, -y). A module is the built-in "#Cube" (100 units a side) scaled to its
size, turned to face its azimuth and tilted, as Qt's instance table wants it: three rows of a 3x4
transform, a colour and a custom vector, 20 floats per module.
"""

from __future__ import annotations

import math

import numpy as np

from . import geo

Point = tuple[float, float]
WALL = (0.85, 0.83, 0.79)
ROOF_FLAT = (0.72, 0.71, 0.69)
ROOF_PITCH = (0.66, 0.36, 0.28)
MODULE = (0.10, 0.16, 0.30)
MODULE_SELECTED = (1.00, 0.66, 0.10)
OBSTACLE = (0.56, 0.57, 0.60)
TREE = (0.31, 0.47, 0.27)


def to_qt(x: float, y: float, z: float) -> tuple[float, float, float]:
    return x, z, -y


def signed_area(ring: list[Point]) -> float:
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1], strict=True))


def triangulate(ring: list[Point]) -> list[tuple[int, int, int]]:
    """Ear clipping of a simple polygon (no holes): triangles as indices into `ring`, counter-clockwise."""
    n = len(ring)
    if n < 3:
        return []
    idx = list(range(n))
    if signed_area(ring) < 0:
        idx.reverse()

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def inside(p, a, b, c):
        return cross(a, b, p) >= -1e-12 and cross(b, c, p) >= -1e-12 and cross(c, a, p) >= -1e-12

    out = []
    guard = 0
    while len(idx) > 3 and guard < 10 * n * n:
        guard += 1
        m = len(idx)
        for k in range(m):
            i0, i1, i2 = idx[(k - 1) % m], idx[k], idx[(k + 1) % m]
            a, b, c = ring[i0], ring[i1], ring[i2]
            if cross(a, b, c) <= 1e-12:
                continue                      # reflex or degenerate corner: not an ear
            if any(inside(ring[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            out.append((i0, i1, i2))
            del idx[k]
            break
        else:
            break                             # no ear found (a self-touching outline): stop, do not loop
    if len(idx) == 3:
        out.append(tuple(idx))
    return out


def _normal(p0, p1, p2):
    u = np.subtract(p1, p0)
    v = np.subtract(p2, p0)
    n = np.cross(u, v)
    length = np.linalg.norm(n)
    return n / length if length > 0 else np.array([0.0, 1.0, 0.0])


def _triangle(acc, a, b, c, colour, towards) -> None:
    """One triangle whose normal points to the side of `towards` (a Qt-axes vector): roofs face up, walls
    face out; the winding is swapped when needed, so lighting and culling agree. `acc` holds the lists of
    positions, normals and colours."""
    pos, nor, col = acc
    qa, qb, qc = to_qt(*a), to_qt(*b), to_qt(*c)
    n = _normal(qa, qb, qc)
    if float(np.dot(n, towards)) < 0:
        qb, qc = qc, qb
        n = -n
    for q in (qa, qb, qc):
        pos.append(q)
        nor.append(n)
        col.append(colour)


def _arrays(pos, nor, col) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not pos:
        empty = np.zeros((0, 3), dtype=np.float32)
        return empty, empty, empty
    return (np.asarray(pos, dtype=np.float32), np.asarray(nor, dtype=np.float32), np.asarray(col, dtype=np.float32))


def prism_triangles(ring: list[Point], z0: float, z1: float, colour=OBSTACLE) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A vertical prism, its top and its sides: an obstacle on a roof, a parapet, a tree."""
    acc = ([], [], [])
    ring = [tuple(map(float, q)) for q in ring]
    up = np.array([0.0, 1.0, 0.0])
    for i0, i1, i2 in triangulate(ring):
        _triangle(acc, (*ring[i0], z1), (*ring[i1], z1), (*ring[i2], z1), colour, up)
    ccw = signed_area(ring) > 0
    for a, b in zip(ring, ring[1:] + ring[:1], strict=True):
        dx, dy = b[0] - a[0], b[1] - a[1]
        out = np.array(to_qt(*((dy, -dx) if ccw else (-dy, dx)), 0.0))
        _triangle(acc, (a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), colour, out)
        _triangle(acc, (a[0], a[1], z0), (b[0], b[1], z1), (a[0], a[1], z1), colour, out)
    return _arrays(*acc)


def rgb(hex_: str) -> tuple[float, float, float]:
    """A colour of the theme ("#rrggbb") as the 0-1 floats of the vertex colours and of the instance table."""
    h = hex_.lstrip("#")[:6]
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def building_triangles(footprint: list[Point], pitches, colours: dict | None = None
                       ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Positions, normals and colours (each N x 3, float32, Qt axes) of the walls and the roof pitches.
    `pitches` are roofs.Pitch: a wall rises to the roof surface along its side, ridge ends included.
    `colours` ("wall", "roof", "roof_flat", as "#rrggbb" or 0-1 floats) replace the defaults: the selected
    building's, tinted."""
    pos, nor, col = [], [], []
    colours = colours or {}

    def given(key, default):
        c = colours.get(key, default)
        return rgb(c) if isinstance(c, str) else tuple(c)
    wall, roof, flat = given("wall", WALL), given("roof", ROOF_PITCH), given("roof_flat", ROOF_FLAT)

    def tri(a, b, c, colour, towards):
        _triangle((pos, nor, col), a, b, c, colour, towards)

    up = np.array([0.0, 1.0, 0.0])
    for p in pitches:
        colour = flat if p.tilt == 0 else roof
        ring = [tuple(map(float, q)) for q in p.ring]
        for i0, i1, i2 in triangulate(ring):
            a, b, c = ((ring[i][0], ring[i][1], p.z(*ring[i])) for i in (i0, i1, i2))
            tri(a, b, c, colour, up)

    def roof_z(x, y):
        return _roof_z(pitches, x, y)

    ring = [tuple(map(float, q)) for q in footprint]
    ccw = signed_area(ring) > 0
    corners = {tuple(map(float, q)) for p in pitches for q in p.ring}
    for a, b in zip(ring, ring[1:] + ring[:1], strict=True):
        between = sorted((c for c in corners if c not in (a, b) and _on_segment(c, a, b)),
                         key=lambda c: math.dist(a, c))
        top = [a, *between, b]
        dx, dy = b[0] - a[0], b[1] - a[1]
        nx, ny = (dy, -dx) if ccw else (-dy, dx)            # the side's outward normal, any outline shape
        out = np.array(to_qt(nx, ny, 0.0))
        for p0, p1 in zip(top, top[1:], strict=False):
            z0, z1 = roof_z(*p0), roof_z(*p1)
            tri((p0[0], p0[1], 0.0), (p1[0], p1[1], 0.0), (p1[0], p1[1], z1), wall, out)
            tri((p0[0], p0[1], 0.0), (p1[0], p1[1], z1), (p0[0], p0[1], z0), wall, out)
    return _arrays(pos, nor, col)


def _roof_z(pitches, x: float, y: float) -> float:
    """The height of the roof at a point of the outline: the highest pitch whose side passes there."""
    best = None
    for p in pitches:
        ring = p.ring
        for a, b in zip(ring, ring[1:] + ring[:1], strict=True):
            if _on_segment((x, y), a, b):
                z = p.z(x, y)
                best = z if best is None else max(best, z)
    if best is None:
        best = max(p.z(x, y) for p in pitches) if pitches else 0.0
    return best


# The outline of what is selected or under the pointer in 3D (Daniel, 23/10/2026: the selection «si schiarisce
# solamente», «andrebbero evidenziati i bordi esterni»): its edges as segments, (M, 2, 3) in Qt axes, drawn as
# ribbons a few pixels wide (ribbons below): Qt Quick 3D draws its lines one pixel wide with Direct3D.

def _segments(points) -> np.ndarray:
    pts = [to_qt(*q) for q in points]
    return np.array([[a, b] for a, b in zip(pts, pts[1:] + pts[:1], strict=True)], dtype=np.float64).reshape(-1, 2, 3)


def ring_edges(points3d) -> np.ndarray:
    """A closed ring of model points (x, y, z) as segments."""
    return _segments([tuple(map(float, q)) for q in points3d])


def prism_edges(ring: list[Point], z0: float, z1: float) -> np.ndarray:
    """The edges of a vertical prism: its foot, its top and its corners."""
    ring = [tuple(map(float, q)) for q in ring]
    verticals = np.array([[to_qt(x, y, z0), to_qt(x, y, z1)] for x, y in ring], dtype=np.float64).reshape(-1, 2, 3)
    return np.concatenate([ring_edges([(x, y, z0) for x, y in ring]), ring_edges([(x, y, z1) for x, y in ring]),
                           verticals])


def building_edges(footprint: list[Point], pitches) -> np.ndarray:
    """The edges of a building: its foot, the corners up to the roof, the outline of each pitch (the eaves,
    the ridges, the hips)."""
    ring = [tuple(map(float, q)) for q in footprint]
    parts = [ring_edges([(x, y, 0.0) for x, y in ring]),
             np.array([[to_qt(x, y, 0.0), to_qt(x, y, _roof_z(pitches, x, y))] for x, y in ring],
                      dtype=np.float64).reshape(-1, 2, 3)]
    for p in pitches:
        parts.append(ring_edges([(float(x), float(y), p.z(float(x), float(y))) for x, y in p.ring]))
    return np.concatenate(parts)


def module_edges(m, along: float, across: float, thickness: float = 0.035) -> np.ndarray:
    """The outline of a module's face, where module_table draws it."""
    mat, (tx, ty, tz) = _module_transform(m, along, across, thickness)
    corners = [mat @ np.array(c) + (tx, ty, tz) for c in ((-50, 50, -50), (50, 50, -50), (50, 50, 50), (-50, 50, 50))]
    return np.array([[a, b] for a, b in zip(corners, corners[1:] + corners[:1], strict=True)], dtype=np.float64)


def ribbons(segments: np.ndarray, width: float, colour) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Each segment as a square tube `width` across (positions, normals and colours of its triangles, as
    building_triangles gives them), a little longer than the segment so that the corners close."""
    segs = np.asarray(segments, dtype=np.float64).reshape(-1, 2, 3)
    if len(segs) == 0 or width <= 0:
        empty = np.zeros((0, 3), dtype=np.float32)
        return empty, empty, empty
    h = width / 2
    a, b = segs[:, 0], segs[:, 1]
    d = b - a
    n = np.linalg.norm(d, axis=1, keepdims=True)
    keep = n[:, 0] > 1e-9
    a, b, d, n = a[keep], b[keep], d[keep], n[keep]
    d = d / n
    a, b = a - d * h, b + d * h
    up = np.tile([0.0, 1.0, 0.0], (len(d), 1))
    side = np.where((np.abs(d[:, 1]) > 0.99)[:, None], np.tile([1.0, 0.0, 0.0], (len(d), 1)), up)
    u = np.cross(d, side)
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    v = np.cross(d, u)
    offsets = [(u + v), (u - v), (-u - v), (-u + v)]           # the four long edges of the tube
    quads = []
    for k in range(4):
        o0, o1 = offsets[k] * h, offsets[(k + 1) % 4] * h
        normal = o0 + o1
        normal /= np.linalg.norm(normal, axis=1, keepdims=True)
        p00, p01, p10, p11 = a + o0, a + o1, b + o0, b + o1
        quads.append((p00, p10, p11, normal))
        quads.append((p00, p11, p01, normal))
    pos = np.concatenate([np.stack([q[0], q[1], q[2]], axis=1) for q in quads]).reshape(-1, 3)
    nor = np.concatenate([np.repeat(q[3][:, None, :], 3, axis=1) for q in quads]).reshape(-1, 3)
    col = np.tile(np.asarray(colour, dtype=np.float64), (len(pos), 1))
    return pos.astype(np.float32), nor.astype(np.float32), col.astype(np.float32)


RING_SEGMENTS = 48


def ring(radius: float = 1.0, axis: int = 1, segments: int = RING_SEGMENTS) -> np.ndarray:
    """A circle as `segments` segments (M, 2, 3) in Qt axes, in the plane across the axis `axis` (0 x, 1 y, 2 z),
    counter-clockwise seen from the end of that axis, closed exactly. The ring of the pivot's cross-hair; theme B's
    rotation handles are the same circle."""
    b, c = (axis + 1) % 3, (axis + 2) % 3
    t = np.linspace(0.0, 2 * math.pi, segments + 1)
    pts = np.zeros((segments + 1, 3))
    pts[:, b] = radius * np.cos(t)
    pts[:, c] = radius * np.sin(t)
    pts[-1] = pts[0]
    return np.stack([pts[:-1], pts[1:]], axis=1)


def rings(width: float, colour, radius: float = 1.0, segments: int = RING_SEGMENTS
          ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Three orthogonal rings, one across each axis, as square tubes `width` across (ribbons): Autodesk's «ball with
    three belts», which makes any rotation of the view perceivable (Safe 3D Navigation, 2008)."""
    return ribbons(np.concatenate([ring(radius, axis, segments) for axis in range(3)]), width, colour)


def ring_bands(width: float, colour, radius: float = 1.0, segments: int = RING_SEGMENTS
               ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The same three circles as flat bands `width` across, each in its own plane (two triangles per segment, the
    normals along the axis): what the tubes stand on as their halo, drawn dark and translucent."""
    pos, nor = [], []
    for axis in range(3):
        inner = ring(radius - width / 2, axis, segments)
        outer = ring(radius + width / 2, axis, segments)
        i0, i1, o0, o1 = inner[:, 0], inner[:, 1], outer[:, 0], outer[:, 1]
        pos.append(np.stack([i0, o0, o1, i0, o1, i1], axis=1).reshape(-1, 3))
        normal = np.zeros(3)
        normal[axis] = 1.0
        nor.append(np.tile(normal, (segments * 6, 1)))
    pos, nor = np.concatenate(pos), np.concatenate(nor)
    col = np.tile(np.asarray(colour, dtype=np.float64), (len(pos), 1))
    return pos.astype(np.float32), nor.astype(np.float32), col.astype(np.float32)


# the gizmo of Move and Rotate (task 16b; gizmo.py says where its handles are): solids turned about an axis, in Qt
# axes, one unit long (the view scales the unit to a length on the screen), white (the material gives the colour)

def _axes_of(direction) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    d = np.asarray(direction, dtype=np.float64)
    d = d / np.linalg.norm(d)
    helper = np.array([0.0, 1.0, 0.0]) if abs(d[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(d, helper)
    u /= np.linalg.norm(u)
    return d, u, np.cross(d, u)


def lathe(direction, profile, segments: int = 16, closed: bool = False,
          colour=(1.0, 1.0, 1.0)) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A solid turned about the axis `direction` through the origin: `profile` is the list of (t, r), t along the
    axis and r from it, each pair of points sweeping a band of `segments` quads; `closed` joins the last point to
    the first (a ring's section). The triangles face away from the axis where r grows, as a solid's outside does."""
    d, u, v = _axes_of(direction)
    a = np.linspace(0.0, 2 * math.pi, segments + 1)[:-1]
    around = np.cos(a)[:, None] * u + np.sin(a)[:, None] * v                   # (segments, 3)
    pts = [d * t + around * r for t, r in profile]
    pairs = list(zip(range(len(pts) - 1), range(1, len(pts)), strict=True))
    if closed:
        pairs.append((len(pts) - 1, 0))
    pos = []
    for i, j in pairs:
        p, q = pts[i], pts[j]
        p1, q1 = np.roll(p, -1, axis=0), np.roll(q, -1, axis=0)
        pos.append(np.stack([p, q1, q, p, p1, q1], axis=1).reshape(-1, 3))
    pos = np.concatenate(pos)
    tri = pos.reshape(-1, 3, 3)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    length = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.where(length > 1e-12, n / np.maximum(length, 1e-12), d)
    nor = np.repeat(n, 3, axis=0)
    col = np.tile(np.asarray(colour, dtype=np.float64), (len(pos), 1))
    return pos.astype(np.float32), nor.astype(np.float32), col.astype(np.float32)


GIZMO_SHAFT = (0.14, 0.76, 0.022)        # an arrow's shaft: from, to, radius (units of the arrow's length)
GIZMO_HEAD = (0.76, 1.0, 0.065)          # its head: a cone from, to, radius at the base
GIZMO_RING = (0.80, 0.022, 0.012)        # the ring: radius, half the width of its band, half its thickness
GIZMO_PLANE = (0.26, 0.46)               # the square of the horizontal plane, between these along East and North
GIZMO_HALO = 0.022                       # what the halo adds all round


def arrow(direction, halo: float = 0.0, segments: int = 16) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """An arrow of the gizmo along `direction` from near the origin to 1: a shaft and a cone, closed at both ends;
    `halo` makes it that much thicker (and a little longer), the dark one drawn under it."""
    t0, t1, rs = GIZMO_SHAFT
    _h0, t2, rh = GIZMO_HEAD
    return lathe(direction, [(t0 - halo, 0.0), (t0 - halo, rs + halo), (t1, rs + halo), (t1, rh + 1.6 * halo),
                             (t2 + 1.6 * halo, 0.0)], segments)


def annulus(radius: float, half_width: float, half_thickness: float, axis=(0.0, 1.0, 0.0),
            segments: int = RING_SEGMENTS) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A flat cylinder with a hole (a washer) across `axis`: the ring of the gizmo's rotation, `segments` sides."""
    h, w = half_thickness, half_width
    return lathe(axis, [(-h, radius - w), (-h, radius + w), (h, radius + w), (h, radius - w)], segments, closed=True)


def square(a: float, b: float, u=(1.0, 0.0, 0.0), v=(0.0, 0.0, -1.0)) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The square of a plane of the gizmo, from a to b along u and v (East and North by default), both faces."""
    u, v = np.asarray(u, dtype=np.float64), np.asarray(v, dtype=np.float64)
    c = [u * a + v * a, u * b + v * a, u * b + v * b, u * a + v * b]
    pos = np.array([c[0], c[1], c[2], c[0], c[2], c[3], c[0], c[2], c[1], c[0], c[3], c[2]])
    n = np.cross(u, v)
    nor = np.array([n] * 6 + [-n] * 6)
    return pos.astype(np.float32), nor.astype(np.float32), np.ones((12, 3), dtype=np.float32)


def _on_segment(p, a, b, tol: float = 1e-6) -> bool:
    ab = (b[0] - a[0], b[1] - a[1])
    ap = (p[0] - a[0], p[1] - a[1])
    length2 = ab[0] ** 2 + ab[1] ** 2
    if length2 < 1e-18:
        return math.dist(p, a) < tol
    t = (ap[0] * ab[0] + ap[1] * ab[1]) / length2
    if t < -tol or t > 1 + tol:
        return False
    return abs(ap[0] * ab[1] - ap[1] * ab[0]) / math.sqrt(length2) < tol


def _module_transforms(tilt, azimuth, along: float, across: float, thickness: float, spin=None) -> np.ndarray:
    """The 3 x 3 matrices (N, 3, 3) of "#Cube" (100 units a side) made modules: the `along` side with the row,
    the `across` side up the tilt, facing the azimuth; for arrays of tilts and azimuths, one multiplication for
    all the modules of a sub-field (task 18c, step 7). `spin` (degrees, layout.PlacedModule.spin) turns each about
    its normal: a row on a pitch that does not run level (R278, R280)."""
    mats = _level_transforms(tilt, azimuth, along, across, thickness)
    if spin is None:
        return mats
    theta = np.radians(np.asarray(spin, dtype=float))
    if not theta.any():
        return mats
    k = mats[:, :, 1] / np.linalg.norm(mats[:, :, 1], axis=1, keepdims=True)    # the normal, facing out
    cross = np.zeros((len(k), 3, 3))
    cross[:, 0, 1], cross[:, 0, 2], cross[:, 1, 2] = -k[:, 2], k[:, 1], -k[:, 0]
    cross[:, 1, 0], cross[:, 2, 0], cross[:, 2, 1] = k[:, 2], -k[:, 1], k[:, 0]
    s, c = np.sin(theta)[:, None, None], np.cos(theta)[:, None, None]
    turn = np.eye(3) + s * cross + (1.0 - c) * (cross @ cross)                    # Rodrigues
    return turn @ mats


def _level_transforms(tilt, azimuth, along: float, across: float, thickness: float) -> np.ndarray:
    """_module_transforms with the `along` side level."""
    b = np.radians(geo.azimuth_to_bearing(np.asarray(azimuth, dtype=float)))
    fe, fn = np.sin(b), np.cos(b)
    yaw = np.arctan2(fe, -fn)                 # local +z towards the side the module faces
    beta = np.radians(np.asarray(tilt, dtype=float))
    cy, sy, cb, sb = np.cos(yaw), np.sin(yaw), np.cos(beta), np.sin(beta)
    n = len(cy)
    ry = np.zeros((n, 3, 3))
    ry[:, 0, 0], ry[:, 0, 2], ry[:, 1, 1], ry[:, 2, 0], ry[:, 2, 2] = cy, sy, 1.0, -sy, cy
    rx = np.zeros((n, 3, 3))
    rx[:, 0, 0], rx[:, 1, 1], rx[:, 1, 2], rx[:, 2, 1], rx[:, 2, 2] = 1.0, cb, -sb, sb, cb
    # `along` and `across` one for all, or one each (a module turned by 90° has them the other way, task 16c)
    scale = np.zeros((n, 3, 3))
    scale[:, 0, 0] = np.broadcast_to(np.asarray(along, dtype=float) / 100.0, (n,))
    scale[:, 1, 1] = thickness / 100.0
    scale[:, 2, 2] = np.broadcast_to(np.asarray(across, dtype=float) / 100.0, (n,))
    return ry @ rx @ scale


def _sides(modules, along: float, across: float) -> tuple:
    """`along` and `across` for each module: swapped where its row is turned by 90° (layout.Row.turned)."""
    turned = np.array([bool(getattr(m, "turned", False)) for m in modules])
    if not turned.any():
        return along, across
    return np.where(turned, across, along), np.where(turned, along, across)


def _module_transform(m, along: float, across: float, thickness: float) -> tuple[np.ndarray, tuple]:
    """The 3 x 3 matrix and the place of one module."""
    x, y = m.centre
    a, c = _sides([m], along, across)
    return (_module_transforms([m.tilt], [m.azimuth], a, c, thickness, [getattr(m, "spin", 0.0)])[0],
            to_qt(x, y, m.z))


def module_table(modules, along: float, across: float, thickness: float = 0.035,
                 selected: set[int] = frozenset(), colour=MODULE, selected_colour=MODULE_SELECTED) -> np.ndarray:
    """The instance table (N x 20 float32) for Qt Quick 3D's "#Cube": the module's `along` side runs with
    the row, the `across` side up its tilt, facing its azimuth. Built in numpy for all the modules at once;
    a selection changes only its colours (`recoloured`)."""
    n = len(modules)
    table = np.zeros((n, 20), dtype=np.float32)
    if n == 0:
        return table
    a, c = _sides(modules, along, across)
    mats = _module_transforms([m.tilt for m in modules], [m.azimuth for m in modules], a, c, thickness,
                              [getattr(m, "spin", 0.0) for m in modules])
    centres = np.array([m.centre for m in modules], dtype=float)
    table[:, 0:3], table[:, 3] = mats[:, 0], centres[:, 0]
    table[:, 4:7], table[:, 7] = mats[:, 1], [m.z for m in modules]
    table[:, 8:11], table[:, 11] = mats[:, 2], -centres[:, 1]
    table[:, 15] = 1.0
    return recoloured(table, colour, selected, selected_colour, copy=False)


def recoloured(table: np.ndarray, colour=MODULE, selected=frozenset(), selected_colour=MODULE_SELECTED,
               copy: bool = True) -> np.ndarray:
    """The same instance table in these colours: `selected` are the rows in the selection's colour. The table
    given is left as it is (a copy comes back) unless `copy` is off."""
    out = table.copy() if copy else table
    out[:, 12:15] = colour
    rows = [i for i in selected if 0 <= i < len(out)]
    if rows:
        out[rows, 12:15] = selected_colour
    return out


def support_triangles(project, sf, colour=(0.30, 0.60, 0.65)) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The auxiliary support as a visible plane, also before laying modules. No change to the received building."""
    acc = ([], [], [])
    if sf.support is not None and sf.support.enabled:
        ring = [tuple(q) for q in sf.ring]
        surface = project.surface_of(sf)
        for indices in triangulate(ring):
            points = [(ring[i][0], ring[i][1], surface.z(*ring[i])) for i in indices]
            _triangle(acc, *points, colour, (0, 1, 0))
    return _arrays(*acc)


def project_scene(project, results: dict, colours: dict | None = None, sides=None
                  ) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray], np.ndarray, np.ndarray]:
    """The project's 3D scene with nothing selected, as the report draws it (ui/report_3d.py): the triangles of
    the buildings and of the obstacles (positions, normals, colours), the modules' instance table, the buildings'
    edges as segments (Qt axes). `colours` ("wall", "roof", "roof_flat", "module", "obstacle", "tree", 0-1 floats)
    replace mesh.py's; `sides(project, sf)` gives a sub-field's module as laid (jobs.module_sides by default)."""
    if sides is None:
        from .jobs import module_sides as sides
    c = {"wall": WALL, "roof": ROOF_PITCH, "roof_flat": ROOF_FLAT, "module": MODULE, "obstacle": OBSTACLE,
         "tree": TREE, **(colours or {})}
    parts, edges = [], []
    for b in project.buildings:
        try:
            pitches = b.pitches()
            parts.append(building_triangles(b.footprint, pitches, {k: c[k] for k in ("wall", "roof", "roof_flat")}))
            edges.append(building_edges(b.footprint, pitches))
        except (ValueError, IndexError):
            continue                                    # an outline the roof cannot be made of: the plan says it
    for o in project.obstacle_prisms():
        colour = {"tree": c["tree"], "parapet": c["wall"]}.get(o["kind"], c["obstacle"])
        parts.append(prism_triangles(o["ring"], o["z0"], o["z1"], colour))
    for sf in project.subfields:
        if sf.support is not None and sf.support.enabled:
            parts.append(support_triangles(project, sf))
    tri = tuple(np.concatenate([p[i] for p in parts]) if parts else np.zeros((0, 3), np.float32) for i in range(3))
    tables = []
    for sf in project.subfields:
        r = results.get(sf.id)
        if r is None or isinstance(r, Exception) or not sf.filled or not getattr(r, "modules", None):
            continue
        along, across = sides(project, sf)
        table = r.table if getattr(r, "table", None) is not None and len(r.table) == len(r.modules) else \
            module_table(r.modules, along, across)
        tables.append(recoloured(table, c["module"]))
    table = np.concatenate(tables) if tables else np.zeros((0, 20), np.float32)
    segs = np.concatenate(edges) if edges else np.zeros((0, 2, 3))
    return tri, table, segs
