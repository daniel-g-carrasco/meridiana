"""tools/compile_po.py --check (F7, regola 9): one catalogue, UTF-8, one key per entry, the same placeholders,
no entry src does not use; and the plan's short texts from the one catalogue."""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("compile_po", ROOT / "tools" / "compile_po.py")
compile_po = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compile_po)


class PoCheck(unittest.TestCase):
    def test_the_catalogues_pass_the_check(self):
        run = subprocess.run([sys.executable, str(ROOT / "tools" / "compile_po.py"), "--check"],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "po").rglob("*.po")), ["po/it.po"])

    def test_the_check_finds_what_it_refuses(self):
        text = ('msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
                'msgid "Import an image"\nmsgstr "Importa un?immagine"\n\n'
                'msgid "Import an image"\nmsgstr "Importa un\'immagine"\n\n'
                'msgid "{n} modules"\nmsgstr "{m} moduli"\n\n'
                'msgid "Inv. %1"\nmsgstr "Inverter"\n\n'
                'msgid "Nobody writes this anywhere"\nmsgstr "Nessuno"\n')
        with tempfile.TemporaryDirectory() as d:
            po = Path(d) / "it.po"
            po.write_text(text, encoding="utf-8")
            found = compile_po.problems(po, ({"Import an image", "{n} modules", "Inv. %1"}, ""))
            (Path(d) / "rotto.po").write_bytes("msgid \"a\"\nmsgstr \"è\"\n".encode("cp1252"))
            rotto = compile_po.problems(Path(d) / "rotto.po")
        kinds = [next(k for k in ("broken encoding", "key twice", "placeholders differ", "no line of src") if k in f)
                 for f in found]
        self.assertEqual(sorted(kinds), ["broken encoding", "key twice", "no line of src",
                                         "placeholders differ", "placeholders differ"], found)
        self.assertTrue(rotto and "not UTF-8" in rotto[0], rotto)


class PlanTexts(unittest.TestCase):
    def test_the_plan_reads_its_short_forms_from_the_one_catalogue(self):
        sys.path.insert(0, str(ROOT / "src"))
        from meridiana import i18n
        from meridiana.quick.backend.plan_locale import _
        before = i18n.language()
        self.addCleanup(i18n.setup, before)
        i18n.setup("it")
        self.assertEqual(_("Roof"), "Copertura")                         # msgctxt "plan"
        self.assertEqual(i18n._("Roof"), "Tetto")                         # the Widgets' own entry
        self.assertEqual(_("Click: position · Esc: exit"), "Clic: posizione · Esc: esci")    # from quick-plan
        self.assertEqual(_("Undo"), i18n._("Undo"))                       # no plan entry: the program's


if __name__ == "__main__":
    unittest.main()
