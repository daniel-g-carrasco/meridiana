"""R496: stringing by hand without the strings' layers made again at every move; jumps as dashed arcs; levels by
scale. Pure scene and controller, no window."""
import math
import unittest

from meridiana import model
from meridiana.quick.backend.plan import PlanController
from meridiana.quick.backend.plan_wiring import jump_arc, level_of
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
