"""The local models on this PC, made simple (R105, 25/10/2026; study 14a): what is installed and what is running,
the models each one has, the one to use and why, and the few steps when there is none.

- **Running**: the servers that answer on 127.0.0.1, on the ports their programs use by default: Ollama 11434,
  LM Studio 1234, llama.cpp's llama-server 9931 (8080 before its 0.7.0 and in its Docker images), Jan 1337,
  Lemonade 13305, Docker Model Runner 12434, koboldcpp 5001, and 8000 for any other OpenAI-compatible one (vLLM,
  LocalAI's own). Several of them also answer Ollama's API, so each is recognised by what only it has (`identify`).
  A port is first tried with a bare connection of 0,3 s, all together: on Windows a closed port takes two seconds
  to refuse, and the survey must not wait for it.
- **Installed**: the programs on the disk, and the models they keep (`installed`): told how to start them.
- **The PC**: the RAM and the video memory of an NVIDIA card (`machine`), for what fits.
- **The choice** (`choose`, `guide`): from a table of the models of October 2026 with how well they call tools and
  speak Italian (`CANDIDATES`, the sources in study 14a), the best that fits the memory of this PC.
- **The test** (`check`): a short question that must come back as a call of a tool, as Meridio's do.

Everything here reads, nothing is installed or downloaded; it runs on a worker thread (ui/assistant_chat.SurveyJob,
the preferences): it never touches Qt."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from ..i18n import _, number

HOST = "127.0.0.1"
# port -> the runtime that uses it by default (the sources in study 14a, read on 25/10/2026)
PORTS = {11434: "ollama", 1234: "lmstudio", 9931: "llamacpp", 8080: "llamacpp", 1337: "jan", 13305: "lemonade",
         12434: "docker", 5001: "koboldcpp", 8000: "openai"}
CONNECT_S = 0.3                 # a server on this PC accepts at once
ASK_S = (1.0, 3.0)              # connect, read: a local server's list of models
SHOW_MODELS = 16                # Ollama: the models whose details are asked (/api/show), at most
MIN_CONTEXT = 12288             # below this Meridio's instructions, tools and a few results do not fit
GB = 1e9


def names() -> dict:
    return {"ollama": "Ollama", "lmstudio": "LM Studio", "llamacpp": "llama.cpp (llama-server)", "jan": "Jan",
            "lemonade": "Lemonade", "docker": "Docker Model Runner", "koboldcpp": "KoboldCpp",
            "openai": _("an OpenAI-compatible server"), "foundry": "Foundry Local"}


@dataclass
class Model:
    """A model a runtime has: `name` as a request names it."""
    name: str
    size: int = 0               # bytes on disk, 0 when not said
    params: str = ""            # "35B", "9.7B"
    tools: bool | None = None   # the runtime says it calls tools; None when it does not say
    context: int = 0            # the context it is loaded with, 0 when not said or not loaded
    loaded: bool = False
    thinking: tuple = ()        # Ollama: what its `think` takes (False, True, "low"...)

    @property
    def gb(self) -> float:
        return self.size / GB


@dataclass
class Runtime:
    """A program that serves models: running (it answers at `url`) or only installed (on the disk at `where`)."""
    kind: str
    url: str = ""               # what Meridio's provider is given: Ollama's own address, else the /v1 one
    running: bool = False
    installed: bool = False
    version: str = ""
    models: list = field(default_factory=list)
    where: str = ""             # the program or the data folder found on the disk
    note: str = ""              # what stops it from being used as it is (a key wanted, a context too small)
    locked: bool = False        # it wants a key: not used

    @property
    def name(self) -> str:
        return names().get(self.kind, self.kind)

    @property
    def api(self) -> str:
        """The provider that speaks to it: "ollama" (its own API) or "openai"."""
        return "ollama" if self.kind == "ollama" else "openai"

    def start(self) -> str:
        """How to start it, when it is installed and not running."""
        return start_hint(self.kind)


def start_hint(kind: str) -> str:
    return {
        "ollama": _("open Ollama from the Start menu (it stays in the notification area), or run: ollama serve"),
        "lmstudio": _("start its server: lms server start (or Developer > Start server in LM Studio)"),
        "llamacpp": _("start it with a model, for example: llama-server -hf unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ4_XS "
                      "-c 16384"),
        "jan": _("in Jan: Settings > Local API Server > Start Server"),
        "foundry": _("find its address with: foundry server status"),
    }.get(kind, "")


# talking to the servers

def _session(http=None):
    """A requests session that does not send the PC's own addresses through a proxy set in the environment."""
    if http is not None:
        return http
    import requests
    s = requests.Session()
    s.trust_env = False
    return s


