"""Deterministic low-poly props in metres, with no Qt dependency.

Decorative meshes use Qt axes, x East, y up and z South, like mesh.py. Every solid is closed and flat shaded.
Shadow hulls are lists of corner arrays in model axes, x East, y North and z up, ready for nearshade.Solid.
Dimensions describe the unrotated local envelope; rotation is anticlockwise in the model's plan.
"""

from __future__ import annotations

import math

import numpy as np

from . import mesh

TREE_TRIANGLE_BUDGET = 400
PERSON_TRIANGLE_BUDGET = 300
CAR_TRIANGLE_BUDGET = 300
OBSTACLE_TRIANGLE_BUDGET = 200

TREE_KINDS = ("broadleaf", "conifer", "shrub", "hedge", "palm")
TREE_DEFAULTS = {
    "broadleaf": (6.0, 4.0, 1.8, 4.0),
    "conifer": (8.0, 3.5, 1.2, 3.5),
    "shrub": (1.2, 1.2, 0.12, 1.2),
    "hedge": (1.5, 0.8, 0.10, 4.0),
    "palm": (9.0, 5.0, 6.5, 5.0),
}

DEFAULT_COLOURS = {
    "tree": mesh.TREE,
    "trunk": (0.38, 0.25, 0.15),
}


def _colour(colours, key):
    value = (colours or {}).get(key, DEFAULT_COLOURS[key])
    return mesh.rgb(value) if isinstance(value, str) else tuple(float(c) for c in value)


