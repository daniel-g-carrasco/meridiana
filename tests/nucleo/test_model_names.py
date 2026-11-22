"""R604, format 33: the name of an imported model is the designer's to change. It is saved in the project
(`Project.model_names`, by the bodies' Building.group), changed through session.edit with one step of the undo, and
it is the name wherever the model is named: the short names of its planes («<model> · surface <n>»), the checks, the
arrays of the year, the plant's groups, the report's tables, Meridio. A project of format 32 opens with the name it
had."""
import copy
import unittest

from _fixtures import capannone, laid
from meridiana.app.session import ProjectSession
from meridiana.core.energy import plant, system
from meridiana.core.model import imported, model
from meridiana.core.rules import checks

FILE = "I:/jobs/a long folder/Town hall.ifc"


def two_bodies() -> model.Project:
    """The shed and a canopy of one import (group ifc1), a plane the import made on the shed, laid."""
    p = capannone()
    shed = p.buildings[0]
    shed.name, shed.group = "Town hall", "ifc1"
    p.buildings.append(model.Building(id="b9", name="Town hall 2", footprint=[[50, 0], [60, 0], [60, 8], [50, 8]],
                                      height=4.0, group="ifc1"))
    p.subfields[0].name = f"{FILE}: #604645"
    p.resources = {"ifc_reference": {"file": FILE, "anchor": {"building": shed.id, "footprint": shed.footprint}}}
    return p


def as_format_32(p: model.Project) -> dict:
    data = p.to_json()
    data["version"] = 32
    data.pop("model_names", None)
    return data


class Named(unittest.TestCase):
    def test_a_project_of_format_32_keeps_the_name_it_had(self):
        p = model.Project.from_json(as_format_32(two_bodies()))
        self.assertEqual(p.model_names, {})
        self.assertEqual([m.name for m in imported.models(p)], ["Town hall"])
        self.assertEqual(imported.subfield_name(p, p.subfields[0]), "Town hall · surface 1")

    def test_renamed_once_and_undone_once_and_only_a_text_changed(self):
        session = ProjectSession(two_bodies())
        topics = session.edit("Rename", imported.renamed("ifc1", "  North wing "))
        self.assertEqual(topics, {"project:text", "checks"})        # a name: nothing laid out, no year
        p = session.project
        self.assertEqual(p.model_names, {"ifc1": "North wing"})
        self.assertEqual([m.name for m in imported.models(p)], ["North wing"])
        self.assertEqual([b.name for b in p.buildings], ["Town hall", "Town hall 2"])     # the bodies keep theirs
        self.assertEqual(session.undo.count(), 1)
        session.undo.undo()
        self.assertEqual([m.name for m in imported.models(session.project)], ["Town hall"])
        self.assertEqual(session.project.model_names, {})

    def test_saved_and_read_back(self):
        p = two_bodies()
        imported.renamed("ifc1", "North wing")(p)
        data = p.to_json()
        self.assertEqual((data["version"], data["model_names"]), (model.FORMAT_VERSION, {"ifc1": "North wing"}))
        again = model.Project.from_json(copy.deepcopy(data))
        self.assertEqual([m.name for m in imported.models(again)], ["North wing"])
        self.assertNotIn("model_names", two_bodies().to_json())      # a project without one is written as before

    def test_no_empty_name_and_no_name_for_what_is_not_a_model(self):
        with self.assertRaises(ValueError):
            imported.renamed("ifc1", "   ")
        session = ProjectSession(two_bodies())
        with self.assertRaises(ValueError):
            session.edit("Rename", imported.renamed("ifc7", "Nothing"))
        self.assertEqual(session.project.model_names, {})
        self.assertEqual(session.undo.count(), 0)

    def test_the_new_name_wherever_the_model_is_named(self):
        p = two_bodies()
        imported.renamed("ifc1", "North wing")(p)
        results = {p.subfields[0].id: laid(p, p.subfields[0].id)}
        shown = "North wing · surface 1"
        self.assertEqual(imported.subfield_name(p, p.subfields[0]), shown)
        self.assertEqual(checks.object_names(p)[("subfield", p.subfields[0].id)], shown)
        self.assertEqual([a.name for a in system.arrays_of(p, results)], [shown])
        self.assertEqual({g.name for g in plant.groups_of(p, results)}, {shown})
        from meridiana.app.assistant import tools
        self.assertEqual(tools.object_name(p, "subfield", p.subfields[0].id), shown)
        p.subfields[0].filled = False
        texts = [it.text for it in checks.gather(p, {}, None)]
        self.assertIn(f"{shown}: the modules are not laid yet", texts)

    def test_the_report_tables(self):
        from types import SimpleNamespace
        from unittest import mock

        from meridiana.app.report import chapters
        p = two_bodies()
        imported.renamed("ifc1", "North wing")(p)
        results = {p.subfields[0].id: laid(p, p.subfields[0].id)}
        tables = []

        def tabled(rows, *_a, **_k):
            tables.append(rows)
            return []
        ctx = SimpleNamespace(project=p, get=lambda key: results if key == "results" else None, tabled=tabled,
                              has_chapter=lambda _cid: True, pictures={})
        with mock.patch.object(chapters, "plan_block", lambda _ctx: ""):
            chapters.layout(ctx)
        self.assertEqual(tables[0][0][0], "North wing · surface 1")

    def test_a_new_import_does_not_take_the_name_of_a_model_deleted(self):
        from meridiana.app.exchange import ifc_import
        p = two_bodies()
        imported.renamed("ifc1", "North wing")(p)
        p.buildings = []                            # the model deleted: its group free again
        plan = ifc_import.Plan()
        plan.buildings = [model.Building(id="", name="Depot", footprint=[[0, 0], [9, 0], [9, 9], [0, 9]], height=5.0),
                          model.Building(id="", name="Depot 2", footprint=[[20, 0], [29, 0], [29, 9], [20, 9]],
                                         height=5.0)]
        ifc_import.apply(p, plan)
        self.assertEqual({b.group for b in p.buildings}, {"ifc1"})
        self.assertEqual([m.name for m in imported.models(p)], ["Depot"])


if __name__ == "__main__":
    unittest.main()
