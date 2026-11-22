"""The actual workbench mounts one scene and routes its tools/preferences."""
from pathlib import Path
import tempfile
import unittest

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPointF, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from _setup import wait_until

from meridiana.core.model import model
from meridiana.gui.application import QuickWindow, create_app
from ._fidelity_support import data, settle


class IntegratedSceneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        create_app()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        p = model.Project()
        p.buildings = [model.Building('b1','Shed',[[0,0],[40,0],[40,20],[0,20]],height=9.5)]
        self.host = QuickWindow(p, Path(self.tmp.name), real_views=True)
        self.host.window.show()
        settle(self.app,.1)
        self.view = self.host.window.findChild(QObject,'viewport3d')
        self.view.setProperty('reducedMotion',True)

    def tearDown(self):
        warnings=self.host.warnings[:]
        self.host.close()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.tmp.cleanup()
        self.assertFalse(warnings)

    def test_toolbar_commands_reach_scene_and_selector_has_one_owner(self):
        self.assertEqual(len(self.host.window.findChildren(QObject,'viewport3d')),1)
        controls=self.host.parts.controllers['sceneControls']
        before=data(self.view,'cameraState')
        controls.zoom(1)
        self.assertNotEqual(data(self.view,'cameraState'),before)
        self.host.window.setProperty('viewMode','3d')
        self.assertTrue(self.view.property('showViewSelector'))
        self.view.viewRequested.emit('both')
        self.assertEqual(self.host.window.property('viewMode'),'both')
        self.assertFalse(self.view.property('showViewSelector'))

    def test_cube_toolbar_routes_commands_and_tracks_camera_projection(self):
        from PySide6.QtTest import QSignalSpy
        from quick.gestures import click, item, point, pump
        from ._fidelity_support import js
        win = self.host.window
        win.setProperty('viewMode', '3d')
        pump(500)
        cube = item(win, 'viewCube')
        home = QSignalSpy(cube.homeRequested)
        projection = QSignalSpy(cube.orthographicRequested)
        fit = QSignalSpy(cube.fitRequested)
        set_home = QSignalSpy(cube.setHomeRequested)
        buttons = [item(win, name) for name in ('sceneHome', 'sceneParallel', 'sceneFit', 'sceneSetHome')]
        self.assertEqual([b.property('iconName') for b in buttons], ['house', '3d', 'fit', 'pin'])
        self.assertEqual([b.x() for b in buttons], sorted(b.x() for b in buttons))
        self.assertIn('(Home)', buttons[0].property('tip'))
        self.assertIn('(F)', buttons[2].property('tip'))
        for index in (3, 0, 2):
            click(self.app, win, point(buttons[index]))
            pump(30)
        self.assertEqual(home.count(), 1)
        self.assertEqual(fit.count(), 1)
        self.assertEqual(set_home.count(), 1)
        self.assertIsNotNone(data(self.view, 'homeState'))
        for wanted in (True, False, True):
            click(self.app, win, point(buttons[1]))
            pump(30)
            self.assertEqual(data(self.view, 'cameraState.ortho'), wanted)
            self.assertEqual(buttons[1].property('checked'), wanted)
            self.assertEqual(projection.at(projection.count()-1), [wanted])
        # A camera change outside the button must keep the indicator in sync.
        js(self.view, 'cameraState = Object.assign({}, cameraState, {ortho: false})')
        pump(30)
        self.assertFalse(buttons[1].property('checked'))

    def test_cube_toolbar_moves_below_cube_in_a_narrow_view(self):
        from quick.gestures import click, item, point, pump
        from ._fidelity_support import js
        win = self.host.window
        win.setProperty('viewMode', '3d')
        pump(500)
        toolbar = item(win, 'sceneToolbar')
        cube = item(win, 'viewCube')
        js(self.view, "width = 250")
        pump(500)
        self.assertGreaterEqual(toolbar.y(), cube.y() + cube.height())
        self.assertLessEqual(toolbar.x() + toolbar.width(), self.view.width())
        # As the phase toolbar, the row scrolls when even its own width does not fit.
        js(self.view, "width = 140")
        pump(100)
        scroll = item(win, 'sceneToolbarScroll')
        self.assertGreater(scroll.property('contentWidth'), scroll.width())
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QWheelEvent
        pos = scroll.mapToScene(QPointF(scroll.width()/2, scroll.height()/2))
        for _ in range(1):
            QCoreApplication.sendEvent(win, QWheelEvent(pos, pos, QPoint(), QPoint(-120, 0),
                Qt.NoButton, Qt.NoModifier, Qt.ScrollPhase.NoScrollPhase, False))
            pump(100)
        self.assertGreater(scroll.property('contentX'), 0)
        js(scroll, "contentX = contentWidth - width")
        pump(80)
        before = data(self.view, 'cameraState')
        click(self.app, win, point(item(win, 'sceneZoomOut')))
        pump(80)
        self.assertNotEqual(data(self.view, 'cameraState'), before)

    def test_move_and_select_stay_synchronised_with_plan(self):
        self.host.plan.setTool('move')
        self.assertTrue(self.view.property('moveMode'))
        self.assertTrue(self.view.property('editVertices'))
        self.host.plan.setTool('select')
        self.assertFalse(self.view.property('moveMode'))
        self.assertFalse(self.view.property('editVertices'))
        self.host.shell.trigger('snaps')
        self.assertFalse(self.view.property('snaps'))
        self.view.setProperty('snaps',True)
        self.assertTrue(self.host.plan.snapsEnabled)

    def test_real_orbit_and_pan_in_the_workbench(self):
        from .pilot_scene import perform
        self.host.window.setProperty('viewMode','3d')
        settle(self.app,.2)
        before=data(self.view,'cameraState')
        perform(self.app,self.host.window,'quick',{'action':'drag3d','orbit':True,'delta':[65,-20]},QPointF())
        settle(self.app,.2)
        orbited=data(self.view,'cameraState')
        self.assertNotEqual(orbited['rotation'],before['rotation'])
        perform(self.app,self.host.window,'quick',{'action':'drag3d','delta':[40,20]},QPointF())
        settle(self.app,.2)
        panned=data(self.view,'cameraState')
        self.assertNotEqual(panned['position'],orbited['position'])
        self.assertEqual(panned['rotation'],orbited['rotation'])

    def test_preferences_apply_without_resetting_camera(self):
        controls=self.host.parts.controllers['sceneControls']
        self.assertIs(controls.settings,self.host.parts.controllers['settings'])
        before=data(self.view,'cameraState')
        for key,value,qml in [('navigation','blender','navigationStyle'),('orbit','arcball','orbitMode'),
                              ('pivot','selection','pivotMode'),('pivot_hint',False,'pivotHint')]:
            controls.settings.setValue(key,value)
            self.assertEqual(self.view.property(qml),value)
        self.assertEqual(data(self.view,'cameraState'),before)

    def test_the_edges_are_reduced_while_the_camera_moves_and_full_at_rest(self):
        # study 41, slice E: the setting reaches the view; "moving" drops the multisampling until the camera rests
        from .pilot_scene import perform
        controls=self.host.parts.controllers['sceneControls']
        from PySide6.QtQml import QQmlEngine, QQmlExpression
        scene_env=self.host.window.findChild(QObject,'sceneEnvironment')
        self.assertIsNotNone(scene_env)

        view=self.view

        class Env:          # the enums of SceneEnvironment have no converter in PySide: read in QML
            @staticmethod
            def property(name):
                value=QQmlExpression(QQmlEngine.contextForObject(view),scene_env,name).evaluate()
                return value[0] if isinstance(value,tuple) else value
        env=Env()
        msaa,none=2,0                                   # SceneEnvironment.MSAA, NoAA
        self.host.window.setProperty('viewMode','3d')
        settle(self.app,.2)
        self.assertEqual((self.view.property('edgeQuality'),env.property('antialiasingMode')),('full',msaa))
        perform(self.app,self.host.window,'quick',{'action':'drag3d','orbit':True,'delta':[65,-20]},QPointF())
        self.assertEqual(env.property('antialiasingMode'),msaa)        # "full": never reduced
        controls.settings.setValue('edges_3d','moving')
        self.assertEqual((self.view.property('edgeQuality'),self.view.property('moving')),('moving',False))
        self.assertEqual(env.property('antialiasingMode'),msaa)
        cam=data(self.view,'cameraState'); cam['fov']=cam['fov']+1      # a camera that moved
        self.view.setProperty('cameraState',cam)
        self.assertEqual((self.view.property('moving'),env.property('antialiasingMode')),(True,none))
        settle(self.app,.5)
        self.assertEqual((self.view.property('moving'),env.property('antialiasingMode')),(False,msaa))
        controls.settings.setValue('edges_3d','low')
        self.assertEqual(env.property('antialiasingMode'),none)
        controls.settings.setValue('edges_3d','full')
        self.assertEqual(env.property('antialiasingMode'),msaa)

    def test_meridio_stays_in_the_bottom_corner_of_the_visible_scene(self):
        self.host.window.setProperty('viewMode','3d')
        layer=self.host.window.findChild(QObject,'assistantLayer')
        # R500 (R155): placed once, from a phase to the next he stays where he is; a resize moves him only as much
        # as needed to stay inside the visible scene (before R500 he went back to its corner at every change)
        where=lambda:(layer.property('avatarX'),layer.property('avatarY'))
        for width,height in ((1366,900),(1920,1080)):
            self.host.window.resize(width,height)
            settle(self.app,.1)
            self.assertTrue(wait_until(self.app,lambda:not layer.property('relocating'),4))
            corner=data(self.view,'[mapToItem(null,width,sceneHeight).x,mapToItem(null,width,sceneHeight).y]')
            x,y=where()
            self.assertLessEqual(x,corner[0]-46+1)
            self.assertLessEqual(y,corner[1]-46+1)
            self.assertGreaterEqual(min(x,y),0)
            before=where()
            for phase in ('plant','model'):
                self.host.window.setProperty('phase',phase)
                settle(self.app,.1)
                self.assertTrue(wait_until(self.app,lambda:not layer.property('relocating'),4))
                self.assertEqual(where(),before,phase)

    def test_escape_cancels_preview_then_tool_then_selection_in_workbench(self):
        session = self.host.bridge.session
        session.select('building','b1')
        self.host.plan.setTool('move')
        self.view.forceActiveFocus()
        self.host.scene.beginTransform()
        self.host.scene.previewTransform(2,0,0)
        for key in range(3):
            for event in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
                QCoreApplication.sendEvent(self.host.window,QKeyEvent(event,Qt.Key.Key_Escape,Qt.KeyboardModifier.NoModifier))
            self.app.processEvents()
            if key == 0:
                self.assertIsNone(self.host.scene._trial)
                self.assertTrue(self.view.property('moveMode'))
            elif key == 1:
                self.assertFalse(self.view.property('moveMode'))
                self.assertEqual(session.selection,('building','b1'))
            else:
                self.assertEqual(session.selection,('site',''))
