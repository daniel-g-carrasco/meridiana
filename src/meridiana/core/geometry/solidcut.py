"""Closed solids cut by convex pieces, many triangles at once (R575 D9): the openings of an IFC element and the
clippings of its solids by half spaces, plane or bounded by a polygon.

A cutter is a list of convex pieces. A piece is its planes, a `(k, 4)` array of rows `nx, ny, nz, c` whose unit
normal points out of the piece: a point is inside when `n . x - c <= eps` on every plane. A point on a face counts as
inside, so a face of the solid lying on the face of a piece goes with the piece, and comes back as the face the cut
makes when the solid's material is on the other side. A concave cutter is made of several pieces (the triangles of
its profile, `convex_parts`).

What is kept of the solid's triangles: their parts outside every piece, split plane by plane (exact, NumPy). What
closes the cut (`caps`): on the plane of each face of a piece, the solid's section there (its triangles crossing the
plane, joined into rings by GEOS), inside that face, less the other pieces just beyond the plane; triangulated by GEOS
and turned to look into the cut. A piece whose inside holds only faces lying on its own planes changes nothing and is
left out: an opening already carved in the faces of a Reference View model is not carved again.

Without caps only the first part runs: the points of the cut solid, for its box and its plan. A solid that is not
closed gets no cap where its section does not close. Without Qt."""

from __future__ import annotations

import numpy as np


def plane(point, normal) -> np.ndarray:
    """The row of the plane through `point` with the unit of `normal`."""
    n = np.asarray(normal, float)
    n = n / np.linalg.norm(n)
    return np.r_[n, float(n @ np.asarray(point, float))]


def halfspace(point, normal) -> np.ndarray:
    """The piece of the points behind the plane: `normal . (x - point) <= 0`."""
    return plane(point, normal)[None, :]


def convex_parts(rings: list) -> list:
    """A planar polygon (2D outline first, then its holes) as convex 2D rings: itself when it is convex without holes,
    else the triangles of GEOS's constrained Delaunay triangulation joined across their shared edges while the join
    stays convex (Hertel and Mehlhorn). [] when GEOS cannot take it."""
    outer = np.asarray(rings[0], float)
    if len(rings) == 1 and _convex(outer):
        return [outer]
    key = b"".join(np.round(np.asarray(r, float), 9).tobytes() + b"|" for r in rings)
    hit = _PARTS.get(key)
    if hit is None:
        hit = _parts(rings)
        if len(_PARTS) > 4096:
            _PARTS.clear()
        _PARTS[key] = hit
    return [h.copy() for h in hit]


_PARTS: dict = {}                   # the parts of the polygons already split (openings repeat their shapes)


def _parts(rings: list) -> list:
    import shapely
    try:
        shape = shapely.Polygon(np.asarray(rings[0], float), [np.asarray(h, float) for h in rings[1:]])
        if not shape.is_valid:
            shape = shapely.make_valid(shape)
        tris = [t for t in shapely.get_parts(shapely.constrained_delaunay_triangles(shape)) if t.area > 0]
    except (shapely.errors.GEOSException, ValueError):
        return []
    if not tris:
        return []
    # the corners as numbers, each triangle counter-clockwise as a list of them
    index: dict = {}
    pts: list = []
    polys: list = []
    for t in tris:
        ring = []
        for xy in list(t.exterior.coords)[:3]:
            k = (round(xy[0], 9), round(xy[1], 9))
            if k not in index:
                index[k] = len(pts)
                pts.append(xy)
            ring.append(index[k])
        (x0, y0), (x1, y1), (x2, y2) = (pts[i] for i in ring)
        if (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0) < 0:
            ring.reverse()
        polys.append(ring)
    alive = [True] * len(polys)
    joined = True
    while joined:
        joined = False
        edges: dict = {}
        for i, ring in enumerate(polys):
            if alive[i]:
                for k in range(len(ring)):
                    edges[(ring[k], ring[(k + 1) % len(ring)])] = i
        for (u, v), i in edges.items():
            j = edges.get((v, u))
            if j is None or j == i or not (alive[i] and alive[j]):
                continue
            ri, rj = polys[i], polys[j]
            # ri goes u -> v, rj goes v -> u: the join is ri from v round to u, then rj from u round to v
            ki, kj = ri.index(v), rj.index(u)
            merged = [ri[(ki + m) % len(ri)] for m in range(len(ri))] \
                + [rj[(kj + m) % len(rj)] for m in range(1, len(rj) - 1)]
            if _convex(np.array([pts[q] for q in merged])):
                polys[i], alive[j], joined = merged, False, True
                break
    return [np.array([pts[q] for q in ring]) for i, ring in enumerate(polys) if alive[i]]


