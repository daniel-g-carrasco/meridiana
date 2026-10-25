"""The plan's background in the window (Daniel, 23/10/2026, R21; R36): a «Background» menu in the plan's bar with
the best source for the site, the sources that cover it with their terms, none, the others in the preferences, and
the veil, the source in use always named on the plan and following the site; a building from a template placed on
the orthophoto; images imported
under the drawing (PNG, JPEG, the first page of a PDF) with their transparency, put in scale with two points and the
true distance typed, moved, turned, hidden, removed, undone, saved with the project; what is not an image said. A
source unknown falls back on the plan alone (widget/test_plan.py), the image read in nucleo/test_underlay.py and its
weight in the state of the project in nucleo/test_session.py. PySide6 and a display (offscreen will do)."""

import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup
from _fixtures import capannone

from meridiana import tiles

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


def png(path: Path, w: int = 400, h: int = 200) -> Path:
    from PySide6.QtGui import QColor, QImage
    image = QImage(w, h, QImage.Format.Format_RGB32)
    image.fill(QColor("#c8b89a"))
    image.save(str(path))
    return path


class Background(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone())
        self.win.plan.loader.offline = True                # the cache only: no tile asked to a server
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(self.nothing_to_save)

    def nothing_to_save(self):
        self.win.saved_state = self.win._state_key()        # closing asks nothing

    def items(self):
        return self.win.plan.items_by_kind.get("underlays", [])

    def click(self, x, y):
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtTest import QTest

        from meridiana.ui.plan import to_scene
        plan = self.win.plan
        pos = QPointF(plan.mapFromScene(to_scene(x, y)))
        self.app.sendEvent(plan.viewport(), QMouseEvent(QEvent.Type.MouseMove, pos, plan.viewport().mapToGlobal(pos),
                                                        Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                                                        Qt.KeyboardModifier.NoModifier))
        QTest.mouseClick(plan.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos.toPoint())
        return plan.mapToScene(pos.toPoint())

    def imported(self):
        self.win._import_image(str(png(self.root / "pianta.png")))
        self.assertEqual(len(self.win.project.underlays), 1)
        return self.win.project.underlays[0]

    def test_the_background_menu_with_the_sources_their_terms_none_and_the_veil_and_a_template_on_the_photo(self):
        from PySide6.QtWidgets import QToolButton

        from meridiana import sides, templates
        win = self.win
        button = win.plan.viewbar.buttons[win.background_action]
        self.assertEqual(button.popupMode(), QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = win.background_action.menu()
        menu.aboutToShow.emit()                              # made again when it opens: the site may have moved
        keys = [a.data() for a in win.background_group.actions()]
        # at Rho: the best (the national orthophoto), the sources that cover Rho, photos then maps, and none
        self.assertEqual(keys, ["auto", "pcn", "eox-2016", "osm", "opentopomap", "none"])
        self.assertEqual(win.background_group.actions()[0].text(),
                         "Automatic: Italy: orthophoto 2012 (Geoportale Nazionale)")
        for a in win.background_group.actions():
            if a.data() not in ("auto", "none"):
                self.assertIn(tiles.display_licence(tiles.SOURCES[a.data()]), a.toolTip())   # terms and attribution
                self.assertIn(tiles.SOURCES[a.data()].credit(), a.toolTip())
        texts = [a.text() for a in menu.actions()]
        self.assertIn("Darken the imagery", texts)
        self.assertIn("Import an image…", texts)
        self.assertIn("Other sources…", texts)
        next(a for a in win.background_group.actions() if a.data() == "opentopomap").trigger()
        self.assertEqual((self.cfg.background, win.plan.source), ("opentopomap", "opentopomap"))
        self.assertTrue(win.plan.veil.isVisible())
        # task 16a, step 8: a building from a template, then a click on the plan with the orthophoto under it: the
        # South-West corner of the L where the click was, turned as asked, with the measures written
        next(a for a in win.background_group.actions() if a.data() == "pcn").trigger()
        self.assertEqual((win.plan.source, win.plan.attribution.full),
                         ("pcn", "Ortofoto 2012: Geoportale Nazionale (MASE)"))     # the source in use, named
        buildings = len(win.project.buildings)
        win.place_template(templates.footprint("L"), 90.0)
        self.assertEqual(win.plan.point_pick[0], "template")
        at = self.click(60.0, 35.0)
        self.assertEqual(len(win.project.buildings), buildings + 1)
        b = win.project.buildings[-1]
        self.assertAlmostEqual(b.footprint[0][0], at.x(), places=3)
        self.assertAlmostEqual(b.footprint[0][1], -at.y(), places=3)
        self.assertLess(math.dist(b.footprint[0], (60.0, 35.0)), 2 * win.plan.metres_per_pixel())
        self.assertAlmostEqual(b.footprint[1][0], b.footprint[0][0], places=3)     # turned: the base runs North
        self.assertEqual([round(x, 2) for x in sides.lengths(b.footprint)], [20, 8, 12, 10, 8, 18])
        self.assertEqual(win.selection, ("building", b.id))
        win.undo.undo()
        self.assertEqual(len(win.project.buildings), buildings)

    def test_the_source_follows_the_site_a_source_chosen_elsewhere_waits_and_its_name_is_always_on_the_plan(self):
        win, plan = self.win, self.win.plan
        win._background("auto")
        self.assertEqual(plan.source, "pcn")
        plan.set_origin(48.8566, 2.3522)                     # Paris, the site moved (the window does it with the site)
        self.assertEqual(plan.source, "fr-ign")              # the best there: IGN's orthophotos
        self.assertEqual(plan.attribution.full, "© IGN, BD ORTHO, Licence Ouverte Etalab 2.0")
        win.background_menu.aboutToShow.emit()
        keys = [a.data() for a in win.background_group.actions()]
        self.assertEqual(keys[:3], ["auto", "fr-ign", "eox-2016"])
        self.assertNotIn("pcn", keys)                        # what does not cover Paris is not offered there
        self.assertEqual(win.background_group.checkedAction().data(), "auto")
        next(a for a in win.background_group.actions() if a.data() == "eox-2016").trigger()
        self.assertEqual((self.cfg.background, plan.source), ("eox-2016", "eox-2016"))
        self.assertIn("EOX", plan.attribution.full)
        next(a for a in win.background_group.actions() if a.data() == "fr-ign").trigger()
        plan.set_origin(45.5226, 9.0300)                     # back at Rho: IGN does not cover it, the best is shown
        self.assertEqual((self.cfg.background, plan.source), ("fr-ign", "pcn"))
        win.background_menu.aboutToShow.emit()
        self.assertEqual(win.background_group.checkedAction().data(), "auto")
        plan.set_origin(43.7102, 7.2620)                     # Nice: the choice comes back where it covers
        self.assertEqual(plan.source, "fr-ign")
        next(a for a in win.background_group.actions() if a.data() == "none").trigger()
        self.assertFalse(plan.attribution.isVisibleTo(plan))
        plan.set_origin(45.5226, 9.0300)

    def test_a_source_added_in_the_preferences_is_offered_used_named_on_the_plan_and_saved(self):
        from PySide6.QtWidgets import QDialog

        from meridiana import config
        win = self.win

        def run(dialog):
            page = dialog.maps
            self.assertIs(dialog.pages.currentWidget(), dialog.maps_page)     # the page asked for
            self.assertEqual(page.site, (45.5226, 9.03))                      # the project's site
            page._add()
            page.name.setText("Ortofoto del Comune")
            page.url.setText("https://tiles.example.org/{z}/{x}/{y}.jpg")
            page.attribution.setText("© Comune di Rho, CC BY 4.0")
            page._typed()
            page.default.setCurrentIndex(page.default.findData(page.choice()[1][0]["key"]))
            return QDialog.DialogCode.Accepted
        win._preferences("maps", run=run)
        [d] = self.cfg.map_sources
        self.assertEqual((self.cfg.background, win.plan.source), (d["key"], d["key"]))
        self.assertEqual(win.plan.attribution.full, "© Comune di Rho, CC BY 4.0")
        win.background_menu.aboutToShow.emit()
        self.assertEqual(win.background_group.checkedAction().data(), d["key"])
        self.assertEqual(config.load(self.paths.config_file).map_sources, [d])          # in the settings file
        self.assertIn("Preferences > Maps", win.other_sources_action.toolTip())
        win._background("auto")

    def test_an_image_under_the_drawing_in_scale_moved_turned_hidden_removed_and_saved_where_it_was(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from meridiana.ui import plan as plan_module
        win = self.win
        # imported: under the drawing, half seen, one step of the undo
        u = self.imported()
        self.assertEqual((u.width, u.height, u.name), (400, 200, "pianta.png"))
        [item] = self.items()
        self.assertAlmostEqual(item.opacity(), u.opacity)
        self.assertGreater(item.zValue(), plan_module.Z_VEIL)
        self.assertLess(item.zValue(), plan_module.Z_BUILDING)
        corner = item.mapToScene(0, 0)
        self.assertAlmostEqual(corner.x(), u.x, places=6)
        self.assertAlmostEqual(-corner.y(), u.y, places=6)
        win.undo.undo()
        self.assertEqual((win.project.underlays, self.items()), ([], []))
        # two points and the distance typed put it in scale, as one step; Esc gives the points up
        u = self.imported()
        a, b = u.to_plan(100, 100), u.to_plan(300, 100)            # 200 px apart on the image
        win.plan.pick_points("scale:" + u.id, ["first", "second"])
        with mock.patch("meridiana.ui.window.QInputDialog.getText", return_value=("7,5 m", True)):
            got_a = self.click(*a)
            got_b = self.click(*b)
        v = win.project.underlays[0]
        clicked = math.dist((got_a.x(), -got_a.y()), (got_b.x(), -got_b.y()))
        self.assertAlmostEqual(v.scale, u.scale * 7.5 / clicked, places=6)
        self.assertAlmostEqual(math.dist(v.to_plan(*u.from_plan(got_a.x(), -got_a.y())),
                                         v.to_plan(*u.from_plan(got_b.x(), -got_b.y()))), 7.5, places=4)
        self.assertIsNone(win.plan.point_pick)
        win.undo.undo()                                            # one step back: as imported
        self.assertEqual(win.project.underlays[0].scale, u.scale)
        win.plan.pick_points("scale:" + u.id, ["first", "second"])
        self.click(*u.to_plan(10, 10))
        QTest.keyClick(win.plan, Qt.Key.Key_Escape)
        self.assertIsNone(win.plan.point_pick)
        self.assertEqual(win.project.underlays[0], u)
        # moved with two points, turned, seen through, hidden and removed from its menu
        win.plan.pick_points("move:" + u.id, ["from", "to"])
        self.click(*u.to_plan(0, 0))
        self.click(u.x + 5.0, u.y - 2.0)
        v = win.project.underlays[0]
        pixel = win.plan.metres_per_pixel()                         # within a pixel of the plan (about 0.2 m here)
        self.assertAlmostEqual(v.x - u.x, 5.0, delta=max(0.2, 1.1 * pixel))
        self.assertAlmostEqual(v.y - u.y, -2.0, delta=max(0.2, 1.1 * pixel))
        win._rotate_underlay(u.id, 30.0)
        self.assertAlmostEqual(win.project.underlays[0].rotation, 30.0)
        win.background_menu.aboutToShow.emit()
        [sub] = win.underlay_entries
        self.assertEqual(sub.title(), "pianta.png")
        transparency = next(a.menu() for a in sub.actions() if a.text() == "Transparency")
        next(a for a in transparency.actions() if a.text() == "20 %").trigger()
        self.assertAlmostEqual(win.project.underlays[0].opacity, 0.8)
        self.assertAlmostEqual(self.items()[0].opacity(), 0.8)
        # saved and opened again: where it was
        file = self.file
        win.path = file
        win.project.save(file)
        win.undo.setClean()
        before = self.items()[0].sceneTransform()
        win.open_path(file)
        self.assertEqual(win.project.underlays[0].rotation, 30.0)
        after = self.items()[0].sceneTransform()
        for m in ("m11", "m12", "m21", "m22", "m31", "m32"):
            self.assertAlmostEqual(getattr(after, m)(), getattr(before, m)(), places=6)
        win._rotate_underlay(win.project.underlays[0].id, -45.0)
        self.assertEqual(win.project.underlays[0].rotation, 345.0)    # turns kept between 0 and 360
        win.background_menu.aboutToShow.emit()
        [sub] = win.underlay_entries
        next(a for a in sub.actions() if a.text() == "Show").trigger()
        self.assertFalse(win.project.underlays[0].visible)
        self.assertEqual(self.items(), [])
        next(a for a in sub.actions() if a.text() == "Remove").trigger()
        self.assertEqual(win.project.underlays, [])

    def test_the_first_page_of_a_pdf_goes_under_the_drawing_and_what_is_not_an_image_is_said(self):
        from PySide6.QtCore import QMarginsF
        from PySide6.QtGui import QColor, QPageSize, QPainter, QPdfWriter

        from meridiana.ui import underlays
        bad = self.root / "note.png"
        bad.write_text("not an image")
        self.win._import_image(str(bad))
        self.assertEqual([d[0] for d in self.dialogs], ["warning"])
        self.assertEqual(self.win.project.underlays, [])
        if not underlays.pdf_available():
            self.skipTest("Qt's PDF module is not there")
        f = self.root / "tavola.pdf"
        writer = QPdfWriter(str(f))
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setPageMargins(QMarginsF(0, 0, 0, 0))
        painter = QPainter(writer)
        painter.fillRect(100, 100, 2000, 1000, QColor("#3a6ea5"))
        writer.newPage()
        painter.end()
        self.win._import_image(str(f))
        self.assertEqual(self.win.project.underlays[0].name, "tavola.pdf")


if __name__ == "__main__":
    unittest.main()