def _positive(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return value


class _Builder:
    def __init__(self):
        self.pos = []
        self.nor = []
        self.col = []

    def tri(self, a, b, c, colour, towards=None):
        a, b, c = (np.asarray(p, dtype=np.float64) for p in (a, b, c))
        normal = np.cross(b - a, c - a)
        length = float(np.linalg.norm(normal))
        if length < 1e-14:
            return
        normal /= length
        if towards is not None and float(np.dot(normal, towards)) < 0:
            b, c = c, b
            normal = -normal
        for point in (a, b, c):
            self.pos.append(point)
            self.nor.append(normal)
            self.col.append(colour)

    def quad(self, a, b, c, d, colour, towards):
        self.tri(a, b, c, colour, towards)
        self.tri(a, c, d, colour, towards)

    def arrays(self):
        return (np.asarray(self.pos, dtype=np.float32), np.asarray(self.nor, dtype=np.float32),
                np.asarray(self.col, dtype=np.float32))


def _box(builder, centre, size, colour):
    cx, cy, cz = centre
    hx, hy, hz = (float(v) / 2 for v in size)
    x0, x1, y0, y1, z0, z1 = cx - hx, cx + hx, cy - hy, cy + hy, cz - hz, cz + hz
    faces = (
        (((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)), (-1, 0, 0)),
        (((x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)), (1, 0, 0)),
        (((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)), (0, 0, 1)),
        (((x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)), (0, 0, -1)),
        (((x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)), (0, 1, 0)),
        (((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)), (0, -1, 0)),
    )
    for points, outward in faces:
        builder.quad(*points, colour, outward)


def _lathe(builder, profile, segments, colour, x_scale=1.0, z_scale=1.0, centre=(0.0, 0.0, 0.0)):
    cx, cy, cz = centre
    angle = np.arange(segments) * (2 * math.pi / segments)
    rings = []
    for y, radius in profile:
        rings.append(np.stack((cx + x_scale * radius * np.cos(angle), np.full(segments, cy + y),
                               cz + z_scale * radius * np.sin(angle)), axis=1))
    for lower, upper in zip(rings, rings[1:], strict=False):
        for i in range(segments):
            j = (i + 1) % segments
            middle = (lower[i] + lower[j] + upper[i] + upper[j]) / 4
            outward = middle - (cx, middle[1], cz)
            if np.allclose(lower[i], upper[i]):
                builder.tri(lower[i], lower[j], upper[j], colour, outward)
            elif np.allclose(upper[i], lower[j]):
                builder.tri(lower[i], upper[i], upper[j], colour, outward)
            else:
                builder.quad(lower[i], lower[j], upper[j], upper[i], colour, outward)
    for ring, y, outward, reverse in ((rings[0], profile[0][0], (0, -1, 0), True),
                                      (rings[-1], profile[-1][0], (0, 1, 0), False)):
        if np.allclose(ring, ring[0]):
            continue
        centre_point = (cx, cy + y, cz)
        for i in range(segments):
            j = (i + 1) % segments
            a, b = (ring[j], ring[i]) if reverse else (ring[i], ring[j])
            builder.tri(centre_point, a, b, colour, outward)


def _ellipsoid(builder, y0, y1, radius, colour, segments=12, x_scale=1.0, z_scale=1.0):
    middle = (y0 + y1) / 2
    half = (y1 - y0) / 2
    profile = ((y0, 0.0), (middle - half * 0.5, radius * math.sqrt(0.75)), (middle, radius),
               (middle + half * 0.5, radius * math.sqrt(0.75)), (y1, 0.0))
    _lathe(builder, profile, segments, colour, x_scale, z_scale)


def _prism(builder, ring, y0, y1, colour):
    ring = [tuple(map(float, point)) for point in ring]
    cx = sum(point[0] for point in ring) / len(ring)
    cz = sum(point[1] for point in ring) / len(ring)
    for i, a in enumerate(ring):
        b = ring[(i + 1) % len(ring)]
        outward = ((a[0] + b[0]) / 2 - cx, 0.0, (a[1] + b[1]) / 2 - cz)
        builder.quad((a[0], y0, a[1]), (b[0], y0, b[1]), (b[0], y1, b[1]), (a[0], y1, a[1]),
                     colour, outward)
        builder.tri((cx, y1, cz), (a[0], y1, a[1]), (b[0], y1, b[1]), colour, (0, 1, 0))
        builder.tri((cx, y0, cz), (b[0], y0, b[1]), (a[0], y0, a[1]), colour, (0, -1, 0))


def _leaf(builder, start, end, width, thickness, colour):
    start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    direction = end - start
    direction /= np.linalg.norm(direction)
    helper = np.array((0.0, 1.0, 0.0)) if abs(direction[1]) < 0.9 else np.array((1.0, 0.0, 0.0))
    side = np.cross(direction, helper)
    side /= np.linalg.norm(side)
    normal = np.cross(direction, side)
    middle = (start + end) / 2
    equator = (middle + side * width, middle + normal * thickness,
               middle - side * width, middle - normal * thickness)
    for i in range(4):
        a, b = equator[i], equator[(i + 1) % 4]
        builder.tri(start, a, b, colour, (start + a + b) / 3 - middle)
        builder.tri(end, b, a, colour, (end + b + a) / 3 - middle)


def _rotate_qt(shape, degrees):
    if not degrees:
        return shape
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    matrix = np.array(((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c)))
    return tuple(np.asarray(array, dtype=np.float32) @ matrix.T for array in shape)


def _rotate_model(points, degrees):
    points = np.asarray(points, dtype=np.float64).reshape(-1, 3)
    if not degrees:
        return points
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    out = points.copy()
    out[:, 0] = c * points[:, 0] - s * points[:, 1]
    out[:, 1] = s * points[:, 0] + c * points[:, 1]
    return out


def _tree_dimensions(kind, height, crown_diameter, trunk_height, length):
    if kind not in TREE_KINDS:
        raise ValueError(f"unknown tree kind: {kind}")
    default_height, default_crown, default_trunk, default_length = TREE_DEFAULTS[kind]
    height = _positive(default_height if height is None else height, "height")
    crown = _positive(default_crown if crown_diameter is None else crown_diameter, "crown_diameter")
    trunk = float(default_trunk if trunk_height is None else trunk_height)
    length = _positive(default_length if length is None else length, "length")
    if not math.isfinite(trunk) or not 0 <= trunk < height:
        raise ValueError("trunk_height must be finite and between zero and height")
    return height, crown, trunk, length


def tree(kind="broadleaf", height=None, crown_diameter=None, trunk_height=None, length=None,
         rotation=0.0, colours=None):
    """A broadleaf, conifer, shrub, hedge or palm, standing at the local origin."""
    height, crown, trunk, length = _tree_dimensions(kind, height, crown_diameter, trunk_height, length)
    green, bark = _colour(colours, "tree"), _colour(colours, "trunk")
    builder = _Builder()
    radius = crown / 2
    crown_height = height - trunk
    trunk_radius = max(0.025, min(crown * 0.035, max(trunk, 0.1) * 0.04))
    _lathe(builder, ((0.0, trunk_radius), (max(trunk, 0.02), trunk_radius * 0.8)), 8, bark)

    if kind in ("broadleaf", "shrub"):
        _ellipsoid(builder, trunk, height, radius, green)
    elif kind == "conifer":
        for level, scale in enumerate((1.0, 0.8, 0.58)):
            base = trunk + crown_height * level * 0.24
            top = base + crown_height * 0.52
            _lathe(builder, ((base, radius * scale), (top, 0.0)), 12, green)
    elif kind == "hedge":
        chamfer = min(crown * 0.18, length * 0.08)
        x, z = length / 2, crown / 2
        ring = ((-x + chamfer, -z), (x - chamfer, -z), (x, -z + chamfer), (x, z - chamfer),
                (x - chamfer, z), (-x + chamfer, z), (-x, z - chamfer), (-x, -z + chamfer))
        _prism(builder, ring, trunk, height, green)
    else:
        for index in range(8):
            angle = index * math.tau / 8
            radial = np.array((math.cos(angle), 0.0, math.sin(angle)))
            start = radial * radius * 0.05 + (0.0, trunk + crown_height * 0.65, 0.0)
            end = radial * radius + (0.0, trunk + crown_height * (0.18 + 0.08 * (index % 2)), 0.0)
            _leaf(builder, start, end, radius * 0.18, max(0.015, crown_height * 0.025), green)
        for index in range(3):
            angle = index * math.tau / 3
            end = (math.cos(angle) * radius * 0.18, height, math.sin(angle) * radius * 0.18)
            _leaf(builder, (0.0, trunk + crown_height * 0.45, 0.0), end,
                  radius * 0.12, max(0.015, crown_height * 0.02), green)
    return _rotate_qt(builder.arrays(), float(rotation))


def _shadow_crown(height, crown, trunk, rounded):
    radius = crown / 2
    angle = np.arange(8) * math.tau / 8
    ring = np.stack((radius * np.cos(angle), radius * np.sin(angle),
                     np.full(8, trunk + (height - trunk) * (0.5 if rounded else 0.0))), axis=1)
    points = [ring, np.array(((0.0, 0.0, height),))]
    if rounded:
        points.append(np.array(((0.0, 0.0, trunk),)))
    return np.concatenate(points)


def _shadow_box(width, depth, z0, z1):
    return np.array([(x, y, z) for z in (z0, z1) for x, y in
                     ((-width / 2, -depth / 2), (width / 2, -depth / 2),
                      (width / 2, depth / 2), (-width / 2, depth / 2))])


def _tree_shadow(kind, height, crown, trunk, length):
    if kind == "hedge":
        crown_corners = _shadow_box(length, crown, trunk, height)
    else:
        crown_corners = _shadow_crown(height, crown, trunk, kind in ("broadleaf", "shrub", "palm"))
    radius = max(0.025, min(crown * 0.035, max(trunk, 0.1) * 0.04))
    trunk_corners = _shadow_box(radius * 2, radius * 2, 0.0, max(trunk, 0.02))
    return [crown_corners, trunk_corners]


def shadow_solid(kind, rotation=0.0, **dimensions):
    """Simplified convex shadow hulls, in model coordinates, contained in the decorative envelope."""
    if kind in TREE_KINDS:
        values = _tree_dimensions(kind, dimensions.get("height"), dimensions.get("crown_diameter"),
                                  dimensions.get("trunk_height"), dimensions.get("length"))
        return [_rotate_model(corners, rotation) for corners in _tree_shadow(kind, *values)]
    raise ValueError(f"unknown prop kind: {kind}")
