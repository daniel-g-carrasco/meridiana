"""The 3D view's probe for the measuring tool (study 46, state of r34-righello sections 2.3 and 2.6): from the pointer's
ray to a `Probe`, with the snaps on the project's geometry (the corners, the middles and the edges of the walls, the
roofs, the obstacles, the props, the supports: the triangles mesh.project_scene made). No Qt.

The view gives the ray in its own axes (Qt: east x, height y, north -z) and how many metres a pixel is at a distance
along it (`pixel`: a constant for an orthographic camera, a spread times the distance for a perspective one). The ray
meets the first triangle of the scene (hit3d.Hits.cast, float64: the point lies on the face, not on the view's
float32); the corners, middles and edges within the tolerance in pixels around the ray, and not hidden behind the face
met, win over the face. The edges are the sides of the faces, not the diagonals that split a face into triangles:
built once per scene, as Hits is. A point taken from the geometry (a corner, a middle, a point on an edge) is exact;
a free point on a face is not (the tool writes «≈»). The ray that meets no face goes to the ground (height 0), or to
nothing when the view shows an IFC model as context (its geometry is not the project's: it is not snapped to, and the
ground behind it would be a point through it).

The modules are not among the triangles (the view draws them as instances): a ray on a module meets the roof under it.
"""

from __future__ import annotations

import numpy as np

from meridiana.app.view.hit3d import Hits
from meridiana.app.view.measure_tool import Probe

TOLERANCE_PX = 10.0     # the reach of a snap, in pixels, as in the plan (plan_probe.PlanProbe)
WELD = 1e-4             # corners closer than this (metres) are one corner: the triangles are the view's float32
COPLANAR = 0.9998       # two faces whose normals are this close are one face: the side between them is a diagonal
SEEN = 1e-3             # a face met this close before a corner (metres) is its own: the corner is seen
CHECKED = 4             # the snaps nearest the ray tried for being seen, no more (one ray cast each)
SNAP_ORDER = ("vertex", "midpoint", "edge")


def from_qt(point) -> np.ndarray:
    """A point or a direction of the view (Qt axes) as (East, North, height)."""
    x, y, z = (float(v) for v in point)
    return np.array((x, -z, y))


def enu_triangles(positions_qt) -> np.ndarray:
    """The scene's triangle positions (Qt axes, three per triangle) as (n, 3, 3) in (East, North, height)."""
    a = np.asarray(positions_qt, dtype=np.float64).reshape(-1, 3)
    return np.column_stack((a[:, 0], -a[:, 2], a[:, 1])).reshape(-1, 3, 3)


def feature_edges(tri: np.ndarray) -> np.ndarray:
    """The sides of the faces of `tri` (n, 3, 3) as segments (m, 2, 3): a side two triangles of one plane share (a
    diagonal) is left out; a side of one triangle only, or between faces that meet at an angle, stays."""
    if not len(tri):
        return np.zeros((0, 2, 3))
    normal = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    length = np.linalg.norm(normal, axis=1)
    keep = length > 1e-12
    tri, normal = tri[keep], normal[keep] / length[keep, None]
    points = tri.reshape(-1, 3)
    keys = np.round(points / WELD).astype(np.int64)
    corners, inverse = np.unique(keys, axis=0, return_inverse=True)
    inverse = inverse.reshape(-1)
    first = np.zeros(len(corners), dtype=np.int64)
    first[inverse[::-1]] = np.arange(len(points))[::-1]           # each corner where it first comes
    where = points[first]
    ids = inverse.reshape(-1, 3)
    pairs = np.sort(np.stack((ids[:, [0, 1]], ids[:, [1, 2]], ids[:, [2, 0]]), axis=1).reshape(-1, 2), axis=1)
    face = np.repeat(np.arange(len(tri)), 3)
    sides, which, counts = np.unique(pairs, axis=0, return_inverse=True, return_counts=True)
    which = which.reshape(-1)
    order = np.argsort(which, kind="stable")
    starts = np.concatenate(([0], np.cumsum(counts)[:-1]))
    feature = counts != 2
    two = np.nonzero(counts == 2)[0]
    if len(two):
        near_face, far_face = face[order][starts[two]], face[order][starts[two] + 1]
        feature[two] = np.einsum("ij,ij->i", normal[near_face], normal[far_face]) < COPLANAR
    return where[_straightened(sides[feature], where)].reshape(-1, 2, 3)


