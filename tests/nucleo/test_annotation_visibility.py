"""Exact occlusion intervals, including empty space inside a mesh's bounds."""
import unittest
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np

import _setup  # noqa: F401  (src on the path: this module is the first of the folder to be loaded)
from meridiana.app.view.annotation_visibility import _geometry, calculate, clip_segment, visible_intervals


class VisibilityIntervals(unittest.TestCase):
    def test_triangle_does_not_hide_the_empty_half_of_its_box(self):
        tri = np.array([[[0, 0, 0], [4, 0, 0], [0, 4, 0]]], float)
        camera = dict(origin=[0, 0, 10], forward=[0, 0, -1], ortho=True)
        self.assertEqual(visible_intervals(tri, [3, 3, -2], [3.5, 3, -2], camera), [(0., 1.)])
        self.assertEqual(visible_intervals(tri, [1, 1, -2], [2, 1, -2], camera), [])
        self.assertEqual(visible_intervals(tri, [1, 1, 0], [2, 1, 0], camera), [(0., 1.)])

    def test_partial_span_keeps_both_visible_ends(self):
        tri = np.array([[[0, 0, 0], [4, 0, 0], [0, 4, 0]]], float)
        camera = dict(origin=[0, 0, 10], forward=[0, 0, -1], ortho=True)
        parts = visible_intervals(tri, [-2, 1, -2], [6, 1, -2], camera)
        np.testing.assert_allclose(parts, [(0, .25), (.625, 1)], atol=1e-6)

    def test_perspective_cone_and_camera_side(self):
        tri = np.array([[[-1, -1, 0], [1, -1, 0], [0, 1, 0]]], float)
        camera = dict(origin=[0, 0, 10], forward=[0, 0, -1], ortho=False)
        self.assertEqual(visible_intervals(tri, [0, 0, -10], [.2, 0, -10], camera), [])
        self.assertEqual(visible_intervals(tri, [0, 0, 5], [.2, 0, 5], camera), [(0., 1.)])

    def test_context_uses_transformed_faces_and_omits_derived_proxy(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'context.npz'
            np.savez(path, vertices=[[0, 0, 0], [4, 0, 0], [0, 4, 0]], faces=[[0, 1, 2]],
                     pieces=[[0, 3, 0, 1]], colours=[[1, 1, 1, 1]])
            answer = dict(triangles=(np.zeros((3, 3)),), owners=[('building', 'proxy', 1)], table=np.zeros((0, 20)))
            request = dict(context=dict(path=str(path), hidden=[['building', 'proxy']], skip=[],
                                        position=[10, 2, 0], turn=90))
            with patch('meridiana.app.scene_job.run', return_value=answer):
                triangles = _geometry(request, SimpleNamespace(checkpoint=lambda: None))
            np.testing.assert_allclose(triangles, [[[10, 2, 0], [10, 2, -4], [6, 2, 0]]], atol=1e-8)

    def test_module_instances_are_solid_boxes_with_their_actual_transform(self):
        table = np.zeros((1, 20))
        transform = np.column_stack((np.eye(3)*.01, [1, 2, 3]))
        table[0, :12] = transform.ravel()
        answer = dict(triangles=(np.zeros((0, 3)),), owners=[], table=table)
        with patch('meridiana.app.scene_job.run', return_value=answer):
            triangles = _geometry({}, SimpleNamespace(checkpoint=lambda: None))
        self.assertEqual(triangles.shape, (12, 3, 3))
        np.testing.assert_allclose(triangles.reshape(-1, 3).min(0), [.5, 1.5, 2.5])
        np.testing.assert_allclose(triangles.reshape(-1, 3).max(0), [1.5, 2.5, 3.5])

    def test_live_pointer_uses_the_face_hit_instead_of_an_estimated_depth_plane(self):
        triangles = np.array([[[-1, -1, 0], [1, -1, 0], [0, 1, 0]]], float)
        request = dict(camera=dict(origin=[0, 0, 10], forward=[0, 0, -1], ortho=False), points=[],
                       segments=[dict(key='live', a=[0, -2, 0], b=[0, 10, 0], ray=[[0, 0, 10], [0, 0, -1]])])
        result = calculate(triangles, request)['segments']['live']
        self.assertEqual(len(result), 1)
        np.testing.assert_allclose(result[0]['b'], [0, 0, 0])

    def test_camera_frustum_clips_without_sampling(self):
        camera = dict(origin=[0, 0, 10], forward=[0, 0, -1], right=[1, 0, 0], up=[0, 1, 0],
                      ortho=False, tangent=1, aspect=1, far=100)
        parts = clip_segment(np.array([-100., 0, 0]), np.array([100., 0, 0]), camera)
        np.testing.assert_allclose(parts, [[-10, 0, 0], [10, 0, 0]])
