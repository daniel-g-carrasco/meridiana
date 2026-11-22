"""R602: while an imported model's true geometry is shown the lawn of the 3D follows the model's terrain on the site
(its basement in the terrain's dig, not buried), and stays the plain «#Rectangle» otherwise (a project without an
import draws as before). The sample is tests/data/ifc/terreno-interrato.ifc (tests/nucleo/test_ifc_terreno.py has the rule)."""
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PySide6.QtCore import QCoreApplication, QEvent, QObject
from PySide6.QtWidgets import QApplication

from meridiana.app.exchange import ifc_import, ifc_worker
from meridiana.core.model import model
from meridiana.gui.application import QuickWindow, create_app
from ._fidelity_support import settle

SAMPLE = Path(__file__).resolve().parents[2] / 'data' / 'ifc' / 'terreno-interrato.ifc'


class LawnTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        create_app()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.host = None

    def tearDown(self):
        warnings = []
        if self.host is not None:
            warnings = self.host.warnings[:]
            self.host.close()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.app.processEvents()
        self.tmp.cleanup()
        self.assertFalse(warnings)

    def ground(self, project):
        self.host = QuickWindow(project, self.folder / 'window', real_views=True)
        self.host.window.show()
        settle(self.app, .2)
        self.host.window.setProperty('viewMode', 'both')
        settle(self.app, .3)
        return next(n for n in self.host.window.findChildren(QObject) if n.objectName() == 'ground')

    def test_the_lawn_follows_the_terrain_of_the_model_shown(self):
        found = ifc_worker.read(str(SAMPLE), 'direct', lambda f, w: None, None, str(self.folder / 'cache'))
        project = model.Project()
        ifc_import.apply(project, ifc_import.plan(found, project, 'origin', None, name='t', source_name='t.ifc'))
        node = self.ground(project)
        self.assertTrue(self.host.scene.contextModels)
        geometry = node.property('geometry')
        self.assertIsNotNone(geometry)
        self.assertIs(geometry, self.host.scene.lawnGeometry)
        data = np.frombuffer(bytes(geometry.vertexData()), '<f4').reshape(-1, 6)
        # the flat lawn at 0, the lawn on the terrain (at the zero, -0.6 m in the model) DROP under it, its dig lower
        self.assertLessEqual(data[:, 1].max(), 1e-4)
        self.assertTrue(np.isclose(data[:, 1], 0.0).any())
        self.assertTrue(np.isclose(data[:, 1], -0.03, atol=1e-3).any())
        self.assertTrue((data[:, 4] >= -1e-6).all())                     # nothing faces down
        # the basement is not buried: over the body's footprint the lawn is the dig's floor, under the basement
        tri = data[:, :3].reshape(-1, 3, 3)
        middle = tri.mean(axis=1)
        body = np.asarray(project.buildings[0].footprint, float)
        (x0, y0), (x1, y1) = body.min(0), body.max(0)
        inside = ((middle[:, 0] > x0 + .3) & (middle[:, 0] < x1 - .3) & (-middle[:, 2] > y0 + .3)
                  & (-middle[:, 2] < y1 - .3))
        self.assertTrue(inside.any())
        self.assertLessEqual(tri[inside][:, :, 1].max(), -2.59)

    def test_without_an_import_the_lawn_is_the_plain_rectangle(self):
        node = self.ground(model.Project())
        self.assertIsNone(node.property('geometry'))
        self.assertEqual(node.property('source').toString(), '#Rectangle')


if __name__ == '__main__':
    unittest.main()
