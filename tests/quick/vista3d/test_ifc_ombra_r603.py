"""R603: an imported IFC model shown with its true geometry makes its shadow in the 3D view and receives the
shadows of the scene, at rest and while the view moves.

Daniel (14/11/2026): the buildings of the context shadowed the lawn, the IFC model in the middle did not. With the true
geometry in view the import's simple bodies are unseen and cast nothing (r21-ifc-vista: drawn, they made grey ghosts
and shades over the model), and the pieces of the true geometry cast nothing either. R603 made the pieces cast with
the camera at rest; then (14/11, after trying it) «turning the view they go away», and the model should also receive the shadows: the
pieces cast always and receive, their material (View3D/context.frag) keeps the CAD look of the file's colours and
takes a face in the sun's shadow down to the token d3 light_shade. A tower on the sun's side throws its shadow on the
model's roof.

The scene is drawn as the window draws it (Viewport.qml with SceneBackend) by a QQuickRenderControl into a texture,
as the report's pictures are. Off screen Qt Quick takes its software renderer, where Qt Quick 3D draws nothing, unless
QT_QUICK_BACKEND=rhi is set before the first window of the process: the pictures are made in a process of their own
(`python -m <this module> --render FOLDER`), and the test is skipped where Qt has no RHI at all.
The sample (tests/data/ifc/r575-sintetico.ifc): one body «Edificio», 10 x 8 m, 3.3 m high; nothing else casts."""
from pathlib import Path
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / 'tests' / 'data' / 'ifc' / 'r575-sintetico.ifc'
SIZE = 640
NO_RHI = 3                      # the exit code of the picture process where Qt Quick has no RHI
SHARES = (.2, .45, .7)          # where the lawn is read, as shares of the shadow's length past the body's edge
SOURCE = b'''import QtQuick
import Meridiana.View3D
Item {
    property Item view: viewport
    Viewport { id: viewport; anchors.fill: parent; sceneBackend: sceneBackendObject; showTools: false }
}'''


class Offscreen:
    """The 3D view of a session drawn into a texture by a QQuickRenderControl and read back."""

    def __init__(self, session, cache: Path):
        from PySide6.QtCore import QSize, QUrl
        from PySide6.QtGui import QRhiColorAttachment, QRhiRenderBuffer, QRhiTexture, QRhiTextureRenderTargetDescription
        from PySide6.QtQml import QQmlComponent, QQmlEngine
        from PySide6.QtQuick import QQuickRenderControl, QQuickRenderTarget, QQuickWindow
        from meridiana.gui.backend.scene_host import QML_ROOT, install
        from meridiana.gui.backend.scene_jobs import SceneLayouts
        from meridiana.gui.backend.tokens import install_theme
        self.control = QQuickRenderControl()
        self.window = QQuickWindow(self.control)
        self.engine = QQmlEngine()
        self.warnings = []
        self.engine.warnings.connect(lambda errors: self.warnings.extend(e.toString() for e in errors))
        self.backend = install(self.engine, session, cache)
        self.layouts = SceneLayouts(session, self.backend)
        self.layouts.begin()
        self.theme = install_theme(self.engine, {'theme': 'light'})
        self.component = QQmlComponent(self.engine)
        self.component.setData(SOURCE, QUrl.fromLocalFile(str(QML_ROOT / 'SceneHost.qml')))
        self.root = self.component.create()
        if self.root is None:
            raise RuntimeError('\n'.join(e.toString() for e in self.component.errors()))
        self.root.setParentItem(self.window.contentItem())
        self.view = self.root.property('view')
        self.rhi = self.control.rhi() if self.control.initialize() else None
        if self.rhi is None:
            return
        self.texture = self.rhi.newTexture(QRhiTexture.Format.RGBA8, QSize(SIZE, SIZE), 1,
                                           QRhiTexture.Flag.RenderTarget | QRhiTexture.Flag.UsedAsTransferSource)
        self.depth = self.rhi.newRenderBuffer(QRhiRenderBuffer.Type.DepthStencil, QSize(SIZE, SIZE), 1)
        self.texture.create()
        self.depth.create()
        self.target = self.rhi.newTextureRenderTarget(
            QRhiTextureRenderTargetDescription(QRhiColorAttachment(self.texture), self.depth))
        self.passes = self.target.newCompatibleRenderPassDescriptor()
        self.target.setRenderPassDescriptor(self.passes)
        self.target.create()
        target = QQuickRenderTarget.fromRhiRenderTarget(self.target)
        target.setDevicePixelRatio(1.0)
        self.window.setRenderTarget(target)
        self.window.resize(SIZE, SIZE)
        self.root.setWidth(SIZE)
        self.root.setHeight(SIZE)

    def grab(self):
        from PySide6.QtGui import QImage, QRhiReadbackDescription, QRhiReadbackResult
        self.control.polishItems()
        self.control.beginFrame()
        self.control.sync()
        self.control.render()
        result = QRhiReadbackResult()
        batch = self.rhi.nextResourceUpdateBatch()
        batch.readBackTexture(QRhiReadbackDescription(self.texture), result)
        self.control.commandBuffer().resourceUpdate(batch)
        self.control.endFrame()
        size = result.pixelSize
        image = QImage(bytes(result.data), size.width(), size.height(), QImage.Format.Format_RGBA8888_Premultiplied)
        return image.mirrored() if self.rhi.isYUpInFramebuffer() else image.copy()

    def close(self):
        """Everything let go in Qt's order, as gui/paper/report_3d.py does: the target and its texture before the
        render control that holds the RHI, the scene and the window before the render control, the engine last."""
        import shiboken6
        from PySide6.QtQuick import QQuickRenderTarget
        self.layouts.close()
        self.backend.close()
        self.window.setRenderTarget(QQuickRenderTarget())
        self.root.setParentItem(None)
        for thing in (self.target, self.passes, self.depth, self.texture, self.root, self.window, self.control,
                      self.component, self.engine):
            if shiboken6.isValid(thing):
                shiboken6.delete(thing)


