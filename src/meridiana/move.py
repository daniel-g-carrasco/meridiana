"""Move and rotate an object of the project with what belongs to it, and the arithmetic of the gestures that do
it (study 16, B; task 16b). No Qt: the plan and the 3D view collect the gestures, the session applies the change.

What moves with what (study 16, B.7):
- a building: its outline, the pitches drawn by hand on it, the sub-fields and the exclusions that cite it (the
  sub-fields of every variant, not only of the one in hand: the building is shared by the variants); turned, the
  sides keep their places, so the eave of a single pitch, the gable ends and the sub-fields' pitches stay;
- a sub-field: its outline and its rows by hand (task 16c); turned, its explicit azimuth turns as much (automatic,
  the layout finds it again), and so do its rows; the modules taken out by hand stay taken out. It stays on its
  pitch (or on the ground): one that would leave it is refused, with the reason;
- an exclusion: its outline; one that leaves its building (or comes onto one) belongs to the building now under
  its middle, or to the ground (`host`);
- a free pitch ("pitch", "<building>:<pitch id>"): its outline and the sub-fields on it; it stays on its building;
- a row of modules ("row", "<sub-field>/<row id>", task 16c): within its sub-field, by manual.translate (the
  sub-field becomes by hand); it keeps the orientation of its sub-field, so a turn is refused with the reason.

`translate`, `rotate` and `copy` give a function `change(project)` for `session.edit`: the snapshot and the undo
are the session's, and a change that raises leaves the project as it was. Angles are in degrees, anticlockwise
on the plan (East towards North), as AutoCAD's ROTATE; an azimuth (CEI 82-25, from South, positive towards West)
turned anticlockwise by a degrees becomes azimuth - a.

The gestures (`Gesture`): a base point and a second point, or a value typed («3» is 3 m along the direction of
the pointer, «3;2» 3 m East and 2 m North, Tab passes to the direction); the angle of a rotation from where it
started, in steps; the arrows of the keyboard."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

from .i18n import _

KINDS = ("building", "subfield", "exclusion", "pitch", "row")
DECIMALS = 4                    # 0,1 mm, as the outlines drawn and the copies (model.Project.duplicate)
OUTSIDE_TOLERANCE = 0.01        # m2 a sub-field or a free pitch may go further out of its pitch or building
NUDGE = {"": 0.10, "shift": 1.0, "ctrl": 0.01}      # the arrows: 10 cm, 1 m with Shift, 1 cm with Ctrl (PVsyst)
ANGLE_STEPS = {"": 15.0, "ctrl": 5.0, "shift": 90.0}   # the steps of a rotation on the plan (SketchUp, the cube)

Point = tuple[float, float]


# the objects

def _things(project, kind: str) -> list:
    return {"building": project.buildings, "subfield": project.subfields, "exclusion": project.exclusions}.get(kind, [])


def _free_pitch(project, oid: str):
    """(building, its free pitch as a dict, its place among the free pitches) for "<building>:<pitch id>"."""
    bid, _sep, pid = oid.partition(":")
    b = project.building(bid)
    if b is None:
        return None
    for i, fp in enumerate(b.roof.free_pitches):
        if str(fp.get("id")) == pid:
            return b, fp, i
    return None


def _row(project, oid: str):
    """(sub-field, its rows now, the row) for "<sub-field>/<row>" (task 16c), or None."""
    from . import manual
    sfid, _sep, rid = oid.partition("/")
    sf = next((s for s in project.subfields if s.id == sfid), None)
    if sf is None or not (sf.filled or sf.manual):
        return None
    rows = manual.rows_now(project, sf)
    row = next((r for r in rows if r.id == rid), None)
    return (sf, rows, row) if row is not None and row.places else None


def outline(project, kind: str, oid: str) -> list[Point] | None:
    """The outline of the object, or None when there is no such object. A row's is the rectangle about its modules."""
    if kind == "pitch":
        found = _free_pitch(project, oid)
        return [tuple(map(float, q)) for q in found[1]["ring"]] if found else None
    if kind == "row":
        found = _row(project, oid)
        if found is None:
            return None
        from . import manual
        shape = manual.footprint(project, found[0], [found[2]]).minimum_rotated_rectangle
        return [tuple(map(float, q)) for q in list(shape.exterior.coords)[:-1]] if shape.geom_type == "Polygon" else None
    thing = next((x for x in _things(project, kind) if x.id == oid), None)
    if thing is None:
        return None
    return [tuple(map(float, q)) for q in (thing.footprint if kind == "building" else thing.ring)]