def _straightened(pairs, where) -> np.ndarray:
    """The sides as pairs of corners, the ones split in a straight line at a corner only they share made one (a gable
    wall triangulated from a point of its foot): its middle is the side's, and that point is no corner."""
    seg = [[int(a), int(b)] for a, b in pairs]
    at: dict = {}
    for i, (a, b) in enumerate(seg):
        at.setdefault(a, set()).add(i)
        at.setdefault(b, set()).add(i)
    gone = set()
    for v, sides in at.items():
        if len(sides) != 2:
            continue
        i, j = sides
        a = seg[i][0] if seg[i][1] == v else seg[i][1]
        b = seg[j][0] if seg[j][1] == v else seg[j][1]
        ua, ub = where[a] - where[v], where[b] - where[v]
        la, lb = float(np.linalg.norm(ua)), float(np.linalg.norm(ub))
        if a == b or la < 1e-12 or lb < 1e-12 or float(ua @ ub) / (la * lb) > -COPLANAR:
            continue
        seg[i] = [a, b]
        gone.add(j)
        at[b].discard(j)
        at[b].add(i)
        sides.clear()
    return np.array([s for k, s in enumerate(seg) if k not in gone], dtype=np.int64).reshape(-1, 2)


class SceneProbe:
    """The project's scene ready for the measuring tool: its faces and their sides, built once per scene."""

    def __init__(self, positions_qt=(), tolerance_px: float = TOLERANCE_PX):
        self.tolerance_px = float(tolerance_px)
        tri = enu_triangles(positions_qt) if len(positions_qt) else np.zeros((0, 3, 3))
        self.hits = Hits(tri.reshape(-1, 3), [("scene", "", len(tri))]) if len(tri) else None
        self.edges = feature_edges(tri)
        ends = self.edges.reshape(-1, 3)
        self.corners = (ends[np.unique(np.round(ends / WELD).astype(np.int64), axis=0, return_index=True)[1]]
                        if len(ends) else np.zeros((0, 3)))
        self.middles = self.edges.mean(axis=1) if len(self.edges) else np.zeros((0, 3))

    def probe(self, origin, direction, pixel, wanted, ground: bool = True) -> Probe | None:
        """`origin`, `direction` the pointer's ray in the view's axes; `pixel` (fixed, spread): a pixel is fixed +
        spread * distance metres at that distance along the ray; `wanted` the tool's Wanted; `ground` False when
        the view shows an IFC model as context (a ray that meets no face of the project gives no probe)."""
        o, d = from_qt(origin), from_qt(direction)
        norm = float(np.linalg.norm(d))
        if not np.isfinite(o).all() or not norm > 1e-12:
            return None
        d = d / norm
        ray = (tuple(map(float, o)), tuple(map(float, d)))
        met = self.hits.cast(o, d) if self.hits is not None else None
        if met is not None:
            reach, index = met
            point, normal, kind = o + reach * d, tuple(map(float, self.hits.normal[index])), "face"
        elif ground and d[2] < -1e-9:
            reach = -o[2] / d[2]
            point, normal, kind = o + reach * d, (0.0, 0.0, 1.0), "free"
        else:
            reach, point, normal, kind = None, None, None, None
        fixed, spread = (float(v) for v in pixel)
        snaps = frozenset(wanted.snaps)
        found = self._snap(o, d, fixed, spread, snaps) if snaps else None
        if found is None and point is None:
            return None
        edge = self._edge(o, d, fixed, spread) if snaps else None
        if found is not None:
            kind, point, on = found
            edge = on if on is not None else edge
            return Probe(tuple(map(float, point)), kind, edge=edge, normal=normal, exact=True, ray=ray)
        return Probe(tuple(map(float, point)), kind, edge=edge, normal=normal, exact=False, ray=ray)

    # -- the search around the ray ------------------------------------------------------------------------------

    def _reach(self, t, fixed, spread):
        """The tolerance in metres at the distances `t` along the ray."""
        return self.tolerance_px * (fixed + spread * np.maximum(t, 0.0))

    def _visible(self, o, point) -> bool:
        """Nothing of the scene between the camera and `point` (the faces it lies on meet the sight at its end)."""
        if self.hits is None:
            return True
        sight = point - o
        far = float(np.linalg.norm(sight))
        if far < 1e-9:
            return True
        met = self.hits.cast(o, sight / far)
        return met is None or met[0] >= far - SEEN

    def _first_seen(self, o, points, t, off, ok):
        """The index of the point nearest the ray among `ok` that the camera sees (the first CHECKED tried), or None."""
        idx = np.nonzero(ok)[0]
        for i in idx[np.lexsort((t[idx], off[idx]))][:CHECKED]:
            if self._visible(o, points[i]):
                return int(i)
        return None

    def _near_points(self, points, o, d, fixed, spread):
        """The index of the point of `points` nearest the ray within the tolerance and seen, or None."""
        if not len(points):
            return None
        w = points - o
        t = w @ d
        off = np.linalg.norm(w - t[:, None] * d, axis=1)
        ok = (t > 0) & (off <= self._reach(t, fixed, spread))
        return self._first_seen(o, points, t, off, ok) if ok.any() else None

    def _near_edges(self, o, d, fixed, spread):
        """(index, point on the edge) of the edge nearest the ray within the tolerance and seen, or None."""
        if not len(self.edges):
            return None
        a = self.edges[:, 0]
        u = self.edges[:, 1] - a
        w0 = a - o
        uu = np.einsum("ij,ij->i", u, u)
        ud = u @ d
        uw = np.einsum("ij,ij->i", u, w0)
        dw = w0 @ d
        denom = uu - ud * ud
        s = np.divide(ud * dw - uw, denom, out=np.zeros_like(denom), where=denom > 1e-12)
        s = np.clip(s, 0.0, 1.0)
        on = a + s[:, None] * u
        t = (on - o) @ d
        off = np.linalg.norm(on - o - t[:, None] * d, axis=1)
        ok = (t > 0) & (off <= self._reach(t, fixed, spread))
        best = self._first_seen(o, on, t, off, ok) if ok.any() else None
        return None if best is None else (best, on[best])

    def _edge_ends(self, index):
        return tuple(tuple(map(float, end)) for end in self.edges[index])

    def _snap(self, o, d, fixed, spread, snaps):
        """(kind, point, edge or None) of the first snap the tool wants that lies near the ray, or None."""
        for kind in SNAP_ORDER:
            if kind not in snaps:
                continue
            if kind == "vertex":
                near = self._near_points(self.corners, o, d, fixed, spread)
                if near is not None:
                    return kind, self.corners[near], None
            elif kind == "midpoint":
                near = self._near_points(self.middles, o, d, fixed, spread)
                if near is not None:
                    return kind, self.middles[near], self._edge_ends(near)
            else:
                near = self._near_edges(o, d, fixed, spread)
                if near is not None:
                    return kind, near[1], self._edge_ends(near[0])
        return None

    def _edge(self, o, d, fixed, spread):
        """The edge the pointer passes over, the reference of the tool's Down (perpendicular, parallel)."""
        near = self._near_edges(o, d, fixed, spread)
        return self._edge_ends(near[0]) if near is not None else None
