"""The theme's colours from one chosen colour (study 13, section 12): the ready-made colours give the values of
the table in 12.4, and 500 colours at random keep the contrasts and the distances from the status colours, in
the light and the dark theme, with the three backgrounds. The values were computed by
docs/studio/13-colori/colori.js, the same code as the study's canvas."""

import unittest

import _setup  # noqa: F401
from _fixtures import flat

from meridiana import theme_colors as tc

# study 13, 12.4: name, seed, light accent and white on it, dark accent and on the view #101318,
# assistant light / dark, the status the accent was moved away from in light / dark ("" if not moved)
TABLE = [
    ("system (Windows)", "#0078d4", "#0075cf", 4.7, "#97c9ff", 10.7, "#624726", "#e2d5c7", "", ""),
    ("system (GNOME yellow)", "#c88800", "#906102", 5.4, "#f3e2ca", 14.7, "#374e6e", "#a5c0e5", "critical", "warning"),
    ("bronze", "#8b5a12", "#805210", 6.7, "#f1dac1", 13.8, "#334f6d", "#a1c1e4", "critical", "warning"),
    ("terracotta", "#a4482b", "#7e351e", 8.7, "#f9d5ca", 13.6, "#205563", "#92c8d8", "critical", "warning"),
    ("olive", "#5f6b1f", "#5f6b1f", 5.8, "#dbe2c4", 13.9, "#51466a", "#c2b6e0", "", "warning"),
    ("forest", "#2f6b4f", "#2f6b4f", 6.3, "#97d4b4", 11.0, "#634057", "#daafc9", "", ""),
    ("petrol", "#1f6a7a", "#1f6a7a", 6.2, "#8ad1e3", 10.9, "#6a4136", "#e4cbc4", "", ""),
    ("blue", "#2a5ea8", "#2a5ea8", 6.4, "#9fc6ff", 10.6, "#5f4925", "#e1d6c6", "", ""),
    ("indigo", "#5b4bb0", "#5b4bb0", 6.8, "#bfbbff", 10.4, "#514f26", "#d9d9c7", "", ""),
    ("plum", "#8a3a6e", "#8a3a6e", 7.2, "#f6a7d7", 10.1, "#2b5744", "#9bcab3", "", ""),
    ("graphite", "#4a4f57", "#4a4f57", 8.2, "#bfc4ce", 10.6, "#5e4925", "#e0d6c6", "", ""),
]


def random_seeds(n: int) -> list[str]:
    """The first `n` colours of docs/studio/13-colori/casuali.js: its generator, in the same floating point."""
    x, out = 12345.0, []
    for _i in range(n):
        s = "#"
        for _c in range(3):
            x = (x * 1103515245.0 + 12345.0) % 2147483648.0
            s += f"{int(x / 2147483648.0 * 256):02x}"
        out.append(s)
    return out


