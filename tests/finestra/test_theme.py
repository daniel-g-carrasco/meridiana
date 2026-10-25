"""The theme of the window (study 13; task 17a): a change of theme that leaves nothing of the old one on the widgets
made before it and on the charts, the plan and the 3D view in their own colours whatever the theme (view_colours,
Daniel 23/10/2026), the orthophoto always darkened and the paper never; the preferences' preview that changes at once
and the window when the choice settles; the sheet applied to the whole window in a short time and the window drawn
in both themes, the screenshots kept. The theme alone is in widget/test_theme.py. PySide6 and a display (offscreen
will do)."""

import unittest

import _setup
from _fixtures import capannone

from meridiana import config, theme_colors, view_colours

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class ThemeOfTheWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, cfg=config.Config(background="none", theme="light", accent="petrol"))

    def test_a_change_of_theme_leaves_no_old_colour_and_the_views_keep_their_own(self):
        from PySide6.QtGui import QPalette

        from meridiana.ui import charts
        win = self.win
        props = win.props.widget()                          # a widget made before the change
        win._appearance("dark", "plum", "tinted")
        t = theme_colors.derive("#8a3a6e", True, "tinted").tokens
        self.assertEqual(self.app.palette().color(QPalette.ColorRole.Window).name(), t["window"])
        # the page of the properties is see-through on its card (the style sheet): its text takes the new colour
        self.assertEqual(props.palette().color(QPalette.ColorRole.WindowText).name(), t["text"])
        self.assertEqual(win.docks[1].palette().color(QPalette.ColorRole.Window).name(), t["window"])
        self.assertIn(t["accent"], self.app.styleSheet())
        self.assertEqual(charts.CHROME["dark"]["surface"], t["chart"]["surface"])
        win._appearance("light", "petrol", "meridiana")
        self.assertEqual(self.app.palette().color(QPalette.ColorRole.Window).name(), "#f2f1ed")
        # the plan and the 3D view keep their own colours in every theme, on the paper and on the photo
        for background in ("none", "pcn"):
            win._background(background)
            seen = []
            for theme, accent in (("light", "petrol"), ("dark", "plum"), ("light", "bronze")):
                win._appearance(theme, accent, "meridiana")
                b = win.view3d.backend
                seen.append((dict(win.plan.colours), win.plan.backgroundBrush().color().name(),
                             b.skyTop, b.skyBottom, b.groundColor))
            with self.subTest(background=background):
                self.assertEqual(seen[0][0], view_colours.plan(background != "none"))
                self.assertEqual(seen[0][2], view_colours.D3["sky_top"])            # the day sky
                self.assertTrue(all(s == seen[0] for s in seen))
        # the orthophoto is always darkened, the veil chosen kept; the paper never
        plan = win.plan
        win._background("pcn")
        self.assertTrue(plan.veil.isVisible())
        self.assertAlmostEqual(plan.veil.brush().color().alphaF(), view_colours.VEIL, delta=0.01)
        win._appearance("dark", "plum", "meridiana")
        self.assertTrue(plan.veil.isVisible())
        chosen = next(a for a in win.veil_group.actions() if a.data() == 0.6)
        chosen.trigger()
        self.assertEqual(win.cfg.veil, 0.6)
        self.assertAlmostEqual(plan.veil.brush().color().alphaF(), 0.6, delta=0.01)
        win._background("none")
        self.assertFalse(plan.veil.isVisible())
        self.assertEqual(plan.backgroundBrush().color().name(), view_colours.PHOTO["bg"])   # the same dark ground

    def test_the_preview_changes_at_once_and_the_window_when_the_choice_settles(self):
        from PySide6.QtWidgets import QDialog

        from _setup import wait_until

        def choose(dialog):
            page = dialog.appearance
            page.colour.setCurrentIndex(page.colour.findData("indigo"))
            page._changed()
            self.assertEqual(page.preview.character.colour.name(),
                             theme_colors.derive("#5b4bb0", False).tokens["assistant"])
            self.assertEqual(self.win.theme.tokens["accent"], "#1f6a7a")       # the window: not yet
            self.assertTrue(wait_until(self.app, lambda: self.win.theme.tokens["accent"] == "#5b4bb0", 3))
            self.assertIn("4.5:1", page.contrast.text())
            return QDialog.DialogCode.Accepted
        self.win._preferences("appearance", run=choose)
        self.assertEqual(config.load(self.paths.config_file).accent, "indigo")

        def cancel(dialog):
            dialog.appearance.choose_custom("#C0FFEE")
            # the choice settles and the window shows it (a condition, not a fixed wait), then Cancel takes it back
            self.assertTrue(wait_until(self.app, lambda: not dialog.appearance.timer.isActive()
                                       and self.win.theme.tokens["accent"] != "#5b4bb0", 3))
            return QDialog.DialogCode.Rejected
        self.win._preferences("appearance", run=cancel)
        self.assertEqual((self.cfg.accent, self.win.theme.tokens["accent"]), ("indigo", "#5b4bb0"))

    def test_the_sheet_goes_on_the_whole_window_quickly_and_it_draws_in_both_themes_with_the_screenshots_kept(self):
        """A grab() of the window with the Properties and the Production page, light and dark, without errors;
        the images in build/schermate-17a (git ignores build/) for a look on the PC."""
        import time

        from PySide6.QtWidgets import QWidget
        win = self.win
        # the proof measured 16-37 ms for 108 widgets (study 17, A.5); the window has about 1,100: a blank sheet and
        # then this one again cost 87 ms on Daniel's PC offscreen (23/10/2026), a generous bound here
        widgets = win.findChildren(QWidget)
        self.assertGreater(len(widgets), 500)
        sheet = self.app.styleSheet()
        t0 = time.perf_counter()
        self.app.setStyleSheet("")
        self.app.setStyleSheet(sheet)
        for w in widgets:
            w.ensurePolished()
        self.assertLess(time.perf_counter() - t0, 1.0)
        f = self.paths.state / "p.meridiana"
        f.parent.mkdir(parents=True, exist_ok=True)
        capannone().save(f)
        win.open_path(f)
        sid = win.project.subfields[0].id
        self.assertTrue(_setup.wait_until(self.app, lambda: sid in win.results))
        win._select("subfield", sid)
        folder = _setup.ROOT / "build" / "schermate-17a"
        folder.mkdir(parents=True, exist_ok=True)
        win.resize(1400, 900)
        for theme in ("light", "dark"):
            win._appearance(theme, "bronze", "meridiana")
            for pid, page in (("model", "modello"), ("production", "produzione")):
                win.show_phase(pid)
                self.app.processEvents()
                image = win.grab().toImage()
                self.assertFalse(image.isNull())
                t = win.theme.tokens
                # the floor of the window at a corner between the bars and the cards, the card's colour inside it;
                # the grab is in device pixels on a real screen, read in the middle of each logical pixel
                dock = win.docks[0]
                dpr = image.devicePixelRatio()

                def at(x, y, image=image, dpr=dpr):
                    return image.pixelColor(int((x + 0.5) * dpr), int((y + 0.5) * dpr)).name()

                corner = at(dock.x() + 2, dock.y() + 2)
                inside = at(dock.x() + dock.width() // 2, dock.y() + 40)
                self.assertEqual(corner, t["window"], f"{theme} {page}: the floor at the card's corner")
                self.assertEqual(inside, t["card"] if theme == "dark" else t["panel"], f"{theme} {page}: the card")
                self.assertTrue(image.save(str(folder / f"test-{theme}-{page}.png")))
        win._appearance("light", "bronze", "meridiana")


if __name__ == "__main__":
    unittest.main()
