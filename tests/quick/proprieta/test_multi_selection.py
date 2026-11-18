"""More objects of one kind chosen in the tree, changed together (R439): the rule of the tree, the common fields, one
undo, the same selection lit on the plan. The gestures in the real window are in quick/percorsi/test_native_selezione."""
import unittest

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtWidgets import QApplication

from meridiana import i18n, model
from meridiana.quick.backend.plan import PlanController
from meridiana.quick.backend.project_tree import ProjectTreeBackend
from meridiana.quick.backend.properties import PropertiesBackend
from meridiana.session import ProjectSession

app = QApplication.instance() or QApplication([])


def project():
    p = model.Project(name="Prova")
    for i, height in enumerate((8.0, 6.0, 6.0)):
        x = 60 * i
        p.buildings.append(model.Building(id=f"b{i+1}", name=f"Corpo {i+1}", height=height,
                                          footprint=[[x, 0], [x+40, 0], [x+40, 20], [x, 20]]))
    p.subfields.append(model.SubField(id="s1", name="A", ring=[[2, 2], [10, 2], [10, 10], [2, 10]], building="b1",
                                      pitch=0, params={"mounting": "tilted_anchored"}))
    p.subfields.append(model.SubField(id="s2", name="B", ring=[[62, 2], [70, 2], [70, 10], [62, 10]], building="b2",
                                      pitch=0, params={"mounting": "tilted_ballasted"}))
    return p


class Base(unittest.TestCase):
    def setUp(self):
        self.language = i18n.language()
        i18n.setup("en")
        self.addCleanup(i18n.setup, self.language)
        self.session = ProjectSession(project())
        self.tree = ProjectTreeBackend(self.session)
        self.props = PropertiesBackend(self.session)
        self.plan = PlanController(self.session, manage_layout=False)
        self.addCleanup(self.tree.close)
        self.addCleanup(self.props.close)
        self.addCleanup(self.plan.close)

    def all_buildings(self):
        self.tree.selectMany("building", ["b1", "b2", "b3"])

    def buildings(self):
        return self.session.project.buildings


class Properties(Base):
    def test_the_real_case_all_buildings_subject_with_one_undo(self):
        self.all_buildings()
        undos = self.session.undo.count()
        self.assertTrue(self.props.commit("fire.subject", True))
        self.assertTrue(all(b.fire.subject for b in self.buildings()))
        self.assertEqual(self.session.undo.count(), undos + 1)
        self.props.undo()
        self.assertFalse(any(b.fire.subject for b in self.buildings()))
        self.props.redo()
        self.assertTrue(all(b.fire.subject for b in self.buildings()))

    def test_different_values_are_said_and_common_ones_shown(self):
        self.all_buildings()
        height = self.props.field("height").data
        self.assertTrue(height["mixed"])
        self.assertEqual(height["display"], "")
        self.assertEqual(height["mixedText"], "different values")
        subject = self.props.field("fire.subject").data
        self.assertFalse(subject["mixed"])
        self.tree.selectMany("building", ["b2", "b3"])
        self.assertFalse(self.props.field("height").data["mixed"])
        self.assertIn("6", self.props.field("height").data["display"])

    def test_a_check_that_differs_is_mixed_and_a_click_settles_it(self):
        self.session.select("building", "b1")
        self.props.commit("fire.subject", True)
        self.all_buildings()
        self.assertTrue(self.props.field("fire.subject").data["mixed"])
        self.assertTrue(self.props.commit("fire.subject", True))
        self.assertFalse(self.props.field("fire.subject").data["mixed"])

    def test_a_number_goes_to_all(self):
        self.all_buildings()
        self.assertTrue(self.props.commit("height", "9 m"))
        self.assertEqual([b.height for b in self.buildings()], [9.0, 9.0, 9.0])
        self.assertFalse(self.props.field("height").data["mixed"])

    def test_what_is_each_ones_own_is_not_offered(self):
        self.all_buildings()
        ids = [f.data["id"] for section in self.props.sections for f in section["fields"]]
        self.assertNotIn("name", ids)
        self.assertFalse([i for i in ids if i.startswith("side.")])
        self.assertIn("many", ids)
        kinds = {f.data["kind"] for section in self.props.sections for f in section["fields"]}
        self.assertNotIn("action", kinds)

    def test_one_that_cannot_take_it_refuses_it_for_all(self):
        def tall(p):
            p.buildings[1].roof = model.Roof(type="gable", tilt=15.0)
            p.buildings[2].roof = model.Roof(type="gable", tilt=15.0)
            p.buildings[2].height = 12.0
        self.session.edit("Roof", tall)
        self.tree.selectMany("building", ["b2", "b3"])
        before = self.session.snapshot()
        self.assertFalse(self.props.commit("roof.ridge_height", 10.0))
        self.assertEqual(self.session.snapshot(), before)
        self.assertTrue(self.props.error)

    def test_sub_fields_have_their_choice_mixed_and_it_goes_to_all(self):
        self.tree.selectMany("subfield", ["s1", "s2"])
        mounting = self.props.field("params.mounting").data
        self.assertTrue(mounting["mixed"])
        self.assertIsNone(mounting["value"])
        self.assertTrue(self.props.commit("params.mounting", "east_west"))
        self.assertEqual([s.params["mounting"] for s in self.session.project.subfields], ["east_west", "east_west"])

    def test_a_single_selection_is_as_before(self):
        self.session.select("building", "b1")
        ids = [f.data["id"] for section in self.props.sections for f in section["fields"]]
        self.assertIn("name", ids)
        self.assertNotIn("mixed", self.props.field("height").data)


