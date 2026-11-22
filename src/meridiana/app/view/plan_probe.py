"""The plan's probe for the measuring tool (study 46, state of r34-righello section 2.3): from the point under the pointer
to a `Probe`, with the plan's snaps (vertices, midpoints, edges, intersections, the polar guides when they are on) and
the height of the surface under the point (a pitch, a flat roof, the ground). No Qt.

The references are the outlines the drawing tools snap to (buildings, pitches, sub-fields, exclusions); the edge the
pointer passes over is given with the heights of its ends, so that the tool's constraints (Down: perpendicular to it)
work in space.
"""

from __future__ import annotations

from meridiana.app.view.heights import Surfaces
from meridiana.app.view.measure_tool import Probe
from meridiana.core.geometry.snapping import Snapper

PLAN_SNAPS = frozenset({"vertex", "midpoint", "edge", "intersection"})
# what the Snapper found, as the tool's kinds: the first point to close a ring is a vertex, a point on a guide is free
KINDS = {"close": "vertex", "direction": "free"}


def reference_segments(project) -> list:
    """The outlines the plan snaps to, as segments in plan: the drawing tools' (DrawingMachine.set_project)."""
    segments = []
    if project is None:
        return segments
    rings = [b.footprint for b in project.buildings]
    rings += [p.ring for b in project.buildings for p in b.pitches()]
    rings += [s.ring for s in project.subfields] + [e.ring for e in project.exclusions]
    for ring in rings:
        pts = [(float(p[0]), float(p[1])) for p in ring]
        segments.extend(zip(pts, pts[1:] + pts[:1], strict=True))
    return segments


class PlanProbe:
    def __init__(self, project=None, tolerance_px: float = 10.0):
        self.snapper = Snapper(tolerance_px)
        self.surfaces = Surfaces()
        self.set_project(project)

    def set_project(self, project):
        self.set_references(reference_segments(project))
        self.surfaces = Surfaces(project)

    def set_references(self, segments, points=None):
        self.snapper.set_references(segments, points)

    def point3(self, x: float, y: float) -> tuple:
        return float(x), float(y), self.surfaces.height(x, y)

    def probe(self, point, scale: float, wanted, snaps_on: bool = True) -> Probe:
        """`point` (East, North) under the pointer, `scale` metres per pixel, `wanted` the tool's Wanted; `snaps_on`
        False when the plan's snaps are switched off: no object, the polar guides as the tool says."""
        cursor = (float(point[0]), float(point[1]))
        chain = [(float(p[0]), float(p[1])) for p in wanted.chain]
        kinds = frozenset(wanted.snaps) & PLAN_SNAPS if snaps_on else frozenset()
        if not chain:
            self.snapper.reset()            # a measurement made leaves no direction to the next one (R563)
        if kinds or wanted.polar:
            snap = self.snapper.snap(cursor, chain, scale, kinds=kinds, directions=bool(wanted.polar))
        else:
            snap = self.snapper.snap(cursor, chain, scale, free=True)
        x, y = snap.point
        z, normal = self.surfaces.at(x, y)
        edge = None
        if wanted.snaps:                     # Ctrl, or «none» from the menu: no reference edge either
            segment = self.snapper.nearest_segment(cursor, scale)
            if segment is not None:
                edge = tuple(self.point3(*end) for end in segment)
        return Probe((x, y, z), KINDS.get(snap.kind, snap.kind), edge=edge, normal=normal, exact=True,
                     guides=tuple(snap.guides))
