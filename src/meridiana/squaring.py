# SPDX-License-Identifier: GPL-3.0-or-later AND ISC
# Ported from iD, the OpenStreetMap editor: modules/actions/orthogonalize.ts and modules/geo/ortho.ts at
# https://github.com/openstreetmap/iD/tree/1f6118db61b86dd3a77bc8b39bd370842777cc3e
# Copyright (c) iD Contributors. ISC License:
#   Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is
#   hereby granted, provided that the above copyright notice and this permission notice appear in all copies.
#   THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE
#   INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
#   ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE,
#   DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
#   CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""Squaring an outline traced by hand on an orthophoto (the "Q" of iD and JOSM): the corners within 13° of a
right angle become right angles, the vertices within 13° of a straight line go onto the side, the corners
far from both (a 45° chamfer) stay as they are.

The method is iD's, from Potlatch 2: the vertices near a straight angle are set aside; every other vertex
near a right angle moves a little along its bisector (0.1 of its cosine times twice its shorter side), all
together, a thousand times at most; the shape with the best score is kept (the score adds, for each vertex
near a right or straight angle, twice its cosine's distance from -1, 0 or 1); the vertices set aside are
then projected onto the nearest side of the result. Nothing is deleted: the outline keeps its vertices.
"""

from __future__ import annotations

import math

Point = tuple[float, float]
THRESHOLD = 13.0            # degrees from a right or a straight angle that are squared
EPSILON = 1e-4
MAX_STEPS = 1000


def _unit(v):
    n = math.hypot(v[0], v[1])
    return (v[0] / n, v[1] / n) if n > 0 else (0.0, 0.0)


def _normalized_dot(a, b, origin) -> float:
    p = _unit((a[0] - origin[0], a[1] - origin[1]))
    q = _unit((b[0] - origin[0], b[1] - origin[1]))
    return p[0] * q[0] + p[1] * q[1]


def _project(a, ring) -> Point:
    best, dmin = a, math.inf
    for o, b in zip(ring, ring[1:] + ring[:1], strict=True):
        s = (b[0] - o[0], b[1] - o[1])
        v = (a[0] - o[0], a[1] - o[1])
        den = s[0] * s[0] + s[1] * s[1]
        t = 0.0 if den == 0 else min(max((v[0] * s[0] + v[1] * s[1]) / den, 0.0), 1.0)
        p = (o[0] + t * s[0], o[1] + t * s[1])
        d = math.hypot(p[0] - a[0], p[1] - a[1])
        if d < dmin:
            best, dmin = p, d
    return best


def corner_angles(ring: list[Point]) -> list[float]:
    n = len(ring)
    return [math.degrees(math.acos(max(-1.0, min(1.0, _normalized_dot(ring[i - 1], ring[(i + 1) % n], ring[i])))))
            for i in range(n)]


def square(ring: list[Point], threshold: float = THRESHOLD) -> tuple[list[Point], str]:
    """The squared outline (closed, the first vertex not repeated) and "" when it changed; the same outline
    and the reason when there is nothing to do: "not_squarish" (no corner near 90° or 180°) or
    "square_enough"."""
    pts_in = [(float(x), float(y)) for x, y in ring]
    n = len(pts_in)
    if n < 3:
        return pts_in, "not_squarish"
    lower = math.cos(math.radians(90.0 - threshold))
    upper = math.cos(math.radians(threshold))
    keep, straight = [], []
    for i, p in enumerate(pts_in):
        d = abs(_normalized_dot(pts_in[i - 1], pts_in[(i + 1) % n], p))
        (straight if d > upper else keep).append(i)
    pts = [list(pts_in[i]) for i in keep]
    m = len(pts)
    if m < 3:
        return pts_in, "not_squarish"

    def score() -> float:
        total = 0.0
        squarish = False
        for i in range(m):
            d = _normalized_dot(pts[i - 1], pts[(i + 1) % m], pts[i])
            a = abs(d)
            if a < EPSILON:
                d = 0.0
            elif not (a < lower or a > upper):
                continue                            # a corner far from right or straight: not touched
            squarish = True
            total += 2.0 * min(abs(d - 1.0), abs(d), abs(d + 1.0))
        return total if squarish else math.nan

    first = score()
    if math.isnan(first):
        return pts_in, "not_squarish"
    if first < EPSILON and not straight:
        return pts_in, "square_enough"

    def motion(i):
        a, o, b = pts[i - 1], pts[i], pts[(i + 1) % m]
        p = (a[0] - o[0], a[1] - o[1])
        q = (b[0] - o[0], b[1] - o[1])
        scale = 2.0 * min(math.hypot(*p), math.hypot(*q))
        p, q = _unit(p), _unit(q)
        d = p[0] * q[0] + p[1] * q[1]
        if abs(d) < lower:
            v = _unit((p[0] + q[0], p[1] + q[1]))
            k = 0.1 * d * scale
            return (v[0] * k, v[1] * k)
        return (0.0, 0.0)

    best, best_score = [p[:] for p in pts], first
    for _step in range(MAX_STEPS):
        moves = [motion(i) for i in range(m)]
        for i, (dx, dy) in enumerate(moves):
            pts[i][0] += dx
            pts[i][1] += dy
        s = score()
        if s < best_score:
            best, best_score = [p[:] for p in pts], s
        if best_score < EPSILON:
            break
    out = list(pts_in)
    for k, i in enumerate(keep):
        out[i] = (best[k][0], best[k][1])
    ring_best = [tuple(p) for p in best]
    for i in straight:
        out[i] = _project(pts_in[i], ring_best)
    return out, ""
