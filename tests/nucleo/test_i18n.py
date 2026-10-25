#!/usr/bin/env python3
"""The language of the interface: the preference first, then the variables
of the desktop, or on Windows (which sets none) the language of its own
interface."""

import os
import unittest
from unittest import mock

import _setup

from meridiana import i18n

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

VARS = ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")
CATALOGUE = _setup.ROOT / "locale" / "it" / "LC_MESSAGES" / "meridiana.mo"


@unittest.skipUnless(CATALOGUE.exists(), "tools/compile_po.py first")
class LanguageTest(unittest.TestCase):
    def setUp(self):
        saved = {var: os.environ.pop(var, None) for var in VARS}
        self.addCleanup(lambda: [os.environ.__setitem__(k, v) for k, v in saved.items() if v is not None])
        before = i18n._translation        # the other tests read the source strings
        self.addCleanup(lambda: setattr(i18n, "_translation", before))

    def test_the_variables_first(self):
        os.environ["LANG"] = "it_IT.UTF-8"
        with mock.patch.object(i18n, "_system_languages", return_value=["en_US"]):
            i18n.setup()
        self.assertEqual(i18n._("Properties"), "Proprietà")

    def test_the_preference_over_the_variables(self):
        os.environ["LANG"] = "it_IT.UTF-8"
        i18n.setup("en")
        self.assertEqual(i18n._("Properties"), "Properties")
        i18n.setup("it")
        self.assertEqual(i18n._("Properties"), "Proprietà")

    def test_without_variables_the_system_language(self):
        with mock.patch.object(i18n, "_system_languages", return_value=["it_IT"]):
            i18n.setup()
        self.assertEqual(i18n._("Properties"), "Proprietà")
        with mock.patch.object(i18n, "_system_languages", return_value=["en_US"]):
            i18n.setup()
        self.assertEqual(i18n._("Properties"), "Properties")

    def test_plurals(self):
        i18n.setup("it")
        self.assertEqual(i18n.ngettext("{n} module laid in {ms} ms", "{n} modules laid in {ms} ms", 2),
                         "{n} moduli posati in {ms} ms")
        self.assertEqual(i18n.ngettext("{n} module laid in {ms} ms", "{n} modules laid in {ms} ms", 1),
                         "{n} modulo posato in {ms} ms")

    def test_numbers_in_the_language_of_the_window(self):
        i18n.setup("it")
        self.assertEqual(i18n.language(), "it")
        self.assertEqual(i18n.number(3.5791), "3,58")
        self.assertEqual(i18n.number(-11.94, 1, sign=True), "-11,9")
        i18n.setup("en")
        self.assertEqual(i18n.language(), "en")
        self.assertEqual(i18n.number(3.5791), "3.58")


class WindowsLanguageTest(unittest.TestCase):
    @unittest.skipUnless(_setup.WINDOWS, "Windows only")
    def test_windows_interface_language(self):
        languages = i18n._system_languages()
        self.assertEqual(len(languages), 1)
        self.assertRegex(languages[0], r"^[a-z]{2,3}(_[A-Z]{2})?")

    def test_counts_as_the_locale_writes_them(self):
        import locale
        before = locale.setlocale(locale.LC_NUMERIC)
        self.addCleanup(locale.setlocale, locale.LC_NUMERIC, before)
        locale.setlocale(locale.LC_NUMERIC, "C")
        self.assertEqual(i18n.count(1200), "1200")                      # the C locale groups nothing
        for name in ("it_IT.UTF-8", "it_IT.utf8", "it-IT", "Italian_Italy.1252"):
            try:
                locale.setlocale(locale.LC_NUMERIC, name)
                break
            except locale.Error:
                continue
        else:
            self.skipTest("no Italian locale on this machine: the grouping is not tried")
        sep = locale.localeconv()["thousands_sep"]          # "." or a space: the system's tables differ (Windows)
        self.assertTrue(sep)
        self.assertEqual((i18n.count(1200), i18n.count(1234567)), (f"1{sep}200", f"1{sep}234{sep}567"))


