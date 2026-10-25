"""Preferences > Assistant, the local models of this PC (R105; ui/assistant_local.py): the survey on the pool (the
page opens at once), what runs and what is only installed, the models found with the recommended one and why,
«Use it» that fills the fields, «Test» that tries the connection, the guide with its commands when nothing is
there. The surveys are stand-ins and the servers fakes on 127.0.0.1: the PC's real ports are never knocked at.
PySide6 and a display (offscreen will do)."""

import time
import unittest

import _setup
from _fakes import FakeServer, nothing_local, tool_answer
from _setup import wait_until

from meridiana import config
from meridiana.assistant import local
from meridiana.assistant.local import Machine, Model, Runtime

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

DANIEL = Machine(31.6, 8.0, "NVIDIA RTX A2000 8GB Laptop GPU")


def with_ollama(extra=(), **_more):
    ollama = Runtime("ollama", "http://127.0.0.1:11434", running=True, installed=True, version="0.40.11", models=[
        Model("qwen3.5:4b", 3_300_000_000, tools=True), Model("qwen3.6:35b-a3b", 23_900_000_000, tools=True),
        Model("granite4.2:8b", 5_300_000_000, tools=False)])
    studio = Runtime("lmstudio", "http://127.0.0.1:1234/v1", installed=True, where="C:/x/lms.exe",
                     models=[Model("Qwen3.5-9B-Q4_K_M", 5_700_000_000)])
    return local.Survey([ollama, studio], DANIEL, local.choose([ollama], DANIEL))


class LocalModelsPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def page(self, survey, cfg=None):
        from meridiana.ui.preferences import MeridioPage
        page = MeridioPage(cfg or config.Config(), survey=survey)
        self.addCleanup(_setup.dispose, page)
        page.resize(640, 900)
        return page

    def shown(self, page) -> local.Survey:
        got = []
        page.locals.surveyed.connect(got.append)
        page.show()
        self.assertTrue(wait_until(self.app, lambda: got, 10))
        return got[0]

    def test_the_page_opens_at_once_and_the_survey_comes_after(self):
        def slow(extra=(), **_more):
            time.sleep(0.4)
            return with_ollama()
        page = self.page(slow)
        t = time.perf_counter()
        page.show()
        self.app.processEvents()
        self.assertLess(time.perf_counter() - t, 0.3)              # the dialog does not wait for the ports
        self.assertIn("Looking for the local models", page.locals.state.text())
        self.assertTrue(wait_until(self.app, lambda: page.locals.found is not None, 10))

    def test_what_runs_what_is_only_installed_and_the_recommended_model_with_its_reason(self):
        page = self.page(with_ollama)
        self.shown(page)
        lm = page.locals
        state = lm.state.text()
        from meridiana.ui.design import semibold                      # the bold is the semibold (R121)
        self.assertIn(semibold("<b>Ollama</b> 0.40.11 running at http://127.0.0.1:11434: 3 models"), state)
        self.assertIn(semibold("<b>LM Studio</b> is installed, not running, 1 model on the disk: start its server: lms "
                               "server start"), state)
        self.assertIn("This PC: 32 GB of RAM, NVIDIA RTX A2000 8GB Laptop GPU with 8 GB; about 32 GB for a model.",
                      lm.pc.text())
        self.assertEqual(lm.models.count(), 3)
        self.assertEqual(lm.models.currentText(), "qwen3.6:35b-a3b · Ollama · 23.9 GB · recommended")
        self.assertIn("tried with Meridio's tools", lm.why.text())
        self.assertTrue(lm.use.isEnabled())
        self.assertFalse(lm.guide.isVisible())
        lm.models.setCurrentIndex(2)                               # one that does not call tools: not to be used
        self.assertIn("does not call tools", lm.models.currentText())
        self.assertFalse(lm.use.isEnabled())

    def test_use_it_fills_the_server_the_model_and_its_kind_and_chooses_the_local_model(self):
        cfg = config.Config(assistant_provider="claude")
        page = self.page(with_ollama, cfg)
        self.shown(page)
        page.locals.use.click()
        self.assertEqual((page.url.text(), page.model.text(), page.api.currentData()),
                         ("http://127.0.0.1:11434", "qwen3.6:35b-a3b", "ollama"))
        self.assertTrue(page.local.isChecked())
        choice = page.choice()
        self.assertEqual((choice["assistant_provider"], choice["assistant_local_runtime"],
                          choice["assistant_local_model"]), ("local", "ollama", "qwen3.6:35b-a3b"))
        self.assertIn("OK keeps it", page.locals.test_state.text())

    def test_with_nothing_on_the_pc_the_guide_gives_the_steps_and_their_commands_to_copy(self):
        from PySide6.QtWidgets import QApplication, QLineEdit, QToolButton
        page = self.page(nothing_local)
        self.shown(page)
        lm = page.locals
        self.assertIn("No program of local models on this PC", lm.state.text())
        self.assertFalse(lm.models_row.isVisible())
        self.assertTrue(lm.guide.isVisible())
        commands = [f.text() for f in lm.guide.findChildren(QLineEdit)]
        self.assertIn("ollama pull qwen3.6:35b-a3b", commands)      # the model for 32 GB and a card of 8
        self.assertEqual(len(commands), 2)                         # Ollama itself, the model
        copy = [b for b in lm.guide.findChildren(QToolButton)]
        copy[-1].click()
        self.assertEqual(QApplication.clipboard().text(), "ollama pull qwen3.6:35b-a3b")
        texts = " ".join(w.text() for w in lm.guide.findChildren(type(lm.state)))
        self.assertIn("about 24 GB", texts)

    def test_with_ollama_but_no_model_the_guide_skips_the_installer(self):
        from PySide6.QtWidgets import QLineEdit

        def empty_ollama(extra=(), **_more):
            return local.Survey([Runtime("ollama", "http://127.0.0.1:11434", running=True, installed=True)], DANIEL)
        page = self.page(empty_ollama)
        self.shown(page)
        commands = [f.text() for f in page.locals.guide.findChildren(QLineEdit)]
        self.assertEqual(commands, ["ollama pull qwen3.6:35b-a3b"])

    def test_test_tries_the_fields_server_and_says_it_works(self):
        from meridiana.assistant import providers
        server = FakeServer([tool_answer([("ping", {})])])
        self.addCleanup(server.close)
        page = self.page(nothing_local)
        page.url.setText(server.url)
        page.model.setText("qwen3.6")
        page.api.setCurrentIndex(page.api.findData(""))
        provider = page.locals.provider()
        self.assertIsInstance(provider, providers.OpenAICompatible)
        self.assertEqual((provider.base_url, provider.model), (server.url, "qwen3.6"))
        results = []
        page.locals.tested.connect(results.append)
        page.locals.test.click()
        self.assertFalse(page.locals.test.isEnabled())
        self.assertIn("Trying qwen3.6", page.locals.test_state.text())
        self.assertTrue(wait_until(self.app, lambda: results, 10))
        self.assertTrue(results[0].tools)
        self.assertIn("It works: qwen3.6 answered in", page.locals.test_state.text())
        self.assertTrue(page.locals.test.isEnabled())
        page.api.setCurrentIndex(page.api.findData("ollama"))
        self.assertIsInstance(page.locals.provider(), providers.Ollama)


if __name__ == "__main__":
    unittest.main()
