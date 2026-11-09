"""R389 real Qt input and D3D pixels, isolated from personal projects and settings."""
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana import i18n, model
from meridiana.quick.backend.plan import PlanController


APP = None


def setUpModule():
    global APP
    os.environ['QSG_RHI_BACKEND'] = 'd3d11'
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')
    os.environ['QML_DISABLE_DISK_CACHE'] = '1'
    APP = QApplication.instance() or QApplication(['plan-test'])
    i18n.setup('it')


def settle_zoom(plan, controller=None, seconds: float = 5.0) -> None:
    """R541: the plan lays its dashes, hatches and the strings' names out 300 ms after the last zoom step (and the
    backend makes the strings' layers again then): a test waits for that end of the gesture, not for a time."""
    from PySide6.QtCore import QCoreApplication
    from _setup import wait_until
    timer = getattr(controller, '_scale_settle', None) if controller is not None else None

    def settled():
        backend = getattr(controller, '_scale_settle', None) if controller is not None else timer
        return plan.property('settledZoom') == plan.property('zoom') and not (backend is not None and backend.isActive())
    if not wait_until(QCoreApplication.instance(), settled, seconds):
        raise AssertionError(f"the plan's zoom did not settle in {seconds} s")


class WindowTest(unittest.TestCase):
    def setUp(self):
        self.project = model.Project(name='Quick test')
        self.controller = PlanController(self.project)
        self.engine = QQmlApplicationEngine()
        self.warnings = []
        self.engine.warnings.connect(lambda errors: self.warnings.extend(e.toString() for e in errors))
        self.controller.install(self.engine)
        self.engine.rootContext().setContextProperty('planBackend', self.controller)
        root = Path(__file__).resolve().parents[3] / 'src/meridiana/quick/qml/Meridiana/Plan/PlanWindow.qml'
        self.engine.load(QUrl.fromLocalFile(str(root)))
        self.assertTrue(self.engine.rootObjects(), self.warnings)
        self.window = self.engine.rootObjects()[0]
        self.window.show()
        QTest.qWaitForWindowExposed(self.window)
        QTest.qWait(100)
        from PySide6.QtCore import QObject
        self.plan = self.window.findChild(QObject, 'plan')

    def tearDown(self):
        self.window.close()
        self.controller.close()
        self.engine.deleteLater()
        APP.processEvents()

    def test_building_key_clicks_and_enter_change_real_project(self):
        QTest.keyClick(self.window, Qt.Key_B)
        for x, y in ((500, 400), (700, 400), (700, 600), (500, 600)):
            QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, QPoint(x, y))
        QTest.keyClick(self.window, Qt.Key_Return)
        QTest.qWait(100)
        self.assertEqual(len(self.controller.session.project.buildings), 1, self.controller.error)
        self.assertEqual(len(self.controller.session.project.buildings[0].footprint), 4)
        self.assertFalse(self.warnings, self.warnings)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'drawn.meridiana'
            self.controller.session.project.save(path)
            restored, _ = model.Project.load(path)
            self.assertEqual(restored.buildings[0].footprint, self.controller.session.project.buildings[0].footprint)

    def test_pan_and_resize_do_not_send_pointer_or_rebuild_geometry(self):
        from PySide6.QtCore import QObject
        geometry = self.window.findChild(QObject, 'moduleGeometry')
        self.controller.calls.clear()
        uploads = geometry.uploads
        QTest.mousePress(self.window, Qt.MiddleButton, Qt.NoModifier, QPoint(500, 400))
        for i in range(12):
            QTest.mouseMove(self.window, QPoint(510+i*5, 400), 2)
        QTest.mouseRelease(self.window, Qt.MiddleButton, Qt.NoModifier, QPoint(565, 400))
        self.window.resize(1600, 960)
        QTest.qWait(170)
        self.assertEqual(self.controller.calls['pointer'], 0)
        self.assertEqual(geometry.uploads, uploads)
        self.assertFalse(self.window.grabWindow().isNull())
        self.assertFalse(self.warnings, self.warnings)

    def test_temporary_collectors_do_not_draw_and_escape_restores_tool(self):
        self.controller.setTool('building')
        self.controller.pickPoints('scale', ['First', 'Second'])
        picked=[]
        self.controller.pointsPicked.connect(lambda purpose, points:picked.append((purpose,points)))
        for x in (400,600):
            QTest.mouseClick(self.window,Qt.LeftButton,Qt.NoModifier,QPoint(x,400))
        self.assertEqual(picked[0][0],'scale')
        self.assertEqual(len(picked[0][1]),2)
        self.assertEqual(self.controller.tool,'building')
        self.assertFalse(self.controller.drawing.points)
        self.controller.pickAnyEdge('align')
        QTest.keyClick(self.window,Qt.Key_Escape)
        self.assertFalse(self.controller.collecting)
        self.assertEqual(self.controller.tool,'building')

    def test_shadows_are_asynchronous_visible_and_can_be_disabled(self):
        import time
        from PySide6.QtCore import QPointF, QObject
        self.controller.session.edit('Building',lambda p:p.buildings.append(model.Building(
            id='cube',name='Cube',height=10,footprint=[[0,0],[10,0],[10,10],[0,10]])))
        self.plan.fit()
        # Include the shadow north of the building in the camera.
        self.plan.setProperty('zoom',20.)
        self.plan.setProperty('panX',500.)
        self.plan.setProperty('panY',600.)
        before=self.window.grabWindow()
        self.controller.setShadows({'azimuth':180.,'elevation':45.})
        deadline=time.monotonic()+10
        while not self.controller.shadows and time.monotonic()<deadline:
            QTest.qWait(10)
        self.assertTrue(self.controller.shadows)
        QTest.qWait(40)
        after=self.window.grabWindow()
        layer=self.window.findChild(QObject,'worldLayer')
        p=layer.mapToScene(QPointF(5,-15))
        dpr=self.window.devicePixelRatio()
        xy=(int((p.x()+.5)*dpr),int((p.y()+.5)*dpr))
        self.assertLess(after.pixelColor(*xy).lightness(),before.pixelColor(*xy).lightness())
        folder=Path(__file__).resolve().parents[3]/'build/quick-foto/pianta/shadows'
        folder.mkdir(parents=True,exist_ok=True)
        after.save(str(folder/f'cube-shadow-s{dpr:g}.png'))
        self.controller.setShadows({'enabled':False})
        self.assertEqual(self.controller.shadows,[])
        self.assertFalse(self.warnings,self.warnings)

    def test_twenty_thousand_modules_render_past_sixteen_bit_batch_limit(self):
        import math
        from PySide6.QtCore import QObject
        from meridiana.quick.backend.plan import qml_objects
        raw=[dict(kind='module',oid='s1',key=str(i),rid=str(i//140),
                  points=[[i%140*1.3,i//140*2.5],[i%140*1.3+1.13,i//140*2.5],
                          [i%140*1.3+1.13,i//140*2.5+2.27],[i%140*1.3,i//140*2.5+2.27]])
             for i in range(20000)]
        self.controller._modules=qml_objects(raw)
        self.controller._bounds=[0.,0.,140*1.3,math.ceil(20000/140)*2.5]
        self.controller.sceneChanged.emit()
        self.plan.fit()
        import time
        limit = time.monotonic()+10
        while self.plan.property('renderedModules') != 20000 and time.monotonic()<limit:
            QTest.qWait(20)
        self.assertEqual(self.plan.property('renderedModules'), 20000)
        QTest.qWait(100)
        frame=self.window.grabWindow()
        dpr=self.window.devicePixelRatio()
        for i in (0,8192,10922,16384,19999):
            p=raw[i]['points']
            # Magnify each indexed module: a 1.5-pixel-wide antialiased module
            # has no pixel of pure fill. Still check exact ink, including the last batch.
            self.plan.setProperty('zoom', 20.)
            self.plan.setProperty('panX', 500-sum(q[0] for q in p)/4*20)
            self.plan.setProperty('panY', 400-sum(q[1] for q in p)/4*20)
            QTest.qWait(25)
            frame=self.window.grabWindow()
            x,y=500,400
            self.assertEqual(frame.pixelColor(int(x*dpr),int(y*dpr)).name(),'#192d5a',i)
        geometry=self.window.findChild(QObject,'moduleGeometry')
        uploads=geometry.uploads
        self.controller.calls.clear()
        for _ in range(10):
            self.plan.setProperty('panX',self.plan.property('panX')+2)
            APP.processEvents()
            self.window.grabWindow()
        self.assertEqual(geometry.uploads,uploads)
        self.assertEqual(self.controller.calls['pointer'],0)
        self.assertFalse(self.warnings,self.warnings)

    def test_native_pinch_preserves_anchor_and_native_rotation_does_not_turn_plan(self):
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QNativeGestureEvent, QPointingDevice, QInputDevice
        pad=QPointingDevice('test pad',123,QInputDevice.DeviceType.TouchPad,
                            QPointingDevice.PointerType.Finger,QInputDevice.Capability.Position,5,0)
        at=QPointF(350,300)
        def event(kind,value):
            e=QNativeGestureEvent(kind,pad,2,at,at,QPointF(self.window.mapToGlobal(at.toPoint())),value,QPointF())
            APP.sendEvent(self.window,e)
            APP.processEvents()
        scale=self.plan.property('zoom')
        panx,pany=self.plan.property('panX'),self.plan.property('panY')
        event(Qt.BeginNativeGesture,0)
        event(Qt.ZoomNativeGesture,.25)
        self.assertAlmostEqual(self.plan.property('zoom'),scale*1.25)
        self.assertAlmostEqual(self.plan.property('panX'),at.x()-(at.x()-panx)*1.25)
        self.assertAlmostEqual(self.plan.property('panY'),at.y()-(at.y()-pany)*1.25)
        event(Qt.RotateNativeGesture,17)
        self.assertEqual(self.plan.property('bearing'),0)
        event(Qt.EndNativeGesture,0)


if __name__ == '__main__':
    unittest.main()
