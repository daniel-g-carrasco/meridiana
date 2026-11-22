"""R598, study 48 chapter 6 step 1: the layout after a change is a job of the mechanism (app/layout_job.py), in its
process kept warm, on the window's one center (work.py). The window is the real one, off screen, with the plan.

- The guard of the window (chapter 5) around a true Canc of a module in a string: from the gesture to the end of the
  views' round no call of the job on the window's thread (submit, restart, build, on_done, the center's listener)
  takes more than 5 ms. What the views do with the layout is spread a view per turn of the window (session.pieces)
  and timed with each view's name: those still over 5 ms belong to later steps (the plan, the 3D, the checks, the
  pages) and are printed with their numbers, not asserted (ONLY).
- A change while the layout is on its way: the layout of before is never taken, only the last one is, after the
  quiet, and it is the layout of the project as it is (real processes). The same for Undo and Redo.
- Cancel from the bar: the layout of before stays, its sub-fields «to update» (layout_state "stale"), nothing taken."""
import sys
import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import clear_sky_meteo, mixed, write_cache
from meridiana.app import jobs
from meridiana.app.session import photo_of, project_from
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.finestra_libera import settled, software_frames, window_stays_free

# the calls of the layout's job on the window's thread, asserted under 5 ms: its submit, its restart after the quiet,
# its request (build), its answer taken (on_done), its Cancel. The others are measured and printed: the plan's
# overlays (the scene of the strings is made by the job in its process, app/view/plan_wiring.py: 4-11 ms here, from 13;
# 30-40 ms on Rho, from 111-141, the rest is the QML of the overlay), the views told of the layout (tell:<view>: the
# plan, the 3D, the checks, the pages), what the bridge hands to the QML (bridge.*: its scene, the checks asked, the
# status bar's line) and the bar's rows, which a thread of the window holding the interpreter can make wait (measured
# 14/11/2026: 30-100 ms of wait for 0,5 ms of work while the checks' or the plant's thread computes: steps 6 and 7)
# R598 (r35-ciclo-giro): the round after the frame of the Canc (R547) is now in the block too, a view per piece
# (`tell:<view>`, as the views told of the layout); the views brought under 5 ms in it are asserted as well: the
# results' controller (the pages greyed by `stale` alone, no longer the three pages whole: 40-80 ms on screen)
ONLY = ("submit:layout", "restart:layout", "layout.", "cancel:layout", "warm:layout", "changed",
        "tell:ResultsController.")


