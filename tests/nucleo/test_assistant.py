"""The assistant's shell (study 14, 7.3 and 8; study 17, theme G; design 3.9): Meridio drawn on a grid of 24 in the
theme's colours and his pixel twin on a grid of 17, the disc kept light enough on a light panel (R33), the small
movements (`Mood`), the place where he floats on each tab and where his speech bubble opens, the questions ready.
The window is in test_assistant_window.py."""

import re
import unittest
import xml.etree.ElementTree as ET

import _setup  # noqa: F401

from meridiana import assistant, theme_colors

SVG = "{http://www.w3.org/2000/svg}"


def elements(text: str, tag: str) -> list:
    return list(ET.fromstring(text).iter(SVG + tag))


class Character(unittest.TestCase):
    def test_the_disc_keeps_its_hue_and_is_light_on_the_light_panel_and_readable_under_the_ink(self):
        for seed in list(theme_colors.PRESETS.values()) + ["#0078d4", "#c88800", "#000000", "#ffffff"]:
            for dark in (False, True):
                t = theme_colors.derive(seed, dark).tokens
                disc = assistant.disc_colour(t["assistant"])
                L, C, h = theme_colors.lch(disc)
                with self.subTest(seed=seed, dark=dark):
                    if dark:
                        self.assertTrue(0.575 <= L <= 0.725, L)
                    else:
                        self.assertAlmostEqual(L, 0.80, delta=0.01)             # R33: it was 0.58, too dark
                    self.assertLessEqual(C, 0.1505)
                    self.assertGreaterEqual(theme_colors.contrast(assistant.INK, disc), 4.5 if dark else 7.0)
                    self.assertGreaterEqual(theme_colors.contrast(t["panel"], disc), 1.5)
                    if theme_colors.lch(t["assistant"])[1] > 0.02:            # a grey has no hue to keep
                        self.assertLess(abs((h - theme_colors.lch(t["assistant"])[2] + 180) % 360 - 180), 8)
        self.assertEqual(assistant.disc_colour("#334f6d"), assistant.disc_colour("#334f6d", dark=False))
        self.assertEqual(assistant.disc_colour("#a1c1e4"), assistant.disc_colour("#a1c1e4", dark=True))

    def test_meridio_is_drawn_on_a_grid_of_24_as_the_study_says(self):
        text = assistant.svg("#ece8e1", "#a1c1e4")
        self.assertEqual(ET.fromstring(text).get("viewBox"), "0 0 24 24")
        circles = elements(text, "circle")
        disc = circles[0]
        self.assertEqual((disc.get("cx"), disc.get("cy"), disc.get("r")), ("12", "10.2", "5.3"))
        self.assertEqual((disc.get("stroke"), disc.get("stroke-width")), ("#24211d", "1.3"))
        eyes = [(c.get("cx"), c.get("cy")) for c in circles[1:]]
        self.assertEqual(eyes, [("10.1", "9.5"), ("13.9", "9.5")])
        paths = elements(text, "path")
        self.assertEqual(paths[0].get("stroke"), "#ece8e1")               # the rays in the text's colour
        self.assertTrue(paths[0].get("d").startswith("M5.10 10.20L3.40 10.20"))   # the first ray, as it was
        self.assertEqual(paths[0].get("d").count("M"), 11)    # the whole picture: the rays above the horizon only
        self.assertEqual(assistant.svg("#000", "#4f6f95", parts="rays").count("M"), 12)    # the layer: all twelve
        self.assertEqual(paths[2].get("d"), assistant.SMILE)

    def test_the_rays_turn_above_the_horizon_and_the_layers_come_apart(self):
        turned = elements(assistant.svg("#000", "#4f6f95", rays=15), "path")[0].get("d")
        self.assertNotEqual(turned, assistant.RAYS)
        layer = elements(assistant.svg("#000", "#4f6f95", rays=30, parts="rays"), "path")[0].get("d")
        self.assertEqual(layer.count("M"), 12)
        # no clipPath: Qt's SVG renderer has none and painted its rectangle black (24/10/2026); the whole picture
        # cuts its rays on the geometry, every point above the line
        whole = assistant.svg("#000", "#4f6f95", rays=15)
        self.assertEqual(len(elements(whole, "clipPath")) + len(elements(whole, "rect")), 0)
        ys = [float(v) for v in re.findall(r"[ML][-0-9.]+ ([-0-9.]+)", elements(whole, "path")[0].get("d"))]
        self.assertTrue(ys and max(ys) <= assistant.RAYS_CLIP_Y + 1e-9)
        rays_only = assistant.svg("#000", "#4f6f95", parts="rays")
        face_only = assistant.svg("#000", "#4f6f95", parts="face")
        self.assertEqual(len(elements(rays_only, "circle")), 0)
        self.assertEqual(len(elements(face_only, "clipPath")), 0)
        self.assertEqual(len(elements(face_only, "circle")), 3)

    def test_thinking_the_eyes_go_up_and_three_dots_appear(self):
        circles = elements(assistant.svg("#1e1c19", "#334f6d", thinking=True), "circle")
        self.assertEqual([c.get("cy") for c in circles[1:3]], ["8.7", "8.7"])
        self.assertEqual([(c.get("cx"), c.get("r")) for c in circles[3:]],
                         [("19.2", "0.75"), ("21.2", "0.75"), ("23.2", "0.75")])

    def test_the_gaze_moves_the_eyes_by_half_a_unit_at_most_and_the_blink_closes_them(self):
        for gaze in ((1, 1), (-1, -1), (0, 1), (3, -7)):
            circles = elements(assistant.svg("#000", "#4f6f95", gaze=gaze), "circle")
            for c, x0 in zip(circles[1:3], (10.1, 13.9), strict=True):
                with self.subTest(gaze=gaze):
                    self.assertLessEqual(abs(float(c.get("cx")) - x0), 0.5001)
                    self.assertLessEqual(abs(float(c.get("cy")) - 9.5), 0.5001)
        closed = assistant.svg("#000", "#4f6f95", blink=True)
        self.assertEqual(len(elements(closed, "circle")), 1)              # the disc alone: the eyes are lines
        self.assertEqual(len(elements(closed, "path")), 5)                # rays, horizon, smile, two lids

    def test_four_brief_faces(self):
        wink = assistant.svg("#000", "#4f6f95", expression="wink")
        self.assertEqual(len(elements(wink, "circle")), 2)                # one eye closed
        surprise = assistant.svg("#000", "#4f6f95", expression="surprise")
        self.assertEqual(len(elements(surprise, "ellipse")), 1)           # the mouth an "o"
        self.assertEqual(elements(surprise, "circle")[1].get("r"), "1.15")
        self.assertIn(assistant.GRIN, assistant.svg("#000", "#4f6f95", expression="grin"))
        self.assertIn(assistant.FLAT, assistant.svg("#000", "#4f6f95", expression="hmm"))
        self.assertEqual(len(assistant.EXPRESSIONS), 4)