def along(sun: dict, ring: np.ndarray, sign: float, beyond: float) -> tuple[float, float]:
    """A point of the lawn `beyond` metres past the body's edge, away from the sun (sign 1) or towards it (-1)."""
    b = math.radians(sun['bearing'])
    dx, dy = -sign * math.sin(b), -sign * math.cos(b)                  # east, north
    cx, cy = ring.mean(0)
    hx, hy = np.ptp(ring[:, 0]) / 2, np.ptp(ring[:, 1]) / 2
    edge = min(hx / abs(dx) if abs(dx) > 1e-9 else math.inf, hy / abs(dy) if abs(dy) > 1e-9 else math.inf)
    return cx + dx * (edge + beyond), cy + dy * (edge + beyond)


def old_opengl(rhi) -> bool:
    """Whether the RHI is an OpenGL below 3.3 (Qt's offscreen OpenGL without a graphics card, the CI's Linux): Qt
    Quick 3D has no shaders for it and draws the sky alone, no model and no shadow (22/11/2026, Mesa llvmpipe in the
    WSL). Its default surface format cannot be raised there: the application then stops at its start."""
    from PySide6.QtGui import QOpenGLContext, QRhi
    if rhi.backend() != QRhi.Implementation.OpenGLES2:
        return False
    context = QOpenGLContext.currentContext()
    if context is None or context.isOpenGLES():
        return False
    version = context.format().version()
    return tuple(version) < (3, 3)