class ReadyMadeColours(unittest.TestCase):
    def test_the_ready_made_colours_give_the_table_of_the_study(self):
        for name, seed, light, on_white, dark, on_view, asst_l, asst_d, near_l, near_d in TABLE:
            with self.subTest(name):
                a, b = tc.derive(seed, False), tc.derive(seed, True)
                self.assertEqual(a.tokens["accent"], light)
                self.assertAlmostEqual(tc.contrast(light, "#ffffff"), on_white, delta=0.05)
                self.assertEqual(b.tokens["accent"], dark)
                self.assertAlmostEqual(tc.contrast(dark, "#101318"), on_view, delta=0.05)
                self.assertEqual((a.tokens["assistant"], b.tokens["assistant"]), (asst_l, asst_d))
                self.assertEqual((a.report.near, b.report.near), (near_l, near_d))

    def test_the_presets_are_the_table_without_the_system_colours(self):
        self.assertEqual(list(tc.PRESETS.values()), [row[1] for row in TABLE[2:]])
        self.assertEqual(tc.DEFAULT_SEED, "#8b5a12")

    def test_bronze_gives_the_selection_the_selected_module_and_the_translucent_accent(self):
        t = tc.derive("#8b5a12", False).tokens
        self.assertEqual((t["select_bg"], t["select_fg"]), ("#ebe1d6", "#1e1c19"))     # a grey of the hue (R104)
        self.assertEqual(t["d3"]["module_sel"], "#fedfbc")
        self.assertEqual((t["accent_soft"], t["plan"]["sub_fill"]), ("#80521020", "#80521014"))
        self.assertEqual((t["plan"]["sel"], t["plan"]["sub_stroke"]), ("#805210", "#805210"))
        d = tc.derive("#8b5a12", True).tokens
        self.assertEqual((d["accent_fg"], d["d3"]["module_sel"]), ("#151515", "#f1dac1"))  # dark: the accent

    def test_the_assistant_takes_the_opposite_hue_of_the_seed(self):
        for seed in ("#8b5a12", "#1f6a7a", "#5b4bb0"):
            for dark in (False, True):
                h = tc.lch(tc.derive(seed, dark).tokens["assistant"])[2]
                gap = abs((h - tc.lch(seed)[2]) % 360 - 180)
                self.assertLess(gap, 6, f"{seed} {'dark' if dark else 'light'}")

    def test_the_tinted_and_grey_backgrounds_follow_the_seed(self):
        petrol = "#1f6a7a"
        expected = {
            ("tinted", False): ("#ebf2f4", "#f4f9fa", "#ffffff", "#ccd7da", "#182022", "#5e6a6d", "#f9fcfc",
                                "#ffffff", "#e7eced", "#727c7f"),
            ("tinted", True): ("#0f1719", "#1e2729", "#161d1f", "#384245", "#e7eff0", "#929ea1", "#161d1f",
                               "#1e2729", "#171e20", "#697477"),
            ("grey", False): ("#f1f1f1", "#f8f8f8", "#ffffff", "#d5d5d5", "#1e1e1e", "#676767", "#fbfbfb",
                              "#ffffff", "#ebebeb", "#7a7a7a"),
            ("grey", True): ("#151515", "#252525", "#1c1c1c", "#404040", "#ededed", "#9b9b9b", "#1c1c1c",
                             "#252525", "#1d1d1d", "#6f6f6f"),
        }
        for (backgrounds, dark), values in expected.items():
            with self.subTest(backgrounds=backgrounds, dark=dark):
                t = tc.derive(petrol, dark, backgrounds).tokens
                got = (tuple(t[k] for k in ("window", "panel", "view", "line", "text", "muted")) + (t["plan"]["bg"],)
                       + tuple(t[k] for k in ("card", "field", "field_line")))
                self.assertEqual(got, values)
                self.assertEqual(t["accent"], "#8ad1e3" if dark else "#1f6a7a")
                self.assertEqual(t["select_bg"], "#334043" if dark else "#d6e6ea")

    def test_unknown_backgrounds_are_refused(self):
        with self.assertRaises(ValueError):
            tc.derive("#8b5a12", False, "colore")

    def test_the_base_tokens_are_not_changed(self):
        before = repr(tc.MERIDIANA_LIGHT)
        tc.derive("#8b5a12", False)
        self.assertEqual(repr(tc.MERIDIANA_LIGHT), before)


class Colour(unittest.TestCase):
    def test_a_colour_goes_to_oklch_and_back(self):
        for hex_ in ("#000000", "#ffffff", "#8b5a12", "#1f6a7a", "#fab219", "#0ca30c"):
            self.assertEqual(tc.hex_of(*tc.lch(hex_)), hex_)

    def test_a_colour_out_of_gamut_keeps_its_lightness_and_hue(self):
        hex_ = tc.hex_of(0.6, 0.4, 250)                     # no sRGB blue is that vivid
        L, C, h = tc.lch(hex_)
        self.assertAlmostEqual(L, 0.6, delta=0.005)
        self.assertAlmostEqual(h, 250, delta=1)
        self.assertLess(C, 0.4)

    def test_the_contrast_ratio_is_the_wcag_one(self):
        self.assertAlmostEqual(tc.contrast("#000000", "#ffffff"), 21.0)
        self.assertAlmostEqual(tc.contrast("#777777", "#777777"), 1.0)

    def test_a_colour_near_a_status_is_moved_away_from_it(self):
        moved, did = tc.protect("#fab219", darker=True)
        self.assertTrue(did)
        self.assertGreaterEqual(tc.nearest_status(moved)[1], tc.NEAR)
        self.assertLess(tc.lch(moved)[0], tc.lch("#fab219")[0])     # darker in the light theme
        same, did = tc.protect("#2a5ea8", darker=True)
        self.assertEqual((same, did), ("#2a5ea8", False))

    def test_a_translucent_colour_goes_to_qt_in_its_order(self):
        self.assertEqual(tc.qt_hex("#80521020"), "#20805210")
        self.assertEqual(tc.qt_hex("#805210"), "#805210")


