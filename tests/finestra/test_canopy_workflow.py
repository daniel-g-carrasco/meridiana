"""Dedicated modelling commands use the real project, geometry and undo path."""
import unittest

import _setup
from meridiana import canopies, model

setUpModule = _setup.keep_global_state


class CanopyWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_place_two_slopes_is_one_undo_step_and_both_are_filled(self):
        win = _setup.window(self, model.Project())
        self.assertFalse(win.commands['carport'].icon().isNull())
        self.assertFalse(win.commands['layout_east_west'].icon().isNull())
        win.place_carport(canopies.Spec(rows=2))
        win._points_picked('carport', [[20, 30]])
        self.assertEqual(len(win.project.subfields), 2)
        self.assertTrue(all(win.project.fill(sf).modules for sf in win.project.subfields))
        win.undo.undo()
        self.assertFalse(win.project.subfields)
        win.undo.redo()
        self.assertEqual(len(win.project.subfields), 2)

    def test_east_west_command_preserves_manual_rows_and_undoes_automatic_conversion(self):
        p = model.Project()
        p.subfields = [model.SubField(id='s1', name='Ground', ring=[[0, 0], [20, 0], [20, 20], [0, 20]])]
        win = _setup.window(self, p)
        win._select('subfield', 's1')
        win.commands['layout_east_west'].trigger()
        sf = win.project.subfields[0]
        self.assertEqual(sf.params['mounting'], 'east_west')
        directions = {round(pm.azimuth, 3) for pm in win.project.fill(sf).modules}
        self.assertEqual(len(directions), 2)
        win.undo.undo()
        self.assertNotIn('mounting', win.project.subfields[0].params)
        win.project.subfields[0].manual = True
        win._east_west()
        self.assertNotIn('mounting', win.project.subfields[0].params)

    def test_dialog_exposes_dimensions_and_two_row_preview(self):
        from meridiana.ui.canopy_dialog import CanopyDialog
        dialog = CanopyDialog()
        self.addCleanup(dialog.deleteLater)
        dialog.rows.setCurrentIndex(1)
        dialog.fields['turn'].setValue(30)
        self.assertEqual(dialog.spec().rows, 2)
        self.assertEqual(len(dialog.preview.ring), 4)
