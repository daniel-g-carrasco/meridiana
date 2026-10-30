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

    def test_east_west_command_is_a_tool_that_lays_pairs_along_a_line_in_one_step(self):
        # R279: the command no longer turns the whole sub-field; it draws pairs as Row draws a row
        p = model.Project()
        p.subfields = [model.SubField(id='s1', name='Ground', ring=[[0, 0], [20, 0], [20, 20], [0, 20]])]
        win = _setup.window(self, p)
        win.commands['layout_east_west'].trigger()
        self.assertEqual(win.plan.tool, 'east_west')
        self.assertTrue(win.commands['layout_east_west'].isChecked())
        self.assertNotIn('mounting', win.project.subfields[0].params)
        win._row_drawn([2.0, 2.0], [2.0, 12.0])
        sf = win.project.subfields[0]
        self.assertEqual(sf.params['mounting'], 'east_west')
        directions = {round(pm.azimuth, 3) for pm in win.project.fill(sf).modules}
        self.assertEqual(len(directions), 2)
        win.undo.undo()
        self.assertNotIn('mounting', win.project.subfields[0].params)

    def test_dialog_exposes_dimensions_and_two_row_preview(self):
        from meridiana.ui.canopy_dialog import CanopyDialog
        dialog = CanopyDialog()
        self.addCleanup(dialog.deleteLater)
        dialog.rows.setCurrentIndex(1)
        dialog.fields['turn'].setValue(30)
        self.assertEqual(dialog.spec().rows, 2)
        self.assertEqual(len(dialog.preview.ring), 4)