def _get(http, url: str, timeout=ASK_S):
    """(status, JSON or None) of a GET; (0, None) when nothing answers."""
    import requests
    try:
        r = http.get(url, timeout=timeout)
    except requests.RequestException:
        return 0, None
    try:
        data = r.json()
    except ValueError:
        data = None
    return r.status_code, data


def _post(http, url: str, body: dict, timeout=ASK_S):
    import requests
    try:
        r = http.post(url, json=body, timeout=timeout)
    except requests.RequestException:
        return 0, None
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, None


def open_ports(ports, host: str = HOST, timeout: float = CONNECT_S) -> list[int]:
    """The ports that accept a connection, tried all together, in the order given."""
    ports = list(dict.fromkeys(ports))

    def accepts(port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False
    if not ports:
        return []
    with ThreadPoolExecutor(max_workers=min(16, len(ports))) as pool:
        return [p for p, ok in zip(ports, pool.map(accepts, ports), strict=True) if ok]


def _items(data, *keys) -> list:
    """The list under the first of `keys` that holds one."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in keys:
            if isinstance(data.get(k), list):
                return data[k]
    return []


def identify(base: str, port: int = 0, http=None) -> Runtime | None:
    """What answers at `base` ("http://127.0.0.1:11434"): each runtime by what only it has, then any server with
    OpenAI's list of models; None when nothing of the kind answers."""
    http = _session(http)
    status, props = _get(http, base + "/props")
    if status == 200 and isinstance(props, dict) and ("build_info" in props or "default_generation_settings" in props):
        return _llamacpp(base, props, http, kind="koboldcpp" if PORTS.get(port) == "koboldcpp" else "llamacpp")
    status, data = _get(http, base + "/api/v1/models")
    if status == 200 and isinstance(data, dict) and isinstance(data.get("models"), list):
        return _lmstudio_v1(base, data)
    listed = _items(data, "data") if status == 200 else []
    if any(isinstance(m, dict) and "labels" in m for m in listed):
        return _lemonade(base, data)
    status, data = _get(http, base + "/engines/v1/models")
    if status == 200 and isinstance(data, dict) and isinstance(data.get("data"), list):
        return _openai(base, base + "/engines/v1", data, "docker")
    status, data = _get(http, base + "/api/version")
    if status == 200 and isinstance(data, dict) and "version" in data and PORTS.get(port, "ollama") == "ollama":
        return _ollama(base, str(data["version"]), http)
    status, data = _get(http, base + "/v1/models")
    kind = PORTS.get(port, "openai")
    kind = kind if kind in ("jan", "koboldcpp", "lmstudio", "lemonade", "llamacpp") else "openai"
    if status == 200 and isinstance(data, dict) and isinstance(data.get("data"), list):
        if kind == "lmstudio":
            status0, data0 = _get(http, base + "/api/v0/models")
            if status0 == 200 and _items(data0, "data"):
                return _lmstudio_v0(base, data0)
        return _openai(base, base + "/v1", data, kind)
    if status in (401, 403):
        return Runtime(kind, base + "/v1", running=True, locked=True,
                       note=_("it wants an API key: Meridio does not send one to a local server; turn the key off "
                              "in its settings"))
    return None


def _ollama(base: str, version: str, http) -> Runtime:
    rt = Runtime("ollama", base, running=True, version=version)
    _status, tags = _get(http, base + "/api/tags")
    _s, ps = _get(http, base + "/api/ps")
    loaded = {m.get("name"): m for m in _items(ps, "models") if isinstance(m, dict)}
    for m in _items(tags, "models")[:64]:
        if not isinstance(m, dict) or not m.get("name"):
            continue
        details = m.get("details") or {}
        model = Model(m["name"], int(m.get("size") or 0), str(details.get("parameter_size") or ""))
        if m["name"] in loaded:
            model.loaded = True
            model.context = int(loaded[m["name"]].get("context_length") or 0)
        rt.models.append(model)
    for model in rt.models[:SHOW_MODELS]:
        status, show = _post(http, base + "/api/show", {"model": model.name})
        if status != 200 or not isinstance(show, dict):
            continue
        caps = show.get("capabilities")
        if isinstance(caps, list):
            model.tools = "tools" in caps
            if "embedding" in caps and "completion" not in caps:
                model.tools = False
        values = (show.get("thinking") or {}).get("values") if isinstance(show.get("thinking"), dict) else None
        if isinstance(values, list):
            model.thinking = tuple(values)
        elif isinstance(caps, list) and "thinking" in caps:
            model.thinking = (False, True)
    rt.models = [m for m in rt.models if m.tools is not False or "embed" not in m.name]
    return rt


def _lmstudio_v1(base: str, data: dict) -> Runtime:
    rt = Runtime("lmstudio", base + "/v1", running=True)
    for m in data["models"]:
        if not isinstance(m, dict) or m.get("type") not in ("llm", "vlm", None) or not m.get("key"):
            continue
        caps = m.get("capabilities") or {}
        instances = m.get("loaded_instances") or []
        context = 0
        for inst in instances:
            context = max(context, int(((inst or {}).get("config") or {}).get("context_length") or 0))
        rt.models.append(Model(m["key"], int(m.get("size_bytes") or 0), str(m.get("params_string") or ""),
                               tools=caps.get("trained_for_tool_use") if isinstance(caps, dict) else None,
                               context=context, loaded=bool(instances)))
    short = [m for m in rt.models if m.loaded and 0 < m.context < MIN_CONTEXT]
    if short:
        rt.note = _("{model} is loaded with {n} tokens of context: Meridio wants at least {min}; load it with: lms "
                    "load {model} --context-length 16384").format(model=short[0].name, n=short[0].context,
                                                                  min=MIN_CONTEXT)
    return rt


def _lmstudio_v0(base: str, data: dict) -> Runtime:
    rt = Runtime("lmstudio", base + "/v1", running=True)
    for m in _items(data, "data"):
        if isinstance(m, dict) and m.get("id") and m.get("type", "llm") in ("llm", "vlm"):
            loaded = m.get("state") == "loaded"
            rt.models.append(Model(m["id"], loaded=loaded,
                                   context=int(m.get("loaded_context_length") or 0) if loaded else 0))
    return rt


def _lemonade(base: str, data: dict) -> Runtime:
    rt = Runtime("lemonade", base + "/api/v1", running=True)
    for m in _items(data, "data"):
        if not isinstance(m, dict) or not m.get("id") or m.get("downloaded") is False:
            continue
        labels = m.get("labels") or []
        if "embeddings" in labels or "reranking" in labels:
            continue
        rt.models.append(Model(m["id"], tools="tool-calling" in labels))
    return rt


def _llamacpp(base: str, props: dict, http, kind: str = "llamacpp") -> Runtime:
    rt = Runtime(kind, base + "/v1", running=True, version=str((props.get("build_info") or "")))
    n_ctx = int((props.get("default_generation_settings") or {}).get("n_ctx") or 0)
    caps = props.get("chat_template_caps") or {}
    tools = caps.get("supports_tools") if isinstance(caps, dict) and "supports_tools" in caps else None
    status, data = _get(http, base + "/models")              # router mode: several models, each with its state
    listed = _items(data, "data", "models") if status == 200 else []
    if not listed:
        _s, data = _get(http, base + "/v1/models")
        listed = _items(data, "data", "models")
    for m in listed:
        if not isinstance(m, dict):
            continue
        name = m.get("id") or m.get("name") or m.get("model")
        if not name:
            continue
        meta = m.get("meta") or {}
        state = m.get("status")
        state = state.get("value") if isinstance(state, dict) else state
        rt.models.append(Model(str(name), int(meta.get("size") or 0),
                               _params(meta.get("n_params")), tools=tools,
                               context=n_ctx, loaded=state in (None, "loaded")))
    if not rt.models and props.get("model_path"):
        rt.models.append(Model(Path(str(props["model_path"])).stem, tools=tools, context=n_ctx, loaded=True))
    if n_ctx and n_ctx < MIN_CONTEXT:
        rt.note = _("its context is {n} tokens: Meridio wants at least {min}; start it with -c 16384").format(
            n=n_ctx, min=MIN_CONTEXT)
    return rt


def _params(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return ""
    return f"{n / 1e9:.1f}B" if n >= 1e9 else (f"{n / 1e6:.0f}M" if n > 0 else "")


def _openai(base: str, url: str, data: dict, kind: str) -> Runtime:
    rt = Runtime(kind, url, running=True)
    for m in _items(data, "data"):
        if isinstance(m, dict) and m.get("id") and "embed" not in str(m["id"]).lower():
            rt.models.append(Model(str(m["id"])))
    return rt


def running(ports=None, host: str = HOST, http=None, extra: tuple = ()) -> list[Runtime]:
    """The local servers that answer now: on the known ports and on those of `extra` (the address already in the
    preferences), each recognised in parallel."""
    wanted = list(ports if ports is not None else PORTS) + [p for p in extra if p]
    found = open_ports(wanted, host)
    if not found:
        return []
    http = _session(http)
    with ThreadPoolExecutor(max_workers=min(8, len(found))) as pool:
        out = list(pool.map(lambda p: identify(f"http://{host}:{p}", p, http), found))
    return [rt for rt in out if rt is not None]


# on the disk

def _env(name: str, env) -> Path | None:
    value = env.get(name)
    return Path(value) if value else None


def installed(env=None, home: Path | None = None, which=shutil.which, platform: str | None = None) -> list[Runtime]:
    """The runtimes whose program or data are on the disk, with the models they keep (read from their folders, not
    asked: they may not be running)."""
    env = os.environ if env is None else env
    home = Path.home() if home is None else home
    platform = platform or sys.platform
    windows = platform.startswith("win")
    local = _env("LOCALAPPDATA", env) or home / "AppData" / "Local"
    roaming = _env("APPDATA", env) or home / "AppData" / "Roaming"
    out: list[Runtime] = []

    def first(paths) -> Path | None:
        return next((p for p in paths if p and p.exists()), None)

    # Ollama: its program, and the manifests of its models (registry/namespace/name/tag)
    exe = which("ollama")
    program = Path(exe) if exe else first([local / "Programs" / "Ollama" / "ollama.exe"] if windows else
                                          [Path("/usr/local/bin/ollama"), Path("/usr/bin/ollama"),
                                           Path("/Applications/Ollama.app")])
    store = first([_env("OLLAMA_MODELS", env), home / ".ollama" / "models", Path("/usr/share/ollama/.ollama/models")])
    if program or store:
        rt = Runtime("ollama", f"http://{HOST}:11434", installed=bool(program), where=str(program or store))
        if store:
            rt.models = ollama_manifests(store)
        out.append(rt)
    # LM Studio: its command line or the app, the GGUF files of its folder
    exe = which("lms")
    program = Path(exe) if exe else first([home / ".lmstudio" / "bin" / ("lms.exe" if windows else "lms"),
                                           local / "Programs" / "LM Studio" / "LM Studio.exe",
                                           Path("/Applications/LM Studio.app")])
    store = first([home / ".lmstudio" / "models", home / ".cache" / "lm-studio" / "models"])
    if program or store:
        rt = Runtime("lmstudio", f"http://{HOST}:1234/v1", installed=bool(program), where=str(program or store))
        if store:
            rt.models = gguf_files(store)
        out.append(rt)
    # llama.cpp: llama-server on the PATH (winget, brew, a folder of its own), the GGUF files it downloaded
    exe = which("llama-server") or which("llama-server.exe")
    program = Path(exe) if exe else first([local / "Microsoft" / "WinGet" / "Links" / "llama-server.exe"] if windows
                                          else [Path("/usr/local/bin/llama-server"), Path("/usr/bin/llama-server")])
    if program:
        rt = Runtime("llamacpp", f"http://{HOST}:9931/v1", installed=True, where=str(program))
        caches = [_env("LLAMA_CACHE", env), (_env("HF_HOME", env) or home / ".cache" / "huggingface") / "hub",
                  local / "llama.cpp", home / ".cache" / "llama.cpp"]
        for c in caches:
            if c and c.exists():
                rt.models += gguf_files(c)
        out.append(rt)
    # Jan: its data folder, the models in llamacpp/models/<org>/<repo>
    data = first([roaming / "Jan" / "data"] if windows else
                 [home / ".local" / "share" / "Jan" / "data",
                  home / "Library" / "Application Support" / "Jan" / "data"])
    if data:
        rt = Runtime("jan", f"http://{HOST}:1337/v1", installed=True, where=str(data))
        models = data / "llamacpp" / "models"
        if models.exists():
            rt.models = [Model(f"{org.name}/{repo.name}") for org in _dirs(models) for repo in _dirs(org)][:64]
        out.append(rt)
    exe = which("foundry")
    if exe:
        out.append(Runtime("foundry", "", installed=True, where=exe,
                           note=_("its port changes at every start: find it with foundry server status and write "
                                  "the address in the field above")))
    return out


def _dirs(folder: Path) -> list[Path]:
    try:
        return sorted(p for p in folder.iterdir() if p.is_dir())
    except OSError:
        return []


def ollama_manifests(store: Path) -> list[Model]:
    """Ollama's models from their manifests: library/<name>/<tag> as «name:tag», others as «namespace/name:tag»;
    the size is the sum of the layers the manifest lists."""
    out = []
    root = store / "manifests"
    for registry in _dirs(root):
        for namespace in _dirs(registry):
            for name in _dirs(namespace):
                try:
                    tags = sorted(p for p in name.iterdir() if p.is_file())
                except OSError:
                    continue
                for tag in tags:
                    size = 0
                    try:
                        manifest = json.loads(tag.read_text(encoding="utf-8"))
                        size = sum(int(layer.get("size") or 0) for layer in manifest.get("layers") or [])
                    except (OSError, ValueError, AttributeError):
                        pass
                    full = f"{name.name}:{tag.name}"
                    if namespace.name != "library" or registry.name != "registry.ollama.ai":
                        full = f"{namespace.name}/{full}"
                    out.append(Model(full, size))
                    if len(out) >= 64:
                        return out
    return out


def gguf_files(folder: Path, limit: int = 64) -> list[Model]:
    """The GGUF models of a folder and its subfolders (the vision projectors left out), by file name."""
    out = []
    try:
        for path in folder.rglob("*.gguf"):
            low = path.name.lower()
            if "mmproj" in low:
                continue
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            out.append(Model(path.stem, size))
            if len(out) >= limit:
                break
    except OSError:
        pass
    return out


# the PC

@dataclass(frozen=True)
class Machine:
    ram_gb: float = 0.0
    vram_gb: float = 0.0        # an NVIDIA card's own memory, 0 when there is none or it is not known
    gpu: str = ""
    unified: bool = False       # Apple's chips: one memory for both

    @property
    def budget_gb(self) -> float:
        """The memory a model may take: the card's, and the RAM less what Windows and the programs open keep
        (a quarter of it, at least 6 GB)."""
        if self.unified:
            return self.ram_gb * 0.7
        return self.vram_gb + max(0.0, self.ram_gb - max(6.0, self.ram_gb * 0.25))


def machine(run=subprocess.run, platform: str | None = None) -> Machine:
    platform = platform or sys.platform
    ram = _ram(platform)
    vram, gpu = 0.0, ""
    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            r = run([smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], capture_output=True,
                    text=True, timeout=4, creationflags=flags)
            line = (r.stdout or "").strip().splitlines()[0] if (r.stdout or "").strip() else ""
            if "," in line:
                gpu, mib = (s.strip() for s in line.rsplit(",", 1))
                vram = float(mib) / 1024.0
        except (OSError, subprocess.SubprocessError, ValueError, IndexError):
            pass
    unified = platform == "darwin" and os.uname().machine == "arm64" if hasattr(os, "uname") else False
    return Machine(ram, vram, gpu, unified)


def _ram(platform: str) -> float:
    try:
        if platform.startswith("win"):
            import ctypes

            class Status(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                            ("avail", ctypes.c_ulonglong), ("page_total", ctypes.c_ulonglong),
                            ("page_avail", ctypes.c_ulonglong), ("virtual_total", ctypes.c_ulonglong),
                            ("virtual_avail", ctypes.c_ulonglong), ("extended", ctypes.c_ulonglong)]
            s = Status()
            s.length = ctypes.sizeof(Status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s)):
                return s.total / 2 ** 30
            return 0.0
        if platform == "darwin":
            r = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=3)
            return int(r.stdout.strip()) / 2 ** 30
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) / 2 ** 20
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        pass
    return 0.0