def centre(project, kind: str, oid: str) -> Point | None:
    """The middle of the object's outline (its centroid): where a rotation turns by default and the 3D gizmo
    stands."""
    ring = outline(project, kind, oid)
    if not ring or len(ring) < 3:
        return None
    from shapely.geometry import Polygon
    c = Polygon(ring).centroid
    return (float(c.x), float(c.y)) if not c.is_empty else ring[0]


def height(project, kind: str, oid: str, point: Point) -> float:
    """The height of the object at a point of the plan: the roof of a building, of the building a sub-field or an
    exclusion lies on, the ground otherwise."""
    from . import model
    sfid = oid.partition("/")[0] if kind == "row" else oid
    sf = next((s for s in project.subfields if s.id == sfid), None) if kind in ("subfield", "row") else None
    if sf is not None and sf.support is not None and sf.support.enabled:
        return float(project.surface_of(sf).z(*point))
    if kind == "building":
        b = project.building(oid)
    elif kind == "pitch":
        b = project.building(oid.partition(":")[0])
    elif kind == "row":
        sf = next((s for s in project.subfields if s.id == oid.partition("/")[0]), None)
        b = project.building(sf.building) if sf is not None else None
    else:
        thing = next((x for x in _things(project, kind) if x.id == oid), None)
        b = project.building(thing.building) if thing is not None else None
    return float(model.roof_z(b, [point])[0]) if b is not None else 0.0


def moving(project, kind: str, oid: str) -> list[list[Point]]:
    """The outlines that move with the object, the object's first: what the plan shows while it moves."""
    own = outline(project, kind, oid)
    if own is None:
        return []
    out = [own]
    if kind == "building":
        b = project.building(oid)
        out += [[tuple(map(float, q)) for q in fp["ring"]] for fp in b.roof.free_pitches]
        out += [[tuple(map(float, q)) for q in x.ring] for x in (*project.subfields, *project.exclusions)
                if x.building == oid]
    elif kind == "pitch":
        b, _fp, index = _free_pitch(project, oid)
        out += [[tuple(map(float, q)) for q in sf.ring] for sf in project.subfields
                if sf.building == b.id and sf.pitch == index]
    return out


def host(project, ring):
    """The building under the middle of `ring` and what a sub-field keeps of the pitch there (the side of its eave
    on a gable or hip roof, model.Building.pitch_ref); (None, None) on the ground."""
    from shapely.geometry import Polygon
    point = Polygon([tuple(map(float, q)) for q in ring]).representative_point()
    for b in project.buildings:
        if Polygon(b.footprint).buffer(1e-6).contains(point):
            for i, p in enumerate(b.pitches()):
                if Polygon(p.ring).buffer(1e-6).contains(point):
                    return b, b.pitch_ref(i)
            return b, b.pitch_ref(0)
    return None, None


# the transformations

def shift(dx: float, dy: float) -> Callable[[float, float], Point]:
    return lambda x, y: (x + dx, y + dy)


def turn(cx: float, cy: float, degrees: float) -> Callable[[float, float], Point]:
    """Anticlockwise on the plan by `degrees` about (cx, cy)."""
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return lambda x, y: (cx + c * (x - cx) - s * (y - cy), cy + s * (x - cx) + c * (y - cy))


def moved(ring, f) -> list[list[float]]:
    """A ring through `f`, as the file keeps it (lists, DECIMALS)."""
    return [[round(p[0], DECIMALS), round(p[1], DECIMALS)] for p in (f(float(x), float(y)) for x, y in ring)]


def turned_azimuth(azimuth: float, degrees: float) -> float:
    """An azimuth (from South, positive towards West) after a turn of `degrees` anticlockwise on the plan, in
    (-180, 180]."""
    a = (float(azimuth) - degrees) % 360.0
    a = a - 360.0 if a > 180.0 else a
    return round(a, DECIMALS) + 0.0


def _subfield(raw_ring, params: dict, f, degrees: float):
    """A sub-field's outline and its params moved: the explicit azimuth turned with it."""
    ring = moved(raw_ring, f)
    if degrees and params.get("azimuth") is not None:
        params = {**params, "azimuth": turned_azimuth(params["azimuth"], degrees)}
    return ring, params


def moved_rows(rows: list, f, degrees: float) -> list:
    """The rows by hand of a sub-field (layout.Row.as_dict) moved with it: each origin through `f`, each azimuth
    turned as much (task 16c)."""
    out = []
    for raw in rows or []:
        x, y = f(float(raw["x"]), float(raw["y"]))
        row = {**raw, "x": round(x, DECIMALS), "y": round(y, DECIMALS)}
        if degrees:
            row["azimuth"] = turned_azimuth(raw["azimuth"], degrees)
        out.append(row)
    return out


