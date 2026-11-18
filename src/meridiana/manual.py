"""The layout by hand (task 16c; study 16, C): the rows of a sub-field as the designer's objects, drawn, moved,
lengthened, taken away, exploded into their modules, turned. No Qt: the plan collects the gestures, the session
applies the change; every function gives a `change(project)` for `session.edit`, as move.py does, so that the snapshot
and the undo are the session's and a change that raises leaves the project as it was.

The automatic layout stays the first gesture (Daniel, 23/10/2026): a sub-field is laid with «Lay the modules», then
corrected. The first gesture on a row makes the sub-field «by hand» (`SubField.manual`): its rows, those of its last
layout (`Result.rows`), are kept in the file and laid as they are; the pitch, the fire-brigade rules and the shadows
no longer make them again but are checked (checks.manual_items). «Lay again automatically» (`relayout`) gives them
back to the generator, as PVsyst warns: «Any changes on rows will be lost if you generate the zone again».

Invariants (study 16, C.3): one module, one orientation and one tilt for a sub-field (a row keeps where its places
are, the sub-field says what is on them); the rows and the modules exploded stay in their sub-field: a move that
takes them further out of it is refused, with the reason. A row drawn over the edge or an exclusion is kept (PV*SOL
draws it red, the designer may be right): the checks say it."""

from __future__ import annotations

import copy
from collections.abc import Callable

from . import geo, layout
from .i18n import _

OUTSIDE_TOLERANCE = 0.01        # m2 of modules a move may take further out of the sub-field
SAME_SIZE = 0.02                # m: a new module this close in both sides keeps the rows by hand (Daniel, 23/10/2026)
DECIMALS = 4                    # 0,1 mm, as the outlines (move.DECIMALS)


# what a sub-field is made of

def _subfield(project, sfid: str):
    sf = next((s for s in project.subfields if s.id == sfid), None)
    if sf is None:
        raise ValueError(_("there is no such sub-field"))
    return sf


def rows_now(project, sf, result=None) -> list[layout.Row]:
    """The rows of a sub-field as they are now: its own by hand, else those of its layout in hand (`result`, when
    it is that sub-field's and not an error), else those of a layout made here."""
    if sf.manual:
        return sf.hand_rows()
    if result is not None and not isinstance(result, Exception) and getattr(result, "rows", None) is not None:
        if result.rows or result.count == 0:
            return [layout.Row.of(r.as_dict()) for r in result.rows]
    if not sf.filled:
        return []
    return [layout.Row.of(r.as_dict()) for r in project.fill(sf, shade=_shade()).rows]


def removed_on_alignment(project, sf, alignment: str, result=None) -> list[str]:
    """The modules taken out by hand of a sub-field that changes its alignment (R418): their keys say where they stood
    in the rows of the old way, so they become those of the modules that take their place in the new one, where one
    does, at most a module's width away (rows further apart than the pitch move across). Lays the sub-field once, only
    when something was taken out."""
    import shapely
    from shapely.geometry import Polygon
    whole = copy.deepcopy(sf)
    whole.removed = []
    whole.params.pop("target_kwp", None)
    params = project.fill_params(whole)
    module, surface = project.module_of(whole), project.surface_of(whole)
    rows = result.rows if result is not None and not isinstance(result, Exception) else project.fill(whole, shade=_shade()).rows
    gone = set(sf.removed)
    points = [pm.centre for pm in layout.modules_of(rows, module, params, surface) if pm.key in gone]
    whole.params["alignment"] = alignment
    laid = project.fill(whole, shade=_shade()).modules
    if not laid or not points:
        return []
    tree = shapely.STRtree([Polygon(pm.corners) for pm in laid])
    found = tree.query_nearest(shapely.points(points), max_distance=module.width, all_matches=False)
    return sorted({laid[i].key for i in found[1].tolist()})


def _shade():
    from .energy import system           # the layout out of the shadows needs them; the model does not load them
    return system.shadow_exclusions


def frame(project, sf, rows: list[layout.Row] | None = None,
          params: layout.Params | None = None) -> tuple[layout.Frame, layout.Sizes, layout.Params]:
    """The work frame of the sub-field's rows (that of its rows, or the one its automatic layout would take), the
    sizes of a row (on the plane of its surface) and the parameters (`params`, or the sub-field's)."""
    from shapely.geometry import Polygon
    p = params or project.fill_params(sf)
    surface = project.surface_of(sf)
    tilt = layout.mount_tilt(surface, p)
    if rows:
        azimuth = rows[0].azimuth
    else:
        area = Polygon([tuple(map(float, q)) for q in sf.ring]).buffer(0)
        azimuth = layout.row_azimuth(area, surface, p)
    size = layout.Sizes.of(project.module_of(sf), p, tilt, surface=surface)
    return layout.row_frame(azimuth, size), size, p


def east_west_params(project, sf) -> layout.Params:
    """The sub-field's parameters with its modules in east-west pairs (the East-west tool, R279)."""
    import dataclasses
    return dataclasses.replace(project.fill_params(sf), mounting="east_west")


def footprint(project, sf, rows: list[layout.Row], params: layout.Params | None = None):
    """The plan shape of the modules of `rows` (shapely), as the layout would lay them."""
    from shapely.geometry import MultiPolygon, Polygon
    placed = layout.modules_of(rows, project.module_of(sf), params or project.fill_params(sf), project.surface_of(sf))
    return MultiPolygon([Polygon(m.corners) for m in placed]) if placed else MultiPolygon()


