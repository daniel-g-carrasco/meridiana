"""The short name of a plane the import made is the one shown wherever the program names a sub-field (R605): the
arrays of the year, the plant's groups, the faces, the report's tables, Meridio's tools, the drawing exported. None of
them shows the file's path or the element's number the import saves as the sub-field's name."""
import unittest

from _fixtures import capannone, laid
from meridiana.core.energy import faces, plant, system
from meridiana.core.model import imported

SAVED = "I:/jobs/a long folder/another/Town hall.ifc: #604645"
SHOWN = "Capannone · surface 1"


def project():
    p = capannone()
    p.subfields[0].name = SAVED
    return p, {p.subfields[0].id: laid(p, p.subfields[0].id)}


class Shown(unittest.TestCase):
    def assertShort(self, text):
        self.assertNotIn("I:/", text)
        self.assertNotIn("#604645", text)

    def test_the_rule_gives_the_short_name(self):
        p, _results = project()
        self.assertEqual(imported.subfield_name(p, p.subfields[0]), SHOWN)

    def test_the_arrays_and_the_groups_of_the_plant(self):
        p, results = project()
        self.assertEqual([a.name for a in system.arrays_of(p, results)], [SHOWN])
        self.assertEqual({g.name for g in plant.groups_of(p, results)}, {SHOWN})

    def test_a_face_on_the_ground(self):
        p, _results = project()
        p.subfields[0].building = None
        self.assertEqual(faces.faces_of(p)[p.subfields[0].id].name, "Town hall · surface 1")

    def test_meridio_names_it_short(self):
        from meridiana.app.assistant import tools
        p, _results = project()
        self.assertEqual(tools.object_name(p, "subfield", p.subfields[0].id), SHOWN)

    def test_the_report_tables(self):
        from types import SimpleNamespace
        from unittest import mock

        from meridiana.app.report import chapters
        p, results = project()
        tables = []

        def tabled(rows, *_a, **_k):
            tables.append(rows)
            return []
        ctx = SimpleNamespace(project=p, get=lambda key: results if key == "results" else None, tabled=tabled,
                              has_chapter=lambda _cid: True, pictures={})
        with mock.patch.object(chapters, "plan_block", lambda _ctx: ""):
            chapters.layout(ctx)
        with mock.patch.object(chapters.profiles, "for_project",
                               lambda _p: SimpleNamespace(report_fragment=lambda *_a: [])):
            chapters.fields(ctx)
        self.assertEqual([rows[0][0] for rows in tables], [SHOWN, SHOWN])
        self.assertShort(str(tables))


if __name__ == "__main__":
    unittest.main()
