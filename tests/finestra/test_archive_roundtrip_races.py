"""Archive searches restore local aliases and never reuse obsolete privacy metadata."""

import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import _setup
from _fakes import FakeAnthropic
from _fixtures import capannone

from meridiana import config, project_index
from meridiana.assistant import privacy, providers, tools
from meridiana.ui.assistant_chat import WindowHost

setUpModule = _setup.keep_global_state


class ArchiveRoundtripRaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.win = _setup.window(self, capannone("Current project"),
                                 cfg=config.Config(background="none", assistant_provider="claude"))
        self.assertTrue(_setup.wait_until(self.app, lambda: self.win.pool.activeThreadCount() == 0))

    def test_cloud_search_restores_the_alias_to_the_local_job_code(self):
        row = {"path": "/jobs/example.meridiana", "title": "Example shed", "job_code": "26042",
               "reserved": False, "power_kwp": 100.0, "kind": "roof", "revision": "R01"}
        redactor = privacy.Redactor.of(self.win.project, self.win.path).with_archive([row])
        alias = redactor.redact("26042")
        client = FakeAnthropic([[('tool', 'search_projects', {'query': alias})], [('text', 'Fine.')]])
        chat = self.win.assistant_chat
        chat.keys = SimpleNamespace(get=lambda family: "sk-ant-api-test-0123456789")
        chat.make_cloud = lambda key: providers.Anthropic(model=self.win.cfg.assistant_cloud_model,
                                                         key=key, client=client)
        self.win.cfg.assistant_consent = {"anthropic": ["2026-10-24"]}
        with mock.patch.object(self.win.registry, "list_index", return_value=[row]):
            self.win.assistant.ask("Apri la commessa 26042")
            self.assertTrue(_setup.wait_until(self.app, lambda: len(client.calls) == 2 and chat.job is None))
        results = [m for m in chat.conversation.messages if m["role"] == "tool"]
        self.assertEqual(len(json.loads(results[-1]["content"])["projects"]), 1)
        self.assertNotIn("26042", json.dumps(client.calls, default=str))

    def test_reserving_a_job_filters_the_old_index_before_a_scan_finishes(self):
        reg = self.win.registry
        job = reg.create_job("26042", "Example job", reg.create_client("Example client")["id"])
        row = {"path": "/jobs/example.meridiana", "job_id": job["id"], "reserved": False,
               "power_kwp": 100.0, "kind": "roof", "revision": "R01"}
        reg.replace_index([row])
        reg.update_job(job["id"], reserved=True)
        result = tools.search_projects(WindowHost(self.win), tools.State(cloud=True))
        self.assertEqual(json.loads(result.content)["projects"], [])

    def test_a_slow_old_scan_cannot_overwrite_the_new_reserved_snapshot(self):
        reg = self.win.registry
        job = reg.create_job("26042", "Example job", reg.create_client("Example client")["id"])
        folder = Path(tempfile.mkdtemp())
        reg.link_folder(job["id"], folder)
        started, newer_written = threading.Event(), threading.Event()
        persist = project_index.persist

        def scan(folders, known):
            reserved = folders[0][1]["reserved"]
            if not reserved:
                started.set()
                newer_written.wait(0.3)
            return [{"path": str(folder / "example.meridiana"), "reserved": reserved}]

        def write(database, rows):
            persist(database, rows)
            if rows[0]["reserved"]:
                newer_written.set()

        with mock.patch.object(project_index, "scan", side_effect=scan), \
                mock.patch.object(project_index, "persist", side_effect=write):
            self.win._refresh_index()
            self.assertTrue(started.wait(5))
            reg.update_job(job["id"], reserved=True)
            self.win._refresh_index()
            self.assertTrue(_setup.wait_until(self.app, lambda: newer_written.is_set()
                                              and self.win.pool.activeThreadCount() == 0))
            self.app.processEvents()
        self.assertTrue(reg.list_index()[0]["reserved"])
