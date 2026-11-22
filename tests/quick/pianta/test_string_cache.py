"""R496: stringing by hand without the strings' layers made again at every move; jumps as dashed arcs; levels by
scale. Pure scene and controller, no window."""
import math
import unittest

from meridiana.core.model import model
from meridiana.gui.backend.plan import PlanController
from meridiana.app.view.plan_wiring import JOINED, WiringScene, jump_arc, level_of
from quick.pianta import test_edit_window as edit
from quick.pianta.test_string_drawing import DraftScene

setUpModule = edit.setUpModule       # the window's application: the window tests that follow in the same process


class SceneKept(DraftScene):
    def test_the_scene_is_built_once_while_only_the_pointer_moves(self):
        e = self.editor
        e.start_draft()
        e.click(self.row[0].centre)
        scene = e.wiring_scene(.02)
        built = e._wiring_scene.builds
        for k in range(10):
            e.move((self.row[0].centre[0] + k * .1, self.row[0].centre[1] + 1.0))
            again = e.wiring_scene(.02)
            self.assertIs(again["objects"], scene["objects"], "the same objects: nothing to draw again")
            self.assertEqual(again["band"][2:], [self.row[0].centre[0] + k * .1, -(self.row[0].centre[1] + 1.0)])
        self.assertEqual(e._wiring_scene.builds, built)
        self.assertEqual(scene["band"][:2], [self.row[0].centre[0], -self.row[0].centre[1]], "from the last module")

    def test_another_step_of_the_scale_makes_the_marks_alone(self):
        """R706: at another step of the scale the fills, the lines, the dots and the names are those of the scene in
        hand, the very lists (the plan draws nothing of them again); only what follows the scale is made: the
        arrowheads, the jumps that take a lane, the numbers of the string chosen. And the scene is the one a maker
        that starts from nothing makes. It was made whole at every step: 190-530 ms at 2000 modules."""
        e = self.editor
        modules = self.result.modules
        runs = [{"inverter": 1, "mppt": 1, "modules": ["s1/" + modules[i].key for i in (0, 2, 4)]},
                {"inverter": 1, "mppt": 2, "modules": ["s1/" + modules[i].key for i in (1, 3, 5)]}]
        self.session.project.energy["strings"] = {"runs": runs}
        e.chosen_string = 0
        first = e.wiring_scene(.001)
        maker, size = e._wiring_scene, first["size"]           # the scales by the modules' size on screen
        self.assertEqual(maker.marked, 0)
        self.assertTrue(first["layers"]["wireMarks"], "arrowheads at least: the jumps' arrivals")
        self.assertFalse([o for o in first["layers"]["wires"] if o["kind"] == "string_arrow"])
        for step, mpp in enumerate((size / 80, size / 50, size / 20), 1):
            again = e.wiring_scene(mpp)
            self.assertEqual(again["level"], "near")
            self.assertEqual(maker.marked, step, "the marks alone")
            for name in ("wires", "wireFills", "unwired"):
                self.assertIs(again["paths"][name], first["paths"][name], name)
            self.assertIs(again["layers"]["spots"], first["layers"]["spots"])
            # R707: a dot on each module from 40 px, the first of each string alone below
            self.assertIs(again["layers"]["dots"], first["layers"]["spots" if size / mpp >= 40 else "heads"])
            whole = WiringScene().build(e, mpp)
            self.assertEqual(again, whole, "the scene a maker that starts from nothing makes")
            self.assertNotEqual(again["paths"]["wireMarks"], first["paths"]["wireMarks"], "the marks follow the scale")
        marked = maker.marked
        far = e.wiring_scene(size / 3)
        self.assertEqual(far["level"], "far")
        self.assertEqual(maker.marked, marked + 1, "another level of detail: the marks alone, again")
        self.assertEqual(far["dots"], [], "the dots are kept and not shown")
        self.assertIs(far["layers"]["spots"], first["layers"]["spots"])
        self.assertIs(far["paths"]["wires"], first["paths"]["wires"])
        self.assertEqual(far, WiringScene().build(e, size / 3))

    def test_a_module_added_builds_the_scene_again_and_the_band_follows_it(self):
        e = self.editor
        e.start_draft()
        e.click(self.row[0].centre)
        before = e.wiring_scene(.02)
        e.click(self.row[1].centre)
        after = e.wiring_scene(.02)
        self.assertIsNot(after["objects"], before["objects"])
        self.assertEqual(after["band"][:2], [self.row[1].centre[0], -self.row[1].centre[1]])
        self.assertEqual(len([o for o in after["objects"] if o["kind"] == "string_fill" and o["draft"]]), 2)

    def test_the_scale_only_counts_in_steps(self):
        e = self.editor
        e.start_draft()
        e.click(self.row[0].centre)
        e.wiring_scene(.02)
        built = e._wiring_scene.builds
        e.wiring_scene(.021)
        self.assertEqual(e._wiring_scene.builds, built, "a wheel step of 1.2 inside the same step of 1.5")
        e.wiring_scene(.2)
        self.assertEqual(e._wiring_scene.builds, built + 1)

    def test_other_states_change_the_names_alone_as_a_scene_made_anew_would(self):
        """R598: the plant tells the strings' states (set_string_details): the names take them, the scene is not made
        again, and it is the scene a build with those states makes."""
        e = self.editor
        keys = [m.key for m in self.row[:3]]
        self.session.project.energy["strings"] = {"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/" + k for k in keys]}]}
        before = e.wiring_scene(.02, states={0: "check"})
        built = e._wiring_scene.builds
        after = e.wiring_scene(.02, states={0: "fail"})
        self.assertEqual(e._wiring_scene.builds, built, "not made again")
        self.assertEqual(next(p for p in after["labels"] if p["kind"] == "name")["state"], "fail")
        self.assertIs(after["paths"], before["paths"], "the strings' lines and fills as they were")
        fresh = WiringScene().build(e, .02, states={0: "fail"})
        self.assertEqual(after["labels"], fresh["labels"])
        self.assertEqual(after["paths"], fresh["paths"])
        for name, layer in fresh["layers"].items():
            self.assertEqual(after["layers"][name], layer, name)
        e.wiring_scene(.02, states={0: "fail"}, tints=None)
        self.assertEqual(e._wiring_scene.builds, built, "the same states again: the same scene")

    def test_while_a_layout_brings_the_strings_the_scene_of_before_stays(self):
        """R598: a change that moves modules, with a layout on its way that brings the plan's scene made with it
        (plan_wiring.coming): the plan keeps the scene it has instead of making one on the window's thread; the hand
        drawing a string, the tests' full scene and the layout come make it here."""
        e, s = self.editor, self.session
        keys = [m.key for m in self.row[:3]]
        s.edit("strings", lambda p: p.energy.__setitem__(
            "strings", {"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/" + k for k in keys]}]}))
        s.layout_keys = s.expected_layout_keys()            # the layouts in hand are those of the project
        s.later, s.wiring_options = (lambda call: None), (lambda: {})
        before = e.wiring_scene(.02, wait=True)
        built = e._wiring_scene.builds
        s.edit("out", lambda p: p.subfields[0].removed.append(self.row[1].key))     # a layout to wait for
        kept = e.wiring_scene(.02, wait=True)
        self.assertIs(kept["paths"], before["paths"])
        self.assertEqual((e._wiring_scene.builds, e._wiring_scene.waited), (built, 1))
        e.wiring_scene(.02, wait=True)
        self.assertEqual(e._wiring_scene.builds, built, "a move of the pointer meanwhile makes nothing either")
        e.wiring_scene(.02, wait=False)
        self.assertEqual(e._wiring_scene.builds, built + 1, "asked without waiting (the tests): made")
        s.edit("back", lambda p: p.subfields[0].removed.remove(self.row[1].key))
        e.start_draft()
        e.click(self.row[0].centre)
        e.wiring_scene(.02, wait=True)
        self.assertEqual(e._wiring_scene.builds, built + 2, "the hand drawing a string: made at once")
        e.draft = e.draft_target = None
        s.edit("out again", lambda p: p.subfields[0].removed.append(self.row[2].key))
        e.wiring_scene(.02, wait=True)
        self.assertEqual(e._wiring_scene.builds, built + 2)
        s.layout_keys = s.expected_layout_keys()            # the layout came, without a scene made with it
        e.wiring_scene(.02, wait=True)
        self.assertEqual(e._wiring_scene.builds, built + 3)

    def test_far_strings_have_no_dots_and_names_know_their_inverter(self):
        e = self.editor
        keys = [m.key for m in self.row[:3]]
        self.session.project.energy["strings"] = {"runs": [{"inverter": 2, "mppt": 1, "modules": ["s1/" + k for k in keys]}]}
        near = e.wiring_scene(.02)
        self.assertEqual(near["level"], "near")
        self.assertEqual(len(near["dots"]), 3)
        name = next(p for p in near["labels"] if p["kind"] == "name")
        self.assertEqual(name["inverter"], 2)
        far = e.wiring_scene(2.0)
        self.assertEqual(far["level"], "far")
        self.assertEqual(far["dots"], [])
        self.assertEqual(far["size"], near["size"])


