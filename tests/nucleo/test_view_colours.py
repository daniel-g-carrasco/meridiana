"""The colours of the plan and the 3D view, their own and the same in both themes (Daniel, 23/10/2026): over the
veiled orthophoto every outline reads on a light roof and on a dark one, on the light ground too; the selection
has a tint of its own, apart from the warnings, the errors and the sub-fields; the 3D sky is a day sky."""

import unittest

import _setup  # noqa: F401

from meridiana import theme_colors as tc
from meridiana import view_colours as vc

ROOFS = ("#e8e6e0", "#bdbab2", "#6b6660", "#2c2a28", "#9a5a3e", "#5d7a4a")     # light, grey, dark, tiles, grass
OUTLINES = ("bld_stroke", "pitch", "sub_stroke", "exclusion", "sel", "hover", "guide", "draw")


class Plan(unittest.TestCase):
    def test_over_the_veiled_photo_each_outline_or_its_halo_stands_out_from_any_roof(self):
        for roof in ROOFS:
            under = vc.veiled(roof, vc.VEIL)
            for key in OUTLINES:
                stroke, halo = vc.PHOTO[key][:7], vc.PHOTO["halo"][:7]
                with self.subTest(roof=roof, key=key):
                    self.assertGreaterEqual(max(tc.contrast(stroke, under), tc.contrast(halo, under)), 3.0)
                    self.assertGreaterEqual(tc.contrast(stroke, halo), 6.0)      # a line of two tones

    def test_daniels_case_a_line_on_a_light_roof(self):
        under = vc.veiled("#e8e6e0", vc.VEIL)               # 23/10/2026: «quasi invisibile su un tetto chiaro»
        stroke, halo = vc.PHOTO["bld_stroke"][:7], vc.PHOTO["halo"][:7]
        self.assertGreaterEqual(tc.contrast(halo, under), 4.5)          # the line of two tones: its dark part
        self.assertGreaterEqual(tc.contrast(stroke, under), 3.0)        # and the light one, both seen
        self.assertLess(tc.luminance(under), tc.luminance("#e8e6e0"))  # the photo is darker under the veil

    def test_on_the_light_ground_the_outlines_are_dark_enough(self):
        for key in OUTLINES:
            with self.subTest(key=key):
                self.assertGreaterEqual(tc.contrast(vc.PAPER[key][:7], vc.PAPER["bg"]), 3.0)

    def test_the_selection_is_not_a_warning_an_error_or_a_sub_field(self):
        for colours in (vc.PHOTO, vc.PAPER):
            for key in ("sel", "hover"):
                with self.subTest(key=key, bg=colours["bg"]):
                    self.assertGreater(tc.nearest_status(colours[key])[1], tc.NEAR)
                    self.assertGreater(tc.distance(colours[key], colours["sub_stroke"]), 0.2)
                    self.assertGreater(tc.distance(colours[key], colours["pitch"]), 0.2)

    def test_the_veil_goes_from_nothing_to_black(self):
        self.assertEqual(vc.veil(0.0), "#00000000")
        self.assertEqual(vc.veil(vc.VEIL), "#00000066")
        self.assertEqual(vc.veil(2.0), "#000000ff")
        self.assertEqual(vc.veiled("#ffffff", 0.0), "#ffffff")
        self.assertIn(vc.VEIL, vc.VEILS)

    def test_the_plan_colours_are_the_same_whatever_the_theme(self):
        self.assertEqual(vc.plan(True), vc.PHOTO)
        self.assertEqual(vc.plan(False), vc.PHOTO)         # Daniel, 23/10/2026: the dark ground without the photo too
        self.assertIsNot(vc.plan(True), vc.PHOTO)          # a copy: the plan may add to it


