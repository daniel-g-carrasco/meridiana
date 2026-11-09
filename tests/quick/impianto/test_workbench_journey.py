"""R297/R298/R396: actual toolbar, dialogs, rename and drafting on one workbench."""
import os
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QCoreApplication, QEvent, QPointF, Qt
from meridiana import i18n, jobs
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import click, drag, item, key, point, pump, wait_for, wheel
from quick.parity.differential import connected_fixture


setUpModule = _setup.keep_global_state


class WorkbenchJourney(unittest.TestCase):
    def test_commands_edit_the_actual_session_and_dialogs_reopen(self):
        app = _setup.qt_or_skip()
        create_app()
        i18n.setup('it')
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        with tempfile.TemporaryDirectory() as folder:
            host = QuickWindow(project, Path(folder), real_views=True,
                               theme={'theme': 'light', 'accent': 'indigo', 'backgrounds': 'grey'})
            win, session = host.window, host.bridge.session
            plant = host.parts.controllers['plant']
            actions = host.parts.controllers['plantActions']
            out = _setup.ROOT / 'build/quick-foto/r13-fasi' / f'comandi-{os.getpid()}'
            out.mkdir(parents=True, exist_ok=False)
            def capture(name):
                pump(150)
                self.assertTrue(win.grabWindow().save(str(out / (name+'.png'))))
            def press(name):
                pending = [win.contentItem()]
                control = None
                while pending:
                    candidate = pending.pop()
                    pending.extend(candidate.childItems())
                    if candidate.objectName() == name and candidate.isVisible():
                        control = candidate
                        break
                self.assertIsNotNone(control, name)
                self.assertTrue(control.isVisible(), name)
                self.assertTrue(control.isEnabled(), name)
                click(app, win, point(control))
                pump(80)
            def escape():
                key(app, win, Qt.Key.Key_Escape)
                pump(180)
            def settle():
                wait_for(lambda: not plant.busy, 60)
                pump(80)
            try:
                host.bridge.accept_layout(session.generation, results, keys)
                win.show()
                # r22-unita: after the show, as the other journeys do: offscreen the screen is 800 x 800 and R430
                # (keep_on_screen, at the show) brought a window sized before it to 796 x 796, the panel too short
                # for the strings' view button and the bar folding «Compute» away
                win.resize(1600, 960)
                host.shell.trigger('phase_production')
                pump(350)
                # r22-unita: «Compute» sits in more than one phase's bar, each with its stale mark; item() gave the
                # first one met, in a phase not shown, so the mark looked hidden whatever the state. The mark of the
                # bar on screen is the one the user sees.
                def shown(name):
                    pending, found = [win.contentItem()], []
                    while pending:
                        candidate = pending.pop()
                        pending.extend(candidate.childItems())
                        if candidate.objectName() == name and candidate.parentItem().isVisible():
                            found.append(candidate)
                    self.assertEqual(len(found), 1, name)
                    return found[0]
                dot = shown('stale-compute')
                self.assertEqual(dot.parentItem().objectName(), 'tool_compute')
                self.assertFalse(dot.isVisible())
                from meridiana.energy.pipeline import EnergyResult
                from quick.grafici.fixtures import build_results
                year = build_results()
                session.energy_done(session.energy_asked(), EnergyResult(
                    sim=year.sim, load=year.load, econ=year.econ, pvgis=year.pvgis,
                    sizing=year.sizing, storage=year.storage, battery_kwh=0.).as_dict())
                pump(300)
                self.assertFalse(dot.isVisible())
                session.edit('Price', lambda p: p.economics.update(buy_f1=.42))
                pump(50)
                self.assertTrue(dot.isVisible())
                session.undo.undo()
                pump(50)
                self.assertFalse(dot.isVisible())
                capture('calcola-aggiornato')
                host.shell.trigger('phase_plant')
                settle()
                pump(500)
                press('tool_inverter_catalog')
                self.assertEqual(actions.dialog, 'catalog')
                wait_for(lambda: not actions.catalog.busy, 60)
                capture('catalogo')
                self.assertGreater(actions.catalog.model.rowCount(), 0)
                before = len(project.energy['inverters'])
                self.assertEqual(actions.catalog.selectedCount, 0)      # R421: no row at random
                actions.catalog.select(0, False)
                press('dialogAccept')                                    # R518: «Choose» is the window's own button (named by r22-f2)
                settle()
                if actions.dialog == 'catalog':                         # the module does not go with it: said, then taken
                    self.assertTrue(actions.catalog.confirmation)
                    actions.catalog.chooseAnyway()
                    settle()
                self.assertGreaterEqual(len(project.energy['inverters']), before)
                self.assertEqual(actions.dialog, '')
                self.assertTrue(session.undo.can_undo())
                session.undo.undo()
                settle()
                press('tool_inverter_auto')
                self.assertEqual(actions.dialog, 'sizing')
                wait_for(lambda: bool(plant.makers), 60)
                capture('scelta-automatica')
                escape()
                self.assertEqual(actions.dialog, '')
                press('tool_battery_catalog')
                self.assertEqual(actions.dialog, 'storage')
                storage = item(win, 'plant-storage-form')
                storage.setProperty('units', 7)
                capture('accumulo')
                escape()
                press('tool_battery_catalog')
                self.assertEqual(storage.property('units'), 1)
                escape()
                for _attempt in range(2):
                    press('tool_strings_auto')
                    self.assertEqual(actions.dialog, 'proposal')
                    # R518: «String» is the proposal window's own button
                    self.assertTrue(shown('dialogAccept').isVisible())
                    capture(f'automatico-{_attempt}')
                    escape()
                actions.openSection('inverter')
                pump(350)
                press('inverter-card-1')
                key(app, win, Qt.Key.Key_F2)
                name = item(win, 'inverter-name-1')
                self.assertTrue(name.isVisible())
                key(app, win, Qt.Key.Key_A, modifiers=Qt.KeyboardModifier.ControlModifier)
                for char in 'Inverter tetto':
                    key(app, win, 0, char)
                key(app, win, Qt.Key.Key_Return)
                settle()
                self.assertEqual(plant.units[0]['name'], 'Inverter tetto')
                capture('inverter-rinominato')
                inspector = item(win, 'plant-inverters')
                view_button = item(win, 'plant-strings-view')
                for _attempt in range(30):
                    if 20 <= view_button.mapToItem(inspector, QPointF(12, 12)).y() < inspector.height()-25:
                        break
                    wheel(app, win, point(inspector), notches=1)
                press('plant-strings-view')
                capture('menu-vista-stringhe')
                press('plant-view-diagram')
                self.assertEqual(actions.stringsView, 'diagram')
                capture('schema-stringhe')
                press('plant-strings-view')
                press('plant-view-table')
                self.assertEqual(actions.stringsView, 'table')
                capture('tabella-stringhe')
                scroll = item(win, 'stringsHorizontalScroll')
                self.assertGreater(scroll.property('contentWidth'), scroll.width())
                for column in (1, 2, 3):
                    self.assertFalse(item(win, f'string-cell-0-{column}').property('truncated'), column)
                start = point(scroll, scroll.width()-25, 65)
                drag(app, win, start, start-QPointF(180, 0), steps=15)
                pump(250)
                self.assertGreater(scroll.property('contentX'), 50)
                capture('tabella-stringhe-scorsa')
                press('tool_strings_manual')
                self.assertIsNotNone(host.plan.editor.draft_target)
                capture('disegna')
                escape()
                self.assertIsNone(host.plan.editor.draft_target)
                press('tool_tool_erase_string')
                self.assertEqual(host.plan.editor.tool, 'erase_string')
                escape()
                self.assertEqual(host.plan.editor.tool, 'select')
                self.assertFalse(host.warnings, host.warnings)
            finally:
                host.close()
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                app.processEvents()