class ScalesKept(DraftScene):
    """R706, study 56 (Daniel 20/11/2026: «un blocco da mezzo secondo circa, immancabile quando faccio un paio di
    zoom in e zoom out»): the scene of the strings was one, made again at every step of the scale, the steps a zoom
    in and back had just crossed too."""

    def strings(self):
        keys = [m.key for m in self.row[:3]]
        self.session.project.energy["strings"] = {"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/" + k for k in keys]}]}

    def test_a_scale_crossed_twice_makes_its_scene_once(self):
        self.strings()
        e = self.editor
        near, far = e.wiring_scene(.02), e.wiring_scene(.5)
        built = e._wiring_scene.builds
        self.assertEqual(built, 2)
        for _trip in range(3):
            self.assertIs(e.wiring_scene(.02)["layers"], near["layers"], "the scene of before, not one made anew")
            self.assertIs(e.wiring_scene(.5)["layers"], far["layers"])
        self.assertEqual(e._wiring_scene.builds, built, "three zooms in and back make no scene again")
        self.assertTrue(e.wiring_kept(.02, None) and e.wiring_kept(.5, None))
        self.assertFalse(e.wiring_kept(5., None), "a step of the scale never seen is still to make")

    def test_other_strings_forget_the_scenes_kept(self):
        self.strings()
        e = self.editor
        e.wiring_scene(.02)
        e.wiring_scene(.5)
        self.session.project.energy["strings"]["runs"][0]["modules"].pop()
        self.assertFalse(e.wiring_kept(.02, None))
        built = e._wiring_scene.builds
        scene = e.wiring_scene(.02)
        self.assertEqual(e._wiring_scene.builds, built + 1)
        self.assertEqual(len(scene["layers"]["wireFills"]), 2, "the scene of the strings as they are now")

    def test_the_hand_s_draft_is_never_taken_from_the_scenes_kept(self):
        e = self.editor
        e.start_draft()
        e.click(self.row[0].centre)
        e.wiring_scene(.02)
        e.wiring_scene(.5)
        built = e._wiring_scene.builds
        e.wiring_scene(.02)
        self.assertEqual(e._wiring_scene.builds, built + 1, "what the hand draws is made where it is")
        self.assertEqual(len(e._wiring_scene._kept), 0)

    def test_the_scenes_kept_give_back_what_the_budget_no_longer_allows(self):
        self.strings()
        e = self.editor
        limit = [1 << 30]
        e._wiring_scene = WiringScene(limit=lambda: limit[0])
        for mpp in (.02, .06, .2, .5):
            e.wiring_scene(mpp)
        scene = e._wiring_scene
        self.assertEqual(len(scene._kept), 4)
        self.assertGreater(scene.kept_bytes(), 0)
        in_hand = e.wiring_scene(.5)["layers"]
        limit[0] = 1                        # the machine is short of memory: the budget has all but gone
        e.trim_wiring()
        self.assertEqual(len(scene._kept), 1, "all given back but the scene in hand")
        built = scene.builds
        self.assertIs(e.wiring_scene(.5)["layers"], in_hand)
        self.assertEqual(scene.builds, built)
        e.wiring_scene(.02)
        self.assertEqual(scene.builds, built + 1, "a scene given back is made again when the view returns to it")

    def test_the_plan_has_its_share_of_the_budget(self):
        from meridiana.core.compute import resources
        self.assertEqual(resources.CACHE_SHARES["plan"], .05)
        self.assertEqual(resources.CACHE_SHARES_ALL["plan"], .08)
        self.assertGreaterEqual(resources.cache_limit("plan"), 32 * resources.MIB)


