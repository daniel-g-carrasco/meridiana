"""What an import made, read back from the project as it is saved (R604, R605): the bodies of one imported model
gathered as one thing, and the short names of what the import created. No Qt. All of it comes from what the import
writes (`Building.group`, `Building.part_of`, the sub-fields' saved names, `Project.resources["ifc_reference"]`), so a
project imported before this module reads the same way; the one field of its own is the name the designer gives a
model (`Project.model_names`, format 33).

The one place for both questions:
- `models(project)`: one `Model` for each import of several bodies, with its name, the bodies shown in its node of
  the project's tree and the ones gathered in one row;
- `namer(project)`: the name shown for a sub-field the import made. The import saves «<the file with its whole
  path>: #<the element's number>», the same text for every plane read from one element; shown it is «<model> ·
  surface <n>», short and different for each. The saved name stays in the project (the properties show it), and a
  sub-field the designer renamed is shown with his name.

The bodies shown in a model's node (R604, the rule chosen on 14/11/2026 on 14 real models, study 49 chapter 10): a
body holding a sub-field of the designer's (drawn, renamed or laid by him; a plane the import offered and nobody
touched does not count), or one on whose roof at least ROOF_LEAST modules of the project fit. The others are
gathered in «Other bodies». What fits is `fitting`: FIT_SHARE of the room where a module fits lengthwise, once the
edge band and the obstacles are taken off, over the module's area.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from meridiana.i18n import _

ROOF_LEAST = 7                  # modules of the project: about 3 kWp at 450 W, the smallest plant worth a roof; a
#                                 body where fewer fit (a stair tower, a lantern, a canopy) is gathered with the others
FIT_SHARE = 0.6                 # of the room where a module fits lengthwise, what a layout takes (the gaps between
#                                 the rows on a flat roof, the band of the rules): on 14 real models «Fill» laid 0,51-0,56
#                                 of it (median by kind of roof), 0,81 on gable roofs; 0,6 hid no body where 7 modules
#                                 are laid, 0,4 hid three (study 49, chapter 10)
OTHERS_LEAST = 2                # fewer bodies than this are not worth a row of their own: they are shown as they are

_NUMBERED = re.compile(r"^(?P<stem>.*\S)\s+(?P<n>\d+)$")
_IFC_FILE = re.compile(r"\.ifc(?:zip|xml)?$", re.IGNORECASE)


@dataclass(frozen=True)
class Model:
    """One imported model of several bodies."""
    key: str                    # Building.group, the same on all its bodies
    name: str
    file: str                   # the file it came from as the project keeps it, "" when it is not known
    bodies: tuple               # the ids of all its bodies, in the project's order
    shown: tuple                # the bodies listed in its node: with sub-fields, or a roof worth laying
    others: tuple               # the bodies gathered in one row of the node


def _area(ring) -> float:
    total = 0.0
    for (x0, y0), (x1, y1) in zip(ring, list(ring[1:]) + list(ring[:1]), strict=True):
        total += x0 * y1 - x1 * y0
    return abs(total) / 2.0


def file_stem(path: str) -> str:
    """A file's name without its folders and its extension, whatever the separators («I:/a/b/Model.ifc» is «Model»)."""
    name = re.split(r"[\\/]", str(path or "").strip())[-1]
    return _IFC_FILE.sub("", name) if _IFC_FILE.search(name) else name.rpartition(".")[0] or name


def _reference(project) -> dict:
    ref = (getattr(project, "resources", None) or {}).get("ifc_reference")
    return ref if isinstance(ref, dict) else {}


def _stem(name: str) -> tuple[str, int | None]:
    m = _NUMBERED.match(name or "")
    return (m.group("stem"), int(m.group("n"))) if m else ((name or "").strip(), None)


def shared_name(names) -> str:
    """The name some bodies share, "" when they do not: the import calls the bodies of one building «Name», «Name 2»,
    «Name 3»; bodies numbered from 1 («Body 1», «Body 2») have no name of their own."""
    stems = [_stem(n) for n in names]
    first = stems[0][0] if stems else ""
    if not first or any(s != first for s, _n in stems) or any(n == 1 for _s, n in stems):
        return ""
    return first


def _tops(project):
    """(the bodies that are not a part of another, {id of a body: its parts})."""
    by_id = {b.id: b for b in project.buildings}
    parts: dict = {}
    tops = []
    for b in project.buildings:
        whole = by_id.get(b.part_of) if b.part_of and b.part_of != b.id else None
        if whole is not None and whole.part_of not in by_id:
            parts.setdefault(whole.id, []).append(b)
        else:
            tops.append(b)
    return tops, parts


def own_field(sf) -> bool:
    """Whether a sub-field is the designer's: drawn or renamed by him (a name that is not the import's), or laid. A
    plane the import offered and nobody touched yet is not: it does not keep its body in view (R604)."""
    return sf.filled or _parsed(sf.name) is None


