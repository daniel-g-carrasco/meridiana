"""R13 real D3D11 pixels: occlusion, terrain, bars and a usable initial fit."""
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PySide6.QtCore import QCoreApplication, QEvent, QObject, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest

from meridiana import i18n, model
from meridiana.quick.backend.scene_host import SceneWindow
from meridiana.session import ProjectSession
from ._fidelity_support import click, data, js, pixels, settle


@unittest.skipUnless(os.environ.get('MERIDIANA_QUICK_3D_NATIVE') == '1', 'Explicit D3D11 process')
class FidelityNativeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Direct3D11)
        QQuickStyle.setStyle('Basic')
        cls.app = QApplication.instance() or QApplication([])
        i18n.setup('it')
        cls.out = Path('build/quick-foto/r13-vista3d/regressions')
        cls.out.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=self.out)
        p = model.Project()
        p.buildings = [model.Building('front', 'Front', [[-12,-5],[12,-5],[12,5],[-12,5]], height=18),
                       model.Building('back', 'Back', [[-3,12],[3,12],[3,18],[-3,18]], height=5)]
        self.session = ProjectSession(p)
        self.host = SceneWindow(self.session, self.tmp.name, width=800, height=600)
        self.view = self.host.view
        self.host.window.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.host.window.show()
        settle(self.app, 0.3)
        self.view.setProperty('reducedMotion', True)

    def tearDown(self):
        warnings = self.host.warnings[:]
        self.host.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.tmp.cleanup()
        self.assertFalse(warnings)

    def shot(self, name):
        settle(self.app)
        image = self.host.window.grabWindow()
        self.assertFalse(image.isNull())
        image.save(str(self.out / (name + '.png')))
        return pixels(image)

    def test_selection_of_hidden_building_is_occluded(self):
        js(self.view, 'cameraState=({position:[0,8,65],rotation:[1,0,0,0],target:[0,8,0],fov:60,ortho:false})')
        plain = self.shot('occlusion-plain')
        self.session.select('building', 'back')
        selected = self.shot('occlusion-hidden')
        # Entire rear building is behind the broad front wall. Its outline must disappear.
        self.assertLess(np.count_nonzero(np.max(np.abs(plain.astype(int)-selected.astype(int)), axis=2)>12), 20)
        self.session.select('building', 'front')
        visible = self.shot('occlusion-visible')
        self.assertGreater(np.count_nonzero(np.max(np.abs(plain.astype(int)-visible.astype(int)), axis=2)>12), 100)

    def test_sun_below_scene_and_toolbar_buttons_zoom_without_python(self):
        sun = self.host.window.findChild(QObject, 'sunBar')
        self.assertIsNotNone(sun, 'SunBar must be a full-width row below the scene')
        self.assertEqual(sun.property('width'), self.view.property('width'))
        self.assertEqual(sun.property('y'), self.view.property('sceneHeight'))
        toolbar = self.host.window.findChild(QObject, 'sceneToolbar')
        self.assertIsNotNone(toolbar)
        before = data(self.view, 'cameraState')
        calls = dict(self.host.backend.calls)
        plus = self.host.window.findChild(QObject, 'sceneZoomIn')
        xy = data(plus, '[mapToItem(null,width/2,height/2).x,mapToItem(null,width/2,height/2).y]')
        click(self.host.window, *xy)
        settle(self.app)
        self.assertNotEqual(data(self.view, 'cameraState'), before)
        self.assertEqual(dict(self.host.backend.calls), calls)

    def test_fit_follows_resize_until_navigation(self):
        before = data(self.view, 'cameraState')
        self.host.window.resize(400, 800)
        settle(self.app)
        self.assertNotEqual(data(self.view, 'cameraState.position'), before['position'])

    def test_narrow_sun_bar_keeps_both_end_buttons_and_slider_visible(self):
        self.host.theme.configure({'textSize':'large'})
        self.host.window.resize(400,600)
        settle(self.app)
        slider=self.host.window.findChild(QObject,'sunHour')
        last=self.host.window.findChild(QObject,'sunDesign')
        self.assertGreaterEqual(slider.property('width'),80)
        end=data(last,'mapToItem(null,width,0).x')
        self.assertLessEqual(end,392)
        self.shot('narrow-large-sun')

    def test_ground_covers_bottom_corners(self):
        image = self.shot('ground')
        scene_h = self.view.property('sceneHeight') or self.view.property('height')
        dpr = self.host.window.devicePixelRatio()
        for x in (5, 795):
            r, g, b, _ = image[int((scene_h-8)*dpr), int(x*dpr)]
            self.assertGreater(int(g), int(b), 'Terrain, not blue sky, at the bottom corner')

    def test_distant_ground_does_not_shadow_itself(self):
        # A wide overview makes the terrain cross the directional shadow cascades.
        # The upper empty strip must stay smooth, while buildings still cast shadows below.
        rho = model.Project.load(Path('docs/quick/compat/fixtures/rho.meridiana'))[0]
        self.session.edit('Load reference geometry',lambda p: setattr(p,'buildings',rho.buildings))
        self.host.window.resize(870,564)
        js(self.view, 'fitScene()')
        shadowed = self.shot('ground-shadowed')
        self.view.setProperty('shadows',False)
        plain = self.shot('ground-unshadowed')
        d = self.host.window.devicePixelRatio()
        rect = (slice(int(80*d),int(160*d)),slice(int(10*d),int(680*d)))
        diff = np.max(np.abs(shadowed[rect].astype(int)-plain[rect].astype(int)),axis=2)
        self.assertLess(np.count_nonzero(diff>8),20*d*d)
        self.assertGreater(np.count_nonzero(np.max(np.abs(shadowed.astype(int)-plain.astype(int)),axis=2)>8),100)

    def test_calendar_and_object_menu_are_real_controls(self):
        def press(name):
            control = self.host.window.findChild(QObject,name)
            self.assertIsNotNone(control,name)
            xy = data(control,'[mapToItem(null,width/2,height/2).x,mapToItem(null,width/2,height/2).y]')
            click(self.host.window,*xy)
            settle(self.app)
        press('sunDay')
        calendar = self.host.window.findChild(QObject,'sunCalendar')
        self.assertTrue(calendar.property('visible'))
        self.shot('calendar')
        QTest.keyClick(self.host.window,Qt.Key.Key_Escape)
        settle(self.app)
        self.assertFalse(calendar.property('visible'),'Escape closes the day popup before changing the scene tool')
        # A real right click on the front wall selects it before opening its menu.
        js(self.view, 'userMoved=true;cameraState=({position:[0,8,65],rotation:[1,0,0,0],target:[0,8,0],fov:60,ortho:false})')
        settle(self.app)
        click(self.host.window,400,280,Qt.MouseButton.RightButton)
        settle(self.app)
        self.assertEqual(self.session.selection,('building','front'))
        self.assertTrue(self.host.window.findChild(QObject,'sceneContextMenu').property('visible'))
        self.assertEqual(self.host.window.findChild(QObject,'sceneContextMenu').property('count'),9)
        self.shot('object-menu')
        press('sceneAction_rename')
        self.assertTrue(self.host.window.findChild(QObject,'sceneRename').property('visible'))
        self.host.window.findChild(QObject,'sceneRenameField').setProperty('text','Renamed shed')
        self.host.window.findChild(QObject,'sceneRename').accept()
        self.assertEqual(self.session.project.building('front').name,'Renamed shed')
        self.session.undo.undo()
        self.assertEqual(self.session.project.building('front').name,'Front')