class RandomColours(unittest.TestCase):
    def test_500_colours_at_random_keep_the_contrasts_and_the_distances(self):
        seeds = random_seeds(500)
        self.assertEqual(seeds[:3], ["#a74ea1", "#feadac", "#2ce2b5"])   # the generator of casuali.js
        failures = []
        for seed in seeds:
            for backgrounds in tc.BACKGROUNDS:
                for dark in (False, True):
                    t = tc.derive(seed, dark, backgrounds).tokens
                    checks = [
                        ("text on the accent", tc.contrast(t["accent"], t["accent_fg"]), 4.5),
                        ("accent on the view", tc.contrast(t["accent"], t["view"]), 4.5),
                        ("muted on the panels", tc.contrast(t["muted"], t["panel"]), 4.5),
                        ("text on the selection", tc.contrast(t["text"], t["select_bg"]), 7),
                        ("accent from the status colours", tc.nearest_status(t["accent"])[1], tc.NEAR),
                        ("assistant from the status colours", tc.nearest_status(t["assistant"])[1], tc.NEAR),
                        ("assistant on its background",
                         tc.contrast(t["assistant"], t["window"] if dark else "#ffffff"), 4.5),
                        ("selected module from the status colours", tc.nearest_status(t["d3"]["module_sel"])[1],
                         tc.NEAR),
                    ]
                    failures += [f"{seed} {backgrounds} {'dark' if dark else 'light'}: {what} {value:.3f}"
                                 for what, value, least in checks if value < least]
        self.assertEqual(failures, [])


