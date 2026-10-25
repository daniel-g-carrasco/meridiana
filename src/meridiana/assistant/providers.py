"""The models Meridio talks to (study 14, 6.1-6.3; task 14): one interface, `Provider.stream`, that gives the answer
as it comes, as events: `Text` pieces, the `ToolCall`s the model asks for, the `Usage` of the round and `Done` with
why it ended. Three adapters:
- `OpenAICompatible`, towards a server that speaks OpenAI's chat completions with server-sent events: llama-server
  (llama.cpp, the local model chosen on 23/10/2026), Ollama, LM Studio, and the cloud services that copy the API.
  A plain client on `requests`, which Meridiana already has (energy/meteo.py), not the `openai` library;
- `Ollama`, Ollama's own API, where the context and the reasoning are set at each request (R105);
- `Anthropic`, Claude with the official SDK (`anthropic`, imported only when it is used: the program starts
  without it).

The conversation is kept in one shape for all (`Conversation.messages`), turned into each wire format here:
    {"role": "user", "content": text}
    {"role": "assistant", "content": text, "calls": [{"id", "name", "arguments": dict}], "raw": {family: ...}}
    {"role": "tool", "id": the call's id, "name": the tool, "content": JSON text, "error": bool}
`raw` keeps a provider's own answer to give back unchanged on the next round (Claude's thinking blocks must be
passed back as they came); another provider rebuilds the turn from `content` and `calls`.

`stream` runs on a worker thread (ui/assistant_chat.ChatJob): it never touches Qt. `stop` (a threading.Event) is
looked at between two pieces, and `cancel` closes the connection from the window's thread, so that a model that
has not yet written its first word stops at once. Errors are ProviderError with a kind the window can say in
words: "offline" (nothing answers: the local server is not running, or there is no network), "auth" (the key is
missing or refused), "limit" (rate or spending limit), "model" (the model is not there), "server" (the service
failed), "bad" (an answer that is not what the protocol says) and "tools" (the model does not call
tools). No Qt."""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field

LOCAL_CONNECT_S = 3.05          # a server on this PC answers at once or is not there
LOCAL_READ_S = 240.0            # the local model reads a long prompt before its first word (study 14, 4.4: up to 50 s)
CLOUD_TIMEOUT_S = 60.0
MAX_TOKENS = 2048               # an answer of Meridio is a few paragraphs (study 14, 4.4: 700-1500 tokens at most)
MAX_TOKENS_CLOUD = 8000         # Claude thinks before answering (adaptive, on by default): its thinking counts too
FALLBACK_BETA = "server-side-fallback-2026-07-01"      # Sonnet: a refusal re-run on another model (claude-api skill)


@dataclass(frozen=True)
class Text:
    text: str


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict | None       # None when the model wrote something that is not a JSON object
    raw: str = ""                # what it wrote, for the error sent back


@dataclass(frozen=True)
class Usage:
    input: int = 0               # tokens read at the full price
    output: int = 0
    cache_read: int = 0          # tokens read from the provider's cache
    cache_write: int = 0         # tokens written to it

    def __add__(self, other: Usage) -> Usage:
        return Usage(self.input + other.input, self.output + other.output, self.cache_read + other.cache_read,
                     self.cache_write + other.cache_write)

    @property
    def total(self) -> int:
        return self.input + self.output + self.cache_read + self.cache_write


@dataclass(frozen=True)
class Done:
    reason: str                  # "end", "tools", "length", "refusal", "stopped"
    model: str = ""              # the model that answered, as the provider says it
    raw: object = None           # the provider's own content of the turn, to give back as it came


class ProviderError(Exception):
    def __init__(self, kind: str, detail: str = ""):
        super().__init__(f"{kind}: {detail}" if detail else kind)
        self.kind = kind
        self.detail = detail


@dataclass
class Provider:
    """What a provider is: its family ("openai", "anthropic"), whether it is a cloud service, its model."""
    model: str = ""
    family: str = ""
    cloud: bool = False
    stop: threading.Event = field(default_factory=threading.Event, repr=False)

    def stream(self, system: str, messages: list[dict], tools: list[dict]) -> Iterator:
        raise NotImplementedError

    def cancel(self) -> None:
        """From the window's thread: stop now."""
        self.stop.set()


