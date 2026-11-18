"""Finding a site by its address with OpenStreetMap's Nominatim: the request, the answer read, the policy
(at most one request a second, as its usage policy asks; Italy only, the scope of the program). No network
here: the dialog (ui/site_dialog.py) sends the request with Qt and gives the bytes back."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.parse import urlencode

NOMINATIM = "https://nominatim.openstreetmap.org/search"
MIN_INTERVAL = 1.0              # seconds between two requests
LIMIT = 8                       # places asked for


@dataclass
class Place:
    name: str
    lat: float
    lon: float


def search_url(text: str, limit: int = LIMIT, countrycodes: str = "it") -> str:
    """The URL of a search of `text`, as Nominatim's API wants it (format jsonv2)."""
    return NOMINATIM + "?" + urlencode({"q": text, "format": "jsonv2", "limit": str(limit), "countrycodes": countrycodes})


def places(payload: bytes) -> list[Place]:
    """The places of an answer; ValueError when the answer is not what Nominatim gives (not JSON, not a list,
    a place without coordinates)."""
    try:
        found = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError(f"not JSON: {error}") from None
    if not isinstance(found, list):
        raise ValueError("not a list of places")
    out = []
    for p in found:
        if not isinstance(p, dict):
            raise ValueError("a place that is not a table")
        try:
            out.append(Place(str(p.get("display_name", "")), float(p["lat"]), float(p["lon"])))
        except (KeyError, TypeError, ValueError):
            raise ValueError("a place without coordinates") from None
    return out


class Throttle:
    """One request every MIN_INTERVAL seconds: `allow()` says whether a request may go now and, if so, counts it."""

    def __init__(self, interval: float = MIN_INTERVAL):
        self.interval = interval
        self.last = -interval

    def allow(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        if now - self.last < self.interval:
            return False
        self.last = now
        return True
