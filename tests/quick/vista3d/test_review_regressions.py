"""R356/R365/R389: regressions found by independent review, without a render surface."""
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

import numpy as np
from PySide6.QtWidgets import QApplication

import _setup
from meridiana import jobs, model, roof_vertices, sun
from meridiana.quick.backend.scene import SceneBackend
from meridiana.session import ProjectSession

setUpModule = _setup.keep_global_state


class ReviewRegressionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.session = ProjectSession(model.Project())
        self.scene = SceneBackend(self.session, Path(directory.name))
        self.addCleanup(self.scene.close)

    def building(self, pitched=False):
        building = model.Building('b', 'Roof', [[0, 0], [40, 0], [40, 20], [0, 20]], height=9.5)
        if pitched:
            building.roof = model.Roof(type='gable', tilt=20)
        self.session.edit('Add roof', lambda p: p.buildings.append(building))
        self.session.select('building', 'b')
        return building

    def chosen_at_different_heights(self):
        handles = roof_vertices.handles(self.session.project.buildings[0])
        second = next(i for i, hand in enumerate(handles) if abs(hand.z - handles[0].z) > 0.1)
        self.scene.beginVertex(0, False)
        self.scene.beginVertex(second, True)
        return [handles[0], handles[second]]

    def assert_corner_heights(self, handles, wanted):
        building = self.session.project.buildings[0]
        actual = building.solved().heights
        for hand, height in zip(handles, wanted, strict=True):
            pitch, corner = hand.corners[0]
            self.assertAlmostEqual(actual[pitch][corner], height, places=3)

    def test_shift_adds_ctrl_toggles_and_the_arrows_raise_them_together_r356(self):
        # R356 (Daniel 08/11/2026) with the rule of the selection (R529): Shift+click adds, Ctrl+click adds or takes
        # away; the arrows of the view (Viewport.qml) raise them together by beginVertex + commitVertex, one Undo
        self.building(pitched=True)
        handles = roof_vertices.handles(self.session.project.buildings[0])
        self.scene.beginVertex(0, False)
        self.scene.cancelEdit()
        self.scene.beginVertex(1, False, True)
        self.scene.cancelEdit()
        self.scene.beginVertex(1, False, True)
        self.assertEqual(self.scene._chosen, [0, 1])          # Shift adds; once in, it stays
        self.scene.cancelEdit()
        self.scene.beginVertex(1, True)
        self.assertEqual(self.scene._chosen, [0])             # Ctrl takes away
        self.scene.cancelEdit()
        self.scene.beginVertex(1, True)
        count = self.session.undo.count()
        self.scene.beginVertex(0, False)                       # what the arrow does
        self.scene.commitVertex(0.1)
        self.assertEqual(self.session.undo.count(), count + 1)
        self.assert_corner_heights([handles[0], handles[1]], [handles[0].z + 0.1, handles[1].z + 0.1])

    def test_absolute_height_sets_each_selected_corner_and_undo_restores(self):
        self.building(pitched=True)
        before = self.session.snapshot()
        handles = self.chosen_at_different_heights()
        count = self.session.undo.count()
        self.scene.vertexHeight('15')
        self.assert_corner_heights(handles, [15, 15])
        self.assertEqual(self.session.undo.count(), count + 1)
        self.scene.undo()
        self.assertEqual(self.session.snapshot(), before)

    def test_relative_height_preserves_difference_between_selected_corners(self):
        self.building(pitched=True)
        handles = self.chosen_at_different_heights()
        self.scene.vertexHeight('+2,5')
        self.assert_corner_heights(handles, [round(hand.z + 2.5, 3) for hand in handles])

    def test_undo_topology_change_leaves_next_vertex_edit_valid(self):
        self.building()
        self.session.edit('Gable roof', lambda p: setattr(p.buildings[0], 'roof', model.Roof(type='gable', tilt=20)))
        self.assertEqual(len(self.scene.vertices), 6)
        self.scene.selectVertices([0, 2, 5], False)
        self.scene.undo()
        self.assertEqual(len(self.scene.vertices), 4)
        self.scene.beginVertex(0, False)
        self.scene.commitVertex(1)
        # R411: a flat roof tilts by its corner; the handle of that corner is where it was asked. R455: it stays flat.
        self.assertEqual(self.session.project.buildings[0].roof.type, 'flat')
        self.assertIsNotNone(self.session.project.buildings[0].roof.plane)
        self.assertAlmostEqual(self.scene.vertices[0]['point'][1], 10.5)

    def assert_sun_matches_site(self):
        data = self.scene.sunData
        when = datetime(data['year'],data['month'],data['day'],tzinfo=ZoneInfo('Europe/Rome')) + timedelta(hours=data['hour'])
        site = self.session.project.site
        expected = sun.position(site.lat, site.lon, when)
        self.assertAlmostEqual(data['elevation'], expected.apparent, places=8)
        self.assertAlmostEqual(data['bearing'], expected.bearing, places=8)

    def test_sun_follows_site_edit_and_undo(self):
        before = dict(self.scene.sunData)
        self.session.edit('Latitude', lambda p: setattr(p.site, 'lat', 0))
        self.assertNotEqual(self.scene.sunData['elevation'], before['elevation'])
        self.assert_sun_matches_site()
        self.scene.undo()
        self.assert_sun_matches_site()
        self.assertEqual(self.scene.sunData, before)

    def test_sun_follows_replacement_project(self):
        project = model.Project()
        project.site.lat, project.site.lon = 35, 15
        self.session.take(project, None, True)
        self.assert_sun_matches_site()

    def test_ground_only_modules_are_inside_fit_bounds(self):
        project = model.Project()
        project.subfields.append(model.SubField('s', 'Ground',
            [[1000, 1000], [1010, 1000], [1010, 1010], [1000, 1010]], filled=True))
        self.session.take(project, None, True)
        results, keys, _ = jobs.layout_of(project, {})
        self.session.layout_done(self.session.generation, results, keys)
        self.assertGreater(self.scene.moduleCount, 0)
        self.assertEqual(len(self.scene.triangles[0]), 0)
        bounds = self.scene.bounds
        self.assertGreater(bounds['centre'][0], 1000)
        self.assertLess(bounds['centre'][2], -1000)
        transforms = self.scene.module_table[:, :12].reshape(-1, 3, 4)
        cube = np.array([[x, y, z] for x in (-50, 50) for y in (-50, 50) for z in (-50, 50)])
        for transform in transforms:
            corners = cube @ transform[:, :3].T + transform[:, 3]
            distance = np.linalg.norm(corners - np.asarray(bounds['centre']), axis=1)
            self.assertTrue(np.all(distance < bounds['radius']))

    def test_new_project_resets_previous_bounds(self):
        empty_bounds = dict(self.scene.bounds)
        self.building()
        self.assertNotEqual(self.scene.bounds, empty_bounds)
        self.session.new()
        self.assertEqual(self.scene.bounds, empty_bounds)

    def test_selection_change_cancels_vertex_preview_and_late_release(self):
        self.building()
        before = self.session.snapshot()
        original_mesh = self.scene.triangles[0].copy()
        count = self.session.undo.count()
        self.scene.beginVertex(0, False)
        self.scene.previewVertex(3)
        self.assertFalse(np.array_equal(self.scene.triangles[0], original_mesh))
        self.session.select('site', '')
        np.testing.assert_array_equal(self.scene.triangles[0], original_mesh)
        self.scene.commitVertex(3)
        self.assertEqual(self.session.snapshot(), before)
        self.assertEqual(self.session.undo.count(), count)

    def test_selection_change_cancels_transform_preview_and_late_release(self):
        self.building()
        before = self.session.snapshot()
        original_mesh = self.scene.triangles[0].copy()
        count = self.session.undo.count()
        self.scene.beginTransform()
        self.scene.previewTransform(5, 2, 0)
        self.assertFalse(np.array_equal(self.scene.triangles[0], original_mesh))
        self.session.select('site', '')
        np.testing.assert_array_equal(self.scene.triangles[0], original_mesh)
        self.scene.commitTransform(5, 2, 0, False)
        self.assertEqual(self.session.snapshot(), before)
        self.assertEqual(self.session.undo.count(), count)

    def test_refused_weld_reports_error_without_mutation_or_exception(self):
        self.building(pitched=True)
        before = self.session.snapshot()
        count = self.session.undo.count()
        handles = roof_vertices.handles(self.session.project.buildings[0])
        first_pitch = handles[0].corners[0][0]
        other = next(i for i, hand in enumerate(handles[1:], 1)
                     if hand.corners[0][0] == first_pitch)
        self.scene.beginVertex(0, False)
        self.scene.vertexAction('weld')
        self.scene.beginVertex(other, False)
        self.assertTrue(self.scene.error)
        self.assertEqual(self.session.snapshot(), before)
        self.assertEqual(self.session.undo.count(), count)


if __name__ == '__main__':
    unittest.main()
