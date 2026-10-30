"""The files Meridiana writes and reads, as they are on the designer's disk (study 18, D 6.1 and 6.5; task 18e,
step 1): one frozen settings file for every version of the format, 1 to 16 (the project's, 1 to 10, are opened in
test_model.Formats), files cut short, not in UTF-8 or of a newer version, and the writes that fail half way.

The files of tests/formati/file were written once and are never written again: a change of format adds the
file of the new version. The settings files were rebuilt on 24/10/2026 from the fields of each version (the
`Config` of its commit) and from what each migrator of config.py says the version brought, with a choice of the
designer's in every key, so that a key lost on the way would not hide behind its default."""

import dataclasses
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup

from meridiana import atomic, config, model, session

FOLDER = _setup.FORMATS

# what each version of the settings brought (config.py, the migrators and the Config of each version's commit)
BROUGHT = {
    1: {"theme", "language", "check_updates", "last_update_check", "last_folder"},
    2: {"last_project", "background", "shortcuts"},
    3: {"accent", "backgrounds"},
    4: {"navigation", "orbit", "pivot"},
    5: {"assistant"},
    6: {"veil"},
    7: {"toolbar"},
    8: {"assistant_docked"},
    9: {"network_geocoding", "network_pvgis", "network_tiles"},
    10: {"toolbar_place"},
    11: {"assistant_animated", "assistant_style", "assistant_width", "assistant_height"},
    12: {"checks_view"},
    13: {"help_open"},
    14: {"pivot_hint"},
    15: {"menu_bar", "recent"},
    16: {"report_profiles", "report_profile"},
    18: {"assistant_voice_engine", "assistant_voice_name", "assistant_kokoro_dir", "assistant_kokoro_python"},
    17: {"assistant_provider", "assistant_local_url", "assistant_local_model", "assistant_cloud_model",
         "assistant_consent", "assistant_voice"},
    19: {"map_sources"},
    20: {"assistant_introduced", "assistant_local_runtime"},
    21: {"text_size"},
    22: {"auto_install_updates", "pending_update", "tour_status", "tour_step"},
    23: {"assistant_cloud_profiles"},
    24: {"inverter_brand_favourites"},
}


def read(name: str) -> dict:
    return json.loads((FOLDER / name).read_text(encoding="utf-8"))


