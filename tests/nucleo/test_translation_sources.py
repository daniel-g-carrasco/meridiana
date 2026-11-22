"""Extraction and coverage use the same Python, table and QML messages."""
import tempfile
import unittest
from pathlib import Path

from tools import compile_po


class TranslationSources(unittest.TestCase):
    def test_plan_wrapper_accepts_its_context_or_the_shared_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'src').mkdir()
            (root / 'po').mkdir()
            (root / 'src/plan.py').write_text('from .plan_locale import _\n_("Short plan text")', encoding='utf-8')
            po = root / 'po/it.po'
            for prefix in ('', 'msgctxt "plan"\n'):
                po.write_text(prefix + 'msgid "Short plan text"\nmsgstr "Testo"\n', encoding='utf-8')
                self.assertEqual(compile_po.check_all(root), [])

    def test_catalogue_fields_are_marked_and_reasons_come_from_the_rules(self):
        """The catalogue's labels are marked with N_ (R593): no rule of the extraction knows schema.py."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            catalogue = root / 'src/meridiana/data/catalog'
            catalogue.mkdir(parents=True)
            (catalogue / 'schema.py').write_text('''
CHOICES = (("id", N_("Choice label")),)
GROUP = (N_("Group title"), (Field("key", N_("Field label"), hint=N_("Field hint"),
         choices=CHOICES, when=("other_key", "internal_value")),))
UNMARKED = ("Not a message", (Field("other", "Unmarked label"),))
''', encoding='utf-8')
            (catalogue / 'optimizer_rules.json').write_text('{"maker": {"why": "Maker reason", "id": "internal"}}',
                                                          encoding='utf-8')
            self.assertEqual(compile_po.required_messages(root), {(None, text) for text in (
                'Choice label', 'Group title', 'Field label', 'Field hint', 'Maker reason')})

    def test_extracts_qml_and_python_tables_without_comment_or_identifier_noise(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'src'
            source.mkdir()
            (source / 'page.qml').write_text('''
// qsTr("Comment only")
/* qsTr("Block comment") */
Text { text: qsTr("Rename object") + qsTr('It\\'s ready') }
Text { text: qsTr("Long " + "message") }
Text { text: qsTr("Rename object", "disambiguation") }
Text { text: qsTr(runtimeValue) }
Text { text: qsTr("%n module", "%n modules", count) }
property var later: [QT_TR_NOOP("Marked for later"), QT_TRANSLATE_NOOP("plan", "Marked with a context")]
''', encoding='utf-8')
            (source / 'page.py').write_text('''
labels = {'internal_id': 'Chart title'}
copy = {key: _(value) for key, value in labels.items()}
def tile(key, title):
    return _(title)
tile('open_id', 'Open project')
message = 'Variable message'
_(message)
_('Direct message')
pgettext('plan', 'Roof')
ngettext('One module', 'Many modules', 2)
npgettext('plan', 'One roof', 'Many roofs', 2)
N_('Marked in Python')
ITALIAN = {'Not extracted': 'Traduzione'}
''', encoding='utf-8')
            messages = compile_po.required_messages(root)
            self.assertEqual(messages, {(None, text) for text in (
                'Rename object', "It's ready", 'Long message', 'Chart title', 'Open project', 'Variable message',
                'Direct message', 'One module', '%n module', 'Marked for later', 'Marked in Python')} | {
                ('plan', 'Roof'), ('disambiguation', 'Rename object'), ('plan', 'Marked with a context'),
                ('plan', 'One roof')})
            self.assertEqual(compile_po.required_plurals(root), {
                (None, 'One module'): 'Many modules', (None, '%n module'): '%n modules', ('plan', 'One roof'): 'Many roofs'})

    def test_missing_messages_fail_check_and_present_messages_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'src').mkdir()
            (root / 'po').mkdir()
            (root / 'src/page.qml').write_text('Text { text: qsTr("Keep me") }', encoding='utf-8')
            po = root / 'po/it.po'
            po.write_text('msgid ""\nmsgstr ""\n', encoding='utf-8')
            self.assertTrue(any('missing message' in line and 'Keep me' in line
                                for line in compile_po.check_all(root)))
            po.write_text('msgid "Keep me"\nmsgstr "Conservami"\n', encoding='utf-8')
            self.assertEqual(compile_po.check_all(root), [])

    def test_a_plural_needs_its_plural_entry_and_a_translation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'src').mkdir()
            (root / 'po').mkdir()
            (root / 'src/page.qml').write_text('Text { text: qsTr("%n item", "%n items", n) + qsTr("Other") }',
                                               encoding='utf-8')
            po = root / 'po/it.po'
            po.write_text('msgid "%n item"\nmsgstr "%n elemento"\n\nmsgid "Other"\nmsgstr ""\n', encoding='utf-8')
            found = compile_po.check_all(root)
            self.assertTrue(any('without a plural' in line and '%n item' in line for line in found), found)
            self.assertTrue(any('not translated' in line and 'Other' in line for line in found), found)
            po.write_text('msgid "%n item"\nmsgid_plural "%n items"\nmsgstr[0] "%n elemento"\nmsgstr[1] "%n elementi"\n'
                          '\nmsgid "Other"\nmsgstr "Altro"\n', encoding='utf-8')
            self.assertEqual(compile_po.check_all(root), [])

    def test_a_dictionary_of_translations_in_the_code_is_refused(self):
        """R593: a translation is looked for in one place. The four tables taken out on 20/11/2026 (catalogue,
        plant, settings, Meridio) had these two shapes."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'src').mkdir()
            (root / 'po').mkdir()
            (root / 'po/it.po').write_text('msgid "Send"\nmsgstr "Invia"\n\nmsgid "Stop"\nmsgstr "Ferma"\n\n'
                                           'msgid "Close"\nmsgstr "Chiudi"\n', encoding='utf-8')
            page = root / 'src/page.py'
            calls = "_('Send'), _('Stop'), _('Close')\n"
            page.write_text(calls + "ITALIAN = {'Choose a file': 'Scegli un file della cartella', 'Not now': 'Non ora',\n"
                            "           'Read aloud': 'Leggi ad alta voce', 'Speed': 'Velocità'}\n", encoding='utf-8')
            self.assertTrue(any('page.py:2: a dictionary of translations' in line
                                for line in compile_po.check_all(root)))
            page.write_text(calls + "labels = dict(send='Invia', stop='Ferma', close='Chiudi')\n", encoding='utf-8')
            self.assertTrue(any('page.py:2: a dictionary of translations' in line
                                for line in compile_po.check_all(root)))
            page.write_text(calls + "keys = {'send': 'Send', 'stop': 'Stop', 'close': 'Close'}\n", encoding='utf-8')
            self.assertEqual(compile_po.check_all(root), [])

    def test_no_translator_is_written_in_python(self):
        """R593: Qt translates on its own threads too (the QML loader's) and a translate() in Python there stops the
        window; the QML's catalogue is a .qm read by Qt's own QTranslator (gui/translator.py)."""
        import ast
        found = []
        for path in sorted((compile_po.ROOT / 'src').rglob('*.py')):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
                if isinstance(node, ast.ClassDef) and any(getattr(base, 'id', getattr(base, 'attr', '')) == 'QTranslator'
                                                          for base in node.bases):
                    found.append(f'{path.relative_to(compile_po.ROOT).as_posix()}:{node.lineno} {node.name}')
        self.assertEqual(found, [])

    def test_the_qml_catalogue_is_a_qm_with_context_and_plural(self):
        """The .qm compile_po writes, read here as Qt's QTranslator reads it (by the hash of source and comment):
        messages without a Qt context, msgctxt as the comment, a plural with its English plural as the comment."""
        entries = compile_po.parse('msgid ""\nmsgstr "Plural-Forms: nplurals=2; plural=(n != 1);\\n"\n\n'
                                   'msgid "Roof"\nmsgstr "Tetto"\n\nmsgctxt "plan"\nmsgid "Roof"\nmsgstr "Copertura"\n\n'
                                   'msgid "%n folder"\nmsgid_plural "%n folders"\nmsgstr[0] "%n cartella"\n'
                                   'msgstr[1] "%n cartelle"\n')
        data = compile_po.qm(entries, 'it')
        self.assertTrue(data.startswith(compile_po.QM_MAGIC))
        for source, comment in (('Roof', ''), ('Roof', 'plan'), ('%n folder', '%n folders')):
            self.assertIn(compile_po._elf_hash((source + comment).encode()).to_bytes(4, 'big'), data)
        self.assertIn('%n cartelle'.encode('utf-16-be'), data)
        english = compile_po.qm(entries, 'en', english=True)
        self.assertIn('%n folders'.encode('utf-16-be'), english)
        self.assertNotIn('Tetto'.encode('utf-16-be'), english)
        with self.assertRaises(compile_po.PoError):
            compile_po.qm(compile_po.parse('msgid ""\nmsgstr "Plural-Forms: nplurals=3; plural=(n%10==1 ? 0 : 1);\\n"\n'
                                           '\nmsgid "a"\nmsgstr "b"\n'), 'xx')

    def test_the_source_has_no_dictionary_of_translations(self):
        self.assertEqual(compile_po.dictionaries(compile_po.ROOT), [])


if __name__ == '__main__':
    unittest.main()
