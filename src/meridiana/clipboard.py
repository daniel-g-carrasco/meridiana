"""Copy, cut and paste of a sub-field, a building, an exclusion or a 3D object (R432). No Qt: the plan collects the
gestures, the session applies the change.

What is taken is a copy of the object, with what belongs to it: a sub-field with the parts of its split (R426), a
building with what stands on it. A paste has its centre at the point given and new ids.

A sub-field takes the pitch, the tilt and the azimuth of where it falls, by the same rule as a move (move.py, R426:
the pitch that holds most of its area): the module and the mounting stay, unless that mounting cannot stand there, and
the modules are laid again on the new plane. One that falls half off a roof is refused with the reason: nothing is
pasted in silence. Strings are not copied: the modules pasted are in no string, and the checks of the Plant say so.

`cut` also takes the strings' references to what goes. Paste after a cut joins the cut in one undo step in the plan."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from . import layout, model, move
from .i18n import _

LEVEL_ROOF = ("tilted_anchored", "tilted_ballasted", "east_west")
ON_GROUND = ("ground", "east_west")


@dataclass
class Clip:
    kind: str                       # "subfield", "building", "exclusion", "prop"
    subfields: list = field(default_factory=list)
    building: object = None
    exclusions: list = field(default_factory=list)
    props: list = field(default_factory=list)
    modules: dict = field(default_factory=dict)     # the modules its sub-fields use, for a project without them
    centre: tuple = (0.0, 0.0)
    source: tuple = ("", "")        # (kind, id) as it was taken
    cut_step: object = None         # the undo step of the cut, until a paste joins it


def take(project, kind: str, oid: str) -> Clip:
    """A copy of the object, for later; ValueError for what cannot be taken."""
    clip = Clip(kind, source=(kind, oid))
    if kind == "subfield":
        clip.subfields = copy.deepcopy(move._group_of(project, oid))
        if not clip.subfields:
            raise ValueError(_("there is no such object to move"))
    elif kind == "building":
        b = project.building(oid)
        if b is None:
            raise ValueError(_("there is no such object to move"))
        clip.building = copy.deepcopy(b)
        clip.subfields = copy.deepcopy([s for s in project.subfields if s.building == oid])
        clip.exclusions = copy.deepcopy([e for e in project.exclusions if e.building == oid])
        clip.props = copy.deepcopy([x for x in project.props if x.building == oid])
    elif kind == "exclusion":
        clip.exclusions = copy.deepcopy([e for e in project.exclusions if e.id == oid])
        if not clip.exclusions:
            raise ValueError(_("there is no such object to move"))
    elif kind == "prop":
        clip.props = copy.deepcopy([x for x in project.props if x.id == oid])
        if not clip.props:
            raise ValueError(_("there is no such object to move"))
    else:
        raise ValueError(_("Select a sub-field, a building, an exclusion or a 3D object first."))
    clip.modules = {s.module: copy.deepcopy(project.modules[s.module]) for s in clip.subfields
                    if s.module in project.modules}
    clip.centre = move.centre_of(_own_rings(clip))
    return clip


def _own_rings(clip: Clip) -> list:
    """The outlines that give the centre: the object itself, not what stands on it."""
    if clip.kind == "subfield":
        return [s.ring for s in clip.subfields]
    if clip.kind == "building":
        return [clip.building.footprint]
    if clip.kind == "exclusion":
        return [e.ring for e in clip.exclusions]
    return [x.footprint() for x in clip.props]


def rings(clip: Clip, point) -> list[list[list[float]]]:
    """The outlines of what would be pasted with its centre at `point`, the object's first."""
    f = move.shift(float(point[0]) - clip.centre[0], float(point[1]) - clip.centre[1])
    out = [move.moved(ring, f) for ring in _own_rings(clip)]
    if clip.kind == "building":
        out += [move.moved(x.ring, f) for x in (*clip.subfields, *clip.exclusions)]
        out += [move.moved(x.footprint(), f) for x in clip.props]
    return out


def _landing(project, ring):
    """Where an outline falls: (building or None for the ground, place in its pitches() or None, why it cannot stand
    there or "")."""
    from shapely.ops import unary_union
    from .i18n import number
    shape = move._polygon(ring)
    best, roof, most = None, None, move.OUTSIDE_TOLERANCE
    for b in project.buildings:
        top = unary_union([move._polygon(b.footprint), *(move._polygon(p.ring) for p in b.pitches())])
        on = float(shape.intersection(top).area)
        if on > most:
            best, roof, most = b, top, on
    if best is None:
        return None, None, ""
    off = float(shape.difference(roof).area)
    if off > move.OUTSIDE_TOLERANCE:
        return best, None, _("it does not fit on {name}: {area} m² would stand off its roof").format(
            name=best.name, area=number(off, 1))
    return best, move._largest_pitch(best, ring), ""


def refused(project, clip: Clip, point) -> str:
    """Why it cannot be pasted at `point`, or "". Only a sub-field has a plane to find: the others stand anywhere."""
    if clip.kind != "subfield":
        return ""
    for ring in rings(clip, point):
        why = _landing(project, ring)[2]
        if why:
            return why
    return ""


def where(project, clip: Clip, point) -> str:
    """Where a sub-field would fall, in a few words, for the hint and for the note of a paste."""
    if clip.kind != "subfield":
        return ""
    b, index, why = _landing(project, rings(clip, point)[0])
    if why:
        return why
    return _("on the ground") if b is None else _("on {name}, pitch {n}").format(name=b.name, n=(index or 0) + 1)


