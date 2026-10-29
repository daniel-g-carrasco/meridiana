"""The window, driven as the designer drives it: a project opened, laid out, edited, undone, saved and opened again,
the panels following the width of the window, the energy pages, the Plant phase, the strings and the rows by hand.
Each test is a journey of steps on one window (Journeys.again opens the shed again between two steps); a step is
what was a test of its own, with a window of its own, until task 18e. What a widget does alone is in widget/: the
properties panel (test_properties.PanelAlone), the preferences and the keys (test_preferences), the bar of the sun
(test_sunbar), the report and the formulas (test_report). They need PySide6 and a display (offscreen will do);
elsewhere they say why they are skipped. No network: the background is off."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup
from _fixtures import capannone as sample
from _fixtures import inverter_record
from _setup import wait_until

from meridiana import config, model

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class StartUp(unittest.TestCase):
    def test_the_window_imports_without_pandas_matplotlib_and_pvlib(self):
        """The heavy libraries come in where they are used, not with the window: 0,7 s of a 1,5 s start before
        (task 18c, step 10); pyqtgraph, 0,35 s, at the first chart (task 17c). A fresh process, as the start is."""
        import os
        import subprocess
        import sys
        code = ("import sys; import meridiana.ui.window; "
                "print(sorted(m for m in ('pandas', 'matplotlib', 'pvlib', 'scipy', 'pyqtgraph', 'meridiana.ui.charts_pg') "
                "if m in sys.modules))")
        env = {**os.environ, "PYTHONPATH": str(_setup.ROOT / "src"), "QT_QPA_PLATFORM": "offscreen"}
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=120,
                             check=False)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        self.assertEqual(out.stdout.strip(), "[]", out.stdout)


class Journeys(unittest.TestCase):
    """A window on the shed (_setup.window: every dialog noted and answered at once) driven along journeys: each
    journey is a few steps, each step what was a test of its own with a window of its own (study 18, D 7.1: 299
    windows for 637 tests); between two steps the shed is opened again as it was saved (`again`), the window
    kept."""
    size = (1200, 800)

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, sample(), size=self.size, answers=self.answers(), cache=self.cache())
        self.sid = self.win.project.subfields[0].id

    def answers(self) -> dict | None:
        """The answer to a kind of dialog, when not _setup.window's (a question: Discard)."""
        return None

    def cache(self):
        """The weather year put in the cache of the window, or None."""
        return None

    def again(self) -> None:
        """The next step starts on the shed as the file holds it: opened again, the tool Select, no dialog noted,
        its layout back."""
        self.win._set_tool("select")
        self.win.open_path(self.file)
        self.sid = self.win.project.subfields[0].id
        self.assertTrue(wait_until(self.app, lambda: self.sid in self.win.results), "the layout did not come back")
        self.app.processEvents()
        self.dialogs.clear()


