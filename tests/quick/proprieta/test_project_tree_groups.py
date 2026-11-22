"""R575 (proposal of the IFC layers, 6.5, the first slice): the Project tree by building.

The sub-fields and the exclusions under their building, groups that close and are remembered for each project in the
user's settings, the sub-fields and kWp of each building, names in their natural order («Lastra 2» before «Lastra
10»), a selection made elsewhere opening the groups that hold it, the rows of a closed group never made (a project of
2 000 sub-fields gives the rows of its buildings), the arrows of the keyboard, the marks of what a closed building
holds no longer on its row (R604: no marks in the tree)."""
import tempfile
import time
import unittest
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlEngine, QQmlExpression
from PySide6.QtTest import QTest

import _setup
from meridiana.app import jobs
from meridiana.app.platform import config
from meridiana.app.session import ProjectSession
from meridiana.core.model import model
from meridiana.gui.backend.controls import install_controls
from meridiana.gui.backend.project_tree import FoldMemory, ProjectTreeBackend, natural_key


def square(x, y, side):
    return [[x, y], [x + side, y], [x + side, y + side], [x, y + side]]


def three_buildings() -> model.Project:
    """3 buildings, 7 sub-fields (one on the ground), 5 exclusions (two on the ground)."""
    p = model.Project(name="Prova")
    for bid, name, x in (("b1", "Corpo 2", 0), ("b2", "Corpo 10", 50), ("b3", "Corpo 1", 100)):
        p.buildings.append(model.Building(id=bid, name=name, footprint=square(x, 0, 40), height=8.0))
    for sid, name, bid, x, y in (("s1", "Lastra 10", "b1", 1, 1), ("s2", "Lastra 2", "b1", 1, 21),
                                 ("s3", "Lastra 1", "b1", 21, 1), ("s4", "Lastra 3", "b2", 51, 1),
                                 ("s5", "Lastra 4", "b2", 51, 21), ("s6", "Lastra 5", "b3", 101, 1),
                                 ("s7", "A terra", None, 0, 60)):
        p.subfields.append(model.SubField(id=sid, name=name, ring=square(x, y, 18), building=bid, filled=True))
    for eid, kind, bid, x, y in (("e1", "chimney", "b1", 30, 30), ("e2", "chimney", "b1", 35, 35),
                                 ("e3", "vent", "b2", 80, 30), ("e4", "tree", None, 200, 0),
                                 ("e5", "tree", None, 210, 0)):
        p.exclusions.append(model.ExclusionItem(id=eid, ring=square(x, y, 1), kind=kind, building=bid))
    return p


def shown(backend):
    return [(r["kind"], r["oid"], r["depth"]) for r in backend.rows]


