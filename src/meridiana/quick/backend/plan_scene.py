"""Immutable plan drawing data, in scene metres (East, minus North). No Qt."""
from __future__ import annotations

import math

import numpy as np

from meridiana import geo, roofs, view_colours
from meridiana.i18n import number


def scene_of(project, results: dict) -> dict:
    objects, modules, labels, segments = [], [], [], []

    def add(kind, oid, ring, stroke, fill='transparent', width=1.5, closed=True, key='', **extra):
        points = [[float(x), -float(y)] for x, y in ring]
        if not points:
            return
        objects.append(dict(kind=kind, oid=oid, key=key, points=points, stroke=stroke,
                            fill=fill, width=width, closed=closed, **extra))
        end = ring[1:] + ring[:1] if closed else ring[1:]
        segments.extend((tuple(a), tuple(b)) for a, b in zip(ring, end, strict=False))

    c, widths = view_colours.PHOTO, view_colours.WIDTHS
    for b in project.buildings:
        add('building', b.id, b.footprint, c['bld_stroke'], c['bld_fill'], widths['building'])
        for i, pitch in enumerate(b.pitches()):
            if pitch.tilt > 0:
                add('pitch', f'{b.id}:{i}', pitch.ring, c['pitch'], width=widths['pitch'])
                xs, ys = zip(*pitch.ring, strict=True)
                cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
                fx, fy = geo.facing_vector(pitch.azimuth)
                size = max(1., .25*min(max(xs)-min(xs), max(ys)-min(ys)))
                a, end = (cx-fx*size/2, cy-fy*size/2), (cx+fx*size/2, cy+fy*size/2)
                add('slope', b.id, [a, end], c['pitch'], width=1.5, closed=False)
                angle = math.atan2(end[1]-a[1], end[0]-a[0])
                for delta in (2.6, -2.6):
                    tip = (end[0]-.25*size*math.cos(angle+delta/6), end[1]-.25*size*math.sin(angle+delta/6))
                    add('slope', b.id, [end, tip], c['pitch'], width=1.5, closed=False)
        # Ridges are already calculated in the shared roof core.
        for a, z in roofs.ridges(b.pitches(), b.height):
            add('ridge', b.id, [a[:2], z[:2]], c['pitch'], closed=False)
    for sf in project.subfields:
        add('subfield', sf.id, sf.ring, c['sub_stroke'], c['sub_fill'], widths['subfield'], dashed=True)
    for e in project.exclusions:
        add('exclusion', e.id, e.ring, c['exclusion'], c['exclusion'] + '22', widths['exclusion'])
    for prop in project.props:
        ring = prop.footprint()
        add('prop', prop.id, ring, c['prop'], c['prop'] + '33')
        x, y = prop.at[:2]
        for a, b in (((x - .3, y), (x + .3, y)), ((x, y - .3), (x, y + .3))):
            add('prop_mark', prop.id, [a, b], c['prop'], closed=False)
    # R445, decision 2: the fire-brigade rules as guides on the roofs subject to them (1 m from the edge, 1 m around
    # the vents, openings and plant), dashed, never a wall
    for bid, ring in project.fire_guides():
        add('fire_guide', bid, ring, c['guide'], width=widths['guide'], dashed=True)
    for sfid, result in results.items():
        if isinstance(result, Exception):
            continue
        for group in result.groups:
            add('group', sfid, group, c['guide'], width=widths['guide'], dashed=True)
        # R445, decision 3: the modules set aside on an obstacle or off the roof, red, a click puts them back
        for module in getattr(result, 'blocked', None) or []:
            add('blocked', sfid, [tuple(q) for q in module.corners], c['sweep_remove'], c['sweep_remove'] + '55',
                1.0, key=module.key)
        for module in result.modules:
            modules.append(dict(kind='module', oid=sfid, key=module.key, rid=module.rid,
                                points=[[float(x), -float(y)] for x, y in module.corners],
                                centre=[float(module.centre[0]), -float(module.centre[1])]))
    points = [p for item in objects + modules for p in item['points']]
    if points:
        a = np.asarray(points)
        low, high = a.min(axis=0), a.max(axis=0)
        bounds = [*low.tolist(), *np.maximum(1., high - low).tolist()]
    else:
        bounds = [-20., -20., 40., 40.]
    return dict(objects=objects, modules=modules, labels=labels, bounds=bounds, segments=segments)


def module_geometry(modules):
    """Six triangle vertices and eight line vertices per module, no polygon rasterisation."""
    quads = np.asarray([[(p.x(), p.y()) if hasattr(p, 'x') else p for p in m['points']]
                        for m in modules], dtype=np.float32).reshape(-1, 4, 2)
    return (np.ascontiguousarray(quads[:, [0, 1, 2, 0, 2, 3]].reshape(-1, 2)),
            np.ascontiguousarray(quads[:, [0, 1, 1, 2, 2, 3, 3, 0]].reshape(-1, 2)))


def side_labels(ring):
    """R276/R336: label centres in world coordinates, text in logical screen pixels."""
    return [dict(index=i, x=(a[0] + b[0]) / 2, y=-(a[1] + b[1]) / 2,
                 length=math.dist(a, b), text=f'{i + 1}  {number(math.dist(a, b))} m')
            for i, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1], strict=True))]
