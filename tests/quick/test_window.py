"""Interaction tests of the light plan (quick/Plan.qml, the Workbench's plan without the real views) and of its year
chart, against a QQuickWindow, never Widgets or a native mouse. F5 (r23-f5) took away the legacy prototype
(quick/Main.qml): the tests of its own panels and fields went with it, the plan's and the chart's run on the Workbench.
The Workbench's cards cover the middle of the light plan: the tests of geometry under the pointer (zoom, image,
rectangle and handles) are the real plan's, in quick/pianta."""
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QPointF

from _fixtures import capannone
from meridiana import jobs
from meridiana.quick.app import QuickWindow, create_app
from meridiana.quick.capture import grab
from quick.gestures import click, item, point, pump


class QuickWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.renderer = os.environ.get('MERIDIANA_QUICK_TEST_RENDERER', 'shapes')
        if cls.renderer not in ('shapes', 'canvas'):
            raise ValueError('Unknown Quick test renderer: '+cls.renderer)
        print('Quick plan renderer:', cls.renderer, flush=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.host = QuickWindow(capannone(), Path(self.temp.name))
        self.win, self.bridge = self.host.window, self.host.bridge
        item(self.win, 'plan').setProperty('renderer', self.renderer)
        results, keys, _ = jobs.layout_of(self.bridge.session.project)
        self.bridge.accept_layout(0, results, keys)
        self.win.show()
        pump(40)
        self.plan = item(self.win, 'plan')

    def tearDown(self):
        warnings = list(self.host.warnings)
        self.host.close()
        self.app.processEvents()
        self.temp.cleanup()
        self.assertEqual(warnings, [])

    def test_modules_are_present_and_click_selects_the_hit_module(self):
        self.assertGreater(self.plan.property('zoom'), .02)
        self.assertEqual(self.plan.property('renderedModules'), self.bridge.moduleCount)
        self.assertEqual(self.plan.property('polygonCount'), len(self.bridge.scene))
        self.assertEqual(self.plan.property('paintedModules'), self.bridge.moduleCount)
        module = self.bridge.session.results['s1'].modules[0]
        x, y = module.centre
        pos = point(self.plan, x*self.plan.property('zoom')+self.plan.property('panX'),
                    -y*self.plan.property('zoom')+self.plan.property('panY'))
        click(self.app, self.win, pos)
        self.assertEqual(self.bridge.session.selected_module, ('s1', module.key))

    def test_the_entry_point_can_select_either_renderer(self):
        # r23-unita: QuickWindow.set_renderer went with F6 (the backend does not write QML properties, and nothing in
        # the program called it); the plan's own `renderer` is what this test drives
        for renderer in ('canvas', 'shapes'):
            self.plan.setProperty('renderer', renderer)
            pump(40)
            self.assertEqual(self.plan.property('renderer'), renderer)
            self.assertEqual(self.plan.property('paintedModules'), self.bridge.moduleCount)

    def test_year_chart_draws_the_same_points_in_both_geometry_modes(self):
        import math
        from PySide6.QtCore import QPointF
        self.bridge._year = {'points': [QPointF(i/365, .5+.4*math.sin(i/20)) for i in range(366)],
                             'maximum': 1000., 'total': '100000', 'hours': 8760, 'source': 'Fixture'}
        self.bridge.yearChanged.emit()
        self.win.setProperty('phase', 'production')
        chart = item(self.win, 'yearChart')
        for retained in (True, False):
            chart.setProperty('retained', retained)
            pump(250)
            self.assertEqual(chart.property('pointCount'), 366)
            image = grab(self.win)
            dpr = image.devicePixelRatio()
            origin = point(chart, 0, 0)
            coloured = 0
            for y in range(int(origin.y()+88), int(origin.y()+chart.height()-64), 2):
                for x in range(int(origin.x()+64), int(origin.x()+chart.width()-12), 2):
                    c = image.pixelColor(int((x+.5)*dpr), int((y+.5)*dpr))
                    coloured += c.blue()>c.red()+30 and c.red()<150
            self.assertGreater(coloured, 100, 'The energy curve must be painted in both modes')