class CompilerTest(unittest.TestCase):
    """tools/compile_po.py without msgfmt (Windows with python.org's Python, the Windows runner): the same catalogue
    as GNU's for what Meridiana's .po files use (task 18f)."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location("compile_po", _setup.ROOT / "tools" / "compile_po.py")
        cls.tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.tool)

    def catalogue(self, text: str):
        import gettext
        import io
        return gettext.GNUTranslations(io.BytesIO(self.tool.mo(self.tool.parse(text))))

    def test_contexts_plurals_escapes_and_what_msgfmt_leaves_out(self):
        po = ('msgid ""\nmsgstr ""\n"Language: it\\n"\n"POT-Creation-Date: 2026-10-22\\n"\n'
              '"Content-Type: text/plain; charset=UTF-8\\n"\n'
              '"Plural-Forms: nplurals=2; plural=(n != 1);\\n"\n\n'
              '#: a.py:1\nmsgid "Open"\nmsgstr "Apri"\n\n'
              'msgctxt "menu"\nmsgid "Open"\nmsgstr "Apri…"\n\n'
              'msgid "{n} module"\nmsgid_plural "{n} modules"\nmsgstr[0] "{n} modulo"\nmsgstr[1] "{n} moduli"\n\n'
              'msgid ""\n"two\\n"\n"lines \\"quoted\\""\nmsgstr "due\\nrighe \\"tra virgolette\\""\n\n'
              '#, fuzzy\nmsgid "Close"\nmsgstr "Chiudi forse"\n\n'
              'msgid "Save"\nmsgstr ""\n\n'
              '#~ msgid "Gone"\n#~ msgstr "Andato"\n')
        t = self.catalogue(po)
        self.assertEqual(t.gettext("Open"), "Apri")
        self.assertEqual(t.pgettext("menu", "Open"), "Apri…")
        self.assertEqual(t.ngettext("{n} module", "{n} modules", 1), "{n} modulo")
        self.assertEqual(t.ngettext("{n} module", "{n} modules", 3), "{n} moduli")
        self.assertEqual(t.gettext('two\nlines "quoted"'), 'due\nrighe "tra virgolette"')
        self.assertEqual(t.gettext("Close"), "Close")              # fuzzy: left out
        self.assertEqual(t.gettext("Save"), "Save")                # untranslated: left out
        self.assertEqual(t.gettext("Gone"), "Gone")                # obsolete
        self.assertEqual(t.info()["language"], "it")
        self.assertNotIn("pot-creation-date", t.info())            # as msgfmt: a build repeatable

    def test_a_translation_with_a_placeholder_its_source_has_not_is_refused(self):
        entries = self.tool.parse('msgid "{n} files"\nmsgstr "{count} file"\n')
        with self.assertRaises(self.tool.PoError):
            self.tool.check(entries)
        self.tool.check(self.tool.parse('msgid "{n} files ({{x}})"\nmsgstr "{n:d} file"\n'))     # fine

    def test_the_italian_catalogue_compiles_whole(self):
        import shutil
        import subprocess
        import tempfile
        from pathlib import Path
        po = _setup.ROOT / "po" / "it.po"
        entries = self.tool.parse(po.read_text(encoding="utf-8"), po.name)
        self.tool.check(entries, po.name)
        t = self.catalogue(po.read_text(encoding="utf-8"))
        translated = [e for e in entries if e.get("msgstr") and e["msgid"] and not e["fuzzy"] and "msgctxt" not in e]
        self.assertGreater(len(translated), 1000)
        for e in translated:
            self.assertEqual(t.gettext(e["msgid"]), e["msgstr"])
        if shutil.which("msgfmt"):                                 # Linux, and the CI: the very same catalogue
            import gettext
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "it.mo"
                subprocess.run(["msgfmt", "-o", str(out), str(po)], check=True)
                with open(out, "rb") as f:
                    self.assertEqual(gettext.GNUTranslations(f)._catalog, t._catalog)


if __name__ == "__main__":
    unittest.main()
