"""The corners of a roof, one by one (R303), without Qt: which ones there are, their height written or dragged, two of them
made one point and parted again. The 3D view shows them and passes the gestures; every change is a function here that
the window applies as one step of the undo.

A corner is `[pitch, place in its ring]`. Corners at one plan point of a joined roof go together, one handle for all,
unless parted; corners made to coincide (Roof.welds) go together on any roof and stay so: in the file, through every
new model of the roof, until they are parted. Parting them (Roof.detached) leaves them where they are, each free to go
its own way; two handles then stand on one point, and a click on them passes from one to the other.

A flat roof moved by one corner tilts (R411, in place of R357): that corner goes where it is taken, the one opposite stays,
the others rise as little as one plane allows, and the roof remains one plane and remains flat (R455, Roof.plane, format
28): not a pitched roof, the building's height its lowest corner. All its corners taken together at one height are the
building's height again, the plane gone, and what stands on it follows. A roof of another type (mono-pitch, gable, hip) becomes a roof drawn by hand at the first corner moved (to_manual): its faces become
free pitches, the same planes in the same places, the sub-fields following; undo takes it back. A canopy has no corners
to move: its roof is its structure's (canopies.py).

A height moved takes the pitches of that corner to the heights of their corners ("z", roof_join.py); those off one plane
are folded there, along a diagonal. The obstacles (an exclusion with a height) stay prisms: a corner dragged moves
their whole top.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from shapely.geometry import Polygon

from . import roof_join
from .i18n import _

GROUND = 0.0            # m: no corner goes under the ground
LIMIT = 1000.0          # m: as the file's heights (model.HEIGHT_LIMIT)
OBSTACLE = -1           # the "pitch" of a corner of an obstacle
BASE = -2               # the "pitch" of a corner of the base of a body (r20-solidi: Building.base)


@dataclass(frozen=True)
class Handle:
    """One point that can be taken: the corners that go together, where they stand (plan and height)."""
    corners: tuple
    x: float
    y: float
    z: float

    @property
    def obstacle(self) -> bool:
        return self.corners[0][0] == OBSTACLE

    @property
    def base(self) -> bool:
        return self.corners[0][0] == BASE


def parse_height(text: str) -> tuple[float, bool] | None:
    """What is written in the field of a corner: (value, relative). With a sign (+5, -10) it moves the corner up or
    down; without, it is the height above the ground. The comma or the point; None when it is not a number."""
    t = text.strip().replace(",", ".").replace("−", "-")
    relative = t[:1] in ("+", "-")
    try:
        value = float(t)
    except ValueError:
        return None
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return value, relative


def height_written(current: float, written: tuple[float, bool]) -> float:
    value, relative = written
    return current + value if relative else value


def _corners_of(b) -> list[list[tuple[float, float, float]]]:
    """For each pitch, (x, y, z) at each corner: of the free pitches as the file has them, of the faces otherwise."""
    if b.roof.type == "free":
        solved = b.solved()
        return [[(float(q[0]), float(q[1]), z) for q, z in zip(f["ring"], heights, strict=True)]
                for f, heights in zip(b.roof.free_pitches, solved.heights, strict=True)]
    return [list(p.corners_3d()) for p in b.pitches()]


def _groups(b, corners) -> list[list[tuple[int, int]]]:
    """The corners that go together: welded on any roof; on a joined one (a generated roof is one too), at one plan
    point unless parted. In the order of the pitches."""
    slots = [(i, j) for i, ring in enumerate(corners) for j in range(len(ring))]
    root = {s: s for s in slots}

    def find(s):
        while root[s] != s:
            root[s] = root[root[s]]
            s = root[s]
        return s

    joined = b.roof.type != "free" or b.roof.joined
    apart = {tuple(c) for c in b.roof.detached}
    if joined:
        for k, s in enumerate(slots):
            if s in apart:
                continue
            xs = corners[s[0]][s[1]]
            for t in slots[k + 1:]:
                if t not in apart and t[0] != s[0]:
                    xt = corners[t[0]][t[1]]
                    if abs(xs[0] - xt[0]) <= roof_join.TOUCH and abs(xs[1] - xt[1]) <= roof_join.TOUCH:
                        root[find(t)] = find(s)
    for weld in b.roof.welds:
        members = [tuple(c) for c in weld if tuple(c) in root]
        for other in members[1:]:
            root[find(other)] = find(members[0])
    out: dict = {}
    for s in slots:
        out.setdefault(find(s), []).append(s)
    return list(out.values())


def handles(b) -> list[Handle]:
    """The handles of a building's roof; none on a canopy."""
    if b.canopy is not None:
        return []
    corners = _corners_of(b)
    out = []
    for group in _groups(b, corners):
        points = [corners[i][j] for i, j in group]
        out.append(Handle(tuple(group), points[0][0], points[0][1], sum(q[2] for q in points) / len(points)))
    return out