class LayoutFree(unittest.TestCase):
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
                and self.session.layouts_answer() and not self.bridge.checks_feed.busy())

    def wait_idle(self, what: str):
        self.assertTrue(_setup.wait_for(self.idle, 180000), what)

    def laid(self) -> dict:
        return {sid: [m.key for m in r.modules] for sid, r in self.session.good_results().items()}

    def of_the_project(self) -> dict:
        results, _keys, _laid = jobs.layout_of(project_from(photo_of(self.session.project)))
        return {sid: [m.key for m in r.modules] for sid, r in results.items() if not isinstance(r, Exception)}

    def strung(self):
        """The designer's strings on the modules of the shed, and a module of them selected on the plan."""
        self.wait_idle('the opening of the window has ended')
        sf = self.session.project.subfields[0]
        mods = self.session.results[sf.id].modules
        runs = [{"inverter": 1, "mppt": 1, "modules": [f"{sf.id}/{m.key}" for m in mods[:12]]}]
        self.session.edit('strings', lambda p: p.energy.__setitem__('strings', {'runs': runs}))
        self.wait_idle('the strings told')
        return sf, mods[5]

    def test_1_the_window_stays_free_from_a_canc_to_the_end_of_the_views_round(self):
        sf, module = self.strung()
        self.host.plan.editor.select('subfield', sf.id, module.key)
        self.assertTrue(settled(self.win), 'the window has settled')
        before = len(self.session.results[sf.id].modules)
        notices, answers = [], []
        self.bridge.noticed.connect(notices.append)
        came = self.bridge._layout_came
        self.bridge._layout_came = lambda answer, stale: (answers.append(answer), came(answer, stale))
        self.addCleanup(setattr, self.bridge, '_layout_came', came)
        with window_stays_free(self.center, call_ms=5, beat_ms=None, only=ONLY) as seen:
            self.host.plan.key('Delete')
            self.wait_idle('the layout of the Canc came back and every view was told')
        self.bridge.noticed.disconnect(notices.append)
        # the plan's strings made in the layout's process with the layout, and taken by the plan (plan_wiring)
        self.assertTrue(answers and answers[-1]['wiring'] is not None, 'the strings made with the layout')
        self.assertIsNone(self.session.wiring_offer, 'and taken by the plan')
        self.assertEqual(self.host.plan.wirePaths,
                         self.host.plan.editor.wiring_scene(self.host.plan._mpp, wiring_on=True,
                                                            states=self.host.plan._string_states,
                                                            full=True)['paths']['wires'])
        names = seen.over(5)
        overlays = self.center.stats()['by_name'].get('plan.overlays', 0) * 1000
        told = {k: round(v, 1) for k, v in sorted(seen.left.items()) if k.startswith('tell:')}
        print(f'\nlayout after a Canc: {seen}; software frames: {software_frames(self.win)}\n'
              f'plan.overlays {overlays:.1f} ms; still over 5 ms (later steps): {names}\n'
              f'the views told, a piece each (R547 and the layout): {told}', file=sys.stderr)
        self.assertEqual(len(self.session.results[sf.id].modules), before - 1)
        self.assertEqual(self.laid(), self.of_the_project())
        self.assertEqual(self.session.realigned, [('1.1.1', 1, [sf.name])], 'the string lost the module')
        self.assertNotIn(f'{sf.id}/{module.key}', self.session.project.energy['strings']['runs'][0]['modules'])
        self.assertEqual(notices, [self.session.realigned_text(self.session.realigned)], 'R442: said in the bar')
        self.assertTrue(any(k.startswith('tell:') for k in seen.left), 'the views told a piece each')
        by_name = self.center.stats()['by_name']
        self.assertIn('layout.on_done', by_name)
        self.assertIn('layout.build', by_name)

    def test_1b_the_plans_strings_are_never_made_on_the_windows_thread(self):
        """R598 (passo 1b): a Canc of a module in a string, the module added back from the plan's menu, Undo; each to
        the end of the views' round and of the plant. The plan never makes its scene of the strings on the window's
        thread: inside the gesture it keeps the scene it has (a layout brings the one made with it), at the layout it
        takes the job's, at the plant it gives the names their states (plan_wiring._restate). What it draws after each
        is what a scene made anew on the project in hand draws. The plant's strings handed to the plan
        (plant.wiring) are asserted under 5 ms with the layout's calls."""
        from meridiana.app.view import plan_wiring
        plant = self.host.parts.controllers['plant']

        def calm():
            return self.idle() and not plant.busy
        sf, module = self.strung()
        self.assertTrue(_setup.wait_for(calm, 180000), 'the plant of the strings')
        plan = self.host.plan
        plan.editor.select('subfield', sf.id, module.key)
        self.assertTrue(settled(self.win), 'the window has settled')

        def add():
            plan.contextAt(*module.centre)
            plan.contextCommand('add_module')
        gestures = (('Canc', lambda: plan.key('Delete')), ('add', add), ('Undo', self.session.undo.undo))
        for name, gesture in gestures:
            scene = plan.editor._wiring_scene
            builds = scene.builds
            with window_stays_free(self.center, call_ms=5, beat_ms=None, only=ONLY + ('plant.wiring',)) as seen:
                gesture()
                self.assertTrue(_setup.wait_for(calm, 180000), f'{name}: laid out, told and its plant')
            print(f'\n{name}: {seen}; plant.wiring {self.center.stats()["by_name"].get("plant.wiring", 0) * 1000:.1f} '
                  f'ms, plan.overlays {self.center.stats()["by_name"].get("plan.overlays", 0) * 1000:.1f} ms; '
                  f'still over 5 ms: {seen.over(5)}', file=sys.stderr)
            self.assertIs(plan.editor._wiring_scene, scene)
            self.assertEqual(scene.builds, builds, f'{name}: no scene of the strings made on the window')
            self.assertIsNone(self.session.wiring_offer, f'{name}: the scene made with the layout taken')
            made = plan_wiring.WiringScene().build(plan.editor, plan._mpp, wiring_on=True, states=plan._string_states)
            self.assertEqual(plan.wirePaths, made['paths']['wires'], name)
            self.assertEqual(plan.wireFillPaths, made['paths']['wireFills'], name)
            self.assertEqual(plan.unwiredJoined, made['paths']['unwired'], name)
            self.assertEqual(plan.stringLabels, made['layers']['stringLabels'], name)
            states = {s.run: s.state for s in getattr(plant.state, 'strings', []) if getattr(s, 'run', -1) >= 0}
            self.assertEqual(plan._string_states, states, f'{name}: the states of the plant in hand')
        self.assertEqual(self.laid(), self.of_the_project())

    def on_its_way(self, change):
        """`change(handle)` made right after the next layout's job has gone to its process (after the quiet), before
        its answer can come: in the jobs' turn that sends it, as a gesture made then would find it (a wait that looks
        at the state now and then misses it: the job can end before the next look). The handle of that job."""
        from meridiana.app import layout_job
        launch, seen = self.center._launch, []

        def launched(handle):
            launch(handle)
            if handle.kind is layout_job.KIND and not seen:
                seen.append(handle)
                change(handle)
        self.center._launch = launched
        try:
            self.assertTrue(_setup.wait_for(lambda: bool(seen), 30000), 'the layout started')
        finally:
            self.center._launch = launch
        return seen[0]

    def counted(self) -> list:
        """The layouts taken (accept_layout from the jobs' layout): their keys."""
        taken, real = [], self.bridge.accept_layout

        def accept(generation, results, keys, *more):
            ok = real(generation, results, keys, *more)
            if ok:
                taken.append(dict(keys))
            return ok
        self.bridge.accept_layout = accept
        self.addCleanup(setattr, self.bridge, 'accept_layout', real)
        return taken

    def shrink(self, metres):
        ring = self.ring
        return lambda p: setattr(p.subfields[0], 'ring', [ring[0], [ring[1][0] - metres, ring[1][1]],
                                                          [ring[2][0] - metres, ring[2][1]], ring[3]])

    def test_2_a_change_while_the_layout_is_on_its_way_keeps_only_the_last(self):
        self.wait_idle('the window is idle')
        self.ring = [list(p) for p in self.session.project.subfields[0].ring]
        came = self.counted()
        self.session.edit('first', self.shrink(4))
        first = self.on_its_way(lambda handle: self.session.edit('second', self.shrink(8)))
        self.wait_idle('the last layout came back')
        self.assertNotEqual(first.state, 'running')
        self.assertEqual(came, [self.session.expected_layout_keys()], 'one layout taken, of the last change')
        self.assertEqual(self.laid(), self.of_the_project())
        self.session.undo.undo()
        self.on_its_way(lambda handle: self.session.undo.undo())
        self.wait_idle('the layout of the undo came back')
        self.assertEqual(self.laid(), self.of_the_project(), 'the layout of the project after both undos')
        self.session.undo.redo()
        self.on_its_way(lambda handle: self.session.undo.redo())
        self.wait_idle('the layout of the redo came back')
        self.assertEqual(self.laid(), self.of_the_project())
        self.assertEqual(len(came), 3, 'one layout taken for each pair of changes, the last of each')
        self.assertEqual(came[-1], self.session.expected_layout_keys())

    def test_2b_a_selection_and_a_canc_half_way_through_the_views_round(self):
        """R598: the round after the frame of a Canc (R547) is told a view per piece; a selection and a second Canc
        made after its first piece find every view told of the first one, in order, and the window ends on the
        project as it is: its layout, Properties on the selection in hand."""
        sf, module = self.strung()
        laid = self.session.results[sf.id].modules
        other = next(m for m in laid if m.key != module.key)
        before = len(laid)
        self.host.plan.editor.select('subfield', sf.id, module.key)
        heard = []
        self.session.subscribe(lambda topics: heard.append((frozenset(topics), self.session.selected_module[1])))
        self.addCleanup(lambda: self.session.listeners.pop())
        tell, done = self.session._tell_one, []

        def one(listener):
            tell(listener)
            if not done and not self.session.layouts_answer():         # a piece of the round of the Canc
                done.append(True)
                self.assertTrue(self.session.telling(), 'the round is half done')
                self.host.plan.editor.select('subfield', sf.id, other.key)
                self.host.plan.key('Delete')
        self.session._tell_one = one
        self.addCleanup(setattr, self.session, '_tell_one', tell)
        self.host.plan.key('Delete')
        self.wait_idle('both deletions laid out and told')
        self.assertTrue(done, 'the second gesture came half way through the round')
        self.assertEqual(len(self.session.results[sf.id].modules), before - 2)
        self.assertEqual(self.laid(), self.of_the_project())
        properties = self.host.parts.controllers['properties']
        self.assertEqual((properties.kind, properties.objectId), ('subfield', sf.id))
        # the last view, still waiting for its piece when the second gesture came: the first Canc heard first, while
        # the module selected after it was not selected yet; then the selection of the other module, then its Canc
        first, _module = heard[0]
        self.assertTrue(any(x.startswith('project:') for x in first), heard)
        self.assertNotEqual(_module, other.key, 'the first Canc heard before the selection made after it')
        chosen = next(i for i, (t, m) in enumerate(heard) if 'selection' in t and m == other.key)
        self.assertTrue(any(any(x.startswith('project:') for x in t) for t, _m in heard[chosen + 1:]),
                        'and the second Canc after the selection')

    def test_3_cancel_from_the_bar_leaves_the_layout_of_before_to_update(self):
        self.wait_idle('the window is idle')
        self.ring = [list(p) for p in self.session.project.subfields[0].ring]
        before = self.laid()
        came = self.counted()
        rows = []

        def cancel(handle):
            row = next(r for r in self.center.rows() if r['slot'] == 'layout')
            rows.append(row['cancellable'])
            self.work.cancel(row['id'])             # the bar's Cancel
            rows.append([r for r in self.center.rows() if r['slot'] == 'layout'])
        self.session.edit('smaller', self.shrink(3))
        job = self.on_its_way(cancel)
        self.assertTrue(_setup.wait_for(lambda: len(rows) == 2, 10000))
        self.assertEqual(rows, [True, []], 'cancellable, and the row goes at once')
        self.assertEqual(job.state, 'cancelled')
        # the process answers its stop (or ends its layout, unheard): nothing of it is taken
        self.assertTrue(_setup.wait_for(lambda: all(p.run is None for p in self.center.runner.processes()), 10000))
        self.assertTrue(_setup.wait_for(lambda: not self.session.telling() and not self.center.pump(), 10000))
        self.assertEqual(came, [])
        self.assertEqual(self.laid(), before, 'the modules of before stay')
        self.assertEqual(self.session.layout_state(self.session.project.subfields[0]), 'stale', 'to be laid again')
        self.session.edit('again', lambda p: setattr(p.subfields[0], 'ring', self.ring))
        self.wait_idle('the next change lays out again')
        self.assertEqual(self.laid(), self.of_the_project())


if __name__ == '__main__':
    unittest.main()
