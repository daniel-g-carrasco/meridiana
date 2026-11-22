"""The settings the Quick keeps after each choice, undo, restore and shortcut, as the Widgets' Preferences kept them
for the same gestures (recorded on 10/11/2026, quick/aiuti/riferimenti.py). In a process of its own, offscreen."""
import gzip
import json
import os
import subprocess
import sys
import unittest

from pathlib import Path

from meridiana.app.platform import config
from quick.aiuti.differential import compare

SCRIPT = r'''
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from meridiana.app.platform import config
from meridiana.app.assistant.local import Survey
from meridiana.gui.backend.settings import SettingsBackend

app = QApplication([])
states = []
with TemporaryDirectory() as folder, patch('meridiana.app.assistant.keys.get', return_value=''), \
     patch('meridiana.app.assistant.setup.available', return_value=[]), \
     patch('meridiana.app.assistant.local.survey', return_value=Survey()):
    quick_config = config.Config(extra={'future': {'number': 12}})
    quick = SettingsBackend(quick_config, Path(folder) / 'quick.json')

    def same():
        states.append({'held': quick_config.to_json(), 'saved': config.load(Path(folder) / 'quick.json').to_json()})

    assert quick.setValue('orbit', 'arcball')
    same()
    quick.undoLast()
    same()
    quick.setValue('pivot', 'selection')
    quick.restoreDefaults('navigation')
    same()

    quick.setValue('network_geocoding', False)
    same()
    quick.restoreDefaults('privacy')
    same()
    quick.undoLast()
    same()

    quick.setValue('theme', 'dark')
    same()
    quick.setValue('font', 'plex')
    same()

    assert not quick.setShortcut('open', ['Ctrl+S'])
    assert quick.takeShortcut()
    same()
    quick.close()
    print('settings-states ' + json.dumps(states))
'''


class SettingsParityTest(unittest.TestCase):
    def test_widgets_and_quick_apply_undo_restore_and_shortcut_assignment(self):
        environment = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'PYTHONUTF8': '1'}
        result = subprocess.run([sys.executable, '-c', SCRIPT], env=environment, capture_output=True,
                                text=True, timeout=90)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        line = next((x for x in result.stdout.splitlines() if x.startswith('settings-states ')), None)
        self.assertIsNotNone(line, result.stdout)
        actual = json.loads(line.split(' ', 1)[1])
        path = Path(__file__).with_name('riferimenti') / (Path(__file__).stem + '.' + self._testMethodName + '.1.json.gz')
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            expected = json.load(stream)
        # Keep the recorded choices intact, applying the same format migrations as an old profile.
        for state in expected:
            for key in ('held', 'saved'):
                state[key] = config.Config.from_json(config.migrate(state[key])).to_json()
        self.assertEqual(compare(expected, actual), [])
