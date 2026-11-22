"""R592: two signs, two meanings, each drawn in one place and sharp at every scale of the screen.

Daniel (11/11/2026, Consumi > Dati): «le frecce verso il basso che ci sono all'interno dei campi delle selectbox sono
tutte sfocate», and his choice: the full arrow where a value is chosen (M.Arrow: lists, buttons with a menu, the
steps of a number), the open arrow where a section opens and closes (M.Chevron, the project tree's, «ha un buono
spessore che mi piace»), grey. Measured on the drawn image at 100, 125, 150 and 200 %: the full arrow of a list and
of a number's steps has no half-covered pixel (every pixel of its box is the field or the arrow's grey), and is
symmetric; the open arrow is the tree's drawing, the same pixels in a box of 14 as in one of 20. And no QML file
outside the two components draws an arrow of its own.
"""
import json
import os
import re
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
    width: 260; height: 140; color: Theme.colors.panel
    M.ComboBox { objectName: "combo"; x: 10; y: 10; width: 200; model: ["Domestico"] }
    M.NumberField { objectName: "number"; x: 10; y: 50; width: 200; value: 3; decimals: 1 }
    Item { objectName: "wide"; x: 10; y: 90; width: 20; height: 20; M.Chevron { anchors.fill: parent; open: false } }
    Item { objectName: "small"; x: 40; y: 93; width: 14; height: 14; M.Chevron { anchors.fill: parent; open: false } }
}
'''
SCALES = ('1', '1.25', '1.5', '2')
ROOT = Path(__file__).resolve().parents[3]
QML_DIR = ROOT / 'src' / 'meridiana' / 'gui' / 'qml' / 'Meridiana'


def measure():
    """Run in a process with QT_SCALE_FACTOR set: what the arrows look like in device pixels, as JSON."""
    from PySide6.QtCore import QPointF, QUrl
    from PySide6.QtQuick import QQuickItem, QQuickView
    from meridiana.gui.backend.controls import install_controls
    from quick.gestures import pump
    _setup.qt_or_skip()
    view = QQuickView()
    install_controls(view.engine(), dict(theme='light', reducedMotion=True))
    file = tempfile.NamedTemporaryFile('wb', suffix='.qml', delete=False)
    file.write(QML)
    file.close()
    view.setSource(QUrl.fromLocalFile(file.name))
    view.show()
    pump(250)
    image = view.grabWindow()
    dpr = image.width() / view.width()
    root = view.rootObject()

    def box(name, left, top, width, height):
        item = root.findChild(QQuickItem, name)
        p = item.mapToScene(QPointF(0, 0))
        x0, y0 = int((p.x() + left) * dpr), int((p.y() + top) * dpr)
        return [[image.pixelColor(x, y).lightness() for x in range(x0, x0 + int(width * dpr))]
                for y in range(y0, y0 + int(height * dpr))]

    combo = root.findChild(QQuickItem, 'combo')
    out = {'combo': box('combo', combo.width() - 22, 4, 20, 20), 'number': box('number', 200 - 22, 4, 20, 20),
           'wide': box('wide', 0, 0, 20, 20), 'small': box('small', -3, -3, 20, 20)}
    print(json.dumps(out))
    os.unlink(file.name)


def setUpModule():
    _setup.keep_global_state()


class ArrowsSharpAndOne(unittest.TestCase):
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

    def test_the_full_arrow_has_no_half_covered_pixel_and_is_symmetric(self):
        for scale, found in self.found.items():
            for name in ('combo', 'number'):
                pixels = found[name]
                ground = pixels[0][0]
                ink = min(min(row) for row in pixels)
                self.assertLess(ink, ground - 40, f'{scale} {name}: no arrow drawn')
                blurred = [v for row in pixels for v in row if ink + 8 < v < ground - 8]
                self.assertFalse(blurred, f'{scale} {name}: {len(blurred)} half-covered pixels')
                axes = set()        # every row of ink is whole and centred on the same column
                for row in pixels:
                    cols = [x for x, v in enumerate(row) if v < ground - 8]
                    if cols:
                        self.assertEqual(len(cols), cols[-1] - cols[0] + 1, f'{scale} {name}: a row with a hole')
                        axes.add(cols[0] + cols[-1])
                self.assertLessEqual(len(axes), 2 if name == 'number' else 1, f'{scale} {name}: not symmetric {axes}')

    def test_the_open_arrow_is_the_same_drawing_in_a_small_box(self):
        def drawing(pixels):        # the pixels of the ink, cut to their bounding box
            ground = pixels[0][0]
            rows = [y for y, row in enumerate(pixels) if min(row) < ground - 8]
            cols = [x for row in pixels for x, v in enumerate(row) if v < ground - 8]
            return [row[min(cols):max(cols) + 1] for row in pixels[rows[0]:rows[-1] + 1]]
        for scale, found in self.found.items():
            self.assertEqual(drawing(found['wide']), drawing(found['small']),
                             f'{scale}: the chevron in 14 px is not the 20 px one')

    def test_no_arrow_is_drawn_outside_the_two_components(self):
        pattern = re.compile(r'control:chevron|field:(up|down|open)|"chevron-(right|down)"|PathLine \{ x: 4; y: 5\.5')
        allowed = {'Controls/Chevron.qml'}
        found = []
        for path in QML_DIR.rglob('*.qml'):
            name = path.relative_to(QML_DIR).as_posix()
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                # the calendar's months (SunBar) are commands, not arrows
                if pattern.search(line) and name not in allowed and 'calendar.turn' not in line:
                    found.append(f'{name}:{number}')
        self.assertFalse(found, found)


if __name__ == '__main__':
    if '--measure' in sys.argv:
        measure()
    else:
        unittest.main()
