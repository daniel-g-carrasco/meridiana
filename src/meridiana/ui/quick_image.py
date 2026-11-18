"""A Qt Quick scene shown as a picture in a plain widget (R120, docs/prestazioni/README.md). A QQuickWidget makes Qt
compose the whole window through the graphics card at every frame, the panels and the charts included, even when the
3D view is hidden: on Daniel's 4K screen at 200 % every frame of a panel dragged cost 35-60 ms (25/10/2026). Here a
QQuickRenderControl has the scene drawn into a texture, the texture is read back into a QImage and the widget paints
the picture: the window stays on Qt's plain (raster) way of reaching the screen, and the widgets laid over the view
(the cube, the marks, the field of Move, the view's bar) stay as they are.

The part of QQuickWidget's interface the 3D view uses: `rootContext`, `setSource`, `status`, `errors`,
`rootObject`, `quickWindow`, `sceneGraphError`. The mouse and the wheel go to the scene as QQuickWidget sends them.
Without a graphics device (the offscreen platform of the tests) the scene is made and answers, but is not drawn."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QEvent, QPointF, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QWheelEvent
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickRenderControl, QQuickWindow
from PySide6.QtWidgets import QWidget

from .. import log

RESIZE_REST_MS = 90         # the size at rest this long: the scene drawn at it


class _Held:
    """What the widget holds of the graphics and the scene, let go in Qt's order (the targets and their textures before
    the device the render control holds, the scene and its window before the render control, the engine last) when
    the widget goes or the program closes. Not the widget's children: Qt deletes those before `destroyed` comes."""

    def __init__(self):
        self.control = QQuickRenderControl()
        self.quick = QQuickWindow(self.control)
        self.engine = QQmlEngine()
        self.component = None
        self.root = None
        self.texture = self.depth = self.target = self.passes = None

    def targets(self) -> None:
        import shiboken6
        from PySide6.QtQuick import QQuickRenderTarget
        if self.target is not None and self.quick is not None and shiboken6.isValid(self.quick):
            self.quick.setRenderTarget(QQuickRenderTarget())
        for thing in (self.target, self.passes, self.depth, self.texture):
            if thing is not None and shiboken6.isValid(thing):
                shiboken6.delete(thing)
        self.texture = self.depth = self.target = self.passes = None

    def release(self, *_args) -> None:
        import shiboken6
        self.targets()
        if self.root is not None and shiboken6.isValid(self.root):
            self.root.setParentItem(None)
        for thing in (self.root, self.quick, self.control, self.component, self.engine):
            if thing is not None and shiboken6.isValid(thing):
                shiboken6.delete(thing)
        self.root = self.quick = self.control = self.component = self.engine = None


