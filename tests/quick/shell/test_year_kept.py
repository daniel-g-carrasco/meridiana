"""R437: the year survives save, close and open; its state is one, said everywhere; an undo brings it back at once;
the report asks before going out with old numbers and remembers what it was made from."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

from _fixtures import capannone
from meridiana import i18n, model, year_store
from meridiana.quick.app import create_app
from meridiana.quick.backend import shell_compute
from meridiana.quick.backend.report import ReportBackend
from meridiana.quick.backend.shell import ShellController
from meridiana.quick.backend.shell_compute import ShellBridge
from meridiana.quick.sample import recorded_weather
from meridiana.paths import Paths


class YearKept(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        i18n.setup('it')
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.cache = Path(cls.folder.name)/'cache'
        cls.cache.mkdir()
        cls.file = Path(cls.folder.name)/'prova.meridiana'
        project = capannone()
        recorded_weather(project, cls.cache)
        cls.first = ShellBridge(project, cls.cache)
        cls.first.session.path = cls.file
        cls.first.recompute()
        cls.wait(cls.first)
        cls.kwh = cls.first.session.energy['sim'].energy_kwh
        cls.first.session.save(cls.file, cls.cache)

    @classmethod
    def tearDownClass(cls):
        cls.first.close()
        cls.folder.cleanup()

    @classmethod
    def wait(cls, bridge, seconds=240):
        end = time.perf_counter() + seconds
        while time.perf_counter() < end and bridge.busy:
            cls.app.processEvents()
            time.sleep(.01)
        for _turn in range(50):
            cls.app.processEvents()
            time.sleep(.002)
        assert not bridge.busy

    def reopen(self):
        project, _notice = model.Project.load(self.file, self.cache)
        bridge = ShellBridge(project, self.cache)
        bridge.session.path = self.file
        self.addCleanup(bridge.close)
        return bridge

    def test_the_year_is_kept_with_a_size_that_is_said(self):
        fingerprint = self.first.session.year_fingerprint()
        path = year_store.path_of(self.cache, fingerprint)
        self.assertTrue(path.is_file())
        print(f'R437: year kept, {path.stat().st_size} bytes, project file {self.file.stat().st_size} bytes')

    def test_opening_again_the_numbers_are_there_at_once(self):
        bridge = self.reopen()
        self.assertEqual(bridge.session.energy, {})
        with mock.patch.object(shell_compute, 'Worker', side_effect=AssertionError('nothing to compute')):
            bridge.recompute()
        self.assertFalse(bridge._busy)      # the checks of the year may still be on their way in their thread
        self.assertIsNone(bridge._job)
        self.assertEqual(bridge.session.energy['sim'].energy_kwh, self.kwh)
        self.assertFalse(bridge.session.energy_outdated())
        self.assertTrue(bridge.session.results)

    def test_opening_through_the_session_finds_it_too(self):
        bridge = self.reopen()
        bridge.recompute()
        bridge.session.open(self.file, self.cache)
        self.assertEqual(bridge.session.energy, {})
        self.assertTrue(bridge.timer.isActive())
        with mock.patch.object(shell_compute, 'Worker', side_effect=AssertionError('nothing to compute')):
            bridge.timer.stop()
            bridge._launch()
        self.assertEqual(bridge.session.energy['sim'].energy_kwh, self.kwh)

    def test_a_change_marks_it_with_what_changed_and_undo_clears_it(self):
        bridge = self.reopen()
        bridge.recompute()
        shell = ShellController(bridge)
        self.assertEqual(shell.yearState['state'], 'current')
        kept = bridge.session.energy['sim']
        session = bridge.session
        session.edit('Losses', lambda p: p.energy.setdefault('losses', {}).__setitem__('soiling', 7.5))
        bridge.timer.stop()
        state = shell.yearState
        self.assertEqual(state['state'], 'stale')
        self.assertIn('perdite', state['text'])
        self.assertIs(session.energy['sim'], kept)      # R435: the numbers of before stay, marked; never zeros
        session.undo.undo()
        bridge.timer.stop()
        self.assertEqual(shell.yearState['state'], 'current')
        self.assertIs(session.energy['sim'], kept)

    def test_a_change_of_the_modules_says_so_and_a_file_of_before_opens_the_same(self):
        bridge = self.reopen()
        bridge.recompute()
        session = bridge.session
        session.edit('Tilt', lambda p: p.subfields[0].params.__setitem__('tilt', 22.0))
        bridge.timer.stop()
        self.assertTrue(session.energy_outdated())
        self.assertIn('la posa dei moduli', session.year_changes())
        saved = json.loads(self.file.read_text(encoding='utf-8')) if self.file.read_bytes()[:1] == b'{' else None
        if saved is not None:
            self.assertNotIn('sim', saved)

    def test_a_year_damaged_is_as_one_not_there(self):
        bridge = self.reopen()
        fingerprint = bridge.session.year_fingerprint()
        key = bridge.session.energy_key(bridge.session._expected_keys())
        self.assertIsNotNone(year_store.read(self.cache, fingerprint, key))
        self.assertIsNone(year_store.read(self.cache, fingerprint, key + 'x'))
        other = Path(self.folder.name)/'other'
        (other/year_store.FOLDER).mkdir(parents=True)
        year_store.path_of(other, fingerprint).write_bytes(b'not a year')
        self.assertIsNone(year_store.read(other, fingerprint, key))

    def report(self, bridge):
        paths = Paths(*(Path(self.folder.name)/'profile'/name for name in ('config', 'state', 'data', 'cache')))
        backend = ReportBackend(bridge.session, None, paths)
        self.addCleanup(backend.close)
        return backend

    def test_the_report_asks_before_going_out_with_old_numbers(self):
        bridge = self.reopen()
        bridge.recompute()
        report = self.report(bridge)
        self.assertFalse(report.exportState['stale'])
        asked, commands = [], []
        report.recomputeAsked.connect(lambda: asked.append(True))
        report.commandRequested.connect(commands.append)
        bridge.session.edit('Losses', lambda p: p.energy.setdefault('losses', {}).__setitem__('soiling', 9.0))
        bridge.timer.stop()
        self.assertTrue(report.exportState['stale'])
        with mock.patch.object(ReportBackend, '_start') as start:
            report.exportPdf(str(Path(self.folder.name)/'relazione.pdf'))
            self.assertEqual(asked, [True])
            start.assert_not_called()
            report.recomputeThenExport()
            self.assertEqual(commands, ['compute'])
            bridge.session.undo.undo()      # the numbers answer again: it goes
            bridge.timer.stop()
            for _turn in range(20):
                self.app.processEvents()
            start.assert_called_once()
            self.assertEqual(start.call_args[0][0], 'export')

    def test_the_report_exported_is_said_to_no_longer_answer(self):
        bridge = self.reopen()
        bridge.recompute()
        report = self.report(bridge)
        report._remember_export(Path('x.pdf'), bridge.session.year_fingerprint(), '05/11/2026')
        self.assertFalse(report.exportState['behind'])
        self.assertIn('05/11/2026', report.exportState['exported'])
        bridge.session.edit('Losses', lambda p: p.energy.setdefault('losses', {}).__setitem__('soiling', 9.0))
        bridge.timer.stop()
        self.assertTrue(report.exportState['behind'])
        bridge.session.undo.undo()
        bridge.timer.stop()
        self.assertFalse(report.exportState['behind'])

    def test_the_pdf_carries_its_mark(self):
        from pypdf import PdfReader, PdfWriter
        from meridiana.quick.backend.report_worker import mark_pdf
        path = Path(self.folder.name)/'marked.pdf'
        writer = PdfWriter()
        writer.add_blank_page(100, 100)
        with path.open('wb') as stream:
            writer.write(stream)
        mark_pdf(path, 'abc123', '05/11/2026')
        info = PdfReader(str(path)).metadata
        self.assertEqual(info['/MeridianaFingerprint'], 'abc123')
        self.assertEqual(info['/MeridianaExported'], '05/11/2026')


if __name__ == '__main__':
    unittest.main()