# the models of October 2026 (study 14a: the sources and the dates)

@dataclass(frozen=True)
class Candidate:
    key: str                    # how it is known
    title: str
    patterns: tuple             # parts of a model's name that say it is this one (folded, «-» for «.:_ »)
    tools: int                  # 1-5: how well it calls tools, for Meridio
    italian: int                # 1-5
    ollama: str = ""            # the tag of Ollama's library
    ollama_gb: float = 0.0      # its download
    gguf: str = ""              # llama-server -hf <this>
    gguf_gb: float = 0.0
    tried: bool = False         # tried with Meridio's tools (study 14, 4.4)

    @property
    def score(self) -> int:
        return 2 * self.tools + self.italian

    def why(self) -> str:
        return candidate_why().get(self.key, "")


def candidate_why() -> dict:
    return {
        "qwen3.6-35b": _("tried with Meridio's tools (study 14): it reads before answering, proposes the fixes and "
                         "does not invent; a mixture of experts with 3 billion parameters at work, quick even on "
                         "the processor"),
        "gemma4-26b": _("the best in Italian of those that fit, and good with tools (Tau2 {score} by Google); not yet "
                        "tried with Meridio").format(score=number(68.2, 1)),
        "gpt-oss-20b": _("mature with tools and quick; weaker in Italian, and its reasoning cannot be turned off "
                         "(Meridiana keeps it low)"),
        "qwen3.5-9b": _("it fits whole in a card of 8 GB, so it is the quickest; good with tools by its makers' "
                        "measures, not yet tried with Meridio"),
        "gemma4-12b": _("small and good in Italian; with tools a step below Qwen3.5-9B"),
        "nemotron-bolt": _("small, Italian among its languages; out on 23/10/2026, still to be tried"),
        "ministral-3": _("speaks Italian, calls tools, never reasons at length; no published measure of its tools"),
        "lfm2.5-24b": _("very quick with tools, but it always reasons before answering"),
        "nemotron-lightning": _("good with tools by NVIDIA's measures; large for what it gives"),
        "qwen3.8-27b": _("strong, but dense: slow without a large card"),
        "gemma4-31b": _("strong, but dense: slow without a large card"),
        "qwen3.5-4b": _("for a PC with little memory: in the trial of study 14 it invented what it did not find"),
        "qwen3": _("the generation before 2026: good with tools, less in Italian"),
        "llama3": _("of 2024: overtaken"),
        "granite4": _("Ollama does not mark it as calling tools"),
    }


