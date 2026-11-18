"""R426, R427, R432 in the real window, with native messages on a separate desktop, on a synthetic project.

Run with `python -m unittest quick.percorsi.test_native_selezione`. The hover needs the correction of r14-correzioni
(Meridio's layer took it): without it those methods skip and say so; proved on a trial merge of the two branches."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from quick.percorsi.selezione_journey import JOURNEY, MANY, SCALED, synthetic, three_buildings

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT/'tools/quick_native_input.py'


def _run(*args, timeout, env=None):
    environment = dict(os.environ, PYTHONUTF8='1', PYTHONPATH=os.pathsep.join((str(ROOT/'tests'), str(ROOT/'src'))),
                       **(env or {}))
    with tempfile.TemporaryFile() as output:     # a pipe would stay open in the program left running
        code = subprocess.run([sys.executable, str(TOOL), *args], stdout=output, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, env=environment, timeout=timeout, cwd=ROOT).returncode
        output.seek(0)
        return code, output.read().decode('utf-8', 'replace')


def journey(script_text, desktop, size, env=None, keep=None, make=synthetic):
    with tempfile.TemporaryDirectory(prefix='meridiana-selezione-', ignore_cleanup_errors=True) as ctl:
        project = Path(ctl)/'prova.meridiana'
        make(project)
        code, text = _run('start', '--engine', 'quick', '--ctl', ctl, '--project', str(project),
                          '--width', str(size[0]), '--height', str(size[1]), '--timeout', '120', '--desktop', desktop,
                          timeout=140, env=env)
        if code:
            raise AssertionError(text)
        script = Path(ctl)/'journey.py'
        script.write_text(script_text, encoding='utf-8')
        code, text = _run('run', '--ctl', ctl, str(script), '--timeout', '280', timeout=300, env=env)
        _run('run', '--ctl', ctl, '--stop', timeout=30, env=env)
        if os.environ.get('MERIDIANA_NATIVE_DUMP'):
            Path(os.environ['MERIDIANA_NATIVE_DUMP']).write_text(text, encoding='utf-8')
        if keep:
            keep.mkdir(parents=True, exist_ok=True)
            for picture in Path(ctl).glob('*.png'):
                (keep/picture.name).write_bytes(picture.read_bytes())
        try:
            return json.loads(text.strip().splitlines()[-1])
        except (IndexError, ValueError):
            raise AssertionError(text) from None


def corners_hold(case, seen):
    case.assertEqual(seen['corner_select'], ['subfield', 's2'])
    case.assertEqual(seen['corners_with_a_module'], 4)
    case.assertEqual(len(seen['corners']), 3)
    zooms = [row['zoom'] for row in seen['corners']]
    case.assertGreater(zooms[1], zooms[0])
    case.assertLess(zooms[2], zooms[0])
    for row in seen['corners']:
        with case.subTest(zoom=row['zoom']):
            case.assertTrue(row['moved'])
            case.assertTrue(row['others_still'])
            case.assertEqual(row['selection'], ['subfield', 's2'])
            case.assertEqual(row['swept'], 0)
    case.assertTrue(seen['corner_click_changes_nothing'])


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class Journey(unittest.TestCase):
    seen = None

    @classmethod
    def setUpClass(cls):
        cls.seen = journey(JOURNEY, 'meridiana-selezione-test', (1600, 960),
                           keep=Path(os.environ['MERIDIANA_PHOTOS']) if os.environ.get('MERIDIANA_PHOTOS') else None)

    def need_hover(self):
        if not self.seen['hover_works']:
            self.skipTest('hover blocked by Meridio\'s layer: see r14-correzioni')

    def test_the_phase_and_no_qml_warning(self):
        self.assertEqual(self.seen['phase'], 'plant')
        self.assertEqual(self.seen['warnings'], [])
        self.assertEqual(self.seen['warnings_head'], [])

    def test_corners_win_over_the_modules_at_every_zoom(self):
        corners_hold(self, self.seen)

    def test_the_corner_shows_it_is_the_one(self):
        self.need_hover()
        self.assertEqual(self.seen['grip_width_away'], 10)
        self.assertGreater(self.seen['grip_width_near'], 10)
        self.assertEqual(self.seen['grip_width_back'], 10)
        self.assertFalse(self.seen['hover_on_corner'])
        self.assertTrue(self.seen['hover_on_module'])
        self.assertIn('Trascina', self.seen['corner_hint'])
        self.assertTrue(self.seen['corner_area_cursor'])

    def test_the_hover_lights_only_what_a_click_would_take(self):
        self.need_hover()
        self.assertFalse(self.seen['plant_hover_roof'])
        self.assertEqual(self.seen['model_hover_module'], 'building')
        self.assertFalse(self.seen['anchored_hover'])

    def test_astride_it_moves_passes_and_says_so(self):
        self.assertEqual(self.seen['astride_selected'], ['subfield', 's1'])
        self.assertEqual(self.seen['move_tool'], 'move')
        self.assertEqual(self.seen['move_error'], '')
        self.assertGreater(self.seen['moved_by'], 1.5)      # asked 2,5 m: the snaps take what they take
        self.assertTrue(self.seen['pitch_changed'])
        self.assertIn('piano', self.seen['move_hint'])

    def test_split_undo_redo_together_and_reopened(self):
        self.assertTrue(self.seen['split_in_menu'])
        self.assertEqual(self.seen['after_split'], 3)
        self.assertEqual(len(self.seen['split_groups']), 1)
        self.assertTrue(self.seen['split_groups'][0])
        self.assertEqual(len(self.seen['split_pitches']), 2)
        self.assertEqual(self.seen['after_split_undo'], 2)
        self.assertEqual(self.seen['after_split_redo'], 3)
        self.assertEqual(len(set(self.seen['parts_moved'])), 1)
        self.assertLess(self.seen['parts_moved'][0], -1.0)
        self.assertTrue(self.seen['reopened_groups'])
        self.assertTrue(self.seen['reopened_rings'])

    def test_in_plant_a_roof_and_an_exclusion_are_not_taken_and_it_says_where(self):
        self.assertEqual(self.seen['plant_click_roof'], ['site', ''])
        self.assertIn('Modellazione', self.seen['plant_click_roof_hint'])
        self.assertEqual(self.seen['plant_click_exclusion'], ['site', ''])

    def test_in_modelling_modules_do_not_catch(self):
        self.assertEqual(self.seen['phase_model'], 'model')
        self.assertEqual(self.seen['model_click_module'], ['building', 'b1'])
        self.assertEqual(self.seen['model_module_key'], ['', ''])

    def test_the_click_stays_on_what_is_selected_until_esc(self):
        self.assertEqual(self.seen['anchored'], ['building', 'b1'])
        self.assertEqual(self.seen['esc_lets_go'][0], 'site')
        self.assertEqual(self.seen['after_esc_click'], ['exclusion', 'e1'])

    def test_tab_walks_what_lies_under(self):
        walk = self.seen['tab_walk']
        self.assertEqual({tuple(x)[0] for x in walk}, {'exclusion', 'pitch', 'building'})
        self.assertIn('Tab', self.seen['tab_hint'])
        self.assertNotEqual(self.seen['shift_tab'], walk[-1])

    def test_copy_and_paste_in_modelling(self):
        self.assertEqual(self.seen['paste_tool_model'], 'paste')
        self.assertEqual(self.seen['exclusions_after_paste'], 2)

    def test_copy_and_paste_a_sub_field_with_a_preview(self):
        self.assertEqual(self.seen['copied'], 'subfield')
        self.assertEqual(self.seen['paste_tool'], 'paste')
        self.assertEqual(self.seen['paste_rings'], 1)
        self.assertGreater(self.seen['paste_preview_drawn'], 0)

    def test_the_preview_follows_the_pointer_and_says_where_it_falls(self):
        self.need_hover()
        self.assertIn('falda', self.seen['paste_hint'])

    def test_a_paste_off_the_roof_is_refused_and_said(self):
        self.assertTrue(self.seen['paste_refused'])
        self.assertEqual(self.seen['paste_refused_count'], 0)
        self.assertIn('Capannone', self.seen['paste_refused_said'])

    def test_a_paste_takes_the_plane_and_keeps_the_rest_in_no_string(self):
        self.assertEqual(self.seen['pasted'], 1)
        self.assertTrue(self.seen['pasted_on_north'])
        self.assertEqual(self.seen['pasted_undo_steps'], 1)
        self.assertTrue(self.seen['pasted_keeps_module'])
        self.assertGreater(self.seen['pasted_modules'] or 0, 0)
        self.assertFalse(self.seen['pasted_in_a_string'])
        self.assertIn('stringa', self.seen['pasted_hint'])

    def test_cut_and_paste_are_one_undo(self):
        self.assertTrue(self.seen['cut_gone'])
        self.assertEqual(self.seen['cut_pasted'], 1)
        self.assertEqual(self.seen['cut_paste_undo_steps'], 1)
        self.assertTrue(self.seen['cut_paste_undone'])


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class ManyInTheTree(unittest.TestCase):
    def test_more_buildings_chosen_in_the_tree_change_together(self):
        seen = journey(MANY, 'meridiana-selezione-test3', (1600, 960), make=three_buildings,
                       keep=Path(os.environ['MERIDIANA_PHOTOS']) if os.environ.get('MERIDIANA_PHOTOS') else None)
        self.assertEqual(seen['one'], ['building', 'b1'])
        self.assertEqual(seen['ctrl'], ['b1', 'b2'])
        self.assertEqual(seen['lit_two'], ['b1', 'b2'])
        self.assertEqual(seen['shift'], ['b2', 'b3'])
        self.assertEqual(seen['all'], ['b1', 'b2', 'b3'])
        self.assertEqual(seen['lit_all'], ['b1', 'b2', 'b3'])
        self.assertEqual(seen['grips'], 0)
        self.assertEqual(seen['rows_selected'], 3)
        self.assertEqual(seen['height_text'], '')
        self.assertEqual(seen['height_placeholder'], 'valori diversi')
        self.assertEqual(seen['box_state_before'], 0)
        self.assertEqual(seen['subject'], [True, True, True])
        self.assertEqual(seen['undo_steps'], 1)
        self.assertEqual(seen['box_state_after'], 2)
        self.assertEqual(seen['undone'], [False, False, False])
        self.assertEqual(seen['other_kind'], [['subfield', 's1'], []])
        self.assertEqual(seen['plain'], [['building', 'b2'], []])
        self.assertEqual(seen['warnings'], [])


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class AtScaleTwo(unittest.TestCase):
    def test_the_corners_at_scale_two(self):
        seen = journey(SCALED, 'meridiana-selezione-test2', (1000, 700), env={'QT_SCALE_FACTOR': '2'})
        # twice the system's own: 4 on Daniel's screen at 200 % (07/11/2026, the test asked 2 and failed there), 2 at
        # 100 %. The system's DPI as a DPI-aware thread reads it (an unaware one is always told 96)
        import ctypes
        user32 = ctypes.windll.user32
        user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        before = user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))      # per monitor, version 2
        try:
            system = user32.GetDpiForSystem() / 96
        finally:
            user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(before))
        self.assertEqual(seen['dpr'], 2.0 * system)
        corners_hold(self, seen)
        self.assertEqual(seen['warnings'], [])


if __name__ == '__main__':
    unittest.main()