def fitting(project, bodies) -> dict:
    """{id of a body: the modules of the project that fit on its roof, about}, for the bodies of `bodies` that are not
    a part of another (a part adds its own to its body's). FIT_SHARE of the room where a module fits lengthwise, once
    the edge band of the next sub-fields and the obstacles on it are taken off, over the module's area in plan. The
    room of each outline is kept on the body until its outline, the band or the module change (the tree asks at every
    refresh); the ones to make are made in one call of shapely (2 000 bodies, about 0,1 s once)."""
    from meridiana.core.layout import layout
    from meridiana.core.model import model as _model
    record = project.modules.get(project.default_module()) or _model.GENERIC_MODULES["generic-450"]
    across, area = max(record["length"], record["width"]), record["length"] * record["width"]
    edge = float(project.default_params().get("edge", layout.Params.edge))     # the class default: no profile asked
    rooms, todo = {}, []
    for b in bodies:
        if len(b.footprint) < 3:
            continue
        key = (repr(b.footprint), edge, across)
        kept = b.__dict__.get("_room_cache")           # not a field: never in the file nor compared
        if kept is not None and kept[0] == key:
            rooms[b.id] = kept[1]
        else:
            todo.append((b, key))
    if todo:
        import numpy as np
        import shapely
        outlines = shapely.make_valid(shapely.polygons([shapely.linearrings(np.asarray(b.footprint, dtype=float)) for b, _key in todo]))
        inner = shapely.buffer(outlines, -edge, join_style="mitre") if edge > 0 else outlines
        room = shapely.buffer(shapely.buffer(inner, -across / 2, join_style="mitre"), across / 2, join_style="mitre")
        for (b, key), free in zip(todo, np.asarray(shapely.area(room), dtype=float).tolist(), strict=True):
            b.__dict__["_room_cache"] = (key, free)
            rooms[b.id] = free
    blocked: dict = {}
    for e in project.exclusions:
        if e.building in rooms and len(e.ring) >= 3:
            blocked[e.building] = blocked.get(e.building, 0.0) + _area(e.ring)
    by_id = {b.id: b for b in project.buildings}
    out: dict = {}
    for b in bodies:
        if b.id not in rooms:
            continue
        n = int(max(0.0, rooms[b.id] - blocked.get(b.id, 0.0)) * FIT_SHARE / area) if area > 0 else 0
        whole = b.part_of if b.part_of in by_id and b.part_of != b.id else b.id
        out[whole] = out.get(whole, 0) + n
    return out


def models(project) -> list[Model]:
    """The imported models of the project, in the order of their first body. A model is two bodies or more that came
    in together (`Building.group`); a body imported alone, or left alone, is a building as any other."""
    tops, parts = _tops(project)
    grouped: dict = {}
    for b in project.buildings:
        if b.group:
            grouped.setdefault(b.group, []).append(b)
    ref = _reference(project)
    anchor = (ref.get("anchor") or {}).get("building")
    with_fields = {sf.building for sf in project.subfields if sf.building and own_field(sf)}
    fit = fitting(project, [b for bodies in grouped.values() if len(bodies) > 1 for b in bodies])
    own = getattr(project, "model_names", None) or {}           # format 33: the name the designer gave it
    out = []
    for key, bodies in grouped.items():
        if len(bodies) < 2:
            continue
        mine = [b for b in tops if b.group == key]
        if not mine:
            continue                                # all of them parts of a building outside the model: shown there
        file = str(ref.get("file") or "") if any(b.id == anchor for b in bodies) else ""
        name = (own.get(key) or "").strip() or shared_name([b.name for b in mine]) or file_stem(file)
        if not name:
            number = key[3:] if key.startswith("ifc") and key[3:].isdigit() else ""
            name = (_("Imported model {n}").format(n=number) if number not in ("", "1") else _("Imported model"))
        shown, others = [], []
        for b in mine:
            useful = (b.id in with_fields or any(x.id in with_fields for x in parts.get(b.id, []))
                      or fit.get(b.id, 0) >= ROOF_LEAST)
            (shown if useful else others).append(b.id)
        if not shown or len(others) < OTHERS_LEAST:
            shown, others = [b.id for b in mine], []
        out.append(Model(key, name, file, tuple(b.id for b in bodies), tuple(shown), tuple(others)))
    return out


def renamed(key: str, name: str):
    """The change that gives the imported model of the group `key` the name `name` (format 33), for session.edit: the
    name goes where the model is shown (the tree, the checks, the short names of its planes, the report). Raises
    ValueError for an empty name or a group that is not a model of the project."""
    name = (name or "").strip()
    if not name:
        raise ValueError("an imported model needs a name")

    def change(p):
        if not any(m.key == key for m in models(p)):
            raise ValueError(f"no imported model {key!r}")
        p.model_names = {**p.model_names, key: name}
    return change


