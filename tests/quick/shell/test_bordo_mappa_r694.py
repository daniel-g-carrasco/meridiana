"""The views fill their hosts and keep the card's narrow padding, equal on four sides, after panel gestures (R694)."""
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QPointF

from _fixtures import capannone
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import drag, item, point, pump, wait_for
from quick.aiuti.avvisi import real

setUpModule = _setup.keep_global_state


class ViewMargins(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def test_views_fill_the_card_after_resize_close_reopen_and_move(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            host = QuickWindow(capannone(), Path(folder), real_views=True,
                               theme={'reducedMotion': False})
            host.bridge.configure_background(enabled=False)
            win = host.window
            win.show()
            win.resize(1600, 960)
            pump(1000)
            workspace = item(win, 'workspace')
            central = item(win, 'centralPanel')
            plan = item(win, 'plan').parentItem()
            scene_host = item(win, 'view3dHost')

            def measure(mode, gesture):
                wait_for(lambda: not workspace.property('settling') and
                         not workspace.property('landing') and
                         workspace.property('draggedPanel') == '', seconds=3)
                pump(100)
                loaders = [plan] if mode == 'plan' else []
                if mode != 'plan':
                    loaders.extend(child for child in scene_host.childItems()
                                   if child.property('frozen') is not None)
                if mode == 'both':
                    loaders.append(plan)
                corners = []
                for loader in loaders:
                    frame = loader.parentItem()
                    with self.subTest(mode=mode, gesture=gesture, view=loader.metaObject().className()):
                        self.assertAlmostEqual(loader.x(), 0, delta=0.01)
                        self.assertAlmostEqual(loader.y(), 0, delta=0.01)
                        self.assertAlmostEqual(loader.width(), frame.width(), delta=0.01)
                        self.assertAlmostEqual(loader.height(), frame.height(), delta=0.01)
                    corners.append((loader.mapToItem(central, QPointF()),
                                    loader.mapToItem(central, QPointF(loader.width(), loader.height()))))
                margins = (min(a.x() for a, b in corners), min(a.y() for a, b in corners),
                           central.width() - max(b.x() for a, b in corners),
                           central.height() - max(b.y() for a, b in corners))
                with self.subTest(mode=mode, gesture=gesture, margins=margins):
                    for margin in margins:
                        # the card's padding as before 16/11 (Space.S): equal on the four sides and narrow,
                        # Daniel 17/11/2026 on 12 px everywhere: «ma perché i margini delle mappe sono diventati
                        # improvvisamente più larghi??»
                        self.assertAlmostEqual(margin, 6, delta=0.01)

            try:
                for mode in ('plan', '3d', 'both'):
                    win.setProperty('viewMode', mode)
                    pump(500)
                    measure(mode, 'initial')
                    for delta in (-160, 240):
                        before = item(win, 'leftPanel').width()
                        start = point(item(win, 'leftResizeHandle'))
                        drag(self.app, win, start, start + QPointF(delta, 0), steps=12, pause=8)
                        measure(mode, f'resize {delta}')
                        self.assertAlmostEqual(item(win, 'leftPanel').width() - before, delta, delta=1)
                    project = item(win, 'leftPanel')
                    for opened in (False, True):
                        project.setProperty('opened', opened)
                        pump(500)
                        measure(mode, 'reopen' if opened else 'close')
                        self.assertEqual(project.isVisible(), opened)
                    drag(self.app, win, point(item(win, 'checksTitleDrag')),
                         point(workspace, workspace.width()/2, workspace.height()/2), steps=20, pause=20)
                    measure(mode, 'float checks')
                    self.assertTrue(item(win, 'checksPanel').property('floating'))
                    drag(self.app, win, point(item(win, 'checksTitleDrag')),
                         point(workspace, workspace.width()/2, workspace.height()-10), steps=20, pause=20)
                    measure(mode, 'dock checks')
                    self.assertEqual(item(win, 'checksPanel').property('zone'), 'bottom')
                    workspace.setProperty('previousLayout', None)
                    win.runCommand('default_layout')
                    pump(500)
                self.assertEqual(real(host.warnings), [])
            finally:
                host.close()
                pump(100)


if __name__ == '__main__':
    unittest.main()
