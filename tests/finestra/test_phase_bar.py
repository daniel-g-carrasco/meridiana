"""The row of the phases and the bar of each phase in the window (task 17b, steps 2-4; study 17, B4; design
document 3.3 and 5.3): the change of phase from the keyboard and the menu, the right bar for each phase with its
groups and its one accent button, the tools that bring the model back, Lay and Empty on the selection, the checks
that lead to a phase; the words under the icons and the option that takes them away, the icons alone by themselves
in a low window, «Variant» in the corner, the bar on the left side, the preferences, only the drawing; the Report
phase with its buttons and the Deliverables inspector, the Plant phase as a shell. The bars and the commands are
the window's (MainWindow builds the actions with their icons, keys and tooltips): they are tested through it, three
windows for the fifteen tests of before (study 18, D 7.1). PySide6 and a display (offscreen will do)."""

import unittest
from pathlib import Path
from unittest import mock

import _setup
from _fixtures import capannone, clear_sky_meteo, inverter_record

from meridiana import config, phases

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

TALL_WINDOW, LOW_WINDOW_HEIGHT = 960, 840


class PhaseRow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone(), config.Config(background="none", theme="light"), size=(1400, TALL_WINDOW))
        self.sid = self.win.project.subfields[0].id

    def test_six_phases_the_keys_that_go_round_and_the_bar_of_each_with_its_groups_and_one_accent_button(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        win = self.win
        tabs = win.tabs
        self.assertEqual([tabs.tabText(i) for i in range(tabs.count())],
                         ["1 Model", "2 Plant", "3 Production", "4 Consumption", "5 Balance and economics", "6 Report"])
        self.assertEqual(win.phase(), "model")
        self.assertIs(tabs.currentWidget(), win.split)
        win.show_phase("report")
        self.assertIs(tabs.currentWidget(), win.report_page)
        self.assertTrue(win.phase_actions["report"].isChecked())               # View > Phases follows
        win.show_phase("model")
        # the phases by their numbers (Daniel, 24/10/2026), the Properties on Ctrl+P; the keys go round too
        for n, pid in enumerate(("model", "plant", "production", "consumption", "economics", "report"), 1):
            QTest.keyClick(win, getattr(Qt.Key, f"Key_{n}"), Qt.KeyboardModifier.ControlModifier)
            self.assertEqual(win.phase(), pid)
        win.show_phase("model")
        self.assertEqual(win.commands["next_phase"].shortcuts()[0].toString(), "Ctrl+Tab")
        QTest.keyClick(win, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(win.phase(), "plant")
        QTest.keyClick(win, Qt.Key.Key_PageDown, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(win.phase(), "production")
        QTest.keyClick(win, Qt.Key.Key_PageUp, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(win.phase(), "plant")
        QTest.keyClick(win, Qt.Key.Key_Backtab, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(win.phase(), "model")
        win.commands["previous_phase"].trigger()                               # before the first: the last
        self.assertEqual(win.phase(), "report")
        win.commands["next_phase"].trigger()
        self.assertEqual(win.phase(), "model")
        self.assertEqual(win.commands["panel_properties"].shortcut().toString(), "Ctrl+P")
        # the bar of each phase: the groups of the design, each tool the window's command, one accent at most
        for phase in phases.phases():
            with self.subTest(phase.id):
                win.show_phase(phase.id)
                bar = win.tabs.bars.currentWidget()
                self.assertIs(bar, win.bars[phase.id])
                self.assertEqual(bar.phase.id, phase.id)
                self.assertEqual([g.title.text() for g in bar.groups],
                                 [g.title for g in phase.groups if any(not t.planned for t in g.tools)])
                self.assertEqual(list(bar.buttons()), [t.command for t in phase.tools()])
                for cid, button in bar.buttons().items():
                    self.assertIs(button.defaultAction(), win.commands[cid])
                    self.assertEqual(button.toolButtonStyle(), Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
                    self.assertFalse(button.icon().isNull(), cid)
                    self.assertTrue(button.toolTip().startswith(button.defaultAction().toolTip().split("\n")[0]))
                primaries = [b for b in bar.buttons().values() if b.property("primary")]
                self.assertLessEqual(len(primaries), 1)
                self.assertEqual(bar.height(), win.tabs.bars.height())      # the same height in every phase
                self.assertTrue(bar.isVisibleTo(win))
        self.assertEqual(win.bars["model"].primary().property("tool"), "fill")
        self.assertEqual(win.bars["production"].primary().property("tool"), "compute")
        self.assertEqual(win.bars["model"].buttons()["tool_building"].text(), "Building")
        self.assertEqual(win.bars["model"].buttons()["fill"].text(), "Lay")           # short, the name in the tip
        self.assertIn("Lay the modules", win.bars["model"].buttons()["fill"].toolTip())
        self.assertIn("(B)", win.bars["model"].buttons()["tool_building"].toolTip())
        self.assertNotIn("Sun", [g.title.text() for g in win.bars["model"].groups])  # C5: in the views
        # the tools of the model bring the model phase back; the checks lead to a phase by its id
        win.show_phase("production")
        win.commands["tool_building"].trigger()
        self.assertEqual(win.phase(), "model")
        self.assertEqual(win.plan.tool, "building")
        win.commands["tool_select"].trigger()
        win.checks_page.navigate.emit(("phase", "economics"))
        self.assertEqual(win.phase(), "economics")
        win.checks_page.navigate.emit(("site",))
        self.assertEqual(win.phase(), "model")
        # Lay and Empty act on the selected sub-field, one undo step each
        fill, empty = win.commands["fill"], win.commands["empty"]
        win._select("site", "")
        self.assertFalse(fill.isEnabled() or empty.isEnabled())
        win._select("subfield", self.sid)
        self.assertTrue(fill.isEnabled() and empty.isEnabled())
        empty.trigger()
        self.assertTrue(_setup.wait_until(self.app, lambda: not win.project.subfields[0].filled))
        self.assertFalse(empty.isEnabled())
        fill.trigger()
        self.assertTrue(_setup.wait_until(self.app, lambda: win.project.subfields[0].filled))
        win.undo.undo()
        win.undo.undo()
        self.assertTrue(win.project.subfields[0].filled)

    def test_propose_is_a_menu_opened_by_one_click_and_sizing_says_what_it_did(self):
        """R141 on Linux: the menu itself is not the automatic proposal; the sizing command answers in the bar."""
        win = self.win
        win.show_phase("plant")
        button = win.bars["plant"].buttons()["strings_auto"]
        button.click()
        menu = win.strategy_menu
        self.addCleanup(menu.close)
        self.assertTrue(menu.isVisible())
        self.assertIs(menu.parentWidget(), win)
        self.assertEqual(win.project.energy.get("strings", {}).get("runs"), None)
        menu.close()
        win.project.energy["inverters"] = [{"record": inverter_record(model="AC-10K", ac_power_nominal_w=10000), "count": 1,
                                            "name": ""}]
        win.commands["inverter_auto"].trigger()
        message = win.statusBar().currentMessage()
        self.assertIn("AC-10K", message)
        self.assertIn("DC/AC", message)

    def test_the_words_under_the_icons_the_low_window_the_bar_on_the_left_the_preferences_and_the_variant(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtWidgets import QDialog, QToolBar

        from meridiana.ui.phasebar import LOW, TALL
        win, cfg = self.win, self.cfg
        bar = win.bars["model"]
        button = bar.buttons()["tool_building"]
        # the words under the icons by default, and View > Text under the icons that takes them away
        self.assertEqual(cfg.toolbar, "text")
        self.assertTrue(win.toolbar_text_action.isChecked())
        self.assertEqual(button.toolButtonStyle(), Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.assertEqual(button.iconSize().height(), 24)
        self.assertLessEqual(bar.height(), TALL)
        win.toolbar_text_action.trigger()
        self.assertEqual(cfg.toolbar, "icons")
        self.assertEqual(button.toolButtonStyle(), Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.assertEqual(button.iconSize().height(), 22)
        self.assertLessEqual(bar.height(), LOW + 4)
        self.assertTrue(bar.groups[0].title.isVisibleTo(bar))                    # the group's title stays
        win.toolbar_text_action.trigger()
        self.assertEqual(cfg.toolbar, "text")
        self.assertEqual(button.toolButtonStyle(), Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        # a low window gets the icons alone by itself, the preference untouched; forced, a tall one too
        win.resize(1400, LOW_WINDOW_HEIGHT)
        self.app.processEvents()
        self.assertEqual(button.toolButtonStyle(), Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.assertEqual(cfg.toolbar, "text")
        self.assertTrue(win.toolbar_text_action.isChecked())
        win.resize(1400, TALL_WINDOW)
        self.app.processEvents()
        self.assertEqual(button.toolButtonStyle(), Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        win._toolbar_style("icons")
        self.assertEqual(button.toolButtonStyle(), Qt.ToolButtonStyle.ToolButtonIconOnly)
        win._toolbar_style("text")
        # «Variant» in the corner of the row of the phases, in no toolbar
        combo = win.variant_bar
        header = win.tabs.header                                               # the row above the panels
        self.assertTrue(header.isAncestorOf(combo))
        tab_bar = win.tabs.tabBar()
        at = combo.mapTo(header, QPoint(0, 0))
        self.assertGreater(at.x(), tab_bar.x() + tab_bar.width())              # to the right of the phases
        self.assertLessEqual(at.y() + combo.height(), header.card.y())         # on the row, not on the bar
        for toolbar in win.findChildren(QToolBar):
            self.assertFalse(toolbar.isAncestorOf(combo), toolbar.objectName())
        self.assertEqual(combo.currentText(), "Base")
        # only the drawing hides the bar and brings it back
        win.clean_action.trigger()
        self.assertFalse(win.tabs.bars.isVisible())
        win.clean_action.trigger()
        self.assertTrue(win.tabs.bars.isVisible())
        # the bar on the left side: the icons alone, the groups as separators, filled again for each phase
        win._toolbar_style(place="left")
        self.assertEqual(cfg.toolbar_place, "left")
        self.assertTrue(win.side_bar.isVisible())
        self.assertFalse(win.tabs.bars.isVisible())
        self.assertEqual(win.toolBarArea(win.side_bar), Qt.ToolBarArea.LeftToolBarArea)
        self.assertEqual(win.side_bar.toolButtonStyle(), Qt.ToolButtonStyle.ToolButtonIconOnly)
        actions = win.side_bar.actions()
        self.assertEqual([a for a in actions if not a.isSeparator()],
                         [win.commands[t.command] for t in phases.by_id("model").tools()])
        self.assertEqual(sum(a.isSeparator() for a in actions), len(win.bars["model"].groups) - 1)
        win.show_phase("report")
        self.assertEqual([a for a in win.side_bar.actions() if not a.isSeparator()],
                         [win.commands[t.command] for t in phases.by_id("report").tools()])
        win.show_phase("model")
        win._toolbar_style(place="top")
        self.assertFalse(win.side_bar.isVisible())
        self.assertTrue(win.tabs.bars.isVisible())

        # the preferences choose the words and the place
        def choose(dialog):
            self.assertEqual(dialog.appearance.toolbar.currentData(), "text")
            self.assertEqual(dialog.appearance.place.currentData(), "top")
            dialog.appearance.toolbar.setCurrentIndex(dialog.appearance.toolbar.findData("icons"))
            dialog.appearance.place.setCurrentIndex(dialog.appearance.place.findData("left"))
            return QDialog.DialogCode.Accepted
        win._preferences("appearance", run=choose)
        self.assertEqual((cfg.toolbar, cfg.toolbar_place), ("icons", "left"))
        self.assertTrue(win.side_bar.isVisible())
        self.assertFalse(win.toolbar_text_action.isChecked())
        self.assertEqual(win.bars["model"].buttons()["tool_building"].toolButtonStyle(),
                         Qt.ToolButtonStyle.ToolButtonIconOnly)


class ReportAndPlant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone(), config.Config(background="none", theme="light"), size=(1400, TALL_WINDOW),
                      cache=clear_sky_meteo(45.5226, 9.03))      # a weather year: no network
        self.sid = self.win.project.subfields[0].id

    def test_the_report_phase_with_its_buttons_and_deliverables_and_the_plant_phase_with_its_inspector(self):
        from PySide6.QtWidgets import QFileDialog, QPushButton
        win = self.win
        # the Report phase: the buttons of today, the Deliverables inspector, the report not yet possible
        win.show_phase("report")
        page = win.report_page
        self.assertEqual(list(page.buttons), ["export_report", "compare_variants", "save_revision", "copy_notes"])
        self.assertEqual(page.buttons["save_revision"].text(), "Save as a new revision")
        self.assertIs(win.inspector.currentWidget(), win.inspector.deliverables)
        self.assertEqual(win.docks[1].windowTitle(), "Deliverables")
        states = win.inspector.deliverables.states
        self.assertEqual(states["report"], "unavailable")                        # no production yet
        self.assertEqual(states["csv"], "unavailable")
        self.assertEqual(states["dxf"], "planned")
        self.assertEqual(states["ifc"], "todo")                                   # the model needs no year (R91)
        buttons = [b for b in win.inspector.deliverables.findChildren(QPushButton)
                   if not win.report_side.isAncestorOf(b)]                       # the deliverables' own
        self.assertEqual(len(buttons), 3)                                         # the report's and the series', greyed; the IFC's
        self.assertEqual(sorted(b.isEnabled() for b in buttons), [False, False, True])
        with mock.patch.object(win, "_export_report") as export:
            page.buttons["export_report"].click()
        export.assert_called_once()
        # with the year: to do, done once exported, to make again when the project changes, done again undone
        win.energy = {}
        win._compute_energy(fetch=False)
        self.assertTrue(_setup.wait_until(self.app, lambda: bool(win.energy), 60))
        self.assertEqual(win.inspector.deliverables.states["report"], "todo")
        target = self.paths.data / "relazione.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)

        def steps(project, data, path, profile=None):       # the report a step at a time (study 16, F4)
            path.write_bytes(b"%PDF")
            yield 1.0, "page 1 of 1"

        with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "")), \
                mock.patch("meridiana.ui.report.export_steps", steps):
            win.commands["export_report"].trigger()
            self.assertTrue(_setup.wait_until(self.app, lambda: "report" in win.exports, 10))
        self.assertEqual(win.exports["report"][0], "relazione.pdf")
        self.assertEqual(win.inspector.deliverables.states["report"], "done")
        win._edited("subfield", self.sid, {"params.tilt": 20.0})
        self.assertEqual(win.inspector.deliverables.states["report"], "stale")
        win.undo.undo()
        self.assertEqual(win.inspector.deliverables.states["report"], "done")
        # the Plant phase: the inverter sized by itself and its inspector; Production: the results
        win.show_phase("plant")
        self.assertIs(win.tabs.currentWidget(), win.plant_page)
        self.assertIn("sized by itself", win.plant_page.inv_label.text())
        self.assertIs(win.inspector.currentWidget(), win.plant_inspector)      # design C10
        self.assertEqual(win.docks[1].windowTitle(), "Inverters")
        win.show_phase("production")
        self.assertEqual(win.docks[1].windowTitle(), "Data")
        self.assertEqual(win.inspector.results.heading.text(), "Production")

    def test_the_report_phase_shows_its_pages_and_its_choices_are_edits_undone_with_ctrl_z(self):
        """R61: the preview of the pages a step at a time, the template and the chapters chosen on the right as edits
        of the project, the preview made again after them."""
        from meridiana import reports
        win = self.win
        win._compute_energy(fetch=False)
        self.assertTrue(_setup.wait_until(self.app, lambda: bool(win.energy), 60))
        win.show_phase("report")
        page, side = win.report_page, win.report_side
        self.assertTrue(win.report_side.isVisible())                       # above the deliverables
        self.assertTrue(_setup.wait_until(self.app, lambda: len(page.preview.images) > 2, 120))
        complete = len(page.preview.images)
        self.assertIn(str(complete), page.status.text())
        self.assertEqual(list(side.boxes), list(reports.templates()["complete"].chapters))
        side.template.setCurrentIndex(side.template.findData("compact"))
        self.assertEqual(win.project.report["template"], "compact")
        self.assertEqual(list(side.boxes), list(reports.templates()["compact"].chapters))
        self.assertTrue(_setup.wait_until(self.app, lambda: 0 < len(page.preview.images) < complete, 120))
        win.undo.undo()
        self.assertEqual(reports.settings(win.project)["template"], "complete")
        self.assertEqual(side.template.currentData(), "complete")
        side.boxes["annexes"].setChecked(False)
        self.assertEqual(win.project.report["off"], ["annexes"])
        side.client.setText("Committente")
        side.client.editingFinished.emit()
        self.assertEqual(win.project.report["client"], "Committente")
        self.assertFalse(side.boxes["consumption"].isEnabled() and not reports.has(win._report_data(), "load"))

    def sample_pdfs(self, *specs) -> list[str]:
        """PDF files in the test's data folder, (name, pages) each, a frame on every page."""
        from PySide6.QtCore import QMarginsF
        from PySide6.QtGui import QPageLayout, QPainter, QPdfWriter
        files = []
        for name, pages in specs:
            path = self.paths.data / f"{name}.pdf"
            path.parent.mkdir(parents=True, exist_ok=True)
            writer = QPdfWriter(str(path))
            writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
            painter = QPainter(writer)
            for i in range(pages):
                if i:
                    writer.newPage()
                painter.drawRect(100, 100, 400, 400)
            painter.end()
            del painter, writer
            files.append(str(path))
        return files

    def test_the_attachments_are_chosen_as_edits_and_one_gone_is_said_before_the_export(self):
        """The attachments of the report (PDF files after the last chapter) added, renamed, moved and taken away in the
        Report phase, each an undoable edit; a file gone is shown as left out and said before the export, which stops
        there or goes on without it."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        win = self.win
        win._compute_energy(fetch=False)
        self.assertTrue(_setup.wait_until(self.app, lambda: bool(win.energy), 60))
        win.show_phase("report")
        side = win.report_side
        files = self.sample_pdfs(("Scheda modulo", 2), ("Scheda inverter", 1))
        with mock.patch.object(QFileDialog, "getOpenFileNames", return_value=(files, "")) as asked:
            side.add_button.click()
        self.assertEqual(asked.call_args[0][2], str(self.file.parent))           # the dialog opens by the project
        self.assertEqual([a["path"] for a in win.project.report["attachments"]], files)
        self.assertEqual([r.detail.text() for r in side.rows], ["Scheda modulo.pdf, 2 pages",
                                                                "Scheda inverter.pdf, 1 page"])
        self.assertFalse(side.rows[0].buttons["up"].isEnabled())
        side.rows[0].title.setText("Modulo di prova")
        side.rows[0].title.editingFinished.emit()
        self.assertEqual(win.project.report["attachments"][0]["title"], "Modulo di prova")
        side.rows[1].buttons["up"].click()
        self.assertEqual([a["path"] for a in win.project.report["attachments"]], files[::-1])
        side.rows[0].buttons["remove"].click()
        self.assertEqual([a["path"] for a in win.project.report["attachments"]], [files[0]])
        win.undo.undo()
        self.assertEqual([a["path"] for a in win.project.report["attachments"]], files[::-1])
        self.assertEqual(len(side.rows), 2)
        # a file gone: left out, in the danger's colour, and said before the export, which stops there
        Path(files[1]).unlink()
        win._show_inspector()
        gone = side.rows[0]
        self.assertEqual(gone.detail.objectName(), "row-problem")
        self.assertTrue(gone.detail.text().startswith("Left out: not found"))
        with mock.patch.object(QFileDialog, "getSaveFileName") as save:
            win.commands["export_report"].trigger()
        save.assert_not_called()
        self.assertEqual(self.dialogs[-1][0], "warning")
        self.assertIn("Scheda inverter: not found", self.dialogs[-1][1][1])
        target = self.paths.data / "Relazione.pdf"

        def steps(project, data, path, profile=None):       # the report, made quickly
            path.write_bytes(b"%PDF")
            yield 1.0, "page 1 of 1"

        with mock.patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Yes), \
                mock.patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "")), \
                mock.patch("meridiana.ui.report.export_steps", side_effect=steps) as made:
            win.commands["export_report"].trigger()
            self.assertTrue(_setup.wait_until(self.app, lambda: "report" in win.exports, 60))
        self.assertEqual(made.call_count, 1)
        self.assertEqual(win.exports["report"][0], "Relazione.pdf")

    def test_the_register_of_the_calculations_goes_beside_the_report_or_alone_from_the_bar(self):
        """The box «Export the register of the calculations too», an undoable edit: the report's PDF, then the hours
        of the year as a CSV file and «How it is computed» on its own beside it; the CSV of the Report phase's bar
        writes the hours alone. The deliverable «Hourly series» follows both."""
        from PySide6.QtWidgets import QFileDialog

        from meridiana import reports
        win = self.win
        win._compute_energy(fetch=False)
        self.assertTrue(_setup.wait_until(self.app, lambda: bool(win.energy), 60))
        win.show_phase("report")
        self.assertEqual(win.inspector.deliverables.states["csv"], "todo")
        side = win.report_side
        side.register.setChecked(True)
        self.assertTrue(win.project.report["register"])
        target = self.paths.data / "Relazione.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)

        def steps(project, data, path, profile=None, only=""):      # the PDFs, made quickly
            path.write_bytes(b"%PDF")
            yield 1.0, "page 1 of 1"

        with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "")), \
                mock.patch("meridiana.ui.report.export_steps", side_effect=steps) as made:
            win.commands["export_report"].trigger()
            self.assertTrue(_setup.wait_until(self.app, lambda: "report" in win.exports, 120))
        self.assertEqual(made.call_count, 2)                    # the report, then «How it is computed» on its own
        self.assertEqual(made.call_args.kwargs["only"], "methods")
        self.assertTrue((self.paths.data / "Relazione - register of the calculations.csv").is_file())
        self.assertTrue((self.paths.data / "Relazione - how it is computed.pdf").is_file())
        self.assertEqual(win.exports["csv"][0], "Relazione - register of the calculations.csv")
        self.assertEqual(win.inspector.deliverables.states["csv"], "done")
        win.undo.undo()                                                        # the register's box, undone
        self.assertFalse(reports.settings(win.project)["register"])
        # the hourly series on its own: the CSV of the Report phase's bar
        alone = self.paths.data / "Serie.csv"
        with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(str(alone), "")):
            win.commands["export_csv"].trigger()
        self.assertTrue(alone.read_text(encoding="utf-8-sig").startswith("# Meridiana"))
        self.assertEqual(win.exports["csv"][0], "Serie.csv")
        self.assertIn("export_csv", win.bars["report"].buttons())

    def test_the_authors_of_the_reports_are_written_in_the_preferences_with_a_copy_of_their_logo(self):
        from PySide6.QtGui import QColor, QImage
        from PySide6.QtWidgets import QDialog
        win = self.win
        logo = self.paths.cache / "logo-di-prova.png"
        logo.parent.mkdir(parents=True, exist_ok=True)
        image = QImage(40, 20, QImage.Format.Format_RGB32)
        image.fill(QColor("#336699"))
        image.save(str(logo))

        def run(dialog):
            page = dialog.report
            self.assertIs(dialog.pages.currentWidget(), page)              # the page asked for
            page._add()
            page.fields["name"].setText("Studio")
            page._typed("name")
            page.fields["signer"].setText("Firmatario")
            page._typed("signer")
            page._set_logo(str(logo))
            page.default.setCurrentIndex(page.default.findData("Studio"))
            return QDialog.DialogCode.Accepted
        win._preferences("report", run=run)
        self.assertEqual([p["name"] for p in win.cfg.report_profiles], ["Studio"])
        self.assertEqual(win.cfg.report_profile, "Studio")
        kept = win.cfg.report_profiles[0]["logo"]
        self.assertNotIn("/", kept)                                         # a name in the data folder, not a path
        self.assertTrue((self.paths.data / "logos" / kept).is_file())
        profile = win._report_profile()                                     # the project chose none: the default
        self.assertEqual(profile["signer"], "Firmatario")
        self.assertTrue(Path(profile["logo"]).is_file())
        win._report_edited("profile", "")                                   # nobody, for this project
        self.assertIsNone(win._report_profile())


if __name__ == "__main__":
    unittest.main()
