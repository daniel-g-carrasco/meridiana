"""Best-effort local prefill, called only by background workers."""
from threading import Lock
from urllib.parse import urlsplit

from meridiana.app.assistant import local, providers
from meridiana.core.compute.resources import system_memory

_LOCK = Lock()


def prepare(provider, system, specs):
    """Return prepared/loaded/memory/unavailable; never load when free RAM is unknown.

    The server owns residency across processes. The lock coalesces workers within
    this process; the second worker rechecks the server after the first finishes.
    """
    with _LOCK:
        http = local._session(getattr(provider, "session", None))
        base = provider.base_url.rstrip("/")
        if isinstance(provider, providers.Ollama):
            status, ps = local._get(http, base + "/api/ps")
            if status != 200:
                return "unavailable"
            if any(m.get("name") == provider.model for m in local._items(ps, "models")):
                return "loaded"
            status, tags = local._get(http, base + "/api/tags")
            models = local._items(tags, "models") if status == 200 else []
            size = next((m.get("size", 0) / local.GB for m in models
                         if m.get("name") == provider.model), 0)
        else:
            root = base.removesuffix("/v1")
            rt = local.identify(root, urlsplit(root).port or 0, http)
            model = next((m for m in rt.models if m.name == provider.model), None) if rt else None
            if model and model.loaded:
                return "loaded"
            size = model.gb if model else 0
        memory = system_memory()
        if not size or memory is None or local.need_gb(size) > memory[1] / local.GB:
            return "memory"
        if isinstance(provider, providers.Ollama):
            body = provider.request(system, [], specs, provider._think(http), predict=1)
            response = http.post(base + "/api/chat", json=body, stream=True,
                                 timeout=(providers.LOCAL_CONNECT_S, providers.LOCAL_READ_S))
            try:
                if response.status_code != 200:
                    raise providers._http_error(response.status_code, providers._body_text(response))
                # Consume the stream to finish evaluating the fixed prefix; no answer reaches the view.
                list(provider._read_lines(response))
            finally:
                response.close()
        else:
            from dataclasses import replace
            list(replace(provider, max_tokens=1).stream(system, [], specs))
        return "prepared"
