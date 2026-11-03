"""Meridio's bubble holding still: the tail at him while the bubble is resized on all four sides (R361), nothing moving
in a conversation (R362), the small bubble's arrangement and its minimum (R363). The conversation is a stub: no model.
PySide6 and a display (offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state

# the elements of the bubble and what must hold still in them, between one event of a conversation and the next
STILL = ("bubble", "head", "status", "context", "conversation", "slot", "questions_box", "attach_row", "field", "panel")


def snapshot(a) -> dict:
    from PySide6.QtCore import QPoint
    out = {"bubble": a.bubble.geometry().getRect(), "text width": a.conversation.viewport().width()}
    for name in STILL[1:]:
        w = getattr(a, name)
        at = w.mapTo(a.bubble, QPoint(0, 0))
        out[name] = (w.isVisible(), at.x(), at.y(), w.width(), w.height())
    return out


def jumps(before: dict, after: dict) -> list:
    """What moved or changed its size, visible before and after. An element coming and going in a kept place is not a
    jump: what would move for it is what is measured."""
    out = []
    for key, value in before.items():
        if value == after[key]:
            continue
        if isinstance(value, tuple) and len(value) == 5 and not (value[0] and after[key][0]):
            continue
        out.append((key, value, after[key]))
    return out


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def open(self, place=("right", "bottom", 12, 12), size=(1400, 900), bubble=(320, 500), avoid=None, reduced=True):
        from PySide6.QtWidgets import QWidget

        from meridiana.ui.assistant import Assistant
        area = QWidget()
        self.addCleanup(_setup.dispose, area)
        area.resize(*size)
        a = Assistant(area)
        a.reduced_motion = reduced
        a.places[a.tab] = place
        if avoid is not None:
            a.avoid = lambda: avoid
        a.set_bubble_size(*bubble)
        area.show()
        a.reposition()
        a.open_panel()
        self.settle(a)
        return a

    def settle(self, a=None) -> None:
        for _ in range(6):
            self.app.processEvents()
        if a is not None:
            self.assertTrue(_setup.wait_until(self.app, lambda: a.bubble_animation is None, 3))
            for _ in range(6):
                self.app.processEvents()


class Tail(Base):
    def mouse(self, grip, kind, at, buttons) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QMouseEvent
        self.app.sendEvent(grip, QMouseEvent(kind, grip.mapFromGlobal(at), at, Qt.MouseButton.LeftButton, buttons,
                                             Qt.KeyboardModifier.NoModifier))

    def check(self, a, where) -> None:
        """The tip as painted, at the fixed distance from him and level with his middle; its base on the straight part
        of the side, off the rounded corners."""
        from meridiana import assistant as core
        from meridiana.ui.assistant import RADIUS, TAIL_HALF, outline
        b = a.bubble
        s = b.shape
        points = [(p.x(), p.y()) for p in outline(b.width(), b.height(), s.tail, b.tail_at()).toSubpathPolygons()[0]]
        cx, cy = a.x() + core.SIZE / 2, a.y() + core.SIZE / 2
        if s.tail in ("left", "right"):
            tip = (min if s.tail == "left" else max)(points, key=lambda q: q[0])
            self.assertLessEqual(abs(b.y() + tip[1] - cy), 1, where)
            self.assertLessEqual(abs(abs(b.x() + tip[0] - cx) - (core.SIZE / 2 + core.GAP)), 1, where)
            along, length = tip[1], b.height()
        else:
            tip = (min if s.tail == "top" else max)(points, key=lambda q: q[1])
            self.assertLessEqual(abs(b.x() + tip[0] - cx), 1, where)
            self.assertLessEqual(abs(abs(b.y() + tip[1] - cy) - (core.SIZE / 2 + core.GAP)), 1, where)
            along, length = tip[0], b.width()
        self.assertGreaterEqual(along - TAIL_HALF, RADIUS + 1, where)
        self.assertLessEqual(along + TAIL_HALF, length - RADIUS - 1, where)

    def drag_in_steps(self, a, tail) -> None:
        from PySide6.QtCore import QEvent, QPointF, Qt
        self.assertEqual(a.bubble.shape.tail, tail)
        self.check(a, (tail, "opened"))
        g = a.bubble.grip
        sx = -1 if g.corner.endswith("left") else 1
        sy = -1 if g.corner.startswith("top") else 1
        fixed_corner = g.corner
        before = a.bubble.geometry()
        start = QPointF(g.mapToGlobal(g.rect().center()))
        self.mouse(g, QEvent.Type.MouseButtonPress, start, Qt.MouseButton.LeftButton)
        end = start
        for step in (30, 90, 160, 400, 60, -40, -120, -600):
            end = start + QPointF(sx * step, sy * step)
            self.mouse(g, QEvent.Type.MouseMove, end, Qt.MouseButton.LeftButton)
            self.settle()
            self.check(a, (tail, "drag", step, a.bubble.geometry().getRect()))
            now = a.bubble.geometry()
            self.assertEqual(now.right() if sx < 0 else now.left(), before.right() if sx < 0 else before.left())
            self.assertEqual(now.bottom() if sy < 0 else now.top(), before.bottom() if sy < 0 else before.top())
            self.assertTrue(a.area.rect().contains(now), (tail, step, now))
        dragged = a.bubble.geometry()
        self.mouse(g, QEvent.Type.MouseButtonRelease, end, Qt.MouseButton.NoButton)
        self.settle()
        self.assertEqual(a.bubble.geometry(), dragged, (tail, fixed_corner))        # it stays where it was let go
        self.check(a, (tail, "released"))
        a.place_bubble()                                                            # and at the next change of anything
        self.assertEqual(a.bubble.geometry(), dragged, tail)
        self.check(a, (tail, "placed again"))

    def test_on_the_left_and_on_the_right_at_every_step_and_after(self):
        for place, tail in ((("right", "bottom", 12, 12), "right"), (("right", "top", 12, 12), "right"),
                            (("left", "bottom", 12, 12), "left"), (("left", "top", 12, 12), "left"),
                            (("left", "top", 700, 300), "right"), (("left", "top", 300, 300), "left")):
            with self.subTest(place=place):
                self.drag_in_steps(self.open(place=place), tail)

    def test_above_and_below_at_every_step_and_after(self):
        # both sides of him taken: above or below is what is left
        for y, tail in ((60, "top"), (800, "bottom")):
            for x in (60, 1300):
                with self.subTest(x=x, tail=tail):
                    keep_off = [(0, y, x - 2, 46), (x + 48, y, 1400 - x, 46)]
                    a = self.open(place=("left", "top", x, y), avoid=keep_off)
                    self.drag_in_steps(a, tail)

    def test_moved_off_the_selection_it_still_points_at_him(self):
        from meridiana import assistant as core
        a = self.open(place=("left", "top", 700, 300))
        self.assertEqual(a.bubble.shape.tail, "right")
        where = a.bubble.geometry()
        a.avoid = lambda: [(where.x(), where.y(), where.width(), where.height())]
        a.place_bubble()
        self.settle()
        self.assertEqual(a.bubble.shape.tail, "left")
        self.check(a, "off the selection")
        self.assertFalse(core.overlaps(a.bubble.geometry().getRect(), (where.x(), where.y(), where.width(), where.height())))

    def test_the_grip_stops_at_the_minimum_and_where_the_tail_would_leave_him(self):
        from PySide6.QtCore import QEvent, QPointF, Qt

        from meridiana import assistant as core
        a = self.open(place=("left", "top", 12, 12))
        g = a.bubble.grip
        start = QPointF(g.mapToGlobal(g.rect().center()))
        self.mouse(g, QEvent.Type.MouseButtonPress, start, Qt.MouseButton.LeftButton)
        self.mouse(g, QEvent.Type.MouseMove, start - QPointF(2000, 2000), Qt.MouseButton.LeftButton)
        self.assertEqual((a.bubble.width(), a.bubble.height()), core.BUBBLE_MIN)
        self.mouse(g, QEvent.Type.MouseButtonRelease, start - QPointF(2000, 2000), Qt.MouseButton.NoButton)
        self.settle()
        self.check(a, "at the minimum")


class Steady(Base):
    def conversation(self, a):
        """The events of a turn and of what comes round it, in order: (name, what happens)."""
        from PySide6.QtGui import QImage
        from PySide6.QtWidgets import QLabel
        long = "Una risposta lunga, che va a capo piu' volte e scorre nel fumetto senza fine. " * 12
        picture = QImage(160, 90, QImage.Format.Format_RGB32)
        picture.fill(0x336699)
        questions = iter([["Corta?"],
                          ["Quante stringhe servono per questo impianto?", "Cosa cambia con gli ottimizzatori?",
                           "Si puo' fare meglio?"],
                          ["Una", "Due"]])
        a.suggest = lambda _tab: next(questions, ["Una"])
        card = QLabel("Una proposta di due righe\nda confermare")
        card.setProperty("confirmation", True)              # in the place of the questions
        return (("where and voice", lambda: (a.set_where("local", "Locale", "tip"), a.set_voice(True))),
                ("the first cost", lambda: a.set_cost("Locale, senza costi · 1.200 token")),
                ("asked", lambda: a.ask("Quante stringhe?")),
                ("a picture with it", lambda: a.show_pictures([(picture, "vista.png · 160×90")])),
                ("the first words", lambda: a.stream("Prime parole")),
                ("a long answer", lambda: a.stream(long)),
                ("back to thinking", a.settle),
                ("a note of progress", lambda: a.note("Ho letto il tetto", who="tool")),
                ("more words", lambda: a.stream("Altre parole")),
                ("one question back", a.finish),
                ("a longer cost", lambda: a.set_cost("4.200 token · circa 0,05 centesimi (prezzi del 01/11/2026)")),
                ("asked again", lambda: a.ask("E poi?")),
                ("three long questions", a.finish),
                ("a card comes", lambda: a.add_card(card)),
                ("the card goes", lambda: a.remove_card(card)),
                ("asked once more", lambda: a.ask("E ancora?")),
                ("stopped", a.stop),
                ("voice off", lambda: a.set_voice(False, "none")),
                ("no cost", lambda: a.set_cost("")))

    def test_nothing_moves_in_a_conversation(self):
        """R362: 28 jumps before, in this conversation (three runs: 14 of the conversation's height, 3 of the bubble,
        with the field and «Attach» under it)."""
        for reduced in (True, False):
            with self.subTest(reduced=reduced):
                a = self.open(bubble=(320, 500), reduced=reduced)
                last = snapshot(a)
                for name, event in self.conversation(a):
                    event()
                    self.settle()
                    now = snapshot(a)
                    self.assertEqual(jumps(last, now), [], name)
                    last = now
                a.stop()

    def test_a_card_takes_the_questions_place_when_there_is_no_room_for_both(self):
        from PySide6.QtWidgets import QLabel
        a = self.open(bubble=(320, 400))
        self.assertTrue(a.questions_box.isVisible())
        height = a.conversation.height()
        card = QLabel("Una proposta\nsu due righe")
        a.add_card(card)
        self.settle()
        self.assertFalse(a.questions_box.isVisible())
        self.assertEqual(a.conversation.height(), height)
        a.remove_card(card)
        self.settle()
        self.assertTrue(a.questions_box.isVisible())
        self.assertEqual(a.conversation.height(), height)
        b = self.open(bubble=(320, 640))                    # with room, both
        card = QLabel("Una proposta\nsu due righe")
        b.add_card(card)
        self.settle()
        self.assertTrue(b.questions_box.isVisible())

    def test_questions_needing_more_than_their_place_take_it_once_and_keep_it(self):
        long = "Una domanda molto lunga che va a capo tante volte in un fumetto stretto come questo qui, davvero."
        a = self.open(bubble=(320, 600))
        kept = a.slot.height()
        answers = iter([[long, long, long], ["Una"], [long, long, long]])
        a.suggest = lambda _tab: next(answers)
        a.ask("Prima")
        a.finish()
        self.settle()
        grown = a.slot.height()
        self.assertGreater(grown, kept)
        for question in ("Seconda", "Terza"):
            a.ask(question)
            a.finish()
            self.settle()
            self.assertEqual(a.slot.height(), grown)
        too_long = long * 6                                 # more than there is room for: they give way, then come back
        answers = iter([[too_long] * 3, ["Una"]])
        a.ask("Quarta")
        a.finish()
        self.settle()
        self.assertFalse(a.questions_box.isVisible())
        a.ask("Quinta")
        a.finish()
        self.settle()
        self.assertTrue(a.questions_box.isVisible())

    def test_a_low_bubble_does_not_grow_by_itself_and_goes_back_after_a_card(self):
        from PySide6.QtWidgets import QLabel
        a = self.open(bubble=(280, 240))
        size = a.bubble.size()
        a.ask("Quante stringhe?")
        a.stream("Parole")
        a.finish()
        self.settle()
        self.assertEqual(a.bubble.size(), size)
        card = QLabel("\n".join(f"Riga {n} di una carta che chiede spazio" for n in range(10)))
        a.add_card(card)
        self.settle()
        self.assertGreater(a.bubble.height(), size.height())                        # it shows the card whole
        self.assertEqual(a.bubble_dims, (size.width(), size.height()))              # its size is still the designer's
        a.remove_card(card)
        self.settle()
        self.assertEqual(a.bubble.size(), size)

    def test_while_he_answers_the_questions_cannot_be_chosen_with_a_key(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        a = self.open()
        a.ask("Quante stringhe?")
        self.assertTrue(a.questions_box.isVisible())
        self.assertFalse(a.questions_content.isEnabled())
        told = len(a.messages)
        QTest.keyClick(a.field, Qt.Key.Key_1)
        self.assertEqual(len(a.messages), told)
        a.stop()
        self.assertTrue(a.questions_content.isEnabled())


class Small(Base):
    def test_the_minimum_is_the_design_systems(self):
        from meridiana import assistant as core
        from meridiana.ui.design import Size
        self.assertEqual(core.BUBBLE_MIN, (Size.BUBBLE_MIN_WIDTH, Size.BUBBLE_MIN_HEIGHT))
        self.assertGreaterEqual(core.BUBBLE_DEFAULT[1], Size.BUBBLE_LOW)

    def test_a_bubble_saved_smaller_opens_at_the_minimum(self):
        from meridiana import assistant as core
        a = self.open(bubble=(100, 120))
        self.assertEqual((a.bubble.width(), a.bubble.height()), core.BUBBLE_MIN)
        self.assertEqual(a.bubble_dims, core.BUBBLE_MIN)

    def test_at_the_minimum_the_arrangement_holds_on_all_four_sides(self):
        from PySide6.QtCore import QPoint, QRect

        from meridiana.ui.design import Size
        for place, avoid in ((("left", "bottom", 12, 12), None), (("right", "top", 12, 12), None),
                             (("right", "bottom", 12, 12), None), (("left", "top", 12, 12), None),
                             (("left", "top", 700, 60), [(0, 60, 698, 46), (748, 60, 652, 46)])):
            with self.subTest(place=place):
                a = self.open(place=place, bubble=(280, 240), avoid=avoid)
                a.set_where("local", "Locale, senza costi di uso", "tip")
                a.set_voice(True)
                a.view_button.show()
                a.set_cost("4.200 token · circa 0,05 centesimi (prezzi del 01/11/2026)")
                a.answer("Tre stringhe da otto moduli.")
                self.settle()
                self.assertFalse(a.title.isVisible() or a.attach_row.isVisible() or a.questions_box.isVisible())
                self.assertTrue(a.more_button.isVisible())
                self.assertGreaterEqual(a.conversation.height(), Size.BUBBLE_READING)
                self.assertEqual(a.status.height(), Size.BUBBLE_STATUS)
                rect = lambda w, bubble=a.bubble: QRect(w.mapTo(bubble, QPoint(0, 0)), w.size())  # noqa: E731
                body = a.bubble.body().toRect()
                buttons = [a.where_button, a.voice_button, a.more_button, a.dock_button, a.close_button]
                for one in buttons + [a.field, a.conversation, a.status]:
                    self.assertTrue(body.contains(rect(one)), one)
                    self.assertTrue(one.width() > 0 and one.height() > 0)
                for one, other in zip(buttons, buttons[1:], strict=False):
                    self.assertFalse(rect(one).intersects(rect(other)))
                grip = rect(a.bubble.grip)
                for one in buttons:                                     # the name and the buttons off the grip
                    self.assertFalse(grip.intersects(rect(one)), one)
                near = grip.intersected(rect(a.field))
                self.assertLessEqual(max(near.width(), near.height()), 2)   # at most inside the field's round corner
                _setup.dispose(a.area)

    def test_the_menu_of_a_low_bubble_holds_what_its_row_held(self):
        a = self.open(bubble=(280, 240))
        heard = []
        a.attachmentRequested.connect(lambda: heard.append("attach"))
        a.viewRequested.connect(lambda: heard.append("view"))
        a.view_button.show()
        a._fill_more()
        for action in a.more_menu.actions():
            action.trigger()
        self.assertEqual(heard, ["attach", "view"])
        a.view_button.hide()
        a._fill_more()
        self.assertEqual(len(a.more_menu.actions()), 1)

    def test_narrow_with_the_questions_nothing_is_cut_on_the_right(self):
        """Under 318 px the rows went beyond the panel: a push button's least width is its hint (280 px)."""
        from PySide6.QtCore import QPoint
        a = self.open(bubble=(280, 560))
        self.assertTrue(a.questions_box.isVisible())
        right = a.panel.width() - a.panel.layout().contentsMargins().right()
        for row in a.questions:
            self.assertLessEqual(row.mapTo(a.panel, QPoint(row.width(), 0)).x(), right)
        self.assertLessEqual(a.field.mapTo(a.panel, QPoint(a.field.width(), 0)).x(), right)

    def test_the_whole_arrangement_comes_back_when_it_is_large_or_docked(self):
        a = self.open(bubble=(280, 240))
        self.assertTrue(a.more_button.isVisible())
        a.set_bubble_size(320, 500)
        self.settle()
        self.assertTrue(a.title.isVisible() and a.attach_row.isVisible() and a.questions_box.isVisible())
        self.assertFalse(a.more_button.isVisible())


if __name__ == "__main__":
    unittest.main()
