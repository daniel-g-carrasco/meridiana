import json
import unittest
from urllib.parse import parse_qs, urlparse

import _setup
from meridiana import config, feedback, tour
from meridiana.assistant import tools

setUpModule = _setup.keep_global_state


class FeedbackTests(unittest.TestCase):
    def test_draft_is_local_and_context_is_opt_in(self):
        draft = feedback.Draft("Wrong result", "Expected 10, saw 20", "1.2", "Windows", "3.12")
        body = draft.body()
        self.assertIn("Expected 10, saw 20", body)
        self.assertNotIn("project", body.lower())
        self.assertEqual(parse_qs(urlparse(draft.issue_url()).query)["body"], [body])
        self.assertEqual(urlparse(draft.issue_url()).hostname, "github.com")

    def test_selected_diagnostics_redact_paths_and_secrets(self):
        raw = 'File "C:\\Users\\Daniel\\client\\work.py", line 4\nAuthorization: Bearer secret-key\napi_key=secret'
        safe = feedback.redact_diagnostics(raw)
        self.assertNotIn("Daniel", safe)
        self.assertNotIn("secret", safe)
        self.assertIn("work.py", safe)

    def test_large_draft_is_not_silently_truncated(self):
        with self.assertRaises(ValueError):
            feedback.Draft("Test", "x" * 14000, "1", "Linux", "3").issue_url()


class TourTests(unittest.TestCase):
    def test_existing_configuration_migrates_without_enabling_updates(self):
        data = config.migrate({"version": 21, "check_updates": False, "theme": "dark"})
        self.assertEqual(data["version"], config.CONFIG_VERSION)        # every later migration runs too
        self.assertFalse(data["check_updates"])
        self.assertFalse(data["auto_install_updates"])
        self.assertEqual(data["tour_status"], "new")
        self.assertEqual(data["tour_step"], 0)
        self.assertEqual(data["theme"], "dark")

    def test_tour_covers_all_phases_and_has_stable_steps(self):
        steps = tour.steps()
        self.assertEqual(len({s.id for s in steps}), len(steps))
        self.assertTrue({"model", "plant", "production", "consumption", "economics", "report"}
                        <= {s.target[1] for s in steps if s.target[0] == "phase"})
        self.assertTrue(all(s.title and s.text for s in steps))

    def test_local_commands_are_explicit_not_incidental_words(self):
        self.assertEqual(tour.local_command("Avvia la visita guidata"), "tour")
        self.assertEqual(tour.local_command("Segnala un bug"), "bug")
        self.assertEqual(tour.local_command("Non avviare la visita guidata"), "")
        self.assertEqual(tour.local_command("La visita guidata mi è piaciuta"), "")

    def test_tools_only_prepare_report_or_start_navigation(self):
        class Host:
            def prepare_bug_report(self, summary, details):
                self.draft = (summary, details)
            def start_guided_tour(self):
                self.started = True
        host = Host()
        outcome = tools.run("prepare_bug_report", {"summary": "Unexpected", "details": "Observe this"}, host, tools.State())
        self.assertFalse(outcome.error)
        self.assertFalse(json.loads(outcome.content)["sent"])
        self.assertEqual(host.draft, ("Unexpected", "Observe this"))
        self.assertFalse(tools.run("start_guided_tour", {}, host, tools.State()).error)
        self.assertTrue(host.started)
