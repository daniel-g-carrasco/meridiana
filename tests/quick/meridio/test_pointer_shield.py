"""R570: nothing behind Meridio reacts to the pointer over his bubble or over him (Daniel 09/11 and 14/11/2026).

«Continua ad esserci con il fumetto di Meridio il problema che il cursore può interagire dietro di lui»: over the
bubble's margin, its tail and the middle of the conversation, and over the character, the gestures (moving, the wheel
upright and sideways and with Ctrl, the left and right click, the double click, the drag, a touch, a touchscreen pinch)
reach none of the stand-ins of quick/aiuti/sonde_puntatore.py behind: no hover, no tip, no cursor of theirs, no
click, no scroll or zoom. Past the rounded corners, inside the bubble's rectangle but outside its drawing, they do.
Before r35-meridio, 148 of these checks were red (the bubble and the character let everything through).
"""
import unittest

from PySide6.QtCore import QObject, QPoint, QPointF
from PySide6.QtTest import QTest

from _setup import wait_until
from meridiana.app.platform import config
from meridiana.gui.backend.assistant_chat import AssistantChat
from quick.aiuti.sonde_puntatore import PROBES, PointerProbes
from quick.meridio.support import Host, KeyStore, Voice


class PointerShieldTest(PointerProbes, unittest.TestCase):
    def bubble_points(self, layer):
        """Inside the bubble's outline where it has no control: its margin, its tail, the middle of the conversation."""
        bubble = layer.findChild(QObject, 'assistantBubble')
        self.assertEqual(layer.property('tail'), 'right', 'the preview puts the bubble to the left of Meridio')
        at = layer.property('avatarY') + 23 - bubble.y()
        content = layer.findChild(QObject, 'conversationScroll')
        return {'margin': bubble.mapToScene(QPointF(4, bubble.height() / 2)),
                'tail': bubble.mapToScene(QPointF(bubble.width() - 6, at)),
                'conversation': content.mapToScene(QPointF(content.width() / 2, content.height() / 2))}

    def test_nothing_behind_meridio_bubble_reacts(self):
        for kind in PROBES:
            window, layer, probe, _ = self.scene(kind)
            for where, pos in self.bubble_points(layer).items():
                # from the tail the drag goes into the bubble, so that it ends on it
                way = QPointF(-3, 0) if where == 'tail' else QPointF(0, 3)
                # the drag of the conversation over a DragHandler: test_a_drag_handler_behind_takes_the_conversations_drag
                self.check_blocked(window, probe, pos, f'{kind} under the bubble ({where})', way,
                                   skip_drag=kind == 'handlers' and where == 'conversation')

    def test_nothing_behind_meridio_character_reacts(self):
        for kind in ('handlers', 'mouse', 'list'):
            window, layer, probe, _ = self.scene(kind)
            avatar = layer.findChild(QObject, 'assistantCharacter')
            self.check_blocked(window, probe, avatar.mapToScene(QPointF(23, 23)), f'{kind} under the character')

    def test_past_the_outline_the_pointer_reaches_what_is_behind(self):
        # past the rounded corners on the left (the grip of the size stands on one of them): nothing drawn there
        for kind in ('handlers', 'mouse'):
            window, layer, probe, _ = self.scene(kind)
            bubble = layer.findChild(QObject, 'assistantBubble')
            for side, y in (('top', 1.5), ('bottom', bubble.height() - 1.5)):
                self.check_passes(window, probe, bubble.mapToScene(QPointF(1.5, y)), f'{kind} past the {side} corner')

    def test_closed_the_bubble_is_not_there(self):
        # closed (faded out), the bubble's place is what is behind again
        window, layer, probe, _ = self.scene('mouse', opened=False)
        bubble = layer.findChild(QObject, 'assistantBubble')
        self.assertFalse(bubble.isVisible())
        self.check_passes(window, probe, bubble.mapToScene(QPointF(bubble.width() / 2, bubble.height() / 2)), 'closed')

    def test_inside_the_bubble_everything_still_works(self):
        # R570, point 3: the shield lies under the bubble's own content, which keeps its gestures: the wheel scrolls the
        # conversation, a drag selects its words, a click puts the keyboard in the question and the keys write there,
        # the grip resizes the bubble; and all the while nothing behind reacts
        chat = AssistantChat(Host(), config.Config(assistant_introduced=True, assistant_local_model='fake'),
                             key_store=KeyStore(), voice=Voice())
        self.addCleanup(chat.close)
        window, layer, probe, _ = self.scene('mouse', chat=chat)
        chat.view.answer('\n\n'.join('Un paragrafo lungo con dettagli utili da leggere e copiare.' for _ in range(30)))
        scroll = layer.findChild(QObject, 'conversationScroll')
        flick = scroll.property('contentItem')
        self.assertTrue(wait_until(self.app, lambda: flick.property('contentHeight') > flick.height() + 200, 5))
        with self.subTest(gesture='wheel scrolls the conversation'):
            at = flick.property('contentY')
            self.wheel(window, scroll.mapToScene(QPointF(scroll.width() / 2, scroll.height() / 2)), QPoint(0, 120))
            self.assertTrue(wait_until(self.app, lambda: not flick.property('moving'), 2))
            self.assertNotEqual(flick.property('contentY'), at)
        with self.subTest(gesture='drag selects the words'):
            words, pending = [], [scroll]
            while pending:
                item = pending.pop()
                pending.extend(item.childItems())
                # ReadableText derives from TextArea: use the message's semantic
                # identity, not the obsolete concrete QQuickTextEdit class name.
                if item.objectName() == 'conversationMessage' and item.isVisible() and item.height() > 40:
                    words.append(item)
            self.assertTrue(words)
            edit = max(words, key=lambda e: e.height())
            middle = edit.mapToScene(QPointF(0, edit.height() / 2))
            top = scroll.mapToScene(QPointF(0, 0)).y()
            bottom = top + scroll.height()
            y = min(max(middle.y(), top + 30), bottom - 30)
            # a little down as well: the middle of the message can be the air between two paragraphs, where it falls
            # with the font's line heights (on Linux an empty line, and a drag along it selected nothing)
            self.drag(window, QPointF(middle.x() + 20, y), QPointF(20, 4))
            self.assertNotEqual(edit.property('selectedText'), '')
        with self.subTest(gesture='the question takes the click and the keys'):
            field = layer.findChild(QObject, 'assistantQuestion')
            self.click(window, field.mapToScene(QPointF(20, field.height() / 2)))
            self.assertTrue(field.hasActiveFocus())
            for char in 'ciao':
                QTest.keyClick(window, char)
            self.assertEqual(field.property('text'), 'ciao')
        with self.subTest(gesture='the grip resizes'):
            grip = layer.findChild(QObject, 'assistantGrip')
            width = layer.property('bubbleWidth')
            self.drag(window, grip.mapToScene(QPointF(8, 8)), QPointF(-5, 0))
            self.assertGreater(layer.property('bubbleWidth'), width)
        self.assertEqual(self.counts(probe), {'taps': 0, 'wheels': 0, 'pinches': 0, 'drags': 0})

    def test_scrolling_the_words_never_scrolls_what_is_behind(self):
        # R612 (Daniel 14/11/2026, the tour over the Properties panel: two fingers «scorre il testo del fumetto E ANCHE
        # il pannello sotto»): the wheel and the touchpad's two fingers (pixels with their phases) over the bubble's
        # words, in the middle of them and once they are at their end, scroll the words only, never the list behind
        chat = AssistantChat(Host(), config.Config(assistant_introduced=True, assistant_local_model='fake'),
                             key_store=KeyStore(), voice=Voice())
        self.addCleanup(chat.close)
        window, layer, probe, _ = self.scene('list', chat=chat)
        chat.view.answer('\n\n'.join('Un paragrafo lungo con dettagli utili da leggere e copiare.' for _ in range(30)))
        scroll = layer.findChild(QObject, 'conversationScroll')
        flick = scroll.property('contentItem')
        self.assertTrue(wait_until(self.app, lambda: flick.property('contentHeight') > flick.height() + 200, 5))
        pos = scroll.mapToScene(QPointF(scroll.width() / 2, scroll.height() / 2))
        self.move(window, pos)
        top = flick.property('contentHeight') - flick.height()
        for where, at in (('middle', top / 2), ('end', top)):
            for gesture in ('wheel', 'pad-scroll'):
                with self.subTest(where=where, gesture=gesture):
                    flick.setProperty('contentY', at)
                    wait_until(self.app, lambda: not flick.property('moving'), 2)
                    # downwards: in the middle the words move, at their end they cannot
                    if gesture == 'wheel':
                        self.wheel(window, pos, QPoint(0, -120))
                    else:
                        self.pad_scroll(window, pos)
                    wait_until(self.app, lambda: not flick.property('moving') and not probe.property('moving'), 3)
                    self.assertEqual(probe.property('contentY'), 0, 'the list behind scrolled')
                    if where == 'middle':
                        self.assertGreater(flick.property('contentY'), at, 'the words did not scroll')

    @unittest.expectedFailure
    def test_a_drag_handler_behind_takes_the_conversations_drag(self):
        # KNOWN, not closed (r35-meridio, 14/11/2026): a press on the conversation is its list's (a Flickable), which
        # does not keep it while it has nothing to scroll; Qt gives the press to the pointer handlers behind as well
        # (passively), and a DragHandler behind takes the drag over at its threshold. In Meridiana the only DragHandler
        # that can be behind Meridio is the order of the inverters (PlantPage). The shield and Meridio's own handle
        # keep theirs (preventStealing). Stated in docs/quick/stato/r35-meridio.md.
        window, layer, probe, _ = self.scene('handlers')
        pos = self.bubble_points(layer)['conversation']
        self.move(window, pos)
        self.drag(window, pos)
        self.assertEqual(probe.property('drags'), 0)

    @unittest.expectedFailure
    def test_the_touchpad_gesture_does_not_reach_what_is_behind(self):
        # KNOWN, not closed (r35-meridio, 14/11/2026): the touchpad's own pinch (QNativeGestureEvent: Wayland and macOS;
        # on Windows the pinch comes as Ctrl and the wheel, closed above) given to the window goes to the PinchHandler
        # behind at every gesture, also with the shield's PinchHandler over it. Stated in docs/quick/stato/r35-meridio.md.
        window, layer, probe, _ = self.scene('handlers')
        pos = self.bubble_points(layer)['margin']
        self.move(window, pos)
        self.pad_pinch(window, pos)
        self.assertEqual(probe.property('pinches'), 0)


if __name__ == '__main__':
    unittest.main()