def corners(project, sf, rows: list[layout.Row], params: layout.Params | None = None) -> list:
    """The plan corners of each module of `rows`: what the plan draws while a row is drawn or moved."""
    placed = layout.modules_of(rows, project.module_of(sf), params or project.fill_params(sf), project.surface_of(sf))
    return [m.corners for m in placed]


def trouble(project, sf, rows: list[layout.Row], params: layout.Params | None = None) -> bool:
    """Whether the modules of `rows` go out of the area the layout would use (the sub-field less its edge band) or
    onto an exclusion with its clearance: the row drawn red (PV*SOL), kept all the same."""
    from shapely.geometry import Polygon
    shape = footprint(project, sf, rows, params)
    if shape.is_empty:
        return False
    area = Polygon([tuple(map(float, q)) for q in sf.ring]).buffer(0)
    usable = layout.usable_area(area, project.fill_params(sf), project.exclusions_of(sf))
    return shape.difference(usable.buffer(layout.DISTANCE_TOLERANCE)).area > 1e-4


def new_id(rows: list[layout.Row]) -> str:
    """An id for a new row, «f» and a number past every row's and every key's: the keys of the modules exploded
    out of a row keep its id, and a new row must not take them."""
    used = 0
    for r in rows:
        for text in [r.id] + [k.partition(":")[0] for k in r.keys]:
            if text.startswith("f") and text[1:].isdigit():
                used = max(used, int(text[1:]))
    return f"f{used + 1}"


def _store(sf, rows: list[layout.Row], project=None) -> None:
    sf.rows = [r.as_dict() for r in rows]
    sf.manual = True
    sf.filled = True
    if project is not None:
        refresh_outline(project, sf)


def refresh_outline(project, sf) -> None:
    """A sub-field that is its modules (R445) keeps its outline flush with them: made again from its rows, less the
    modules taken out by hand, after every change of them. Nothing for the others."""
    if sf.flush and sf.rows:
        ring = outline(project, sf, sf.hand_rows(), sf.removed)
        if ring:
            sf.ring = ring


def take(project, sfid: str, result=None) -> Callable:
    """The change that makes a sub-field by hand, with the rows of its layout (`result`); nothing if it is already."""
    sf = _subfield(project, sfid)
    rows = None if sf.manual else [r for r in rows_now(project, sf, result) if r.places]

    def change(p):
        sf = _subfield(p, sfid)
        if not sf.manual:
            _store(sf, rows or [], p)
    return change


def _hand(project, sfid: str, result) -> list[layout.Row]:
    """The rows a change works on: the sub-field's by hand, or those of its layout (rows without places left out)."""
    sf = _subfield(project, sfid)
    return [r for r in rows_now(project, sf, result) if r.places or sf.manual]


def _row(rows: list[layout.Row], rid: str) -> layout.Row:
    found = next((r for r in rows if r.id == rid), None)
    if found is None:
        raise ValueError(_("there is no such row"))
    return found


# drawing a row