def prism(ring: np.ndarray, frame: np.ndarray, sweep: np.ndarray | None, extra: list | None = None) -> np.ndarray:
    """The piece of a convex 2D `ring` placed by the 4x4 `frame` (its xy plane) and swept by the vector `sweep` (in
    the frame's output): bounded by the two caps, or unbounded along the frame's z when `sweep` is None; with the
    `extra` planes added (a half space's own plane)."""
    ring = np.asarray(ring, float)
    p = np.c_[ring, np.zeros(len(ring))] @ frame[:3, :3].T + frame[:3, 3]
    along = frame[:3, 2] if sweep is None else np.asarray(sweep, float)
    centre = p.mean(axis=0) + (0.5 * along if sweep is not None else 0.0)
    e = np.roll(p, -1, axis=0) - p
    n = np.cross(e, along)
    size = np.linalg.norm(n, axis=1)
    ok = size > 1e-12 * np.maximum(1.0, np.linalg.norm(e, axis=1) * np.linalg.norm(along))
    n = n[ok] / size[ok, None]
    c = np.einsum("ij,ij->i", n, p[ok])
    flip = n @ centre - c > 0
    n[flip], c[flip] = -n[flip], -c[flip]
    rows = [np.c_[n, c]]
    if sweep is not None:
        z = frame[:3, 2] / np.linalg.norm(frame[:3, 2])
        if z @ along < 0:
            z = -z
        rows.append(np.array([np.r_[z, z @ (p[0] + along)], np.r_[-z, -z @ p[0]]]))
    if extra:
        rows.append(np.asarray(extra, float).reshape(-1, 4))
    return np.concatenate(rows)


def convex_hull_piece(tris: np.ndarray, tolerance: float) -> np.ndarray | None:
    """The piece of a closed convex solid given by its triangles; None when the solid is not convex (within
    `tolerance`) or has no volume."""
    if not len(tris):
        return None
    pts = tris.reshape(-1, 3)
    centre = pts.mean(axis=0)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    size = np.linalg.norm(n, axis=1)
    keep = size > 1e-12 * max(1.0, float(np.ptp(pts, axis=0).max()) ** 2)
    if not keep.any():
        return None
    n = n[keep] / size[keep, None]
    c = np.einsum("ij,ij->i", n, tris[keep, 0])
    flip = n @ centre - c > 0
    n[flip], c[flip] = -n[flip], -c[flip]
    rows = np.c_[n, c]
    # the same plane once (normals within a thousandth, offsets within the tolerance)
    key = np.c_[np.round(n * 1000), np.round(c / max(tolerance, 1e-12))]
    _u, first = np.unique(key, axis=0, return_index=True)
    rows = rows[np.sort(first)]
    d = pts @ rows[:, :3].T - rows[:, 3]
    if (d > tolerance).any():
        return None
    if (centre @ rows[:, :3].T - rows[:, 3] > -tolerance).any():
        return None
    return rows


def moved(piece: np.ndarray, m: np.ndarray) -> np.ndarray:
    """The piece in the frame where `m` (4x4) takes it."""
    n, c = piece[:, :3], piece[:, 3]
    point = n * c[:, None]
    inv_t = np.linalg.inv(m[:3, :3]).T
    nn = n @ inv_t.T
    nn /= np.linalg.norm(nn, axis=1)[:, None]
    pp = point @ m[:3, :3].T + m[:3, 3]
    return np.c_[nn, np.einsum("ij,ij->i", nn, pp)]


