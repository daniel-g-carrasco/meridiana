"""The real PVsyst files of the study (docs/studio/10 and 11), read when MERIDIANA_PVSYST_SAMPLES names their folder:
every text file read without anomalies, every variant laid with PVsyst's count of modules, the hourly results equal
to the report. On Daniel's PC the folder is C:\\Users\\utente\\dev\\meridiana-prove\\pvsyst-campioni; the path is
never written in the test (study 18, D 6.8)."""

import os
import unittest
from pathlib import Path

import _setup  # noqa: F401

from meridiana.pvsyst import mapping, pvobject
from meridiana.pvsyst import project as pvproject

SAMPLES = Path(os.environ.get("MERIDIANA_PVSYST_SAMPLES", "") or "-no-folder-")


@unittest.skipUnless(SAMPLES.is_dir(), "MERIDIANA_PVSYST_SAMPLES does not name the folder of the real PVsyst files")
class RealFiles(unittest.TestCase):
    """Every real PVsyst file of the study read, and every variant laid with PVsyst's count of modules."""

    def test_every_text_file_reads_cleanly(self):
        kinds = {".PRJ", ".SIT", ".MET", ".SHD", ".BTR", ".LOD", ".SFI"}
        for path in SAMPLES.rglob("*"):
            ext = path.suffix.upper()
            if path.is_file() and (ext in kinds or (len(ext) == 4 and ext.startswith(".V"))) and "SYNTH" not in path.name:
                with self.subTest(file=path.name):
                    self.assertEqual(pvobject.read(path).anomalies, [])

    def test_every_variant_is_laid_with_pvsysts_modules(self):
        for prj_path in SAMPLES.rglob("*.PRJ"):
            prj = pvproject.read_project(prj_path)
            for head in prj.variants:
                if "SYNTH" in head.path.name:
                    continue
                with self.subTest(variant=head.path.name):
                    v = pvproject.read_variant(head.path)
                    p, _report = mapping.to_project(prj, [v])
                    self.assertEqual(sum(p.fill(sf).count for sf in p.subfields), v.modules)

    def test_the_hourly_results_equal_the_report(self):
        v = pvproject.read_variant(SAMPLES / "github-jdnewmil-BifiOutboard" / "extracted-sheds" /
                                   "Test Bifi Sheds_Project.VC0")
        self.assertAlmostEqual(v.results["E_Grid"][0], 196038, delta=1)     # kWh in January, as the report
        self.assertAlmostEqual(sum(v.results["E_Grid"]), 4436353, delta=2)


if __name__ == "__main__":
    unittest.main()
