"""R711 (20/11/2026): what one change of the plant makes the pages do again. The Impianto inspector's cards are made of
the plant's `dataChanged` (one emission made 1141 items again for 80 strings, 1 s offscreen) and the Production
inspector's form of its editor's `sectionsChanged` (the whole form): one emission of the first per change, none of
the second unless the fields themselves change. Measured with tools/fasi_probe.py --count."""
import copy
import time
import unittest

import _setup  # noqa: F401  isolate the user's profile before loading Qt
from _fixtures import capannone, inverter_record
from PySide6.QtWidgets import QApplication

from meridiana.app import jobs
from meridiana.app.session import ProjectSession
from meridiana.gui.backend.charts_editor import ResultEditor
from meridiana.gui.backend.plant import PlantBackend


class OneChangeOneEmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.project = capannone()
        cls.results, cls.keys, _ = jobs.layout_of(cls.project)

    def setUp(self):
        self.session = ProjectSession(copy.deepcopy(self.project))
        self.session.results, self.session.layout_keys = self.results, self.keys
        self.backend = PlantBackend(self.session)
        self.addCleanup(self.backend.close)
        self.editor = ResultEditor(self.session, 'production')
        self.counts = {}
        for name in ('dataChanged', 'changed'):
            getattr(self.backend, name).connect(lambda *_a, k='plant.' + name: self.count(k))
        self.editor.sectionsChanged.connect(lambda: self.count('production.sectionsChanged'))
        self.wait()

    def count(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1

    def wait(self):
        until = time.monotonic() + 30
        while self.backend.busy and time.monotonic() < until:
            self.app.processEvents()
            time.sleep(.005)  # wait: a breath between two looks at the condition, so the workers' threads run
        for _ in range(20):                         # the notifications of the turn after the job
            self.app.processEvents()
            time.sleep(.005)  # wait: a breath between two looks at the condition, so the workers' threads run
        self.assertFalse(self.backend.busy, self.backend.message)

    def test_each_change_of_the_plant_emits_its_data_once_and_leaves_the_production_form(self):
        modules = [f's1/{m.key}' for m in self.results['s1'].modules][:20]
        for label, change in (('an inverter added', lambda: self.backend.addInverter(inverter_record())),
                              ('a string drawn', lambda: self.backend.commitString(1, 1, modules, -1)),
                              ('the DC/AC ratio', lambda: self.backend.setEnergy('dc_ac_ratio', 1.2))):
            with self.subTest(change=label):
                self.counts.clear()
                change()
                self.wait()
                self.assertEqual(self.counts.get('plant.dataChanged'), 1, self.counts)
                self.assertNotIn('production.sectionsChanged', self.counts)      # the same fields: not made again

    def test_the_production_form_is_made_again_only_when_its_fields_change(self):
        self.counts.clear()
        self.editor.refresh()
        self.assertNotIn('production.sectionsChanged', self.counts)
        self.editor._shape = ()                     # as when the strings' fields arrive
        self.editor.refresh()
        self.assertEqual(self.counts.get('production.sectionsChanged'), 1)


if __name__ == '__main__':
    unittest.main()