class PixelCharacter(unittest.TestCase):
    def test_the_pixel_twin_stays_in_its_grid_and_is_symmetric(self):
        cells = assistant.pixel_cells()
        for key, points in cells.items():
            for x, y in points:
                self.assertTrue(0 <= x < assistant.PIXEL_N and 0 <= y < assistant.PIXEL_N, (key, x, y))
        disc = cells["disc"] | {c for c in cells["ink"] if c[1] <= 11 and c not in assistant.PIXEL_MOUTHS[""]}
        self.assertEqual({(16 - x, y) for x, y in disc if y != 6}, {c for c in disc if c[1] != 6})
        self.assertTrue({(6, 6), (10, 6)} <= cells["ink"] and (8, 6) in cells["disc"])      # the eyes
        self.assertTrue(cells["disc"].isdisjoint(cells["ink"]))

    def test_the_pixel_svg_is_crisp_and_shows_the_state(self):
        text = assistant.pixel_svg("#1e1c19", "#4f6f95")
        root = ET.fromstring(text)
        self.assertEqual((root.get("viewBox"), root.get("shape-rendering")), ("0 0 17 17", "crispEdges"))
        self.assertTrue(all(r.get("height") == "1" for r in elements(text, "rect")))
        thinking = assistant.pixel_cells(thinking=True)
        self.assertTrue(set(assistant.PIXEL_DOTS) <= thinking["text"])
        self.assertTrue({(6, 5), (10, 5)} <= thinking["ink"] and (6, 6) not in thinking["ink"])   # the eyes up
        blink = assistant.pixel_cells(blink=True)
        self.assertTrue({(5, 7), (6, 7), (7, 7), (9, 7), (10, 7), (11, 7)} <= blink["ink"])
        self.assertTrue(set(assistant.PIXEL_MOUTHS["grin"]) <= assistant.pixel_cells(expression="grin")["ink"])

    def test_the_pixel_rays_go_by_eight_steps(self):
        steps = [assistant.pixel_rays(s) for s in range(8)]
        self.assertGreaterEqual(len(set(steps)), 4)
        self.assertEqual(assistant.pixel_rays(8), steps[0])
        self.assertTrue(all(y <= assistant.PIXEL_RAYS_CLIP_ROW for cells in steps for _x, y in cells))
        self.assertEqual([assistant.pixel_step(a) for a in (0, 3.75, 7.5, 29.9, 30, 33.75, 360)], [0, 1, 2, 7, 0, 1, 0])

    def test_the_drawings_shipped_in_data_are_the_ones_the_program_draws(self):
        from meridiana import paths
        for name, text in (("meridio.svg", assistant.svg("#1e1c19", "#4f6f95")),
                           ("meridio-pixel.svg", assistant.pixel_svg("#1e1c19", "#4f6f95"))):
            shipped = paths.shipped("meridio", name)
            self.assertIsNotNone(shipped, name)
            on_disk = shipped.read_text(encoding="utf-8")
            start = on_disk.index("-->") + 3
            self.assertEqual(on_disk[:on_disk.index("<!--")] + on_disk[start:].rstrip("\n"), text, name)


