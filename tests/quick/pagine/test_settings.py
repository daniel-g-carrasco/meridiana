"""Settings use the Widgets Config and undo transactions, R329/R378/R390."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from meridiana import config
from meridiana.quick.backend.settings import SettingsBackend


class SettingsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'config.json'
        self.cfg = config.Config(font='inter', extra={'future': {'keep': [1, 2]}})   # from Inter to Plex and back
        self.backend = SettingsBackend(self.cfg, self.path)

    def test_immediate_atomic_persistence_undo_and_extra(self):
        changes = []
        self.backend.changed.connect(lambda key, value: changes.append((key, value)))
        self.assertTrue(self.backend.setValue('theme', 'dark'))
        self.assertEqual('dark', self.cfg.theme)
        self.assertEqual('dark', config.load(self.path).theme)
        self.assertTrue(self.backend.setValue('font', 'plex'))
        self.assertTrue(config.backup_file(self.path).exists())
        self.assertTrue(self.backend.undoLast())
        self.assertEqual('inter', self.cfg.font)
        self.assertEqual('dark', self.cfg.theme)
        self.assertEqual({'future': {'keep': [1, 2]}}, config.load(self.path).extra)
        self.assertIn(('font', 'inter'), changes)

    def test_failed_save_rolls_back_memory_history_and_signals(self):
        before = deepcopy(self.cfg)
        changes = []
        self.backend.changed.connect(lambda *args: changes.append(args))
        with patch('meridiana.quick.backend.settings.config.save', side_effect=OSError('disk full')):
            self.assertFalse(self.backend.setValue('theme', 'dark'))
        self.assertEqual(before, self.cfg)
        self.assertFalse(self.backend.canUndo)
        self.assertFalse(changes)
        self.assertIn('disk full', self.backend.error)

    def test_validation_never_changes_config(self):
        before = deepcopy(self.cfg)
        for key, value in [('theme', 'purple'), ('veil', 2), ('assistant', 1),
                           ('assistant_width', -10), ('font', 'missing'), ('unknown', 'x')]:
            with self.subTest(key=key):
                self.assertFalse(self.backend.setValue(key, value))
                self.assertEqual(before, self.cfg)

    def test_reset_category_uses_quick_defaults_and_is_undoable(self):
        self.backend.setValue('theme', 'dark')
        self.backend.setValue('navigation', 'blender')
        self.assertTrue(self.backend.restoreDefaults('appearance'))
        self.assertEqual(('light', 'indigo', 'grey', 'plex'),
                         (self.cfg.theme, self.cfg.accent, self.cfg.backgrounds, self.cfg.font))
        self.assertEqual('blender', self.cfg.navigation)
        self.assertTrue(self.backend.undoLast())
        self.assertEqual('dark', self.cfg.theme)

    def test_shortcuts_validate_conflicts_and_preserve_future_commands(self):
        self.cfg.shortcuts = {'future_command': ['Ctrl+9']}
        self.assertFalse(self.backend.setShortcut('open', ['Ctrl+Alt+E']))
        self.assertFalse(self.backend.setShortcut('open', ['Ctrl+S']))
        self.assertTrue(self.backend.setShortcut('open', ['Ctrl+Shift+O']))
        self.assertEqual(['Ctrl+9'], self.cfg.shortcuts['future_command'])
        self.assertTrue(self.backend.setShortcut('open', ['Ctrl+O']))
        self.assertNotIn('open', self.cfg.shortcuts)
        self.backend.restoreDefaults('keyboard')
        self.assertEqual(['Ctrl+9'], self.cfg.shortcuts['future_command'])

    def test_profiles_rename_default_and_remove_without_stale_reference(self):
        from meridiana import reports
        self.assertEqual(reports.NOBODY, self.backend.defaultProfile)
        self.assertTrue(self.backend.addProfile())
        name = self.cfg.report_profiles[0]['name']
        self.assertEqual(name, self.backend.defaultProfile)
        self.assertTrue(self.backend.setValue('report_profile', name))
        self.assertTrue(self.backend.editProfile(0, 'name', 'Studio'))
        self.assertEqual('Studio', self.cfg.report_profile)
        self.assertTrue(self.backend.editProfile(0, 'signer', 'Daniel Grasso'))
        self.assertTrue(self.backend.removeProfile(0))
        self.assertEqual('', self.cfg.report_profile)
        self.assertTrue(self.backend.undoLast())
        self.assertEqual('Daniel Grasso', self.cfg.report_profiles[0]['signer'])

    def test_map_drafts_preserved_but_not_used_until_valid(self):
        from meridiana import tiles
        self.assertTrue(self.backend.addMapSource())
        item = self.cfg.map_sources[0]
        self.assertNotIn(item['key'], tiles.catalogue(self.cfg.map_sources))
        self.assertTrue(self.backend.editMapSource(0, 'url', 'https://example.org/{z}/{x}/{y}.png'))
        self.assertTrue(self.backend.editMapSource(0, 'attribution', 'Example'))
        self.assertIn(item['key'], tiles.catalogue(self.cfg.map_sources))
        self.backend.setValue('background', item['key'])
        self.assertTrue(self.backend.removeMapSource(0))
        self.assertEqual('auto', self.cfg.background)

    def test_all_config_fields_accounted_for_and_every_category_exposed(self):
        from dataclasses import fields
        from meridiana.quick.backend.settings import SECTIONS, INTERNAL_FIELDS
        classified = set(INTERNAL_FIELDS) | {key for values in SECTIONS.values() for key in values}
        self.assertEqual({f.name for f in fields(config.Config)}, classified - {'reduced_motion'})
        self.assertEqual({'appearance', 'navigation', 'keyboard', 'privacy', 'assistant', 'report', 'maps', 'performance'},
                         {category['key'] for category in self.backend.categories})

    def test_memory_budget_and_background_year_are_set_from_the_settings(self):
        from meridiana import resources
        from meridiana.quick.backend import settings_schema
        rows = {row['key']: row for row in settings_schema.fields_for('performance', self.cfg)}
        self.assertEqual(list(rows), ['edges_3d', 'memory_mode', 'background_year', 'background_year_wait_s',
                                      'background_year_workers', 'background_year_battery_factor'])
        # R548: Risparmia / Automatico / Usa tutto, and what Meridiana holds now in the description
        self.assertEqual((rows['memory_mode']['kind'], [o['value'] for o in rows['memory_mode']['options']]),
                         ('choice', ['save', 'auto', 'all']))
        self.assertIn('GB', rows['memory_mode']['description'])
        self.assertEqual(rows['background_year']['kind'], 'bool')
        self.addCleanup(resources.configure, 'auto')
        self.assertTrue(self.backend.setValue('memory_mode', 'save'))
        self.assertTrue(self.backend.setValue('background_year_wait_s', 12.0))
        self.assertTrue(self.backend.setValue('background_year_workers', 3))
        self.assertTrue(self.backend.setValue('background_year', False))
        saved = config.load(self.path)
        self.assertEqual((saved.memory_mode, saved.background_year_wait_s, saved.background_year_workers,
                          saved.background_year), ('save', 12.0, 3, False))
        self.assertFalse(self.backend.setValue('memory_mode', 'everything'))
        self.assertFalse(self.backend.setValue('background_year_workers', 20))
        self.assertTrue(self.backend.setValue('memory_mode', 'auto'))

    def test_the_edges_of_the_3d_are_chosen_among_three_and_saved(self):
        from meridiana.quick.backend import settings_schema
        row = next(r for r in settings_schema.fields_for('performance', self.cfg) if r['key'] == 'edges_3d')
        self.assertEqual((row['kind'], [o['value'] for o in row['options']]), ('choice', ['full', 'moving', 'low']))
        self.assertTrue(row['description'])
        self.assertEqual(self.cfg.edges_3d, 'full')                         # as the program drew them before
        self.assertTrue(self.backend.setValue('edges_3d', 'moving'))
        self.assertEqual(config.load(self.path).edges_3d, 'moving')
        self.assertFalse(self.backend.setValue('edges_3d', 'jagged'))
        self.assertEqual(config.load(self.path).edges_3d, 'moving')

    def test_theme_updates_and_reduced_motion_roundtrip(self):
        from meridiana.quick.backend.tokens import ThemeTokens
        theme = ThemeTokens()
        backend = SettingsBackend(self.cfg, self.path, theme)
        self.assertTrue(backend.setValue('theme', 'dark'))
        self.assertTrue(theme.dark)
        self.assertTrue(backend.setValue('reduced_motion', True))
        self.assertTrue(theme.reducedMotion)
        self.assertTrue(config.load(self.path).extra['reduced_motion'])
        backend.undoLast()
        self.assertFalse(theme.reducedMotion)

    def test_cloud_profiles_and_secrets_use_existing_provider_and_keyring_services(self):
        self.assertFalse(self.backend.setCloudProfile('openai', 'model-test', 'http://example.org'))
        self.assertTrue(self.backend.setCloudProfile('anthropic', 'model-test', 'https://api.anthropic.com'))
        self.assertEqual('model-test', self.cfg.assistant_cloud_model)
        with patch('meridiana.assistant.keys.put') as put:
            self.assertTrue(self.backend.setSecret('openai', 'private-token', 'meridiana-assistant'))
            put.assert_called_once_with('openai', 'private-token', 'meridiana-assistant')
        self.assertNotIn('private-token', self.path.read_text(encoding='utf8'))

    def test_capabilities_respects_privacy_and_matches_source_after_async_reply(self):
        self.backend.addMapSource()
        self.backend.editMapSource(0, 'kind', 'wmts')
        self.backend.editMapSource(0, 'url', 'https://example.org/wmts')
        service = self.backend.services
        self.backend.setValue('network_tiles', False)
        self.assertFalse(service.readCapabilities(0))
        source_key = self.cfg.map_sources[0]['key']
        fixture = Path('tests/formati/file/mappe/wmts-pdok.xml')
        if not fixture.exists():
            fixture = next(Path('tests').rglob('wmts-pdok.xml'))
        data = fixture.read_bytes()
        self.assertTrue(service.accept_capabilities(source_key, 'https://example.org/wmts', data))
        self.assertTrue(service.chooseLayer(0, 'Actueel_orthoHR'))
        self.assertEqual('EPSG:3857', self.cfg.map_sources[0]['matrix_set'])
        self.assertTrue(self.cfg.map_sources[0]['matrices'])
        self.backend.editMapSource(0, 'capabilities', 'https://example.org/other')
        self.assertFalse(service.chooseLayer(0, 'Actueel_orthoHR'))
        self.backend.removeMapSource(0)
        self.assertFalse(service.accept_capabilities(source_key, 'https://example.org/wmts', data))

    def test_local_model_choice_is_one_undo_transaction(self):
        from meridiana.assistant.local import Model, Runtime, Survey
        original = (self.cfg.assistant_local_url, self.cfg.assistant_local_model, self.cfg.assistant_local_runtime)
        survey = Survey([Runtime('ollama', url='http://127.0.0.1:11434', running=True, models=[Model('test-model')])])
        self.backend.services._local_finished(survey, '')
        self.assertTrue(self.backend.services.useLocal(0))
        self.assertEqual(('test-model', 'ollama'), (self.cfg.assistant_local_model, self.cfg.assistant_local_runtime))
        self.backend.undoLast()
        self.assertEqual(original, (self.cfg.assistant_local_url, self.cfg.assistant_local_model, self.cfg.assistant_local_runtime))

    def test_every_simple_setting_persists_and_undo_keeps_external_changes(self):
        from meridiana.quick.backend.settings_schema import SECTIONS, TABLE_FIELDS, choices
        options = choices(self.cfg)
        for keys in SECTIONS.values():
            for key in keys:
                if key in TABLE_FIELDS:
                    continue
                with self.subTest(key=key):
                    previous = self.backend.values[key]
                    if key in options:
                        value = next((v for v in options[key] if v != previous), previous)
                    elif isinstance(previous, bool):
                        value = not previous
                    elif isinstance(previous, (int, float)):
                        value = {'veil': 0.7, 'assistant_voice_pitch': 2,             # R492: inside their ranges
                                 'assistant_voice_speed': 1.2, 'background_year_workers': 3,
                                 'background_year_battery_factor': 2.0,
                                 'background_year_wait_s': 9.0}.get(key, previous + 10)
                    else:
                        value = 'sample'
                    self.assertTrue(self.backend.setValue(key, value), self.backend.error)
                    loaded = config.load(self.path)
                    self.assertEqual(value, loaded.extra.get(key, False) if key == 'reduced_motion' else getattr(loaded, key))
                    self.cfg.last_folder = 'external-folder'
                    self.assertTrue(self.backend.undoLast())
                    self.assertEqual(previous, self.backend.values[key])
                    self.assertEqual('external-folder', self.cfg.last_folder)

    def test_local_model_test_and_voice_download_are_worker_jobs(self):
        import time
        from PySide6.QtTest import QTest
        from meridiana.assistant import local
        service = self.backend.services

        def wait_done(predicate):
            until = time.monotonic() + 3
            while predicate() and time.monotonic() < until:
                QTest.qWait(10)
            self.assertFalse(predicate())

        with patch('meridiana.assistant.local.check', return_value=local.Check(True, 0.1, True)) as check:
            self.assertTrue(service.testLocal())
            wait_done(lambda: service.testBusy)
            check.assert_called_once()
            self.assertIn('0', service.testStatus)
        self.assertFalse(service.downloadVoice())
        self.backend.setValue('assistant_kokoro_dir', str(Path(self.folder.name) / 'voices'))
        with patch('meridiana.assistant.speech.download_model') as download:
            self.assertTrue(service.downloadVoice())
            wait_done(lambda: service.downloadBusy)
            self.assertEqual(Path(self.folder.name) / 'voices', download.call_args.args[0])

    def test_pending_text_flushes_on_leaving_category_and_undo(self):
        self.backend.showSection('assistant')
        self.backend.stageValue('assistant_local_model', 'written-before-leaving')
        self.assertEqual('', self.cfg.assistant_local_model)
        self.backend.showSection('maps')
        self.assertEqual('written-before-leaving', self.cfg.assistant_local_model)
        self.backend.addProfile()
        original = self.cfg.report_profiles[0]['name']
        self.backend.stageProfile(0, 'name', 'Unsaved typing')
        self.backend.undoLast()
        self.assertEqual(original, self.cfg.report_profiles[0]['name'])

    def test_shortcut_can_be_taken_explicitly_from_another_command(self):
        from meridiana import shortcuts
        self.assertFalse(self.backend.setShortcut('open', ['Ctrl+S']))
        self.assertTrue(self.backend.shortcutConflict)
        self.assertTrue(self.backend.takeShortcut())
        current = shortcuts.bindings(self.cfg.shortcuts)
        self.assertEqual(['Ctrl+S'], current['open'])
        self.assertEqual([], current['save'])
        self.backend.undoLast()
        self.assertEqual(['Ctrl+S'], shortcuts.bindings(self.cfg.shortcuts)['save'])

    def test_close_flushes_typing_and_ignores_late_worker_results(self):
        from meridiana.assistant.local import Survey
        self.backend.stageValue('assistant_local_model', 'kept-on-close')
        self.backend.close()
        self.assertEqual('kept-on-close', config.load(self.path).assistant_local_model)
        changes = []
        self.backend.services.changed.connect(lambda: changes.append(True))
        self.backend.services._local_finished(Survey(), '')
        self.backend.services._progress(1, 2)
        self.assertFalse(changes)
        self.assertFalse(self.backend.setValue('theme', 'dark'))

    def test_report_logo_is_kept_in_the_shell_data_directory(self):
        from PySide6.QtGui import QImage
        source = Path(self.folder.name) / 'original.png'
        image = QImage(20, 10, QImage.Format.Format_RGB32)
        image.fill(0xffaabbcc)
        self.assertTrue(image.save(str(source)))
        self.backend.setDataDirectory(Path(self.folder.name) / 'data')
        self.backend.addProfile()
        self.assertTrue(self.backend.editProfile(0, 'logo', str(source)))
        name = self.cfg.report_profiles[0]['logo']
        self.assertEqual(Path(name).name, name)
        self.assertEqual(source.read_bytes(), (Path(self.folder.name) / 'data/logos' / name).read_bytes())


if __name__ == '__main__':
    unittest.main()