# OpenAI-compatible servers

def sse_data(lines) -> Iterator[str]:
    """The `data:` payloads of a stream of server-sent events, one per event (the lines of one event joined), up
    to `[DONE]`; comments and other fields are skipped."""
    parts: list[str] = []
    for raw in lines:
        line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
        line = line.rstrip("\r")
        if not line:
            if parts:
                payload = "\n".join(parts)
                parts = []
                if payload.strip() == "[DONE]":
                    return
                yield payload
            continue
        if line.startswith(":"):
            continue
        name, _colon, value = line.partition(":")
        if name == "data":
            parts.append(value[1:] if value.startswith(" ") else value)
    if parts and "\n".join(parts).strip() != "[DONE]":
        yield "\n".join(parts)


def openai_messages(system: str, messages: list[dict]) -> list[dict]:
    """The conversation as OpenAI's chat completions take it."""
    out = [{"role": "system", "content": system}] if system else []
    for m in messages:
        role = m["role"]
        if role == "user":
            out.append({"role": "user", "content": m["content"]})
        elif role == "assistant":
            turn = {"role": "assistant", "content": m.get("content") or ""}
            calls = m.get("calls") or []
            if calls:
                turn["tool_calls"] = [{"id": c["id"], "type": "function", "function": {
                    "name": c["name"], "arguments": json.dumps(c.get("arguments") or {}, ensure_ascii=False)}}
                    for c in calls]
            out.append(turn)
        elif role == "tool":
            out.append({"role": "tool", "tool_call_id": m["id"], "content": m["content"]})
    return out


def openai_tools(tools: list[dict]) -> list[dict]:
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                              "parameters": t["parameters"]}} for t in tools]


def _arguments(text: str) -> dict | None:
    try:
        value = json.loads(text) if text.strip() else {}
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