def obstacle_handles(project, oid: str) -> list[Handle]:
    """The corners of the top of an obstacle (an exclusion that rises), each moves its whole top."""
    found = next((o for o in project.obstacle_prisms() if o.get("id") == oid and o.get("kind") != "parapet"), None)
    if found is None:
        return []
    return [Handle(((OBSTACLE, j),), x, y, float(found["z1"])) for j, (x, y) in enumerate(found["ring"])]


def base_handles(project, b) -> list[Handle]:
    """The corners of the base of a body (r20-solidi): each takes the whole base up or down, the walls start there.
    Only on a body that does not simply stand on the ground: one raised, one on another building, one part of a
    building or a building with parts; the others change their base in the Properties."""
    if b.canopy is not None or not (b.base > 0 or b.on or b.part_of or project.parts_of(b.id)):
        return []
    return [Handle(((BASE, j),), float(x), float(y), float(b.base)) for j, (x, y) in enumerate(b.footprint)]


def set_base(project, bid: str, z: float) -> None:
    """The base of body `bid` at height `z` above the ground: its walls start there, its heights stay where they
    are (measured from the ground). Refused under the ground or above its roof."""
    b = project.building(bid)
    if b is None:
        raise ValueError(_("there is no such object"))
    if z < GROUND:
        raise ValueError(_("the base stands on the ground or above it"))
    if z >= b.wall_top() - 0.1:
        raise ValueError(_("the base must stand under the roof ({h} m)").format(h=round(b.wall_top(), 2)))
    b.base = round(float(z), 3)


def handles_of(project, kind: str, oid: str) -> list[Handle]:
    """The handles of what is selected: a building, one of its pitches, an obstacle; else none. A body has those of
    its base after those of its roof."""
    if kind == "exclusion":
        return obstacle_handles(project, oid)
    bid = oid.partition(":")[0] if kind == "pitch" else oid
    b = project.building(bid) if kind in ("building", "pitch") else None
    return handles(b) + base_handles(project, b) if b is not None else []


def owner_of(kind: str, oid: str) -> str:
    """The building or obstacle a selection's handles belong to."""
    return oid.partition(":")[0] if kind == "pitch" else oid


def set_obstacle_height(project, oid: str, z: float) -> None:
    """The top of an obstacle brought to height `z`: its height above what it stands on (never under it)."""
    e = next((x for x in project.exclusions if x.id == oid), None)
    found = next((o for o in project.obstacle_prisms() if o.get("id") == oid and o.get("kind") != "parapet"), None)
    if e is None or found is None:
        raise ValueError(_("there is no such object"))
    e.height = round(max(0.0, z - (float(found["z1"]) - e.obstacle_height())), 3)


def _lowest_side(ring, heights) -> tuple[int | None, float]:
    """The level side at the lowest height of a ring: (its place, the height); no such side: (None, lowest)."""
    low = min(heights)
    n = len(ring)
    for i in range(n):
        if abs(heights[i] - low) < 1e-6 and abs(heights[(i + 1) % n] - low) < 1e-6:
            return i, low
    return None, low


def to_manual(project, b) -> bool:
    """A generated roof as free pitches: the same planes in the same places, the sub-fields on their pitch whichever way
    it was named. Whether it changed anything."""
    if b.roof.type == "free":
        return False
    if b.canopy is not None:
        raise ValueError(_("a canopy's roof follows its structure: change it in its properties"))
    found = b.pitches()
    free = []
    for i, p in enumerate(found):
        ring = [[float(x), float(y)] for x, y in p.ring]
        heights = [z for _x, _y, z in p.corners_3d()]
        side, low = _lowest_side(p.ring, heights)
        spec = {"id": f"p{i + 1}", "ring": ring, "eave_side": side or 0, "eave": float(low), "tilt": float(p.tilt)}
        if side is None and p.tilt > 0:
            spec["z"] = [float(z) for z in heights]
        free.append(spec)
    was_pitched = b.roof.type in ("gable", "hip")
    if was_pitched:                 # a sub-field names its pitch by its eave's side there, by its place here
        for sf in project.subfields:
            if sf.building == b.id:
                sf.pitch = b.pitch_index(sf.pitch)
        for v in project.variants:
            design = v.get("design")
            if isinstance(design, dict):
                for raw in design.get("subfields") or []:
                    if isinstance(raw, dict) and raw.get("building") == b.id:
                        raw["pitch"] = b.pitch_index(raw.get("pitch"))
    b.roof.type = "free"
    b.roof.free_pitches = free
    b.roof.joined, b.roof.welds, b.roof.detached = True, [], []
    return True


