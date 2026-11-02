"""Images for Meridio in the chat (R320): pasted with Ctrl+V, dropped, chosen as files; the thumbnail under the
question; at most four attachments with the documents. No model is called: the turn stops before the provider."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import _setup
from meridiana import config, model
from meridiana.assistant import images

setUpModule = _setup.keep_global_state

OUT = Path(__file__).resolve().parents[2] / "build" / "claude-r07"


def picture(w=320, h=200, colour="#2a6f97"):
    from PySide6.QtGui import QColor, QImage, QPainter
    image = QImage(w, h, QImage.Format.Format_RGB32)
    image.fill(QColor(colour))
    p = QPainter(image)
    p.fillRect(w // 4, h // 4, w // 2, h // 2, QColor("#f2c14e"))
    p.end()
    return image


class Images(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look()                                 # the fonts, for the photo

    def setUp(self):
        from PySide6.QtWidgets import QWidget
        from meridiana.ui.assistant import Assistant
        from meridiana.ui.assistant_chat import Chat
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.area = QWidget()
        self.area.resize(1100, 850)
        self.a = Assistant(self.area)
        self.a.reduced_motion = True
        self.host = SimpleNamespace(project=model.Project(), set_status=lambda text: None,
                                    preferences=lambda: None, selection=lambda: ('site', ''),
                                    phase_title=lambda: 'Model', phase=lambda: 'model', path=lambda: '',
                                    checks=lambda: [], energy=lambda: {})
        self.cfg = config.Config(assistant_introduced=True)
        self.chat = Chat(self.a, self.host, self.cfg)
        self.addCleanup(self.chat.stop)
        self.addCleanup(self.chat.voice.close)
        self.addCleanup(_setup.dispose, self.area)
        self.area.show()
        self.a.open_panel()

    def ready(self, n=1):
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.chat.attachment_jobs, 10))
        self.assertEqual(len(self.chat.attachments), n)

    def paste(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.a.field.setFocus()
        QTest.keyClick(self.a.field, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)

    def test_ctrl_v_with_a_picture_on_the_clipboard_attaches_it(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setImage(picture())
        self.paste()
        self.ready()
        item = next(iter(self.chat.attachments.values()))
        self.assertIsInstance(item, images.Picture)
        self.assertEqual(item.name, "Pasted image")
        self.assertEqual((item.width, item.height), (320, 200))
        self.assertFalse(item.captured)
        self.assertEqual(self.a.field.text(), "")
        card = next(iter(self.chat.attachment_cards.values()))
        from PySide6.QtWidgets import QLabel
        thumb = card.findChild(QLabel, "meridio-thumbnail")
        self.assertIsNotNone(thumb)
        self.assertFalse(thumb.pixmap().isNull())

    def test_ctrl_v_with_text_and_a_picture_pastes_the_text(self):
        """Cells copied from a spreadsheet bring their text and a picture of themselves: they are text."""
        from PySide6.QtCore import QMimeData
        from PySide6.QtWidgets import QApplication
        mime = QMimeData()
        mime.setText("450 W")
        mime.setImageData(picture())
        QApplication.clipboard().setMimeData(mime)
        self.paste()
        self.app.processEvents()
        self.assertEqual(self.a.field.text(), "450 W")
        self.assertFalse(self.chat.attachment_cards)

    def test_a_picture_dropped_or_an_image_file_dropped_is_attached(self):
        from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
        from PySide6.QtGui import QDropEvent
        mime = QMimeData()
        mime.setImageData(picture())
        target = self.a.conversation.viewport()
        drop = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton,
                          Qt.KeyboardModifier.NoModifier)
        self.a.eventFilter(target, drop)
        self.ready()
        self.assertEqual(next(iter(self.chat.attachments.values())).name, "Dropped image")
        path = Path(self.tmp.name) / "tetto.png"
        picture(800, 600).save(str(path))
        files = QMimeData()
        files.setUrls([QUrl.fromLocalFile(str(path))])
        drop = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, files, Qt.MouseButton.LeftButton,
                          Qt.KeyboardModifier.NoModifier)
        self.a.eventFilter(target, drop)
        self.ready(2)
        self.assertIn("tetto.png", [a.name for a in self.chat.attachments.values()])

    def test_at_most_four_attachments_documents_and_images_together(self):
        doc = Path(self.tmp.name) / "scheda.txt"
        doc.write_text("Pmax 450 W", encoding="utf-8")
        self.chat.add_attachments([str(doc)])
        for n in range(4):
            self.chat.add_image(picture(), f"img{n}")
        self.ready(4)
        self.assertIn("At most four attachments", self.a.conversation.toPlainText())
        kinds = sorted(type(a).__name__ for a in self.chat.attachments.values())
        self.assertEqual(kinds, ["Attachment", "Picture", "Picture", "Picture"])

    def test_the_question_carries_the_pictures_and_shows_their_thumbnail_with_name_and_size(self):
        self.chat.add_image(picture(2400, 1500), "vista.png")
        self.ready()
        provider = SimpleNamespace(cloud=False, model="gemma4:12b", family="ollama", cancel=lambda: None)
        self.chat.make_local = lambda: provider
        with mock.patch.object(self.chat, "_round"):
            self.a.ask("Cosa vedi in questa immagine?")
        sent = self.chat.conversation.messages[-1]
        self.assertEqual(len(sent["images"]), 1)
        self.assertEqual((sent["images"][0]["width"], sent["images"][0]["height"]), (1568, 980))
        self.assertIn("Attached images: vista.png", sent["content"])
        self.assertFalse(self.chat.attachments)
        self.assertTrue(self.chat.has_attachment_turn)          # an image from outside: tools off, as a document
        whos = [who for who, _t in self.a.messages]
        self.assertEqual(whos[whos.index("you") + 1], "pictures")
        html = self.a.conversation.toHtml()
        self.assertIn("meridio-picture://", html)
        self.assertIn("vista.png", self.a.conversation.toPlainText())
        self.assertIn("1568 × 980 px", self.a.conversation.toPlainText())
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QTextDocument
        url = QUrl(self.a.pictures["p1"][0][0])
        self.assertIsNotNone(self.a.conversation.document().resource(QTextDocument.ResourceType.ImageResource, url))
        self.a.answer("Un rettangolo giallo su fondo blu.")
        OUT.mkdir(parents=True, exist_ok=True)
        self.app.processEvents()
        self.assertTrue(self.a.panel.grab().save(str(OUT / "OM-chat-miniatura.png")))

    def test_a_captured_view_keeps_the_tools(self):
        self.chat.add_image(picture(), "Modello", captured=True)
        self.ready()
        provider = SimpleNamespace(cloud=False, model="gemma4:12b", family="ollama", cancel=lambda: None)
        self.chat.make_local = lambda: provider
        with mock.patch.object(self.chat, "_round"):
            self.a.ask("Che ne pensi?")
        self.assertFalse(self.chat.has_attachment_turn)
        self.assertIn("Meridiana's own view", self.chat.conversation.messages[-1]["content"])

    def test_a_new_conversation_forgets_the_thumbnails(self):
        self.chat.add_image(picture(), "x.png")
        self.ready()
        self.chat.make_local = lambda: SimpleNamespace(cloud=False, model="llava", family="ollama",
                                                       cancel=lambda: None)
        with mock.patch.object(self.chat, "_round"):
            self.a.ask("Guarda")
        self.chat.new_conversation()
        self.assertEqual(self.a.pictures, {})
        self.assertNotIn("pictures", [who for who, _t in self.a.messages])
        self.assertFalse(self.chat.history)

    def test_a_local_model_known_without_vision_is_said_and_the_pictures_wait(self):
        self.chat.add_image(picture(), "tetto.png")
        self.ready()
        blind = SimpleNamespace(cloud=False, model="gpt-oss:20b", family="openai", cancel=lambda: None)
        self.chat.make_local = lambda: blind
        with mock.patch.object(self.chat, "_round") as rounds:
            self.a.ask("Cosa vedi?")
            rounds.assert_not_called()
        self.assertIn("does not see images", self.a.conversation.toPlainText())
        self.assertIn("gpt-oss:20b", self.a.conversation.toPlainText())
        self.assertEqual(len(self.chat.attachments), 1)        # kept for another model
        self.assertEqual(self.a.field.text(), "Cosa vedi?")
        self.assertEqual(self.chat.conversation.messages, [])

    def test_a_refusal_for_lack_of_vision_is_said_and_the_pictures_are_not_sent_again(self):
        from meridiana.assistant import providers
        self.chat.add_image(picture(), "tetto.png")
        self.ready()
        unknown = SimpleNamespace(cloud=False, model="my-model", family="openai", cancel=lambda: None)
        self.chat.make_local = lambda: unknown
        with mock.patch.object(self.chat, "_round"):
            self.a.ask("Cosa vedi?")
        self.assertTrue(providers.has_images(self.chat.conversation.messages))
        self.chat._failed(self.chat.generation, providers.ProviderError("vision", "mmproj missing"))
        self.assertFalse(providers.has_images(self.chat.conversation.messages))
        self.assertIn("does not see images", self.a.conversation.toPlainText())
        self.chat._failed(self.chat.generation, providers.ProviderError("image", "image exceeds 5 MB maximum"))
        self.assertIn("refused the image", self.a.conversation.toPlainText())

    def cloud(self):
        import datetime as dt
        from meridiana.assistant import privacy
        self.cfg.assistant_provider = "claude"
        self.cfg.assistant_consent = privacy.consent({}, "anthropic", dt.date.today())
        self.chat.keys = SimpleNamespace(get=lambda key: "fake-key")
        cloud = SimpleNamespace(cloud=True, model="claude-haiku-5-5", family="anthropic", cancel=lambda: None)
        self.chat.make_cloud = lambda key: cloud
        return cloud

    def test_an_image_for_the_cloud_asks_each_time_and_says_a_picture_is_not_redacted(self):
        self.cloud()
        self.chat.add_image(picture(), "schermata.png")
        self.ready()
        with mock.patch.object(self.chat, "_start") as start:
            self.a.ask("Cosa vedi?")
            start.assert_not_called()                           # a consent given before is not enough
        card = self.chat.consent_card
        self.assertIsNotNone(card)
        from PySide6.QtWidgets import QLabel
        words = " ".join(label.text() for label in card.findChildren(QLabel))
        self.assertIn("schermata.png", words)
        self.assertIn("address", words)
        self.assertIn("aliases", words)
        self.assertIn("Images: about 86 tokens", words)          # 320 × 200 / 750 (costs.image_tokens)
        with mock.patch.object(self.chat, "_round"):
            card.buttons["allow"].click()
        self.assertTrue(self.chat.conversation.messages[-1]["images"])
        self.chat.job = None
        self.a.answer("Una schermata.")                         # the turn over, as the model's answer ends it
        with mock.patch.object(self.chat, "_start") as start:
            self.a.ask("E adesso?")                             # the picture goes again: asked again
            start.assert_not_called()
        words = " ".join(label.text() for label in self.chat.consent_card.findChildren(QLabel))
        self.assertIn("images attached earlier", words)
        self.chat.consent_card.buttons["cancel"].click()

    def test_a_reserved_project_keeps_the_picture_on_this_pc(self):
        cloud = self.cloud()
        self.host.project.reserved = True
        local = SimpleNamespace(cloud=False, model="gemma4:12b", family="ollama", cancel=lambda: None)
        self.chat.make_local = lambda: local
        self.chat.add_image(picture(), "schermata.png")
        self.ready()
        with mock.patch.object(self.chat, "_round"):
            self.a.ask("Cosa vedi?")
        self.assertIs(self.chat.provider, local)
        self.assertIsNot(self.chat.provider, cloud)

    def test_the_window_keeps_only_the_thumbnail_and_the_name(self):
        self.chat.add_image(picture(1200, 800), "vista.png")
        self.ready()
        self.chat.make_local = lambda: SimpleNamespace(cloud=False, model="llava", family="ollama",
                                                       cancel=lambda: None)
        with mock.patch.object(self.chat, "_round"):
            self.a.ask("Guarda")
        data = self.chat.conversation.messages[-1]["images"][0]["data"]
        self.assertNotIn(data[:200], repr(self.a.messages) + repr(self.a.pictures))
        self.assertEqual([caption.split(" · ")[0] for _url, caption in self.a.pictures["p1"]], ["vista.png"])


if __name__ == "__main__":
    unittest.main()
