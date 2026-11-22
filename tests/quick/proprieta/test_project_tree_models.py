"""R604: one imported model is ONE node of the Project tree.

The bodies of an import listed in one row (the bodies worth a row inside it, the small ones in «Other bodies»), the
node chosen is the whole import (selected, moved, framed and deleted as one, one undo step), the planes the import made
shown by their short name, no marks of the checks in the tree, and the list not jumping to the top when it changes."""
import time
import unittest
from types import SimpleNamespace

from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlEngine, QQmlExpression
from PySide6.QtTest import QTest

import _setup
from meridiana.app import jobs
from meridiana.app.exchange import ifc_import, ifc_read
from meridiana.app.session import ProjectSession
from meridiana.core.model import model
from meridiana.gui.backend.controls import install_controls
from meridiana.gui.backend.plan_edit import PlanEditor
from meridiana.gui.backend.project_tree import FoldMemory, ProjectTreeBackend, footprints_bounds

FILE = "C:/models/a long folder/Town hall.ifc"


def square(x, y, side):
    return [[x, y], [x + side, y], [x + side, y + side], [x, y + side]]


def town_hall(alone=("Shed",)) -> model.Project:
    """An import of six bodies as the import saves it (Building.group, the planes named «<file>: #<n>», the model's
    reference without the list of what it derived): the main roof with three planes, a large roof without, four small
    ones; a plane on the ground from the same file; and buildings drawn by hand."""
    p = model.Project(name="Prova")
    for n, name in enumerate(alone):
        p.buildings.append(model.Building(id=f"h{n}", name=name, footprint=square(-100.0 - 50 * n, 0, 20), height=6.0))
    sides = [("Town hall", 30.0), ("Town hall 2", 12.0)] + [(f"Town hall {n}", 4.0) for n in range(3, 7)]
    for k, (name, side) in enumerate(sides):
        p.buildings.append(model.Building(id=f"b{k + 1}", name=name, footprint=square(40.0 * k, 0, side), height=8.0,
                                          group="ifc1"))
    for k in range(3):
        p.subfields.append(model.SubField(id=f"s{k + 1}", name=f"{FILE}: #40, #41", ring=square(1 + 9 * k, 1, 8),
                                          building="b1", filled=True, support=model.SupportPlane(enabled=True)))
    p.subfields.append(model.SubField(id="s9", name=f"{FILE}: #77", ring=square(0, 60, 8), building=None))
    p.resources = {"ifc_reference": {"file": FILE, "anchor": {"building": "b1", "footprint": square(0, 0, 30.0)}}}
    return p


def shown(backend):
    return [(r["kind"], r["oid"], r["depth"]) for r in backend.rows]


def row(backend, kind, oid):
    return next(r for r in backend.rows if (r["kind"], r["oid"]) == (kind, oid))


