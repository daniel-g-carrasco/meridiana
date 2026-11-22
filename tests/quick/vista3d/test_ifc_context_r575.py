"""R575: the true geometry of an imported IFC in the 3D view, where its bodies are.

D1: the position computed for the model's geometry reached QML as numpy.float64, which QML reads as '': the model
was drawn about the scene's origin whatever the bodies did (26.5 m off in plan and 8.1 m low on a real model).
D2: the model's zero was the storeys' Elevation attribute (0.26 m here), not their height in the world (84.669 m,
the bodies' ground): with D1 alone corrected the model would have stood 84.4 m above the ground.

The sample (tests/data/ifc/r575-sintetico.ifc) places its site at 84.409 m and its storey 0.26 m above it, as the
real model does; its flat roof «TETTO» (#109) is the body «Edificio» of the import.

D3: every change of geometry, sub-fields or layout made the context's Models again (a Repeater3D over a list made
again); their meshes left the scene with them and came back empty, and the model vanished from the 3D after the first
change. The pieces are now rows that stay (scene_slots.ContextSlots): the tests hold the Models made at the start."""
from pathlib import Path
import math
import tempfile
import unittest

import numpy as np
from PySide6.QtCore import QCoreApplication, QEvent, QObject
from PySide6.QtWidgets import QApplication

from meridiana.app import jobs
from meridiana.app.exchange import ifc_export, ifc_import, ifc_mesh, ifc_worker
from meridiana.core.model import model
from meridiana.gui.application import QuickWindow, create_app
from ._fidelity_support import settle
from quick.aiuti.tempi import timed

SAMPLE = Path(__file__).resolve().parents[2] / 'data' / 'ifc' / 'r575-sintetico.ifc'
ROOF = 109                       # the record of «TETTO», the roof the body «Edificio» is made of
WORLD_ZERO = 84.669              # the site at 84.409, the storey 0.26 above it
TERRAIN_ZERO = 84.369            # R602: the top of the sample's terrain, the model's zero


def imported(folder: Path) -> model.Project:
    """A project with the sample imported the way the window does it (the worker, the plan, apply)."""
    found = ifc_worker.read(str(SAMPLE), 'direct', lambda f, w: None, None, str(folder / 'cache'))
    project = model.Project()
    plan = ifc_import.plan(found, project, 'origin', None, name='t', source_name='t.ifc')
    ifc_import.apply(project, plan)
    return project


def numpy_inside(value, path='') -> list:
    """The places in `value` (lists and maps as given to QML) that hold a NumPy value."""
    if isinstance(value, (np.generic, np.ndarray)):
        return [path or '.']
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in numpy_inside(v, f'{path}.{k}')]
    if isinstance(value, (list, tuple)):
        return [p for i, v in enumerate(value) for p in numpy_inside(v, f'{path}[{i}]')]
    return []


class ContextPlaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        create_app()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.project = imported(self.folder)
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

    def open(self, project):
        self.host = QuickWindow(project, self.folder / 'window', real_views=True)
        self.host.window.show()
        settle(self.app, .2)
        # the 3D on show (R598: one not on show makes nothing); off screen this window has room for one view at a time
        self.host.window.setProperty('viewMode', '3d')
        settle(self.app, .3)
        self.session = self.host.bridge.session

    def nodes(self):
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        return sorted((n for n in self.host.window.findChildren(QObject) if n.objectName().startswith('ifc-context:')),
                      key=lambda n: int(n.objectName().split(':')[1]))

    def roof_in_scene(self, project):
        """The corners of «TETTO» where the 3D view draws them, in the plan (east, north) and above the ground: by the
        Model's own position and turn, as QML has them."""
        ref = project.resources['ifc_reference']
        mesh = ifc_mesh.load(ref['context']['mesh'])
        k = [int(e[0]) for e in mesh['elements']].index(ROOF)
        piece = int(mesh['piece_of'][k])
        v, f, _c = ifc_mesh.piece(mesh, piece)
        first, n = int(mesh['elements'][k][1]), int(mesh['elements'][k][2])
        q = v[np.unique(f[first:first + n])].astype(float)       # about the model's middle: x east, y north, z up
        node = next(n for n in self.nodes() if n.objectName() == f'ifc-context:{piece}')
        p = node.property('position')
        t = math.radians(node.property('eulerRotation').y())
        qx, qy, qz = q[:, 0], q[:, 2], -q[:, 1]                  # Qt: x east, y up, z south
        x = qx * math.cos(t) + qz * math.sin(t) + p.x()
        z = -qx * math.sin(t) + qz * math.cos(t) + p.z()
        return np.column_stack((x, -z, qy + p.y()))

    def assert_on_its_body(self, project, where=''):
        roof = self.roof_in_scene(project)
        body = next(b for b in project.buildings if b.name == 'Edificio')
        ring = np.asarray(body.footprint, float)
        np.testing.assert_allclose(roof[:, :2].mean(0), ring.mean(0), atol=.03, err_msg=f'centre in plan {where}')
        np.testing.assert_allclose([roof[:, 0].min(), roof[:, 0].max(), roof[:, 1].min(), roof[:, 1].max()],
                                   [ring[:, 0].min(), ring[:, 0].max(), ring[:, 1].min(), ring[:, 1].max()],
                                   atol=.05, err_msg=f'box in plan {where}')
        self.assertAlmostEqual(float(roof[:, 2].max()), body.ridge(), delta=.05, msg=f'top {where}')

    def test_the_zero_of_the_model_is_in_the_world(self):
        """D2: the zero is a height in the model's world, never the Elevation attribute (0.26 m). R602: the sample's
        terrain stands 0.3 m under its ground floor (WORLD_ZERO) at the foot of the building, and the zero is the
        terrain's (ifc_ground)."""
        ref = self.project.resources['ifc_reference']
        self.assertAlmostEqual(ref['context']['ground'], TERRAIN_ZERO, places=3)
        anchor = ref['anchor']['building']
        self.assertAlmostEqual(ref['buildings'][anchor], TERRAIN_ZERO, places=3)
        self.assertAlmostEqual(ifc_export.context_ground(ref), TERRAIN_ZERO, places=3)

    def test_the_values_given_to_qml_are_python_numbers(self):
        self.open(self.project)
        scene = self.host.scene
        self.assertTrue(scene.contextModels)
        meta = scene.metaObject()
        body = next(b for b in self.session.project.buildings if b.name == 'Edificio')
        for selected in ((), ('building', body.id)):
            if selected:
                self.session.select(*selected)
                settle(self.app, .1)
            found = {}
            for i in range(meta.propertyCount()):           # every list and map the 3D view reads
                prop = meta.property(i)
                if prop.typeName() in ('QVariantList', 'QVariantMap', 'QVariant'):
                    name = prop.name()
                    where = numpy_inside(getattr(scene, name))
                    if where:
                        found[name] = where[:4]
            self.assertEqual(found, {}, selected)
        for entry in scene.contextModels:
            self.assertTrue(all(type(v) is float for v in entry['position']), entry['position'])

    def test_the_model_stands_on_its_bodies_and_follows_them(self):
        self.open(self.project)
        nodes = self.nodes()
        self.assertEqual(len(nodes), len(self.host.scene.contextModels))
        for node, entry in zip(nodes, self.host.scene.contextModels, strict=True):
            p = node.property('position')
            np.testing.assert_allclose([p.x(), p.y(), p.z()], entry['position'], atol=1e-3)
        self.assert_on_its_body(self.session.project, 'as imported')

        def move(p):
            c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
            for b in p.buildings:
                b.footprint = [[c * x - s * y + 40.0, s * x + c * y - 25.0] for x, y in b.footprint]
        self.session.edit('move', move)
        settle(self.app, .2)
        self.assert_on_its_body(self.session.project, 'moved and turned')

    def test_a_project_imported_before_the_correction_opens_right(self):
        """Its context kept the Elevation attribute as its zero (0.26 m); the anchor's ground is in the reference since
        R453, and the 3D takes that: no new import."""
        ref = self.project.resources['ifc_reference']
        ref['context']['ground'] = 0.26
        again = model.Project.from_json(self.project.to_json())
        self.open(again)
        self.assert_on_its_body(self.session.project, 'old project')

    def assert_the_same_pieces(self, first, where):
        """The Models of the context are still the ones made at the start, shown, on their meshes with their data
        (D3: a Model made again took its mesh out of the scene, Qt Quick 3D gave it back empty)."""
        nodes = self.nodes()
        self.assertEqual([n.property('r575') for n in nodes], [f'first-{k}' for k in range(len(first))],
                         f'the Models of the IFC context were made again ({where})')
        for node, (geometry, size) in zip(nodes, first, strict=True):
            self.assertIs(node.property('geometry'), geometry, where)
            self.assertTrue(node.property('visible'), where)
            self.assertEqual(node.property('geometry').vertexData().size(), size, where)
            self.assertGreater(size, 0)

    def test_the_pieces_stay_in_the_3d_after_changes(self):
        """R575 D3: a change of geometry (the height of an obstacle), twenty of them, and the modules laid on a
        sub-field: the pieces of the model are the same Models on the same meshes, still drawn where they belong."""
        body = next(b for b in self.project.buildings if b.name == 'Edificio')
        self.project.exclusions.append(model.ExclusionItem(id='e-r575', ring=[[-1, -1], [0, -1], [0, 0], [-1, 0]],
                                                           kind='chimney', building=body.id, height=1.0))
        self.open(self.project)
        nodes = self.nodes()
        self.assertTrue(nodes)
        for k, node in enumerate(nodes):
            node.setProperty('r575', f'first-{k}')
        first = [(n.property('geometry'), n.property('geometry').vertexData().size()) for n in nodes]
        rebuilds = self.host.scene.rebuilds

        def taller(p, h):
            next(e for e in p.exclusions if e.id == 'e-r575').height = h
        self.session.edit('height', lambda p: taller(p, 1.5))
        # the scene is made again a turn of events after the change, or more on a loaded machine (1 not > 1 on Linux)
        from quick.gestures import wait_for
        wait_for(lambda: self.host.scene.rebuilds > rebuilds, 10)
        settle(self.app, .1)
        self.assert_the_same_pieces(first, 'after one change')

        def shift(p):
            for b in p.buildings:
                b.footprint = [[x + .25, y - .1] for x, y in b.footprint]
        for i in range(20):             # the obstacle's height, and the bodies moved: the model's place changes too
            if i % 2:
                self.session.edit('move', shift)
            else:
                self.session.edit('height', lambda p, i=i: taller(p, 1.0 + .05 * i))
            settle(self.app, .02)
        settle(self.app, .2)
        self.assert_the_same_pieces(first, 'after twenty changes')
        self.assert_on_its_body(self.session.project, 'after twenty changes')

        ring = [[-4.5, -3.5], [4.5, -3.5], [4.5, 3.5], [-4.5, 3.5]]
        self.session.edit('lay', lambda p: p.subfields.append(
            model.SubField('sf-r575', 'Roof', ring, building=body.id, filled=True)))
        results, keys, _skipped = jobs.layout_of(self.session.project, {})
        self.assertTrue(results['sf-r575'].modules)
        self.session.layout_done(self.session.generation, results, keys)
        settle(self.app, .2)
        self.assertGreater(self.host.scene.moduleCount, 0)
        self.assert_the_same_pieces(first, 'after the modules were laid')
        self.assert_on_its_body(self.session.project, 'after the changes')

    def test_the_pieces_hide_when_the_frame_is_lost_and_come_back(self):
        """The anchor reshaped: nothing of the model is drawn (as before), its Models stay hidden; undone, the same
        Models are drawn again."""
        self.open(self.project)
        nodes = self.nodes()
        for k, node in enumerate(nodes):
            node.setProperty('r575', f'first-{k}')
        first = [(n.property('geometry'), n.property('geometry').vertexData().size()) for n in nodes]
        anchor = self.session.project.resources['ifc_reference']['anchor']['building']

        def reshape(p):
            p.building(anchor).footprint = [[0, 0], [9, 0], [9, 9]]
        # the scene is made again a turn of events after each change, or more on a loaded machine (once on Windows)
        from quick.gestures import wait_for
        rebuilds = self.host.scene.rebuilds
        self.session.edit('reshape', reshape)
        wait_for(lambda: self.host.scene.rebuilds > rebuilds, 10)
        settle(self.app, .1)
        self.assertEqual(self.host.scene.contextModels, [])
        self.assertEqual([n.property('r575') for n in self.nodes()], [f'first-{k}' for k in range(len(first))])
        self.assertFalse(any(n.property('visible') for n in self.nodes()))
        rebuilds = self.host.scene.rebuilds
        self.session.undo.undo()
        wait_for(lambda: self.host.scene.rebuilds > rebuilds, 10)
        settle(self.app, .1)
        self.assert_the_same_pieces(first, 'after the undo')


