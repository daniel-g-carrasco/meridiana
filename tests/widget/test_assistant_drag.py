"""Meridio dragged with the bubble open (Daniel, 03/11/2026, his recording): the two go together over a picture of the
window, nothing laid out and no side changed but for lack of room; the real bubble takes the place at the release."""
import unittest
from unittest import mock

import _setup
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QWidget

from meridiana import assistant as core
from meridiana.ui.assistant import Assistant, DragStage

setUpModule = _setup.keep_global_state


class Follow(unittest.TestCase):
    AREA = (1000, 800)
    SIZE = (320, 400)

    def test_it_keeps_its_side_past_the_middle_of_the_area(self):
        """bubble_place goes by the middle: this is what jumped at every half."""
        for x in (100, 400, 501, 600):
            b = core.bubble_follow("left", 20, self.SIZE, (x, 300, 46, 46), self.AREA)
            self.assertEqual(b.tail, "left", x)
            self.assertEqual(b.x, x + 46 + core.GAP)
            self.assertEqual(b.y, 300 + 23 - 20)

    def test_it_changes_side_only_when_this_one_has_no_room(self):
        x = self.AREA[0] - self.SIZE[0] - 46 - core.GAP
        self.assertEqual(core.bubble_follow("left", 20, self.SIZE, (x, 300, 46, 46), self.AREA).tail, "left")
        other = core.bubble_follow("left", 20, self.SIZE, (x + 1, 300, 46, 46), self.AREA)
        self.assertEqual(other.tail, "right")
        self.assertEqual(other.x + other.width + core.GAP, x + 1)

    def test_along_its_side_it_stops_at_the_edges_and_goes_back_where_it_was(self):
        low = core.bubble_follow("left", 20, self.SIZE, (100, 750, 46, 46), self.AREA)
        self.assertEqual(low.y + low.height, self.AREA[1])
        self.assertEqual(low.at, 750 + 23 - low.y)                          # the tail still at him
        self.assertEqual(core.bubble_follow("left", 20, self.SIZE, (100, 300, 46, 46), self.AREA).y, 300 + 23 - 20)

    def test_in_an_area_too_small_there_is_still_a_place(self):
        b = core.bubble_follow("left", 20, self.SIZE, (10, 10, 46, 46), (340, 300))
        self.assertEqual((b.width, b.height), self.SIZE)


class Dragged(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.area = QWidget()
        self.addCleanup(_setup.dispose, self.area)
        self.area.resize(1400, 900)
        self.a = Assistant(self.area)
        self.a.show()
        self.area.show()
        self.a.move(1000, 700)
        self.a.opened = False
        self.a.toggle()
        _setup.turn_events(self.app, 500)
        self.assertTrue(self.a.bubble.isVisible())

    def mouse(self, kind, at, button=Qt.MouseButton.NoButton, buttons=Qt.MouseButton.LeftButton):
        face = self.a.face
        event = QMouseEvent(kind, QPointF(face.mapFromGlobal(at)), QPointF(at), button, buttons,
                            Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(face, event)

    def press(self):
        at = self.a.face.mapToGlobal(self.a.face.rect().center())
        self.mouse(QEvent.Type.MouseButtonPress, at, Qt.MouseButton.LeftButton)
        return at

    def release(self, at):
        self.mouse(QEvent.Type.MouseButtonRelease, at, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)

    def test_a_move_lays_out_nothing_and_the_real_bubble_waits(self):
        start = self.press()
        was = self.a.bubble.geometry()
        with mock.patch.object(self.a.bubble, "set_shape") as laid:
            self.mouse(QEvent.Type.MouseMove, start - QPoint(60, 40))
            for step in range(2, 6):
                self.mouse(QEvent.Type.MouseMove, start - QPoint(60 * step, 40))
            self.assertFalse(laid.called)
        self.assertIsInstance(self.a.stage, DragStage)
        self.assertEqual(self.a.bubble.geometry(), was)
        self.assertEqual(self.a.stage.place.topLeft() - was.topLeft(), self.a.pos() - QPoint(1000, 700))

    def test_the_picture_of_the_window_leaves_him_and_the_bubble_out_and_the_focus_stays(self):
        self.a.field.setFocus()
        start = self.press()
        bubble_at, him = self.a.bubble.pos(), self.a.pos()
        self.mouse(QEvent.Type.MouseMove, start - QPoint(60, 0))
        self.assertEqual(self.a.bubble.pos(), bubble_at)
        self.assertEqual(self.a.y(), him.y())
        self.assertTrue(self.a.bubble.isVisible())
        self.assertEqual(self.a.stage.ground.deviceIndependentSize().toSize(), self.area.size())

    def test_the_release_gives_the_real_bubble_the_place_and_the_stage_goes(self):
        start = self.press()
        to = start - QPoint(200, 100)
        self.mouse(QEvent.Type.MouseMove, to)
        place = self.a.stage.place
        self.release(to)
        self.assertIsNone(self.a.stage)
        self.assertEqual(self.a.bubble.geometry(), place)
        self.assertEqual(self.a.bubble.tail_at(), self.a.y() + core.SIZE / 2 - place.y()
                         if self.a.bubble.shape.tail in ("left", "right") else self.a.x() + core.SIZE / 2 - place.x())

    def test_a_click_makes_no_picture(self):
        at = self.press()
        with mock.patch.object(self.a.area, "grab") as grab:
            self.release(at)
        self.assertFalse(grab.called)
        self.assertIsNone(self.a.stage)

    def test_hidden_during_the_drag_the_stage_does_not_stay_on_the_window(self):
        start = self.press()
        self.mouse(QEvent.Type.MouseMove, start - QPoint(60, 0))
        stage = self.a.stage
        self.a.hide()
        self.assertIsNone(self.a.stage)
        self.assertFalse(stage.isVisible())


if __name__ == "__main__":
    unittest.main()