class Jumps(DraftScene):
    def test_a_jump_is_a_dashed_arc_with_an_arrowhead_where_it_lands(self):
        e = self.editor
        modules = self.result.modules
        rows = [m for m in modules]
        keys = [rows[0].key, rows[2].key]
        self.session.project.energy["strings"] = {"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/" + k for k in keys]}]}
        scene = e.wiring_scene(.02)
        jumps = [o for o in scene["objects"] if o["kind"] == "string_jump"]
        self.assertEqual(len(jumps), 1)
        jump = jumps[0]
        self.assertTrue(jump["dashed"])
        self.assertLess(jump["width"], 2.5, "thinner than a plain leg")
        self.assertGreater(len(jump["points"]), 2, "an arc, not a straight line")
        a, b = jump["points"][0], jump["points"][-1]
        self.assertEqual(a, [rows[0].centre[0], -rows[0].centre[1]])
        self.assertEqual(b, [rows[2].centre[0], -rows[2].centre[1]])
        middle = jump["points"][len(jump["points"]) // 2]
        chord = abs((b[0] - a[0]) * (middle[1] - a[1]) - (b[1] - a[1]) * (middle[0] - a[0])) / math.dist(a, b)
        self.assertGreater(chord, .3, "the middle of the arc rises off the chord")
        arrows = [o for o in scene["objects"] if o["kind"] == "string_arrow"]
        self.assertEqual(len(arrows), 1, "the arrival of the jump, even for a string not chosen")
        tip = arrows[0]["points"][0]
        self.assertLess(math.dist(tip, b), .15, "the tip sits on the module the jump lands on")

    def test_a_string_on_optimizers_runs_from_unit_to_unit_in_one_leg(self):
        e = self.editor
        modules = self.result.modules
        keys = [modules[i].key for i in (0, 1, 8, 9)]       # two units, one well away from the other
        self.session.project.energy["strings"] = {"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/" + k for k in keys]}]}
        e.string_optimizers = {1: 2}                         # two modules on each optimizer
        scene = e.wiring_scene(.02)
        self.assertTrue(scene["optimizers"], "the units and their cables are drawn")
        kinds = [o["kind"] for o in scene["objects"]]
        self.assertEqual(kinds.count("string_line"), 1, "one plain leg through the units, never an arc (R424)")
        self.assertNotIn("string_jump", kinds)

    def test_jump_arc_bulges_to_the_left_of_its_direction_and_stays_bounded(self):
        arc = jump_arc((0.0, 0.0), (10.0, 0.0), 1.0)
        self.assertEqual(arc[0], (0.0, 0.0))
        self.assertEqual(arc[-1], (10.0, 0.0))
        top = max(p[1] for p in arc)
        self.assertGreater(top, 1.0)
        self.assertLessEqual(top, 2.0 + 1e-9, "never above two module sizes")
        self.assertGreater(min(p[1] for p in arc), -1e-9)
        self.assertEqual(level_of(20), "near")
        self.assertEqual(level_of(8), "mid")
        self.assertEqual(level_of(3), "far")