class Palette(unittest.TestCase):
    """The palette of the window and the roles of plan, 3D and charts, for every choice."""

    def test_every_backgrounds_has_every_role(self):
        for dark in (False, True):
            keys = {b: set(flat(tc.derive("#1f6a7a", dark, b).tokens)) for b in tc.BACKGROUNDS}
            self.assertEqual(keys["meridiana"], keys["tinted"])
            self.assertEqual(keys["grey"], keys["tinted"])
            for name in ("plan.bg", "plan.module", "plan.halo", "plan.sel", "d3.sky_top", "d3.module_sel",
                         "chart.surface", "accent", "assistant", "tooltip_bg"):
                self.assertIn(name, keys["meridiana"])

    def test_meridiana_keeps_the_colours_of_section_7(self):
        t = tc.derive("#8b5a12", False).tokens
        self.assertEqual((t["window"], t["plan"]["bg"], t["plan"]["module"], t["d3"]["roof"]),
                         ("#f2f1ed", "#fbfaf8", "#1f3352", "#b5643f"))      # the window of the mockups (study 17)
        d = tc.derive("#8b5a12", True).tokens
        self.assertEqual((d["view"], d["plan"]["guide"], d["d3"]["sky_top"]), ("#1c1c1c", "#8ab4f8", "#0f141c"))

    def test_every_role_of_the_palette_is_set_and_the_contrasts_hold(self):
        seeds = list(tc.PRESETS.values()) + ["#0078d4", "#c88800"] + random_seeds(60)
        for seed in seeds:
            for backgrounds in tc.BACKGROUNDS:
                for dark in (False, True):
                    pal = tc.palette(tc.derive(seed, dark, backgrounds).tokens, dark)
                    where = f"{seed} {backgrounds} {'dark' if dark else 'light'}"
                    self.assertEqual(set(pal), set(tc.GROUPS), where)
                    for group in tc.GROUPS:
                        self.assertEqual(set(pal[group]), set(tc.ROLES), where)
                        self.assertTrue(all(tc.valid_hex(c) for c in pal[group].values()), where)
                    a = pal["Active"]
                    for fg, bg, least in (("WindowText", "Window", 7), ("Text", "Base", 7), ("ButtonText", "Button", 7),
                                          ("ToolTipText", "ToolTipBase", 7), ("HighlightedText", "Highlight", 7),
                                          ("PlaceholderText", "Base", 4.5), ("Link", "Base", 4.5)):
                        self.assertGreaterEqual(tc.contrast(a[fg], a[bg]), least, f"{where}: {fg} on {bg}")
                    self.assertLess(tc.contrast(pal["Disabled"]["Text"], a["Base"]), tc.contrast(a["Text"], a["Base"]))

    def test_every_token_is_a_colour(self):
        for backgrounds in tc.BACKGROUNDS:
            for dark in (False, True):
                for name, value in flat(tc.derive("#5b4bb0", dark, backgrounds).tokens).items():
                    self.assertTrue(tc.valid_hex(value[:7]) and len(value) in (7, 9), f"{name} {value}")

    def test_the_surfaces_and_the_controls_stand_apart(self):
        """The floors of the mockups Daniel chose (study 17, A3 and C2; back to them on 24/10/2026): the window, the
        panel and the card go up in lightness, the cards stand apart by their line (and their shadow), the fields and
        the result tiles by their tone; the border of a field at 3:1 from the panel and from the field (WCAG
        1.4.11), the muted text at 4.5:1 on every floor, the errors' red readable on a field, the text on the
        accent."""
        seeds = list(tc.PRESETS.values()) + ["#0078d4", "#c88800"]
        c = tc.contrast
        for seed in seeds:
            for backgrounds in tc.BACKGROUNDS:
                for dark in (False, True):
                    t = tc.derive(seed, dark, backgrounds).tokens
                    where = f"{seed} {backgrounds} {'dark' if dark else 'light'}"
                    lighter = (lambda a, b: tc.luminance(a) >= tc.luminance(b))
                    self.assertTrue(lighter(t["panel"], t["window"]) and lighter(t["card"], t["panel"]), where)
                    self.assertGreaterEqual(c(t["window"], t["panel"]), 1.04, where)
                    self.assertGreaterEqual(c(t["line_soft"], t["window"]), 1.07, where)     # the edge of a card
                    self.assertGreaterEqual(c(t["line"], t["card"]), 1.25, where)            # a group's frame
                    self.assertGreaterEqual(c(t["field"], t["panel"]), 1.05, where)          # fields and tiles
                    self.assertGreaterEqual(c(t["field_line"], t["panel"]), 3.0, where)
                    self.assertGreaterEqual(c(t["field_line"], t["field"]), 3.0, where)
                    for floor in ("window", "panel", "card"):
                        self.assertGreaterEqual(c(t["muted"], t[floor]), 4.5, f"{where}: muted on {floor}")
                    self.assertGreaterEqual(c(t["danger"], t["field"]), 4.5, where)
                    self.assertGreaterEqual(c(t["accent"], t["accent_fg"]), 4.5, where)
                    self.assertGreaterEqual(c(t["accent_hover"], t["accent_fg"]), 4.5, where)
                    self.assertGreaterEqual(tc.nearest_status(t["accent"])[1], tc.NEAR, where)
                    self.assertGreaterEqual(tc.nearest_status(t["assistant"])[1], tc.NEAR, where)

    def test_bronze_gives_the_surfaces_of_the_study(self):
        t = tc.derive("#8b5a12", False).tokens
        self.assertEqual((t["card"], t["field"], t["field_line"]), ("#ffffff", "#ebeae7", "#7e7a72"))
        d = tc.derive("#8b5a12", True).tokens
        self.assertEqual((d["card"], d["field"], d["field_line"]), ("#252525", "#1d1d1d", "#6f6f6f"))
        self.assertEqual(d["card"], d["panel"])                                       # as in the mockups

    def test_mixing_two_colours(self):
        self.assertEqual(tc.mix("#000000", "#ffffff", 0.5), "#808080")
        self.assertEqual(tc.mix("#123456", "#abcdef", 0.0), "#123456")
        self.assertEqual(tc.mix("#123456", "#abcdef", 1.0), "#abcdef")


