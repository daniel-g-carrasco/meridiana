"""The local models made simple (R105): the runtimes found on this PC (fake servers on 127.0.0.1 answering as Ollama,
LM Studio, llama-server, Lemonade, Docker Model Runner, Jan and any OpenAI-compatible one do, from their docs of
25/10/2026), the programs and models on the disk (a temporary home), the PC's memory, the model chosen and why, the
steps when there is none, the test of the connection; and Ollama through its own API, with the context and the
reasoning set at each request. Nothing here knocks at the real ports of the PC or uses the network."""

import json
import socket
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import _setup  # noqa: F401
from _fakes import FakeRuntime, FakeServer, Host, ollama_answer, ollama_routes, text_answer, tool_answer
from _fixtures import capannone_rho

from meridiana.assistant import conversation, local, providers
from meridiana.assistant.local import Machine, Model, Runtime

DANIEL = Machine(31.6, 8.0, "NVIDIA RTX A2000 8GB Laptop GPU")     # the PC of 25/10/2026


def closed_port() -> int:
    """A port of 127.0.0.1 nobody listens on."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Identify(unittest.TestCase):
    def serve(self, routes, **more) -> FakeRuntime:
        server = FakeRuntime(routes, **more)
        self.addCleanup(server.close)
        return server

    def test_ollama_by_its_version_with_its_models_and_what_each_one_can_do(self):
        server = self.serve(ollama_routes())
        rt = local.identify(server.base, 11434)
        self.assertEqual((rt.kind, rt.name, rt.version, rt.url, rt.api), ("ollama", "Ollama", "0.40.11", server.base,
                                                                          "ollama"))
        self.assertEqual([m.name for m in rt.models], ["qwen3.6:35b-a3b"])     # the embedding model left out
        m = rt.models[0]
        self.assertEqual((m.tools, m.thinking, m.params), (True, (False, True), "35.0B"))
        self.assertAlmostEqual(m.gb, 23.9)

    def test_lm_studio_by_its_own_list_with_the_tool_flag_and_a_context_too_short_said(self):
        server = self.serve({"/api/v1/models": {"models": [
            {"type": "llm", "key": "qwen/qwen3.6-35b-a3b", "display_name": "Qwen3.6 35B A3B",
             "size_bytes": 22_100_000_000,
             "params_string": "35B", "capabilities": {"vision": True, "trained_for_tool_use": True},
             "loaded_instances": [{"id": "qwen/qwen3.6-35b-a3b", "config": {"context_length": 4096}}]},
            {"type": "embedding", "key": "text-embedding-nomic-embed-text-v1.5"}]},
            "/v1/models": {"data": [{"id": "qwen/qwen3.6-35b-a3b"}]}})
        rt = local.identify(server.base, 1234)
        self.assertEqual((rt.kind, rt.url), ("lmstudio", server.base + "/v1"))
        self.assertEqual([(m.name, m.tools, m.context, m.loaded) for m in rt.models],
                         [("qwen/qwen3.6-35b-a3b", True, 4096, True)])
        self.assertIn("--context-length 16384", rt.note)

    def test_an_older_lm_studio_by_its_v0_list(self):
        server = self.serve({"/api/v0/models": {"data": [{"id": "qwen3.5-9b", "type": "llm", "state": "loaded",
                                                           "loaded_context_length": 16384},
                                                          {"id": "nomic", "type": "embeddings"}]},
                             "/v1/models": {"data": [{"id": "qwen3.5-9b"}]}})
        rt = local.identify(server.base, 1234)
        self.assertEqual((rt.kind, [m.name for m in rt.models]), ("lmstudio", ["qwen3.5-9b"]))

    def test_llama_server_by_its_props_with_the_template_s_tools_and_its_context(self):
        server = self.serve({"/props": {"build_info": "b11869-abc", "model_path": "/m/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf",
                                        "default_generation_settings": {"n_ctx": 16384},
                                        "chat_template_caps": {"supports_tools": True}},
                             "/v1/models": {"object": "list", "data": [
                                 {"id": "Qwen3.6-35B-A3B-UD-IQ4_XS.gguf", "owned_by": "llamacpp",
                                  "meta": {"size": 17_730_000_000, "n_params": 34_660_000_000}}]}})
        rt = local.identify(server.base, 9931)
        self.assertEqual((rt.kind, rt.url, rt.note), ("llamacpp", server.base + "/v1", ""))
        m = rt.models[0]
        self.assertEqual((m.name, m.tools, m.context, m.params), ("Qwen3.6-35B-A3B-UD-IQ4_XS.gguf", True, 16384,
                                                                  "34.7B"))
        self.assertEqual(local.match(m.name).key, "qwen3.6-35b")

    def test_llama_server_with_a_small_context_says_how_to_start_it(self):
        server = self.serve({"/props": {"build_info": "b1", "default_generation_settings": {"n_ctx": 4096}},
                             "/v1/models": {"data": [{"id": "model.gguf"}]}})
        self.assertIn("-c 16384", local.identify(server.base, 8080).note)

    def test_lemonade_and_docker_model_runner_by_what_only_they_have(self):
        lemonade = self.serve({"/api/v1/models": {"data": [
            {"id": "Qwen3.5-9B-GGUF", "labels": ["tool-calling", "reasoning"], "downloaded": True},
            {"id": "nomic-embed-text-v2", "labels": ["embeddings"], "downloaded": True},
            {"id": "Gemma-4-26B", "labels": ["tool-calling"], "downloaded": False}]},
            "/api/version": {"version": "0.0.0"}})                  # it also answers Ollama's API
        rt = local.identify(lemonade.base, 13305)
        self.assertEqual((rt.kind, rt.url, [(m.name, m.tools) for m in rt.models]),
                         ("lemonade", lemonade.base + "/api/v1", [("Qwen3.5-9B-GGUF", True)]))
        docker = self.serve({"/engines/v1/models": {"object": "list", "data": [{"id": "ai/qwen3.5:9B-Q4_K_M"}]},
                             "/api/tags": {"models": []}})
        rt = local.identify(docker.base, 12434)
        self.assertEqual((rt.kind, rt.url, rt.models[0].name), ("docker", docker.base + "/engines/v1",
                                                               "ai/qwen3.5:9B-Q4_K_M"))

    def test_jan_and_any_other_openai_compatible_server_by_the_list_of_models(self):
        server = self.serve({"/v1/models": {"object": "list", "data": [{"id": "Qwen3.5-9B-Q4_K_M"},
                                                                        {"id": "text-embedding-3"}]}})
        jan = local.identify(server.base, 1337)
        self.assertEqual((jan.kind, jan.name, jan.url), ("jan", "Jan", server.base + "/v1"))
        self.assertEqual([m.name for m in jan.models], ["Qwen3.5-9B-Q4_K_M"])
        self.assertEqual(local.identify(server.base, 45678).kind, "openai")

    def test_a_server_that_wants_a_key_is_found_but_never_chosen(self):
        server = self.serve({"/v1/models": 401})
        rt = local.identify(server.base, 1337)
        self.assertTrue(rt.locked and rt.running)
        self.assertIn("API key", rt.note)
        rt.models = [Model("qwen3.6:35b-a3b", tools=True)]
        self.assertIsNone(local.choose([rt], DANIEL))

    def test_what_is_no_model_server_is_not_one(self):
        server = self.serve({"/": {"hello": "world"}})
        self.assertIsNone(local.identify(server.base, 8000))

    def test_the_ports_are_tried_together_and_a_closed_one_does_not_make_it_wait(self):
        server = self.serve(ollama_routes())
        closed = [closed_port() for _ in range(4)]
        t = time.perf_counter()
        self.assertEqual(local.open_ports([*closed, server.port]), [server.port])
        self.assertLess(time.perf_counter() - t, 1.5)            # 0,3 s each, all at once
        found = local.running([closed[0], server.port])
        self.assertEqual([rt.kind for rt in found], ["ollama"])


class OnTheDisk(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.env = {"LOCALAPPDATA": str(self.home / "AppData" / "Local"),
                    "APPDATA": str(self.home / "AppData" / "Roaming")}

    def write(self, path: Path, data=b"") -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())
        return path

    def test_nothing_on_the_disk_is_nothing(self):
        self.assertEqual(local.installed(self.env, self.home, lambda _n: None, "win32"), [])

    def test_ollama_s_program_and_its_models_from_the_manifests(self):
        self.write(self.home / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe")
        lib = self.home / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library"
        self.write(lib / "qwen3.6" / "35b-a3b",
                   json.dumps({"layers": [{"size": 23_000_000_000}, {"size": 900_000_000}]}))
        self.write(lib / "gemma4" / "26b-a4b-it-qat", json.dumps({"layers": [{"size": 16_000_000_000}]}))
        self.write(self.home / ".ollama" / "models" / "manifests" / "hf.co" / "unsloth" / "Qwen3.5-9B-GGUF" / "Q4_K_M",
                   "{}")
        found = local.installed(self.env, self.home, lambda _n: None, "win32")
        self.assertEqual([rt.kind for rt in found], ["ollama"])
        rt = found[0]
        self.assertTrue(rt.installed and not rt.running)
        self.assertEqual(sorted(m.name for m in rt.models), ["gemma4:26b-a4b-it-qat", "qwen3.6:35b-a3b",
                                                             "unsloth/Qwen3.5-9B-GGUF:Q4_K_M"])
        self.assertAlmostEqual(next(m for m in rt.models if m.name.startswith("qwen3.6")).gb, 23.9)
        self.assertIn("ollama serve", rt.start())

    def test_lm_studio_llama_cpp_and_jan_with_their_files(self):
        self.write(self.home / ".lmstudio" / "bin" / "lms.exe")
        models = self.home / ".lmstudio" / "models" / "lmstudio-community" / "Qwen3.5-9B-GGUF"
        self.write(models / "Qwen3.5-9B-Q4_K_M.gguf", b"x" * 10)
        self.write(models / "mmproj-Qwen3.5-9B-F16.gguf", b"x")
        hub = self.home / ".cache" / "huggingface" / "hub" / "models--unsloth--Qwen3.6-35B-A3B-GGUF" / "snapshots" / "a"
        self.write(hub / "Qwen3.6-35B-A3B-UD-IQ4_XS.gguf", b"x" * 20)
        self.write(self.home / "AppData" / "Roaming" / "Jan" / "data" / "llamacpp" / "models" / "unsloth" /
                   "Qwen3.5-9B-GGUF" / "model.yml", "name: x")
        server = str(self.home / "bin" / "llama-server.exe")
        found = {rt.kind: rt for rt in local.installed(self.env, self.home,
                                                       lambda n: server if n.startswith("llama-server") else None,
                                                       "win32")}
        self.assertEqual(set(found), {"lmstudio", "llamacpp", "jan"})
        self.assertEqual([(m.name, m.size) for m in found["lmstudio"].models], [("Qwen3.5-9B-Q4_K_M", 10)])
        self.assertEqual([m.name for m in found["llamacpp"].models], ["Qwen3.6-35B-A3B-UD-IQ4_XS"])
        self.assertEqual(found["llamacpp"].where, server)
        self.assertEqual([m.name for m in found["jan"].models], ["unsloth/Qwen3.5-9B-GGUF"])
        self.assertIn("lms server start", found["lmstudio"].start())
        self.assertIn("Local API Server", found["jan"].start())


class Choice(unittest.TestCase):
    def test_the_memory_for_a_model_the_card_s_and_the_ram_less_what_the_pc_keeps(self):
        self.assertAlmostEqual(DANIEL.budget_gb, 8 + 31.6 * 0.75, places=3)
        self.assertAlmostEqual(Machine(16.0).budget_gb, 10.0)
        self.assertAlmostEqual(Machine(8.0).budget_gb, 2.0)
        self.assertAlmostEqual(Machine(32.0, unified=True).budget_gb, 22.4)
        self.assertAlmostEqual(local.need_gb(24.0), 27.4)

    def test_the_machine_is_read_from_the_system_and_the_nvidia_card(self):
        class Done:
            stdout = "NVIDIA RTX A2000 8GB Laptop GPU, 8192\n"
        pc = local.machine(run=lambda *a, **k: Done())
        self.assertGreater(pc.ram_gb, 1)                       # this PC's own RAM
        if pc.vram_gb:                                          # nvidia-smi is on this PC's PATH
            self.assertEqual((pc.gpu, pc.vram_gb), ("NVIDIA RTX A2000 8GB Laptop GPU", 8.0))

    def test_the_best_with_tools_that_fits_is_chosen_and_said_why(self):
        ollama = Runtime("ollama", "http://127.0.0.1:11434", running=True, models=[
            Model("qwen3.5:4b", 3_300_000_000, tools=True), Model("qwen3.6:35b-a3b", 23_900_000_000, tools=True),
            Model("gemma4:26b-a4b-it-qat", 16_000_000_000, tools=True), Model("granite4.2:8b", 5_300_000_000,
                                                                               tools=False)])
        choice = local.choose([ollama], DANIEL)
        self.assertEqual((choice.model.name, choice.fits, choice.candidate.key), ("qwen3.6:35b-a3b", True,
                                                                                   "qwen3.6-35b"))
        reason = choice.reason(DANIEL)
        self.assertIn("qwen3.6:35b-a3b on Ollama: tried with Meridio's tools", reason)
        self.assertIn("It takes about 27 GB; this PC has about 32 for a model.", reason)
        small = local.choose([ollama], Machine(16.0))           # 10 GB for a model: only the 4B fits
        self.assertEqual((small.model.name, small.fits), ("qwen3.5:4b", True))

    def test_a_model_that_does_not_call_tools_is_never_the_choice_and_an_unknown_one_with_tools_may_be(self):
        rt = Runtime("openai", "http://127.0.0.1:8000/v1", running=True, models=[Model("granite4.2:8b", tools=False)])
        self.assertIsNone(local.choose([rt], DANIEL))
        rt.models.append(Model("my-own-model", tools=True))
        self.assertEqual(local.choose([rt], DANIEL).model.name, "my-own-model")
        self.assertIsNone(local.choose([Runtime("ollama", running=False, models=[Model("qwen3.6:35b-a3b")])], DANIEL))

    def test_the_names_of_the_runtimes_are_recognised_as_the_candidates(self):
        for name, key in (("qwen3.6:35b-a3b", "qwen3.6-35b"), ("Qwen3.6-35B-A3B-UD-IQ4_XS.gguf", "qwen3.6-35b"),
                          ("unsloth/gemma-4-26B-A4B-it-GGUF:UD-IQ4_XS", "gemma4-26b"), ("gpt-oss:20b", "gpt-oss-20b"),
                          ("lmstudio-community/Qwen3.5-9B-GGUF", "qwen3.5-9b"), ("qwen3:8b", "qwen3"),
                          ("ai/qwen3.5:9B-Q4_K_M", "qwen3.5-9b"), ("llama3.1:8b", "llama3")):
            with self.subTest(name):
                self.assertEqual(local.match(name).key, key)
        self.assertIsNone(local.match("my-own-model"))

    def test_on_a_pc_without_models_the_model_to_download_is_the_best_that_fits(self):
        self.assertEqual(local.suggested(DANIEL).ollama, "qwen3.6:35b-a3b")    # 27 GB of 32
        self.assertEqual(local.suggested(Machine(32.0)).ollama, "gemma4:26b-a4b-it-qat")
        self.assertEqual(local.suggested(Machine(16.0)).ollama, "qwen3.5:9b")
        self.assertEqual(local.suggested(Machine(8.0)).ollama, "qwen3.5:4b")

    def test_the_steps_with_their_commands_for_windows_linux_and_with_ollama_already_there(self):
        c, steps = local.guide(DANIEL, "win32")
        self.assertEqual(c.key, "qwen3.6-35b")
        self.assertEqual([s.command for s in steps],
                         ["winget install Ollama.Ollama", "ollama pull qwen3.6:35b-a3b", ""])
        self.assertIn("ollama.com/download", steps[0].text)
        self.assertIn("about 24 GB", steps[1].text)
        _c, steps = local.guide(DANIEL, "linux")
        self.assertEqual(steps[0].command, "curl -fsSL https://ollama.com/install.sh | sh")
        _c, steps = local.guide(DANIEL, "win32", have_ollama=True)
        self.assertEqual(steps[0].command, "ollama pull qwen3.6:35b-a3b")

    def test_the_survey_finds_the_running_one_and_chooses(self):
        server = FakeRuntime(ollama_routes())
        self.addCleanup(server.close)
        found = local.survey(ports=[server.port, closed_port()], disk=False, pc=DANIEL)
        self.assertEqual([rt.kind for rt in found.running], ["ollama"])
        self.assertTrue(found.running[0].installed)
        self.assertEqual(found.choice.model.name, "qwen3.6:35b-a3b")
        self.assertLess(found.seconds, 3)


class Test(unittest.TestCase):
    """«Test»: a short question that must come back as a call of the tool ping."""

    def test_a_model_that_calls_the_tool_passes(self):
        server = FakeServer([tool_answer([("ping", {})])])
        self.addCleanup(server.close)
        result = local.check(providers.OpenAICompatible(base_url=server.url, model="qwen"))
        self.assertTrue(result.ok and result.tools)
        self.assertIn("It works: qwen answered in", local.said(result, "qwen"))
        sent = server.requests[0]
        self.assertEqual([t["function"]["name"] for t in sent["tools"]], ["ping"])

    def test_a_model_that_writes_instead_is_said_and_nothing_answering_is_offline(self):
        server = FakeServer([text_answer("Pong!")])
        self.addCleanup(server.close)
        result = local.check(providers.OpenAICompatible(base_url=server.url, model="small"))
        self.assertTrue(result.ok)
        self.assertFalse(result.tools)
        self.assertIn("did not call the tool", local.said(result, "small"))
        port = closed_port()
        with mock.patch.object(providers, "LOCAL_CONNECT_S", 0.2):     # Windows takes 2 s to refuse a closed port
            offline = local.check(providers.OpenAICompatible(base_url=f"http://127.0.0.1:{port}/v1"))
        self.assertEqual((offline.ok, offline.error), (False, "offline"))
        self.assertIn("Nothing answers", local.said(offline, "x"))

    def test_ollama_answers_the_test_through_its_own_api(self):
        server = FakeRuntime({"_shows": {"qwen3.6:35b-a3b": {"capabilities": ["completion", "tools"]}}},
                             chat=[ollama_answer(calls=[("ping", {})])])
        self.addCleanup(server.close)
        result = local.check(providers.Ollama(model="qwen3.6:35b-a3b", base_url=server.base))
        self.assertTrue(result.ok and result.tools)


class OllamaOwnApi(unittest.TestCase):
    """Ollama through /api/chat: the context asked at each request (on /v1 it stays at 4.096 tokens and cuts the
    instructions), the reasoning off, the calls whole with their arguments as objects."""

    def serve(self, shows=None, chat=()):
        server = FakeRuntime({"_shows": shows or {"qwen3.6:35b-a3b": {
            "capabilities": ["completion", "tools", "thinking"], "thinking": {"values": [False, True]}}}},
            chat=list(chat))
        self.addCleanup(server.close)
        return server

    def chats(self, server) -> list[dict]:
        return [body for path, body in server.requests if path == "/api/chat"]

    def test_the_context_the_reasoning_off_and_the_tools_go_with_the_question(self):
        server = self.serve(chat=[ollama_answer(calls=[("read_checks", {"min_level": "warn"})]),
                                  ollama_answer("Due problemi: la tensione e l'ombra.")])
        p = capannone_rho()
        host = Host(p, lay=False)
        conv = conversation.Conversation()
        last = conversation.answer(conv, providers.Ollama(model="qwen3.6:35b-a3b", base_url=server.base),
                                   "SYSTEM", "Problemi?", host)
        self.assertEqual(last.text, "Due problemi: la tensione e l'ombra.")
        first, second = self.chats(server)
        self.assertEqual(first["options"], {"num_ctx": 16384, "num_predict": providers.MAX_TOKENS})
        self.assertIs(first["think"], False)
        self.assertEqual((first["stream"], first["keep_alive"]), (True, "30m"))
        self.assertEqual(first["tools"][0]["type"], "function")
        self.assertEqual(second["messages"][2]["tool_calls"],
                         [{"type": "function",
                           "function": {"name": "read_checks", "arguments": {"min_level": "warn"}}}])
        self.assertEqual((second["messages"][3]["role"], second["messages"][3]["tool_name"]), ("tool", "read_checks"))
        self.assertIn("checks", json.loads(second["messages"][3]["content"]))
        self.assertEqual(conv.bill.usage.input, 6200)            # prompt_eval_count of the two rounds

    def test_gpt_oss_reasons_at_its_lowest_and_a_model_that_does_not_reason_gets_no_think(self):
        server = self.serve({"gpt-oss:20b": {"capabilities": ["completion", "tools", "thinking"],
                                             "thinking": {"values": ["low", "medium", "high"]}},
                             "qwen3.5:9b": {"capabilities": ["completion", "tools"]}})
        for model in ("gpt-oss:20b", "qwen3.5:9b"):
            list(providers.Ollama(model=model, base_url=server.base).stream("S", [{"role": "user", "content": "x"}],
                                                                             []))
        gpt, qwen = self.chats(server)
        self.assertEqual(gpt["think"], "low")
        self.assertNotIn("think", qwen)
        self.assertEqual(providers.ollama_think({"capabilities": ["thinking"]}, "gpt-oss:120b"), "low")
        self.assertIsNone(providers.ollama_think({}, "x"))

    def test_a_failure_of_500_before_a_word_is_asked_once_more(self):
        server = self.serve(chat=[500, ollama_answer("Eccomi.")])
        events = list(providers.Ollama(model="qwen3.6:35b-a3b", base_url=server.base).stream(
            "S", [{"role": "user", "content": "x"}], []))
        self.assertEqual("".join(e.text for e in events if isinstance(e, providers.Text)), "Eccomi.")
        self.assertEqual(len(self.chats(server)), 2)

    def test_a_model_without_tools_no_model_chosen_and_nothing_answering_are_said(self):
        server = self.serve(chat=[(400, "registry.ollama.ai/library/granite4.2:8b does not support tools")])
        with self.assertRaises(providers.ProviderError) as said:
            list(providers.Ollama(model="", base_url=server.base).stream("S", [], []))
        self.assertEqual(said.exception.kind, "model")
        with self.assertRaises(providers.ProviderError) as said:
            list(providers.Ollama(model="granite4.2:8b", base_url=server.base, think=None).stream(
                "S", [{"role": "user", "content": "x"}], [{"name": "a", "description": "b", "parameters": {}}]))
        self.assertEqual(said.exception.kind, "tools")
        port = closed_port()
        with self.assertRaises(providers.ProviderError) as said, mock.patch.object(providers, "LOCAL_CONNECT_S", 0.2):
            list(providers.Ollama(model="m", base_url=f"http://127.0.0.1:{port}", think=None).stream("S", [], []))
        self.assertEqual(said.exception.kind, "offline")


if __name__ == "__main__":
    unittest.main()