class Zones(unittest.TestCase):
    def test_outlines_far_apart_are_paths_apart_that_say_what_they_cover(self):
        """R706: the large layers are cut in squares, each path with its bounds: the plan draws those in view."""
        from meridiana.app.view.plan_wiring import ZONE, dot_paths, joined

        def outline(x, y):
            return dict(points=[(x, y), (x + 1, y), (x + 1, y + 2), (x, y + 2)])
        far = 10 * ZONE
        paths = joined([outline(0, 0), outline(3, 0), outline(far, 0)])
        self.assertEqual(sorted(p['bounds'] for p in paths), [[0, 0, 4, 2], [far, 0, far + 1, 2]])
        self.assertEqual(sorted(p['path'].count('M') for p in paths), [1, 2])
        dots = dot_paths([dict(x=1.0, y=1.0, colour='#112233'), dict(x=far + 1.0, y=1.0, colour='#112233')])
        self.assertEqual(len(dots), 2)
        for path in dots:
            west, north, east, south = path['bounds']
            self.assertLessEqual(east - west, ZONE + .01)
            self.assertLessEqual(south - north, ZONE + .01)


class ControllerLayers(unittest.TestCase):
    def setUp(self):
        p = model.Project(name='Layers')
        p.buildings.append(model.Building(id='b1', name='Roof', footprint=[[0, 0], [40, 0], [40, 20], [0, 20]]))
        p.subfields.append(model.SubField(id='s1', name='Array', building='b1', filled=True,
                                         ring=[[2, 2], [38, 2], [38, 18], [2, 18]]))
        self.c = PlanController(p, manage_layout=False)
        self.c.session.results = {'s1': p.fill(p.subfields[0])}
        self.c.refresh()
        self.c.setPhase('plant')
        self.c.pointerScale(.02, 0.0)
        self.modules = sorted(self.c.editor.results['s1'].modules, key=lambda m: (round(m.centre[1], 3), m.centre[0]))
        self.counts = dict(wiring=0, draft=0, band=0, unwired=0, overlay=0)
        self.c.wiringChanged.connect(lambda: self.counts.__setitem__('wiring', self.counts['wiring'] + 1))
        self.c.draftChanged.connect(lambda: self.counts.__setitem__('draft', self.counts['draft'] + 1))
        self.c.bandChanged.connect(lambda: self.counts.__setitem__('band', self.counts['band'] + 1))
        self.c.unwiredChanged.connect(lambda: self.counts.__setitem__('unwired', self.counts['unwired'] + 1))
        self.c.overlayChanged.connect(lambda: self.counts.__setitem__('overlay', self.counts['overlay'] + 1))

    def tearDown(self):
        self.c.close()

    def draft(self):
        self.c.setTool('string')
        self.c.editor.start_draft(1, 1)
        self.c._overlays()

    def test_the_overlays_again_lay_no_name_out(self):
        """R706: the strings' names and dots tell their change with a signal of their own, and the plan's other
        labels are read without them: the overlays drawn again with the same strings touch neither (the layout
        of the names ran at each signal of the overlays and of the strings, 25-50 ms of the window at 2000
        modules)."""
        keys = [m.key for m in self.modules[:3]]
        self.c.session.edit('Strings', lambda p: p.energy.update(
            strings={"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/" + k for k in keys]}]}))
        self.c.setPhase('plant')
        self.c._overlays()
        self.assertTrue([p for p in self.c.stringLabels if p['kind'] == 'name'])
        self.assertTrue(self.c.dotPlaces)
        spots = []
        self.c.spotsChanged.connect(lambda: spots.append(1))
        self.c._overlays()
        self.c._overlays()
        self.assertEqual(spots, [], 'the same names and dots: no signal of theirs')
        self.assertTrue([p for p in self.c.labels if p.get('kind') == 'name'], 'what the tests read: everything')
        self.assertFalse([p for p in self.c.plainLabels if p.get('kind') in ('name', 'number')])
        self.c.editor.chosen_string = 0
        self.c._overlays()
        self.assertEqual(spots, [1], 'the numbers of the string chosen: once')

    def test_the_collector_waits_while_the_view_moves(self):
        """R706: a whole collection of Python's collector stops the window for 125-165 ms with 10 000 modules, and
        fell where it happened to, in a zoom too: it waits while the view moves and a moment after."""
        import gc
        import _setup
        from PySide6.QtCore import QCoreApplication
        from meridiana.gui.backend import plan as plan_backend
        self.assertTrue(gc.isenabled())
        self.c.viewMoving(True)
        self.assertFalse(gc.isenabled(), 'held while the view moves')
        self.c.viewMoving(False)
        self.assertFalse(gc.isenabled(), 'and in the pause between two zooms')
        self.c.viewMoving(True)
        self.c.viewMoving(False)
        self.assertTrue(_setup.wait_until(QCoreApplication.instance(), gc.isenabled,
                                          plan_backend.MOVING_REST_MS / 1000 + 3), 'let go at rest')
        self.c.viewMoving(True)
        self.c.close()
        self.assertTrue(gc.isenabled(), 'and with the plan, if it closes while moving')

    def test_the_view_back_at_a_scale_asks_for_no_scene(self):
        """R706: a new scale's scene is made off the window's thread, once; back at a scale already seen the plan
        takes the scene it kept, without a job and without making anything."""
        import _setup
        from PySide6.QtCore import QCoreApplication
        from meridiana.gui.backend import plan as plan_backend
        app = QCoreApplication.instance()
        keys = [m.key for m in self.modules[:3]]
        self.c.session.edit('Strings', lambda p: p.energy.update(
            strings={"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/" + k for k in keys]}]}))
        self.c.setPhase('plant')
        self.assertTrue(self.c.stringsVisible and self.c.editor.runs())

        def settle(mpp):
            self.c.viewSettled(0, -20, 40, 0, mpp, 1.0)
            self.assertTrue(_setup.wait_until(app, lambda: not (self.c._scale_settle and self.c._scale_settle.isActive())
                                              and not (self.c._wiring_jobs and self.c._wiring_jobs.busy), 10))
            _setup.turn_events(app, 20)
        settle(.02)
        settle(.5)
        jobs, scene = self.c._wiring_jobs, self.c.editor._wiring_scene
        self.assertIsNotNone(jobs, 'a new scale is made by a job')
        asked, built = jobs.serial, scene.builds
        wires = {}
        for _trip in range(2):
            for mpp in (.02, .5):
                settle(mpp)
                wires.setdefault(mpp, self.c.wirePaths)
                self.assertEqual(self.c.wirePaths, wires[mpp])
        self.assertEqual(jobs.serial, asked, 'no job for a scale already seen')
        self.assertEqual(scene.builds, built, 'and nothing made on the window either')
        self.assertGreater(plan_backend.KEPT_TRIM_MS, 0)
        self.assertTrue(self.c._kept_trim.isActive(), 'the scenes kept are measured against the budget now and then')
        # Python's collector waits while a scene is made in its thread: a collection there would destroy Qt objects
        # away from the window's thread (timers firing for objects that are no more: a crash, two runs in three)
        import gc
        self.assertTrue(gc.isenabled())
        self.c.viewSettled(0, -20, 40, 0, 5., 1.0)
        self.assertTrue(_setup.wait_until(app, lambda: jobs.busy, 10), 'a scale never seen asks for a job')
        self.assertFalse(gc.isenabled(), 'held while the thread works')
        self.assertTrue(_setup.wait_until(app, lambda: not jobs.busy, 10))
        self.assertTrue(gc.isenabled(), 'and let go with its answer')
        self.assertEqual(jobs.serial, asked + 1)

    def test_a_move_changes_the_band_alone(self):
        self.draft()
        m = self.modules[0]
        self.c.click(m.centre[0], m.centre[1], 0)
        wires, fills, draft_wires, unwired = self.c.wires, self.c.wireFills, self.c.draftWires, self.c.unwiredPaths
        self.counts.update(wiring=0, draft=0, band=0, unwired=0, overlay=0)
        for k in range(5):
            self.c.pointer(m.centre[0] + k * .2, m.centre[1] + 1.0, 0, .02)
        self.assertEqual(self.counts['band'], 5)
        self.assertEqual(self.counts['overlay'], 0, "nothing else to draw again: the overlay keeps quiet (R496)")
        self.assertEqual((self.counts['wiring'], self.counts['draft'], self.counts['unwired']), (0, 0, 0))
        self.assertIs(self.c.wires, wires)
        self.assertIs(self.c.wireFills, fills)
        self.assertIs(self.c.draftWires, draft_wires)
        self.assertIs(self.c.unwiredPaths, unwired)
        self.assertEqual(self.c.draftBand[2:], [m.centre[0] + .8, -(m.centre[1] + 1.0)])

    def test_a_click_changes_the_draft_and_the_unwired_modules_but_not_the_finished_strings(self):
        keys = [m.key for m in self.modules[:3]]
        self.c.session.project.energy["strings"] = {"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/" + k for k in keys]}]}
        self.c._overlays()
        self.draft()
        wires, fills, dots, labels = self.c.wires, self.c.wireFills, self.c.dots, self.c.stringLabels
        self.assertEqual(len(fills), 3)
        self.assertEqual(len(labels), 1, "the name of the finished string")
        self.counts.update(wiring=0, draft=0, band=0, unwired=0)
        free = self.modules[4]
        self.c.click(free.centre[0], free.centre[1], 0)
        self.assertEqual(self.c.editor.draft, [('s1', free.key)])
        self.assertEqual(self.counts['wiring'], 0, "the finished strings' layers are untouched")
        self.assertEqual(self.counts['draft'], 1)
        self.assertEqual(self.counts['unwired'], 1, "the module taken is red no more")
        self.assertIs(self.c.wires, wires)
        self.assertIs(self.c.wireFills, fills)
        self.assertIs(self.c.dots, dots)
        self.assertIs(self.c.stringLabels, labels)
        self.assertEqual(len(self.c.draftFills), 1)
        self.assertEqual([p["text"] for p in self.c.draftLabels], ["1"])
        self.assertEqual(len(self.c.draftDots), 1)
        self.assertTrue(self.c.draftColour.startswith('#'))
        self.assertEqual(len(self.c.unwiredPaths), len(self.modules) - 4)
        # what the tests of before read keeps the whole picture
        self.assertEqual(len([p for p in self.c.labels if p.get('kind') == 'number']), 1)

    def test_the_large_layers_reach_the_plan_joined_as_its_batch_joined_their_rows(self):
        """R598: the strings' lines, fills and the modules in no string go to the QML as the paths the plan's batch
        made of their rows on the window's thread (Qt points, colours in Qt's order): the same picture."""
        from meridiana.gui.backend.plan_paths import batches
        keys = [m.key for m in self.modules[:3]]
        self.c.session.project.energy["strings"] = {"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/" + k for k in keys]}]}
        self.c._overlays()
        layers = ((self.c.wirePaths, self.c.wires), (self.c.wireFillPaths, self.c.wireFills),
                  (self.c.unwiredJoined, self.c.unwiredPaths))
        for joined, rows in layers:
            self.assertTrue(rows)
            self.assertEqual(joined, batches(rows))
        self.assertTrue(any(len(row['fill']) == 9 for _joined, rows in layers for row in rows), 'colours with alpha')

    def test_the_scene_the_layouts_job_makes_is_the_one_the_plan_makes_and_the_plan_takes_it(self):
        """R598: the layout's job makes the plan's scene of the strings in its process (plan_wiring.made_with, with
        the plan's options): the same layers and paths as the plan's own, taken without a build on the window's
        thread; the objects the tests read are made here when read, the same."""
        import pickle
        import threading
        from meridiana.app import jobs, layout_job
        from meridiana.app.work.job import Context
        session = self.c.session
        results, keys, _laid = jobs.layout_of(session.project)
        session.results, session.layout_keys = results, keys
        mods = sorted(results['s1'].modules, key=lambda m: (round(m.centre[1], 3), m.centre[0]))
        runs = [{"inverter": 1, "mppt": 1, "modules": ["s1/" + m.key for m in mods[:4]]},
                {"inverter": 1, "mppt": 2, "modules": ["s1/" + m.key for m in mods[6:9] + mods[20:22]]}]
        session.edit('strings', lambda p: p.energy.__setitem__('strings', {'runs': runs}))
        self.c.set_string_details({}, '', {}, {0: 'ok', 1: 'fail'})
        self.c.chooseString(1)
        self.c.refresh()
        here = self.c.editor.wiring_scene(self.c._mpp, wiring_on=True, states=self.c._string_states)
        request = layout_job.request_of(session)
        self.assertEqual(request['wiring']['chosen'], 1)
        answer = layout_job.run(request, Context(1, (0, 1), {}, lambda m: None, stop=threading.Event()))
        made = pickle.loads(pickle.dumps(answer['wiring'], protocol=5))     # as it comes from the process
        self.assertEqual(made['key'], self.c.editor._wiring_scene._key)
        self.assertEqual(made['scene']['paths'], here['paths'])
        for name, layer in here['layers'].items():
            if name not in JOINED:
                self.assertEqual(made['scene']['layers'][name], layer, name)
        self.assertTrue(here['paths']['wires'] and here['layers']['stringLabels'])
        # a plan with no scene yet: it takes the job's, no build here
        self.c.editor._wiring_scene = None
        wires, labels = self.c.wires, self.c.stringLabels
        session.wiring_offer = made
        self.c._overlays()
        scene = self.c.editor._wiring_scene
        self.assertEqual(scene.builds, 0, 'taken, not made on the window')
        self.assertIsNone(session.wiring_offer, 'taken once')
        self.assertEqual(self.c.wirePaths, here['paths']['wires'])
        self.assertEqual(self.c.stringLabels, labels)
        self.assertEqual(self.c.wires, wires, 'the rows the tests read, made here when read: the same')
        self.assertEqual(scene.builds, 1)
        # inputs that changed meanwhile (another string chosen): the job's scene is not taken
        self.c.editor._wiring_scene = None
        session.wiring_offer = made
        self.c.chooseString(0)
        self.assertEqual(self.c.editor._wiring_scene.builds, 1)
        self.assertIsNotNone(session.wiring_offer)
        # R598: other states alone (the plant came while the layout was on its way): taken, the names in those of now
        self.c.chooseString(1)
        self.c.editor._wiring_scene = None
        session.wiring_offer = made
        self.c.set_string_details({}, '', {}, {0: 'fail', 1: 'fail'})
        self.assertEqual(self.c.editor._wiring_scene.builds, 0, 'taken, not made on the window')
        self.assertIsNone(session.wiring_offer)
        self.assertEqual([p['state'] for p in self.c.stringLabels if p['kind'] == 'name'], ['fail', 'fail'])
        self.assertEqual(self.c.wirePaths, here['paths']['wires'])

    def test_the_states_of_the_strings_reach_the_labels(self):
        keys = [m.key for m in self.modules[:3]]
        self.c.session.project.energy["strings"] = {"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/" + k for k in keys]}]}
        self.c._overlays()
        self.assertEqual(self.c.stringLabels[0]['state'], 'check')
        self.counts.update(wiring=0)
        self.c.set_string_details({}, '', {}, {0: 'ok'})
        self.assertEqual(self.counts['wiring'], 1)
        self.assertEqual(self.c.stringLabels[0]['state'], 'ok')
        self.c.set_string_details({}, '', {}, {0: 'ok'})
        self.assertEqual(self.counts['wiring'], 1, "the same states: nothing drawn again")

    def test_the_level_and_the_module_size_follow_the_scale(self):
        keys = [m.key for m in self.modules[:3]]
        self.c.session.project.energy["strings"] = {"runs": [{"inverter": 1, "mppt": 1, "modules": ["s1/" + k for k in keys]}]}
        self.c._overlays()
        self.assertEqual(self.c.wiringLevel, 'near')
        self.assertGreater(self.c.moduleSize, .5)
        self.c.pointer(0, 0, 0, 2.0)
        self.assertEqual(self.c.wiringLevel, 'far')
        self.assertEqual(self.c.dots, [])


if __name__ == '__main__':
    unittest.main()