class Selection(Base):
    def test_a_plain_selection_lets_the_many_go(self):
        self.all_buildings()
        self.assertEqual(len(self.tree.selectedRows), 3)
        self.tree.select("building", "b1")
        self.assertEqual(self.tree.selectedRows, ["building/b1"])
        self.assertEqual(self.session.selected_many(), [])

    def test_the_tree_menu_on_many_deletes_them_in_one_undo(self):
        self.all_buildings()
        names = [a["id"] for a in self.tree.actions("building", "b2")]
        self.assertEqual(names, ["properties", "", "delete"])
        undos = self.session.undo.count()
        self.assertTrue(self.tree.trigger("delete", "building", "b2"))
        self.assertEqual(self.buildings(), [])
        self.assertEqual(self.session.undo.count(), undos + 1)
        self.session.undo.undo()
        self.assertEqual(len(self.buildings()), 3)

    def test_what_is_gone_leaves_the_many(self):
        self.all_buildings()
        self.session.edit("Gone", lambda p: p.buildings.__delitem__(0))
        self.assertEqual(self.session.selected_many(), ["b2", "b3"])
        self.session.edit("Gone", lambda p: p.buildings.__delitem__(0))
        self.assertEqual(self.session.selected_many(), [])


class Plan(Base):
    def test_the_same_selection_is_lit_on_the_plan_without_corners(self):
        self.plan.setPhase("model")
        self.all_buildings()
        lit = {o["oid"] for o in self.plan.highlights if o.get("kind") == "building"}
        self.assertEqual(lit, {"b1", "b2", "b3"})
        self.assertEqual(self.plan.grips, [])
        self.assertEqual(self.plan.selectedRing, [])

    def test_on_the_plan_it_does_not_move_and_delete_takes_all(self):
        self.plan.setPhase("model")
        self.all_buildings()
        self.assertFalse(self.plan.editor._movable())
        self.assertIsNone(self.plan.editor.clip_target())
        self.plan.key("Delete", "", 0)
        self.assertEqual(self.buildings(), [])

    def test_a_click_on_the_plan_lets_it_go(self):
        self.plan.setPhase("model")
        self.all_buildings()
        self.plan.click(20.0, 10.0, 0)
        self.assertEqual(self.session.selected_many(), [])
        self.assertEqual(self.session.selection, ("building", "b1"))


class Rule(unittest.TestCase):
    """The rule of the tree, in the control's own script."""

    def run_rule(self, selected, anchor, oid, ctrl=False, shift=False):
        from pathlib import Path
        import meridiana.quick as quick
        qml = Path(quick.__file__).parent/"qml"
        engine = QQmlEngine()
        engine.addImportPath(str(qml))
        component = QQmlComponent(engine)
        source = (b'import QtQuick\nimport Meridiana.Controls as M\nQtObject { property var result: M.TreeSelection.click(['
                  b'{id:"a",group:"x"},{id:"b",group:"x"},{id:"g",group:"y",selectable:false},{id:"c",group:"x"},'
                  b'{id:"d",group:"y"}], ' + repr(selected).encode() + b', "' + anchor.encode() + b'", "' + oid.encode()
                  + b'", ' + str(ctrl).lower().encode() + b', ' + str(shift).lower().encode() + b') }\n')
        component.setData(source, QUrl.fromLocalFile(str(qml/"rule.qml")))
        made = component.create()
        self.assertIsNotNone(made, component.errorString())
        result = made.property("result")
        result = result.toVariant() if hasattr(result, "toVariant") else result
        return result["selected"], result["anchor"]

    def test_plain_ctrl_shift_and_groups(self):
        self.assertEqual(self.run_rule(["a"], "a", "b"), (["b"], "b"))
        self.assertEqual(self.run_rule(["a"], "a", "b", ctrl=True), (["a", "b"], "b"))
        self.assertEqual(self.run_rule(["a", "b"], "b", "b", ctrl=True), (["a"], "a"))
        self.assertEqual(self.run_rule(["a"], "a", "a", ctrl=True), (["a"], "a"))
        self.assertEqual(self.run_rule(["a"], "a", "c", shift=True), (["a", "b", "c"], "a"))
        self.assertEqual(self.run_rule(["a", "b"], "b", "d", ctrl=True), (["d"], "d"))
        self.assertEqual(self.run_rule(["a"], "a", "d", shift=True), (["d"], "d"))
        self.assertEqual(self.run_rule(["a"], "a", "g", ctrl=True), (["a"], "a"))


if __name__ == "__main__":
    unittest.main()