class Choice(unittest.TestCase):
    def test_the_accent_of_the_portal(self):
        self.assertEqual(tc.portal_accent((0.784, 0.533, 0.0)), "#c88800")       # GNOME's yellow on Lucciola
        self.assertEqual(tc.portal_accent([1, 1, 1]), "#ffffff")
        for nothing in ((-1.0, -1.0, -1.0), (1.2, 0, 0), (0.5, 0.5), None, "x", ("a", 0, 0)):
            self.assertEqual(tc.portal_accent(nothing), "", nothing)

    def test_the_accent_as_gdbus_prints_it(self):
        self.assertEqual(tc.gdbus_accent("(<(0.78431372549019607, 0.53333333333333333, 0.0)>,)\n"), "#c88800")
        self.assertEqual(tc.gdbus_accent("(<<(1.0, 1.0, 1.0)>>,)"), "#ffffff")      # the older Read
        for nothing in ("(<(-1.0, -1.0, -1.0)>,)", "", "Error: GDBus.Error:org.freedesktop.DBus.Error.ServiceUnknown",
                        "(<uint32 1>,)", None):
            self.assertEqual(tc.gdbus_accent(nothing), "", nothing)

    def test_a_number_of_the_portal_as_gdbus_prints_it(self):
        self.assertEqual(tc.gdbus_number("(<uint32 1>,)"), 1)          # reduced-motion: less, please
        self.assertEqual(tc.gdbus_number("(<<uint32 0>>,)"), 0)
        for nothing in ("", "Error: GDBus.Error:org.freedesktop.portal.Error.NotFound", None):
            self.assertIsNone(tc.gdbus_number(nothing))

    def test_the_colour_chosen_in_the_settings(self):
        self.assertEqual(tc.seed_for("system", "#0078D4"), "#0078d4")
        self.assertEqual(tc.seed_for("system", ""), tc.DEFAULT_SEED)            # no system accent: bronze
        self.assertEqual(tc.seed_for("petrol"), "#1f6a7a")
        self.assertEqual(tc.seed_for("#AbCdEf"), "#abcdef")
        for wrong in ("#abc", "teal", "", "#ggggggg"):
            self.assertEqual(tc.seed_for(wrong), tc.DEFAULT_SEED, wrong)

    def test_the_preview_says_when_the_colour_was_moved(self):
        self.assertIn("red of the errors", tc.retouch_note(tc.derive("#8b5a12", False).report, False))
        self.assertIn("darker", tc.retouch_note(tc.derive("#8b5a12", False).report, False))
        self.assertIn("yellow", tc.retouch_note(tc.derive("#8b5a12", True).report, True))
        self.assertEqual(tc.retouch_note(tc.derive("#1f6a7a", False).report, False), "")


class StringTints(unittest.TestCase):
    """A tint for each string on the plan (task 16d, step 6), from the chosen colour: distinct from each other and
    from the traffic light by the threshold of study 13 (12.3), for the ready-made colours and 100 at random."""

    def test_the_tints_stay_apart_from_each_other_and_from_the_states(self):
        import itertools
        seeds = list(tc.PRESETS.values()) + ["#0078d4", "#c88800"] + random_seeds(100)
        for seed in seeds:
            with self.subTest(seed=seed):
                tints = tc.string_tints(seed)
                self.assertEqual(len(tints), tc.TINTS)
                self.assertEqual(len(set(tints)), tc.TINTS)
                for a, b in itertools.combinations(tints, 2):
                    self.assertGreaterEqual(tc.distance(a, b), tc.NEAR, (a, b))
                for t in tints:
                    self.assertGreaterEqual(tc.nearest_status(t)[1], tc.NEAR, t)
                    self.assertGreaterEqual(tc.distance(t, "#ff38c8"), tc.NEAR, t)      # nor the selection
                    self.assertGreaterEqual(tc.contrast(t, tc.TINT_HALO), tc.TINT_CONTRAST, t)

    def test_the_first_tint_takes_the_hue_of_the_chosen_colour(self):
        for name in ("bronze", "petrol", "plum", "blue"):
            seed = tc.PRESETS[name]
            first = tc.string_tints(seed)[0]
            gap = abs(((tc.lch(first)[2] - tc.lch(seed)[2] + 180) % 360) - 180)
            self.assertLess(gap, 30.0, name)
        self.assertNotEqual(tc.string_tints(tc.PRESETS["bronze"]), tc.string_tints(tc.PRESETS["blue"]))
        self.assertEqual(tc.string_tints("#8B5A12"), tc.string_tints("#8b5a12"))


if __name__ == "__main__":
    unittest.main()