class TreeByBuilding(unittest.TestCase):
    def setUp(self):
        self.session = ProjectSession(three_buildings())
        results, keys, _laid = jobs.layout_of(self.session.project)
        self.session.layout_done(self.session.generation, results, keys)
        self.folds = FoldMemory()
        self.backend = ProjectTreeBackend(self.session, folds=self.folds)
        self.addCleanup(self.backend.close)

    def test_1_rows_order_depth_counts_kwp_and_natural_names(self):
        self.assertEqual(natural_key("Lastra 2") < natural_key("Lastra 10"), True)
        self.assertEqual(shown(self.backend), [
            ("site", "", 0), ("group", "building", 0),
            ("building", "b3", 1), ("building", "b1", 1), ("building", "b2", 1),      # Corpo 1, Corpo 2, Corpo 10
            ("group", "free", 0), ("subfield", "s7", 1), ("fold", "exclusions:", 1)])
        rows = {(r["kind"], r["oid"]): r for r in self.backend.rows}
        self.assertEqual(rows[("group", "building")]["count"], 3)
        self.assertEqual(rows[("group", "free")]["count"], 3)
        self.assertEqual(rows[("fold", "exclusions:")]["count"], 2)
        self.assertFalse(rows[("fold", "exclusions:")]["open"])
        results = self.session.results
        for bid, fields in (("b1", ("s1", "s2", "s3")), ("b2", ("s4", "s5")), ("b3", ("s6",))):
            row = rows[("building", bid)]
            self.assertEqual((row["fold"], row["open"]), (f"building:{bid}", False))
            kw = sum(results[s].count for s in fields) * 0.45
            self.assertGreater(kw, 0)
            # R665: a building says its kWp alone, the count of its sub-fields went
            self.assertEqual(row["value"], f"{kw:.1f} kWp")
            self.assertEqual(row["tail"], f" · {kw:.1f} kWp")
        total = sum(r.count for r in results.values() if not isinstance(r, Exception) and r is not results["s7"]) * .45
        self.assertEqual(rows[("group", "building")]["tail"], f" · {total:.1f} kWp")
        self.assertEqual(rows[("building", "b1")]["children"], 4)       # three sub-fields and its exclusions
        self.backend.setOpen("building:b1", True)
        self.assertEqual(shown(self.backend)[3:8], [
            ("building", "b1", 1), ("subfield", "s3", 2), ("subfield", "s2", 2), ("subfield", "s1", 2),
            ("fold", "exclusions:b1", 2)])                                  # Lastra 1, Lastra 2, Lastra 10
        self.backend.setOpen("exclusions:b1", True)
        self.assertEqual(shown(self.backend)[8:10], [("exclusion", "e1", 3), ("exclusion", "e2", 3)])

    def test_1b_a_part_of_a_building_stands_under_it(self):
        self.session.edit("part", lambda p: (p.buildings.append(model.Building(
            id="b4", name="Torre", footprint=square(5, 5, 4), height=12.0, part_of="b1")),
            p.subfields.append(model.SubField(id="s8", name="Torre", ring=square(5.5, 5.5, 3), building="b4"))))
        self.assertNotIn(("building", "b4", 1), shown(self.backend))
        laid = [r for r in self.backend.rows if r["kind"] == "subfield" and r["oid"] == "s8"]
        self.assertEqual(laid, [], 'closed: the sub-field of its part is not a row')
        b1 = next(r for r in self.backend.rows if r["oid"] == "b1")
        self.assertTrue(b1["value"].endswith("kWp"))                      # its part's kWp in its own (R665)
        self.backend.setOpen("building:b1", True)
        self.assertIn(("building", "b4", 2), shown(self.backend))
        self.backend.setOpen("building:b4", True)
        self.assertIn(("subfield", "s8", 3), shown(self.backend))

    def test_2_closed_and_opened_kept_through_refresh_and_a_new_backend(self):
        self.backend.setOpen("building:b2", True)
        self.assertIn(("subfield", "s4", 2), shown(self.backend))
        self.backend.toggle("building:b2")
        self.assertNotIn(("subfield", "s4", 2), shown(self.backend))
        self.backend.toggle("building:b2")
        self.backend.setOpen("group:free", False)
        before = shown(self.backend)
        self.assertIn(("subfield", "s4", 2), before)
        self.assertNotIn(("subfield", "s7", 1), before)
        self.backend.refresh()
        self.assertEqual(shown(self.backend), before)
        again = ProjectTreeBackend(self.session, folds=self.folds)
        self.addCleanup(again.close)
        self.assertEqual(shown(again), before)
        # in the user's settings, for this project only: the file read again by a new window
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            cfg = config.Config()
            saved = ProjectTreeBackend(self.session, folds=FoldMemory(cfg, path))
            self.addCleanup(saved.close)
            saved.setOpen("building:b2", True)
            saved.setOpen("group:free", False)
            self.assertEqual(config.load(path).tree_folds, {self.session.project.bim_id: ["building:b2", "group:free"]})
            read = ProjectTreeBackend(self.session, folds=FoldMemory(config.load(path), path))
            self.addCleanup(read.close)
            self.assertEqual(shown(read), before)
            other = ProjectTreeBackend(ProjectSession(three_buildings()), folds=FoldMemory(config.load(path), path))
            self.addCleanup(other.close)
            self.assertNotIn(("subfield", "s4", 2), shown(other))          # another project starts closed

    def test_3_a_selection_elsewhere_opens_the_groups_that_hold_it(self):
        self.session.select("exclusion", "e2")
        self.assertIn(("exclusion", "e2", 3), shown(self.backend))
        self.assertEqual(self.backend.selectedRows, ["exclusion/e2"])
        self.backend.setOpen("group:building", False)
        self.session.select("row", "s4/r0")
        self.assertIn(("subfield", "s4", 2), shown(self.backend))
        self.assertEqual(self.backend.selectedRows, ["subfield/s4"])
        self.session.select_many("subfield", ["s6", "s7"])
        self.assertIn(("subfield", "s6", 2), shown(self.backend))
        self.assertEqual(self.backend.selectedRows, ["subfield/s6", "subfield/s7"])
        self.assertTrue(self.backend.reveal("subfield", "s1") is False)     # its building is open already

    def test_6_no_marks_of_the_checks_closed_or_open(self):
        # R604: a closed building, its sub-fields and its exclusions carry no count of checks
        for opened in (False, True):
            self.backend.setOpen("building:b2", opened)
            self.backend.setOpen("exclusions:b2", opened)
            self.assertEqual([r for r in self.backend.rows if any(k.startswith("mark") for k in r)], [])


