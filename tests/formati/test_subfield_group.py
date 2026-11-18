"""The group of the parts of a sub-field split on its ridge (R426): an optional field, written only when there is one,
without a new format. A project saved before opens the same; a sub-field out of a group is written as before."""
import json
import tempfile
import unittest
from pathlib import Path

from meridiana import model, move


def project():
    p = model.Project(name="Prova")
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=8.0, roof=model.Roof(type="gable", tilt=15.0)))
    p.subfields.append(model.SubField(id="s1", name="Tetto", ring=[[10, 6], [20, 6], [20, 14], [10, 14]],
                                      building="b1", pitch=p.buildings[0].pitch_ref(0), filled=True))
    return p


class Group(unittest.TestCase):
    def test_no_new_format_number(self):
        data = project().to_json()
        self.assertEqual(data["version"], model.FORMAT_VERSION)
        self.assertEqual(model.FORMAT_VERSION, 30)      # 27 is R445 (flush, kept, band), 28 the solids (study 37),
        # 29 R523 (the layout of the next sub-fields), 30 R374 (a 3D object's model): R426 adds no number

    def test_a_sub_field_out_of_a_group_is_written_as_before(self):
        design = next(v["design"] for v in project().to_json()["variants"])
        self.assertNotIn("group", design["subfields"][0])

    def test_the_key_of_a_layout_does_not_see_the_group(self):
        p = project()
        key = p.layout_key(p.subfields[0])
        p.subfields[0].group = "s1"
        self.assertEqual(p.layout_key(p.subfields[0]), key)

    def test_a_file_written_before_opens_the_same(self):
        p = project()
        data = json.loads(json.dumps(p.to_json()))
        unknown = []
        q = model.Project.from_json(data, unknown=unknown)
        self.assertEqual(unknown, [])
        self.assertEqual(q.subfields[0].group, "")
        self.assertEqual(q.to_json()["variants"], data["variants"])

    def test_saved_and_opened_the_parts_stay_together(self):
        p = project()
        move.split_on_pitches(p, "s1")(p)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "p.meridiana"
            p.save(path)
            q = model.Project.load(path)[0]
        self.assertEqual([s.group for s in q.subfields], [s.group for s in p.subfields])
        self.assertEqual(len({s.group for s in q.subfields}), 1)
        self.assertEqual(len(move.moving(q, "subfield", "s1")), 2)

    def test_a_group_that_is_not_text_is_refused_with_its_path(self):
        data = json.loads(json.dumps(project().to_json()))
        next(v for v in data["variants"])["design"]["subfields"][0]["group"] = 3
        with self.assertRaisesRegex(ValueError, "group"):
            model.Project.from_json(data)


if __name__ == "__main__":
    unittest.main()
