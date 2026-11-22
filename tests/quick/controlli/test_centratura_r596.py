"""R596 (Daniel 13/11/2026: «il ? non mi sembra perfettamente centrato nel disco»): the dot of the help mark's «?» stands on
the disc's vertical axis, measured on the drawn image in device pixels at 100, 125, 150, 200 and 250 %, in both themes
and at three places of the window. The disc's centre is the centroid of what it covers, the dot's centre the centroid
of the ink of the lowest piece of the glyph; their distance stays under half a device pixel (the glyph is drawn from a
whole device pixel, so half a pixel is the least that can be promised without blurring it). Before: up to 0,88."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _setup

QML = b'''
import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M
Rectangle {
    width: 100; height: 40; color: Theme.colors.card
    M.HelpMark { objectName: "mark-a"; x: 4; y: 4 }
    M.HelpMark { objectName: "mark-b"; x: 37; y: 5 }
    M.HelpMark { objectName: "mark-c"; x: 71; y: 7 }
}
'''
SCALES = ('1', '1.25', '1.5', '2', '2.5')
MARKS = ('mark-a', 'mark-b', 'mark-c')
LIMIT = 0.5         # device pixels
ROOT = Path(__file__).resolve().parents[3]


def lum(c):
    return 0.2126 * c.red() + 0.7152 * c.green() + 0.0722 * c.blue()


def centres(image, dpr, at):
    """The disc's centre and the dot's centre in device pixels, for the mark whose zone starts at `at` (logical)."""
    x0, y0, size = int(at.x() * dpr), int(at.y() * dpr), int(20 * dpr) + 1
    ground = lum(image.pixelColor(x0 - 1, y0 - 1))
    disc = lum(image.pixelColor(int((at.x() + 4.5) * dpr), int((at.y() + 13.5) * dpr)))
    zone = [(x, y, lum(image.pixelColor(x, y))) for y in range(y0, y0 + size) for x in range(x0, x0 + size)]
    ink = (min if disc < ground else max)(v for _x, _y, v in zone if abs(v - disc) > 0)
    if abs(ink - disc) < 30:
        raise AssertionError('no «?» drawn')
    ink_w = {(x, y): min(1.0, max(0.0, (v - disc) / (ink - disc))) for x, y, v in zone}
    cover = {(x, y): 1.0 if ink_w[(x, y)] > 0.02 else min(1.0, max(0.0, (v - ground) / (disc - ground)))
             for x, y, v in zone}
    total = sum(cover.values())
    cx = sum((x + 0.5) * w for (x, _y), w in cover.items()) / total
    cy = sum((y + 0.5) * w for (_x, y), w in cover.items()) / total
    radius = (total / 3.14159265) ** 0.5
    inside = {p: w for p, w in ink_w.items() if ((p[0] + 0.5 - cx) ** 2 + (p[1] + 0.5 - cy) ** 2) ** 0.5 < radius - 1}
    rows = sorted({y for (_x, y), w in inside.items() if w > 0.15})
    row_ink = {y: sum(w for (_x, yy), w in inside.items() if yy == y) for y in range(rows[0], rows[-1] + 1)}
    peak, seen, gap = max(row_ink.values()), 0.0, None
    for y in range(rows[-1], rows[0], -1):        # from the bottom: the dot, then the gap above it
        if row_ink[y] > 0.2 * peak:
            seen = max(seen, row_ink[y])
        elif seen and row_ink[y] < 0.35 * seen:
            gap = y
            break
    if gap is None:
        raise AssertionError('the dot is not apart from the hook')
    dot = {p: w for p, w in inside.items() if p[1] > gap}
    return cx, sum((x + 0.5) * w for (x, _y), w in dot.items()) / sum(dot.values())


def measure():
    """Run in a process with QT_SCALE_FACTOR set: the dot's distance from the disc's axis of each mark, as JSON."""
    from PySide6.QtCore import QPointF, QUrl
    from PySide6.QtQuick import QQuickItem, QQuickView
    from meridiana.gui.backend.controls import install_controls
    from quick.gestures import pump
    _setup.qt_or_skip()
    file = tempfile.NamedTemporaryFile('wb', suffix='.qml', delete=False)
    file.write(QML)
    file.close()
    out = {}
    for theme in ('light', 'dark'):
        view = QQuickView()
        install_controls(view.engine(), dict(theme=theme, reducedMotion=True))
        view.setSource(QUrl.fromLocalFile(file.name))
        view.show()
        pump(300)
        image = view.grabWindow()
        dpr = image.width() / view.width()
        root = view.rootObject()
        for name in MARKS:
            mark = root.findChild(QQuickItem, name)
            disc, dot = centres(image, dpr, mark.mapToScene(QPointF(0, 0)))
            out[f'{theme} {name}'] = dot - disc
        view.close()
    print(json.dumps(out))
    os.unlink(file.name)


def setUpModule():
    _setup.keep_global_state()


class TheDotOnTheAxis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.found = {}
        for scale in SCALES:
            env = dict(os.environ, QT_SCALE_FACTOR=scale, QT_QPA_PLATFORM='offscreen', QSG_RENDER_LOOP='basic')
            run = subprocess.run([sys.executable, __file__, '--measure'], env=env, capture_output=True, text=True,
                                 timeout=120, cwd=ROOT)
            line = [x for x in run.stdout.splitlines() if x.startswith('{')]
            assert line, run.stderr[-2000:]
            cls.found[scale] = json.loads(line[-1])

    def test_the_dot_is_within_half_a_device_pixel_of_the_disc_axis(self):
        for scale, found in self.found.items():
            self.assertEqual(len(found), 2 * len(MARKS), scale)
            for where, offset in found.items():
                self.assertLess(abs(offset), LIMIT, f'{scale} {where}: the dot is {offset:+.2f} device px off the axis')


if __name__ == '__main__':
    if '--measure' in sys.argv:
        measure()
    else:
        unittest.main()