class ImportedThroughTheRealPath(unittest.TestCase):
    """A synthetic IFC of tests/data/ifc whose building the import makes into two bodies, through ifc_import.plan and
    apply inside session.edit, as the import window does."""

    def setUp(self):
        if not ifc_read.available():
            raise unittest.SkipTest("ifcopenshell is not installed")
        found = ifc_read.read(_setup.DATA / "ifc" / "finestra-facciata.ifc")
        self.session = ProjectSession(model.Project(name="Prova"))
        plan = ifc_import.plan(found, self.session.project, "file")
        self.session.edit("Import", lambda p: ifc_import.apply(p, plan))
        self.assertGreaterEqual(len(self.session.project.buildings), 2)
        self.backend = ProjectTreeBackend(self.session, folds=FoldMemory())
        self.addCleanup(self.backend.close)

    def test_one_node_its_bodies_selected_deleted_and_back_with_one_undo(self):
        p = self.session.project
        bodies = [b.id for b in p.buildings]
        key = p.buildings[0].group
        self.assertTrue(key)
        self.assertEqual([(k, o) for k, o, d in shown(self.backend) if d == 1], [("model", key)])
        self.assertEqual(row(self.backend, "group", "building")["count"], 1)
        node = row(self.backend, "model", key)
        self.assertEqual((node["fold"], node["open"], node["pick"], node["join"]), (f"model:{key}", False, True, False))
        self.backend.setOpen(f"model:{key}", True)
        self.assertEqual(sorted(o for k, o, d in shown(self.backend) if k == "building" and d == 2), sorted(bodies))
        self.backend.setOpen(f"model:{key}", False)
        self.backend.select("model", key)
        self.assertEqual(set(self.session.selected_many()), set(bodies))
        self.assertEqual((self.backend.selectionKind, self.backend.selectionId), ("model", key))
        self.assertIn(f"model/{key}", self.backend.selectedRows)
        self.assertFalse(row(self.backend, "model", key)["open"])        # a click on the node does not unfold it
        steps = self.session.undo.count()
        self.assertTrue(self.backend.trigger("delete", "model", key))
        self.assertEqual(self.session.project.buildings, [])
        self.assertEqual(self.session.undo.count(), steps + 1)
        self.assertNotIn(("model", key, 1), shown(self.backend))
        self.backend.undo()
        self.assertEqual(sorted(b.id for b in self.session.project.buildings), sorted(bodies))
        self.assertIn(("model", key, 1), shown(self.backend))


