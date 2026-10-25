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

from collections.abc import Callable

from . import layout
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


def _shade():
    from .energy import system           # the layout out of the shadows needs them; the model does not load them
    return system.shadow_exclusions


def frame(project, sf, rows: list[layout.Row] | None = None) -> tuple[layout.Frame, layout.Sizes, layout.Params]:
    """The work frame of the sub-field's rows (that of its rows, or the one its automatic layout would take), the
    sizes of a row and the parameters."""
    from shapely.geometry import Polygon
    p = project.fill_params(sf)
    surface = project.surface_of(sf)
    tilt = layout.mount_tilt(surface, p)
    if rows:
        azimuth = rows[0].azimuth
    else:
        area = Polygon([tuple(map(float, q)) for q in sf.ring]).buffer(0)
        azimuth = layout.row_azimuth(area, surface, p)
    return layout.Frame.of(azimuth, tilt, p.mounting in layout.FLUSH), layout.Sizes.of(project.module_of(sf), p, tilt), p


def footprint(project, sf, rows: list[layout.Row]):
    """The plan shape of the modules of `rows` (shapely), as the layout would lay them."""
    from shapely.geometry import MultiPolygon, Polygon
    placed = layout.modules_of(rows, project.module_of(sf), project.fill_params(sf), project.surface_of(sf))
    return MultiPolygon([Polygon(m.corners) for m in placed]) if placed else MultiPolygon()


def corners(project, sf, rows: list[layout.Row]) -> list:
    """The plan corners of each module of `rows`: what the plan draws while a row is drawn or moved."""
    placed = layout.modules_of(rows, project.module_of(sf), project.fill_params(sf), project.surface_of(sf))
    return [m.corners for m in placed]


def trouble(project, sf, rows: list[layout.Row]) -> bool:
    """Whether the modules of `rows` go out of the area the layout would use (the sub-field less its edge band) or
    onto an exclusion with its clearance: the row drawn red (PV*SOL), kept all the same."""
    from shapely.geometry import Polygon
    shape = footprint(project, sf, rows)
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


def _store(sf, rows: list[layout.Row]) -> None:
    sf.rows = [r.as_dict() for r in rows]
    sf.manual = True
    sf.filled = True


def take(project, sfid: str, result=None) -> Callable:
    """The change that makes a sub-field by hand, with the rows of its layout (`result`); nothing if it is already."""
    sf = _subfield(project, sfid)
    rows = None if sf.manual else [r for r in rows_now(project, sf, result) if r.places]

    def change(p):
        sf = _subfield(p, sfid)
        if not sf.manual:
            _store(sf, rows or [])
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


def line_row(project, sf, start, end, rows: list[layout.Row], rid: str | None = None) -> layout.Row:
    """The row from `start` to `end` (plan points): its front edge starts at `start` and runs along the sub-field's
    rows as far as the projection of `end` (the side the pointer is), with the module, the gap, the tables and the
    orientation of the sub-field (study 16, C.6: the row takes the sub-field's)."""
    f, size, p = frame(project, sf, rows)
    us, vs = f.to_work(float(start[0]), float(start[1]))
    ue, _ve = f.to_work(float(end[0]), float(end[1]))
    length = abs(ue - us)
    places = places_along(length, size, p)
    span = places[-1] + size.along
    u0 = us if ue >= us else us - span
    x, y = f.to_plan(u0, vs)
    return layout.Row(rid or new_id(rows), x, y, f.azimuth, places)


