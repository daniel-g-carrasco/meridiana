"""R605: the checks after an import. Short names instead of the import's saved path; the same information on several
objects in one row with their number (errors and warnings stay one per object, in evidence); on the drawings only
errors and warnings have a mark, and marks on one point are one."""

import unittest

import _setup  # noqa: F401

from meridiana.app.view import viewaids
from meridiana.core.model import model
from meridiana.core.rules import checks
from meridiana.core.rules.checks import Item

FILE = "I:/jobs/a long folder/another/Town hall.ifc"


def square(x: float, y: float, side: float) -> list:
    return [[x, y], [x + side, y], [x + side, y + side], [x, y + side]]


def project(empty: int, *, imported: bool = False, extra: tuple = ()) -> model.Project:
    """One building of 60 x 20 m with `empty` sub-fields drawn and not laid; `imported`: two bodies of one import whose
    sub-fields carry the names the import saves («<file>: #12»); `extra`: more sub-fields (id, name, filled, mounting)."""
    p = model.Project(name="Prova")
    p.buildings.append(model.Building(id="b1", name="Town hall", footprint=square(0, 0, 60), height=9.5,
                                      group="ifc1" if imported else ""))
    if imported:
        p.buildings.append(model.Building(id="b2", name="Town hall 2", footprint=square(100, 0, 20), height=6.0,
                                          group="ifc1"))
        p.resources = {"ifc_reference": {"file": FILE, "anchor": {"building": "b1", "footprint": square(0, 0, 60)}}}
    for n in range(empty):
        name = f"{FILE}: #12" if imported else f"Field {n + 1}"
        p.subfields.append(model.SubField(id=f"s{n + 1}", name=name, ring=square(1 + 10 * n, 1, 8), building="b1"))
    for sid, name, filled, mounting in extra:
        p.subfields.append(model.SubField(id=sid, name=name, ring=square(1, 30, 20), building="b1", filled=filled,
                                          params={"mounting": mounting}))
    return p


def results_of(p: model.Project) -> dict:
    return {sf.id: p.fill(sf) for sf in p.subfields if sf.filled}


class Condensed(unittest.TestCase):
    def test_one_sub_field_without_modules_is_said_as_today(self):
        p = project(1)
        items = checks.gather(p, results_of(p), None)
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual((it.level, it.text, it.target), ("info", "Field 1: the modules are not laid yet",
                                                          ("subfield", "s1")))
        self.assertEqual(it.fix, ("action", "fill", "subfield", "s1"))
        self.assertEqual(it.members, ())

    def test_five_sub_fields_without_modules_are_one_row_with_their_number_and_names(self):
        p = project(5)
        items = checks.gather(p, results_of(p), None)
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual((it.level, it.area, it.text), ("info", "layout", "5 sub-fields without modules"))
        self.assertEqual(it.members, tuple(("subfield", f"s{n}") for n in range(1, 6)))
        self.assertEqual(it.target, ())
        # «Fill all»: the bar's «Fill» on the five (app/interface/layout_commands.fill_all)
        self.assertEqual((it.fix, it.fix_label), (("action", "fill_all", "subfield", "s1", "s2", "s3", "s4", "s5"),
                                                  "Fill all"))
        self.assertTrue(it.window_only)
        shared, _sep, names = it.detail.partition("\n\n")
        self.assertIn("«Fill» lays them", shared)
        self.assertEqual(names, "Field 1, Field 2, Field 3, Field 4, Field 5")
        self.assertEqual(checks.counts(items), {"fail": 0, "warn": 0, "info": 1, "ok": 0})
        # what is about one of them includes the row that stands for it
        self.assertEqual(checks.about(items, "subfield", "s3"), [0])
        self.assertEqual(checks.about(items, "subfield", "s9"), [])
        # in the view «by object» it belongs to the project, not to one of the five
        groups = checks.grouped(items, "object", checks.object_names(p))
        self.assertEqual([g.key for g in groups], [("object", "site", "")])
        # calling it again changes nothing
        self.assertEqual(checks.condensed(items, p), items)

    def test_errors_and_warnings_stay_one_row_each_above_the_merged_information(self):
        p = project(5, extra=(("s6", "Broken", False, "tilted_ballasted"), ("s7", "Slab", True, "tilted_ballasted")))
        p.subfields[5].filled = True
        results = results_of(p)
        results["s6"] = ValueError("outside its roof")
        items = checks.gather(p, results, None)
        bad = [(it.level, it.target) for it in items if it.level in ("fail", "warn")]
        self.assertEqual(bad, [("fail", ("subfield", "s6")), ("warn", ("subfield", "s7"))])
        merged = [it for it in items if it.members]
        self.assertEqual(len(merged), 1)
        self.assertGreater(items.index(merged[0]), max(n for n, it in enumerate(items) if it.level in ("fail", "warn")))
        self.assertEqual(sum(1 for it in items if it.same == "unfilled" or it.members), 1)

    def test_warnings_with_the_same_key_are_never_merged(self):
        p = project(2)
        items = [Item("warn", "layout", "a", target=("subfield", "s1"), same="unfilled"),
                 Item("warn", "layout", "b", target=("subfield", "s2"), same="unfilled"),
                 Item("info", "layout", "c", target=("subfield", "s1"), same="unfilled")]
        self.assertEqual(checks.condensed(items, p), items)

    def test_the_names_of_an_import_are_short_and_different_never_its_path(self):
        p = project(3, imported=True)
        p.subfields[1].filled = True                   # one laid: its own checks speak of it too
        p.subfields[1].params = {"mounting": "tilted_ballasted"}
        items = checks.gather(p, results_of(p), None)
        for it in items:
            for words in (it.text, it.detail, it.fix_label):
                self.assertNotIn("Town hall.ifc", words)
                self.assertNotIn("#12", words)
                self.assertNotIn("I:/jobs", words)
        ballast = next(it for it in items if "NTC" in it.source)
        self.assertEqual(ballast.text.partition(":")[0], "Town hall · surface 2")
        merged = next(it for it in items if it.members)
        self.assertEqual(merged.detail.partition("\n\n")[2], "Town hall · surface 1, Town hall · surface 3")
        names = checks.object_names(p)
        shown = [names[("subfield", sf.id)] for sf in p.subfields]
        self.assertEqual(shown, ["Town hall · surface 1", "Town hall · surface 2", "Town hall · surface 3"])
        self.assertEqual(len(set(shown)), 3)

    def test_one_empty_imported_plane_alone_is_named_short(self):
        p = project(1, imported=True)
        (it,) = checks.gather(p, {}, None)
        self.assertEqual(it.text, "Town hall · surface 1: the modules are not laid yet")


