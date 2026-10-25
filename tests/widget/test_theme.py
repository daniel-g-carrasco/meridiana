"""The theme alone (ui/theme.py; study 13): Fusion with a full palette from the colour chosen, the contrasts that hold,
the windows11 style that does not come back, the system's accent when chosen and bronze without one, the preview's
note on a moved colour; the style sheet of the surfaces with only the colours of the tokens (task 17a, step 2); one
primary button on each page and the numbers to the right. The Theme is made alone, as the window makes it before its
widgets; what a change of theme does to the window (no old colour left, the plan and the 3D view in their own colours,
the preferences, the screenshots) is in finestra/test_theme.py. PySide6 and a display (offscreen will do)."""

import re
import unittest

import _setup
from _fixtures import capannone, flat

from PySide6.QtCore import Qt

from meridiana import config, theme_colors

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


def hexes(sheet: str) -> set:
    """The colours written in a style sheet, as #rrggbb (a translucent #aarrggbb by its rgb)."""
    out = set()
    for h in re.findall(r"#[0-9a-fA-F]{6,8}\b", sheet):
        out.add(("#" + h[3:9] if len(h) == 9 else h).lower())
    return out


class TheTheme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.ui.theme import Theme
        self.cfg = config.Config(background="none", theme="light", accent="petrol")
        self.theme = Theme(self.cfg, app=self.app)
        self.addCleanup(self.theme.deleteLater)

    def appearance(self, theme: str, accent: str, backgrounds: str) -> None:
        """What the window does with a choice of the preferences (MainWindow._appearance)."""
        self.cfg.theme, self.cfg.accent, self.cfg.backgrounds = theme, accent, backgrounds
        self.theme.apply()

    def test_every_role_of_the_palette_is_set_in_every_group(self):
        from PySide6.QtGui import QPalette
        expected = theme_colors.palette(self.theme.tokens, False)
        pal = self.app.palette()
        for group in theme_colors.GROUPS:
            for role in theme_colors.ROLES:
                with self.subTest(group=group, role=role):
                    got = pal.color(getattr(QPalette.ColorGroup, group), getattr(QPalette.ColorRole, role)).name()
                    self.assertEqual(got, expected[group][role])
        self.assertEqual(pal.color(QPalette.ColorRole.Accent).name(), "#1f6a7a")      # petrol, as it is

    def test_the_contrasts_of_the_window_hold(self):
        from PySide6.QtGui import QPalette
        pal = self.app.palette()
        c = theme_colors.contrast
        r = QPalette.ColorRole
        self.assertGreaterEqual(c(pal.color(r.WindowText).name(), pal.color(r.Window).name()), 7)
        self.assertGreaterEqual(c(pal.color(r.HighlightedText).name(), pal.color(r.Highlight).name()), 7)
        self.assertGreaterEqual(c(pal.color(r.Accent).name(), "#ffffff"), 4.5)

    def under_the_sheet(self) -> str:
        """The style under the style sheet: Meridiana's scroll bars over Fusion (ui/scrollbars.py, R100)."""
        from meridiana.ui.scrollbars import ScrollStyle
        style = self.app.style()
        self.assertIsInstance(style, ScrollStyle)
        return style.baseStyle().name().lower()

    def test_the_windows11_style_does_not_come_back(self):
        sheet = self.app.styleSheet()
        self.app.setStyleSheet("")                          # a style sheet wraps the style: look under it
        try:
            self.assertEqual(self.under_the_sheet(), "fusion")
        finally:
            self.app.setStyleSheet(sheet)
        self.appearance("dark", "plum", "grey")
        self.app.setStyleSheet("")
        try:
            self.assertEqual(self.under_the_sheet(), "fusion")
        finally:
            self.appearance("light", "petrol", "meridiana")

    def test_the_system_accent_is_used_when_chosen_and_bronze_without_one(self):
        self.theme.system_accent = "#0078d4"
        self.appearance("light", "system", "meridiana")
        self.assertEqual(self.theme.tokens["accent"], "#0075cf")                  # study 13, 12.4
        self.theme.system_accent = ""
        self.appearance("light", "system", "meridiana")
        self.assertEqual(self.theme.tokens["accent"], "#805210")                  # bronze

    def test_a_moved_colour_is_said_in_the_preview(self):
        from meridiana.ui.appearance import Appearance
        page = Appearance(config.Config(theme="light", accent="bronze"), self.theme)
        self.addCleanup(page.deleteLater)
        self.assertIn("red of the errors", page.note.text())
        page.choose_custom("#1f6a7a")
        self.assertIn("as it is", page.note.text())

    def test_the_sheet_has_the_rules_of_the_surfaces_and_only_the_colours_of_the_tokens(self):
        from meridiana.ui.theme import style_sheet
        for dark in (False, True):
            t = theme_colors.derive("#8b5a12", dark).tokens
            sheet = style_sheet(t, dark)
            for rule in ("QMainWindow::separator", "QDockWidget::title", "QPushButton:focus", "QPushButton:disabled",
                         'QPushButton[primary="true"]', 'QPushButton[destructive="true"]', 'QLabel#state-stale',
                         "QFrame#tile", "QLineEdit:focus", "QComboBox::drop-down", "QTabBar::tab:selected",
                         '*[tone="text2"]', '*[tone="muted"]', "QToolButton#file-chip:checked"):
                self.assertIn(rule, sheet)
            # no rule reaches a scroll bar: ui/scrollbars.ScrollStyle draws them (R100), a rule would make Qt
            # draw them with its arrows; no font either (the catalogue's, by code: R121), but for the tab bar of a
            # tab widget, which under a sheet takes only a font of the sheet
            self.assertNotIn("QScrollBar", sheet)
            self.assertNotIn("QScrollArea > QWidget > QWidget", sheet)
            fonts = [line for line in sheet.splitlines() if "font-" in line]
            self.assertEqual([line.split("{")[0].strip() for line in fonts], ["QTabWidget > QTabBar"])
            self.assertIn("font-size: 13px; font-weight: 400;", fonts[0])
            allowed = {v[:7].lower() for v in flat(t).values()} | {"#000000", "#ffffff", theme_colors.faded_text(t)}
            self.assertEqual(hexes(sheet) - allowed, set(), "a colour written by hand" if dark else "light")
            self.assertIn(t["field_line"], sheet)
            self.assertIn(t["field"], sheet)
        self.assertEqual(self.app.styleSheet(), style_sheet(self.theme.tokens, False))      # the one applied

    def test_one_primary_button_per_page_and_the_fields_with_the_numbers_to_the_left(self):
        from PySide6.QtWidgets import QAbstractSpinBox, QPushButton

        from meridiana.ui.energy_pages import ConsumptionPage, EconomicsPage, EnergyPage
        from meridiana.ui.properties import Properties
        p = capannone()
        sf = p.subfields[0]
        props = Properties()
        props.show_subfield(p, sf, p.fill(sf))
        pages = {"properties": props.widget(), "production": EnergyPage(), "consumption": ConsumptionPage(),
                 "economics": EconomicsPage()}
        for w in (props, *list(pages.values())[1:]):
            self.addCleanup(_setup.dispose, w)
        for name, page in pages.items():
            where = [page] + ([page.side] if hasattr(page, "side") else [])     # the form on the right (24/10/2026)
            primary = [b.text() for w in where for b in w.findChildren(QPushButton) if b.property("primary")]
            with self.subTest(page=name):
                self.assertEqual(len(primary), 1, primary)
        self.assertEqual([b.text() for b in pages["properties"].findChildren(QPushButton) if b.property("primary")],
                         ["Lay again"])
        self.assertEqual([b.text() for b in pages["properties"].findChildren(QPushButton) if b.property("destructive")],
                         ["Take them out"])
        spins = pages["properties"].findChildren(QAbstractSpinBox)
        self.assertGreater(len(spins), 3)
        for s in spins:                                     # as the mockups of C2 (the target of 24/10/2026)
            self.assertTrue(s.alignment() & Qt.AlignmentFlag.AlignLeft, s.objectName() or s.toolTip())
        # the border of a field under the pointer at 3:1 from the panel it stands on (WCAG 1.4.11)
        t = self.theme.tokens
        self.assertGreaterEqual(theme_colors.contrast(t["field_line"], t["panel"]), 3.0)
        self.assertGreaterEqual(theme_colors.contrast(t["field_line"], t["field"]), 3.0)


if __name__ == "__main__":
    unittest.main()