class Moods(unittest.TestCase):
    def run_mood(self, seed: int, seconds: float, step: float = 0.05, before=None) -> list:
        m = assistant.Mood(seed=seed)
        if before is not None:
            before(m)
        frames, t = [], 0.0
        while t <= seconds:
            frames.append((round(t, 3), m.frame(t)))
            t += step
        return frames

    def test_the_breath_stays_between_1_and_1_04_and_stops_a_few_seconds_after_the_chat_is_closed(self):
        frames = self.run_mood(1, 30)
        scales = [f.scale for _t, f in frames]
        self.assertTrue(all(1.0 <= s <= 1.0401 for s in scales))
        self.assertGreater(max(scales[:80]), 1.03)                        # awake at the start: it breathes
        asleep = [f for t, f in frames if t > assistant.AWAKE_S + assistant.BREATH_S + 0.2]
        self.assertTrue(asleep and all(not f.awake and f.scale == 1.0 for f in asleep))

    def test_the_rays_turn_one_turn_a_minute_while_awake_and_then_stand_still(self):
        def opened(m):
            m.set_opened(True, 0.0)
        frames = self.run_mood(2, 60, before=opened)
        self.assertAlmostEqual(frames[-1][1].rays, 0.0, delta=0.5)       # a whole turn after 60 s
        self.assertAlmostEqual(frames[200][1].rays, 60.0, delta=0.5)      # 10 s: 60 degrees
        m = assistant.Mood(seed=2)
        m.set_opened(True, 0.0)
        m.frame(1.0)
        m.set_opened(False, 1.0)
        angles = [m.frame(1.0 + k * 0.5).rays for k in range(1, 30)]
        self.assertGreater(angles[4], angles[0])                          # still turning right after closing
        self.assertEqual(angles[-1], angles[-5])                          # stopped after AWAKE_S

    def test_the_blink_comes_every_4_to_8_seconds_never_two_closer(self):
        for seed in (1, 7, 42):
            frames = self.run_mood(seed, 300, step=0.02)
            starts, was = [], False
            for t, f in frames:
                if f.blink and not was:
                    starts.append(t)
                was = f.blink
            gaps = [b - a for a, b in zip(starts, starts[1:], strict=False)]
            with self.subTest(seed=seed):
                self.assertGreater(len(starts), 30)
                self.assertTrue(all(4.0 - 0.03 <= g <= 8.0 + 0.03 for g in gaps), (min(gaps), max(gaps)))
                lengths = [sum(1 for t, f in frames if s <= t < s + 0.5 and f.blink) for s in starts[:5]]
                self.assertTrue(all(5 <= n <= 7 for n in lengths), lengths)         # 120 ms at 50 frames a second

    def test_the_gaze_never_goes_beyond_one_step_and_the_same_seed_gives_the_same_sequence(self):
        a = self.run_mood(5, 120)
        b = self.run_mood(5, 120)
        self.assertEqual([f for _t, f in a], [f for _t, f in b])
        self.assertTrue(all(abs(f.gaze[0]) <= 1 and abs(f.gaze[1]) <= 1 for _t, f in a))
        self.assertTrue(any(f.gaze != (0, 0) for _t, f in a))             # it glances aside now and then
        self.assertNotEqual([f for _t, f in a], [f for _t, f in self.run_mood(6, 120)])

    def test_the_faces_come_soon_after_the_chat_is_used_and_slowly_at_random(self):
        m = assistant.Mood(seed=3)
        self.assertEqual(m.frame(0.0).expression, "")
        m.touch(1.0)
        soon = [m.frame(1.0 + k * 0.05).expression for k in range(1, 40)]
        self.assertTrue(any(soon))
        first = next(e for e in soon if e)
        self.assertIn(first, assistant.EXPRESSIONS)
        held = [e for e in soon if e]
        self.assertTrue(16 <= len(held) <= 27, len(held))                 # 0,8-1,3 s long
        self.assertEqual(set(held), {first})
        # at rest: the next one between 60 and 120 s later
        starts, was, t = [], "", 3.0
        while t < 600:
            e = m.frame(t).expression
            if e and not was:
                starts.append(t)
            was = e
            t += 0.05
        gaps = [b - a for a, b in zip(starts, starts[1:], strict=False)]
        self.assertTrue(gaps and all(assistant.EXPRESSION_EVERY[0] - 1 <= g <= assistant.EXPRESSION_EVERY[1] + 2
                                     for g in gaps), gaps)

    def test_the_gaze_follows_a_point_a_tenth_of_a_second_later_and_comes_back_after_two_seconds_still(self):
        m = assistant.Mood(seed=0)
        m.next_glance = 1e9                                               # no glance in the way
        m.frame(0.0)
        m.look_at((2.0, -1.5), 1.0)
        self.assertEqual(m.frame(1.05).gaze, (0, 0))                     # not yet
        self.assertEqual(m.frame(1.15).gaze, (1, -1))
        self.assertEqual(m.frame(2.9).gaze, (1, -1))
        self.assertEqual(m.frame(3.1).gaze, (0, 0))                       # still for two seconds: back
        m.look_at((0.1, 0.2), 4.0)                                        # straight ahead: too near to matter
        self.assertEqual(m.frame(4.2).gaze, (0, 0))

    def test_thinking_shows_in_the_frame_and_keeps_him_awake(self):
        m = assistant.Mood(seed=0)
        m.set_state(assistant.THINKING, 0.0)
        f = m.frame(20.0)
        self.assertTrue(f.thinking and f.awake)
        m.set_state(assistant.IDLE, 20.0)
        self.assertFalse(m.frame(20.1).thinking)
        with self.assertRaises(ValueError):
            m.set_state("bored", 0.0)


