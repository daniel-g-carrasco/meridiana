"""R413 in Properties: «Keep the ridge height when the slope changes», on by default, on drawn and imported pitches, undone."""
import math
import unittest

from meridiana import model, roofs


def rect(x0, y0, x1, y1):
    return [[float(x0), float(y0)], [float(x1), float(y0)], [float(x1), float(y1)], [float(x0), float(y1)]]


class RidgeKept(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import _setup
        from meridiana import i18n
        cls.app = _setup.qt_or_skip()
        i18n.setup("en")

    def start(self, roof, height=6.0):
        from _fixtures import capannone
        from meridiana.quick.backend.properties import PropertiesBackend
        from meridiana.session import ProjectSession
        self.project = capannone()
        self.building = self.project.buildings[0]
        self.building.footprint, self.building.height, self.building.roof = rect(0, 0, 40, 20), height, roof
        self.session = ProjectSession(self.project)
        self.backend = PropertiesBackend(self.session)
        self.addCleanup(self.backend.close)
        self.session.select("building", self.building.id)
        self.app.processEvents()
        self.building = self.session.project.building(self.building.id)

    def now(self):
        return self.session.project.building(self.building.id)

    def free_pitch(self):
        return {"id": "p1", "ring": rect(0, 0, 40, 10), "eave_side": 0, "eave": 6.0, "tilt": 20.0}

    def test_the_box_is_on_by_default_and_a_project_keeps_the_choice(self):
        self.start(model.Roof(type="gable", tilt=20.0))
        field = self.backend.field("roof.keep_ridge")
        self.assertIsNotNone(field)
        self.assertTrue(field.data["value"])
        self.assertTrue(self.backend.commit("roof.keep_ridge", False))
        self.assertTrue(self.now().roof.keep_eave)
        saved = model.Project.from_json(self.session.project.to_json())
        self.assertTrue(saved.building(self.building.id).roof.keep_eave)
        self.session.undo.undo()
        self.assertFalse(self.now().roof.keep_eave)

    def test_generated_roof_eave_written_slope_worked_out_undone(self):
        self.start(model.Roof(type="gable", tilt=20.0))
        top, slope = self.now().ridge(), self.now().slope()
        self.assertTrue(self.backend.commit("height", 7.5))
        self.assertAlmostEqual(self.now().ridge(), top, places=2)
        self.assertLess(self.now().slope(), slope)
        self.session.undo.undo()
        self.assertEqual(self.now().height, 6.0)
        self.assertAlmostEqual(self.now().slope(), slope)

    def test_generated_roof_slope_written_eave_worked_out_undone(self):
        self.start(model.Roof(type="mono", tilt=20.0))
        top = self.now().ridge()
        self.assertTrue(self.backend.commit("roof.tilt", 10.0))
        self.assertAlmostEqual(self.now().ridge(), top, places=2)
        self.assertGreater(self.now().height, 6.0)
        self.session.undo.undo()
        self.assertEqual(self.now().height, 6.0)

    def test_eave_over_the_ridge_is_refused(self):
        self.start(model.Roof(type="gable", tilt=20.0))
        self.assertFalse(self.backend.commit("height", 40.0))
        self.assertEqual(self.now().height, 6.0)

    def test_with_the_eave_kept_the_old_way(self):
        self.start(model.Roof(type="gable", tilt=20.0, keep_eave=True))
        slope = self.now().slope()
        self.assertTrue(self.backend.commit("height", 7.5))
        self.assertAlmostEqual(self.now().slope(), slope)

    def test_drawn_pitch_both_ways_undone(self):
        self.start(model.Roof(type="free", free_pitches=[self.free_pitch()]))
        pitch = self.now().roof.free_pitches[0]
        top = roofs.free_ridge(pitch["ring"], 0, 6.0, 20.0)
        self.assertTrue(self.backend.commit("free.0.eave", 7.0))
        pitch = self.now().roof.free_pitches[0]
        self.assertEqual(pitch["eave"], 7.0)
        self.assertAlmostEqual(roofs.free_ridge(pitch["ring"], 0, pitch["eave"], pitch["tilt"]), top)
        self.assertLess(pitch["tilt"], 20.0)
        self.session.undo.undo()
        self.assertEqual(self.now().roof.free_pitches[0]["tilt"], 20.0)
        self.assertTrue(self.backend.commit("free.0.tilt", 10.0))
        pitch = self.now().roof.free_pitches[0]
        self.assertAlmostEqual(roofs.free_ridge(pitch["ring"], 0, pitch["eave"], pitch["tilt"]), top, places=2)
        self.assertGreater(pitch["eave"], 6.0)

    def test_imported_pitches_on_their_own_plane_with_the_ridge_kept(self):
        # As ifc_import.plan writes them: free, not joined.
        self.start(model.Roof(type="free", free_pitches=[self.free_pitch()], joined=False))
        pitch = self.now().roof.free_pitches[0]
        top = roofs.free_ridge(pitch["ring"], 0, 6.0, 20.0)
        self.assertTrue(self.backend.commit("free.0.percent", 100*math.tan(math.radians(10.0))))
        pitch = self.now().roof.free_pitches[0]
        self.assertAlmostEqual(pitch["tilt"], 10.0, delta=.05)       # the percent field has one decimal
        self.assertAlmostEqual(roofs.free_ridge(pitch["ring"], 0, pitch["eave"], pitch["tilt"]), top, places=2)

    def test_ridge_written_moves_the_slope_from_the_eave(self):
        self.start(model.Roof(type="free", free_pitches=[self.free_pitch()]))
        self.assertTrue(self.backend.commit("free.0.ridge", 12.0))
        pitch = self.now().roof.free_pitches[0]
        self.assertEqual(pitch["eave"], 6.0)
        self.assertAlmostEqual(roofs.free_ridge(pitch["ring"], 0, 6.0, pitch["tilt"]), 12.0)


if __name__ == "__main__":
    unittest.main()