class ManyObjects(unittest.TestCase):
    def test_5_two_thousand_sub_fields_give_the_rows_of_their_buildings(self):
        p = model.Project(name="Grande")
        for i in range(200):
            bid = f"b{i}"
            p.buildings.append(model.Building(id=bid, name=f"Corpo {i}", footprint=square(50 * i, 0, 40), height=8.0))
            for k in range(10):
                p.subfields.append(model.SubField(id=f"s{i}-{k}", name=f"Lastra {k}",
                                                  ring=square(50 * i + 1, 1 + 3 * k, 2), building=bid))
            for k in range(20):
                p.exclusions.append(model.ExclusionItem(id=f"e{i}-{k}", ring=square(50 * i + 30, k, 1), kind="vent",
                                                        building=bid))
        session = ProjectSession(p)
        backend = ProjectTreeBackend(session)
        self.addCleanup(backend.close)
        times = []
        for _ in range(5):
            t = time.perf_counter()
            backend.refresh()
            times.append(time.perf_counter() - t)
        self.assertLess(min(times), 0.050, times)
        self.assertEqual(len(backend.rows), 2 + 200)
        backend.setOpen("building:b7", True)
        backend.setOpen("exclusions:b7", True)
        self.assertEqual(len(backend.rows), 2 + 200 + 31)


