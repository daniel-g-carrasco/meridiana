"""Modelling journeys on a hidden desktop: what the collaudo found, and what must keep matching the Widgets.

A method marked expectedFailure names a defect of docs/quick/collaudo/difetti-modellazione.csv: when the correction
arrives the mark must go, because unittest reports an unexpected success. Run with
    python -m unittest quick.percorsi.test_modellazione
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from quick.percorsi.modellazione_nascosto import run


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class ModellingJourneys(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='meridiana-modellazione-', ignore_cleanup_errors=True)
        cls.out = Path(cls.folder.name)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def journey(self, engine, name):
        code, text = run(engine, name, self.out)
        self.assertEqual(code, 0, text)
        self.assertNotIn('Traceback', text, text)
        return json.loads((self.out/f'{name}-{engine}.json').read_text(encoding='utf8'))

    def log(self, engine, name):
        return (self.out/f'{name}-{engine}.log').read_text(encoding='utf8')

    # M01, corrected
    def test_ctrl_z_undoes_in_the_model_phase(self):
        self.journey('quick', 'scorciatoie')
        self.assertIn('model, Ctrl+Z numero 1: stato cambiato True', self.log('quick', 'scorciatoie'))

    # M02, corrected
    def test_r_gives_a_pitch_by_corners(self):
        steps = self.journey('quick', 'falda5')
        self.assertEqual(steps[-1]['buildings'][0]['pitches'][0]['corners'], 5)

    # M03, corrected
    def test_strings_by_hand_take_the_next_free_input(self):
        steps = self.journey('quick', 'ingressi')
        self.assertEqual(steps[-1]['strings']['targets'], ['1/1', '1/2', '1/3'])

    def test_automatic_proposal_and_year_match_the_widgets(self):
        quick, widgets = self.journey('quick', 'proposta')[-1], self.journey('widgets', 'proposta')[-1]
        for key in ('modules', 'kwp', 'checks'):
            self.assertEqual(quick[key], widgets[key], key)
        self.assertEqual(quick['strings']['sizes'], widgets['strings']['sizes'])
        self.assertEqual(quick['strings']['targets'], widgets['strings']['targets'])
        # The outlines differ by the rounding of a pixel: see the report, 0.005 % in the proof run.
        self.assertAlmostEqual(quick['energy_kwh']['kwh'], widgets['energy_kwh']['kwh'], delta=widgets['energy_kwh']['kwh']*.001)


if __name__ == '__main__':
    unittest.main()