@dataclass
class OpenAICompatible(Provider):
    """A server with OpenAI's chat completions: `base_url` is the part before /chat/completions
    ("http://127.0.0.1:9931/v1" for llama-server). `key` only for a cloud service that wants one. `local` sends
    llama-server's switch that keeps Qwen's reasoning off (study 14, 4.5: on, the same question takes two or three
    times as long)."""
    base_url: str = "http://127.0.0.1:9931/v1"
    key: str = ""
    local: bool = True
    max_tokens: int = MAX_TOKENS
    family: str = "openai"
    session: object = field(default=None, repr=False)        # a requests.Session, for the tests
    _response: object = field(default=None, repr=False)

    def cancel(self) -> None:
        """Stop now, also while the reader waits for a model that reads a long prompt and sends nothing for tens
        of seconds: the connection shut down (it wakes the reader on Linux, and llama-server stops at its next
        word) and the socket's file closed (it wakes the reader on Windows, where a shutdown alone does not)."""
        self.stop.set()
        response = self._response
        if response is None:
            return
        raw = getattr(response, "raw", None)
        # urllib3 2 lets go of the connection's socket once the body is streaming: it is http.client's file then,
        # a SocketIO whose socket object is marked closed while its descriptor still reads
        sockio = getattr(getattr(getattr(raw, "_fp", None), "fp", None), "raw", None)
        sock = getattr(sockio, "_sock", None) or getattr(getattr(raw, "connection", None), "sock", None)
        try:
            fd = sock.fileno() if sock is not None else -1
            if fd != -1:
                import socket
                held = socket.socket(fileno=fd)         # a wrapper of the same descriptor, let go at once
                try:
                    held.shutdown(socket.SHUT_RDWR)
                finally:
                    held.detach()
            if sockio is not None and hasattr(sockio, "readinto"):
                sockio.close()                          # the descriptor really closed: the blocked read returns
            response.close()
        except Exception:  # noqa: BLE001  closing a connection another thread is reading: whatever it says
            pass

    def stream(self, system: str, messages: list[dict], tools: list[dict]) -> Iterator:
        import requests
        body = {"model": self.model or "local", "messages": openai_messages(system, messages), "stream": True,
                "stream_options": {"include_usage": True}, "max_tokens": self.max_tokens}
        if tools:
            body["tools"] = openai_tools(tools)
        if self.local:
            body["chat_template_kwargs"] = {"enable_thinking": False}
        headers = {"Accept": "text/event-stream"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        url = self.base_url.rstrip("/") + "/chat/completions"
        http = self.session or requests
        try:
            response = http.post(url, json=body, headers=headers, stream=True,
                                 timeout=(LOCAL_CONNECT_S, LOCAL_READ_S) if self.local else CLOUD_TIMEOUT_S)
        except requests.ConnectionError as error:
            if self.stop.is_set():
                yield Done("stopped")
                return
            raise ProviderError("offline", str(error)) from error
        except requests.Timeout as error:
            raise ProviderError("offline", str(error)) from error
        self._response = response
        try:
            if self.stop.is_set():          # Stop came while the request went, before there was a response to close
                yield Done("stopped")
                return
            if response.status_code != 200:
                raise _http_error(response.status_code, _body_text(response))
            yield from self._read(response)
        except (requests.RequestException, AttributeError, ValueError, OSError) as error:
            if self.stop.is_set():          # the connection closed under the reader by Stop
                yield Done("stopped")
                return
            if isinstance(error, ProviderError):
                raise
            raise ProviderError("offline" if isinstance(error, requests.ConnectionError) else "bad",
                                str(error)) from error
        finally:
            self._response = None
            try:
                response.close()
            except Exception:  # noqa: BLE001  already closed by cancel()
                pass

    def _read(self, response) -> Iterator:
        calls: dict[int, dict] = {}
        reason, model, usage = "end", self.model, None
        for payload in sse_data(response.iter_lines()):
            if self.stop.is_set():
                yield Done("stopped")
                return
            try:
                chunk = json.loads(payload)
            except ValueError as error:
                raise ProviderError("bad", f"not JSON: {payload[:80]}") from error
            if not isinstance(chunk, dict):
                continue
            if chunk.get("error"):
                error = chunk["error"]
                raise ProviderError("server", error.get("message", str(error)) if isinstance(error, dict) else str(error))
            model = chunk.get("model") or model
            if isinstance(chunk.get("usage"), dict):
                u = chunk["usage"]
                cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
                usage = Usage(input=max(0, int(u.get("prompt_tokens") or 0) - int(cached)),
                              output=int(u.get("completion_tokens") or 0), cache_read=int(cached))
            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                if delta.get("content"):
                    yield Text(delta["content"])
                for piece in delta.get("tool_calls") or []:
                    slot = calls.setdefault(int(piece.get("index", len(calls))), {"id": "", "name": "", "arguments": ""})
                    slot["id"] = piece.get("id") or slot["id"]
                    function = piece.get("function") or {}
                    slot["name"] = function.get("name") or slot["name"]
                    slot["arguments"] += function.get("arguments") or ""
                finish = choice.get("finish_reason")
                if finish:
                    reason = {"tool_calls": "tools", "length": "length", "stop": "end"}.get(finish, "end")
        if self.stop.is_set():
            yield Done("stopped")
            return
        for n, (_index, c) in enumerate(sorted(calls.items())):
            yield ToolCall(c["id"] or f"call_{n}", c["name"], _arguments(c["arguments"]), c["arguments"])
        if calls and reason == "end":
            reason = "tools"
        if usage is not None:
            yield usage
        yield Done(reason, model)


def _body_text(response) -> str:
    try:
        data = response.json()
        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict):
            return str(error.get("message") or error)
        return str(error or data)[:300]
    except ValueError:
        return (response.text or "")[:300]


def _http_error(status: int, text: str) -> ProviderError:
    if status in (401, 403):
        return ProviderError("auth", text)
    if status == 404:
        return ProviderError("model", text)
    if status == 429:
        return ProviderError("limit", text)
    return ProviderError("server" if status >= 500 else "bad", f"HTTP {status}: {text}")


# Ollama's own API

OLLAMA_CONTEXT = 16384          # Meridio's instructions, ten tools and a few results (study 14, 4.4: 2-4k a round)
OLLAMA_KEEP = "30m"             # the model stays loaded between two questions


