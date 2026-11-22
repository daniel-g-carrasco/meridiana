"""R598, study 48 chapter 6 step 5: the 3D scene off the window's thread. The window is the real one, off screen, with
the plan and the 3D (off screen it has room for one view at a time: «3D» shows the 3D, «plan» the plan alone).

- The 3D on show, a true Canc of a module in a string: the scene of the change comes from its job in the layout's
  process (app/scene_job.py). The guard of the window (chapter 5) around it, from the gesture to the scene taken: no
  call of the scene's job on the window's thread (submit, restart, build, on_done), nor the 3D's listener told of the
  layout, nor the first two pieces of what the 3D does with the answer (scene.bodies, scene.view), takes more than
  5 ms; the selection's outline made again (scene.selection) and the 3D's listener in the gesture are printed.
  mesh.project_scene is never called in the window's process, on no thread, and the scene shown is the one of
  mesh.project_scene called directly on the project in hand (the same arrays).
- The 3D not on show (the plan alone, a phase without the views) makes nothing for the same Canc: no scene, on no
  thread, and the 3D's listener costs nothing in the gesture nor when the layout comes; shown again, the 3D has the
  scene of the project in hand, and the outline of what was chosen meanwhile."""
import contextlib
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import _setup
from _fixtures import clear_sky_meteo, mixed, write_cache
from meridiana.app import scene_job, session as session_module
from meridiana.app.view import viewaids
from meridiana.core.geometry import mesh
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.finestra_libera import settled, software_frames, window_stays_free

# the calls of the scene's job on the window's thread, the 3D's listener told of the layout (a piece of the window's
# turns) and the first two pieces of what the 3D does with the answer (the bodies to the GPU; the bounds and the lawn
# told to the QML), asserted under 5 ms: 0,01-0,6 ms and 0,5-1,5 ms in five runs off screen (15/11/2026)
ONLY = ("submit:scene", "restart:scene", "scene.build", "scene.on_done", "scene.on_failed", "scene_strings.",
        "tell:SceneBackend.", "scene.bodies", "scene.view")
# the selection's outline made again with the scene that came: 1,9-3,0 ms in those runs, printed, not asserted
PIECES = ("scene.bodies", "scene.view", "scene.selection", "scene.strings")