CANDIDATES = (
    Candidate("qwen3.6-35b", "Qwen3.6-35B-A3B", ("qwen3-6-35b", "qwen3.6-35b"), 5, 4, "qwen3.6:35b-a3b", 24.0,
              "unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ4_XS", 17.7, tried=True),
    Candidate("gemma4-26b", "Gemma 4 26B-A4B", ("gemma4-26b", "gemma-4-26b", "gemma4:26b"), 4, 5,
              "gemma4:26b-a4b-it-qat", 16.0, "unsloth/gemma-4-26B-A4B-it-GGUF:UD-IQ4_XS", 13.6),
    Candidate("gpt-oss-20b", "gpt-oss-20b", ("gpt-oss-20b", "gpt-oss:20b", "gpt-oss"), 4, 3, "gpt-oss:20b", 14.0,
              "ggml-org/gpt-oss-20b-GGUF", 12.1),
    Candidate("qwen3.5-9b", "Qwen3.5-9B", ("qwen3-5-9b", "qwen3.5-9b", "qwen3.5:9b"), 4, 3, "qwen3.5:9b", 6.6,
              "unsloth/Qwen3.5-9B-GGUF:Q4_K_M", 5.7),
    Candidate("gemma4-12b", "Gemma 4 12B", ("gemma4-12b", "gemma-4-12b", "gemma4:12b"), 3, 4, "gemma4:12b", 7.7,
              "unsloth/gemma-4-12b-it-GGUF:Q4_K_M", 7.1),
    Candidate("nemotron-bolt", "Nemotron 3.5 Bolt E4B", ("nemotron-3-5-bolt", "nemotron-3.5-bolt"), 3, 3,
              "nemotron-3.5-bolt:e4b", 7.2),
    Candidate("ministral-3", "Ministral 3", ("ministral-3",), 3, 3, "ministral-3:14b", 9.1,
              "mistralai/Ministral-3-14B-Instruct-2512-GGUF", 8.2),
    Candidate("lfm2.5-24b", "LFM2.5-24B-A2B", ("lfm2-5-24b", "lfm2.5-24b", "lfm2.5:24b"), 3, 3, "lfm2.5:24b", 15.0,
              "LiquidAI/LFM2.5-24B-A2B-GGUF:Q4_K_M", 14.5),
    Candidate("nemotron-lightning", "Nemotron 3.5 Lightning", ("nemotron-3-5-lightning", "nemotron-3.5-lightning"),
              3, 3, "nemotron-3.5-lightning:30b", 19.0),
    Candidate("qwen3.8-27b", "Qwen3.8-27B", ("qwen3-8-27b", "qwen3.8-27b", "qwen3.8:27b"), 4, 4, "qwen3.8:27b", 18.0),
    Candidate("gemma4-31b", "Gemma 4 31B", ("gemma4-31b", "gemma-4-31b", "gemma4:31b"), 4, 5, "gemma4:31b", 20.0),
    Candidate("qwen3.5-4b", "Qwen3.5-4B", ("qwen3-5-4b", "qwen3.5-4b", "qwen3.5:4b"), 2, 2, "qwen3.5:4b", 3.3,
              "unsloth/Qwen3.5-4B-GGUF:Q4_K_M", 2.7),
    Candidate("qwen3", "Qwen3", ("qwen3-", "qwen3:"), 3, 2),
    Candidate("llama3", "Llama 3", ("llama3", "llama-3"), 2, 2),
    Candidate("granite4", "Granite 4", ("granite4", "granite-4"), 1, 2),
)
# the defaults for a PC without models, from the best to the smallest: the first that fits
DEFAULTS = ("qwen3.6-35b", "gemma4-26b", "qwen3.5-9b", "qwen3.5-4b")


