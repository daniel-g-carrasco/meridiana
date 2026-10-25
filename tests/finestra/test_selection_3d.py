"""The selection shared by the plan and the 3D view through the window (study 12, T1-T3; R29): a click in 3D selects
what the plan would, the selection tinted and outlined in 3D, what is under the pointer outlined lighter and never
twice, F frames the selection in both views; a selection changes only the colours of the 3D table. The cube and the
outline alone are in widget/test_viewcube.py. PySide6 and a display (offscreen will do)."""

import math
import unittest
from unittest import mock

import numpy as np

import _setup
from _fixtures import capannone

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class SelectionIn3D(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone())
        self.sid = self.win.project.subfields[0].id
        self.b = self.win.view3d.backend
        self.b.reduced_motion = True

    def test_the_selection_is_one_for_both_views_tinted_and_outlined_and_framed_by_f(self):
        from meridiana import mesh
        from meridiana.ui.plan import to_scene
        win, v = self.win, self.win.view3d
        # a click in 3D selects what the plan would select at that point
        v.pointPicked.emit(20.0, 10.0)                      # in the middle of the sub-field
        self.assertEqual(win.selection[0], "subfield")
        v.pointPicked.emit(0.3, 19.7)                       # the corner of the roof, outside the area
        self.assertEqual(win.selection[0], "building")
        v.pointPicked.emit(math.nan, math.nan)
        self.assertEqual(win.selection, ("site", ""))
        # the plan's selection tinted in 3D, and outlined
        seen = []
        real = mesh.building_triangles
        with mock.patch.object(mesh, "building_triangles", lambda *a: (seen.append(a[2]), real(*a))[1]):
            win._select("building", win.project.buildings[0].id)
        self.assertNotEqual(seen[-1]["wall"], mesh.WALL)
        self.assertGreater(len(v.outline["select"]), 0)
        # what is under the pointer in 3D: outlined lighter, and the selection is not outlined twice
        win._select("site", "")
        v.hoverPicked.emit(("module", 0))
        sfid, key = win.module_index[0]
        self.assertEqual(win.hovered_3d, ("module", sfid, key))
        self.assertGreater(len(v.outline["hover"]), 0)
        v.hoverPicked.emit(("point", 20.0, 10.0))                   # the middle of the sub-field
        self.assertEqual(win.hovered_3d, ("subfield", self.sid, ""))
        win._select("subfield", self.sid)                          # selected: outlined as the selection only
        self.assertGreater(len(v.outline["select"]), 0)
        self.assertEqual(len(v.outline["hover"]), 0)
        v.hoverPicked.emit(("",))
        self.assertEqual(win.hovered_3d, ("", "", ""))
        # F frames the selection in both views
        win._fit()
        plan = win.plan
        shown = plan.mapToScene(plan.viewport().rect()).boundingRect()
        self.assertTrue(shown.contains(to_scene(20.0, 10.0)))
        self.assertLess(shown.width(), 120.0)
        self.assertTrue(np.allclose(self.b.camera.target, win._centre_3d("subfield", self.sid)))

    def test_a_selection_changes_only_the_colours_of_the_3d_table(self):
        """The instance table of a sub-field is built once per layout; a click recolours it (task 18c, step 7)."""
        from meridiana import mesh, view_colours
        tables = []
        real = self.win.view3d.show_scene
        with mock.patch.object(self.win.view3d, "show_scene", lambda scene, table, **k: (tables.append(table),
                                                                                           real(scene, table, **k))[1]), \
                mock.patch.object(mesh, "module_table", wraps=mesh.module_table) as built:
            self.win._select("subfield", self.sid)
            r = self.win.results[self.sid]
            key = r.modules[3].key
            self.win.plan.selected_module = (self.sid, key)
            self.win._module_clicked(self.sid, key)
            self.win._select("site", "")
        self.assertEqual(built.call_count, 0)                   # the table of the layout in hand, kept
        field, module, none = tables
        for t in (field, module, none):
            self.assertEqual(t.shape, (r.count, 20))
            self.assertTrue(np.array_equal(t[:, :12], none[:, :12]) and np.array_equal(t[:, 15:], none[:, 15:]))
        self.assertFalse(np.array_equal(field[:, 12:15], none[:, 12:15]))          # the sub-field tinted
        np.testing.assert_allclose(module[3, 12:15], mesh.rgb(view_colours.kind_colour("module")), rtol=0, atol=1e-6)   # R67
        self.assertTrue(np.array_equal(module[:3, 12:15], none[:3, 12:15]))
        self.assertEqual(len(self.win.module_index), r.count)
        self.assertEqual(self.win.module_index[3], (self.sid, key))


if __name__ == "__main__":
    unittest.main()
