"""Fresh-process regressions for the weather/sizing race at the first heavy import."""
import os
import subprocess
import sys
import textwrap
import unittest

import _setup


class ConcurrentImport(unittest.TestCase):
    def test_weather_and_stringing_can_start_together_before_pvlib_is_loaded(self):
        code = textwrap.dedent('''
            import importlib.abc
            import importlib.machinery
            import sys
            import tempfile
            import threading
            import time
            from pathlib import Path
            from types import SimpleNamespace
            import requests
            from meridiana.energy import meteo, stringing

            assert 'pvlib' not in sys.modules
            root_entered = threading.Event()
            child_entered = threading.Event()

            class Loader:
                def __init__(self, wrapped, root):
                    self.wrapped, self.root = wrapped, root
                def create_module(self, spec):
                    return self.wrapped.create_module(spec)
                def exec_module(self, module):
                    if self.root:
                        root_entered.set()
                        child_entered.wait(0.4)
                    elif threading.current_thread().name == 'sizing':
                        child_entered.set()
                        time.sleep(0.1)
                    self.wrapped.exec_module(module)

            class Finder(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path=None, target=None):
                    if fullname in ('pvlib', 'pvlib.pvsystem'):
                        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
                        spec.loader = Loader(spec.loader, fullname == 'pvlib')
                        return spec
            sys.meta_path.insert(0, Finder())
            errors, values = [], []
            class NetworkReached(Exception):
                pass
            def no_network(*args, **kwargs):
                raise NetworkReached()
            requests.get = no_network
            def weather():
                try:
                    with tempfile.TemporaryDirectory() as directory:
                        meteo.typical_year(45, 9, Path(directory))
                except NetworkReached:
                    values.append('weather')
                except BaseException as error:
                    errors.append(repr(error))
            def sizing():
                try:
                    assert root_entered.wait(10)
                    module = SimpleNamespace(sdm=lambda: {'linear': True}, vmp=40, beta_voc=-0.25)
                    values.append(stringing.vmp_at(module, 60))
                except BaseException as error:
                    errors.append(repr(error))
            threads = [threading.Thread(target=weather, name='weather', daemon=True),
                       threading.Thread(target=sizing, name='sizing', daemon=True)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(20)
            assert not any(t.is_alive() for t in threads), 'import deadlock'
            assert not errors, errors
            assert 'weather' in values and 36.5 in values, values
            print('concurrent imports passed')
        ''')
        env = {**os.environ, "PYTHONPATH": str(_setup.ROOT / "src")}
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                             env=env, timeout=50, check=False)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("concurrent imports passed", out.stdout)