def _freeze(b, pitches) -> None:
    """Those pitches from here on by the heights of their corners, as they stand now."""
    solved = b.solved()
    for i in pitches:
        fp = b.roof.free_pitches[i]
        if fp.get("z") is None:
            fp["z"] = [round(float(z), 4) for z in solved.heights[i]]


def _settle(b, pitches) -> None:
    """The eave and the slope of a pitch by its corners follow them: what its fields show is what it is."""
    solved = b.solved()
    for i in pitches:
        fp = b.roof.free_pitches[i]
        heights = solved.heights[i]
        side, low = _lowest_side(fp["ring"], heights)
        fp["eave"] = round(float(low), 3)
        fp["tilt"] = round(float(solved.pitches[i].tilt), 3)
        if side is not None:
            fp["eave_side"] = side


def settled(b, pitches) -> None:
    """Free pitches just written by the heights of their corners: their fields say what they are."""
    _settle(b, list(pitches))


def _group_of(b, corner) -> list[tuple[int, int]]:
    corner = tuple(corner)
    for group in _groups(b, _corners_of(b)):
        if corner in group:
            return group
    raise ValueError(_("there is no such corner"))


def stays_flat(b) -> bool:
    """A flat roof, not a canopy's: all its corners together are the building's height, one alone tilts it (R411)."""
    return b.roof.type == "flat" and b.canopy is None


def _plane_through(ring, moved: dict, base) -> list[float]:
    """The heights of a flat roof's corners on the plane that takes the `moved` ones (place: height) where asked. One
    corner alone keeps the farthest from it where it is; the others stay as near to where they are (`base`: one height,
    or one for each corner) as the plane lets them: on a level rectangle the two beside it rise by half (Daniel,
    05/11/2026)."""
    points = np.asarray(ring, float)[:, :2]
    now = [float(base)] * len(points) if np.isscalar(base) else [float(z) for z in base]
    fixed = dict(moved)
    if len(moved) == 1:
        place = next(iter(moved))
        far = int(np.argmax(np.hypot(*(points - points[place]).T)))
        fixed[far] = now[far]
    origin = points.mean(0)
    rows, values = [], []
    for j, (x, y) in enumerate(points):
        weight = 1e4 if j in fixed else 1.0     # hard where it is written, the least change elsewhere
        rows.append([weight*(x - origin[0]), weight*(y - origin[1]), weight])
        values.append(weight*fixed.get(j, now[j]))
    a, b, c = np.linalg.lstsq(np.asarray(rows), np.asarray(values), rcond=None)[0]
    return [float(a*(x - origin[0]) + b*(y - origin[1]) + c) for x, y in points]


def _move_flat(project, b, moves) -> None:
    """Corners of a flat roof: all of them at one height, the building's height, the roof level; fewer, the roof tilted
    on one plane and still flat (R455: Roof.plane), the building's height its lowest corner."""
    ring = b.pitches()[0].ring
    moved = {tuple(corner)[1]: float(z) for corner, z in moves}
    if len(moved) == len(ring) and len(set(moved.values())) == 1:
        b.height = round(next(iter(moved.values())), 3)
        b.roof.plane = None
        return
    now = b.plane() or [float(b.height)] * len(ring)
    heights = _plane_through(ring, moved, now)
    if min(heights) < GROUND:
        raise ValueError(_("a corner stands between the ground and {limit} m").format(limit=int(LIMIT)))
    if min(heights) <= b.base:
        raise ValueError(_("a corner would stand under the base of the walls ({h} m)").format(h=round(b.base, 2)))
    level = max(heights) - min(heights) < 1e-3
    b.roof.plane = None if level else [round(z, 3) for z in heights]
    b.height = round(min(heights), 3)


def set_height(project, bid: str, corner, z: float) -> None:
    """The corner, and those that go with it, at height `z`; a flat roof tilts on one plane (R411).
    ValueError, said for the designer, under the ground."""
    if corner[0] == BASE:
        set_base(project, bid, z)
        return
    if not GROUND <= z <= LIMIT:
        raise ValueError(_("a corner stands between the ground and {limit} m").format(limit=int(LIMIT)))
    b = project.building(bid)
    if b is None:
        raise ValueError(_("there is no such object"))
    if stays_flat(b):
        _move_flat(project, b, [(corner, z)])
        return
    to_manual(project, b)
    group = _group_of(b, corner)
    touched = sorted({i for i, _j in group})
    _freeze(b, touched)
    for i, j in group:
        b.roof.free_pitches[i]["z"][j] = round(float(z), 3)
    _settle(b, touched)


