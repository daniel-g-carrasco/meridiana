"""Study 56, point 1: Qt's disk caches of the program in the profile, one folder per version, the other versions thrown
away, never in the tests (app/platform/qt_cache.py)."""
import os
import tempfile
import unittest
from pathlib import Path

import _setup  # noqa: F401
from meridiana.app.platform import qt_cache


class Folders(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.profile = Path(self.temp.name)

    def test_a_version_has_its_folder_and_the_others_go(self):
        env = {"QML_DISABLE_DISK_CACHE": "1", "QSG_RHI_PIPELINE_CACHE_LOAD": "elsewhere"}
        old = qt_cache.prepare(self.profile, qt_cache.key_of("0.2.0", "6.12.0"), {})
        (old / "qml" / "a.qmlc").write_bytes(b"x")
        foreign = self.profile / qt_cache.FOLDER / "not-ours"      # without the mark: never thrown away
        foreign.mkdir()
        folder = qt_cache.prepare(self.profile, qt_cache.key_of("0.2.1", "6.12.0"), env)
        self.assertEqual(folder, self.profile / "qt-cache" / "0.2.1-qt6.12.0")
        self.assertFalse(old.exists())
        self.assertTrue(foreign.exists())
        self.assertEqual(env["QML_DISK_CACHE_PATH"], str(folder / "qml"))
        self.assertNotIn("QML_DISABLE_DISK_CACHE", env)
        self.assertEqual(env["QSG_RHI_PIPELINE_CACHE_SAVE"], str(folder / "pipeline.bin"))
        self.assertNotIn("QSG_RHI_PIPELINE_CACHE_LOAD", env)       # nothing saved yet: Qt would warn
        self.assertEqual(env["QT_DISABLE_SHADER_DISK_CACHE"], "1")  # Qt Quick 3D's: only under Qt's own folder
        (folder / "pipeline.bin").write_bytes(b"p")
        qt_cache.prepare(self.profile, qt_cache.key_of("0.2.1", "6.12.0"), env)
        self.assertEqual(env["QSG_RHI_PIPELINE_CACHE_LOAD"], str(folder / "pipeline.bin"))

    def test_a_folder_that_cannot_be_made_is_said_and_the_start_goes_on(self):
        blocked = self.profile / "file"
        blocked.write_text("not a folder")
        said, env = [], {}
        self.assertIsNone(qt_cache.prepare(blocked, "k", env, complain=lambda what, error: said.append(what)))
        self.assertEqual(len(said), 1)
        self.assertNotIn("QML_DISK_CACHE_PATH", env)

    def test_off_in_the_tests_and_in_what_is_not_the_program(self):
        self.assertFalse(qt_cache.wanted())                         # tests/_setup.py
        self.assertTrue(qt_cache.wanted({}))
        env = {"QML_DISK_CACHE_PATH": "x", "QSG_RHI_PIPELINE_CACHE_SAVE": "y"}
        qt_cache.turn_off(env)
        self.assertEqual(env, {"QML_DISABLE_DISK_CACHE": "1", "QT_DISABLE_SHADER_DISK_CACHE": "1"})
        self.assertEqual(qt_cache.key_of("0.2.1+dev 1", "6.12"), "0.2.1_dev_1-qt6.12")
        self.assertEqual(os.environ.get("MERIDIANA_QT_DISK_CACHE"), "0")


if __name__ == "__main__":
    unittest.main()
