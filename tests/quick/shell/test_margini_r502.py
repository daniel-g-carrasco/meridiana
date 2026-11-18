"""R502: the margins of the phase tabs and of the bar of the tools, measured on the picture at 1, 1.5 and 2.

Daniel (06/11/2026, photos margini-linguetta.png and margini-barra-strumenti.png): the side margins of the tab as the
margin between the number's disc and the top of the tab, the hover resized with them; in the bar the same margin on
the left (before «Seleziona»), at the top and on the right. Each margin is counted in device pixels of the window's
picture, from the edge of the thing inside (its pixels at least half its colour) up to the first pixel of the edge
around it (the card's line, or the end of the hover's ground): for the tab the disc and the name, for the bar the
ground of «Seleziona» and the summary at the right of the Plant's bar.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

CHILD = r'''
import json, os, sys, tempfile
from pathlib import Path
os.environ.setdefault('QSG_RENDER_LOOP', 'basic')
import _setup
from PySide6.QtCore import QEvent, QPointF, Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlComponent
from meridiana import i18n, jobs
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import item, mouse, pump
from quick.parity.differential import connected_fixture

app = _setup.qt_or_skip()
create_app()
i18n.setup('it')
project = connected_fixture()
results, keys, _laid = jobs.layout_of(project)
folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
host = QuickWindow(project, Path(folder.name), real_views=True, theme={'theme': 'light'})
host.bridge.accept_layout(host.bridge.session.generation, results, keys)
win = host.window
win.resize(1600, 960)
win.show()
out = {}
NAMES = ('panel', 'window', 'accent', 'text', 'press', 'hover', 'field', 'line_soft')
try:
    component = QQmlComponent(host.engine)
    component.setData(('import QtQuick\nimport Meridiana.Theme\nQtObject { '
                       + '; '.join(f'property color {n}: Theme.colors.{n}' for n in NAMES) + ' }').encode(),
                      QUrl('file:///r502.qml'))
    colours = component.create()
    raw = {k: QColor(colours.property(k)) for k in NAMES}

    def over(colour, ground):
        a = colour.alphaF()
        return tuple(round(getattr(colour, k)() * a + getattr(ground, k)() * (1 - a)) for k in ('red', 'green', 'blue'))

    c = {k: over(v, raw['panel']) for k, v in raw.items()}       # the hover and the press are veils on the card
    host.shell.trigger('phase_plant')
    pump(1500)
    dpr = win.devicePixelRatio()
    shot = os.environ.get('R502_SHOT')
    image = None

    def grab():
        global image
        image = win.grabWindow()
        out.setdefault('size', [image.width(), image.height(), win.width(), win.height(), dpr])

    def rgb(x, y):
        p = image.pixelColor(int(x), int(y))
        return p.red(), p.green(), p.blue()

    def dist(a, b):
        return sum((p - q) ** 2 for p, q in zip(a, b)) ** .5

    def near(colour, ground, x, y, share=.5):
        """The pixel at least that share of the way from the ground to the colour."""
        here = rgb(x, y)
        whole = dist(colour, ground)
        return whole > 0 and dist(here, ground) >= share * whole and dist(here, colour) <= (1 - share) * whole + 1

    def flat(ground, x, y):
        return dist(rgb(x, y), ground) <= 6         # a flat ground: a hair line differs more than that

    def rect(obj):
        p = obj.mapToScene(obj.boundingRect().topLeft())
        return p.x() * dpr, p.y() * dpr, obj.width() * dpr, obj.height() * dpr

    def box(colour, ground, r):
        xs, ys = [], []
        for y in range(int(r[1]), int(r[1] + r[3])):
            for x in range(int(r[0]), int(r[0] + r[2])):
                if near(colour, ground, x, y):
                    xs.append(x); ys.append(y)
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None

    def gap(x, y, dx, dy, ground, limit=120):
        """From a pixel of the thing inside, outwards: its soft edge and the flat ground, up to the edge around."""
        n = 1
        while n < limit and not flat(ground, x + dx * n, y + dy * n):
            n += 1                                  # the soft edge of the thing (less than half its colour)
        while n < limit and flat(ground, x + dx * n, y + dy * n):
            n += 1
        return n - 1

    def ink_gap(edge_x, step, rows, ground, limit=120):
        """From the first pixel past the ground at edge_x, back towards the name: columns without any of its ink."""
        n = 0
        while n < limit and all(flat(ground, edge_x + step * n, y) for y in rows):
            n += 1
        return n

    def visible(name):
        pending, found = [win.contentItem()], []
        while pending:
            obj = pending.pop()
            if obj.objectName() == name and obj.isVisible() and obj.width() > 0:
                p = obj.parentItem()
                while p is not None and p.isVisible():
                    p = p.parentItem()
                if p is None:
                    found.append(obj)
            pending.extend(obj.childItems())
        assert len(found) == 1, (name, len(found))
        return found[0]

    def hover(pos):
        mouse(app, win, QEvent.Type.MouseMove, QPointF(pos[0] / dpr, pos[1] / dpr), Qt.MouseButton.NoButton,
              Qt.MouseButton.NoButton)
        pump(300)
        grab()

    hover((5 * dpr, (win.height() - 5) * dpr))
    # the tab of the phase open: from its disc to the outline, left and top; from the outline to its name, right
    tab = rect(item(win, 'plantTab'))
    disc = box(c['accent'], c['panel'], (tab[0], tab[1], tab[3], tab[3]))   # the disc is in the tab's first square
    cy, cx = (disc[1] + disc[3]) // 2, (disc[0] + disc[2]) // 2
    out['tab_left'] = gap(disc[0], cy, -1, 0, c['panel'])
    out['tab_top'] = gap(cx, disc[1], 0, -1, c['panel'])
    x = int(tab[0] + tab[2] + 2 * dpr)
    while flat(c['panel'], x, cy) or flat(c['window'], x, cy):
        x -= 1                                      # the window's ground outside the tab
    while not flat(c['panel'], x, cy):
        x -= 1                                      # the outline on the right
    band = range(int(cy - 4 * dpr), int(cy + 4 * dpr) + 1)     # the name's middle, clear of the outline's corners
    out['tab_right'] = ink_gap(x, -1, band, c['panel'])
    # a tab under the pointer: its hover's ground around the disc and the name
    other = rect(item(win, 'productionTab'))
    hover((other[0] + other[2] / 2, other[1] + other[3] / 2))
    veil = over(raw['hover'], raw['window'])
    # the disc from its item: its grey is near the hover's, as the soft corners of the hover's ground
    row = next(k for k in item(win, 'productionTab').childItems() if k.childItems() and k.width() < other[2] / dpr)
    d = rect(row.childItems()[0])
    disc = (round(d[0]), round(d[1]), round(d[0] + d[2]) - 1, round(d[1] + d[3]) - 1)
    cy, cx = (disc[1] + disc[3]) // 2, (disc[0] + disc[2]) // 2
    out['hover_left'] = gap(disc[0], cy, -1, 0, veil)
    out['hover_top'] = gap(cx, disc[1], 0, -1, veil)
    x = int(other[0] + other[2])
    while not flat(veil, x, cy):
        x -= 1                                      # the hover's end on the right
    band = range(int(cy - 4 * dpr), int(cy + 4 * dpr) + 1)
    out['hover_right'] = ink_gap(x, -1, band, veil)
    # the bar: «Seleziona» under the pointer (its ground the press's when it is the tool in use)
    tool = rect(visible('tool_tool_select'))
    hover((tool[0] + tool[2] / 2, tool[1] + tool[3] / 2))
    ground = box(c['press'], c['panel'], tool) or box(c['hover'], c['panel'], tool)
    by, bx = (ground[1] + ground[3]) // 2, (ground[0] + ground[2]) // 2
    out['bar_left'] = gap(ground[0], by, -1, 0, c['panel'])
    out['bar_top'] = gap(bx, ground[1], 0, -1, c['panel'])
    # the summary at the right of the Plant's bar: its right side and its top
    hover((5 * dpr, (win.height() - 5) * dpr))
    summary = rect(item(win, 'plant-summary'))
    inside = box(c['field'], c['panel'], (summary[0] + summary[2] - 6 * dpr, summary[1], 8 * dpr, summary[3]))
    sy = int(summary[1] + summary[3] / 2)
    out['bar_right'] = gap(inside[2], sy, 1, 0, c['panel'])
    out['summary_top'] = gap(int(summary[0] + summary[2] / 2), inside[1], 0, -1, c['panel'])
    if shot:
        Path(shot).parent.mkdir(parents=True, exist_ok=True)
        image.copy(0, 0, int(1000 * dpr), int(140 * dpr)).save(shot)
finally:
    host.close()
    pump(50)
    folder.cleanup()
print('R502 ' + json.dumps(out))
'''


def measure(scale, shot=None):
    work = Path(tempfile.mkdtemp(prefix='meridiana-r502-'))
    # the offscreen screen is 800x800 unless told, and the window keeps inside its screen (R430)
    screen = work / 'screen.json'
    screen.write_text('{"screens": [{"name": "R502", "x": 0, "y": 0, "width": 4000, "height": 2400, '
                      '"logicalDpi": 96, "logicalBaseDpi": 96, "dpr": 1}]}', encoding='utf8')
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT / 'tests'), str(ROOT / 'src')]),
               QT_QPA_PLATFORM='offscreen:configfile=' + os.path.relpath(screen, ROOT).replace(os.sep, '/'),
               QSG_RENDER_LOOP='basic', QT_SCALE_FACTOR=str(scale), PYTHONUTF8='1',
               APPDATA=str(work / 'APPDATA'), LOCALAPPDATA=str(work / 'LOCALAPPDATA'))
    if shot:
        env['R502_SHOT'] = str(shot)
    try:
        done = subprocess.run([sys.executable, '-c', CHILD], cwd=ROOT, env=env, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=240)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    lines = [line for line in done.stdout.splitlines() if line.startswith('R502 ')]
    if not lines:
        raise AssertionError(done.stderr[-3000:])
    return json.loads(lines[-1][5:])


class SymmetricMargins(unittest.TestCase):
    def test_tab_and_bar_margins_are_one_at_every_scale(self):
        for scale in (1, 1.5, 2):
            m = measure(scale)
            with self.subTest(scale=scale, margins=m):
                # the tab open: left and right as the top, in device pixels, within one
                self.assertLessEqual(abs(m['tab_left'] - m['tab_top']), 1, m)
                self.assertLessEqual(abs(m['tab_right'] - m['tab_top']), 1, m)
                # a tab under the pointer: its hover as far from the disc on the left as at the top, and from the name
                self.assertLessEqual(abs(m['hover_left'] - m['hover_top']), 1, m)
                self.assertLessEqual(abs(m['hover_right'] - m['hover_top']), 1, m)
                # the bar: «Seleziona» as far from the card's left side as from its top, the summary from its right
                self.assertLessEqual(abs(m['bar_left'] - m['bar_top']), 1, m)
                self.assertLessEqual(abs(m['bar_right'] - m['bar_top']), 1, m)
                self.assertLessEqual(abs(m['summary_top'] - m['bar_top']), 1, m)
                # and the bar's margin is the tab's (one value, ControlMetrics.inset)
                self.assertLessEqual(abs(m['bar_top'] - m['tab_top']), 1, m)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'shot':
        for s in (1, 1.5, 2):
            print(s, measure(s, Path(sys.argv[2]) / f'R502-margini-{sys.argv[3]}-s{s}.png'))
    else:
        unittest.main()
