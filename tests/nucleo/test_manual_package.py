"""Check manual resources without building packages or opening a window."""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import _setup
from meridiana.app.interface import help as helps
from meridiana.gui import package_check


class ManualPackage(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(package_check, 'manual_resources', None)), 'package check must validate both manuals')

    def test_checkout_contains_both_complete_manuals(self):
        self.assertEqual(package_check.manual_resources()['missing'], [])

    def test_shipped_manual_catches_one_missing_english_chapter(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(_setup.ROOT / 'docs/manuale', root / 'manuale')
            # A missing resource is simulated by moving it within this disposable tree.
            missing = root / 'manuale/en/5-bilancio.md'
            missing.rename(root / 'withheld.md')
            with patch.object(helps, 'REPO_ROOT', root / 'no-checkout'), patch(
                    'meridiana.app.platform.paths.shipped', return_value=root / 'manuale'):
                self.assertEqual(package_check.manual_resources()['missing'], ['en/5-bilancio.md'])

    def test_flatpak_manual_copy_includes_the_english_subdirectory(self):
        import shlex
        manifest = _setup.ROOT / 'build-aux/flatpak/io.github.daniel_g_carrasco.meridiana.yaml'
        copies = [shlex.split(line.strip()[2:]) for line in manifest.read_text(encoding='utf-8').splitlines()
                  if line.strip().startswith('- cp -r docs/manuale ')]
        self.assertEqual(len(copies), 1)
        command = copies[0]
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / Path(command[-1]).name
            shutil.copytree(_setup.ROOT / command[2], target)
            with patch.object(helps, 'manual_dir', return_value=target):
                self.assertEqual(package_check.manual_resources()['missing'], [])

    def test_windows_manual_directory_data_includes_both_languages(self):
        import ast
        spec = _setup.ROOT / 'build-aux/windows/meridiana.spec'
        tree = ast.parse(spec.read_text(encoding='utf-8'))
        data = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'datas' for t in node.targets))
        # Evaluate only the literal resource pairs, not PyInstaller or its build steps.
        entry = next(pair for pair in data.elts if isinstance(pair, ast.Tuple)
                     and isinstance(pair.elts[1], ast.Constant) and pair.elts[1].value == 'share/manuale')
        source = Path(eval(compile(ast.Expression(entry.elts[0]), str(spec), 'eval'), {'ROOT': _setup.ROOT}))
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'share/manuale'
            shutil.copytree(source, target)
            with patch.object(helps, 'manual_dir', return_value=target):
                self.assertEqual(package_check.manual_resources()['missing'], [])


if __name__ == '__main__':
    unittest.main()
