"""The project file (model.py): everything comes back as it was saved, the previous save kept as .bak, a damaged
file opened from it and said; a file edited by hand or damaged refused with the path of the key; one frozen file
for every version of the format, 1 to 15, opened as it is (tests/formati/file), and the migrations field by field.
The files of the settings and the damaged ones are in test_formats."""

import json
import math
import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import capannone_rho as sample

from meridiana import model


class Files(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.file = self.dir / "progetto.meridiana"

    def test_a_project_comes_back_as_it_was_saved(self):
        p = sample()
        p.save(self.file)
        q, notice = model.Project.load(self.file)
        self.assertIsNone(notice)
        self.assertEqual(q.to_json() | {"modified": None}, p.to_json() | {"modified": None})

    def test_the_maker_chosen_for_the_inverters_comes_back(self):
        """R141 wrote it in the energy of the variant and the file's check did not know it: Daniel, 27/10/2026,
        opened his project and read «1 keys this Meridiana does not know were left out: ...inverter_maker»."""
        p = sample()
        p.energy["inverter_maker"] = "Huawei"
        p.save(self.file)
        q, notice = model.Project.load(self.file)
        self.assertIsNone(notice)
        self.assertEqual(q.energy["inverter_maker"], "Huawei")

    def test_a_second_save_keeps_the_first_as_backup(self):
        p = sample()
        p.save(self.file)
        p.name = "Rinominato"
        p.save(self.file)
        backup = json.loads((self.dir / "progetto.meridiana.bak").read_text(encoding="utf-8"))
        self.assertEqual(backup["name"], "Capannone Rho")

    def test_a_damaged_file_opens_the_previous_save_and_says_so(self):
        p = sample()
        p.save(self.file)
        p.save(self.file)
        self.file.write_text('{"format": "meridiana-proj', encoding="utf-8")
        q, notice = model.Project.load(self.file)
        self.assertEqual(q.name, "Capannone Rho")
        self.assertIn("previous save", notice)

    def test_a_newer_format_is_refused(self):
        data = sample().to_json()
        data["version"] = model.FORMAT_VERSION + 1
        with self.assertRaises(ValueError):
            model.Project.from_json(data)

    def test_a_file_of_the_first_format_is_read(self):
        data = sample().to_json()
        data["version"] = 1
        for raw in data["exclusions"]:
            raw.pop("height")
        for raw in data["buildings"]:
            raw.pop("parapet")
        q = model.Project.from_json(data)
        self.assertIsNone(q.exclusions[1].height)          # the default of its kind
        self.assertEqual(q.buildings[0].parapet, 0.0)

    def test_something_else_is_not_a_project(self):
        with self.assertRaises(ValueError):
            model.Project.from_json({"name": "x"})


class Damaged(unittest.TestCase):
    """A file edited by hand or damaged is said with the path of the key, never a crash later (study 18, A 5.1,
    G 6.1: twenty files, eight of them crashed the window's slot)."""

    def base(self) -> dict:
        return json.loads(json.dumps(sample().to_json()))

    def refused(self, data, words: str) -> None:
        with self.assertRaises(ValueError) as caught:
            model.Project.from_json(data)
        self.assertIn(words, str(caught.exception))

    def test_a_version_that_is_not_a_number_is_refused(self):
        self.refused({**self.base(), "version": "6"}, "version")
        self.refused({**self.base(), "version": 0}, "version")

    def test_a_building_that_is_not_a_table_or_has_no_id_is_refused(self):
        self.refused({**self.base(), "buildings": ["x"]}, "buildings[0]")
        self.refused({**self.base(), "buildings": [{"name": "a", "footprint": []}]}, "'id' is missing")

    def test_a_footprint_of_text_or_of_two_points_is_refused(self):
        b = self.base()
        b["buildings"][0]["footprint"] = "abc"
        self.refused(b, "buildings[0].footprint")
        b["buildings"][0]["footprint"] = [[0, 0], [1, 1]]
        self.refused(b, "at least 3")

    def test_nan_and_absurd_numbers_are_refused_with_their_path(self):
        self.refused(json.loads(json.dumps(self.base()).replace("45.5226", "NaN")), "site.lat")
        self.refused({**self.base(), "site": {"lat": 1e308, "lon": 9.0, "address": ""}}, "site.lat")
        b = self.base()
        b["buildings"][0]["height"] = 1e300
        self.refused(b, "buildings[0].height")

    def test_a_module_without_its_size_is_refused_before_the_layout(self):
        b = self.base()
        b["variants"][0]["design"]["modules"] = {"m1": {"manufacturer": "X", "model": "Y"}}
        self.refused(b, "modules[m1]")

    def test_variants_that_are_not_tables_are_refused(self):
        self.refused({**self.base(), "variants": ["v1"], "variant": "v1"}, "variants[0]")

    def test_unknown_keys_are_left_out_and_said(self):
        unknown: list = []
        data = {**self.base(), "foo": 1}
        data["site"]["bar"] = 2
        p = model.Project.from_json(data, unknown=unknown)
        self.assertEqual(sorted(unknown), ["foo", "site.bar"])
        self.assertNotIn("foo", p.to_json())
        d = Path(tempfile.mkdtemp())
        (d / "p.meridiana").write_text(json.dumps(data), encoding="utf-8")
        _p, notice = model.Project.load(d / "p.meridiana")
        self.assertIn("2 keys this Meridiana does not know were left out: ", notice)
        self.assertIn("site.bar", notice)
        del data["foo"]
        (d / "p.meridiana").write_text(json.dumps(data), encoding="utf-8")
        _p, notice = model.Project.load(d / "p.meridiana")
        self.assertEqual(notice, "1 key this Meridiana does not know was left out: site.bar")     # one, not «1 keys»

    def test_the_windows_own_snapshots_skip_the_check(self):
        data = {**self.base(), "foo": 1}
        model.Project.from_json(data, check=False)


class Formats(unittest.TestCase):
    """One frozen file for every version of the format, opened as it is: the files of the designer never stop
    opening (study 18, D 6.1)."""

    def test_every_version_of_the_format_opens(self):
        folder = _setup.FORMATS
        for version in range(1, model.FORMAT_VERSION + 1):
            with self.subTest(version=version):
                p, notice = model.Project.load(folder / f"progetto-v{version}.meridiana")
                self.assertIsNone(notice)
                self.assertEqual(p.name, "Capannone Rho")
                self.assertEqual([b.name for b in p.buildings], ["Capannone"])
                self.assertEqual(len(p.subfields), 1)
                self.assertEqual(p.variants[0]["id"], p.variant)
                self.assertEqual(p.to_json()["version"], model.FORMAT_VERSION)

    def test_the_sixth_format_migrates_to_the_seventh_field_by_field(self):
        folder = _setup.FORMATS
        six = json.loads((folder / "progetto-v6.meridiana").read_text(encoding="utf-8"))
        seven = json.loads((folder / "progetto-v7.meridiana").read_text(encoding="utf-8"))
        migrated = model.MIGRATIONS[6](six)
        for key in model.DESIGN:                            # the design of the one in hand went into its variant
            self.assertNotIn(key, migrated)
            self.assertEqual(migrated["variants"][0]["design"][key], six[key])
        self.assertEqual(migrated["variants"][0]["design"], seven["variants"][0]["design"])
        for key in ("name", "site", "sun_window", "buildings", "exclusions", "consumption", "rules", "variant",
                    "underlays", "created", "modified"):
            self.assertEqual(migrated[key], seven[key], key)
        self.assertNotIn("app_version", seven)
        p6, p7 = model.Project.load(folder / "progetto-v6.meridiana")[0], model.Project.load(folder / "progetto-v7.meridiana")[0]
        self.assertEqual(p6, p7)
        # a pitch drawn by hand gets an id on the way
        six["buildings"][0]["roof"] = {"type": "free", "free_pitches": [
            {"ring": [[0, 0], [10, 0], [10, 5], [0, 5]], "eave_side": 0, "eave": 6.0, "tilt": 20.0}]}
        self.assertEqual(model.MIGRATIONS[6](six)["buildings"][0]["roof"]["free_pitches"][0]["id"], "p1")

    def test_the_seventh_format_migrates_to_the_eighth_with_the_inverter_first_of_a_list(self):
        folder = _setup.FORMATS
        seven = json.loads((folder / "progetto-v7.meridiana").read_text(encoding="utf-8"))
        rec = {"manufacturer": "Acme", "model": "50K", "ac_power_nominal_w": 50000}
        seven["variants"][0]["design"]["energy"] = {"inverter": rec, "inverter_count": 3, "dc_ac_ratio": 1.2,
                                                    "strings": {"n_series": 15, "per_mppt": [2, 1]}}
        seven["variants"].append({"id": "v2", "name": "Senza", "note": "",
                                  "design": {"energy": {"inverter_count": 2}}})
        eight = model.MIGRATIONS[7](seven)
        energy = eight["variants"][0]["design"]["energy"]
        self.assertEqual(energy["inverters"], [{"record": rec, "count": 3, "name": ""}])
        self.assertNotIn("inverter", energy)
        self.assertNotIn("inverter_count", energy)
        self.assertEqual((energy["dc_ac_ratio"], energy["strings"]), (1.2, {"n_series": 15, "per_mppt": [2, 1]}))
        self.assertEqual(eight["variants"][1]["design"]["energy"], {})     # a count without an inverter meant nothing
        p = model.Project.from_json(seven)
        self.assertEqual(p.energy["inverters"][0]["count"], 3)
        # the file of format 8 has the inverters, an input chosen for its sub-field and strings by hand
        p8, notice = model.Project.load(folder / "progetto-v8.meridiana")
        self.assertIsNone(notice)
        self.assertEqual((p8.energy["inverters"][0]["count"], p8.subfields[0].params["mppt"]), (2, 2))
        self.assertFalse(p8.energy["strings"]["auto"])

    def test_the_ninth_format_has_the_sides_the_ridge_and_the_covering_of_a_roof(self):
        folder = _setup.FORMATS
        p, notice = model.Project.load(folder / "progetto-v9.meridiana")
        self.assertIsNone(notice)
        b = p.buildings[0]
        self.assertEqual((b.roof.edges, b.roof.ridge_height, b.roof.covering),
                         (["eave", "gable", "eave", "gable"], 10.2, "metal"))
        self.assertAlmostEqual(b.slope(), math.degrees(math.atan(0.7 / 10.0)), places=9)   # from the ridge
        self.assertAlmostEqual(b.ridge(), 10.2, places=9)
        self.assertEqual(p.surface_of(p.subfields[0]).azimuth, 0.0)                       # the eave of side 1

    def test_the_twelfth_format_keeps_a_project_reserved_and_the_older_ones_open_not_reserved(self):
        """Task 14: a reserved project is never sent to a cloud model; the mark has its own format, so that an older
        Meridiana refuses the file instead of saving it again without the mark."""
        folder = _setup.FORMATS
        p, notice = model.Project.load(folder / "progetto-v12.meridiana")
        self.assertIsNone(notice)
        self.assertTrue(p.reserved)
        self.assertTrue(p.to_json()["reserved"])
        self.assertFalse(model.Project.load(folder / "progetto-v11.meridiana")[0].reserved)
        eleven = json.loads((folder / "progetto-v11.meridiana").read_text(encoding="utf-8"))
        twelve = json.loads((folder / "progetto-v12.meridiana").read_text(encoding="utf-8"))
        self.assertEqual(model.MIGRATIONS[11](eleven), {**eleven, "reserved": False})
        self.assertEqual({k: v for k, v in twelve.items() if k not in ("reserved", "version")},
                         {k: v for k, v in eleven.items() if k != "version"})
        twelve["reserved"] = "yes"
        with self.assertRaisesRegex(ValueError, "reserved"):
            model.Project.from_json(twelve)

    def test_the_thirteenth_format_keeps_the_optimizers_of_an_inverter(self):
        """Task 22: a SolarEdge inverter keeps its power optimizers in its entry; an older Meridiana would drop them at
        the first change of a count, so they have a format of their own and a file before migrates unchanged."""
        from meridiana.energy import system
        folder = _setup.FORMATS
        p, notice = model.Project.load(folder / "progetto-v13.meridiana")
        self.assertIsNone(notice)
        (entry,) = system.inverter_entries(p.energy)
        self.assertEqual((entry["record"]["model"], entry["optimizer"]["model"], entry["per_optimizer"]),
                         ("SE5000H", "S500", 1))
        self.assertEqual(p.to_json()["variants"][0]["design"]["energy"]["inverters"][0]["optimizer"]["model"], "S500")
        twelve = json.loads((folder / "progetto-v12.meridiana").read_text(encoding="utf-8"))
        self.assertEqual(model.MIGRATIONS[12](twelve), twelve)
        thirteen = json.loads((folder / "progetto-v13.meridiana").read_text(encoding="utf-8"))
        thirteen["variants"][0]["design"]["energy"]["inverters"][0]["per_optimizer"] = 3
        with self.assertRaisesRegex(ValueError, "per_optimizer"):
            model.Project.from_json(thirteen)
        thirteen["variants"][0]["design"]["energy"]["inverters"][0]["per_optimizer"] = 2
        thirteen["variants"][0]["design"]["energy"]["inverters"][0]["optimizer"] = "S500"
        with self.assertRaisesRegex(ValueError, "optimizer"):
            model.Project.from_json(thirteen)

    def test_the_fourteenth_format_keeps_the_proposal_of_before_and_never_proposes_by_itself(self):
        """R114, R118: from format 14 the strings are the designer's and nothing makes them by itself. A file of 13
        whose strings were Meridiana's live proposal (no «auto», or «auto» true) keeps it as an explicit «auto», which
        the window writes down at the first layout; strings by hand stay by hand; a file of 14 without strings has
        none."""
        from meridiana.energy import plant
        folder = _setup.FORMATS
        p, notice = model.Project.load(folder / "progetto-v14.meridiana")
        self.assertIsNone(notice)
        self.assertNotIn("auto", p.energy["strings"])                              # the designer's, by hand
        self.assertEqual(len(p.energy["strings"]["runs"]), 1)
        proposal = next(v for v in p.variants if v["id"] == "v2")["design"]["energy"]["strings"]
        self.assertTrue(proposal["auto"])
        thirteen = json.loads((folder / "progetto-v13.meridiana").read_text(encoding="utf-8"))
        energy = thirteen["variants"][0]["design"]["energy"]
        self.assertEqual(model.MIGRATIONS[13](thirteen)["variants"][0]["design"]["energy"]["strings"],
                         energy["strings"])                                          # by hand: unchanged
        energy.pop("strings")
        self.assertEqual(model.MIGRATIONS[13](thirteen)["variants"][0]["design"]["energy"]["strings"], {"auto": True})
        thirteen["variants"][0]["design"]["energy"] = {}
        self.assertEqual(model.MIGRATIONS[13](thirteen)["variants"][0]["design"]["energy"], {"strings": {"auto": True}})
        fresh = model.Project(name="Nuovo")
        self.assertFalse(plant.build(fresh, groups=[]).auto)
        self.assertIsNone(model.Project.from_json(fresh.to_json()).energy.get("strings"))

    def test_the_input_of_a_sub_field_lays_out_nothing_again(self):
        p = sample()
        sf = p.subfields[0]
        key = p.layout_key(sf)
        sf.params["inverter"], sf.params["mppt"] = 2, 1
        self.assertEqual(p.layout_key(sf), key)
        sf.params["tilt"] = 22.0
        self.assertNotEqual(p.layout_key(sf), key)


if __name__ == "__main__":
    unittest.main()