class ThreeD(unittest.TestCase):
    def test_the_sky_is_a_day_sky(self):
        for key in ("sky_top", "sky_bottom"):
            self.assertGreater(tc.lab(vc.D3[key])[0], 0.75)          # light, «sempre notte» no more
            self.assertGreater(tc.lch(vc.D3[key])[2], 200)           # and blue

    def test_the_selection_stands_out_from_the_roofs_the_walls_and_the_modules(self):
        from meridiana import mesh

        def hexed(rgb):
            return "#" + "".join(f"{round(c * 255):02x}" for c in rgb)
        for name, rgb in (("roof", mesh.ROOF_PITCH), ("flat", mesh.ROOF_FLAT), ("wall", mesh.WALL),
                          ("module", mesh.MODULE)):
            with self.subTest(name=name):
                self.assertGreater(tc.distance(vc.D3["select"], hexed(rgb)), 0.2)

    def test_each_kind_has_its_colour_apart_from_the_traffic_light_and_readable_in_the_panels(self):
        """R67 (Daniel, 24/10/2026): a building, a sub-field, an exclusion each in its colour, in the plan, in 3D
        and in the tree; none is a status colour (those stay for the checks)."""
        kinds = ("building", "subfield", "exclusion")
        for i, a in enumerate(kinds):
            for b in kinds[i + 1:]:
                self.assertGreater(tc.distance(vc.KIND[a], vc.KIND[b]), 0.12, (a, b))
            for status in tc.STATUS.values():
                self.assertGreater(tc.distance(vc.KIND[a], status), 0.15, a)
            light, dark = vc.KIND_UI[a]
            self.assertGreaterEqual(tc.contrast(light, "#f8f7f4"), 3.0, a)        # an icon on the light panel
            self.assertGreaterEqual(tc.contrast(dark, "#252525"), 3.0, a)         # and on the dark one
        self.assertEqual(vc.kind_colour("row"), vc.kind_colour("subfield"))       # what is laid in it
        self.assertEqual(vc.kind_colour(""), vc.SELECT)                           # what has no kind

    def test_the_pivots_cross_hair_is_a_two_tone_line_that_reads_on_any_ground_and_has_no_other_use(self):
        core, halo = vc.D3["pivot"], vc.D3["pivot_halo"]
        a = vc.PIVOT_HALO_OPACITY
        self.assertGreaterEqual(tc.contrast(core, halo), 12.0)             # lime on the dark halo
        for bg in ("#ffffff", "#e4edf3", "#9fae93", "#808080", "#5d7a4a", "#2b2f33", "#000000"):
            under = tc.mix(bg, halo, a)                                      # the halo is drawn 70 % opaque over it
            with self.subTest(bg=bg):
                self.assertGreaterEqual(tc.contrast(core, under), 4.5)       # the core over its halo
                self.assertGreaterEqual(max(tc.contrast(core, bg), tc.contrast(under, bg)), 3.0)   # and set apart
        for key in ("sel", "hover", "guide", "draw", "pitch", "sub_stroke", "exclusion"):
            with self.subTest(key=key):
                self.assertGreater(tc.distance(core, vc.PHOTO[key][:7]), 0.2)


    def test_the_gizmo_is_red_green_and_blue_on_its_halo_and_the_handle_under_the_pointer_yellow(self):
        d3 = vc.D3
        names = ("gizmo_x", "gizmo_y", "gizmo_z", "gizmo_hot")
        for key in names:
            with self.subTest(key=key):
                self.assertGreaterEqual(tc.contrast(d3[key], d3["gizmo_halo"]), 4.5)
                for other in names:
                    if other != key:
                        self.assertGreater(tc.distance(d3[key], d3[other]), 0.15)
        self.assertLess(abs(tc.lch(d3["gizmo_x"])[2] - 30), 30)                  # red
        self.assertLess(abs(tc.lch(d3["gizmo_y"])[2] - 145), 30)                 # green
        self.assertLess(abs(tc.lch(d3["gizmo_z"])[2] - 265), 30)                 # blue


class Strokes(unittest.TestCase):
    """R35 (Daniel, 23/10/2026): «diamo un buono spessore a tutto»."""

    def test_the_outlines_are_about_two_pixels_and_the_selection_thicker(self):
        w = vc.WIDTHS
        for key in ("building", "subfield", "exclusion", "draw", "measure"):
            self.assertGreaterEqual(w[key], 2.0, key)
            self.assertLessEqual(w[key], 3.0, key)
        self.assertGreaterEqual(w["pitch"], 1.5)
        self.assertGreater(w["select"], w["building"])
        self.assertGreater(w["hover"], w["pitch"])
        self.assertGreater(w["halo"], 2.0)                           # the halo shows around the thicker stroke
        self.assertLess(w["module_line"], 1.0)                       # the modules' lines stay thin
        self.assertGreater(vc.RIBBONS["select"], vc.RIBBONS["hover"])
        self.assertGreaterEqual(vc.RIBBONS["select"], 4.0)


if __name__ == "__main__":
    unittest.main()
