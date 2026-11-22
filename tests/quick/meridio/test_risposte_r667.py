"""R667 (Daniel 16/11/2026: «non deve esserci scritto Meridio ad ogni sua risposta, ruba solo spazio»): his answers
carry no name over them, nor do the designer's messages («You», removed the same day); who speaks is still said to
screen readers."""
import unittest

from PySide6.QtCore import QObject
from PySide6.QtGui import QAccessible  # noqa: F401  the module of Accessible.name
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from meridiana.app.platform import config
from meridiana.gui.backend.assistant import build_page
from meridiana.gui.backend.assistant_chat import AssistantChat
from quick.gestures import pump, wait_for
from quick.meridio.support import Host, KeyStore, Voice


def items(root, name):
    out, pending = [], [root]
    while pending:
        node = pending.pop()
        if node.objectName() == name:
            out.append(node)
        pending.extend(node.childItems())
    return out


class AnswersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['r667-tests'])

    def test_no_name_over_his_answers_and_who_speaks_is_still_said(self):
        chat = AssistantChat(Host(), config.Config(assistant_introduced=True), key_store=KeyStore(), voice=Voice())
        self.addCleanup(chat.close)
        colours = {'field': '#eeeeee', 'view': '#ffffff', 'text': '#000000', 'muted': '#777777'}
        answer = {'kind': 'assistant', 'author': 'Meridio', 'bodyHtml': '<p>Ok.</p>', 'outgoing': False}
        mine = {'kind': 'you', 'author': 'You', 'bodyHtml': '<p>Ciao</p>', 'outgoing': True}
        self.assertNotIn('Meridio', chat.messageBlock(answer, colours))
        self.assertNotIn('You', chat.messageInner(mine, colours))      # Daniel 16/11/2026: «Togli anche tu»
        engine, window, _ = build_page('meridio', options={'reducedMotion': True}, chat=chat)
        self.assertTrue(QTest.qWaitForWindowExposed(window))

        def cleanup():
            window.close()
            delete(engine)
        self.addCleanup(cleanup)
        chat.view.answer('Una risposta di una riga.')
        layer = window.findChild(QObject, 'assistantLayer')
        wait_for(lambda: any(i.isVisible() for i in items(layer, 'conversationMessage')), 5)
        pump(100)
        shown = [i for i in items(layer, 'conversationMessage') if i.isVisible()]
        self.assertTrue(shown)
        self.assertNotIn('Meridio', shown[-1].property('text'))
        name = shown[-1].property('Accessible.name')
        if name is not None:            # read where the attached property answers by name
            self.assertEqual(name, 'Meridio')


if __name__ == '__main__':
    unittest.main()
