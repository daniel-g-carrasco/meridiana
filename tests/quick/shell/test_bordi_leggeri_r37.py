"""Dragging an edge of the workspace lays out nothing but the cards' frames (R37, Daniel 21/11/2026: «il
ridimensionamento delle schede è molto scattante in qualsiasi fase»).

Before, every pixel laid out the whole inspector again (30-45 ms a step on Plant), drew a new image of the plan at the
new size (25-30 ms with 2000 modules) and laid out the charts of the page in the middle (20-45 ms): 80-180 ms a frame
with the right edge. Now while the edge moves the cards and the page hold their content, the plan moves the image it
has, and all is laid out once at the release. Measured on the real window with tools/measure_panel_drag.py.

Since r39 (the template's kit, Daniel 21/11/2026: «vorrei che il contenuto si spostasse dinamicamente... come
Electron»): what the cards hold follows the edge live; only when a step costs too much (the median of the last five
past 33 ms, after the first eight) the cards hold it for the rest of the drag, as before."""
import statistics
import tempfile
import time
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QEvent, QPointF, Qt

from _fixtures import capannone
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import item, mouse, point, pump, wait_for

setUpModule = _setup.keep_global_state


class LightEdges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def test_an_edge_dragged_moves_the_frames_and_lays_out_the_content_once_at_the_release(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            host = QuickWindow(capannone(), Path(folder), real_views=True, theme={'reducedMotion': True})
            host.bridge.configure_background(enabled=False)
            win = host.window
            win.show()
            win.resize(1600, 960)
            pump(1000)
            try:
                host.shell.trigger('phase_plant')
                pump(800)
                workspace = item(win, 'workspace')
                right = item(win, 'rightPanel')
                body = right.property('contentItem')
                plan = item(win, 'plan')
                wait_for(lambda: not workspace.property('settling'), 3)
                pump(300)
                card, held = right.width(), body.width()
                draws = plan.property('geometryDraws')
                handle = item(win, 'rightResizeHandle')
                start = point(handle)
                mouse(self.app, win, QEvent.Type.MouseButtonPress, start, Qt.MouseButton.LeftButton,
                      Qt.MouseButton.LeftButton)
                costs = []
                for step in range(1, 41):
                    # two pixels a step: the plan's image covers it, it is moved and not drawn again
                    at = start + QPointF(-2*step, 0)
                    began = time.perf_counter()
                    mouse(self.app, win, QEvent.Type.MouseMove, at, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
                    costs.append((time.perf_counter()-began)*1000)
                    pump(8)
                self.assertAlmostEqual(right.width()-card, 80, delta=1)        # the card follows the pointer
                if workspace.property('holdContent'):                          # the steps cost: held, as before
                    self.assertLess(body.width(), held+79)
                else:                                                          # light: it follows live
                    self.assertAlmostEqual(body.width(), held+80, delta=1)
                self.assertGreaterEqual(len(workspace.property('stepCosts').toVariant()), 8)
                if plan.property('retained'):
                    # the plan's image is only moved (drawn without an image, on the software renderer, it is drawn)
                    self.assertEqual(plan.property('geometryDraws'), draws)
                # the move's own cost, bindings and layouts: 40-55 ms a step before on the real window, 10-20 after;
                # here a margin for a busy machine, far under what a layout of the inspector costs
                # live or held, the last steps of the drag stay light
                self.assertLess(statistics.median(costs[-10:]), 25, (costs, workspace.property('holdContent')))
                mouse(self.app, win, QEvent.Type.MouseButtonRelease, at, Qt.MouseButton.LeftButton,
                      Qt.MouseButton.NoButton)
                pump(600)
                self.assertFalse(workspace.property('resizing'))
                self.assertAlmostEqual(body.width(), held+80, delta=1)         # laid out once, at the release
                wait_for(lambda: plan.property('geometryDraws') > draws, 3)    # and the plan drawn at rest
                wait_for(lambda: plan.property('renderCamera').toVariant()['x'] == plan.property('panX'), 3)
            finally:
                host.close()
                pump(100)


if __name__ == '__main__':
    unittest.main()