def subtract(tris: np.ndarray, pieces: list, eps: float, caps: bool = True,
             report: dict | None = None) -> tuple[np.ndarray, int]:
    """The triangles `(n, 3, 3)` of a closed solid less the convex `pieces`, and how many pieces changed it. `eps` is
    the distance under which a point is on a plane (the file's units). `report` counts what could not be made
    ("caps not made": a face of the cut GEOS could not build, left open)."""
    if not len(tris) or not pieces:
        return tris, 0
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    kept = tris
    used = []
    for piece in pieces:
        if not _reaches(tris, normals, piece, eps):
            continue
        out, inside = _cut_out(kept, piece, eps)
        if not _matters(inside, piece, eps):
            continue
        kept = out
        used.append(piece)
    if not used:
        return tris, 0
    out = kept
    if caps:
        lids = _caps(tris, used, eps, report if report is not None else {})
        out = np.concatenate([kept, lids]) if len(lids) else kept
    area2 = np.linalg.norm(np.cross(out[:, 1] - out[:, 0], out[:, 2] - out[:, 0]), axis=1)
    out = out[area2 > eps * eps * 1e-6]
    if caps:
        out = _seal(out, eps)
    return out, len(used)


def _seal(tris: np.ndarray, eps: float) -> np.ndarray:
    """The corners lying inside another triangle's edge put into that edge (a part kept whole beside one split again,
    a cap beside the faces it closes), so that the surface is closed edge to edge. Only the edges used once are
    looked at: in a closed surface those are the ones with such a corner."""
    from scipy.spatial import cKDTree
    for _round in range(12):
        pts = tris.reshape(-1, 3)
        _k, first, inv = np.unique(np.round(pts / eps).astype(np.int64), axis=0, return_index=True,
                                   return_inverse=True)
        verts = pts[first]
        f = inv.reshape(-1, 3)
        e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
        und = np.sort(e, axis=1)
        _u, where, count = np.unique(und, axis=0, return_inverse=True, return_counts=True)
        lone = np.flatnonzero(count[where.ravel()] == 1)        # edge rows (k * n + triangle) used once
        if not len(lone):
            break
        a, b = verts[e[lone, 0]], verts[e[lone, 1]]
        ab = b - a
        length = np.linalg.norm(ab, axis=1)
        tree = cKDTree(verts)
        near = tree.query_ball_point((a + b) / 2, length / 2 + eps)
        splits: dict = {}
        for r, cand in enumerate(near):
            if len(cand) < 3 or length[r] <= 2 * eps:
                continue
            c = np.array(cand)
            t = (verts[c] - a[r]) @ ab[r] / length[r] ** 2
            off = np.linalg.norm(a[r] + t[:, None] * ab[r] - verts[c], axis=1)
            inner = (off <= eps) & (t * length[r] > eps) & ((1 - t) * length[r] > eps)
            if inner.any():
                row = int(lone[r])
                tri, k = row % len(f), row // len(f)
                if tri not in splits:
                    splits[tri] = (k, verts[c[inner]][np.argsort(t[inner])])
        if not splits:
            break
        new = []
        for tri, (k, mid) in splits.items():
            corner = tris[tri]
            p, q, o = corner[k], corner[(k + 1) % 3], corner[(k + 2) % 3]
            chain = np.concatenate([p[None], mid, q[None]])
            new.append(np.stack([chain[:-1], chain[1:], np.broadcast_to(o, (len(chain) - 1, 3))], axis=1))
        keep = np.ones(len(tris), bool)
        keep[list(splits)] = False
        tris = np.concatenate([tris[keep]] + new)
    return tris


def _reaches(tris: np.ndarray, normals: np.ndarray, piece: np.ndarray, eps: float) -> bool:
    """Whether some triangle may enter the piece: on every plane a corner inside it by more than eps, or the
    triangle lying on the plane with the solid's material inside the piece. A quick test, without splitting: a
    triangle that fails it on one plane cannot reach the piece's inside (an opening already carved fails it)."""
    d = tris @ piece[:, :3].T - piece[:, 3]                       # (n, 3 corners, planes)
    ok = d.min(axis=1) < -eps
    ok |= (np.abs(d) <= eps).all(axis=1) & (normals @ piece[:, :3].T > 0)
    return bool(ok.all(axis=1).any())