class SettingsFiles(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = self.dir / "config.json"

    def put(self, name: str, as_name: str = "config.json") -> Path:
        shutil.copyfile(FOLDER / name, self.dir / as_name)
        return self.dir / as_name

    def test_each_frozen_file_has_what_its_version_brought_and_nothing_later(self):
        self.assertEqual(sorted(BROUGHT), list(range(1, config.CONFIG_VERSION + 1)))
        before: set = set()
        for version in range(1, config.CONFIG_VERSION + 1):
            with self.subTest(version=version):
                keys = set(read(f"config-v{version}.json")) - {"version"}
                self.assertEqual(read(f"config-v{version}.json")["version"], version)
                self.assertEqual(keys - before, BROUGHT[version])
                self.assertLessEqual(before, keys)          # what the version before had, kept
                before = keys
        fields = {f.name for f in dataclasses.fields(config.Config)} - {"extra", "notices"}
        self.assertEqual(before, fields)                    # the last one has every field of today

    def test_every_version_of_the_settings_opens_with_the_designers_choices(self):
        defaults = config.Config()
        for version in range(1, config.CONFIG_VERSION + 1):
            with self.subTest(version=version):
                raw = read(f"config-v{version}.json")
                cfg = config.load(self.put(f"config-v{version}.json"))
                self.assertEqual(cfg.notices, [])
                self.assertEqual(cfg.extra, {})             # every key of the file is known today
                for f in dataclasses.fields(config.Config):
                    if f.name in ("extra", "notices"):
                        continue
                    got = getattr(cfg, f.name)
                    if f.name == "toolbar" and version < 10:
                        self.assertEqual(got, "text", "version 10 gives everybody the text under the icons")
                    elif f.name == "shortcuts" and version == 13:
                        self.assertEqual(got, {"fit": ["Z"], "tool_measure": ["D", "Shift+M"]})   # M is Move from 14
                    elif f.name in raw:
                        self.assertEqual(got, raw[f.name], f.name)
                    else:
                        self.assertEqual(got, getattr(defaults, f.name), f.name)
                config.save(cfg, self.path)                 # written back in today's version, the same settings
                self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["version"], config.CONFIG_VERSION)
                self.assertEqual(config.load(self.path), cfg)

    def test_settings_of_a_newer_version_are_used_and_what_this_one_does_not_know_is_written_back(self):
        cfg = config.load(self.put("config-futuro.json"))
        self.assertEqual(cfg.notices, [config.Notice("newer", "99")])
        self.assertEqual((cfg.theme, cfg.accent, cfg.navigation), ("dark", "plum", "blender"))
        self.assertEqual(cfg.extra, {"brand_new": {"kept": [1, 2]}})
        config.save(cfg, self.path)
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual((saved["brand_new"], saved["version"]), ({"kept": [1, 2]}, config.CONFIG_VERSION))

    def test_settings_cut_short_are_set_aside_and_said_and_the_previous_save_is_used_when_there(self):
        self.put("config-troncato.json")
        cfg = config.load(self.path)
        [notice] = cfg.notices
        self.assertEqual(notice.kind, "fresh")              # nothing to recover: a fresh start, said
        self.assertIn("JSONDecodeError", notice.reason)
        self.assertEqual(Path(notice.detail).read_bytes(), (FOLDER / "config-troncato.json").read_bytes())
        self.assertEqual(cfg, config.Config())
        self.put("config-troncato.json")
        self.put("config-v14.json", "config.json.bak")
        cfg = config.load(self.path)
        self.assertEqual([n.kind for n in cfg.notices], ["recovered"])
        self.assertEqual((cfg.theme, cfg.pivot_hint), ("dark", False))
        self.assertEqual(config.load(self.path).notices, [])   # and written again whole

    def test_the_starred_makers_survive_a_save_and_a_restart_and_anything_else_there_is_damage(self):
        """R268: the favourites of the picker are a list of texts in the settings (format 24), the first list of
        texts the file has: written and read back as they are, in their order, accents included; a file that
        holds something else under that key is damaged, and the previous save is used."""
        cfg = config.load(self.put("config-v23.json"))
        self.assertEqual(cfg.inverter_brand_favourites, [])     # migrated from 23: none starred yet
        cfg.inverter_brand_favourites = ["Huawei", "SMA", "Zeta Énergie"]
        config.save(cfg, self.path)
        again = config.load(self.path)
        self.assertEqual(again.notices, [])
        self.assertEqual(again.inverter_brand_favourites, ["Huawei", "SMA", "Zeta Énergie"])
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["inverter_brand_favourites"],
                         ["Huawei", "SMA", "Zeta Énergie"])
        for damaged in ("Huawei", ["Huawei", 3], {"Huawei": True}):
            with self.subTest(value=damaged):
                data = json.loads((FOLDER / "config-v24.json").read_text(encoding="utf-8"))
                data["inverter_brand_favourites"] = damaged
                self.path.write_text(json.dumps(data), encoding="utf-8")
                self.put("config-v24.json", "config.json.bak")
                cfg = config.load(self.path)
                self.assertEqual([n.kind for n in cfg.notices], ["recovered"])
                self.assertIn("is not a list of text", cfg.notices[0].reason)
                self.assertEqual(cfg.inverter_brand_favourites, ["Huawei", "SMA", "Fronius"])  # the previous save


