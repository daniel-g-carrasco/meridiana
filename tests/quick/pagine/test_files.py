"""R389: real File commands preserve the Widgets project and config contracts."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import _setup
from meridiana import config, model
from meridiana.paths import Paths
from meridiana.session import ProjectSession
from quick.parity.differential import canonical_project, compare

setUpModule = _setup.keep_global_state


class FileCommandsTest(unittest.TestCase):
    def test_installer_continuation_waits_for_dirty_project_choice(self):
        called = []
        self.session.edit('Rename', lambda p: setattr(p, 'name', 'Unsaved'))
        self.backend._guard('callback', lambda: called.append('start'))
        self.assertTrue(self.backend.confirmation)
        self.assertEqual([], called)
        self.backend.resolveChanges('cancel')
        self.assertEqual([], called)
        self.backend._guard('callback', lambda: called.append('start'))
        self.backend.resolveChanges('discard')
        self.assertEqual(['start'], called)

    def setUp(self):
        from meridiana.quick.backend.files import FilesBackend
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.paths = Paths(*(root / name for name in ('config', 'state', 'data', 'cache')))
        self.session = ProjectSession()
        self.cfg = config.Config(extra={'future_setting': [1, 2]})
        self.backend = FilesBackend(self.session, self.cfg, self.paths)
        self.addCleanup(self.backend.close)
        self.errors = []
        self.backend.failed.connect(self.errors.append)

    def test_frozen_project_roundtrips_both_extensions(self):
        from quick.parity.formats import frozen_cases
        for case in frozen_cases():
            if case.kind != 'project':
                continue
            with self.subTest(case=case.path.name):
                self.assertTrue(self.backend.openPath(str(case.path)), self.backend.error)
                # Saving populates portable resources, including an empty weather map.
                # Compare the actual legacy session save, without dropping that field.
                reference = ProjectSession(model.Project.load(case.path)[0])
                for suffix in ('.mer', '.meridiana'):
                    target = Path(self.tmp.name) / (case.path.stem + suffix)
                    expected_path = Path(self.tmp.name) / ('reference-' + case.path.stem + suffix)
                    reference.save(expected_path, self.paths.cache)
                    original = canonical_project(model.Project.load(expected_path, self.paths.cache)[0])
                    self.assertTrue(self.backend.saveAs(str(target)), self.backend.error)
                    loaded, _notice = model.Project.load(target, self.paths.cache)
                    self.assertEqual([], compare(original, canonical_project(loaded)))

    def test_save_atomic_backup_revision_and_config(self):
        path = Path(self.tmp.name) / 'project.mer'
        self.assertTrue(self.backend.saveAs(str(path)))
        previous = path.read_bytes()
        self.session.edit('rename', lambda p: setattr(p, 'name', 'Changed'))
        self.assertTrue(self.backend.save())
        self.assertEqual(previous, path.with_suffix('.mer.bak').read_bytes())
        saved = path.read_bytes()
        self.assertTrue(self.backend.saveRevision())
        self.assertEqual(saved, path.read_bytes())
        self.assertEqual('project_R01.mer', self.session.path.name)
        reloaded = config.load(self.paths.config_file)
        self.assertEqual(str(self.session.path), reloaded.recent[0])
        self.assertEqual([1, 2], reloaded.extra['future_setting'])

    def test_failed_save_does_not_move_path_or_mark_clean(self):
        self.session.edit('rename', lambda p: setattr(p, 'name', 'Unsaved'))
        with patch.object(model.Project, 'save', side_effect=OSError('disk full')):
            self.assertFalse(self.backend.saveAs(str(Path(self.tmp.name) / 'bad.mer')))
        self.assertIsNone(self.session.path)
        self.assertTrue(self.session.dirty())
        self.assertIn('disk full', self.errors[-1])

    def test_failed_open_retains_project_and_recent(self):
        before = self.session.snapshot()
        path = Path(self.tmp.name) / 'broken.meridiana'
        path.write_text('{ broken', encoding='utf-8')
        self.assertFalse(self.backend.openPath(str(path)))
        self.assertEqual(before, self.session.snapshot())
        self.assertEqual([], self.cfg.recent)
        self.assertTrue(self.errors)

    def test_dirty_open_cancel_discard_and_save_before_open(self):
        target = Path(self.tmp.name) / 'other.meridiana'
        model.Project(name='Other').save(target)
        self.session.edit('rename', lambda p: setattr(p, 'name', 'Keep me'))
        self.backend.openChosen(str(target))
        self.assertTrue(self.backend.confirmation)
        self.backend.resolveChanges('cancel')
        self.assertEqual('Keep me', self.session.project.name)
        self.backend.openChosen(str(target))
        self.backend.resolveChanges('save')
        self.assertEqual('Keep me', self.session.project.name)
        saved = Path(self.tmp.name) / 'saved.mer'
        self.backend.fileChosen('save', str(saved))
        self.assertEqual('Keep me', model.Project.load(saved)[0].name)
        self.assertEqual('Other', self.session.project.name)

    def test_cancel_save_picker_cancels_pending_replacement(self):
        self.session.edit('rename', lambda p: setattr(p, 'name', 'Keep me'))
        self.backend.request('new')
        self.backend.resolveChanges('save')
        self.backend.cancelFileDialog()
        self.assertEqual('open', self.backend.section)
        self.assertEqual('Keep me', self.session.project.name)
        self.assertFalse(self.backend.confirmation)

    def test_recent_filters_missing_and_deduplicates_eight(self):
        for n in range(10):
            self.assertTrue(self.backend.saveAs(str(Path(self.tmp.name) / f'p{n}.mer')))
        self.assertEqual(8, len(self.cfg.recent))
        self.assertTrue(self.backend.save())
        self.assertEqual(8, len(set(self.cfg.recent)))
        self.cfg.recent.append(str(Path(self.tmp.name) / 'gone.mer'))
        self.backend.refresh()
        self.assertEqual(8, len(self.backend.recent))

    def test_file_actions_match_widgets_sections(self):
        from unittest.mock import patch
        from meridiana.quick.backend.files import page_sections
        # gettext's empty msgid is the catalogue header, never visible copy.
        with patch('meridiana.quick.backend.files._', side_effect=lambda s: s or 'Project-Id-Version: meridiana'):
            self.assertTrue(all(t['description'] == '' for t in page_sections()['catalogues']['tiles']))
        actions = {tile['action'] for group in self.backend.sections.values()
                   for tile in group.get('tiles', [])}
        self.assertTrue({'open', 'import_pvsyst', 'save', 'save_as', 'save_revision',
                         'export_report', 'export_ifc', 'copy_notes', 'manual', 'shortcuts',
                         'guided_tour', 'report_bug', 'about', 'catalog_module',
                         'catalog_inverter', 'catalog_battery'} <= actions)

    def test_url_is_decoded_without_changing_spaces_or_unicode(self):
        from PySide6.QtCore import QUrl
        path = Path(self.tmp.name) / 'Prova città e tetto.meridiana'
        self.assertTrue(self.backend.saveAs(QUrl.fromLocalFile(str(path)).toString()))
        self.assertTrue(path.exists())
        self.assertEqual(path, self.session.path)

    def test_new_page_remembers_discard_until_project_is_created(self):
        self.session.edit('rename', lambda p: setattr(p, 'name', 'Old unsaved'))
        self.backend.request('new')
        self.backend.resolveChanges('discard')
        self.assertEqual('new', self.backend.section)
        self.backend.createProject({'name': 'New', 'site': model.Site(45, 9)})
        self.assertFalse(self.backend.confirmation)
        self.assertEqual('New', self.session.project.name)

    def test_new_confirmation_is_needed_again_if_project_changed_while_page_open(self):
        self.session.edit('rename', lambda p: setattr(p, 'name', 'Old unsaved'))
        self.backend.request('new')
        self.backend.resolveChanges('discard')
        self.session.edit('rename', lambda p: setattr(p, 'name', 'New edit'))
        self.backend.createProject({'name': 'New'})
        self.assertTrue(self.backend.confirmation)
        self.assertEqual('New edit', self.session.project.name)


if __name__ == '__main__':
    unittest.main()