class AlreadyImported(unittest.TestCase):
    """A project saved after an import: grouped and named again without importing anything."""

    def setUp(self):
        self.session = ProjectSession(town_hall())
        results, keys, _laid = jobs.layout_of(self.session.project)
        self.session.layout_done(self.session.generation, results, keys)
        self.backend = ProjectTreeBackend(self.session, folds=FoldMemory())
        self.addCleanup(self.backend.close)

    def test_one_node_its_counts_bodies_and_other_bodies(self):
        b = self.backend
        self.assertEqual(shown(b), [("site", "", 0), ("group", "building", 0), ("building", "h0", 1),
                                    ("model", "ifc1", 1), ("group", "free", 0), ("subfield", "s9", 1)])
        self.assertEqual(row(b, "group", "building")["count"], 2)                 # the model counts one
        results, p = self.session.results, self.session.project
        laid = sum(results[s].count for s in ("s1", "s2", "s3") if not isinstance(results[s], Exception))
        self.assertGreater(laid, 0)
        kw = laid * p.module_of(p.subfields[0]).power_kw
        node = row(b, "model", "ifc1")
        self.assertEqual(node["tail"], f" · 3 sub-fields · {kw:.1f} kWp")
        self.assertEqual(node["label"], "Town hall")
        self.assertEqual(node["tint"], "building")
        self.assertEqual(node["tip"].split("\n"), [f"Imported model: 6 bodies, {laid} modules", FILE])
        self.assertNotIn(FILE, node["label"] + node["tail"])
        b.toggle("model:ifc1")
        self.assertEqual(shown(b)[3:7], [("model", "ifc1", 1), ("building", "b1", 2), ("building", "b2", 2),
                                         ("fold", "others:ifc1", 2)])
        others = row(b, "fold", "others:ifc1")
        self.assertEqual((others["label"], others["count"], others["pick"], others["open"]), ("Other bodies", 4, False, False))
        self.assertEqual(row(b, "building", "b1")["tail"], f" · {kw:.1f} kWp")   # all its sub-fields on b1, its kWp alone (R665)
        b.toggle("others:ifc1")
        self.assertEqual(shown(b)[7:11], [("building", f"b{n}", 3) for n in range(3, 7)])

    def test_the_planes_by_their_short_name_and_where_they_came_from(self):
        b = self.backend
        b.setOpen("model:ifc1", True)
        b.setOpen("building:b1", True)
        planes = [r for r in b.rows if r["kind"] == "subfield" and r["depth"] == 3]
        self.assertEqual([r["label"] for r in planes], ["Surface 1", "Surface 2", "Surface 3"])
        self.assertTrue(all(r["tip"].split("\n")[-1] == f"From {FILE}, IFC #40, #41" for r in planes))
        ground = row(b, "subfield", "s9")
        self.assertEqual(ground["label"], "Town hall · surface 4")              # the full form under «On the ground»: the
        #                                                     model's fourth plane, numbered with the ones on its bodies
        self.assertEqual(ground["tip"], f"From {FILE}, IFC #77")

    def test_a_selection_elsewhere_opens_the_node_and_its_other_bodies(self):
        self.session.select("building", "b5")
        self.assertIn(("building", "b5", 3), shown(self.backend))
        self.assertTrue(row(self.backend, "model", "ifc1")["open"])
        self.assertTrue(row(self.backend, "fold", "others:ifc1")["open"])
        self.backend.setOpen("model:ifc1", False)
        self.session.select("subfield", "s2")
        self.assertIn(("subfield", "s2", 3), shown(self.backend))

    def test_the_node_is_the_whole_import_framed_and_its_menu(self):
        b = self.backend
        self.assertEqual([a["id"] for a in b.actions("model", "ifc1")],
                         ["properties", "frame", "", "rename", "", "delete"])
        self.assertEqual(b.actions("model", "nothing"), [])
        b.select("model", "ifc1")
        self.assertEqual(self.session.selection, ("building", "b1"))          # the anchor last: the one followed
        self.assertEqual(set(self.session.selected_many()), {f"b{n}" for n in range(1, 7)})
        self.assertNotIn("model:ifc1", [r["fold"] for r in b.rows if r["open"]])
        asked = []
        b.propertiesRequested.connect(lambda *a: asked.append(("properties",) + a))
        b.frameRequested.connect(lambda *a: asked.append(("frame",) + a))
        self.session.select("building", "h0")
        self.assertTrue(b.trigger("frame", "model", "ifc1"))
        self.assertTrue(b.trigger("properties", "model", "ifc1"))
        self.assertEqual(asked, [("frame", "model", "ifc1"), ("properties", "model", "ifc1")])
        self.assertEqual(b.selectionKind, "model")
        bounds = b.model_bounds("ifc1")
        self.assertEqual(bounds, [0.0, -30.0, 204.0, 30.0])        # from the first body's corner to the last's
        self.assertEqual(bounds, footprints_bounds(self.session.project, [f"b{n}" for n in range(1, 7)]))
        # one body more or less is not the model: the selection is buildings
        self.session.select_many("building", ["b1", "b2"])
        self.assertEqual(b.selectionKind, "building")
        self.assertNotIn("model/ifc1", b.selectedRows)

    def test_the_inspectors_show_and_frame_the_whole_model(self):
        from meridiana.gui.backend.properties_part import Inspectors
        _setup.qt_or_skip()
        panels, phases = [], []
        plan = SimpleNamespace(targetBounds=[1.0, 2.0, 3.0, 4.0], setMarks=lambda marks: None)
        window = SimpleNamespace(cfg=None, paths=None, plan=plan, bridge=SimpleNamespace(recompute=lambda: None),
                                 shell=SimpleNamespace(trigger=lambda *a: None,
                                                       panelRequested=SimpleNamespace(emit=panels.append)))
        owner = QObject()
        self.addCleanup(owner.deleteLater)
        inspectors = Inspectors(owner, self.session, window)
        self.addCleanup(inspectors.close)
        inspectors.root = SimpleNamespace(property=lambda name: "model", showPhase=phases.append)
        framed = []
        inspectors.fitBoundsRequested.connect(framed.append)
        self.backend.close()
        inspectors.tree.trigger("frame", "model", "ifc1")
        self.assertEqual(framed, [[0.0, -30.0, 204.0, 30.0]])
        self.assertEqual(set(self.session.selected_many()), {f"b{n}" for n in range(1, 7)})
        self.session.select("site", "")
        inspectors.tree.trigger("properties", "model", "ifc1")
        self.assertEqual(panels, ["properties"])
        self.assertEqual(inspectors.tree.selectionKind, "model")       # not undone by a select of one body


