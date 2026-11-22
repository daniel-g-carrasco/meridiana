"""R619: Meridio's new figure in a real Quick window, offscreen.

1. The matrices Character.qml computes are figure.part_matrix's (the formula is in both: this keeps them one).
2. The sticker always has its white border round the figure, at both sizes.
3. **The rule Daniel was angry about twice**: in no frame a side passes over another solid's face. Measured on the
   window's own picture while he turns and moves with inertia: no pixel of a side's colour inside the faces.
4. The states of the program on his face: thinking, answering, typing, a reaction, idle a long time, picked up.
5. The frames run only while something moves: after a move they stop; with the reduced motion none at all.
"""
import unittest

from PySide6.QtCore import Q_ARG, QMetaObject, QPointF, QSize, QUrl
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shiboken6 import delete

import _setup
from meridiana.app.assistant import figure as f
from meridiana.gui.backend.assistant import FigureImages, QML, install_assistant

SCENE = """
import QtQuick
import Meridiana.Assistant
Window {
    visible: true; width: 420; height: 260; color: "%(ground)s"
    Character { objectName: "big"; x: 40; y: 40; width: 184; height: 184 }
    Character { objectName: "small"; x: 300; y: 100; width: 46; height: 46 }
}
"""


def colour(name):
    c = QColor(name)
    return (c.red(), c.green(), c.blue())


class FigureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['meridio-figure'])

    def scene(self, ground='#25282b', reduced=False):
        engine = QQmlApplicationEngine()
        errors = []
        engine.warnings.connect(lambda items: errors.extend(i.toString() for i in items))
        install_assistant(engine, theme={'theme': 'dark', 'reducedMotion': reduced})
        engine.addImportPath(str(QML.parent.parent))
        engine.loadData((SCENE % {'ground': ground}).encode(), QUrl.fromLocalFile(str(QML / 'test.qml')))
        window = engine.rootObjects()[0]
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        window.requestActivate()
        _setup.wait_for(lambda: window.isActive(), 2000)

        def cleanup():
            window.close()
            delete(engine)
            self.assertEqual(errors, [])
        self.addCleanup(cleanup)
        items = {}
        todo = [window.contentItem()]
        while todo:
            item = todo.pop()
            if item.objectName() in ('big', 'small'):
                items[item.objectName()] = item
            todo.extend(item.childItems())
        return engine, window, items

    @staticmethod
    def js(item, name):
        value = item.property(name)
        return value.toVariant() if hasattr(value, 'toVariant') else value

    def settle(self, item, ms=3000):
        return _setup.wait_for(lambda: not item.property('live'), ms)

    def test_legacy_icon_names_always_draw_the_sticker(self):
        provider = FigureImages()
        sticker = provider.requestImage('sticker', QSize(), QSize(50, 50))
        self.assertFalse(sticker.isNull())
        for name in ('solid', 'smooth', 'pixel', ''):
            self.assertEqual(provider.requestImage(name, QSize(), QSize(50, 50)), sticker)

    def test_the_qml_matrices_are_the_cores(self):
        _, window, items = self.scene(reduced=True)
        big = items['big']
        for name in ('rest', 'think', 'wave', 'proud', 'surprised'):
            with self.subTest(expression=name):
                if name != 'rest':
                    QMetaObject.invokeMethod(big, 'react', Q_ARG('QVariant', name), Q_ARG('QVariant', 60))
                self.assertEqual(big.property('expression'), name)
                p = dict(f.POSES[name])
                p['yaw'] += p['gx'] * f.GAZE_TURN[0]
                p['pitch'] += p['gy'] * f.GAZE_TURN[1]
                scale, ox, oy = f.origin(184)
                mats = self.js(big, 'mats')
                for key, m in zip(f.ORDER, mats, strict=True):
                    want = f.part_matrix(key, p, scale, ox, oy)
                    for a, b in zip(m, want, strict=True):
                        self.assertAlmostEqual(a, b, places=6, msg=(name, key))
                depth = big.property('depth')
                dx, dy = f.depth_shift(p['yaw'], p['pitch'], scale, -f.PLATE)
                self.assertAlmostEqual(depth.x(), dx, places=6)
                self.assertAlmostEqual(depth.y(), dy, places=6)

    def white_round(self, window, item):
        image = window.grabWindow()
        dpr = image.devicePixelRatio()
        top = item.mapToScene(QPointF(0, 0))
        whites = 0
        for y in range(int(top.y() * dpr), int((top.y() + item.height()) * dpr)):
            for x in range(int(top.x() * dpr), int((top.x() + item.width()) * dpr)):
                c = image.pixelColor(x, y)
                whites += c.red() > 245 and c.green() > 245 and c.blue() > 245
        return whites

    def test_the_sticker_always_has_its_white_border(self):
        _, window, items = self.scene()
        self.assertGreater(self.white_round(window, items['big']), 400)
        self.assertGreater(self.white_round(window, items['small']), 20)

    def faces_and_eyes(self, item, dpr):
        """The faces on the window's picture (device pixels), from the matrices the item has now; the eyes."""
        top = item.mapToScene(QPointF(0, 0))
        outlines = [[(q.x(), q.y()) for q in part] for part in self.js(item, 'figure')['outlines']]
        mats, eye_mats = self.js(item, 'mats'), self.js(item, 'eyeMats')
        faces = []
        for m, outline in zip(mats, outlines, strict=True):
            faces.append(Polygon([((top.x() + m[0] * x + m[1] * y + m[2]) * dpr, (top.y() + m[3] * x + m[4] * y + m[5]) * dpr)
                                  for x, y in outline]))
        eyes = []
        for m, shape in zip(eye_mats, self.js(item, 'eyeShapes'), strict=True):
            points = [(q.x(), q.y()) for q in shape['outline']]
            if len(points) >= 3:
                eyes.append(Polygon([((top.x() + m[0] * x + m[1] * y + m[2]) * dpr,
                                      (top.y() + m[3] * x + m[4] * y + m[5]) * dpr) for x, y in points]).buffer(0))
            arch = [(q.x(), q.y()) for q in shape['arch']]
            if arch:            # surprise's thin arch, black on the yellow: its edge blends to a darker yellow
                width = shape['archLine'] * abs(m[4]) * dpr / 2
                eyes.append(LineString([((top.x() + m[0] * x + m[1] * y + m[2]) * dpr,
                                         (top.y() + m[3] * x + m[4] * y + m[5]) * dpr) for x, y in arch]).buffer(width))
        return faces, eyes

    def sides_over_faces(self, window, item):
        """The pixels of a side's colour inside the faces (1,5 device pixels in from every edge, off the eyes)."""
        image = window.grabWindow()
        dpr = image.devicePixelRatio()
        faces, eyes = self.faces_and_eyes(item, dpr)
        inside = unary_union([face.buffer(0) for face in faces]).buffer(-1.5 * dpr)
        if eyes:
            inside = inside.difference(unary_union(eyes).buffer(1.5 * dpr))
        # the inner edges between faces are edges too: a face over another blends at its rim
        rims = unary_union([face.exterior.buffer(1.5 * dpr) for face in faces])
        inside = inside.difference(rims)
        sides = [colour(c) for c in f.SIDES.values()]
        x0, y0, x1, y1 = (int(v) for v in inside.bounds)
        bad = []
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if not inside.contains(Point(x + 0.5, y + 0.5)):
                    continue
                c = image.pixelColor(x, y)
                rgb = (c.red(), c.green(), c.blue())
                if any(max(abs(a - b) for a, b in zip(rgb, s, strict=True)) <= 6 for s in sides):
                    bad.append((x, y, rgb))
        return bad, inside.area

    def test_no_side_over_another_solids_face_while_he_turns_and_moves(self):
        _, window, items = self.scene()
        big = items['big']
        self.assertTrue(big.property('moving'))
        checked = 0
        for name in ('rest', 'wave', 'proud', 'surprised', 'worried'):

            if name != 'rest':
                QMetaObject.invokeMethod(big, 'react', Q_ARG('QVariant', name), Q_ARG('QVariant', 30))
            # a fast move to the right and back: the body turns, the parts lag and turn in the plane
            for dx in (12, 12, 12, 12, 0, 0, -12, -12, -12, -12, 0, 0):
                big.setX(big.x() + dx)
                QTest.qWait(16)
                bad, area = self.sides_over_faces(window, big)
                self.assertGreater(area, 2000)
                self.assertEqual(bad[:5], [], f'{name}: a side over a face')
                checked += 1
        self.assertGreater(checked, 50)

    def test_the_guard_sees_a_side_put_over_the_faces(self):
        # the check above must catch what it is for: the face's own back copy raised over the faces is seen
        _, window, items = self.scene(reduced=True)
        big = items['big']
        QMetaObject.invokeMethod(big, 'react', Q_ARG('QVariant', 'proud'), Q_ARG('QVariant', 30))  # turned: pitch -7
        self.assertEqual(self.sides_over_faces(window, big)[0], [])
        # the yellow face's back copy (a Slab under its layer): its layer raised over the faces' layers
        layers = [kid for kid in big.childItems()
                  if any(c.property('at') == 1.0 and c.property('part') == 3
                         and QColor(c.property('colour')) == QColor(f.SIDES['face']) for c in kid.childItems())]
        self.assertEqual(len(layers), 1)
        layers[0].setZ(100)
        QTest.qWait(30)
        self.assertGreater(len(self.sides_over_faces(window, big)[0]), 20)

    def test_he_turns_and_lags_when_moved_then_the_frames_stop(self):
        _, window, items = self.scene()
        big = items['big']
        self.settle(big)
        turned = lagged = 0.0
        for _ in range(10):
            big.setX(big.x() + 15)
            QTest.qWait(16)
            body, lag = self.js(big, 'body'), self.js(big, 'lag')
            turned = max(turned, abs(body['yaw']))
            lagged = max(lagged, max(abs(v['t']) for v in lag.values()), max(abs(v['x']) for v in lag.values()))
        self.assertGreater(turned, 3.0)
        self.assertGreater(lagged, 0.5)
        self.assertTrue(self.settle(big, 4000), 'the frames go on after he stopped')
        self.assertLess(abs(self.js(big, 'body')['yaw']), 0.05)

    def test_reduced_motion_and_an_inactive_window_run_no_frames(self):
        _, window, items = self.scene(reduced=True)
        big = items['big']
        self.assertFalse(big.property('moving'))
        for _ in range(5):
            big.setX(big.x() + 15)
            QTest.qWait(16)
            self.assertFalse(big.property('live'))
        self.assertEqual(self.js(big, 'body')['yaw'], 0)

    def test_the_states_of_the_program_on_his_face(self):

        _, window, items = self.scene()
        big = items['big']
        self.assertEqual(big.property('expression'), 'rest')
        big.setProperty('state', 'thinking')
        self.assertEqual(big.property('expression'), 'think')
        big.setProperty('state', 'answering')
        self.assertEqual(big.property('expression'), 'speak')
        big.setProperty('state', 'idle')
        QMetaObject.invokeMethod(big, 'hear')
        self.assertEqual(big.property('expression'), 'listen')
        QMetaObject.invokeMethod(big, 'react', Q_ARG('QVariant', 'worried'), Q_ARG('QVariant', 0.2))
        self.assertEqual(big.property('expression'), 'worried')
        big.setProperty('heardAt', 0)
        _setup.wait_for(lambda: big.property('expression') == 'rest', 2000)
        self.assertEqual(big.property('expression'), 'rest')
        big.setProperty('awake', False)
        big.setProperty('lastUse', big.property('lastUse') - 1000 * (f.DROWSY_S + 1))
        _setup.wait_for(lambda: big.property('expression') == 'drowsy', 1000)
        self.assertEqual(big.property('expression'), 'drowsy')
        big.setProperty('lastUse', big.property('lastUse') - 1000 * f.ASLEEP_S)
        _setup.wait_for(lambda: big.property('expression') == 'asleep', 1000)
        self.assertEqual(big.property('expression'), 'asleep')
        self.settle(big)
        self.assertFalse(big.property('live'), 'asleep he stands still: no frames')
        QMetaObject.invokeMethod(big, 'lookAt', Q_ARG('QVariant', 1.0), Q_ARG('QVariant', 0.0))
        _setup.wait_for(lambda: big.property('expression') == 'rest', 1000)
        self.assertEqual(big.property('expression'), 'rest')       # the pointer wakes him
        big.setProperty('dragging', True)
        self.assertEqual(big.property('expression'), 'surprised')
        big.setProperty('dragging', False)


if __name__ == '__main__':
    unittest.main()
