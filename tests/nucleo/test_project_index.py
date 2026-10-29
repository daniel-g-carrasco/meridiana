"""The derived local index of known project folders (R151)."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401
from _fixtures import capannone

from meridiana import project_index, registry


class ProjectIndexTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.reg = registry.Registry(self.folder / "registry.sqlite3")
        self.addCleanup(self.reg.close)
        client = self.reg.create_client("Example client")
        self.job = self.reg.create_job("26042", "Example shed", client["id"], reserved=False)
        self.metadata = {"job_id": self.job["id"], "job_code": "26042", "job_name": "Example shed",
                         "client_name": "Example client", "reserved": False}

    def project_file(self, name="shed_R04.meridiana"):
        project = capannone("Example shed")
        project.job_id = self.job["id"]
        project.series_id = "series-stable-id"
        path = self.folder / name
        project.save(path)
        return path

    def test_an_index_row_has_the_search_data_without_the_whole_project(self):
        path = self.project_file()
        row = project_index.read(path, self.metadata)
        self.assertEqual(row["series_id"], "series-stable-id")
        self.assertEqual(row["job_code"], "26042")
        self.assertEqual(row["client_name"], "Example client")
        self.assertEqual(row["kind"], "roof")
        self.assertEqual(row["power_kwp"], 57.6)
        self.assertEqual(row["buildings"], 1)
        self.assertEqual(row["subfields"], 1)
        self.assertEqual(row["mountings"], ["tilted_anchored"])
        self.assertEqual(row["tilts"], [15.0])
        self.assertEqual(row["revision"], "R04")
        self.assertEqual(row["revision_number"], 4)
        self.assertFalse(row["reserved"])
        self.assertEqual(row["error"], "")
        self.assertNotIn("resources", row)
        self.assertNotIn("report", row)

    def test_an_unchanged_file_is_not_read_again_and_a_damaged_one_stays_visible(self):
        path = self.project_file()
        first = project_index.scan([(self.folder, self.metadata)], {})
        with mock.patch("meridiana.model.Project.from_json", side_effect=AssertionError("read again")):
            second = project_index.scan([(self.folder, self.metadata)],
                                        {row["path"]: row for row in first})
        self.assertEqual(second, first)
        path.write_text("not a project", encoding="utf-8")
        third = project_index.scan([(self.folder, self.metadata)], {row["path"]: row for row in second})
        self.assertEqual(len(third), 1)
        self.assertEqual(third[0]["path"], str(path))
        self.assertIn("JSON", third[0]["error"])

    def test_an_unchanged_file_takes_the_current_registry_metadata(self):
        self.project_file()
        first = project_index.scan([(self.folder, self.metadata)], {})
        changed = {**self.metadata, "client_name": "Renamed client", "reserved": True}
        with mock.patch("meridiana.model.Project.from_json", side_effect=AssertionError("read again")):
            second = project_index.scan([(self.folder, changed)], {row["path"]: row for row in first})
        self.assertEqual(second[0]["client_name"], "Renamed client")
        self.assertTrue(second[0]["reserved"])
        with mock.patch("meridiana.model.Project.from_json", side_effect=AssertionError("read again")):
            third = project_index.scan([(self.folder, self.metadata)], {row["path"]: row for row in second})
        self.assertFalse(third[0]["reserved"])

    def test_a_series_without_an_id_uses_the_folder_and_revisionless_name(self):
        project = capannone("Old example")
        path = self.folder / "old_shed_R07.meridiana"
        project.save(path)
        row = project_index.read(path)
        self.assertEqual(row["series_id"], str(self.folder / "old_shed"))
        self.assertTrue(row["series_inferred"])
        self.assertEqual(row["revision"], "R07")

    def test_the_registry_persists_and_replaces_the_derived_index(self):
        path = self.project_file()
        row = project_index.read(path, self.metadata)
        self.reg.replace_index([row])
        self.assertEqual(self.reg.list_index(), [row])
        self.reg.replace_index([])
        self.assertEqual(self.reg.list_index(), [])


if __name__ == "__main__":
    unittest.main()
