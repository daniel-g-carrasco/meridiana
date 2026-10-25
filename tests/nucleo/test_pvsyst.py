"""PVsyst projects opened in Meridiana: the text format read from its markers (lists, records, groups,
circuit nodes, split values, PVsyst's irregular closers), the hourly records in base 62, a project with its
variants, and the Meridiana project made from them, with what was approximated or missing said. The files of
tests/data/pvsyst were written by hand for these tests (see its README); the real files of the study are read
in esterni/test_pvsyst_campioni.py, when MERIDIANA_PVSYST_SAMPLES names their folder."""

import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401

from meridiana import model
from meridiana.pvsyst import mapping, pvobject, records
from meridiana.pvsyst import project as pvproject

DATA = _setup.DATA / "pvsyst"
PRJ = DATA / "Prova Rho_Project.PRJ"


class Format(unittest.TestCase):
    def test_the_markers_build_the_tree(self):
        doc = pvobject.read(DATA / "Prova Rho_Project.VC0")
        self.assertEqual(doc.anomalies, [])
        self.assertEqual(doc.top.type, "pvVCalcul")
        circuit = doc.root.find(type="pvCircuit")
        self.assertEqual([n.name for n in circuit.walk() if n.kind == "circuit"],
                         ["InjectionPointNode", "InverterNode", "MPPTNode", "StringNode"])
        table = doc.root.find(type="TInterpole2D")                 # closed by "End of TInterpolenD"
        self.assertEqual(table.get("Line_1"), "0.000,0.000,0.000,0.000,")     # the _contd line joined
        self.assertEqual(doc.root.find(type="pvIAM").find(type="TCubicProfile").get("Point_9"), "90.0,0.00000")

    def test_what_does_not_close_is_noted_not_fatal(self):
        doc = pvobject.parse("PVObject_=pvProject\n  Comment=x\n  EndTags\n")
        self.assertEqual(doc.top.get("Comment"), "x")
        self.assertEqual([a[1] for a in doc.anomalies], ["EndTags without its opener", "object pvProject never closed"])

    def test_binary_files_before_6_40_are_refused(self):
        path = Path(tempfile.mkdtemp()) / "old.PAN"
        path.write_bytes(b"\x1a\x00\x05PVsyst binary")
        with self.assertRaises(pvobject.FormatError) as caught:
            pvobject.read(path)
        self.assertIn("6.39", str(caught.exception))

    def test_reading_errors_speak_italian(self):
        from meridiana import i18n
        before = i18n._translation
        self.addCleanup(lambda: setattr(i18n, "_translation", before))
        i18n.setup("it")
        folder = Path(tempfile.mkdtemp())
        binary = folder / "old.PAN"
        binary.write_bytes(b"\x1a\x00\x05PVsyst binary")
        with self.assertRaises(pvobject.FormatError) as caught:
            pvobject.read(binary)
        self.assertEqual(str(caught.exception), "old.PAN: non è un file di testo PVsyst "
                         "(PVsyst scriveva file binari fino a 6.39)")
        wrong = folder / "wrong.PRJ"
        wrong.write_text("PVObject_=pvSite\nEnd of PVObject pvSite\n", encoding="utf-8")
        for read, expected in ((pvproject.read_project, "non è un progetto PVsyst"),
                               (pvproject.read_variant, "non è una variante PVsyst"),
                               (pvproject.read_met, "non è un file meteo PVsyst")):
            with self.subTest(reader=read.__name__), self.assertRaises(pvobject.FormatError) as caught:
                read(wrong)
            self.assertEqual(str(caught.exception), f"wrong.PRJ: {expected}")
        var = pvobject.Node("var", "", attrs=[("Day_0101", "+0+1")])
        with self.assertRaises(ValueError) as caught:
            records.series(var)
        self.assertEqual(str(caught.exception), "Day_0101: 2 valori invece di 24")

    def test_the_hourly_records_in_base_62(self):
        self.assertEqual(records.day("+0+w+RE-1C"), [0, 58, 1688, -74])
        var = pvobject.read(DATA / "Prova Rho_Project.VC0").root.find(type="E_Grid")
        hourly = records.series(var)
        self.assertEqual(len(hourly), 48)
        self.assertAlmostEqual(hourly[8], 1.0)                      # "A" is 10, the WRFactor 10
        self.assertAlmostEqual(hourly[11], 1688 / 10)