class Renamed(unittest.TestCase):
    """Format 33: the node renamed as a building is, from its menu, the tree's editor and the Properties' field, one
    step of the undo; the new name wherever the model is named."""

    def setUp(self):
        self.session = ProjectSession(town_hall())
        self.backend = ProjectTreeBackend(self.session, folds=FoldMemory())
        self.addCleanup(self.backend.close)

    def test_from_the_tree_with_one_undo(self):
        b = self.backend
        self.assertFalse(b.rename("model", "ifc1", "   "))
        self.assertFalse(b.rename("model", "ifc1", "Town hall"))          # the same name: nothing changes
        self.assertEqual(self.session.undo.count(), 0)
        self.assertTrue(b.rename("model", "ifc1", "North wing"))
        self.assertEqual(row(b, "model", "ifc1")["label"], "North wing")
        self.assertEqual(row(b, "subfield", "s9")["label"], "North wing · surface 4")    # on the ground, of the import
        self.assertEqual(self.session.undo.count(), 1)
        self.assertEqual(self.session.undo.steps[0].text, "Rename the imported model")
        self.assertEqual([x.name for x in self.session.project.buildings][1:3], ["Town hall", "Town hall 2"])
        b.undo()
        self.assertEqual(row(b, "model", "ifc1")["label"], "Town hall")
        b.redo()
        self.assertEqual(row(b, "model", "ifc1")["label"], "North wing")

    def test_from_the_properties_with_one_undo(self):
        from meridiana.gui.backend.properties import PropertiesBackend
        _setup.qt_or_skip()
        props = PropertiesBackend(self.session)
        self.addCleanup(props.close)
        self.backend.select("model", "ifc1")
        field = props.field("model.name")
        self.assertIsNotNone(field)
        self.assertEqual((field.data["label"], field.data["value"]), ("Name", "Town hall"))
        self.assertTrue(props.commit("model.name", "North wing"))
        self.assertEqual(row(self.backend, "model", "ifc1")["label"], "North wing")
        self.assertEqual(props.field("model.name").data["value"], "North wing")
        self.assertEqual(self.session.undo.count(), 1)
        self.session.select_many("building", ["b1", "b2"])                 # not the whole model: no such field
        self.assertIsNone(props.field("model.name"))


class MovedAndDeletedOnThePlan(unittest.TestCase):
    def setUp(self):
        self.session = ProjectSession(town_hall())
        self.backend = ProjectTreeBackend(self.session, folds=FoldMemory())
        self.addCleanup(self.backend.close)
        self.editor = PlanEditor(self.session)

    def test_move_the_node_moves_every_body_and_one_undo_puts_them_back(self):
        before = {b.id: [list(q) for q in b.footprint] for b in self.session.project.buildings}
        self.backend.select("model", "ifc1")
        self.editor.set_tool("move")
        self.editor.key("", "3;2")
        self.editor.key("Enter")
        for b in self.session.project.buildings:
            shift = (3, 2) if b.group == "ifc1" else (0, 0)
            self.assertEqual([list(q) for q in b.footprint],
                             [[x + shift[0], y + shift[1]] for x, y in before[b.id]], b.id)
        self.assertEqual(self.session.undo.count(), 1)
        self.session.undo.undo()
        self.assertEqual({b.id: [list(q) for q in b.footprint] for b in self.session.project.buildings}, before)

    def test_a_building_and_a_body_together_do_not_move(self):
        self.session.select_many("building", ["h0", "b1"])
        self.editor.set_tool("move")
        self.editor.key("Right")
        self.assertEqual(self.session.undo.count(), 0)              # R439 as before: chosen together, not moved

    def test_delete_on_the_plan_takes_the_whole_model_in_one_step(self):
        self.backend.select("model", "ifc1")
        self.editor.key("Delete")
        self.assertEqual([b.id for b in self.session.project.buildings], ["h0"])
        self.assertEqual([s.id for s in self.session.project.subfields], ["s9"])
        self.assertEqual(self.session.undo.count(), 1)
        self.session.undo.undo()
        self.assertEqual(len(self.session.project.buildings), 7)
        self.assertEqual(len(self.session.project.subfields), 4)


