"""What a sweep of the pointer selects on the plan, as AutoCAD's selection (R300; Daniel, 02/11/2026: «il classico quadrato
di autocad [...] se tieni premuto sul click sinistro fa una sorta di selezione informe»). No Qt: the plan collects the
gesture, this does the sums.

- A press and a drag: a rectangle. From left to right a window, what is all inside it; from right to left a crossing,
  what it touches too. Left and right are the screen's, whichever way the view is turned: the plan decides them.
- A press held still for HOLD_MS, then a drag: a lasso of free shape, with the same rule. Its way is the way its first
  stretch went, and stays: closing the loop the pointer comes back the other way. AutoCAD says clockwise for the
  window and anticlockwise for the crossing, which is the same thing for a loop started towards the right along its
  top, or towards the left along its bottom, and changes under the pointer while the loop is being drawn.

The shapes are given in whatever plane the caller uses, the same for all: the plan gives the scene's."""

from __future__ import annotations

import numpy as np
import shapely

WINDOW, CROSSING = "window", "crossing"
HOLD_MS = 350                   # a press still for this long, then a drag, is a lasso


def kind_of(start_x: float, x: float) -> str:
    """A window going right, a crossing going left (screen pixels)."""
    return WINDOW if x >= start_x else CROSSING


def _area(ring):
    """The surface of `ring`, also when a free shape crosses itself."""
    shape = shapely.Polygon(ring)
    if not shape.is_valid:
        shape = shapely.make_valid(shape)
    shapely.prepare(shape)
    return shape


class QuadIndex:
    """The quadrilaterals of a layout made ready once (R344): their shapes and their boxes. A sweep moves many times
    over the same modules; each move then tests only the modules whose box is near the sweep, not all of them, and the
    shapes are not made again. Same answer as `chosen_quads`: the box test only leaves out what cannot be chosen."""

    def __init__(self, quads):
        self.quads = quads
        q = np.asarray(quads, dtype=float).reshape(-1, 4, 2)
        self.low = q.min(axis=1) if len(q) else np.zeros((0, 2))
        self.high = q.max(axis=1) if len(q) else np.zeros((0, 2))
        self.shapes = shapely.polygons(shapely.linearrings(q)) if len(q) else np.empty(0, dtype=object)

    def chosen(self, ring, kind: str) -> np.ndarray:
        """Which of the quadrilaterals the sweep `ring` selects, as an array of bools."""
        out = np.zeros(len(self.shapes), dtype=bool)
        if len(ring) < 3 or not len(out):
            return out
        area = _area(ring)
        points = np.asarray(ring, dtype=float)
        low, high = points.min(axis=0), points.max(axis=0)
        if kind == WINDOW:
            near = np.all((self.low >= low) & (self.high <= high), axis=1)
        else:
            near = np.all((self.high >= low) & (self.low <= high), axis=1)
        at = np.flatnonzero(near)
        if len(at):
            shapes = self.shapes[at]
            out[at] = shapely.covers(area, shapes) if kind == WINDOW else shapely.intersects(area, shapes)
        return out


def chosen_quads(quads, ring, kind: str) -> np.ndarray:
    """Which of the quadrilaterals `quads` (n, 4, 2) the sweep `ring` selects, as an array of bools."""
    quads = np.asarray(quads, dtype=float)
    if len(ring) < 3 or not len(quads):
        return np.zeros(len(quads), dtype=bool)
    area = _area(ring)
    shapes = shapely.polygons(shapely.linearrings(quads))
    return shapely.covers(area, shapes) if kind == WINDOW else shapely.intersects(area, shapes)


def chosen_rings(rings: list, ring, kind: str) -> list[bool]:
    """Which of the outlines `rings` (each a list of points) the sweep `ring` selects."""
    if len(ring) < 3:
        return [False] * len(rings)
    area = _area(ring)
    out = []
    for other in rings:
        shape = shapely.Polygon(other) if len(other) >= 3 else None
        out.append(shape is not None and bool(area.covers(shape) if kind == WINDOW else area.intersects(shape)))
    return out
