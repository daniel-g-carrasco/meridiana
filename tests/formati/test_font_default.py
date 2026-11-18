"""New preferences use Plex while saved choices and historic migrations remain unchanged."""
import json
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401
from meridiana import config


class FontDefault(unittest.TestCase):
    def test_fresh_config_uses_plex_and_old_choices_remain(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'settings.json'
            self.assertEqual(config.load(path).font, 'plex')
            self.assertEqual(config.Config().font, 'plex')
            for font in ('inter', 'plex'):
                config.save(config.Config(font=font), path)
                self.assertEqual(config.load(path).font, font)
            path.write_text(json.dumps({'version': 25}), encoding='utf-8')
            self.assertEqual(config.load(path).font, 'inter')
            self.assertGreaterEqual(config.CONFIG_VERSION, 26)
