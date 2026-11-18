"""What a click in the 3D view hit (R488): the triangle of the scene the picked point lies on, and whose it is.

The 3D view draws the buildings, their obstacles, the props and the supports as one model; the view gives back the
point the ray met, not the face. Projecting that point on the plan and asking the plan what lies there takes the
sub-field for a wall under its edge (a sub-field as wide as its pitch shares the outline with the walls): here the
point finds its triangle again, so a wall says "building" and only the roof under a sub-field says "sub-field".
No Qt: numpy on the triangles mesh.project_scene made, with its `owners`.
"""

from __future__ import annotations

import numpy as np

# how far the point may lie from its triangle: the view's float32 positions and a rounding of the pick
TOLERANCE = 0.02
# a face whose normal leans less than this from the horizontal is a wall (cos 78 degrees): a roof is never this steep
WALL_NORMAL = 0.2


class Hits:
    """The triangles of a scene, ready to say which one a point lies on. Built once per scene, on the first ask."""

    def __init__(self, positions, owners):
        tri = np.asarray(positions, dtype=np.float64).reshape(-1, 3, 3)
        self.a = tri[:, 0]
        self.u = tri[:, 1] - tri[:, 0]
        self.v = tri[:, 2] - tri[:, 0]
        normal = np.cross(self.u, self.v)
        length = np.linalg.norm(normal, axis=1)
        keep = length > 1e-12
        self.a, self.u, self.v = self.a[keep], self.u[keep], self.v[keep]
        self.normal = normal[keep] / length[keep, None]
        self.uu = np.einsum('ij,ij->i', self.u, self.u)
        self.uv = np.einsum('ij,ij->i', self.u, self.v)
        self.vv = np.einsum('ij,ij->i', self.v, self.v)
        self.det = self.uu * self.vv - self.uv * self.uv
        self.size = np.sqrt(np.maximum(self.uu, self.vv))
        index = np.repeat(np.arange(len(owners)), [n for _part, _id, n in owners]) if owners else np.zeros(0, int)
        if len(index) != len(tri):
            raise ValueError('the owners do not count the triangles of the scene')
        self.owner = index[keep]
        self.owners = [(part, oid) for part, oid, _n in owners]

    def at(self, point, tolerance: float = TOLERANCE):
        """(part, id, wall) of the triangle `point` (Qt axes) lies on, the nearest when more are within
        `tolerance`; None when it lies on none (a point the view did not give, or another model's)."""
        if not len(self.a):
            return None
        w = np.asarray(point, dtype=np.float64) - self.a
        distance = np.einsum('ij,ij->i', w, self.normal)
        near = np.abs(distance) <= tolerance
        if not near.any():
            return None
        idx = np.nonzero(near)[0]
        flat = w[idx] - distance[idx, None] * self.normal[idx]
        wu = np.einsum('ij,ij->i', flat, self.u[idx])
        wv = np.einsum('ij,ij->i', flat, self.v[idx])
        det = self.det[idx]
        s = (self.vv[idx] * wu - self.uv[idx] * wv) / det
        t = (self.uu[idx] * wv - self.uv[idx] * wu) / det
        # the barycentric margin in metres: the tolerance over the triangle's size
        margin = tolerance / np.maximum(self.size[idx], tolerance)
        inside = (s >= -margin) & (t >= -margin) & (s + t <= 1 + margin)
        if not inside.any():
            return None
        candidates = idx[inside]
        best = candidates[np.argmin(np.abs(distance[candidates]))]
        part, oid = self.owners[self.owner[best]]
        return part, oid, bool(abs(self.normal[best, 1]) < WALL_NORMAL)
