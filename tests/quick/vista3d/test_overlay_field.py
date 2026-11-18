"""R534, R535: the corner's field and the sign of Ctrl in the 3D view are the plan's, and the field holds its corner."""
from pathlib import Path
import tempfile
import unittest

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QApplication

from meridiana import model, view_colours
from meridiana.quick.app import QuickWindow, create_app
from meridiana.ui import design
from ._fidelity_support import data, settle


def kind(item):
    return item.metaObject().className().split('_QML')[0]


class OverlayFieldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        create_app()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        p = model.Project()
        p.buildings = [model.Building('b1', 'Casa', [[0, 0], [16, 0], [16, 10], [0, 10]], height=6,
                                      roof=model.Roof(type='hip', tilt=30))]
        self.host = QuickWindow(p, Path(self.tmp.name), real_views=True)
        self.window = self.host.window
        self.window.show()
        settle(self.app, .1)
        self.window.setProperty('viewMode', '3d')
        settle(self.app, .2)
        self.view = self.window.findChild(QObject, 'viewport3d')
        self.view.setProperty('reducedMotion', True)
        self.host.bridge.session.select('building', 'b1')
        settle(self.app, .1)
        self.view.setProperty('editVertices', True)
        settle(self.app, .2)
        self.points = data(self.view, 'verticesData.map(v=>v.point)')
        self.top = max(range(len(self.points)), key=lambda i: (self.points[i][1], self.points[i][0]))

    def tearDown(self):
        warnings = self.host.warnings[:]
        self.host.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.tmp.cleanup()
        self.assertFalse(warnings)

    def mouse(self, kind_, x, y, button=Qt.MouseButton.NoButton, buttons=Qt.MouseButton.NoButton,
              mods=Qt.KeyboardModifier.NoModifier):
        at = self.view.mapToScene(QPointF(x, y))
        QCoreApplication.sendEvent(self.window, QMouseEvent(kind_, at, at, at, button, buttons, mods))
        self.app.processEvents()

    def corner(self, index=None):
        return data(self.view, f'projectPoint(verticesData[{self.top if index is None else index}].point)')

    def open_field(self):
        at = self.corner()
        left = Qt.MouseButton.LeftButton
        self.mouse(QEvent.Type.MouseButtonPress, *at, left, left)
        self.mouse(QEvent.Type.MouseButtonRelease, *at, left)
        settle(self.app, .1)
        field = self.view.findChild(QObject, 'vertexHeight')
        self.assertTrue(field.isVisible())
        return field

    def offset(self, field):
        place = field.mapToItem(self.view, QPointF(0, 0))
        at = self.corner()
        return place.x() - at[0], place.y() - at[1]

    def drag(self, dx, dy, mods):
        middle = Qt.MouseButton.MiddleButton
        x0, y0 = self.view.width()*.2, data(self.view, 'sceneHeight')*.8
        self.mouse(QEvent.Type.MouseButtonPress, x0, y0, middle, middle, mods)
        for i in range(1, 7):
            self.mouse(QEvent.Type.MouseMove, x0+dx*i/6, y0+dy*i/6, Qt.MouseButton.NoButton, middle, mods)
        self.mouse(QEvent.Type.MouseButtonRelease, x0+dx, y0+dy, middle)

    def test_field_holds_its_corner_through_orbit_pan_and_zoom(self):
        field = self.open_field()
        first = self.offset(field)
        self.assertGreater(first[0], 0)                  # beside the corner, not on it
        self.assertGreater(first[1], 0)
        camera = data(self.view, 'cameraState')
        for move in (lambda: self.drag(70, -25, Qt.KeyboardModifier.ShiftModifier),
                     lambda: self.drag(-60, 30, Qt.KeyboardModifier.NoModifier)):
            move()
            self.assertNotEqual(data(self.view, 'cameraState'), camera)
            camera = data(self.view, 'cameraState')
            dx, dy = self.offset(field)
            self.assertLessEqual(abs(dx-first[0]), 1)
            self.assertLessEqual(abs(dy-first[1]), 1)
            self.assertTrue(field.isVisible())
        at = self.view.mapToScene(QPointF(*[c+20 for c in self.corner()]))
        QCoreApplication.sendEvent(self.window, QWheelEvent(at, at, QPoint(), QPoint(0, 120), Qt.MouseButton.NoButton,
                                                            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
                                                            False))
        self.app.processEvents()
        self.assertNotEqual(data(self.view, 'cameraState'), camera)
        dx, dy = self.offset(field)
        self.assertLessEqual(abs(dx-first[0]), 1)
        self.assertLessEqual(abs(dy-first[1]), 1)
        # Panned far away, the corner leaves the view: the field stops at the edge with what is written in it
        self.drag(-900, 0, Qt.KeyboardModifier.NoModifier)
        self.assertLess(self.corner()[0], 0)
        self.assertEqual(field.mapToItem(self.view, QPointF(0, 0)).x(), 0)
        self.assertTrue(field.isVisible())
        # Esc closes it and writes nothing
        before = self.host.bridge.session.undo.count()
        input_ = field.findChild(QObject, 'overlayFieldInput')
        self.assertTrue(input_.hasActiveFocus())
        QCoreApplication.sendEvent(self.window, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
        self.app.processEvents()
        self.assertFalse(field.isVisible())
        self.assertEqual(self.host.bridge.session.undo.count(), before)

    def test_enter_writes_the_height(self):
        field = self.open_field()
        input_ = field.findChild(QObject, 'overlayFieldInput')
        input_.setProperty('text', '9,5')
        QCoreApplication.sendEvent(self.window, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
        settle(self.app, .2)
        self.assertFalse(field.isVisible())
        self.assertAlmostEqual(max(p[1] for p in data(self.view, 'verticesData.map(v=>v.point)')), 9.5, 2)

    def test_field_is_the_plans_with_its_word_and_unit(self):
        field = self.open_field()
        self.assertEqual(kind(field), 'OverlayField')
        plan = self.window.findChild(QObject, 'sideEditor')
        self.assertEqual(plan.metaObject().superClass().className().split('_QML')[0], 'OverlayField')
        for name in ('height', 'radius'):
            self.assertEqual(field.property(name), plan.property(name), name)
        self.assertEqual(field.property('radius'), design.Radius.PLAN_LABEL)
        self.assertEqual(field.property('label'), 'Quota da terra')
        self.assertEqual(field.property('unit'), 'm')
        input_ = field.findChild(QObject, 'overlayFieldInput')
        self.assertEqual(input_.property('font').pixelSize(), design.Type.SMALL)
        self.assertEqual(field.property('text'), '8,89')
        # As wide as what it holds: the word, the value, the unit, and the margins, nothing more
        self.assertLess(field.width(), 200)
        # On the picture: the ground of the plan's pills, opaque, and the outline of the selection
        image = self.window.grabWindow()
        dpr = image.devicePixelRatio()
        top_left = field.mapToScene(QPointF(0, 0))
        pick = lambda x, y: image.pixelColor(int((top_left.x()+x+.5)*dpr), int((top_left.y()+y+.5)*dpr))
        ground = QColor(view_colours.PHOTO['label_bg'][:7])
        inside = pick(field.width()-4, field.height()/2)
        self.assertLessEqual(max(abs(inside.red()-ground.red()), abs(inside.green()-ground.green()),
                                 abs(inside.blue()-ground.blue())), 3)
        sel = QColor(view_colours.PHOTO['sel'][:7])
        edge = pick(field.width()/2, .5)
        self.assertLessEqual(max(abs(edge.red()-sel.red()), abs(edge.green()-sel.green()), abs(edge.blue()-sel.blue())), 40)

    def test_two_corners_say_so(self):
        other = max((i for i in range(len(self.points)) if i != self.top), key=lambda i: (self.points[i][1], -self.points[i][0]))
        self.open_field()
        at = self.corner(other)
        left, ctrl = Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier
        self.mouse(QEvent.Type.MouseButtonPress, *at, left, left, ctrl)
        self.mouse(QEvent.Type.MouseButtonRelease, *at, left, Qt.MouseButton.NoButton, ctrl)
        settle(self.app, .1)
        field = self.view.findChild(QObject, 'vertexHeight')
        self.assertEqual(field.property('label'), 'Quota da terra di 2 vertici')
        place = field.mapToItem(self.view, QPointF(0, 0))
        for corner in (self.corner(), self.corner(other)):       # it covers neither corner
            self.assertFalse(place.x() <= corner[0] <= place.x()+field.width()
                             and place.y() <= corner[1] <= place.y()+field.height())

    def test_ctrl_sign_is_the_plans(self):
        at = self.corner()
        ctrl = Qt.KeyboardModifier.ControlModifier
        self.mouse(QEvent.Type.MouseMove, at[0]-60, at[1]+70, mods=ctrl)
        sign = self.view.findChild(QObject, 'vertexPlus')
        self.assertTrue(sign.isVisible())
        plan = self.window.findChild(QObject, 'selectionSign')
        self.assertEqual(kind(sign), 'PointerSign')
        self.assertEqual(kind(plan), 'PointerSign')
        for name in ('width', 'height', 'radius', 'color', 'addColor', 'offsetX', 'offsetY'):
            self.assertEqual(sign.property(name), plan.property(name), name)
        self.assertEqual(sign.property('sign'), 'add')
        place = sign.mapToItem(self.view, QPointF(0, 0))
        self.assertEqual((place.x(), place.y()), (round(at[0]-60)+14, round(at[1]+70)+16))
        # Over a corner already taken, Ctrl gives it back: the minus
        self.open_field()
        self.mouse(QEvent.Type.MouseMove, *at, mods=ctrl)
        self.assertEqual(sign.property('sign'), 'remove')
        text = sign.findChild(QObject, 'pointerSignText')
        self.assertEqual(text.property('name'), 'control:minus')
        self.mouse(QEvent.Type.MouseMove, at[0]+3, at[1]+3)
        self.assertFalse(sign.isVisible())


if __name__ == '__main__':
    unittest.main()
