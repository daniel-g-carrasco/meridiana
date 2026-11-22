"""Pinching retains rendered content, draws it again in steps and ends at the same pixels (R702, R706)."""
import importlib.util
import json
from pathlib import Path
import statistics
import tempfile
import unittest

import _setup
from _fixtures import generated
from PySide6.QtCore import QCoreApplication, QPointF, Qt, QUrl
from PySide6.QtGui import QInputDevice, QNativeGestureEvent, QPointingDevice
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from meridiana.app import jobs
from meridiana.gui.application import create_app
from meridiana.gui.backend.plan import PlanController

setUpModule = _setup.keep_global_state


@unittest.skipUnless(_setup.WINDOWS, 'the offscreen hardware probe uses D3D11')
class PinchRendering(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
        if QQuickWindow.graphicsApi() == QSGRendererInterface.Software:
            self.skipTest('run this module separately with QT_QUICK_BACKEND=rhi QSG_RHI_BACKEND=d3d11')
        spec = importlib.util.spec_from_file_location('plan_render_probe', _setup.ROOT/'tools/plan_render_probe.py')
        self.helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.helper)
        project = generated(7, 1, 0)
        results, keys, _ = jobs.layout_of(project)
        self.cache = tempfile.TemporaryDirectory()
        self.addCleanup(self.cache.cleanup)
        self.controller = PlanController(project, manage_layout=False, cache=Path(self.cache.name))
        self.controller.session.layout_done(self.controller.session.generation, results, keys)
        self.controller.setPhase('plant')
        self.engine = QQmlApplicationEngine()
        self.controller.install(self.engine)
        self.component = QQmlComponent(self.engine, QUrl.fromLocalFile(str(Path(_setup.ROOT)/
            'src/meridiana/gui/qml/Meridiana/Plan/Plan.qml')))
        self.plan = self.component.createWithInitialProperties({'backend': self.controller})
        try:
            self.probe = self.helper.PlanRenderProbe(self.plan)
        except self.helper.HardwareUnavailable as error:
            self.controller.close()
            self.engine.deleteLater()
            self.app.processEvents()
            self.skipTest(str(error))
        self.plan.fit()
        for _ in range(10):
            self.app.processEvents()
            self.probe.render()
        _setup.turn_events(self.app, 1600)
        self.pad = QPointingDevice('render pad', 9702, QInputDevice.TouchPad,
                                  QPointingDevice.Finger, QInputDevice.Position, 5, 0)

    def tearDown(self):
        self.probe.close()
        self.controller.close()
        self.engine.deleteLater()
        self.app.processEvents()

    def pinch(self, value, kind=Qt.ZoomNativeGesture):
        point = QPointF(700, 400)
        QCoreApplication.sendEvent(self.probe.window, QNativeGestureEvent(
            kind, self.pad, 2, point, point, point, value, QPointF()))
        _setup.turn_events(self.app, 18)
        samples = [self.probe.render()]
        for _ in range(10):
            if self.plan.property('pendingMotion') is None:
                break
            _setup.turn_events(self.app, 10)
            samples.append(self.probe.render())
        self.assertIsNone(self.plan.property('pendingMotion'), 'the measured frame must apply the gesture')
        return max(samples, key=lambda sample: sample['draw_ms'])

    def test_zoom_reuses_a_snapshot_and_fits_the_offscreen_draw_budget(self):
        self.assertGreaterEqual(self.plan.property('paintedModules'), 778)
        self.pinch(0, Qt.BeginNativeGesture)
        drawn = self.plan.property('geometryDraws')
        samples = [self.pinch(.004) for _ in range(35)]
        # Removing the retained texture would force the 778 curves through MSAA again at every step.
        snapshot = self.plan.findChild(type(self.plan), 'motionSnapshot')
        self.assertIsNotNone(snapshot)
        self.assertTrue(self.plan.property('motionActive'))
        # 35 steps of 0.4 % are 15 %: under the stretch that asks for the geometry again (R706)
        self.assertEqual(self.plan.property('geometryDraws'), drawn, 'small steps only move the retained image')
        draws = sorted(s['draw_ms'] for s in samples[2:])
        print('pinch render median/p95 ms:', statistics.median(draws), draws[int(.95*(len(draws)-1))])
        self.assertLess(draws[int(.95*(len(draws)-1))], 16.6,
                        'offscreen scheduling allows two 120 Hz frames; the measured target remains 8.3 ms')

    def test_a_deep_pinch_draws_the_geometry_again_before_it_is_stretched_out_of_focus(self):
        # R706 (Daniel 20/11/2026: «mentre lo si fa tutta l'immagine si abbassa molto di risoluzione»): the image was
        # stretched up to four times before it was taken again
        self.pinch(0, Qt.BeginNativeGesture)
        drawn = self.plan.property('geometryDraws')
        worst = 1.
        for _ in range(40):
            self.pinch(.03)
            worst = max(worst, self.plan.property('motionRatio'))
        self.assertGreater(self.plan.property('geometryDraws'), drawn+2, 'a zoom of 3.2 times needs several redraws')
        self.assertLessEqual(worst, self.plan.property('motionStretch')*1.04,
                             'the retained image is never shown stretched beyond its tolerance')
        # the lines' pens follow in steps: never more than twice as thick or as thin as they should
        self.assertLess(self.plan.property('zoom')/self.plan.property('strokeZoom'), 2.01)

    def test_what_is_out_of_the_view_is_not_drawn(self):
        # R706: the large layers are cut in squares (plan_wiring.ZONE) and those out of the view and of the margin
        # around it are neither drawn nor built again when the lines change their width.
        # R707: and each layer only at its level of detail: from far a fill for each row, no module
        from PySide6.QtCore import QObject
        modules = self.plan.findChild(QObject, 'moduleGeometry')
        rows = self.plan.findChild(QObject, 'moduleRows')

        def shown(batch):
            shapes = [item for item in batch.childItems() if item.property('penScale') is not None]
            return sum(1 for item in shapes if item.isVisible()), len(shapes)

        def far():
            return self.plan.property('modulePixels') < self.controller.levels['field']
        every = shown(modules)[1]
        self.assertGreater(every, 1, 'a plant wider than a square')
        whole = far()
        self.assertEqual(shown(modules)[0], 0 if whole else every, 'the whole plant in view')
        self.assertEqual(shown(rows)[0], shown(rows)[1] if whole else 0, 'its rows, when a module is a few pixels')
        self.plan.zoomAt(8, self.plan.property('width')/2, self.plan.property('height')/2)
        _setup.turn_events(self.app, 700)
        self.probe.render()
        self.assertFalse(far(), 'eight times nearer: the scale of the modules')
        seen = shown(modules)[0]
        print('squares of modules drawn near the modules:', seen, 'of', every)
        self.assertLess(seen, every, 'near the modules the squares far from the view are not drawn')
        self.assertGreater(seen, 0)
        self.assertEqual(shown(rows)[0], 0, 'and no row')
        for _ in range(40):
            if modules.property('ready'):
                break
            _setup.turn_events(self.app, 50)
            self.probe.render()
        self.assertTrue(modules.property('ready'), 'what is in view is built, whatever is out of it')
        self.plan.fit()
        _setup.turn_events(self.app, 700)
        self.probe.render()
        self.assertEqual(shown(modules)[0], 0 if whole else every, 'and back: as it was')
        self.assertEqual(shown(rows)[0], shown(rows)[1] if whole else 0)

    def test_pinch_settlement_keeps_the_camera_and_rendered_edges_in_place(self):
        self.pinch(0, Qt.BeginNativeGesture)
        for _ in range(4):
            self.pinch(.01)
        self.pinch(0, Qt.EndNativeGesture)
        camera = tuple(self.plan.property(n) for n in ('panX', 'panY', 'zoom'))
        early = self.probe.render(readback=True)
        _setup.turn_events(self.app, 800)
        for _ in range(5):
            self.probe.render()
            _setup.turn_events(self.app, 30)
        late = self.probe.render(readback=True)
        self.assertEqual(tuple(self.plan.property(n) for n in ('panX', 'panY', 'zoom')), camera)
        self.assertFalse(self.plan.property('motionActive'))
        drawn = self.plan.property('renderCamera')
        drawn = drawn.toVariant() if hasattr(drawn, 'toVariant') else drawn
        self.assertEqual((drawn['x'], drawn['y'], drawn['zoom']), camera, 'at rest the geometry is drawn at the camera')
        self.assertLess(abs(self.plan.property('zoom')/self.plan.property('strokeZoom')-1), .17,
                        'at rest the lines are as wide as they should, within a sixth')
        motion = self.helper.image_motion(early, late, camera, camera)
        self.assertEqual(motion['residual_px'], [0, 0], motion)

    def test_the_first_pinch_frame_uses_the_image_prepared_during_idle(self):
        for _ in range(80):
            _setup.turn_events(self.app, 20)
            self.probe.render()
        self.pinch(0, Qt.BeginNativeGesture)
        drawn = self.plan.property('geometryDraws')
        first = self.pinch(.01)
        self.app.processEvents()
        self.assertEqual(self.plan.property('geometryDraws'), drawn,
                         'the settled image should be reused without a redraw on the first step')
        self.assertLess(first['draw_ms'], 16.6, 'the first movement must not allocate a new MSAA texture')

    def test_the_hardware_trace_records_real_frame_durations_and_the_visual_camera(self):
        from meridiana.gui.backend.gesture_trace import GestureTrace
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'gpu.jsonl'
            trace = GestureTrace(self.probe.window, path, render_control=True)
            try:
                self.pinch(0, Qt.BeginNativeGesture)
                self.pinch(.01)
                self.pinch(0, Qt.EndNativeGesture)
            finally:
                trace.close()
            rows = [json.loads(line) for line in path.read_text(encoding='utf8').splitlines()]
            frames = [r for r in rows if r['record'] == 'frame']
            self.assertTrue(frames)
            self.assertTrue(all(r['timing_available'] for r in frames))
            self.assertTrue(all(r['render_frame_ms'] >= r['render_ms'] >= 0 for r in frames))
            self.assertIsNotNone(frames[-1]['camera'])
            self.assertAlmostEqual(frames[-1]['camera']['zoom'], self.plan.property('zoom'))

    def test_the_retained_image_follows_the_drawing_while_the_camera_rests(self):
        # R706: one live image of the geometry. What changes under it (a tile that arrives, the sun map, the phase)
        # is drawn without a gesture; the second texture of R702 had to be told of each of them, one by one.
        from PySide6.QtCore import QObject
        from PySide6.QtGui import QColor, QImage
        snapshot = self.plan.findChild(QObject, 'motionSnapshot')
        self.assertTrue(snapshot.property('live'))
        self.assertTrue(snapshot.property('hideSource'), 'the geometry is drawn once, through its image')
        maps = self.controller.maps
        maps.setSource('osm')
        wanted = sorted(maps.state.wanted)
        self.assertGreaterEqual(len(wanted), 1)
        for _ in range(20):
            _setup.turn_events(self.app, 20)
            self.probe.render()
        before = self.probe.render(readback=True)
        camera = tuple(self.plan.property(n) for n in ('panX', 'panY', 'zoom'))
        image = QImage(256, 256, QImage.Format_RGB32)
        image.fill(QColor('#c0392b'))
        for key in wanted:
            maps._ready(*key, image)
        for _ in range(20):
            _setup.turn_events(self.app, 20)
            self.probe.render()
        after = self.probe.render(readback=True)
        self.assertEqual(tuple(self.plan.property(n) for n in ('panX', 'panY', 'zoom')), camera)
        self.assertNotEqual(before, after, 'the tiles that arrived are in the picture without a gesture')

    def test_changing_phase_takes_the_wiring_out_of_the_picture_at_once(self):
        for _ in range(20):
            _setup.turn_events(self.app, 20)
            self.probe.render()
        before = self.probe.render(readback=True)
        self.controller.setPhase('model')
        for _ in range(20):
            _setup.turn_events(self.app, 20)
            self.probe.render()
        self.assertNotEqual(before, self.probe.render(readback=True),
                            'plant wiring must not stay in the picture of the modelling phase')