def _outside(ring, shape) -> float:
    from shapely.geometry import Polygon
    poly = Polygon([tuple(map(float, q)) for q in ring])
    if not poly.is_valid:
        poly = poly.buffer(0)
    return float(poly.difference(shape).area)


def _keep_on_pitch(project, sf, before) -> None:
    """A sub-field on a roof stays on its pitch: no further out of it than it was (a sub-field drawn a hair over the
    eave can still move). On the ground it stays on the ground."""
    from shapely.geometry import Polygon
    if sf.support is not None and sf.support.enabled:
        return
    b = project.building(sf.building)
    if b is None:
        if sf.building is not None:
            return
        middle = Polygon([tuple(map(float, q)) for q in sf.ring]).representative_point()
        for other in project.buildings:
            if Polygon(other.footprint).contains(middle):
                raise ValueError(_("a sub-field on the ground cannot go onto a building: draw it on its roof"))
        return
    pitches = b.pitches()
    index = b.pitch_index(sf.pitch)
    shape = Polygon(pitches[index].ring if index is not None else b.footprint).buffer(0)
    if _outside(sf.ring, shape) > _outside(before, shape) + OUTSIDE_TOLERANCE:
        raise ValueError(_("the sub-field would leave its pitch: a sub-field moves on its own pitch only"))


def _move_support(support, f, degrees: float) -> None:
    if support is not None:
        support.x0, support.y0 = f(support.x0, support.y0)
        support.azimuth = (support.azimuth - degrees + 180.0) % 360.0 - 180.0


def _apply(p, kind: str, oid: str, f, degrees: float) -> None:
    from shapely.geometry import Polygon
    if kind == "building":
        b = p.building(oid)
        if b is None:
            raise ValueError(_("there is no such object to move"))
        b.footprint = moved(b.footprint, f)
        for fp in b.roof.free_pitches:
            fp["ring"] = moved(fp["ring"], f)
        for sf in p.subfields:
            if sf.building == oid:
                sf.ring, sf.params = _subfield(sf.ring, sf.params, f, degrees)
                sf.rows = moved_rows(sf.rows, f, degrees)
                _move_support(sf.support, f, degrees)
        # the sub-fields of the other variants stand on the same building
        for v in p.variants:
            design = v.get("design")
            if not isinstance(design, dict):
                continue
            for raw in design.get("subfields") or []:
                if isinstance(raw, dict) and raw.get("building") == oid:
                    raw["ring"], params = _subfield(raw["ring"], raw.get("params") or {}, f, degrees)
                    if params != (raw.get("params") or {}):
                        raw["params"] = params
                    if raw.get("rows"):
                        raw["rows"] = moved_rows(raw["rows"], f, degrees)
                    if raw.get("support"):
                        support = raw["support"]
                        support["x0"], support["y0"] = f(support.get("x0", 0.0), support.get("y0", 0.0))
                        support["azimuth"] = (support.get("azimuth", 0.0) - degrees + 180.0) % 360.0 - 180.0
        for e in p.exclusions:
            if e.building == oid:
                e.ring = moved(e.ring, f)
        return
    if kind == "subfield":
        sf = next((s for s in p.subfields if s.id == oid), None)
        if sf is None:
            raise ValueError(_("there is no such object to move"))
        before = sf.ring
        sf.ring, sf.params = _subfield(sf.ring, sf.params, f, degrees)
        sf.rows = moved_rows(sf.rows, f, degrees)
        _move_support(sf.support, f, degrees)
        _keep_on_pitch(p, sf, before)
        return
    if kind == "exclusion":
        e = next((x for x in p.exclusions if x.id == oid), None)
        if e is None:
            raise ValueError(_("there is no such object to move"))
        e.ring = moved(e.ring, f)
        b, _pitch = host(p, e.ring)
        e.building = b.id if b is not None else None
        return
    if kind == "pitch":
        found = _free_pitch(p, oid)
        if found is None:
            raise ValueError(_("there is no such object to move"))
        b, fp, index = found
        before = fp["ring"]
        fp["ring"] = moved(fp["ring"], f)
        shape = Polygon(b.footprint).buffer(0)
        if _outside(fp["ring"], shape) > _outside(before, shape) + OUTSIDE_TOLERANCE:
            raise ValueError(_("a free pitch stays on its building: this would take it out"))
        for sf in p.subfields:
            if sf.building == b.id and sf.pitch == index:
                sf.ring, sf.params = _subfield(sf.ring, sf.params, f, degrees)
                sf.rows = moved_rows(sf.rows, f, degrees)
                _move_support(sf.support, f, degrees)
        return
    raise ValueError(_("there is no such object to move"))


