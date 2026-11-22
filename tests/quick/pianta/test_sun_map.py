"""The sun map in the plan (study 45, package 5): the button of the plan's bar turns it on and off (off cancels its job),
the images of the surfaces come and are laid on the plan, the legend has the six classes of the loss with the limits
decided, the figures under the pointer are SunMap.value_at's, changing what is shown or the scale starts no job, a
change of the project leaves the old map dimmed until the new one comes, and the window stays free while the map is
computed with the layer in view (the guard of study 48, chapter 5). The real window, off screen, a project with
obstacles and modules laid (mixed: the shed of Rho with its parapet, vent and plant, the houses)."""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtTest import QTest

import _setup
from _fixtures import capannone_rho, clear_sky_meteo, write_cache
from meridiana import i18n
from meridiana.app import jobs
from meridiana.app.maps import tiles
from meridiana.core.energy import irradiance_map as im
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.finestra_libera import settled, software_frames, window_stays_free
from quick.aiuti.tempi import timed

COMPUTE_MS = 400000          # the whole map of the test's project, on a PC loaded by other suites


def items(root):
    """Every item under `root`, Repeaters' delegates too (they are child items, not always child objects)."""
    out, pending = [], [root]
    while pending:
        item = pending.pop()
        out.append(item)
        pending.extend(item.childItems())
    return out


class SunMapInThePlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())
        cls.app = _setup.qt_or_skip()
        create_app()
        i18n.setup('it')
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.cache = Path(cls.folder.name)
        write_cache(clear_sky_meteo(), cls.cache)
        project = capannone_rho()
        project.subfields[0].filled = True
        results, keys, _laid = jobs.layout_of(project)
        # no motion and no background of the map: what the window draws by itself does not cover what the map costs
        cls.host = QuickWindow(project, cls.cache, real_views=True, theme={'theme': 'light', 'reducedMotion': True})
        cls.host.plan.configureMaps({'offline': True, 'source': tiles.NONE})
        cls.host.bridge.accept_layout(cls.host.bridge.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.resize(1400, 900)
        cls.win.show()
        QTest.qWaitForWindowExposed(cls.win)
        cls.bridge = cls.host.sun_map
        cls.sun = cls.bridge.sun
        cls.center = cls.host.work.center
        cls.host.shell.trigger('view_plan')
        cls.host.shell.trigger('clean_screen')
        assert _setup.wait_for(lambda: not cls.host.bridge.busy and not cls.host.work.rows and cls.host.plan.modules,
                               120000), 'the window has opened and laid its modules'
        cls.plan = cls.win.findChild(QObject, 'plan')
        # the plan alone in the window, laid out (the bar's buttons where they stay)
        assert _setup.wait_for(lambda: cls.plan.width() >= 700, 10000), 'the plan has the window'

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def item(self, name):
        found = [i for i in items(self.win.contentItem()) if i.objectName() == name]
        self.assertTrue(found, f'{name} is in the window')
        return found[0]

    def click(self, item, x=None):
        at = item.mapToScene(QPointF(item.width() / 2 if x is None else x, item.height() / 2))
        QTest.mouseClick(self.win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, at.toPoint())

    def on_and_done(self):
        if not self.sun.on:
            self.click(self.item('planView-sun_map'), 4)
        self.assertTrue(_setup.wait_for(lambda: self.sun.done or bool(self.sun.error), COMPUTE_MS), 'the map is done')
        self.assertEqual(self.sun.error, '')
        self.drawn()

    def drawn(self):
        """What SunMap told is drawn a piece per turn of the events (plan_map._told): until nothing is left."""
        self.assertTrue(_setup.wait_for(lambda: not self.bridge.drawing), 'the plan is drawn')

    @timed('no call of the window over 5 ms')
    def test_1_the_window_stays_free_while_the_map_is_computed(self):
        # The calls: every piece of the map's work on the window's thread (the deliveries, the pictures one surface
        # at a time, the rows, the modules, the legend, the gestures) under 5 ms, asserted everywhere. The beat (50
        # ms): asserted on a graphics API (on screen, Direct3D 11 on Windows: the frames are drawn on the render
        # thread); off screen Qt's software renderer draws the plan on the window's thread, 30-50 ms a frame with or
        # without a job, so there it would measure the renderer, not the map: printed beside the beat of the same
        # window without the map for as long, not asserted (study 48, chapter 5; measured on 14/11/2026, in
        # docs/quick/stato/r33-mappa.md: on screen 11,7-15,8 ms with the map, 6,7-9,7 ms without).
        # The window is let settle first: just opened, it makes the forms of Properties ahead (warmForms, R465) and
        # one of them held its thread 255-281 ms inside this block, which the beat printed as the map's.
        # The items are found before the block: walking the window's items from Python holds its thread 150-300 ms
        # (measured on 13/11/2026 with a sampler of the main thread's stack: test_sun_map.items), the test's own stall.
        # The tests' check of the photo (MERIDIANA_CHECK_PHOTO, tests/_setup.py: every session.photo() compared with a
        # photo made again of the project) is off inside the block: it is a whole photo_of on the window's thread that
        # the program never makes, 1-2 ms of sun_map.on on Rho (measured with cProfile, 14/11/2026). The other tests of
        # this module keep it.
        import time
        from unittest import mock
        from meridiana.app import session as session_module
        button, layer = self.item('planView-sun_map'), self.item('sunMapLayer')
        self.assertTrue(settled(self.win), 'the window has drawn the frames of its opening')
        beat = None if software_frames(self.win) else 50
        start = time.perf_counter()
        with mock.patch.object(session_module, 'CHECK_PHOTO', False), \
                window_stays_free(self.center, call_ms=5, beat_ms=beat) as seen:
            self.click(button, 4)
            self.assertTrue(self.sun.on, 'the button turned it on')
            self.assertTrue(self.bridge.busy, 'the job is in hand')
            self.assertTrue(layer.isVisible(), 'the layer is in view')
            self.assertTrue(_setup.wait_for(lambda: self.sun.done or bool(self.sun.error), COMPUTE_MS), 'the map is done')
            self.drawn()
        spent = time.perf_counter() - start
        self.bridge.setOn(False)
        with window_stays_free(self.center, call_ms=5, beat_ms=None) as base:
            end = time.perf_counter() + spent
            _setup.wait_for(lambda: time.perf_counter() >= end, int(spent * 1000) + 5000)
        where = 'beat not asserted: software renderer' if beat is None else f'beat asserted under {beat} ms'
        print(f'\nsun map, the guard ({where}): {seen}\nthe same window without the map, {spent:.1f} s: {base}')
        self.assertGreater(seen.calls, len(self.sun.surfaces))
        self.bridge.setOn(True)

    def test_2_the_images_come_laid_on_their_surfaces(self):
        self.on_and_done()
        model = self.bridge.model
        rows = [r for r in model.rows if r['coloured']]
        self.assertTrue(rows, 'some surface is coloured')
        for row in rows:
            level = self.sun.level_of(row['sid'])
            k = row['scale']
            self.assertEqual((row['rows'], row['cols']), (level['shape'][0] * k, level['shape'][1] * k))
            self.assertTrue(row['source'].startswith('image://sunmap/'))
            # the matrix lays the corner (0, 0) of the image on the corner of the grid, on the plan
            x0, y0, *_rest = self.sun.surfaces[row['sid']].transform(level)
            self.assertAlmostEqual(row['matrix'][2], x0, places=6)
            self.assertAlmostEqual(row['matrix'][5], -y0, places=6)
        images = [i for i in items(self.win.contentItem()) if i.objectName() == 'sunMapImage' and i.isVisible()]
        self.assertTrue(_setup.wait_for(lambda: all(i.property('progress') == 1.0 for i in images)), 'the images are read')
        self.assertEqual(len([i for i in images if i.property('source').toString()]), len(rows))
        # the shed has its obstacles: tiles under them, hatched on its surface
        self.assertTrue(any(r['under'] for r in rows), 'the tiles under the obstacles are hatched')
        # the image the plan shows is the one painted for the row (TheImage checks the cut on the contour)
        from PySide6.QtCore import QSize
        row = rows[0]
        image = self.bridge.images.requestImage(row['source'].rsplit('/', 1)[1], QSize(), QSize())
        self.assertEqual((image.width(), image.height()), (row['cols'], row['rows']))
        self.assertEqual(image.pixelColor(image.width() // 2, image.height() // 2).alpha(), 255)

    def test_3_the_legend_has_the_six_classes_decided(self):
        self.on_and_done()
        self.bridge.setQuantity('loss')
        self.drawn()
        legend = self.item('sunMapLegend')
        self.assertTrue(legend.isVisible())
        self.assertEqual(list(legend.property('limits')), ['0', '2', '5', '10', '20', '40', '100'])
        colours = legend.property('colors').toVariant()
        self.assertEqual(len(colours), 6)
        self.assertEqual(len(set(colours)), 6, 'six shades')
        self.assertEqual(len(im.LOSS_CLASSES), 7)

    def test_4_the_figures_under_the_pointer_are_the_maps(self):
        self.on_and_done()
        from shapely.geometry import Point, Polygon
        modules = [Polygon([(p.x(), -p.y()) for p in m['points']]) for m in self.host.plan.modules]
        # a point of a roof with its figures and no module over it (a module's own figures are the module's)
        spots = [(x + 0.25, y + 0.25) for x in range(0, 100) for y in range(0, 35)]
        x, y = next((x, y) for x, y in spots if self.sun.value_at(x, y) is not None
                    and not any(m.buffer(0.3).contains(Point(x, y)) for m in modules))
        at = self.plan.mapToScene(self.screen(x, y))
        QTest.mouseMove(self.win, at.toPoint())
        self.assertTrue(_setup.wait_for(lambda: self.bridge.pointerText != ''), 'the figures are said')
        px, py = self.bridge.last                         # where the plan put the pointer: within a pixel of (x, y)
        self.assertLess(abs(px - x) + abs(py - y), 0.5)
        self.assertEqual(self.bridge.pointerText, self.bridge._figures(self.sun.value_at(px, py)))
        tip = self.win.findChild(QObject, 'moduleTip')
        self.assertEqual(tip.property('text'), self.bridge.pointerText, 'said at the pointer, as the modules are')

    def screen(self, x, y):
        from PySide6.QtCore import Q_ARG, Q_RETURN_ARG, QMetaObject
        p = QMetaObject.invokeMethod(self.plan, 'screen', Qt.ConnectionType.DirectConnection, Q_RETURN_ARG('QVariant'),
                                     Q_ARG('QVariant', x), Q_ARG('QVariant', y))
        return p if isinstance(p, QPointF) else QPointF(p.x(), p.y())

    def test_5_what_is_shown_and_the_scale_start_no_job(self):
        self.on_and_done()
        handle, before = self.sun.handle, self.center.stats()['calls']
        keys = {r['sid']: r['source'] for r in self.bridge.model.rows if r['coloured']}
        for quantity in ('year', 'hours', 'loss'):
            self.bridge.setQuantity(quantity)
        self.bridge.setScale('viridis')
        self.drawn()
        self.assertIs(self.sun.handle, handle, 'no other job')
        self.assertFalse(self.sun.busy)
        self.assertFalse(self.host.work.rows, 'nothing in the bar')
        after = {r['sid']: r['source'] for r in self.bridge.model.rows if r['coloured']}
        self.assertEqual(keys.keys(), after.keys())
        self.assertTrue(all(keys[k] != after[k] for k in keys), 'the images made again')
        self.assertGreaterEqual(self.center.stats()['calls'], before)
        self.bridge.setScale('amber')
        self.drawn()

    def test_6_a_change_leaves_the_old_map_dimmed_until_the_new_one(self):
        self.on_and_done()
        session = self.host.bridge.session
        vent = next(e for e in session.project.exclusions if e.kind == 'vent')

        def move(project):
            e = next(x for x in project.exclusions if x.id == vent.id)
            e.ring = [[x + 2.0, y] for x, y in e.ring]
        session.edit('Move the vent', move)
        self.assertTrue(_setup.wait_for(lambda: self.sun.changing, 5000), 'dimmed at once, before the plan of the change comes')
        self.drawn()
        self.assertTrue(any(r['stale'] for r in self.bridge.model.rows), 'the shed is to be updated')
        stale = [r for r in self.bridge.model.rows if r['stale']]
        self.assertTrue(all(r['coloured'] and r['source'] for r in stale), 'the old map stays')
        self.assertTrue(all('\n' in r['label'] for r in stale), 'with its words')
        self.assertTrue(_setup.wait_for(lambda: self.sun.done and not any(r['stale'] for r in self.bridge.model.rows),
                                        COMPUTE_MS), 'the new map came')

    def test_7_the_modules_are_coloured_by_class(self):
        self.on_and_done()
        self.bridge.setColour('auto')
        self.assertTrue(_setup.wait_for(lambda: bool(self.bridge.modulePaths)), 'the modules are coloured')
        batch = self.item('sunMapModules')
        self.assertTrue(batch.isVisible())
        fills = {p['fill'] for p in self.bridge.modulePaths}
        self.assertLessEqual(len(fills), 6)

    def test_8_off_cancels_the_job(self):
        if self.sun.on:
            self.click(self.item('planView-sun_map'), 4)
        self.assertFalse(self.sun.on)
        self.bridge.setDay('06-21')
        self.click(self.item('planView-sun_map'), 4)
        self.assertTrue(self.sun.on and self.sun.busy)
        handle = self.sun.handle
        self.click(self.item('planView-sun_map'), 4)
        self.assertFalse(self.sun.on)
        self.assertFalse(handle.active, 'the job is cancelled')
        self.assertTrue(_setup.wait_for(lambda: not self.host.work.rows), 'its row is gone from the bar')
        self.assertFalse(self.item('sunMapLayer').isVisible())
        self.bridge.setDay('12-21')

    @timed('the only call over 5 ms is the one made slow')
    def test_9_a_slow_picture_makes_the_guard_red(self):
        # what the guard of test_1 is written for: a picture that holds the window's thread past 5 ms is caught, with
        # its name (checked on 13/11/2026 with 8 ms: red, «sun_map.surface»)
        import time
        from unittest import mock
        from meridiana.gui.backend import plan_map
        self.on_and_done()
        real = plan_map.image_of

        def slow(*args):
            end = time.perf_counter() + 0.008
            while time.perf_counter() < end:
                pass
            return real(*args)
        with mock.patch.object(plan_map, 'image_of', slow):
            with self.assertRaises(AssertionError) as caught:
                with window_stays_free(self.center, call_ms=5, beat_ms=None):
                    self.bridge.setScale('viridis')
                    self.drawn()
        self.assertIn('sun_map.surface', str(caught.exception))
        self.bridge.setScale('amber')
        self.drawn()


    def test_9b_a_turn_that_changes_nothing_tells_the_qml_nothing(self):
        # named to run after test_9 (unittest sorts the names: «test_10» would run before «test_1», leaving the map on
        # for test_1's click, which then turned it off)
        # every signal of the bridge has the QML evaluate its bindings again: a turn of the drawing (a surface, the
        # legend, the state) whose figures and state are those already shown must emit none (sun_map.legend was
        # 5,5-6,4 ms on screen with an emit at every turn, 14/11/2026)
        self.on_and_done()
        self.drawn()
        heard = []
        signals = {'changed': self.bridge.changed, 'legendChanged': self.bridge.legendChanged,
                   'modulesChanged': self.bridge.modulesChanged, 'dataChanged': self.bridge.model.dataChanged,
                   'rowsInserted': self.bridge.model.rowsInserted, 'rowsRemoved': self.bridge.model.rowsRemoved}
        listeners = {name: (lambda *_a, n=name: heard.append(n)) for name in signals}
        for name, signal in signals.items():
            signal.connect(listeners[name])
        try:
            self.bridge._told(set(self.sun.surfaces))       # what SunMap says when a level comes again, the same
            self.drawn()
            self.bridge._rows()                             # what the bar's rows say when they change, the same state
            self.bridge._timed('sun_map.legend', self.bridge._legend_and_state)
        finally:
            for name, signal in signals.items():
                signal.disconnect(listeners[name])
        self.assertEqual(heard, [], 'nothing told to the QML')
        # and a real change is told: the quantity
        told = []
        self.bridge.changed.connect(lambda: told.append(self.bridge.quantity))
        self.bridge.setQuantity('year')
        self.drawn()
        self.bridge.setQuantity('loss')
        self.drawn()
        self.assertEqual(told, ['year', 'loss'], 'once for each change of the state')


class TheImage(unittest.TestCase):
    """The image of a surface: the tiles of the border cut on the contour, those under an obstacle hatched."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_border_tiles_do_not_leave_the_surface(self):
        import numpy as np
        from meridiana.app import sun_map_image
        from meridiana.gui.backend import plan_map
        classes = np.zeros((4, 4), dtype=np.uint8)
        classes[2, 0] = im.UNDER
        table = plan_map.lut(plan_map.palette('amber', 'loss', 6))
        k = 8
        triangle = np.array([[0.0, 0.0], [4.0, 0.0], [0.0, 4.0]])          # half of the grid, on columns and rows
        # the raster as the job's process makes it (the geometry), the colours laid as the window lays them
        raster = sun_map_image.raster(triangle, classes.shape, np.ones((4, 4), dtype=bool), classes == im.UNDER, k)
        image, _words = plan_map.image_of(classes, table, raster)
        self.assertEqual((image.width(), image.height()), (32, 32))
        self.assertEqual(image.pixelColor(4, 4).alpha(), 255, 'inside the contour: the tile')
        self.assertEqual(image.pixelColor(28, 28).alpha(), 0, 'past the contour, in the same tile grid: nothing')
        self.assertEqual(image.pixelColor(13, 13).name(), plan_map.palette('amber', 'loss', 6)[0], 'class 0, lightest')
        hatch = {image.pixelColor(x, y).name() for y in range(16, 24) for x in range(0, 8)}
        self.assertEqual(hatch, {theme_colours('under'), theme_colours('under_line')}, 'under an obstacle: hatched')


def theme_colours(name):
    from meridiana.app.interface import theme_colors
    return theme_colors.SUN_MAP[name]


if __name__ == '__main__':
    unittest.main()