def ollama_messages(system: str, messages: list[dict]) -> list[dict]:
    """The conversation as Ollama's /api/chat takes it: the calls without ids and with their arguments as objects,
    each result with the name of its tool."""
    out = [{"role": "system", "content": system}] if system else []
    for m in messages:
        role = m["role"]
        if role == "user":
            out.append({"role": "user", "content": m["content"]})
        elif role == "assistant":
            turn = {"role": "assistant", "content": m.get("content") or ""}
            calls = m.get("calls") or []
            if calls:
                turn["tool_calls"] = [{"type": "function", "function": {"name": c["name"],
                                                                        "arguments": c.get("arguments") or {}}}
                                      for c in calls]
            out.append(turn)
        elif role == "tool":
            out.append({"role": "tool", "content": m["content"], "tool_name": m.get("name", "")})
    return out


def ollama_think(show: dict, model: str = "") -> object:
    """What `think` to send for a model, from Ollama's /api/show: off when the model can turn it off, the lowest
    effort when it only takes efforts (gpt-oss: low, medium, high), nothing when it does not reason."""
    caps = show.get("capabilities") if isinstance(show, dict) else None
    thinking = show.get("thinking") if isinstance(show, dict) else None
    values = thinking.get("values") if isinstance(thinking, dict) else None
    if isinstance(values, list) and values:
        if False in values:
            return False
        for effort in ("low", "medium", "high"):
            if effort in values:
                return effort
        return None
    if isinstance(caps, list):
        if "thinking" not in caps:
            return None
        return "low" if model.startswith("gpt-oss") else False
    return None


@dataclass
class Ollama(OpenAICompatible):
    """Ollama through its own API (/api/chat, lines of JSON), not the OpenAI-compatible one: there the context
    cannot be set, and Ollama's default is 4.096 tokens below 24 GiB of video memory, which cuts Meridio's
    instructions from the front without saying so (docs.ollama.com/context-length, 25/10/2026; study 14a). Here
    the context is asked at each request (the same every time: Ollama reloads a model when it changes), the
    reasoning off or at its lowest (`think`, read once from /api/show), the model kept loaded half an hour. A
    malformed call that makes Ollama fail with 500 before a word (ollama#16383) is asked once more."""
    base_url: str = "http://127.0.0.1:11434"
    context: int = OLLAMA_CONTEXT
    family: str = "ollama"
    think: object = "ask"       # "ask": read from /api/show the first time; then False, "low"... or None (not sent)

    def _think(self, http) -> object:
        import requests
        if self.think == "ask":
            self.think = None
            try:
                r = http.post(self.base_url.rstrip("/") + "/api/show", json={"model": self.model},
                              timeout=(LOCAL_CONNECT_S, 10.0))
                if r.status_code == 200:
                    self.think = ollama_think(r.json(), self.model)
            except (requests.RequestException, ValueError, OSError):
                self.think = None           # the question goes without `think`: the server's default
        return self.think

    def stream(self, system: str, messages: list[dict], tools: list[dict]) -> Iterator:
        import requests
        if not self.model:
            raise ProviderError("model", "no model chosen")
        http = self.session or requests
        think = self._think(http)
        body = {"model": self.model, "messages": ollama_messages(system, messages), "stream": True,
                "options": {"num_ctx": self.context, "num_predict": self.max_tokens}, "keep_alive": OLLAMA_KEEP}
        if tools:
            body["tools"] = openai_tools(tools)
        if think is not None:
            body["think"] = think
        url = self.base_url.rstrip("/") + "/api/chat"
        for attempt in (1, 2):
            try:
                response = http.post(url, json=body, stream=True, timeout=(LOCAL_CONNECT_S, LOCAL_READ_S))
            except requests.ConnectionError as error:
                if self.stop.is_set():
                    yield Done("stopped")
                    return
                raise ProviderError("offline", str(error)) from error
            except requests.Timeout as error:
                raise ProviderError("offline", str(error)) from error
            self._response = response
            try:
                if self.stop.is_set():
                    yield Done("stopped")
                    return
                if response.status_code == 500 and attempt == 1:
                    continue                    # a call the model wrote badly: once more (ollama#16383)
                if response.status_code != 200:
                    text = _body_text(response)
                    if response.status_code == 400 and "does not support tools" in text:
                        raise ProviderError("tools", text)
                    raise _http_error(response.status_code, text)
                yield from self._read_lines(response)
                return
            except (requests.RequestException, AttributeError, ValueError, OSError) as error:
                if self.stop.is_set():
                    yield Done("stopped")
                    return
                if isinstance(error, ProviderError):
                    raise
                raise ProviderError("offline" if isinstance(error, requests.ConnectionError) else "bad",
                                    str(error)) from error
            finally:
                self._response = None
                try:
                    response.close()
                except Exception:  # noqa: BLE001  already closed by cancel()
                    pass

    def _read_lines(self, response) -> Iterator:
        calls: list[dict] = []
        reason, model, usage = "end", self.model, None
        for raw in response.iter_lines():
            if self.stop.is_set():
                yield Done("stopped")
                return
            line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
            if not line.strip():
                continue
            try:
                chunk = json.loads(line)
            except ValueError as error:
                raise ProviderError("bad", f"not JSON: {line[:80]}") from error
            if not isinstance(chunk, dict):
                continue
            if chunk.get("error"):
                raise ProviderError("server", str(chunk["error"]))
            model = chunk.get("model") or model
            message = chunk.get("message") or {}
            if message.get("content"):
                yield Text(message["content"])
            for c in message.get("tool_calls") or []:
                function = (c or {}).get("function") or {}
                if function.get("name"):
                    calls.append(function)
            if chunk.get("done"):
                reason = {"length": "length", "stop": "end"}.get(chunk.get("done_reason") or "stop", "end")
                usage = Usage(input=int(chunk.get("prompt_eval_count") or 0),
                              output=int(chunk.get("eval_count") or 0))
                break
        if self.stop.is_set():
            yield Done("stopped")
            return
        for n, f in enumerate(calls):
            arguments = f.get("arguments")
            if isinstance(arguments, str):
                raw_args, arguments = arguments, _arguments(arguments)
            else:
                raw_args = json.dumps(arguments, ensure_ascii=False, default=str)
                arguments = arguments if isinstance(arguments, dict) else None
            yield ToolCall(f"call_{n}_{f['name']}", f["name"], arguments, raw_args)
        if calls and reason == "end":
            reason = "tools"
        if usage is not None:
            yield usage
        yield Done(reason, model)


