"""R598, study 48 chapter 6 steps 1 and 7: the plant after a change is a job of the mechanism (app/plant_job.py), at home
in the layout's process; before, a QRunnable of the window's pool that held the interpreter while the views took the
layout (a view's 20 ms became 146-175 ms on Rho). The window is the real one, off screen, with the plan.

- The guard of the window (chapter 5) around a true Canc of a module in a string: from the gesture to the end of the
  plant no call of the plant's job on the window's thread (submit, restart, build, on_done) takes more than 5 ms; the
  pieces of what the page does with the answer are printed with their numbers.
- During the gesture no thread of the window's pool computes the plant: plant.build with its checks is never called in
  the window's process, nor a PlantJob of the build.
- The page shows the plant of plant.build called directly on the project in hand, and the checks read the same plant
  (made once in the process, app/plant_job.shared)."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import _setup
from _fixtures import clear_sky_meteo, mixed, write_cache
from meridiana.app import checks_job
from meridiana.app import session as session_module
from meridiana.app.session import photo_of, project_from
from meridiana.core.energy import faces, plant
from meridiana.gui.application import QuickWindow, create_app
from meridiana.gui.backend import plant_jobs
from meridiana.gui.backend.plant_presenter import present
from quick.aiuti.finestra_libera import settled, software_frames, window_stays_free
from quick.aiuti.tempi import timed

# the calls of the plant's job on the window's thread, asserted under 5 ms: its submit and start (restart, after the
# quiet), its request (build), its answer (on_done)
ONLY = ("submit:plant", "restart:plant", "cancel:plant", "plant.on_done", "plant.build", "plant.on_failed")
# what the page does with the answer, in pieces of the window's turns (PlantBackend: the page's lists, the strings on
# the plan and the summary, Meridiana's strings written down, the page's signals to the QML): printed, not asserted
PIECES = ("plant.present", "plant.wiring", "plant.adopt", "plant.signals", "tell:PlantBackend.")


class PlantFree(unittest.TestCase):
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
        cls.plant = cls.host.parts.controllers['plant']
        cls.panel = cls.host.parts.controllers['checks']
        cls.bridge.configure_background(enabled=False)      # the year in the background is a job of its own
        cls.win = cls.host.window
        cls.win.resize(1400, 900)
        cls.win.show()
        cls.bridge.recompute()              # as the program at its start: the year, the layouts, the warm process

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def idle(self) -> bool:
        return (not self.bridge.busy and self.bridge._layout is None and not self.session.telling()
                and not self.bridge.checks_feed.busy() and not self.plant.busy)

    def direct(self):
        sim = (self.session.energy or {}).get('sim')
        hot = max(a['t_cell_max'] for a in sim.arrays) if sim is not None else None
        power = sim.hourly.p_dc.to_numpy() if sim is not None else None
        return plant.build(project_from(photo_of(self.session.project)), self.session.good_results(),
                           t_cell_max_year=hot, p_dc_hourly=power, exposure=faces.year_of(sim))

    @timed('no call of the window over its few ms')
    def test_a_canc_of_a_module_in_a_string_the_plant_stays_off_the_windows_thread(self):
        self.assertTrue(_setup.wait_for(self.idle, 180000), 'the opening of the window has ended')
        runs = (self.session.project.energy.get('strings') or {}).get('runs') or []
        strung = {k for r in runs for k in r['modules']}
        self.assertTrue(strung, "Meridiana's strings written down at the opening")
        sf = next(s for s in self.session.project.subfields if any(k.startswith(f'{s.id}/') for k in strung))
        module = next(m for m in self.session.results[sf.id].modules if f'{sf.id}/{m.key}' in strung)
        self.host.plan.editor.select('subfield', sf.id, module.key)
        before = len(self.session.results[sf.id].modules)
        self.assertTrue(_setup.wait_for(self.idle, 180000), 'the selection told')
        self.assertTrue(settled(self.win), 'the window has settled')
        window = threading.get_ident()
        built, jobs_run = [], []
        real_build, real_run = plant.build, plant_jobs.PlantJob.run

        def build(*args, **kwargs):
            built.append((threading.get_ident() == window, kwargs.get('check', True)))
            return real_build(*args, **kwargs)

        def run(job):
            jobs_run.append(job.kind)
            return real_run(job)
        with mock.patch.object(session_module, 'CHECK_PHOTO', False), \
                mock.patch.object(plant, 'build', build), mock.patch.object(plant_jobs.PlantJob, 'run', run), \
                window_stays_free(self.center, call_ms=5, beat_ms=None, only=ONLY) as seen:
            self.host.plan.key('Delete')
            self.assertTrue(_setup.wait_for(lambda: len(self.session.results[sf.id].modules) == before - 1
                                            and self.idle(), 180000), 'the Canc, its layout, its plant')
        by_name = self.center.stats()['by_name']
        mine = {k: round(v * 1000, 2) for k, v in by_name.items() if k.startswith(ONLY)}
        pieces = {k: round(v * 1000, 2) for k, v in by_name.items() if k.startswith(PIECES)}
        print(f'\nplant after the Canc: {seen}; software frames: {software_frames(self.win)}\n'
              f'the plant\'s job (ms): {mine}\nwhat the page does with it (ms): {pieces}\n'
              f'still over 5 ms (other steps): {seen.over(5)}\nplant.build in the window: {built}',
              file=sys.stderr)
        self.assertIn('plant.on_done', by_name, 'the plant came from its job')
        self.assertIn('plant.build', by_name)
        self.assertIn('plant.present', by_name, 'and the page took it')
        self.assertNotIn('build', jobs_run, 'no PlantJob of the build on the window\'s pool')
        self.assertEqual([b for b in built if b[1]], [], 'plant.build with its checks never in the window\'s process')
        self.assertEqual([p.name for p in self.center.runner.processes()], ['layout'],
                         'the plant in the layout\'s process, no other')
        # the same plant as before: the page's lists are those of plant.build on the project in hand
        direct = self.direct()
        self.assertEqual(self.plant.data, present(direct, self.session.project))
        project = project_from(photo_of(self.session.project))
        items, extras, _notes = checks_job.gather_session(project, self.session.results, self.session.energy)
        self.assertEqual(self.panel.items, items, 'the checks of the plant made once')


if __name__ == '__main__':
    unittest.main()
