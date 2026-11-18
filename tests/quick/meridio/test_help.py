"""R383: one authoritative help catalogue, manual and resumable tour."""
import unittest
from meridiana import help as helps, tour
from meridiana.config import Config
from meridiana.quick.backend.assistant_help import AssistantHelp


class HelpTest(unittest.TestCase):
    def test_every_help_keeps_the_widgets_content_and_links(self):
        service = AssistantHelp()
        for key, value in helps.texts().items():
            self.assertTrue(service.request(key))
            self.assertEqual(service.content['title'], value.title)
            self.assertEqual(service.content['text'], value.text)
            self.assertEqual(service.content['sources'], helps.sources(value))
            self.assertEqual(service.content['manual'], value.manual)
            self.assertEqual(service.content['pedigree'], value.pedigree)
        previous = service.content
        self.assertFalse(service.request('missing'))
        self.assertEqual(service.content, previous)

    def test_manual_is_internal_and_cannot_escape_its_catalogue(self):
        service = AssistantHelp()
        for chapter in helps.CHAPTERS:
            self.assertTrue(service.openManual(chapter))
            self.assertTrue(service.manualText)
        before = service.manualText
        self.assertFalse(service.openManual('../../CLAUDE.md'))
        self.assertFalse(service.openManual('https://example.com'))
        self.assertEqual(service.manualText, before)

    def test_ask_and_how_emit_the_core_question_and_target(self):
        service = AssistantHelp()
        questions, targets = [], []
        service.askRequested.connect(questions.append)
        service.howRequested.connect(targets.append)
        service.request('phase.production')
        service.ask()
        service.how()
        self.assertEqual(questions, [helps.question(helps.get('phase.production'))])
        self.assertEqual(targets, ['production'])

    def test_tour_uses_all_core_steps_and_saves_resume(self):
        cfg = Config()
        saved, targets = [], []
        service = AssistantHelp(cfg=cfg, save=lambda: saved.append(cfg.tour_step))
        service.navigateRequested.connect(targets.append)
        service.startTour(False)
        for index, step in enumerate(tour.steps()):
            self.assertEqual(service.tourStep['id'], step.id)
            self.assertEqual(service.tourStep['points'], list(step.points))
            self.assertEqual(targets[-1], list(step.target))
            if index < len(tour.steps()) - 1:
                service.next()
        service.previous()
        service.pauseTour()
        self.assertEqual(cfg.tour_status, 'paused')
        service.startTour(True)
        self.assertEqual(service.tourIndex, len(tour.steps()) - 2)
        service.next()
        service.next()
        self.assertEqual(cfg.tour_status, 'done')
        self.assertTrue(saved)
