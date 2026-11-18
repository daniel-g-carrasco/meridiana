"""Real worker exports: commit complete files and leave existing files on cancel."""
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QObject, QProcess

from _fixtures import capannone
from meridiana.quick.app import create_app
from meridiana.quick.backend.shell import ShellController
from meridiana.quick.backend.shell_compute import ShellBridge
from meridiana.quick.backend.shell_tasks import ShellTasks
from quick.gestures import wait_for


class TasksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary.name)
        self.bridge = ShellBridge(capannone(), self.folder)
        self.engine = QObject()
        self.tasks = ShellTasks(SimpleNamespace(engine=self.engine, bridge=self.bridge,
                                               shell=ShellController(self.bridge)))

    def tearDown(self):
        self.tasks.close()
        self.bridge.close()
        self.temporary.cleanup()

    def test_ifc_is_committed_and_opens_as_a_complete_model(self):
        import ifcopenshell
        target = self.folder / 'model.ifc'
        self.tasks.exportTo('ifc', str(target))
        wait_for(lambda: not self.tasks.busy, seconds=60)
        self.assertTrue(target.exists(), self.tasks.message)
        model = ifcopenshell.open(str(target))
        self.assertTrue(model.by_type('IfcBuilding'))
        self.assertTrue(model.by_type('IfcSolarDevice'))
        self.assertTrue(all(module.Representation for module in model.by_type('IfcSolarDevice')))
        self.assertEqual(list(self.folder.glob('*.part')), [])

    def test_cancel_preserves_target_and_unrelated_part_file(self):
        target = self.folder / 'model.ifc'
        target.write_bytes(b'previous user file')
        unrelated = self.folder / 'model.ifc.part'
        unrelated.write_bytes(b'not this job')
        self.tasks.exportTo('ifc', str(target))
        wait_for(lambda: self.tasks.process.state() == QProcess.ProcessState.Running)
        start = time.perf_counter()
        self.tasks.cancel()
        self.assertLess(time.perf_counter()-start, .75)
        self.assertEqual(target.read_bytes(), b'previous user file')
        self.assertEqual(unrelated.read_bytes(), b'not this job')
        self.assertEqual(list(self.folder.glob('*.part')), [unrelated])

    def test_failed_csv_preserves_target_and_reports_reason(self):
        target = self.folder / 'hours.csv'
        target.write_bytes(b'previous user file')
        self.tasks.exportTo('csv', str(target))
        wait_for(lambda: not self.tasks.busy, seconds=60)
        self.assertEqual(target.read_bytes(), b'previous user file')
        self.assertIn('Error', self.tasks.message)
        self.assertEqual(list(self.folder.glob('*.part')), [])

    def test_csv_uses_the_session_hourly_register(self):
        import pandas as pd
        from meridiana.ui.report import write_register_csv
        from meridiana import i18n
        i18n.setup('it')
        index = pd.date_range('2025-01-01', periods=2, freq='h', tz='Europe/Rome')
        hourly = pd.DataFrame({'ghi': [0, 900], 'poa': [0, 1000], 'temp_air': [10, 20],
                              'e_kwh': [0, 4]}, index=index)
        self.bridge.session.energy['sim'] = SimpleNamespace(hourly=hourly, inverters=[])
        expected, actual = self.folder / 'expected.csv', self.folder / 'actual.csv'
        write_register_csv(self.bridge.session.project, self.bridge.session.energy, expected)
        self.tasks.exportTo('csv', str(actual))
        wait_for(lambda: not self.tasks.busy, seconds=60)
        self.assertTrue(actual.exists(), self.tasks.message)
        self.assertEqual(actual.read_bytes(), expected.read_bytes())
        self.assertEqual(list(self.folder.glob('*.part')), [])
