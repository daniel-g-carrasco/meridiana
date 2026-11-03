"""Deterministic low-poly props in metres, with no Qt dependency.

Decorative meshes use Qt axes, x East, y up and z South, like mesh.py. Every solid is closed and flat shaded.
Shadow hulls are lists of corner arrays in model axes, x East, y North and z up, ready for nearshade.Solid.
Dimensions describe the unrotated local envelope; rotation is anticlockwise in the model's plan.
"""

from __future__ import annotations

import math

import numpy as np

from . import mesh

TREE_TRIANGLE_BUDGET = 700
PERSON_TRIANGLE_BUDGET = 600
CAR_TRIANGLE_BUDGET = 1600
OBSTACLE_TRIANGLE_BUDGET = 200

TREE_KINDS = ("broadleaf", "conifer", "pine", "shrub", "hedge", "palm")
TREE_DEFAULTS = {
    "broadleaf": (6.0, 4.0, 1.8, 4.0),
    "conifer": (8.0, 3.5, 1.2, 3.5),
    "pine": (14.0, 10.0, 9.5, 10.0),
    "shrub": (1.2, 1.2, 0.12, 1.2),
    "hedge": (1.5, 0.8, 0.10, 4.0),
    "palm": (9.0, 5.0, 6.5, 5.0),
}

DEFAULT_COLOURS = {
    "tree": mesh.TREE,
    "trunk": (0.38, 0.25, 0.15),
    "obstacle": mesh.OBSTACLE,
    "metal": (0.42, 0.46, 0.50),
    "glass": (0.35, 0.62, 0.72),
    "dark": (0.12, 0.16, 0.19),
    "person": (0.25, 0.43, 0.62),
    "skin": (0.76, 0.55, 0.40),
    "helmet": (0.95, 0.70, 0.12),
    "car": (0.38, 0.56, 0.68),
    "car_glass": (0.09, 0.15, 0.18),
    "tyre": (0.09, 0.10, 0.11),
    "light": (0.92, 0.88, 0.62),
    "rear": (0.65, 0.16, 0.12),
}

CAR_KINDS = ("compact", "suv")
CAR_DEFAULTS = {"compact": (4.10, 1.78, 1.48), "suv": (4.65, 1.90, 1.70)}

PERSON_KINDS = ("adult", "walking", "child", "worker")
PERSON_DEFAULTS = {
    "adult": (0.55, 0.32, 1.75),
    "walking": (0.58, 0.55, 1.75),
    "child": (0.42, 0.26, 1.20),
    "worker": (0.58, 0.34, 1.75),
}

OBSTACLE_KINDS = ("chimney", "vent", "skylight", "dome_skylight", "plant", "antenna", "dish", "tank",
                  "stairwell", "elevator", "walkway", "opening", "other")