# Claude

TOOL_ID = re.compile(r"[^a-zA-Z0-9_-]")


def anthropic_messages(messages: list[dict]) -> list[dict]:
    """The conversation as Claude's Messages API takes it: an answer of Claude's own given back as it came (its
    content blocks, thinking included); the others rebuilt as text and tool_use blocks; the results of the tools
    of one turn together in one user message, as the API asks."""
    out: list[dict] = []
    results: list[dict] = []

    def flush() -> None:
        if results:
            out.append({"role": "user", "content": list(results)})
            results.clear()
    for m in messages:
        role = m["role"]
        if role == "tool":
            block = {"type": "tool_result", "tool_use_id": TOOL_ID.sub("_", m["id"]), "content": m["content"]}
            if m.get("error"):
                block["is_error"] = True
            results.append(block)
            continue
        flush()
        if role == "user":
            out.append({"role": "user", "content": m["content"]})
        elif role == "assistant":
            raw = (m.get("raw") or {}).get("anthropic")
            if raw is not None:
                out.append({"role": "assistant", "content": raw})
                continue
            blocks: list[dict] = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for c in m.get("calls") or []:
                blocks.append({"type": "tool_use", "id": TOOL_ID.sub("_", c["id"]), "name": c["name"],
                               "input": c.get("arguments") or {}})
            out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": "…"}]})
    flush()
    return out


def anthropic_tools(tools: list[dict]) -> list[dict]:
    """The tools with their inputs streamed as they are written (the claude-api skill's default for streaming with
    client tools): the inputs are checked by tools.py before anything runs."""
    return [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"],
             "eager_input_streaming": True} for t in tools]