def by_key(key: str) -> Candidate:
    return next(c for c in CANDIDATES if c.key == key)


def _norm(name: str) -> str:
    out = name.lower()
    for ch in ".:_ /":
        out = out.replace(ch, "-")
    return out


def match(name: str) -> Candidate | None:
    """The candidate a model's name is ("qwen3.6:35b-a3b", "Qwen3.6-35B-A3B-UD-IQ4_XS", "unsloth/gemma-4-26B..."),
    the most precise pattern first."""
    low = _norm(name)
    for c in CANDIDATES:
        if any(_norm(p) in low for p in c.patterns):
            return c
    return None


def need_gb(size_gb: float) -> float:
    """The memory a model of `size_gb` on the disk takes with a context of 16.384 tokens: the weights, a tenth more
    for the work buffers, a gigabyte for the context (an estimate: study 14a)."""
    return size_gb * 1.1 + 1.0


@dataclass
class Choice:
    runtime: Runtime
    model: Model
    candidate: Candidate | None
    fits: bool

    def reason(self, pc: Machine) -> str:
        c = self.candidate
        what = c.why() if c is not None else (_("it says it calls tools") if self.model.tools else
                                               _("a model Meridiana does not know yet: try it with «Test»"))
        text = _("{model} on {runtime}: {why}.").format(model=self.model.name, runtime=self.runtime.name, why=what)
        if self.model.size and pc.budget_gb:
            text += " " + (_("It takes about {need} GB; this PC has about {budget} for a model.") if self.fits else
                           _("It takes about {need} GB and this PC has about {budget} for a model: it may be slow "
                             "or not load.")).format(need=number(need_gb(self.model.gb), 0),
                                                     budget=number(pc.budget_gb, 0))
        return text