class ContextNeverWaitedTest(unittest.TestCase):
    """Passo 2 (R598): the 3D never waits for the model's true geometry read ahead (R548). The reading held in its
    thread, the window shows the bodies as they are; the model comes when the reading ends, in a piece of the
    window's turns, without the scene made again. Closed meanwhile, or the import undone meanwhile: nothing is shown,
    nothing raises."""
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        create_app()

    setUp, tearDown, open = ContextPlaceTest.setUp, ContextPlaceTest.tearDown, ContextPlaceTest.open
    nodes = ContextPlaceTest.nodes
    roof_in_scene, assert_on_its_body = ContextPlaceTest.roof_in_scene, ContextPlaceTest.assert_on_its_body

    def held_reading(self):
        """scene_context.prepared held in the reading ahead's thread until `release` is set (and on the window's
        thread, never: it would hang the test)."""
        import threading
        from unittest import mock
        from meridiana.gui.backend import scene_context
        release, started = threading.Event(), threading.Event()
        real = scene_context.prepared

        def held(*a, **k):
            self.assertIsNot(threading.current_thread(), threading.main_thread(), "made on the window's thread")
            started.set()
            release.wait(30)
            return real(*a, **k)
        patches = [mock.patch.object(scene_context, 'prepared', side_effect=held),
                   mock.patch.dict('os.environ', {'MERIDIANA_PRELOAD': '1'})]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(release.set)
        return release, started

    @timed('no call of the window over its few ms')
    def test_the_bodies_first_then_the_model_without_the_scene_made_again(self):
        import _setup
        from quick.aiuti.finestra_libera import window_stays_free
        release, started = self.held_reading()
        self.open(self.project)
        scene = self.host.scene
        self.assertTrue(started.wait(30), 'the reading started in its thread')
        self.assertEqual((scene.contextModels, scene.context._pieces), ([], []), 'the bodies as they are, meanwhile')
        self.assertTrue(scene.context.waiting())
        rebuilds = scene.rebuilds
        with window_stays_free(self.host.work.center, call_ms=5, beat_ms=None, only=('scene.context.piece',)) as seen:
            release.set()
            self.assertTrue(_setup.wait_for(lambda: bool(scene.contextModels), 30000), scene.context.error)
        # asserted: each piece of the geometry given to Qt in a turn of its own. Printed with its number, not asserted:
        # the turn that places them (entries, the rows of the 3D, the bodies made faint, the bounds), 4-6 ms here
        print(f"\nthe model's geometry, a piece a turn: {seen}; the placing: "
              f"{round(seen.left.get('scene.context', 0.0), 1)} ms; above 5 ms: {seen.over(5)}")
        self.assertEqual(seen.call_name, 'scene.context.piece')
        self.assertIn('scene.context', seen.left, 'placed in a turn of its own')
        self.assertEqual(scene.rebuilds, rebuilds, 'the scene was not made again')
        settle(self.app, .2)
        self.assert_on_its_body(self.session.project, 'come after the bodies')

    def test_closed_while_it_is_read(self):
        release, started = self.held_reading()
        self.open(self.project)
        self.assertTrue(started.wait(30))
        self.host.close()
        self.host = None
        release.set()
        settle(self.app, .3)                    # the reading's end tells nobody: its window is gone

    def test_the_import_undone_while_it_is_read(self):
        import _setup
        release, started = self.held_reading()
        project = model.Project()
        self.open(project)
        plan = ifc_import.plan(ifc_worker.read(str(SAMPLE), 'direct', lambda f, w: None, None,
                                               str(self.folder / 'cache')), project, 'origin', None, name='t',
                               source_name='t.ifc')
        import copy
        from meridiana.gui.backend import scene_context
        probe = model.Project()
        ifc_import.apply(probe, copy.deepcopy(plan))
        ahead = probe.resources['ifc_reference']['context']
        self.assertTrue(scene_context.preload(ahead['mesh'], ahead.get('skip') or ()))   # as the dialog reads ahead
        self.session.edit('import', lambda p: ifc_import.apply(p, plan))
        self.assertTrue(started.wait(30))
        scene = self.host.scene
        self.session.undo.undo()
        release.set()
        self.assertTrue(_setup.wait_for(lambda: not scene.context.waiting(), 30000))
        settle(self.app, .2)
        self.assertEqual(scene.contextModels, [], 'nothing of a model no longer in the project')


if __name__ == '__main__':
    unittest.main()
