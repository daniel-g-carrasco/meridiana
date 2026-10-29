"""Meridio keeps compact suggestions beside a readable conversation."""
import unittest

import _setup

setUpModule = _setup.keep_global_state


class Presentation(unittest.TestCase):
    def setUp(self):
        from PySide6.QtWidgets import QWidget
        from meridiana.ui.assistant import Assistant
        self.app = _setup.qt_or_skip()
        _setup.meridiana_look()
        self.area = QWidget()
        self.area.resize(1000, 700)
        self.addCleanup(_setup.dispose, self.area)
        self.a = Assistant(self.area)
        self.a.reduced_motion = True
        self.area.show()
        self.a.open_panel()
        self.app.processEvents()

    def test_every_phase_has_a_human_readable_name(self):
        self.a.set_tab('plant')
        self.assertIn('Plant', self.a.context.text())
        self.a.set_tab('report')
        self.assertIn('Report', self.a.context.text())

    def test_streaming_does_not_pull_a_reader_back_to_the_bottom(self):
        self.a.messages = [('assistant', 'First paragraph.\n\n' * 90)]
        self.a._show_messages()
        self.app.processEvents()
        bar = self.a.conversation.verticalScrollBar()
        self.assertGreater(bar.maximum(), 50)
        bar.setValue(20)
        self.a.live = 'A new answer being streamed.'
        self.a._show_messages()
        self.assertEqual(bar.value(), 20)

    def test_user_markup_is_plain_text_and_roles_have_separate_blocks(self):
        self.a.messages = [('you', '<b>my question</b>'), ('assistant', 'A clear answer')]
        self.a._show_messages()
        self.assertIn('<b>my question</b>', self.a.conversation.toPlainText())
        frames = self.a.conversation.document().rootFrame().childFrames()
        self.assertGreaterEqual(len(frames), 2)

    def test_suggestions_can_fold_without_losing_their_text_or_sending_a_message(self):
        before = [q.text() for q in self.a.questions]
        self.a.questions_title.click()
        self.app.processEvents()
        self.assertTrue(all(q.isHidden() for q in self.a.questions))
        self.assertEqual([q.text() for q in self.a.questions], before)
        self.assertEqual(self.a.messages, [])
        self.a.questions_title.click()
        self.assertTrue(any(not q.isHidden() for q in self.a.questions))

    def test_suggestion_number_and_arrow_are_centred_beside_wrapped_text(self):
        row = self.a.questions[0]
        row.setText('A long suggestion that wraps onto several lines in a narrow conversation panel')
        self.app.processEvents()
        from PySide6.QtCore import Qt
        self.assertTrue(row.number.alignment() & Qt.AlignmentFlag.AlignVCenter)
        self.assertTrue(row.arrow.alignment() & Qt.AlignmentFlag.AlignVCenter)

    def test_one_line_suggestions_do_not_expand_to_fill_a_tall_bubble(self):
        self.a.suggest = lambda _tab: ["Check the inverter", "Show the settings", "Read the results"]
        self.a.fill_questions()
        self.a.set_bubble_size(460, 600)
        self.a.place_bubble()
        self.app.processEvents()
        for row in self.a.questions:
            self.assertLessEqual(row.height(), 36)