def _check(project, kind: str, oid: str) -> None:
    if kind not in KINDS or outline(project, kind, oid) is None:
        raise ValueError(_("there is no such object to move"))


def translate(project, kind: str, oid: str, dx: float, dy: float) -> Callable:
    """The change that moves the object `dx` m East and `dy` m North, with what belongs to it. ValueError, with the
    reason in the designer's language, for an object that is not there; the change raises it for a move refused
    (session.edit then leaves the project as it was)."""
    _check(project, kind, oid)
    if kind == "row":                    # a row by hand, within its sub-field (task 16c: manual.translate)
        from . import manual
        sfid, _sep, rid = oid.partition("/")
        return manual.translate(project, sfid, rid, dx, dy)
    f = shift(float(dx), float(dy))
    return lambda p: _apply(p, kind, oid, f, 0.0)


def rotate(project, kind: str, oid: str, cx: float, cy: float, degrees: float) -> Callable:
    """The change that turns the object by `degrees` anticlockwise about (cx, cy), with what belongs to it. A row
    keeps the orientation of its sub-field: refused, with the reason."""
    _check(project, kind, oid)
    if kind == "row":
        raise ValueError(_("a row turns with its sub-field; a module on its own turns with a double click"))
    f = turn(float(cx), float(cy), float(degrees))
    return lambda p: _apply(p, kind, oid, f, float(degrees))


def copy(project, kind: str, oid: str, dx: float = 0.0, dy: float = 0.0, about: Point | None = None,
         degrees: float = 0.0) -> Callable:
    """The change that makes a copy of the object (model.Project.duplicate: the object alone, a sub-field without
    modules until asked), moved by (dx, dy) or turned by `degrees` about `about`; the change gives the copy's id."""
    _check(project, kind, oid)
    if kind == "pitch":
        raise ValueError(_("a free pitch is copied with its building"))
    if kind == "row":
        raise ValueError(_("a row is copied with «Add a row at the back»"))
    if degrees:
        f = turn(float(about[0]), float(about[1]), float(degrees)) if about is not None else None
    else:
        f = shift(float(dx), float(dy))

    def change(p):
        made = p.duplicate(kind, oid, (0.0, 0.0))
        g = f if f is not None else turn(*centre(p, kind, made), float(degrees))
        _apply(p, kind, made, g, float(degrees))
        return made
    return change


# the gestures

def parse(text: str) -> float | None:
    """A number as the designer types it, with the comma or the point; None when it is not one (yet)."""
    t = text.strip().replace(",", ".")
    if t in ("", "-", ".", "-."):
        return None
    try:
        value = float(t)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def typed_offset(distance: str, direction: str, pointer: Point) -> Point | None:
    """What was typed for a move: «3» is 3 m along `pointer` (the vector from the base point to the pointer, East
    if it has no length), «3;2» 3 m East and 2 m North; with a direction typed (Tab), the distance along that
    bearing from North. None when nothing usable was typed."""
    head, sep, tail = distance.partition(";")
    if sep:
        east, north = parse(head), parse(tail)
        if east is None and north is None:
            return None
        return (east or 0.0, north or 0.0)
    length = parse(head)
    bearing = parse(direction)
    if length is None:
        return None
    if bearing is not None:
        b = math.radians(bearing)
        return (length * math.sin(b), length * math.cos(b))
    n = math.hypot(*pointer)
    ux, uy = (pointer[0] / n, pointer[1] / n) if n > 1e-9 else (1.0, 0.0)
    return (length * ux, length * uy)


def angle_of(centre_: Point, start: Point, point: Point) -> float:
    """The angle from the direction centre -> start to the direction centre -> point, anticlockwise, in
    (-180, 180]."""
    a = math.atan2(start[1] - centre_[1], start[0] - centre_[0])
    b = math.atan2(point[1] - centre_[1], point[0] - centre_[0])
    d = math.degrees(b - a) % 360.0
    return d - 360.0 if d > 180.0 else d


def stepped(value: float, step: float) -> float:
    """`value` to the nearest multiple of `step` (none: as it is)."""
    return round(value / step) * step if step > 0 else value


def angle_step(mods: set) -> float:
    """The step of a rotation on the plan: 15°, 5° with Ctrl, 90° with Shift."""
    if "shift" in mods:
        return ANGLE_STEPS["shift"]
    if "ctrl" in mods:
        return ANGLE_STEPS["ctrl"]
    return ANGLE_STEPS[""]