def choose(runtimes: list[Runtime], pc: Machine) -> Choice | None:
    """The model to use among those of the running servers: tools first, then Italian, the one that fits; a model
    that says it does not call tools is never the choice."""
    best: tuple | None = None
    for rt in runtimes:
        if not rt.running or rt.locked:
            continue
        for m in rt.models:
            if m.tools is False:
                continue
            c = match(m.name)
            score = c.score if c is not None else (4 if m.tools else 2)
            fits = not m.size or not pc.budget_gb or need_gb(m.gb) <= pc.budget_gb
            rank = (fits, score, m.loaded, -m.size)
            if best is None or rank > best[0]:
                best = (rank, Choice(rt, m, c, fits))
    return best[1] if best else None


def suggested(pc: Machine) -> Candidate:
    """The model to download on a PC without one: the first of DEFAULTS that fits, else the smallest (also when the
    memory is not known: the guide asks for it)."""
    if not pc.ram_gb and not pc.vram_gb:
        return by_key(DEFAULTS[-1])
    for key in DEFAULTS:
        c = by_key(key)
        if need_gb(c.ollama_gb) <= pc.budget_gb:
            return c
    return by_key(DEFAULTS[-1])


@dataclass
class Step:
    text: str
    command: str = ""           # what to type, copied by the page's button