@dataclass
class Anthropic(Provider):
    """Claude through the official SDK. `effort` is the model's thinking depth (Haiku 5.5 and Sonnet 5.5 think
    adaptively by default; "low" keeps the current questions quick and cheap); `fallbacks` re-runs a refused
    request on another model inside the same call (beta, Sonnet only: the claude-api skill asks it by default);
    `client` stands in for anthropic.Anthropic in the tests."""
    key: str = ""
    effort: str = "low"
    fallbacks: bool = False
    max_tokens: int = MAX_TOKENS_CLOUD
    family: str = "anthropic"
    cloud: bool = True
    client: object = field(default=None, repr=False)
    _stream: object = field(default=None, repr=False)

    def _client(self):
        if self.client is None:
            try:
                import anthropic
            except ImportError as error:
                raise ProviderError("missing", "anthropic") from error
            self.client = anthropic.Anthropic(api_key=self.key, max_retries=1, timeout=CLOUD_TIMEOUT_S)
        return self.client

    def cancel(self) -> None:
        self.stop.set()
        stream = self._stream
        if stream is not None:
            try:
                stream.close()
            except Exception:  # noqa: BLE001  closing a stream another thread is reading: whatever it says
                pass

    def request(self, system: str, messages: list[dict], tools: list[dict]) -> dict:
        """The arguments of the call: the instructions and the tools cached (they are the same at every round),
        the conversation after them."""
        args = {"model": self.model, "max_tokens": self.max_tokens,
                "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                "messages": anthropic_messages(messages), "output_config": {"effort": self.effort},
                "cache_control": {"type": "ephemeral"}}
        if tools:
            args["tools"] = anthropic_tools(tools)
        if self.fallbacks:
            args["betas"] = [FALLBACK_BETA]
            args["fallbacks"] = "default"
        return args

    def stream(self, system: str, messages: list[dict], tools: list[dict]) -> Iterator:
        client = self._client()
        args = self.request(system, messages, tools)
        errors = _anthropic_errors()
        try:
            opened = client.beta.messages.stream(**args) if self.fallbacks else client.messages.stream(**args)
            with opened as stream:
                self._stream = stream
                for event in stream:
                    if self.stop.is_set():
                        break
                    if getattr(event, "type", "") == "text" and event.text:
                        yield Text(event.text)
                if self.stop.is_set():
                    yield Done("stopped")
                    return
                final = stream.get_final_message()
        except errors as error:
            if self.stop.is_set():
                yield Done("stopped")
                return
            raise _anthropic_error(error) from error
        finally:
            self._stream = None
        content = list(final.content or [])
        for block in content:
            if getattr(block, "type", "") == "tool_use":
                arguments = block.input if isinstance(block.input, dict) else None
                yield ToolCall(block.id, block.name, arguments, json.dumps(block.input, default=str))
        u = final.usage
        yield Usage(input=int(getattr(u, "input_tokens", 0) or 0), output=int(getattr(u, "output_tokens", 0) or 0),
                    cache_read=int(getattr(u, "cache_read_input_tokens", 0) or 0),
                    cache_write=int(getattr(u, "cache_creation_input_tokens", 0) or 0))
        reason = {"tool_use": "tools", "end_turn": "end", "max_tokens": "length", "refusal": "refusal",
                  "stop_sequence": "end", "pause_turn": "end"}.get(final.stop_reason or "end_turn", "end")
        yield Done(reason, getattr(final, "model", "") or self.model, content)


def _anthropic_errors() -> tuple:
    """The SDK's errors, when it is there; the tests' fake client raises ProviderError itself."""
    try:
        import anthropic
    except ImportError:
        return (ProviderError,)
    return (anthropic.APIError, ProviderError)


def _anthropic_error(error) -> ProviderError:
    if isinstance(error, ProviderError):
        return error
    import anthropic
    if isinstance(error, anthropic.APIConnectionError):         # no network, the name not resolved, a timeout
        return ProviderError("offline", str(error))
    if isinstance(error, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return ProviderError("auth", getattr(error, "message", str(error)))
    if isinstance(error, anthropic.RateLimitError):
        return ProviderError("limit", getattr(error, "message", str(error)))
    if isinstance(error, anthropic.NotFoundError):
        return ProviderError("model", getattr(error, "message", str(error)))
    if isinstance(error, anthropic.BadRequestError):
        return ProviderError("bad", getattr(error, "message", str(error)))
    return ProviderError("server", getattr(error, "message", str(error)))
