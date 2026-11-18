"""Stand-ins for the models Meridio talks to (task 14): a server that answers as llama-server does, in server-sent
events, from answers written beforehand or recorded from the real one (tests/data/assistant/*.sse); a client that
stands in for the Anthropic SDK and notes everything it is given; a host that answers the tools from a project
without a window. Nothing here uses the network: the server listens on 127.0.0.1 on a port of its own."""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

RECORDED = Path(__file__).resolve().parent / "data" / "assistant"


def chunk(delta: dict | None = None, finish: str | None = None, usage: dict | None = None, model: str = "qwen") -> str:
    body = {"id": "chatcmpl-1", "object": "chat.completion.chunk", "model": model,
            "choices": [] if delta is None and finish is None else
            [{"index": 0, "delta": delta or {}, "finish_reason": finish}]}
    if usage is not None:
        body["usage"] = usage
    return "data: " + json.dumps(body, ensure_ascii=False) + "\n\n"


def text_answer(text: str, pieces: int = 6, usage=(900, 120)) -> list[str]:
    """An answer in words, cut in `pieces` as a server sends it."""
    step = max(1, len(text) // pieces)
    out = [chunk({"role": "assistant", "content": ""})]
    out += [chunk({"content": text[i:i + step]}) for i in range(0, len(text), step)]
    out += [chunk(finish="stop"), chunk(usage={"prompt_tokens": usage[0], "completion_tokens": usage[1]}),
            "data: [DONE]\n\n"]
    return out


def tool_answer(calls: list[tuple[str, dict]], text: str = "", usage=(1035, 40)) -> list[str]:
    """An answer that asks for tools, the arguments of each sent in two pieces as llama-server does."""
    out = [chunk({"role": "assistant", "content": None})]
    if text:
        out.append(chunk({"content": text}))
    for n, (name, args) in enumerate(calls):
        arguments = json.dumps(args)
        half = len(arguments) // 2
        out.append(chunk({"tool_calls": [{"index": n, "id": f"call_{n}{name[:4]}", "type": "function",
                                          "function": {"name": name, "arguments": arguments[:half]}}]}))
        out.append(chunk({"tool_calls": [{"index": n, "function": {"arguments": arguments[half:]}}]}))
    out += [chunk(finish="tool_calls"), chunk(usage={"prompt_tokens": usage[0], "completion_tokens": usage[1]}),
            "data: [DONE]\n\n"]
    return out


def recorded(name: str) -> list[str]:
    """A stream recorded from llama-server: the events of the file, as they came."""
    text = (RECORDED / name).read_text(encoding="utf-8")
    return [part + "\n\n" for part in text.split("\n\n") if part.strip()]


class FakeServer:
    """llama-server's /v1/chat/completions on 127.0.0.1: each request gets the next answer of `answers` (a list of
    events, or an int for an HTTP error), sent `pause` seconds apart; `requests` keeps the bodies received. `hold`
    keeps the stream open after its first event until `release` (for Stop)."""

    def __init__(self, answers: list, pause: float = 0.0):
        self.answers = list(answers)
        self.pause = pause
        self.requests: list[dict] = []
        self.hold = threading.Event()
        self.held = threading.Event()
        self.closed_by_client = threading.Event()
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                server.requests.append(json.loads(self.rfile.read(length) or b"{}"))
                answer = server.answers.pop(0) if server.answers else text_answer("Fine.")
                if isinstance(answer, int):
                    self.send_response(answer)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": {"message": "refused"}}).encode())
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                try:
                    for n, event in enumerate(answer):
                        self.wfile.write(event.encode("utf-8"))
                        self.wfile.flush()
                        if n == 0 and server.hold.is_set():
                            server.held.set()
                            for _i in range(200):          # at most 10 s, then on
                                if not server.hold.is_set():
                                    break
                                time.sleep(0.05)
                        if server.pause:
                            time.sleep(server.pause)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    server.closed_by_client.set()

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.httpd.server_address[1]}/v1"

    def release(self) -> None:
        self.hold.clear()

    def close(self) -> None:
        self.hold.clear()
        self.httpd.shutdown()
        self.httpd.server_close()


class Offline:
    """The local model's server not running: the provider says so at once."""
    model, family, cloud = "", "openai", False

    def stream(self, system, messages, tools):
        from meridiana.assistant.providers import ProviderError
        raise ProviderError("offline", "connection refused")
        yield                                           # a generator, as the providers are

    def cancel(self):
        pass


def offline() -> Offline:
    return Offline()


