"""Negative fixtures for the layer guard: no application module is imported."""
import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nucleo import test_strati as guard


@contextlib.contextmanager
def package(files):
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        for name, source in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding='utf-8')
        with patch.object(guard, 'SRC', root), patch.object(guard, 'MODULES', set()):
            guard.MODULES = guard.modules()
            yield root


class ImportGuards(unittest.TestCase):
    def test_deferred_dynamic_imports_cannot_bypass_layer_rules(self):
        with package({'core/bad.py': '''import importlib as loader
from importlib import import_module as load

def later():
    loader.import_module("PySide6.QtCore")
    load("meridiana.gui.window")
    __import__("requests")
''', 'gui/window.py': ''}):
            messages = '\n'.join(message for lines in guard.against_the_rules().values() for message in lines)
            for rule in ('Qt only in gui', 'core may not import gui', 'no network in core'):
                self.assertIn(rule, messages)

    def test_relative_import_between_folders_is_rejected_even_within_one_layer(self):
        with package({'core/model/bad.py': 'from ..geometry import shape\n', 'core/geometry/shape.py': ''}):
            messages = '\n'.join(message for lines in guard.against_the_rules().values() for message in lines)
            self.assertIn('R5', messages)

    def test_relative_import_within_one_folder_is_allowed(self):
        with package({'core/model/good.py': 'from . import shape\n', 'core/model/shape.py': ''}):
            self.assertEqual(guard.against_the_rules(), {})

    def test_dynamic_relative_import_cannot_bypass_r5(self):
        with package({'app/load.py': 'from importlib import import_module\nimport_module(".platform.paths", "meridiana.app")\n',
                      'app/platform/paths.py': ''}):
            messages = '\n'.join(message for lines in guard.against_the_rules().values() for message in lines)
            self.assertIn('R5', messages)

    def test_replacing_an_approved_debt_at_the_same_count_is_rejected(self):
        replacement = dict(guard.DEBITI)
        replacement.pop(next(iter(replacement)))
        replacement['core/unapproved.py -> gui/unapproved'] = 'not approved'
        with patch.dict(guard.DEBITI, replacement, clear=True):
            with self.assertRaises(AssertionError):
                guard.Layers().test_the_debts_are_those_of_the_study()


if __name__ == '__main__':
    unittest.main()
