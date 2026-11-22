"""The Python types of the report's 3D scene (ReportScene.qml): every building in one mesh, the outlines, and every
module as Qt's instance table. They were the 3D view's own (ui/view3d.py, which takes them from here until the
Widgets window goes); registered in the QML module «Meridiana», as before."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QVector3D
from PySide6.QtQml import QmlElement
from PySide6.QtQuick3D import QQuick3DGeometry, QQuick3DInstancing

QML_IMPORT_NAME = "Meridiana"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
class BuildingsGeometry(QQuick3DGeometry):
    """Every building in one mesh: position, normal and colour per vertex."""

    def set_mesh(self, pos: np.ndarray, nor: np.ndarray, col: np.ndarray) -> None:
        self.clear()
        n = len(pos)
        if n == 0:
            data = np.zeros((3, 10), dtype=np.float32)          # an empty triangle keeps Qt happy
            lo = hi = QVector3D(0, 0, 0)
        else:
            rgba = np.hstack([col, np.ones((n, 1), dtype=np.float32)])
            data = np.hstack([pos, nor, rgba]).astype(np.float32)
            lo = QVector3D(*map(float, pos.min(axis=0)))
            hi = QVector3D(*map(float, pos.max(axis=0)))
        self.setVertexData(QByteArray(data.tobytes()))
        self.setStride(40)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        A = QQuick3DGeometry.Attribute
        self.addAttribute(A.Semantic.PositionSemantic, 0, A.ComponentType.F32Type)
        self.addAttribute(A.Semantic.NormalSemantic, 12, A.ComponentType.F32Type)
        self.addAttribute(A.Semantic.ColorSemantic, 24, A.ComponentType.F32Type)
        self.setBounds(lo, hi)
        self.update()


@QmlElement
class OutlineGeometry(BuildingsGeometry):
    """The outline of what is selected and of what is under the pointer: ribbons (mesh.ribbons), unlit."""


@QmlElement
class ModulesInstancing(QQuick3DInstancing):
    """Every module of every filled sub-field, as Qt's instance table (mesh.module_table)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = QByteArray()
        self._count = 0

    def set_table(self, table: np.ndarray) -> None:
        self._data = QByteArray(table.astype(np.float32).tobytes())
        self._count = int(len(table))
        self.markDirty()

    def getInstanceBuffer(self):
        # PySide6 6.12: no argument, (data, count) back (tried on 21/10/2026)
        return self._data, self._count