def _fit_mounting(params: dict, tilt: float | None) -> None:
    """The mounting of a sub-field stays when it can stand on where it fell (`tilt`: None on the ground)."""
    mounting = params.get("mounting", layout.Params().mounting)
    if tilt is None:
        fit = mounting if mounting in ON_GROUND else "ground"
    elif tilt > 0:
        fit = mounting if mounting in layout.FLUSH else "coplanar"
    else:
        fit = mounting if mounting in LEVEL_ROOF else "tilted_anchored"
    if fit != mounting:
        params["mounting"] = fit


def _fresh_name(taken: set, name: str) -> str:
    return _("{name} (copy)").format(name=name) if name in taken else name


def _paste_subfields(p, clip: Clip, f, parts: list) -> list[str]:
    """Each part with a new id, on where it falls, its modules to lay again."""
    made = []
    names = {s.name for s in p.subfields}
    for module, spec in clip.modules.items():
        p.modules.setdefault(module, copy.deepcopy(spec))
    for source in parts:
        sf = copy.deepcopy(source)
        sf.id = p.new_id("s")
        sf.ring = move.moved(source.ring, f)
        sf.name = _fresh_name(names, source.name)
        sf.support, sf.manual, sf.rows, sf.removed = None, False, [], []
        sf.params = {k: v for k, v in sf.params.items() if k not in model.ELECTRICAL}
        b, index, why = _landing(p, sf.ring)
        if why:
            raise ValueError(why)
        sf.building = b.id if b is not None else None
        sf.pitch = b.pitch_ref(index if index is not None else 0) if b is not None else None
        _fit_mounting(sf.params, b.pitches()[index or 0].tilt if b is not None else None)
        p.subfields.append(sf)
        made.append(sf.id)
    group = made[0] if len(made) > 1 else ""
    for sf in p.subfields[-len(made):]:
        sf.group = group
    return made


def _paste_building(p, clip: Clip, f) -> str:
    """The building with what stands on it, as it is: same roof, so its rows by hand stay, in no string."""
    b = copy.deepcopy(clip.building)
    b.id = p.new_id("b")
    b.name = _fresh_name({x.name for x in p.buildings}, b.name)
    p.buildings.append(b)
    for source in clip.subfields:
        sf = copy.deepcopy(source)
        sf.id, sf.building, sf.group = p.new_id("s"), b.id, ""
        sf.params = {k: v for k, v in sf.params.items() if k not in model.ELECTRICAL}
        p.subfields.append(sf)
    for module, spec in clip.modules.items():
        p.modules.setdefault(module, copy.deepcopy(spec))
    for source in clip.exclusions:
        e = copy.deepcopy(source)
        e.id, e.building = p.new_id("e"), b.id
        p.exclusions.append(e)
    for source in clip.props:
        x = copy.deepcopy(source)
        x.id, x.building = p.new_id("o"), b.id
        p.props.append(x)
    move._apply(p, "building", b.id, f, 0.0)
    return b.id


def paste(project, clip: Clip, point):
    """The change that pastes the clip with its centre at `point`; it gives the new ids, the object's first."""
    why = refused(project, clip, point)
    if why:
        raise ValueError(why)
    f = move.shift(float(point[0]) - clip.centre[0], float(point[1]) - clip.centre[1])

    def change(p):
        if clip.kind == "subfield":
            return _paste_subfields(p, clip, f, clip.subfields)
        if clip.kind == "building":
            return [_paste_building(p, clip, f)]
        if clip.kind == "exclusion":
            e = copy.deepcopy(clip.exclusions[0])
            e.id = p.new_id("e")
            p.exclusions.append(e)
            move._apply(p, "exclusion", e.id, f, 0.0)
            return [e.id]
        x = copy.deepcopy(clip.props[0])
        x.id = p.new_id("o")
        p.props.append(x)
        move._apply(p, "prop", x.id, f, 0.0)
        return [x.id]
    return change


def drop(p, kind: str, oid: str) -> None:
    """An object off the project, with what stands on a building."""
    if kind == "building":
        p.buildings = [b for b in p.buildings if b.id != oid]
        p.subfields = [s for s in p.subfields if s.building != oid]
        p.exclusions = [e for e in p.exclusions if e.building != oid]
        p.props = [x for x in p.props if x.building != oid]
    else:
        attr = {"subfield": "subfields", "exclusion": "exclusions", "prop": "props"}.get(kind)
        if attr:
            setattr(p, attr, [x for x in getattr(p, attr) if x.id != oid])


def cut(clip: Clip):
    """The change that takes off the project what the clip holds, and the strings' references to it."""
    def change(p):
        gone = {s.id for s in clip.subfields}
        if clip.kind == "subfield":
            for sf in clip.subfields:
                drop(p, "subfield", sf.id)
        else:
            drop(p, *clip.source)
        strings = p.energy.get("strings")
        if gone and strings and strings.get("runs"):
            runs = [{**r, "modules": [m for m in r.get("modules", []) if m.partition("/")[0] not in gone]}
                    for r in strings["runs"]]
            if runs != strings["runs"]:
                from .energy import plant
                p.energy["strings"] = plant.touched(strings, runs)
    return change
