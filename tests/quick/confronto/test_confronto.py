"""The giro of giro.py on the Quick window, offscreen, on a copy of Rho: the comparison of 05/11/2026 with the
Widgets window, kept for what it proves of the Quick once the Widgets went (r30, phase B).

Long (the year of Rho is computed, about 5 minutes): run only when asked,
    MERIDIANA_CONFRONTO=1 python -m unittest quick.confronto.test_confronto
The window runs in a process of its own (giro.py sets the platform and a temporary profile before Meridiana is
imported). A method marked expectedFailure names a regression of the Quick window in
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
        run = subprocess.Popen([sys.executable, str(HERE/'giro.py'), 'quick', str(out), *STEPS], cwd=ROOT, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        run.wait(timeout=2400)
        records = json.loads((out/'giro-quick.json').read_text(encoding='utf8'))
        cls.steps = {r['passo']: r for r in records}

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def facts(self, step):
        record = self.steps[step]
        self.assertEqual(record['esito_driver'], 'ok', record.get('traceback'))
        return record['fatti']

    def test_the_project_opens_with_its_numbers(self):
        self.assertTrue(self.facts('apertura')['conteggi'])

    def test_the_year_is_computed(self):
        year = self.facts('calcolo_f5')['anno_dopo_f5']
        self.assertTrue(year['calcolato'])
        self.assertGreater(year['energy_kwh'], 0)

    def test_f5_computes_again(self):
        self.assertTrue(self.facts('calcolo_f5')['f5_parte'])

    def test_an_old_year_is_said_and_ctrl_z_brings_it_back(self):
        facts = self.facts('non_aggiornato')
        self.assertTrue(facts['stale_nucleo'])
        self.assertIn('production', facts['fasi_segnate'])
        self.assertTrue(facts['ctrl_z_torna'])

    def test_several_buildings_chosen_in_the_left_panel(self):
        self.assertEqual(sorted(self.facts('selezione_multipla')['insieme']), ['b1', 'b2'])

    def test_ctrl_c_ctrl_v_copies_a_building(self):
        facts = self.facts('copia_incolla')
        self.assertEqual(facts['edifici_sottocampi_dopo'][0], facts['edifici_sottocampi_prima'][0]+1, facts)

    # reproduced in one run of two (05/11/2026): «Da controllare» drawn over the row under it after «Da correggere»
    # was closed; docs/quick/confronto-widgets-quick-20261105.md, row 50
    @unittest.expectedFailure
    def test_the_checks_rows_never_overlap(self):
        """Daniel, 05/11/2026: opening and closing the groups drew the headers over the rows, rows cut in half, a
        header twice. Every group opened and closed twice, by level and by area: no row over another, no header
        twice, no row without height."""
        for step in ('verifiche_gruppi', 'verifiche_aree'):
            facts = self.facts(step)
            self.assertTrue(facts['passi'], step)
            for p in facts['passi']:
                self.assertNotIn('clic', p, p)
                self.assertEqual(p['sovrapposte'], [], (step, p['gruppo'], p['giro']))
                self.assertEqual(p['intestazioni_doppie'], [], (step, p['gruppo'], p['giro']))
                self.assertEqual(p['altezza_zero'], [], (step, p['gruppo'], p['giro']))

    # Quick: a project opened from the command line (the launcher) has no path; Ctrl+S opens «Save as» (05/11/2026)
    @unittest.expectedFailure
    def test_ctrl_s_writes_the_file_opened(self):
        """Ctrl+S, or the command Save when the synthetic key did not write."""
        facts = self.facts('salva')
        self.assertTrue(facts['scritto'] or facts.get('scritto_col_comando'), facts)

    def test_a_revision_is_a_new_file(self):
        facts = self.facts('salva_revisione')
        self.assertTrue(facts['file_nuovi'] or facts.get('file_nuovi_col_comando'))

    def test_the_report_is_written(self):
        facts = self.facts('relazione_pdf')
        self.assertTrue(facts['scritto'])
        self.assertGreater(facts['pagine'], 3)


if __name__ == '__main__':
    unittest.main()
