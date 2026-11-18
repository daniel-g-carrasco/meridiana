"""Batched scene graph modules. Only a changed layout uploads new GPU vertices.

QML owns the parent transform. D3D line primitives keep a one-pixel border at any
scale; no Python slot or paint callback is needed while navigating the plan.
"""
from __future__ import annotations

import ctypes
from collections import defaultdict

from PySide6.QtCore import Property, Signal
from PySide6.QtGui import QColor
from PySide6.QtQml import qmlRegisterType
from PySide6.QtQuick import QQuickItem, QSGFlatColorMaterial, QSGGeometry, QSGGeometryNode, QSGNode

from .plan_scene import module_geometry


class ModuleGeometry(QQuickItem):
    modulesChanged = Signal()
    fillChanged = Signal()
    strokeChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlag(QQuickItem.Flag.ItemHasContents, True)
        self._modules = []
        self._fill, self._stroke = QColor('#192d5a'), QColor('#c6cbd6')
        self._buffers = module_geometry([])
        self._packets = []
        self.uploads = 0
        self._nodes = []
        self._attributes = QSGGeometry.defaultAttributes_Point2D()

    @Property('QVariantList', notify=modulesChanged)
    def modules(self):
        return self._modules

    @modules.setter
    def modules(self, value):
        self._modules = value
        self._buffers = module_geometry(value)
        # Qt's batch renderer uses 16-bit vertex indices. A node above 65,535
        # vertices silently truncates on D3D11, even without an index buffer.
        groups = defaultdict(list)
        for module in value:
            groups[(module.get('fill', ''), module.get('stroke', ''))].append(module)
        self._packets = []
        for colours, group in groups.items():
            buffers = self._buffers if len(groups) == 1 else module_geometry(group)
            for kind, (array, per_module) in enumerate(zip(buffers, (6, 8), strict=True)):
                if colours[kind] == 'transparent':
                    continue
                self._packets.extend((array[start:start+per_module*5000], kind, colours[kind])
                                     for start in range(0, len(array), per_module*5000))
        self.modulesChanged.emit()
        self.update()

    @Property(QColor, notify=fillChanged)
    def fill(self):
        return self._fill

    @fill.setter
    def fill(self, value):
        if self._fill != value:
            self._fill = QColor(value)
            self.fillChanged.emit()
            self.update()

    @Property(QColor, notify=strokeChanged)
    def stroke(self):
        return self._stroke

    @stroke.setter
    def stroke(self, value):
        if self._stroke != value:
            self._stroke = QColor(value)
            self.strokeChanged.emit()
            self.update()

    def updatePaintNode(self, old, _data):
        node = old or QSGNode()
        self._root_node = node
        if not old:
            self._nodes = []
        # Reuse existing child nodes; surplus nodes receive empty geometry.
        packets = self._packets + [(self._buffers[0][:0], 0, '')] * max(0, len(self._nodes)-len(self._packets))
        for i, (vertices, kind, tint) in enumerate(packets):
            colour = QColor(tint) if tint else (self._fill, self._stroke)[kind]
            mode = (QSGGeometry.DrawingMode.DrawTriangles, QSGGeometry.DrawingMode.DrawLines)[kind]
            if i < len(self._nodes):
                child, geometry, material = self._nodes[i]
                geometry.allocate(len(vertices))
            else:
                geometry = QSGGeometry(self._attributes, len(vertices))
                material = QSGFlatColorMaterial()
                child = QSGGeometryNode()
                child.setGeometry(geometry)
                child.setMaterial(material)
                child.setFlag(QSGNode.Flag.OwnsGeometry, True)
                child.setFlag(QSGNode.Flag.OwnsMaterial, True)
                node.appendChildNode(child)
                self._nodes.append((child, geometry, material))
            geometry.setDrawingMode(mode)
            geometry.setLineWidth(1.)
            if vertices.nbytes:
                ctypes.memmove(int(geometry.vertexData()), vertices.ctypes.data, vertices.nbytes)
            material.setColor(colour)
            child.markDirty(QSGNode.DirtyStateBit.DirtyGeometry | QSGNode.DirtyStateBit.DirtyMaterial)
        self.uploads += 1
        return node


_registered = False


def register_geometry():
    global _registered
    if not _registered:
        qmlRegisterType(ModuleGeometry, 'Meridiana.Plan.Geometry', 1, 0, 'ModuleGeometry')
        _registered = True
