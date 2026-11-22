"""R636, seen on the laptop (Daniel 16/11/2026: «l'input del testo in meridio mantiene la barra di scorrimento sulla
destra anche se non ce n'è bisogno»): Meridio's field showed its bar with one empty line.

The cause: its heights were counted with the font's metrics (FontMetrics.height), while a written line of the text is
laid out a pixel taller with some fonts and sizes (IBM Plex at the small text here, the laptop's fonts there): the text
was a pixel taller than the field, its bar thought there was something to scroll. Now a line is as tall as the text
lays it out, and within the cap nothing scrolls and no bar shows. Checked at the scales 1, 2 and 2.5 of the screen
(each in a process of its own: Qt reads the scale once), with both text sizes that differ.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

PROBE = r'''
import json, os, sys, tempfile
w = tempfile.mkdtemp()
for n in ("APPDATA", "LOCALAPPDATA", "HOME", "USERPROFILE"):
    os.environ[n] = w
from PySide6.QtCore import QObject
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from meridiana.gui.backend.assistant import build_page
from quick.gestures import pump
app = QApplication([])
out = {}
for size in ("small", "medium"):
    engine, window, _ = build_page("meridio", options={"reducedMotion": True, "font": "plex", "textSize": size})
    QTest.qWaitForWindowExposed(window)
    pump(200)
    layer = window.findChild(QObject, "assistantLayer")
    layer.setProperty("bubbleHeight", 620)
    pump(150)
    field = layer.findChild(QObject, "assistantQuestion")
    view = next(c for c in field.childItems() if c.metaObject().className().startswith("QQuickFlickable"))
    bar = next(c for c in view.childItems() if "ScrollBar" in c.metaObject().className())
    for n in (0, 1, 3, 6, 10):
        field.setProperty("text", "\n".join("riga" for _ in range(n)))
        pump(120)
        out[f"{size}-{n}"] = [bar.isVisible(), view.property("contentHeight") > view.height() + 0.01]
    window.close()
print("RESULT " + json.dumps(out))
'''


class FieldBarTest(unittest.TestCase):
    def test_the_bar_shows_only_past_the_cap_at_every_scale(self):
        for scale in ("1", "2", "2.5"):
            env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_SCALE_FACTOR=scale,
                       PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(ROOT / "tests")]))
            done = subprocess.run([sys.executable, "-c", PROBE], env=env, capture_output=True, text=True, timeout=300)
            line = next((ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")), None)
            self.assertIsNotNone(line, done.stdout + done.stderr)
            for case, (shown, scrolls) in json.loads(line[len("RESULT "):]).items():
                past = case.endswith("-10")
                self.assertEqual(shown, past, f"scale {scale}, {case}: the bar {'hidden' if past else 'shown'}")
                self.assertEqual(scrolls, past, f"scale {scale}, {case}")


if __name__ == "__main__":
    unittest.main()
