"""The released graphics of a QuickImage are never used by a later resize. PySide6 and a display (offscreen will do)."""

import unittest
from unittest import mock

import _setup

setUpModule = _setup.keep_global_state


class ReleasedImage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def image(self):
        from meridiana.ui.quick_image import QuickImage
        image = QuickImage()
        self.addCleanup(image.deleteLater)
        image.resize(100, 100)
        return image

    def test_fit_after_release_does_nothing(self):
        image = self.image()
        image.release()
        image._fit()

    def test_resize_after_release_does_nothing(self):
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QImage, QResizeEvent
        image = self.image()
        image.image = QImage(1, 1, QImage.Format.Format_ARGB32)
        image.release()
        image.resizeEvent(QResizeEvent(QSize(200, 150), QSize(100, 100)))
        errors = []
        with mock.patch("sys.excepthook", side_effect=lambda kind, value, tb:
                        errors.append(f"{kind.__name__}: {value}")):
            image.resize(200, 150)
            self.app.processEvents()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