def nudge(key: str, mods: set) -> Point | None:
    """The move of an arrow of the keyboard ("left", "right", "up", "down"): 10 cm, 1 m with Shift, 1 cm with
    Ctrl; North is up on the plan."""
    d = NUDGE["shift"] if "shift" in mods else NUDGE["ctrl"] if "ctrl" in mods else NUDGE[""]
    return {"left": (-d, 0.0), "right": (d, 0.0), "up": (0.0, d), "down": (0.0, -d)}.get(key)


@dataclass
class Gesture:
    """A Move (or a Rotate) in progress on the plan: what it moves, where it started, what was typed. The plan
    gives it the points already snapped; it answers with the move or the turn they make.

    Move: a base point (`base`), then the pointer; the offset is pointer - base. Rotate: about `about` (the base
    point clicked, else the object's middle), from the direction of `start` (where the pointer was when the turn
    began, or the grip), in steps (`angle_step`); with snaps off, to 0,1°."""
    kind: str
    oid: str
    middle: Point
    mode: str = "move"                  # "move" or "rotate"
    base: Point | None = None
    about: Point | None = None
    start: Point | None = None
    copy: bool = False                  # C: the result is a copy
    grip: bool = False                  # begun from a grip: Enter and Space go round the modes (AutoCAD)
    fields: list = field(default_factory=lambda: ["", ""])     # move: distance (or «E;N»), direction; rotate: angle
    field_at: int = 0

    @property
    def typing(self) -> bool:
        return any(self.fields)

    def type(self, text: str) -> bool:
        """A character typed: digits, the comma or the point, the minus, and «;» in the distance."""
        if not text or not all(c.isdigit() or c in ",.-" or (c == ";" and self.mode == "move" and self.field_at == 0)
                               for c in text):
            return False
        self.fields[self.field_at] += text
        return True

    def tab(self) -> None:
        """Tab: from the distance to the direction and back (a move); a rotation has one field."""
        if self.mode == "move":
            self.field_at = 1 - self.field_at

    def backspace(self) -> bool:
        if self.fields[self.field_at]:
            self.fields[self.field_at] = self.fields[self.field_at][:-1]
            return True
        if self.field_at and not self.fields[1]:
            self.field_at = 0
            return True
        return False

    def clear(self) -> None:
        self.fields, self.field_at = ["", ""], 0

    def to_rotate(self, pointer: Point, pixels: float) -> None:
        """«R»: the turn begins about the base point clicked, or the middle; from where the pointer is, or East when
        the pointer is on the centre (closer than `pixels` metres)."""
        self.mode = "rotate"
        self.about = self.base if self.base is not None else self.middle
        far = math.dist(pointer, self.about) > max(pixels, 1e-6)
        self.start = pointer if far else (self.about[0] + 1.0, self.about[1])
        self.clear()

    def to_move(self) -> None:
        self.mode = "move"
        if self.base is None:
            self.base = self.about or self.middle
        self.clear()

    def cycle(self, pointer: Point, pixels: float) -> None:
        """Enter or Space on a grip: Move, Rotate, Move..."""
        if self.mode == "move":
            self.to_rotate(pointer, pixels)
        else:
            self.to_move()

    def offset(self, pointer: Point) -> Point:
        """The move as the pointer gives it (typed values win)."""
        base = self.base if self.base is not None else self.middle
        v = (pointer[0] - base[0], pointer[1] - base[1])
        if self.mode == "move" and self.typing:
            got = typed_offset(self.fields[0], self.fields[1], v)
            if got is not None:
                return got
        return v

    def angle(self, pointer: Point, step: float) -> float:
        """The turn as the pointer gives it, in steps of `step` degrees (0: to 0,1°); a typed angle wins."""
        if self.typing:
            typed = parse(self.fields[0])
            if typed is not None:
                return typed
        about = self.about or self.middle
        if math.dist(pointer, about) < 1e-9:
            return 0.0
        value = angle_of(about, self.start or (about[0] + 1.0, about[1]), pointer)
        return round(stepped(value, step), 6) if step > 0 else round(value, 1)

    def label(self) -> str:
        """What was typed, as the plan writes it next to the pointer."""
        if self.mode == "rotate":
            return _("angle: {value}_°").format(value=self.fields[0])
        if self.field_at == 1:
            return _("direction: {value}_° from North").format(value=self.fields[1])
        return _("distance: {value}_").format(value=self.fields[0])
