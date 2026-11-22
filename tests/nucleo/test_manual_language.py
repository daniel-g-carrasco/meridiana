"""The manual follows the interface language, independently of regulatory scope."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import _setup  # noqa: F401
from meridiana import i18n
from meridiana.app.assistant import tools
from meridiana.app.interface import help as helps


class ManualLanguage(unittest.TestCase):
    def setUp(self):
        kept = i18n._translation
        self.addCleanup(setattr, i18n, '_translation', kept)

    def test_the_english_interface_searches_english_even_for_italy(self):
        i18n.setup('en')
        passages = tools.manual_passages(profile_id='it')
        found = [text for _, heading, text in passages if heading == 'Power asked']
        self.assertTrue(found, 'the English chapter must be read')
        self.assertIn('45.13 kWp', ' '.join(found))
        self.assertNotIn('Facoltativa', ' '.join(found))

    def test_the_generic_profile_still_excludes_national_sections_in_english(self):
        i18n.setup('en')
        italian = tools.manual_passages(profile_id='it')
        generic = tools.manual_passages(profile_id='generic')
        self.assertTrue(any(h == 'Fire brigade' for _, h, _ in italian))
        self.assertFalse(any(h == 'Fire brigade' for _, h, _ in generic))
        self.assertFalse(any(h == 'Connection and obligations' for _, h, _ in generic))
        self.assertTrue(any(h == 'Sides' for _, h, _ in generic))

    def test_language_switch_does_not_keep_previous_passages(self):
        i18n.setup('en')
        self.assertTrue(any(h == 'Power asked' for _, h, _ in tools.manual_passages()))
        i18n.setup('it')
        self.assertTrue(any(h == 'Potenza richiesta' for _, h, _ in tools.manual_passages()))
        self.assertFalse(any(h == 'Power asked' for _, h, _ in tools.manual_passages()))

    def test_missing_chapter_and_section_fall_back_to_italian_in_a_shipped_manual(self):
        i18n.setup('en')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'en').mkdir()
            (root / '1-modello.md').write_text('# Modello\n\nIntro italiana.\n\n## Lati\n\nLati italiani.\n', encoding='utf-8')
            (root / '2-impianto.md').write_text('# Impianto\n\nImpianto italiano.\n', encoding='utf-8')
            (root / 'en/1-modello.md').write_text('<a id="modello"></a>\n\n# Model\n\nEnglish introduction.\n', encoding='utf-8')
            with patch.object(helps, 'REPO_ROOT', root / 'missing-checkout'), patch(
                    'meridiana.app.platform.paths.shipped', return_value=root):
                passages = tools.manual_passages()
            self.assertIn(('Model', 'Model', 'English introduction.'), passages)
            self.assertIn(('Model', 'Lati', 'Lati italiani.'), passages)
            self.assertIn(('Impianto', 'Impianto', 'Impianto italiano.'), passages)

    def test_explicit_anchors_keep_help_links_valid_with_translated_titles(self):
        self.assertEqual(helps.anchors('<a id="il-sito"></a>\n\n## The site\n\nText.\n'), ['il-sito'])

    def test_unavailable_manual_returns_no_passages(self):
        with patch.object(helps, 'manual_dir', return_value=None):
            self.assertEqual(tools.manual_passages(), [])

    def test_the_assistant_manual_index_and_display_use_english(self):
        from meridiana.gui.backend.assistant_help import AssistantHelp
        i18n.setup('en')
        book = AssistantHelp()
        self.assertEqual(next(c['title'] for c in book.chapters if c['id'] == '1-modello.md'), '1. Modelling')
        self.assertTrue(book.openManual('1-modello.md#potenza-richiesta'))
        self.assertEqual(book.manualAnchor, 'potenza-richiesta')
        self.assertIn('#### Power asked', book.manualText)
        self.assertIn('45.13 kWp', book.manualText)
        self.assertNotIn('Facoltativa', book.manualText)

    def test_the_assistant_display_uses_the_same_section_fallback_as_search(self):
        from meridiana.gui.backend.assistant_help import AssistantHelp
        i18n.setup('en')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'en').mkdir()
            (root / '1-modello.md').write_text('# Modello\n\nIntro italiana.\n\n## Lati\n\nLati italiani.\n', encoding='utf-8')
            (root / 'en/1-modello.md').write_text('<a id="modello"></a>\n\n# Model\n\nEnglish introduction.\n', encoding='utf-8')
            with patch.object(helps, 'manual_dir', return_value=root):
                book = AssistantHelp()
                self.assertTrue(book.openManual('1-modello.md#lati'))
            self.assertEqual(helps.chapter_title(book.manualText), 'Model')
            self.assertIn('Lati italiani.', book.manualText)

    def test_italian_fallback_passages_still_receive_the_quotation_marker(self):
        from types import SimpleNamespace
        import json
        i18n.setup('en')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / '1-modello.md').write_text(
                '# Ombre\n\nLe ombre degli ostacoli sono alte perché gli edifici sono vicini al campo.\n', encoding='utf-8')
            with patch.object(helps, 'manual_dir', return_value=root):
                result = tools.run('search_manual', {'query': 'ombre'}, SimpleNamespace(), tools.State())
        self.assertEqual(json.loads(result.content)['quoted_language'], 'Italian')


if __name__ == '__main__':
    unittest.main()
