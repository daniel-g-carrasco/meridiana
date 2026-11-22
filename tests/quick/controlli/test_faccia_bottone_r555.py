"""R555 (Daniel 13/11/2026, Meridio: «il pulsante "Suggestions" ha la scritta che esce dai bordi»): a M.Button that brings
a face of its own (`contentItem`) is as wide as that face and its paddings, for every face. Measured on the drawn
button at 100 % and 200 %, in both themes: the last column of the word's ink stands inside the button's ground with at
least the right padding of air, as the first stands after the left one. Before: the button kept the width of its
default face (the plain word in the push button's weight), «Suggerimenti» with its chevron ran 2 px past the ground
and a face 120 px wide 90 px (at 100 %)."""
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
    width: 320; height: 90; color: Theme.colors.card
    Column {
        x: 10; y: 10; spacing: 10
        M.Button { objectName: "chevronFace"; text: "Suggerimenti"; font.pixelSize: Theme.text.caption.size
            contentItem: Row { spacing: 2
                M.Chevron { open: true; width: 14; height: 14; anchors.verticalCenter: parent.verticalCenter }
                M.Label { text: "Suggerimenti"; textStyle: "caption"; anchors.verticalCenter: parent.verticalCenter } } }
        M.Button { objectName: "wideFace"; text: "OK"
            contentItem: Item { implicitWidth: 120; implicitHeight: 20
                Rectangle { objectName: "wideInk"; width: 120; height: 10; anchors.verticalCenter: parent.verticalCenter; color: Theme.colors.text } } }
    }
}
'''
SCALES = ('1', '2')
ROOT = Path(__file__).resolve().parents[3]


def measure():
    """Run in a process with QT_SCALE_FACTOR set: per button, the air left and right of the face's ink, as JSON."""
    from PySide6.QtCore import QPointF, QUrl
    from PySide6.QtGui import QColor
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
        card = QColor(view.rootObject().property('color')).rgb()
        for name in ('chevronFace', 'wideFace'):
            button = view.rootObject().findChild(QQuickItem, name)
            at = button.mapToScene(QPointF(0, 0))
            y = int((at.y() + button.height() / 2) * dpr)
            # the ground: drawn from the button's left edge to its right one (read in a row above the face, where
            # nothing else is drawn on it); inside the card only, the window around it is another colour
            x0 = int(at.x() * dpr) + 2
            end = min(image.width(), int(view.rootObject().width() * dpr))
            field = image.pixelColor(x0, y).rgb()
            above = int((at.y() + 6) * dpr)
            right = x0
            while right + 1 < end and image.pixelColor(right + 1, above).rgb() == field:
                right += 1
            # the face's ink across the middle rows: what is neither the ground nor the card
            rows = range(int((at.y() + 7) * dpr), int((at.y() + button.height() - 6) * dpr))
            ink = [x for x in range(x0, end) for yy in rows
                   if image.pixelColor(x, yy).rgb() not in (field, card)]
            out[f'{theme} {name}'] = {'dpr': dpr, 'left_pad': button.property('leftPadding') * dpr,
                                      'right_pad': button.property('rightPadding') * dpr,
                                      'air_left': min(ink) - (x0 - 2), 'air_right': right - max(ink)}
        view.close()
    print(json.dumps(out))
    os.unlink(file.name)


def setUpModule():
    _setup.keep_global_state()


class TheFaceStaysInsideTheButton(unittest.TestCase):
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

    def test_the_face_has_its_padding_of_air_on_both_sides(self):
        for scale, found in self.found.items():
            self.assertEqual(len(found), 4, scale)
            for where, seen in found.items():
                # the ink may start a little after the padding (a glyph's own side bearing), never before it
                self.assertGreaterEqual(seen['air_left'], seen['left_pad'] - 1, f'{scale}x {where}: {seen}')
                self.assertGreaterEqual(seen['air_right'], seen['right_pad'] - 1, f'{scale}x {where}: {seen}')


if __name__ == '__main__':
    if '--measure' in sys.argv:
        measure()
    else:
        unittest.main()
