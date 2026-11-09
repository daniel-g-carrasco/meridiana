"""R389: Quick conversation parity, with providers and keyring kept in memory."""
import threading
import unittest
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from _setup import wait_until
from meridiana import config
from meridiana.assistant import attachments, conversation, providers, setup, tools
from meridiana.quick.backend.assistant_chat import AssistantChat
from quick.meridio.support import Host, Provider, Voice


class ChatTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.host = Host()
        self.cfg = config.Config(assistant_introduced=True, assistant_local_model="fake")
        self.chat = AssistantChat(self.host, self.cfg, voice=Voice(),
                                  key_store=SimpleNamespace(get=lambda provider: "test-key"))
        self.addCleanup(self.chat.close)
        self.local = Provider()
        self.chat.make_local = lambda: self.local

    def idle(self):
        self.assertTrue(wait_until(self.app, lambda: not self.chat.busy, 5))

    def test_streaming_is_off_thread_markdown_and_costs_reach_qml(self):
        self.chat.ask("How much?")
        self.idle()
        self.assertEqual(self.chat.messages[0]["outgoing"], True)
        self.assertIn("<b>Ready</b>", self.chat.messages[-1]["bodyHtml"])
        self.assertNotEqual(self.local.requests[0][3], threading.get_ident())
        self.assertIn("15", self.chat.costLine)
        self.assertTrue(self.chat.suggestions)

    def test_cloud_waits_for_card_and_reserved_project_stays_local(self):
        setup.remember(self.cfg, "openai", "test-model")
        self.chat.chooseProvider("openai")
        cloud = Provider(cloud=True)
        self.chat.make_cloud = lambda key: cloud
        self.chat.ask("Tell me about this project")
        self.assertFalse(cloud.requests)
        card = next(c for c in self.chat.cards if any(b["id"] == "allow" for b in c["buttons"]))
        self.chat.cardAction(card["id"], "allow")
        self.idle()
        self.assertEqual(len(cloud.requests), 1)
        self.host.project.reserved = True
        self.chat.ask("And now?")
        self.idle()
        self.assertEqual(len(cloud.requests), 1)
        self.assertEqual(len(self.local.requests), 1)

    def test_stop_drops_late_text_and_new_conversation_is_empty(self):
        self.chat._text(self.chat.generation - 1, "late")
        self.assertFalse(self.chat.messages)
        self.chat.ask("Hello")
        self.chat.stop()
        self.assertFalse(self.chat.busy)
        self.assertTrue(self.local.stop.is_set())
        self.chat._text(self.chat.generation - 1, "late")
        self.assertNotIn("late", str(self.chat.messages))
        self.chat.newConversation()
        self.assertFalse(self.chat.messages)
        self.assertFalse(self.chat.cards)

    def test_markdown_tables_are_safe_and_formulas_stay_textual(self):
        self.local.text = "| Quantity | Value |\n| --- | --- |\n| Energy | **42** |\n| Unsafe | <img src='https://bad/image'> |\n\nN_max = floor(V_max / Uoc_max)"
        self.chat.ask("Compare")
        self.idle()
        body = self.chat.messages[-1]["bodyHtml"]
        self.assertIn("<table", body)
        self.assertIn("<b>42</b>", body)
        self.assertNotIn("<img", body)
        self.assertIn("N_max = floor(V_max / Uoc_max)", body)

    def test_proposals_apply_only_after_click_and_repeated_click_is_inert(self):
        previous = self.host.project.name
        proposal = tools.Proposal("p1", "Rename", "site", "", [("name", previous, "Renamed")],
                                  change=lambda p: setattr(p, "name", "Renamed"))
        self.chat._show_proposal(proposal)
        self.assertEqual(self.host.project.name, previous)
        identifier = self.chat.cards[0]["id"]
        self.chat.cardAction(identifier, "apply")
        self.assertEqual(self.host.project.name, "Renamed")
        self.assertEqual(len(self.host.edits), 1)
        self.chat.cardAction(identifier, "apply")
        self.assertEqual(len(self.host.edits), 1)
        self.assertFalse(self.chat.cards)
        self.assertEqual(proposal.state, "applied")

    def test_history_and_tasks_are_confirmed_then_dispatched_to_host(self):
        from unittest.mock import Mock
        for kind, method in (("history", "history"), ("task", "apply_task"), ("open_project", "open_project")):
            hook = Mock(return_value=True)
            setattr(self.host, method, hook)
            item = {"path": "synthetic.meridiana"} if kind == "open_project" else {"action": "create"}
            proposal = tools.Proposal("p-" + kind, kind, kind, "undo", [], item=item)
            self.chat._show_proposal(proposal)
            hook.assert_not_called()
            self.chat.cardAction(self.chat.cards[-1]["id"], "apply")
            hook.assert_called_once_with("undo" if kind == "history" else item["path"] if kind == "open_project" else item)

    def test_discard_does_not_edit_and_next_turn_hears_decision(self):
        proposal = tools.Proposal("p2", "Rename", "site", "", [], change=lambda p: setattr(p, "name", "wrong"))
        self.chat._show_proposal(proposal)
        self.chat.cardAction(self.chat.cards[0]["id"], "discard")
        self.assertFalse(self.host.edits)
        self.chat.ask("Continue")
        self.idle()
        self.assertIn("discarded p2", str(self.local.requests[0][1]))

    def test_tool_rounds_run_on_main_thread_and_the_response_reaches_next_round(self):
        from unittest.mock import patch
        calls = []
        self.local.events = [providers.ToolCall("c1", "read_checks", {}), providers.Done("tools")]
        real = conversation.Conversation.run_tools

        def run(conv, *args, **kwargs):
            calls.append(threading.get_ident())
            result = real(conv, *args, **kwargs)
            self.local.events = None
            return result

        with patch.object(conversation.Conversation, "run_tools", run):
            self.chat.ask("Checks?")
            self.idle()
        self.assertEqual(calls, [threading.get_ident()])
        self.assertEqual(self.local.requests[1][1][-1]["role"], "tool")
        self.assertFalse(self.chat.conversation.open_calls())

    def test_external_documents_disable_tools_even_if_provider_requests_them(self):
        self.chat.attachments["doc"] = attachments.Attachment("doc.txt", "text/plain", "untrusted", "doc.txt")
        self.local.events = [providers.ToolCall("c1", "read_checks", {}), providers.Done("tools")]
        self.chat.ask("Read document")
        self.idle()
        self.assertEqual([t["name"] for t in self.local.requests[0][2]], ["propose_catalog_record"])
        self.assertIn("untrusted data", self.local.requests[0][0])
        self.assertFalse(self.chat.conversation.open_calls())
        self.assertNotIn("Read the checks", str(self.chat.messages))
        self.local.events = None
        self.chat.ask("Again")
        self.idle()
        self.assertEqual([t["name"] for t in self.local.requests[1][2]], ["propose_catalog_record"])

    def test_a_document_may_only_fill_the_review_window(self):
        """R415: with a document in the conversation the model can propose a product, and nothing else."""
        self.chat.attachments["doc"] = attachments.Attachment("doc.txt", "text/plain", "sheet", "doc.txt")
        record = {"manufacturer": "Acme", "model": "X1", "pmax": 450}
        self.local.events = [providers.ToolCall("c1", "propose_catalog_record", {"kind": "modules", "record": record}), providers.Done("tools")]
        self.host.prepare_catalog_record = self.chat.prepare_catalog_record
        self.chat.ask("Aggiungi questa scheda")
        self.idle()
        self.local.events = None
        cards = [c for c in self.chat.cards if c["kind"] == "catalog"]
        self.assertTrue(cards, self.chat.cards)
        self.assertIn("X1", str(cards[0]["lines"]))

    def test_a_datasheet_is_offered_for_review_with_no_model(self):
        from meridiana.catalog import datasheet
        reading = datasheet.Reading("sheet.pdf", "modules")
        reading.proposals = [datasheet.Proposal("modules", {"manufacturer": "Jinko Solar", "model": "JKM475N"})]
        item = attachments.Attachment("sheet.pdf", "application/pdf", "text", "sheet.pdf", "C:/x/sheet.pdf", reading)
        seen = []
        self.chat.catalogReviewRequested.connect(lambda card, kind, record: seen.append((kind, dict(record))))
        self.assertTrue(self.chat.offer_reading(item))
        card = next(c for c in self.chat.cards if c["kind"] == "catalog")
        self.chat.cardAction(card["id"], "review")
        self.assertEqual(seen, [("modules", {"__datasheet": "C:/x/sheet.pdf"})])
        payload = attachments.message([item])
        self.assertNotIn("C:/x", payload)                      # the local path never leaves
        self.assertIn("reader_draft", payload)

    def test_captured_view_keeps_tools_external_image_disables_them(self):
        from PySide6.QtGui import QImage
        picture = QImage(60, 40, QImage.Format.Format_RGB32)
        picture.fill("red")
        self.host.view_image = lambda: picture
        self.chat.showView()
        self.assertTrue(wait_until(self.app, lambda: not self.chat.attachment_jobs, 5))
        item = next(iter(self.chat.attachments.values()))
        self.assertTrue(item.captured)
        card = self.chat.cards[0]
        self.assertTrue(card["thumbnail"].startswith("data:image/png;base64,"))
        self.chat.cardAction(card["id"], "preview")
        self.assertEqual(self.chat.preview["title"], item.name)
        self.assertTrue(self.chat.preview["imageSource"])
        self.chat.ask("What do you see?")
        self.idle()
        self.assertTrue(self.local.requests[0][2])
        self.assertTrue(self.local.requests[0][1][-1]["images"])
        self.chat.newConversation()
        self.chat.add_image(picture, "outside.png")
        self.assertTrue(wait_until(self.app, lambda: not self.chat.attachment_jobs, 5))
        self.chat.ask("And outside?")
        self.idle()
        self.assertEqual([t["name"] for t in self.local.requests[1][2]], ["propose_catalog_record"])

    def test_cloud_redacts_names_and_switching_to_cloud_starts_fresh_history(self):
        self.host.project.name = "Private Customer Name"
        self.chat.ask("Local confidential question")
        self.idle()
        setup.remember(self.cfg, "openai", "test-model")
        self.chat.chooseProvider("openai")
        cloud = Provider(cloud=True, text="Project 1")
        self.chat.make_cloud = lambda key: cloud
        self.chat.ask("Private Customer Name")
        self.chat.cardAction(self.chat.cards[-1]["id"], "allow")
        self.idle()
        sent = str(cloud.requests[0][1])
        self.assertNotIn("Private Customer Name", sent)
        self.assertNotIn("Local confidential question", sent)

    def test_voice_toggle_and_close_silence_output(self):
        self.chat.toggleVoice()
        self.assertTrue(self.chat.voiceEnabled)
        self.assertTrue(self.cfg.assistant_voice)
        self.chat.ask("Speak")
        self.idle()
        self.assertTrue(self.chat.voice.spoken)
        self.chat.setOpened(False)
        self.assertFalse(self.chat.voice.spoken)

    def test_cloud_offline_falls_back_locally_without_losing_question(self):
        class Offline(Provider):
            def stream(self, *args):
                raise providers.ProviderError("offline")

        setup.remember(self.cfg, "openai", "test-model")
        self.chat.chooseProvider("openai")
        self.chat.make_cloud = lambda key: Offline(cloud=True)
        self.chat.ask("Cloud question")
        self.chat.cardAction(self.chat.cards[-1]["id"], "allow")
        self.idle()
        self.assertIn("Cloud question", str(self.local.requests[0][1]))
        self.assertFalse(self.chat.conversation.state.cloud)
        self.assertIn("No network", str(self.chat.messages))

    def test_consent_cancel_and_local_choice_never_call_cloud(self):
        from unittest.mock import Mock
        setup.remember(self.cfg, "openai", "test-model")
        self.chat.chooseProvider("openai")
        self.chat.make_cloud = Mock(side_effect=AssertionError("No consent"))
        self.chat.ask("Cancel this")
        self.chat.cardAction(self.chat.cards[-1]["id"], "cancel")
        self.assertFalse(self.chat.busy)
        self.assertFalse(self.local.requests)
        self.chat.ask("Keep this local")
        self.chat.cardAction(self.chat.cards[-1]["id"], "local")
        self.idle()
        self.assertTrue(self.local.requests)
        self.chat.make_cloud.assert_not_called()

    def test_change_provider_stops_pending_request_and_rejects_late_answer(self):
        from unittest.mock import Mock
        self.chat.pool = SimpleNamespace(start=Mock())
        self.chat.ask("Wait")
        generation = self.chat.generation
        self.assertTrue(self.chat.busy)
        setup.remember(self.cfg, "openai", "test-model")
        self.chat.chooseProvider("openai")
        self.assertFalse(self.chat.busy)
        self.assertTrue(self.local.stop.is_set())
        self.chat._text(generation, "discard me")
        self.chat._done(generation, conversation.Round(text="discard me"))
        self.assertNotIn("discard me", str(self.chat.messages))

    def test_attachment_url_is_extracted_off_thread_and_removed_before_result_stays_gone(self):
        from unittest.mock import patch
        from PySide6.QtCore import QUrl
        from pathlib import Path
        threads = []
        result = attachments.Attachment("synthetic.txt", "text/plain", "hello", "synthetic.txt")

        def extract(path):
            threads.append((threading.get_ident(), path))
            return result

        url = QUrl.fromLocalFile(str(Path.cwd() / "synthetic.txt")).toString()
        with patch.object(attachments, "extract", extract):
            self.chat.addAttachments([url])
            self.assertTrue(wait_until(self.app, lambda: not self.chat.attachment_jobs, 5))
        self.assertNotEqual(threads[0][0], threading.get_ident())
        self.assertTrue(threads[0][1].endswith("synthetic.txt"))
        card = self.chat.cards[-1]
        self.chat.cardAction(card["id"], "preview")
        self.assertEqual(self.chat.preview["text"], "hello")
        self.chat.cardAction(card["id"], "remove")
        self.assertFalse(self.chat.attachments)
        from unittest.mock import Mock
        self.chat.pool = SimpleNamespace(start=Mock())
        self.chat._reading("pending.txt", False, lambda: result)
        token = next(iter(self.chat.attachment_cards))
        self.chat.remove_attachment(token)
        self.chat._attachment_read((token, result, ""))
        self.assertFalse(self.chat.cards)
        self.assertFalse(self.chat.attachments)

    def test_clipboard_images_are_attached_and_plain_text_is_left_to_editor(self):
        from unittest.mock import patch
        from PySide6.QtCore import QMimeData
        from PySide6.QtGui import QImage
        picture = QImage(20, 20, QImage.Format.Format_RGB32)
        picture.fill("blue")
        mime = QMimeData()
        mime.setImageData(picture)
        with patch("meridiana.quick.backend.assistant_chat.QGuiApplication.clipboard",
                   return_value=SimpleNamespace(mimeData=lambda: mime)):
            self.assertTrue(self.chat.pasteClipboard())
            self.assertTrue(wait_until(self.app, lambda: not self.chat.attachment_jobs, 5))
            self.assertEqual(len(self.chat.pictures()), 1)
            mime.clear()
            mime.setText("Keep this in the editor")
            self.assertFalse(self.chat.pasteClipboard())

    def test_blind_model_does_not_send_image_and_keeps_draft(self):
        from PySide6.QtGui import QImage
        picture = QImage(20, 20, QImage.Format.Format_RGB32)
        picture.fill("blue")
        self.chat.add_image(picture, "picture.png")
        self.assertTrue(wait_until(self.app, lambda: not self.chat.attachment_jobs, 5))
        self.local.model = "qwen3:4b"
        self.chat.ask("See it?")
        self.assertFalse(self.local.requests)
        self.assertEqual(self.chat.draft, "See it?")
        self.assertEqual(len(self.chat.pictures()), 1)
        self.assertFalse(self.chat.busy)

    def test_card_text_and_headers_cannot_inject_html(self):
        from meridiana.quick.backend.assistant_chat import message_html
        body = message_html("| <img src=x> | B |\n| --- | --- |\n| 1 | 2 |")
        self.assertNotIn("<img", body)
        self.assertIn("&lt;img", body)
        fenced = message_html("```\n| A | B |\n| --- | --- |\n| 1 | 2 |\n```")
        self.assertNotIn("<table", fenced)
        self.assertIn("<pre>", fenced)

    def test_r362_busy_retains_suggestions_and_disables_actions(self):
        from unittest.mock import Mock
        before = list(self.chat.suggestions)
        self.assertTrue(before)
        self.chat.pool = SimpleNamespace(start=Mock())
        self.chat.ask("Wait for model")
        self.assertEqual(self.chat.suggestions, before)
        self.assertFalse(self.chat.suggestionsEnabled)
        self.chat.stop()
        self.assertTrue(self.chat.suggestionsEnabled)

    def test_qml_suggestion_binding_updates_when_confirmation_appears_and_is_discarded(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtQml import QQmlComponent, QQmlEngine
        engine = QQmlEngine()
        engine.rootContext().setContextProperty("chat", self.chat)
        component = QQmlComponent(engine)
        component.setData(b'import QtQml\nQtObject { property int count: chat.suggestions.length }', QUrl())
        bound = component.create()
        self.assertIsNotNone(bound, str(component.errors()))
        try:
            before = bound.property("count")
            self.assertGreater(before, 0)
            proposal = tools.Proposal("confirm-task", "Task", "task", "", [], item={"action": "create"})
            self.chat._show_proposal(proposal)
            self.assertEqual(bound.property("count"), 0)
            self.chat.cardAction(self.chat.cards[-1]["id"], "discard")
            self.assertEqual(bound.property("count"), before)
        finally:
            bound.setParent(engine)

    def test_catalog_reviews_report_id_and_save_removes_only_its_own_card(self):
        from meridiana.catalog import KINDS
        kind = next(iter(KINDS))
        requested = []
        self.chat.catalogReviewRequested.connect(lambda *args: requested.append(args))
        self.assertTrue(self.chat.prepare_catalog_record(kind, {"model": "One"}))
        self.assertTrue(self.chat.prepare_catalog_record(kind, {"model": "Two"}))
        first, second = self.chat.cards
        self.chat.cardAction(first["id"], "review")
        self.chat.cardAction(second["id"], "review")
        self.assertEqual(requested, [(first["id"], kind, {"model": "One"}),
                                     (second["id"], kind, {"model": "Two"})])
        self.chat.catalogReviewFinished(second["id"], False)
        self.assertEqual(len(self.chat.cards), 2)
        self.chat.catalogReviewFinished(first["id"], True)
        self.assertEqual([c["id"] for c in self.chat.cards], [second["id"]])
        self.assertIn("Product saved in the personal catalogue.", str(self.chat.messages))
        count = len(self.chat.messages)
        self.chat.catalogReviewFinished(first["id"], True)
        self.assertEqual(len(self.chat.messages), count)
        self.chat.newConversation()
        self.chat.catalogReviewFinished(second["id"], True)
        self.assertFalse(self.chat.messages)

    def test_provider_menu_lists_only_the_assistants_configured_with_one_checked_entry(self):
        # R288, R490: one line per assistant configured, never the Claude models an Anthropic key could reach
        def menu():
            return [(row["id"], row["text"]) for row in self.chat.providerOptions]
        setup.remember(self.cfg, "anthropic", "claude-sonnet-5-5")
        self.chat.refresh()
        self.assertEqual(menu(), [("local", "Local model, on this PC"), ("anthropic", "Claude Sonnet 5.5")])
        self.assertEqual(self.chat.setupLabel, "Set up another assistant…")
        self.assertTrue(all(row["enabled"] for row in self.chat.providerOptions))
        self.chat.chooseProvider("anthropic")
        self.assertEqual([row["id"] for row in self.chat.providerOptions if row["checked"]], ["anthropic"])
        self.chat.chooseModel("anthropic", "custom-model")        # a model of the user's own: provider and model
        self.assertEqual(menu()[1:], [("anthropic", "Claude / Anthropic, custom-model")])
        self.assertEqual([row["id"] for row in self.chat.providerOptions if row["checked"]], ["anthropic"])
        setup.remember(self.cfg, "openai", "gpt-test")             # a second provider set up: two assistants
        self.chat.refresh()
        self.assertEqual([row["id"] for row in self.chat.providerOptions], ["local", "openai", "anthropic"])
        self.chat.chooseProvider("local")
        self.assertEqual([row["id"] for row in self.chat.providerOptions if row["checked"]], ["local"])

    def test_without_an_assistant_configured_the_menu_has_local_and_set_up_a_model(self):
        chat = AssistantChat(self.host, config.Config(assistant_introduced=True), voice=Voice(),
                             key_store=SimpleNamespace(get=lambda provider: ""))
        self.addCleanup(chat.close)
        chat.refresh()
        self.assertEqual([row["id"] for row in chat.providerOptions], ["local"])
        self.assertEqual(chat.setupLabel, "Set up a model…")

    def test_withdraw_consent_cancels_pending_cloud_question_and_preferences_is_a_signal(self):
        from unittest.mock import Mock
        setup.remember(self.cfg, "openai", "test-model")
        self.chat.chooseProvider("openai")
        self.chat.ask("Wait for consent")
        self.cfg.assistant_consent = {"openai": "synthetic"}
        self.chat.save_config = Mock()
        self.chat.withdrawConsent()
        self.assertFalse(self.cfg.assistant_consent)
        self.assertFalse(self.chat.busy)
        self.assertFalse(self.chat.waiting)
        self.assertIsNone(self.chat.consent_card)
        self.chat.save_config.assert_called_once()
        opened = []
        self.chat.preferencesRequested.connect(lambda: opened.append(True))
        self.chat.requestPreferences()
        self.assertEqual(opened, [True])
