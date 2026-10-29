"""The derived, local index of the projects in folders linked to the registry (R151)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import model

_REVISION = re.compile(r"_R(\d+)$", re.IGNORECASE)


def _path(path: Path) -> Path:
    return Path(path).expanduser().absolute()


def _fingerprint(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    stat = path.stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": digest.hexdigest(),
            "file_modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds")}


def _revision(path: Path) -> str:
    found = _REVISION.search(path.stem)
    return f"R{int(found.group(1)):02d}" if found else ""


def _base(path: Path, fingerprint: dict, metadata: dict | None = None) -> dict:
    metadata = metadata or {}
    return {"path": str(path), "name": path.stem, "job_id": metadata.get("job_id", ""),
            "job_code": metadata.get("job_code", ""), "job_name": metadata.get("job_name", ""),
            "client_name": metadata.get("client_name", ""), "reserved": bool(metadata.get("reserved", False)),
            "revision": _revision(path), "error": "", **fingerprint}


def _power(project: model.Project) -> float:
    if not any(sf.filled for sf in project.subfields):
        return 0.0
    from .energy import system
    total = 0.0
    for sf in project.subfields:
        if not sf.filled:
            continue
        try:
            result = project.fill(sf, shade=system.shadow_exclusions)
        except (ValueError, TypeError, KeyError, IndexError):
            continue
        module = project.modules.get(sf.module) or {}
        total += result.count * float(module.get("power_kw") or 0.0)
    return round(total, 3)


def read(path: Path, metadata: dict | None = None) -> dict:
    """Read only the searchable facts of one project, never its embedded resources or report."""
    path = _path(path)
    fingerprint = _fingerprint(path)
    row = _base(path, fingerprint, metadata)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        return {**row, "error": f"JSON could not be read: {error}"}
    try:
        project = model.Project.from_json(data)
    except (ValueError, TypeError, KeyError, IndexError) as error:
        return {**row, "error": f"Project data could not be read: {error}"}
    base = _REVISION.sub("", path.stem)
    series_inferred = not project.series_id
    roof = any(sf.building for sf in project.subfields)
    ground = any(not sf.building for sf in project.subfields)
    kind = "mixed" if roof and ground else "roof" if roof or project.buildings else "ground"
    mountings, tilts = set(), set()
    for sf in project.subfields:
        params = sf.layout_params()
        mountings.add(params.mounting)
        tilts.add(round(project.surface_of(sf).tilt if params.mounting == "coplanar" else params.tilt, 3))
    row.update({"title": project.name, "series_id": project.series_id or str(path.parent / base),
                "series_inferred": series_inferred, "address": project.site.address,
                "lat": round(project.site.lat, 6), "lon": round(project.site.lon, 6),
                "created": project.created, "modified": project.modified, "kind": kind,
                "power_kwp": _power(project), "buildings": len(project.buildings), "subfields": len(project.subfields),
                "mountings": sorted(mountings), "tilts": sorted(tilts), "project_reserved": project.reserved,
                "reserved": bool(row["reserved"] or project.reserved)})
    return row


def scan(folders, known: dict | None = None) -> list[dict]:
    """Refresh the files of the linked folders; an unchanged fingerprint keeps its existing derived row."""
    known = known or {}
    rows = {}
    for folder, metadata in folders:
        folder = _path(folder)
        try:
            files = folder.rglob("*.meridiana")
            for path in files:
                path = _path(path)
                try:
                    fingerprint = _fingerprint(path)
                except OSError as error:
                    rows[str(path)] = {**_base(path, {}, metadata), "error": f"File could not be read: {error}"}
                    continue
                previous = known.get(str(path))
                if previous and all(previous.get(key) == fingerprint[key] for key in ("size", "mtime_ns", "sha256")):
                    administrative = {key: metadata.get(key, "") for key in
                                      ("job_id", "job_code", "job_name", "client_name", "reserved")}
                    project_reserved = previous.get("project_reserved", previous.get("reserved", False))
                    rows[str(path)] = {**previous, **administrative,
                                       "reserved": bool(project_reserved or administrative["reserved"])}
                else:
                    rows[str(path)] = read(path, metadata)
        except OSError as error:
            rows[str(folder)] = {**_base(folder, {}, metadata), "error": f"Folder could not be scanned: {error}"}
    return [rows[path] for path in sorted(rows)]
