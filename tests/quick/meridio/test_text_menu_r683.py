"""Rendered message text and original Markdown stay distinct."""
import _setup
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from quick.aiuti.text_scene import TextScene

class MessageCopy(TextScene):
    def test_whole_plain_and_original_markdown(self):
        root, window = self.scene('ReadableText', 'textFormat: TextEdit.RichText')
        self.evaluate(root, 'text = "<p>Caf\u00e9 <b>bold</b> \U0001f600</p><table><tr><td>Energy</td><td>12,5 kWh</td></tr></table><pre>  a = 1</pre><ul><li>item</li></ul>"')
        self.evaluate(root, 'markdownSource = "**bold**"; textActions.execute("copy")')
        text = self.app.clipboard().text()
        self.assertIn('bold', text)
        self.assertIn('  a = 1', text)
        self.assertNotIn('<', text)
        self.assertIn('12,5 kWh', text)
        self.assertIn('\U0001f600', text)
        self.assertNotIn('|', text)
        self.evaluate(root, 'textActions.execute("markdown")')
        self.assertEqual(self.app.clipboard().text(), '**bold**')

    def test_streaming_freezes_visible_text(self):
        root, window = self.scene('ReadableText')
        QTest.mouseClick(window, Qt.RightButton, pos=QPoint(25, 12))
        self.assertTrue(_setup.wait_for(lambda: self.evaluate(root, 'textActions.menuActive'), 500))
        self.evaluate(root, 'text = ""; textActions.execute("copy")')
        self.assertEqual(self.app.clipboard().text(), 'Alpha beta')

    def test_image_paste_uses_same_handler_as_menu(self):
        from PySide6.QtGui import QImage
        root, window = self.scene('GrowingField', 'property int pastes: 0; textActions.pasteHandler: () => { pastes++; return true }; textActions.canPasteOverride: textEditing.canPaste')
        image = QImage(2, 2, QImage.Format_RGB32)
        image.fill(Qt.red)
        self.app.clipboard().setImage(image)
        self.evaluate(root, 'area.forceActiveFocus()')
        QTest.keyClick(window, Qt.Key_V, Qt.ControlModifier)
        self.assertEqual(root.property('pastes'), 1)
        self.evaluate(root, 'textActions.execute("paste")')
        self.assertEqual(root.property('pastes'), 2)
        self.assertEqual(root.property('text'), 'Alpha beta')
