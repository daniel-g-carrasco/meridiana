"""Virtual placement areas can be previewed and confirmed without any building or automatic layout."""
import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import RHO, exported
from meridiana import ifc_read, model

setUpModule = _setup.keep_global_state


class SurfaceImport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_surface_only_model_is_previewed_then_added_as_one_undo_step(self):
        from PySide6.QtWidgets import QLabel
        from meridiana.ui.ifc_import import IfcImportDialog
        with tempfile.TemporaryDirectory() as folder:
            p = model.Project(site=model.Site(**RHO))
            p.subfields = [model.SubField(id='s1', name='Virtual canopy reference',
                ring=[[0, 0], [12, 0], [12, 8], [0, 8]],
                support=model.SupportPlane(z0=4, tilt=19, azimuth=37))]
            path, _summary, _results = exported(p, Path(folder), 'surfaces.ifc')
            found = ifc_read.read(path)
            win = _setup.window(self, model.Project(site=model.Site(**RHO)))
            dialog = IfcImportDialog(found, win.project, path.name)
            self.addCleanup(_setup.dispose, dialog)
            self.assertEqual(dialog.plan().buildings, [])
            self.assertEqual(len(dialog.plan().supports), 1)
            self.assertTrue(dialog.buttons.button(dialog.buttons.StandardButton.Ok).isEnabled())
            self.assertTrue(any('surfaces.ifc' in label.text() and 'normal (' in label.text()
                                for label in dialog.lists.findChildren(QLabel)))
            self.assertEqual(win.project.subfields, [])
            self.assertFalse(dialog.preview.grab().isNull())
            win._ifc_read(found, str(path), confirm=lambda _found: dialog.plan())
            self.assertEqual(len(win.project.subfields), 1)
            self.assertFalse(win.project.subfields[0].filled)
            self.assertTrue(win.project.subfields[0].support.enabled)
            win.undo.undo()
            self.assertEqual(win.project.subfields, [])


if __name__ == '__main__':
    unittest.main()