def split(tris: np.ndarray, row: np.ndarray, eps: float) -> tuple[np.ndarray, np.ndarray]:
    """The parts of the triangles outside the plane (`n . x - c > eps`) and inside it, orientation kept."""
    d = _dist(tris, row)
    ins = d <= eps
    k = ins.sum(axis=1)
    all_in, all_out = k == 3, k == 0
    mixed = ~(all_in | all_out)
    if not mixed.any():
        return tris[all_out], tris[all_in]
    t, dd, ii = tris[mixed], d[mixed], ins[mixed]
    lone_in = ii.sum(axis=1) == 1               # the lone corner is the inside one
    a, b, c, lone_in = _rolled(t, dd, ii, lone_in, eps)
    pab, pac = a[1], a[2]
    a = a[0]
    lone = np.stack([a, pab, pac], axis=1)
    q1 = np.stack([pab, b, c], axis=1)
    q2 = np.stack([pab, c, pac], axis=1)
    out = np.concatenate([tris[all_out], lone[~lone_in], q1[lone_in], q2[lone_in]])
    inside = np.concatenate([tris[all_in], lone[lone_in], q1[~lone_in], q2[~lone_in]])
    return out, inside


def _dist(tris: np.ndarray, row: np.ndarray) -> np.ndarray:
    # written out, so that the same corner gives the same number in every triangle
    return tris[..., 0] * row[0] + tris[..., 1] * row[1] + tris[..., 2] * row[2] - row[3]


def _rolled(t, dd, ii, lone_in, eps):
    """The lone corner of each mixed triangle first, and the points where its two edges cross the plane, each
    computed from the edge's inside end (the same point for the two triangles of an edge)."""
    lone = np.where(lone_in, ii.argmax(axis=1), (~ii).argmax(axis=1))
    idx = (lone[:, None] + np.arange(3)) % 3
    t = np.take_along_axis(t, idx[:, :, None], axis=1)
    dd = np.take_along_axis(dd, idx, axis=1)
    dd = np.where(np.abs(dd) <= eps, 0.0, dd)
    a, b, c = t[:, 0], t[:, 1], t[:, 2]

    def cross(p, q, dp, dq):
        i = np.where(lone_in[:, None], p, q)
        o = np.where(lone_in[:, None], q, p)
        di = np.where(lone_in, dp, dq)
        do = np.where(lone_in, dq, dp)
        s = di / (di - do)
        return i + s[:, None] * (o - i)
    return (a, cross(a, b, dd[:, 0], dd[:, 1]), cross(a, c, dd[:, 0], dd[:, 2])), b, c, lone_in


def _cut_out(tris: np.ndarray, piece: np.ndarray, eps: float) -> tuple[np.ndarray, np.ndarray]:
    # a triangle wholly outside one of the planes is kept whole (most of a large wall around a window); the corners
    # this leaves inside a neighbour's edge are put into it afterwards (`_seal`)
    d = tris @ piece[:, :3].T - piece[:, 3]                    # (n, 3 corners, planes)
    away = (d > eps).all(axis=1).any(axis=1)
    kept = [tris[away]]
    rest = tris[~away]
    for row in piece:
        if not len(rest):
            break
        out, rest = split(rest, row, eps)
        kept.append(out)
    return (np.concatenate(kept) if kept else np.zeros((0, 3, 3))), rest


def _matters(inside: np.ndarray, piece: np.ndarray, eps: float) -> bool:
    """Whether the part of the solid inside a piece is more than faces lying on its planes with the solid's material
    beyond them (the faces an earlier carving made: the cut would take them and put them back)."""
    if not len(inside):
        return False
    normal = np.cross(inside[:, 1] - inside[:, 0], inside[:, 2] - inside[:, 0])
    real = np.linalg.norm(normal, axis=1) > eps * eps
    if not real.any():
        return False
    inside, normal = inside[real], normal[real]
    on_face = np.zeros(len(inside), bool)
    for row in piece:
        on_face |= (np.abs(_dist(inside, row)) <= eps).all(axis=1) & (normal @ row[:3] < 0)
    return not on_face.all()


def _frame(n: np.ndarray):
    x, y, z = float(n[0]), float(n[1]), float(n[2])
    k = int(np.abs(n).argmin())
    e1 = np.array([0.0, z, -y]) if k == 0 else (np.array([-z, 0.0, x]) if k == 1 else np.array([y, -x, 0.0]))
    e1 /= np.linalg.norm(e1)
    a, b, c = float(e1[0]), float(e1[1]), float(e1[2])
    return e1, np.array([y * c - z * b, z * a - x * c, x * b - y * a])


