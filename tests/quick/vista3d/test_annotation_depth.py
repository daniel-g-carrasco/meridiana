"""R692: rendered measurements follow the visibility of the actual scene solids."""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QObject

import _setup
from meridiana.app.view.measure_tool import Measure, Probe
from meridiana.core.model.model import Building, Project
from quick.vista3d._fidelity_support import js, pixels, settle

setUpModule = _setup.keep_global_state


class AnnotationDepth(unittest.TestCase):
    def test_hidden_partial_and_front_spans_by_pixels(self):
        from meridiana.gui.application import QuickWindow, create_app
        app = create_app()
        project = Project(name='Visibility fixture')
        project.buildings.append(Building(id='b', name='Block', height=6, footprint=[[0, 0], [24, 0], [0, 12]]))
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        host = QuickWindow(project, Path(tmp.name), real_views=True, theme={'reducedMotion': True})
        self.addCleanup(host.close)
        host.window.resize(1100, 800)
        host.window.show()
        host.window.setProperty('viewMode', '3d')
        self.assertTrue(_setup.wait_until(app, lambda: host.window.findChild(QObject, 'viewport3d') is not None))
        view = host.window.findChild(QObject, 'viewport3d')
        self.assertTrue(_setup.wait_until(app, lambda: len(host.scene.triangles[0]) > 0 and not host.scene.drawing))
        js(view, 'userMoved=true; cameraState={position:[12,3,40],target:[12,3,-6],rotation:[1,0,0,0],fov:60,ortho:false}')
        settle(app, 1)
        layer = view.findChild(QObject, 'sceneMeasures')

        def visual_items(item):
            yield item
            for child in item.childItems():
                yield from visual_items(child)

        def picture():
            settle(app, .2)
            grab = view.grabToImage()
            ready = []
            grab.ready.connect(lambda: ready.append(True))
            self.assertTrue(_setup.wait_until(app, lambda: ready))
            return pixels(grab.image())

        ids = iter(range(1, 10))

        def measure(a, b):
            host.measure.tool.measures[:] = [Measure(next(ids), 'distance', (Probe(a), Probe(b)))]
            host.measure._changed()
            settle(app, .2)
            self.assertTrue(_setup.wait_until(app, lambda: not view.property('sceneMeasure').property('annotationPending'), 30))

        baseline = picture()
        measure((8, 15, 3), (16, 15, 3))
        hidden = picture()
        import numpy as np
        self.assertEqual(int(np.abs(hidden.astype(int)-baseline.astype(int)).max()), 0,
                         'A measurement wholly behind the building changed the rendered view')
        self.assertFalse(any(i.isVisible() for i in visual_items(layer)
                             if i.objectName() == 'measurePill'))
        measure((-35, 15, 3), (16, 15, 3))
        partial = picture()
        pills = [pill for pill in visual_items(layer)
                 if pill.objectName() == 'measurePill' and pill.isVisible()]
        self.assertTrue(pills, js(layer, 'JSON.stringify({width:width,height:height,labels:labels,places:places,fixed:fixed})'))
        for pill in pills:
            self.assertEqual(pill.property('mode'), 'on')
        self.assertGreater(int(np.count_nonzero(np.any(partial != baseline, axis=2))), 40)
        measure((8, -5, 3), (16, -5, 3))
        front = picture()
        self.assertGreater(int(np.count_nonzero(np.any(front != baseline, axis=2))), 40)
        # The unoccupied half of a triangular building's bounding box stays visible.
        host.measure.tool.measures.clear()
        host.measure._changed()
        js(view, 'cameraState={position:[12,40,-6],target:[12,0,-6],rotation:[0.7071067812,-0.7071067812,0,0],fov:60,ortho:true}')
        baseline = picture()
        measure((20,10,3),(23,10,3))
        empty_box = picture()
        self.assertGreater(int(np.count_nonzero(np.any(empty_box != baseline,axis=2))),40)
        self.assertFalse(host.warnings, host.warnings)
