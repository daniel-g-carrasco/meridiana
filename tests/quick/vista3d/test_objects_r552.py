"""R554: the 3D objects placed with the tool stay in the 3D view, one per click, and the tool places them from the 3D
view too.

Daniel (08/11/2026, Flatpak on Linux): the objects placed with «3D object» showed on the plan and not in the 3D view.
Their models were made by the backend, but the 3D view's Repeater3D made its Models again at every change of the
objects, and the shared mesh of a model left the scene with the last of them: Qt Quick 3D gave it back empty, so the
objects of that model drew nothing until the mesh was written again (seen on a real Wayland display, mutter headless).
The view now keeps one Model per model of the catalogue for the whole session: the test holds the Model made at the
first object and checks it is still the one drawing after the next ones (Qt Quick 3D in offscreen does not draw,
the picture is in docs/richieste.md R554)."""
from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np
from PySide6.QtCore import QCoreApplication, QEvent, QObject
from PySide6.QtWidgets import QApplication

from meridiana import mesh, model
from meridiana.quick.app import QuickWindow, create_app
from meridiana.quick.backend.scene_assets import load_model
from ._fidelity_support import data, js, settle

PICKER = {'mode': 'place', 'step': 5.0, 'align': True, 'radius': 6.0, 'variation': 20.0, 'repeat': True, 'seed': 0}


def instances(path):
    raw = Path(path).read_bytes()
    count = struct.unpack('<4sHHIII', raw[:20])[5]
    return np.frombuffer(raw[20:], '<f4').reshape(count, 20)


class PlacedObjectsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        create_app()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        p = model.Project()
        p.buildings = [model.Building('b1', 'Shed', [[0, 0], [40, 0], [40, 20], [0, 20]], height=9.5)]
        self.host = QuickWindow(p, Path(self.tmp.name), real_views=True)
        self.host.window.show()
        settle(self.app, .1)
        self.host.window.setProperty('viewMode', 'both')
        settle(self.app, .1)
        self.view = self.host.window.findChild(QObject, 'viewport3d')
        self.view.setProperty('reducedMotion', True)
        self.session = self.host.bridge.session

    def tearDown(self):
        warnings = self.host.warnings[:]
        self.host.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.tmp.cleanup()
        self.assertFalse(warnings)

    def choose(self, kind):
        """The picker's «Choose and place»: a copy at every click until Esc (ObjectPicker.qml)."""
        self.host.shell.objectWanted.emit(kind, PICKER)
        settle(self.app, .05)

    def click_plan(self, x, y):
        self.host.plan.pointer(x, y, 0, .05)
        self.host.plan.click(x, y, 0)
        settle(self.app, .1)

    def models(self):
        """The decorative Models of the 3D view, once what was given up is gone (deleteLater runs in the loop)."""
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        found = {}
        for node in self.host.window.findChildren(QObject):
            if node.objectName().startswith('prop:'):
                found.setdefault(node.objectName(), []).append(node)
        return found

    def drawn(self, node):
        instancing = node.property('instancing')
        return node.property('visible'), instances(instancing.property('source').toLocalFile())

    def test_the_models_of_the_objects_stay_in_the_3d_view_one_object_per_click(self):
        self.choose('truck')
        self.click_plan(60., 10.)
        self.assertEqual([(x.kind, x.at) for x in self.session.project.props], [('truck', [60., 10.])])
        truck = self.models()['prop:truck']
        self.assertEqual(len(truck), 1)
        truck = truck[0]
        truck.setProperty('r552', 'first')
        self.assertIs(truck.property('geometry'), self.host.scene._asset_geometry['truck'])
        visible, table = self.drawn(truck)
        self.assertTrue(visible)
        self.assertEqual(len(table), 1)
        # the model as large as the truck's measures, standing on the ground where it was placed
        positions = load_model('truck')[0]
        extents = positions.max(0) - positions.min(0)
        matrix = table[0, :12].reshape(3, 4)
        np.testing.assert_allclose(np.abs(matrix[:, :3]) @ extents, [7.5, 3.3, 2.5], atol=.01)
        np.testing.assert_allclose(matrix[:, 3], mesh.to_qt(60., 10., 0.), atol=1e-4)

        self.choose('sports_car')
        self.click_plan(60., 16.)
        self.click_plan(70., 10.)
        self.assertEqual([x.kind for x in self.session.project.props], ['truck', 'sports_car', 'sports_car'])
        found = self.models()
        self.assertEqual(len(found['prop:truck']), 1)
        self.assertEqual(found['prop:truck'][0].property('r552'), 'first',
                         'the Model of the truck was made again: its shared mesh leaves the scene and comes back empty')
        self.assertEqual(len(self.drawn(found['prop:truck'][0])[1]), 1)
        self.assertEqual(len(found['prop:sports_car']), 1)
        visible, table = self.drawn(found['prop:sports_car'][0])
        self.assertTrue(visible)
        self.assertEqual(len(table), 2)

        # the last truck taken away: its Model stays, hidden and empty, ready for the next truck
        truck_id = self.session.project.props[0].id
        self.session.edit('remove', lambda p: setattr(p, 'props', [x for x in p.props if x.id != truck_id]))
        settle(self.app, .1)
        found = self.models()
        self.assertEqual(found['prop:truck'][0].property('r552'), 'first')
        visible, table = self.drawn(found['prop:truck'][0])
        self.assertFalse(visible)
        self.assertEqual(len(table), 0)

    def test_a_click_on_an_object_already_placed_takes_it(self):
        """R554 (Daniel 08/11): the capture's «double» was a second car placed on the truck by a click meant to take
        it; with the tool on, a click on an object takes it and the tool stays."""
        self.choose('truck')
        self.click_plan(60., 10.)
        truck = self.session.project.props[0].id
        self.choose('sports_car')
        self.click_plan(61., 10.3)                  # on the truck (7,5 x 2,5 m about 60, 10)
        self.assertEqual(len(self.session.project.props), 1)
        self.assertEqual(tuple(self.session.selection), ('prop', truck))
        self.assertEqual(self.host.plan.tool, 'prop')
        self.click_plan(60., 20.)                   # beside it: a car, and the tool still on
        self.assertEqual([x.kind for x in self.session.project.props], ['truck', 'sports_car'])
        self.assertEqual(self.host.plan.tool, 'prop')
        self.host.plan.key('Escape')
        settle(self.app, .05)
        self.assertEqual(self.host.plan.tool, 'select')

    def test_frame_the_selected_object(self):
        self.choose('truck')
        self.click_plan(60., 10.)
        self.assertEqual(self.session.selection[0], 'prop')
        js(self.view, 'frameSelection()')
        settle(self.app, .05)
        np.testing.assert_allclose(data(self.view, 'cameraState.target'), mesh.to_qt(60., 10., 0.), atol=1e-6)

    def test_a_click_in_the_3d_view_places_the_object_on_the_ground_or_on_the_roof(self):
        self.choose('truck')
        js(self.view, 'home()')
        settle(self.app, .05)
        x, y = data(self.view, "projectPoint([55, 0, -5])")[:2]
        # the pointer over the 3D view moves the plan's pointer: the plan shows where the object goes
        js(self.view, f'pressedHit = null; placeAt("move", {x}, {y}, ["ctrl"])')
        np.testing.assert_allclose(self.host.plan.drawing.pointer, (55., 5.), atol=.05)
        self.assertTrue(data(self.view, 'hoverData.edges').__len__() >= 12)
        # a click on the ground: the point of the ground under the pointer
        js(self.view, f'pressedHit = null; actions([{{kind: "select", phase: "once", x: {x}, y: {y}, mods: ["ctrl"]}}])')
        settle(self.app, .1)
        props = self.session.project.props
        self.assertEqual(len(props), 1)
        np.testing.assert_allclose(props[0].at, (55., 5.), atol=.05)
        self.assertIsNone(props[0].building)
        # a click on the roof: the point the ray met, the object stands on the roof
        js(self.view, f'pressedHit = {{point: [20, 9.5, -12], name: "buildings", index: 0}}; '
                      f'actions([{{kind: "select", phase: "once", x: {x}, y: {y}, mods: ["ctrl"]}}])')
        settle(self.app, .1)
        roof = self.session.project.props[-1]
        self.assertEqual(len(self.session.project.props), 2)
        np.testing.assert_allclose(roof.at, (20., 12.), atol=.05)
        self.assertEqual(roof.building, 'b1')
        table = self.drawn(self.models()['prop:truck'][0])[1]
        self.assertEqual(len(table), 2)
        np.testing.assert_allclose(table[1, 3::4][:3], mesh.to_qt(20., 12., 9.5), atol=1e-3)
        # R554: a click on the truck already placed takes it, no truck on the truck; the tool stays
        first = self.session.project.props[0].id
        js(self.view, f'pressedHit = {{point: [55.5, 1.5, -5.4], name: "prop:truck", index: 0}}; '
                      f'actions([{{kind: "select", phase: "once", x: {x}, y: {y}, mods: []}}])')
        settle(self.app, .1)
        self.assertEqual(len(self.session.project.props), 2)
        self.assertEqual(tuple(self.session.selection), ('prop', first))
        self.assertEqual(self.host.plan.tool, 'prop')
        # Esc in the 3D view ends the tool, as on the plan
        js(self.view, 'cancel(true)')
        settle(self.app, .05)
        self.assertEqual(self.host.plan.tool, 'select')
        self.assertEqual(data(self.view, 'hoverData.edges'), [])


if __name__ == '__main__':
    unittest.main()