class TreePage(unittest.TestCase):
    """The page itself, offscreen: the rows made by the ListView, the keyboard, Shift across the rows shown."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def open_page(self, project, folds=None):
        self.session = ProjectSession(project)
        self.backend = ProjectTreeBackend(self.session, folds=folds)
        self.addCleanup(self.backend.close)
        self.engine = QQmlApplicationEngine()
        self.theme = install_controls(self.engine)
        self.engine.rootContext().setContextProperty("treeBackend", self.backend)
        self.warnings = []
        self.engine.warnings.connect(lambda messages: self.warnings.extend(str(m) for m in messages))
        self.engine.loadData(b'''import QtQuick
import QtQuick.Window
import Meridiana.Theme
import Meridiana.ProjectTree
Window {
    width: 360; height: 600; visible: true
    color: Theme.colors.panel
    ProjectTreePage { id: page; objectName: "tree-page"; anchors.fill: parent; backend: treeBackend }
}''', QUrl("tree-groups.qml"))
        self.assertTrue(self.engine.rootObjects(), self.warnings)
        self.window = self.engine.rootObjects()[0]
        self.addCleanup(self.window.close)
        self.assertTrue(_setup.wait_until(self.app, lambda: self.window.isExposed()))
        self.page = self.window.findChild(QObject, "tree-page")
        self.list = self.window.findChild(QObject, "project-tree-list")
        self.addCleanup(lambda: self.assertFalse(self.warnings))

    def run_js(self, source):
        expression = QQmlExpression(QQmlEngine.contextForObject(self.page), self.page, source)
        value = expression.evaluate()
        self.assertFalse(expression.hasError(), expression.error().toString())
        return value[0] if isinstance(value, tuple) else value

    def delegates(self):
        stack, found = [self.window.contentItem()], []
        while stack:
            item = stack.pop()
            if item.objectName().startswith("tree-row-") and item.isVisible():
                found.append(item)
            stack.extend(item.childItems())
        return found

    def click(self, kind, oid, shift=False):
        index = [(r["kind"], r["oid"]) for r in self.backend.rows].index((kind, oid))
        self.run_js(f"clickRow(backend.rows[{index}], false, {str(shift).lower()})")

    def test_4_shift_within_a_building_and_across_buildings(self):
        self.open_page(three_buildings())
        self.backend.setOpen("building:b1", True)
        self.click("subfield", "s3")
        self.click("subfield", "s1", shift=True)
        self.assertEqual(self.backend.selectedRows, ["subfield/s3", "subfield/s2", "subfield/s1"])
        self.backend.setOpen("building:b2", True)
        self.click("subfield", "s2")
        self.click("subfield", "s5", shift=True)
        self.assertEqual(sorted(self.backend.selectedRows),
                         ["subfield/s1", "subfield/s2", "subfield/s4", "subfield/s5"])
        # a group's row is not chosen: a click opens or closes it
        self.click("fold", "exclusions:b1")
        self.assertIn(("exclusion", "e1", 3), shown(self.backend))
        self.assertEqual(len(self.backend.selectedRows), 4)

    def test_5_the_list_makes_only_the_rows_it_shows(self):
        p = model.Project(name="Grande")
        for i in range(200):
            p.buildings.append(model.Building(id=f"b{i}", name=f"Corpo {i}", footprint=square(50 * i, 0, 40),
                                              height=8.0))
            for k in range(10):
                p.subfields.append(model.SubField(id=f"s{i}-{k}", name=f"Lastra {k}",
                                                  ring=square(50 * i + 1, 1 + 3 * k, 2), building=f"b{i}"))
        t = time.perf_counter()
        self.open_page(p)
        opened = time.perf_counter() - t
        _setup.wait_until(self.app, lambda: len(self.delegates()) > 10)
        made = len(self.delegates())
        self.assertGreater(made, 10)
        self.assertLess(made, 60, made)                   # 600 px of rows, not 202
        self.assertLess(opened, 5.0)
        self.backend.setOpen("building:b0", True)
        _setup.wait_until(self.app, lambda: any(d.objectName() == "tree-row-subfield-s0-0" for d in self.delegates()))
        self.assertLess(len(self.delegates()), 60)

    def test_6_right_opens_left_closes_and_goes_to_the_building(self):
        self.open_page(three_buildings())
        self.list.forceActiveFocus()
        self.window.requestActivate()
        self.backend.select("building", "b2")
        _setup.wait_until(self.app, lambda: self.list.property("activeFocus"))
        QTest.keyClick(self.window, Qt.Key_Right)
        self.assertTrue(next(r for r in self.backend.rows if r["oid"] == "b2")["open"])
        QTest.keyClick(self.window, Qt.Key_Left)
        self.assertFalse(next(r for r in self.backend.rows if r["oid"] == "b2")["open"])
        self.backend.select("subfield", "s5")                 # opens b2
        QTest.keyClick(self.window, Qt.Key_Left)
        self.assertEqual(self.session.selection, ("building", "b2"))
        QTest.keyClick(self.window, Qt.Key_Down)               # the rows shown, as before
        self.assertEqual(self.session.selection, ("subfield", "s4"))


setUpModule = _setup.keep_global_state

if __name__ == "__main__":
    unittest.main()
