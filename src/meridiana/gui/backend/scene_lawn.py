"""The lawn of the 3D with its openings (R602): while the true geometry of an imported IFC model is shown, the lawn opens
on the model's parts under its zero and, on the site, follows the model's terrain with a slope to the flat lawn around
(app.exchange.ifc_ground.lawn_triangles).
Without openings the 3D keeps its plain «#Rectangle» (View3D/Viewport.qml): a project without an import, or imported
before, draws exactly as it did."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry


class LawnGeometry(QQuick3DGeometry):
    """Positions and normals of the lawn's triangles, in the Qt axes (the flat lawn at the height 0, the site's lawn on
    the model's terrain and its slope at their heights)."""

    def set_triangles(self, plan: np.ndarray) -> None:
        """`plan`: (n, 3, 3) triangles in the plan (east, north, height), or (n, 3, 2) at the height 0."""
        plan = np.asarray(plan, float)
        p = np.zeros((len(plan), 3, 3), np.float32)
        p[:, :, 0] = plan[:, :, 0]
        p[:, :, 2] = -plan[:, :, 1]
        if plan.shape[2] > 2:
            p[:, :, 1] = plan[:, :, 2]
        # facing up in Qt's axes, whatever the order the triangulation gave (a wall of the dig keeps its own)
        n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        down = n[:, 1] < 0
        p[down] = p[down][:, ::-1]
        n[down] = -n[down]
        n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
        data = np.zeros((len(p) * 3, 6), '<f4')
        data[:, :3] = p.reshape(-1, 3)
        data[:, 3:] = np.repeat(n, 3, axis=0)
        self.clear()
        self.setVertexData(QByteArray(data.tobytes()))
        self.setStride(24)
        self.setPrimitiveType(self.PrimitiveType.Triangles)
        a = self.Attribute
        self.addAttribute(a.Semantic.PositionSemantic, 0, a.ComponentType.F32Type)
        self.addAttribute(a.Semantic.NormalSemantic, 12, a.ComponentType.F32Type)
        low, high = data[:, :3].min(0), data[:, :3].max(0)
        self.setBounds(QVector3D(*map(float, low)), QVector3D(*map(float, high)))
        self.update()


class Lawn:
    """The lawn's geometry made once and changed only when its triangles change; `geometry` None for the plain one."""

    def __init__(self, parent):
        self._geometry = LawnGeometry()
        self._geometry.setParent(parent)
        self._key = None
        self.geometry = None

    def show(self, plan) -> None:
        if plan is None or not len(plan):
            self.geometry, self._key = None, None
            return
        key = np.asarray(plan, np.float32).tobytes()
        if key != self._key:
            self._geometry.set_triangles(np.asarray(plan, float))
            self._key = key
        self.geometry = self._geometry
