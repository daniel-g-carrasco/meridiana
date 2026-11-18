"""R389: actual Widgets and Quick file handlers in both directions."""
import unittest
from unittest.mock import patch

import _setup
from meridiana import config, model
from meridiana.quick.backend.files import FilesBackend
from meridiana.session import ProjectSession
from quick.parity.differential import canonical_project, compare

setUpModule = _setup.keep_global_state


class WidgetsFilesParityTest(unittest.TestCase):
    def test_old_open_save_new_open_save_old_open_all_frozen_projects(self):
        from quick.parity.formats import frozen_cases
        from PySide6.QtWidgets import QFileDialog
        win = _setup.window(self, cfg=config.Config(background='none', network_pvgis=False,
                                                   assistant=False, check_updates=False))
        backend = FilesBackend(ProjectSession(), config.Config(), self.paths)
        self.addCleanup(backend.close)
        destination = self.paths.data / 'parity'
        destination.mkdir(parents=True, exist_ok=True)
        for case in frozen_cases():
            if case.kind != 'project':
                continue
            for suffix in ('.mer', '.meridiana'):
                with self.subTest(file=case.path.name, suffix=suffix):
                    self.assertTrue(win.open_path(case.path))
                    if win.project.job_id and not win.registry.job(win.project.job_id):
                        client = win.registry.create_client('Fixture client')
                        win.registry.create_job(f'{len(win.registry.list_jobs()) + 1:05d}', 'Fixture job',
                                                client['id'], job_id=win.project.job_id)
                    # _save keeps the selected extension, unlike _save_as which defaults to SUFFIX.
                    legacy = destination / ('widgets-' + case.path.stem + suffix)
                    win.path = legacy
                    self.assertTrue(win._save())
                    self.assertTrue(backend.openPath(str(legacy)), backend.error)
                    self.assertEqual([], compare(canonical_project(win.project), canonical_project(backend.session.project)))
                    current = destination / ('quick-' + case.path.stem + suffix)
                    self.assertTrue(backend.saveAs(str(current)), backend.error)
                    self.assertTrue(win.open_path(current))
                    self.assertEqual([], compare(canonical_project(win.project), canonical_project(backend.session.project)))
        # Also use the real Save As handler with the native chooser's returned path.
        target = destination / 'native-choice.mer'
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(target), '')):
            self.assertTrue(win._save_as())
        self.assertTrue(backend.openPath(str(target)))
        self.assertEqual([], compare(canonical_project(win.project), canonical_project(backend.session.project)))
        # None of the immutable source fixtures were opened for writing.
        self.assertEqual(model.FORMAT_VERSION, backend.session.project.to_json()['version'])


if __name__ == '__main__':
    unittest.main()
