"""The archive is filtered and redacted by Meridiana before any cloud message (R151)."""

import json
import unittest

import _setup  # noqa: F401
from _fixtures import capannone

from meridiana.assistant import privacy, tools


def row(name, series, revision, modified):
    return {"path": f"/jobs/{name}_{revision}.meridiana", "name": f"{name}_{revision}", "title": name,
            "series_id": series, "revision": revision, "revision_number": int(revision[1:]), "modified": modified,
            "file_modified": modified, "kind": "roof", "power_kwp": 100.0, "mountings": ["tilted_anchored"],
            "tilts": [15.0], "lat": 45.5, "lon": 9.0, "address": "Example town", "job_id": "job1",
            "job_code": "26042", "job_name": name, "client_name": "Example client", "reserved": False, "error": ""}


class ArchiveHost:
    def __init__(self, projects):
        self._index = projects

    def index_rows(self):
        return self._index


class MeridioPrivacyTest(unittest.TestCase):
    def test_cloud_tools_receive_only_aliases_and_no_reserved_project(self):
        public = row("Public shed", "public", "R01", "2026-10-01T10:00:00+00:00")
        public["error"] = "Could not read /jobs/Public shed_R01.meridiana"
        secret = row("Secret client", "secret", "R09", "2026-10-09T10:00:00+00:00")
        secret["path"] = "/private/Secret client_R09.meridiana"
        secret["reserved"] = True
        host = ArchiveHost([public, secret])
        state = tools.State(cloud=True)
        outcome = tools.run("search_projects", {"query": ""}, host, state)
        result = json.loads(outcome.content)
        self.assertEqual(len(result["projects"]), 1)
        item = result["projects"][0]
        self.assertEqual(item["id"], "pr1")
        for field in ("path", "title", "name", "client_name", "job_code", "job_name", "address", "reserved", "error"):
            self.assertNotIn(field, item)
        self.assertFalse(item["readable"])
        sent = outcome.content
        for secret_text in ("Public shed", "Secret client", "/jobs", "/private", "26042", "Example client"):
            self.assertNotIn(secret_text, sent)
        prepared = tools.run("prepare_open_project", {"project_id": "pr1"}, host, state)
        self.assertNotIn(public["path"], prepared.content)
        self.assertEqual(prepared.proposal.item["path"], public["path"])

    def test_archive_redaction_covers_names_paths_clients_and_short_names(self):
        project = capannone("Current project")
        public = row("Public shed", "public", "R01", "2026-10-01T10:00:00+00:00")
        secret = row("XY", "secret", "R09", "2026-10-09T10:00:00+00:00")
        secret["reserved"] = True
        redactor = privacy.Redactor.of(project).with_archive([public, secret])
        text = "Public shed, XY, Example client, 26042, /jobs/Public shed_R01.meridiana"
        redacted = redactor.redact(text)
        for secret_text in ("Public shed", "XY", "Example client", "26042", "/jobs"):
            self.assertNotIn(secret_text, redacted)

    def test_a_request_about_reserved_projects_forces_the_local_model(self):
        self.assertTrue(privacy.requires_local("Cerca anche nei progetti riservati"))
        self.assertTrue(privacy.requires_local("Show confidential projects"))
        self.assertFalse(privacy.requires_local("Cerca un capannone"))


if __name__ == "__main__":
    unittest.main()
