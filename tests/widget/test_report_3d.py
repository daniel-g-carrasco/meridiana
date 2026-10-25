"""The 3D pictures of the report drawn for real (ui/report_3d.py): Qt Quick 3D through a QQuickRenderControl into a
texture of its own, no window on the screen. Qt's offscreen platform runs Qt Quick on its software renderer unless
QT_QUICK_BACKEND=rhi is set, and the other tests run without it (the window's 3D view among them): the pictures are
made in a process of their own with it. Where Qt Quick has no RHI even so (a machine without a graphics driver)
the process says so and the test is skipped with the reason."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _setup

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

SCRIPT = """
import sys, time
from pathlib import Path
from PySide6.QtWidgets import QApplication
app = QApplication([])
from _fixtures import capannone_rho, casa_a_falde
from meridiana import jobs
from meridiana.ui import report_3d
out = Path(sys.argv[1])
if not report_3d.available():
    print("unavailable")
    sys.exit(0)
p = capannone_rho()
p.subfields[0].filled = True
results, _keys, _laid = jobs.layout_of(p)
t = time.perf_counter()
shots = report_3d.render(p, results)
first = time.perf_counter() - t
t = time.perf_counter()
again = report_3d.render(p, results)
cached = time.perf_counter() - t
house = casa_a_falde()
t = time.perf_counter()
other = report_3d.render(house, jobs.layout_of(house)[0])
second = time.perf_counter() - t
for vid, png in shots.items():
    (out / f"{vid}.png").write_bytes(png)
print("same" if again == shots else "different", round(first, 3), round(cached, 4), round(second, 3), sorted(other))
"""


class Pictures(unittest.TestCase):
    def test_the_layout_is_drawn_from_the_south_east_and_the_south_west_on_white_with_its_modules_in_navy(self):
        from PySide6.QtGui import QImage
        _setup.qt_or_skip()
        out = Path(tempfile.mkdtemp())
        env = {**os.environ, "QT_QUICK_BACKEND": "rhi", "QT_QPA_PLATFORM": os.environ.get("QT_QPA_PLATFORM", "offscreen"),
               "PYTHONPATH": os.pathsep.join([str(_setup.ROOT / "src"), str(_setup.HERE)])}
        run = subprocess.run([sys.executable, "-c", SCRIPT, str(out)], env=env, capture_output=True, text=True,
                             timeout=240)
        self.assertEqual(run.returncode, 0, run.stderr[-2000:])
        if "No GLSL shader code found" in run.stderr and "Failed to build graphics pipeline state" in run.stderr:
            self.skipTest("Qt Quick cannot build the report's graphics pipeline here")
        words = run.stdout.split()
        if words[:1] == ["unavailable"]:
            self.skipTest("Qt Quick has no RHI here: the report leaves its 3D pictures out")
        same, first, cached, second = words[0], float(words[1]), float(words[2]), float(words[3])
        self.assertEqual(same, "same")                              # the same scene: the pictures kept
        self.assertLess(cached, 0.05)
        self.assertLess(second, max(1.0, first))                    # the renderer kept: no shaders made again
        self.assertIn("'south_east', 'south_west'", run.stdout)     # the house drawn as well
        centres = []
        for vid in ("south_east", "south_west"):
            image = QImage(str(out / f"{vid}.png"))
            self.assertEqual((image.width(), image.height()), (1100, 720))
            for x, y in ((2, 2), (image.width() - 3, 2)):          # the paper's white at the top corners
                c = image.pixelColor(x, y)
                self.assertGreater(min(c.red(), c.green(), c.blue()), 245, (vid, c.name()))
            navy, sx, sy = 0, 0, 0
            for y in range(0, image.height(), 4):
                for x in range(0, image.width(), 4):
                    c = image.pixelColor(x, y)
                    if c.blue() > c.red() + 40 and c.red() < 110:     # the modules' navy, lit
                        navy += 1
                        sx += x
                        sy += y
            self.assertGreater(navy, 0.03 * (image.width() // 4) * (image.height() // 4), vid)
            centres.append((sx / navy, sy / navy))
        self.assertGreater(abs(centres[0][0] - centres[1][0]), 30)  # two views, not the same picture twice


if __name__ == "__main__":
    unittest.main()
