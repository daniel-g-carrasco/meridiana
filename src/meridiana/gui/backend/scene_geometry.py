"""GUI-thread geometry uploads and native Qt instance files, with no render-thread Python virtuals."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry

from meridiana.app import scene_job
from meridiana.app.scene_job import instance_file  # noqa: F401 (the 3D's instance files: made by the scene's job too)


class SceneGeometry(QQuick3DGeometry):
    """Same vertex format as Widgets BuildingsGeometry; no Python updateSpatialNode override."""

    def set_mesh(self, positions, normals, colours, *, indexed=False):
        p, n, c = (np.asarray(a, dtype=np.float32) for a in (positions, normals, colours))
        if p.shape != n.shape or p.ndim != 2 or p.shape[1] != 3 or len(p) != len(c):
            raise ValueError('Position, normal and colour arrays must have matching vertices')
        if c.ndim != 2 or c.shape[1] not in (3, 4) or len(p) % 3:
            raise ValueError('Geometry requires triangles and RGB or RGBA colours')
        if not all(np.isfinite(a).all() for a in (p, n, c)):
            raise ValueError('Geometry cannot contain non-finite values')
        rgba = np.column_stack((c, np.ones(len(c), dtype=np.float32))) if c.shape[1] == 3 else c
        data = np.column_stack((p, n, rgba)) if len(p) else np.zeros((3, 10), np.float32)
        indices = None
        if indexed and len(p):
            # Share identical vertices without decimating a single triangle or changing a seam.
            data, indices = np.unique(data, axis=0, return_inverse=True)
        self.clear()
        self.setVertexData(QByteArray(data.astype('<f4').tobytes()))
        self.setStride(40)
        self.setPrimitiveType(self.PrimitiveType.Triangles)
        a = self.Attribute
        if indices is not None:
            self.setIndexData(QByteArray(indices.astype('<u4').tobytes()))
            self.addAttribute(a.Semantic.IndexSemantic, 0, a.ComponentType.U32Type)
        for semantic, offset in ((a.Semantic.PositionSemantic, 0), (a.Semantic.NormalSemantic, 12),
                                 (a.Semantic.ColorSemantic, 24)):
            self.addAttribute(semantic, offset, a.ComponentType.F32Type)
        low, high = (p.min(0), p.max(0)) if len(p) else (np.zeros(3), np.zeros(3))
        self.setBounds(QVector3D(*map(float, low)), QVector3D(*map(float, high)))
        self.update()


class DotGeometry(SceneGeometry):
    """Round marks of a fixed size in pixels, expanded in the vertex shader (View3D/dots.vert).

    POSITION is the mark's point, NORMAL.xy its offset in pixels, NORMAL.z its lift towards the camera in pixels.
    Upload only when the marks change; the camera moves them without Python.
    """
    SIDES = 20
    LIFT = 9.0      # more than the largest radius: a disc standing on a corner does not enter its faces

    def set_dots(self, dots):
        """`dots`: (point, diameter, fill, edge), colours as (r, g, b) in 0..1. Each dot two discs (its edge, then its
        fill a pixel smaller and nearer), each disc SIDES triangles from its centre; made with arrays, not a tuple at
        a time: the 706 corners of a model's body took 110 ms at its selection (passo 2, R598)."""
        angles = np.linspace(0, 2*np.pi, self.SIDES+1)
        ring = np.column_stack((np.cos(angles), np.sin(angles)))
        dots = list(dots)
        points = np.asarray([d[0] for d in dots], np.float64).reshape(-1, 3)
        # the discs in their order: the edge of a dot, its fill, the edge of the next...
        radius = np.asarray([r for _p, diameter, _f, _e in dots for r in (diameter/2, diameter/2-1)], np.float64)
        lift = np.tile([self.LIFT, self.LIFT+.5], len(dots))
        colour = np.asarray([c for _p, _d, fill, edge in dots for c in (edge, fill)], np.float64).reshape(-1, 3)
        normals = np.zeros((len(radius), self.SIDES, 3, 3))
        normals[:, :, :, 2] = lift[:, None, None]
        for corner, side in ((1, ring[:-1]), (2, ring[1:])):
            normals[:, :, corner, 0] = side[None, :, 0] * radius[:, None]
            normals[:, :, corner, 1] = side[None, :, 1] * radius[:, None]
        each = 3 * self.SIDES
        self.set_mesh(np.repeat(np.repeat(points, 2, axis=0), each, axis=0).astype(np.float32),
                      normals.reshape(-1, 3).astype(np.float32), np.repeat(colour, each, axis=0).astype(np.float32))
        if len(points):
            low, high = points.min(0), points.max(0)
            self.setBounds(QVector3D(*map(float, low-5)), QVector3D(*map(float, high+5)))


class RibbonGeometry(SceneGeometry):
    """Square tubes as in mesh.ribbons, expanded in the vertex shader in screen pixels.

    POSITION is an endpoint, NORMAL its unit-width displacement. Upload only when
    the selection changes; camera uniforms keep the width steady without Python.
    """

    def set_segments(self, segments):
        self.set_ribbons(scene_job.ribbons(segments))

    def set_ribbons(self, made):
        """The tubes made by scene_job.ribbons (here, or in the job that made the segments): endpoints,
        displacements, colours and the bounds (None without a segment)."""
        endpoints, displacements, colours, bounds = made
        self.set_mesh(endpoints, displacements, colours)
        if bounds is not None:
            self.setBounds(QVector3D(*bounds[0]), QVector3D(*bounds[1]))
