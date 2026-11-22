"""The key of the energy year: everything the year is computed from, as one string, and its short mark (R437).

The one place it is made (revision r30, finding 3). The session, the window's bridges, the computation's process
that keeps the year (data/year_store) and the charts all ask here: equal keys, the same year; a change that leaves it
alone (a name, a rule) computes nothing again (study 18, A 9.2). tests/nucleo/test_chiave_anno.py fails when the key
is built anywhere else.

The bricks that are not only the year's stay with the model: the key of a sub-field's layout (Project.layout_key)
and what casts the shadows (Project.shadow_casters), which the layout's key and the checks use too."""

from __future__ import annotations

import dataclasses
import json

from meridiana.core.model import model
from meridiana.core.rules import registry
from meridiana.data import year_store


def layout_keys(project: model.Project) -> dict:
    """The key each filled sub-field's layout has (or will have, once laid out): id -> Project.layout_key."""
    return {sf.id: project.layout_key(sf) for sf in project.subfields if sf.filled}


def inputs(project: model.Project, layouts: dict) -> dict:
    """What the year is computed from, by part: the layouts (by their keys, `layouts`), the energy, consumption and
    economics settings, the modules, the site, the regulatory profile; the inverter and the input of each sub-field
    (not in the layout's key: model.ELECTRICAL); what shades the modules."""
    p = project
    wired = {sf.id: [sf.params.get(k) for k in model.ELECTRICAL] for sf in p.subfields}
    data = {"layouts": sorted(layouts.items()), "energy": p.energy, "regulatory": registry.identity(p),
            "consumption": p.consumption, "economics": p.economics, "modules": p.modules,
            "site": dataclasses.asdict(p.site), "wired": wired,
            # what shades the modules in the year (energy/system.obstacles_of): every building and obstacle with
            # its height; the layout's key holds them only for a sub-field kept out of the shadows, so a chimney
            # made taller left the year computed as good (found 31/10/2026)
            "shade": p.shadow_casters()}
    # R303: the walls of a roof drawn by hand stop at its lowest corner; only then, the keys of before stay
    walls = {b.id: top for b in p.buildings if (top := b.wall_top()) != b.height}
    if walls:
        data["shade"]["walls"] = walls
    from meridiana.app.exchange import ifc_shade
    true = ifc_shade.key(p)
    if true:                            # r22-ifc: the IFC model's shapes cast shadows; only then, as above
        data["shade"]["ifc"] = true
    shading = [x.as_dict() for x in p.props if x.casts_shadow()]
    if shading:                         # R269: a tree placed shades the year; only then, the keys of before stay
        data["props"] = shading
    return data


def key(project: model.Project, layouts: dict) -> str:
    """The year's key on the layouts of `layouts` (id -> layout key): those in hand, or layout_keys(project)."""
    return json.dumps(inputs(project, layouts), sort_keys=True, default=str)


def expected(project: model.Project) -> str:
    """The year's key for the project as it is now, the layouts on their way included (layout_keys)."""
    return key(project, layout_keys(project))


def fingerprint(text: str) -> str:
    """The short mark of a key: the name of the year kept (data/year_store) and of a report's numbers."""
    return year_store.fingerprint_of(text)


def parts(project: model.Project, layouts: dict) -> dict:
    """The inputs of the year, each with its mark, to say what changed (the energy one by one)."""
    data = inputs(project, layouts)
    energy = data.pop("energy") or {}
    out = {f"energy.{k}": v for k, v in energy.items()}
    out.update(data)
    return {name: fingerprint(json.dumps(value, sort_keys=True, default=str)) for name, value in out.items()}