class Places(unittest.TestCase):
    def test_where_it_floats_on_each_tab(self):
        area, size = (1000, 600), (46, 46)
        model = assistant.place(assistant.default_anchor("model", reserved_bottom=40), size, area)
        self.assertEqual(model, (1000 - 46 - 12, 600 - 46 - 12 - 40))     # above the sun bar, by the properties
        production = assistant.place(assistant.default_anchor("production", 40), size, area)
        self.assertEqual(production, (1000 - 46 - 12, 600 - 46 - 12))     # bottom right, as every phase
        economics = assistant.place(assistant.default_anchor("economics", 40), size, area)
        self.assertEqual(economics, (1000 - 46 - 12, 600 - 46 - 12))
        plant = assistant.place(assistant.default_anchor("plant", 30), size, area)
        self.assertEqual(plant, (1000 - 46 - 12, 600 - 46 - 12 - 30))     # above the plan's attribution

    def test_a_dragged_place_keeps_its_corner_when_the_area_changes(self):
        anchor = assistant.anchor_of((100, 50), (46, 46), (1000, 600))
        self.assertEqual(anchor, ("left", "top", 100, 50))
        anchor = assistant.anchor_of((800, 500), (46, 46), (1000, 600))
        self.assertEqual(anchor, ("right", "bottom", 154, 54))
        self.assertEqual(assistant.place(anchor, (46, 46), (700, 400)), (700 - 46 - 154, 400 - 46 - 54))

    def test_an_anchor_read_back_is_checked(self):
        self.assertEqual(assistant.valid_anchor(["right", "bottom", 3, 4]), ("right", "bottom", 3, 4))
        for bad in (None, "x", ["up", "bottom", 3, 4], ["left", "top", -1, 0], ["left", "top", 1.5, 0], [1, 2]):
            self.assertIsNone(assistant.valid_anchor(bad), bad)

    def test_a_place_stays_inside_the_area(self):
        self.assertEqual(assistant.clamp((-30, 900), (800, 500), (320, 380)), (0, 120))
        self.assertEqual(assistant.clamp((700, 10), (800, 500), (320, 380)), (480, 10))
        self.assertEqual(assistant.clamp((10, 10), (100, 100), (320, 380)), (0, 0))      # too big: the corner

    def test_three_questions_ready_for_each_tab(self):
        for tab in assistant.TABS:
            self.assertEqual(len(assistant.questions(tab)), 3)
        self.assertIn("layout", assistant.questions("model")[0])


