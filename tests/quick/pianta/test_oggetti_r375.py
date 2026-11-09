"""R375: the three ways of placing a 3D object, as the picker (Shell/ObjectPicker.qml) asks them of the drawing
machine and the editor: «Choose and place» (prop with repeat: a copy at every click, Esc ends), «Along a line»
(prop_series: a copy every step between two clicks, turned along the line; a fence is one object along the line),
«Small family» (prop_group: five to seven round a click, people and vehicles mixed, the same with the same seed)."""
import unittest

import _setup  # noqa: F401

from meridiana import model
from meridiana.session import ProjectSession
from meridiana.quick.backend.plan_edit import PlanEditor
from meridiana.quick.backend.plan_tools import DrawingMachine


def machine(tool, **options):
    m = DrawingMachine()
    m.set_tool(tool, **options)
    return m


def project():
    p = model.Project()
    p.buildings.append(model.Building(id="b1", name="Shed", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]]))
    return p


class Machine(unittest.TestCase):
    def test_choose_and_place_stays_in_the_tool_until_escape(self):
        m = machine("prop", kind="truck", repeat=True)
        self.assertEqual(m.click((3, 4)), [{"type": "prop", "kind": "truck", "point": (3., 4.)}])
        self.assertEqual(m.tool, "prop")
        self.assertEqual(m.click((8, 4))[0]["point"], (8., 4.))
        self.assertEqual(m.tool, "prop")
        m.key("Escape")
        self.assertEqual(m.tool, "select")

    def test_a_chosen_model_travels_with_the_command(self):
        m = machine("prop", kind="adult", asset="hoodie_standing")
        self.assertEqual(m.click((1, 1))[0]["asset"], "hoodie_standing")
        self.assertEqual(m.tool, "select")

    def test_along_a_line_takes_two_clicks_and_leaves(self):
        m = machine("prop_series", kind="lamp", step=4.0, align=True)
        self.assertEqual(m.points, [])
        self.assertEqual(m.click((0, 0)), [])
        self.assertEqual(len(m.points), 1)
        out = m.click((12, 0))
        self.assertEqual(out[0]["type"], "prop_series")
        self.assertEqual([(round(x, 6), round(y, 6)) for x, y in out[0]["points"]], [(0., 0.), (12., 0.)])
        self.assertEqual(out[0]["options"]["step"], 4.0)
        self.assertEqual(m.tool, "select")

    def test_a_small_family_is_one_click(self):
        m = machine("prop_group", kind="adult", radius=5.0, variation=20.0, seed=3)
        out = m.click((5, 5))
        self.assertEqual(out[0]["type"], "prop_group")
        self.assertEqual(out[0]["options"]["radius"], 5.0)
        self.assertEqual(m.tool, "select")


class Editor(unittest.TestCase):
    def setUp(self):
        self.session = ProjectSession(project())
        self.editor = PlanEditor(self.session)

    @property
    def props(self):
        return self.session.project.props

    def test_a_row_every_step_turned_along_the_line(self):
        self.editor.apply_command({"type": "prop_series", "kind": "lamp", "points": [(0, 0), (12, 0)],
                                   "options": {"step": 4.0, "align": True}})
        self.assertEqual([tuple(x.at) for x in self.props], [(0., 0.), (4., 0.), (8., 0.), (12., 0.)])
        self.assertEqual({x.kind for x in self.props}, {"lamp"})
        self.assertEqual(self.session.selection[:2], ("prop", self.props[-1].id))
        self.editor.apply_command({"type": "prop_series", "kind": "broadleaf", "points": [(0, 10), (0, 19)],
                                   "options": {"step": 5.0, "align": True}})
        self.assertEqual([round(x.rotation) for x in self.props[-2:]], [90, 90])
        self.session.undo.undo()
        self.assertEqual(len(self.props), 4)

    def test_a_row_not_aligned_keeps_the_turn_at_zero(self):
        self.editor.apply_command({"type": "prop_series", "kind": "compact", "points": [(0, 0), (3, 4)],
                                   "options": {"step": 10.0, "align": False}})
        self.assertEqual([(tuple(x.at), x.rotation) for x in self.props], [((0., 0.), 0.0)])

    def test_a_small_family_of_people_mixes_the_models_and_repeats_with_the_seed(self):
        c = {"type": "prop_group", "kind": "adult", "point": (10, 10), "options": {"radius": 6.0, "variation": 20.0, "seed": 1}}
        self.editor.apply_command(c)
        family = [(x.kind, x.asset, tuple(x.at), x.rotation, x.height) for x in self.props]
        self.assertIn(len(family), (5, 6, 7))
        self.assertTrue({k for k, *_r in family} <= {"adult", "walking"})
        for kind, asset, at, _turn, height in family:
            self.assertLessEqual(((at[0] - 10) ** 2 + (at[1] - 10) ** 2) ** .5, 6.0)
            self.assertTrue(1.75 * 0.9 - 1e-6 <= height <= 1.75 * 1.1 + 1e-6, height)
        self.session.undo.undo()
        self.assertEqual(self.props, [])
        self.editor.apply_command(c)
        self.assertEqual([(x.kind, x.asset, tuple(x.at)) for x in self.props], [(k, a, p) for k, a, p, *_r in family])

    def test_a_small_family_of_cars_turns_little_and_a_group_of_trees_turns_freely(self):
        self.editor.apply_command({"type": "prop_group", "kind": "compact", "point": (30, 10),
                                   "options": {"radius": 8.0, "variation": 10.0, "seed": 2}})
        self.assertTrue({x.kind for x in self.props} <= {"compact", "suv", "pickup", "sports_car"})
        for x in self.props:
            self.assertTrue(x.rotation <= 18.0 + 1e-6 or x.rotation >= 342.0 - 1e-6, x.rotation)
        self.editor.apply_command({"type": "prop_group", "kind": "conifer", "point": (30, 30),
                                   "options": {"radius": 4.0, "variation": 30.0, "seed": 0}})
        trees = [x for x in self.props if x.kind == "conifer"]
        self.assertGreaterEqual(len(trees), 5)
        self.assertTrue(all(x.asset is None for x in trees))

    def test_a_fence_is_one_object_along_the_line_and_shades_by_segment(self):
        self.editor.apply_command({"type": "prop_line", "kind": "fence", "points": [(0, -5), (20, -5), (20, 5)]})
        fence = self.props[-1]
        self.assertEqual((fence.kind, len(fence.path), fence.casts_shadow()), ("fence", 3, True))
        from meridiana import props
        self.assertEqual(len(props.placed_solids("fence", fence.at, path=fence.path)), 2)


if __name__ == "__main__":
    unittest.main()
