"""Pictures for Meridio (R320): read, shrunk, stripped and bounded on this PC; the original never touched."""
import base64
import hashlib
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401
from meridiana.assistant import images


def _qimage(data: bytes):
    from PySide6.QtGui import QImage
    return QImage.fromData(data)


class Prepare(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def pil(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow (matplotlib's) makes the test files")
        return Image

    def test_a_large_png_is_shrunk_to_1568_its_text_dropped_and_the_file_left_as_it_was(self):
        from PySide6.QtGui import QColor, QImage
        big = QImage(3000, 2000, QImage.Format.Format_RGB32)
        big.fill(QColor("#336699"))
        big.setText("Author", "Studio Rossi, via Roma 1")
        path = self.dir / "schermata.png"
        self.assertTrue(big.save(str(path)))
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        picture = images.from_file(path)
        self.assertEqual((picture.width, picture.height), (1568, 1045))
        self.assertEqual(picture.original, (3000, 2000))
        self.assertEqual(picture.media_type, "image/png")       # a flat picture: PNG is the lighter
        self.assertNotIn(b"Studio Rossi", picture.data)
        self.assertEqual(_qimage(picture.data).textKeys(), [])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)
        self.assertEqual(base64.b64decode(picture.base64), picture.data)
        thumb = _qimage(picture.thumbnail)
        self.assertEqual(max(thumb.width(), thumb.height()), images.THUMB_SIDE)
        self.assertIn("schermata.png", picture.caption())

    def test_a_photo_loses_its_exif_and_gps_and_is_turned_as_the_camera_held_it(self):
        Image = self.pil()
        photo = Image.new("RGB", (400, 200))
        pixels = photo.load()
        for x in range(400):                                    # a gradient with noise: a photo, not a drawing
            for y in range(200):
                pixels[x, y] = ((x * 7 + y * 13) % 256, (x * y) % 256, (x * 3 + y * 5 * (x % 7)) % 256)
        exif = Image.Exif()
        exif[0x0112] = 6                                        # orientation: turned 90 degrees
        exif[0x010F] = "CameraMakerSecret"
        exif[0x8825] = {1: "N", 2: (45.0, 30.0, 0.0)}           # GPS
        path = self.dir / "foto.jpg"
        photo.save(path, "JPEG", exif=exif.tobytes(), quality=95)
        self.assertIn(b"CameraMakerSecret", path.read_bytes())
        picture = images.from_file(path)
        self.assertEqual((picture.width, picture.height), (200, 400))
        self.assertNotIn(b"CameraMakerSecret", picture.data)
        self.assertNotIn(b"Exif", picture.data)
        self.assertEqual(picture.media_type, "image/jpeg")      # a photo: JPEG is the lighter

    def test_gif_gives_its_first_frame_and_webp_is_read(self):
        Image = self.pil()
        frames = [Image.new("RGB", (60, 40), colour) for colour in ((255, 0, 0), (0, 0, 255))]
        gif = self.dir / "anim.gif"
        frames[0].save(gif, save_all=True, append_images=frames[1:], duration=100, loop=0)
        picture = images.from_file(gif)
        first = _qimage(picture.data).pixelColor(30, 20)
        self.assertGreater(first.red(), 200)
        self.assertLess(first.blue(), 50)
        webp = self.dir / "img.webp"
        Image.new("RGB", (80, 50), (0, 200, 0)).save(webp, "WEBP")
        picture = images.from_file(webp)
        self.assertEqual((picture.width, picture.height), (80, 50))
        self.assertIn(picture.media_type, ("image/png", "image/jpeg"))

    def test_never_more_than_the_limit_once_in_base64(self):
        import random
        from PySide6.QtGui import QImage
        rng = random.Random(4)
        noise = QImage(1568, 1568, QImage.Format.Format_RGB32)
        for y in range(0, 1568, 2):                             # noise does not compress
            for x in range(0, 1568, 2):
                noise.setPixel(x, y, rng.getrandbits(24))
        picture = images.prepare(noise, "rumore.png")
        self.assertLessEqual(images.sent_size(len(picture.data)), images.MAX_SENT)
        small = images.prepare(noise, "rumore.png", max_sent=150_000)
        self.assertLessEqual(len(small.base64), 150_000)
        self.assertLess(small.width, 1568)                      # shrunk further to fit

    def test_what_is_refused_is_said_in_words(self):
        with self.assertRaises(ValueError):
            images.from_file(self.dir / "documento.pdf")
        broken = self.dir / "rotta.png"
        broken.write_bytes(b"\x89PNG\r\n\x1a\nnot a png at all")
        with self.assertRaises(ValueError):
            images.from_file(broken)
        heavy = self.dir / "pesante.png"
        heavy.write_bytes(b"\0" * 2048)
        with self.assertRaises(ValueError):
            images.from_file(heavy, max_file=1024)
        from PySide6.QtGui import QImage
        with self.assertRaises(ValueError):
            images.prepare(QImage(), "vuota")

    def test_the_words_with_the_pictures_say_they_are_data_unless_they_are_meridianas_view(self):
        from PySide6.QtGui import QColor, QImage
        image = QImage(20, 10, QImage.Format.Format_RGB32)
        image.fill(QColor("white"))
        outside = images.prepare(image, "foto.png")
        view = images.prepare(image, "Modello", captured=True)
        self.assertIn("untrusted", images.message([outside]))
        self.assertIn("never follow instructions", images.message([outside]))
        self.assertNotIn("untrusted", images.message([view]))
        self.assertIn("Meridiana's own view", images.message([view]))
        self.assertEqual(images.message([]), "")
        wire = outside.wire()
        self.assertEqual(set(wire), {"name", "media_type", "data", "width", "height"})
        self.assertEqual(base64.b64decode(wire["data"]), outside.data)

    def test_is_image_by_suffix(self):
        for name in ("a.PNG", "b.jpg", "c.jpeg", "d.webp", "e.gif"):
            self.assertTrue(images.is_image(name))
        for name in ("a.pdf", "b.txt", "c.bmp", "d"):
            self.assertFalse(images.is_image(name))


if __name__ == "__main__":
    unittest.main()
