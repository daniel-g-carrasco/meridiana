"""What the plan shows beside the drawing: a scale bar of round lengths, what lies under the cursor with its
height, the quick measure of the selection."""

import unittest

import _setup  # noqa: F401

from meridiana import model, viewaids


def sample() -> model.Project:
    p = model.Project(name="Prova")
    b = model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]], height=9.5)
    b.roof.type = "gable"
    b.roof.tilt = 15.0
    p.buildings.append(b)
    p.subfields.append(model.SubField(id="s1", name="Sud", ring=[[1, 1], [39, 1], [39, 9], [1, 9]], building="b1",
                                      pitch=0, filled=True))
    p.exclusions.append(model.ExclusionItem(id="e1", ring=[[18, 12], [20, 12], [20, 14], [18, 14]], kind="chimney",
                                            building="b1", height=1.5))
    return p


class ScaleBar(unittest.TestCase):
    def test_the_bar_takes_the_longest_round_length_that_fits(self):
        for mpp, length in ((0.1, 10.0), (0.05, 5.0), (0.02, 2.0), (0.3, 20.0), (1.0, 100.0), (7.0, 500.0),
                            (0.004, 0.2), (12.0, 1000.0)):
            with self.subTest(mpp=mpp):
                got, px = viewaids.scale_bar(mpp, 120)
                self.assertAlmostEqual(got, length)
                self.assertLessEqual(px, 120 + 1e-6)
                self.assertGreater(px, 120 / 2.5 - 1e-6)            # never less than 2/5 of the room
                self.assertAlmostEqual(px, length / mpp)

    def test_a_scale_that_is_not_a_scale_is_refused(self):
        for wrong in (0.0, -1.0, float("inf")):
            with self.assertRaises(ValueError):
                viewaids.scale_bar(wrong)

    def test_lengths_written_as_the_bar_writes_them(self):
        self.assertEqual(viewaids.length_text(0.5), "50 cm")
        self.assertEqual(viewaids.length_text(5.0), "5 m")
        self.assertEqual(viewaids.length_text(2000.0), "2 km")


class UnderTheCursor(unittest.TestCase):
    def test_the_height_of_what_is_under_the_cursor(self):
        p = sample()
        b = p.buildings[0]
        for i, pitch in enumerate(b.pitches()):
            self.assertAlmostEqual(viewaids.height_at(p, "pitch", f"b1:{i}", 10, 5), pitch.z(10, 5))
        on_roof = model.roof_z(b, [(10, 5)])[0]             # the pitch the point lies on
        self.assertAlmostEqual(viewaids.height_at(p, "subfield", "s1", 10, 5), on_roof)
        self.assertGreater(on_roof, b.height)               # above the eaves
        self.assertAlmostEqual(viewaids.height_at(p, "building", "b1", 20, 10), max(q.z(20, 10) for q in b.pitches()))
        top = viewaids.height_at(p, "exclusion", "e1", 19, 13)
        self.assertAlmostEqual(top - 1.5, viewaids.height_at(p, "building", "b1", 19, 13))
        self.assertEqual(viewaids.height_at(p, "", "", 100, 100), 0.0)

    def test_over_a_module_the_height_is_the_roof_under_it(self):
        p = sample()
        z = viewaids.height_at(p, "module", "s1", 10, 5)
        self.assertGreater(z, 9.5)
        self.assertAlmostEqual(z, viewaids.height_at(p, "subfield", "s1", 10, 5))
        self.assertNotIn("z 0.00", viewaids.under_text(p, "module", "s1", "r1c2", 10, 5))

    def test_the_status_bar_says_what_and_where(self):
        p = sample()
        text = viewaids.under_text(p, "module", "s1", "r1c2", 10, 5)
        self.assertTrue(text.startswith("Sud, module r1c2"), text)
        self.assertIn("E 10.00  N 5.00  z ", text)
        self.assertTrue(viewaids.under_text(p, "pitch", "b1:1", "", 10, 15).startswith("Capannone, pitch 2"))
        self.assertTrue(viewaids.under_text(p, "exclusion", "e1", "", 19, 13, {"chimney": "Chimney"}).startswith(
            "Chimney e1"))
        self.assertEqual(viewaids.under_text(p, "", "", "", 1, 2), "E 1.00  N 2.00 m")


class Anchor(unittest.TestCase):
    def test_the_mark_of_an_object_sits_inside_it_at_its_height(self):
        from shapely.geometry import Point, Polygon
        p = sample()
        x, y, z = viewaids.anchor(p, "subfield", "s1")
        self.assertTrue(Polygon(p.subfields[0].ring).contains(Point(x, y)))
        self.assertAlmostEqual(z, viewaids.height_at(p, "subfield", "s1", x, y))
        self.assertGreater(viewaids.anchor(p, "exclusion", "e1")[2], viewaids.anchor(p, "building", "b1")[2] - 5)
        self.assertIsNone(viewaids.anchor(p, "subfield", "nothing"))


class QuickMeasure(unittest.TestCase):
    def test_the_measure_of_the_selection(self):
        p = sample()
        m = viewaids.measure(p, {}, "building", "b1")
        self.assertEqual((m["length"], m["area"]), (120.0, 800.0))
        r = p.fill(p.subfields[0])
        m = viewaids.measure(p, {"s1": r}, "subfield", "s1")
        self.assertEqual(m["modules"], r.count)
        self.assertAlmostEqual(m["kwp"], r.count * 0.45)
        text = viewaids.measure_text(m)
        self.assertIn("perimeter 92.00 m", text)
        self.assertIn(f"{r.count} modules", text)
        self.assertNotIn("modules", viewaids.measure(p, {"s1": ValueError("x")}, "subfield", "s1"))
        self.assertEqual(viewaids.measure(p, {}, "site", ""), {})
        self.assertEqual(viewaids.measure_text({}), "")


class Outline(unittest.TestCase):
    """The edges the 3D view draws around what is selected or under the pointer."""

    def test_each_kind_of_object_has_its_edges_where_it_stands(self):
        import numpy as np
        p = sample()
        b = p.buildings[0]
        ridge = max(q.z(20, 10) for q in b.pitches())
        building = viewaids.outline(p, {}, "building", "b1")
        self.assertAlmostEqual(float(building[:, :, 1].max()), ridge, places=6)
        sub = viewaids.outline(p, {}, "subfield", "s1")
        self.assertEqual(len(sub), 4)
        on_roof = model.roof_z(b, [(1.0, 1.0)])[0]
        self.assertTrue(np.isclose(sub[:, :, 1], on_roof + viewaids.LIFT).any())     # on the roof, just above
        chimney = viewaids.outline(p, {}, "exclusion", "e1")
        self.assertEqual(len(chimney), 12)                                              # foot, top, corners
        self.assertEqual(len(viewaids.outline(p, {}, "pitch", "b1:1")), len(b.pitches()[1].ring))
        result = p.fill(p.subfields[0])
        key = result.modules[0].key
        self.assertEqual(len(viewaids.outline(p, {"s1": result}, "module", "s1", key)), 4)
        for kind, oid in (("building", "nothing"), ("subfield", "x"), ("pitch", "b1:9"), ("site", "")):
            self.assertEqual(len(viewaids.outline(p, {}, kind, oid)), 0)


if __name__ == "__main__":
    unittest.main()