class FakeAnthropic:
    """anthropic.Anthropic as Meridio uses it: `messages.stream(**args)` (and `beta.messages.stream`) as a context
    manager whose events are the text pieces and whose final message has the content blocks, the usage, the stop
    reason. `calls` keeps every argument it was given: what would have left the PC. `answers` are lists of blocks:
    ("text", "...") or ("tool", name, input)."""

    def __init__(self, answers: list, raise_error=None):
        self.answers = list(answers)
        self.calls: list[dict] = []
        self.raise_error = raise_error
        self.messages = SimpleNamespace(stream=self._stream)
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **args):
        self.calls.append(args)
        if self.raise_error is not None:
            raise self.raise_error
        blocks = self.answers.pop(0) if self.answers else [("text", "Fine.")]
        return _FakeStream(blocks, args.get("model", ""))


class _FakeStream:
    def __init__(self, blocks, model):
        self.blocks = blocks
        self.model = model

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def close(self):
        pass

    def __iter__(self):
        for b in self.blocks:
            if b[0] == "text":
                for i in range(0, len(b[1]), 12):
                    yield SimpleNamespace(type="text", text=b[1][i:i + 12])

    def get_final_message(self):
        content = []
        for n, b in enumerate(self.blocks):
            if b[0] == "text":
                content.append(SimpleNamespace(type="text", text=b[1]))
            else:
                content.append(SimpleNamespace(type="tool_use", id=f"toolu_{n}", name=b[1], input=b[2]))
        tools = any(b[0] == "tool" for b in self.blocks)
        usage = SimpleNamespace(input_tokens=3000, output_tokens=200, cache_read_input_tokens=1000,
                                cache_creation_input_tokens=0)
        return SimpleNamespace(content=content, usage=usage, stop_reason="tool_use" if tools else "end_turn",
                               model=self.model)


class Host:
    """The tools' host without a window: a project with its layouts laid here, the checks gathered as the window
    gathers them, what was asked of the window noted in `went`."""

    def __init__(self, project, energy=None, selection=("site", ""), phase="model", lay=True):
        from meridiana import checks
        self.project = project
        self._energy = energy or {}
        self._selection = selection
        self._phase = phase
        self.went: list[tuple] = []
        self._layouts = {sf.id: project.fill(sf) for sf in project.subfields if sf.filled} if lay else {}
        self._checks = checks.gather(project, self._layouts, self._energy, None, False)
        self._checks.sort(key=lambda i: checks.LEVELS.index(i.level))

    def checks(self):
        return self._checks

    def layouts(self):
        return self._layouts

    def energy(self):
        return self._energy

    def plant(self):
        return self._energy.get("plant")

    def selection(self):
        return self._selection

    def phase(self):
        return self._phase

    def rules_facts(self):
        from meridiana import rules
        return rules.facts(self.project, self._layouts, self._energy, None)

    def go_to(self, target):
        self.went.append(tuple(target))

    def bindings(self):
        return None


def with_problems(host: Host) -> Host:
    """The checks of the trial of study 14, 4.4, before the real ones: the open-circuit voltage of a string above
    the inverter's at -10 °C (fail, its fix the strings made again), the shade of the obstacles on the sub-field
    «Sud» (warn, its fix the layout out of the shadows). Written as the program writes them in Italian."""
    from meridiana import checks
    uoc = checks.Item("fail", "strings", "Inverter tetto, ingresso 2, 18 in serie: Uoc max 1043 V oltre i 1000 V "
                      "dell'inverter", "CEI 64-8/7:2024, 712.512.1.1", ("phase", "plant"),
                      ("energy", "strings.auto", True), "Rifai le stringhe in automatico",
                      checks.string_detail("uoc"))
    shade = checks.Item("warn", "shade", "Sud: il 4,2 % dell'irraggiamento è perso per le ombre degli ostacoli",
                        "Meridiana", ("subfield", "s1"), ("edit", "subfield", "s1", {"params.shade_free": True}),
                        "Posa fuori dalle ombre")
    host._checks = [uoc, shade, *host._checks]
    return host


def nothing_local(extra=(), **_more):
    """The search for local models (assistant/local.survey) on a PC without any: nothing running, nothing on the
    disk, a PC of 32 GB with a card of 8 (Daniel's, 25/10/2026)."""
    from meridiana.assistant import local
    return local.Survey([], local.Machine(31.6, 8.0, "NVIDIA RTX A2000 8GB Laptop GPU"))


