"""One synthetic provider, the same conversation in Widgets and Quick (R389)."""
import unittest
from unittest.mock import patch

from PySide6.QtCore import QObject, QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget
from shiboken6 import delete

from _setup import wait_until
from meridiana.config import Config
from meridiana.quick.backend.assistant import build_page
from meridiana.quick.backend.assistant_chat import AssistantChat
from quick.meridio.support import Host, Provider, Voice, KeyStore


class ParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['meridio-parity'])

    def quick(self):
        cfg = Config(assistant_introduced=True, assistant_local_model='test-model')
        chat = AssistantChat(Host(), cfg, voice=Voice(), key_store=KeyStore())
        fake = Provider(text='**Risultato**\n\nN_max = floor(V_max / Voc_cold)\n\n- Una verifica per ogni stringa.')
        chat.make_local = lambda: fake
        self.addCleanup(chat.close)
        return chat, fake

    def test_identical_prompt_tools_messages_bill_and_answers(self):
        from meridiana.ui.assistant import Assistant
        from meridiana.ui.assistant_chat import Chat
        quick, fake = self.quick()
        area = QWidget()
        area.resize(1366, 900)
        avatar = Assistant(area)
        avatar.reduced_motion = True
        self.addCleanup(lambda: delete(area))
        cfg = Config(assistant_introduced=True, assistant_local_model='test-model')
        keys = KeyStore()
        with patch('meridiana.ui.voice.Voice', return_value=Voice()), patch('meridiana.ui.assistant_chat.keys.get', side_effect=keys.get):
            widgets = Chat(avatar, Host(), cfg)
        widgets.keys = keys
        old_fake = Provider(text=fake.text)
        widgets.make_local = lambda: old_fake
        self.addCleanup(widgets._gone)
        question = 'Spiegami le verifiche delle stringhe.'
        quick.ask(question)
        avatar.ask(question)
        self.assertTrue(wait_until(self.app, lambda: not quick.busy and widgets.job is None, 5))
        self.assertEqual(fake.requests[0][:3], old_fake.requests[0][:3])
        self.assertEqual(quick.conversation.messages, widgets.conversation.messages)
        self.assertEqual(quick.conversation.bill, widgets.conversation.bill)
        self.assertEqual(quick.view.messages, avatar.messages)

    def test_real_qml_field_enter_stream_cards_and_provider_menu(self):
        chat, fake = self.quick()
        engine, window, theme = build_page(chat=chat)
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        QTest.qWait(250)
        def cleanup():
            window.close()
            errors = list(engine._assistant_diagnostics)
            delete(engine)
            self.assertEqual(errors, [])
        self.addCleanup(cleanup)
        root = window.findChild(QObject, 'assistantLayer')
        question = root.findChild(QObject, 'assistantQuestion')
        question.forceActiveFocus()
        # QWindow receives keyClick, never the real desktop keyboard.
        for char in 'test':
            QTest.keyClick(window, char)
        QTest.keyClick(window, Qt.Key.Key_Return)
        self.assertTrue(wait_until(self.app, lambda: bool(fake.requests) and not chat.busy, 5))
        QTest.qWait(80)
        self.assertIn('Risultato', chat.messages[-1]['bodyHtml'])
        self.assertFalse(window.grabWindow().isNull())
        chat.show_setup()
        QTest.qWait(100)
        card = chat.cards[0]
        chat.cardAction(card['id'], 'configure')
        QTest.qWait(100)
        self.assertEqual(root.property('page'), 'setup')
        self.assertEqual(engine._assistant_diagnostics, [])

    def test_help_button_and_f1_use_the_same_backend(self):
        engine, window, _ = build_page()
        self.addCleanup(lambda: (window.close(), delete(engine)))
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        QTest.qWait(220)
        mark = window.findChild(QObject, 'assistantHelpButton')        # the «?» of the card (R469: 16 px)
        centre = mark.mapToScene(QPointF(mark.width() / 2, mark.height() / 2))
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(round(centre.x()), round(centre.y())))
        QTest.qWait(380)
        root = window.findChild(QObject, 'assistantLayer')
        self.assertEqual(root.property('page'), 'help')
        self.assertEqual(engine._assistant_help.content['id'], 'phase.production')
        QTest.keyClick(window, Qt.Key.Key_Escape)
        QTest.keyClick(window, Qt.Key.Key_F1)
        self.assertEqual(engine._assistant_help.content['id'], 'phase.production')
        root.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_F1)
        self.assertEqual(engine._assistant_help.content['id'], 'phase.model')