class ProjectFiles(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.file = self.dir / "Rho.meridiana"

    def put(self, name: str, as_name: str = "Rho.meridiana") -> Path:
        shutil.copyfile(FOLDER / name, self.dir / as_name)
        return self.dir / as_name

    def test_a_project_cut_short_opens_the_previous_save_and_says_so(self):
        self.put("progetto-troncato.meridiana")
        with self.assertRaises(ValueError):                 # no previous save: it cannot be opened, and says why
            model.Project.load(self.file)
        self.put("progetto-v10.meridiana", "Rho.meridiana.bak")
        p, notice = model.Project.load(self.file)
        self.assertEqual((p.name, len(p.subfields[0].rows)), ("Capannone Rho", 3))
        self.assertIn("Rho.meridiana could not be read (JSONDecodeError", notice)
        self.assertIn("the previous save was opened", notice)

    def test_a_project_not_in_utf8_opens_the_previous_save_and_says_so(self):
        self.put("progetto-latin1.meridiana")
        with self.assertRaises(UnicodeDecodeError):
            model.Project.load(self.file)
        self.put("progetto-v9.meridiana", "Rho.meridiana.bak")
        p, notice = model.Project.load(self.file)
        self.assertEqual(p.name, "Capannone Rho")
        self.assertIn("UnicodeDecodeError", notice)

    def test_project_file_errors_speak_italian(self):
        from meridiana import i18n
        before = i18n._translation
        self.addCleanup(lambda: setattr(i18n, "_translation", before))
        i18n.setup("it")
        self.file.write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            model.Project.load(self.file)
        self.assertEqual(str(caught.exception), "non è un progetto di Meridiana")
        self.put("progetto-futuro.meridiana")
        with self.assertRaises(ValueError) as caught:
            model.Project.load(self.file)
        self.assertEqual(str(caught.exception), "creato da una versione più recente di Meridiana (formato 99); "
                         "aggiorna il programma per aprirlo")

    def test_a_project_of_a_newer_version_is_refused_with_the_reason_and_the_file_stays(self):
        self.put("progetto-futuro.meridiana")
        before = self.file.read_bytes()
        with self.assertRaises(ValueError) as caught:
            model.Project.load(self.file)
        self.assertIn("newer Meridiana (format 99)", str(caught.exception))
        self.assertIn("update the program", str(caught.exception))
        self.assertEqual(self.file.read_bytes(), before)
        s = session.ProjectSession(model.Project(name="In hand"))
        with self.assertRaises(ValueError):
            s.open(self.file)
        self.assertEqual(s.project.name, "In hand")         # the project in hand stays


class AtomicWrites(unittest.TestCase):
    """atomic.py: written whole or not at all, the previous copy kept as .bak; config.py keeps its own backup by a
    link or a copy, and a backup that cannot be made does not stop the settings from being saved."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.file = self.dir / "Rho.meridiana"
        atomic.write_json(self.file, {"name": "old"})
        self.old = self.file.read_bytes()

    def left(self) -> list:
        return sorted(p.name for p in self.dir.iterdir())

    def test_a_write_that_fails_half_way_leaves_the_old_file_whole_and_no_temporary_file(self):
        with mock.patch.object(atomic.os, "fsync", side_effect=OSError(28, "No space left on device")):
            with self.assertRaises(OSError):
                atomic.write_json(self.file, {"name": "new"})
        self.assertEqual(self.file.read_bytes(), self.old)
        self.assertEqual(self.left(), ["Rho.meridiana"])    # no .tmp left behind, no backup of a save that failed
        # the rename refused at the end (the file open in another program on Windows): the old one stays, the
        # backup of it is there, the temporary file goes
        with mock.patch.object(atomic.os, "replace", side_effect=PermissionError(13, "Permission denied")):
            with self.assertRaises(PermissionError):
                atomic.write_json(self.file, {"name": "new"})
        self.assertEqual(self.file.read_bytes(), self.old)
        self.assertEqual(self.left(), ["Rho.meridiana", "Rho.meridiana.bak"])
        self.assertEqual((self.dir / "Rho.meridiana.bak").read_bytes(), self.old)

    def test_a_backup_that_cannot_be_made_stops_the_project_save_and_leaves_the_old_file(self):
        with mock.patch.object(atomic.shutil, "copy2", side_effect=PermissionError(13, "Permission denied")):
            with self.assertRaises(PermissionError):
                atomic.write_json(self.file, {"name": "new"})
        self.assertEqual(self.file.read_bytes(), self.old)
        self.assertEqual(self.left(), ["Rho.meridiana"])

    def test_a_folder_that_takes_no_file_raises_and_the_session_stays_modified(self):
        p = model.Project(name="Rho")
        s = session.ProjectSession(p, self.file)
        s.edit("Rename", lambda q: setattr(q, "name", "Rho 2"))
        self.assertTrue(s.dirty())
        with mock.patch.object(atomic.tempfile, "mkstemp", side_effect=PermissionError(13, "Permission denied")):
            with self.assertRaises(PermissionError):
                s.save()
        self.assertTrue(s.dirty())                           # nothing was saved: still to save
        self.assertEqual(self.file.read_bytes(), self.old)
        self.assertEqual(self.left(), ["Rho.meridiana"])
        if os.name == "posix" and os.geteuid() != 0:        # a folder truly read-only (Windows ignores the flag)
            locked = self.dir / "locked"
            locked.mkdir()
            locked.chmod(0o500)
            self.addCleanup(locked.chmod, 0o700)
            with self.assertRaises(PermissionError):
                atomic.write_json(locked / "Rho.meridiana", {"name": "x"})
            self.assertEqual(list(locked.iterdir()), [])

    def test_the_settings_are_saved_even_when_their_backup_cannot_be_made(self):
        path = self.dir / "config.json"
        config.save(config.Config(theme="dark"), path)
        with mock.patch.object(config.os, "link", side_effect=OSError("no links here")), \
                mock.patch.object(config.shutil, "copyfile", side_effect=PermissionError(13, "Permission denied")):
            config.save(config.Config(theme="light"), path)
        self.assertEqual(config.load(path).theme, "light")
        self.assertFalse(config.backup_file(path).exists())
        with mock.patch.object(config.os, "fsync", side_effect=OSError(28, "No space left on device")):
            with self.assertRaises(OSError):
                config.save(config.Config(theme="dark"), path)
        self.assertEqual(config.load(path).theme, "light")  # the save that failed changed nothing
        self.assertEqual(sorted(p.name for p in self.dir.iterdir() if p.name.startswith(".config-")), [])


if __name__ == "__main__":
    unittest.main()
