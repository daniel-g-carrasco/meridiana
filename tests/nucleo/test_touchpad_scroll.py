"""Precise touchpad movement must survive missing phases and synthetic wheel sources."""
import unittest

import _setup  # noqa: F401
from meridiana.navigation import wheel_action


class TouchpadScroll(unittest.TestCase):
    def test_unphased_pixel_only_scroll_pans_in_both_axes(self):
        self.assertEqual(wheel_action((0, 0), (25, -13), False, False, False), ("pan", 25, -13))

    def test_pixel_delta_has_priority_over_angle_delta_for_a_touchpad(self):
        self.assertEqual(wheel_action((120, 60), (7, -3), False, True, False), ("pan", 7, -3))

    def test_real_touchpad_does_not_need_synthesized_source_or_phases(self):
        self.assertEqual(wheel_action((0, 120), (0, 38), False, False, False, touchpad=True), ("pan", 0, 38))

    def test_angle_only_precision_scroll_is_twice_the_old_half_angle_fallback(self):
        self.assertEqual(wheel_action((120, -60), (0, 0), False, True, False), ("pan", 120, -60))

    def test_a_phased_scroll_moves_by_its_pixels_even_when_they_round_to_zero(self):
        """Review B (30/10/2026): Qt's Wayland client rounds each pixelDelta and carries the remainder to the
        next event, while angleDelta is twelve times the unrounded movement. A slow two-finger scroll has updates
        with pixel (0, 0) and angle (0, -4): falling back to the angle jumped four pixels instead of none."""
        total, carried = 0.0, 0.0
        for delta in (0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3):      # the compositor's movement, surface pixels
            pixel = round(-delta + carried)
            carried += -delta - pixel
            angle = round(-12 * delta)
            action, _dx, dy = wheel_action((0, angle), (0, pixel), True, False, False, touchpad=True)
            self.assertEqual(action, "pan")
            total += dy
        self.assertEqual(total, round(-0.3 * 7))
        self.assertEqual(wheel_action((0, -4), (0, 0), True, False, False), ("pan", 0, 0))

    def test_unphased_angle_only_touchpad_events_still_use_the_angle(self):
        """X11's libinput driver gives no pixels: the angle remains the only measure of the movement."""
        self.assertEqual(wheel_action((0, 24), (0, 0), False, False, False, touchpad=True), ("pan", 0, 24))

    def test_a_mouse_wheel_and_ctrl_pinch_keep_their_zoom_profiles(self):
        self.assertEqual(wheel_action((0, 120), (0, 12), False, False, False), ("wheel", 0, 1))
        self.assertEqual(wheel_action((0, -60), (0, 0), False, True, True), ("zoom", 0, -0.5))
