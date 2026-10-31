"""Dedicated modelling commands use the real project, geometry and undo path."""
import unittest

import _setup
from meridiana import canopies, model

setUpModule = _setup.keep_global_state


class CanopyWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_canopy_is_placed_as_a_structure_and_on_a_canopy_lays_its_modules(self):
        # R281: «Parking canopy…» places the structure alone; «On a canopy» lays the modules, each one step
        win = _setup.window(self, model.Project())
        self.assertFalse(win.commands['carport'].icon().isNull())
        self.assertFalse(win.commands['layout_east_west'].icon().isNull())
        self.assertIn('canopy_layout', win.commands)
        win.place_carport(canopies.Spec(rows=2))
        win._points_picked('carport', [[20, 30]])
        self.assertEqual(win.project.subfields, [])
        (b,) = win.project.buildings
        self.assertIsNotNone(b.canopy)
        self.assertEqual(tuple(win.selection), ("building", b.id))
        self.assertTrue([o for o in win.project.obstacle_prisms() if o["kind"] == "column"])
        ids = win.lay_on_canopy(b.id, portrait=False, gap=0.03, overhang=0.1, edge=0.2)
        self.assertEqual(len(ids), 2)
        self.assertTrue(all(win.project.fill(sf).modules for sf in win.project.subfields))
        self.assertEqual({sf.params['gap'] for sf in win.project.subfields}, {0.03})
        win.undo.undo()
        self.assertEqual(win.project.subfields, [])
        self.assertEqual(len(win.project.buildings), 1)
        win.undo.undo()
        self.assertEqual(win.project.buildings, [])
        win.undo.redo()
        win.undo.redo()
        self.assertEqual(len(win.project.subfields), 2)
        self.assertEqual(win.lay_on_canopy('nothing'), [])                   # refused, said, nothing changed
        self.assertEqual(len(win.project.subfields), 2)

    def test_the_command_on_a_canopy_proposes_the_canopy_selected(self):
        from PySide6.QtWidgets import QDialogButtonBox

        from meridiana.ui.canopy_dialog import CanopyLayoutDialog
        p = model.Project()
        canopies.add(p, canopies.Spec(), (0, 0))
        second = canopies.add(p, canopies.Spec(rows=2), (30, 0))
        dialog = CanopyLayoutDialog(p, second)
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(dialog.values()['bid'], second)
        self.assertEqual(dialog.canopy.count(), 2)
        empty = CanopyLayoutDialog(model.Project())
        self.addCleanup(empty.deleteLater)
        ok = empty.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
        self.assertFalse(ok.isEnabled())                                     # no canopy, nothing to lay

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
        self.assertEqual(len(dialog.ring), 4)
        # R281: the structure, never a module; the columns proposed from the spaces, then chosen
        kinds = [f.kind for f in dialog.preview.faces]
        self.assertEqual(kinds.count('plane'), 2)
        self.assertGreater(kinds.count('structure'), 0)
        self.assertEqual(dialog.spec().columns, 0)
        self.assertIn('3', dialog.columns.specialValueText())
        dialog.pillars.setCurrentIndex(1)
        dialog.columns.setValue(5)
        self.assertEqual((dialog.spec().pillars, dialog.spec().columns), ('two_rows', 5))
        self.assertIn('10', dialog.summary.text())