def draw(project, sfid: str, start, end, result=None) -> Callable:
    """The change that adds the row drawn from `start` to `end` to the sub-field, which becomes (or stays) by hand
    and laid; the change gives the new row's id."""
    sf = _subfield(project, sfid)
    rows = _hand(project, sfid, result) if sf.filled or sf.manual else []
    row = line_row(project, sf, start, end, rows)

    def change(p):
        target = _subfield(p, sfid)
        _store(target, rows + [row])
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
        _store(sf, [r for r in rows if r.id != rid])
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
    own = layout.Frame.of(like.azimuth, size.tilt, size.flush)       # the frame of the row it is like
    u0, _v = own.to_work(like.x, like.y)
    back = max(own.to_work(r.x, r.y)[1] for r in rows if abs(r.azimuth - like.azimuth) < 1e-6)
    x, y = own.to_plan(u0, back + pitch)
    row = layout.Row(new_id(rows), x, y, like.azimuth, list(like.places), turned=like.turned)

    def change(q):
        _store(_subfield(q, sfid), rows + [row])
        return row.id
    return change


def resize(project, sfid: str, rid: str, point, result=None) -> Callable:
    """«Shorten or lengthen»: the end of the row dragged to `point`; its places as far as the point reaches along
    it, at least one; added places take the row's last step (the module and the gap for a row of one)."""
    sf = _subfield(project, sfid)
    rows = _hand(project, sfid, result)
    row = _row(rows, rid)
    f, size, p = frame(project, sf, rows)
    own = layout.Frame.of(row.azimuth, size.tilt, size.flush)
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
        _store(_subfield(q, sfid), [new if r.id == rid else r for r in rows])
    return change


def explode(project, sfid: str, rid: str | None = None, result=None) -> Callable:
    """«Explode»: each place of the row (of every row with `rid` None) becomes a row of one place where it was, with
    the keys its modules had: the strings and the modules taken out stay on them. The change gives the new ids."""
    sf = _subfield(project, sfid)
    rows = _hand(project, sfid, result)
    if rid is not None:
        _row(rows, rid)
    f, size, _p = frame(project, sf, rows)
    halves = 2 if size.east_west else 1
    out: list[layout.Row] = []
    made: list[str] = []
    number = int(new_id(rows)[1:])           # the ids of the new rows, past every row's and key's
    for row in rows:
        if (rid is not None and row.id != rid) or row.count <= 1:
            out.append(row)
            continue
        own = layout.Frame.of(row.azimuth, size.tilt, size.flush)
        u_o, v0 = own.to_work(row.x, row.y)
        for i, u in enumerate(row.places):
            x, y = own.to_plan(u_o + u, v0)
            one = layout.Row(f"f{number}", x, y, row.azimuth, [0.0],
                             [row.slot_key(i * halves + h) for h in range(halves)], row.turned)
            number += 1
            out.append(one)
            made.append(one.id)

    def change(q):
        _store(_subfield(q, sfid), out)
        return made
    return change


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
    own = layout.Frame.of(row.azimuth, size.tilt, size.flush)
    u_o, v0 = own.to_work(row.x, row.y)
    cu, cv = u_o + before.along / 2, v0 + before.depth / 2
    x, y = own.to_plan(cu - after.along / 2, cv - after.depth / 2)
    new = layout.Row(row.id, x, y, row.azimuth, [0.0], list(row.keys), not row.turned)

    def change(q):
        _store(_subfield(q, sfid), [new if r.id == rid else r for r in rows])
    return change


def _outside(project, sf, rows) -> float:
    from shapely.geometry import Polygon
    shape = footprint(project, sf, rows)
    area = Polygon([tuple(map(float, q)) for q in sf.ring]).buffer(0)
    return float(shape.difference(area).area) if not shape.is_empty else 0.0


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
        _store(_subfield(q, sfid), [new if r.id == rid else r for r in rows])
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
    return change


def relayout(project, sfid: str) -> Callable:
    """«Lay again automatically»: the rows by hand go, and the modules taken out by hand with them; the generator
    lays the sub-field again from its parameters."""
    _subfield(project, sfid)

    def change(p):
        sf = _subfield(p, sfid)
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
    own = layout.Frame.of(row.azimuth, size.tilt, size.flush)
    u_o, v0 = own.to_work(row.x, row.y)
    along = size.across if row.turned else size.along
    return own.to_plan(u_o + (row.places[-1] if row.places else 0.0) + along, v0)
