"""Images under the drawing (underlay.py, R21): where their pixels go on the plan, in scale with two points and
the true distance, moved and turned; saved with the project and read back the same; a project of before opens
without them."""

import base64
import math
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401

from meridiana import model, underlay
from meridiana.underlay import Underlay

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n not really an image").decode("ascii")


def sheet(**kw) -> Underlay:
    return Underlay(**{"id": "u1", "name": "pianta.png", "image": PNG, "width": 1000, "height": 500, "x": 10.0,
                       "y": 40.0, "scale": 0.05, **kw})


class WhereThePixelsGo(unittest.TestCase):
    def test_the_top_left_corner_is_the_point_given_and_v_goes_south(self):
        u = sheet()
        self.assertEqual(u.to_plan(0, 0), (10.0, 40.0))
        x, y = u.to_plan(1000, 500)
        self.assertAlmostEqual(x, 60.0)
        self.assertAlmostEqual(y, 15.0)

    def test_from_the_plan_and_back_with_a_rotation(self):
        u = sheet(rotation=33.0, scale=0.02)
        for pixel in ((0, 0), (123.5, 77.25), (1000, 500)):
            back = u.from_plan(*u.to_plan(*pixel))
            self.assertAlmostEqual(back[0], pixel[0])
            self.assertAlmostEqual(back[1], pixel[1])
        a, b = u.to_plan(0, 0), u.to_plan(100, 0)
        self.assertAlmostEqual(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])), 33.0)

    def test_placed_new_it_is_as_wide_as_asked_and_centred(self):
        u = underlay.placed("u3", "f.jpg", PNG, 2000, 1000, (5.0, -3.0), 40.0)
        self.assertAlmostEqual(u.scale, 0.02)
        cx, cy = u.centre()
        self.assertAlmostEqual(cx, 5.0)
        self.assertAlmostEqual(cy, -3.0)

    def test_a_large_image_is_kept_with_its_longer_side_at_the_limit(self):
        self.assertEqual(underlay.fitted_size(8192, 2048), (4096, 1024))
        self.assertEqual(underlay.fitted_size(800, 600), (800, 600))


class InScale(unittest.TestCase):
    def test_two_points_and_the_true_distance_give_the_scale(self):
        u = sheet()
        a, b = u.to_plan(200, 300), u.to_plan(300, 300)          # 100 px apart: 5 m as it lies now
        self.assertAlmostEqual(math.dist(a, b), 5.0)
        v = u.scaled(a, b, 7.5)
        self.assertAlmostEqual(v.scale, 0.075)
        self.assertAlmostEqual(math.dist(v.to_plan(200, 300), v.to_plan(300, 300)), 7.5)
        pa = v.to_plan(200, 300)                                   # the first point stays where it was
        self.assertAlmostEqual(pa[0], a[0])
        self.assertAlmostEqual(pa[1], a[1])
        self.assertEqual(u.scale, 0.05)                            # the old one as it was, for the undo

    def test_in_scale_along_a_slanting_line_of_a_turned_image(self):
        u = sheet(rotation=-20.0)
        a, b = u.to_plan(100, 100), u.to_plan(400, 500)            # 500 px apart
        v = u.scaled(a, b, 12.0)
        self.assertAlmostEqual(math.dist(v.to_plan(100, 100), v.to_plan(400, 500)), 12.0)
        self.assertAlmostEqual(v.scale, 12.0 / 500)
        self.assertEqual(v.rotation, -20.0)

    def test_the_scale_error_speaks_italian(self):
        from meridiana import i18n
        before = i18n._translation
        self.addCleanup(lambda: setattr(i18n, "_translation", before))
        i18n.setup("it")
        with self.assertRaises(ValueError) as caught:
            sheet().scaled((1.0, 1.0), (1.0, 1.0), 5.0)
        self.assertEqual(str(caught.exception), "servono due punti distinti e una distanza maggiore di zero")

    def test_the_same_point_twice_or_no_distance_is_refused(self):
        u = sheet()
        with self.assertRaises(ValueError):
            u.scaled((1.0, 1.0), (1.0, 1.0), 5.0)
        with self.assertRaises(ValueError):
            u.scaled((1.0, 1.0), (2.0, 1.0), 0.0)


