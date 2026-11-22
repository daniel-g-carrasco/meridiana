"""R636 (Daniel 15/11/2026: «darei la possibilità alla casella di input di testo di meridio di accettare anche il
multiriga se gli si sta scrivendo un messaggio più lungo. Ovviamente con limiti in altezza e barra di scorrimento»).

Meridio's field (M.GrowingField) is born one line tall, grows by whole lines up to 6 and never past a third of the
conversation, then scrolls its text with the common bar; Return sends, Shift+Return breaks the line, after the send it
is one line again, spaces alone are not sent; the send button stays on its last line; the wheel scrolls its text only
when it has some to scroll.
"""
import unittest

from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from meridiana.app.platform import config
from meridiana.gui.backend.assistant import build_page
from meridiana.gui.backend.assistant_chat import AssistantChat
from quick.gestures import pump, wait_for, wheel
from quick.meridio.support import Host, KeyStore, Provider, Voice
from quick.aiuti.caratteri import glyph


class FieldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['r636-tests'])

    def setUp(self):
        self.chat = AssistantChat(Host(), config.Config(assistant_introduced=True, assistant_local_model='fake'),
                                  key_store=KeyStore(), voice=Voice())
        self.addCleanup(self.chat.close)
        self.fake = Provider(text='Ok.')
        self.chat.make_local = lambda: self.fake
        engine, window, _ = build_page('meridio', options={'reducedMotion': True}, chat=self.chat)
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        self.window, self.layer = window, window.findChild(QObject, 'assistantLayer')
        wait_for(lambda: not self.layer.property('relocating'), 5)

        def cleanup():
            window.close()
            delete(engine)
        self.addCleanup(cleanup)
        self.field = self.layer.findChild(QObject, 'assistantQuestion')
        self.line = self.field.property('lineHeight')
        self.one = self.field.property('oneLine')

    def view(self):
        return next(c for c in self.field.childItems() if c.metaObject().className().startswith('QQuickFlickable'))

    def type(self, text):
        for ch in text:
            QTest.keyClick(self.window, ch)

    def lines(self, n):
        self.field.setProperty('text', '\n'.join(f'riga {i}' for i in range(1, n + 1)))
        pump(80)

    def test_it_grows_by_whole_lines_up_to_six_then_scrolls(self):
        self.layer.setProperty('bubbleHeight', 620)
        pump(100)
        for n in (1, 2, 3, 6):
            self.lines(n)
            # the field is whole pixels, the font's lines are not outside Windows (quick/aiuti/caratteri.py)
            self.assertAlmostEqual(self.field.height(), self.one + (n - 1) * self.line, delta=glyph(0.5), msg=f'{n} lines')
            self.assertFalse(self.field.property('scrolls'))
        self.lines(10)
        self.assertAlmostEqual(self.field.height(), self.one + 5 * self.line, delta=glyph(0.5), msg='past the cap')
        self.assertTrue(self.field.property('scrolls'))
        bar = next(c for c in self.view().childItems() if 'ScrollBar' in c.metaObject().className())
        self.assertTrue(bar.isVisible(), 'past the cap: no bar')
        send = self.layer.findChild(QObject, 'assistantSend')
        bottom = send.mapToScene(QPointF(0, send.height())).y()
        self.assertAlmostEqual(bottom, self.field.mapToScene(QPointF(0, self.field.height())).y(), delta=0.5,
                               msg='the send button left the last line')

    def test_never_past_a_third_of_the_conversation(self):
        self.layer.setProperty('bubbleHeight', 300)
        pump(150)
        self.lines(10)
        conversation = self.field.parentItem()
        self.assertLessEqual(self.field.height(), conversation.height() / 3 + 0.5)
        rest = (self.field.height() - self.one) / self.line
        self.assertAlmostEqual((rest - round(rest)) * self.line, 0, delta=glyph(0.01 * self.line), msg='not whole lines')

    def test_return_sends_shift_return_breaks_the_line(self):
        self.field.forceActiveFocus()
        pump(30)
        self.type('prima')
        QTest.keyClick(self.window, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
        self.type('seconda')
        pump(50)
        self.assertEqual(self.field.property('text'), 'prima\nseconda')
        self.assertAlmostEqual(self.field.height(), self.one + self.line, delta=0.5)
        QTest.keyClick(self.window, Qt.Key.Key_Return)
        wait_for(lambda: bool(self.fake.requests) and not self.chat.busy, 5)
        self.assertTrue(self.fake.requests[-1][1][-1]['content'].endswith('prima\nseconda'), self.fake.requests[-1][1])
        self.assertEqual(self.field.property('text'), '')
        # the field goes back to one line a turn after the text is emptied, or more on a loaded runner (45 != 28)
        wait_for(lambda: abs(self.field.height() - self.one) <= 0.5, 5)
        self.assertAlmostEqual(self.field.height(), self.one, delta=0.5, msg='after the send: not one line again')

    def test_spaces_and_empty_lines_are_not_sent(self):
        self.field.forceActiveFocus()
        pump(30)
        self.type('  ')
        QTest.keyClick(self.window, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
        QTest.keyClick(self.window, Qt.Key.Key_Return)
        pump(200)
        self.assertEqual(self.fake.requests, [])

    def test_the_wheel_scrolls_the_field_only_when_it_has_something_to_scroll(self):
        for _ in range(8):
            self.chat.view.answer('\n'.join('Un paragrafo lungo con dettagli utili da leggere.' for _ in range(6)))
        scroll = self.layer.findChild(QObject, 'conversationScroll')
        flick = scroll.property('contentItem')
        wait_for(lambda: flick.property('contentHeight') > scroll.height() + 200, 5)
        pump(200)
        middle = self.field.mapToScene(QPointF(self.field.width() / 2, self.field.height() / 2)).toPoint()
        self.lines(2)
        before = flick.property('contentY')
        wheel(self.app, self.window, QPointF(middle), notches=2, dy=120)
        pump(150)
        self.assertNotEqual(flick.property('contentY'), before, 'a field with nothing to scroll kept the wheel')
        self.lines(14)
        middle = self.field.mapToScene(QPointF(self.field.width() / 2, self.field.height() / 2)).toPoint()
        conversation = flick.property('contentY')
        wheel(self.app, self.window, QPointF(middle), notches=2, dy=-120)
        pump(150)
        self.assertGreater(self.view().property('contentY'), 0, 'past the cap, the wheel did not scroll the field')
        self.assertEqual(flick.property('contentY'), conversation)


if __name__ == '__main__':
    unittest.main()
