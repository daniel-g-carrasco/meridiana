"""tools/update_cec.py: NREL's «CEC Modules.csv» becomes the catalogue's list of modules. The fixture is ten rows cut
out of the real file (BSD-3-Clause, NREL; list 2026.7.3 of 6/23/2026) with its three header lines; the tests never
need the network."""

import contextlib
import gzip
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

import _setup

from meridiana import catalog

TOOL = _setup.ROOT / "tools" / "update_cec.py"
spec = importlib.util.spec_from_file_location("update_cec", TOOL)
update_cec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update_cec)

KEYS = {"id", "source", "manufacturer", "model", "technology", "bifacial", "pmax", "vmp", "imp", "voc", "isc",
        "gamma_pmax", "beta_voc", "alpha_isc", "cells_in_series", "length", "width", "noct", "bipv", "sdm",
        "list_version", "list_date"}


def extract() -> str:
    return _setup.fixture_text("cec_modules_extract.csv")


class Reading(unittest.TestCase):
    def setUp(self):
        self.records, self.left_out = update_cec.parse(extract())
        self.by_name = {r["id"]: r for r in self.records}

    def test_ten_rows_give_ten_records_with_the_fields_of_the_catalogue(self):
        self.assertEqual(len(self.records), 10)
        self.assertEqual(self.left_out, [])
        for r in self.records:
            self.assertEqual(set(r), KEYS, r["id"])
            self.assertEqual(r["source"], "cec")
            self.assertEqual(set(r["sdm"]), {"I_L_ref", "I_o_ref", "R_s", "R_sh_ref", "a_ref", "Adjust"})

    def test_a_plain_row_in_the_units_of_the_catalogue(self):
        r = self.by_name["cec:Ablytek 6MN6A270"]
        self.assertEqual((r["manufacturer"], r["model"], r["technology"]), ("Ablytek", "6MN6A270", "Mono-c-Si"))
        self.assertIs(r["bifacial"], False)
        self.assertIs(r["bipv"], False)
        self.assertEqual((r["pmax"], r["vmp"], r["imp"], r["voc"], r["isc"]), (270.0, 30.72, 8.81, 38.63, 9.34))
        self.assertEqual(r["gamma_pmax"], -0.4509)                          # %/K as the list gives it
        self.assertAlmostEqual(r["beta_voc"], -0.12118231 / 38.63 * 100.0, places=4)           # V/K to %/K
        self.assertAlmostEqual(r["alpha_isc"], 0.00486614 / 9.34 * 100.0, places=4)            # A/K to %/K
        self.assertEqual(r["beta_voc"], -0.3137)
        self.assertEqual(r["alpha_isc"], 0.0521)
        self.assertEqual((r["cells_in_series"], r["length"], r["width"], r["noct"]), (60, 1.64, 0.992, 47.4))
        self.assertAlmostEqual(r["sdm"]["a_ref"], 1.582695, places=6)
        self.assertAlmostEqual(r["sdm"]["I_o_ref"], 2.3387860831589717e-10, places=24)
        self.assertEqual(r["sdm"]["R_sh_ref"], 1352.292)
        self.assertEqual((r["list_version"], r["list_date"]), ("2026.7.3", "2026-06-23"))

    def test_every_record_says_which_list_it_comes_from(self):
        self.assertEqual({(r["list_version"], r["list_date"]) for r in self.records}, {("2026.7.3", "2026-06-23")})

    def test_the_flags_and_the_missing_sizes(self):
        bifacial = self.by_name["cec:ALTERNATIVE ENERGY (AE) SOLAR CO LTD AE385MD-108BS"]
        self.assertIs(bifacial["bifacial"], True)
        self.assertIsNone(bifacial["length"])
        self.assertIsNone(bifacial["width"])
        self.assertEqual(sum(r["bipv"] for r in self.records), 1)
        self.assertEqual(sum(r["bifacial"] for r in self.records), 4)
        self.assertEqual(sum(1 for r in self.records if r["length"] and r["width"]), 4)

    def test_stray_spaces_stay_in_the_id_and_go_from_the_names(self):
        r = self.by_name["cec:Yingli Energy Development Co Ltd YL540D-49e1500V   "]
        self.assertEqual((r["manufacturer"], r["model"]), ("Yingli Energy Development Co Ltd", "YL540D-49e1500V"))

    def test_the_materials_are_kept_as_the_list_writes_them(self):
        self.assertEqual({r["technology"] for r in self.records},
                         {"Mono-c-Si", "Mono-C-si", "Multi-c-Si", "CdTe", "a-Si/nc"})

    def test_the_records_are_what_the_catalogue_already_holds(self):
        """The rebuilt file and the one in the program agree on these ten modules."""
        shipped = {r["id"]: r for r in catalog.load("modules") if r["source"] == "cec"}
        for r in self.records:
            kept = shipped[r["id"]]
            self.assertEqual({k: v for k, v in kept.items() if k in KEYS}, r, r["id"])


