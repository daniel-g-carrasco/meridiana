"""R598, study 48 chapter 6 step 6: the checks are one job of the mechanism (app/checks_job.py), at home in the layout's
process, for the bridge's rows and the Checks panel. The window is the real one, off screen, with the plan.

- The guard of the window (chapter 5) around a true Canc of a module and around a change of a name only: from the
  gesture to the end of the checks no call of the checks on the window's thread (submit, restart, build, on_done,
  the job's listener, the bridge's and the panel's pieces, the panel's listener) takes more than 5 ms. The others
  (the layout's views, later steps) are printed with their numbers, not asserted.
- The rows the bridge and the panel show are those of checks.gather and gather_session on the project in hand.
- The year's bar does not say «Computing…» for the checks alone: the bridge is not busy with them, and their row in
  the one bar is their own («Checks»)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup
from _fixtures import clear_sky_meteo, mixed, write_cache
from meridiana.app import checks_job
from meridiana.app import session as session_module
from meridiana.app.session import photo_of, project_from
from meridiana.core.rules import checks
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.finestra_libera import settled, software_frames, window_stays_free
from quick.aiuti.tempi import timed

# the calls of the checks on the window's thread, asserted under 5 ms: the job's submit and start (restart, after the
# quiet), its request (build), its answer (on_done), the job's listener of the session (checks.changed, told as a
# piece of a layout's round: tell:Feed), the bridge's rows and the panel's rows (checks.bridge, checks.panel), the
# panel's listener (checks.related, tell:ChecksBackend)
#
# Not asserted, printed: checks.panel.state, the panel's signal for the rest (counts, title): its listeners are the
# QML bindings (2-3 ms) and Inspectors.publish, whose plan.setMarks takes 4 ms (gui/backend/properties_part.py and
# plan.py, the Properties' and the plan's: measured 14/11/2026 with cProfile, 6,6-7,9 ms in all off screen).
ONLY = ("submit:checks", "restart:checks", "cancel:checks", "checks.on_done", "checks.build", "checks.changed",
        "checks.bridge", "checks.related", "checks.panel.items", "checks.panel.rows", "tell:Feed.",
        "tell:ChecksBackend.")


class ChecksFree(unittest.TestCase):
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
        # not layouts_answer(): a sub-field's name is in its layout key (model.layout_key, on the base too), so after a
        # rename the layouts in hand never «answer», though nothing is laid out for a name (R443)
        return (not self.bridge.busy and self.bridge._layout is None and not self.session.telling()
                and not self.bridge.checks_feed.busy())

    def wait_idle(self, what: str):
        self.assertTrue(_setup.wait_for(self.idle, 180000), what)

    def assert_rows_of_the_project(self):
        project = project_from(photo_of(self.session.project))
        s = self.session
        self.assertEqual(self.bridge._checks, [vars(i) for i in checks.gather(project, s.results, s.energy)])
        items, extras, _notes = checks_job.gather_session(project, s.results, s.energy)
        self.assertEqual(self.panel.items, items)
        self.assertEqual(self.panel.extras, extras)

    def guarded(self, gesture, what, done):
        """`gesture()` inside the guard, until `done()` and the window idle."""
        self.wait_idle('the window is idle')
        self.assertTrue(settled(self.win), 'the window has settled')
        with mock.patch.object(session_module, 'CHECK_PHOTO', False), \
                window_stays_free(self.center, call_ms=5, beat_ms=None, only=ONLY) as seen:
            gesture()
            self.assertTrue(_setup.wait_for(lambda: done() and self.idle(), 180000), what)
        by_name = self.center.stats()['by_name']
        mine = {k: round(v * 1000, 2) for k, v in by_name.items() if k.startswith(ONLY)}
        print(f'\nchecks after {what}: {seen}; software frames: {software_frames(self.win)}\n'
              f'the checks\' calls (ms): {mine}\nstill over 5 ms (other steps): {seen.over(5)}', file=sys.stderr)
        self.assertIn('checks.on_done', by_name)
        self.assertIn('checks.build', by_name)
        self.assertIn('checks.panel.items', by_name, 'the panel had its answer')
        self.assertIn('checks.bridge', by_name, 'and the bridge')
        self.assert_rows_of_the_project()
        return seen

    @timed('no call of the window over 5 ms')
    def test_1_a_canc_the_checks_stay_off_the_windows_thread(self):
        self.wait_idle('the opening of the window has ended')
        sf = self.session.project.subfields[0]
        module = self.session.results[sf.id].modules[5]
        self.host.plan.editor.select('subfield', sf.id, module.key)
        before = len(self.session.results[sf.id].modules)
        self.guarded(lambda: self.host.plan.key('Delete'), 'the Canc, its layout and its checks',
                     lambda: len(self.session.results[sf.id].modules) == before - 1)

    @timed('no call of the window over 5 ms')
    def test_2_a_name_only_its_checks_and_no_layout(self):
        layouts = []
        real = self.bridge._ask_layout
        self.bridge._ask_layout = lambda: (layouts.append(True), real())
        self.addCleanup(setattr, self.bridge, '_ask_layout', real)
        sid = self.session.project.subfields[0].id
        self.guarded(lambda: self.session.edit('rename', lambda p: setattr(p.subfields[0], 'name', 'Renamed')),
                     'a new name and its checks', lambda: self.panel.names.get(('subfield', sid)) == 'Renamed')
        self.assertEqual(layouts, [], 'a name lays out nothing')

    @timed('no call of the window over 5 ms')
    def test_3_the_checks_alone_are_not_the_years_computing(self):
        self.wait_idle('the window is idle')
        seen = []
        self.work.rowsChanged.connect(lambda: seen.append((self.bridge.busy, [r['title'] for r in self.work.rows])))
        sid = self.session.project.subfields[0].id
        self.session.edit('rename', lambda p: setattr(p.subfields[0], 'name', 'Named again'))
        # told after the frame (R547: the name is in the layout key): the checks start then
        self.assertTrue(_setup.wait_for(self.bridge.checks_feed.busy, 10000), 'the checks asked')
        self.assertFalse(self.bridge.busy, 'the bridge is not busy with the checks')
        self.assertTrue(_setup.wait_for(lambda: self.panel.names.get(('subfield', sid)) == 'Named again'
                                        and self.idle(), 180000), 'the checks came')
        titles = {t for _busy, rows in seen for t in rows}
        self.assertFalse(any(busy for busy, _rows in seen), 'never busy while only the checks worked')
        self.assertTrue(titles, 'the checks had their row')
        self.assertTrue(titles <= {'Verifiche', 'Checks'}, f'only the checks\' own row, not «Computing…»: {titles}')


if __name__ == '__main__':
    unittest.main()
