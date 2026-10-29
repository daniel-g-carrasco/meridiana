"""Meridio searches and prepares projects from the local index, without opening them himself (R151)."""

import json
import unittest

import _setup  # noqa: F401
from _fakes import Host
from _fixtures import capannone

from meridiana.assistant import tools


def row(name, series, revision, modified, kind="roof", power=100.0, mounting="tilted_anchored"):
    number = int(revision[1:]) if revision else 0
    return {"path": f"/jobs/{name}_{revision}.meridiana", "name": f"{name}_{revision}", "title": name,
            "series_id": series, "revision": revision, "revision_number": number, "modified": modified,
            "file_modified": modified, "kind": kind, "power_kwp": power, "mountings": [mounting],
            "tilts": [15.0], "lat": 45.5, "lon": 9.0, "address": "Example town",
            "job_id": "job1", "job_code": "26042", "job_name": name, "client_name": "Example client",
            "reserved": False, "error": ""}


def rows():
    return [row("Reference shed", "reference", "R01", "2026-01-01T10:00:00+00:00", power=96.0),
            row("Older shed", "same", "R02", "2026-02-01T10:00:00+00:00"),
            row("Latest shed", "same", "R04", "2026-03-01T10:00:00+00:00"),
            row("Another shed", "other", "R05", "2026-04-01T10:00:00+00:00"),
            row("Ground array", "ground", "R09", "2026-05-01T10:00:00+00:00", kind="ground")]


class ArchiveHost(Host):
    def __init__(self, projects):
        super().__init__(capannone(), lay=False)
        self._index = projects
        self.opened = []

    def index_rows(self):
        return self._index

    def path(self):
        return self._index[0]["path"]

    def dirty(self):
        return False

    def open_project(self, path):
        self.opened.append(path)
        return True


class MeridioProjectsTest(unittest.TestCase):
    def setUp(self):
        self.host = ArchiveHost(rows())
        self.state = tools.State()

    def search(self, query="shed"):
        outcome = tools.run("search_projects", {"query": query}, self.host, self.state)
        self.assertFalse(outcome.error)
        return json.loads(outcome.content)

    def test_search_uses_local_aliases_and_prepare_open_only_shows_a_confirmation(self):
        found = self.search()
        self.assertEqual(len(found["projects"]), 4)
        self.assertEqual(found["projects"][0]["id"], "pr1")
        outcome = tools.run("prepare_open_project", {"project_id": "pr2"}, self.host, self.state)
        proposal = outcome.proposal
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.kind, "open_project")
        self.assertEqual(proposal.item["revision"], "R02")
        self.assertIn((("Path"), "", "/jobs/Older shed_R02.meridiana"), proposal.lines)
        self.assertIn((("Revision"), "", "R02"), proposal.lines)
        self.assertEqual(self.host.opened, [])

    def test_similar_projects_counts_each_series_once_and_explains_the_latest_valid_revision(self):
        found = self.search()
        reference = next(item["id"] for item in found["projects"] if item["title"] == "Reference shed")
        outcome = tools.run("similar_projects", {"project_id": reference}, self.host, self.state)
        result = json.loads(outcome.content)
        self.assertEqual([item["title"] for item in result["projects"]], ["Another shed", "Latest shed"])
        self.assertEqual([item["revision"] for item in result["projects"]], ["R05", "R04"])
        self.assertIn("roof", result["projects"][0]["reason"])
        self.assertIn("100.0 kWp", result["projects"][0]["reason"])
        self.assertIn("same mounting", result["projects"][0]["reason"])

    def test_project_revisions_returns_only_the_latest_valid_row_of_a_series(self):
        damaged = row("Damaged shed", "same", "R06", "2026-06-01T10:00:00+00:00")
        damaged["error"] = "damaged JSON"
        self.host._index.append(damaged)
        outcome = tools.run("project_revisions", {"series_id": "same"}, self.host, self.state)
        result = json.loads(outcome.content)
        self.assertEqual([(item["revision"], item["title"]) for item in result["projects"]], [("R04", "Latest shed")])

    def test_search_filters_power_date_and_distance(self):
        far = row("Far shed", "far", "R08", "2026-06-01T10:00:00+00:00")
        far["lat"], far["lon"] = 0.0, 0.0
        self.host._index.append(far)
        found = self.search()
        reference = next(item["id"] for item in found["projects"] if item["title"] == "Reference shed")
        outcome = tools.run("search_projects", {"query": "shed", "kind": "roof", "power_from": 90,
                                                "power_to": 110, "since": "2026-03-01",
                                                "project_id": reference, "max_distance_km": 100},
                            self.host, self.state)
        result = json.loads(outcome.content)
        self.assertEqual([item["title"] for item in result["projects"]], ["Latest shed", "Another shed"])


if __name__ == "__main__":
    unittest.main()
