"""Differential Config outcomes from real Widgets preferences and Quick settings."""
import os
import subprocess
import sys
import unittest


SCRIPT = r'''
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from meridiana import config, shortcuts
from meridiana.assistant.local import Survey
from meridiana.ui.preferences import Preferences
from meridiana.ui.theme import Theme
from meridiana.quick.backend.settings import SettingsBackend

app = QApplication([])
with TemporaryDirectory() as folder, patch('meridiana.assistant.keys.get', return_value=''), \
     patch('meridiana.assistant.setup.available', return_value=[]), \
     patch('meridiana.assistant.local.survey', return_value=Survey()):
    widget_config = config.Config(extra={'future': {'number': 12}})
    quick_config = deepcopy(widget_config)
    theme = Theme(widget_config, app=app)
    prefs = Preferences(widget_config, shortcuts.bindings({}), theme)
    quick = SettingsBackend(quick_config, Path(folder) / 'quick.json')

    def apply(section):
        # These are the same choice methods used by MainWindow._preferences_changed.
        if section in ('navigation', 'all'):
            for key, value in zip(('navigation', 'orbit', 'pivot', 'pivot_hint'), prefs.navigation.choice()):
                setattr(widget_config, key, value)
        if section in ('privacy', 'all'):
            for key, value in zip(('network_geocoding', 'network_pvgis', 'network_tiles'), prefs.privacy.choice()):
                setattr(widget_config, key, value)
        if section in ('appearance', 'all'):
            widget_config.theme, widget_config.accent, widget_config.backgrounds = prefs.appearance.choice()
            widget_config.font = prefs.appearance.font_choice.currentData()
            widget_config.text_size = prefs.appearance.text_size.currentData()
        if section in ('keyboard', 'all'):
            widget_config.shortcuts = shortcuts.differences(prefs.keys.bindings, widget_config.shortcuts)
        config.save(widget_config, Path(folder) / 'widgets.json')

    prefs.changed.connect(apply)

    def same():
        assert widget_config.to_json() == quick_config.to_json(), (widget_config.to_json(), quick_config.to_json())
        assert config.load(Path(folder) / 'widgets.json').to_json() == config.load(Path(folder) / 'quick.json').to_json()

    prefs.show_page('navigation')
    prefs.navigation.orbit.setCurrentIndex(prefs.navigation.orbit.findData('arcball'))
    assert quick.setValue('orbit', 'arcball')
    same()
    prefs.undo_last()
    quick.undoLast()
    same()
    prefs.navigation.pivot.setCurrentIndex(prefs.navigation.pivot.findData('selection'))
    quick.setValue('pivot', 'selection')
    prefs.restore_defaults()
    quick.restoreDefaults('navigation')
    same()

    prefs.show_page('privacy')
    prefs.privacy.geocoding.setChecked(False)
    quick.setValue('network_geocoding', False)
    same()
    prefs.restore_defaults()
    quick.restoreDefaults('privacy')
    same()
    prefs.undo_last()
    quick.undoLast()
    same()

    prefs.show_page('appearance')
    prefs.appearance.mode.setCurrentIndex(prefs.appearance.mode.findData('dark'))
    prefs.appearance.timer.stop()
    prefs.appearance.settled.emit(*prefs.appearance.choice())
    quick.setValue('theme', 'dark')
    same()
    prefs.appearance.font_choice.setCurrentIndex(prefs.appearance.font_choice.findData('plex'))
    quick.setValue('font', 'plex')
    same()

    prefs.show_page('keyboard')
    prefs.keys.assign('open', 'Ctrl+S')
    apply('keyboard')
    assert not quick.setShortcut('open', ['Ctrl+S'])
    assert quick.takeShortcut()
    same()
    quick.close()
    prefs.close()
    print('settings-parity-ok')
'''


class SettingsParityTest(unittest.TestCase):
    def test_widgets_and_quick_apply_undo_restore_and_shortcut_assignment(self):
        environment = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'PYTHONUTF8': '1'}
        result = subprocess.run([sys.executable, '-c', SCRIPT], env=environment, capture_output=True,
                                text=True, timeout=90)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn('settings-parity-ok', result.stdout)
