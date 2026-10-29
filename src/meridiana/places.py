"""Offline place suggestions: ISTAT municipalities and sites read from recent Meridiana projects."""

from __future__ import annotations

import gzip
import json
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import log, paths


@dataclass(frozen=True)
class PlaceSuggestion:
    name: str
    province: str
    region: str
    lat: float
    lon: float
    code: str = ""
    source: str = "ISTAT"

    @property
    def display(self) -> str:
        return ", ".join(part for part in (self.name, self.province) if part)


@lru_cache(maxsize=1)
def municipalities() -> tuple[PlaceSuggestion, ...]:
    source = paths.shipped("istat", "comuni-2026-02-21.json.gz")
    if source is None:
        return ()
    with gzip.open(source, "rt", encoding="utf-8") as stream:
        rows = json.load(stream)
    return tuple(PlaceSuggestion(**row) for row in rows)


def recent(files: list[str]) -> list[PlaceSuggestion]:
    from . import model
    found = []
    for name in files:
        path = Path(name)
        if not path.is_file():
            continue
        try:
            project, _notice = model.Project.load(path)
        except (OSError, ValueError) as error:
            log.complain(f"recent project place: {path.name}", error)
            continue
        found.append(PlaceSuggestion(project.name, "", "", project.site.lat, project.site.lon,
                                     source="project"))
    return found


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).casefold().encode("ascii", "ignore").decode()


def search(text: str, choices, limit: int = 8) -> list[PlaceSuggestion]:
    words = _fold(text.replace(",", " ").strip()).split()
    if len(" ".join(words)) < 2:
        return []
    text = " ".join(words)
    ranked = []
    for choice in choices:
        name = _fold(choice.name)
        where = f"{name} {_fold(choice.province)} {_fold(choice.region)}"
        if not all(word in where for word in words):
            continue
        score = (0 if choice.source == "project" else 1, 0 if name.startswith(text) else 1,
                 name.find(text) if text in name else 999, name)
        ranked.append((score, choice))
    ranked.sort(key=lambda pair: pair[0])
    return [choice for _score, choice in ranked[:limit]]
