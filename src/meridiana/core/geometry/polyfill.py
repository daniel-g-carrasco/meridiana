"""Planar polygons, concave or with holes, made triangles many at once (R575 D5): the faces of an IFC model.

A fan from the first vertex is right only for a convex outline without holes: on an L, a courtyard or a window frame
it draws triangles outside the face and fills the holes. Here the convex outlines without holes keep the fan (they are
almost all the faces of a model, and the fan costs nothing), the others go through GEOS's constrained Delaunay
triangulation (shapely 2.1+, `constrained_delaunay_triangles`, which keeps the polygon's own vertices and respects its
holes), all in one call. A polygon GEOS cannot take (an outline that crosses itself) keeps its fan, as before.

The rings are given as indices into an array of points in space; each polygon is brought into its plane by dropping
the axis its normal is closest to (no rotation: the coordinates stay the file's), so the triangles found are mapped
back to the points' indices exactly. Without Qt."""

from __future__ import annotations

import numpy as np

CONCAVE_TOLERANCE = 1e-7          # a corner turning the other way by less than this share of its edges is straight
_KEEP = np.array([[1, 2], [0, 2], [0, 1]])


def _rings(flat: np.ndarray, ring_off: np.ndarray):
    n = np.diff(ring_off)
    rid = np.repeat(np.arange(len(n)), n)
    pos = np.arange(len(flat))
    nxt = pos + 1
    ends = ring_off[1:] - 1
    nxt[ends[n > 0]] = ring_off[:-1][n > 0]
    return n, rid, nxt


def normals(xyz: np.ndarray, flat: np.ndarray, ring_off: np.ndarray) -> np.ndarray:
    """The Newell normal of every ring (not of unit length; zero for a ring without area), (R, 3)."""
    n, rid, nxt = _rings(flat, ring_off)
    out = np.zeros((len(n), 3))
    if not len(flat):
        return out
    p = xyz[flat]
    p = p - p[ring_off[:-1][rid]]
    c = np.cross(p, p[nxt])
    for k in range(3):
        out[:, k] = np.bincount(rid, weights=c[:, k], minlength=len(n))
    return out


def concave(xyz: np.ndarray, flat: np.ndarray, ring_off: np.ndarray, normal: np.ndarray | None = None) -> np.ndarray:
    """Which rings have a corner that turns against their normal (a fan from the first vertex would be wrong), (R,)."""
    n, rid, nxt = _rings(flat, ring_off)
    if not len(flat):
        return np.zeros(len(n), bool)
    normal = normals(xyz, flat, ring_off) if normal is None else normal
    p = xyz[flat]
    e = p[nxt] - p
    e2 = e[nxt]
    s = np.einsum("ij,ij->i", np.cross(e, e2), normal[rid])
    scale = np.linalg.norm(e, axis=1) * np.linalg.norm(e2, axis=1) * np.linalg.norm(normal[rid], axis=1)
    bad = s < -CONCAVE_TOLERANCE * scale
    return np.bincount(rid, weights=bad, minlength=len(n)) > 0


