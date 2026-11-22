"""R648 (Daniel 15/11/2026, on the laptop, Niri and a touchpad): «il cursore all'interno di meridio, dopo le varie prove
di stretch, rimane in questo stato in ogni punto lo passi sopra il fumetto, e non mi permette di interagire (anche se
gli hover funzionano)».

The cause: the grip of the bubble's corner took the pointer anywhere in the bubble (its containment mask, the
bubble's outline, without its own bounds), so its cursor and its press were everywhere the words did not catch them
first; which corner it stands on changes with the side of the tail, after a resize too. After sequences of resizes
(outwards, inwards, to the least size, released outside the bubble and outside the window) the pointer over the words
has the plain arrow and a click on a button of the bubble reaches it.
"""
import unittest

from PySide6.QtCore import QObject, QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from meridiana.gui.backend.assistant import build_page
from quick.gestures import pump, wait_for


class GripTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['r648-tests'])

    def setUp(self):
        engine, window, _ = build_page('meridio', options={'reducedMotion': True})
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        self.window, self.layer = window, window.findChild(QObject, 'assistantLayer')
        wait_for(lambda: not self.layer.property('relocating'), 5)

        def cleanup():
            window.close()
            delete(engine)
        self.addCleanup(cleanup)

    def item(self, name):
        return self.layer.findChild(QObject, name)

    def resize(self, way, steps, release_at=None):
        grip = self.item('assistantGrip')
        start = grip.mapToScene(QPointF(8, 8)).toPoint()
        QTest.mousePress(self.window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        for i in range(1, steps + 1):
            QTest.mouseMove(self.window, start + way * i)
            pump(1)
        end = release_at if release_at is not None else start + way * steps
        QTest.mouseRelease(self.window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)
        pump(50)

    def assert_plain(self, what):
        self.assertFalse(self.layer.property('resizing'), what + ': the grip still held')
        scroll = self.item('conversationScroll')
        middle = scroll.mapToScene(QPointF(scroll.width() / 2, scroll.height() / 2)).toPoint()
        QTest.mouseMove(self.window, middle)
        pump(30)
        self.assertNotIn(self.window.cursor().shape(), (Qt.CursorShape.SizeFDiagCursor, Qt.CursorShape.SizeBDiagCursor),
                         what + ': the grip\'s cursor over the words')
        grip = self.item('assistantGrip')
        self.assertFalse(grip.contains(grip.mapFromScene(QPointF(middle))), what + ': the grip takes the middle')
        button = self.item('assistantDock')
        clicked = []
        button.clicked.connect(lambda: clicked.append(True))
        QTest.mouseClick(self.window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint())
        pump(30)
        button.clicked.disconnect()
        self.assertTrue(clicked, what + ': a click on a button of the bubble did not reach it')

    def test_after_sequences_of_resizes_the_words_have_the_pointer(self):
        self.assert_plain('before any resize')
        self.resize(QPoint(-6, -6), 30)
        self.assert_plain('outwards')
        self.resize(QPoint(8, 8), 60)
        self.assert_plain('inwards to the least size')
        self.resize(QPoint(-5, 0), 20, release_at=QPoint(5, 5))
        self.assert_plain('released outside the bubble')
        self.resize(QPoint(0, -5), 20, release_at=QPoint(self.window.width() + 50, -50))
        self.assert_plain('released outside the window')


if __name__ == '__main__':
    unittest.main()