def guide(pc: Machine, platform: str | None = None, have_ollama: bool = False) -> tuple[Candidate, list[Step]]:
    """The steps for a PC without local models, with Ollama: one installer (not when Ollama is there already), one
    command for the model, nothing to set in Meridiana (it asks Ollama for the context and turns the reasoning off
    by itself)."""
    platform = platform or sys.platform
    c = suggested(pc)
    if platform.startswith("win"):
        install = Step(_("Install Ollama: the installer from ollama.com/download (about {size} GB, no administrator "
                         "needed), or from the Command Prompt:").format(size=number(1.7, 1)),
                       "winget install Ollama.Ollama")
    elif platform == "darwin":
        install = Step(_("Install Ollama: the app from ollama.com/download."))
    else:
        install = Step(_("Install Ollama, from a terminal (it asks for the password of the administrator):"),
                       "curl -fsSL https://ollama.com/install.sh | sh")
    steps = [] if have_ollama else [install]
    steps += [Step(_("Download the model, about {size} GB (once):").format(size=number(c.ollama_gb, 0)),
                   f"ollama pull {c.ollama}"),
              Step(_("Ollama keeps running by itself. Back here: «Search again», then «Use it» and «Test».")),
              ]
    return c, steps


@dataclass
class Survey:
    """What the survey found: the runtimes (running or on the disk), the PC, the choice among the models found and
    the model to download when there is none."""
    runtimes: list = field(default_factory=list)
    machine: Machine = field(default_factory=Machine)
    choice: Choice | None = None
    seconds: float = 0.0

    @property
    def running(self) -> list[Runtime]:
        return [rt for rt in self.runtimes if rt.running]

    @property
    def idle(self) -> list[Runtime]:
        """Installed, not running."""
        return [rt for rt in self.runtimes if not rt.running]