class DrawnMarks(unittest.TestCase):
    """The marks of the plan and of the 3D view (viewaids.drawn_marks)."""

    def test_information_has_no_mark_on_the_drawings(self):
        p = project(5)
        items = checks.gather(p, {}, None)
        self.assertTrue(items)
        self.assertEqual(viewaids.drawn_marks(p, items), [])
        self.assertEqual(viewaids.drawn_marks(p, [Item("info", "layout", "x", target=("subfield", "s1"))]), [])

    def test_marks_on_one_point_are_one_with_the_worst_level_and_the_counts_added(self):
        p = project(2)
        p.subfields[1].ring = [list(q) for q in p.subfields[0].ring]          # the same outline: the same anchor
        items = [Item("warn", "layout", "w", target=("subfield", "s1")),
                 Item("fail", "layout", "f", target=("subfield", "s2")),
                 Item("info", "layout", "i", target=("subfield", "s1"))]
        marks = viewaids.drawn_marks(p, items)
        self.assertEqual(len(marks), 1)
        self.assertEqual((marks[0]["level"], marks[0]["count"], marks[0]["kind"], marks[0]["oid"]),
                         ("fail", 2, "subfield", "s2"))
        x, y, z = viewaids.anchor(p, "subfield", "s2")
        self.assertEqual((marks[0]["x"], marks[0]["y"], marks[0]["z"]), (x, y, z))

    def test_marks_apart_stay_two(self):
        p = project(2)                                  # the outlines are 10 m apart
        items = [Item("warn", "layout", "w", target=("subfield", "s1")),
                 Item("fail", "layout", "f", target=("subfield", "s2"))]
        marks = viewaids.drawn_marks(p, items)
        self.assertEqual([(m["oid"], m["level"], m["count"]) for m in marks], [("s1", "warn", 1), ("s2", "fail", 1)])

    def test_a_tie_keeps_the_first_and_close_means_closer_than_the_join(self):
        p = project(2)
        p.subfields[1].ring = [[x + viewaids.MARK_JOIN * 0.8, y] for x, y in p.subfields[0].ring]
        items = [Item("warn", "layout", "a", target=("subfield", "s1")),
                 Item("warn", "layout", "b", target=("subfield", "s2"))]
        (one,) = viewaids.drawn_marks(p, items)
        self.assertEqual((one["oid"], one["level"], one["count"]), ("s1", "warn", 2))
        p.subfields[1].ring = [[x + viewaids.MARK_JOIN * 1.5, y] for x, y in p.subfields[0].ring]
        self.assertEqual(len(viewaids.drawn_marks(p, items)), 2)


if __name__ == "__main__":
    unittest.main()