class SceneFree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.cache = Path(cls.folder.name)
        write_cache(clear_sky_meteo(), cls.cache)
        cls.host = QuickWindow(mixed(), cls.cache, theme={'theme': 'light'}, real_views=True)
        cls.bridge, cls.work = cls.host.bridge, cls.host.work
        cls.center, cls.session = cls.work.center, cls.host.bridge.session
        cls.scene = cls.host.scene
        cls.plant = cls.host.parts.controllers['plant']
        cls.bridge.configure_background(enabled=False)      # the year in the background is a job of its own
        cls.win = cls.host.window
        cls.win.resize(1400, 900)
        cls.win.show()
        cls.bridge.recompute()              # as the program at its start: the year, the layouts, the warm process

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def setUp(self):
        self.win.setProperty('viewMode', '3d')
        self.assertTrue(_setup.wait_for(lambda: self.scene.shown and self.idle(), 180000),
                        f'the 3D on show, at rest: {self.state()}')

    def state(self) -> dict:
        return {'shown': self.scene.shown, 'busy': self.bridge.busy, 'layout': self.bridge._layout is not None,
                'telling': self.session.telling(), 'checks': self.bridge.checks_feed.busy(),
                'plant': self.plant.busy, 'drawing': self.scene.drawing}

    def idle(self) -> bool:
        return (not self.bridge.busy and self.bridge._layout is None and not self.session.telling()
                and not self.bridge.checks_feed.busy() and not self.plant.busy and not self.scene.drawing)

    def a_module_in_a_string(self):
        runs = (self.session.project.energy.get('strings') or {}).get('runs') or []
        strung = {k for r in runs for k in r['modules']}
        self.assertTrue(strung, "Meridiana's strings written down at the opening")
        sf = next(s for s in self.session.project.subfields if any(k.startswith(f'{s.id}/') for k in strung))
        module = next(m for m in self.session.results[sf.id].modules if f'{sf.id}/{m.key}' in strung)
        return sf, module

    def direct(self):
        """mesh.project_scene called here on the project in hand, as the 3D draws it."""
        owners = []
        triangles, table, _edges = mesh.project_scene(self.scene._visual(self.session.project),
                                                      self.session.good_results(), owners=owners)
        return triangles, table, owners

    def assert_scene_in_hand(self):
        triangles, table, owners = self.direct()
        for made, mine in zip(triangles, self.scene.triangles, strict=True):
            np.testing.assert_array_equal(made, mine)
        np.testing.assert_array_equal(table, self.scene.module_table)
        self.assertEqual(owners, self.scene._owners)

    @contextlib.contextmanager
    def canc(self, sf, module, shown):
        """A true Canc of `module` with the 3D on show or not, from the gesture to the scene taken: every call of
        mesh.project_scene in the window's process (`made`), the 3D's listener in the gesture (`at_once`, ms), the
        guard of the window (`seen`)."""
        self.host.plan.editor.select('subfield', sf.id, module.key)
        before = len(self.session.results[sf.id].modules)
        self.win.setProperty('viewMode', '3d' if shown else 'plan')
        self.assertTrue(_setup.wait_for(lambda: self.scene.shown == shown and self.idle(), 180000),
                        f'the views ready: {self.state()}')
        self.assertTrue(settled(self.win), 'the window has settled')
        out = {'made': [], 'at_once': [], 'rebuilds': self.scene.rebuilds}
        real_scene, real_changed = mesh.project_scene, self.scene._changed

        def project_scene(*args, **kwargs):
            out['made'].append(threading.get_ident())
            return real_scene(*args, **kwargs)

        def changed(topics):
            start = time.perf_counter()
            try:
                return real_changed(topics)
            finally:
                out['at_once'].append((time.perf_counter() - start) * 1000)
        changed.__qualname__ = real_changed.__qualname__        # the name of its piece, `tell:SceneBackend._changed`
        lists = (self.session._at_once, self.session.listeners)
        for listeners in lists:
            listeners[listeners.index(real_changed)] = changed
        try:
            with mock.patch.object(session_module, 'CHECK_PHOTO', False), \
                    mock.patch.object(mesh, 'project_scene', project_scene), \
                    window_stays_free(self.center, call_ms=5, beat_ms=None, only=ONLY) as seen:
                self.host.plan.key('Delete')
                self.assertTrue(_setup.wait_for(lambda: len(self.session.results[sf.id].modules) == before - 1
                                                and self.idle(), 180000), 'the Canc, its layout, its scene')
        finally:
            for listeners in lists:
                listeners[listeners.index(changed)] = real_changed
        out['seen'] = seen
        yield out

    def report(self, what, out):
        by_name = self.center.stats()['by_name']
        mine = {k: round(v * 1000, 2) for k, v in by_name.items() if k.startswith(ONLY)}
        pieces = {k: round(v * 1000, 2) for k, v in by_name.items() if k.startswith(PIECES)}
        print(f'\n{what}: {out["seen"]}; software frames: {software_frames(self.win)}\n'
              f'the 3D\'s listener in the gesture (ms): {[round(x, 2) for x in out["at_once"]]}\n'
              f'the scene\'s job and the 3D told of the layout (ms): {mine}\nwhat the 3D does with it (ms): {pieces}\n'
              f'still over 5 ms (other steps): {out["seen"].over(5)}', file=sys.stderr)
        return by_name

    def test_a_canc_with_the_3d_on_show_the_scene_comes_from_its_job(self):
        sf, module = self.a_module_in_a_string()
        with self.canc(sf, module, shown=True) as out:
            pass
        by_name = self.report('the 3D on show, a Canc', out)
        self.assertEqual([], out['made'], 'no scene made in the window\'s process, on no thread')
        self.assertIn('scene.on_done', by_name, 'the scene came from its job')
        self.assertIn('scene.bodies', by_name, 'and the 3D took it')
        self.assertGreater(self.scene.rebuilds, out['rebuilds'])
        # the 3D's listener in the gesture is printed: on show it makes the selection's outline (0,4-5,5 ms here)
        self.assertTrue(out['at_once'], 'the 3D heard the Canc')
        self.assertEqual(['layout'], [p.name for p in self.center.runner.processes()],
                         'the scene in the layout\'s process, no other')
        self.assert_scene_in_hand()

    def test_the_3d_not_on_show_makes_nothing_and_shown_again_has_the_project_in_hand(self):
        sf, module = self.a_module_in_a_string()
        with self.canc(sf, module, shown=False) as out:
            pass
        by_name = self.report('the 3D not on show, a Canc', out)
        self.assertEqual([], out['made'], 'no scene made, on no thread')
        self.assertNotIn('scene.on_done', by_name, 'no scene asked')
        self.assertEqual(out['rebuilds'], self.scene.rebuilds)
        self.assertTrue(out['at_once'] and max(out['at_once']) < 5, f'the 3D\'s listener: {out["at_once"]} ms')
        self.assertIn('tell:SceneBackend._changed', by_name, 'the 3D was told of the layout')
        # shown again: the scene of the project in hand, and the outline of the building chosen meanwhile
        self.host.plan.editor.select('building', sf.building)
        self.assertIn('selection', self.scene._stale, 'no outline made while the 3D is not on show')
        self.win.setProperty('viewMode', '3d')
        self.assertTrue(_setup.wait_for(lambda: self.scene.shown and self.idle(), 180000), 'the 3D again')
        self.assertGreater(self.scene.rebuilds, out['rebuilds'])
        self.assert_scene_in_hand()
        self.assertTrue(self.scene._segments, 'the outline of the building chosen while the 3D was not on show')
        self.assertEqual(set(), self.scene._stale)

    def test_in_the_plant_the_strings_in_3d_come_from_their_job(self):
        sf, module = self.a_module_in_a_string()
        tubes, real = [], self.scene.string_geometry.set_ribbons

        def set_ribbons(made):
            tubes.append(made)
            return real(made)
        self.host.window.showPhase('plant')
        try:
            with mock.patch.object(self.scene.string_geometry, 'set_ribbons', set_ribbons), \
                    mock.patch.object(viewaids, 'string_segments', side_effect=AssertionError('in the window')):
                with self.canc(sf, module, shown=True) as out:
                    pass
            by_name = self.report('the Plant with the 3D on show, a Canc', out)
            self.assertTrue(self.scene.stringsShown)
        finally:
            self.host.window.showPhase('model')
        self.assertIn('scene_strings.on_done', by_name, 'the strings came from their job')
        self.assertIn('scene.strings', by_name, 'and the 3D took them')
        lines, _crosses = viewaids.string_segments(self.session.project, self.session.good_results())
        self.assertTrue(len(lines), 'the strings drawn')
        *made, bounds = scene_job.ribbons(lines)                # the same tubes to the GPU as made here
        *mine, mine_bounds = tubes[-1]
        for a, b in zip(made, mine, strict=True):
            np.testing.assert_array_equal(a, b)
        self.assertEqual(bounds, mine_bounds)

    def test_a_phase_without_the_views_is_not_on_show(self):
        self.host.window.showPhase('production')
        try:
            self.assertTrue(_setup.wait_for(lambda: not self.scene.shown, 30000), 'Production does not show the 3D')
        finally:
            self.host.window.showPhase('model')
        self.assertTrue(_setup.wait_for(lambda: self.scene.shown, 30000), 'Modelling shows it')


if __name__ == '__main__':
    unittest.main()