class ManyBodies(unittest.TestCase):
    def test_a_model_of_two_thousand_bodies_closed_is_one_row(self):
        p = model.Project(name="Grande")
        for i in range(2000):
            p.buildings.append(model.Building(id=f"b{i}", name=f"Corpo {i + 1}", footprint=square(20 * i, 0, 4 + i % 9),
                                              height=6.0, group="ifc1"))
        session = ProjectSession(p)
        backend = ProjectTreeBackend(session, folds=FoldMemory())
        self.addCleanup(backend.close)
        times = []
        for _ in range(5):
            t = time.perf_counter()
            backend.refresh()
            times.append(time.perf_counter() - t)
        self.assertLess(min(times), 0.050, times)
        self.assertEqual(shown(backend), [("site", "", 0), ("group", "building", 0), ("model", "ifc1", 1)])


class TreePage(unittest.TestCase):
    """The page itself, offscreen: no marks drawn, the keyboard from the node, the scroll kept."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def open_page(self, project, height=600):
        self.session = ProjectSession(project)
        self.backend = ProjectTreeBackend(self.session, folds=FoldMemory())
        self.addCleanup(self.backend.close)
        self.engine = QQmlApplicationEngine()
        install_controls(self.engine)
        self.engine.rootContext().setContextProperty("treeBackend", self.backend)
        self.warnings = []
        self.engine.warnings.connect(lambda messages: self.warnings.extend(str(m) for m in messages))
        self.engine.loadData(b'''import QtQuick
import QtQuick.Window
import Meridiana.Theme
import Meridiana.ProjectTree
Window {
    width: 300; height: %d; visible: true
    color: Theme.colors.panel
    ProjectTreePage { id: page; objectName: "tree-page"; anchors.fill: parent; backend: treeBackend }
}''' % height, QUrl("tree-models.qml"))
        self.assertTrue(self.engine.rootObjects(), self.warnings)
        self.window = self.engine.rootObjects()[0]
        self.addCleanup(self.window.close)
        self.assertTrue(_setup.wait_until(self.app, lambda: self.window.isExposed()))
        self.page = self.window.findChild(QObject, "tree-page")
        self.list = self.window.findChild(QObject, "project-tree-list")
        self.addCleanup(lambda: self.assertFalse(self.warnings, self.warnings))

    def run_js(self, source):
        expression = QQmlExpression(QQmlEngine.contextForObject(self.page), self.page, source)
        value = expression.evaluate()
        self.assertFalse(expression.hasError(), expression.error().toString())
        return value[0] if isinstance(value, tuple) else value

    def items(self):
        stack, found = [self.window.contentItem()], []
        while stack:
            item = stack.pop()
            found.append(item)
            stack.extend(item.childItems())
        return found

    def click(self, kind, oid, ctrl=False, shift=False):
        index = [(r["kind"], r["oid"]) for r in self.backend.rows].index((kind, oid))
        self.run_js(f"clickRow(backend.rows[{index}], {str(ctrl).lower()}, {str(shift).lower()})")

    def test_no_mark_drawn_and_the_node_chosen_alone(self):
        self.open_page(town_hall())
        self.backend.setOpen("model:ifc1", True)
        self.backend.setOpen("building:b1", True)
        _setup.wait_until(self.app, lambda: any(i.objectName() == "tree-row-subfield-s1" for i in self.items()))
        names = [i.objectName() for i in self.items()]
        self.assertIn("tree-row-subfield-s1", names)
        self.assertEqual([n for n in names if n.startswith("tree-mark")], [])
        self.backend.setOpen("model:ifc1", False)
        self.click("model", "ifc1")
        self.assertEqual(self.backend.selectionKind, "model")
        self.assertFalse(row(self.backend, "model", "ifc1")["open"])
        self.click("building", "h0")
        self.click("model", "ifc1", ctrl=True)                     # Ctrl on the node: the node alone
        self.assertEqual((self.backend.selectionKind, self.backend.selectionId), ("model", "ifc1"))
        self.click("building", "h0", shift=True)                   # a building does not join the node's bodies
        self.assertEqual(self.backend.selectedRows, ["building/h0"])

    def test_keyboard_from_the_node(self):
        self.open_page(town_hall(alone=("Workshop",)))
        self.list.forceActiveFocus()
        self.window.requestActivate()
        self.backend.select("model", "ifc1")
        _setup.wait_until(self.app, lambda: self.list.property("activeFocus"))
        QTest.keyClick(self.window, Qt.Key_Down)
        self.assertEqual(self.session.selection, ("building", "h0"))          # «Town hall» then «Workshop»
        QTest.keyClick(self.window, Qt.Key_Up)
        self.assertEqual((self.backend.selectionKind, self.backend.selectionId), ("model", "ifc1"))
        QTest.keyClick(self.window, Qt.Key_Right)
        self.assertTrue(row(self.backend, "model", "ifc1")["open"])
        QTest.keyClick(self.window, Qt.Key_Left)
        self.assertFalse(row(self.backend, "model", "ifc1")["open"])
        QTest.keyClick(self.window, Qt.Key_Delete)
        self.assertEqual([b.id for b in self.session.project.buildings], ["h0"])
        self.backend.undo()
        self.assertEqual(len(self.session.project.buildings), 7)

    def test_f2_on_the_node_renames_it(self):
        self.open_page(town_hall())
        self.list.forceActiveFocus()
        self.window.requestActivate()
        self.backend.select("model", "ifc1")
        _setup.wait_until(self.app, lambda: self.list.property("activeFocus"))
        QTest.keyClick(self.window, Qt.Key_F2)
        editor = self.window.findChild(QObject, "project-tree-name-editor")
        field = self.window.findChild(QObject, "project-tree-name-field")
        self.assertTrue(_setup.wait_until(self.app, lambda: editor.property("visible")))
        self.assertEqual(field.property("text"), "Town hall")
        field.setProperty("text", "North wing")
        self.run_js("commitName()")
        self.assertEqual(row(self.backend, "model", "ifc1")["label"], "North wing")
        self.assertEqual(self.session.undo.count(), 1)

    def test_the_list_keeps_its_place_when_it_changes(self):
        self.open_page(town_hall(alone=tuple(f"Edificio {n}" for n in range(1, 41))), height=320)
        self.backend.setOpen("model:ifc1", True)
        bottom = lambda: max(0.0, self.list.property("contentHeight") - self.list.property("height"))
        _setup.wait_until(self.app, lambda: bottom() > 400)
        place = round(bottom() * 0.6)
        self.list.setProperty("contentY", place)
        step = self.list.property("contentHeight") / max(1, self.list.property("count"))

        def kept(why):
            _setup.wait_until(self.app, lambda: abs(self.list.property("contentY") - place) <= step, seconds=1)
            now = self.list.property("contentY")
            self.assertGreater(now, 0, why)
            self.assertLessEqual(abs(now - place), step, why)

        self.backend.toggle("group:free")                           # (a) a group below closed
        kept("a group below")
        self.session.edit("Rename", lambda p: setattr(p.building("h35"), "name", "Edificio rinominato"))
        kept("a rename")                                            # (b) a refresh after an edit
        self.backend.toggle("others:ifc1")                          # (c) «Other bodies» opened
        kept("other bodies")


setUpModule = _setup.keep_global_state

if __name__ == "__main__":
    unittest.main()
