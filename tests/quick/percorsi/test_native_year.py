"""R437, on the real window with native messages: computed, saved, closed, opened again, the numbers are there at once;
changed, marked with what changed and the old numbers still there; Ctrl+Z, up to date again; the report says so too.
Run with
    python -m unittest quick.percorsi.test_native_year
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT/'tools/quick_native_input.py'

FIRST = r'''
import json, time
start = time.perf_counter()
bridge, session = host.bridge, host.bridge.session
wait_until(lambda: not bridge.busy and bool(session.energy), 120)
seen = dict(first_year_s=round(time.perf_counter()-start, 1), kwh=session.energy['sim'].energy_kwh if session.energy.get('sim') is not None else None)
files = host.parts.controllers.get('files')
seen['saved'] = bool(files.saveAs(SAVED))
print(json.dumps(seen))
'''

SECOND = r'''
import json, time
from PySide6.QtCore import QPointF
seen = {}
bridge, session = host.bridge, host.bridge.session
def state():
    return dict(host.shell.yearState)
wait_until(lambda: bool(session.energy), 20)
spin(0.3)
seen['energy_at_once'] = bool(session.energy)
seen['job_started'] = bridge._job is not None
seen['kwh'] = session.energy['sim'].energy_kwh if session.energy.get('sim') is not None else None
seen['state_open'] = state()['state']
win.setProperty('phase', 'production'); spin(1.5)
wait_until(lambda: find(win, name='tile-value-0') is not None, 20)
tile = find(win, name='tile-value-0')
seen['tile'] = tile.property('text') if tile is not None else ''
seen['banner_when_current'] = find(win, name='yearBanner') is not None
# A change: the state says it, the old numbers stay.
session.edit('Losses', lambda p: p.energy.setdefault('losses', {}).__setitem__('soiling', 7.5))
bridge.timer.stop(); spin(0.4)
seen['state_after_edit'] = state()
seen['banner_after_edit'] = find(win, name='yearBanner') is not None
seen['banner_text'] = find(win, name='yearBannerText').property('text') if seen['banner_after_edit'] else ''
seen['tile_after_edit'] = find(win, name='tile-value-0').property('text')
win.setProperty('phase', 'report'); spin(1.5)
report = find(win, name='reportYearState')
seen['report_state_stale'] = report.property('text') if report is not None else ''
win.setProperty('phase', 'production'); spin(0.5)
# Ctrl+Z: up to date again, at once, with a native key.
native.key('z', ('ctrl',)); spin(0.5)
seen['state_after_undo'] = state()['state']
seen['banner_after_undo'] = find(win, name='yearBanner') is not None
seen['tile_after_undo'] = find(win, name='tile-value-0').property('text')
# Compute asked from the banner: never zeros meanwhile, with the bar.
session.edit('Losses', lambda p: p.energy.setdefault('losses', {}).__setitem__('soiling', 8.5))
bridge.timer.stop(); spin(0.3)
native.click(*center(find(win, name='yearBannerCompute')));
tiles = []
start = time.perf_counter()
while time.perf_counter() - start < 60 and bridge.busy:
    native.spin(50)
    item = find(win, name='tile-value-0')
    tiles.append(item.property('text') if item is not None else '')
seen['tiles_during'] = sorted(set(tiles))[:6]
seen['state_after_year'] = state()['state']
seen['warnings'] = host.warnings[-4:]
print(json.dumps(seen, ensure_ascii=False))
'''


def _run(*args, timeout):
    environment = dict(os.environ, PYTHONUTF8='1', PYTHONPATH=os.pathsep.join((str(ROOT/'tests'), str(ROOT/'src'))))
    with tempfile.TemporaryFile() as output:     # a pipe would stay open in the program left running
        code = subprocess.run([sys.executable, str(TOOL), *args], stdout=output, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, env=environment, timeout=timeout, cwd=ROOT).returncode
        output.seek(0)
        return code, output.read().decode('utf-8', 'replace')


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class YearKept(unittest.TestCase):
    seen = None

    @classmethod
    def journey(cls, folder, ctl, project, script):
        ctl = Path(folder)/ctl
        code, text = _run('start', '--engine', 'quick', '--ctl', str(ctl), '--timeout', '120', '--project', str(project),
                          '--cache', str(Path(folder)/'cache'), '--desktop', 'meridiana-collaudo-anno', timeout=140)
        if code:
            raise AssertionError(text)
        path = Path(folder)/(ctl.name+'.py')
        path.write_text(script, encoding='utf-8')
        code, text = _run('run', '--ctl', str(ctl), str(path), '--timeout', '240', timeout=260)
        _run('run', '--ctl', str(ctl), '--stop', timeout=30)
        try:
            return json.loads(text.strip().splitlines()[-1])
        except (IndexError, ValueError):
            raise AssertionError(text) from None

    @classmethod
    def setUpClass(cls):
        sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'src')]
        from _fixtures import capannone
        cls.folder = tempfile.TemporaryDirectory(prefix='meridiana-native-anno-', ignore_cleanup_errors=True)
        folder = Path(cls.folder.name)
        source = folder/'prova.meridiana'
        capannone().save(source)
        saved = folder/'salvato.meridiana'
        cls.first = cls.journey(folder, 'one', source, f'SAVED = {str(saved)!r}\n' + FIRST)
        cls.size = saved.stat().st_size
        cls.seen = cls.journey(folder, 'two', saved, SECOND)
        cls.kept = sorted((folder/'cache/years').glob('*.year'))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_opened_again_the_numbers_are_there_without_a_computation(self):
        self.assertTrue(self.first['saved'])
        self.assertTrue(self.seen['energy_at_once'])
        self.assertFalse(self.seen['job_started'])
        self.assertEqual(self.seen['kwh'], self.first['kwh'])
        self.assertEqual(self.seen['state_open'], 'current')
        self.assertFalse(self.seen['banner_when_current'])
        self.assertTrue(self.seen['tile'])
        print(f'R437: year kept {self.kept[0].stat().st_size} bytes, project file {self.size} bytes, first year {self.first["first_year_s"]} s')

    def test_a_change_is_said_with_what_changed_and_the_old_numbers_stay(self):
        self.assertEqual(self.seen['state_after_edit']['state'], 'stale')
        self.assertTrue(self.seen['banner_after_edit'])
        self.assertIn('perdite', self.seen['banner_text'])
        self.assertEqual(self.seen['tile_after_edit'], self.seen['tile'])
        self.assertIn('non aggiornati', self.seen['report_state_stale'].lower())

    def test_ctrl_z_comes_back_up_to_date(self):
        self.assertEqual(self.seen['state_after_undo'], 'current')
        self.assertFalse(self.seen['banner_after_undo'])
        self.assertEqual(self.seen['tile_after_undo'], self.seen['tile'])

    def test_r435_never_zeros_while_computing(self):
        for text in self.seen['tiles_during']:
            self.assertTrue(text and not text.startswith('0 '), self.seen['tiles_during'])
        self.assertEqual(self.seen['state_after_year'], 'current')

    def test_no_qml_warning(self):
        self.assertEqual(self.seen['warnings'], [])


if __name__ == '__main__':
    unittest.main()
