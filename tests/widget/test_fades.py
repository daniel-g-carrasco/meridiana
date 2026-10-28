"""The soft ends of what scrolls in a card (ui/fades.py): lighter and shorter since R161 (Daniel, 25/10/2026: «troppo
accentuate» on a small dark screen), never over the card's line nor its rounded corners («come se la sfumatura del
contenuto finisse sopra i bordi»). PySide6 and a display (offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class SoftEnds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_band_is_light_short_and_inside_the_cards_line(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtGui import QColor, QImage, QPainter
        from PySide6.QtWidgets import QLabel, QScrollArea

        from meridiana.ui import fades
        fades.set_colour("#202020")
        area = QScrollArea()
        self.addCleanup(area.deleteLater)
        inside = QLabel("x\n" * 200)
        area.setWidget(inside)
        area.resize(300, 200)
        area.show()
        self.app.processEvents()
        f = fades.attach(area)
        _top, bottom = f.edges
        self.assertTrue(bottom.isVisible())
        self.assertLessEqual(bottom.height(), fades.HEIGHT)
        self.assertLessEqual(fades.HEIGHT, 16)
        image = QImage(bottom.size(), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        p = QPainter(image)
        bottom.render(p, QPoint(0, 0))
        p.end()
        w, h = image.width(), image.height()
        edge = QColor.fromRgba(image.pixel(w // 2, h - 2))
        self.assertLess(edge.alpha(), 250)                                  # not solid: what is under it shows
        self.assertGreater(edge.alpha(), 120)                                  # solid only at the outermost pixels
        self.assertEqual(QColor.fromRgba(image.pixel(w // 2, h - 1)).alpha(), 0)    # the card's line stays clear
        self.assertEqual(QColor.fromRgba(image.pixel(0, h - 3)).alpha(), 0)
        self.assertEqual(QColor.fromRgba(image.pixel(2, h - 2)).alpha(), 0)          # and its rounded corner

    def test_the_middle_variant_clears_the_first_row_quickly_without_opening_the_card_edge(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtGui import QColor, QImage, QPainter
        from PySide6.QtWidgets import QLabel, QScrollArea

        from meridiana.ui import fades
        fades.set_colour("#202020")
        area = QScrollArea()
        self.addCleanup(area.deleteLater)
        area.setWidget(QLabel("x\n" * 200))
        area.resize(300, 200)
        area.show()
        self.app.processEvents()
        f = fades.attach(area, air=True)
        top, bottom = f.edges
        self.assertFalse(top.isVisible(), "a list resting at its beginning has no veil")
        self.assertEqual(fades.SOLID, 1.0, "the content still stops before the card's line")
        self.assertLessEqual(fades.HEIGHT, 12)
        image = QImage(bottom.size(), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        p = QPainter(image)
        bottom.render(p, QPoint(0, 0))
        p.end()
        middle = QColor.fromRgba(image.pixel(image.width() // 2, image.height() // 2))
        self.assertLess(middle.alpha(), 50, "the first readable row is not veiled")


if __name__ == "__main__":
    unittest.main()