class MovedAndTurned(unittest.TestCase):
    def test_moved(self):
        v = sheet().moved(2.0, -1.5)
        self.assertEqual((v.x, v.y), (12.0, 38.5))

    def test_turned_about_its_centre_the_centre_stays_and_four_quarters_come_back(self):
        u = sheet()
        v = u.rotated(90.0)
        for got, want in zip(v.centre(), u.centre(), strict=True):
            self.assertAlmostEqual(got, want)
        w = v.rotated(90.0).rotated(90.0).rotated(90.0)
        self.assertAlmostEqual(w.rotation % 360.0, 0.0)
        for got, want in zip(w.to_plan(0, 0), u.to_plan(0, 0), strict=True):
            self.assertAlmostEqual(got, want)

    def test_turned_about_a_point_of_the_plan(self):
        v = sheet().rotated(180.0, about=(10.0, 40.0))
        x, y = v.to_plan(1000, 0)
        self.assertAlmostEqual(x, -40.0)
        self.assertAlmostEqual(y, 40.0)


class InTheProject(unittest.TestCase):
    def test_saved_and_reopened_the_image_is_the_same(self):
        p = model.Project()
        p.underlays.append(sheet(rotation=12.5, opacity=0.35, visible=False))
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "p.meridiana"
            p.save(f)
            q, _notice = model.Project.load(f)
        self.assertEqual(q.underlays, p.underlays)
        self.assertIsInstance(q.underlays[0], Underlay)

    def test_a_project_of_before_opens_without_images(self):
        data = model.Project().to_json()
        data["version"] = 5
        data.pop("underlays")
        q = model.Project.from_json(data)
        self.assertEqual(q.underlays, [])
        self.assertEqual(q.to_json()["version"], model.FORMAT_VERSION)

    def test_a_new_id_is_never_one_of_an_image(self):
        p = model.Project()
        p.underlays.append(sheet(id="u1"))
        self.assertEqual(p.new_id("u"), "u2")


class Imported(unittest.TestCase):
    """What read_image keeps of a file: the pixels, never the metadata (study 18, G 6.2: a photo's EXIF says where
    and when it was taken, and the project file travels)."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_exif_of_a_photo_does_not_enter_the_project(self):
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        from PySide6.QtGui import QImage

        from meridiana.ui import underlays
        image = QImage(40, 30, QImage.Format.Format_RGB32)
        image.fill(0xff8040)
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "JPG", 90)
        buffer.close()
        jpeg = bytes(data)
        exif = b"Exif\x00\x00MM\x00*\x00\x00\x00GPS here 45.5226 9.0300"
        app1 = bytes.fromhex("ffe1") + (len(exif) + 2).to_bytes(2, "big") + exif
        with_exif = jpeg[:2] + app1 + jpeg[2:]                  # the APP1 segment right after the SOI marker
        folder = Path(tempfile.mkdtemp())
        photo = folder / "tetto.jpg"
        photo.write_bytes(with_exif)
        self.assertIn(b"GPS here", photo.read_bytes())
        encoded, w, h = underlays.read_image(photo)
        kept = base64.b64decode(encoded)
        self.assertEqual((w, h), (40, 30))
        self.assertNotIn(b"Exif", kept)
        self.assertNotIn(b"GPS here", kept)
        back = QImage()
        self.assertTrue(back.loadFromData(kept))
        self.assertEqual((back.width(), back.height()), (40, 30))

    def test_the_first_page_of_a_pdf_is_read_at_200_dpi(self):
        from PySide6.QtCore import QMarginsF
        from PySide6.QtGui import QColor, QPageSize, QPainter, QPdfWriter

        from meridiana.ui import underlays
        if not underlays.pdf_available():
            self.skipTest("Qt's PDF module is not there")
        f = Path(tempfile.mkdtemp()) / "tavola.pdf"
        writer = QPdfWriter(str(f))
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setPageMargins(QMarginsF(0, 0, 0, 0))
        painter = QPainter(writer)
        painter.fillRect(100, 100, 2000, 1000, QColor("#3a6ea5"))
        writer.newPage()
        painter.end()
        data, w, h = underlays.read_image(f)
        self.assertGreater(len(data), 100)
        self.assertEqual((w, h), (round(595 * 200 / 72), round(842 * 200 / 72)))   # A4 at 200 dpi

    def test_what_is_not_an_image_is_refused_with_the_reason(self):
        from meridiana.ui import underlays
        bad = Path(tempfile.mkdtemp()) / "note.png"
        bad.write_text("not an image")
        with self.assertRaises(ValueError) as caught:
            underlays.read_image(bad)
        self.assertTrue(str(caught.exception))


if __name__ == "__main__":
    unittest.main()
