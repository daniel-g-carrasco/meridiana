"""How the window arranges itself for its size (R334, study 27): the function without Qt, on the tables of the study, and
nothing that jumps to and fro near a threshold (Daniel: «nessun cambio a sorpresa»)."""

import unittest

from meridiana import phases
from meridiana.arrangement import (BAND, BESIDE, ICONS, UNDER, Arrangement, Choices, arrangement, changes, clean_pins,
                                   from_dict, pinned, shape_of)

# the widths the bars ask for with the Italian words (BC-dopo.json, 03/11/2026)
NEEDS = {UNDER: {"model": 850, "plant": 1030, "production": 420, "report": 700},
         BESIDE: {"model": 930, "plant": 1150, "production": 500, "report": 800},
         ICONS: {"model": 490, "plant": 540, "production": 250, "report": 320}}
TRAILING = {"plant": 300, "production": 240}


def choices(**more) -> Choices:
    return Choices(needs=NEEDS, trailing=TRAILING, row_needs=1000, **more)


def walk(sizes, phase="model", start=None, **more):
    """Every step of a window resized through `sizes`, each knowing the one before."""
    out, was = [], start
    for w, h in sizes:
        was = arrangement(w, h, phase, choices(previous=was, **more))
        out.append(was)
    return out


class TheCasesOfTheStudy(unittest.TestCase):
    def one(self, w, h, phase="model", **more):
        return arrangement(w, h, phase, choices(**more))

    def test_the_wide_window_is_the_reference(self):
        a = self.one(1920, 1080)
        self.assertEqual((a.shape, a.row, a.bar, a.panels, a.checks_open, a.views),
                         ("wide", "names", UNDER, "apart", True, "side"))

    def test_the_laptop_keeps_its_words_beside_the_icons_and_closes_the_checks(self):
        a = self.one(1366, 768)
        self.assertEqual((a.shape, a.row, a.bar, a.panels, a.checks_open, a.views),
                         ("medium", "names", BESIDE, "apart", False, "side"))

    def test_the_monitor_turned_has_the_views_one_above_the_other(self):
        a = self.one(1080, 1920)
        self.assertEqual((a.shape, a.row, a.bar, a.panels, a.checks_open, a.views),
                         ("vertical", "names", UNDER, "apart", True, "stacked"))

    def test_the_tablet_upright_has_numbers_icons_and_the_panels_together(self):
        a = self.one(800, 1280)
        self.assertEqual((a.shape, a.row, a.bar, a.panels, a.checks_open, a.views),
                         ("vertical", "numbers", ICONS, "together", True, "stacked"))

    def test_half_a_screen(self):
        a = self.one(960, 1080)
        self.assertEqual((a.row, a.bar, a.panels, a.views), ("numbers", ICONS, "together", "stacked"))

    def test_one_view_at_a_time_when_there_is_no_room_for_two(self):
        self.assertEqual(self.one(683, 728).views, "one")           # V2: the area under 480 px
        self.assertEqual(self.one(700, 800).views, "one")
        self.assertEqual(self.one(900, 500).views, "one")           # wide enough, too low for two one above the other

    def test_the_bar_looks_at_the_width_too(self):
        """B1: at 800 x 1280 the words used to stay and the groups Precision and Strings went."""
        self.assertEqual(self.one(1080, 1920).bar, UNDER)
        self.assertEqual(self.one(1000, 1920).bar, ICONS)

    def test_the_mode_of_the_bar_is_the_same_in_every_phase(self):
        for w, h in ((1920, 1080), (1366, 768), (1080, 1920), (800, 1280), (960, 1080)):
            self.assertEqual(len({self.one(w, h, p).bar for p in phases.ids()}), 1, (w, h))

    def test_what_stands_at_the_end_of_the_bar_never_takes_the_room_of_the_groups(self):
        self.assertTrue(self.one(1920, 1080, "plant").trailing_in_bar)
        self.assertFalse(self.one(1080, 1920, "plant").trailing_in_bar)      # the groups fit, with it they would not
        self.assertFalse(self.one(1366, 768, "plant").trailing_in_bar)       # two lines of text: not in the low bar
        self.assertTrue(self.one(1080, 1920, "consumption").trailing_in_bar)  # it has none

    def test_the_icons_chosen_stay_chosen(self):
        for w, h in ((1920, 1080), (1366, 768)):
            self.assertEqual(self.one(w, h, toolbar="icons").bar, ICONS)

    def test_the_numbers_go_with_the_room_the_row_asks_for_not_a_fixed_width(self):
        roomy = arrangement(960, 1080, "model", Choices(needs=NEEDS, row_needs=900))
        self.assertEqual(roomy.row, "names")

    def test_the_views_look_at_the_columns_the_user_has_open(self):
        self.assertEqual(self.one(1300, 1200).views, "stacked")
        self.assertEqual(self.one(1300, 1200, columns=(0, 0)).views, "side")


