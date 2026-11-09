"""The real window driven by native messages: what Daniel found with his mouse, and what must not break.

A method marked expectedFailure names a defect listed in docs/quick/collaudo/difetti.csv: when the correction
arrives the mark must go, because unittest reports an unexpected success. Run with
    python -m unittest quick.percorsi.test_native
Each run writes docs/quick/collaudo/run-native.json, which the compatibility registry reads as evidence.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from quick.percorsi.native_journey import JOURNEY

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT/'tools/quick_native_input.py'
REPORT = ROOT/'docs/quick/collaudo/run-native.json'
PARITY = {'test_ctrl_digits_change_phase': ['shortcut:phase_model', 'shortcut:phase_plant'],
          'test_ctrl_tab_changes_phase': ['shortcut:next_phase'],
          'test_delete_removes_the_selection': ['shortcut:delete']}


def _run(*args, timeout):
    environment = dict(os.environ, PYTHONUTF8='1', PYTHONPATH=os.pathsep.join((str(ROOT/'tests'), str(ROOT/'src'))))
    with tempfile.TemporaryFile() as output:     # a pipe would stay open in the program left running
        code = subprocess.run([sys.executable, str(TOOL), *args], stdout=output, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, env=environment, timeout=timeout, cwd=ROOT).returncode
        output.seek(0)
        return code, output.read().decode('utf-8', 'replace')


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class NativeJourney(unittest.TestCase):
    seen = None

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='meridiana-native-test-', ignore_cleanup_errors=True)
        ctl = cls.folder.name
        code, text = _run('start', '--engine', 'quick', '--ctl', ctl, '--timeout', '120',
                          '--desktop', 'meridiana-collaudo-test', timeout=140)
        if code:
            raise AssertionError(text)
        script = Path(ctl)/'journey-script.py'
        script.write_text(JOURNEY, encoding='utf-8')
        code, text = _run('run', '--ctl', ctl, str(script), '--timeout', '200', timeout=220)
        _run('run', '--ctl', ctl, '--stop', timeout=30)
        lines = text.strip().splitlines()
        if os.environ.get('MERIDIANA_NATIVE_DUMP'):
            Path(os.environ['MERIDIANA_NATIVE_DUMP']).write_text(text, encoding='utf-8')
        try:
            cls.seen = json.loads(lines[-1])
        except (IndexError, ValueError):
            raise AssertionError(text) from None

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def tearDown(self):
        outcome = self._outcome.result
        failed = {test.id().rsplit('.', 1)[-1] for test, _ in outcome.failures + outcome.errors}
        cases.append(dict(name=self._testMethodName, failed=self._testMethodName in failed))

    # Daniel's list, 05/11/2026. Common cause, corrected: the assistant layer lived in Qt's overlay with a
    # window-wide HoverHandler (Assistant/AssistantLayer.qml, Shell/Workbench.qml).
    def test_hover_reaches_a_button(self):
        self.assertTrue(self.seen['hover_on_button'])

    def test_tooltip_appears_on_a_button(self):
        self.assertTrue(self.seen['tip_on_button'])

    def test_no_tooltip_stays_after_leaving(self):
        self.assertEqual(self.seen['stuck_tips'], 0)

    def test_no_hover_stays_after_a_click(self):
        self.assertEqual(self.seen['stuck_hover_alpha'], [0, 0])

    def test_menu_closes_on_a_click_outside(self):
        self.assertTrue(self.seen['closes_outside'])

    def test_menu_entry_lights_under_the_pointer(self):
        self.assertTrue(self.seen['entry_hover'])

    def test_provider_menu_is_above_the_bubble(self):
        self.assertTrue(self.seen['provider_menu_on_top'])

    def test_background_menu_is_not_a_list_of_every_source(self):
        self.assertLess(self.seen['background_menu_height'], 400)

    def test_maps_are_on_at_start(self):
        self.assertFalse(self.seen['maps_offline_at_start'])

    def test_ground_has_the_size_of_the_widgets(self):
        self.assertAlmostEqual(self.seen['ground_scale'], self.seen['ground_half']/50, places=3)

    def test_3d_view_lies_on_whole_pixels(self):
        for value in self.seen['scene_view']:
            self.assertAlmostEqual(value, round(value), places=3)

    # Found on the way.
    def test_ctrl_z_undoes(self):
        self.assertEqual(self.seen['after_ctrl_z'], 0)

    def test_a_check_row_stays_on_one_line(self):
        self.assertEqual(set(self.seen['check_row_heights']), {34})

    def test_panel_carried_to_a_column_is_stacked(self):
        self.assertFalse(self.seen['carried_panels_overlap'])

    # What works, and must keep working.
    def test_menu_closes_with_esc(self):
        self.assertTrue(self.seen['closes_esc'])

    def test_menu_closes_with_an_option(self):
        self.assertTrue(self.seen['closes_option'])

    def test_tool_draws_a_building(self):
        self.assertEqual(self.seen['drawn'], 1)

    def test_delete_removes_the_selection(self):
        self.assertEqual(self.seen['selected'][0], 'building')
        self.assertEqual(self.seen['after_delete'], 0)

    def test_ctrl_digits_change_phase(self):
        self.assertEqual((self.seen['ctrl_2'], self.seen['ctrl_1']), ('plant', 'model'))

    def test_ctrl_tab_changes_phase(self):
        self.assertEqual(self.seen['ctrl_tab'], 'plant')

    def test_journey_logs_no_qml_warning(self):
        self.assertEqual(self.seen['warnings'], [])


cases = []


def tearDownModule():
    """Evidence for the registry: this source, these passing methods, the behaviour each one proves."""
    path = Path(__file__).resolve()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    relative = path.relative_to(ROOT).as_posix()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({'cases': [
        dict(symbol=f'NativeJourney.{case["name"]}', path=relative, sha256=digest,
             result='failed' if case['failed'] else 'passed', parity_ids=PARITY.get(case['name'], []))
        for case in cases if case['name'] in PARITY or case['failed']]}, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    unittest.main()
