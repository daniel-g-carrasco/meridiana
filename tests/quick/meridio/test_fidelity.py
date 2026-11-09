"""R13: visible regressions against the Widgets bubble, with real Qt windows."""
import unittest

from PySide6.QtCore import QObject, QPoint, QMimeData, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from meridiana import config
from meridiana.quick.backend.assistant import build_page
from meridiana.quick.backend.assistant_chat import AssistantChat
from quick.meridio.support import Host, KeyStore, Voice


class FidelityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def scene(self, chat=None, **options):
        engine, window, theme = build_page(chat=chat, options={'reducedMotion': True, **options})
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        QTest.qWait(150)
        root = window.findChild(QObject, 'assistantLayer')
        def cleanup():
            window.close()
            errors = list(engine._assistant_diagnostics)
            delete(engine)
            self.assertEqual(errors, [])
        self.addCleanup(cleanup)
        return engine, window, root, theme

    def test_r293_tail_has_no_separating_line_on_either_side(self):
        _, window, root, theme = self.scene()
        panel = QColor(theme.colors['panel'])
        for tail, x in [('left', 80), ('right', 1200)]:
            root.setProperty('avatarX', x)
            root.setProperty('avatarY', 400)
            root.setProperty('tail', tail)
            root.setProperty('tailOffset', 300)
            root.placeBubble()
            QTest.qWait(30)
            image = window.grabWindow()
            bubble = root.findChild(QObject, 'assistantBubble')
            seam_x = bubble.x() + (12 if tail == 'left' else bubble.width() - 12)
            seam_y = 423
            dpr = image.devicePixelRatio()
            colours = [image.pixelColor(round((seam_x + offset) * dpr), round(seam_y * dpr))
                       for offset in (-1, 0, 1)]
            self.assertTrue(all(c == panel for c in colours), (tail, [c.name() for c in colours], panel.name()))

    def test_r258_title_is_centered_independently_of_header_buttons(self):
        _, _, root, _ = self.scene()
        title = root.findChild(QObject, 'assistantTitle')
        self.assertIsNotNone(title, 'The real title must be identifiable for the parity journey')
        bubble = root.findChild(QObject, 'assistantBubble')
        center = title.mapToItem(bubble, title.width() / 2, title.height() / 2)
        self.assertAlmostEqual(center.x(), (bubble.width() - 12) / 2, delta=1)

    def test_r320_spreadsheet_clipboard_with_text_and_image_pastes_text(self):
        chat = AssistantChat(Host(), config.Config(assistant_introduced=True), key_store=KeyStore(), voice=Voice())
        self.addCleanup(chat.close)
        data = QMimeData()
        image = QImage(10, 10, QImage.Format.Format_RGB32)
        image.fill(Qt.GlobalColor.red)
        data.setImageData(image)
        data.setText('Module\tPower\nA\t450')
        self.app.clipboard().setMimeData(data)
        # the clipboard emptied while Python is alive: a QMimeData made in Python and left to the clipboard is deleted
        # by Qt's static destructors after the interpreter has ended, and its wrapper's destructor ended the process
        # with an access violation (139, the whole meridio folder and this test alone, 07/11/2026)
        self.addCleanup(self.app.clipboard().clear)
        self.assertFalse(chat.pasteClipboard())
        self.assertFalse(chat.attachment_jobs)

    def test_r15_pointer_gaze_and_reduced_motion(self):
        _, window, root, _ = self.scene(reducedMotion=False)
        avatar = root.findChild(QObject, 'assistantCharacter')
        window.requestActivate()
        QTest.mouseMove(window, QPoint(300, 200))
        QTest.qWait(180)
        self.assertEqual((avatar.property('gazeX'), avatar.property('gazeY')), (-1, -1))
        root.setProperty('animated', False)
        QTest.qWait(80)
        self.assertFalse(avatar.property('moving'))
        self.assertEqual((avatar.property('gazeX'), avatar.property('gazeY')), (0, 0))

    def test_r156_a_whole_chunk_is_spoken_progressively_and_reduced_motion_finishes_it(self):
        chat = AssistantChat(Host(), config.Config(assistant_introduced=True), key_store=KeyStore(), voice=Voice())
        self.addCleanup(chat.close)
        _, window, root, theme = self.scene(chat, reducedMotion=False)
        chat.view.stream('Una risposta lunga. ' * 30)
        chat.view.finish()
        QTest.qWait(110)
        self.assertTrue(hasattr(chat, 'displayMessages'), 'Presentation must expose progressive speech')
        displayed = ''.join(row.get('text', '') for row in chat.displayMessages)
        self.assertGreater(len(displayed), 0)
        self.assertLess(len(displayed), 570)
        theme.configure({'reducedMotion': True})
        QTest.qWait(80)
        self.assertEqual(chat.displayMessages[-1]['text'], 'Una risposta lunga. ' * 30)

    def test_r362_scrolling_up_keeps_the_reading_position_when_more_text_arrives(self):
        from quick.gestures import point, wheel
        from _setup import wait_until
        chat = AssistantChat(Host(), config.Config(assistant_introduced=True, assistant_local_model='fake'), key_store=KeyStore(), voice=Voice())
        self.addCleanup(chat.close)
        _, window, root, _ = self.scene(chat)
        chat.view.answer('\n\n'.join('A long paragraph with useful details.' for _ in range(35)))
        QTest.qWait(100)
        scroll = root.findChild(QObject, 'conversationScroll')
        content = scroll.property('contentItem')
        old = content.property('contentY')
        wheel(self.app, window, point(scroll), notches=5, dy=120)
        self.assertTrue(wait_until(self.app, lambda: not content.property('moving'), 2))
        self.assertFalse(scroll.property('follow'))
        at = content.property('contentY')
        self.assertLess(at, old)
        chat.view.stream(' Another paragraph. '*20)
        QTest.qWait(100)
        self.assertAlmostEqual(content.property('contentY'), at, delta=1)

    def test_r320_floating_image_card_keeps_preview_and_remove_in_view(self):
        from _setup import wait_until
        from quick.gestures import item
        chat = AssistantChat(Host(), config.Config(assistant_introduced=True, assistant_local_model='fake'), key_store=KeyStore(), voice=Voice())
        self.addCleanup(chat.close)
        picture = QImage(240, 120, QImage.Format.Format_RGB32)
        picture.fill(QColor('blue'))
        chat.add_image(picture, 'Example.png')
        self.assertTrue(wait_until(self.app, lambda: bool(chat.attachments), 5))
        _, window, root, _ = self.scene(chat)
        root.setProperty('bubbleWidth', 360)
        root.setProperty('bubbleHeight', 600)
        QTest.qWait(150)
        area = root.findChild(QObject, 'assistantCards')
        for key in ('preview', 'remove'):
            button = item(window, 'assistantCardButton:'+key)
            point = button.mapToItem(area, button.width()/2, button.height()/2)
            self.assertGreaterEqual(point.y(), 0)
            self.assertLess(point.y(), area.height())

    def test_r197_wrapped_suggestions_fit_the_button_with_large_text(self):
        from quick.gestures import item
        chat = AssistantChat(Host(), config.Config(assistant_introduced=True, assistant_local_model='fake'), key_store=KeyStore(), voice=Voice())
        self.addCleanup(chat.close)
        _, window, root, _ = self.scene(chat, textSize='large', font='plex')
        chat._suggestions = ['Quanti moduli in serie al massimo, e perché?',
                             "C'è altro da sistemare prima della relazione?",
                             "Il rapporto DC/AC è ragionevole qui?"]
        chat.changed.emit()
        root.setProperty('bubbleHeight', 600)
        wrapped = False
        for width in (320, 370, 400):
            root.setProperty('bubbleWidth', width)
            QTest.qWait(150)
            for index in range(1, 4):
                button = item(window, 'assistantSuggestion'+str(index))
                self.assertTrue(button.isVisible())
                label = next(child for child in button.property('contentItem').childItems()
                             if child.property('text') == button.property('text'))
                wrapped |= label.property('lineCount') > 1
                self.assertGreaterEqual(label.height(), label.property('contentHeight'))
                bottom = label.mapToItem(button, 0, label.height()).y()
                self.assertLessEqual(bottom, button.height()-button.property('bottomPadding'), (width, index))
        self.assertTrue(wrapped, 'This regression needs at least one multiline question')
