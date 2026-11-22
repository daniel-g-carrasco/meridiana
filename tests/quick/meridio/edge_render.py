"""Offscreen GPU readback of Character.qml, without a native surface or user settings."""
from pathlib import Path

import _setup  # noqa: F401
import numpy as np
from PySide6.QtCore import QSize, QUrl
from PySide6.QtGui import (QColor, QImage, QRhiColorAttachment, QRhiReadbackDescription,
                          QRhiReadbackResult, QRhiRenderBuffer, QRhiTexture,
                          QRhiTextureRenderTargetDescription)
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickRenderControl, QQuickRenderTarget, QQuickWindow
from shiboken6 import delete

from meridiana.gui.backend.assistant import QML, install_assistant


def edge_counts(image):
    """Count full/partial alpha on oblique exterior row crossings, excluding axis aligned edges and tips."""
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    alpha = np.frombuffer(image.bits(), dtype=np.uint8).reshape(image.height(), image.bytesPerLine())
    alpha = alpha[:, :image.width() * 4].reshape(image.height(), image.width(), 4)[:, :, 3]
    edges = []
    for row in alpha:
        xs = np.flatnonzero(row > 3)
        edges.append((int(xs[0]), int(xs[-1])) if len(xs) > 8 else None)
    hard = soft = 0
    for y in range(2, len(edges) - 2):
        if any(edges[k] is None for k in (y - 2, y, y + 2)):
            continue
        for side in (0, 1):
            before, x, after = (edges[k][side] for k in (y - 2, y, y + 2))
            if not 1 <= abs(after - before) <= 8 or not min(before, after) <= x <= max(before, after):
                continue
            if alpha[y, x] >= 250:
                hard += 1
            else:
                soft += 1
    return {'hard': hard, 'soft': soft}


class EdgeScene:
    def __init__(self, folder: Path, theme: str, style: str, dpr: float):
        self.control = QQuickRenderControl()
        self.window = QQuickWindow(self.control)
        self.window.setColor(QColor('transparent'))
        self.engine = QQmlEngine()
        self.errors = []
        self.engine.warnings.connect(lambda values: self.errors.extend(v.toString() for v in values))
        install_assistant(self.engine, theme={'theme': theme, 'reducedMotion': True})
        self.engine.addImportPath(str(QML.parent.parent))
        self.component = QQmlComponent(self.engine)
        ground = '#f4f4f4' if theme == 'light' else '#25282b'
        self.component.setData(f'''import QtQuick
Rectangle {{ width: 240; height: 240; color: "{ground}"
    ProbeCharacter {{ id: guy; objectName: "guy"; animated: false; x: 28; y: 28; width: 184; height: 184
        function turn(yaw, pitch) {{ pose.yaw = yaw; pose.pitch = pitch; publish() }}
    }}
}}'''.encode(), QUrl.fromLocalFile(str(folder / 'scene.qml')))
        self.root = self.component.create()
        if self.root is None:
            raise RuntimeError(self.component.errorString())
        self.root.setParentItem(self.window.contentItem())
        self.guy = self.root.childItems()[0]
        if not self.control.initialize() or self.control.rhi() is None:
            raise RuntimeError('No offscreen RHI available')
        self.rhi = self.control.rhi()
        self.dpr = dpr
        size = QSize(round(240 * dpr), round(240 * dpr))
        self.texture = self.rhi.newTexture(QRhiTexture.Format.RGBA8, size, 1,
            QRhiTexture.Flag.RenderTarget | QRhiTexture.Flag.UsedAsTransferSource)
        self.depth = self.rhi.newRenderBuffer(QRhiRenderBuffer.Type.DepthStencil, size, 1)
        assert self.texture.create() and self.depth.create()
        self.target = self.rhi.newTextureRenderTarget(
            QRhiTextureRenderTargetDescription(QRhiColorAttachment(self.texture), self.depth))
        self.passes = self.target.newCompatibleRenderPassDescriptor()
        self.target.setRenderPassDescriptor(self.passes)
        assert self.target.create()
        target = QQuickRenderTarget.fromRhiRenderTarget(self.target)
        target.setDevicePixelRatio(dpr)
        self.window.setRenderTarget(target)
        self.window.resize(240, 240)
        self.grab()

    def grab(self):
        self.control.polishItems()
        self.control.beginFrame()
        self.control.sync()
        self.control.render()
        result = QRhiReadbackResult()
        batch = self.rhi.nextResourceUpdateBatch()
        batch.readBackTexture(QRhiReadbackDescription(self.texture), result)
        self.control.commandBuffer().resourceUpdate(batch)
        self.control.endFrame()
        image = QImage(bytes(result.data), result.pixelSize.width(), result.pixelSize.height(),
                       QImage.Format.Format_RGBA8888_Premultiplied).copy()
        if self.rhi.isYUpInFramebuffer():
            image = image.flipped()
        image.setDevicePixelRatio(self.dpr)
        return image

    def close(self):
        self.window.setRenderTarget(QQuickRenderTarget())
        self.root.setParentItem(None)
        self.control.invalidate()
        for item in (self.target, self.passes, self.depth, self.texture, self.root, self.window,
                     self.control, self.component, self.engine):
            delete(item)
        assert not self.errors, self.errors
