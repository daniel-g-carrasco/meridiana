"""The least Shapely the program accepts (review of 11/11/2026, finding 2): the faces of an IFC model are triangulated by
`shapely.constrained_delaunay_triangles` (core/geometry/polyfill.py), which Shapely has since 2.1. Every place that
installs Shapely asks for at least that, and the Shapely installed has the function, or this test says which one is
missing instead of an AttributeError in the middle of an import."""

import json
import re
import unittest
from pathlib import Path

import _setup  # noqa: F401

import shapely

ROOT = Path(__file__).resolve().parents[2]
LEAST = (2, 1)
# where Shapely is asked for: the wheels of Windows and the CI, the package, the cloud sessions, the Flatpak recipes
PLACES = ("requirements.txt", "pyproject.toml", "tools/cloud-setup.sh", "build-aux/flatpak/requirements-flatpak.txt",
          "build-aux/flatpak/python3-requirements.json")


class ShapelyLeastTest(unittest.TestCase):
    def test_installed_shapely_has_the_constrained_triangulation(self):
        self.assertTrue(hasattr(shapely, "constrained_delaunay_triangles"),
                        f"Shapely {shapely.__version__} has no constrained_delaunay_triangles: the IFC import needs "
                        f"Shapely {LEAST[0]}.{LEAST[1]} or later (pip install 'shapely>={LEAST[0]}.{LEAST[1]}')")
        version = tuple(int(x) for x in re.findall(r"\d+", shapely.__version__)[:2])
        self.assertGreaterEqual(version, LEAST, f"Shapely {shapely.__version__} is older than the least accepted")

    def test_every_recipe_asks_for_the_least_version(self):
        for name in PLACES:
            text = (ROOT / name).read_text(encoding="utf-8")
            if name.endswith(".json"):
                text = json.dumps(json.loads(text))
            found = re.findall(r"shapely\s*>=\s*(\d+)\.(\d+)", text, re.IGNORECASE)
            self.assertTrue(found, f"{name} does not ask for a least Shapely")
            for major, minor in found:
                self.assertGreaterEqual((int(major), int(minor)), LEAST,
                                        f"{name} accepts shapely>={major}.{minor}, older than the IFC import needs")


if __name__ == "__main__":
    unittest.main()
