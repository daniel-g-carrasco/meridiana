"""The 3D pictures of the report (R61, docs/compiti/19r-relazione.md): the project's scene from fixed viewpoints,
from the south-east and from the south-west, as parallel (axonometric) views on paper, for the Summary of the
complete template and the Overview of the compact one.

Rendered without a window on the screen: a QQuickWindow driven by a QQuickRenderControl draws qml/ReportScene.qml
into a texture of its own (Qt's RHI: Direct3D 11 on Windows, OpenGL or Vulkan elsewhere), and the texture is read
back as an image. Everything happens on the thread that asks, the main one, as the rest of the report's steps: the
Python instancing is called from there, never from a render thread (the lesson of the QQuickView in a container,
CLAUDE.md). The window's 3D view is not touched: its camera stays where the designer left it. The renderer is
made once and kept (`_RENDERER`): its first frame compiles the shaders (a third of a second, 25/10/2026), the next
ones take milliseconds. A hidden QQuickView grabbed with grabWindow() was tried first: every grab made the whole
device again (a second each) and a second grab of the same view came back empty.

Where Qt Quick runs on its software renderer, Qt Quick 3D cannot draw: Qt's offscreen platform chooses it unless
QT_QUICK_BACKEND=rhi is set (the tests, the CI). The render control then does not start, `available()` says so,
and the report leaves the pictures out rather than printing empty boxes. The pictures of the same scene are kept
(`_CACHE`): a preview made again after a change of the client does not render them again."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PySide6.QtCore import QBuffer, QByteArray, QCoreApplication, QIODevice, QObject, QSize, QUrl
from PySide6.QtGui import QColor, QImage, QQuaternion, QVector3D

from .. import camera, log, mesh, view_colours
from ..i18n import _

QML_FILE = Path(__file__).resolve().parent / "qml" / "ReportScene.qml"
SIZE = (1100, 720)               # pixels of a picture: about 8 cm wide in the report, some 340 dpi
ELEVATION = -30.0                # how far the views look down
MARGIN = 0.05                    # of the picture's width and height, free around the scene
EDGE_PX = 1.4                    # the width of the buildings' edges, pixels
CACHE_SIZE = 8
_RENDERER = None                 # the Renderer, once made; False when it could not be
_CACHE: dict = {}                # (the scene's digest, view, size) -> PNG bytes, the last CACHE_SIZE


def views() -> dict[str, tuple[float, float, str]]:
    """The viewpoints: id -> (where the camera looks, degrees from North; how far down; the caption)."""
    return {"south_east": (315.0, ELEVATION, _("From the south-east")),
            "south_west": (45.0, ELEVATION, _("From the south-west"))}


class Renderer:
    """The report's scene in a QQuickWindow that a QQuickRenderControl draws into a texture, `size` pixels; frames
    rendered on this thread and read back (`grab`). Raises RuntimeError when Qt Quick has no RHI here."""

    def __init__(self, size: tuple[int, int]):
        from PySide6.QtQml import QQmlComponent, QQmlEngine
        from PySide6.QtQuick import QQuickRenderControl, QQuickWindow
        from . import view3d  # noqa: F401  (the scene's Python types: BuildingsGeometry, ModulesInstancing...)
        self.control = QQuickRenderControl()
        self.window = QQuickWindow(self.control)
        self.engine = QQmlEngine()
        self.component = QQmlComponent(self.engine, QUrl.fromLocalFile(str(QML_FILE)))
        self.root = self.component.create()            # the component kept: the scene goes with it
        if self.root is None:
            raise RuntimeError(self.component.errorString())
        self.root.setParentItem(self.window.contentItem())
        if not self.control.initialize() or self.control.rhi() is None:
            raise RuntimeError("Qt Quick has no RHI here (the software renderer)")
        self.rhi = self.control.rhi()
        self.size = (0, 0)
        self._resize(size)

    def _resize(self, size: tuple[int, int]) -> None:
        from PySide6.QtGui import (QRhiColorAttachment, QRhiRenderBuffer, QRhiTexture,
                                   QRhiTextureRenderTargetDescription)
        from PySide6.QtQuick import QQuickRenderTarget
        w, h = size
        self.texture = self.rhi.newTexture(QRhiTexture.Format.RGBA8, QSize(w, h), 1,
                                           QRhiTexture.Flag.RenderTarget | QRhiTexture.Flag.UsedAsTransferSource)
        self.depth = self.rhi.newRenderBuffer(QRhiRenderBuffer.Type.DepthStencil, QSize(w, h), 1)
        if not (self.texture.create() and self.depth.create()):
            raise RuntimeError("the texture of the report's pictures could not be made")
        self.target = self.rhi.newTextureRenderTarget(
            QRhiTextureRenderTargetDescription(QRhiColorAttachment(self.texture), self.depth))
        self.passes = self.target.newCompatibleRenderPassDescriptor()
        self.target.setRenderPassDescriptor(self.passes)
        if not self.target.create():
            raise RuntimeError("the target of the report's pictures could not be made")
        target = QQuickRenderTarget.fromRhiRenderTarget(self.target)
        target.setDevicePixelRatio(1.0)                     # one pixel of the picture a unit of the scene's items
        self.window.setRenderTarget(target)
        self.window.resize(w, h)
        self.root.setWidth(w)
        self.root.setHeight(h)
        self.size = size

    def grab(self, size: tuple[int, int]) -> QImage:
        """A frame of the scene as it is set now, `size` pixels."""
        from PySide6.QtGui import QRhiReadbackDescription, QRhiReadbackResult
        if size != self.size:
            self._resize(size)
        self.control.polishItems()
        self.control.beginFrame()
        self.control.sync()
        self.control.render()
        result = QRhiReadbackResult()
        batch = self.rhi.nextResourceUpdateBatch()
        batch.readBackTexture(QRhiReadbackDescription(self.texture), result)
        self.control.commandBuffer().resourceUpdate(batch)
        self.control.endFrame()                             # an offscreen frame: the read back is done
        w, h = result.pixelSize.width(), result.pixelSize.height()
        image = QImage(bytes(result.data), w, h, QImage.Format.Format_RGBA8888_Premultiplied).copy()
        return image.mirrored() if self.rhi.isYUpInFramebuffer() else image

    def release(self) -> None:
        """Everything let go now and in Qt's order: the target and its texture (the RHI's) before the render control
        that holds the RHI, the scene and the window before the render control, the engine last. At the program's
        end a deleteLater would never run: the event loop has stopped."""
        import shiboken6
        from PySide6.QtQuick import QQuickRenderTarget
        self.window.setRenderTarget(QQuickRenderTarget())
        self.root.setParentItem(None)
        for thing in (self.target, self.passes, self.depth, self.texture, self.root, self.window, self.control,
                      self.component, self.engine):
            if shiboken6.isValid(thing):
                shiboken6.delete(thing)


def renderer():
    """The renderer of the process, made at the first call; None when it cannot be (said once in the log)."""
    global _RENDERER
    if _RENDERER is None:
        try:
            _RENDERER = Renderer(SIZE)
        except RuntimeError as error:
            log.complain("report 3D", RuntimeError(str(error)))      # a line, not a traceback: it is expected
            _RENDERER = False
        else:
            app = QCoreApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(release)
    return _RENDERER or None


def release() -> None:
    """The renderer let go (the program closing); the next picture makes another."""
    global _RENDERER
    if _RENDERER:
        _RENDERER.release()
    _RENDERER = None


def available() -> bool:
    """Whether Qt Quick 3D renders here without a window on the screen."""
    return renderer() is not None


def _digest(tri, table, segs, size) -> str:
    h = hashlib.sha1()
    for a in (*tri, table, segs):
        h.update(np.ascontiguousarray(a).tobytes())
    h.update(repr(size).encode())
    return h.hexdigest()


def _png(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data.data())


def render(project, results: dict, size: tuple[int, int] = SIZE) -> dict[str, bytes]:
    """Every view of the project's scene as PNG bytes, `size` pixels; {} when nothing is laid or when Qt Quick 3D
    cannot render here."""
    # the colours of the vertices and of the instances are taken as linear light: given so, the paper's sRGB
    # colours come out as they are written (the navy of the modules came out a light blue)
    paper = {k: tuple(c ** 2.2 for c in mesh.rgb(v)) for k, v in view_colours.D3_PAPER.items()}
    tri, table, segs = mesh.project_scene(project, results, paper)
    if not len(table):
        return {}
    key = _digest(tri, table, segs, size)
    if all((key, vid, size) in _CACHE for vid in views()):
        return {vid: _CACHE[(key, vid, size)] for vid in views()}
    r = renderer()
    if r is None:
        return {}
    root = r.root
    centres = table[:, [3, 7, 11]].astype(float)
    points = np.concatenate([tri[0].astype(float), centres]) if len(tri[0]) else centres
    lo, hi = points.min(axis=0), points.max(axis=0)
    reach = float(np.linalg.norm(hi - lo)) / 2 + 2.0
    root.setProperty("paper", QColor(view_colours.D3_PAPER["background"]))
    root.setProperty("groundColor", QColor(view_colours.D3_PAPER["ground"]))
    root.setProperty("groundCentre", QVector3D(float(lo[0] + hi[0]) / 2, 0.0, float(lo[2] + hi[2]) / 2))
    root.setProperty("groundHalf", 40.0 * reach)                 # beyond every edge of the picture
    root.setProperty("shadowFar", max(100.0, 6.0 * reach))
    root.findChild(QObject, "buildingsGeometry").set_mesh(*tri)
    root.findChild(QObject, "modulesTable").set_table(table)
    edges = root.findChild(QObject, "edgesGeometry")
    w, h = size
    out: dict[str, bytes] = {}
    for vid, (bearing, elevation, _caption) in views().items():
        cam = camera.axonometric(points, bearing, elevation, w / h, MARGIN)
        magnification = h / (2 * cam.half_height())          # pixels a metre
        edges.set_mesh(*mesh.ribbons(segs, EDGE_PX / magnification, paper["edge"]))
        root.setProperty("magnification", magnification)
        root.setProperty("cameraPosition", QVector3D(*map(float, cam.position)))
        root.setProperty("cameraRotation", QQuaternion(*map(float, cam.rotation)))
        image = r.grab(size)
        if image.isNull():
            return {}
        out[vid] = _png(image)
    while _CACHE and len(_CACHE) + len(out) > CACHE_SIZE:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE.update({(key, vid, size): png for vid, png in out.items()})
    return out


def picture(project, results: dict, vid: str, size: tuple[int, int] = SIZE) -> bytes:
    """One view as PNG bytes (b"" when it cannot be made): the report's steps ask for each image apart; the first
    renders them all, the others find them made."""
    return render(project, results, size).get(vid, b"")
