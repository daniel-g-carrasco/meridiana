"""Existing Italian fire conditions, independent of geometry and storage."""
from meridiana.core.rules.types import FirePolicy
from meridiana.i18n import _
from .defaults import defaults
from .texts import BALLAST_WARNING

FIRE_SOURCE = "DCPREV 14030/2025 sect. 3.3.5.1 (p. 13-16)"


def policy(project, sf=None):
    params = sf.params if sf is not None else {}
    building = project.building(sf.building) if sf is not None else None
    enabled = (bool(params.get("fire_rules")) or bool(building and project.fire_of(building).subject)
               if sf is not None else any(b.fire.subject for b in project.buildings))
    values = defaults("layout")
    return FirePolicy(enabled, params.get("fire_edge", values["fire_edge"]),
                      params.get("fire_group", values["fire_group"]),
                      params.get("fire_corridor", values["fire_corridor"]), 1.0, FIRE_SOURCE, BALLAST_WARNING)


def group_items(placed, p, frame, size, result, sf, here, fix, label, name=""):
    """`name`: the sub-field's name as the checks show it (imported.namer), its own when not given."""
    from meridiana.core.layout import layout
    from meridiana.core.rules.types import Item
    from meridiana.i18n import number
    items = []
    name = name or sf.name
    if p.fire_rules:
        for members in layout.clusters(placed, p.fire_corridor):
            reach = layout.extent(placed, members, frame)
            if reach <= p.fire_group + layout.DISTANCE_TOLERANCE:
                continue
            items.append(Item("warn", "layout", _("{name}: group of {m} m, beyond the {limit} m").format(
                name=name, m=number(reach, 1), limit=number(p.fire_group, 0)), FIRE_SOURCE, here, fix, label,
                detail=_("Modules closer than {corridor} m make one group, and a group reaches at most {limit} m in "
                         "every direction. Leave a corridor of {corridor} m across it, move the rows apart, or lay "
                         "the sub-field again automatically.").format(corridor=number(p.fire_corridor, 0),
                                                                     limit=number(p.fire_group, 0))))
            gaps = layout.narrow_gaps(placed, members, frame, size.along, p, result.clearance)
            if gaps:
                items.append(Item("warn", "layout", _("{name}: corridor of {m} m, below the {limit} m").format(
                    name=name, m=number(gaps[0], 2), limit=number(p.fire_corridor, 0)), FIRE_SOURCE, here, fix,
                    label, detail=_("The rows left a gap between them that is narrower than a corridor: the groups on "
                                    "its two sides count as one. Widen it to {corridor} m.").format(
                                        corridor=number(p.fire_corridor, 0))))
    return items
