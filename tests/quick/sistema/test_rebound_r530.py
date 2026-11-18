"""R530 (Daniel 07/11/2026: «quando si arrivava al fondo di un qualsiasi scrolling, c'era una sorta di rimbalzo. Come mai
adesso non c'è più?»): at the end of a list, the wheel pushes the content a little past it and it comes back to 0
within Theme.motion.FAST + NORMAL; in the middle of the list the wheel only scrolls; the frames keep coming.

    python -m unittest quick.sistema.test_rebound_r530
"""
import time
import unittest

from PySide6.QtCore import QObject, QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from quick.sistema import test_controls

SCENE = '''Item { width: 300; height: 200
    property alias list: view
    ListView { id: view; objectName: "list"; anchors.fill: parent; clip: true; model: 60
        delegate: M.Label { required property int index; width: ListView.view.width; height: 24; text: "Row " + index }
        M.ScrollBar.vertical: M.ScrollBar { }
    }
}'''


def wheel(window, steps):
    for _ in range(abs(steps)):
        event = QWheelEvent(QPointF(150, 100), QPointF(150, 100), QPoint(0, 0), QPoint(0, -120 if steps < 0 else 120),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(window, event) if isinstance(QApplication.instance(), QApplication) else \
            QApplication.instance().sendEvent(window, event)
        QTest.qWait(5)


class Rebound(unittest.TestCase):
    setUpClass = classmethod(test_controls.ControlsTest.setUpClass.__func__)
    scene = test_controls.ControlsTest.scene

    def test_r530_the_wheel_at_the_end_bounces_and_comes_back(self):
        root, window = self.scene(SCENE)
        view = root.findChild(QObject, 'list')
        shift = next((o for o in view.findChildren(QObject) if o.objectName() == 'reboundShift'), None)
        self.assertIsNotNone(shift, 'no rebound on the list')
        wheel(window, -3)
        QTest.qWait(300)
        self.assertEqual(shift.property('y'), 0, 'in the middle the wheel only scrolls')
        view.setProperty('contentY', view.property('contentHeight') - view.property('height'))
        QTest.qWait(50)
        self.assertTrue(view.property('atYEnd'))
        seen, frames = [], []
        window.frameSwapped.connect(lambda: frames.append(time.perf_counter()))
        start = time.perf_counter()
        wheel(window, -1)
        while time.perf_counter() - start < .6:
            seen.append((time.perf_counter() - start, shift.property('y')))
            QTest.qWait(8)
        reach = min(y for _t, y in seen)
        self.assertLessEqual(reach, -8, seen[:10])
        back = next(t for t, y in seen if t > .05 and y == 0)
        self.assertLessEqual(back, .11 + .18 + .08, seen)
        gaps = [b - a for a, b in zip(frames, frames[1:])]
        print('R530 reach px', reach, 'back ms', round(1000 * back), 'frames', len(frames), 'longest gap ms', round(1000 * max(gaps or [0])))
        self.assertLess(max(gaps or [0]), .1)
        self.assertTrue(view.property('atYEnd'), 'the list stays at its end')


if __name__ == '__main__':
    unittest.main()