def _clip2d(poly: list, a: float, b: float, c: float) -> list:
    """A convex 2D polygon (a list of (u, v)) clipped to `a u + b v <= c` (plain floats: a handful of corners)."""
    out = []
    n = len(poly)
    for i in range(n):
        u0, v0 = poly[i]
        u1, v1 = poly[(i + 1) % n]
        s0, s1 = a * u0 + b * v0 - c, a * u1 + b * v1 - c
        if s0 <= 0:
            out.append((u0, v0))
        if (s0 <= 0) != (s1 <= 0):
            k = s0 / (s0 - s1)
            out.append((u0 + (u1 - u0) * k, v0 + (v1 - v0) * k))
    return out


def _face2d(rows: np.ndarray, o, e1, e2, half: float, lift: float = 0.0) -> list:
    """The polygon of the planes `rows` on the plane through `o` spanned by `e1`, `e2` (a square of side 2 `half`
    clipped by each), a list of (u, v), [] when empty. A plane parallel to it is tested `lift` beyond it (along
    e1 x e2): a face of the solid lying on the plane keeps the cap when the solid is beyond, not when it is behind."""
    poly = [(-half, -half), (half, -half), (half, half), (-half, half)]
    if not len(rows):
        return poly
    n = np.cross(e1, e2)
    ab = (rows[:, :3] @ np.c_[e1, e2]).tolist()
    cs = (rows[:, 3] - rows[:, :3] @ o).tolist()
    lifts = (lift * (rows[:, :3] @ n)).tolist()
    for (a, b), c, up in zip(ab, cs, lifts, strict=True):
        if abs(a) < 1e-12 and abs(b) < 1e-12:
            if c - up < 0:
                return []
            continue
        poly = _clip2d(poly, a, b, c)
        if len(poly) < 3:
            return []
    return poly


def _section(tris: np.ndarray, row: np.ndarray, eps: float, o, e1, e2, grid: float):
    """Where the solid's triangles cross the plane: its rings joined by GEOS, the even-odd inside (a shapely
    geometry), or None."""
    import shapely
    d = _dist(tris, row)
    ins = d <= eps
    k = ins.sum(axis=1)
    mixed = (k == 1) | (k == 2)
    if not mixed.any():
        return None
    (_a, p, q), _b, _c, _l = _rolled(tris[mixed], d[mixed], ins[mixed], k[mixed] == 1, eps)
    seg = np.stack([p - o, q - o], axis=1)
    uv = np.stack([seg @ e1, seg @ e2], axis=-1)
    uv = np.round(uv / grid) * grid
    uv = uv[(uv[:, 0] != uv[:, 1]).any(axis=1)]
    if not len(uv):
        return None
    lines = shapely.linestrings(uv.reshape(-1, 2), indices=np.repeat(np.arange(len(uv)), 2))
    faces = shapely.get_parts(shapely.polygonize(lines))
    faces = faces[shapely.area(faces) > 0] if len(faces) else faces
    if not len(faces):
        return None
    if len(faces) == 1:
        return faces[0]
    # inside where the rings around a point are odd (a section's hole is a face of its own here)
    filled = shapely.polygons(shapely.get_exterior_ring(faces))
    probe = shapely.point_on_surface(faces)
    depth = shapely.contains(filled[None, :], probe[:, None]).sum(axis=1)
    kept = faces[depth % 2 == 1]
    return shapely.union_all(kept) if len(kept) else None


