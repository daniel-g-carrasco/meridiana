"""One hover everywhere (R160, Daniel 25/10/2026: «L'hover è ancora troppo incongruente ... Deve avere certi
roundings, dimensioni e caratteristiche di delta colore / colore. Nelle varie fasi in alto per dire è diverso dal
resto, e anche file non c'entra proprio nulla»): the text's colour at 8 % over what is at rest, at 16 % pressed or
on, in both themes; the phases with a control's ground as «File». PySide6 and a display (offscreen will do)."""

import unittest

import _setup

from meridiana import theme_colors

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class OneHover(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_layer_is_the_texts_in_both_themes_over_what_is_at_rest(self):
        from meridiana.ui.theme import style_sheet
        for dark in (False, True):
            t = theme_colors.derive("#5b4bb0", dark).tokens
            self.assertEqual(t["hover"], t["text"] + "14")                        # 8 %
            self.assertEqual(t["press"], t["text"] + "29")                        # 16 %
            # lighter in the dark theme, darker in the light one: the field under the pointer goes towards the text
            field_hover = theme_colors.state(t, t["field"], theme_colors.HOVER)
            towards = theme_colors.luminance(field_hover) > theme_colors.luminance(t["field"])
            self.assertEqual(towards, dark)
            sheet = style_sheet(t, dark)
            hover = theme_colors.qt_hex(t["hover"])
            for rule in ("QToolButton:hover", "QToolButton#file-chip:hover", "QMenu::item:selected",
                         "QToolButton#filter:hover, QToolButton#count:hover"):
                line = next(x for x in sheet.splitlines() if x.startswith(rule + " ") or x.startswith(rule + " {"))
                self.assertIn(hover, line, rule)
            self.assertIn(f"QPushButton:hover {{ background: {field_hover}; }}", sheet)
            self.assertIn(f"QTabBar::tab:hover:!selected {{ background: {field_hover};", sheet)
            # «File» has no ground at rest, as the phases beside it
            self.assertIn("QToolButton#file-chip { background: transparent;", sheet)

    def test_a_phase_under_the_pointer_has_a_controls_ground_and_the_phase_open_none(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtGui import QColor, QImage, QPainter, QRegion
        from PySide6.QtWidgets import QWidget

        from meridiana.ui.design import Radius, Size
        from meridiana.ui.phasebar import HOVER_INSET, PhaseTabBar, _colours
        t = theme_colors.derive("#5b4bb0", False).tokens
        bar = PhaseTabBar()
        self.addCleanup(bar.deleteLater)
        for name in ("1 Modello", "2 Impianto", "3 Producibilità"):
            bar.addTab(name)
        bar.colours = _colours(t)
        bar.resize(bar.sizeHint())

        def picture():
            image = QImage(bar.size(), QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            p = QPainter(image)
            bar.render(p, QPoint(0, 0), QRegion(), QWidget.RenderFlag.DrawChildren)     # no window's ground
            p.end()
            return image

        r = bar.tabRect(2)
        at = (r.left() + 4, r.center().y())                  # left of the disc, inside the ground
        self.assertEqual(QColor.fromRgba(picture().pixel(*at)).alpha(), 0)
        bar.hovered = 2
        image = picture()
        ground = QColor.fromRgba(image.pixel(*at))
        self.assertGreater(ground.alpha(), 0)
        self.assertEqual(ground.alpha(), QColor(theme_colors.qt_hex(t["hover"])).alpha())
        # 28 px high as a control, centred on the tab's content
        x = r.left() + HOVER_INSET + Radius.CONTROL               # past the rounded corner
        column = [QColor.fromRgba(image.pixel(x, y)).alpha() > 0 for y in range(image.height())]
        self.assertAlmostEqual(sum(column), Size.CONTROL, delta=1)
        bar.hovered = 0                                       # the phase open: its tab is the header's, no ground
        r0 = bar.tabRect(0)
        self.assertEqual(QColor.fromRgba(picture().pixel(r0.left() + 4, r0.center().y())).alpha(), 0)


if __name__ == "__main__":
    unittest.main()
