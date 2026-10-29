"""The external resources a project needs, embedded in its file and rebuilt in the cache on arrival."""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
from pathlib import Path

from . import atomic, reports
from .energy import meteo

RESOURCE_LIMIT = 64 << 20


def _encoded(data: bytes) -> str:
    if len(data) > RESOURCE_LIMIT:
        raise ValueError(f"an embedded resource is larger than {RESOURCE_LIMIT >> 20} MB")
    return base64.b64encode(data).decode("ascii")


def _decoded(raw: str) -> bytes:
    if len(raw) > 4 * ((RESOURCE_LIMIT + 2) // 3):
        raise ValueError(f"an embedded resource is larger than {RESOURCE_LIMIT >> 20} MB")
    data = base64.b64decode(raw.encode("ascii"), validate=True)
    if len(data) > RESOURCE_LIMIT:
        raise ValueError(f"an embedded resource is larger than {RESOURCE_LIMIT >> 20} MB")
    return data


def _read_resource(path: Path) -> bytes:
    with path.open("rb") as source:
        data = source.read(RESOURCE_LIMIT + 1)
    if len(data) > RESOURCE_LIMIT:
        raise ValueError(f"an embedded resource is larger than {RESOURCE_LIMIT >> 20} MB")
    return data


def _materialize(cache: Path, name: str, raw: str) -> Path:
    data = _decoded(raw)
    safe = Path(name).name or "resource"
    folder = Path(cache) / "project-resources" / hashlib.sha256(data).hexdigest()[:20]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / safe
    if not path.exists() or path.read_bytes() != data:
        temporary = folder / f".{safe}.tmp"
        temporary.write_bytes(data)
        temporary.replace(path)
    return path


def _embedded_profile(profile: dict | None) -> dict | None:
    clean = reports.clean_profile(profile)
    if clean is None:
        return None
    logo = clean.pop("logo", "")
    if logo:
        path = Path(logo)
        clean["logo_name"] = path.name
        clean["logo_data"] = _encoded(_read_resource(path))
    return clean


def embed(project, path: Path, cache_dir: Path | None = None, report_profile: dict | None = None) -> None:
    """Put the selected report profile, attachment bytes and cached weather into the project itself."""
    resources = copy.deepcopy(getattr(project, "resources", {}) or {})
    project.report = copy.deepcopy(project.report or {})
    existing = {item["path"]: item.get("data") for item in project.report.get("attachments") or []
                if isinstance(item, dict) and isinstance(item.get("path"), str) and isinstance(item.get("data"), str)}
    attachments = []
    for item in reports.clean_attachments(project.report.get("attachments")):
        item = dict(item)
        if existing.get(item["path"]):
            item["data"] = existing[item["path"]]
        if not item.get("data"):
            try:
                item["data"] = _encoded(_read_resource(Path(item["path"])))
            except OSError:
                pass
        attachments.append(item)
    if project.report.get("attachments") is not None:
        project.report["attachments"] = attachments
    if report_profile is not None:
        resources["report_profile"] = _embedded_profile(report_profile)
    if cache_dir is not None:
        weather = dict(getattr(project, "climate", {}) or resources.get("weather") or {})
        typical = meteo._cache_file(Path(cache_dir), "tmy", project.site.lat, project.site.lon)
        if typical.exists():
            weather["tmy"], _notice = atomic.read_json(typical)
        horizon = meteo._cache_file(Path(cache_dir), "horizon", project.site.lat, project.site.lon)
        if horizon.exists():
            weather["horizon"], _notice = atomic.read_json(horizon)
        elif typical.exists():
            weather.pop("horizon", None)
        resources["weather"] = weather
    project.resources = resources


def materialize(project, cache_dir: Path | None) -> list[str]:
    """Rebuild embedded attachments in `cache_dir`; name what has neither bytes nor its original file."""
    problems: list[str] = []
    if cache_dir is None:
        return problems
    for item in (project.report or {}).get("attachments") or []:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            continue
        title = reports.attachment_title(item)
        if item.get("data"):
            try:
                item["path"] = str(_materialize(Path(cache_dir), item["path"], item["data"]))
            except (ValueError, binascii.Error, OSError) as error:
                problems.append(f"{title}: the embedded copy could not be read ({error})")
        elif not Path(item["path"]).is_file():
            problems.append(f"{title}: without an embedded copy; the original file was not found")
    return problems


def profile(project, cache_dir: Path) -> dict | None:
    """The profile embedded in the project, with its logo rebuilt in the cache."""
    raw = (getattr(project, "resources", {}) or {}).get("report_profile")
    profile = reports.clean_profile(raw)
    if profile is None:
        return None
    logo = raw.get("logo_data") if isinstance(raw, dict) else None
    if logo:
        profile["logo"] = str(_materialize(Path(cache_dir), raw.get("logo_name") or "logo.png", logo))
    return profile