class WhatCannotBeRead(unittest.TestCase):
    def lines(self):
        return extract().split("\n")

    def test_a_row_with_an_empty_figure_is_left_out_and_said(self):
        lines = self.lines()
        cells = lines[3].split(",")
        cells[9] = ""                                                        # N_s, the cells in series
        lines[3] = ",".join(cells)
        records, left_out = update_cec.parse("\n".join(lines))
        self.assertEqual(len(records), 9)
        self.assertEqual(len(left_out), 1)
        self.assertEqual(left_out[0][0], "Ablytek 6MN6A270")
        self.assertIn("N_s is empty", left_out[0][1])

    def test_a_date_that_is_not_month_day_year_leaves_the_row_out(self):
        lines = self.lines()
        lines[3] = lines[3].replace("6/23/2026", "2026-06-23")
        records, left_out = update_cec.parse("\n".join(lines))
        self.assertEqual(len(records), 9)
        self.assertIn("Date", left_out[0][1])

    def test_a_name_that_comes_twice_is_kept_once_with_the_last_figures(self):
        lines = self.lines()
        twin = lines[3].split(",")
        twin[5] = "199.9"                                                     # PTC, only to tell the rows apart
        twin[16] = "50"                                                      # T_NOCT
        lines.insert(4, ",".join(twin))
        records, left_out = update_cec.parse("\n".join(lines))
        self.assertEqual(len(records), 10)
        self.assertEqual(len(left_out), 1)
        self.assertIn("twice, with different figures", left_out[0][1])
        self.assertEqual({r["id"]: r for r in records}["cec:Ablytek 6MN6A270"]["noct"], 50.0)
        _records, same = update_cec.parse("\n".join(self.lines()[:4] + [self.lines()[3]] + self.lines()[4:]))
        self.assertIn("with the same figures", same[0][1])

    def test_a_file_that_is_not_the_list_is_refused(self):
        with self.assertRaises(ValueError):
            update_cec.parse("a,b,c\n1,2,3\n4,5,6\n7,8,9\n")
        with self.assertRaises(ValueError):
            update_cec.parse("")

    def test_blank_lines_are_not_rows(self):
        records, left_out = update_cec.parse(extract() + "\n\n,,,,\n")
        self.assertEqual((len(records), left_out), (10, []))


class Writing(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: [p.unlink() for p in self.folder.iterdir()] and self.folder.rmdir())
        self.csv = self.folder / "CEC Modules.csv"
        self.csv.write_text(extract(), encoding="utf-8")
        self.out = self.folder / "modules_cec.json.gz"

    def run_tool(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = update_cec.main(["--file", str(self.csv), "--output", str(self.out), *args])
        return code, out.getvalue()

    def test_the_file_written_is_the_records_and_does_not_change_when_they_do_not(self):
        code, said = self.run_tool()
        self.assertEqual(code, 0)
        self.assertIn("10 modules, list 2026.7.3 of 2026-06-23 (the file in use has 0)", said)
        with gzip.open(self.out, "rt", encoding="utf-8") as fh:
            written = json.load(fh)
        self.assertEqual(written, update_cec.parse(extract())[0])
        first = self.out.read_bytes()
        code, said = self.run_tool()
        self.assertIn("(the file in use has 10)", said)
        self.assertIn("added 0, gone 0, figures changed 0", said)
        self.assertEqual(self.out.read_bytes(), first)                       # no date in the gzip header

    def test_a_dry_run_writes_nothing(self):
        code, said = self.run_tool("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("dry run: nothing written", said)
        self.assertFalse(self.out.exists())

    def test_the_comparison_names_what_was_added_gone_and_changed(self):
        old = update_cec.parse(extract())[0]
        new = [dict(r) for r in old[1:]]                                     # one gone
        new[0] = dict(new[0], noct=40.0)                                     # one changed
        new.append(dict(old[0], id="cec:New Maker NM-1"))                    # one added
        new[1] = dict(new[1], list_version="9.9.9")                          # the version alone is no change
        changes = update_cec.compare(old, new)
        self.assertEqual(changes["added"], ["cec:New Maker NM-1"])
        self.assertEqual(changes["removed"], [old[0]["id"]])
        self.assertEqual(changes["changed"], [new[0]["id"]])

    def test_a_file_that_is_not_the_list_writes_nothing(self):
        self.csv.write_text("a,b,c\n1,2,3\n4,5,6\n7,8,9\n", encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = update_cec.main(["--file", str(self.csv), "--output", str(self.out)])
        self.assertEqual(code, 1)
        self.assertIn("not NREL", err.getvalue())
        self.assertFalse(self.out.exists())

    def test_the_licence_of_the_list_goes_with_it(self):
        self.assertTrue(update_cec.LICENCE.exists())
        self.assertIn("BSD 3-Clause", update_cec.LICENCE.read_text(encoding="utf-8"))
        self.assertTrue(update_cec.URL.startswith("https://raw.githubusercontent.com/NREL/SAM/"))


class TheListInUse(unittest.TestCase):
    def test_the_list_in_the_program_is_the_one_the_tool_made(self):
        modules = [r for r in catalog.load("modules") if r["source"] == "cec"]
        self.assertGreater(len(modules), 21000)
        self.assertEqual({(r["list_version"], r["list_date"]) for r in modules}, {("2026.7.3", "2026-06-23")})
        self.assertEqual(sum(1 for r in modules if r.get("length") and r.get("width")), 5669)
        self.assertEqual(sum(r["bifacial"] for r in modules), 3758)
        self.assertEqual(len({r["id"] for r in modules}), len(modules))


if __name__ == "__main__":
    unittest.main()