def _caps(tris: np.ndarray, pieces: list, eps: float, report: dict) -> np.ndarray:
    import shapely
    pts = tris.reshape(-1, 3)
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    centre = (lo + hi) / 2
    half = 2.0 * float(np.linalg.norm(hi - lo)) + 1.0
    grid = eps / 64
    # a convex solid (a wall, a beam: almost all) is its planes: a face of a piece is clipped by them, no section
    hull = convex_hull_piece(tris, eps)
    out = []
    for i, piece in enumerate(pieces):
        for j, row in enumerate(piece):
            n = row[:3]
            d = pts @ n - row[3]
            if d.max() <= eps or d.min() > eps:
                continue
            o = centre - (centre @ n - row[3]) * n
            e1, e2 = _frame(n)
            rows = np.delete(piece, j, axis=0)
            if hull is not None:
                face = _face2d(np.concatenate([rows, hull]), o, e1, e2, half, 2 * eps)
                if len(face) < 3:
                    continue
                region = None
                u, v = np.array(face).T
                bounds = (u.min(), v.min(), u.max(), v.max())
            else:
                face = _face2d(rows, o, e1, e2, half)
                if len(face) < 3:
                    continue
                try:
                    section = _section(tris, row, eps, o, e1, e2, grid)
                    if section is None:
                        continue
                    region = shapely.intersection(shapely.make_valid(section), shapely.Polygon(face))
                except shapely.errors.GEOSException:
                    report["caps not made"] = report.get("caps not made", 0) + 1
                    continue
                if shapely.is_empty(region):
                    continue
                bounds = shapely.bounds(region)
            # the other pieces that can reach the region: none of their planes leaves its box wholly outside
            u0, v0, u1, v1 = bounds
            corners = o + np.outer([u0, u1, u1, u0], e1) + np.outer([v0, v0, v1, v1], e2) + eps * n
            beyond = []
            for k, other in enumerate(pieces):
                if k == i or ((corners @ other[:, :3].T - other[:, 3]) > eps).all(axis=0).any():
                    continue
                beyond_face = _face2d(other, o + eps * n, e1, e2, half)
                if len(beyond_face) >= 3:
                    beyond.append(shapely.Polygon(beyond_face))
                elif k < i:
                    # an earlier piece with a face on the same plane, turned the same way (two openings sharing
                    # their head, one written twice): the face they share is made once
                    same = np.flatnonzero((np.abs(other[:, :3] @ n - 1) < 1e-9) & (np.abs(other[:, 3] - row[3]) <= eps))
                    if len(same):
                        shared_face = _face2d(np.delete(other, same, axis=0), o, e1, e2, half)
                        if len(shared_face) >= 3:
                            beyond.append(shapely.Polygon(shared_face))
            if region is None:
                region = shapely.Polygon(face)
            if beyond:
                try:
                    region = shapely.difference(shapely.make_valid(region), shapely.union_all(beyond))
                except shapely.errors.GEOSException:
                    # GEOS could not take the shapes (a topology it cannot build): the cut stays open there
                    report["caps not made"] = report.get("caps not made", 0) + 1
                    continue
            if shapely.is_empty(region) or shapely.area(region) <= eps * eps:
                continue
            out.append(_triangles_on(region, o, e1, e2, eps))
    out = [t for t in out if len(t)]
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


def _triangles_on(region, o, e1, e2, eps: float) -> np.ndarray:
    """The triangles of a 2D region, back on its plane, looking against the plane's normal (into the cut)."""
    import shapely
    # the slivers a neighbouring piece leaves along a face they share (a few eps wide) are not faces
    polys = [g for g in shapely.get_parts(region) if g.geom_type == "Polygon" and g.area > 2 * eps * g.length]
    if not polys:
        return np.zeros((0, 3, 3))
    try:
        cdt = shapely.get_parts(shapely.constrained_delaunay_triangles(np.array(polys, dtype=object)))
    except shapely.errors.GEOSException:
        return np.zeros((0, 3, 3))
    if not len(cdt):
        return np.zeros((0, 3, 3))
    coords, which = shapely.get_coordinates(cdt, return_index=True)
    counts = np.bincount(which, minlength=len(cdt))
    starts = np.r_[0, np.cumsum(counts)[:-1]]
    ok = counts == 4
    c2 = coords[starts[ok][:, None] + np.arange(3)]                    # (m, 3, 2)
    area = ((c2[:, 1, 0] - c2[:, 0, 0]) * (c2[:, 2, 1] - c2[:, 0, 1])
            - (c2[:, 2, 0] - c2[:, 0, 0]) * (c2[:, 1, 1] - c2[:, 0, 1]))
    flip = area > 0                                                       # counter-clockwise looks along +n
    c2[flip] = c2[flip][:, ::-1]
    return o + c2[..., :1] * e1 + c2[..., 1:] * e2


def _convex(ring: np.ndarray) -> bool:
    if len(ring) < 3:
        return False
    e = np.roll(ring, -1, axis=0) - ring
    z = e[:, 0] * np.roll(e[:, 1], -1) - e[:, 1] * np.roll(e[:, 0], -1)
    scale = np.abs(z).max()
    return bool(scale > 0 and ((z >= -1e-9 * scale).all() or (z <= 1e-9 * scale).all()))
