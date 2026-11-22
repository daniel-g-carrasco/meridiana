"""A real RHI render target without a platform window, for the motion benchmark only."""
import time

from PySide6.QtCore import QSize
from PySide6.QtGui import (QImage, QRhi, QRhiColorAttachment, QRhiD3D11InitParams, QRhiDriverInfo,
                          QRhiReadbackDescription, QRhiReadbackResult, QRhiTexture,
                          QRhiTextureRenderTargetDescription)
from PySide6.QtQuick import (QQuickGraphicsDevice, QQuickRenderControl, QQuickRenderTarget,
                            QQuickWindow)


class HardwareUnavailable(RuntimeError):
    """The requested hardware budget cannot be measured on this machine."""


class PlanRenderProbe:
    """Keep GPU submission and readback separate: screenshots never enter timing samples."""

    def __init__(self, item, size=(1434, 839), dpr=2):
        self.control = QQuickRenderControl()
        self.window = QQuickWindow(self.control)
        self.window.resize(*size)
        self.rhi = QRhi.create(QRhi.D3D11, QRhiD3D11InitParams(), QRhi.EnableTimestamps)
        if self.rhi is None:
            raise HardwareUnavailable('Direct3D11 could not create a hardware render target')
        info = self.rhi.driverInfo()
        if info.deviceType == QRhiDriverInfo.CpuDevice:
            raise HardwareUnavailable('Direct3D11 selected a CPU adapter, not a physical GPU')
        self.window.setGraphicsDevice(QQuickGraphicsDevice.fromRhi(self.rhi))
        if not self.control.initialize():
            self.window.deleteLater()
            raise HardwareUnavailable('QQuickRenderControl initialization failed: the hardware probe requires '
                                      'a compatible RHI backend (QT_QUICK_BACKEND=rhi QSG_RHI_BACKEND=d3d11)')
        self.texture = self.rhi.newTexture(QRhiTexture.RGBA8, QSize(int(size[0]*dpr), int(size[1]*dpr)),
                                           1, QRhiTexture.RenderTarget | QRhiTexture.UsedAsTransferSource)
        if not self.texture.create():
            raise RuntimeError('render texture creation failed')
        self.target = self.rhi.newTextureRenderTarget(
            QRhiTextureRenderTargetDescription(QRhiColorAttachment(self.texture)))
        self.pass_descriptor = self.target.newCompatibleRenderPassDescriptor()
        self.target.setRenderPassDescriptor(self.pass_descriptor)
        if not self.target.create():
            raise RuntimeError('render target creation failed')
        target = QQuickRenderTarget.fromRhiRenderTarget(self.target)
        target.setDevicePixelRatio(dpr)
        self.window.setRenderTarget(target)
        self.item = item
        self.old_parent = item.parentItem()
        item.setParentItem(self.window.contentItem())
        item.setWidth(size[0])
        item.setHeight(size[1])
        item.setVisible(True)
        self.samples = []

    def render(self, *, readback=False):
        start = time.perf_counter()
        self.control.polishItems()
        polished = time.perf_counter()
        self.control.beginFrame()
        self.control.sync()
        synced = time.perf_counter()
        self.control.render()
        rendered = time.perf_counter()
        result = None
        if readback:
            result = QRhiReadbackResult()
            batch = self.rhi.nextResourceUpdateBatch()
            batch.readBackTexture(QRhiReadbackDescription(self.texture), result)
            self.control.commandBuffer().resourceUpdate(batch)
        gpu = self.control.commandBuffer().lastCompletedGpuTime()*1000
        self.control.endFrame()
        ended = time.perf_counter()
        sample = dict(time=start, polish_ms=(polished-start)*1000, sync_ms=(synced-polished)*1000,
                      render_ms=(rendered-synced)*1000, submit_ms=(ended-rendered)*1000,
                      draw_ms=(ended-polished)*1000, gpu_ms=gpu if gpu > 0 else None)
        if not readback:
            self.samples.append(sample)
            return sample
        self.rhi.finish()
        image = QImage(result.data, result.pixelSize.width(), result.pixelSize.height(),
                       QImage.Format_RGBA8888).copy()
        return image

    def close(self):
        self.item.setParentItem(self.old_parent)
        self.control.invalidate()
        self.target.destroy()
        self.pass_descriptor.destroy()
        self.texture.destroy()
        self.window.deleteLater()


def image_motion(before, after, old, new, dpr=2):
    """Register rendered edges against the gesture's affine transform, in physical pixels.

    A separate readback pass, never a timing sample. Chrome is excluded. No camera-derived
    marker is substituted for the real pixels: an empty or uniform target is an error.
    """
    import numpy as np
    def grey(image):
        image = image.convertToFormat(QImage.Format_RGBA8888)
        rgba = np.frombuffer(image.bits(), np.uint8).reshape(image.height(), image.bytesPerLine())
        return rgba[:, :image.width()*4].reshape(image.height(), image.width(), 4)[:, :, :3].mean(axis=2)
    source, target = grey(before), grey(after)
    yy, xx = np.mgrid[100:target.shape[0]-80:4, 80:target.shape[1]-80:4]
    ratio = new[2]/old[2]
    sx = (old[0]*dpr+(xx-new[0]*dpr)/ratio).round().astype(int)
    sy = (old[1]*dpr+(yy-new[1]*dpr)/ratio).round().astype(int)
    valid = (sx > 6) & (sx < source.shape[1]-7) & (sy > 6) & (sy < source.shape[0]-7)
    sx, sy, xx, yy = sx[valid], sy[valid], xx[valid], yy[valid]
    edges = np.abs(source[sy, sx+1]-source[sy, sx-1])+np.abs(source[sy+1, sx]-source[sy-1, sx]) > 20
    sx, sy, xx, yy = sx[edges], sy[edges], xx[edges], yy[edges]
    if len(sx) < 30:
        raise RuntimeError('not enough rendered edges for a visual continuity measurement')
    scores = []
    expected = source[sy, sx]
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            scores.append((float(np.mean(np.abs(expected-target[yy+dy, xx+dx]))), dx, dy))
    error, dx, dy = min(scores)
    return dict(residual_px=[dx, dy], mean_edge_error=round(error, 3), edges=len(sx),
                changed_fraction=round(float(np.mean(np.abs(expected-target[yy, xx]) > 20)), 4))
