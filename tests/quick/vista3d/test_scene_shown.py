"""R598: the 3D not on show makes nothing. A change while the plan is alone, or another phase is shown, leaves the scene,
the selection's outline and the strings to make; shown again, the 3D makes them, of the project in hand. Whoever reads
the scene from Python meanwhile asks for it (`made_now`) and has it."""

from pathlib import Path
import tempfile
import unittest

import numpy as np

import _setup

from meridiana.core.model import model
from meridiana.gui.backend.scene import SceneBackend
from meridiana.app.session import ProjectSession

setUpModule = _setup.keep_global_state


def project():
    p = model.Project(name="shown")
    p.buildings.append(model.Building(id="b1", name="A", footprint=[[0, 0], [20, 0], [20, 10], [0, 10]], height=6.0))
    return p


def wide(p, k):
    p.buildings.append(model.Building(id=f"n{k}", name=f"N{k}", footprint=[[40 + 30 * k, 0], [60 + 30 * k, 0],
                                                                            [60 + 30 * k, 15], [40 + 30 * k, 15]],
                                      height=9.0))


class SceneNotOnShow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.session = ProjectSession(project())
        self.scene = SceneBackend(self.session, Path(folder.name) / "geometry")
        self.addCleanup(self.scene.close)

    def bodies(self):
        return {oid for part, oid, _n in self.scene._owners if part == "building"}

    def test_a_change_while_not_on_show_is_made_when_shown_again(self):
        self.scene.shown = False
        before = self.scene.rebuilds
        self.session.edit("add", lambda p: wide(p, 0))
        self.session.edit("add", lambda p: wide(p, 1))
        self.assertEqual(before, self.scene.rebuilds, "nothing made while the 3D is not on show")
        self.assertEqual({"b1"}, self.bodies())
        self.scene.shown = True
        self.assertEqual(before + 1, self.scene.rebuilds, "one scene, made when shown")
        self.assertEqual({"b1", "n0", "n1"}, self.bodies())
        made = self.scene.triangles[0].copy()
        self.scene.rebuild()
        np.testing.assert_array_equal(made, self.scene.triangles[0])

    def test_the_outline_of_a_selection_while_not_on_show_comes_when_shown(self):
        self.scene.shown = False
        self.session.select("building", "b1")
        self.assertEqual([], self.scene._segments, "no outline made while the 3D is not on show")
        self.scene.shown = True
        self.assertTrue(self.scene._segments, "the outline of the building chosen meanwhile")
        self.assertTrue(self.scene.gizmo["on"])

    def test_who_reads_from_python_has_the_scene_of_the_project_in_hand(self):
        self.scene.shown = False
        self.session.edit("add", lambda p: wide(p, 0))
        self.session.select("building", "n0")
        self.scene.made_now()
        self.assertEqual({"b1", "n0"}, self.bodies())
        self.assertTrue(self.scene._segments)
        rebuilds = self.scene.rebuilds
        self.scene.shown = True                 # nothing left to make
        self.assertEqual(rebuilds, self.scene.rebuilds)


if __name__ == "__main__":
    unittest.main()
