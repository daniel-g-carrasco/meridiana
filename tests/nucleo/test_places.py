"""Local place suggestions: the official municipalities and the sites of recent projects, never a network service."""

import json
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401
from _fixtures import capannone_rho

from meridiana import model, places


class Municipalities(unittest.TestCase):
    def test_all_the_current_istat_municipalities_have_a_verified_local_point(self):
        found = places.municipalities()
        self.assertEqual(len(found), 7894)
        rho = next(p for p in found if p.name == "Rho")
        self.assertEqual((rho.code, rho.province, rho.region), ("015182", "Milano", "Lombardia"))
        self.assertAlmostEqual(rho.lat, 45.53178, places=6)
        self.assertAlmostEqual(rho.lon, 9.046984, places=6)
        self.assertIn("Castegnero Nanto", {p.name for p in found})

    def test_search_is_offline_case_and_accent_insensitive_and_says_its_source(self):
        found = places.municipalities()
        self.assertEqual(places.search("aglie", found)[0].name, "Agliè")
        rho = places.search("rho", found)[0]
        self.assertEqual((rho.name, rho.source), ("Rho", "ISTAT"))
        self.assertEqual(places.search("r", found), [])


class RecentProjects(unittest.TestCase):
    def test_a_recent_project_suggests_its_site_and_a_damaged_one_does_not_stop_the_others(self):
        folder = Path(tempfile.mkdtemp())
        good = folder / "shed.meridiana"
        project = capannone_rho()
        project.save(good)
        bad = folder / "bad.meridiana"
        bad.write_text("not JSON", encoding="utf-8")
        found = places.recent([str(bad), str(good), str(folder / "missing.meridiana")])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].name, project.name)
        self.assertEqual(found[0].source, "project")
        self.assertEqual((found[0].lat, found[0].lon), (project.site.lat, project.site.lon))
        self.assertEqual(json.loads(good.read_text(encoding="utf-8"))["format"], model.FORMAT)


if __name__ == "__main__":
    unittest.main()
