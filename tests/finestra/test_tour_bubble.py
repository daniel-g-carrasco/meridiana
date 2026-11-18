"""The bubble of the guided tour (R318, R319): as tall as every step needs, in both languages, never cutting the
text or a button; the steps reached from the menu of «step n of m»; the words coming little by little as an answer
in a chat, whole at once with less motion and when a click asks."""
import unittest

import _setup
from _setup import wait_until
from meridiana import config, i18n, tour
from meridiana.ui import motion
from meridiana.ui.tour import TOUR_BUBBLE, step_html, step_plain

setUpModule = _setup.keep_global_state


class TourBubble(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def start(self, size=(1366, 760), moving=False, status="paused", step=None):
        _setup.window(self, cfg=config.Config(background="none", tour_status=status), size=size)
        win = self.win
        win.assistant.reduced_motion = not moving
        if step is None:
            win._start_tour()
        else:
            win.start_tour_at(step)
        return win, win.tour_dialog

    def settle(self, dialog):
        """The words whole and the bubble measured for them (the bubble opens first: its fit waits for that)."""
        dialog.typing.finish()
        dialog.clear_timer.stop()               # the spotlight's poll is not what is measured here
        a = dialog.host.assistant

        def fitted():
            dialog._fit_bubble()
            return (a.bubble_animation is None and a.bubble.height() == a.bubble_dims[1]
                    and dialog.scroll.height() >= dialog.measure.heightForWidth(dialog.scroll.width()))
        self.assertTrue(wait_until(self.app, fitted, 5))
        self.app.processEvents()

    def check_whole(self, dialog, label):
        a = dialog.host.assistant
        bubble = a.bubble.rect()
        # the text whole: the label as tall as its text needs at its real width, and nothing to scroll
        self.assertGreaterEqual(dialog.description.height(),
                                dialog.description.heightForWidth(dialog.description.width()), label)
        self.assertEqual(dialog.scroll.verticalScrollBar().maximum(), 0, label)
        # the end of the text above the buttons, all inside the bubble
        end = dialog.scroll.mapTo(a.bubble, dialog.scroll.rect().bottomLeft()).y()
        buttons = dialog.next.mapTo(a.bubble, dialog.next.rect().topLeft()).y()
        self.assertLessEqual(end, buttons, label)
        self.assertTrue(bubble.contains(dialog.next.mapTo(a.bubble, dialog.next.rect().bottomRight())), label)
        # no button cut: each as wide as its text asks, the top row inside the card
        for button in (dialog.previous, dialog.next, dialog.skip, dialog.steps_button):
            self.assertGreaterEqual(button.width(), button.sizeHint().width(), (label, button.text()))
        self.assertLessEqual(dialog.skip.mapTo(dialog, dialog.skip.rect().bottomRight()).x(), dialog.width(), label)
        self.assertLessEqual(dialog.steps_button.geometry().right(), dialog.skip.geometry().left(), label)

    def test_every_step_is_whole_in_both_languages_and_at_two_sizes(self):
        for language, size in (("en", (1366, 760)), ("it", (1366, 760)), ("it", (1920, 1032))):
            with self.subTest(language=language, size=size):
                i18n.setup(language)
                win, dialog = self.start(size=size)
                for index, item in enumerate(tour.steps()):
                    dialog.index = index
                    dialog.present()
                    self.settle(dialog)
                    self.check_whole(dialog, (language, size, item.id))
                dialog.reject()
                _setup.dispose(win)
        i18n.setup("en")

    def test_the_bubble_is_measured_after_it_has_opened_not_while_it_opens(self):
        # seen in Daniel's photo of step 1: with the bubble still opening the fit ran at once, took the card for
        # smaller than it is and left the 560 px of the start, half of them empty
        i18n.setup("it")
        win, dialog = self.start(moving=True, step=0)
        a = win.assistant
        self.settle(dialog)
        self.assertLess(a.bubble_dims[1], TOUR_BUBBLE[1])
        need = dialog.measure.heightForWidth(dialog.scroll.width())
        self.assertLessEqual(dialog.scroll.height() - need, 3)          # no empty room below the text
        self.check_whole(dialog, "step 1")
        dialog.reject()
        i18n.setup("en")

    def test_a_step_longer_than_the_area_scrolls_and_is_not_cut(self):
        win, dialog = self.start(size=(1366, 760))
        a = win.assistant
        self.settle(dialog)
        top, _w, available = a.free()
        # a window so low that the longest step cannot be shown whole: the area is the limit, the text scrolls
        a.free = lambda: (top, 1366, 330)
        dialog.index = max(range(len(tour.steps())), key=lambda i: len(step_plain(tour.steps()[i])))
        dialog.present()
        dialog.typing.finish()
        dialog.clear_timer.stop()
        self.assertTrue(wait_until(self.app, lambda: (dialog._fit_bubble(), a.bubble.height() == a.bubble_dims[1])[1], 5))
        self.assertLessEqual(a.bubble_dims[1], 330)
        self.assertGreater(dialog.scroll.verticalScrollBar().maximum(), 0)
        bar = dialog.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())                                      # its end can be reached
        end = dialog.description.mapTo(dialog.scroll.viewport(), dialog.description.rect().bottomLeft()).y()
        self.assertLessEqual(end, dialog.scroll.viewport().height())
        dialog.reject()

    def test_the_list_of_steps_jumps_to_a_step_like_next_does(self):
        win, dialog = self.start(step=1)
        self.assertEqual(dialog.steps_button.text(), "Step 2 of 13")
        self.assertEqual([a.text().split(". ", 1)[0] for a in dialog.steps_actions],
                         [str(n) for n in range(1, len(tour.steps()) + 1)])
        self.assertTrue(dialog.steps_actions[1].isChecked())
        titles = [item.title for item in tour.steps()]
        self.assertEqual([a.text().split(". ", 1)[1] for a in dialog.steps_actions], titles)
        dialog.steps_actions[6].trigger()                               # the menu's own path
        self.assertEqual(dialog.index, 6)
        self.assertEqual(dialog.heading.text(), titles[6])
        self.assertEqual(win.cfg.tour_step, 6)
        self.assertEqual(dialog.steps_button.text(), "Step 7 of 13")
        self.assertTrue(dialog.steps_actions[6].isChecked())
        dialog.next.click()                                             # Next goes on from there
        self.assertEqual(dialog.index, 7)
        dialog.reject()

    def test_tour_option_opens_the_tour_at_the_step_asked_for(self):
        # `meridiana --tour 3`: the arguments give the request, the window opens the tour there (app.main does this
        # once the window is shown)
        _rest, request = tour.take_option(["meridiana", "--tour", "3"])
        win, dialog = self.start(step=request.index)
        self.assertEqual(dialog.index, 2)
        self.assertEqual(dialog.heading.text(), tour.steps()[2].title)
        self.assertEqual(dialog.steps_button.text(), "Step 3 of 13")
        self.assertEqual(win.cfg.tour_status, "active")
        self.assertFalse(dialog.invitation)
        dialog.reject()
        # by id, the same step
        _rest, request = tour.take_option(["meridiana", "--tour", "views"])
        self.assertEqual(request.index, 2)
        # `--tour new` is the first start: the invitation, after the moment the program waits
        _rest, request = tour.take_option(["meridiana", "--tour", "new"])
        self.assertTrue(request.new)
        _setup.dispose(win)
        _setup.window(self, cfg=config.Config(background="none", tour_status="new"))
        self.win._offer_tour()
        self.assertTrue(self.win.tour_dialog.invitation)
        self.assertTrue(self.win.tour_dialog.progress.isVisibleTo(self.win.tour_dialog))
        self.assertFalse(self.win.tour_dialog.steps_button.isVisibleTo(self.win.tour_dialog))
        self.win.tour_dialog.reject()

    def test_the_menu_of_steps_is_popped_from_the_step_button(self):
        win, dialog = self.start(step=2)
        self.assertIs(dialog.steps_button.menu(), dialog.steps_menu)
        self.assertEqual(dialog.steps_button.objectName(), "filter")      # the pill of the system, no local sheet
        self.assertEqual(dialog.steps_button.styleSheet(), "")
        dialog.reject()

    def test_the_words_come_little_by_little_and_end_whole(self):
        win, dialog = self.start(moving=True, step=3)
        item = tour.steps()[3]
        full = step_html(item, win.assistant.colours["muted"])
        self.assertTrue(dialog.typing.running)
        self.assertEqual(dialog.measure.text(), full)                     # measured whole from the start
        partial = dialog.description.text()
        self.assertLess(len(partial), len(full))
        self.assertTrue(wait_until(self.app, lambda: len(dialog.description.text()) > len(partial) or
                                   not dialog.typing.running, 2))
        self.assertTrue(wait_until(self.app, lambda: not dialog.typing.running, 4))
        self.assertEqual(dialog.description.text(), full)
        dialog.reject()

    def test_the_layout_of_a_text_that_is_coming_stays_rich(self):
        item = tour.steps()[0]
        plain = step_plain(item)
        first = step_html(item, "#888", chars=len(item.text) + 10)       # inside the first point
        self.assertIn("<ul", first)
        self.assertEqual(first.count("<li>"), 1)
        self.assertNotIn("Try:", first)
        late = step_html(item, "#888", chars=len(plain) - 3)
        self.assertEqual(late.count("<li>"), len(item.points))
        self.assertIn("Try:", late)
        self.assertIn("font-weight", late)
        self.assertEqual(step_html(item, "#888", chars=None), step_html(item, "#888"))
        self.assertEqual(step_html(item, "#888", chars=0), "")

    def test_the_bubble_does_not_move_while_the_words_come(self):
        win, dialog = self.start(moving=True, step=4)
        a = win.assistant
        self.assertTrue(wait_until(self.app, lambda: a.bubble_animation is None and not dialog.clear_timer.isActive(), 5))
        sizes = {a.bubble.height()}
        while dialog.typing.running:
            self.app.processEvents()
            sizes.add(a.bubble.height())
            if len(sizes) > 1:
                break
        self.assertEqual(len(sizes), 1, sizes)
        dialog.reject()

    def test_a_click_on_the_text_or_next_or_previous_completes_it_first(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        win, dialog = self.start(moving=True, step=3)
        self.assertTrue(dialog.typing.running)
        full = step_html(tour.steps()[3], win.assistant.colours["muted"])
        QTest.mouseClick(dialog.description, Qt.MouseButton.LeftButton)
        self.assertFalse(dialog.typing.running)
        self.assertEqual(dialog.description.text(), full)
        self.assertEqual(dialog.index, 3)
        for button, index in ((dialog.next, 3), (dialog.previous, 3)):
            dialog.index = 3
            dialog.present()
            self.assertTrue(dialog.typing.running)
            button.click()                                              # the first click gives the words whole
            self.assertFalse(dialog.typing.running)
            self.assertEqual(dialog.index, index)
            self.assertEqual(dialog.description.text(), full)
        dialog.next.click()                                             # the next one moves on
        self.assertEqual(dialog.index, 4)
        dialog.reject()

    def test_with_less_motion_the_words_are_whole_at_once(self):
        for reduced in (False, True):
            with self.subTest(reduced=reduced):
                win, dialog = self.start(moving=not reduced, step=3)
                if reduced:
                    self.assertFalse(dialog.typing.running)
                    self.assertEqual(dialog.description.text(),
                                     step_html(tour.steps()[3], win.assistant.colours["muted"]))
                dialog.reject()
                _setup.dispose(win)
        with self.subTest(system=True):
            from unittest import mock
            win, dialog = self.start(moving=True, step=3)
            dialog.reject()
            with mock.patch.object(motion, "reduced", return_value=True):
                dialog.host.start_tour_at(4)
                self.assertFalse(win.tour_dialog.typing.running)
            win.tour_dialog.reject()

    def test_the_typing_by_the_clock_is_partial_at_n_ms_and_whole_at_the_end(self):
        from PySide6.QtCore import QCoreApplication
        typed = []
        out = motion.TypeOut()
        out.shown.connect(typed.append)
        out.start("alpha beta gamma delta " * 12)
        self.assertEqual(typed, [0])
        self.assertTrue(wait_until(self.app, lambda: len(typed) > 2, 2))
        self.assertTrue(0 < typed[-1] < out.total)
        self.assertTrue(wait_until(self.app, lambda: not out.running, 4))
        self.assertEqual(typed[-1], out.total)
        self.assertEqual(typed.count(out.total), 1)                       # whole once
        self.assertEqual(typed, sorted(typed))
        out.start("one two", reduced=True)                                # less motion: whole at once, no timer
        self.assertFalse(out.running)
        self.assertEqual(typed[-1], 7)
        QCoreApplication.processEvents()


if __name__ == "__main__":
    unittest.main()
