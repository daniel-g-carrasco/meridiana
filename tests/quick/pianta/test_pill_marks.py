"""R515, R514: a sign inside a disc is centred on it, measured on the image drawn at the screen's scales.

R515 (Daniel 06/11/2026, a warning over an obstacle in the 3D view): «il triangolo centralo nel cerchio please, i 3
angoli equidistanti dalla circonferenza». The triangle has rounded corners: its true corners are measured on the
image, along the rays from the disc's centre through them, where the triangle's colour gives way to the disc's."""
import math
import unittest

import _setup
from PySide6.QtCore import QRectF, QSize
from PySide6.QtGui import QColor, QImage, QPainter

setUpModule = _setup.keep_global_state

PILL = QColor("#1e1c19")            # the plan's pills' ground, opaque so that coverage reads straight


def drawn(name, side, centred_in_round=None):
    """The symbol in a disc of `side` device pixels, as the views draw it (paint_pill), on white."""
    from meridiana.ui import symbols
    image = QImage(QSize(side, side), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor("white"))
    painter = QPainter(image)
    symbols.paint_pill(painter, QRectF(0, 0, side, side), name, PILL)
    painter.end()
    return image


def coverage(image, x, y, tone):
    """How much of the triangle's tone there is at (x, y), bilinear, 0 on the disc's ground and 1 on the tone."""
    x0, y0 = math.floor(x - .5), math.floor(y - .5)
    fx, fy = x - .5 - x0, y - .5 - y0
    total = 0.
    for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        c = image.pixelColor(min(image.width() - 1, max(0, x0 + dx)), min(image.height() - 1, max(0, y0 + dy)))
        span = tone.redF() - PILL.redF()
        total += w * max(0., min(1., (c.redF() - PILL.redF()) / span))
    return total


def extent(image, tone, angle):
    """How far from the disc's centre the tone reaches along the ray at `angle`: the last point where it covers half
    of a pixel, in device pixels."""
    side = image.width()
    cx = cy = side / 2
    ux, uy = math.cos(math.radians(angle)), -math.sin(math.radians(angle))
    last, previous = 0., coverage(image, cx, cy, tone)
    for k in range(1, int(side / 2 * 20)):
        r = k / 20
        now = coverage(image, cx + ux * r, cy + uy * r, tone)
        if previous >= .5 > now:
            last = r - (.5 - now) / max(1e-9, previous - now) / 20
        previous = now
    return last


def corner_gaps(image, tone):
    """The distance from each of the triangle's three true corners (rounded) to the disc's circumference, in device
    pixels: each corner the farthest the tone reaches within 15 degrees of 90, 210 and 330."""
    side = image.width()
    return [side / 2 - max(extent(image, tone, nominal + d / 2) for d in range(-30, 31))
            for nominal in (90, 210, 330)]


class Centred(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_r515_the_warning_triangle_has_its_three_corners_at_one_distance_from_the_disc(self):
        from meridiana.ui import symbols
        tone = QColor(symbols.colour("warning", True))
        for scale in (1, 1.5, 2):
            side = round(22 * scale)        # a mark on the views: a disc of 22 points (PlanSymbol, CheckMark)
            with self.subTest(scale=scale):
                gaps = corner_gaps(drawn("warning", side), tone)
                self.assertTrue(all(g > 1 for g in gaps), gaps)
                self.assertLessEqual(max(gaps) - min(gaps), .5, [round(g, 2) for g in gaps])

    def test_r515_the_signs_in_their_discs_stay_where_they_were(self):
        from meridiana.ui import symbols
        for name in symbols.NAMES:
            ground = symbols.SHAPES[name][1]
            if ground.startswith(symbols.DISC):
                self.assertEqual(symbols.enclosing_centre(name), (8., 8.), name)
        x, y = symbols.enclosing_centre("warning")
        self.assertEqual(x, 8.)
        self.assertGreater(y, 9)            # the circumcentre of a triangle with its point up: below the middle


if __name__ == "__main__":
    unittest.main()
