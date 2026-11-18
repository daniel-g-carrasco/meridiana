"""The plan's view holds still while its size changes (R372): one change costs nothing, the second makes the picture, the
drawing comes back when the size is still."""

from __future__ import annotations

import unittest

import _setup


class StillViewTest(unittest.TestCase):
    def setUp(self):
        self.app = _setup.qt_or_skip()
        from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

        from meridiana.ui.still_view import StillWhileResized

        drawn = self.drawn = []

        class View(QGraphicsView):
            def paintEvent(self, event):
                if not self.still.painted():
                    drawn.append(self.viewport().size())
                    super().paintEvent(event)

            def resizeEvent(self, event):
                super().resizeEvent(event)
                self.still.resized()

        self.view = View()
        self.scene = QGraphicsScene(self.view)
        self.view.setScene(self.scene)
        self.view.still = StillWhileResized(self.view)
        self.view.resize(300, 200)
        self.view.show()
        self.addCleanup(self.view.close)
        _setup.turn_events(self.app, 500)

    def test_one_change_of_size_makes_no_picture(self):
        self.view.resize(320, 200)
        _setup.turn_events(self.app, 20)
        self.assertIsNone(self.view.still.picture)

    def test_the_second_change_makes_the_picture_and_the_drawing_stops(self):
        self.view.resize(320, 200)
        _setup.turn_events(self.app, 10)
        self.view.resize(340, 200)
        self.assertIsNotNone(self.view.still.picture)
        _setup.turn_events(self.app, 10)
        self.drawn.clear()
        self.view.resize(360, 200)
        _setup.turn_events(self.app, 10)
        self.assertEqual(self.drawn, [])

    def test_the_drawing_comes_back_when_the_size_is_still(self):
        self.view.resize(320, 200)
        _setup.turn_events(self.app, 10)
        self.view.resize(340, 200)
        self.drawn.clear()
        _setup.turn_events(self.app, 500)
        self.assertIsNone(self.view.still.picture)
        self.assertTrue(self.drawn)
        self.assertEqual(self.drawn[-1].width(), self.view.viewport().width())

    def test_a_hidden_view_makes_none(self):
        self.view.hide()
        self.view.resize(320, 200)
        self.view.resize(340, 200)
        self.assertIsNone(self.view.still.picture)

    def test_the_picture_stands_in_the_middle_of_the_view(self):
        self.view.resize(320, 200)
        _setup.turn_events(self.app, 10)
        self.view.resize(340, 200)
        self.assertIsNotNone(self.view.still.picture)
        self.assertEqual(self.view.grab().size(), self.view.size())


if __name__ == "__main__":
    unittest.main()
