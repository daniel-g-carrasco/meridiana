"""R555 (11) (Daniel 14/11/2026, variant E of the sketches: «proviamolo»): Meridio's highlight is a hair line of the
focus' grey, as far from the element on its four sides and concentric to its corners, that arrives once at every new
target and settles on the line; with less motion it is there at once. Measured on the drawn image of the real window,
in device pixels, at scale 1 and 2, in both themes, on a phase tab, a button of the bar and a side panel: the gap is the
same on the four sides (0 apart at scale 2, at most 1 at scale 1) and the same along the corner's diagonal. Before:
the tab's top 1,5 px over the tab, the margin twice as wide on the curve (fixed radius 8)."""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _setup

ROOT = Path(__file__).resolve().parents[3]
TARGETS = ('modelTab', 'tool_tool_move', 'leftPanel')
SCALES = ('1', '2')
SIDE_LIMIT = {'1': 1.0, '2': 0.25}     # device px between two sides: 0 at scale 2 (the measure resolves a quarter)
CURVE_LIMIT = 0.5                      # device px between the gap on the corner's diagonal and on the sides
CONTRAST = 3.0


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c.red()) + 0.7152 * ch(c.green()) + 0.0722 * ch(c.blue())


def contrast(a, b):
    high, low = sorted((lum(a), lum(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def change(a, b):
    return max(abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue()))


def stroke(samples, line):
    """samples: (distance from the element's edge, change, colour, colour before). The first line met: its centre
    weighted by the change, less half its width, is the gap; with the contrast of its strongest pixel."""
    peak = max((s[1] for s in samples), default=0)
    if peak < 10:
        return None
    first = next(i for i, s in enumerate(samples) if s[1] >= peak / 2)
    lo, hi = first, first
    while lo > 0 and samples[lo - 1][1] >= peak * 0.1:
        lo -= 1
    while hi + 1 < len(samples) and samples[hi + 1][1] >= peak * 0.1:
        hi += 1
    run = samples[lo:hi + 1]
    centre = sum(t * v for t, v, _a, _b in run) / sum(v for _t, v, _a, _b in run)
    best = max(run, key=lambda s: s[1])
    return centre - line / 2, contrast(best[2], best[3])


def measure():
    """Run in a process with QT_SCALE_FACTOR set: the gaps, the corners and the arrival, as JSON."""
    from PySide6.QtCore import QPointF
    from meridiana import i18n
    from meridiana.app import jobs
    from meridiana.gui.application import QuickWindow, create_app
    from quick.aiuti.differential import connected_fixture
    from quick.gestures import item, pump
    app = _setup.qt_or_skip()
    create_app()
    i18n.setup('en')
    project = connected_fixture()
    results, keys, _laid = jobs.layout_of(project)
    folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    host = QuickWindow(project, Path(folder.name), real_views=True, theme={'theme': 'light'})
    host.bridge.accept_layout(host.bridge.session.generation, results, keys)
    win = host.window
    win.resize(1200, 800)
    win.show()
    host.shell.trigger('phase_model')
    pump(800)
    layer, spot = item(win, 'assistantLayer'), item(win, 'assistantSpotlight')
    # measured where it is drawn: Meridio's layer is on the window's root, above the bars (R612)

    def item(window, name):
        """The item shown with that name: the bar keeps a row of tools for every phase, the others hidden."""
        stack = [window.contentItem()]
        while stack:
            node = stack.pop()
            if node.objectName() == name and node.isVisible() and node.width() > 0:
                return node
            stack.extend(node.childItems())
        return None

    def sample(img, before, x, y):
        ix, iy = int(math.floor(x)), int(math.floor(y))
        if not (0 <= ix < img.width() and 0 <= iy < img.height()):
            return None
        a, b = img.pixelColor(ix, iy), before.pixelColor(ix, iy)
        return change(a, b), a, b

    def shown(target):
        spot.setProperty('active', False)
        _setup.wait_until(app, lambda: spot.property('opacity') == 0, 5)
        layer.setProperty('highlightItem', None)
        pump(50)
        before = win.grabWindow()
        layer.setProperty('highlightItem', target)
        spot.setProperty('active', True)
        _setup.wait_until(app, lambda: spot.property('progress') == 1 and spot.property('opacity') == 1, 5)
        pump(50)
        return before, win.grabWindow()

    out = {}
    for theme in ('light', 'dark'):
        host.theme.configure({'theme': theme})
        pump(200)
        for name in TARGETS:
            target = item(win, name)
            before, after = shown(target)
            s = after.width() / win.width()      # device pixels per logical one (the grab's ratio may say 1)
            p = target.mapToItem(layer, QPointF(0, 0))
            x0, y0, x1, y1 = p.x() * s, p.y() * s, (p.x() + target.width()) * s, (p.y() + target.height()) * s
            line = float(spot.property('line')) * s
            sides = {}
            for side, (edge, step) in dict(left=((x0, (y0 + y1) / 2), (-1, 0)), right=((x1, (y0 + y1) / 2), (1, 0)),
                                           top=(((x0 + x1) / 2, y0), (0, -1)), bottom=(((x0 + x1) / 2, y1), (0, 1))).items():
                got = [(i + 0.5, *g) for i in range(-4, 40)
                       for g in [sample(after, before, edge[0] + step[0] * (i + 0.5), edge[1] + step[1] * (i + 0.5))] if g]
                sides[side] = stroke(got, line)
            value = spot.property('radii')
            radii = [float(r) for r in (value.toVariant() if hasattr(value, 'toVariant') else value)]
            curve = []
            for (cx, cy), (dx, dy), r in zip(((x0, y0), (x1, y0), (x1, y1), (x0, y1)),
                                             ((-1, -1), (1, -1), (1, 1), (-1, 1)), radii, strict=True):
                k = r * s * (1 - 1 / math.sqrt(2))
                px, py = cx - dx * k, cy - dy * k            # the element's arc on the diagonal
                got = [(t, *g) for i in range(-8, 160) for t in [i * 0.25]
                       for g in [sample(after, before, px + dx * t / math.sqrt(2), py + dy * t / math.sqrt(2))] if g]
                found = stroke(got, line)
                curve.append(found[0] if found else None)
            out[f'{theme} {name}'] = dict(sides=sides, curve=curve, gap=float(spot.property('gap')) * s, radii=radii)
    # the arrival: from the line farther out to the line, once at every new target, the step before too
    host.theme.configure({'theme': 'light', 'reducedMotion': False})
    pump(100)
    tab, panel = item(win, 'modelTab'), item(win, 'leftPanel')
    arrival = []
    for target in (tab, panel, tab):
        layer.setProperty('highlightItem', target)
        started = float(spot.property('progress'))      # read at once: the arrival starts from the far line
        _setup.wait_until(app, lambda: spot.property('progress') == 1, 5)
        arrival.append(dict(started=started, outset=float(spot.property('outset')), gap=float(spot.property('gap')),
                            line=float(spot.property('line'))))
    out['arrival'] = arrival
    # the same target again (it only moves): no arrival
    layer.setProperty('highlightItem', tab)
    pump(16)
    out['same'] = float(spot.property('progress'))
    host.theme.configure({'reducedMotion': True})
    pump(100)
    layer.setProperty('highlightItem', panel)
    out['reduced'] = float(spot.property('progress'))
    host.close()
    folder.cleanup()
    print(json.dumps(out))


def setUpModule():
    _setup.keep_global_state()


class TheHighlightOfMeridio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.found = {}
        for scale in SCALES:
            # a screen as large as the window at that scale (offscreen is 800 x 800); the platform's options are split
            # on ':', so on Windows the file is named relative to the repository, without its drive letter
            screen = Path(tempfile.mkdtemp()) / 'screen.json'
            side = int(1400 * float(scale)), int(1000 * float(scale))
            screen.write_text(json.dumps(dict(screens=[dict(name='test', x=0, y=0, width=side[0], height=side[1],
                                                                logicalDpi=96, logicalBpi=96, dpr=1)])), encoding='utf-8')
            try:
                config = os.path.relpath(screen, ROOT).replace('\\', '/')
            except ValueError:          # another drive: no relative path
                config = str(screen)
            env = dict(os.environ, QT_SCALE_FACTOR=scale, QT_QPA_PLATFORM=f'offscreen:configfile={config}',
                       QSG_RENDER_LOOP='basic')
            try:
                run = subprocess.run([sys.executable, __file__, '--measure'], env=env, capture_output=True, text=True,
                                     timeout=300, cwd=ROOT)
            finally:
                screen.unlink(missing_ok=True)
                screen.parent.rmdir()
            line = [x for x in run.stdout.splitlines() if x.startswith('{')]
            assert line, run.stderr[-3000:]
            cls.found[scale] = json.loads(line[-1])

    def cases(self):
        for scale, found in self.found.items():
            for where, m in found.items():
                if where in ('arrival', 'same', 'reduced'):
                    continue
                yield scale, where, m

    def test_the_gap_is_the_same_on_the_four_sides(self):
        for scale, where, m in self.cases():
            sides = m['sides']
            for side, got in sides.items():
                self.assertIsNotNone(got, f'scale {scale} {where}: no line on the {side}')
            gaps = {k: v[0] for k, v in sides.items()}
            spread = max(gaps.values()) - min(gaps.values())
            self.assertLessEqual(spread, SIDE_LIMIT[scale], f'scale {scale} {where}: gaps {gaps}')
            self.assertLessEqual(abs(gaps['left'] - m['gap']), SIDE_LIMIT[scale], f'scale {scale} {where}: {gaps}, gap {m["gap"]}')

    def test_the_margin_is_the_same_along_the_curve(self):
        for scale, where, m in self.cases():
            side = sum(v[0] for v in m['sides'].values()) / 4
            for corner, radius in zip(m['curve'], m['radii'], strict=True):
                if radius <= 0:
                    continue        # a square corner (the tab's bottom): the line turns round it, at the gap from it
                self.assertIsNotNone(corner, f'scale {scale} {where}: no line on a corner')
                self.assertLessEqual(abs(corner - side), CURVE_LIMIT,
                                     f'scale {scale} {where}: {corner:.2f} on the curve, {side:.2f} on the sides')

    def test_the_line_stands_out_from_its_ground(self):
        for scale, where, m in self.cases():
            for side, (_gap, ratio) in m['sides'].items():
                self.assertGreaterEqual(ratio, CONTRAST, f'scale {scale} {where} {side}: {ratio:.2f}')

    def test_the_tab_without_room_above_has_a_smaller_gap_on_all_four_sides(self):
        for scale, found in self.found.items():
            tab, panel = found['light modelTab'], found['light leftPanel']
            self.assertLess(tab['gap'], panel['gap'], scale)
            self.assertGreater(tab['gap'], 0, scale)
            self.assertEqual(tab['radii'][2:], [0, 0], scale)

    def test_the_line_arrives_at_every_new_target_and_settles_on_the_line(self):
        for scale, found in self.found.items():
            for step in found['arrival']:
                self.assertEqual(step['started'], 0, f'scale {scale}: the line did not arrive again')
                self.assertAlmostEqual(step['outset'], step['gap'] + step['line'], 3, scale)
            self.assertEqual(found['same'], 1, f'scale {scale}: the same target arrived again')
            self.assertEqual(found['reduced'], 1, f'scale {scale}: with less motion the line is not still at once')


if __name__ == '__main__':
    if '--measure' in sys.argv:
        measure()
    else:
        unittest.main()
