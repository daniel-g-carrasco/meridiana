"""Meridio alone over an area (ui/assistant.py; study 17, theme G; design 3.9): the speech bubble beside him and never
over him, the tail towards him, inside a low area with the field still there, a free corner when there is no room;
his place on each tab, sliding unless less motion is asked; the bubble that grows and fades and is resized from the
corner opposite the tail; Esc; the numbered questions and the keys 1, 2, 3; the turn with the dots and «Stop»; the
cost of a frame, the pixel style, the timer that runs only when something may move, the gaze; a place dragged and
kept per tab. He is made alone over a plain area of 1000 x 700, as the window makes him over its tabs; what the
window adds (the tabs, the sun bar, the selection to keep off, the dock, the settings, the preferences) is in
finestra/test_assistant_window.py. PySide6 and a display (offscreen will do)."""

import time
import unittest

import _setup
from _setup import wait_until

from meridiana import assistant

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class Alone(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from PySide6.QtWidgets import QWidget

        from meridiana.ui.assistant import Assistant
        self.area = QWidget()
        self.addCleanup(_setup.dispose, self.area)
        self.area.resize(1000, 700)
        self.a = Assistant(self.area)
        self.a.reduced_motion = True                        # the place at once, not after 320 ms
        self.area.show()
        self.app.processEvents()

    def wait(self, condition, seconds: float = 5.0) -> bool:
        return wait_until(self.app, condition, seconds)

    def corner(self):
        a = self.a
        return a.x(), a.y(), a.x() + a.width(), a.y() + a.height()

    def answered(self, a) -> bool:
        return self.wait(lambda: a.mood.state == assistant.IDLE and a.messages and a.messages[-1][0] != "you")

    def test_open_he_stays_visible_and_the_bubble_opens_beside_him_with_the_tail_towards_him(self):
        from PySide6.QtCore import QRect
        a = self.a
        a.open_panel()
        self.app.processEvents()
        self.assertTrue(a.opened and a.isVisible() and a.bubble.isVisible())
        self.assertEqual((a.width(), a.height()), (46, 46))                      # never covered (R33)
        self.assertFalse(a.bubble.geometry().intersects(a.geometry()))
        shape = a.bubble.shape
        self.assertEqual(shape.tail, "right")                                     # he is at the right
        self.assertEqual(a.bubble.geometry().right() + 1 + assistant.GAP, a.x())
        self.assertEqual(a.bubble.y() + shape.at, a.y() + 23)                     # pointing at his centre
        self.assertEqual((a.bubble.width(), a.bubble.height()), (320, 400))
        self.assertTrue(QRect(0, 0, self.area.width(), self.area.height()).contains(a.bubble.geometry()))
        a.places["production"] = ("left", "bottom", 12, 12)                    # dragged to the left
        a.set_tab("production")                                                   # he is at the left
        self.app.processEvents()
        self.assertEqual(a.bubble.shape.tail, "left")
        self.assertEqual(a.bubble.x(), a.x() + 46 + assistant.GAP)
        self.assertFalse(a.small.isVisible())                                     # one Meridio, not two

    def test_opened_in_a_low_area_the_field_is_still_there(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtWidgets import QWidget

        from meridiana.ui.assistant import Assistant
        for height in (400, 300, 240):
            with self.subTest(height=height):
                area = QWidget()
                area.resize(700, height)
                a = Assistant(area)
                a.reduced_motion = True
                area.show()
                a.open_panel()
                self.app.processEvents()
                b = a.bubble
                self.assertTrue(b.isVisible())
                self.assertLessEqual(b.y() + b.height(), area.height())            # inside the area
                self.assertGreaterEqual(b.y(), 0)
                self.assertFalse(b.geometry().intersects(a.geometry()))
                bottom = a.field.mapTo(b, QPoint(0, a.field.height())).y()
                self.assertTrue(a.field.isVisible())
                self.assertLessEqual(bottom, b.height())                           # the field is not cut
                self.assertEqual(a.questions_box.isVisible(), height >= 300)       # the questions give way
                _setup.dispose(area)

    def test_no_room_beside_him_he_slides_to_a_free_corner_and_opens_there(self):
        from PySide6.QtWidgets import QWidget

        from meridiana.ui.assistant import Assistant
        area = QWidget()
        self.addCleanup(_setup.dispose, area)
        area.resize(900, 600)
        a = Assistant(area)
        a.reduced_motion = True
        a.avoid = lambda: [(400, 100, 500, 500)]            # the selection fills the right side
        area.show()
        self.app.processEvents()
        self.assertEqual((a.x(), a.y()), (900 - 46 - 12, 600 - 46 - 12))
        a.open_panel()
        self.app.processEvents()
        self.assertEqual((a.x(), a.y()), (12, 12))          # the top left corner, the farthest from it
        self.assertEqual((a.bubble.x(), a.bubble.shape.tail), (12 + 46 + assistant.GAP, "left"))
        self.assertFalse(a.bubble.geometry().intersects(a.geometry()))
        self.assertEqual(a.places["model"], ("left", "top", 12, 12))

    def test_its_place_on_each_tab_above_what_is_reserved_below_and_under_what_is_at_the_top(self):
        from meridiana import assistant as core
        a, w, h = self.a, self.area.width(), self.area.height()
        a.reserved = lambda: 30                             # the sun bar of the model (the window's: finestra)
        a.top = lambda: 50                                  # the row of the phases and the bar
        a.reposition()
        left, top, right, bottom = self.corner()
        self.assertEqual(right, w - core.MARGIN)                         # by the properties
        self.assertEqual(bottom, h - core.MARGIN - 30)                   # above the sun bar
        a.set_tab("production")
        left, top, right, bottom = self.corner()
        self.assertEqual((right, bottom), (w - core.MARGIN, h - core.MARGIN))   # bottom right, nothing below
        a.set_tab("economics")
        left, top, right, bottom = self.corner()
        self.assertEqual((right, bottom), (w - core.MARGIN, h - core.MARGIN))
        a.open_panel()
        self.app.processEvents()
        self.assertGreaterEqual(a.bubble.y(), 50)            # never over the phases and the bar

    def test_it_slides_to_its_place_unless_less_motion_is_asked(self):
        from PySide6.QtCore import QAbstractAnimation
        a = self.a
        a.reduced_motion = False
        a.reserved = lambda: 30                             # the model above its sun bar, production lower
        a.reposition()
        a.set_tab("production")                             # another place (the Plant shares the Model's)
        self.assertEqual(a.animation.state(), QAbstractAnimation.State.Running)
        self.assertEqual(a.animation.duration(), 320)
        a.reduced_motion = True
        a.set_tab("economics")
        self.assertEqual(a.animation.state(), QAbstractAnimation.State.Stopped)
        self.assertEqual(a.pos(), a.target())

    def test_the_bubble_fades_in_at_its_size_sliding_from_him_and_out_without_the_effect_left_behind(self):
        from PySide6.QtCore import QAbstractAnimation

        from meridiana.ui import assistant as ui
        a = self.a
        a.reduced_motion = False
        a.open_panel()
        group = a.bubble_animation
        self.assertIsNotNone(group)
        self.assertEqual(group.state(), QAbstractAnimation.State.Running)
        self.assertEqual(group.duration(), ui.OPEN_MS)
        self.assertIsNotNone(a.bubble.graphicsEffect())
        final = a.bubble.shape
        self.assertEqual((a.bubble.width(), a.bubble.height()), (final.width, final.height))   # its size at once
        goal = group.animationAt(0).endValue()                                      # where it slides to
        self.assertEqual(abs(a.bubble.x() - goal.x()) + abs(a.bubble.y() - goal.y()), ui.SLIDE_IN)
        self.assertTrue(self.wait(lambda: a.bubble_animation is None, 3))
        self.assertIsNone(a.bubble.graphicsEffect())                                # costs the double: gone
        self.assertEqual((a.bubble.width(), a.bubble.height()), (final.width, final.height))
        a.close_panel()
        self.assertEqual(a.bubble_animation.duration(), ui.CLOSE_MS)
        self.assertTrue(a.bubble.isVisible())
        self.assertTrue(self.wait(lambda: not a.bubble.isVisible(), 3))
        self.assertIsNone(a.bubble.graphicsEffect())
        a.reduced_motion = True                                                     # at once, both ways
        a.open_panel()
        self.assertIsNone(a.bubble_animation)
        self.assertEqual((a.bubble.width(), a.bubble.height()), (final.width, final.height))
        a.close_panel()
        self.assertFalse(a.bubble.isVisible())

    def test_the_bubble_is_resized_from_the_corner_opposite_the_tail_and_says_its_size(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        a = self.a
        heard = []
        a.bubbleResized.connect(lambda w, h: heard.append((w, h)))   # what the window keeps in the settings
        a.open_panel()
        self.app.processEvents()
        self.assertEqual(a.bubble.shape.grip, "top-left")
        g = a.bubble.grip
        self.assertLess(g.x(), a.bubble.width() / 2)
        self.assertLess(g.y(), a.bubble.height() / 2)
        before = a.bubble.geometry()
        centre = g.rect().center()
        QTest.mousePress(g, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre)
        QTest.mouseMove(g, centre + QPoint(-40, -30))
        self.app.processEvents()
        QTest.mouseRelease(g, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre + QPoint(-40, -30))
        self.app.processEvents()
        after = a.bubble.geometry()
        self.assertGreater(after.width(), before.width())
        self.assertGreater(after.height(), before.height())
        self.assertEqual((after.right(), after.bottom()), (before.right(), before.bottom()))   # the tail's corner stays
        self.assertEqual(heard[-1], (after.width(), after.height()))
        self.assertFalse(after.intersects(a.geometry()))
        a.set_bubble_size(100, 100)                                                 # never under the minimum
        self.assertEqual((a.bubble.width(), a.bubble.height()), assistant.BUBBLE_MIN)

    def test_esc_in_the_field_closes_it(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        a = self.a
        heard = []
        a.openedChanged.connect(heard.append)
        a.open_panel()
        _setup.keyboard_or_skip(self, a.field)              # Esc needs the keyboard (said when the desktop gives none)
        QTest.keyClick(a.field, Qt.Key.Key_Escape)
        self.assertFalse(a.opened)
        self.assertTrue(a.isVisible() and not a.bubble.isVisible())
        self.assertEqual((a.width(), a.height()), (46, 46))
        self.assertEqual(heard, [True, False])

    def test_the_questions_ready_follow_the_tab_numbered_and_the_keys_1_2_3_send_them(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from meridiana import assistant as core
        a = self.a
        self.assertEqual([b.text() for b in a.questions], core.questions("model"))
        self.assertEqual([b.number.text() for b in a.questions], ["1", "2", "3"])
        a.set_tab("production")
        self.assertEqual([b.text() for b in a.questions], core.questions("production"))
        a.open_panel()
        self.app.processEvents()
        QTest.keyClick(a.field, Qt.Key.Key_2)
        self.assertEqual(a.messages[0], ("you", core.questions("production")[1]))
        self.assertEqual(a.field.text(), "")
        self.assertTrue(self.answered(a))
        a.field.setText("12 moduli")                        # a number being typed is not a choice
        QTest.keyClick(a.field, Qt.Key.Key_3)
        self.assertEqual(len(a.messages), 2)
        a.field.clear()
        a.questions[2].chosen.emit(a.questions[2].text())   # a click on the row
        self.assertEqual(a.messages[-1], ("you", core.questions("production")[2]))

    def test_while_he_answers_the_questions_go_the_dots_show_and_stop_ends_the_turn(self):
        a = self.a
        a.open_panel()
        self.app.processEvents()
        self.assertTrue(a.questions_box.isVisible())
        a.ask("Quante stringhe?")
        self.assertEqual(a.mood.state, assistant.THINKING)
        self.assertTrue(a.frame.thinking)                   # the face that thinks, even still
        self.assertFalse(a.questions_box.isVisible())
        self.assertTrue(a.dots.isVisible() and a.stop_action.isVisible())
        self.assertTrue(a.pending.isActive())
        a.stop()
        self.assertFalse(a.pending.isActive())
        self.assertEqual(a.messages[-1], ("note", "Stopped."))
        self.assertEqual(a.mood.state, assistant.IDLE)
        self.assertTrue(a.questions_box.isVisible())
        self.assertFalse(a.dots.isVisible() or a.stop_action.isVisible())
        a.ask("E adesso?")
        self.assertTrue(self.answered(a))
        self.assertEqual(a.messages[-1], ("assistant", "Assistant not connected yet"))
        self.assertTrue(a.questions_box.isVisible())

    def test_sixty_frames_cost_less_than_a_millisecond_each_in_both_styles(self):
        a = self.a
        a.face.grab()
        for style in ("smooth", "pixel"):
            a.set_style(style)
            a.frame = assistant.Frame()
            a.face.grab()
            costs = []
            for k in range(60):
                a.frame = assistant.Frame(gaze=((k % 3) - 1, (k // 3 % 3) - 1), blink=k % 7 == 0, rays=k * 0.3,
                                          scale=1 + 0.02 * (k % 5) / 4, expression=("", "wink")[k % 11 == 0])
                t = time.perf_counter()
                a.face.grab()
                costs.append((time.perf_counter() - t) * 1000)
            with self.subTest(style=style):
                self.assertLess(sum(costs) / len(costs), 1.0, f"{style}: {sum(costs) / len(costs):.2f} ms a frame")

    def test_the_pixel_style_is_drawn_crisp_in_the_three_colours(self):
        from meridiana.ui.assistant import picture
        a = self.a
        pix = picture(a.colours["text"], a.colours["assistant"], 34, style="pixel").toImage()
        allowed = {a.colours["text"].lower(), assistant.INK, assistant.disc_colour(a.colours["assistant"])}
        seen = set()
        for x in range(pix.width()):
            for y in range(pix.height()):
                c = pix.pixelColor(x, y)
                if c.alpha():
                    self.assertEqual(c.alpha(), 255)
                    seen.add(c.name())
        self.assertEqual(seen, allowed)
        a.set_style("pixel")
        self.assertEqual(a.style, "pixel")
        a.set_style("blurry")
        self.assertEqual(a.style, "smooth")

    def test_the_gaze_follows_the_pointer_read_at_each_frame_not_from_every_event(self):
        """R120: no application-wide event filter (every event of every widget went through it): the pointer is
        read at each frame of the animation."""
        from unittest import mock

        from PySide6.QtCore import QPoint
        a = self.a
        a._window_active = lambda: True
        inside = a.area.mapToGlobal(QPoint(10, 10))
        with mock.patch("meridiana.ui.assistant.QCursor.pos", return_value=inside),                 mock.patch.object(a.mood, "look_at") as look:
            a._tick()
            self.assertEqual(look.call_count, 1)
            a._tick()                                       # the pointer still: nothing to look at again
            self.assertEqual(look.call_count, 1)

    def test_the_timer_runs_only_when_something_may_move(self):
        a = self.a
        a.reduced_motion = False
        a._window_active = lambda: True
        a._update_timer()
        self.assertTrue(a.timer.isActive())
        self.assertEqual(a.timer.interval(), 50)
        a.reduced_motion = True                             # the desktop asks for less motion: still
        self.assertFalse(a.timer.isActive())
        self.assertEqual(a.frame, assistant.Frame())
        a.reduced_motion = False
        self.assertTrue(a.timer.isActive())
        a.set_animated(False)                               # the preference
        self.assertFalse(a.timer.isActive())
        a.set_animated(True)
        self.assertTrue(a.timer.isActive())
        a._window_active = lambda: False                    # another window has the keyboard
        a._tick()
        self.assertFalse(a.timer.isActive())
        a._window_active = lambda: True
        a._update_timer()
        self.assertTrue(a.timer.isActive())
        a.hide()                                            # hidden (the preferences' switch)
        self.assertFalse(a.timer.isActive())
        a.show()
        self.assertTrue(a.timer.isActive())
        a.set_state(assistant.THINKING)
        a.reduced_motion = True
        self.assertEqual(a.frame, assistant.Frame(thinking=True))      # the state shows even still

    def test_the_pointer_over_the_area_gives_the_gaze(self):
        from PySide6.QtCore import QPointF
        a = self.a
        a.reduced_motion = False
        a._window_active = lambda: True
        a._update_timer()
        centre = a.mapToGlobal(a.rect().center())
        a._look_at_global(QPointF(centre.x() - 300, centre.y() - 200))
        self.assertEqual(a.mood.point, (-1, -1))
        a._look_at_global(QPointF(centre.x() + 2, centre.y()))
        self.assertEqual(a.mood.point, (0, 0))

    def test_dragged_it_keeps_the_place_of_each_tab(self):
        from PySide6.QtCore import QPoint
        a = self.a
        a.move(QPoint(200, 150))
        a.dropped()
        self.assertEqual(a.places["model"], ("left", "top", 200, 150))
        a.set_tab("economics")
        self.assertNotEqual((a.x(), a.y()), (200, 150))
        a.set_tab("model")
        self.assertEqual((a.x(), a.y()), (200, 150))


if __name__ == "__main__":
    unittest.main()
