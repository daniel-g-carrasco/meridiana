"""The shape of Meridio's bubble (ui/assistant.outline): one closed path, the tail let into the card's side, so
that no line is drawn between the tail and the card (R293: the union of two paths kept the tail apart at many
heights, mostly with the tail on the left). Geometry over many sizes, and the pixels at the base in both themes.
PySide6 and a display (offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state


def base_segments(path, tail: str, at: float, width: int, height: int) -> list:
    """The segments of the path's outline lying along the tail's base, inside the tail's span."""
    from meridiana import assistant as core
    from meridiana.ui.assistant import RADIUS, TAIL_HALF
    t, half = core.TAIL, TAIL_HALF
    if tail in ("left", "right"):
        at = min(max(at, RADIUS + half), height - RADIUS - half)
        base = 0.5 + t if tail == "left" else width - 0.5 - t
    else:
        at = min(max(at, RADIUS + half), width - RADIUS - half)
        base = 0.5 + t if tail == "top" else height - 0.5 - t
    found = []
    for poly in path.toSubpathPolygons():
        pts = [(p.x(), p.y()) for p in poly]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:], strict=False):
            along = (y1, y2) if tail in ("left", "right") else (x1, x2)
            across = (x1, x2) if tail in ("left", "right") else (y1, y2)
            if all(abs(v - base) < 0.01 for v in across):
                lo, hi = sorted(along)
                if lo < at + half - 0.5 and hi > at - half + 0.5:
                    found.append(((x1, y1), (x2, y2)))
    return found


class Outline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_one_closed_shape_with_no_edge_along_the_tails_base_at_any_size(self):
        from meridiana.ui.assistant import outline
        # the heights where the union of two paths left a seam (320 wide, tail left): 247, 310, 324, 457, 478...
        for width in (280, 320, 420):
            for height in range(240, 720, 7):
                for tail in ("left", "right", "top", "bottom"):
                    span = height if tail in ("left", "right") else width
                    for at in range(0, span, 23):
                        path = outline(width, height, tail, at)
                        polygons = path.toSubpathPolygons()
                        self.assertEqual(len(polygons), 1, (width, height, tail, at))
                        self.assertEqual(base_segments(path, tail, at, width, height), [], (width, height, tail, at))
                        # the tip is there, t pixels out of the card's side
                        xs = [p.x() for p in polygons[0]]
                        ys = [p.y() for p in polygons[0]]
                        if tail == "left":
                            self.assertAlmostEqual(min(xs), 0.5)
                        elif tail == "right":
                            self.assertAlmostEqual(max(xs), width - 0.5)
                        elif tail == "top":
                            self.assertAlmostEqual(min(ys), 0.5)
                        else:
                            self.assertAlmostEqual(max(ys), height - 0.5)
        self.assertEqual(len(outline(300, 300, "", 0).toSubpathPolygons()), 1)      # no tail: the card alone

    def test_the_pixels_at_the_base_are_the_cards_colour_in_light_and_dark(self):
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QWidget

        from meridiana import assistant as core, theme_colors
        from meridiana.ui.assistant import Assistant, TAIL_HALF
        for dark in (False, True):
            tokens = theme_colors.derive(theme_colors.DEFAULT_SEED, dark).tokens
            area = QWidget()
            self.addCleanup(_setup.dispose, area)
            area.resize(1000, 700)
            a = Assistant(area)
            a.reduced_motion = True
            a.set_colours(tokens)
            a.set_bubble_size(320, 324)                     # a height that showed the seam with the tail on the left
            area.show()
            self.app.processEvents()
            panel = QColor(tokens["panel"])
            for name, (x, y) in {"left": (12, 300), "right": (1000 - 58, 300), "top": (400, 12),
                                 "bottom": (400, 700 - 58)}.items():
                a.close_panel()
                self.app.processEvents()
                a.move(x, y)
                a.dropped()
                a.open_panel()
                self.app.processEvents()
                b, s = a.bubble, a.bubble.shape
                image = b.grab().toImage()
                dpr = image.devicePixelRatio()
                t = core.TAIL
                base_x = t if s.tail == "left" else b.width() - 1 - t
                base_y = t if s.tail == "top" else b.height() - 1 - t
                worst = 0.0
                # inside the tail's span (its slanted edges are antialiased 3 px from the ends), one pixel out of
                # the card and two in
                for k in range(int(-(TAIL_HALF - 4) * dpr), int((TAIL_HALF - 4) * dpr) + 1):
                    for d in range(int(-1 * dpr), int(2 * dpr) + 1):
                        if s.tail in ("left", "right"):
                            px, py = round(base_x * dpr) + d, round(s.at * dpr) + k
                        else:
                            px, py = round(s.at * dpr) + k, round(base_y * dpr) + d
                        colour = image.pixelColor(px, py)
                        worst = max(worst, abs(colour.lightness() - panel.lightness()))
                self.assertLess(worst, 8, (dark, name, s.tail, s.at, worst))


if __name__ == "__main__":
    unittest.main()
