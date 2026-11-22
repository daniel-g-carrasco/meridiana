"""R704 (Daniel 17/11/2026: «la barra di scorrimento non è perfettamente centrata nel suo spazio. Può essere? O effetto
ottico?»). Not an illusion: in a card's margin the bar is as wide as the margin (12), but the card's own line takes its
last pixel, and the thumb was centred on the 12 instead of on the 11 of air between the content and that line: at
scale 2, on Daniel's laptop, 4 logical pixels on the content's side and 3 on the line's. Now the air is the same on
both sides; and, Daniel: «non era meglio ampliare l'aria di 1 px?», the card's margin is 12 of air plus its line
(ControlMetrics.cardMargin 13), so the 4 and 6 wide thumbs are centred at every scale, 1 included.

Each scale in a process of its own (QT_SCALE_FACTOR is read once, when the application starts).

    python -m unittest quick.controlli.test_cursore_centrato_r704
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

TESTS = Path(__file__).resolve().parents[2]

PROBE = r'''
import json, os, sys, tempfile
sys.path[:0] = [os.environ["PROBE_SRC"], os.environ["PROBE_TESTS"]]
import _setup
from PySide6.QtCore import QObject, QPointF, QUrl
from PySide6.QtQuick import QQuickView
from meridiana.gui.backend.controls import install_controls
from quick.gestures import pump
app = _setup.qt_or_skip()
view = QQuickView()
install_controls(view.engine(), dict(theme="light", reducedMotion=True))
qml = """
import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M
Rectangle { width: 400; height: 300; color: Theme.colors.panel
  M.PanelPage { objectName: "page"; x: 12; y: 12; width: 300; height: 276
    Repeater { model: 40; Rectangle { width: parent.width; height: 20; color: Theme.colors.field } } } }"""
with tempfile.NamedTemporaryFile("wb", suffix=".qml", delete=False) as f:
    f.write(qml.encode())
view.setSource(QUrl.fromLocalFile(f.name))
view.show(); pump(300)
page = view.rootObject().findChild(QObject, "page")
bar = next(c for c in page.childItems() if "ScrollBar" in c.metaObject().className())
thumb = next(c for c in bar.childItems() if c.width() > 0)
at = thumb.mapToItem(bar, QPointF(0, 0)).x()
print(json.dumps(dict(left=at, thumb=thumb.width(), right=bar.width() - at - thumb.width(),
                      ratio=view.devicePixelRatio())))
view.close(); os.unlink(f.name)
'''


def placed(scale: str) -> dict:
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_SCALE_FACTOR=scale,
               PROBE_SRC=str(TESTS.parent / 'src'), PROBE_TESTS=str(TESTS))
    done = subprocess.run([sys.executable, '-c', PROBE], env=env, capture_output=True, text=True, timeout=120,
                          cwd=str(TESTS))
    lines = [line for line in done.stdout.splitlines() if line.startswith('{')]
    if not lines:
        raise AssertionError(done.stdout + done.stderr)
    return json.loads(lines[-1])


class ThumbCentredInTheAir(unittest.TestCase):
    HAIR = 1    # the card's line (design.Line.HAIR), inside the margin at its outer side

    def test_scale_two_the_same_air_on_both_sides(self):
        got = placed('2')
        self.assertEqual(got['ratio'], 2)
        air_content, air_line = got['left'], got['right'] - self.HAIR
        self.assertAlmostEqual(air_content, air_line, delta=.01, msg=got)

    def test_scale_one_the_same_air_on_both_sides(self):
        got = placed('1')
        self.assertEqual((got['left'], got['thumb'], got['right']), (4, 4, 5))   # 4 and 4 of air, then the line

    def test_scale_two_and_a_half_the_same_air_on_both_sides(self):
        got = placed('2.5')
        self.assertAlmostEqual(got['left'], got['right'] - self.HAIR, delta=.01, msg=got)


if __name__ == '__main__':
    unittest.main()
