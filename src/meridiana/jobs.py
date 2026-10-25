"""The work the window runs away from its thread, as plain functions without Qt: the layouts of the
sub-fields and (energy/pipeline.py) the energy year. The window wraps them in QRunnable jobs; the comparison
of the variants and the tests call them as they are (study 18, A 9.1)."""

from __future__ import annotations

from . import log, mesh
from .energy import system


def layout_of(project, known: dict | None = None) -> tuple[dict, dict, list]:
    """The layouts of the filled sub-fields of `project`: (results, keys, laid). `results` maps a sub-field's
    id to its layout.Result or to the exception that stopped it; `keys` to the inputs of that result
    (model.layout_key); `laid` lists the ids laid out this time. A sub-field whose inputs are those of a
    layout in hand (`known`: id -> (key, result)) keeps that result: a change lays out again only what it
    touched (study 15, 3.6). Each layout carries what the views need as arrays (its modules' corners and keys
    from layout.compute, its 3D instance table made here): the window's thread only hands them over (task
    18c, step 8)."""
    known = known or {}
    results, keys, laid = {}, {}, []
    for sf in project.subfields:
        if not sf.filled:
            continue
        keys[sf.id] = key = project.layout_key(sf)
        before = known.get(sf.id)
        if before is not None and before[0] == key and not isinstance(before[1], Exception):
            results[sf.id] = before[1]
            continue
        laid.append(sf.id)
        try:
            results[sf.id] = prepared(project, sf, project.fill(sf, shade=system.shadow_exclusions))
        except ValueError as error:
            results[sf.id] = error
        except Exception as error:      # noqa: BLE001 (a thread's boundary: said out loud, not lost)
            log.complain(f"layout of {sf.id}", error)
            results[sf.id] = error
    return results, keys, laid


def module_sides(project, sf) -> tuple[float, float]:
    """The sides of the sub-field's module as laid: along the row, and up the tilt."""
    m = project.module_of(sf)
    return (m.width, m.length) if sf.layout_params().portrait else (m.length, m.width)


def prepared(project, sf, result):
    """`result` with its 3D instance table (mesh.module_table, in the base colour: the window recolours a
    selection), made here in the layout's thread rather than on the window's."""
    along, across = module_sides(project, sf)
    result.table = mesh.module_table(result.modules, along, across)
    return result
