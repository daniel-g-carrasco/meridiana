"""R605 on the real Checks backend: the five sub-fields an import left empty are one row of the panel, whose eye selects
them all and which «related» shows for each of them; the drawings get marks only for errors and warnings."""
from types import SimpleNamespace
import unittest

import _setup
from PySide6.QtGui import QGuiApplication

from meridiana.core.model import model
from meridiana.core.rules import checks
from meridiana.gui.backend.checks import ChecksBackend
from meridiana.gui.backend.properties_part import Inspectors
from meridiana.app.session import ProjectSession
from meridiana.i18n import setup

setUpModule = _setup.keep_global_state

FILE = "I:/jobs/a long folder/another/Town hall.ifc"


def square(x: float, y: float, side: float) -> list:
    return [[x, y], [x + side, y], [x + side, y + side], [x, y + side]]


def imported_project() -> model.Project:
    """Two bodies of one import; on the first, five planes the import made and nobody laid yet."""
    p = model.Project(name="Prova")
    p.buildings.append(model.Building(id="b1", name="Town hall", footprint=square(0, 0, 60), height=9.5, group="ifc1"))
    p.buildings.append(model.Building(id="b2", name="Town hall 2", footprint=square(100, 0, 20), height=6.0,
                                      group="ifc1"))
    p.resources = {"ifc_reference": {"file": FILE, "anchor": {"building": "b1", "footprint": square(0, 0, 60)}}}
    for n in range(5):
        p.subfields.append(model.SubField(id=f"s{n + 1}", name=f"{FILE}: #12", ring=square(1 + 10 * n, 1, 8),
                                          building="b1"))
    return p


class MergedRow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        setup("en")

    def setUp(self):
        self.session = ProjectSession(imported_project())
        self.backend = ChecksBackend(self.session)
        self.addCleanup(self.backend.close)
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.backend.busy, 30))
        self.assertFalse(self.backend.error)

    def merged(self):
        return next(r for r in self.backend.rows if not r["header"] and r["members"])

    def test_the_panel_has_one_row_for_the_five_and_counts_one(self):
        rows = self.backend.rows
        self.assertEqual([(r["header"], r["text"]) for r in rows],
                         [(True, "To know"), (False, "5 sub-fields without modules")])
        self.assertEqual(self.backend.counts["info"], 1)
        self.assertEqual(self.backend.title, "Checks")
        row = self.merged()
        self.assertEqual(row["place"], "objects")
        self.assertTrue(row["hasFix"])
        self.assertEqual(row["fixText"], "Fill all")                    # the button says its command
        self.assertTrue(row["detail"].endswith(", ".join(f"Town hall · surface {n}" for n in range(1, 6))))
        for r in rows:
            self.assertNotIn("Town hall.ifc", r["text"] + r.get("detail", ""))
        # by object: in the project's group, not in one of the five
        self.backend.setView("object")
        headers = [r["key"] for r in self.backend.rows if r["header"]]
        self.assertEqual(headers, ["object|site|"])

    def test_the_eye_selects_the_five_and_frames_the_last(self):
        framed = []
        self.backend.focusRequested.connect(framed.append)
        self.backend.showPlace(self.merged()["itemIndex"])
        self.assertEqual(framed, [["subfield", "s5"]])
        self.assertEqual(self.session.selection, ("subfield", "s5"))
        self.assertEqual(self.session.selected_many(), [f"s{n}" for n in range(1, 6)])

    def test_related_and_this_object_show_the_merged_row_for_each_of_them(self):
        index = self.merged()["itemIndex"]
        self.session.select("subfield", "s3")
        self.assertTrue(self.merged()["related"])
        self.assertEqual(self.backend.currentIndex, index)
        self.backend.setObjectOnly(True)
        self.assertEqual([r["itemIndex"] for r in self.backend.rows if not r["header"]], [index])
        self.assertIn("Town hall · surface 3", self.backend.summary)
        self.assertNotIn("#12", self.backend.summary)

    def test_fill_all_is_one_step_of_the_undo_and_leaves_the_full_ones_alone(self):
        index = self.merged()["itemIndex"]
        told = []
        self.session.subscribe(told.append)
        # one of the five filled meanwhile, the row not gathered again yet: «Fill all» does not count it
        self.session.edit("Fill", lambda p: setattr(p.subfields[1], "filled", True))
        full = self.session.project.subfields[1].__dict__.copy()
        steps = self.session.undo.count()
        self.backend.requestFix(index)
        p = self.session.project
        self.assertEqual([sf.filled for sf in p.subfields], [True] * 5)
        self.assertEqual(p.subfields[1].__dict__, full)
        self.assertEqual(self.session.undo.count(), steps + 1)
        self.assertEqual(self.session.undo.steps[-1].text, "Fill all")
        self.assertIn("project:subfields", told[-1])          # the layouts follow as after any change
        self.assertFalse(self.backend.preview)                   # a command, not a fix to keep or take back
        self.assertEqual(self.backend.summary, "")
        self.session.undo.undo()
        self.assertEqual([sf.filled for sf in self.session.project.subfields], [False, True, False, False, False])

    def test_the_menu_of_the_row_and_copy_and_ask(self):
        index = self.merged()["itemIndex"]
        self.assertTrue(self.backend.eye_tip(self.backend.items[index]))
        self.backend.copyText(index)
        self.assertTrue(QGuiApplication.clipboard().text().startswith("5 sub-fields without modules\n"))
        asked = []
        self.backend.askRequested.connect(asked.append)
        self.backend.ask(index)
        self.assertEqual(asked[0].members, tuple(("subfield", f"s{n}") for n in range(1, 6)))
        self.backend.toggleDetail(index)
        self.assertTrue(self.merged()["expanded"])


class PublishedMarks(unittest.TestCase):
    """Inspectors.publish gives the plan and the 3D the marks of viewaids.drawn_marks."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def publish(self, project, items):
        plan, emitted = [], []
        host = SimpleNamespace(
            _published=None, checks=SimpleNamespace(items=items), tree=SimpleNamespace(set_checks=lambda _items: None),
            session=SimpleNamespace(project=project), _marks3d=None, marksChanged=SimpleNamespace(
                emit=lambda: emitted.append(True)), host=SimpleNamespace(plan=SimpleNamespace(setMarks=plan.append)))
        Inspectors.publish(host)
        self.assertEqual(emitted, [True])
        return plan[0], host._marks3d

    def test_information_alone_draws_nothing(self):
        p = imported_project()
        items = checks.gather(p, {}, None)
        self.assertTrue(items)
        self.assertEqual(self.publish(p, items), ([], []))

    def test_an_error_and_a_warning_on_one_point_are_one_mark_on_both_drawings(self):
        p = imported_project()
        p.subfields[1].ring = [list(q) for q in p.subfields[0].ring]
        items = [checks.Item("warn", "layout", "w", target=("subfield", "s1")),
                 checks.Item("fail", "layout", "f", target=("subfield", "s2")),
                 checks.Item("warn", "layout", "g", target=("subfield", "s4"))]
        plan, marks3d = self.publish(p, items)
        self.assertEqual([(m[2], m[3], m[4]) for m in plan], [("fail", 2, ("subfield", "s2")),
                                                             ("warn", 1, ("subfield", "s4"))])
        self.assertEqual([(m["level"], m["count"], m["oid"]) for m in marks3d], [("fail", 2, "s2"), ("warn", 1, "s4")])


if __name__ == "__main__":
    unittest.main()
