"""GUI-thread geometry uploads and native Qt instance files, with no render-thread Python virtuals."""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

import numpy as np
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry


def instance_file(directory: Path, table: np.ndarray) -> Path:
    """Qt 6.12 FileInstancing v1, exact mesh.module_table layout (20 float32 per instance).

    Header verified against qt/qtquick3d 6.12 src/quick3d/qquick3dinstancing.cpp.
    Content-addressed files stay alive with the scene: Qt memory-maps them on its render thread.
    """
    table = np.asarray(table, dtype='<f4')
    if table.ndim != 2 or table.shape[1] != 20 or not np.isfinite(table).all():
        raise ValueError('An instance table must contain finite rows of 20 floats')
    payload = struct.pack('<4sHHIII', b'QtIR', 1, 0, 80, 20, len(table)) + table.tobytes()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (hashlib.sha256(payload).hexdigest() + '.bin')
    if not path.exists():
        path.write_bytes(payload)
    return path


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
        """`dots`: (point, diameter, fill, edge), colours as (r, g, b) in 0..1."""
        angles = np.linspace(0, 2*np.pi, self.SIDES+1)
        ring = np.column_stack((np.cos(angles), np.sin(angles)))
        positions, normals, colours = [], [], []

        def disc(point, radius, lift, colour):
            for a, b in zip(ring[:-1], ring[1:], strict=True):
                positions.extend((point, point, point))
                normals.extend(((0., 0., lift), (a[0]*radius, a[1]*radius, lift), (b[0]*radius, b[1]*radius, lift)))
                colours.extend((colour, colour, colour))
        for point, diameter, fill, edge in dots:
            disc(point, diameter/2, self.LIFT, edge)
            disc(point, diameter/2-1, self.LIFT+.5, fill)
        self.set_mesh(np.asarray(positions, np.float32).reshape(-1, 3), np.asarray(normals, np.float32).reshape(-1, 3),
                      np.asarray(colours, np.float32).reshape(-1, 3))
        if positions:
            low, high = np.min(positions, 0), np.max(positions, 0)
            self.setBounds(QVector3D(*map(float, low-5)), QVector3D(*map(float, high+5)))


class RibbonGeometry(SceneGeometry):
    """Square tubes as in mesh.ribbons, expanded in the vertex shader in screen pixels.

    POSITION is an endpoint, NORMAL its unit-width displacement. Upload only when
    the selection changes; camera uniforms keep the width steady without Python.
    """

    def set_segments(self, segments):
        from meridiana import mesh
        segs = np.asarray(segments, dtype=np.float64).reshape(-1, 2, 3)
        segs = segs[np.linalg.norm(segs[:, 1]-segs[:, 0], axis=1) > 1e-9]
        positions, _, colours = mesh.ribbons(segs, 1., (1., 1., 1.))
        endpoints = np.concatenate([
            segs[:, [0, 1, 1]].reshape(-1, 3), segs[:, [0, 1, 0]].reshape(-1, 3)
        ]) if len(segs) else np.zeros((0, 3))
        endpoints = np.tile(endpoints, (4, 1))
        self.set_mesh(endpoints, positions-endpoints, colours)
        if len(positions):
            self.setBounds(QVector3D(*map(float, positions.min(0)-5)),
                           QVector3D(*map(float, positions.max(0)+5)))
