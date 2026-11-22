"""R667 (Daniel 16/11/2026: «il caricamento della risposta di meridio deve essere mostrato in modo carino direttamente in
chat, nel punto in cui comparirà la risposta»): his waiting line is there from the question to the first words of the
answer, in the answer's place, and not after; when the words come, nothing moves; it is moved by Animators alone."""
import threading
import unittest
from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from meridiana.app.assistant import providers
from meridiana.app.platform import config
from meridiana.gui.backend.assistant import build_page
from meridiana.gui.backend.assistant_chat import AssistantChat
from quick.gestures import pump, wait_for
from quick.meridio.support import Host, KeyStore, Provider, Voice

QML = Path(__file__).resolve().parents[3] / 'src' / 'meridiana' / 'gui' / 'qml' / 'Meridiana' / 'Assistant'


class Held(Provider):
    """A model that answers one short line once the test lets it."""
    def __init__(self):
        super().__init__(text='Ok.')
        self.go = threading.Event()

    def stream(self, system, messages, tools):
        self.requests.append((system, messages, tools, threading.get_ident()))
        self.go.wait(10)
        yield providers.Text('Una risposta di una riga.')
        self.go.clear()
        self.go.wait(10)
        yield providers.Done('end')


def find(root, name):
    pending = [root]
    while pending:
        node = pending.pop()
        if node.objectName() == name:
            return node
        pending.extend(node.childItems())
    return None


class WaitingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['r667-wait'])

    def test_the_waiting_line_from_the_question_to_the_first_words_and_nothing_moves(self):
        chat = AssistantChat(Host(), config.Config(assistant_introduced=True, assistant_local_model='fake'),
                             key_store=KeyStore(), voice=Voice())
        self.addCleanup(chat.close)
        model = Held()
        chat.make_local = lambda: model
        self.addCleanup(model.go.set)
        engine, window, _ = build_page('meridio', options={'reducedMotion': True}, chat=chat)
        self.assertTrue(QTest.qWaitForWindowExposed(window))

        def cleanup():
            window.close()
            delete(engine)
        self.addCleanup(cleanup)
        layer = window.findChild(QObject, 'assistantLayer')
        waiting = find(layer, 'assistantWaiting')
        scroll = layer.findChild(QObject, 'conversationScroll')
        column = scroll.property('contentItem').property('contentItem').childItems()[0]
        self.assertFalse(waiting.isVisible(), 'before the question')
        chat.ask('Come va?')
        wait_for(lambda: waiting.isVisible(), 5)
        self.assertEqual(waiting.childItems()[0].property('text'), chat.property('waitingText'))
        pump(300)
        before = column.height()
        model.go.set()
        wait_for(lambda: chat.property('state') == 'answering', 5)
        pump(300)
        self.assertFalse(waiting.isVisible(), 'the first words came: the line stayed')
        self.assertAlmostEqual(column.height(), before, delta=1.5, msg='the first line of the answer moved the page')
        model.go.set()
        wait_for(lambda: not chat.busy, 5)
        pump(100)
        self.assertFalse(waiting.isVisible(), 'after the answer')

    def test_it_is_moved_by_animators_alone(self):
        text = (QML / 'WaitingLine.qml').read_text(encoding='utf-8')
        self.assertNotIn('Timer {', text)
        self.assertIn('XAnimator', text)
        self.assertNotIn('NumberAnimation', text)
        self.assertNotIn('Timer {', (QML / 'Conversation.qml').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