def render(out: Path) -> int:
    """The process of the pictures: the sample imported, the sun low in the west, the scene from above with the
    shadows on (lit.png) and off (unlit.png), and where the points read by the test fall (points.json)."""
    os.environ.update({'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'rhi', 'QSG_RENDER_LOOP': 'basic'})
    from PySide6.QtCore import QObject
    from PySide6.QtWidgets import QApplication
    from meridiana import i18n
    from meridiana.app import jobs
    from meridiana.app.exchange import ifc_import, ifc_worker
    from meridiana.app.session import ProjectSession
    from meridiana.core.model import model
    from quick.vista3d._fidelity_support import data, settle
    app = QApplication.instance() or QApplication([])
    i18n.setup('it')
    found = ifc_worker.read(str(SAMPLE), 'direct', lambda f, w: None, None, str(out / 'cache'))
    project = model.Project()
    ifc_import.apply(project, ifc_import.plan(found, project, 'origin', None, name='t', source_name='t.ifc'))
    body = next(b for b in project.buildings if b.name == 'Edificio')
    sun = None
    for step in range(15 * 6, 21 * 6):               # 21 June, an afternoon sun 12-20 degrees high in the west
        sun = dict(sun_position(project, 2026, 6, 21, step / 6))
        if 12 <= sun['elevation'] <= 20 and 240 <= sun['bearing'] <= 300:
            break
    ring = np.asarray(body.footprint, float)
    tower, roof = tower_over(sun, ring, body.ridge())
    project.buildings.append(model.Building(id='torre', name='Torre', footprint=tower['footprint'],
                                            height=tower['height']))
    session = ProjectSession(project)
    results, keys, _ = jobs.layout_of(project, {})
    session.layout_done(session.generation, results, keys)
    host = Offscreen(session, out / 'scene')
    if host.rhi is None or old_opengl(host.rhi):
        return NO_RHI
    view, backend = host.view, host.backend
    view.setProperty('reducedMotion', True)
    settle(app, .3)
    backend.setSun(2026, 6, 21, step / 6)
    length = body.ridge() / math.tan(math.radians(sun['elevation']))
    pieces = [n for n in host.root.findChildren(QObject) if n.objectName().startswith('ifc-context:')]

    def casting():
        return [bool(n.property('castsShadows')) for n in pieces]

    def picture(name):
        for _ in range(3):
            image = host.grab()
        image.save(str(out / f'{name}.png'))
    above = {'position': [0.0, 3.3 * length, 0.0], 'rotation': [math.sqrt(.5), -math.sqrt(.5), 0, 0],
             'target': [0.0, 0.0, 0.0], 'fov': 60.0, 'ortho': False}
    view.setProperty('userMoved', True)                                  # from straight above, the shadow in view
    view.setProperty('cameraState', dict(above, position=[0.5, 3.3 * length, 0.0]))
    settle(app, .5)
    view.setProperty('cameraState', above)
    # the camera just moved: drawn at once, without the events that would let its rest timer fire
    moving = {'casting': casting(), 'resting': bool(view.property('cameraResting'))}
    picture('moving')
    moving['resting_after'] = bool(view.property('cameraResting'))
    settle(app, .5)                                                      # at rest
    resting = {'casting': casting(), 'resting': bool(view.property('cameraResting'))}
    for name, shadows in (('lit', True), ('unlit', False)):
        view.setProperty('shadows', shadows)
        settle(app, .2)
        picture(name)

    def pixel(east, north, up=0.0):
        return data(view, f'projectPoint([{east}, {up}, {-north}])')
    points = {'sunny': pixel(*along(sun, ring, -1, 2.0)),
              'shade': [pixel(*along(sun, ring, 1, share * length)) for share in SHARES],
              'roof': [pixel(*p, body.ridge()) for p in roof['sunny']],
              'roof_shade': [pixel(*p, body.ridge()) for p in roof['shade']]}
    faint = host.root.findChild(QObject, 'buildingsFaint')
    (out / 'points.json').write_text(json.dumps({
        'sun': {k: sun[k] for k in ('elevation', 'bearing')}, 'points': points, 'warnings': host.warnings,
        'context': len(backend.contextModels), 'faint_casts': bool(faint.property('castsShadows')),
        'moving': moving, 'resting': resting}), 'utf-8')
    host.close()
    return 0


def sun_position(project, year, month, day, hour) -> dict:
    """The sun of the 3D view (backend/scene.py, setSun) before the scene exists: its elevation and bearing."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from meridiana.core.geometry import sun
    from meridiana.core.rules import registry
    when = datetime(year, month, day, tzinfo=ZoneInfo(registry.effective_timezone(project))) + timedelta(
        minutes=min(1430, max(0, round(hour * 6) * 10)))
    pos = sun.position(project.site.lat, project.site.lon, when)
    return {'elevation': pos.apparent, 'bearing': pos.bearing}


def tower_over(sun: dict, ring: np.ndarray, ridge: float) -> tuple[dict, dict]:
    """A narrow tower on the sun's side of the body whose shadow crosses one side of its roof (R603: the model receives
    the shadows of the scene). The roof's points in that shadow, and points of the other side in the sun, 2.5 m off
    the line of the lawn's points so that the tower's shadow does not reach those."""
    b = math.radians(sun['bearing'])
    s = np.array([math.sin(b), math.cos(b)])                            # towards the sun, east and north
    across = np.array([-s[1], s[0]])
    centre = ring.mean(0)
    half = np.ptp(ring, axis=0) / 2
    target = centre + 2.5 * across
    edge = min((half[k] - (target[k] - centre[k]) * np.sign(s[k])) / abs(s[k]) for k in (0, 1) if abs(s[k]) > 1e-9)
    foot = target + s * (edge + 4.0)
    rise = math.tan(math.radians(sun['elevation']))
    tower = {'footprint': [[float(foot[0] + dx), float(foot[1] + dy)] for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1))],
             'height': float(ridge + (edge + 5.0) * rise + 3.0)}
    roof = {'shade': [target.tolist(), (target - 1.5 * s).tolist()],
            'sunny': [(centre - 2.5 * across).tolist(), (centre - 2.5 * across + 2.0 * s).tolist(),
                      (centre - 2.5 * across - 2.0 * s).tolist()]}
    return tower, roof


class ModelShadowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = Path(cls.tmp.name)
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(str(p) for p in (ROOT / 'src', ROOT / 'tests')),
                   QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='rhi', QSG_RENDER_LOOP='basic')
        done = subprocess.run([sys.executable, '-m', 'quick.vista3d.test_ifc_ombra_r603', '--render', str(out)],
                              cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        if done.returncode == NO_RHI:
            cls.tmp.cleanup()
            raise unittest.SkipTest('Qt Quick has no RHI here, or an OpenGL below 3.3: the 3D is not drawn off screen')
        if done.returncode != 0:
            cls.tmp.cleanup()
            raise AssertionError(f'the pictures were not made ({done.returncode}):\n{done.stderr[-3000:]}')
        cls.found = json.loads((out / 'points.json').read_text('utf-8'))
        cls.lit = cls.read(out / 'lit.png')
        cls.unlit = cls.read(out / 'unlit.png')
        cls.moving = cls.read(out / 'moving.png')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @staticmethod
    def read(path: Path) -> np.ndarray:
        from PySide6.QtGui import QImage
        from ._fidelity_support import pixels
        return pixels(QImage(str(path))).astype(float)

    def patch(self, image, point, r=3) -> float:
        """The mean brightness of a few pixels around a point of the picture."""
        x, y = (int(round(v)) for v in point)
        self.assertTrue(r <= x < SIZE - r and r <= y < SIZE - r, point)
        return float(image[y - r:y + r + 1, x - r:x + r + 1, :3].mean())

    def test_the_model_casts_also_while_the_camera_moves(self):
        """Daniel (14/11/2026): turning the view the model's shadow went away. Its pieces cast at rest and in motion
        (R603); the picture «moving» is drawn before the camera's rest timer fires."""
        moving, resting = self.found['moving'], self.found['resting']
        self.assertTrue(moving['casting'])
        self.assertTrue(all(moving['casting']) and all(resting['casting']), self.found)
        self.assertFalse(moving['resting'] or moving['resting_after'], 'the picture «moving» was not drawn in motion')
        self.assertTrue(resting['resting'])

    def test_the_picture_is_the_model_s(self):
        self.assertGreater(self.found['context'], 0, 'the true geometry of the model is shown')
        self.assertEqual(self.found['warnings'], [])
        self.assertTrue(12 <= self.found['sun']['elevation'] <= 20, self.found['sun'])

    def test_the_model_shades_the_lawn_away_from_the_sun(self):
        for name, image in (('at rest', self.lit), ('moving', self.moving)):
            sunny = self.patch(image, self.found['points']['sunny'])
            shades = []
            for share, point in zip(SHARES, self.found['points']['shade'], strict=True):
                with self.subTest(name, share=share):
                    shade = self.patch(image, point)
                    shades.append(shade)
                    self.assertLess(shade, sunny - 15, 'the lawn in the model\'s shadow is not darker than the sunny lawn')
                    self.assertLess(shade, self.patch(self.unlit, point) - 15, 'no shadow of the model on the lawn')
            # one tone, as the other buildings' shadows: with the colour in the shadow map it was a pattern of the faces
            self.assertLess(max(shades) - min(shades), 6, f'{name}: the shadow is not one tone: {shades}')

    def test_the_model_receives_the_shadow_of_the_scene(self):
        """R603: the tower's shadow darkens the model's roof, at rest and in motion, to a shade still readable (the
        tokens d3 light_shade, light_sun); the roof in the sun keeps its look, without spots (no shadow acne)."""
        for name, image in (('at rest', self.lit), ('moving', self.moving)):
            for k, point in enumerate(self.found['points']['roof_shade']):
                with self.subTest(name, roof_shade=k):
                    shade, plain = self.patch(image, point, r=2), self.patch(self.unlit, point, r=2)
                    self.assertLess(shade, plain - 15, 'the tower\'s shadow is not on the roof')
                    self.assertGreater(shade, plain * .5, 'the roof in the shadow is too dark to read')
            for k, point in enumerate(self.found['points']['roof']):
                with self.subTest(name, roof=k):
                    self.assertAlmostEqual(self.patch(image, point, r=2), self.patch(self.unlit, point, r=2), delta=6)

    def test_no_shadow_with_the_shadows_off(self):
        sunny = self.patch(self.unlit, self.found['points']['sunny'])
        for share, point in zip(SHARES, self.found['points']['shade'], strict=True):
            with self.subTest(share=share):
                self.assertAlmostEqual(self.patch(self.unlit, point), sunny, delta=4)

    def test_the_sunny_lawn_is_not_marked_and_no_second_shadow(self):
        """The sunny lawn is the same with the shadows on and off. The import's unseen body casts none
        (r21-ifc-vista: «grey ghosts and shades over the model»): no second shadow."""
        point = self.found['points']['sunny']
        self.assertAlmostEqual(self.patch(self.lit, point), self.patch(self.unlit, point), delta=3)
        self.assertFalse(self.found['faint_casts'])


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--render':
        sys.exit(render(Path(sys.argv[2])))
    unittest.main()