class Reading(unittest.TestCase):
    def test_the_project_and_its_variants(self):
        prj = pvproject.read_project(PRJ)
        self.assertEqual((prj.name, prj.version), ("Prova Rho", "8.0.18"))
        self.assertEqual((prj.site.lat, prj.site.lon, prj.site.altitude), (45.5226, 9.03, 150.0))
        self.assertEqual(prj.albedo[-1], 0.3)
        self.assertEqual(prj.design_t_min, -12.0)
        self.assertEqual([v.comment for v in prj.variants], ["File da 3", "Piano ovest"])

    def test_a_variant_with_sheds_and_its_scene(self):
        v = pvproject.read_variant(DATA / "Prova Rho_Project.VC0")
        (o,) = v.orientations
        self.assertEqual((o.kind, o.tilt, o.azimuth, o.sheds, o.pitch), ("Sheds", 25.0, 0.0, 3, 5.0))
        (s,) = v.sub_arrays
        self.assertEqual((s.n_series, s.n_strings, s.modules), (15, 2, 30))
        self.assertEqual((s.quality, s.mismatch, s.string_mismatch, s.lid, s.dc_wiring), (-0.8, 1.0, 0.1, 1.5, 1.5))
        self.assertEqual(len(s.iam_points), 9)
        self.assertEqual(v.inverters, [[1, 1]])
        self.assertEqual((v.uc, v.uv, v.soiling, v.grid_limit_kw), (29.0, 0.0, 2.0, 10.0))
        (f,) = v.fields
        self.assertEqual((f.rows, f.pitch, f.n_width, f.length, f.width), (3, 5.0, 10, 11.52, 2.278))
        self.assertEqual(v.results, {})                              # two days only: no year to sum

    def test_the_defaults_pvsyst_does_not_write(self):
        v = pvproject.read_variant(DATA / "Prova Rho_Project.VC1")
        (o,) = v.orientations
        self.assertEqual((o.kind, o.tilt, o.azimuth), ("FixedPlane", 30.0, 90.0))
        self.assertEqual(v.uv, 0.0)
        self.assertEqual(v.sub_arrays[0].absent, ["PQualityModP", "PMismMPP", "LIDLoss", "RSCablagePC"])
        self.assertAlmostEqual(v.unavailability_days, 3.65)


class Mapping(unittest.TestCase):
    def setUp(self):
        prj = pvproject.read_project(PRJ)
        self.variants = [pvproject.read_variant(h.path) for h in prj.variants]
        self.project, self.report = mapping.to_project(prj, self.variants)

    def test_one_meridiana_variant_for_each_pvsyst_variant(self):
        p = self.project
        self.assertEqual([v["name"] for v in p.variants], ["File da 3", "Piano ovest"])
        self.assertEqual(p.variant, "v1")
        self.assertEqual((p.site.lat, p.site.lon, p.site.address), (45.5226, 9.03, "Rho, Italia"))

    def test_the_sheds_come_back_with_their_modules(self):
        p = self.project
        (sf,) = p.subfields
        self.assertEqual(p.fill(sf).count, 30)
        self.assertEqual(sf.module, "pan:ET SOLAR ET-M772BH550GL")            # the .PAN next to the project
        self.assertEqual(p.modules[sf.module]["iam_profile"]["iam"][-2:], [0.66, 0.0])   # its own profile
        self.assertEqual(p.energy["inverters"][0]["record"]["model"], "CPS SCH275KTL-DO/US-800")
        # PVsyst's counts, laid on the modules by Meridiana's proposal and written down at the first layout
        self.assertEqual(p.energy["strings"], {"n_series": 15, "per_mppt": [1, 1], "auto": True})
        self.assertEqual(p.energy["losses"]["mismatch"], 1.1)
        self.assertEqual(p.energy["thermal"], {sf.id: "open"})
        self.assertEqual(p.energy["t_min"], -12.0)
        self.assertEqual(p.economics["export_limit_kw"], 10.0)
        self.assertAlmostEqual(p.energy["losses"]["albedo"], 2.5 / 12, places=3)

    def test_what_is_missing_or_approximated_is_said(self):
        p = self.project
        p.switch_variant("v2")
        (sf,) = p.subfields
        self.assertEqual(p.fill(sf).count, 20)                                 # one free row
        self.assertEqual(sf.params["azimuth"], 90.0)
        self.assertTrue(any("Introvabile_XZ-123.PAN" in x for x in self.report.missing))
        self.assertTrue(any("taken as 0" in x for x in self.report.approximated))
        self.assertTrue(any("random periods" in x for x in self.report.approximated))
        self.assertTrue(any("Rho_PVGIS_TMY.MET" in x for x in self.report.approximated))
        q = model.Project.from_json(p.to_json())                              # saved and opened again
        self.assertEqual([v["name"] for v in q.variants], ["File da 3", "Piano ovest"])


if __name__ == "__main__":
    unittest.main()