class FakeRuntime:
    """A local runtime's server on 127.0.0.1 (R105): `routes` maps a path to the JSON its GET or POST answers (an
    int for an HTTP status); POST /api/chat answers `chat`, lines of Ollama's stream (a list each, an int for an
    error, or (status, its message)), in turn; POST /v1/chat/completions the events of `events` (as FakeServer).
    `requests` keeps (path, body) of every POST."""

    def __init__(self, routes: dict, chat: list | None = None, events: list | None = None):
        self.routes = dict(routes)
        self.chat = list(chat or [])
        self.events = list(events or [])
        self.requests: list[tuple[str, dict]] = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            # the headers and the body leave at once: with Nagle's algorithm Windows holds the body for the ACK of the
            # headers, 200 ms delayed, at every request
            disable_nagle_algorithm = True

            def log_message(self, *_args):
                pass

            def _json(self, status: int, body) -> None:
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _route(self):
                answer = server.routes.get(self.path.split("?")[0])
                if answer is None:
                    self._json(404, {"error": "not found"})
                elif isinstance(answer, int):
                    self._json(answer, {"error": {"message": "refused"}})
                else:
                    self._json(200, answer(self) if callable(answer) else answer)

            def do_GET(self):
                self._route()

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                path = self.path.split("?")[0]
                server.requests.append((path, body))
                if path == "/api/show" and "_shows" in server.routes:
                    shows = server.routes["_shows"]
                    if body.get("model") in shows:
                        self._json(200, shows[body["model"]])
                    else:
                        self._json(404, {"error": f"model '{body.get('model')}' not found"})
                    return
                if path == "/api/chat":
                    answer = server.chat.pop(0) if server.chat else ollama_answer("Fine.")
                    if isinstance(answer, (int, tuple)):          # a status, or (status, what Ollama says)
                        status, said = answer if isinstance(answer, tuple) else (answer, "failed")
                        self._json(status, {"error": said})
                        return
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-ndjson")
                    self.end_headers()
                    for line in answer:
                        self.wfile.write((json.dumps(line) + "\n").encode())
                        self.wfile.flush()
                    return
                if path.endswith("/chat/completions"):
                    answer = server.events.pop(0) if server.events else text_answer("Fine.")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.end_headers()
                    for event in answer:
                        self.wfile.write(event.encode("utf-8"))
                        self.wfile.flush()
                    return
                self._route()

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        # a short poll: shutdown() waits for it, half a second by default at every test
        self.thread = threading.Thread(target=self.httpd.serve_forever, args=(0.02,), daemon=True)
        self.thread.start()

    @property
    def port(self) -> int:
        return self.httpd.server_address[1]

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


def ollama_answer(text: str = "", calls: list | None = None, done_reason: str = "stop") -> list[dict]:
    """Ollama's /api/chat stream: the words in pieces, the calls whole in one line, the last line with the counts."""
    lines = [{"model": "qwen3.6:35b-a3b", "message": {"role": "assistant", "content": text[i:i + 8]}, "done": False}
             for i in range(0, len(text), 8)]
    if calls:
        lines.append({"model": "qwen3.6:35b-a3b", "done": False, "message": {
            "role": "assistant", "content": "",
            "tool_calls": [{"function": {"name": n, "arguments": a}} for n, a in calls]}})
    lines.append({"model": "qwen3.6:35b-a3b", "message": {"role": "assistant", "content": ""}, "done": True,
                  "done_reason": done_reason, "prompt_eval_count": 3100, "eval_count": 85})
    return lines


def ollama_routes(models=(("qwen3.6:35b-a3b", 23_900_000_000, ["completion", "tools", "thinking", "vision"]),
                          ("nomic-embed-text:latest", 274_000_000, ["embedding"])), version: str = "0.40.11") -> dict:
    """What Ollama answers about itself and its models (docs.ollama.com/api, read on 25/10/2026)."""
    shows = {name: {"capabilities": caps, "details": {"family": "qwen3moe"},
                    **({"thinking": {"values": [False, True], "default": True}} if "thinking" in caps else {})}
             for name, _size, caps in models}
    routes = {"/api/version": {"version": version},
              "/api/tags": {"models": [{"name": n, "model": n, "size": size,
                                        "details": {"parameter_size": "35.0B", "quantization_level": "Q4_K_M"}}
                                       for n, size, _caps in models]},
              "/api/ps": {"models": []},
              "/v1/models": {"object": "list", "data": [{"id": n, "object": "model"} for n, _s, _c in models]}}
    routes["_shows"] = shows
    return routes
