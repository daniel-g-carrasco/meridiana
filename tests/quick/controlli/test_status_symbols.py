"""R464: the status symbols of Verifiche and of the project tree are sharp at every scale of the screen."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# The child draws the check marks of the Checks page and of the tree at three placements (on the pixel, half a pixel
# off, a third off) and gives for each the mean difference, in levels of 255, from the symbol drawn by symbols.paint
# at the exact physical size: the drawing of the Widgets.
CHILD = r'''
import json, os, sys, tempfile, time
from PySide6.QtCore import QRectF, Qt, QUrl
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickView
from meridiana.quick.backend.checks import ChecksBackend
from meridiana.quick.backend.controls import install_controls
from meridiana.ui import symbols

app = QApplication(sys.argv)
scale = float(os.environ['QT_SCALE_FACTOR'])
view = QQuickView()
install_controls(view.engine(), dict(theme='light', reducedMotion=True))
view.engine().rootContext().setContextProperty('marks', ChecksBackend.symbols.fget(None))
offsets = (0.0, 0.5, 1 / 3)
body = ['import QtQuick', 'import Meridiana.Controls', 'Rectangle { width: 300; height: 120; color: "white"']
for i, off in enumerate(offsets):
    body.append(f'CheckMark {{ symbols: marks; level: "warn"; x: {20 + 40 * i + off}; y: {20 + off}; width: 16; height: 16 }}')
body.append('}')
f = tempfile.NamedTemporaryFile('w', suffix='.qml', delete=False, encoding='utf-8')
f.write('\n'.join(body))
f.close()
view.setSource(QUrl.fromLocalFile(f.name))
view.show()
end = time.time() + 1.5
while time.time() < end:
    app.processEvents()
grab = view.grabWindow()
side = round(16 * scale)
ref = QImage(side, side, QImage.Format.Format_ARGB32)
ref.fill(Qt.GlobalColor.white)
p = QPainter(ref)
p.setRenderHint(QPainter.RenderHint.Antialiasing)
symbols.paint(p, QRectF(0, 0, side, side), 'warning', dark=False)
p.end()

def off_by(x0, y0):
    best = None
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            total = 0
            for y in range(side):
                for x in range(side):
                    a, b = grab.pixelColor(x0 + dx + x, y0 + dy + y), ref.pixelColor(x, y)
                    total += abs(a.red() - b.red()) + abs(a.green() - b.green()) + abs(a.blue() - b.blue())
            best = total / (side * side * 3) if best is None else min(best, total / (side * side * 3))
    return best

print(json.dumps([off_by(int((20 + 40 * i + off) * scale), int((20 + off) * scale)) for i, off in enumerate(offsets)]))
'''


class SharpSymbolsTest(unittest.TestCase):
    def test_check_marks_match_the_exact_drawing_at_150_and_200_percent(self):
        for scale in ('1.5', '2'):
            env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT / 'tests'), str(ROOT / 'src')]),
                       QT_QPA_PLATFORM='offscreen', QSG_RENDER_LOOP='basic', QT_SCALE_FACTOR=scale, PYTHONUTF8='1')
            done = subprocess.run([sys.executable, '-c', CHILD], cwd=ROOT, env=env, capture_output=True, text=True,
                                  encoding='utf-8', errors='replace', timeout=120)
            lines = [line for line in done.stdout.splitlines() if line.startswith('[')]
            self.assertTrue(lines, done.stderr[-2000:])
            # On r17-unita (a data-URL SVG scaled by the scene graph): 9.5 to 13.7 at 150 %, about 10 at 200 %.
            for off, value in zip(('0', '1/2', '1/3'), json.loads(lines[-1]), strict=True):
                self.assertLess(value, 1.0, f'scale {scale}, placed {off} of a pixel off')