class QuickImage(QWidget):
    sceneGraphError = Signal(object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)       # the picture covers every pixel
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.held = _Held()
        self.control, self.quick, self.engine = self.held.control, self.held.quick, self.held.engine
        self.quick.sceneGraphError.connect(lambda error, message: self.sceneGraphError.emit(error, message))
        self.destroyed.connect(self.held.release)
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.held.release)
        self.component: QQmlComponent | None = None
        self.root = None
        self.rhi = None
        self.image = QImage()
        self.ground = QColor("#20242a")       # until the first frame
        self.pixels = QSize()                 # the texture's size, device pixels
        self.stale = True                     # the picture no longer the scene: drawn again when shown
        self.dirty = True                     # the scene changed: polish and sync before the next frame
        self.frame = QTimer(self)
        self.frame.setSingleShot(True)
        self.frame.setInterval(0)
        self.frame.timeout.connect(self._render)
        # while the widget is being resized (a panel's edge dragged, the window resized) the last picture stays and
        # the scene is drawn again once the size rests: a frame at a new size costs a new texture and a full draw
        self.settle = QTimer(self)
        self.settle.setSingleShot(True)
        self.settle.setInterval(RESIZE_REST_MS)
        self.settle.timeout.connect(self._changed)
        self.control.renderRequested.connect(self._request)
        self.control.sceneChanged.connect(self._changed)
        try:
            if self.control.initialize() and self.control.rhi() is not None:
                self.rhi = self.control.rhi()
                # BGRA is the byte order of QImage's ARGB32 on Windows: the picture needs no conversion
                from PySide6.QtGui import QRhiTexture
                self.format = (QRhiTexture.Format.BGRA8 if self.rhi.isTextureFormatSupported(QRhiTexture.Format.BGRA8)
                               else QRhiTexture.Format.RGBA8)
        except RuntimeError as error:
            log.complain("3D view: graphics", error)

    # QQuickWidget's interface, the part the 3D view uses

    def rootContext(self):
        return self.engine.rootContext()

    def setSource(self, url: QUrl) -> None:
        self.component = self.held.component = QQmlComponent(self.engine, url)
        self.root = self.held.root = self.component.create() if self.component.isReady() else None
        if self.root is not None:
            self.root.setParentItem(self.quick.contentItem())
            self._fit()

    def status(self):
        return self.component.status() if self.component is not None else QQmlComponent.Status.Null

    def errors(self) -> list:
        return self.component.errors() if self.component is not None else []

    def rootObject(self):
        return self.root

    def quickWindow(self) -> QQuickWindow:
        return self.quick

    def drawn(self) -> bool:
        """Whether the scene is drawn here: False without a graphics device (the tests' offscreen platform)."""
        return self.rhi is not None

    # the size: the scene's items in the widget's units, the texture in the screen's pixels

    def _fit(self) -> None:
        if self.held.quick is None:
            return
        w, h = max(1, self.width()), max(1, self.height())
        self.quick.resize(w, h)
        if self.root is not None:
            self.root.setWidth(w)
            self.root.setHeight(h)
        self._changed()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.held.quick is None:
            return
        if self.image.isNull() or not event.oldSize().isValid():
            self._fit()
            return
        # the scene's items follow at once (the backend's camera and the overlays use the size), the picture later
        w, h = max(1, self.width()), max(1, self.height())
        self.quick.resize(w, h)
        if self.root is not None:
            self.root.setWidth(w)
            self.root.setHeight(h)
        self.frame.stop()
        self.settle.start()

    def showEvent(self, event) -> None:
        """Shown again (the File page closed, a phase with the 3D view): drawn again only if the scene changed or the
        size did while it was hidden; else the last picture (a full frame was 18 ms at every close of File, R120)."""
        super().showEvent(event)
        # on the next turn: Qt sends showEvent just before the widget is visible, and on Wayland the frame asked for
        # now found it still hidden and was never asked again (the 3D view stayed empty on Linux, 25/10/2026)
        QTimer.singleShot(0, self, self._shown)

    def _shown(self) -> None:
        if not self.isVisible():
            return
        size = self.image.deviceIndependentSize()
        if (self.stale or self.image.isNull() or abs(size.width() - self.width()) >= 1
                or abs(size.height() - self.height()) >= 1):
            self._changed()
        else:
            self.update()

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.DevicePixelRatioChange:
            self._changed()
        return super().event(event)

    def _target(self) -> bool:
        """The texture and its target at the widget's size in device pixels, made again when it changed."""
        from PySide6.QtGui import QRhiColorAttachment, QRhiRenderBuffer, QRhiTexture, QRhiTextureRenderTargetDescription
        from PySide6.QtQuick import QQuickRenderTarget
        ratio = self.devicePixelRatioF()
        size = QSize(max(1, round(self.width() * ratio)), max(1, round(self.height() * ratio)))
        h = self.held
        if size == self.pixels and h.target is not None:
            return True
        h.targets()
        self.pixels = QSize()
        h.texture = self.rhi.newTexture(self.format, size, 1,
                                        QRhiTexture.Flag.RenderTarget | QRhiTexture.Flag.UsedAsTransferSource)
        h.depth = self.rhi.newRenderBuffer(QRhiRenderBuffer.Type.DepthStencil, size, 1)
        if not (h.texture.create() and h.depth.create()):
            log.complain("3D view: graphics", RuntimeError("the view's texture could not be made"))
            return False
        h.target = self.rhi.newTextureRenderTarget(
            QRhiTextureRenderTargetDescription(QRhiColorAttachment(h.texture), h.depth))
        h.passes = h.target.newCompatibleRenderPassDescriptor()
        h.target.setRenderPassDescriptor(h.passes)
        if not h.target.create():
            log.complain("3D view: graphics", RuntimeError("the view's target could not be made"))
            return False
        target = QQuickRenderTarget.fromRhiRenderTarget(h.target)
        target.setDevicePixelRatio(ratio)
        self.quick.setRenderTarget(target)
        self.pixels = size
        self.dirty = True
        return True

    # the frames: drawn on the next turn of the loop, as many changes as come before it in one frame

    def _changed(self) -> None:
        self.dirty = True
        self._request()

    def _request(self) -> None:
        self.stale = True
        if self.rhi is not None and not self.frame.isActive() and not self.settle.isActive():
            self.frame.start()

    def _render(self) -> None:
        if self.rhi is None or self.held.control is None or self.root is None or not self.isVisible():
            return
        if not self._target():
            return
        from PySide6.QtGui import QRhiReadbackDescription, QRhiReadbackResult
        if self.dirty:
            self.control.polishItems()
        self.control.beginFrame()
        if self.dirty:
            self.control.sync()
            self.dirty = False
        self.control.render()
        result = QRhiReadbackResult()
        batch = self.rhi.nextResourceUpdateBatch()
        batch.readBackTexture(QRhiReadbackDescription(self.held.texture), result)
        self.control.commandBuffer().resourceUpdate(batch)
        self.control.endFrame()                             # an offscreen frame: the read back is done
        w, h = result.pixelSize.width(), result.pixelSize.height()
        bgra = self.format != self._rgba()
        image = QImage(result.data.data(), w, h, 4 * w, QImage.Format.Format_ARGB32_Premultiplied if bgra
                       else QImage.Format.Format_RGBA8888_Premultiplied)
        # out of the read back's memory, upright (OpenGL reads from the bottom) and in the byte order the raster
        # painter draws without converting at every paint (OpenGL and Vulkan give RGBA, Direct3D BGRA)
        if self.rhi.isYUpInFramebuffer():
            image = image.mirrored()
        if not bgra:
            image = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        elif not self.rhi.isYUpInFramebuffer():
            image = image.copy()
        image.setDevicePixelRatio(self.devicePixelRatioF())
        self.image = image
        self.stale = False
        self.update()

    @staticmethod
    def _rgba():
        from PySide6.QtGui import QRhiTexture
        return QRhiTexture.Format.RGBA8

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        if self.image.isNull():
            p.fillRect(self.rect(), self.ground)
            return
        size = self.image.deviceIndependentSize()
        if abs(size.width() - self.width()) < 1 and abs(size.height() - self.height()) < 1:
            p.drawImage(0, 0, self.image)
            return
        # while a resize settles: the last picture covering the widget, its proportions kept, centred
        k = max(self.width() / size.width(), self.height() / size.height())
        w, h = size.width() * k, size.height() * k
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawImage(QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h), self.image)

    # the pointer and the wheel to the scene, as QQuickWidget sends them

    def _send(self, event) -> bool:
        if self.held.quick is None:
            return False
        QCoreApplication.sendEvent(self.quick, event)
        return event.isAccepted()

    def _mouse(self, e: QMouseEvent) -> None:
        mapped = QMouseEvent(e.type(), e.position(), e.position(), e.globalPosition(), e.button(), e.buttons(),
                             e.modifiers(), e.pointingDevice())
        e.setAccepted(self._send(mapped))

    def mousePressEvent(self, e) -> None:
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self._mouse(e)

    def mouseReleaseEvent(self, e) -> None:
        self._mouse(e)

    def mouseMoveEvent(self, e) -> None:
        self._mouse(e)

    def mouseDoubleClickEvent(self, e) -> None:
        self._mouse(e)

    def wheelEvent(self, e) -> None:
        mapped = QWheelEvent(e.position(), e.globalPosition(), e.pixelDelta(), e.angleDelta(), e.buttons(),
                             e.modifiers(), e.phase(), e.inverted(), e.source(), e.pointingDevice())
        e.setAccepted(self._send(mapped))

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        # out of the scene: a move outside its items ends their hover (the MouseArea's onExited)
        outside = QPointF(-10000, -10000)
        self._send(QMouseEvent(QEvent.Type.MouseMove, outside, outside, self.mapToGlobal(outside.toPoint()).toPointF(),
                               Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))

    def release(self) -> None:
        """The scene and the graphics let go now (the window closing)."""
        self.frame.stop()
        self.rhi = None
        self.root = None
        self.held.release()
