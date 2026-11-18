"""Temporary point and edge collectors, independent of any view or project mutation."""
from __future__ import annotations

import math

from .plan_locale import _


def align_angle(ring, side):
    """The view's bearing that lays side `side` of `ring` (metres, y North) horizontal at the BOTTOM of the view,
    the inside of the outline above it (R477). The plan draws a point (x, y) at (x cos b + y sin b, x sin b - y cos
    b): with the bearing equal to the side's direction the side is horizontal, but the inside falls under it for a
    ring that turns clockwise, so that ring takes the opposite direction. Before, the direction alone was taken
    and the side came out at the top or at the bottom by the ring's turn and the side's sense."""
    a, b = ring[side], ring[(side + 1) % len(ring)]
    angle = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    area = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(ring, ring[1:] + ring[:1], strict=True))
    if area < 0:            # clockwise in metres: the inside is on the right of a -> b, under it once drawn
        angle += 180.
    return (angle + 180.) % 360. - 180.


# R505: how far from a side the pointer takes it, and within what two sides count as equally near, in screen
# pixels at any zoom
REACH_PX = 14
TIE_PX = 3


def _owned(kind, oid, preferred):
    """Whether the outline (kind, oid) is the selected object's: itself, a pitch of the selected building, the
    sub-field of the selected row."""
    pk, po = preferred
    if not pk:
        return False
    if pk == 'row':
        pk, po = 'subfield', po.partition('/')[0]
    return (kind, oid) == (pk, po) or (pk == 'building' and kind == 'pitch' and oid.partition(':')[0] == po)


def nearest_side(rings, point, mpp, preferred=('', '')):
    """(kind, oid, ring, side) of the side the pointer takes (R505), None when none is within REACH_PX: the nearest,
    a side of the selected object first; of two within TIE_PX of each other the longer, then the first by kind."""
    reach, tie = REACH_PX * mpp, TIE_PX * mpp
    px, py = map(float, point)
    found = []
    for rank, (kind, oid, ring) in enumerate(rings):
        pts = [tuple(map(float, q)) for q in ring]
        if len(pts) < 2:
            continue
        for i, (a, b) in enumerate(zip(pts, pts[1:] + pts[:1], strict=True)):
            dx, dy = b[0] - a[0], b[1] - a[1]
            n2 = dx * dx + dy * dy
            t = 0.0 if n2 < 1e-12 else max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / n2))
            d = math.hypot(px - a[0] - t * dx, py - a[1] - t * dy)
            if d <= reach and n2 >= 1e-12:
                found.append((d, math.sqrt(n2), rank, _owned(kind, oid, preferred), kind, oid, ring, i))
    if not found:
        return None
    pool = [f for f in found if f[3]] or found
    best = min(f[0] for f in pool)
    _d, _length, _rank, _mine, kind, oid, ring, side = max(
        (f for f in pool if f[0] <= best + tie), key=lambda f: (f[1], -f[2], -f[0]))
    return kind, oid, ring, side


class Collector:
    def __init__(self):
        self.cancel()

    def cancel(self):
        self.mode = self.purpose = ''
        self.rings, self.hints, self.picked = [], [], []
        self.hover = None
        self.preferred = ('', '')

    @property
    def active(self):
        return bool(self.mode)

    @property
    def hint(self):
        if self.mode == 'points':
            return self.hints[len(self.picked)]
        return _('Click: choose side · Esc: cancel') if self.mode else ''

    def edges(self, purpose, rings, preferred=('', '')):
        self.cancel()
        self.mode, self.purpose = 'edge', purpose
        order = {'exclusion': 0, 'subfield': 1, 'pitch': 2, 'building': 3}
        self.rings = sorted(rings, key=lambda r: order.get(r[0], 99))
        self.preferred = tuple(preferred)

    def points(self, purpose, hints):
        if not hints:
            raise ValueError('At least one point is required')
        self.cancel()
        self.mode, self.purpose, self.hints = 'points', purpose, list(hints)

    def move(self, point, mpp):
        self.hover = nearest_side(self.rings, point, mpp, self.preferred) if self.mode == 'edge' else None

    def click(self, point, mpp):
        self.move(point, mpp)
        if self.mode == 'edge' and self.hover:
            kind, oid, ring, side = self.hover
            result = dict(type='edge', purpose=self.purpose, kind=kind, oid=oid, side=side,
                          angle=align_angle(ring, side))
        elif self.mode == 'points':
            self.picked.append(list(map(float, point)))
            if len(self.picked) < len(self.hints):
                return None
            result = dict(type='points', purpose=self.purpose, points=self.picked)
        else:
            return None
        self.cancel()
        return result

    def key(self, key):
        if key == 'Escape':
            self.cancel()
        elif key == 'Backspace' and self.mode == 'points' and self.picked:
            self.picked.pop()