def set_heights(project, bid: str, moves) -> None:
    """Several corners, (corner, z) each, as one change (R356). The first refused refuses them all: session.edit puts the
    project back. The base of a body (BASE) goes with the first of its corners."""
    based = [(corner, z) for corner, z in moves if corner[0] == BASE]
    if based:
        set_base(project, bid, based[0][1])
        moves = [(corner, z) for corner, z in moves if corner[0] != BASE]
    b = project.building(bid)
    if b is not None and stays_flat(b) and moves:
        for _corner, z in moves:
            if not GROUND <= z <= LIMIT:
                raise ValueError(_("a corner stands between the ground and {limit} m").format(limit=int(LIMIT)))
        _move_flat(project, b, moves)
        return
    for corner, z in moves:
        set_height(project, bid, corner, z)


def folded(b, corner) -> bool:
    """Whether a pitch of this corner is folded (roof_join.Fold): its heights keep it off one plane."""
    solved = b.solved() if b.roof.type == "free" and corner[0] != BASE else None
    if solved is None:
        return False
    pitches = {i for i, _j in _group_of(b, corner)}
    return any(f.pitch in pitches for f in solved.folds)


def unfold(project, bid: str, corner) -> None:
    """The folded pitches of this corner back on one plane, the slope and the eave they had settled on (R354): corners
    no more written one by one."""
    b = project.building(bid)
    if b is None or b.roof.type != "free":
        raise ValueError(_("there is no such object"))
    bent = {f.pitch for f in b.solved().folds}
    for i in sorted({i for i, _j in _group_of(b, corner)} & bent):
        b.roof.free_pitches[i].pop("z", None)


def weld(project, bid: str, corner_a, corner_b) -> None:
    """Corner b, with those that go with it, brought onto corner a, in plan and in height, and kept there."""
    b = project.building(bid)
    if b is None:
        raise ValueError(_("there is no such object"))
    if BASE in (corner_a[0], corner_b[0]):
        raise ValueError(_("a corner of the base goes with the whole base: it cannot be made one with another"))
    to_manual(project, b)
    one, two = _group_of(b, corner_a), _group_of(b, corner_b)
    if one == two and len(one) > 1 and any(sorted(map(list, one)) == sorted(map(list, w)) for w in b.roof.welds):
        return
    together = sorted(set(one) | set(two))
    if len(together) < 2:
        raise ValueError(_("choose another corner"))
    if len({i for i, _j in together}) < len(together):
        raise ValueError(_("two corners of one pitch cannot be one point"))
    touched = sorted({i for i, _j in together})
    _freeze(b, touched)
    i0, j0 = tuple(corner_a)
    fp0 = b.roof.free_pitches[i0]
    x, y, z = float(fp0["ring"][j0][0]), float(fp0["ring"][j0][1]), float(fp0["z"][j0])
    for i, j in together:
        fp = b.roof.free_pitches[i]
        fp["ring"] = [list(q) for q in fp["ring"]]
        fp["ring"][j] = [x, y]
        fp["z"][j] = z
        shape = Polygon(fp["ring"])
        if not shape.is_valid or shape.area < 0.01:
            raise ValueError(_("pitch {n} would cross itself: these corners cannot be one point").format(n=i + 1))
    gone = {tuple(c) for w in b.roof.welds for c in w if tuple(c) in together}
    b.roof.welds = [w for w in b.roof.welds if not any(tuple(c) in gone for c in w)]
    b.roof.welds.append([list(c) for c in together])
    b.roof.detached = [c for c in b.roof.detached if tuple(c) not in together]
    _settle(b, touched)


def detach(project, bid: str, corner) -> None:
    """The corners that go with this one parted: they stay where they are, each free from here on. ValueError when it is
    alone already."""
    b = project.building(bid)
    if b is None:
        raise ValueError(_("there is no such object"))
    if corner[0] == BASE:
        raise ValueError(_("this corner is on its own already"))
    to_manual(project, b)
    group = _group_of(b, corner)
    if len(group) < 2:
        raise ValueError(_("this corner is on its own already"))
    _freeze(b, sorted({i for i, _j in group}))
    members = {tuple(c) for c in group}
    b.roof.welds = [w for w in b.roof.welds if not any(tuple(c) in members for c in w)]
    b.roof.detached = sorted([list(c) for c in members] + [c for c in b.roof.detached if tuple(c) not in members])


def can_detach(corners) -> bool:
    return len(corners) > 1 and corners[0][0] != BASE


def forget_pitch_corners(b, index: int) -> None:
    """A free pitch moved on its own: its corners leave what they were welded to or parted from."""
    b.roof.welds = [kept for w in b.roof.welds
                    if len(kept := [c for c in w if c[0] != index]) >= 2]
    b.roof.detached = [c for c in b.roof.detached if c[0] != index]


def fold_news(before, after) -> list:
    """The folds of `after` that `before` did not have: what to tell the designer (roof_join.Fold)."""
    had = {f.pitch for f in (before.folds if before is not None else [])}
    return [f for f in (after.folds if after is not None else []) if f.pitch not in had]
