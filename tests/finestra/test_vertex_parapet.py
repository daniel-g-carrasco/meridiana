"""The first corner moved on a flat roof makes it a roof drawn by hand, and its parapet stops shading: the program
says so, it does not leave it to be found in the numbers (R303, 02/11/2026)."""
import unittest

import _setup
from _fixtures import capannone


class ParapetSaid(unittest.TestCase):
    def test_a_flat_roof_with_a_parapet_is_told_about_it(self):
        from meridiana import roof_vertices
        self.app = _setup.qt_or_skip()
        project = capannone()
        b = project.buildings[0]
        b.roof.type = "flat"
        b.parapet = 1.0
        _setup.window(self, project)
        win = self.win
        win._select("building", b.id)
        _setup.turn_events(self.app, 100)
        win._vertex_change("corner", lambda p, bid: roof_vertices.to_manual(p, p.building(bid)))
        self.assertEqual(win.project.building(b.id).roof.type, "free")
        self.assertIn("parapet", win.hint.text())


if __name__ == "__main__":
    unittest.main()
