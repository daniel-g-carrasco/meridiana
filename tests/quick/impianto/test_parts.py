"""R389/R396: the installed phases operate the real workbench's one session."""
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent
from _fixtures import capannone, inverter_record
from meridiana.quick.app import QuickWindow


setUpModule = _setup.keep_global_state


class InstalledPhasesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.host = QuickWindow(capannone(), Path(self.temp.name), real_views=True)
        self.addCleanup(self.host.close)

    def test_registry_installs_same_session_and_toolbar_commands(self):
        parts = self.host.parts
        self.assertIn('plant', parts.controllers)
        self.assertIn('results', parts.controllers)
        plant = parts.controllers['plant']
        self.assertIs(plant.session, self.host.bridge.session)
        for command in ('inverter_catalog', 'inverter_auto', 'battery_catalog', 'strings_auto',
                        'strings_complete', 'strings_manual', 'strings_clear', 'compute', 'import_curve'):
            self.assertTrue(self.host.shell.available(command), command)
        self.assertTrue(self.host.shell.trigger('inverter_catalog'))
        self.assertEqual(parts.controllers['plantActions'].dialog, 'catalog')
        parts.controllers['plantActions'].catalog.chosen.emit('inverters', inverter_record())
        self.assertEqual(plant.session.project.energy['inverters'][0]['record']['model'], inverter_record()['model'])
        self.host.bridge.undo()
        self.assertFalse(plant.session.project.energy.get('inverters'))

    def test_r398_the_curve_command_shows_consumption_and_asks_for_the_file(self):
        # R398: in the Widgets the menu's «Load curve» called a private method through the lazy page and stopped
        # with an AttributeError; here the command goes to the Consumption phase and the editor asks for the file
        editor = self.host.parts.controllers['consumptionEditor']
        asked = []
        editor.importRequested.connect(lambda: asked.append(True))
        self.assertTrue(self.host.shell.trigger('import_curve'))
        _setup.turn_events(self.app, 200)
        self.assertEqual(self.host.window.property('phase'), 'consumption')
        self.assertTrue(asked)
        self.assertTrue(editor.importPending)
        editor.dismissImport()
        self.assertFalse(editor.importPending)

    def test_production_inspector_edits_reach_session_and_clear_on_close(self):
        editor = self.host.parts.controllers['productionEditor']
        self.assertIs(editor.session, self.host.bridge.session)
        self.assertTrue(editor.commit('losses.soiling', 4, editor.epoch))
        self.assertEqual(editor.session.project.energy['losses']['soiling'], 4)
        self.host.close()
        self.assertNotIn(editor._on_change, editor.session.listeners)

    def test_strings_view_is_remembered_in_the_isolated_profile(self):
        from meridiana import config
        actions = self.host.parts.controllers['plantActions']
        before = self.host.bridge.session.project.to_json()
        actions.setStringsView('diagram')
        self.assertEqual(actions.stringsView, 'diagram')
        self.assertEqual(config.load(self.host.paths.config_file).strings_view, 'diagram')
        actions.setStringsView('invalid')
        self.assertEqual(actions.stringsView, 'diagram')
        self.assertEqual(self.host.bridge.session.project.to_json(), before)

    def test_real_inspectors_load_without_qml_errors(self):
        from meridiana.quick.backend.parts import QML
        for file in ('Plant/PlantSide.qml', 'Charts/ProductionInspector.qml',
                     'Charts/ConsumptionInspector.qml', 'Charts/EconomicsInspector.qml'):
            with self.subTest(file=file):
                component = QQmlComponent(self.host.engine, QUrl.fromLocalFile(str(QML / file)))
                self.assertTrue(_setup.wait_until(self.app, lambda component=component: not component.isLoading()))
                self.assertFalse(component.isError(), [e.toString() for e in component.errors()])
                page = component.create()
                self.assertIsNotNone(page, [e.toString() for e in component.errors()])
                page.setParentItem(self.host.window.contentItem())
                page.setWidth(370)
                page.setHeight(700)
                self.app.processEvents()
                page.deleteLater()
        owned = [w for w in self.host.warnings if '/Plant/' in w or '/Charts/' in w]
        self.assertFalse(owned, owned)
