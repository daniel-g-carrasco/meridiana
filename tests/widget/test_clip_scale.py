"""The DC/AC bar (ui/plant_page.ClipScale, R353, draft C of study 28): a line for the ratio, a line and a track for the
energy cut. Nothing leaves the widget at either end of the scale, where the old mark was cut. PySide6 and a display
(offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state


class ClipScaleBar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def scale(self, loss):
        from meridiana.ui.plant_page import ClipScale
        s = ClipScale()
        self.addCleanup(s.deleteLater)
        s.resize(256, s.height())
        s.set(1.44, loss)
        s.resize(256, s.height())
        return s

    def colour_at(self, s, x):
        image = s.grab().toImage()
        y = s._lines() + 4 + s.TICK_OUT + s.TRACK // 2
        return image.pixelColor(x, y)

    def test_before_the_computation_there_is_no_track(self):
        waiting, computed = self.scale(None), self.scale(0.6)
        self.assertEqual(waiting.height(), waiting._lines())
        self.assertGreater(computed.height(), waiting.height())

    def test_the_colour_follows_the_thresholds_of_the_checks(self):
        for loss, state in ((0.0, "good"), (0.99, "good"), (1.0, "warning"), (3.0, "warning"), (3.1, "critical"),
                            (7.5, "critical")):
            self.assertEqual(self.scale(loss).state(), state, loss)

    def test_the_span_starts_at_the_edge_and_stops_at_the_end(self):
        from PySide6.QtGui import QColor
        s = self.scale(7.5)
        red = QColor(s.colours["critical"])
        for x in (s.TRACK, s.width() - s.TRACK):         # inside the rounded ends, away from the ticks
            c = self.colour_at(s, x)
            self.assertLess(abs(c.red() - red.red()), 12, x)
        empty = self.scale(0.0)
        c = self.colour_at(empty, empty.TRACK)
        self.assertNotEqual(c.name(), QColor(empty.colours["good"]).name())   # 0 %: the track alone

    def test_a_small_share_still_shows(self):
        from PySide6.QtGui import QColor
        s = self.scale(0.01)
        good = QColor(s.colours["good"])
        c = self.colour_at(s, s.TRACK // 2)
        self.assertLess(abs(c.green() - good.green()), 30)

    def test_the_menu_of_an_inverter_is_an_icon(self):
        from meridiana.ui import icons
        self.assertFalse(icons.icon("ellipsis").isNull())
        self.assertFalse(icons.icon("ellipsis").pixmap(16, 16).isNull())


if __name__ == "__main__":
    unittest.main()