def survey(ports=None, http=None, extra: tuple = (), disk: bool = True, pc: Machine | None = None) -> Survey:
    """Everything at once, on a worker thread: the servers that answer, the programs on the disk (those not running
    only), the PC, the choice."""
    t = time.perf_counter()
    live = running(ports, http=http, extra=extra)
    kinds = {rt.kind for rt in live}
    for rt in live:
        rt.installed = True
    idle = [rt for rt in installed() if rt.kind not in kinds] if disk else []
    pc = pc if pc is not None else machine()
    out = Survey(live + idle, pc, choose(live, pc))
    out.seconds = time.perf_counter() - t
    return out


# the test

@dataclass
class Check:
    ok: bool
    seconds: float = 0.0
    tools: bool = False         # it answered with a call of the tool
    text: str = ""              # what it wrote, if it wrote instead
    error: str = ""             # the provider's error kind
    detail: str = ""


PING = {"name": "ping", "description": "Answer the test of the connection. Call it, with no arguments.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}


def check(provider, timeout_s: float = 240.0) -> Check:
    """One short question that must come back as a call of the tool `ping`: the server answers, the model is
    there and calls tools as Meridio needs. The first time a server loads the model from the disk: it can take a
    minute."""
    from .providers import ProviderError, Text, ToolCall
    t = time.perf_counter()
    words: list[str] = []
    called = False
    try:
        for event in provider.stream("You are testing a connection. Call the tool ping now; write nothing else.",
                                     [{"role": "user", "content": "Call ping."}], [PING]):
            if isinstance(event, Text):
                words.append(event.text)
            elif isinstance(event, ToolCall) and event.name == "ping":
                called = True
            if time.perf_counter() - t > timeout_s:
                provider.cancel()
                break
    except ProviderError as error:
        return Check(False, time.perf_counter() - t, error=error.kind, detail=error.detail)
    return Check(True, time.perf_counter() - t, called, "".join(words).strip()[:200])


def said(result: Check, model: str) -> str:
    """The test's outcome in words."""
    if not result.ok:
        return {
            "offline": _("Nothing answers at that address: is the server running?"),
            "model": _("The server answers but does not have the model {model}.").format(model=model),
            "tools": _("The model {model} does not call tools: Meridio needs them. Choose another one.").format(
                model=model),
        }.get(result.error, _("The server answered with an error: {detail}").format(
            detail=result.detail or result.error))
    seconds = number(result.seconds, 1)
    if result.tools:
        return _("It works: {model} answered in {s} s and called the tool as Meridio needs.").format(
            model=model, s=seconds)
    return _("{model} answered in {s} s but did not call the tool: Meridio may not read the project with it. A "
             "model of the list above calls tools better.").format(model=model, s=seconds)