def fan(flat: np.ndarray, ring_off: np.ndarray, rings: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The fan from the first vertex of the given rings: triangles as indices of `flat`'s values, and their ring."""
    rings = np.asarray(rings, np.int64)
    start, n = ring_off[rings], np.diff(ring_off)[rings]
    m = np.maximum(n - 2, 0)
    total = int(m.sum())
    j = np.arange(total) - np.repeat(np.cumsum(m) - m, m)
    first = np.repeat(start, m)
    tris = np.stack([flat[first], flat[first + 1 + j], flat[first + 2 + j]], axis=1) if total else np.zeros((0, 3),
                                                                                                         np.int64)
    return tris, np.repeat(rings, m)


def fill(xyz: np.ndarray, flat: np.ndarray, ring_off: np.ndarray, poly_off: np.ndarray,
         check: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """The triangles of P planar polygons. Ring k is `flat[ring_off[k]:ring_off[k + 1]]` (indices into `xyz`, the
    first point not repeated at the end); polygon p is the rings `poly_off[p]:poly_off[p + 1]`, the first its outline
    and the others its holes. Gives the triangles as indices into `xyz`, turned as the outline, and the polygon of each
    (sorted by polygon). `check=False` when the caller knows every polygon needs the triangulation."""
    flat = np.asarray(flat, np.int64)
    ring_off = np.asarray(ring_off, np.int64)
    poly_off = np.asarray(poly_off, np.int64)
    rings_of = np.diff(poly_off)
    outer = poly_off[:-1]
    normal = normals(xyz, flat, ring_off)
    some = rings_of > 0
    hard = rings_of > 1
    if check:
        lone = np.flatnonzero(some & ~hard)
        if len(lone):
            sub_off = np.r_[0, np.cumsum(np.diff(ring_off)[outer[lone]])]
            sub_flat = _gather(flat, ring_off, outer[lone])
            hard[lone[concave(xyz, sub_flat, sub_off, normal[outer[lone]])]] = True
    else:
        hard[:] = some
    easy = np.flatnonzero(some & ~hard)
    tris_e, ring_e = fan(flat, ring_off, outer[easy])
    poly_e = easy[np.searchsorted(outer[easy], ring_e)] if len(ring_e) else np.zeros(0, np.int64)
    tris_h, poly_h, failed = _constrained(xyz, flat, ring_off, poly_off, np.flatnonzero(hard), normal)
    tris_f, ring_f = fan(flat, ring_off, outer[failed])
    poly_f = failed[np.searchsorted(outer[failed], ring_f)] if len(ring_f) else np.zeros(0, np.int64)
    tris = np.concatenate([tris_e, tris_h, tris_f])
    owner = np.concatenate([poly_e, poly_h, poly_f]).astype(np.int64)
    order = np.argsort(owner, kind="stable")
    return tris[order], owner[order]


def _gather(flat: np.ndarray, ring_off: np.ndarray, rings: np.ndarray) -> np.ndarray:
    n = np.diff(ring_off)[rings]
    start = ring_off[rings]
    idx = np.repeat(start - np.r_[0, np.cumsum(n)[:-1]], n) + np.arange(int(n.sum()))
    return flat[idx]


def _keys(poly: np.ndarray, uv: np.ndarray) -> np.ndarray:
    a = np.ascontiguousarray(np.c_[poly.astype(np.float64), uv + 0.0])
    return a.view(np.dtype((np.void, a.dtype.itemsize * 3))).ravel()


def _constrained(xyz, flat, ring_off, poly_off, polys, normal) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The polygons `polys` through GEOS: (triangles, their polygon, the polygons that failed)."""
    empty = np.zeros((0, 3), np.int64), np.zeros(0, np.int64)
    if not len(polys):
        return (*empty, np.zeros(0, np.int64))
    import shapely
    n_rings = np.diff(ring_off)
    rings = _gather(np.arange(len(ring_off) - 1), poly_off, polys)            # their rings, in order
    ring_poly = np.repeat(polys, np.diff(poly_off)[polys])
    outer = poly_off[:-1][polys]
    keep = n_rings[rings] >= 3
    keep &= np.isin(ring_poly, polys[n_rings[outer] >= 3])
    rings, ring_poly = rings[keep], ring_poly[keep]
    if not len(rings):
        return (*empty, polys)
    verts = _gather(flat, ring_off, rings)
    vert_ring = np.repeat(np.arange(len(rings)), n_rings[rings])
    vert_poly = ring_poly[vert_ring]
    # into the plane: drop the axis the outline's normal is closest to; around the outline's first point
    axis = np.abs(normal[poly_off[:-1][vert_poly]]).argmax(axis=1)
    origin = xyz[flat[ring_off[poly_off[:-1][vert_poly]]]]
    p = xyz[verts] - origin
    uv = np.take_along_axis(p, _KEEP[axis], axis=1)
    lr = shapely.linearrings(uv, indices=vert_ring)
    # the polygons in the order of `polys` that have rings left
    present, first = np.unique(ring_poly, return_index=True)
    poly_index = np.searchsorted(present, ring_poly)
    shapes = shapely.polygons(lr, indices=poly_index)
    ok = shapely.is_valid(shapes) & ~shapely.is_empty(shapes)
    failed = list(np.setdiff1d(polys, present))
    failed += list(present[~ok])
    good = np.flatnonzero(ok)
    if not len(good):
        return (*empty, np.array(sorted(failed), np.int64))
    try:
        cdt = shapely.constrained_delaunay_triangles(shapes[good])
    except shapely.errors.GEOSException:
        cdt = np.array([_one(s) for s in shapes[good]], dtype=object)
    tri_geoms, tri_of = shapely.get_parts(cdt, return_index=True)
    lost = np.setdiff1d(np.arange(len(good)), tri_of)
    failed += list(present[good[lost]])
    if not len(tri_geoms):
        return (*empty, np.array(sorted(failed), np.int64))
    coords, cidx = shapely.get_coordinates(tri_geoms, return_index=True)
    counts = np.bincount(cidx, minlength=len(tri_geoms))
    four = counts == 4
    starts = np.r_[0, np.cumsum(counts)[:-1]]
    corner = coords[starts[four][:, None] + np.arange(3)]                       # (m, 3, 2)
    tri_poly = present[good[tri_of[four]]]
    # back to the points: the same coordinates in the same polygon
    keys = _keys(vert_poly, uv)
    order = np.argsort(keys)
    sorted_keys = keys[order]
    want = _keys(np.repeat(tri_poly, 3), corner.reshape(-1, 2))
    at = np.clip(np.searchsorted(sorted_keys, want), 0, len(sorted_keys) - 1)
    hit = (sorted_keys[at] == want).reshape(-1, 3).all(axis=1)
    tri_idx = verts[order[at]].reshape(-1, 3)
    bad_polys = np.unique(tri_poly[~hit])
    if len(bad_polys):
        failed += list(bad_polys)
        drop = np.isin(tri_poly, bad_polys)
        tri_idx, corner, tri_poly = tri_idx[~drop], corner[~drop], tri_poly[~drop]
    # turned as the outline (in the same plane)
    out_area = _ring_area2d(uv, vert_ring, ring_poly)
    tri_area = ((corner[:, 1, 0] - corner[:, 0, 0]) * (corner[:, 2, 1] - corner[:, 0, 1])
                - (corner[:, 2, 0] - corner[:, 0, 0]) * (corner[:, 1, 1] - corner[:, 0, 1]))
    flip = np.sign(tri_area) != np.sign(out_area[np.searchsorted(present, tri_poly)])
    tri_idx[flip] = tri_idx[flip][:, ::-1]
    return tri_idx.astype(np.int64), tri_poly.astype(np.int64), np.array(sorted(set(int(x) for x in failed)),
                                                                          np.int64)


def _one(shape):
    import shapely
    try:
        return shapely.constrained_delaunay_triangles(shape)
    except shapely.errors.GEOSException:
        return shapely.GeometryCollection()


def _ring_area2d(uv, vert_ring, ring_poly) -> np.ndarray:
    """The signed area (twice) of each present polygon's outline in its plane (its first ring)."""
    first_ring = np.r_[True, ring_poly[1:] != ring_poly[:-1]]
    rings = np.flatnonzero(first_ring)
    sel = np.isin(vert_ring, rings)
    v = uv[sel]
    r = vert_ring[sel]
    nxt = np.arange(len(v)) + 1
    last = np.r_[r[1:] != r[:-1], True]
    starts = np.r_[0, np.flatnonzero(last)[:-1] + 1]
    nxt[last] = starts
    cross = v[:, 0] * v[nxt, 1] - v[nxt, 0] * v[:, 1]
    return np.bincount(np.searchsorted(rings, r), weights=cross, minlength=len(rings))
