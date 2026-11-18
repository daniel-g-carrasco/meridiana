"""R448: the Quick window opens where a screen shows it (06/11/2026).

On Daniel's PC the window came up at x -2887, where no screen is: open, but nowhere to be found. The window watches
its position: when no screen shows its title strip, it comes back in the middle of the primary screen; a window whose
title is in sight is only kept inside its screen's useful area (R430), never moved to the middle.

    python -m unittest quick.test_placement
"""
import os
import unittest

from PySide6.QtCore import QPoint
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from meridiana.quick.app import keep_on_screen, screen_for, watch_placement


def setUpModule():
    global APP
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    APP = QApplication.instance() or QApplication(['placement-test'])


class Placement(unittest.TestCase):
    def setUp(self):
        self.window = QWindow()
        self.area = QGuiApplication.primaryScreen().availableGeometry()
        self.window.resize(min(600, self.area.width() - 40), min(400, self.area.height() - 40))
        self.window.setFramePosition(QPoint(self.area.left() + 10, self.area.top() + 10))
        self.timer = watch_placement(self.window)
        self.window.show()
        QTest.qWait(300)

    def tearDown(self):
        self.timer.stop()
        self.window.destroy()

    def inside(self):
        frame = self.window.frameGeometry()
        return self.area.contains(frame.topLeft()) and self.area.contains(frame.bottomRight())

    def test_a_window_where_no_screen_is_comes_back_in_the_middle(self):
        self.window.setFramePosition(QPoint(-2887, 120))
        self.assertTrue(screen_for(self.window)[1])
        QTest.qWait(600)
        self.assertTrue(self.inside(), self.window.frameGeometry())
        frame = self.window.frameGeometry()
        self.assertLessEqual(abs(frame.center().x() - self.area.center().x()), 2, frame)

    def test_a_window_below_every_screen_comes_back_too(self):
        self.window.setFramePosition(QPoint(self.area.left() + 20, self.area.bottom() + 3000))
        QTest.qWait(600)
        self.assertTrue(self.inside(), self.window.frameGeometry())

    def test_a_window_with_its_title_in_sight_is_not_moved(self):
        where = QPoint(self.area.left() + 30, self.area.top() + 25)
        self.window.setFramePosition(where)
        QTest.qWait(600)
        self.assertEqual(self.window.frameGeometry().topLeft(), where)
        self.assertFalse(screen_for(self.window)[1])

    def test_keep_on_screen_brings_a_lost_window_back_at_once(self):
        self.timer.stop()
        self.window.setFramePosition(QPoint(-2887, -900))
        keep_on_screen(self.window)
        self.assertTrue(self.inside(), self.window.frameGeometry())


if __name__ == '__main__':
    unittest.main()
