"""Old answers are rejected; camera motion retains clipping, scene changes discard it."""
from types import SimpleNamespace
import unittest

import _setup
from PySide6.QtCore import QObject, Signal

from meridiana.core.model.model import Project
from meridiana.gui.backend.scene_measure import SceneMeasure

setUpModule = _setup.keep_global_state


class Scene(QObject):
    sceneChanged = Signal()


class AnnotationJob(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.scene = Scene()
        self.scene.scenes = SimpleNamespace(center=SimpleNamespace(submit=self.submit))
        self.scene.session = SimpleNamespace(project=Project(), photo=lambda: {}, layout_keys={}, good_results=lambda: {})
        self.scene.contextModels = []
        self.measure = SceneMeasure(self.scene, SimpleNamespace(register=lambda *_: None))

    def submit(self, kind, payload, **callbacks):
        self.requests.append((kind, payload, callbacks))

    def ask(self, z):
        self.measure.visibility(dict(camera=dict(origin=[0, 0, z], forward=[0, 0, -1], ortho=False),
                                     segments=[], points=[]))

    def test_late_answer_is_rejected_and_camera_motion_retains_the_last_clipping(self):
        self.ask(10)
        self.ask(20)
        old = dict(segments={'old': []}, points={})
        current = dict(segments={'current': []}, points={})
        self.requests[0][2]['on_done'](old, False)
        self.assertEqual(self.measure.annotationData['segments'], {})
        self.requests[1][2]['on_done'](current, False)
        self.assertEqual(self.measure.annotationData, current)
        self.measure.invalidateVisibility()
        self.assertEqual(self.measure.annotationData, current)
        self.ask(30)
        self.assertEqual(self.measure.annotationData, current)
        self.requests[1][2]['on_done'](old, False)
        self.assertEqual(self.measure.annotationData, current)

    def test_new_scene_rejects_the_old_scene_answer(self):
        self.ask(10)
        self.scene.sceneChanged.emit()
        self.requests[0][2]['on_done'](dict(segments={'old': []}, points={}), False)
        self.assertEqual(self.measure.annotationData['segments'], {})
        self.assertFalse(self.measure.annotationPending)