def model_of(project, building_id: str) -> Model | None:
    """The imported model a body belongs to, None for a building on its own."""
    b = project.building(building_id)
    if b is None or not b.group:
        return None
    return next((m for m in models(project) if m.key == b.group), None)


_SAVED = (re.compile(r"^(?P<file>.+?\.ifc(?:zip|xml)?): (?P<ids>#\d+(?:, #\d+)*)(?P<rest>.*)$", re.IGNORECASE | re.DOTALL),
          re.compile(r"^(?P<file>.+?\.ifc(?:zip|xml)?): (?P=file)(?P<rest>.*)$", re.IGNORECASE | re.DOTALL))


def _parsed(saved: str):
    """(the file, the elements, what follows) of a name the import saved for a placement plane, None for any other.
    What follows is what the program added since: «(copy)» on a duplicate, «, pitch 2» on a part of a split."""
    for pattern in _SAVED:
        m = pattern.match(saved or "")
        if m:
            return m.group("file"), m.groupdict().get("ids") or "", m.group("rest")
    return None


def source_of(saved: str) -> tuple[str, str]:
    """(the file, the elements) of a name as the import saves it for a placement plane («<file>: #12, #40», or
    «<file>: <file>» when the plane has no element), ("", "") for any other name."""
    found = _parsed(saved)
    return (found[0], found[1]) if found else ("", "")


class Names:
    """The names shown for what an import made, for one state of the project (make it once, ask it in a loop)."""

    def __init__(self, project):
        by_group = {m.key: m for m in models(project)}
        by_file = {m.file: m for m in by_group.values() if m.file}
        bodies = {b.id: b for b in project.buildings}
        ref = _reference(project)
        made = ref.get("derived") if isinstance(ref.get("derived"), dict) else {}
        listed = [str(i) for i in made.get("supports") or []]
        anchor = bodies.get((ref.get("anchor") or {}).get("building"))
        self._names: dict = {}
        self._sources: dict = {}
        home = None                                 # the import whose list of what it made the project keeps
        if anchor is not None:
            home = ("model", anchor.group) if anchor.group in by_group else ("body", anchor.id)
        place = {sid: n for n, sid in enumerate(listed, 1)}
        counted: dict = {}
        for sf in project.subfields:
            file, elements, rest = _parsed(sf.name) or ("", "", "")
            if not file and sf.support is None:
                continue
            body = bodies.get(sf.building)
            model = by_group.get(body.group) if body is not None and body.group else None
            if model is None and body is None and file in by_file:
                model = by_file[file]               # a plane on the ground of a model's import is the model's
            if model is not None:
                key, name = ("model", model.key), model.name
            elif body is not None:
                key, name = ("body", body.id), body.name
            elif file:
                key, name = ("file", file), file_stem(file)
            else:
                continue
            # the number of a plane is its place among the planes of its import: by the import's own list when the
            # project has it (the same for ever), else among the planes on the import's bodies in the order made (a
            # plane renamed keeps its place, so the others keep their numbers; only a deletion moves them)
            n = place.get(sf.id) if key == home else None
            if n is None:
                counted[key] = counted.get(key, len(place) if key == home else 0) + 1
                n = counted[key]
            if file:
                self._sources[sf.id] = (file, elements)
                self._names[sf.id] = (name, n, rest)

    def subfield(self, sf, short: bool = False) -> str:
        """The name shown for a sub-field: its own, or for a plane the import made «<model> · surface <n>» (`short`:
        «Surface <n>», where the model is already said, as under its body in the project's tree)."""
        found = self._names.get(sf.id)
        if found is None:
            # a plane that is not in this project (cut, on the clipboard): the file's name, never its path
            parsed = _parsed(sf.name)
            return file_stem(parsed[0]) + parsed[2] if parsed else sf.name
        name, n, rest = found
        if short or not name:
            return _("Surface {n}").format(n=n) + rest
        return _("{model} · surface {n}").format(model=name, n=n) + rest

    def source(self, sf) -> str:
        """Where a plane the import made comes from, in words for a tooltip or the properties: the file with its whole
        path and the elements' numbers; "" for any other sub-field."""
        found = self._sources.get(sf.id)
        if found is None:
            return ""
        file, elements = found
        return (_("From {file}, IFC {elements}").format(file=file, elements=elements) if elements
                else _("From {file}").format(file=file))


def namer(project) -> Names:
    return Names(project)


def subfield_name(project, sf, short: bool = False) -> str:
    """The name shown for one sub-field (`Names.subfield`); in a loop make a `namer` once. A name that is not the
    import's costs nothing (the status bar asks at every move of the pointer)."""
    if _parsed(sf.name) is None:
        return sf.name
    return Names(project).subfield(sf, short)
