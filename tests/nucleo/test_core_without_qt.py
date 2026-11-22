"""The core runs without Qt (NQ, for a future interface that is not Qt): the energy system, the model and the
session, imported in a fresh interpreter, never load PySide6; nor does any other module of the package outside the
interface's side (gui/ and __main__.py). tests/nucleo/test_strati.py reads the imports; this one imports for real, so
it sees a Qt brought by a library too."""

import subprocess
import sys
import unittest

import _setup

SRC = str(_setup.ROOT / "src")
INTERFACE = ("meridiana.gui", "meridiana.__main__")


def run(code: str) -> str:
    out = subprocess.run([sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {SRC!r})\n" + code],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


class NoQt(unittest.TestCase):
    def test_the_system_the_model_and_the_session_do_not_load_pyside6(self):
        out = run("import meridiana.core.energy.system, meridiana.core.model.model, meridiana.app.session\n"
                  "print(sorted(m for m in sys.modules if m.split('.')[0] in ('PySide6', 'shiboken6')))")
        self.assertEqual(out, "[]")

    def test_no_module_outside_the_interface_loads_pyside6(self):
        out = run("import importlib, pkgutil, meridiana\n"
                  "bad = []\n"
                  f"skip = {INTERFACE!r}\n"
                  "for m in pkgutil.walk_packages(meridiana.__path__, 'meridiana.'):\n"
                  "    if m.name.startswith(skip):\n"
                  "        continue\n"
                  "    importlib.import_module(m.name)\n"
                  "    if 'PySide6' in sys.modules:\n"
                  "        bad.append(m.name)\n"
                  "        break\n"
                  "print(bad)")
        self.assertEqual(out, "[]")


if __name__ == "__main__":
    unittest.main()