class NothingJumps(unittest.TestCase):
    FIELDS = ("shape", "row", "bar", "panels", "checks_open", "views", "trailing_in_bar")

    def flips(self, steps, name):
        values = [getattr(a, name) for a in steps]
        return sum(1 for x, y in zip(values, values[1:], strict=False) if x != y)

    def test_a_window_moved_to_and_fro_around_each_threshold_changes_at_most_once(self):
        """Within BAND of a line whatever it was stays: 30 px to and fro, three times, for every line."""
        for label, w, h, dw, dh in (("low window", 1400, 900, 0, 1), ("narrow", 1000, 800, 1, 0),
                                    ("bar under", 1074, 1400, 1, 0), ("bar beside", 1194, 800, 1, 0),
                                    ("row", 1000, 1200, 1, 0), ("one view", 796, 800, 1, 0),
                                    ("vertical", 1500, 1500, 0, 1), ("stacked", 1400, 1056, 0, 1)):
            sweep = [(w + dw * d, h + dh * d) for d in (-1, 29, -1, 29, -1, 29)]
            steps = walk(sweep, phase="plant")
            for name in self.FIELDS:
                # past the first step, which may be on either side, nothing changes back and forth
                self.assertLessEqual(self.flips(steps[1:], name), 1, (label, name))

    def test_a_slow_drag_across_all_the_sizes_and_back_is_stable(self):
        """Every pixel from 1920 to 640 and back: each field changes as often going down as there are lines, never more,
        and never twice on the same line."""
        down = [(w, 1080) for w in range(1920, 639, -1)]
        steps = walk(down + down[::-1])
        for name in self.FIELDS:
            self.assertLessEqual(self.flips(steps, name), 6, name)
        # the same for the height
        tall = [(1500, h) for h in range(1600, 500, -1)]
        steps = walk(tall + tall[::-1])
        for name in self.FIELDS:
            self.assertLessEqual(self.flips(steps, name), 6, name)

    def test_the_band_is_what_it_says(self):
        tall = arrangement(1400, 1000, "model", choices())
        low = arrangement(1400, 899, "model", choices(previous=tall))
        self.assertFalse(low.checks_open)
        self.assertFalse(arrangement(1400, 900 + BAND - 1, "model", choices(previous=low)).checks_open)
        self.assertTrue(arrangement(1400, 900 + BAND, "model", choices(previous=low)).checks_open)

    def test_the_answer_does_not_depend_on_what_it_changes(self):
        """Asked again with its own answer as the one before, it says the same thing: no loop of the window with itself."""
        for w, h in ((1920, 1080), (1366, 768), (1080, 1920), (800, 1280), (960, 1080), (683, 728), (1280, 800), (640, 480)):
            once = arrangement(w, h, "model", choices())
            self.assertEqual(arrangement(w, h, "model", choices(previous=once)), once, (w, h))


class TheUsersChoiceWins(unittest.TestCase):
    def test_a_pin_holds_its_field_and_only_that(self):
        a = arrangement(1366, 768, "model", choices(pins={"checks_open": True}))
        self.assertTrue(a.checks_open)
        self.assertEqual(a.bar, BESIDE)

    def test_undo_pins_what_the_change_moved(self):
        wide = arrangement(1920, 1080, "model", choices())
        low = arrangement(1366, 768, "model", choices(previous=wide))
        moved = changes(wide, low)
        self.assertEqual(moved, ("checks_open", "bar"))
        pins = pinned({}, wide, moved)
        back = arrangement(1366, 768, "model", choices(previous=low, pins=pins))
        self.assertEqual(changes(wide, back), ())

    def test_only_what_the_user_sees_move_is_said(self):
        a = Arrangement()
        self.assertEqual(changes(a, Arrangement(row="numbers", trailing_in_bar=False, tall=False)), ())


class TheShapes(unittest.TestCase):
    def test_the_shapes(self):
        self.assertEqual(shape_of(1920, 1080), "wide")
        self.assertEqual(shape_of(1366, 768), "medium")
        self.assertEqual(shape_of(960, 700), "medium")
        self.assertEqual(shape_of(1080, 1920), "vertical")
        self.assertEqual(shape_of(800, 1280), "vertical")

    def test_a_shape_has_its_band(self):
        self.assertEqual(shape_of(1000, 1000 + BAND - 1, "wide"), "wide")
        self.assertEqual(shape_of(1000, 1000 + BAND, "wide"), "vertical")
        self.assertEqual(shape_of(1000, 1000, "vertical"), "vertical")
        self.assertEqual(shape_of(1001, 1000, "vertical"), "medium")
        self.assertEqual(shape_of(1100, 1000, "vertical"), "wide")


class WhatComesFromAFile(unittest.TestCase):
    def test_an_arrangement_read_back(self):
        from dataclasses import asdict
        a = arrangement(800, 1280, "model", choices())
        self.assertEqual(from_dict(asdict(a)), a)
        self.assertIsNone(from_dict({"shape": "wide"}))
        self.assertIsNone(from_dict(None))
        self.assertIsNone(from_dict({**asdict(a), "shape": "round"}))

    def test_pins_that_are_not_pins_are_left_out(self):
        self.assertEqual(clean_pins({"checks_open": True, "bar": "huge", "other": 1}), {"checks_open": True})
        self.assertEqual(clean_pins("nothing"), {})


if __name__ == "__main__":
    unittest.main()
