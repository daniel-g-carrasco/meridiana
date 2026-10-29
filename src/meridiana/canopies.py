"""Editable parking canopy placement planes. These dimensions do not certify a structural design."""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import model
from .i18n import _


@dataclass(frozen=True)
class Spec:
    stalls: int = 4
    rows: int = 1
    bay_width: float = 2.5
    depth: float = 5.0
    clearance: float = 2.7
    tilt: float = 8.0
    turn: float = 0.0

    def validate(self) -> None:
        if type(self.stalls) is not int or not 1 <= self.stalls <= 100 or self.rows not in (1, 2):
            raise ValueError('Invalid parking row count')
        for value, low, high in ((self.bay_width, 0.5, 20), (self.depth, 1, 50),
                                 (self.clearance, 0.1, 100), (self.tilt, 0, 60), (self.turn, -180, 180)):
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError('Invalid canopy dimensions')


def fields(spec: Spec, at: tuple[float, float]) -> list[model.SubField]:
    """One slope per parking row; two rows meet at a ridge and keep their own module orientation."""
    spec.validate()
    angle = math.radians(spec.turn)
    co, si = math.cos(angle), math.sin(angle)

    def point(x, y):
        return [at[0] + x * co - y * si, at[1] + x * si + y * co]

    width, depth = spec.stalls * spec.bay_width, spec.depth
    centre_z = spec.clearance + depth * 0.5 * math.tan(math.radians(spec.tilt))
    result = []
    for row in range(spec.rows):
        bottom = row * depth
        ring = [point(0, bottom), point(width, bottom), point(width, bottom + depth), point(0, bottom + depth)]
        cx, cy = point(width / 2, bottom + depth / 2)
        azimuth = ((180 * row - spec.turn) + 180) % 360 - 180
        support = model.SupportPlane(tilt=spec.tilt, azimuth=azimuth, z0=centre_z, x0=cx, y0=cy)
        result.append(model.SubField(id=f's{row + 1}', name=_("Canopy row {n}").format(n=row + 1), ring=ring,
                                    params={'mounting': 'canopy', 'tilt': spec.tilt, 'azimuth': azimuth,
                                            'edge': 0.2, 'stand_off': 0.1},
                                    support=support, filled=True))
    return result


def add(project: model.Project, spec: Spec, at: tuple[float, float]) -> list[str]:
    """Call inside one session edit; allocate IDs against the growing project, never overwrite existing rows."""
    ids = []
    for sf in fields(spec, at):
        sf.id = project.new_id('s')
        project.subfields.append(sf)
        ids.append(sf.id)
    return ids
