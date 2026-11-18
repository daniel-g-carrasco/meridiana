"""New colour defaults do not rewrite choices already stored in settings."""
import json
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401
from meridiana import config


class ColourDefaults(unittest.TestCase):
    def test_new_configs_use_grey_and_indigo_while_saved_choices_survive(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'settings.json'
            for cfg in (config.Config(), config.load(path)):
                self.assertEqual((cfg.backgrounds, cfg.accent), ('grey', 'indigo'))
            for backgrounds, accent in (('meridiana', 'bronze'), ('tinted', '#abcdef'), ('grey', 'system')):
                config.save(config.Config(backgrounds=backgrounds, accent=accent), path)
                actual = config.load(path)
                self.assertEqual((actual.backgrounds, actual.accent), (backgrounds, accent))
            path.write_text(json.dumps({'version': 2}), encoding='utf-8')
            historic = config.load(path)
            self.assertEqual((historic.backgrounds, historic.accent), ('meridiana', 'bronze'))
            self.assertGreaterEqual(config.CONFIG_VERSION, 26)
