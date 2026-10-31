"""R269: the «3D object» command of the Modelling bar: placed with a click, in the plan, the tree, the 3D scene and
the properties, every change one step of the undo."""
import unittest

import _setup
from meridiana import model, phases, props

setUpModule = _setup.keep_global_state


def project() -> model.Project:
    p = model.Project()
    p.buildings.append(model.Building(id="b1", name="Shed", footprint=[[0, 0], [20, 0], [20, 10], [0, 10]],
                                      height=6.0))
    return p


class PropsWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_command_is_on_the_modelling_bar_with_its_menu_of_kinds(self):
        win = _setup.window(self, project())
        modelling = next(ph for ph in phases.phases() if ph.id == "model")
        tools = [t for g in modelling.groups if g.id == "obstacles" for t in g.tools]
        self.assertEqual([t.command for t in tools if not t.planned], ["tool_exclusion", "object_3d"])
        self.assertFalse(win.commands["object_3d"].icon().isNull())
        self.assertEqual(win.commands["object_3d"].shortcut().toString(), "O")
        kinds = [a.data() for a in win.prop_menu().actions() if a.data()]
        self.assertEqual(set(kinds), set(props.KINDS) - {"opening"})
        for family in ("broadleaf", "chimney", "worker", "suv"):
            self.assertIn(family, kinds)

    def test_a_click_places_it_and_it_is_drawn_selected_changed_and_taken_back(self):
        win = _setup.window(self, project())
        shown = []
        win.view3d.show_scene = lambda tri, table: shown.append(tri[0].shape[0])
        win._show_3d()
        empty = shown[-1]
        win.place_prop("conifer")
        win._points_picked("prop", [[30.0, 4.0]])
        (x,) = win.project.props
        self.assertEqual((x.kind, x.at, x.building), ("conifer", [30.0, 4.0], None))
        self.assertEqual(tuple(win.selection), ("prop", x.id))
        # the plan: its outline, picked by a click inside it
        from meridiana.ui.plan import to_scene
        self.assertTrue(_setup.wait_until(self.app, lambda: ("prop", x.id) in win.plan.rings))
        self.assertEqual(win.plan._pick(to_scene(30.0, 4.0))[:2], ("prop", x.id))
        # the tree of the project
        labels = []
        stack = [win.tree.topLevelItem(0)]
        while stack:
            node = stack.pop()
            labels.append(node.text(0))
            stack.extend(node.child(i) for i in range(node.childCount()))
        self.assertIn("Conifer 1", labels)
        # the 3D scene holds its triangles
        win._show_3d()
        self.assertGreater(shown[-1], empty)
        # the properties: its kind and measures, a change is one step
        self.assertEqual(win.props.kind, "prop")
        win._edited("prop", x.id, {"height": 12.0})
        self.assertEqual(win.project.prop(x.id).measures()["height"], 12.0)
        win.undo.undo()
        self.assertIsNone(win.project.prop(x.id).height)
        # moved onto the roof it stands on the building
        win._transform("prop", x.id, {"mode": "move", "dx": -20.0, "dy": 1.0, "copy": False})
        self.assertEqual(win.project.prop(x.id).building, "b1")
        win.undo.undo()
        self.assertIsNone(win.project.prop(x.id).building)
        # deleted, and back
        win._select("prop", x.id)
        win._delete()
        self.assertEqual(win.project.props, [])
        win.undo.undo()
        self.assertEqual(len(win.project.props), 1)
        win.undo.undo()                                 # the placing itself
        self.assertEqual(win.project.props, [])

    def test_the_properties_change_the_kind_and_reset_the_measures_across_families(self):
        p = project()
        p.props.append(model.Prop(id="o1", kind="broadleaf", at=[30.0, 4.0], width=6.0))
        win = _setup.window(self, p)
        win._select("prop", "o1")
        from PySide6.QtWidgets import QComboBox
        kind = win.props.findChild(QComboBox)
        kind.setCurrentIndex(kind.findData("conifer"))          # a tree to a tree: the crown stays
        self.assertEqual((win.project.prop("o1").kind, win.project.prop("o1").width), ("conifer", 6.0))
        kind = win.props.findChild(QComboBox)
        kind.setCurrentIndex(kind.findData("compact"))          # a tree to a car: the car's own measures
        x = win.project.prop("o1")
        self.assertEqual((x.kind, x.width), ("compact", None))
        self.assertEqual(x.measures()["width"], props.CAR_DEFAULTS["compact"][1])


if __name__ == "__main__":
    unittest.main()
