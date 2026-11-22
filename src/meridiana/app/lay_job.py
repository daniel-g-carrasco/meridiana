"""A sub-field drawn as modules (R445) laid as a job of the mechanism (R598) when it is large (Daniel 21/11/2026: a field
drawn 1,5 km long by mistake, 5635 modules, froze the window). The grid of its modules and its outline flush with
them (manual.make_flush) cost in proportion to the modules: 4 s for 11 784 on the window's thread, most of it the
union of their shapes. Here they are made in a process; the window asks first (plan_tools.CONFIRM_MODULES), shows the
job in the bar with its Cancel, and Esc stops it. What comes back is small: the rows as the file keeps them and the
outline, written into the project by one change (plan_edit._polygon with `laid`)."""

from __future__ import annotations

from meridiana.app.work.job import GIB, Kind
from meridiana.i18n import N_

KIND = Kind(name="lay_modules", title=N_("Laying the modules"), run="meridiana.app.lay_job:run", where="process",
            processes=1, memory=2 * GIB, topics=(), cancellable=True)


def request(photo: dict, ring) -> dict:
    """What the job needs: the project's photo (session.photo(), a reference) and the ring as drawn."""
    return {"photo": photo, "ring": [list(map(float, q)) for q in ring]}


def lay(project, ring) -> dict:
    """The rows and the outline of a sub-field drawn as modules inside `ring`, as plan_edit._polygon would make
    them: {"rows": [...], "ring": [...]}. Pure: the project given is changed (a draft sub-field added)."""
    from meridiana.core.layout import manual
    from meridiana.core.model import move
    ring = move.drawn_ring(ring)
    b, pitch = move.host(project, ring)
    sf = project.new_subfield("_lay", "", ring, b.id if b else None, pitch)
    project.add_subfield(sf)
    manual.make_flush(project, sf)
    return {"rows": sf.rows, "ring": sf.ring, "drawn": ring}


def run(req: dict, ctx) -> dict:
    from meridiana.app.session import project_from
    return lay(project_from(req["photo"]), req["ring"])