class Window(Journeys):
    def a_damaged_file_is_said_and_the_project_in_hand_stays(self):
        # study 18, G 6.1: eight malformed files out of twenty crashed this slot; now every one is a warning
        before = self.win.project.name
        for n, text in enumerate(('{"format": "meridiana-project", "version": "6"}',
                                  '{"format": "meridiana-project", "version": 6, "buildings": ["x"]}',
                                  '{"format": "meridiana-project", "version": 6, "site": {"lat": NaN, "lon": 9}}',
                                  "not json at all")):
            bad = self.file.with_name(f"rotto{n}.meridiana")
            bad.write_text(text, encoding="utf-8")
            self.dialogs.clear()
            self.win.open_path(bad)
            self.assertEqual([d[0] for d in self.dialogs], ["warning"], text)
            self.assertEqual(self.win.project.name, before)
            self.assertEqual(self.win.path, self.file)

    def an_error_nobody_caught_is_told_in_the_status_bar_and_once_in_a_dialog(self):
        self.dialogs.clear()
        self.win.tell_error("RuntimeError: boom")
        self.assertIn("boom", self.win.statusBar().currentMessage())
        self.win.tell_error("RuntimeError: again")
        self.assertEqual([d[0] for d in self.dialogs], ["warning"])        # the dialog once, the bar every time
        self.assertIn("again", self.win.statusBar().currentMessage())

    def a_map_tile_that_fails_is_said_once_a_minute(self):
        self.win.plan.loader.tileFailed.emit("pcn", 17, 1, 2, "timeout")
        self.assertIn("Italy: orthophoto 2012", self.win.statusBar().currentMessage())     # the source by its name
        self.win.statusBar().clearMessage()
        self.win.plan.loader.tileFailed.emit("pcn", 17, 1, 3, "timeout")
        self.assertEqual(self.win.statusBar().currentMessage(), "")

    def the_privacy_switches_stop_the_map_loader_and_the_pvgis_fetch(self):
        # the page of the preferences, alone: widget/test_preferences.py
        self.win._network(False, False, False)
        self.assertTrue(self.win.plan.loader.offline)
        loader = self.win.plan.loader
        loader.request("osm", 17, 1, 2)                           # nothing in the cache: nothing asked either
        self.assertEqual((len(loader.queue), len(loader.in_flight)), (0, 0))
        self.win._compute_energy(fetch=True)
        self.assertIn("Privacy", self.win.statusBar().currentMessage())
        self.assertTrue(wait_until(self.app, lambda: bool(self.win.energy), 60), "the energy job did not come back")
        self.win._network(True, True, True)
        self.assertFalse(self.win.plan.loader.offline)

    def a_new_window_has_nothing_to_save(self):
        from meridiana.ui.window import MainWindow
        fresh = MainWindow(self.paths, config.Config(background="none"))
        self.assertFalse(fresh._dirty())
        self.assertNotIn("*", fresh.windowTitle())
        _setup.dispose(fresh)
        self.assertEqual(self.dialogs, [])

    def an_opened_project_has_nothing_to_save(self):
        self.assertFalse(self.win._dirty())
        self.assertNotIn("*", self.win.windowTitle())

    def the_eave_picked_on_the_plan_and_a_side_made_longer(self):
        from PySide6.QtWidgets import QInputDialog
        bid = self.win.project.buildings[0].id
        self.win._edited("building", bid, {"roof.type": "mono", "roof.tilt": 10.0})
        self.win._select("building", bid)
        self.win._action("pick_eave", "building", bid)              # «Pick on the plan» in the properties
        self.assertEqual(self.win.plan.edge_pick[:3], ("eave", "building", bid))
        self.win.plan.edgePicked.emit("eave", "building", bid, 2)   # the North side clicked
        self.assertEqual(self.win.project.buildings[0].roof.eave_side, 2)
        self.assertAlmostEqual(self.win.project.buildings[0].pitches()[0].azimuth % 360, 180.0, places=4)
        with mock.patch.object(QInputDialog, "getDouble", return_value=(50.0, True)):
            self.win._side_clicked("building", bid, 0)               # the South side, 40 m, made 50
        self.assertEqual(self.win.project.buildings[0].footprint, [[0, 0], [50.0, 0], [50.0, 20], [0, 20]])
        self.win.undo.undo()
        self.assertEqual(self.win.project.buildings[0].footprint, [[0, 0], [40, 0], [40, 20], [0, 20]])
        with mock.patch.object(QInputDialog, "getDouble", return_value=(0.01, True)):
            self.win._side_clicked("building", bid, 0)               # it would vanish: refused, said
        self.assertIn("Not changed", self.win.hint.text())

    def a_side_clicked_as_a_gable_end_changes_the_roof_and_is_undone(self):
        """Task 16a: the type in the Roof group proposes the slope of tiles, 35 % (Daniel, 23/10/2026); a side
        clicked on the plan becomes a gable end, and Undo takes it back."""
        import math

        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QComboBox, QLabel

        from meridiana.ui.plan import to_scene
        bid = self.win.project.buildings[0].id
        self.win._select("building", bid)
        kind = next(c for c in self.win.props.widget().findChildren(QComboBox) if c.findData("hip") >= 0)
        kind.setCurrentIndex(kind.findData("gable"))
        b = self.win.project.buildings[0]
        self.assertEqual((b.roof.type, b.roof.covering), ("gable", "tiles"))
        self.assertAlmostEqual(b.slope(), math.degrees(math.atan(0.35)), places=9)
        self.assertEqual([p.side for p in b.pitches()], [0, 2])           # the gable ends on the short sides
        self.assertTrue(any("ANDIL" in w.text() for w in self.win.props.widget().findChildren(QLabel)))  # the source
        self.win._action("pick_gable", "building", bid)                    # «Pick on the plan» in the Roof group
        self.assertEqual(self.win.plan.edge_pick[:3], ("gable", "building", bid))
        plan = self.win.plan
        pos = QPointF(plan.mapFromScene(to_scene(20.0, 20.0)))             # the middle of the North side
        self.app.sendEvent(plan.viewport(), QMouseEvent(QEvent.Type.MouseMove, pos, plan.viewport().mapToGlobal(pos),
                                                        Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                                                        Qt.KeyboardModifier.NoModifier))
        QTest.mouseClick(plan.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos.toPoint())
        b = self.win.project.buildings[0]
        self.assertEqual(b.roof.edges, ["eave", "gable", "gable", "gable"])
        self.assertEqual([p.side for p in b.pitches()], [0])               # one pitch, up to the North wall
        self.assertIn("gable end", self.win.hint.text())
        self.win.undo.undo()
        self.assertEqual([p.side for p in self.win.project.buildings[0].pitches()], [0, 2])

    def the_ridge_height_written_sets_the_slope(self):
        import math

        from PySide6.QtWidgets import QDoubleSpinBox
        b = self.win.project.buildings[0]
        self.win._edited("building", b.id, b.retyped("gable"))
        self.win._select("building", b.id)
        page = self.win.props.widget()
        ridge = next(s for s in page.findChildren(QDoubleSpinBox) if s.maximum() == 1000)
        slope = next(s for s in page.findChildren(QDoubleSpinBox) if s.maximum() == 80)
        self.assertAlmostEqual(ridge.value(), 9.5 + 10.0 * 0.35, places=2)         # 35 % over half of 20 m
        ridge.setValue(12.0)                                 # the ridge 2.5 m above the eave of 9.5 m
        b = self.win.project.buildings[0]
        self.assertEqual(b.roof.ridge_height, 12.0)
        self.assertAlmostEqual(b.slope(), math.degrees(math.atan(2.5 / 10.0)), places=9)
        self.assertAlmostEqual(slope.value(), math.degrees(math.atan(0.25)), places=1)   # the slope shown follows
        self.assertIs(self.win.props.widget(), page)
        slope.setValue(20.0)                                 # a slope written wins over the ridge again
        b = self.win.project.buildings[0]
        self.assertEqual((b.roof.ridge_height, b.slope()), (None, 20.0))
        ridge.setValue(9.0)                                  # under the eave: refused, said
        self.assertIn("Not changed", self.win.hint.text())
        self.assertIsNone(self.win.project.buildings[0].roof.ridge_height)
        self.win.undo.undo()                                 # the slope written undone: the ridge again
        self.assertEqual(self.win.project.buildings[0].roof.ridge_height, 12.0)

    def a_pvsyst_project_opens_as_a_new_project_with_its_variants(self):
        from meridiana.ui.pvsyst_import import summary_html
        data = _setup.DATA / "pvsyst" / "Prova Rho_Project.PRJ"
        seen = []
        ok = self.win._import_pvsyst_project(str(data), choose=lambda prj: [0, 1],
                                             confirm=lambda report: seen.append(summary_html(report)) or True)
        self.assertTrue(ok)
        p = self.win.project
        self.assertEqual([v["name"] for v in p.variants], ["File da 3", "Piano ovest"])
        self.assertIsNone(self.win.path)
        self.assertTrue(self.win._dirty())                                   # new and unsaved
        self.assertEqual(self.win.variant_bar.count(), 2)
        self.assertIn("Missing", seen[0])
        sid = p.subfields[0].id
        self.assertTrue(wait_until(self.app, lambda: sid in self.win.results), "the layout did not come back")
        self.assertEqual(self.win.results[sid].count, 30)
        self.win._show_checks()
        self.assertTrue(any(i.area == "import" for i in self.win.checks_page.items))

    def a_dragged_corner_is_one_undoable_edit(self):
        bid = self.win.project.buildings[0].id
        self.win._select("building", bid)
        self.win.plan.vertexMoved.emit("building", bid, 2, 45.0, 25.0)
        self.assertEqual(self.win.project.buildings[0].footprint[2], [45.0, 25.0])
        self.win.undo.undo()
        self.assertEqual(self.win.project.buildings[0].footprint[2], [40, 20])
        self.win.plan.vertexMoved.emit("building", bid, 2, 0.0, -5.0)          # across the outline: refused
        self.assertEqual(self.win.project.buildings[0].footprint[2], [40, 20])
        self.assertIn("Not changed", self.win.hint.text())

    def a_building_a_sub_field_and_an_exclusion_drawn_on_the_plan_are_in_the_project_and_undone(self):
        """The plan's outline reaches the project through the window (MainWindow._drawn, study 18, D 6.3): each
        tool makes its object on the building under it, selects it and is one step of the undo; the page of an
        exclusion shows its kind, its height and the default of the kind."""
        from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QLabel, QPushButton

        from meridiana.ui.plan import to_scene
        plan = self.win.plan
        plan.fitInView(QRectF(-10.0, -30.0, 90.0, 60.0))      # room beside the shed
        plan.snaps_on = False

        def draw(tool, corners):
            self.win._set_tool(tool)
            for x, y in corners:
                pos = QPointF(plan.mapFromScene(to_scene(x, y)))
                self.app.sendEvent(plan.viewport(), QMouseEvent(
                    QEvent.Type.MouseMove, pos, plan.viewport().mapToGlobal(pos), Qt.MouseButton.NoButton,
                    Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
                QTest.mouseClick(plan.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                                 pos.toPoint())
            QTest.keyClick(plan, Qt.Key.Key_Return)

        def near(ring, corners):
            tol = 3 * plan.metres_per_pixel()
            return len(ring) == len(corners) and all(abs(x - a) <= tol and abs(y - b) <= tol
                                                     for (x, y), (a, b) in zip(ring, corners, strict=True))
        steps = self.win.undo.count()
        draw("building", [(50, 0), (62, 0), (62, 8), (50, 8)])
        p = self.win.project
        self.assertEqual(len(p.buildings), 2)
        new = p.buildings[1]
        self.assertTrue(near(new.footprint, [(50, 0), (62, 0), (62, 8), (50, 8)]), new.footprint)
        self.assertEqual((new.name, new.height), ("Building 2", 6.0))
        self.assertEqual(self.win.selection, ("building", new.id))
        self.assertEqual(self.win.undo.undoText(), "Draw a building")
        draw("subfield", [(51, 1), (61, 1), (61, 7), (51, 7)])
        sf = self.win.project.subfields[1]
        self.assertEqual((sf.building, sf.name, sf.params["mounting"]), (new.id, "Sub-field 2", "tilted_anchored"))
        self.assertEqual(self.win.selection, ("subfield", sf.id))
        self.assertEqual(self.win.undo.undoText(), "Draw a sub-field")
        draw("exclusion", [(18, 8), (20, 8), (20, 10), (18, 10)])
        [e] = self.win.project.exclusions
        self.assertEqual((e.kind, e.building, e.height), ("skylight", self.win.project.buildings[0].id, None))
        self.assertEqual(self.win.selection, ("exclusion", e.id))
        self.assertEqual(self.win.undo.count(), steps + 3)
        # the page of the exclusion: its kind, its height from the kind until given, the way back to the default
        page = self.win.props.widget()
        self.assertEqual(self.win.props.kind, "exclusion")
        kind = next(c for c in page.findChildren(QComboBox) if c.findData("chimney") >= 0)
        height = next(s for s in page.findChildren(QDoubleSpinBox) if s.maximum() == 60)
        self.assertEqual((kind.currentData(), height.value()), ("skylight", model.OBSTACLE_HEIGHTS["skylight"]))
        self.assertTrue(any("default for this kind" in w.text() for w in page.findChildren(QLabel)))
        kind.setCurrentIndex(kind.findData("chimney"))
        self.assertEqual(self.win.project.exclusions[0].kind, "chimney")
        self.assertEqual(height.value(), model.OBSTACLE_HEIGHTS["chimney"])      # the field follows the kind
        height.setValue(2.5)
        self.assertEqual(self.win.project.exclusions[0].height, 2.5)
        back = next(b for b in self.win.props.widget().findChildren(QPushButton) if "default height" in b.text())
        back.click()
        self.assertIsNone(self.win.project.exclusions[0].height)
        # too small to be anything: said, nothing made
        draw("exclusion", [(5, 5), (5.3, 5), (5.3, 5.3)])
        self.assertEqual(len(self.win.project.exclusions), 1)
        self.assertIn("Too small to keep", self.win.hint.text())
        for _step in range(self.win.undo.index() - steps):
            self.win.undo.undo()
        p = self.win.project
        self.assertEqual((len(p.buildings), len(p.subfields), len(p.exclusions)), (1, 1, 0))

    def the_layout_comes_back_and_is_shown(self):
        r = self.win.results[self.sid]
        self.assertGreater(r.count, 50)
        self.assertEqual(len(self.win.module_index), r.count)
        self.assertEqual(self.win.tree.topLevelItemCount(), 1)

    def a_module_taken_out_and_put_back(self):
        r = self.win.results[self.sid]
        key = r.modules[5].key
        self.win.plan.selected_module = (self.sid, key)
        self.win._module_clicked(self.sid, key)
        self.win._delete()
        self.assertTrue(wait_until(self.app, lambda: self.win.results[self.sid].count == r.count - 1))
        self.assertIn(key, self.win.project.subfields[0].removed)
        self.win.undo.undo()
        self.assertTrue(wait_until(self.app, lambda: self.win.results[self.sid].count == r.count))
        self.assertNotIn(key, self.win.project.subfields[0].removed)

    def a_change_of_tilt_lays_again_without_moving_the_camera_on_its_own(self):
        before = self.win.results[self.sid]
        self.win._edited("subfield", self.sid, {"params.tilt": 30.0})
        self.assertTrue(wait_until(self.app, lambda: self.win.results[self.sid] is not before))
        self.assertAlmostEqual(self.win.results[self.sid].tilt, 30.0)
        self.assertTrue(self.win.view3d.fitted)
        self.assertIn("tilt", self.win.undo.undoText())

    def a_subfields_sun_window_lays_differently_and_is_undone_redone_and_used_by_all(self):
        sf = self.win.project.subfields[0]
        original = self.win.results[self.sid].pitch
        own = {**self.win.project.sun_window, "start": 9.0, "end": 15.0}
        self.win._edited("subfield", self.sid, {"params.window": own})
        self.assertEqual(sf.params["window"], own)
        self.assertTrue(wait_until(self.app, lambda: self.win.results[self.sid].pitch != original))
        self.win.undo.undo()
        self.assertNotIn("window", self.win.project.subfields[0].params)
        self.assertTrue(wait_until(self.app, lambda: self.win.results[self.sid].pitch == original))
        self.win.undo.redo()
        self.assertEqual(self.win.project.subfields[0].params["window"], own)
        self.assertTrue(wait_until(self.app, lambda: self.win.results[self.sid].pitch != original))
        before = self.win.project.sun_window
        self.win._edited("sun_window", self.sid, {"window": own})
        self.assertEqual(self.win.project.sun_window, own)
        self.assertTrue(all("window" not in s.params for s in self.win.project.subfields))
        self.win.undo.undo()
        self.assertEqual(self.win.project.sun_window, before)
        self.assertEqual(self.win.project.subfields[0].params["window"], own)
        self.win.undo.redo()
        self.assertEqual(self.win.project.sun_window, own)
        self.assertNotIn("window", self.win.project.subfields[0].params)

    def the_sun_of_the_3d_view_starts_on_the_design_day_and_moves(self):
        """The window's share: the site of the project opened, the bar joined to the 3D view. The bar itself, the
        night, the day played: widget/test_sunbar.py."""
        bar, backend = self.win.sunbar, self.win.view3d.backend
        noon = bar.position()
        self.assertEqual((bar.lat, bar.lon), (self.win.project.site.lat, self.win.project.site.lon))
        self.assertEqual((bar.day.date().month(), bar.day.date().day()), (12, 21))
        self.assertLess(abs(noon.azimuth), 3.0)                    # solar noon: the sun in the South
        self.assertAlmostEqual(backend._sun_elev, noon.apparent, places=6)
        bar.hour.setValue(9 * 6)                                   # 09:00 on the clock
        self.assertAlmostEqual(backend._sun_bearing, bar.position().bearing, places=6)
        bar.to_design_day()

    def an_obstacle_gets_its_height_from_its_kind_until_given(self):
        eid = self.win.project.new_id("e")
        ring = [[10.0, 8.0], [11.0, 8.0], [11.0, 9.0], [10.0, 9.0]]
        self.win.edit("add", lambda p: p.exclusions.append(model.ExclusionItem(id=eid, ring=ring, kind="chimney",
                                                                               building=p.buildings[0].id)))
        self.win._edited("exclusion", eid, {"height": 2.5})
        self.assertIn("height", self.win.undo.undoText())
        e = next(x for x in self.win.project.exclusions if x.id == eid)
        self.assertEqual(e.obstacle_height(), 2.5)
        self.win._edited("exclusion", eid, {"height": None})
        e = next(x for x in self.win.project.exclusions if x.id == eid)
        self.assertEqual(e.obstacle_height(), model.OBSTACLE_HEIGHTS["chimney"])

    def a_value_typed_in_the_properties_does_not_pull_the_field_away(self):
        import shiboken6
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication, QDoubleSpinBox
        bid = self.win.project.buildings[0].id
        self.win._select("building", bid)
        self.app.processEvents()
        spin = next(s for s in self.win.props.findChildren(QDoubleSpinBox) if s.isVisible() and s.maximum() >= 300)
        _setup.keyboard_or_skip(self, spin)                 # said when the desktop gives no keyboard, not passed
        spin.selectAll()
        QTest.keyClicks(spin, "12")
        before = self.win.results
        QTest.keyClick(spin, Qt.Key.Key_Return)           # the edit comes back to the panel inside this key press
        # the layout comes back and the panel shows it (a condition, never a fixed wait)
        self.assertTrue(wait_until(self.app, lambda: self.win.results is not before and self.sid in self.win.results,
                                   10), "the layout did not come back")
        self.app.processEvents()
        self.assertEqual(self.win.project.buildings[0].height, 12.0)
        self.assertTrue(shiboken6.isValid(spin))          # the same field: only its value was set
        self.assertIs(spin.window(), self.win)
        self.assertEqual(spin.value(), 12.0)
        self.assertIn(QApplication.focusWidget(), (spin, spin.lineEdit()))   # the keyboard stays on it

    def a_length_in_the_properties_takes_units_and_a_calculation(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        from meridiana.ui.quantity_field import QuantityField
        bid = self.win.project.buildings[0].id
        self.win._select("building", bid)
        height = next(s for s in self.win.props.widget().findChildren(QuantityField) if s.maximum() == 300)
        for text in ("10 m + 50 cm", "3 kg"):
            height.setFocus()
            height.selectAll()
            QTest.keyClicks(height, text)
            QTest.keyClick(height, Qt.Key.Key_Return)
        self.assertEqual(self.win.project.buildings[0].height, 10.5)
        self.assertIn("mm, cm, m, km", self.win.hint.text())        # the second one is said, not taken

    def del_while_drawing_deletes_nothing(self):
        bid = self.win.project.buildings[0].id
        self.win._select("building", bid)
        self.win._set_tool("subfield")
        self.win.plan.chain = [(2.0, 2.0), (10.0, 2.0)]    # a sub-field being drawn on the selected building
        self.win.commands["delete"].trigger()               # Del, a key of the whole window
        self.assertIsNotNone(self.win.project.building(bid))
        self.assertEqual(len(self.win.project.subfields), 1)
        self.assertEqual(self.win.plan.chain, [(2.0, 2.0), (10.0, 2.0)])
        self.assertIn("Backspace", self.win.hint.text())
        self.win._set_tool("select")
        self.win._select("building", bid)
        self.win.commands["delete"].trigger()               # with Select it deletes, as before
        self.assertIsNone(self.win.project.building(bid))

    def the_name_field_shows_the_name_the_project_kept(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QLineEdit
        bid = self.win.project.buildings[0].id
        self.win._select("building", bid)
        name = self.win.props.widget().findChildren(QLineEdit)[0]
        _setup.keyboard_or_skip(self, name)
        name.selectAll()
        QTest.keyClick(name, Qt.Key.Key_Delete)
        QTest.keyClick(name, Qt.Key.Key_Return)             # an empty name is not taken
        self.assertEqual(self.win.project.building(bid).name, "Capannone")
        self.assertEqual(name.text(), "Capannone")          # and the field says so, with the keyboard still on it
        name.selectAll()
        QTest.keyClicks(name, "  Magazzino  ")
        QTest.keyClick(name, Qt.Key.Key_Return)
        self.assertEqual(self.win.project.building(bid).name, "Magazzino")
        self.assertEqual(name.text(), "Magazzino")

    def _typing_in_height(self, text: str):
        """The eave height of the building with the keyboard on it and `text` typed, not confirmed."""
        from PySide6.QtTest import QTest

        from meridiana.ui.quantity_field import QuantityField
        height = next(s for s in self.win.props.widget().findChildren(QuantityField) if s.maximum() == 300)
        _setup.keyboard_or_skip(self, height)
        height.selectAll()
        QTest.keyClicks(height, text)
        return height

    def an_undo_drops_what_was_being_written_and_enter_keeps_the_project_as_undone(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        bid = self.win.project.buildings[0].id
        self.win._select("building", bid)
        self.win._edited("building", bid, {"height": 10.0})
        height = self._typing_in_height("1")                # the start of "10"
        self.win.undo.undo()                                # Undo from the toolbar: its button takes no keyboard
        self.assertEqual(self.win.project.buildings[0].height, 9.5)
        self.assertEqual(height.cleanText(), height.textFromValue(9.5))     # what was written is dropped
        QTest.keyClick(height, Qt.Key.Key_Return)
        self.assertEqual(self.win.project.buildings[0].height, 9.5)
        self.assertEqual(height.value(), 9.5)               # the field and the project say the same

    def a_value_confirmed_after_an_edit_from_elsewhere_goes_into_the_project(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        bid = self.win.project.buildings[0].id
        self.win._select("building", bid)
        self.win._edited("building", bid, {"height": 10.0})
        height = self._typing_in_height("1")
        self.win._edited("building", bid, {"height": 8.0})  # not an undo: what is being written stays
        self.assertEqual(height.cleanText(), "1")
        QTest.keyClicks(height, "0")
        QTest.keyClick(height, Qt.Key.Key_Return)           # 10, as the field held before: the project was 8
        self.assertEqual(self.win.project.buildings[0].height, 10.0)

    def a_name_written_across_an_undo_of_a_variant_does_not_go_to_the_other_variant(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QLineEdit
        self.win.edit("variant", lambda p: p.add_variant("B"))
        self.win._select("subfield", self.sid)
        name = self.win.props.widget().findChildren(QLineEdit)[0]
        _setup.keyboard_or_skip(self, name)
        name.selectAll()
        QTest.keyClicks(name, "Nord")
        self.win.undo.undo()                                # back to the first variant, whose sub-field has the same id
        self.assertEqual(self.win.project.variant, self.win.project.variants[0]["id"])
        QTest.keyClick(name, Qt.Key.Key_Return)
        self.assertEqual(self.win.project.subfields[0].name, "Sud")
        self.assertEqual(name.text(), "Sud")

    def a_result_that_comes_back_leaves_the_text_being_written(self):
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QDoubleSpinBox, QLineEdit
        self.win._select("subfield", self.sid)
        self.app.processEvents()
        page = self.win.props.widget()
        gap = next(s for s in page.findChildren(QDoubleSpinBox) if s.maximum() == 1.0 and getattr(s, "unit", "") == "m")
        name = page.findChildren(QLineEdit)[0]
        steps, built = self.win.undo.count(), self.win.props.rebuilds
        _setup.keyboard_or_skip(self, gap)                  # what is being written is the field's with the keyboard
        gap.selectAll()
        QTest.keyClicks(gap, "0")                           # the start of "0,07", not confirmed
        before = self.win.results
        self.win._start_layout()                            # a result comes back meanwhile
        self.assertTrue(wait_until(self.app, lambda: self.win.results is not before, 10))
        self.win._show_properties()
        self.assertIs(self.win.props.widget(), page)        # the page stays
        self.assertEqual(self.win.props.rebuilds, built)
        self.assertEqual(gap.cleanText(), "0")             # what is being written stays
        self.assertNotIn("gap", self.win.project.subfields[0].params)
        self.assertEqual(self.win.undo.count(), steps)
        self.win._edited("subfield", self.sid, {"name": "Est"})      # an edit from elsewhere: the value follows
        self.assertEqual(name.text(), "Est")
        self.assertEqual(self.win.undo.count(), steps + 1)  # the edit, and nothing more from the panel

    def a_change_lays_out_again_only_the_sub_field_it_touches(self):
        sid2 = self.win.project.new_id("s")

        def add(p):
            p.subfields.append(model.SubField(id=sid2, name="Terra", ring=[[50, 0], [70, 0], [70, 10], [50, 10]],
                                              filled=True))
        self.win.edit("add", add)
        self.assertTrue(wait_until(self.app, lambda: sid2 in self.win.results))
        self.assertEqual(self.win.layout_job.laid, [sid2])           # the first one kept its layout
        first = self.win.results[self.sid]
        self.win._edited("subfield", sid2, {"params.gap": 0.05})
        self.assertEqual(self.win.project.layout_state(self.win.project.subfields[1], self.win.layout_keys,
                                                       self.win.results), "stale")
        tree = [self.win.tree.topLevelItem(0).child(1).child(i).text(0) for i in range(2)]
        self.assertTrue(tree[1].endswith("…"))             # marked in the tree until the layout is back
        before = self.win.results
        self.assertTrue(wait_until(self.app, lambda: self.win.results is not before))
        self.assertEqual(self.win.layout_job.laid, [sid2])
        self.assertIs(self.win.results[self.sid], first)
        self.assertEqual(self.win.project.layout_state(self.win.project.subfields[1], self.win.layout_keys,
                                                       self.win.results), "ok")

    def a_layout_that_fails_is_marked_in_the_tree_and_the_properties(self):
        from PySide6.QtWidgets import QLabel
        self.win._select("subfield", self.sid)
        keys = dict(self.win.layout_keys)
        self.win._layout_done(self.win.generation, {self.sid: ValueError("no room")}, 0.0, keys)
        from PySide6.QtCore import QSize

        from meridiana.ui.marks import icon
        item = self.win.tree.topLevelItem(0).child(1).child(0)
        self.assertEqual(item.text(0), self.win.project.subfields[0].name)    # no «✘», a character of no font here
        size = QSize(22, 20)
        self.assertEqual(item.icon(0).pixmap(size).toImage(), icon("fail").pixmap(size).toImage())   # the mark
        self.assertIn("no room", item.toolTip(0))
        texts = [label.text() for label in self.win.props.widget().findChildren(QLabel)]
        self.assertTrue(any("no room" in t for t in texts))

    def the_page_is_built_again_only_for_another_object_or_other_fields(self):
        from PySide6.QtWidgets import QDoubleSpinBox
        bid = self.win.project.buildings[0].id
        self.win._select("building", bid)
        built = self.win.props.rebuilds
        page = self.win.props.widget()
        for height in (10.0, 11.0):                         # values: set in place
            self.win._edited("building", bid, {"height": height})
        self.win._show_properties()
        self.assertEqual(self.win.props.rebuilds, built)
        self.assertIs(self.win.props.widget(), page)
        heights = [s for s in page.findChildren(QDoubleSpinBox) if s.maximum() == 300]
        self.assertEqual(heights[0].value(), 11.0)
        self.win.undo.undo()                                # undone: the field shows the value before
        self.assertEqual(heights[0].value(), 9.5)
        self.assertEqual(self.win.props.rebuilds, built)
        self.win._edited("building", bid, {"roof.type": "gable"})     # a slope and a ridge: other fields
        self.assertEqual(self.win.props.rebuilds, built + 1)
        self.win._select("subfield", self.sid)              # another object
        self.assertEqual(self.win.props.rebuilds, built + 2)
        self.win._select("subfield", self.sid)
        self.assertEqual(self.win.props.rebuilds, built + 2)

    def a_side_changed_in_place_stretches_the_outline_as_it_is_now(self):
        from PySide6.QtWidgets import QDoubleSpinBox
        bid = self.win.project.buildings[0].id
        self.win._select("building", bid)
        page = self.win.props.widget()
        sides_ = [s for s in page.findChildren(QDoubleSpinBox) if s.maximum() == 10000]
        sides_[0].setValue(50.0)                            # the south side: 40 m to 50 m
        self.assertEqual(self.win.props.widget(), page)
        self.assertEqual(sides_[0].value(), 50.0)
        sides_[1].setValue(25.0)                            # then the east side, of the outline already stretched
        b = self.win.project.buildings[0]
        self.assertEqual(sorted({round(x, 3) for x, _y in b.footprint}), [0.0, 50.0])
        self.assertEqual(sorted({round(y, 3) for _x, y in b.footprint}), [0.0, 25.0])

    def unsaved_changes_are_kept_aside_and_offered_back(self):
        from PySide6.QtWidgets import QMessageBox

        from meridiana import recovery
        from meridiana.ui.window import MainWindow
        self.win._edited("project", "", {"name": "Da recuperare"})
        self.win._autosave()
        copy = recovery.slot(self.paths.state, self.file)
        self.assertTrue(copy.exists())
        # the session stops without saving; the next one offers the copy back
        again = MainWindow(self.paths, config.Config(background="none"))
        self.addCleanup(lambda: (setattr(again, "saved_state", again._state_key()), _setup.dispose(again)))
        with mock.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.assertTrue(again.offer_recovery())
        self.assertEqual(again.project.name, "Da recuperare")
        self.assertEqual(again.path, self.file)
        self.assertTrue(again._dirty())
        self.assertTrue(again._save())
        self.assertFalse(copy.exists())                     # saved: the copy has done its job

    def a_new_revision_is_a_new_file_next_to_the_old_one(self):
        before = self.file.read_text(encoding="utf-8")
        self.win._edited("project", "", {"name": "Revisione"})
        self.win._save_revision()
        self.assertEqual(self.win.path.name, "prova_R01.meridiana")
        self.assertTrue(self.win.path.exists())
        self.assertEqual(self.file.read_text(encoding="utf-8"), before)   # the previous one stays as it was
        self.assertFalse(self.win._dirty())

    def a_disk_that_refuses_is_said_and_the_project_stays_to_save(self):
        """The writes that fail (study 18, D 6.5): the save and the new revision say it in a dialog and the project
        stays to save, the file as it was; the recovery copy and the settings say it in the status bar."""
        import tempfile as tempfile_module
        before = self.file.read_bytes()
        self.win._edited("project", "", {"name": "Da salvare"})
        self.dialogs.clear()
        with mock.patch.object(tempfile_module, "mkstemp", side_effect=PermissionError(13, "Permission denied")):
            self.assertFalse(self.win._save())
            self.win._save_revision()
            self.assertEqual([d[0] for d in self.dialogs], ["warning", "warning"])
            self.assertTrue(all("could not be saved" in d[1][1] and "Permission denied" in d[1][1]
                                for d in self.dialogs))
            self.win._autosave()
            self.assertIn("The recovery copy could not be written", self.win.statusBar().currentMessage())
            self.win._save_config()
            self.assertIn("The settings could not be saved", self.win.statusBar().currentMessage())
        self.assertTrue(self.win._dirty())
        self.assertIn("*", self.win.windowTitle())
        self.assertEqual((self.win.path, self.file.read_bytes()), (self.file, before))
        self.assertEqual(sorted(p.name for p in self.file.parent.glob("prova*")), ["prova.meridiana"])
        self.assertTrue(self.win._save())                   # the disk again: saved
        self.assertFalse(self.win._dirty())

    def a_pvsyst_module_and_inverter_are_imported_after_a_look(self):
        from PySide6.QtWidgets import QMessageBox

        from _fixtures import OND, PAN, written
        pan = written(PAN, "AS-54-415.PAN")
        ond = written(OND, "AP-50K.OND")
        self.win._select("subfield", self.sid)
        with mock.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            self.win._import_pvsyst("module", str(pan))            # looked at and declined: nothing changes
        self.assertFalse(any(k.startswith("pan:") for k in self.win.project.modules))
        with mock.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.win._import_pvsyst("module", str(pan))
            self.win._import_pvsyst("inverter", str(ond))
        sf = self.win.project.subfields[0]
        self.assertEqual(sf.module, "pan:Acme Solar AS-54-415")
        self.assertEqual(self.win.project.modules[sf.module]["pmax"], 415.0)
        self.assertEqual(self.win.project.energy["inverters"][0]["record"]["model"], "AP-50K")
        self.win.undo.undo()
        self.assertNotIn("inverters", self.win.project.energy)

    def saved_and_opened_again(self):
        self.win._edited("project", "", {"name": "Rinominato"})
        self.assertTrue(self.win._save())
        q, _notice = model.Project.load(self.file)
        self.assertEqual(q.name, "Rinominato")
        self.assertEqual(self.win.windowTitle().split(" - ")[0], "prova.meridiana")

    def a_narrow_window_puts_the_panels_together_and_back(self):
        from PySide6.QtCore import Qt
        left, right = self.win.docks
        self.win.resize(1500, 800)
        self.app.processEvents()
        self.win._view_mode("both")
        self.win.resize(700, 800)                 # a column of niri
        self.app.processEvents()
        self.assertEqual(self.win.tabifiedDockWidgets(right), [left])
        self.assertTrue(self.win.view_actions["plan"].isChecked())
        self.win.resize(1500, 800)
        self.app.processEvents()
        self.assertEqual(self.win.dockWidgetArea(left), Qt.DockWidgetArea.LeftDockWidgetArea)
        self.assertEqual(self.win.tabifiedDockWidgets(right), [])
        self.assertTrue(self.win.view_actions["both"].isChecked())

    def a_view_chosen_in_a_narrow_window_stays_when_it_widens(self):
        self.win.resize(1500, 800)
        self.app.processEvents()
        self.win._view_mode("both")
        self.win.resize(700, 800)
        self.app.processEvents()
        self.win._view_mode("3d")                 # the designer's choice
        self.win.resize(1500, 800)
        self.app.processEvents()
        self.assertTrue(self.win.view_actions["3d"].isChecked())

    def the_plan_stays_framed_until_moved_by_hand(self):
        plan = self.win.plan
        self.win.resize(1500, 800)
        self.app.processEvents()
        plan.fit()
        self.win.resize(900, 800)
        # the docks and the splitter settle: the plan's size and scale stay the same for a few turns of the events
        self.assertTrue(_setup.wait_settled(self.app, lambda: (plan.viewport().size(), plan.transform().m11())))
        self.assertFalse(plan.user_moved)
        framed = plan.transform().m11()
        plan.fit()
        # framed again by the resize: fitting now changes nothing (with the checks below the views the height may
        # decide both before and after, so the scale itself need not change)
        self.assertAlmostEqual(plan.transform().m11(), framed, places=6)
        plan.translate_view(30, 0)
        scale = plan.transform().m11()
        self.win.resize(1500, 800)
        self.app.processEvents()
        self.assertAlmostEqual(plan.transform().m11(), scale, places=6)

    def q_squares_the_selected_building(self):
        from meridiana import squaring
        b = self.win.project.buildings[0]
        b.footprint = [[0, 0], [40.3, 0.4], [40.0, 20.2], [-0.2, 19.8]]        # traced by hand
        self.win._select("building", b.id)
        self.win._square()
        angles = squaring.corner_angles([tuple(q) for q in self.win.project.buildings[0].footprint])
        for a in angles:
            self.assertAlmostEqual(a, 90.0, delta=0.5)
        self.win.undo.undo()
        self.assertEqual(self.win.project.buildings[0].footprint[1], [40.3, 0.4])

    def the_window_remembers_its_layout(self):
        self.win._view_mode("plan")
        self.win._save_window()
        self.assertTrue(self.paths.window_state_file.exists())
        from meridiana.ui.window import MainWindow
        again = MainWindow(self.paths, config.Config(background="none"))
        self.addCleanup(_setup.dispose, again)
        self.assertTrue(again.restored)
        self.assertTrue(again.view_actions["plan"].isChecked())

    def a_window_closed_before_its_first_layout_leaves_nothing_behind(self):
        import sys
        from unittest import mock

        from meridiana.ui.window import MainWindow
        other = MainWindow(self.paths, config.Config(background="none"))
        other.show()                                    # the first layout waits for the event loop
        _setup.dispose(other)
        with mock.patch.object(sys, "excepthook") as hook:
            self.app.processEvents()
        hook.assert_not_called()

    def wheel(self, widget):
        """A notch of the wheel over the middle of a widget, as Qt delivers it (accepted until refused)."""
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import QApplication
        middle = QPointF(widget.width() / 2, widget.height() / 2)
        event = QWheelEvent(middle, widget.mapToGlobal(middle), QPoint(0, 0), QPoint(0, -120),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
                            False)
        event.setAccepted(True)
        QApplication.sendEvent(widget, event)
        return event.isAccepted()

    def the_wheel_over_a_field_without_the_keyboard_leaves_it_alone(self):
        """The window's share: it puts the guard on the application. The fields and the lists of the panel, the
        chart: widget/test_properties.py (PanelAlone)."""
        from PySide6.QtWidgets import QDoubleSpinBox
        self.win._select("subfield", self.sid)
        self.app.processEvents()
        page = self.win.props.widget()
        spin = next(s for s in page.findChildren(QDoubleSpinBox) if s.maximum() == 60)      # the module tilt
        steps, value = self.win.undo.count(), spin.value()
        self.assertFalse(self.wheel(spin))                  # refused: the form under it scrolls instead
        self.assertEqual((spin.value(), self.win.undo.count()), (value, steps))
        self.assertFalse(self.wheel(self.win.energy_page.monthly.canvas))  # a chart lets the page scroll too

    def a_closed_panel_comes_back_from_the_view_menu_and_its_shortcut(self):
        left, right = self.win.docks
        menus = []

        def walk(menu):
            for a in menu.actions():
                if a.menu():
                    walk(a.menu())
                else:
                    menus.append(a)
        for a in self.win.menuBar().actions():
            walk(a.menu())
        for dock, keys in ((right, "Ctrl+P"), (left, "Ctrl+B")):
            toggle = dock.toggleViewAction()
            self.assertIn(toggle, menus)                    # View > Panels
            self.assertEqual(toggle.shortcut().toString(), keys)
            dock.close()
            self.assertFalse(dock.isVisible())
            toggle.trigger()
            self.assertTrue(dock.isVisible())

    def only_the_drawing_and_back_and_the_default_layout(self):
        from PySide6.QtWidgets import QToolBar
        left, right = self.win.docks
        clean = self.win.clean_action
        self.assertEqual(clean.shortcut().toString(), "Ctrl+0")
        clean.trigger()
        self.assertFalse(left.isVisible() or right.isVisible())
        self.assertFalse(any(t.isVisible() for t in self.win.findChildren(QToolBar)))
        clean.trigger()
        self.assertTrue(left.isVisible() and right.isVisible())
        right.close()
        self.win._view_mode("3d")
        self.win._default_layout()
        self.assertTrue(left.isVisible() and right.isVisible())
        self.assertTrue(self.win.view_actions["both"].isChecked())

    def ctrl_shift_2_shows_the_plan_alone_and_again_both_views(self):
        plan, both = self.win.view_actions["plan"], self.win.view_actions["both"]
        self.assertEqual(plan.shortcut().toString(), "Ctrl+Shift+2")
        self.assertEqual(self.win.view_actions["3d"].shortcut().toString(), "Ctrl+Shift+3")
        self.win._view_mode("both")
        plan.trigger()
        self.assertTrue(plan.isChecked())
        self.assertFalse(self.win.view3d_box.isVisibleTo(self.win))
        plan.trigger()                                      # again: side by side
        self.assertTrue(both.isChecked())
        self.assertTrue(self.win.view3d_box.isVisibleTo(self.win))

    def menu_actions(self) -> list:
        found = []

        def walk(menu):
            for a in menu.actions():
                if a.menu():
                    found.append(a)                 # a command with its own menu (the strategies of the strings)
                    walk(a.menu())
                else:
                    found.append(a)
        for a in self.win.menuBar().actions():
            walk(a.menu())
        return found

    def every_command_has_its_action_its_keys_and_a_menu(self):
        from PySide6.QtGui import QKeySequence

        from meridiana import shortcuts
        menus = self.menu_actions()
        for c in shortcuts.commands():
            with self.subTest(c.id):
                action = self.win.commands[c.id]
                self.assertIn(action, menus)                # never only on a key (an F key above all)
                self.assertEqual([k.toString(QKeySequence.SequenceFormat.PortableText) for k in action.shortcuts()],
                                 list(c.keys))
        self.assertIn("(B)", self.win.commands["tool_building"].toolTip())

    def f8_and_f3_switch_the_ortho_and_the_snaps_of_the_plan(self):
        ortho, snaps = self.win.commands["ortho"], self.win.commands["snaps"]
        self.assertEqual((self.win.plan.ortho, self.win.plan.snaps_on), (False, True))
        ortho.trigger()
        snaps.trigger()
        self.assertEqual((self.win.plan.ortho, self.win.plan.snaps_on), (True, False))
        self.win.plan.set_tool("building")
        self.win.plan.chain = [(0.0, 0.0)]
        from meridiana.ui.plan import to_scene
        self.win.plan._update_cursor(self.win.plan.mapFromScene(to_scene(7.0, 1.0)))
        x, y = self.win.plan.snap.point
        self.assertAlmostEqual(y, 0.0, places=6)            # square to East, the first side
        self.assertAlmostEqual(x, 7.0, delta=0.2)

    def ctrl_j_and_ctrl_shift_m_show_the_checks(self):
        dock = self.win.checks_dock
        toggle = self.win.commands["panel_checks"]
        self.assertTrue(dock.isVisible())
        toggle.trigger()
        self.assertFalse(dock.isVisible())
        _setup.keyboard_or_skip(self, self.win.plan)        # Ctrl+Shift+M moves the keyboard: it must be there
        self.win.commands["focus_checks"].trigger()
        self.assertTrue(dock.isVisible())
        self.app.processEvents()
        self.assertTrue(self.win.checks_page.tree.hasFocus())

    def keys_changed_by_the_designer_are_kept_and_given_back(self):
        from meridiana import shortcuts
        from meridiana.ui.shortcuts_dialog import ShortcutsEditor
        editor = ShortcutsEditor(self.win.bindings)         # what it says of the keys typed: widget/test_preferences.py
        self.addCleanup(_setup.dispose, editor)
        editor.assign("ortho", "Ctrl+B")                    # taken from the Project panel
        self.assertEqual(editor.bindings["panel_project"], [])
        self.win._set_shortcuts(editor.bindings)
        self.assertEqual(self.win.commands["ortho"].shortcut().toString(), "Ctrl+B")
        self.assertEqual(self.win.cfg.shortcuts, {"ortho": ["Ctrl+B"], "panel_project": []})
        saved = config.load(self.paths.config_file)
        self.assertEqual(shortcuts.bindings(saved.shortcuts)["ortho"], ["Ctrl+B"])

    def a_saved_key_a_newer_command_also_has_stays_the_designers_and_is_said(self):
        from meridiana.ui.window import MainWindow
        cfg = config.Config(background="none", shortcuts={"fit": ["Ctrl+L"], "future_command": ["Ctrl+K"]})
        win = MainWindow(self.paths, cfg)
        self.addCleanup(_setup.dispose, win)
        self.assertEqual(win.commands["fit"].shortcut().toString(), "Ctrl+L")
        self.assertEqual(win.commands["assistant"].shortcuts(), [])     # not both: Qt would run neither
        self.assertIn("Ctrl+L", win.hint.text())
        self.assertIn("Settings", win.hint.text())
        win._set_shortcuts(win.bindings)                    # OK in the preferences
        self.assertEqual(cfg.shortcuts["future_command"], ["Ctrl+K"])  # a newer version's command keeps its key
        self.assertEqual(cfg.shortcuts["fit"], ["Ctrl+L"])

    def the_arrows_of_a_field_clicked_again_and_again_are_one_step(self):
        steps = self.win.undo.count()
        for tilt in (16.0, 17.0, 18.0):
            self.win._edited("subfield", self.sid, {"params.tilt": tilt})
        self.assertEqual(self.win.undo.count(), steps + 1)
        self.win._edited("subfield", self.sid, {"params.gap": 0.05})      # another field: a step of its own
        self.assertEqual(self.win.undo.count(), steps + 2)
        self.win.undo.undo()
        self.win.undo.undo()
        self.assertEqual(self.win.project.subfields[0].params["tilt"], 15.0)

    # the journeys

    def test_opened_laid_out_with_nothing_to_save_a_damaged_file_said_and_saved_and_opened_again(self):
        self.an_opened_project_has_nothing_to_save()
        self.the_layout_comes_back_and_is_shown()
        self.the_sun_of_the_3d_view_starts_on_the_design_day_and_moves()
        self.a_new_window_has_nothing_to_save()
        self.a_damaged_file_is_said_and_the_project_in_hand_stays()
        self.saved_and_opened_again()

    def test_a_disk_that_refuses_a_new_revision_and_the_unsaved_changes_kept_aside_and_offered_back(self):
        self.a_disk_that_refuses_is_said_and_the_project_stays_to_save()
        self.a_new_revision_is_a_new_file_next_to_the_old_one()
        self.again()
        self.unsaved_changes_are_kept_aside_and_offered_back()

    def test_from_pvsyst_a_module_and_an_inverter_after_a_look_and_a_project_with_its_variants(self):
        self.a_pvsyst_module_and_inverter_are_imported_after_a_look()
        self.a_pvsyst_project_opens_as_a_new_project_with_its_variants()

    def test_what_goes_wrong_is_said_the_privacy_switches_stop_the_network_and_the_wheel_is_guarded(self):
        self.an_error_nobody_caught_is_told_in_the_status_bar_and_once_in_a_dialog()
        self.a_map_tile_that_fails_is_said_once_a_minute()
        self.the_privacy_switches_stop_the_map_loader_and_the_pvgis_fetch()
        self.the_wheel_over_a_field_without_the_keyboard_leaves_it_alone()

    def test_the_roof_its_eave_its_gable_ends_and_its_ridge_from_the_plan_and_the_properties(self):
        self.the_eave_picked_on_the_plan_and_a_side_made_longer()
        self.again()
        self.a_side_clicked_as_a_gable_end_changes_the_roof_and_is_undone()
        self.again()
        self.the_ridge_height_written_sets_the_slope()

    def test_outlines_drawn_dragged_stretched_squared_and_deleted_each_one_step_of_the_undo(self):
        self.a_building_a_sub_field_and_an_exclusion_drawn_on_the_plan_are_in_the_project_and_undone()
        self.again()
        self.a_dragged_corner_is_one_undoable_edit()
        self.a_side_changed_in_place_stretches_the_outline_as_it_is_now()
        self.again()
        self.q_squares_the_selected_building()
        self.again()
        self.an_obstacle_gets_its_height_from_its_kind_until_given()
        self.del_while_drawing_deletes_nothing()

    def test_the_layout_follows_each_change_only_where_it_touches_and_a_failure_is_marked(self):
        self.a_module_taken_out_and_put_back()
        self.a_change_of_tilt_lays_again_without_moving_the_camera_on_its_own()
        self.again()
        self.the_arrows_of_a_field_clicked_again_and_again_are_one_step()
        self.again()
        self.a_change_lays_out_again_only_the_sub_field_it_touches()
        self.again()
        self.a_layout_that_fails_is_marked_in_the_tree_and_the_properties()

    def test_what_is_typed_in_the_properties_goes_into_the_project_when_confirmed(self):
        self.a_value_typed_in_the_properties_does_not_pull_the_field_away()
        self.again()
        self.a_length_in_the_properties_takes_units_and_a_calculation()
        self.again()
        self.the_name_field_shows_the_name_the_project_kept()

    def test_an_undo_an_edit_from_elsewhere_or_a_result_leave_the_fields_as_the_project_wants(self):
        self.the_page_is_built_again_only_for_another_object_or_other_fields()
        self.again()
        self.an_undo_drops_what_was_being_written_and_enter_keeps_the_project_as_undone()
        self.again()
        self.a_value_confirmed_after_an_edit_from_elsewhere_goes_into_the_project()
        self.again()
        self.a_name_written_across_an_undo_of_a_variant_does_not_go_to_the_other_variant()
        self.again()
        self.a_result_that_comes_back_leaves_the_text_being_written()

    def test_the_panels_follow_the_width_of_the_window_and_the_plan_stays_framed(self):
        self.a_narrow_window_puts_the_panels_together_and_back()
        self.a_view_chosen_in_a_narrow_window_stays_when_it_widens()
        self.win._view_mode("both")                         # the views side by side again, as a new window has them
        self.the_plan_stays_framed_until_moved_by_hand()

    def test_the_panels_close_and_come_back_the_views_alone_and_the_window_keeps_its_layout(self):
        self.a_closed_panel_comes_back_from_the_view_menu_and_its_shortcut()
        self.only_the_drawing_and_back_and_the_default_layout()
        self.ctrl_shift_2_shows_the_plan_alone_and_again_both_views()
        self.the_window_remembers_its_layout()
        self.a_window_closed_before_its_first_layout_leaves_nothing_behind()

    def test_every_command_has_its_action_keys_and_menu_and_the_keys_of_the_designer_are_kept(self):
        self.every_command_has_its_action_its_keys_and_a_menu()
        self.f8_and_f3_switch_the_ortho_and_the_snaps_of_the_plan()
        self.again()
        self.keys_changed_by_the_designer_are_kept_and_given_back()
        self.a_saved_key_a_newer_command_also_has_stays_the_designers_and_is_said()
        self.ctrl_j_and_ctrl_shift_m_show_the_checks()      # last: it needs the keyboard, or it says so


class Moving(Journeys):
    """Move and Rotate in the window (task 16b): M, two clicks on the plan, the building moved with its sub-field in
    one undo step; a value typed; Ctrl at the click that copies; Esc that changes nothing; D for Measure."""

    def plan_event(self, kind, x, y, mods=None):
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtTest import QTest

        from meridiana.ui.plan import to_scene
        plan = self.win.plan
        pos = QPointF(plan.mapFromScene(to_scene(x, y)))
        mods = mods if mods is not None else Qt.KeyboardModifier.NoModifier
        self.app.sendEvent(plan.viewport(), QMouseEvent(QEvent.Type.MouseMove, pos, plan.viewport().mapToGlobal(pos),
                                                        Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, mods))
        if kind == "click":
            QTest.mouseClick(plan.viewport(), Qt.MouseButton.LeftButton, mods, pos.toPoint())

    def key(self, key, mods=None):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.win.plan.setFocus()
        QTest.keyClick(self.win.plan, key, mods if mods is not None else Qt.KeyboardModifier.NoModifier)

    def start(self):
        from PySide6.QtCore import Qt
        bid = self.win.project.buildings[0].id
        self.win._select("building", bid)
        self.key(Qt.Key.Key_M)
        self.assertEqual(self.win.plan.tool, "move")
        self.assertTrue(self.win.tool_actions["move"].isChecked())
        self.win.plan.snaps_on = False
        return bid

    def m_and_two_clicks_move_the_building_with_its_sub_field_in_one_step(self):
        bid = self.start()
        steps = self.win.undo.count()
        self.plan_event("click", 10.0, 10.0)
        self.plan_event("click", 13.0, 14.0)
        b = self.win.project.building(bid)
        tol = 3 * self.win.plan.metres_per_pixel()
        self.assertAlmostEqual(b.footprint[0][0], 3.0, delta=tol)
        self.assertAlmostEqual(b.footprint[0][1], 4.0, delta=tol)
        sf = self.win.project.subfields[0]
        self.assertAlmostEqual(sf.ring[0][0] - b.footprint[0][0], 1.0, places=6)     # moved with it
        self.assertAlmostEqual(sf.ring[0][1] - b.footprint[0][1], 1.0, places=6)
        self.assertEqual(self.win.undo.count(), steps + 1)
        self.assertEqual(self.win.undo.undoText(), "Move")
        self.win.undo.undo()
        self.assertEqual(self.win.project.building(bid).footprint[0], [0, 0])
        self.assertEqual(self.win.project.subfields[0].ring[0], [1, 1])

    def a_value_typed_moves_by_it(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        bid = self.start()
        self.win.plan.setFocus()
        QTest.keyClicks(self.win.plan, "3;-2")
        self.key(Qt.Key.Key_Return)
        self.assertEqual(self.win.project.building(bid).footprint[0], [3.0, -2.0])
        self.assertEqual(self.win.project.subfields[0].ring[0], [4.0, -1.0])

    def ctrl_at_the_click_copies_and_selects_the_copy(self):
        from PySide6.QtCore import Qt
        bid = self.start()
        self.plan_event("click", 10.0, 10.0)
        self.plan_event("click", 10.0, -25.0, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(len(self.win.project.buildings), 2)
        copy = self.win.project.buildings[1]
        self.assertEqual(self.win.project.building(bid).footprint[0], [0, 0])
        self.assertAlmostEqual(copy.footprint[0][1], -35.0, delta=3 * self.win.plan.metres_per_pixel())
        self.assertEqual(self.win.selection, ("building", copy.id))
        self.assertEqual(self.win.undo.undoText(), "Copy")

    def esc_changes_nothing_and_goes_back_to_select(self):
        from PySide6.QtCore import Qt
        self.start()
        before, steps = self.win.snapshot(), self.win.undo.count()
        self.plan_event("click", 10.0, 10.0)
        self.plan_event("move", 15.0, 12.0)
        self.key(Qt.Key.Key_Escape)
        self.assertEqual((self.win.snapshot(), self.win.undo.count()), (before, steps))
        self.assertEqual(self.win.plan.tool, "select")
        self.assertTrue(self.win.tool_actions["select"].isChecked())

    def a_move_refused_says_why_and_changes_nothing(self):
        before = self.win.snapshot()
        self.win._select("subfield", self.sid)
        self.win._transform("subfield", self.sid, {"mode": "move", "dx": 30.0, "dy": 0.0})
        self.assertEqual(self.win.snapshot(), before)
        self.assertIn("pitch", self.win.hint.text())

    def the_arrows_join_in_one_step(self):
        from PySide6.QtCore import Qt
        bid = self.start()
        steps = self.win.undo.count()
        for _i in range(3):
            self.key(Qt.Key.Key_Right)
        self.assertAlmostEqual(self.win.project.building(bid).footprint[0][0], 0.3, places=6)
        self.assertEqual(self.win.undo.count(), steps + 1)

    def d_is_measure_and_r_is_the_rectangle_outside_move_and_turns_inside(self):
        from PySide6.QtCore import Qt
        self.key(Qt.Key.Key_D)
        self.assertEqual(self.win.plan.tool, "measure")
        self.win._set_tool("building")
        self.key(Qt.Key.Key_R)
        self.assertTrue(self.win.plan.rect_mode)                  # outside Move, R is the rectangle
        self.key(Qt.Key.Key_R)
        self.start()
        self.assertIn("R is the rectangle only outside Move", self.win.hint.text())     # said in the hint
        self.key(Qt.Key.Key_R)
        self.assertFalse(self.win.plan.rect_mode)
        self.assertEqual(self.win.plan.gesture.mode, "rotate")    # inside Move, R turns
        self.assertTrue(self.win.tool_actions["rotate"].isChecked())

    def turning_a_sub_field_turns_its_azimuth_and_the_rotate_button_does_it_too(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.win._edited("subfield", self.sid, {"ring": [[10, 5], [30, 5], [30, 15], [10, 15]], "params.azimuth": 10.0})
        self.win._select("subfield", self.sid)
        self.win.commands["tool_rotate"].trigger()
        self.assertEqual((self.win.plan.tool, self.win.plan.gesture.mode), ("move", "rotate"))
        self.assertTrue(self.win.tool_actions["rotate"].isChecked())
        self.win.plan.setFocus()
        QTest.keyClicks(self.win.plan, "30")
        self.key(Qt.Key.Key_Return)
        sf = self.win.project.subfields[0]
        self.assertEqual(sf.params["azimuth"], -20.0)               # 30° to the left: 10° West becomes 20° East
        self.assertEqual(self.win.undo.undoText(), "Rotate")
        self.assertTrue(self.win.tool_actions["rotate"].isChecked())    # the button stays: the next one turns too
        self.assertEqual(self.win.plan._gesture().mode, "rotate")

    # the journeys

    def test_m_and_two_clicks_a_value_typed_ctrl_esc_and_the_arrows_each_one_step_or_none(self):
        self.m_and_two_clicks_move_the_building_with_its_sub_field_in_one_step()
        self.again()
        self.a_value_typed_moves_by_it()
        self.again()
        self.ctrl_at_the_click_copies_and_selects_the_copy()
        self.again()
        self.esc_changes_nothing_and_goes_back_to_select()
        self.again()
        self.the_arrows_join_in_one_step()

    def test_a_move_refused_d_and_r_and_a_sub_field_turned_by_its_azimuth(self):
        self.a_move_refused_says_why_and_changes_nothing()
        self.again()
        self.d_is_measure_and_r_is_the_rectangle_outside_move_and_turns_inside()
        self.again()
        self.turning_a_sub_field_turns_its_azimuth_and_the_rotate_button_does_it_too()


class EnergyPages(Journeys):
    """The three energy pages, computed from a weather year put in the cache: no network. A formula drawn once and
    the report are in widget/test_report.py; the year without the weather, in calcoli/test_pipeline.py."""

    def cache(self):
        from _fixtures import clear_sky_meteo
        return clear_sky_meteo(45.5226, 9.03)

    def compute(self):
        self.win.energy = {}
        self.win._compute_energy(fetch=False)
        self.assertTrue(wait_until(self.app, lambda: bool(self.win.energy), 60), "the energy job did not come back")
        return self.win.energy

    def production_consumption_and_economics_from_the_cache(self):
        e = self.compute()
        self.assertIsNone(e.get("error_sim"), e.get("error_sim"))
        self.assertGreater(e["sim"].energy_kwh, 1000)
        self.assertGreater(e["load"].annual_kwh, 0)
        self.assertIn("npv", e["econ"].kpi)
        self.assertNotEqual(self.win.energy_page.tiles[0].value.text(), "–")
        self.assertNotEqual(self.win.economics_page.tiles[5].value.text(), "–")
        from meridiana import phases
        for pid in phases.ids():
            self.win.show_phase(pid)
            self.app.processEvents()

    def without_bills_the_consumption_follows_the_context(self):
        e = self.compute()
        sim, load = e["sim"], e["load"]
        self.assertGreater(sim.p_stc_kw, 20.0)                       # a roof of 40 x 20 m: a business
        self.assertAlmostEqual(load.annual_kwh, round(sim.energy_kwh, -2), places=3)
        page = self.win.consumption_page
        self.assertIn(page.profile.itemText(0).split(": ")[-1], page.profile.currentText())
        self.assertTrue(page.guess_note.isVisibleTo(page.side))     # the form stands in the right column
        self.win._energy_edited("consumption", "annual_kwh", 30000.0)
        e = self.compute()
        self.assertAlmostEqual(e["load"].annual_kwh, 30000.0, places=3)

    def the_checks_gather_the_project_and_lead_to_the_place(self):
        self.compute()
        page = self.win.checks_page
        areas = {i.area for i in page.items}
        self.assertIn("connection", areas)                         # 40 x 20 m of modules: CEI 0-21 has its say
        self.assertTrue(any("8.6.2" in i.source for i in page.items))
        # a section per level present (the default view, task 17e), and per area more than one
        self.assertEqual(page.tree.topLevelItemCount(), len({i.level for i in page.items}))
        page.set_view("area")
        self.assertGreater(page.tree.topLevelItemCount(), 1)
        self.assertIs(self.win.checks_dock.widget(), page)          # a panel below the views, in every tab
        self.assertEqual(self.win.checks_dock.windowTitle(), page.title("Checks"))
        page.navigate.emit(("phase", "production"))
        self.assertEqual(self.win.phase(), "production")
        sid = self.win.project.subfields[0].id
        page.navigate.emit(("subfield", sid))
        self.assertEqual((self.win.phase(), self.win.selection), ("model", ("subfield", sid)))

    def a_fix_from_the_checks_page_is_applied_and_undone(self):
        from PySide6.QtCore import Qt
        sid = self.win.project.subfields[0].id
        self.win._action("empty", "subfield", sid)
        self.assertTrue(wait_until(self.app, lambda: not self.win.project.subfields[0].filled))
        page = self.win.checks_page
        self.win._show_checks()
        n = next(k for k, i in enumerate(page.items) if i.fix == ("action", "fill", "subfield", sid))
        row = next(page.tree.topLevelItem(g).child(c) for g in range(page.tree.topLevelItemCount())
                   for c in range(page.tree.topLevelItem(g).childCount())
                   if page.tree.topLevelItem(g).child(c).data(1, Qt.ItemDataRole.UserRole) == n)
        # R126: shown first, the views on it; taken back, nothing left to redo; kept, an ordinary step
        steps = self.win.session.undo.count()
        fix = page.row_buttons(row.data(1, Qt.ItemDataRole.UserRole))["fix"]
        fix.click()
        self.assertTrue(self.win.project.subfields[0].filled)
        self.assertTrue(page.previewing())
        self.assertIn("Lay the modules", page.preview_text.text())
        page.preview_drop.click()
        self.assertFalse(page.previewing())
        self.assertFalse(self.win.project.subfields[0].filled)
        self.assertEqual(self.win.session.undo.count(), steps)
        self.assertFalse(self.win.session.undo.can_redo())
        self.assertIn("taken back", self.win.statusBar().currentMessage())
        n = next(k for k, i in enumerate(page.items) if i.fix == ("action", "fill", "subfield", sid))
        page.row_buttons(n)["fix"].click()
        page.preview_keep.click()
        self.assertTrue(self.win.project.subfields[0].filled)
        self.assertEqual(self.win.session.undo.count(), steps + 1)
        self.win.undo.undo()
        self.assertFalse(self.win.project.subfields[0].filled)
        n = next(k for k, i in enumerate(page.items) if i.fix == ("action", "fill", "subfield", sid))
        page.row_buttons(n)["fix"].click()                  # a preview, then another change: the fix is kept
        self.win._edited("subfield", sid, {"name": "Altro"})
        self.assertFalse(page.previewing())
        self.assertTrue(self.win.project.subfields[0].filled)
        self.win.undo.undo()
        self.win.undo.undo()

    def the_site_sets_the_rules_and_their_notes_are_copied(self):
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QComboBox
        self.compute()
        self.win._select("site", "")
        combos = self.win.props.widget().findChildren(QComboBox)
        obligation = next(c for c in combos if c.findData("renovation") >= 0)
        obligation.setCurrentIndex(obligation.findData("new"))
        self.assertEqual(self.win.project.rules.get("obligation"), "new")
        self.win._show_checks()
        page = self.win.checks_page
        self.assertTrue(any(i.area == "rules" and i.text.startswith("N24") for i in page.items))
        page.copy_button.click()
        text = QGuiApplication.clipboard().text()
        self.assertIn("4. MINIMUM RENEWABLE CAPACITY OBLIGATION", text)
        self.assertIn("Source: ", text)
        self.win.undo.undo()
        self.assertEqual(self.win.project.rules, {})

    def variants_keep_their_own_design_and_are_compared(self):
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QInputDialog
        self.compute()
        base = self.win.project.variant
        with mock.patch.object(QInputDialog, "getText", return_value=("Inclinati 30°", True)):
            self.win._new_variant()
        self.assertEqual([v["name"] for v in self.win.project.variants], ["Base", "Inclinati 30°"])
        self.assertEqual(self.win.variant_bar.currentText(), "Inclinati 30°")
        sid = self.win.project.subfields[0].id
        self.win._edited("subfield", sid, {"params.tilt": 30.0})
        self.win._switch_variant(base)
        self.assertEqual(self.win.project.subfields[0].params["tilt"], 15.0)      # the base as it was
        self.assertEqual(self.win.variant_bar.currentText(), "Base")
        self.win._compare_variants()
        dialog = self.win.compare_dialog
        self.addCleanup(dialog.close)
        self.assertTrue(wait_until(self.app, lambda: len(dialog.figures) == 2, 120), dialog.status.text())
        first, second = dialog.summaries()
        self.assertNotIn("error", first, first)
        self.assertNotAlmostEqual(first["kwh"], second["kwh"], delta=1.0)           # the tilt counts
        self.assertTrue(wait_until(self.app, dialog.copy_button.isEnabled))
        dialog.copy_button.click()
        self.assertIn("Production (kWh/year)", QGuiApplication.clipboard().text())
        self.win.undo.undo()                                                        # the switch, undone
        self.assertEqual(self.win.project.subfields[0].params["tilt"], 30.0)

    def an_edit_on_a_page_is_undoable_and_recomputed(self):
        self.compute()
        self.win._energy_edited("energy", "losses.soiling", 5.0)
        self.assertEqual(self.win.project.energy["losses"]["soiling"], 5.0)
        e = self.compute()
        soiling = next(c for c in e["sim"].chain if c.key == "soiling")
        self.assertAlmostEqual(soiling.change, -5.0, places=6)
        self.win.undo.undo()
        self.assertNotIn("soiling", self.win.project.energy.get("losses", {}))

    def a_measured_curve_from_a_csv(self):
        import pandas as pd
        times = pd.date_range("2025-01-01", periods=24 * 365, freq="h")
        path = Path(tempfile.mkdtemp()) / "curva.csv"
        path.write_text("data;kWh\n" + "\n".join(f"{t.strftime('%d/%m/%Y %H:%M')};1,5" for t in times), encoding="utf-8")
        self.win._import_curve(str(path), "kWh")
        self.assertEqual(len(self.win.project.consumption["measured"]["values"]), 24 * 365)
        e = self.compute()
        self.assertAlmostEqual(e["load"].annual_kwh, 1.5 * 8760, delta=1.5 * 48)

    def strings_are_suggested_and_checked_with_an_inverter_from_the_catalogue(self):
        from meridiana import catalog
        e = self.compute()
        self.assertIn("error", e["strings"])                     # sized by itself: no window to check against
        rec = next(r for r in catalog.search("inverters", "SCA100K-T-US-480"))
        self.win._add_inverter(rec, "Add")
        e = self.compute()
        self.assertEqual(e["plant"].strings, [])                 # an inverter added makes no string (R118)
        self.win.strategy_actions["serpentine"].trigger()           # «Propose the strings»
        e = self.compute()
        plant = e["plant"]
        self.assertFalse(plant.auto)
        self.assertTrue(plant.strings)
        plans = [slot.plan for slot in plant.inputs.values() if slot.used]
        self.assertTrue(plans and all(any(c.key == "uoc" for c in p.checks) for p in plans))
        self.assertEqual(len({len(s.modules) for s in plant.strings}), 1)        # identical strings
        self.assertTrue(any(i.area == "strings" and i.target == ("phase", "plant") for i in self.win.checks_page.items))
        self.assertTrue(self.win.plan.items_by_kind.get("wiring"))          # drawn on the plan
        self.win.plan.show_wiring(False)
        self.assertFalse(self.win.plan.items_by_kind.get("wiring"))

    def a_result_draws_only_what_is_on_screen(self):
        from meridiana.ui import charts
        from meridiana.ui.pedigree import formula_png
        self.win.show_phase("model")                        # on the model: the energy pages are hidden
        formula_png.cache_clear()
        self.compute()
        page = self.win.energy_page
        self.assertIsNotNone(page.monthly.pending)          # noted, not drawn
        self.assertTrue(page.pedigree.pending)
        self.assertEqual(formula_png.cache_info().currsize, 0)
        self.assertTrue(self.win.busy.isHidden())           # the status bar said it, and no longer does
        self.assertIsNone(page.monthly.plot)                # no pyqtgraph widget made yet (task 18c, step 10)
        with mock.patch.object(charts, "_enqueue", wraps=charts._enqueue) as queued:
            self.win.show_phase("production")
        self.assertEqual(queued.call_count, 1)              # the production page: its first chart, shown
        self.assertTrue(wait_until(self.app, lambda: page.monthly.pending is None, 10))
        self.assertIsNotNone(page.losses_chart.pending)     # a tab of its own, still waiting
        self.assertIsNone(page.losses_chart.plot)
        self.assertGreater(len(page.monthly.numbers.rows), 0)
        self.assertEqual(type(page.monthly.canvas).__name__, "Plot")             # pyqtgraph's, now
        # the consumption page shows its four charts one at a time: all queued at the show, none drawn before
        # the event loop turns, then every one drawn
        cons = self.win.consumption_page
        with mock.patch.object(charts, "_enqueue", wraps=charts._enqueue) as queued:
            self.win.show_phase("consumption")
        shown = [c for c in (cons.monthly, cons.day, cons.week, cons.duration) if c.isVisible()]
        self.assertTrue(shown)                              # the consumption page, with at least one chart in view
        self.assertEqual(queued.call_count, len(shown))
        self.assertTrue(all(c.pending is not None for c in shown))
        self.assertTrue(wait_until(self.app, lambda: all(c.pending is None for c in shown), 10))

    # the journeys

    def test_the_pages_draw_only_what_is_on_screen_the_year_the_consumption_the_economics_and_their_edits(self):
        self.a_result_draws_only_what_is_on_screen()        # first: nothing of the pages drawn yet
        self.production_consumption_and_economics_from_the_cache()
        self.again()
        self.without_bills_the_consumption_follows_the_context()
        self.again()
        self.an_edit_on_a_page_is_undoable_and_recomputed()
        self.again()
        self.a_measured_curve_from_a_csv()

    def test_the_checks_gather_the_project_lead_to_the_place_apply_a_fix_and_carry_the_rules(self):
        self.the_checks_gather_the_project_and_lead_to_the_place()
        self.again()
        self.a_fix_from_the_checks_page_is_applied_and_undone()
        self.again()
        self.the_site_sets_the_rules_and_their_notes_are_copied()

    def test_the_variants_compared_and_the_strings_proposed_with_an_inverter_from_the_catalogue(self):
        self.variants_keep_their_own_design_and_are_compared()
        self.again()
        self.strings_are_suggested_and_checked_with_an_inverter_from_the_catalogue()


class PlantWindow(Journeys):
    """A window on the sample project with a weather year in the cache, for the Plant phase (task 16d); a question
    answered Yes."""
    size = (1400, 960)

    def answers(self):
        from PySide6.QtWidgets import QMessageBox
        return {"question": QMessageBox.StandardButton.Yes}

    def cache(self):
        from _fixtures import clear_sky_meteo
        return clear_sky_meteo(45.5226, 9.03)

    def choose(self, rec: dict) -> None:
        from PySide6.QtWidgets import QDialog
        fake = mock.MagicMock()
        fake.return_value.exec.return_value = QDialog.DialogCode.Accepted
        fake.return_value.chosen.return_value = rec
        with mock.patch("meridiana.ui.window.CatalogDialog", fake):
            self.win.commands["inverter_catalog"].trigger()

    def plant(self, condition=lambda p: True):
        self.assertTrue(wait_until(self.app, lambda: not self.win.plant_pending() and self.win.plant_state is not None
                                   and condition(self.win.plant_state), 60))
        return self.win.plant_state


class PlantPhase(PlantWindow):
    """The Plant phase of task 16d, step 3: between Model and Production, the plan lent with the strings shown, the
    inverters in the right panel; Production keeps a reference to it."""

    def the_plant_is_the_second_phase_reached_with_ctrl_tab_and_lends_the_plan(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        QTest.keyClick(self.win, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.win.phase(), "plant")
        self.assertIs(self.win.tabs.currentWidget(), self.win.plant_page)
        self.assertIs(self.win.plan.parentWidget(), self.win.plant_page.host)
        self.assertTrue(self.win.plan.isVisible())
        self.assertTrue(self.win.plan.wiring_on)                        # W always on in this phase
        self.assertIs(self.win.inspector.currentWidget(), self.win.plant_inspector)
        self.assertEqual(self.win.docks[1].windowTitle(), "Inverters")
        self.assertEqual([b.property("tool") for b in self.win.bars["plant"].buttons().values()],
                         ["inverter_catalog", "inverter_auto", "strings_auto", "strings_complete", "strings_manual"])
        QTest.keyClick(self.win, Qt.Key.Key_PageUp, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.win.phase(), "model")
        self.assertEqual(self.win.split.indexOf(self.win.plan), 0)     # back beside the 3D view
        self.assertTrue(self.win.plan.isVisible())

    def the_reference_in_production_leads_to_the_plant(self):
        self.win.show_phase("production")
        ref = self.win.inverter_reference
        self.assertTrue(ref.isVisible())
        self.assertTrue(self.win.energy_page.inv_label.parentWidget().isHidden())     # the old group, hidden
        self.assertIn("sized by itself", ref.label.text())
        ref.button.click()
        self.assertEqual(self.win.phase(), "plant")

    def an_inverter_chosen_from_the_catalogue_joins_the_list_and_production_says_so(self):
        rec = inverter_record()
        self.win.show_phase("plant")
        self.choose(rec)
        self.assertEqual(self.win.project.energy["inverters"], [{"record": rec, "count": 1, "name": ""}])
        self.assertIn("AC-20K", self.win.inverter_reference.label.text())
        self.assertIn("AC-20K", self.win.plant_page.inv_label.text())
        plant = self.plant(lambda p: len(p.units) == 1 and p.units[0].checkable)
        self.assertEqual(plant.strings, [])                              # no string by itself (R118)
        self.assertTrue(plant.left)
        self.assertEqual(len(self.win.plant_inspector.entry_rows), 1)
        self.win.plant_inspector.entry_rows[0][1].setValue(3)           # how many: three alike
        self.assertEqual(self.win.project.energy["inverters"][0]["count"], 3)
        self.assertIn("3 x", self.win.inverter_reference.label.text())
        plant = self.plant(lambda p: len(p.units) == 3)
        self.assertEqual([u.number for u in plant.units], [1, 2, 3])
        self.choose(rec)                                                  # the same model again: one more of it
        self.assertEqual(self.win.project.energy["inverters"][0]["count"], 4)
        self.win.undo.undo()
        self.win.undo.undo()
        self.assertEqual(self.win.project.energy["inverters"][0]["count"], 1)

    def a_sub_field_sent_to_an_inverters_input_and_sized_by_itself(self):
        rec = inverter_record(ac_power_nominal_w=10000)
        self.choose(rec)
        self.win.show_phase("plant")
        self.win._select("subfield", self.sid)
        self.assertTrue(self.win.plant_inspector.subfield_group.isVisibleTo(self.win.plant_inspector))
        self.win._assign_subfield(self.sid, 1, 2)
        self.assertEqual((self.win.project.subfields[0].params["inverter"], self.win.project.subfields[0].params["mppt"]),
                         (1, 2))
        self.win.strategy_actions["serpentine"].trigger()                 # «Propose»: there, as the sub-field says
        plant = self.plant(lambda p: bool(p.strings))
        self.assertEqual({(s.inverter, s.mppt) for s in plant.strings}, {(1, 2)})
        self.win._assign_subfield(self.sid, 0, 0)                        # otherwise only input 2 may be used
        from PySide6.QtWidgets import QInputDialog
        with mock.patch("meridiana.ui.window.catalog.load", return_value=(rec,)), \
                mock.patch.object(QInputDialog, "getItem", return_value=("Acme", True)):
            self.win.commands["inverter_auto"].trigger()
        self.assertGreaterEqual(self.win.project.energy["inverters"][0]["count"], 1)
        self.assertEqual(sum(len(r["modules"]) for r in self.win.project.energy["strings"]["runs"]),
                         self.win.results[self.sid].count)

    def sizing_asks_the_brand_remembers_it_and_says_the_result(self):
        from PySide6.QtWidgets import QInputDialog
        rec = inverter_record(model="AC-10K", ac_power_nominal_w=10000)
        with mock.patch("meridiana.ui.window.catalog.brands", return_value=["Acme", "Other"]), \
                mock.patch("meridiana.ui.window.catalog.load", return_value=(rec,)), \
                mock.patch.object(QInputDialog, "getItem", return_value=("Acme", True)) as asked:
            self.win.commands["inverter_auto"].trigger()
            self.assertEqual(asked.call_count, 1)
        entry = self.win.project.energy["inverters"][0]
        self.assertEqual(entry["record"], rec)
        self.assertGreaterEqual(entry["count"], 1)
        self.assertEqual(sum(len(r["modules"]) for r in self.win.project.energy["strings"]["runs"]),
                         self.win.results[self.sid].count)
        self.assertEqual(self.win.project.energy["inverter_maker"], "Acme")
        message = self.win.statusBar().currentMessage()
        self.assertIn("AC-10K", message)
        self.assertIn("DC/AC", message)
        before = self.win.project.to_json()
        with mock.patch("meridiana.ui.window.catalog.brands", return_value=["Acme", "Other"]), \
                mock.patch.object(QInputDialog, "getItem", return_value=("Acme", False)) as cancelled:
            self.win.commands["inverter_auto"].trigger()
        self.assertEqual(cancelled.call_args.args[4], 0)                 # the remembered brand is preselected
        self.assertEqual(self.win.project.to_json(), before)

    def sizing_chooses_the_model_and_count_together(self):
        from PySide6.QtWidgets import QInputDialog
        self.win._entries_edit("Clear", lambda entries: entries.clear())
        from meridiana.energy import system
        good = self.win.session.good_results()
        p_stc = sum(a.p_stc for a in system.arrays_of(self.win.project, good))
        target = p_stc / 1.1
        room = {"mppt_count": 4, "dc_current_max_per_mppt_a": [60] * 4,
                "dc_isc_max_per_mppt_a": [100] * 4}
        near = inverter_record(model="NEAR", ac_power_nominal_w=round(target * 0.975), **room)
        better = inverter_record(model="BETTER", ac_power_nominal_w=round(target * 1.22), **room)
        with mock.patch("meridiana.ui.window.catalog.load", return_value=(near, better)), \
                mock.patch.object(QInputDialog, "getItem", return_value=("Acme", True)):
            self.win.commands["inverter_auto"].trigger()
        entry = self.win.project.energy["inverters"][0]
        self.assertEqual(entry["record"]["model"], "NEAR")
        self.assertEqual(entry["count"], 1)

    def test_the_plant_phase_lends_the_plan_production_leads_to_it_and_its_inverters_and_inputs(self):
        self.the_plant_is_the_second_phase_reached_with_ctrl_tab_and_lends_the_plan()
        self.the_reference_in_production_leads_to_the_plant()   # before an inverter is chosen: sized by itself
        self.an_inverter_chosen_from_the_catalogue_joins_the_list_and_production_says_so()
        self.again()
        self.a_sub_field_sent_to_an_inverters_input_and_sized_by_itself()
        self.again()
        self.sizing_asks_the_brand_remembers_it_and_says_the_result()
        self.again()
        self.sizing_chooses_the_model_and_count_together()


class Stringing(PlantWindow):
    """The strings in the Plant phase (R114-R119, Daniel 25/10/2026): nothing makes them by itself; Meridiana proposes,
    completes or deletes them only when asked, each one undo step; a string drawn by hand with clicks and drags, the
    order numbered, Backspace, Enter and Esc, a module of another string refused unless Shift moves it, a skipped
    module drawn as a jump; the list of the right panel chooses a string and brings it into view, Del deletes it, «+»
    draws one on its input; no card over the plan. The strings in the report: widget/test_report.py."""

    def setUp(self):
        super().setUp()
        self.ready()

    def ready(self) -> None:
        """An inverter from the catalogue, the Plant phase on the plan fitted: no string yet."""
        self.choose(inverter_record())
        self.win.show_phase("plant")
        self.app.processEvents()
        self.win.plan.fit()
        self.plant(lambda p: len(p.units) == 1 and p.units[0].checkable)

    def points(self, n: int, row: int = 0) -> list:
        """The first `n` modules of a row, in order along it: (key, the point of the plan's viewport)."""
        from PySide6.QtCore import QPointF
        r = self.win.results[self.sid]
        mods = sorted((pm for pm in r.modules if pm.row == row and pm.level == 0), key=lambda pm: pm.slot)[:n]
        self.assertEqual(len(mods), n)
        return [(f"{self.sid}/{pm.key}", self.win.plan.mapFromScene(QPointF(pm.centre[0], -pm.centre[1])))
                for pm in mods]

    def mouse(self, kind: str, point, button=None, mods=None) -> None:
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtWidgets import QApplication
        button = button or Qt.MouseButton.LeftButton
        mods = mods or Qt.KeyboardModifier.NoModifier
        types = {"press": QEvent.Type.MouseButtonPress, "move": QEvent.Type.MouseMove,
                 "release": QEvent.Type.MouseButtonRelease, "double": QEvent.Type.MouseButtonDblClick}
        viewport = self.win.plan.viewport()
        local = QPointF(point)
        held = button if kind in ("press", "move", "double") else Qt.MouseButton.NoButton
        event = QMouseEvent(types[kind], local, QPointF(viewport.mapToGlobal(point)),
                            Qt.MouseButton.NoButton if kind == "move" else button, held, mods)
        QApplication.sendEvent(viewport, event)

    def click(self, point, button=None, mods=None) -> None:
        self.mouse("press", point, button, mods)
        self.mouse("release", point, button, mods)
        self.assertTrue(wait_until(self.app, lambda: not self.win.plant_pending(), 30))

    def key(self, key) -> None:
        from PySide6.QtTest import QTest
        QTest.keyClick(self.win.plan, key)

    def runs(self) -> list:
        return [list(r["modules"]) for r in (self.win.project.energy.get("strings") or {}).get("runs") or []]

    def zoom_on_row(self, n: int = 8) -> None:
        """The plan framed on the first `n` modules of the first row."""
        from PySide6.QtCore import QRectF
        r = self.win.results[self.sid]
        mods = sorted((pm for pm in r.modules if pm.row == 0 and pm.level == 0), key=lambda pm: pm.slot)[:n]
        xs, ys = [pm.centre[0] for pm in mods], [-pm.centre[1] for pm in mods]
        self.win.plan.fit(QRectF(min(xs), min(ys) - 1, max(xs) - min(xs), max(ys) - min(ys) + 2))

    def nothing_comes_by_itself_and_propose_complete_and_delete_all_come_when_asked(self):
        from PySide6.QtCore import QPointF
        from PySide6.QtWidgets import QWidget
        plant = self.plant()
        self.assertEqual((plant.strings, plant.auto), ([], False))          # an inverter chosen: no string (R118)
        self.assertTrue(plant.left)
        left = next(i for i in self.win.checks_page.items if "in no string" in i.text)
        self.assertEqual(left.fix, ("command", "strings_complete"))
        host = self.win.plant_page.host                                      # nothing over the plan (R119)
        self.assertEqual([w for w in host.findChildren(QWidget) if w.parentWidget() is host and w.isVisible()],
                         [self.win.plan])
        steps = self.win.undo.count()
        self.win.strategy_actions["rows"].trigger()                       # «Propose», a row per string: no question
        self.assertEqual(self.dialogs, [])
        plant = self.plant(lambda p: bool(p.strings))
        self.assertEqual((self.win.undo.count(), self.win.undo.undoText()), (steps + 1, "Propose the strings: one row "
                                                                                         "per string"))
        strings = self.win.project.energy["strings"]
        self.assertEqual(strings["strategy"], "rows")
        self.assertNotIn("auto", strings)                                    # the designer's from now on
        tag = next(it for it in self.win.plan.items_by_kind["wiring"] if it.data(0) == "string")
        first = plant.strings[tag.data(1)].modules[0][2]
        anchor = self.win.plan.mapFromScene(QPointF(first[0], -first[1]))
        top = QPointF(self.win.plan.mapFromScene(tag.pos())) + tag.offset + tag.rect.topLeft()
        self.assertAlmostEqual(anchor.y() - top.y(), tag.boundingRect().height() + 6, delta=1.0)
        mine = self.runs()
        self.choose(inverter_record(model="AC-10K", ac_power_nominal_w=10000))      # a second inverter
        plant = self.plant(lambda p: len(p.units) == 2)
        self.assertEqual(self.runs(), mine)                                  # nothing moved, nothing came
        self.assertFalse(any(s.inverter == 2 for s in plant.strings))
        self.assertIn("inputs are free", self.win.statusBar().currentMessage())
        n = len(plant.strings)
        self.win.commands["strings_complete"].trigger()                      # the modules left, around mine
        plant = self.plant(lambda p: len(p.strings) > n)
        self.assertEqual(self.runs()[:n], mine)
        self.assertEqual(self.win.undo.undoText(), "Complete the strings")
        self.dialogs.clear()
        self.win.strategy_actions["serpentine"].trigger()                    # over strings: asked first
        self.assertEqual([d[0] for d in self.dialogs], ["question"])
        self.dialogs.clear()
        self.win.commands["strings_clear"].trigger()                         # all deleted: asked, one step
        self.assertEqual([d[0] for d in self.dialogs], ["question"])
        plant = self.plant(lambda p: not p.strings)
        self.assertEqual(self.win.undo.undoText(), "Delete all the strings")
        self.win.undo.undo()
        self.plant(lambda p: bool(p.strings))

    def a_string_is_drawn_numbered_taken_back_closed_and_given_up(self):
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtWidgets import QToolButton
        lst = self.win.plant_inspector.list
        self.assertEqual(set(lst.adders), {(1, 1), (1, 2)})
        add = lst.adders[(1, 2)]
        self.assertIsInstance(add, QToolButton)                              # a tool button with Lucide's «plus»
        self.assertFalse(add.icon().isNull())
        self.assertIn("input 2 of inverter 1", add.toolTip())
        self.zoom_on_row()                                                    # the modules large enough to number
        keys = [k for k, _p in self.points(6)]

        def at(i):
            return self.points(6)[i][1]
        steps = self.win.undo.count()
        add.click()
        self.assertIsNotNone(self.win.plan.draft)
        self.assertTrue(self.win.stringing_action.isChecked())
        from meridiana.ui.sections import ACTIVE_ROLE
        head = lst.input_heads[(1, 2)]
        self.assertTrue(head.data(0, ACTIVE_ROLE))
        # the string being drawn in the strip's corner, nothing over the plan (R181, Daniel 26/10/2026: «la pillola
        # che compare è troppo invasiva, andrebbe portata in un angolo tipo dove c'è la legenda»)
        card = self.win.plant_page.draft_card
        self.assertTrue(card.isVisibleTo(self.win))
        self.assertFalse(self.win.plant_page.texts.isVisibleTo(self.win))     # the summary steps aside
        self.assertEqual(card.symbol_name, "warning")                           # still being drawn: to check
        for text in ("Inverter 1", "Acme AC-20K", "Input 2", "0 modules", "Enter", "double click", "Backspace", "Esc"):
            self.assertIn(text, card.text)
        self.assertFalse(any(it.data(0) == "draft_status" for it in self.win.plan.scene().items()))
        self.assertIn("Acme AC-20K", self.win.plant_page.inv_label.text())
        with mock.patch.object(self.win.plan, "_draw_wiring", wraps=self.win.plan._draw_wiring) as wiring, \
                mock.patch.object(self.win.plan, "_draw_draft", wraps=self.win.plan._draw_draft) as draft:
            self.mouse("move", QPointF(30, 30))
        wiring.assert_not_called()
        draft.assert_not_called()
        for i in (0, 1, 3, 4):                                               # the third skipped
            self.click(at(i))
        self.assertEqual([f"{sf}/{k}" for sf, k in self.win.plan.draft], [keys[i] for i in (0, 1, 3, 4)])
        numbers = sorted(it.text for it in self.win.plan.items_by_kind["draft"] if hasattr(it, "text"))
        self.assertEqual(numbers, ["1", "2", "3", "4"])                    # the order on the modules
        self.assertIn("modules", self.win.plant_page.strings_label.text())
        slot = self.plant().inputs[(1, 2)]
        lo, hi = slot.series
        for n, symbol, words in ((0, "warning", f"{lo} short"), (1, "warning", f"{lo - 1} short"),
                                 (lo, "check", "fine"), (hi + 1, "stop", "1 too many")):
            self.win._draft_changed([keys[0]] * n)
            self.assertEqual(card.symbol_name, symbol)
            self.assertIn(words, card.text)
            self.assertIn(f"{n} module" + ("" if n == 1 else "s"), card.text)
            self.assertIn(f"{lo} to {hi}", card.text)
        self.win._draft_changed(self.win.plan.draft)
        self.key(Qt.Key.Key_Backspace)
        self.assertEqual(len(self.win.plan.draft), 3)
        self.key(Qt.Key.Key_Escape)                                          # given up: nothing changed
        self.assertIsNone(self.win.plan.draft)
        self.assertFalse(card.isVisibleTo(self.win))
        self.assertTrue(self.win.plant_page.texts.isVisibleTo(self.win))       # the summary back
        self.assertFalse(head.data(0, ACTIVE_ROLE))
        self.assertNotIn("Inverter 1 · Acme AC-20K · Input 2", self.win.plant_page.inv_label.text())
        self.assertEqual(self.win.undo.count(), steps)
        self.assertFalse(self.win.stringing_action.isChecked())
        add.click()
        for i in (0, 1, 3, 4, 5):
            self.click(at(i))
        self.key(Qt.Key.Key_Return)                                          # closed: one step
        self.assertFalse(card.isVisibleTo(self.win))
        self.assertFalse(lst.input_heads[(1, 2)].data(0, ACTIVE_ROLE))
        self.assertEqual(self.runs(), [[keys[i] for i in (0, 1, 3, 4, 5)]])
        self.assertEqual(self.win.undo.count(), steps + 1)
        plant = self.plant(lambda p: len(p.strings) == 1)
        self.assertEqual((plant.strings[0].inverter, plant.strings[0].mppt), (1, 2))
        # the module skipped: a dashed jump around it, not filled in the string's colour (R117)
        items = self.win.plan.items_by_kind["wiring"]
        dashed = [it for it in items if hasattr(it, "pen") and it.pen().style() == Qt.PenStyle.DashLine]
        self.assertTrue(dashed)
        fills = [it for it in items if hasattr(it, "brush") and it.brush().style() == Qt.BrushStyle.SolidPattern
                 and hasattr(it, "path") and it.zValue() < 35]
        r = self.win.results[self.sid]
        centre = {f"{self.sid}/{pm.key}": QPointF(pm.centre[0], -pm.centre[1]) for pm in r.modules}
        self.assertTrue(any(f.path().contains(centre[keys[0]]) for f in fills))
        self.assertFalse(any(f.path().contains(centre[keys[2]]) for f in fills))
        self.assertEqual(self.dialogs, [])

    def a_module_of_another_string_is_refused_and_shift_moves_it_and_a_double_click_draws_it_again(self):
        from PySide6.QtCore import Qt
        lst = self.win.plant_inspector.list
        keys = [k for k, _p in self.points(6)]

        def at(i):
            return self.points(6)[i][1]
        lst.adders[(1, 1)].click()
        for i in range(4):
            self.click(at(i))
        self.key(Qt.Key.Key_Enter)
        self.plant(lambda p: len(p.strings) == 1)
        lst.adders[(1, 2)].click()
        self.click(at(0))                                                    # in string 1.1.1: refused, said
        self.assertEqual(self.win.plan.draft, [])
        self.assertIn("Shift", self.win.hint.text())
        self.click(at(0), mods=Qt.KeyboardModifier.ShiftModifier)            # moved
        self.click(at(4))
        self.key(Qt.Key.Key_Return)
        self.assertEqual(self.runs(), [keys[1:4], [keys[0], keys[4]]])
        self.assertIn("moved from string 1.1.1", self.win.statusBar().currentMessage())
        self.win.undo.undo()
        self.assertEqual(self.runs(), [keys[:4]])
        plant = self.plant(lambda p: len(p.strings) == 1)
        self.mouse("double", at(2))                                          # drawn again from its modules
        self.assertEqual(len(self.win.plan.draft), 4)
        self.assertEqual(self.win.plan.draft_index, 0)
        self.key(Qt.Key.Key_Backspace)
        self.click(at(5))
        self.key(Qt.Key.Key_Return)
        self.assertEqual(self.runs(), [keys[:3] + [keys[5]]])
        self.assertEqual(self.win.undo.undoText(), f"Draw string {plant.strings[0].label} again")
        lst.adders[(1, 2)].click()                                           # an undo under a string being drawn
        self.click(at(4))
        self.win.undo.undo()
        self.assertIsNone(self.win.plan.draft)
        self.assertIn("given up", self.win.hint.text())

    def the_list_chooses_a_string_brings_it_into_view_and_del_deletes_it(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        self.win.strategy_actions["rows"].trigger()
        plant = self.plant(lambda p: len(p.strings) >= 2)
        lst = self.win.plant_inspector.list
        self.assertEqual(len(lst.rows), len(plant.strings))
        self.win.plan.fit()
        last = len(plant.strings) - 1
        lst.setCurrentItem(lst.rows[last])                                   # chosen in the list (R115)
        self.assertEqual((self.win.chosen_string, self.win.plan.chosen_string), (last, last))
        view = self.win.plan.mapToScene(self.win.plan.viewport().rect()).boundingRect()
        self.assertTrue(view.contains(self.win.plan.string_rect(last)))
        self.assertIn(plant.strings[last].label, self.win.plant_inspector.string_checks.text())
        name = plant.strings[last].label
        _setup.keyboard_or_skip(self, lst)
        QTest.keyClick(lst, Qt.Key.Key_Delete)                               # Del: that string, one step
        self.assertEqual(self.win.undo.undoText(), f"Delete string {name}")
        plant = self.plant(lambda p: len(p.strings) == last)
        self.win.undo.undo()
        plant = self.plant(lambda p: len(p.strings) == last + 1)
        # a click on a module of a string on the plan chooses it there and in the list
        first = plant.strings[0].modules[0]
        from PySide6.QtCore import QPointF
        self.click(self.win.plan.mapFromScene(QPointF(first[2][0], -first[2][1])))
        self.assertEqual(self.win.chosen_string, 0)
        self.assertEqual(lst.current(), 0)
        self.key(Qt.Key.Key_Escape)                                          # let go
        self.assertEqual(self.win.chosen_string, -1)
        self.win._string_list_menu(0, QPoint(0, 0))                          # its menu: move, reverse, draw, delete
        menu = self.win.context_menu
        self.addCleanup(menu.close)
        texts = [a.text() for a in menu.actions() if a.text()]
        self.assertTrue(any(t.startswith("Delete string") for t in texts), texts)
        self.assertTrue(any(t.startswith("Move string") for t in texts), texts)

    def an_older_project_s_proposal_is_written_down_as_it_was_without_a_step(self):
        from meridiana.energy import plant as plant_model
        p = sample()
        p.energy["inverters"] = [{"record": inverter_record(), "count": 1, "name": ""}]
        p.energy["strings"] = {"auto": True, "strategy": "rows"}            # a file of 13 migrated: the proposal
        path = Path(tempfile.mkdtemp()) / "vecchio.meridiana"
        # Keep the offline fixture's climate already embedded: downloading it is a separate, real edit (R196).
        from meridiana.energy import meteo
        self.assertTrue(wait_until(self.app, lambda: self.win.pool.activeThreadCount() == 0))
        meteo.capture(p, self.win.paths.cache)
        p.save(path)
        self.win.open_path(path)
        self.assertTrue(wait_until(self.app, lambda: self.sid in self.win.results))
        plant = self.plant(lambda q: bool(q.strings) and not q.auto)
        strings = self.win.project.energy["strings"]
        self.assertNotIn("auto", strings)
        self.assertEqual(self.win.undo.count(), 0)                           # no step, nothing to save
        self.assertFalse(self.win.session.dirty())
        expected = plant_model.propose(model.Project.from_json(p.to_json()), self.win.session.good_results())
        self.assertEqual([r["modules"] for r in strings["runs"]], [r["modules"] for r in expected])
        self.assertEqual(len(plant.strings), len(expected))

    # the journeys

    def test_nothing_comes_by_itself_and_a_string_is_drawn_numbered_taken_back_closed_and_given_up(self):
        self.nothing_comes_by_itself_and_propose_complete_and_delete_all_come_when_asked()
        self.again()
        self.ready()
        self.a_string_is_drawn_numbered_taken_back_closed_and_given_up()

    def test_another_string_refused_moved_drawn_again_the_list_and_an_older_proposal(self):
        self.a_module_of_another_string_is_refused_and_shift_moves_it_and_a_double_click_draws_it_again()
        self.again()
        self.ready()
        self.the_list_chooses_a_string_brings_it_into_view_and_del_deletes_it()
        self.again()
        self.an_older_project_s_proposal_is_written_down_as_it_was_without_a_step()


class RowsByHand(Journeys):
    """The layout by hand in the window (task 16c): L and two clicks draw a row; a second click on a module selects
    its row, Delete takes it away; Move takes a row; the menu explodes, adds, turns; a row dragged onto a skylight
    is said in the checks; «Lay again automatically» asks first; a new module adapts the rows or asks."""

    plan_event = Moving.plan_event
    key = Moving.key

    def laid(self, check=lambda r: True):
        self.assertTrue(wait_until(self.app, lambda: self.sid in self.win.results and
                                   self.win.layout_keys.get(self.sid) == self.win.project.layout_key(
                                       self.win.project.subfields[0]) and check(self.win.results[self.sid])),
                        "the layout did not come back")
        return self.win.results[self.sid]

    def l_and_two_clicks_draw_a_row_and_the_sub_field_is_by_hand(self):
        from PySide6.QtCore import Qt
        auto = self.laid()
        self.key(Qt.Key.Key_L)
        self.assertEqual(self.win.plan.tool, "row")
        self.assertTrue(self.win.tool_actions["row"].isChecked())
        self.assertIn("row", self.win.hint.text().lower())
        self.win.plan.snaps_on = False
        steps = self.win.undo.count()
        self.plan_event("click", 3.0, 18.0)
        self.plan_event("move", 12.0, 18.0)
        quads, bad = self.win._row_preview(self.win.plan.row_start, (12.0, 18.0))
        self.assertEqual((len(quads), bad), (7, True))                 # beyond the edge band of the sub-field: red
        self.plan_event("click", 12.0, 18.0)
        sf = self.win.project.subfields[0]
        self.assertTrue(sf.manual)
        self.assertEqual(len(sf.rows), sum(1 for r in auto.rows if r.places) + 1)
        self.assertEqual((self.win.undo.count(), self.win.undo.undoText()), (steps + 1, "Draw a row"))
        self.assertIn("Lay again automatically", self.win.hint.text())
        r = self.laid(lambda r: r.manual)
        self.assertEqual(r.count, auto.count + 7)
        self.assertEqual(self.win.plan.tool, "row")                     # the tool stays for the next row
        self.win.undo.undo()
        self.assertFalse(self.win.project.subfields[0].manual)

    def a_second_click_on_a_module_selects_its_row_and_delete_takes_it_away(self):
        r = self.laid()
        self.win.plan.snaps_on = False
        m = next(m for m in r.modules if m.rid == r.rows[1].id and m.level == 0)
        self.plan_event("click", *m.centre)
        self.assertEqual(self.win.plan.selected_module, (self.sid, m.key))
        # two clicks, not a double click: QTest moves its clock past the double-click interval after each release
        self.plan_event("click", *m.centre)
        self.assertEqual(self.win.selection, ("row", f"{self.sid}/{m.rid}"))
        self.assertEqual(self.win.plan.selected_module, ("", ""))
        self.assertIn("row of", self.win.measure_label.text())
        self.win._delete()
        sf = self.win.project.subfields[0]
        self.assertTrue(sf.manual)
        self.assertNotIn(m.rid, [x["id"] for x in sf.rows])
        self.assertEqual(self.win.undo.undoText(), "Take the row away")
        after = self.laid(lambda x: x.manual)
        self.assertEqual(after.count, r.count - sum(1 for x in r.modules if x.rid == m.rid))

    def the_square_at_the_end_of_a_row_selected_shortens_it_when_dragged(self):
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtTest import QTest

        from meridiana.ui.plan import to_scene
        r = self.laid()
        row = r.rows[0]
        oid = f"{self.sid}/{row.id}"
        self.win._select("row", oid)
        end = self.win.plan._row_end()
        self.assertIsNotNone(end)
        plan, vp = self.win.plan, self.win.plan.viewport()
        at = plan.mapFromScene(to_scene(*end))
        # 3,3 m back: the last three places (1,154 m each with the gap) no longer reach, the fourth does
        to = plan.mapFromScene(to_scene(end[0] - 3.3, end[1]))
        QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, at)
        QTest.mouseMove(vp, QPointF(at + (to - at) * 0.5).toPoint())
        QTest.mouseMove(vp, to)
        QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, to)
        self.assertEqual(self.win.undo.undoText(), "Shorten or lengthen a row")
        sf = self.win.project.subfields[0]
        self.assertEqual(len(next(x for x in sf.rows if x["id"] == row.id)["places"]), row.count - 3)

    def move_takes_a_row_and_a_turn_is_refused_with_the_reason(self):
        r = self.laid()
        row = r.rows[0]
        oid = f"{self.sid}/{row.id}"
        self.win._select("row", oid)
        self.win._transform("row", oid, {"mode": "move", "dx": 0.0, "dy": 0.5})
        moved = next(x for x in self.win.project.subfields[0].rows if x["id"] == row.id)
        self.assertAlmostEqual(moved["y"] - row.y, 0.5, places=3)
        before = self.win.snapshot()
        self.win._transform("row", oid, {"mode": "rotate", "cx": 0.0, "cy": 0.0, "degrees": 15.0})
        self.assertEqual(self.win.snapshot(), before)
        self.assertIn("turns with its sub-field", self.win.hint.text())
        self.win._transform("row", oid, {"mode": "move", "dx": 0.0, "dy": -30.0})
        self.assertEqual(self.win.snapshot(), before)
        self.assertIn("stays in its sub-field", self.win.hint.text())

    def the_menu_of_a_module_explodes_its_row_and_a_module_alone_turns_and_goes(self):
        r = self.laid()
        m = next(m for m in r.modules if m.rid == r.rows[0].id and m.level == 0)
        actions = dict(a for a in self.win.context_actions("subfield", self.sid, m.key) if a is not None)
        for text in ("Select the row", "Take the row away", "Add a row at the back", "Shorten or lengthen…",
                     "Explode the row", "Explode the rows"):
            self.assertIn(text, actions)
        actions["Explode the row"]()
        sf = self.win.project.subfields[0]
        self.assertTrue(sf.manual)
        exploded = self.laid(lambda x: x.manual)
        self.assertEqual(sorted(x.key for x in exploded.modules), sorted(x.key for x in r.modules))
        alone = next(x for x in exploded.modules if x.key == m.key)
        self.win._module_double_clicked(self.sid, m.key)                # Aurora's double click: turned by 90°
        self.assertEqual(self.win.undo.undoText(), "Turn the module")
        turned = self.laid(lambda x: any(y.turned for y in x.modules))
        self.assertAlmostEqual(next(x for x in turned.modules if x.key == m.key).centre[0], alone.centre[0], places=3)
        self.win.plan.selected_module = (self.sid, m.key)
        self.win._delete()
        gone = self.laid(lambda x: m.key not in x.keys)
        self.assertEqual(gone.count, r.count - 1)
        self.assertEqual(self.win.project.subfields[0].removed, [])     # a module alone goes with its row

    def a_row_dragged_onto_a_skylight_is_said_in_the_checks(self):
        self.win.edit("skylight", lambda p: p.exclusions.append(model.ExclusionItem(
            id="e1", ring=[[20, 9], [22, 9], [22, 11], [20, 11]], kind="skylight", building=p.buildings[0].id)))
        r = self.laid()
        whole = max((x for x in r.rows if x.places), key=lambda x: x.count)
        dy = 9.5 - whole.y
        self.win._transform("row", f"{self.sid}/{whole.id}", {"mode": "move", "dx": 0.0, "dy": dy})
        self.laid(lambda x: x.manual)
        self.win._show_checks()
        texts = [i.text for i in self.win.checks_page.items]
        self.assertTrue(any("on the exclusion Skylight 1" in t for t in texts), texts)
        self.assertTrue(any("rows by hand" in t for t in texts))

    def lay_again_automatically_asks_first_and_brings_the_layout_back(self):
        from PySide6.QtWidgets import QMessageBox
        r = self.laid()
        self.win._transform("row", f"{self.sid}/{r.rows[0].id}", {"mode": "move", "dx": 0.0, "dy": 0.2})
        self.assertTrue(self.win.project.subfields[0].manual)
        self.win._select("row", f"{self.sid}/{r.rows[0].id}")       # a row selected: its sub-field is laid again
        self.assertTrue(self.win.commands["refill"].isEnabled())
        self.dialogs.clear()
        self.win.commands["refill"].trigger()                           # answered «no» by setUp
        self.assertEqual([d[0] for d in self.dialogs], ["question"])
        self.assertTrue(self.win.project.subfields[0].manual)
        with mock.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.win.commands["refill"].trigger()
        self.assertFalse(self.win.project.subfields[0].manual)
        self.assertEqual(self.win.undo.undoText(), "Lay again automatically")
        back = self.laid(lambda x: not x.manual)
        self.assertEqual([m.key for m in back.modules], [m.key for m in r.modules])

    def the_properties_say_the_rows_are_by_hand(self):
        from PySide6.QtWidgets import QLabel, QPushButton
        r = self.laid()
        self.win._transform("row", f"{self.sid}/{r.rows[0].id}", {"mode": "move", "dx": 0.0, "dy": 0.2})
        self.laid(lambda x: x.manual)
        self.win._select("subfield", self.sid)
        labels = " ".join(w.text() for w in self.win.props.widget().findChildren(QLabel))
        self.assertIn("Rows by hand", labels)
        buttons = [b.text() for b in self.win.props.widget().findChildren(QPushButton)]
        self.assertIn("Lay again automatically", buttons)

    def a_new_module_within_two_centimetres_keeps_the_rows_and_a_larger_one_asks(self):
        r = self.laid()
        self.win._transform("row", f"{self.sid}/{r.rows[0].id}", {"mode": "move", "dx": 0.0, "dy": 0.2})
        self.win.edit("modules", lambda p: p.modules.update(
            near={"manufacturer": "X", "model": "N", "length": 2.29, "width": 1.14, "power_kw": 0.46},
            big={"manufacturer": "X", "model": "B", "length": 2.38, "width": 1.30, "power_kw": 0.6}))
        with mock.patch.object(type(self.win), "_ask_rows_module", return_value="") as asked:
            self.win._edited("subfield", self.sid, {"module": "near"})
            self.assertEqual(asked.call_count, 0)
            sf = self.win.project.subfields[0]
            self.assertEqual((sf.module, sf.manual), ("near", True))
            self.win._edited("subfield", self.sid, {"module": "big"})
            self.assertEqual(asked.call_count, 1)
            self.assertEqual(self.win.project.subfields[0].module, "near")          # «Cancel»: nothing changes
        with mock.patch.object(type(self.win), "_ask_rows_module", return_value="again"):
            self.win._edited("subfield", self.sid, {"module": "big"})
        sf = self.win.project.subfields[0]
        self.assertEqual((sf.module, sf.manual), ("big", False))

    # the journeys

    def test_l_draws_a_row_a_second_click_selects_it_delete_takes_it_and_its_end_shortens_it(self):
        self.l_and_two_clicks_draw_a_row_and_the_sub_field_is_by_hand()
        self.again()
        self.a_second_click_on_a_module_selects_its_row_and_delete_takes_it_away()
        self.again()
        self.the_square_at_the_end_of_a_row_selected_shortens_it_when_dragged()

    def test_a_row_moved_turned_exploded_and_the_properties_say_the_rows_are_by_hand(self):
        self.move_takes_a_row_and_a_turn_is_refused_with_the_reason()
        self.again()
        self.the_menu_of_a_module_explodes_its_row_and_a_module_alone_turns_and_goes()
        self.again()
        self.the_properties_say_the_rows_are_by_hand()

    def test_a_row_on_a_skylight_lay_again_automatically_and_a_new_module_for_the_rows_by_hand(self):
        self.a_row_dragged_onto_a_skylight_is_said_in_the_checks()
        self.again()
        self.lay_again_automatically_asks_first_and_brings_the_layout_back()
        self.again()
        self.a_new_module_within_two_centimetres_keeps_the_rows_and_a_larger_one_asks()


class Optimizers(PlantWindow):
    """Task 22: a SolarEdge inverter in the Plant phase takes the power optimizers Meridiana proposes, or the ones
    chosen in the catalogue (undone with Ctrl+Z); the strip says a string's optimizers and power against SolarEdge's
    limits instead of its voltages; the Checks panel cites SolarEdge's documents; Production has the optimizers'
    step."""

    def test_a_solaredge_inverter_takes_its_optimizers_and_the_strip_says_count_and_power(self):
        from PySide6.QtWidgets import QDialog

        from meridiana import catalog
        se = next(r for r in catalog.search("inverters", manufacturer="SolarEdge", limit=None) if r["model"] == "SE10K")
        s500 = next(r for r in catalog.search("optimizers", manufacturer="SolarEdge", limit=None)
                    if r["model"] == "S500")
        self.choose(se)
        self.win.show_phase("plant")
        self.plant(lambda p: p.optimized)
        self.win.strategy_actions["serpentine"].trigger()                 # «Propose the strings»
        plant = self.plant(lambda p: p.optimized and bool(p.strings))
        self.assertTrue(plant.units[0].choice.suggested)
        inspector = self.win.plant_inspector
        self.assertIn("proposed by Meridiana", inspector.optimizer_labels[0].text())
        self.assertIn("750 V", " ".join(w.text() for w in inspector.findChildren(type(inspector.describe))))
        fake = mock.MagicMock()
        fake.return_value.exec.return_value = QDialog.DialogCode.Accepted
        fake.return_value.chosen.return_value = s500
        fake.return_value.query.text.return_value = ""
        fake.return_value.maker_name.return_value = ""
        with mock.patch("meridiana.ui.window.CatalogDialog", fake):
            inspector.optimizerAsked.emit(0)
        fake.return_value.query.setText.assert_called_with("SolarEdge")          # SolarEdge's shown first
        entry = self.win.project.energy["inverters"][0]
        self.assertEqual((entry["optimizer"]["model"], entry["per_optimizer"]), ("S500", 1))
        plant = self.plant(lambda p: p.units[0].choice is not None and not p.units[0].choice.suggested)
        self.assertEqual(plant.units[0].choice.optimizer.model, "S500")
        self.assertIn("S500", inspector.optimizer_labels[0].text())
        self.win._choose_string(0)
        strip = self.win.plant_page.strings_label.text()
        self.assertIn("optimizers", strip)
        self.assertIn("kW", strip)
        self.assertNotIn("Umpp", strip)
        lst = inspector.list                                                       # «Strings»: one DC bus
        self.assertIn("STRINGS", " ".join(lst.topLevelItem(i).text(0).upper() for i in range(lst.topLevelItemCount())))
        strings = [i for i in self.win.checks_page.items if i.area == "strings"]
        self.assertTrue(strings)
        self.assertTrue(all("SolarEdge" in i.source or "CEI" not in i.source for i in strings))
        self.win.undo.undo()                                                       # back to the proposal
        self.assertNotIn("optimizer", self.win.project.energy["inverters"][0])
        self.plant(lambda p: p.units[0].choice is not None and p.units[0].choice.suggested)
        lst.adders[(1, 1)].click()
        card = self.win.plant_page.draft_card
        self.assertIn("0 modules", card.text)
        self.assertEqual(card.symbol_name, "")
        self.assertNotIn("short", card.text)
        self.assertNotIn("fine", card.text)
        self.win.plan.cancel_draft()


if __name__ == "__main__":
    unittest.main()
