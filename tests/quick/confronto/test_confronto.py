"""The comparison of 05/11/2026 as tests: the giro of giro.py on both windows, offscreen, on a copy of Rho.

Long (the year of Rho is computed by both windows, about 5 minutes each): run only when asked,
    MERIDIANA_CONFRONTO=1 python -m unittest quick.confronto.test_confronto
Each window runs in a process of its own (giro.py sets the platform and a temporary profile before Meridiana is
imported), the two at the same time. A method marked expectedFailure names a regression of the Quick window in
docs/quick/confronto-widgets-quick-20261105.md: when it is corrected the mark must go (unittest says «unexpected
success»).
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STEPS = ['apertura', 'calcolo_f5', 'non_aggiornato', 'selezione_multipla', 'copia_incolla', 'verifiche',
         'verifiche_gruppi', 'verifiche_aree', 'salva', 'salva_revisione', 'relazione_pdf']


@unittest.skipUnless(os.environ.get('MERIDIANA_CONFRONTO'), 'long: MERIDIANA_CONFRONTO=1 to run it')
class Confronto(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='meridiana-confronto-', ignore_cleanup_errors=True)
        out = Path(cls.folder.name)
        env = dict(os.environ, PYTHONUTF8='1', QSG_RENDER_LOOP='basic',
                   PYTHONPATH=os.pathsep.join((str(ROOT/'tests'), str(ROOT/'src'))))
        env.pop('QT_QPA_PLATFORM', None)            # giro.py gives the offscreen platform a screen of its own
        runs = [subprocess.Popen([sys.executable, str(HERE/'giro.py'), engine, str(out), *STEPS], cwd=ROOT, env=env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for engine in ('widgets', 'quick')]
        for run in runs:
            run.wait(timeout=2400)
        cls.steps = {}
        for engine in ('widgets', 'quick'):
            records = json.loads((out/f'giro-{engine}.json').read_text(encoding='utf8'))
            cls.steps[engine] = {r['passo']: r for r in records}

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def facts(self, engine, step):
        record = self.steps[engine][step]
        self.assertEqual(record['esito_driver'], 'ok', record.get('traceback'))
        return record['fatti']

    def test_the_project_opens_with_the_same_numbers(self):
        self.assertEqual(self.facts('quick', 'apertura')['conteggi'], self.facts('widgets', 'apertura')['conteggi'])

    def test_the_year_is_the_same(self):
        w, q = self.facts('widgets', 'calcolo_f5')['anno_dopo_f5'], self.facts('quick', 'calcolo_f5')['anno_dopo_f5']
        self.assertTrue(w['calcolato'] and q['calcolato'])
        self.assertAlmostEqual(q['energy_kwh'], w['energy_kwh'], delta=w['energy_kwh']*1e-6)

    def test_f5_computes_again(self):
        self.assertTrue(self.facts('quick', 'calcolo_f5')['f5_parte'])

    def test_an_old_year_is_said_and_ctrl_z_brings_it_back(self):
        for engine in ('widgets', 'quick'):
            facts = self.facts(engine, 'non_aggiornato')
            self.assertTrue(facts['stale_nucleo'], engine)
            self.assertIn('production', facts['fasi_segnate'], engine)
            self.assertTrue(facts['ctrl_z_torna'], engine)

    def test_several_buildings_chosen_in_the_left_panel(self):
        self.assertEqual(sorted(self.facts('quick', 'selezione_multipla')['insieme']), ['b1', 'b2'])

    def test_ctrl_c_ctrl_v_copies_a_building(self):
        facts = self.facts('quick', 'copia_incolla')
        self.assertEqual(facts['edifici_sottocampi_dopo'][0], facts['edifici_sottocampi_prima'][0]+1, facts)

    # reproduced in one run of two (05/11/2026): «Da controllare» drawn over the row under it after «Da correggere»
    # was closed; docs/quick/confronto-widgets-quick-20261105.md, row 50
    @unittest.expectedFailure
    def test_the_checks_rows_never_overlap(self):
        """Daniel, 05/11/2026: opening and closing the groups drew the headers over the rows, rows cut in half, a
        header twice. Every group opened and closed twice, by level and by area: no row over another, no header
        twice, no row without height."""
        for step in ('verifiche_gruppi', 'verifiche_aree'):
            facts = self.facts('quick', step)
            self.assertTrue(facts['passi'], step)
            for p in facts['passi']:
                self.assertNotIn('clic', p, p)
                self.assertEqual(p['sovrapposte'], [], (step, p['gruppo'], p['giro']))
                self.assertEqual(p['intestazioni_doppie'], [], (step, p['gruppo'], p['giro']))
                self.assertEqual(p['altezza_zero'], [], (step, p['gruppo'], p['giro']))

    # Quick: a project opened from the command line (the launcher) has no path; Ctrl+S opens «Save as» (05/11/2026)
    @unittest.expectedFailure
    def test_ctrl_s_writes_the_file_opened(self):
        """Ctrl+S, or the command Save when the synthetic key did not write (the Widgets write nothing on Ctrl+S
        offscreen with the project unchanged; the command does)."""
        for engine in ('widgets', 'quick'):
            facts = self.facts(engine, 'salva')
            self.assertTrue(facts['scritto'] or facts.get('scritto_col_comando'), (engine, facts))

    def test_a_revision_is_a_new_file(self):
        for engine in ('widgets', 'quick'):
            facts = self.facts(engine, 'salva_revisione')
            self.assertTrue(facts['file_nuovi'] or facts.get('file_nuovi_col_comando'), engine)

    def test_the_report_is_written(self):
        for engine in ('widgets', 'quick'):
            facts = self.facts(engine, 'relazione_pdf')
            self.assertTrue(facts['scritto'], engine)
            self.assertGreater(facts['pagine'], 3, engine)


if __name__ == '__main__':
    unittest.main()
