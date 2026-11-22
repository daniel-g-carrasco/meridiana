"""The measuring tool (the ruler) without its views: the states and gestures, the constraints, what to draw (study 46,
state of r34-righello section 2).

The views give probes (`Probe`): the point under the pointer as (East, North, height) with what it snapped to. The
tool does not know which view a probe comes from, only whether it carries the pointer's ray (the 3D view does): a
measurement begun in the plan can end in the 3D view. `display(view)` is everything the view draws, in plain dicts,
lists, numbers, strings and bools; `wanted()` is what the view's probe looks for.

Gestures (Daniel's choice 1: always a path): a click adds a point, Enter or a double click ends the measurement, a
click on the first point (from three) closes the ring; Backspace takes the last point back, Esc the measurement in
hand and then the tool. The arrows are the tool's only while a point is placed. No Qt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from meridiana.app.platform import log
from meridiana.app.view import measure_text as words
from meridiana.app.view.measure_display import about, build, done as made
from meridiana.core.geometry import measure as geo
from meridiana.core.geometry.measure import Point3

MODES = ("distance", "height")
SNAPS = frozenset({"vertex", "midpoint", "edge", "intersection"})       # «all»: what the views look for by default
MENU = frozenset(SNAPS | {"perpendicular", "none"})
SNAPPED = frozenset({"vertex", "midpoint", "edge", "intersection", "perpendicular"})
ARROWS = {"Right": "east", "Left": "north", "Up": "up"}
DOWN = (None, "perpendicular", "parallel")
DIGITS = set("0123456789,.-")
# a click this close to a placed point is the same point (the 3D view's hit is float32, 2 cm: app/view/hit3d)
SAME_EXACT, SAME_APPROX = 0.005, 0.02
INCLINED = (0.2, 0.9999)        # |normal height| of a pitch: steeper is a wall, flatter is a flat roof

# what key() answers: the key was not the tool's (the view may use it), it was, or the tool is to be left
IGNORED, USED, LEAVE = "", "used", "leave"


@dataclass(frozen=True)
class Probe:
    """The point under the pointer, as a view found it (state, section 2.3)."""
    point: Point3
    kind: str = "free"                   # vertex, midpoint, edge, intersection, perpendicular, face, free
    edge: tuple[Point3, Point3] | None = None
    normal: Point3 | None = None         # of the face under the point
    exact: bool = True                   # False when the coordinates are the 3D view's hit (float32)
    ray: tuple[Point3, Point3] | None = None     # the pointer's ray (origin, direction), only in the 3D view
    guides: tuple = ()                   # the view's guides (the plan's polar ones): snapping.Guide or dicts
    # the height mode's top, on the foot's vertical, keeps the point it took its height from (the vertex snapped, the
    # surface under the pointer): the dotted line of the reference, never the measure
    source: Point3 | None = None


@dataclass(frozen=True)
class Wanted:
    """What the view's probe should look for: the snaps allowed (empty: none), the polar guides, the points of the
    measurement in hand (the plan's guides start from the last one)."""
    snaps: frozenset
    polar: bool
    chain: tuple


@dataclass
class Measure:
    id: int
    mode: str
    points: tuple                        # of Probe
    closed: bool = False

    def spans(self) -> list:
        pts = [p.point for p in self.points]
        pairs = list(zip(pts, pts[1:], strict=False)) + ([(pts[-1], pts[0])] if self.closed else [])
        return [geo.span(a, b) for a, b in pairs]


def _minus(a, b) -> Point3:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


class MeasureTool:
    def __init__(self):
        self.mode = "distance"
        # the 15° guides follow the plan's Ortho (its bar's button, F8): one setting for drawing and measuring, set
        # by whoever holds it (gui/backend/plan.py); on until told otherwise
        self.polar = True
        self.measures: list[Measure] = []
        self.selected: set[int] = set()
        self._next_id = 1
        self._clear()

    def _clear(self):
        """The measurement in hand forgotten: points, pointer, typed number, constraints, snap asked."""
        self.points: list[Probe] = []
        self.probe: Probe | None = None
        self.target: Probe | None = None
        self.typed = ""
        self.constraint: str | None = None
        self.held: Point3 | None = None
        self.edge = None                 # the edge the arrows refer to: frozen while Down's constraint is on
        self.touched = None              # the last edge the pointer passed over since the last point
        self.snap_request: str | None = None
        self.free = False
        self.pitch = False
        self.message = ""

    # -- state --------------------------------------------------------------------------------------------------

    @property
    def state(self) -> str:
        return "typing" if self.typed else "measuring" if self.points else "idle"

    @property
    def hint(self) -> str:
        """The hint bar's gestures for the state, or what a key said."""
        return self.message or words.hint(self.mode, len(self.points), bool(self.typed))

    @property
    def numbers(self) -> str:
        """R609: what the drawing no longer writes of the span to the pointer (its number, along the slope, height
        difference, slope, direction from North, the path's total), for the hint bar before the gestures; "" at rest,
        while a number is typed or while a key's message is said."""
        return "" if self.typed or self.message else about(self)

    def set_mode(self, mode: str):
        if mode not in MODES:
            raise ValueError(f"Unknown measuring mode: {mode}")
        if mode != self.mode:
            self.leave()
            self.mode = mode

    def set_snap(self, kind: str | None):
        """The snap the menu asked for, for the point being placed only; None (or "all") gives them all back."""
        kind = None if kind in (None, "all") else kind
        if kind is not None and kind not in MENU:
            raise ValueError(f"Unknown snap: {kind}")
        self.snap_request = kind
        self._again()

    def set_polar(self, on: bool):
        """The plan's Ortho switched: the point under the pointer found again with the guides or without."""
        if bool(on) != self.polar:
            self.polar = bool(on)
            self._again()

    def wanted(self, modifiers=frozenset()) -> Wanted:
        free = "ctrl" in modifiers and "alt" not in modifiers
        if free or self.snap_request == "none":
            snaps = frozenset()
        elif self.snap_request:
            snaps = frozenset({self.snap_request})
        else:
            snaps = SNAPS
        polar = (self.polar and self.mode == "distance" and bool(self.points) and not free
                 and self.constraint is None and self.held is None)
        return Wanted(snaps, polar, tuple(tuple(p.point) for p in self.points))

    # -- the pointer --------------------------------------------------------------------------------------------

    def move(self, probe: Probe, modifiers=frozenset()):
        if probe is None or not geo.finite(probe.point):
            # nothing to measure under the pointer (the 3D view's sky): no point, no mark, no span to it; the view
            # keeps its cross (Controls/ToolCursor.js)
            self.probe = self.target = None
            self.pitch = False
            return
        probe = replace(probe, point=geo.point3(probe.point))
        self.message = ""
        self.free = "ctrl" in modifiers and "alt" not in modifiers
        if probe.edge is not None and self.constraint not in DOWN[1:]:
            self.touched = probe.edge
        if "shift" in modifiers:
            if self.held is None:
                self._hold()
        else:
            self.held = None
        self.probe = probe
        self.target = self._resolve(probe)

    def _again(self):
        if self.probe is not None:
            self.target = self._resolve(self.probe)

    def _hold(self):
        """Shift: the direction shown now is kept."""
        if self.points and self.target is not None and self.mode == "distance":
            self.held = geo.unit(_minus(self.target.point, self.points[-1].point))

    def _resolve(self, probe: Probe) -> Probe:
        """Where the point goes: the probe with the snap asked, the constraints, the pitch's plane."""
        self.pitch = False
        if not self.points:
            return probe
        last = self.points[-1]
        if self.mode == "height":
            # in the plan and in the 3D view alike the top stays on the foot's vertical: the pointer gives only its
            # height (the surface under it in the plan, the vertex snapped or the face hit in the 3D view); where it
            # took it from is kept as the reference, drawn dotted; the kind stays the snap's, the mark of the source's
            top = (last.point[0], last.point[1], probe.point[2])
            away = math.dist(top, probe.point) > 1e-6
            return replace(probe, point=top, source=probe.point if away else None)
        base = probe
        if self.snap_request == "perpendicular" and probe.edge is not None:
            base = replace(probe, point=geo.foot(last.point, *probe.edge), kind="perpendicular", exact=last.exact)
        c = self._constraint(base)
        if c is None:
            return base
        if base.ray is not None and base.kind not in SNAPPED:
            point = geo.constrain_ray(c, *base.ray) or geo.project(c, base.point)
            exact = last.exact
        elif base.ray is not None:
            point, exact = geo.project(c, base.point), last.exact and base.exact
        else:
            point, exact = geo.constrain_point(c, base.point), last.exact and base.exact
        moved = math.dist(point, base.point) > 1e-6
        return replace(base, point=point, kind="free" if moved else base.kind, exact=exact)

    def _constraint(self, base: Probe):
        last = self.points[-1].point
        if self.held is not None:
            return geo.line(last, self.held)
        if self.constraint in geo.AXES:
            return geo.axis(last, self.constraint)
        if self.constraint == "parallel" and self.edge:
            return geo.parallel(last, self.edge)
        plane = self._pitch_plane(base)
        if self.constraint == "perpendicular" and self.edge:
            perp = geo.perpendicular(last, self.edge)
            both = geo.meet(perp, plane) if perp and plane else None
            self.pitch = both is not None
            return both or perp
        self.pitch = plane is not None
        return plane

    def _pitch_plane(self, base: Probe):
        """The plane of the pitch the last point is on, while the pointer is on the same pitch (Ctrl: never)."""
        last = self.points[-1]
        if self.free or last.normal is None or base.normal is None:
            return None
        nz = abs((geo.unit(last.normal) or (0.0, 0.0, 1.0))[2])
        if not INCLINED[0] < nz < INCLINED[1] or not geo.parallel_normals(last.normal, base.normal):
            return None
        if not geo.on_plane(base.point, last.point, last.normal, SAME_APPROX):
            return None
        return geo.plane(last.point, last.normal)

    # -- clicks and keys ----------------------------------------------------------------------------------------

    def click(self, probe: Probe, modifiers=frozenset()):
        if probe is None:
            log.note("tool-click rejected tool=measure reason=no-probe")
            return
        if not geo.finite(probe.point):
            log.note("tool-click rejected tool=measure reason=non-finite")
            return
        if self.typed:
            self._apply_typed()
            return
        self.move(probe, modifiers)
        target = self.target
        if self.mode == "height":
            if not self.points:
                self._place(target)
            elif not self._same(target, self.points[0]):
                self._place(target)
                self.finish()
            else:
                log.note("tool-click rejected tool=measure reason=same-point")
            return
        if len(self.points) >= 3 and (self._same(self.probe, self.points[0]) or self._same(target, self.points[0])):
            self.finish(closed=True)
            return
        if self.points and self._same(target, self.points[-1]):
            log.note("tool-click rejected tool=measure reason=same-point")
            return                       # the second click of a double click: the point is there already
        self._place(target)

    def double_click(self, probe: Probe = None, modifiers=frozenset()):
        """Ends the measurement and adds no point (the click before it added it)."""
        self.finish()

    def _same(self, a: Probe, b: Probe) -> bool:
        tol = SAME_EXACT if a.exact and b.exact else SAME_APPROX
        return math.dist(a.point, b.point) <= tol

    def _place(self, p: Probe):
        self.points.append(replace(p, ray=None, guides=()))
        self.snap_request = None         # the snap asked from the menu was for this point
        self.constraint = None
        self.held = None
        self.edge = p.edge
        self.touched = None
        self.typed = ""
        self._again()

    def finish(self, closed: bool = False):
        """Enter, a double click, the first point clicked: the measurement goes to the list (from two points)."""
        if len(self.points) >= 2:
            self.measures.append(Measure(self._next_id, self.mode, tuple(self.points), closed))
            self._next_id += 1
        self._clear()

    def leave(self):
        """Another tool: the measurement in hand is kept when it has two points, else dropped; the list stays."""
        self.finish()

    def release(self, key: str) -> bool:
        """A key let go: Shift lets the direction held go at once, not at the next step of the pointer. True when
        something changed."""
        if key == "Shift" and self.held is not None:
            self.held = None
            self._again()
            return True
        return False

    def key(self, key: str, text: str = "", modifiers=frozenset()) -> str:
        """IGNORED when the key is not the tool's, USED, or LEAVE when Esc found nothing left to take back."""
        self.message = ""
        if key in {"Escape", "Esc"}:
            if self.typed:
                self.typed = ""
            elif self.points:
                self._clear()            # the measurement in hand goes, the list stays
            else:
                return LEAVE
            return USED
        if key == "Backspace":
            if self.typed:
                self.typed = self.typed[:-1]
            elif self.points:
                self.points.pop()
                self.constraint, self.held = None, None
                self.edge = self.points[-1].edge if self.points else None
                self._again()
            else:
                return IGNORED
            return USED
        if key in {"Enter", "Return"}:
            if self.typed:
                self._apply_typed()
            elif self.points:
                self.finish()
            else:
                return IGNORED
            return USED
        if key in {"Delete", "Del"} and not self.points and self.selected:
            self.remove_selected()
            return USED
        if key == "Shift":
            self._hold()
            return USED if self.held is not None else IGNORED
        if key in ARROWS or key == "Down":
            if not self.points:
                return IGNORED           # the view's: navigation
            if self.mode == "distance":
                self._arrow(key)
            return USED                  # with a point placed the arrows never move the view (the height has its vertical)
        if self.points and text and all(c in DIGITS for c in text):
            self.typed += text
            return USED
        return IGNORED

    def _arrow(self, key: str):
        self.held = None
        if key in ARROWS:
            axis = ARROWS[key]
            self.constraint = None if self.constraint == axis else axis
        else:
            edge = self.edge if self.constraint in DOWN[1:] else (self.touched or self.points[-1].edge)
            if edge is None:
                self.constraint = None
                self.message = words.no_edge()
                return
            now = self.constraint if self.constraint in DOWN else None
            self.constraint = DOWN[(DOWN.index(now) + 1) % len(DOWN)]
            self.edge = edge
        self._again()

    def _apply_typed(self):
        value = geo.parse_length(self.typed)
        self.typed = ""
        if value is None or not self.points:
            self.message = words.bad_length()
            return
        last = self.points[-1]
        if self.mode == "height":
            point = (last.point[0], last.point[1], last.point[2] + value)
        else:
            if value <= 0:
                self.message = words.bad_length()
                return
            direction = self._direction()
            plan = self.probe is None or self.probe.ray is None     # the length the view's large number shows
            point = geo.along(last.point, direction, value, plan=plan) if direction else None
            if point is None:
                self.message = words.no_direction()
                return
        typed = Probe(point, "free", exact=last.exact)
        self.target = typed
        self._place(typed)
        if self.mode == "height":
            self.finish()

    def _direction(self):
        """The direction a typed length goes along: the constraint's line towards the pointer, or the one shown."""
        last = self.points[-1].point
        shown = _minus(self.target.point, last) if self.target is not None else None
        c = self._constraint(self.target) if self.target is not None else None
        if c is not None and c.is_line:
            u = c.direction
            if shown and sum(shown[i] * u[i] for i in range(3)) < 0:
                return -u[0], -u[1], -u[2]
            return u
        return shown if shown and geo.unit(shown) else None

    # -- the measurements done ----------------------------------------------------------------------------------

    def select(self, ids, add: bool = False):
        known = {m.id for m in self.measures}
        chosen = {i for i in ids if i in known}
        self.selected = (self.selected | chosen) if add else chosen

    def choose(self, measure_id: int, modifiers=frozenset()) -> None:
        """A click on a measurement made, by the rule of the selection (docs/quick/regole.md, R529): alone it is the
        only one chosen, with Shift it is added, with Ctrl it is added or taken away."""
        if measure_id not in {m.id for m in self.measures}:
            return
        if "ctrl" in modifiers:
            self.selected = self.selected ^ {measure_id}
        else:
            self.select([measure_id], add="shift" in modifiers)

    @property
    def chosen_hint(self) -> str:
        """With Select and measurements chosen: the numbers of the one chosen (R609: the drawing writes only its
        lengths), or how many, then the gestures."""
        if not self.selected:
            return ""
        if len(self.selected) == 1:
            first = self.copy_text(next(iter(self.selected))).splitlines()
            about_it = first[0].replace("; ", words.SEP) if first else ""
            # a path: the length of each span too (R618: a number the drawing hides where there is no room is read here)
            if len(first) > 2:
                about_it += words.SEP + " + ".join(line.split("; ")[0] for line in first[1:])
        else:
            about_it = words.chosen_count(len(self.selected))
        return words.chosen_hint(about_it)

    def reset(self) -> None:
        """Another project in hand: the measurement in hand and those made go (they are of the project before)."""
        self._clear()
        self.remove_all()

    def remove_selected(self) -> int:
        before = len(self.measures)
        self.measures = [m for m in self.measures if m.id not in self.selected]
        self.selected = set()
        return before - len(self.measures)

    def remove_all(self) -> int:
        n = len(self.measures)
        self.measures, self.selected = [], set()
        return n

    def copy_text(self, measure_id: int) -> str:
        m = next((m for m in self.measures if m.id == measure_id), None)
        if m is None:
            return ""
        approx = not all(p.exact for p in m.points)
        spans = m.spans()
        if m.mode == "height":
            return words.height_copy(spans[0], m.points[-1].point[2], approx)
        if len(spans) == 1:
            return words.span_copy(spans[0], approx)
        true, plan = geo.totals([p.point for p in m.points], m.closed)
        area = geo.plan_area([p.point for p in m.points]) if m.closed else None
        return words.path_copy(spans, true, plan, area, approx)

    def copy_selected(self) -> str:
        return "\n\n".join(self.copy_text(m.id) for m in self.measures if m.id in self.selected)

    # -- what the views draw ------------------------------------------------------------------------------------

    def display(self, view: str, with_done: bool = True) -> dict:
        """Everything the view ("plan" or "3d") draws: the shape is in app/view/measure_display.py. `with_done`
        False: "done" left empty (`done(view)` gives it on its own)."""
        if view not in ("plan", "3d"):
            raise ValueError(f"Unknown view: {view}")
        return build(self, view, with_done)

    def done(self, view: str) -> list:
        """The measurements of the session as the view draws them."""
        if view not in ("plan", "3d"):
            raise ValueError(f"Unknown view: {view}")
        return made(self, view)
