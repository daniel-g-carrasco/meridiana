"""Plan shadows from the same solids and solar projection used in the energy model."""
from __future__ import annotations

import math

from meridiana import model
from meridiana.energy import nearshade, system


def shadow_paths(project, azimuth, elevation, height=0.):
    if not all(math.isfinite(v) for v in (azimuth,elevation,height)):
        raise ValueError('Solar angles and shadow height must be finite')
    if elevation <= 0:
        return []
    # A receiver without a host includes all buildings, parapets, exclusions and props.
    receiver=model.SubField(id='shadow-receiver',name='',ring=[])
    solids=system.obstacles_of(project,receiver)
    geometry=nearshade.plan_shadow(solids,azimuth,elevation,height)
    if geometry is None or geometry.is_empty:
        return []
    polygons=list(geometry.geoms) if geometry.geom_type=='MultiPolygon' else [geometry]
    paths=[]
    for polygon in polygons:
        if polygon.geom_type!='Polygon':
            continue
        parts=[]
        for ring in [polygon.exterior,*polygon.interiors]:
            points=list(ring.coords)
            parts.append('M'+' L'.join(f'{x:.9g},{-y:.9g}' for x,y in points)+' Z')
        paths.append(dict(path=' '.join(parts),area=polygon.area,bounds=list(polygon.bounds)))
    return paths
