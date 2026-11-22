"""Keep translated chapters, command explanations and gettext terminology together."""
import re
import unittest

import _setup
from _knowledge_text import explained, fold
from meridiana import i18n
from meridiana.app.assistant import tools
from meridiana.app.interface import help as helps, shortcuts

ROOT = _setup.ROOT / 'docs/manuale'
HEADINGS = {
    'README.md': ('Meridiana manual', 'How to ask for help', 'Text menus', 'Settings', 'Clients and jobs',
                  'Layout, canopies and BIM model', 'Sizing and calculation limits', 'Report profiles',
                  'Meridio, the assistant', 'Local projects and tasks', 'A local model in a few steps',
                  'The chapters', 'Installing and updating', 'How to read the numbers', 'Updates, documents and support'),
    '1-modello.md': ('1. Modelling', 'The site', 'Row pitch from the sun', 'Day and hours of the sub-field',
                     'Connection and obligations', 'The buildings', 'Roof', 'Building from a template',
                     "From the architect's model (IFC)", 'Sides', 'Moving and rotating', 'Fire brigade',
                     'The sub-field', 'Rows by hand', 'Mounting', 'Modules per table, across', 'Module placement',
                     'Power asked', 'Gaps and margins', 'From the edge of the area', 'Between rows', 'Row pitch',
                     "Out of the obstacles' shadows", 'The exclusions'),
    '2-impianto.md': ('2. Plant', 'The panel on the right', 'The strings are yours', 'Drawing a string by hand', 'On the plan'),
    '3-producibilita.md': ('3. Production', 'Module connection', "The site's weather", 'PVGIS', 'The results',
                          'Energy a year', 'Specific yield', 'Performance ratio', 'Power', 'Losses', 'How it is computed'),
    '4-consumi.md': ('4. Consumption', 'Where it comes from', 'The results', 'Consumption a year', 'The bands', 'Shape of the consumption'),
    '5-bilancio.md': ('5. Balance and economics', 'Self-consumption', 'Self-sufficiency', 'The first year',
                      'Net present value', 'Return', 'Prices'),
    '6-relazione.md': ('6. Report', 'Navigating the preview', "Copying a page's text", 'Scope of the regulatory profile'),
    'verifiche.md': ('Checks', 'The symbols', 'To fix', 'To check', 'To know', 'Passed', 'Source'),
    'glossario.md': ('Interface glossary',),
}


def glossary():
    rows = re.findall(r'^\| ([^|]+) \| ([^|]+) \|$', (ROOT / 'glossario.md').read_text(encoding='utf-8'), re.M)
    return [(it.strip(), en.strip()) for it, en in rows if it not in ('Italiano', '---')]


def prose(text):
    """Exclude identifiers and explicitly marked verbatim Italian legal quotations."""
    text = re.sub(r'<q lang="it">.*?</q>', '', text, flags=re.S)
    text = re.sub(r'```.*?```|`[^`]*`|<[^>]*>', '', text, flags=re.S)
    return re.sub(r'\]\([^)]*\)', ']', text)


def contains(text, term, *, case_sensitive=False):
    flags = 0 if case_sensitive else re.I
    return re.search(r'(?<!\w)' + re.escape(term).replace(r'\ ', r'\s+') + r'(?!\w)', text, flags) is not None


def interface_term_in(text, term, terms):
    """Match the longest interface label, not a shorter label embedded in it."""
    for longer, _ in sorted(terms, key=lambda pair: len(pair[0]), reverse=True):
        if len(longer) > len(term) and contains(longer, term, case_sensitive=True):
            text = text.replace(longer.rstrip('…'), '')
    return contains(text, term.rstrip('…'), case_sensitive=True)


class ManualTranslation(unittest.TestCase):
    def test_files_headings_and_anchors_match_in_order(self):
        self.assertEqual({p.name for p in ROOT.glob('*.md')}, {p.name for p in (ROOT / 'en').glob('*.md')})
        for p in ROOT.glob('*.md'):
            it = p.read_text(encoding='utf-8')
            en = (ROOT / 'en' / p.name).read_text(encoding='utf-8')
            with self.subTest(file=p.name):
                self.assertEqual([l for l, _ in helps.headings(it)], [l for l, _ in helps.headings(en)])
                self.assertEqual(tuple(title for _, title in helps.headings(en)), HEADINGS[p.name])
                self.assertEqual(helps.anchors(it), helps.anchors(en))
                self.assertTrue(all(title for _, title in helps.headings(en)))
                self.assertEqual(len(re.findall(r'^\|', it, re.M)), len(re.findall(r'^\|', en, re.M)))
                if p.name != 'glossario.md':
                    self.assertEqual(re.findall(r'`([^`]+)`', it), re.findall(r'`([^`]+)`', en))

    def test_commands_explained_in_italian_are_explained_in_english(self):
        kept = i18n._translation
        self.addCleanup(setattr, i18n, '_translation', kept)
        i18n.setup('it')
        italian = [fold(f'{heading} {text}') for _, heading, text in tools.manual_passages()]
        required = {c.id for c in shortcuts.commands() if explained(c.text, italian)}
        self.assertGreater(len(required), 30, 'the guard must cover the manual commands of study 50')
        i18n.setup('en')
        english = [fold(f'{heading} {text}') for _, heading, text in tools.manual_passages()]
        missing = [c.id for c in shortcuts.commands() if c.id in required and not explained(c.text, english, language='en')]
        self.assertEqual(missing, [], 'commands with an Italian explanation need an English explanation too')

    def test_glossary_terms_use_the_gettext_english_in_the_same_section(self):
        terms = glossary()
        # Read the actual compiled catalogue, also used by the program, not a second glossary.
        catalogue = i18n.translation_for('it')
        displayed = {(en.replace('&', ''), it.replace('&', ''))
                     for en, it in catalogue._catalog.items() if isinstance(en, str)}
        for it, en in terms:
            self.assertIn((en, it), displayed, en)
        for name in helps.CHAPTERS:
            italian = helps.sections((ROOT / name).read_text(encoding='utf-8'))
            english = {a: (h, body) for _, h, a, body in helps.sections((ROOT / 'en' / name).read_text(encoding='utf-8'))}
            for _, heading, anchor, body in italian:
                source = prose(heading + '\n' + body)
                target = prose('\n'.join(english[anchor]))
                for it in {it for it, _ in terms}:
                    # Capitalised interface labels, not homographs in running prose:
                    # "File" is a menu, "file" can mean rows; "Modifica" is Edit,
                    # whereas "modifica" in a sentence can mean a change.
                    if interface_term_in(source, it, terms):
                        choices = [en for term, en in terms if term == it]
                        with self.subTest(file=name, section=anchor, term=it):
                            self.assertTrue(any(contains(target, en) for en in choices), choices)

    def test_no_italian_glossary_term_leaks_outside_legal_quotations(self):
        terms = glossary()
        # Identical words and words contained in legitimate English labels are not leaks.
        shared = {it for it, _ in terms if any(contains(en, it) for _, en in terms)}
        for name in helps.CHAPTERS:
            text = prose((ROOT / 'en' / name).read_text(encoding='utf-8'))
            for it, _ in terms:
                if it not in shared:
                    with self.subTest(file=name, term=it):
                        self.assertFalse(contains(text, it), it)


if __name__ == '__main__':
    unittest.main()
