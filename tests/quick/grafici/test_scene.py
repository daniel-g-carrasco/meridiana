"""Chart geometry and paper export, including negative and missing values."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from meridiana.quick.backend import charts_scene as scene


class SceneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_negative_stacks_and_exact_readout_data_are_preserved(self):
        data = dict(kind="bars", categories=["A", "B"], series=[["one", [5, -2]], ["two", [3, -4]]],
                    stacked=True, unit="kWh")
        p = scene.prepare(data)
        self.assertLessEqual(p["ymin"], -6)
        self.assertGreaterEqual(p["ymax"], 8)
        self.assertEqual([r["value"] for s in p["layers"] for r in s["rects"]], [5, -2, 3, -4])
        self.assertEqual(len(p["layers"]), 2)

    def test_line_gaps_do_not_join_and_negative_cash_has_zero(self):
        p = scene.prepare(dict(kind="line", xs=[0, 1, 2, 3], series=[["cash", [-100, None, 20, 40]]],
                               area=True, mark_zero=True))
        self.assertLess(p["ymin"], 0)
        self.assertGreater(p["ymax"], 40)
        self.assertEqual([len(path) for path in p["layers"][0]["paths"]], [1, 2])

    def test_heatmap_orientation_and_missing_cells(self):
        p = scene.prepare(dict(kind="heatmap", matrix=[[1, None], [2, 3]], rows=["Jan", "Feb"], cols=["0", "1"]))
        self.assertEqual((p["columns"], p["rows"]), (2, 2))
        image = QImage.fromData(scene.image_bytes(p["image"]))
        self.assertEqual(image.pixelColor(1, 0).alpha(), 0)
        self.assertNotEqual(image.pixelColor(0, 0), image.pixelColor(1, 1))

    def test_export_light_svg_and_png_include_title_and_real_geometry(self):
        data = dict(kind="bars", title="Test energy", categories=["Jan", "Feb"],
                    series=[["Energy", [10, 20]]], unit="kWh", source="recorded weather")
        with tempfile.TemporaryDirectory() as tmp:
            for kind in ("svg", "png"):
                path = Path(tmp) / ("result." + kind)
                scene.export_chart(data, path, family="Arial")
                self.assertGreater(path.stat().st_size, 1000)
                if kind == "png":
                    image = QImage(str(path))
                    self.assertGreater(image.pixelColor(0, 0).lightness(), 240)
                else:
                    self.assertIn("Test energy", path.read_text(encoding="utf-8"))

    def test_zoom_export_remaps_ticks_and_clips_lines_markers_and_hidden_series(self):
        from meridiana.quick.backend.charts_bridge import ChartServices
        from PySide6.QtCore import QUrl

        data = dict(kind="line", title="Zoomed year", xs=list(range(101)),
                    series=[["Visible", list(range(101))], ["Hidden", [70] * 101]],
                    markers=True, area=False, unit="kW", xlabel="hour",
                    ticks=[(0, "outside-left"), (50, "inside"), (100, "outside-right")],
                    mark=[10, "outside-mark"])
        service = ChartServices()
        with tempfile.TemporaryDirectory() as tmp:
            for kind in ("png", "svg"):
                with self.subTest(kind=kind):
                    path = Path(tmp) / ("zoom." + kind)
                    self.assertTrue(service.exportChart(data, QUrl.fromLocalFile(str(path)), "Arial", ["Hidden"], .4, .6))
                    image = self.export_image(path)
                    # Full y range stays 0..106. The quarter points now represent x=45/55, not 25/75.
                    for px, py in ((446, 509), (1174, 442)):
                        self.assertTrue(any(image.pixelColor(x, y).name() == scene.SERIES[False][0]
                                            for x in range(px-2, px+3) for y in range(py-3, py+4)))
                    blue = self.colored_pixels(image, scene.SERIES[False][0])
                    self.assertTrue(blue)
                    self.assertGreaterEqual(min(x for x, _ in blue), 82)
                    self.assertLessEqual(max(x for x, _ in blue), 1538)
                    self.assertFalse(self.colored_pixels(image, "#eb6834"))
                    if kind == "svg":
                        text = path.read_text(encoding="utf-8")
                        self.assertIn("inside", text)
                        for label in ("outside-left", "outside-right", "outside-mark", "Hidden"):
                            self.assertNotIn(label, text)

    def test_zoom_export_clips_area_at_both_plot_edges(self):
        data = dict(kind="line", xs=list(range(101)), series=[["Energy", [50] * 101]],
                    area=True, markers=True, mark_zero=True, unit="kW")
        with tempfile.TemporaryDirectory() as tmp:
            for kind in ("png", "svg"):
                with self.subTest(kind=kind):
                    path = Path(tmp) / ("area." + kind)
                    scene.export_chart(data, path, family="Arial", view_start=.4, view_end=.6)
                    image = self.export_image(path)
                    # The light blue area reaches both crop edges, but never paints the axis labels.
                    surface = QColor(scene.palette(False)["surface"])
                    inside = image.pixelColor(90, 700)
                    self.assertNotEqual(inside, surface)
                    self.assertEqual(image.pixelColor(75, 700), surface)
                    self.assertEqual(image.pixelColor(1545, 700), surface)

    def test_distinct_formulas_do_not_register_the_fonts_again(self):
        from matplotlib import font_manager
        from meridiana.quick.backend.charts_bridge import _formula

        first = _formula(r"E=P\cdot t", "#121212", "IBM Plex Sans", 11, 1)
        count = len(font_manager.fontManager.ttflist)
        second = _formula(r"Q=I^2\cdot R\cdot t", "#121212", "IBM Plex Sans", 11, 1)
        self.assertEqual(len(font_manager.fontManager.ttflist), count)
        for url in (first, second):
            self.assertFalse(QImage.fromData(scene.image_bytes(url)).isNull())

    @staticmethod
    def export_image(path):
        if path.suffix == ".png":
            return QImage(str(path))
        image = QImage(1600, 900, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor("white"))
        painter = QPainter(image)
        QSvgRenderer(str(path)).render(painter, QRectF(0, 0, 1600, 900))
        painter.end()
        return image

    @staticmethod
    def colored_pixels(image, color):
        pixels = np.asarray(image.bits()).reshape(image.height(), image.bytesPerLine())[:, :image.width()*4]
        pixels = pixels.reshape(image.height(), image.width(), 4)
        c = QColor(color)
        # Exclude the legend above the plot. QImage's ARGB32 bytes are BGRA on this platform.
        mask = np.all(pixels[90:820, :, :3] == [c.blue(), c.green(), c.red()], axis=2)
        ys, xs = np.nonzero(mask)
        return list(zip(xs.tolist(), (ys+90).tolist(), strict=True))



if __name__ == "__main__":
    unittest.main()