OBSTACLE_DEFAULTS = {
    "chimney": (0.8, 0.6, 1.0),
    "vent": (0.3, 0.3, 0.5),
    "skylight": (1.2, 0.9, 0.25),
    "dome_skylight": (1.2, 0.9, 0.45),
    "plant": (1.4, 0.8, 0.9),
    "antenna": (1.2, 0.5, 2.2),
    "dish": (0.9, 0.7, 1.1),
    "tank": (1.0, 1.0, 1.6),
    "stairwell": (2.8, 2.2, 2.4),
    "elevator": (2.2, 2.0, 2.6),
    "walkway": (3.0, 0.8, 0.02),
    "opening": (1.0, 0.8, 0.10),
    "other": (1.0, 1.0, 0.5),
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


def _ellipsoid(builder, y0, y1, radius, colour, segments=12, x_scale=1.0, z_scale=1.0,
               centre=(0.0, 0.0, 0.0)):
    middle = (y0 + y1) / 2
    half = (y1 - y0) / 2
    profile = ((y0, 0.0), (middle - half * 0.5, radius * math.sqrt(0.75)), (middle, radius),
               (middle + half * 0.5, radius * math.sqrt(0.75)), (y1, 0.0))
    _lathe(builder, profile, segments, colour, x_scale, z_scale, centre)


def _organic_crown(builder, y0, y1, radius, colour, profile, segments=24):
    angle = np.arange(segments) * math.tau / segments
    variation = np.minimum(1.0, 1.0 + 0.10 * np.cos(3 * angle) + 0.06 * np.sin(5 * angle))
    variation[::segments // 4] = 1.0
    drop = (y1 - y0) * 0.07 * (0.5 - 0.5 * np.cos(3 * angle))
    rings = []
    for fraction, size in profile:
        r = radius * size * variation
        y = y0 + (y1 - y0) * fraction - drop * fraction ** 1.5
        rings.append(np.stack((r * np.cos(angle), y, r * np.sin(angle)), axis=1))
    for lower, upper in zip(rings, rings[1:], strict=False):
        for i in range(segments):
            j = (i + 1) % segments
            middle = (lower[i] + lower[j] + upper[i] + upper[j]) / 4
            outward = middle - (0.0, middle[1], 0.0)
            if np.allclose(lower[i], upper[i]):
                builder.tri(lower[i], lower[j], upper[j], colour, outward)
            elif np.allclose(upper[i], lower[j]):
                builder.tri(lower[i], upper[i], upper[j], colour, outward)
            else:
                builder.quad(lower[i], lower[j], upper[j], upper[i], colour, outward)
    for ring, y, outward, reverse in ((rings[0], y0, (0.0, -1.0, 0.0), True),
                                      (rings[-1], y1, (0.0, 1.0, 0.0), False)):
        size = profile[0][1] if reverse else profile[-1][1]
        if size > 0.0:
            for i in range(segments):
                j = (i + 1) % segments
                a, b = (ring[j], ring[i]) if reverse else (ring[i], ring[j])
                builder.tri((0.0, y, 0.0), a, b, colour, outward)


def _extrude_xy(builder, profile, z0, z1, colour):
    ring = [tuple(map(float, point)) for point in profile]
    if mesh.signed_area(ring) < 0:
        ring.reverse()
    for i0, i1, i2 in mesh.triangulate(ring):
        for z, outward in ((z0, (0.0, 0.0, -1.0)), (z1, (0.0, 0.0, 1.0))):
            builder.tri((ring[i0][0], ring[i0][1], z), (ring[i1][0], ring[i1][1], z),
                        (ring[i2][0], ring[i2][1], z), colour, outward)
    for a, b in zip(ring, ring[1:] + ring[:1], strict=True):
        outward = (b[1] - a[1], a[0] - b[0], 0.0)
        builder.quad((a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1),
                     colour, outward)


def _loft(builder, layers, colour):
    layers = [(float(y), [tuple(map(float, point)) for point in ring]) for y, ring in layers]
    for (y0, lower), (y1, upper) in zip(layers, layers[1:], strict=False):
        centre = np.mean(np.asarray(lower), axis=0)
        for a, b, c, d in zip(lower, lower[1:] + lower[:1], upper, upper[1:] + upper[:1], strict=True):
            outward = ((a[0] + b[0]) / 2 - centre[0], 0.0, (a[1] + b[1]) / 2 - centre[1])
            builder.quad((a[0], y0, a[1]), (b[0], y0, b[1]), (d[0], y1, d[1]), (c[0], y1, c[1]),
                         colour, outward)
    for y, ring, outward in ((layers[0][0], layers[0][1], (0.0, -1.0, 0.0)),
                             (layers[-1][0], layers[-1][1], (0.0, 1.0, 0.0))):
        for i0, i1, i2 in mesh.triangulate(ring):
            builder.tri((ring[i0][0], y, ring[i0][1]), (ring[i1][0], y, ring[i1][1]),
                        (ring[i2][0], y, ring[i2][1]), colour, outward)


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
    return tuple(np.asarray(array, dtype=np.float32) @ matrix.T for array in shape[:2]) + (shape[2],)


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
    if kind not in ("pine", "palm"):
        _lathe(builder, ((0.0, trunk_radius), (max(trunk, 0.02), trunk_radius * 0.8)), 8, bark)

    if kind in ("broadleaf", "shrub"):
        profile = ((0.0, 0.0), (0.25, 0.86), (0.5, 1.0), (0.75, 0.86), (1.0, 0.0))
        _organic_crown(builder, trunk, height, radius, green, profile)
    elif kind == "pine":
        fork = (radius * 0.08, trunk * 0.94, 0.0)
        _rod(builder, (0.0, 0.0, 0.0), (0.0, trunk * 0.55, 0.0), trunk_radius, bark, 10)
        _rod(builder, (0.0, trunk * 0.55, 0.0), fork, trunk_radius * 0.85, bark, 10)
        for x, z in ((-radius * 0.48, -radius * 0.12), (radius * 0.43, -radius * 0.32),
                     (radius * 0.10, radius * 0.45)):
            elbow = (x, trunk + crown_height * 0.03, z)
            _rod(builder, fork, elbow, trunk_radius * 0.62, bark, 6)
            _rod(builder, elbow, (x * 0.82, trunk + crown_height * 0.34, z * 0.82),
                 trunk_radius * 0.42, bark, 6)
        profile = ((0.12, 0.18), (0.24, 0.62), (0.42, 0.96), (0.60, 1.0),
                   (0.76, 0.94), (0.91, 0.60), (1.0, 0.32))
        _organic_crown(builder, trunk, height, radius, green, profile)
    elif kind == "conifer":
        profile = ((0.0, 0.55), (0.18, 0.92), (0.36, 1.0), (0.52, 0.78),
                   (0.68, 0.58), (0.84, 0.32), (1.0, 0.0))
        _organic_crown(builder, trunk, height, radius, green, profile)
    elif kind == "hedge":
        chamfer = min(crown * 0.18, length * 0.08)
        x, z = length / 2, crown / 2
        ring = ((-x + chamfer, -z), (x - chamfer, -z), (x, -z + chamfer), (x, z - chamfer),
                (x - chamfer, z), (-x + chamfer, z), (-x, z - chamfer), (-x, -z + chamfer))
        layers = []
        for y, scale in ((trunk, 0.92), (trunk + crown_height * 0.16, 1.0),
                         (height - crown_height * 0.18, 1.0), (height, 0.78)):
            layers.append((y, [(px * scale, pz * scale) for px, pz in ring]))
        _loft(builder, layers, green)
    else:
        base_y = max(0.05, trunk_radius * 1.5)
        _lathe(builder, ((0.0, trunk_radius), (base_y, trunk_radius)), 8, bark)
        stem_top = trunk + crown_height * 0.62
        stem = [np.array((radius * 0.08 * (step / 4) ** 2,
                          base_y + (stem_top - base_y) * step / 4, 0.0)) for step in range(5)]
        for a, b in zip(stem, stem[1:], strict=False):
            _rod(builder, a, b, trunk_radius * (1.0 - 0.25 * a[1] / stem[-1][1]), bark, 6)
        start = stem[-1]
        for index in range(8):
            angle = index * math.tau / 8
            radial = np.array((math.cos(angle), 0.0, math.sin(angle)))
            side = np.array((-math.sin(angle), 0.0, math.cos(angle)))
            middle = start + radial * radius * 0.48 + (0.0, crown_height * 0.25, 0.0)
            end = radial * radius + (0.0, trunk + crown_height * (0.20 + 0.06 * (index % 2)), 0.0)
            _leaf(builder, start, middle, radius * 0.09, max(0.015, crown_height * 0.02), green)
            _leaf(builder, middle, end, radius * 0.07, max(0.015, crown_height * 0.015), green)
            for fraction in (0.36, 0.56, 0.74):
                base = (1 - fraction) ** 2 * start + 2 * (1 - fraction) * fraction * middle + fraction ** 2 * end
                for sign in (-1.0, 1.0):
                    tip = base + side * sign * radius * (0.25 - fraction * 0.13) + radial * radius * 0.06
                    tip[1] -= crown_height * 0.06
                    _leaf(builder, base, tip, radius * 0.04, max(0.01, crown_height * 0.01), green)
        for index in range(3):
            angle = index * math.tau / 3
            end = (math.cos(angle) * radius * 0.18, height, math.sin(angle) * radius * 0.18)
            _leaf(builder, start, end, radius * 0.10, max(0.015, crown_height * 0.02), green)
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


def _rod(builder, start, end, radius, colour, segments=6):
    start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    direction = end - start
    direction /= np.linalg.norm(direction)
    helper = np.array((0.0, 1.0, 0.0)) if abs(direction[1]) < 0.9 else np.array((1.0, 0.0, 0.0))
    u = np.cross(direction, helper)
    u /= np.linalg.norm(u)
    v = np.cross(direction, u)
    angle = np.arange(segments) * math.tau / segments
    around = np.cos(angle)[:, None] * u + np.sin(angle)[:, None] * v
    rings = (start + around * radius, end + around * radius)
    for i in range(segments):
        j = (i + 1) % segments
        outward = around[i] + around[j]
        builder.quad(rings[0][i], rings[0][j], rings[1][j], rings[1][i], colour, outward)
        builder.tri(start, rings[0][j], rings[0][i], colour, -direction)
        builder.tri(end, rings[1][i], rings[1][j], colour, direction)


def _dish(builder, width, depth, height, colour):
    rx, ry, cy = width / 2, height * 0.3, height * 0.7
    angle = np.arange(12) * math.tau / 12
    rings = []
    for fraction, front_z in ((0.5, -0.2), (1.0, 0.1)):
        rings.append(np.stack((rx * fraction * np.cos(angle), cy + ry * fraction * np.sin(angle),
                               np.full(12, front_z * depth)), axis=1))
    front, back = rings, [ring - (0.0, 0.0, depth * 0.2) for ring in rings]
    front_centre, back_centre = (0.0, cy, -depth * 0.3), (0.0, cy, -depth * 0.5)
    for i in range(12):
        j = (i + 1) % 12
        builder.tri(front_centre, front[0][i], front[0][j], colour, (0, 0, 1))
        builder.quad(front[0][i], front[1][i], front[1][j], front[0][j], colour, (0, 0, 1))
        builder.tri(back_centre, back[0][j], back[0][i], colour, (0, 0, -1))
        builder.quad(back[0][j], back[1][j], back[1][i], back[0][i], colour, (0, 0, -1))
        outward = (front[1][i][0] + front[1][j][0], front[1][i][1] + front[1][j][1] - 2 * cy, 0.0)
        builder.quad(front[1][i], back[1][i], back[1][j], front[1][j], colour, outward)
    radius = min(width, depth) * 0.035
    _box(builder, (0.0, height * 0.02, 0.0), (radius * 2, height * 0.04, radius * 2), colour)
    _rod(builder, (0.0, height * 0.04, 0.0), (0.0, cy, -depth * 0.35), radius, colour)
    _rod(builder, front_centre, (0.0, cy, depth * 0.5), radius * 0.65, colour)


def _obstacle_dimensions(kind, width, depth, height):
    if kind not in OBSTACLE_KINDS:
        raise ValueError(f"unknown obstacle kind: {kind}")
    defaults = OBSTACLE_DEFAULTS[kind]
    return tuple(_positive(default if value is None else value, name)
                 for default, value, name in zip(defaults, (width, depth, height), ("width", "depth", "height"),
                                                 strict=True))


def obstacle(kind="other", width=None, depth=None, height=None, rotation=0.0, colours=None):
    """A roof or site obstacle with its requested local width, depth and total height."""
    width, depth, height = _obstacle_dimensions(kind, width, depth, height)
    body, metal = _colour(colours, "obstacle"), _colour(colours, "metal")
    glass, dark = _colour(colours, "glass"), _colour(colours, "dark")
    builder = _Builder()
    if kind == "chimney":
        _box(builder, (0.0, height * 0.42, 0.0), (width * 0.72, height * 0.84, depth * 0.72), body)
        _box(builder, (0.0, height * 0.92, 0.0), (width, height * 0.16, depth), metal)
    elif kind == "vent":
        _lathe(builder, ((0.0, 0.32), (height * 0.78, 0.32)), 8, metal, width, depth)
        _lathe(builder, ((height * 0.78, 0.5), (height, 0.5)), 8, body, width, depth)
    elif kind == "skylight":
        _box(builder, (0.0, height * 0.15, 0.0), (width, height * 0.3, depth), metal)
        _box(builder, (0.0, height * 0.65, 0.0), (width * 0.9, height * 0.7, depth * 0.9), glass)
    elif kind == "dome_skylight":
        _box(builder, (0.0, height * 0.1, 0.0), (width, height * 0.2, depth), metal)
        _lathe(builder, ((height * 0.2, 0.5), (height * 0.56, 0.43), (height, 0.0)), 12, glass, width, depth)
    elif kind == "plant":
        _box(builder, (0.0, height * 0.45, 0.0), (width, height * 0.9, depth), body)
        _lathe(builder, ((height * 0.9, 0.25), (height, 0.25)), 8, metal, width, depth)
        _box(builder, (0.0, height * 0.42, depth * 0.49), (width * 0.65, height * 0.42, depth * 0.02), dark)
    elif kind == "antenna":
        radius = min(width, depth) * 0.035
        _box(builder, (0.0, height * 0.03, 0.0), (width * 0.25, height * 0.06, depth), body)
        _rod(builder, (0.0, 0.0, 0.0), (0.0, height, 0.0), radius, metal)
        _rod(builder, (-width / 2, height * 0.82, 0.0), (width / 2, height * 0.82, 0.0), radius, metal)
        for level in (0.58, 0.70):
            _rod(builder, (0.0, height * level, -depth / 2), (0.0, height * level, depth / 2), radius, metal)
    elif kind == "dish":
        _dish(builder, width, depth, height, body)
    elif kind == "tank":
        _lathe(builder, ((0.0, 0.5), (height * 0.88, 0.5)), 12, body, width, depth)
        _lathe(builder, ((height * 0.88, 0.16), (height, 0.16)), 8, metal, width, depth)
    elif kind in ("stairwell", "elevator"):
        _box(builder, (0.0, height * 0.5, 0.0), (width, height, depth * 0.96), body)
        _box(builder, (0.0, height * 0.32, depth * 0.49), (width * 0.34, height * 0.64, depth * 0.02), dark)
        _box(builder, (0.0, height * 0.97, 0.0), (width, height * 0.06, depth), metal)
    elif kind == "walkway":
        radius = min(depth, height) * 0.06
        _box(builder, (0.0, height * 0.15, 0.0), (width, height * 0.3, depth), body)
        for z in (-depth / 2 + radius, depth / 2 - radius):
            _rod(builder, (-width / 2 + radius, height - radius, z),
                 (width / 2 - radius, height - radius, z), radius, metal)
            for x in (-width / 2 + radius, width / 2 - radius):
                _rod(builder, (x, 0.0, z), (x, height, z), radius, metal)
    else:
        _box(builder, (0.0, height / 2, 0.0), (width, height, depth), body)
    return _rotate_qt(builder.arrays(), float(rotation))


def _person_dimensions(kind, width, depth, height):
    if kind not in PERSON_KINDS:
        raise ValueError(f"unknown person kind: {kind}")
    default_width, default_depth, default_height = PERSON_DEFAULTS[kind]
    height = _positive(default_height if height is None else height, "height")
    width = _positive(default_width * height / default_height if width is None else width, "width")
    depth = _positive(default_depth * height / default_height if depth is None else depth, "depth")
    return width, depth, height


def person(kind="adult", width=None, depth=None, height=None, rotation=0.0, colours=None):
    """A standing adult, walking adult, child or helmeted worker, with anatomical reference proportions."""
    width, depth, height = _person_dimensions(kind, width, depth, height)
    cloth, skin = _colour(colours, "person"), _colour(colours, "skin")
    dark = _colour(colours, "dark")
    builder = _Builder()
    walking = kind == "walking"
    stride = 1.0 if walking else 0.0

    torso_radius = width * 0.29
    _lathe(builder, ((height * 0.43, width * 0.21), (height * 0.52, width * 0.25),
                     (height * 0.77, torso_radius), (height * 0.84, width * 0.20)), 10, cloth,
           z_scale=depth * 0.34 / torso_radius, centre=(0.0, 0.0, -depth * 0.125))
    _lathe(builder, ((height * 0.41, width * 0.20), (height * 0.49, width * 0.21)), 8, dark,
           z_scale=depth * 0.28 / (width * 0.21))
    for side in (-1.0, 1.0):
        hip_z = -side * depth * 0.12 * stride
        foot_z = side * depth * (0.25 if walking else 0.15)
        hip = (side * width * 0.15, height * 0.47, hip_z)
        knee = (side * width * 0.15, height * 0.27, (hip_z + foot_z) * 0.5)
        ankle = (side * width * 0.15, height * 0.08, foot_z)
        _rod(builder, hip, knee, width * 0.065, dark)
        _rod(builder, knee, ankle, width * 0.055, dark)
        _box(builder, (side * width * 0.15, height * 0.04, foot_z),
             (width * 0.14, height * 0.08, depth * (0.50 if walking else 0.70)), dark)
        hand_x = side * width * 0.435
        hand_z = -side * depth * 0.20 * stride
        shoulder = (side * width * 0.27, height * 0.77, -depth * 0.08)
        elbow = (side * width * 0.36, height * 0.59, hand_z * 0.55)
        _rod(builder, shoulder, elbow, width * 0.052, cloth)
        _rod(builder, elbow, (hand_x, height * 0.44, hand_z), width * 0.043, cloth)
        _ellipsoid(builder, height * 0.36, height * 0.44, width * 0.065, skin, segments=8,
                   z_scale=depth * 0.12 / (width * 0.065), centre=(hand_x, 0.0, hand_z))

    _rod(builder, (0.0, height * 0.78, 0.0), (0.0, height * 0.86, 0.0), width * 0.07, skin)
    head_radius = width * (0.18 if kind == "child" else 0.15)
    head_bottom = height * (0.80 if kind == "child" else (0.82 if kind == "worker" else 0.84))
    head_top = height * (0.96 if kind == "worker" else 1.0)
    _ellipsoid(builder, head_bottom, head_top, head_radius, skin, z_scale=depth * 0.32 / head_radius)
    if kind == "worker":
        helmet = _colour(colours, "helmet")
        helmet_radius = width * 0.19
        _lathe(builder, ((height * 0.925, width * 0.23), (height * 0.945, width * 0.23)), 10, helmet,
               z_scale=depth * 0.38 / (width * 0.23))
        _lathe(builder, ((height * 0.945, helmet_radius), (height * 0.975, helmet_radius * 0.82),
                         (height, 0.0)), 10, helmet, z_scale=depth * 0.34 / helmet_radius)
    return _rotate_qt(builder.arrays(), float(rotation))


def _car_dimensions(kind, length, width, height):
    if kind not in CAR_KINDS:
        raise ValueError(f"unknown car kind: {kind}")
    defaults = CAR_DEFAULTS[kind]
    return tuple(_positive(default if value is None else value, name)
                 for default, value, name in zip(defaults, (length, width, height), ("length", "width", "height"),
                                                 strict=True))


def _car_cabin(builder, kind, length, width, height, colour):
    suv = kind == "suv"
    y0 = height * (0.675 if suv else 0.585)
    roof_y = height * 0.96
    rear_bottom, front_bottom = (-0.40, 0.24) if suv else (-0.30, 0.23)
    rear_top, front_top = (-0.34, 0.11) if suv else (-0.11, 0.09)
    bottom_width, top_width = width * 0.41, width * (0.35 if suv else 0.33)
    bottom = np.array(((length * rear_bottom, y0, -bottom_width), (length * front_bottom, y0, -bottom_width),
                       (length * front_bottom, y0, bottom_width), (length * rear_bottom, y0, bottom_width)))
    top = np.array(((length * rear_top, roof_y, -top_width), (length * front_top, roof_y, -top_width),
                    (length * front_top, roof_y, top_width), (length * rear_top, roof_y, top_width)))
    centre = (bottom.mean(axis=0) + top.mean(axis=0)) / 2
    for i in range(4):
        j = (i + 1) % 4
        outward = (bottom[i] + bottom[j] + top[i] + top[j]) / 4 - centre
        builder.quad(bottom[i], bottom[j], top[j], top[i], colour, outward)
    for ring, outward in ((bottom, (0.0, -1.0, 0.0)), (top, (0.0, 1.0, 0.0))):
        builder.tri(ring[0], ring[1], ring[2], colour, outward)
        builder.tri(ring[0], ring[2], ring[3], colour, outward)
    return bottom, top


def _car_body(builder, kind, length, width, height, colour):
    radius = height * 0.19
    arch = radius * 1.16
    profile = [(-length / 2, radius)]
    for centre in (-length * 0.31, length * 0.31):
        for step in range(9):
            angle = math.pi - step * math.pi / 8
            profile.append((centre + arch * math.cos(angle), radius + arch * math.sin(angle)))
    profile.append((length / 2, radius))
    if kind == "suv":
        profile.extend(((length / 2, height * 0.59), (length * 0.40, height * 0.64),
                        (length * 0.18, height * 0.69), (-length * 0.40, height * 0.69),
                        (-length * 0.48, height * 0.64), (-length / 2, height * 0.59)))
    else:
        profile.extend(((length / 2, height * 0.50), (length * 0.40, height * 0.55),
                        (length * 0.18, height * 0.60), (-length * 0.28, height * 0.60),
                        (-length * 0.44, height * 0.55), (-length / 2, height * 0.48)))
    _extrude_xy(builder, profile, -width * 0.43, width * 0.43, colour)


def car(kind="compact", length=None, width=None, height=None, rotation=0.0, colours=None):
    """A compact car or SUV, length along local East and wheels resting at height zero."""
    length, width, height = _car_dimensions(kind, length, width, height)
    paint, tyre = _colour(colours, "car"), _colour(colours, "tyre")
    glass = _colour(colours, "car_glass")
    builder = _Builder()
    dark, metal = _colour(colours, "dark"), _colour(colours, "metal")
    _car_body(builder, kind, length, width, height, paint)
    bottom, top = _car_cabin(builder, kind, length, width, height, glass)
    roof_length = float(top[:, 0].max() - top[:, 0].min()) + length * 0.04
    roof_width = float(top[:, 2].max() - top[:, 2].min()) + width * 0.02
    _box(builder, (float(top[:, 0].mean()), height * 0.98, 0.0),
         (roof_length, height * 0.04, roof_width), paint)
    for side in (0, 1):
        for index in (0, 1):
            _rod(builder, bottom[index + side * 2], top[index + side * 2], width * 0.014, paint, 6)
        middle_bottom = bottom[side * 2] * 0.45 + bottom[1 + side * 2] * 0.55
        middle_top = top[side * 2] * 0.45 + top[1 + side * 2] * 0.55
        _rod(builder, middle_bottom, middle_top, width * 0.012, paint, 6)
    radius = height * 0.19
    for x in (-length * 0.31, length * 0.31):
        for side in (-1.0, 1.0):
            _rod(builder, (x, radius, side * width * 0.36), (x, radius, side * width * 0.482),
                 radius, tyre, 24)
            _rod(builder, (x, radius, side * width * 0.484), (x, radius, side * width * 0.5),
                 radius * 0.60, metal, 16)
            _rod(builder, (x, radius, side * width * 0.486), (x, radius, side * width * 0.5),
                 radius * 0.17, dark, 10)
    light_y = height * (0.54 if kind == "suv" else 0.46)
    for side in (-1.0, 1.0):
        _box(builder, (length * 0.495, light_y, side * width * 0.27),
             (length * 0.01, height * 0.09, width * 0.20), _colour(colours, "light"))
        _box(builder, (-length * 0.495, light_y, side * width * 0.27),
             (length * 0.01, height * 0.09, width * 0.20), _colour(colours, "rear"))
        _box(builder, (length * 0.15, height * 0.63, side * width * 0.45),
             (length * 0.07, height * 0.06, width * 0.08), paint)
        _box(builder, (-length * 0.04, height * 0.53, side * width * 0.434),
             (length * 0.08, height * 0.025, width * 0.008), metal)
    _box(builder, (length * 0.495, height * 0.36, 0.0),
         (length * 0.01, height * 0.10, width * 0.34), dark)
    return _rotate_qt(builder.arrays(), float(rotation))


def shadow_solid(kind, rotation=0.0, **dimensions):
    """Simplified convex shadow hulls, in model coordinates, contained in the decorative envelope."""
    if kind in TREE_KINDS:
        values = _tree_dimensions(kind, dimensions.get("height"), dimensions.get("crown_diameter"),
                                  dimensions.get("trunk_height"), dimensions.get("length"))
        return [_rotate_model(corners, rotation) for corners in _tree_shadow(kind, *values)]
    if kind in OBSTACLE_KINDS:
        width, depth, height = _obstacle_dimensions(kind, dimensions.get("width"), dimensions.get("depth"),
                                                    dimensions.get("height"))
        return [_rotate_model(_shadow_box(width, depth, 0.0, height), rotation)]
    if kind in PERSON_KINDS:
        width, depth, height = _person_dimensions(kind, dimensions.get("width"), dimensions.get("depth"),
                                                  dimensions.get("height"))
        head_bottom = height * (0.80 if kind == "child" else 0.82)
        solids = (_shadow_box(width * 0.55, depth * 0.75, height * 0.43, height * 0.82),
                  _shadow_box(width * 0.36, depth * 0.64, head_bottom, height))
        return [_rotate_model(corners, rotation) for corners in solids]
    if kind in CAR_KINDS:
        length, width, height = _car_dimensions(kind, dimensions.get("length"), dimensions.get("width"),
                                                dimensions.get("height"))
        solids = (_shadow_box(length, width * 0.84, height * 0.18, height * 0.54),
                  _shadow_box(length * 0.55, width * 0.60, height * 0.52, height))
        return [_rotate_model(corners, rotation) for corners in solids]
    raise ValueError(f"unknown prop kind: {kind}")


# R269: the props as objects of a project (model.Prop), placed on the site. A prop keeps its kind, where it stands,
# its turn and up to three measures (None: the kind's default); these functions give its plan outline, its mesh in
# the 3D scene and its shadow solids at its place.

FAMILIES = {**{k: "tree" for k in TREE_KINDS}, **{k: "obstacle" for k in OBSTACLE_KINDS},
            **{k: "person" for k in PERSON_KINDS}, **{k: "car" for k in CAR_KINDS}}
KINDS = tuple(FAMILIES)
ROUND = ("broadleaf", "conifer", "pine", "shrub", "palm")      # a round crown: an octagon on the plan


def family(kind: str) -> str:
    """"tree", "obstacle", "person" or "car"; ValueError for a kind that is none of them."""
    if kind not in FAMILIES:
        raise ValueError(f"unknown prop kind: {kind}")
    return FAMILIES[kind]


def measures(kind: str, height=None, width=None, length=None) -> dict:
    """The keyword arguments of the kind's builder (and of shadow_solid), every one resolved: for a tree `width` is
    the crown's diameter and `length` a hedge's length, the trunk the kind's share of the height; for an obstacle
    `width` and `length` its sides (local East and North); for a car `length` along local East; a person keeps its
    proportions with its height."""
    group = family(kind)
    if group == "tree":
        h0, c0, t0, l0 = TREE_DEFAULTS[kind]
        h = h0 if height is None else _positive(height, "height")
        h, crown, trunk, long_ = _tree_dimensions(kind, h, width, t0 * h / h0, length)
        out = {"height": h, "crown_diameter": crown, "trunk_height": trunk}
        if kind == "hedge":
            out["length"] = long_
        return out
    if group == "obstacle":
        w, d, h = _obstacle_dimensions(kind, width, length, height)
        return {"width": w, "depth": d, "height": h}
    if group == "person":
        w, d, h = _person_dimensions(kind, width, None, height)
        return {"width": w, "depth": d, "height": h}
    long_, w, h = _car_dimensions(kind, length, width, height)
    return {"length": long_, "width": w, "height": h}


def plan_size(kind: str, height=None, width=None, length=None) -> tuple[float, float]:
    """The sides of the prop's outline on the plan before its turn: along local East, along local North."""
    m = measures(kind, height, width, length)
    group = family(kind)
    if group == "tree":
        return (m.get("length", m["crown_diameter"]), m["crown_diameter"])
    if group == "car":
        return m["length"], m["width"]
    return m["width"], m["depth"]


def footprint(kind: str, at, rotation: float = 0.0, height=None, width=None, length=None,
              path=None) -> list[tuple[float, float]]:
    """The outline the prop covers on the plan, including the mitred buffer of a linear path."""
    if path is not None:
        from shapely.geometry import LineString
        width = measures(kind, height, width, length)["crown_diameter" if kind == "hedge" else "width"]
        shape = LineString(path).buffer(width / 2, cap_style="flat", join_style="mitre")
        return [(round(float(x), 4), round(float(y), 4)) for x, y in list(shape.exterior.coords)[:-1]]
    a, b = plan_size(kind, height, width, length)
    if kind in ROUND:
        angle = np.arange(8) * math.tau / 8 + math.tau / 16
        local = np.stack((a / 2 * np.cos(angle), a / 2 * np.sin(angle), np.zeros(8)), axis=1)
    else:
        local = np.array(((-a / 2, -b / 2, 0.0), (a / 2, -b / 2, 0.0), (a / 2, b / 2, 0.0), (-a / 2, b / 2, 0.0)))
    turned = _rotate_model(local, float(rotation))
    x, y = float(at[0]), float(at[1])
    return [(round(float(p[0]) + x, 4), round(float(p[1]) + y, 4)) for p in turned]


def placed_mesh(kind: str, at, z0: float = 0.0, rotation: float = 0.0, height=None, width=None, length=None,
                colours=None, path=None, railing=False, surface=None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The prop's triangles where it stands (positions, normals, colours), in the 3D view's axes (mesh.to_qt)."""
    m = measures(kind, height, width, length)
    if path is not None and kind in ("hedge", "walkway"):
        ring = footprint(kind, at, height=height, width=width, length=length, path=path)
        if surface is not None:
            return mesh.path_triangles(ring, surface, m["height"], _colour(colours, "obstacle"), railing)
        colour = _colour(colours, "tree" if kind == "hedge" else "obstacle")
        return mesh.prism_triangles(ring, z0, z0 + m["height"], colour)
    builder = {"tree": tree, "obstacle": obstacle, "person": person, "car": car}[family(kind)]
    pos, nor, col = builder(kind, rotation=float(rotation), colours=colours, **m)
    pos = np.asarray(pos, dtype=np.float32) + np.asarray(mesh.to_qt(float(at[0]), float(at[1]), float(z0)),
                                                         dtype=np.float32)
    return pos, np.asarray(nor, dtype=np.float32), np.asarray(col, dtype=np.float32)


def placed_solids(kind: str, at, z0: float = 0.0, rotation: float = 0.0, height=None, width=None,
                  length=None, path=None) -> list[np.ndarray]:
    """The prop's shadow solids where it stands (model axes, nearshade.Solid's corners)."""
    m = measures(kind, height, width, length)
    if path is not None:
        from shapely.geometry import Polygon
        ring = footprint(kind, at, height=height, width=width, length=length, path=path)
        hull = Polygon(ring).convex_hull
        xy = list(hull.exterior.coords)[:-1]
        return [np.array([(x, y, z) for z in (z0, z0 + m["height"]) for x, y in xy])]
    m = measures(kind, height, width, length)
    shift = np.array((float(at[0]), float(at[1]), float(z0)))
    return [np.asarray(c, dtype=np.float64) + shift for c in shadow_solid(kind, float(rotation), **m)]