def places_along(length: float, size: layout.Sizes, p: layout.Params) -> list[float]:
    """Where the places of a row `length` metres long start, from its origin: as many modules as fit with the gap
    between them, in tables of the sub-field's size (whole tables first) when it has them; at least one."""
    step = size.along + size.gap
    n = max(1, int((length + size.gap) // step + 1e-9))
    per = int(p.table_modules or 0)
    if per > 0:
        table_len = per * size.along + (per - 1) * size.gap
        tables = int((length + p.table_gap) // (table_len + p.table_gap) + 1e-9)
        if tables > 0:
            return [round(t * (table_len + p.table_gap) + k * step, 6) for t in range(tables) for k in range(per)]
    return [round(k * step, 6) for k in range(n)]


def line_azimuth(start, end, near: float, inside=None, either: bool = False) -> float:
    """The azimuth of a row whose front edge runs from `start` to `end`: square to the line, on the side closest to
    `near` (the sub-field's rows); `near` itself for a line of no length. When both sides are as close, or when
    either will do (`either`: an east-west pair faces both ways), the row goes from the line towards `inside` (the
    middle of the sub-field) rather than out of it."""
    import math
    dx, dy = float(end[0]) - float(start[0]), float(end[1]) - float(start[1])
    if math.hypot(dx, dy) < 1e-9:
        return near
    bearing = math.degrees(math.atan2(dx, dy))
    sides = [geo.bearing_to_azimuth(bearing + turn) for turn in (90.0, -90.0)]
    off = [abs((a - near + 180.0) % 360.0 - 180.0) for a in sides]
    if inside is not None and (either or abs(off[0] - off[1]) < 1e-6):
        tx, ty = float(inside[0]) - float(start[0]), float(inside[1]) - float(start[1])
        # the back of the row (away from the side it faces) towards the middle
        return round(max(sides, key=lambda a: -(geo.facing_vector(a)[0] * tx + geo.facing_vector(a)[1] * ty)), 6)
    return round(sides[0] if off[0] <= off[1] else sides[1], 6)


def line_row(project, sf, start, end, rows: list[layout.Row], rid: str | None = None,
             params: layout.Params | None = None) -> layout.Row:
    """The row from `start` to `end` (plan points): its front edge starts at `start` and runs along the line drawn
    (R280: the row follows the line, its modules square to it, facing the side of the sub-field's rows) as far as
    `end`, with the module, the gap, the tables of the sub-field (`params`, or its own). On a pitch the length is
    measured on it."""
    from shapely.geometry import Polygon
    f, size, p = frame(project, sf, rows, params)
    middle = Polygon([tuple(map(float, q)) for q in sf.ring]).centroid
    f = layout.row_frame(line_azimuth(start, end, f.azimuth, (middle.x, middle.y), size.east_west), size)
    us, vs = f.to_work(float(start[0]), float(start[1]))
    ue, _ve = f.to_work(float(end[0]), float(end[1]))
    length = abs(ue - us)
    places = places_along(length, size, p)
    span = places[-1] + size.along
    u0 = us if ue >= us else us - span
    x, y = f.to_plan(u0, vs)
    return layout.Row(rid or new_id(rows), x, y, f.azimuth, places)


def draw(project, sfid: str, start, end, result=None, east_west: bool = False) -> Callable:
    """The change that adds the row drawn from `start` to `end` to the sub-field, which becomes (or stays) by hand
    and laid; the change gives the new row's id. With `east_west` (the East-west tool, R279) the row is of east-west
    pairs and the sub-field's mounting becomes east-west in the same step; the rows it had of another mounting give
    way (one mounting for a sub-field, study 16 C.3), with the modules taken out of them."""
    sf = _subfield(project, sfid)
    rows = _hand(project, sfid, result) if sf.filled or sf.manual else []
    params = east_west_params(project, sf) if east_west else None
    row = line_row(project, sf, start, end, rows, params=params)
    keep = rows if not east_west or project.fill_params(sf).mounting == "east_west" else []

    def change(p):
        target = _subfield(p, sfid)
        if east_west:
            target.params["mounting"] = "east_west"
            if not keep:
                target.removed = []
        _store(target, keep + [row], p)
        return row.id
    return change


# the rows by hand

def remove(project, sfid: str, rid: str, result=None) -> Callable:
    """The change that takes a row away, with the modules of it taken out by hand."""
    rows = _hand(project, sfid, result)
    gone = _row(rows, rid)
    f, size, _p = frame(project, _subfield(project, sfid), rows)
    keys = set(layout.row_keys(gone, size))

    def change(p):
        sf = _subfield(p, sfid)
        sf.removed = [k for k in sf.removed if k not in keys]
        _store(sf, [r for r in rows if r.id != rid], p)
    return change


def append(project, sfid: str, rid: str, result=None) -> Callable:
    """«Add a row at the back»: a row like `rid`, one pitch behind the last row of the sub-field (the pitch of its
    layout); the change gives its id."""
    sf = _subfield(project, sfid)
    rows = _hand(project, sfid, result)
    like = _row(rows, rid)
    f, size, p = frame(project, sf, rows)
    pitch = float(getattr(result, "pitch", 0.0) or 0.0) if result is not None and not isinstance(result, Exception) \
        else 0.0
    pitch = max(pitch, size.depth)
    own = layout.row_frame(like.azimuth, size)       # the frame of the row it is like
    u0, _v = own.to_work(like.x, like.y)
    back = max(own.to_work(r.x, r.y)[1] for r in rows if abs(r.azimuth - like.azimuth) < 1e-6)
    x, y = own.to_plan(u0, back + pitch)
    row = layout.Row(new_id(rows), x, y, like.azimuth, list(like.places), turned=like.turned)

    def change(q):
        _store(_subfield(q, sfid), rows + [row], q)
        return row.id
    return change


def resize(project, sfid: str, rid: str, point, result=None) -> Callable:
    """«Shorten or lengthen»: the end of the row dragged to `point`; its places as far as the point reaches along
    it, at least one; added places take the row's last step (the module and the gap for a row of one)."""
    sf = _subfield(project, sfid)
    rows = _hand(project, sfid, result)
    row = _row(rows, rid)
    f, size, p = frame(project, sf, rows)
    own = layout.row_frame(row.azimuth, size)
    u_o, _v = own.to_work(row.x, row.y)
    reach = own.to_work(float(point[0]), float(point[1]))[0] - u_o
    along = size.across if row.turned else size.along
    step = row.places[-1] - row.places[-2] if len(row.places) > 1 else along + size.gap
    places = [u for u in row.places if u + along <= reach + 1e-6] or row.places[:1]
    while places[-1] + step + along <= reach + 1e-6:
        places.append(round(places[-1] + step, 6))
    halves = 2 if size.east_west else 1
    keys = list(row.keys[:len(places) * halves])
    new = layout.Row(row.id, row.x, row.y, row.azimuth, places, keys, row.turned)

    def change(q):
        _store(_subfield(q, sfid), [new if r.id == rid else r for r in rows], q)
    return change


def explode(project, sfid: str, rid: str | None = None, result=None) -> Callable:
    """«Explode»: each place of the row (of every row with `rid` None) becomes a row of one place where it was, with
    the keys its modules had: the strings and the modules taken out stay on them. The change gives the new ids."""
    sf = _subfield(project, sfid)
    rows = _hand(project, sfid, result)
    if rid is not None:
        _row(rows, rid)
    out, made = _exploded(project, sf, rows, rid)

    def change(q):
        _store(_subfield(q, sfid), out, q)
        return made
    return change


def _exploded(project, sf, rows: list[layout.Row], rid: str | None) -> tuple[list[layout.Row], list[str]]:
    """The rows with those to explode (`rid`, or all) made rows of one place each, and the ids of the new ones."""
    f, size, _p = frame(project, sf, rows)
    halves = 2 if size.east_west else 1
    out: list[layout.Row] = []
    made: list[str] = []
    number = int(new_id(rows)[1:])           # the ids of the new rows, past every row's and key's
    for row in rows:
        if (rid is not None and row.id != rid) or row.count <= 1:
            out.append(row)
            continue
        own = layout.row_frame(row.azimuth, size)
        u_o, v0 = own.to_work(row.x, row.y)
        for i, u in enumerate(row.places):
            x, y = own.to_plan(u_o + u, v0)
            one = layout.Row(f"f{number}", x, y, row.azimuth, [0.0],
                             [row.slot_key(i * halves + h) for h in range(halves)], row.turned)
            number += 1
            out.append(one)
            made.append(one.id)
    return out, made


def turn(project, sfid: str, rid: str, result=None) -> Callable:
    """Turn a module exploded by 90° about its middle (Aurora's double click): the module's other side along the
    row. A row of more places is turned only by its sub-field: refused, with the reason."""
    sf = _subfield(project, sfid)
    rows = _hand(project, sfid, result)
    row = _row(rows, rid)
    if row.count != 1:
        raise ValueError(_("only a module on its own turns: explode the row first"))
    f, size, p = frame(project, sf, rows)
    module = project.module_of(sf)
    before = layout.Sizes.of(module, p, size.tilt, row.turned)
    after = layout.Sizes.of(module, p, size.tilt, not row.turned)
    own = layout.row_frame(row.azimuth, size)
    u_o, v0 = own.to_work(row.x, row.y)
    cu, cv = u_o + before.along / 2, v0 + before.depth / 2
    x, y = own.to_plan(cu - after.along / 2, cv - after.depth / 2)
    new = layout.Row(row.id, x, y, row.azimuth, [0.0], list(row.keys), not row.turned)

    def change(q):
        _store(_subfield(q, sfid), [new if r.id == rid else r for r in rows], q)
    return change


def _outside(project, sf, rows) -> float:
    """How much of the modules of `rows` lies out of where they may be: the sub-field's outline; for a sub-field that
    is its modules (R445), the roof it lies on (its outline follows the modules), nothing on the ground."""
    from shapely.geometry import Polygon
    shape = footprint(project, sf, rows)
    if shape.is_empty:
        return 0.0
    ring = project.host_ring(sf) if sf.flush else sf.ring
    if ring is None:
        return 0.0
    area = Polygon([tuple(map(float, q)) for q in ring]).buffer(0)
    return float(shape.difference(area).area)


def translate(project, sfid: str, rid: str, dx: float, dy: float, result=None) -> Callable:
    """Move a row (a module exploded is a row of one) `dx` m East and `dy` m North, within its sub-field: one that
    would take its modules further out of it is refused, with the reason (the keys stay: the strings follow)."""
    sf = _subfield(project, sfid)
    rows = _hand(project, sfid, result)
    row = _row(rows, rid)
    new = layout.Row(row.id, round(row.x + float(dx), DECIMALS), round(row.y + float(dy), DECIMALS), row.azimuth,
                     list(row.places), list(row.keys), row.turned)
    if _outside(project, sf, [new]) > _outside(project, sf, [row]) + OUTSIDE_TOLERANCE:
        raise ValueError(_("a row stays in its sub-field: this would take it out"))

    def change(q):
        _store(_subfield(q, sfid), [new if r.id == rid else r for r in rows], q)
    return change


def _with_key(rows: list[layout.Row], key: str) -> layout.Row | None:
    """The row one of whose places holds the module `key`."""
    return next((r for r in rows for slot in range(max(len(r.keys), 2 * r.count)) if r.slot_key(slot) == key), None)


def move_module(project, sfid: str, key: str, dx: float, dy: float, result=None) -> Callable:
    """Move one module `dx` m East and `dy` m North, within its sub-field (R295): its row is exploded where it was and
    the module's place, a row of one now, moves. The keys stay, so the strings follow; on a place shared with another
    module (a pair facing east and west) the place moves whole. One that would leave the sub-field is refused."""
    sf = _subfield(project, sfid)
    rows = _hand(project, sfid, result)
    home = _with_key(rows, key)
    if home is None:
        raise ValueError(_("this module is not on a row of its sub-field"))
    alone = _exploded(project, sf, rows, home.id)[0] if home.count > 1 else rows
    row = _with_key(alone, key)
    new = layout.Row(row.id, round(row.x + float(dx), DECIMALS), round(row.y + float(dy), DECIMALS), row.azimuth,
                     list(row.places), list(row.keys), row.turned)
    if _outside(project, sf, [new]) > _outside(project, sf, [row]) + OUTSIDE_TOLERANCE:
        raise ValueError(_("a module stays in its sub-field: this would take it out"))

    def change(q):
        _store(_subfield(q, sfid), [new if r.id == row.id else r for r in alone], q)
    return change


def delete_module(project, sfid: str, key: str, result=None) -> Callable:
    """Delete on a module: a module on its own (a row of one place and one module) goes with its row; any other is
    taken out by hand (SubField.removed), as before task 16c."""
    sf = _subfield(project, sfid)
    rid = None
    if sf.manual:
        f, size, _p = frame(project, sf, sf.hand_rows())
        for r in sf.hand_rows():
            if r.count == 1 and size.stack == 1 and not size.east_west and r.slot_key(0) == key:
                rid = r.id
    if rid is not None:
        return remove(project, sfid, rid, result)

    def change(p):
        target = _subfield(p, sfid)
        if key not in target.removed:
            target.removed.append(key)
        refresh_outline(p, target)
    return change


def delete_modules(project, sfid: str, keys: list[str], result=None) -> Callable:
    """Delete on many modules of a sub-field, as one change: as delete_module for each."""
    sf = _subfield(project, sfid)
    wanted = set(keys)
    gone: dict[str, layout.Row] = {}
    if sf.manual:
        f, size, _p = frame(project, sf, sf.hand_rows())
        if size.stack == 1 and not size.east_west:
            gone = {r.id: r for r in sf.hand_rows() if r.count == 1 and r.slot_key(0) in wanted}
    alone = {r.slot_key(0) for r in gone.values()}

    def change(p):
        target = _subfield(p, sfid)
        if gone:
            _store(target, [r for r in target.hand_rows() if r.id not in gone], p)
        target.removed = [k for k in target.removed if k not in alone]
        target.removed += [k for k in keys if k not in alone and k not in target.removed]
        refresh_outline(p, target)
    return change


def _fresh_key(rows: list[layout.Row], removed, rid: str) -> str:
    """A key «rid:n» no module of the sub-field has, nor one taken out (with its levels, «rid:n:level»)."""
    taken = {r.slot_key(slot) for r in rows for slot in range(max(len(r.keys), 2 * r.count))}
    taken.update(str(k).rsplit(":", 1)[0] for k in removed if str(k).count(":") >= 2)
    taken.update(str(k) for k in removed)
    n = 0
    while f"{rid}:{n}" in taken:
        n += 1
    return f"{rid}:{n}"


def add_module(project, sfid: str, point, result=None) -> Callable:
    """«Add a module» where the designer points (06/11/2026), one, never a whole row: a module taken out by hand
    under the point comes back; else the row whose line the point is on gets one place there, at the row's step from
    its nearest place (past an end or in a gap), the other modules keeping their keys and places; else a row of one
    module at the point, facing as the others. Refused on a module already there, with no room between two, or
    where the module would leave the sub-field."""
    from shapely.geometry import Point, Polygon
    sf = _subfield(project, sfid)
    here = Point(float(point[0]), float(point[1]))
    rows = _hand(project, sfid, result)
    if not rows:
        raise ValueError(_("lay the modules first: a module goes on a row of its sub-field"))
    placed = layout.modules_of(rows, project.module_of(sf), project.fill_params(sf), project.surface_of(sf))
    under = [m for m in placed if Polygon(m.corners).buffer(1e-6).contains(here)]
    back = next((m for m in under if m.key in sf.removed), None)
    if back is not None:
        def restore(q):
            target = _subfield(q, sfid)
            target.removed = [k for k in target.removed if k != back.key]
            refresh_outline(q, target)
        return restore
    # R445, decision 3: a module set aside on an obstacle or off the roof (drawn red) comes back with a click, the
    # designer's call; the checks say it stands on the obstacle
    aside = next((m for m in getattr(result, "blocked", None) or [] if Polygon(m.corners).buffer(1e-6).contains(here)),
                 None)
    if aside is not None and aside.key not in sf.kept:
        def keep(q):
            target = _subfield(q, sfid)
            if aside.key not in target.kept:
                target.kept.append(aside.key)
        return keep
    if under:
        raise ValueError(_("there is a module here already"))
    f, size, p = frame(project, sf, rows)
    halves = 2 if size.east_west else 1
    ordered = sorted(rows, key=lambda r: footprint(project, sf, [r]).distance(here))
    for row in ordered:
        if not row.places:
            continue
        own = layout.row_frame(row.azimuth, size)
        along = size.across if row.turned else size.along
        u_o, _v = own.to_work(row.x, row.y)
        start = own.to_work(here.x, here.y)[0] - u_o - along / 2
        steps = sorted(b - a for a, b in zip(row.places, row.places[1:], strict=False) if b - a > 1e-6)
        step = steps[0] if steps else along + size.gap
        near = min(row.places, key=lambda u: abs(u - start))
        place = round(near + round((start - near) / step) * step, 6)
        alone = layout.Row(row.id, row.x, row.y, row.azimuth, [place], [], row.turned)
        if not any(Polygon(c).buffer(1e-6).contains(here) for c in corners(project, sf, [alone])):
            continue        # the point is not on this row's line
        if any(abs(place - u) < along + size.gap - 1e-6 for u in row.places):
            raise ValueError(_("no room for a module here: it would lie on the modules beside it"))
        at = sum(1 for u in row.places if u < place)
        keys = [row.slot_key(slot) for slot in range(row.count * halves)]
        fresh = []
        for _half in range(halves):
            fresh.append(_fresh_key(rows + [layout.Row(row.id, 0, 0, 0, [], keys + fresh)], sf.removed, row.id))
        places = row.places[:at] + [place] + row.places[at:]
        keys = keys[:at * halves] + fresh + keys[at * halves:]
        new = layout.Row(row.id, row.x, row.y, row.azimuth, places, keys, row.turned)
        if _outside(project, sf, [new]) > _outside(project, sf, [row]) + OUTSIDE_TOLERANCE:
            raise ValueError(_("a module stays in its sub-field: this would take it out"))

        def change(q, new=new):
            _store(_subfield(q, sfid), [new if r.id == new.id else r for r in rows], q)
        return change
    like = ordered[0]
    own = layout.row_frame(like.azimuth, size)
    along = size.across if like.turned else size.along
    u, v = own.to_work(here.x, here.y)
    probe = layout.Row("probe", *own.to_plan(u - along / 2, v), like.azimuth, [0.0], [], like.turned)
    shape = footprint(project, sf, [probe])
    dx, dy = here.x - shape.centroid.x, here.y - shape.centroid.y
    one = layout.Row(new_id(rows), round(probe.x + dx, DECIMALS), round(probe.y + dy, DECIMALS), like.azimuth, [0.0],
                     [], like.turned)
    if _outside(project, sf, [one]) > OUTSIDE_TOLERANCE:
        raise ValueError(_("a module stays in its sub-field: this would take it out"))
    if not footprint(project, sf, [one]).intersection(footprint(project, sf, rows)).area < 1e-4:
        raise ValueError(_("no room for a module here: it would lie on the modules beside it"))

    def single(q):
        _store(_subfield(q, sfid), rows + [one], q)
    return single


def relayout(project, sfid: str) -> Callable:
    """«Lay again automatically»: the rows by hand go, and the modules taken out by hand with them; the generator
    lays the sub-field again from its parameters. A sub-field that is its modules (R445) is gridded again whole over
    its outline, the modules taken out and those kept on obstacles forgotten: it stays its modules."""
    sf = _subfield(project, sfid)
    rows = grid(project, sf) if sf.flush else None

    def change(p):
        sf = _subfield(p, sfid)
        if rows is not None:
            sf.removed, sf.kept = [], []
            _store(sf, rows, p)
            return
        sf.rows, sf.manual, sf.removed, sf.filled = [], False, [], True
    return change


def row_of(result, key: str) -> str:
    """The id of the row a module is in, by its key; "" when it is not laid."""
    for m in getattr(result, "modules", None) or []:
        if m.key == key:
            return m.rid
    return ""


# a new module on rows by hand (Daniel, 23/10/2026: adapt within 2 cm, else ask)

def same_size(a: layout.Module, b: layout.Module, tolerance: float = SAME_SIZE) -> bool:
    return abs(a.length - b.length) <= tolerance + 1e-9 and abs(a.width - b.width) <= tolerance + 1e-9


def adapted(rows: list, old: layout.Module, new: layout.Module, portrait: bool) -> list:
    """The rows by hand (as the file keeps them) for a new module: the same origins and the same number of places,
    each place moved by the change of the module's side along the row, so that the gaps between them stay."""
    out = []
    for raw in rows:
        row = layout.Row.of(raw)
        upright = bool(portrait) != bool(row.turned)
        grow = (new.width - old.width) if upright else (new.length - old.length)
        row.places = [round(u + i * grow, 6) for i, u in enumerate(row.places)]
        out.append(row.as_dict())
    return out


def change_module(project, sfid: str, module_id: str, adapt: bool = True) -> Callable:
    """The change of a sub-field's module: by hand, its rows adapted (`adapted`) unless `adapt` is False, when the
    sub-field is laid again automatically."""
    sf = _subfield(project, sfid)
    old = project.module_of(sf)

    def change(p):
        target = _subfield(p, sfid)
        target.module = module_id
        if not target.manual:
            return
        if adapt:
            target.rows = adapted(target.rows, old, p.module_of(target), target.layout_params().portrait)
        else:
            target.rows, target.manual, target.removed = [], False, []
    return change


def apply_defaults(project, sfid: str) -> Callable:
    """«Apply the defaults» to a sub-field (R523): the module and the DEFAULT_KEYS of the project's defaults in place
    of its own (what it says of its strings and the power asked of it stay), the mounting chosen for its surface. A
    sub-field that is its modules is gridded again whole over its outline, as `relayout`; one by hand keeps its rows,
    adapted to the new module as `change_module`; an automatic one lays again from the parameters."""
    from . import model
    sf = _subfield(project, sfid)
    module = project.default_module()
    params = {k: v for k, v in project.default_params().items() if k not in model.OWN_KEYS}
    mounting = model.chosen_mounting(params.pop("mounting", None), project.building(sf.building), sf.pitch)
    params = {"mounting": mounting, "alignment": params.pop("alignment", layout.NEW_ALIGNMENT), **params}
    old = project.module_of(sf)

    def change(p):
        target = _subfield(p, sfid)
        own = {k: v for k, v in target.params.items() if k not in model.DEFAULT_KEYS or k in model.OWN_KEYS}
        target.params = {**params, **own}
        target.module = module
        if target.flush:
            rows = grid(p, target)
            if not rows:
                raise ValueError(_("no module of the defaults fits in this sub-field"))
            target.removed, target.kept = [], []
            _store(target, rows, p)
        elif target.manual:
            target.rows = adapted(target.rows, old, p.module_of(target), target.layout_params().portrait)
    return change


def needs_asking(project, sfid: str, module_id: str) -> bool:
    """Whether a new module on a sub-field by hand differs from the one there by more than 2 cm in a side: then the
    designer is asked whether to adapt the rows or lay the sub-field again (Daniel, 23/10/2026)."""
    sf = _subfield(project, sfid)
    if not sf.manual or module_id == sf.module:
        return False
    import copy
    other = copy.copy(sf)
    other.module = module_id
    return not same_size(project.module_of(sf), project.module_of(other))


def length_of(row: layout.Row, size: layout.Sizes) -> float:
    """The length of a row from the start of its first place to the end of its last."""
    if not row.places:
        return 0.0
    along = size.across if row.turned else size.along
    return max(row.places) + along - min(row.places)


def end_point(row: layout.Row, size: layout.Sizes) -> tuple[float, float]:
    """The plan point at the end of the row's front edge: the grip that lengthens it."""
    own = layout.row_frame(row.azimuth, size)
    u_o, v0 = own.to_work(row.x, row.y)
    along = size.across if row.turned else size.along
    return own.to_plan(u_o + (row.places[-1] if row.places else 0.0) + along, v0)


# the sub-field as its modules (R445, format 27)

def grid_params(project, sf) -> layout.Params:
    """The parameters of the plain grid a sub-field drawn as modules is made of: no band inside it, rows from its
    front edge on one grid of straight columns (aligned, R418: a row no longer centred on its own room), no
    fire-brigade corridors (the rules are guides and checks there, decision 2), no power asked (laid out of the grid at
    the layout, R417) and no keeping out of the shadows (the designer takes modules out himself)."""
    import dataclasses
    return dataclasses.replace(project.fill_params(sf), edge=0.0, alignment="aligned", target_kwp=0.0,
                               shade_free=False, fire_rules=False)


def grid(project, sf, ring=None) -> list[layout.Row]:
    """The rows of a plain grid of the sub-field's modules filling `ring` (its outline): as many whole modules as
    fit on one grid of columns (R418), a row every pitch from the front. The obstacles are not taken out here: the modules
    on them are set aside at the layout (layout.set_aside), red and rimettibili."""
    ring = [tuple(map(float, q)) for q in (ring if ring is not None else sf.ring)]
    result = layout.compute(ring, project.surface_of(sf), project.module_of(sf), grid_params(project, sf), [],
                            project.site.lat, project.site.lon)
    return [r for r in result.rows if r.places]


def outline(project, sf, rows: list[layout.Row], removed=()) -> list[list[float]]:
    """The outline of a sub-field that is its modules: flush with the outer modules of `rows` (those taken out by
    hand left out), the gaps between modules and rows closed, the corners of a grid kept and the steps of a stepped
    one (decision 1); the hull when the modules stand in parts apart. [] without modules."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    placed = layout.modules_of(rows, project.module_of(sf), project.fill_params(sf), project.surface_of(sf),
                               set(removed))
    if not placed:
        return []
    f, size, _p = frame(project, sf, rows)
    vs = sorted({round(f.to_work(r.x, r.y)[1], 4) for r in rows})
    pitch = min((b - a for a, b in zip(vs, vs[1:], strict=False) if b - a > 1e-6), default=size.depth)
    reach = 0.5 * max(pitch - size.depth, size.gap, 0.0) + 0.002
    union = unary_union([Polygon(m.corners) for m in placed])
    shape = union.buffer(reach, join_style="mitre").buffer(-reach, join_style="mitre").simplify(0.002)
    if shape.geom_type != "Polygon":
        shape = union.convex_hull
    if shape.is_empty or shape.geom_type != "Polygon":
        return []
    return [[round(x, DECIMALS), round(y, DECIMALS)] for x, y in shape.exterior.coords[:-1]]


def make_flush(project, sf) -> None:
    """Make `sf` a sub-field that is its modules, in place: a grid of rows over its outline, by hand from the start,
    the outline brought flush with them. Called inside the change that draws it."""
    sf.flush = True
    sf.removed, sf.kept = [], []
    _store(sf, grid(project, sf), project)


def _fits(zone, u0: float, v0: float, along: float, depth: float) -> bool:
    from shapely.geometry import box
    return zone.covers(box(u0 + 1e-4, v0 + 1e-4, u0 + along - 1e-4, v0 + depth - 1e-4))


def reshape(project, sf, rows: list[layout.Row], ring, removed=(), pitch: float | None = None) -> tuple:
    """The rows of a sub-field that is its modules after its outline became `ring` (R445, phase B): the modules
    stay where they are; the places whose module no longer fits whole inside go, a row left empty goes with them;
    along every row that stays, places are added at its step past either end while a module fits; past the first and
    the last row, rows are added a pitch apart (`pitch` on the plan across the rows, else the rows' own) with the
    places of the row next to them, lengthened the same way. Returns (rows, keys added, keys gone)."""
    from shapely.geometry import Polygon
    f, size, _p = frame(project, sf, rows)
    zone = Polygon([f.to_work(float(x), float(y)) for x, y in ring]).buffer(0).buffer(layout.DISTANCE_TOLERANCE)
    halves = 2 if size.east_west else 1
    depth = size.depth
    gone: list[str] = []
    added: list[str] = []
    kept_rows: list[layout.Row] = []
    for row in rows:
        along = size.across if row.turned else size.along
        u_o, v0 = f.to_work(row.x, row.y)
        places, keys = [], []
        for i, u in enumerate(row.places):
            slots = [row.slot_key(i * halves + h) for h in range(halves)]
            if _fits(zone, u_o + u, v0, along, depth):
                places.append(u)
                keys.extend(slots)
            else:
                gone.extend(slots)
        if places:
            kept_rows.append(layout.Row(row.id, row.x, row.y, row.azimuth, places, keys, row.turned))
    vs = sorted({round(f.to_work(r.x, r.y)[1], 4) for r in rows})
    if pitch is None:
        pitch = min((b - a for a, b in zip(vs, vs[1:], strict=False) if b - a > 1e-6), default=None)
    if pitch is None:
        pitch = project.fill(sf).pitch if sf.manual else depth + size.gap

    def lengthened(row: layout.Row, taken: list[layout.Row]) -> layout.Row:
        along = size.across if row.turned else size.along
        u_o, v0 = f.to_work(row.x, row.y)
        steps = sorted(b - a for a, b in zip(row.places, row.places[1:], strict=False) if b - a > 1e-6)
        step = steps[0] if steps else along + size.gap
        places, keys = list(row.places), [row.slot_key(j) for j in range(row.count * halves)]
        for direction in (1, -1):
            u = (max(places) if direction > 0 else min(places)) + direction * step
            while _fits(zone, u_o + u, v0, along, depth):
                fresh = []
                for _h in range(halves):
                    fresh.append(_fresh_key(taken + [layout.Row(row.id, 0, 0, 0, [], keys + fresh)], removed, row.id))
                added.extend(fresh)
                if direction > 0:
                    places.append(u)
                    keys.extend(fresh)
                else:
                    places.insert(0, u)
                    keys[0:0] = fresh
                u += direction * step
        return layout.Row(row.id, row.x, row.y, row.azimuth, places, keys, row.turned)

    out = []
    for row in kept_rows:
        out.append(lengthened(row, rows + out))
    if not out:
        return out, added, gone
    for direction in (1, -1):
        like = max(out, key=lambda r: f.to_work(r.x, r.y)[1]) if direction > 0 else min(out, key=lambda r: f.to_work(r.x, r.y)[1])
        while True:
            along = size.across if like.turned else size.along
            u_o, v0 = f.to_work(like.x, like.y)
            v = v0 + direction * pitch
            if not zone.intersects(Polygon([(u_o, v), (u_o + 1, v), (u_o + 1, v + depth), (u_o, v + depth)])):
                break
            places = [u for u in like.places if _fits(zone, u_o + u, v, along, depth)]
            if not places:
                break
            first = places[0]
            x, y = f.to_plan(u_o + first, v)
            rid = new_id(rows + out)
            keys = []
            for _u in places:
                for _h in range(halves):
                    keys.append(_fresh_key(rows + out + [layout.Row(rid, 0, 0, 0, [], keys)], removed, rid))
            added.extend(keys)
            new = layout.Row(rid, round(x, DECIMALS), round(y, DECIMALS), like.azimuth, [u - first for u in places],
                             keys, like.turned)
            new = lengthened(new, rows + out)
            out.append(new)
            like = new
    return out, added, gone


def preview_shift(project, sf, side: int, distance: float, result=None) -> dict:
    """What dragging side `side` of a sub-field that is its modules by `distance` metres would do (R445, phase B): the
    outline it would have, the plan corners of the modules that would be added (green ghosts) and taken away (red),
    their numbers. A move that would fold the outline is refused with the reason."""
    from . import sides
    ring = sides.shift(sf.ring, side, distance)
    rows = rows_now(project, sf, result)
    pitch = getattr(result, "pitch", None) if result is not None and not isinstance(result, Exception) else None
    new_rows, added, gone = reshape(project, sf, rows, ring, sf.removed, pitch)
    before = {m.key: m.corners for m in layout.modules_of(rows, project.module_of(sf), project.fill_params(sf),
                                                            project.surface_of(sf), set(sf.removed))}
    after = {m.key: m.corners for m in layout.modules_of(new_rows, project.module_of(sf), project.fill_params(sf),
                                                           project.surface_of(sf), set(sf.removed))}
    add = [after[k] for k in added if k in after]
    remove = [before[k] for k in gone if k in before]
    return {"ring": ring, "rows": new_rows, "add": add, "remove": remove, "added": len(add), "removed": len(remove)}


def reshape_to(project, sfid: str, ring, result=None) -> Callable:
    """The change that gives a sub-field that is its modules the outline `ring` (a vertex dragged or a side written,
    R418): its rows reshaped as for a side (`reshape`: the modules stay where they are, those that no longer fit go,
    new ones come on the same grid) and its outline brought flush with them again; one step of undo."""
    sf = _subfield(project, sfid)
    rows = rows_now(project, sf, result)
    pitch = getattr(result, "pitch", None) if result is not None and not isinstance(result, Exception) else None
    new_rows, _added, _gone = reshape(project, sf, rows, [tuple(map(float, q)) for q in ring], sf.removed, pitch)
    laid = {k for r in new_rows for k in layout.row_keys(r, frame(project, sf, new_rows)[1])} if new_rows else set()

    def change(q):
        target = _subfield(q, sfid)
        if not new_rows:
            raise ValueError(_("no module would be left: the sub-field is its modules"))
        target.removed = [k for k in target.removed if k in laid]
        target.kept = [k for k in target.kept if k in laid]
        _store(target, new_rows, q)
    return change


def shift_side(project, sfid: str, side: int, distance: float, result=None) -> Callable:
    """The change that moves side `side` of a sub-field that is its modules by `distance` metres, its rows reshaped
    (`reshape`) and its outline brought flush with them again; one step of undo."""
    sf = _subfield(project, sfid)
    found = preview_shift(project, sf, side, distance, result)
    rows = found["rows"]
    laid = {k for r in rows for k in layout.row_keys(r, frame(project, sf, rows)[1])} if rows else set()

    def change(q):
        target = _subfield(q, sfid)
        target.removed = [k for k in target.removed if k in laid]
        target.kept = [k for k in target.kept if k in laid]
        if not rows:
            raise ValueError(_("no module would be left: the sub-field is its modules"))
        _store(target, rows, q)
    return change
