"""The scenes of the procedural props: a line-up with scale references, a realistic shed with a car park, one kind
alone (tests/nucleo/test_props.py builds them). The viewer that showed them, on the 3D view of the Widgets window,
went with it (r30, phase B)."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from meridiana.core.layout import layout
from meridiana.core.geometry import mesh, props, roofs  # noqa: E402


def _join(parts):
    return tuple(np.concatenate([part[index] for part in parts]).astype(np.float32) for index in range(3))


def _placed(shape, x, z, y=0.0):
    pos, nor, col = shape
    offset = np.array((x, y, z), dtype=np.float32)
    return pos + offset, nor, col


def _box(width, depth, z0, z1, colour, x=0.0, z=0.0):
    ring = ((-width / 2, -depth / 2), (width / 2, -depth / 2),
            (width / 2, depth / 2), (-width / 2, depth / 2))
    return _placed(mesh.prism_triangles(ring, z0, z1, colour), x, z)


def _grid(x0, x1, z0, z1):
    segments = []
    for x in range(int(x0), int(x1) + 1):
        segments.append(((x, 0.008, z0), (x, 0.008, z1)))
    for z in range(int(z0), int(z1) + 1):
        segments.append(((x0, 0.008, z), (x1, 0.008, z)))
    return mesh.ribbons(np.asarray(segments), 0.015, (0.48, 0.53, 0.43))


def lineup_scene():
    """Every prop in category rows, with a one-metre grid and the two scale references."""
    parts = [_grid(-24, 24, -14, 14)]
    for index, kind in enumerate(props.TREE_KINDS):
        shape = props.tree(kind, rotation=index * 17.0)
        parts.append(_placed(shape, -18 + index * 7.2, -9))
    for index, kind in enumerate(props.OBSTACLE_KINDS):
        shape = props.obstacle(kind, rotation=(index % 4) * 15.0)
        parts.append(_placed(shape, -18 + index * 3, 0))
    for index, kind in enumerate(props.PERSON_KINDS):
        parts.append(_placed(props.person(kind), -10 + index * 4, 9))
    parts.append(_placed(props.car("compact", rotation=-12), 9, 9))
    parts.append(_placed(props.car("suv", rotation=12), 16, 9))
    parts.append(_box(4.0, 0.20, 0.0, 2.0, mesh.WALL, -20, 9))
    parts.append(_box(1.13, 0.035, 0.0, 2.28, mesh.MODULE, -16, 9))
    return _join(parts), np.zeros((0, 20), dtype=np.float32)


def _modules(centres, z, tilt):
    placed = [layout.PlacedModule(row=row, slot=slot, group=0, corners=[], centre=centre, z=z,
                                  tilt=tilt, azimuth=0.0)
              for row, slot, centre in centres]
    return mesh.module_table(placed, along=1.13, across=2.28)


def realistic_scene():
    """A shed with photovoltaic modules, trees, people and two cars under a covered parking bay."""
    footprint = [(-20.0, -6.0), (2.0, -6.0), (2.0, 6.0), (-20.0, 6.0)]
    parts = [mesh.building_triangles(footprint, roofs.flat(footprint, 5.0))]
    roof_centres = [(row, slot, (-17 + slot * 4.0, -4.0 + row * 2.6))
                    for row in range(4) for slot in range(5)]
    canopy_centres = [(row, slot, (10.5 + slot * 2.5, -1.5 + row * 3.0))
                      for row in range(2) for slot in range(3)]
    table = np.concatenate((_modules(roof_centres, 5.15, 20.0), _modules(canopy_centres, 3.15, 0.0)))

    parts.append(_box(10.0, 8.0, 2.85, 3.0, mesh.ROOF_FLAT, 13, -1))
    for x in (8.5, 17.5):
        for z in (-4.5, 2.5):
            parts.append(_box(0.18, 0.18, 0.0, 2.85, mesh.OBSTACLE, x, z))
    parts.append(_placed(props.obstacle("plant"), -15, 0, 5.0))
    parts.append(_placed(props.obstacle("chimney"), -5, 2, 5.0))
    for kind, x, z, rotation in (("broadleaf", -25, 4, 0), ("conifer", -24, -6, 0),
                                 ("palm", 23, -6, 20), ("shrub", 5, 4, 0)):
        parts.append(_placed(props.tree(kind, rotation=rotation), x, z))
    for kind, x, z, rotation in (("adult", -1, 9, 15), ("walking", 2, 10, -20),
                                 ("child", 1, 11, 0), ("worker", 6, 8, 45)):
        parts.append(_placed(props.person(kind, rotation=rotation), x, z))
    parts.append(_placed(props.car("compact", colours={"car": (0.55, 0.62, 0.67)}), 11, 1))
    parts.append(_placed(props.car("suv", colours={"car": (0.47, 0.55, 0.42)}), 15, -3))
    return _join(parts), table.astype(np.float32)


def detail_scene(name):
    if name in props.KINDS:
        family = props.family(name)
        factory = {"tree": props.tree, "obstacle": props.obstacle, "person": props.person, "car": props.car}[family]
        return factory(name), np.zeros((0, 20), dtype=np.float32)
    if name == "auto":
        return _join([_placed(props.car("compact", rotation=-18), -3, 0),
                      _placed(props.car("suv", rotation=18), 3, 0)]), np.zeros((0, 20), dtype=np.float32)
    if name == "alberi":
        return _join([_placed(props.tree("conifer"), -6, 0), _placed(props.tree("pine"), 6, 0)]), \
            np.zeros((0, 20), dtype=np.float32)
    footprint = [(-5.0, -4.0), (5.0, -4.0), (5.0, 4.0), (-5.0, 4.0)]
    parts = [mesh.building_triangles(footprint, roofs.mono(footprint, 0, 3.0, 18.0))]
    surface = lambda x, y: 3.0 + (y + 4.0) * np.tan(np.radians(18.0))
    for path, railing in (([(-3, -2), (1, -2), (1, 2)], False), ([(-2, 2), (3, 2)], True)):
        ring = props.footprint("walkway", path[0], width=0.7, path=path)
        parts.append(mesh.path_triangles(ring, surface, 0.02, (0.56, 0.28, 0.21), railing))
    hedge = props.footprint("hedge", [0, 0], width=0.7, height=1.2,
                            path=[[-4, -5], [-1, -5], [-1, -7], [3, -7]])
    parts.append(mesh.prism_triangles(hedge, 0.1, 1.2, mesh.TREE))
    return _join(parts), np.zeros((0, 20), dtype=np.float32)


def shot_jobs():
    """The twelve captures in Gallery.apply's theme, scene and viewpoint order."""
    return [(theme, scene, view) for scene in ("galleria", "realistica") for theme in ("light", "dark")
            for view in ("assonometrica", "fronte", "alto")]
