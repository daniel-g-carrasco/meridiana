"""Phase changes keep the cards in place and fade only their changing contents (R640)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import capannone
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import item, pump, wait_for


def items(node):
    yield node
    for child in node.childItems():
        yield from items(child)


def phase_views(win):
    node = item(win, 'view3dHost')
    while node.property('shown') is None:
        node = node.parentItem()
    return node


def setUpModule():
    _setup.keep_global_state()


class PhaseChanges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(capannone(), Path(cls.folder.name), real_views=True,
                               theme={'theme': 'light', 'reducedMotion': False, 'phaseAnimations': True})
        cls.win = cls.host.window
        cls.host.keep_on_screen = lambda: None
        cls.host._placement.timeout.disconnect()
        cls.win.resize(1800, 1000)
        cls.win.show()
        pump(500)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def setUp(self):
        self.win.showPhase('model')
        pump(300)

    def test_phase_changes_never_start_the_file_veil(self):
        veil = item(self.win, 'fileTransition')
        for phase in ('plant', 'production', 'economics', 'report', 'model'):
            self.win.showPhase(phase)
            self.assertEqual(self.win.property('phase'), phase)
            self.assertFalse(veil.property('running'), phase)
            pump(50)
            self.assertFalse(veil.property('running'), phase)
            pump(200)

    def test_file_keeps_its_veil_in_both_directions(self):
        veil = item(self.win, 'fileTransition')
        self.win.setProperty('fileOpen', True)
        self.assertTrue(veil.property('running'))
        pump(400)
        self.win.showPhase('plant')
        self.assertTrue(veil.property('running'))
        pump(400)
        self.assertFalse(self.win.property('fileShown'))

    def test_outgoing_inspector_is_drawn_but_immediately_out_of_reach(self):
        old = next(n for n in items(self.win.contentItem())
                   if n.objectName() == 'propertiesPartLoader' and n.property('phaseId') == 'model')
        self.win.showPhase('plant')
        self.assertEqual(self.win.property('leavingPhase'), 'model')
        self.assertTrue(old.isVisible())
        self.assertFalse(old.isEnabled())
        for _ in range(16):
            pump(10)
        self.assertEqual(self.win.property('leavingPhase'), '')
        self.assertFalse(old.isVisible())

    def test_rapid_changes_retire_all_but_the_latest_pair(self):
        self.win.showPhase('plant')
        self.win.showPhase('production')
        self.assertEqual(self.win.property('leavingPhase'), 'plant')
        model = next(n for n in items(self.win.contentItem())
                     if n.objectName() == 'propertiesPartLoader' and n.property('phaseId') == 'model')
        self.assertFalse(model.isVisible())
        for _ in range(16):
            pump(10)
        self.assertEqual(self.win.property('leavingPhase'), '')

    def test_project_leaves_alone_and_shared_cards_hold_their_geometry(self):
        self.win.showPhase('plant')
        pump(300)
        project = item(self.win, 'leftPanel')
        shared = [item(self.win, name) for name in ('centralPanel', 'rightPanel')]
        before = [(n.x(), n.y(), n.width(), n.height(), n.opacity()) for n in shared]
        self.assertTrue(project.isVisible(), 'Project starts visible in Plant')
        self.win.showPhase('production')
        self.assertTrue(project.isVisible(), 'Project stays drawn during its own exit')
        self.assertFalse(project.isEnabled())
        self.assertEqual([(n.x(), n.y(), n.width(), n.height(), n.opacity()) for n in shared], before)
        for _ in range(20):
            pump(10)
        self.assertFalse(project.isVisible())
        self.assertTrue(all(n.opacity() == 1 for n in shared))

    def test_shared_plan_scene_and_tree_are_kept_without_refresh(self):
        self.win.setProperty('viewOfPhase', {'model': 'both', 'plant': 'both'})
        self.win.setProperty('viewMode', 'both')
        plan, scene = self.win.property('planItem'), self.win.property('sceneItem')
        tree = item(self.win, 'projectPartLoader').property('item')
        changed = []
        self.host.bridge.sceneChanged.connect(lambda: changed.append('scene'))
        from meridiana.gui.backend.project_tree import ProjectTreeBackend
        backend = next(c for c in self.host.parts.controllers.values() if isinstance(c, ProjectTreeBackend))
        backend.rowsAboutToChange.connect(lambda: changed.append('tree'))
        for phase in ('plant', 'model', 'plant'):
            self.win.showPhase(phase)
            self.assertEqual(self.win.property('planItem'), plan)
            self.assertEqual(self.win.property('sceneItem'), scene)
            self.assertEqual(item(self.win, 'projectPartLoader').property('item'), tree)
            views = phase_views(self.win)
            self.assertEqual(views.opacity(), 1)
            for _ in range(16):
                pump(10)
        self.assertEqual(changed, [])

    def test_views_fade_on_exit_and_remain_allocated_after_it(self):
        views = phase_views(self.win)
        self.win.showPhase('production')
        self.assertFalse(views.isEnabled())
        self.assertEqual(views.opacity(), 1, 'the old view starts whole, not blank')
        for _ in range(20):
            pump(10)
        self.assertTrue(views.isVisible(), 'retained so the 3D buffers are not rebuilt')
        self.assertEqual(views.opacity(), 0)

    def test_reduced_motion_switches_every_body_immediately(self):
        self.host.theme.configure({'reducedMotion': True})
        self.addCleanup(self.host.theme.configure, {'reducedMotion': False})
        for phase in ('plant', 'production', 'economics', 'report', 'model'):
            self.win.showPhase(phase)
            self.assertEqual(self.win.property('leavingPhase'), '')
            self.assertFalse(item(self.win, 'fileTransition').property('running'))
            inspectors = [n for n in items(self.win.contentItem()) if n.objectName() == 'propertiesPartLoader']
            self.assertEqual([n.property('phaseId') for n in inspectors if n.isEnabled()], [phase])
            for n in inspectors:
                self.assertEqual(n.opacity(), 1 if n.property('phaseId') == phase else 0)

    def test_enabling_reduced_motion_finishes_a_running_change(self):
        self.win.showPhase('plant')
        self.assertEqual(self.win.property('leavingPhase'), 'model')
        self.host.theme.configure({'reducedMotion': True})
        self.addCleanup(self.host.theme.configure, {'reducedMotion': False})
        self.assertEqual(self.win.property('leavingPhase'), '')
        old = next(n for n in items(self.win.contentItem())
                   if n.objectName() == 'propertiesPartLoader' and n.property('phaseId') == 'model')
        self.assertFalse(old.isVisible())
        self.assertEqual(old.opacity(), 0)

    def test_popups_of_the_leaving_inspector_close_before_its_fade(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtQml import QQmlComponent
        loader = next(n for n in items(self.win.contentItem())
                      if n.objectName() == 'propertiesPartLoader' and n.property('phaseId') == 'model')
        component = QQmlComponent(self.host.engine)
        component.setData(b'import QtQuick\nimport Meridiana.Controls as M\nItem {'
                          b'M.ToolTip { objectName: "tip"; text: "Help" }'
                          b'M.Menu { objectName: "menu"; M.MenuItem { text: "Action" } }'
                          b'M.Popup { objectName: "panel"; width: 80; height: 40 }}', QUrl())
        anchor = component.create()
        self.assertIsNotNone(anchor, component.errorString())
        anchor.setParent(loader)
        anchor.setParentItem(loader)
        from PySide6.QtCore import QObject
        popups = [p for p in anchor.findChildren(QObject) if p.objectName() in ('tip', 'menu', 'panel')]
        self.assertEqual(len(popups), 3)
        for popup in popups:
            self.win.showPhase('model')
            for _ in range(20):
                pump(10)
            popup.setProperty('visible', True)
            for _ in range(70):
                pump(10)
            self.assertTrue(popup.property('visible'), popup.objectName())
            self.win.showPhase('plant')
            self.assertTrue(loader.isVisible(), 'still drawn while leaving')
            self.assertFalse(popup.property('reachable'), popup.objectName())
            wait_for(lambda p=popup: not p.property('visible'), seconds=.16)
            popup.setProperty('visible', True)
            pump(1200)
            self.assertFalse(popup.property('visible'), 'cannot reopen behind the new phase')

    def test_object_picker_does_not_follow_its_old_phase(self):
        self.win.openObjects()
        pump(100)
        picker = item(self.win, 'objectPicker')
        self.assertTrue(picker.property('visible'))
        self.win.showPhase('plant')
        self.assertFalse(picker.property('visible'))


def render_borders(out):
    """Read pixels from the real workbench's GPU scene in an isolated child process."""
    import time
    from PySide6.QtCore import QPointF
    from PySide6.QtQuick import QSGRendererInterface
    create_app()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        host = QuickWindow(capannone(), Path(folder), real_views=True,
                           theme={'theme': 'light', 'reducedMotion': False, 'phaseAnimations': True})
        win = host.window
        host.keep_on_screen = lambda: None
        host._placement.timeout.disconnect()
        win.resize(1400, 900)
        win.show()

        def settle():
            for _ in range(40):
                pump(10)

        def grab():
            result = win.contentItem().grabToImage()
            ready = []
            result.ready.connect(lambda: ready.append(True))
            start = time.perf_counter()
            # a limit, not a measure: on the CI's runner (software OpenGL, two cores) a grab took more than 10 s
            while not ready and time.perf_counter() - start < 60:
                pump(2)
            if not ready:
                raise AssertionError('GPU capture timed out')
            return result.image()

        try:
            settle()
            if win.rendererInterface().graphicsApi() in (QSGRendererInterface.GraphicsApi.Software,
                                                       QSGRendererInterface.GraphicsApi.Unknown):
                return 3
            for phase in ('plant', 'production', 'economics', 'report', 'model'):
                win.showPhase(phase)
                settle()
            cases = []
            for before, after in (('model', 'plant'), ('plant', 'production'), ('economics', 'report')):
                win.showPhase(before)
                settle()
                cards = [item(win, name) for name in ('rightPanel', 'centralPanel')]
                points = [n.mapToItem(win.contentItem(), QPointF(n.width()/2, .5)) for n in cards]
                first = grab()
                win.showPhase(after)
                veil = bool(item(win, 'fileTransition').property('running'))
                pump(40)
                middle = grab()
                settle()
                last = grab()
                colors = []
                for im in (first, middle, last):
                    dpr = im.width() / win.width()
                    colors.append([im.pixelColor(int(p.x()*dpr), int(p.y()*dpr)).name() for p in points])
                for name, im in (('before', first), ('middle', middle), ('after', last)):
                    im.save(str(out / f'{before}-{after}-{name}.png'))
                cases.append(dict(before=before, after=after, veil=veil, colors=colors))
            (out / 'borders.json').write_text(json.dumps(cases), encoding='utf8')
        finally:
            host.close()
    return 0


class GraphicsBorders(unittest.TestCase):
    def test_card_border_pixels_do_not_fade_with_their_contents(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='rhi',
                       QSG_RENDER_LOOP='threaded', QT_SCALE_FACTOR='1', PYTHONDONTWRITEBYTECODE='1')
            if sys.platform == 'win32':
                env['QSG_RHI_BACKEND'] = 'd3d11'
            result = subprocess.run([sys.executable, '-m', 'quick.shell.test_cambio_fase_r640', '--render', folder],
                                    env=env, capture_output=True, text=True, timeout=180)
            if result.returncode == 3:
                self.skipTest('Qt Quick has no graphics API')
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
            cases = json.loads((Path(folder) / 'borders.json').read_text(encoding='utf8'))
            self.assertEqual(len(cases), 3)
            for case in cases:
                with self.subTest(phase=case['after']):
                    self.assertFalse(case['veil'])
                    self.assertEqual(case['colors'][0], case['colors'][1])
                    self.assertEqual(case['colors'][0], case['colors'][2])


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--render':
        sys.exit(render_borders(Path(sys.argv[2])))
    unittest.main()
