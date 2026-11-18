"""R365 and R389: core parity and atomic live editing, without a render surface."""
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import QApplication

from meridiana import jobs, mesh, model
from meridiana.session import ProjectSession
from meridiana.quick.backend.scene import SceneBackend
from meridiana.quick.backend.scene_geometry import instance_file


def project():
    p = model.Project(name='Quick 3D parity')
    p.buildings.append(model.Building('b1', 'Shed', [[0, 0], [40, 0], [40, 20], [0, 20]], height=9.5))
    p.subfields.append(model.SubField('s1', 'South', [[1, 1], [39, 1], [39, 19], [1, 19]],
                                       building='b1', params={'tilt': 15.0}, filled=True))
    return p


class SceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.session = ProjectSession(project())
        results, keys, _ = jobs.layout_of(self.session.project, {})
        self.session.layout_done(self.session.generation, results, keys)
        self.scene = SceneBackend(self.session, Path(self.tmp.name))
        self.addCleanup(self.scene.close)

    def test_hover_uses_core_outline_without_changing_selection_or_project(self):
        before = self.session.snapshot()
        self.scene.hover('modules',0,0,0,0)
        sfid, key = self.scene._module_keys[0]
        from meridiana import viewaids
        expected = viewaids.outline(self.session.project,self.session.good_results(),'module',sfid,key)
        np.testing.assert_allclose(self.scene.hoverData['edges'],expected)
        self.assertEqual(self.session.selection,('site',''))
        self.assertEqual(self.session.snapshot(),before)
        self.scene.hover('',-1,0,0,0)
        self.assertEqual(self.scene.hoverData['edges'],[])

    def test_selection_pivot_and_fit_use_widgets_roof_base_and_footprint(self):
        self.session.select('building','b1')
        self.assertEqual(self.scene.selectionCentre,[20,9.5,-10])
        self.assertEqual(self.scene.frameBounds(),{'centre':[20,9.5,-10],'radius':26})
        self.session.select('subfield','s1')
        self.assertEqual(self.scene.selectionCentre,[20,9.5,-10])
        self.session.select('site','')
        self.assertEqual(self.scene.selectionCentre,[])

    def test_same_buildings_and_modules_as_core(self):
        expected, table, _ = mesh.project_scene(self.session.project, self.session.good_results())
        for actual, wanted in zip(self.scene.triangles, expected, strict=True):
            np.testing.assert_array_equal(actual, wanted)
        np.testing.assert_array_equal(self.scene.module_table, table)
        self.assertGreater(len(table), 50)

    def test_native_table_contains_exact_core_bytes(self):
        table = self.scene.module_table
        path = instance_file(Path(self.tmp.name), table)
        data = path.read_bytes()
        self.assertEqual(struct.unpack('<4sHHIII', data[:20]), (b'QtIR', 1, 0, 80, 20, len(table)))
        self.assertEqual(data[20:], table.astype('<f4').tobytes())
        self.assertEqual(instance_file(Path(self.tmp.name), table), path)

    def test_r365_preview_changes_mesh_but_not_project_then_one_undo(self):
        self.session.select('building', 'b1')
        before = self.session.snapshot()
        old = self.scene.triangles[0].copy()
        self.scene.beginVertex(0, False)
        self.scene.previewVertex(2.0)
        self.assertEqual(self.session.snapshot(), before)
        self.assertFalse(np.array_equal(self.scene.triangles[0], old))
        self.scene.commitVertex(2.0)
        self.assertEqual(self.session.project.building('b1').roof.type, 'flat')     # R411 with R455: tilted, still flat
        self.assertIsNotNone(self.session.project.building('b1').roof.plane)
        self.assertAlmostEqual(self.scene.vertices[0]['point'][1], 11.5)
        self.assertEqual(self.session.undo.count(), 1)
        self.session.undo.undo()
        self.assertEqual(self.session.snapshot(), before)
        np.testing.assert_array_equal(self.scene.triangles[0], old)

    def test_cancel_preview_restores_exact_mesh(self):
        self.session.select('building', 'b1')
        old = self.scene.triangles[0].copy()
        self.scene.beginVertex(0, False)
        self.scene.previewVertex(3.0)
        self.scene.cancelEdit()
        np.testing.assert_array_equal(self.scene.triangles[0], old)
        self.assertEqual(self.session.undo.count(), 0)

    def test_rename_does_not_rebuild_geometry(self):
        before = self.scene.rebuilds
        self.session.edit('Rename', lambda p: setattr(p.buildings[0], 'name', 'Other'))
        self.assertEqual(self.scene.rebuilds, before)

    def test_invalid_height_retains_last_valid_mesh_and_reports_error(self):
        self.session.select('building', 'b1')
        self.scene.beginVertex(0, False)
        self.scene.previewVertex(2.0)
        valid = self.scene.triangles[0].copy()
        self.scene.previewVertex(-100.0)
        np.testing.assert_array_equal(self.scene.triangles[0], valid)
        self.assertTrue(self.scene.error)
        self.scene.cancelEdit()

    def test_sun_uses_core_position_and_night_disables_direct_light(self):
        self.scene.setSun(2026, 6, 21, 12.0)
        self.assertGreater(self.scene.sunData['elevation'], 40)
        self.scene.setSun(2026, 6, 21, 0.0)
        self.assertLess(self.scene.sunData['elevation'], 0)

    def test_car_dimensions_follow_core_axes(self):
        self.session.project.props.append(model.Prop('car',kind='compact',at=[12,8],rotation=0))
        self.scene.rebuild()
        corners=np.asarray(self.scene.decorations[0]['bounds'])
        np.testing.assert_allclose(corners.max(0)-corners.min(0),[4.10,1.48,1.78],atol=1e-6)
        np.testing.assert_allclose((corners.max(0)+corners.min(0))/2,[12,0.74,-8],atol=1e-6)

    def test_move_rotate_preview_and_atomic_commit(self):
        self.session.select('building','b1')
        before=self.session.snapshot()
        modules=self.scene.module_table.copy()
        self.scene.beginTransform()
        self.scene.previewTransform(3.,2.,0.)
        self.assertEqual(self.session.snapshot(),before)
        self.assertAlmostEqual(float(self.scene.triangles[0][:,0].min()),3.)
        np.testing.assert_allclose(self.scene.module_table[:,3],modules[:,3]+3)
        np.testing.assert_allclose(self.scene.module_table[:,11],modules[:,11]-2)
        self.scene.commitTransform(3.,2.,0.,False)
        self.assertEqual(self.session.project.buildings[0].footprint[0],[3.,2.])
        self.assertEqual(self.session.undo.count(),1)
        self.session.undo.undo()
        self.assertEqual(self.session.snapshot(),before)
        self.scene.beginTransform()
        self.scene.commitTransform(0.,0.,90.,False)
        self.assertNotEqual(self.session.snapshot(),before)
        self.session.undo.undo()
        self.assertEqual(self.session.snapshot(),before)

    def test_vertex_actions_flat_to_manual_and_multi_selection(self):
        self.session.select('building','b1')
        self.scene.beginVertex(0,False)
        self.scene.vertexAction('pitched')
        self.assertEqual(self.session.project.buildings[0].roof.type,'free')
        self.scene.selectVertices([0,1],False)
        self.assertEqual(sum(v['selected'] for v in self.scene.vertices),2)


if __name__ == '__main__':
    unittest.main()
