"""D3D11 rendered pixels and input journeys. Run explicitly with MERIDIANA_QUICK_3D_NATIVE=1."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
import unittest

import numpy as np
from PySide6.QtCore import QCoreApplication, QEvent, QPointF, Qt, QSize
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent, QNativeGestureEvent, QPointingDevice, QInputDevice
from PySide6.QtQml import QQmlExpression, QQmlEngine
from PySide6.QtQuick import QSGRendererInterface, QQuickWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtQuickControls2 import QQuickStyle

from meridiana import camera, i18n, jobs, model
from meridiana.session import ProjectSession
from meridiana.quick.backend.scene_host import SceneWindow

ROOT = Path(__file__).resolve().parents[3]
NATIVE = os.environ.get('MERIDIANA_QUICK_3D_NATIVE') == '1'


def pixels(image):
    image = image.convertToFormat(image.Format.Format_RGBA8888)
    return np.frombuffer(image.bits(), np.uint8).reshape(image.height(), image.width(), 4).copy()


@unittest.skipUnless(NATIVE, 'Real Windows D3D11 probe is explicitly enabled in its own process')
class NativeSceneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Direct3D11)
        QQuickStyle.setStyle('Basic')
        cls.app = QApplication.instance() or QApplication([])
        i18n.setup('it')
        cls.out = ROOT / 'build/quick-foto/r12-vista3d/native-exact'
        cls.out.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=self.out)
        p = model.Project(name='Native scene test')
        p.buildings.append(model.Building('b1','Capannone',[[0,0],[40,0],[40,20],[0,20]],height=9.5))
        p.subfields.append(model.SubField('s1','Sud',[[1,1],[39,1],[39,19],[1,19]],building='b1',
                                         params={'tilt':15.},filled=True))
        self.session = ProjectSession(p)
        results, keys, _ = jobs.layout_of(p, {})
        self.session.layout_done(self.session.generation, results, keys)
        self.host = SceneWindow(self.session, Path(self.tmp.name))
        self.host.window.show()
        self.wait(0.35)
        self.host.view.setProperty('reducedMotion', True)

    def tearDown(self):
        self.assertFalse(self.host.warnings)
        self.host.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.tmp.cleanup()

    def wait(self, seconds=0.12):
        until = time.perf_counter()+seconds
        while time.perf_counter() < until:
            self.app.processEvents()
            time.sleep(0.004)

    def js(self, source):
        expression = QQmlExpression(QQmlEngine.contextForObject(self.host.view), self.host.view, source)
        value = expression.evaluate()
        self.assertFalse(expression.hasError(), expression.error().toString())
        return value[0] if isinstance(value, tuple) else value

    def state(self):
        return json.loads(self.js('JSON.stringify(cameraState)'))

    def mouse(self, kind, x, y, button=Qt.MouseButton.NoButton, buttons=Qt.MouseButton.NoButton,
              mods=Qt.KeyboardModifier.NoModifier):
        p = QPointF(x,y)
        event = QMouseEvent(kind, p, p, p, button, buttons, mods)
        QCoreApplication.sendEvent(self.host.window,event)
        self.app.processEvents()

    def key(self, kind, key, mods=Qt.KeyboardModifier.NoModifier):
        QCoreApplication.sendEvent(self.host.window,QKeyEvent(kind,key,mods))
        self.app.processEvents()

    def shot(self, name):
        self.wait()
        image = self.host.window.grabWindow()
        self.assertFalse(image.isNull())
        scale = self.host.window.devicePixelRatio()
        self.assertEqual((image.width(),image.height()),
                         (round(self.host.window.width()*scale),round(self.host.window.height()*scale)))
        image.save(str(self.out/f'{name}-s{scale:g}.png'))
        return pixels(image)

    def test_pixels_modules_shadows_and_six_sizes_themes(self):
        self.assertEqual(self.app.platformName(),'windows')
        self.assertEqual(self.host.window.rendererInterface().graphicsApi(),QSGRendererInterface.GraphicsApi.Direct3D11)
        for width,height in ((1366,900),(1600,960),(1920,1080)):
            self.host.window.setMinimumSize(QSize(width,height))
            self.host.window.resize(width,height)
            self.js('fitScene()')
            for dark in (False,True):
                self.host.theme.configure({'theme':'dark' if dark else 'light'})
                original=self.shot(f'{width}x{height}-'+('dark' if dark else 'light'))
                self.assertEqual((self.host.window.width(),self.host.window.height()),(width,height))
                self.host.view.setProperty('modulesVisible',False)
                absent=self.shot('without-modules')
                self.host.view.setProperty('modulesVisible',True)
                self.host.view.setProperty('shadows',False)
                unshadowed=self.shot('without-shadows')
                self.host.view.setProperty('shadows',True)
                self.assertGreater(np.count_nonzero(np.max(np.abs(original.astype(int)-absent.astype(int)),2)>15),1000)
                self.assertGreater(np.count_nonzero(np.max(np.abs(original.astype(int)-unshadowed.astype(int)),2)>15),1000)

    def test_navigation_real_events_no_python_callbacks_and_pick(self):
        before=self.state()
        calls=dict(self.host.backend.calls)
        self.mouse(QEvent.Type.MouseButtonPress,600,400,Qt.MouseButton.RightButton,Qt.MouseButton.RightButton)
        for i in range(1,31):
            self.mouse(QEvent.Type.MouseMove,600+i*3,400+i,buttons=Qt.MouseButton.RightButton)
        self.mouse(QEvent.Type.MouseButtonRelease,690,430,Qt.MouseButton.RightButton)
        self.assertNotEqual(before,self.state())
        self.assertEqual(calls,dict(self.host.backend.calls))
        orbit=self.state()
        self.key(QEvent.Type.KeyPress,Qt.Key.Key_Space)
        for i in range(15): self.mouse(QEvent.Type.MouseMove,690+i*2,430)
        self.key(QEvent.Type.KeyRelease,Qt.Key.Key_Space)
        self.assertNotEqual(orbit['position'],self.state()['position'])
        self.assertEqual(orbit['rotation'],self.state()['rotation'])
        self.assertEqual(calls,dict(self.host.backend.calls))
        self.key(QEvent.Type.KeyPress,Qt.Key.Key_F)
        self.js('home()')
        # Picking uses the renderer's last camera, so wait for this orientation's frame.
        self.wait()
        # A real ray pick on the central wall, not a synthetic backend selection.
        point=json.loads(self.js('JSON.stringify(projectPoint([20,5,0]))'))
        self.mouse(QEvent.Type.MouseButtonPress,*point,Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton)
        self.mouse(QEvent.Type.MouseButtonRelease,*point,Qt.MouseButton.LeftButton)
        self.assertEqual(self.session.selection,('building','b1'))
        self.shot('selected-wall')

    def test_r365_real_drag_pixels_cancel_commit_and_undo(self):
        self.session.select('building','b1')
        self.host.view.setProperty('editVertices',True)
        before=self.session.snapshot()
        self.shot('vertices-before')
        point=json.loads(self.js('JSON.stringify(projectPoint(sceneBackend.vertices[0].point))'))
        self.mouse(QEvent.Type.MouseButtonPress,*point,Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton)
        self.mouse(QEvent.Type.MouseMove,point[0],point[1]-50,buttons=Qt.MouseButton.LeftButton)
        self.wait(0.10)
        preview=self.shot('vertices-live')
        self.assertEqual(self.session.snapshot(),before)
        self.assertIsNotNone(self.host.backend._trial)
        self.key(QEvent.Type.KeyPress,Qt.Key.Key_Escape)
        self.mouse(QEvent.Type.MouseButtonRelease,point[0],point[1]-50,Qt.MouseButton.LeftButton)
        restored=self.shot('vertices-cancel')
        self.assertGreater(np.count_nonzero(preview!=restored),1000)
        self.assertEqual(self.session.snapshot(),before)
        self.mouse(QEvent.Type.MouseButtonPress,*point,Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton)
        self.mouse(QEvent.Type.MouseMove,point[0],point[1]-40,buttons=Qt.MouseButton.LeftButton)
        self.mouse(QEvent.Type.MouseButtonRelease,point[0],point[1]-40,Qt.MouseButton.LeftButton)
        self.assertGreater(self.session.project.buildings[0].height,9.5)
        self.assertEqual(self.session.undo.count(),1)
        self.key(QEvent.Type.KeyPress,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.session.snapshot(),before)

    def test_wheel_zoom_is_cursor_anchored(self):
        point=[20,9.5,-10]
        pos=json.loads(self.js(f'JSON.stringify(projectPoint({point}))'))
        hit=json.loads(self.js(f'JSON.stringify(hitAt({pos[0]},{pos[1]}))'))
        anchor=hit['point']
        anchor_before=json.loads(self.js(f'JSON.stringify(projectPoint({anchor}))'))
        before=self.state()
        event=QWheelEvent(QPointF(*pos),QPointF(*pos),QPointF(0,0).toPoint(),QPointF(0,120).toPoint(),
                          Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
        QCoreApplication.sendEvent(self.host.window,event)
        after=self.state()
        self.assertNotEqual(before['position'],after['position'])
        anchor_after=json.loads(self.js(f'JSON.stringify(projectPoint({anchor}))'))
        np.testing.assert_allclose(anchor_after,anchor_before,atol=1.)

    def test_native_touchpad_zoom_and_scroll_pan_without_python(self):
        device=QPointingDevice('Test trackpad',99,QInputDevice.DeviceType.TouchPad,
            QPointingDevice.PointerType.Finger,QInputDevice.Capability.Position,2,0)
        point=QPointF(600,450)
        def gesture(kind,value=0.):
            event=QNativeGestureEvent(kind,device,2,point,point,point,value,QPointF())
            QCoreApplication.sendEvent(self.host.window,event)
            self.app.processEvents()
        calls=dict(self.host.backend.calls)
        before=self.state()
        gesture(Qt.NativeGestureType.BeginNativeGesture)
        gesture(Qt.NativeGestureType.ZoomNativeGesture,.2)
        zoomed=self.state()
        self.assertNotEqual(before['position'],zoomed['position'])
        expected=camera.Camera(position=np.array(before['position']),rotation=np.array(before['rotation']),
                               target=np.array(before['target']))
        expected.zoom(np.log(1.2)/np.log(1/camera.ZOOM_STEP),
                      expected.zoom_point(600,450,1366,self.host.view.property('sceneHeight')))
        np.testing.assert_allclose(zoomed['position'],expected.position,atol=1e-6)
        gesture(Qt.NativeGestureType.EndNativeGesture)
        scroll=QWheelEvent(point,point,QPointF(24,12).toPoint(),QPointF().toPoint(),
            Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.ScrollUpdate,False)
        QCoreApplication.sendEvent(self.host.window,scroll)
        self.assertNotEqual(zoomed['position'],self.state()['position'])
        self.assertEqual(zoomed['rotation'],self.state()['rotation'])
        self.assertEqual(dict(self.host.backend.calls),calls)

    def test_move_handle_preview_pixels_commit_and_relayout(self):
        self.session.select('building','b1')
        self.host.view.setProperty('moveMode',True)
        self.host.view.setProperty('editVertices',True)  # The actual workbench enables both.
        state=self.state()
        cam=camera.Camera(position=np.asarray(state['position']),rotation=np.asarray(state['rotation']),
                          target=np.asarray(state['target']))
        centre=self.host.backend.gizmo['centre']
        size=cam.pixel_size(centre,self.host.window.height())*90
        point=json.loads(self.js(f'JSON.stringify(projectPoint({[centre[0]+size*.75,centre[1],centre[2]]}))'))
        before=self.session.snapshot()
        old=self.shot('move-before')
        self.mouse(QEvent.Type.MouseButtonPress,*point,Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton)
        self.mouse(QEvent.Type.MouseMove,point[0]+50,point[1],buttons=Qt.MouseButton.LeftButton)
        self.wait(.1)
        self.assertIsNotNone(self.host.backend._trial)
        self.assertEqual(self.session.snapshot(),before)
        self.assertEqual(self.state(),state,'Moving an object must not refit the camera around its preview')
        moved=self.shot('move-live')
        self.assertGreater(np.count_nonzero(old!=moved),1000,
                           {'drag':self.js('JSON.stringify(gizmoDrag)'), 'value':self.js('JSON.stringify(gizmoValue)'),
                            'motion':self.host.backend._transform_motion, 'calls':dict(self.host.backend.calls)})
        self.mouse(QEvent.Type.MouseButtonRelease,point[0]+50,point[1],Qt.MouseButton.LeftButton)
        self.wait(.35)
        self.assertNotEqual(self.session.snapshot(),before)
        results,keys,_=jobs.layout_of(self.session.project,{})
        self.assertEqual(self.session.layout_keys,keys)
        np.testing.assert_allclose(self.host.backend.module_table[:,:12],results['s1'].table[:,:12])
        self.assertEqual(self.session.undo.count(),1)

    def test_detached_coincident_vertices_can_both_be_picked(self):
        def pitched(p): p.buildings[0].roof=model.Roof(type='gable',tilt=20)
        self.session.edit('Pitched roof',pitched)
        self.session.select('building','b1')
        self.host.backend.beginVertex(2,False)
        self.host.backend.vertexAction('detach')
        self.host.view.setProperty('editVertices',True)
        points=[v['point'] for v in self.host.backend.vertices]
        pair=next((i,j) for i in range(len(points)) for j in range(i+1,len(points)) if points[i]==points[j])
        at=json.loads(self.js(f'JSON.stringify(projectPoint({points[pair[0]]}))'))
        picks=[self.js(f'vertexAt({at[0]},{at[1]},true)') for _ in range(2)]
        self.assertEqual(set(picks),set(pair))

    def test_modes_selection_and_sun_have_nonempty_frames(self):
        before=len(self.app.topLevelWindows())
        captures=[]
        for mode in ('shaded','wireframe','xray','shaded'):
            self.host.view.setProperty('viewMode',mode)
            for hour in (9.,15.):
                self.host.backend.setSun(2026,6,21,hour)
                self.session.select('building','b1')
                self.wait(.04)
                frame=self.shot('mode-'+mode+'-'+str(int(hour)))
                # Building/modules remain present in the central viewport, even in wireframe.
                centre=frame[frame.shape[0]//4:3*frame.shape[0]//4,frame.shape[1]//4:3*frame.shape[1]//4,:3]
                self.assertGreater(float(centre.std()),10.)
                captures.append(frame)
                self.session.select('site','')
        self.assertGreater(np.count_nonzero(captures[0]!=captures[1]),1000)
        self.assertEqual(len(self.app.topLevelWindows()),before)


if __name__=='__main__':
    unittest.main()