class SpeechBubble(unittest.TestCase):
    def test_it_opens_beside_him_towards_the_middle_with_the_tail_pointing_at_him(self):
        area, size, gap = (1000, 800), (320, 400), assistant.GAP
        b = assistant.bubble_place((942, 742, 46, 46), size, area)        # bottom right: to his left
        self.assertEqual((b.tail, b.x + b.width + gap, b.y + b.height), ("right", 942, 742 + 46))
        self.assertEqual(b.y + b.at, 742 + 23)                            # the tail at his centre
        self.assertEqual(b.grip, "top-left")
        self.assertFalse(assistant.overlaps(b.rect, (942, 742, 46, 46)))
        b = assistant.bubble_place((12, 742, 46, 46), size, area)         # bottom left: to his right
        self.assertEqual((b.tail, b.x, b.grip), ("left", 12 + 46 + gap, "top-right"))
        b = assistant.bubble_place((12, 12, 46, 46), size, area)          # top left: to his right, top aligned
        self.assertEqual((b.tail, b.y, b.at, b.grip), ("left", 12, 23, "bottom-right"))

    def test_it_goes_above_or_below_when_there_is_no_room_beside_and_nowhere_over_what_is_to_be_avoided(self):
        b = assistant.bubble_place((300, 542, 46, 46), (320, 400), (400, 600))      # a narrow area: above
        self.assertEqual((b.tail, b.y + b.height + assistant.GAP), ("bottom", 542))
        self.assertEqual(b.x + b.at, 323)
        self.assertEqual(b.grip, "top-left")
        blocked = assistant.bubble_place((942, 742, 46, 46), (320, 400), (1000, 800), avoid=[(500, 300, 400, 400)])
        self.assertIsNone(blocked)
        beside = assistant.bubble_place((942, 742, 46, 46), (320, 400), (1000, 800), avoid=[(0, 0, 300, 300)])
        self.assertEqual(beside.tail, "right")

    def test_when_nothing_fits_the_bubble_stays_inside_the_area_beside_him(self):
        b = assistant.bubble_fallback((242, 102, 46, 46), (280, 160), (300, 160))
        self.assertEqual((b.tail, b.x, b.y, b.width, b.height), ("right", 0, 0, 280, 160))
        self.assertEqual(b.at, 125)
        b = assistant.bubble_fallback((12, 102, 46, 46), (280, 160), (300, 160))
        self.assertEqual((b.tail, b.x), ("left", 20))

    def test_the_free_corners_the_farthest_from_what_is_to_be_avoided_first(self):
        corners = assistant.free_corners((942, 742, 46, 46), (1000, 800), [(500, 300, 400, 400)], (12, 12))
        self.assertEqual(corners[0], (12, 12))
        self.assertNotIn((942, 742), corners)
        self.assertEqual(len(corners), 3)

    def test_the_size_is_kept_to_what_the_area_holds(self):
        self.assertEqual(assistant.bubble_size((320, 400), (1000, 800)), (320, 400))
        beside = 380 - 46 - assistant.GAP - 2 * assistant.MARGIN                   # 306: narrower than asked
        self.assertEqual(assistant.bubble_size((320, 400), (380, 300)), (beside, 300 - 24))
        self.assertEqual(assistant.bubble_size((320, 400), (500, 300)), (320, 276))
        self.assertEqual(assistant.bubble_size((320, 400), (200, 150)), (200, 150))   # a tiny area: the area


if __name__ == "__main__":
    unittest.main()
