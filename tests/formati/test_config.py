#!/usr/bin/env python3
"""The settings file: a round trip, the settings of a newer version kept,
a damaged file replaced by the previous save and said, format versions."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401

from meridiana import config
from meridiana.config import Config, backup_file, load, save


class ConfigTest(unittest.TestCase):
    def test_roundtrip_and_unknown_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c" / "config.json"
            self.assertEqual(load(path).theme, "system")
            cfg = Config(theme="dark", last_folder="/h/d")
            save(cfg, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["future_key"] = 1
            path.write_text(json.dumps(data), encoding="utf-8")
            again = load(path)
            self.assertEqual((again.theme, again.last_folder), ("dark", "/h/d"))
            self.assertEqual(sorted(os.listdir(path.parent)), ["config.json", "config.json.bak"])   # no temp leftovers
            # what a newer version wrote survives a round trip through this one
            save(again, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual((data["future_key"], data["version"]), (1, config.CONFIG_VERSION))
            self.assertNotIn("extra", data)
            self.assertNotIn("notices", data)

    def test_the_previous_save_is_kept_and_used_when_the_file_is_damaged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            save(Config(theme="dark"), path)
            save(Config(theme="light"), path)
            self.assertEqual(load(backup_file(path)).theme, "dark")      # the save before the last
            self.assertEqual(load(path).notices, [])
            path.write_text('{"theme": "light", "lang', encoding="utf-8")     # a crash mid-write elsewhere
            again = load(path)
            self.assertEqual(again.theme, "dark")
            self.assertEqual(again.notices[0].kind, "recovered")
            aside = Path(again.notices[0].detail)
            self.assertTrue(aside.name.startswith("config.json.broken-"), aside)
            self.assertIn("JSONDecodeError", again.notices[0].reason)
            self.assertTrue(path.exists())                               # written back at once
            self.assertEqual(load(path).notices, [])
            # the file gone, the previous save stands in
            path.unlink()
            again = load(path)
            self.assertEqual(again.theme, "dark")
            self.assertEqual(again.notices[0].kind, "missing")
            self.assertTrue(path.exists())

    def test_damaged_with_nothing_to_recover_starts_anew_and_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("[1, 2]", encoding="utf-8")
            cfg = load(path)
            self.assertEqual(cfg.theme, "system")
            self.assertEqual(cfg.notices[0].kind, "fresh")
            self.assertEqual(Path(cfg.notices[0].detail).read_text(encoding="utf-8"), "[1, 2]")
            save(cfg, path)                                             # now there is a .bak to fall back on
            # a value of the wrong kind is damage too, not a crash later on
            for bad in ('{"check_updates": 1}', '{"theme": 3}', '{"version": "2"}', '{"version": 2, "shortcuts": []}',
                        '{"version": 2, "shortcuts": {"fit": "F"}}'):
                path.write_text(bad, encoding="utf-8")
                self.assertEqual(load(path).notices[0].kind, "recovered", bad)

    def test_format_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            # a newer format: read for what is known, written back whole, said
            path.write_text(json.dumps({"version": config.CONFIG_VERSION + 1, "theme": "dark", "brand_new": True}),
                            encoding="utf-8")
            cfg = load(path)
            self.assertEqual(cfg.theme, "dark")
            self.assertEqual([n.kind for n in cfg.notices], ["newer"])
            save(cfg, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual((data["brand_new"], data["version"]), (True, config.CONFIG_VERSION))
            # an older format goes through the migration steps, one by one
            path.write_text(json.dumps({"version": 0, "old_theme": "dark"}), encoding="utf-8")
            with mock.patch.dict(config.MIGRATIONS, {0: lambda d: {**d, "theme": d.pop("old_theme")}}):
                cfg = load(path)
            self.assertEqual(cfg.theme, "dark")
            self.assertEqual(cfg.notices, [])
            path.write_text(json.dumps({"version": 0}), encoding="utf-8")
            self.assertEqual(load(path).notices[0].kind, "recovered")   # no step for it: as damaged

    def test_version_1_gets_the_table_of_the_changed_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"version": 1, "theme": "dark"}), encoding="utf-8")
            cfg = load(path)
            self.assertEqual((cfg.theme, cfg.shortcuts, cfg.notices), ("dark", {}, []))
            cfg.shortcuts = {"ortho": ["F9"]}
            save(cfg, path)
            self.assertEqual(load(path).shortcuts, {"ortho": ["F9"]})

    def test_version_2_gets_the_colour_and_the_backgrounds_of_the_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"version": 2, "theme": "dark", "shortcuts": {"fit": ["Z"]}}), encoding="utf-8")
            cfg = load(path)
            self.assertEqual((cfg.accent, cfg.backgrounds, cfg.shortcuts), ("bronze", "meridiana", {"fit": ["Z"]}))
            self.assertEqual(cfg.notices, [])

    def test_version_3_gets_the_navigation_of_the_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"version": 3, "accent": "plum"}), encoding="utf-8")
            cfg = load(path)
            self.assertEqual((cfg.accent, cfg.navigation, cfg.orbit, cfg.pivot), ("plum", "autocad", "turntable", "cursor"))
            self.assertEqual(cfg.notices, [])

    def test_version_4_gets_the_switch_of_the_assistant_on(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"version": 4, "navigation": "blender"}), encoding="utf-8")
            cfg = load(path)
            self.assertEqual((cfg.navigation, cfg.assistant, cfg.notices), ("blender", True, []))
            cfg.assistant = False
            save(cfg, path)
            self.assertFalse(load(path).assistant)

    def test_version_5_gets_the_veil_over_the_imagery_at_forty_percent(self):
        from meridiana import view_colours
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"version": 5, "background": "osm"}), encoding="utf-8")
            cfg = load(path)
            self.assertEqual((cfg.background, cfg.veil, cfg.notices), ("osm", view_colours.VEIL, []))
            cfg.veil = 0.6
            save(cfg, path)
            self.assertEqual(load(path).veil, 0.6)

    def test_version_6_gets_the_toolbar_with_the_icons_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"version": 6, "veil": 0.2}), encoding="utf-8")
            cfg = load(path)
            self.assertEqual((cfg.veil, cfg.toolbar, cfg.notices), (0.2, "text", []))   # v10 settles it
            cfg.toolbar = "text"
            save(cfg, path)
            self.assertEqual(load(path).toolbar, "text")

    def test_version_7_gets_the_assistant_floating_as_it_was(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"version": 7, "toolbar": "text"}), encoding="utf-8")
            cfg = load(path)
            self.assertEqual((cfg.toolbar, cfg.assistant_docked, cfg.notices), ("text", False, []))
            cfg.assistant_docked = True
            save(cfg, path)
            self.assertTrue(load(path).assistant_docked)

    def test_version_8_gets_the_three_network_switches_on_as_the_program_behaved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"version": 8, "assistant_docked": True}), encoding="utf-8")
            cfg = load(path)
            self.assertEqual((cfg.network_geocoding, cfg.network_pvgis, cfg.network_tiles, cfg.notices),
                             (True, True, True, []))
            cfg.network_tiles = False
            save(cfg, path)
            self.assertFalse(load(path).network_tiles)

    def test_version_9_gets_the_text_under_the_icons_and_the_bar_on_top(self):
        # the preference changes meaning (task 17b, design C1): "text" is now the words under the icons, the
        # default Daniel chose; the old "icons" was the old default and becomes it too
        for old in ("icons", "text"):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "config.json"
                path.write_text(json.dumps({"version": 9, "toolbar": old, "network_tiles": False}), encoding="utf-8")
                cfg = load(path)
                self.assertEqual((cfg.toolbar, cfg.toolbar_place, cfg.network_tiles, cfg.notices),
                                 ("text", "top", False, []))
                cfg.toolbar, cfg.toolbar_place = "icons", "left"
                save(cfg, path)
                self.assertEqual((load(path).toolbar, load(path).toolbar_place), ("icons", "left"))
        self.assertEqual((Config().toolbar, Config().toolbar_place), ("text", "top"))

    def test_version_10_gets_meridio_animated_smooth_and_his_bubble_at_320_by_400(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            # what version 10 brought (the bar of the phase as chosen) stays as it was
            path.write_text(json.dumps({"version": 10, "toolbar": "icons", "toolbar_place": "left"}), encoding="utf-8")
            cfg = load(path)
            self.assertEqual((cfg.toolbar, cfg.toolbar_place, cfg.assistant_animated, cfg.assistant_style,
                              cfg.assistant_width, cfg.assistant_height, cfg.notices),
                             ("icons", "left", True, "smooth", 320, 400, []))
            cfg.assistant_style, cfg.assistant_width = "pixel", 460
            save(cfg, path)
            again = load(path)
            self.assertEqual((again.assistant_style, again.assistant_width), ("pixel", 460))

    def test_version_11_gets_the_checks_panel_by_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            # what versions 10 and 11 brought stays as it was
            path.write_text(json.dumps({"version": 11, "toolbar_place": "left", "assistant_style": "pixel",
                                        "network_tiles": False}), encoding="utf-8")
            cfg = load(path)
            self.assertEqual((cfg.toolbar_place, cfg.assistant_style, cfg.network_tiles, cfg.checks_view, cfg.notices),
                             ("left", "pixel", False, "level", []))
            cfg.checks_view = "object"
            save(cfg, path)
            self.assertEqual(load(path).checks_view, "object")

    def test_version_12_gets_the_help_box_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            for version in (12,):
                path.write_text(json.dumps({"version": version, "checks_view": "area"}), encoding="utf-8")
                cfg = load(path)
                self.assertEqual((cfg.checks_view, cfg.help_open, cfg.notices), ("area", True, []))
            cfg.help_open = False
            save(cfg, path)
            self.assertFalse(load(path).help_open)

    def test_version_18_gets_the_best_source_for_the_site_in_place_of_the_old_default_and_no_source_of_its_own(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            for before, after in (("pcn", "auto"), ("osm", "osm"), ("none", "none"), ("opentopomap", "opentopomap")):
                path.write_text(json.dumps({"version": 18, "background": before}), encoding="utf-8")
                cfg = load(path)
                self.assertEqual((cfg.background, cfg.map_sources, cfg.notices), (after, [], []))
            path.write_text(json.dumps({"version": 18}), encoding="utf-8")         # the default of then, unwritten
            self.assertEqual(load(path).background, "auto")

    def test_version_9_reaches_the_latest_version_with_every_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"version": 9, "network_tiles": False}), encoding="utf-8")
            cfg = load(path)
            self.assertEqual(cfg.notices, [])
            self.assertEqual(cfg, Config(network_tiles=False))
            self.assertEqual((cfg.toolbar, cfg.toolbar_place, cfg.assistant_animated, cfg.assistant_style,
                              cfg.assistant_width, cfg.assistant_height, cfg.checks_view, cfg.help_open),
                             ("text", "top", True, "smooth", 320, 400, "level", True))
            save(cfg, path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["version"], 20)
            self.assertEqual(config.CONFIG_VERSION, 20)
            self.assertEqual((cfg.background, cfg.map_sources), ("auto", []))     # the best for the site (R36)
            self.assertEqual((cfg.assistant_voice_engine, cfg.assistant_voice_name), ("auto", ""))
            self.assertEqual((cfg.menu_bar, cfg.recent), (False, []))      # the menus hidden until Alt (R53)
            self.assertEqual((cfg.report_profiles, cfg.report_profile), ([], ""))     # no author until one is written
            self.assertEqual((cfg.assistant_provider, cfg.assistant_consent, cfg.assistant_voice), ("local", {}, False))
            # Meridio presents himself once, also to whoever used him before (R106); the local server's API (R105)
            self.assertEqual((cfg.assistant_introduced, cfg.assistant_local_runtime), (False, ""))

    def test_version_13_moves_a_measure_on_m_to_d_and_leaves_the_other_keys_of_the_designer(self):
        """M is Move from version 14 and Measure goes to D (study 16, B; Daniel, 23/10/2026)."""
        from meridiana import shortcuts
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            for keys, measure in (({"tool_measure": ["M", "Shift+M"]}, ["D", "Shift+M"]),
                                  ({"tool_measure": ["M"], "fit": ["Z"]}, None),
                                  ({"tool_measure": []}, []),
                                  ({"tool_measure": ["K"]}, ["K"])):
                with self.subTest(keys=keys):
                    path.write_text(json.dumps({"version": 13, "shortcuts": keys}), encoding="utf-8")
                    cfg = load(path)
                    self.assertEqual(cfg.notices, [])
                    self.assertEqual(cfg.shortcuts.get("tool_measure"), measure)
                    used = shortcuts.bindings(cfg.shortcuts)
                    self.assertEqual(used["tool_move"], ["M"])
                    self.assertEqual(shortcuts.conflicts(used), {})
            self.assertEqual(cfg.shortcuts, {"tool_measure": ["K"]})
            # a designer who had given M to another command keeps it, and Move is left without it
            path.write_text(json.dumps({"version": 13, "shortcuts": {"tool_measure": ["Shift+M"], "fit": ["M"]}}),
                            encoding="utf-8")
            used, notes = shortcuts.settle(load(path).shortcuts)
            self.assertEqual((used["fit"], used["tool_move"], notes), (["M"], [], [("M", ["fit"], ["tool_move"])]))

    def test_the_pivots_cross_hair_on_passing_over_is_on_and_needs_no_new_format_version(self):
        """A setting added with a default of the right type is read from the files before it (config.py): the file of
        a version that did not have it opens with it on, and the version stays."""
        self.assertTrue(Config().pivot_hint)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"version": config.CONFIG_VERSION, "pivot": "selection"}), encoding="utf-8")
            cfg = load(path)
            self.assertEqual((cfg.pivot, cfg.pivot_hint, cfg.notices), ("selection", True, []))
            cfg.pivot_hint = False
            save(cfg, path)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual((saved["pivot_hint"], saved["version"]), (False, config.CONFIG_VERSION))
            self.assertFalse(load(path).pivot_hint)
            path.write_text(json.dumps({"version": config.CONFIG_VERSION, "pivot_hint": "yes"}), encoding="utf-8")
            self.assertEqual([n.kind for n in load(path).notices], ["recovered"])  # a word for a switch is damage

    def test_version_15_gets_meridio_on_the_local_model_without_consents_and_silent(self):
        """Version 17 (task 14): where Meridio thinks, the consents to the cloud, his voice; never a key."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"version": 15, "assistant_style": "pixel"}), encoding="utf-8")
            cfg = load(path)
            self.assertEqual(cfg.notices, [])
            self.assertEqual((cfg.assistant_provider, cfg.assistant_local_url, cfg.assistant_local_model,
                              cfg.assistant_cloud_model, cfg.assistant_consent, cfg.assistant_voice),
                             ("local", "http://127.0.0.1:9931/v1", "", "claude-haiku-5-5", {}, False))
            self.assertEqual(cfg.assistant_style, "pixel")
            cfg.assistant_consent = {"anthropic": ["2026-10-24"]}
            save(cfg, path)
            self.assertEqual(load(path).assistant_consent, {"anthropic": ["2026-10-24"]})
            path.write_text(json.dumps({"version": 16, "assistant_consent": {"anthropic": True}}), encoding="utf-8")
            self.assertEqual([n.kind for n in load(path).notices], ["recovered"])    # a switch for a table: damage

    def test_no_secret_is_ever_saved(self):
        text = json.dumps(Config(assistant_provider="claude").to_json()).lower()
        self.assertNotIn("password", text)
        self.assertNotIn("api_key", text)
        self.assertNotIn("sk-ant", text)


if __name__ == "__main__":
    unittest.main()
