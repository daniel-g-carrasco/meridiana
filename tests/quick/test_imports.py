"""The second interface is explicit and cannot start while enumerating modules."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class Imports(unittest.TestCase):
    def run_fresh(self, code):
        return subprocess.run([sys.executable, '-I', '-c',
                               f'import sys; sys.path.insert(0, {str(ROOT / "src")!r})\n'+code],
                              capture_output=True, text=True, check=True, timeout=30).stdout.strip()

    def test_importing_the_entry_point_does_not_start_the_application(self):
        self.assertEqual(self.run_fresh('import meridiana.quick.__main__\n'
                                       'print("PySide6" in sys.modules)'), 'False')

    def test_the_core_still_imports_without_qt_when_both_interfaces_are_excluded(self):
        code = '''import pkgutil, importlib, meridiana
skip = ('meridiana.ui', 'meridiana.quick', 'meridiana.app', 'meridiana.single_instance', 'meridiana.__main__')
for module in pkgutil.walk_packages(meridiana.__path__, 'meridiana.'):
    if not module.name.startswith(skip):
        importlib.import_module(module.name)
print('PySide6' in sys.modules)
'''
        self.assertEqual(self.run_fresh(code), 'False')
