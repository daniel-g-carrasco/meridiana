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
    revision = _revision(path)
    return {"path": str(path), "name": path.stem, "job_id": metadata.get("job_id", ""),
            "job_code": metadata.get("job_code", ""), "job_name": metadata.get("job_name", ""),
            "client_name": metadata.get("client_name", ""), "reserved": bool(metadata.get("reserved", False)),
            "revision": revision, "revision_number": int(revision[1:]) if revision else 0, "error": "", **fingerprint}


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
    """Refresh linked folders and individual files; unchanged fingerprints keep their existing derived rows."""
    known = known or {}
    rows = {}
    for folder, metadata in folders:
        folder = _path(folder)
        try:
            files = (folder,) if folder.suffix.casefold() == ".meridiana" else folder.rglob("*.meridiana")
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


def stored(database: Path) -> list[dict]:
    """Read the derived rows through a connection owned by the calling worker."""
    import sqlite3
    connection = sqlite3.connect(database)
    try:
        rows = connection.execute("SELECT payload FROM project_index ORDER BY path").fetchall()
        return [json.loads(row[0]) for row in rows]
    finally:
        connection.close()


def persist(database: Path, rows: list[dict]) -> None:
    """Replace derived rows in a worker, without the registry's backups or manifest side effects."""
    import sqlite3
    connection = sqlite3.connect(database, isolation_level=None, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM project_index")
        connection.executemany("INSERT INTO project_index(path, payload) VALUES (?, ?)",
                               [(row["path"], json.dumps(row, ensure_ascii=False, sort_keys=True)) for row in rows])
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def search(rows: list[dict], query: str = "", kind: str = "", client: str = "", power_from: float = 0.0,
           power_to: float = float("inf"), since: str = "", reference: dict | None = None,
           max_distance_km: float | None = None) -> list[dict]:
    """Lexical and structured search over the small derived rows, with every word required."""
    if power_from < 0 or power_to < power_from or (max_distance_km is not None and reference is None):
        raise ValueError("the search filters are not valid")
    words = query.casefold().split()
    client = client.casefold()
    out = []
    for row in rows:
        haystack = " ".join(str(row.get(key, "")) for key in
                            ("title", "name", "address", "job_code", "job_name", "client_name", "kind")).casefold()
        power = float(row.get("power_kwp") or 0.0)
        matches = (all(word in haystack for word in words) and (not kind or row.get("kind") == kind)
                   and (not client or client in str(row.get("client_name", "")).casefold())
                   and power_from <= power <= power_to and (not since or _date(row)[:10] >= since)
                   and (max_distance_km is None or _distance(row, reference) <= max_distance_km))
        if matches:
            out.append(row)
    return out


def _date(row: dict) -> str:
    return str(row.get("modified") or row.get("file_modified") or "")


def revisions(rows: list[dict], series_id: str = "") -> list[dict]:
    """The newest readable revision of each series, never a newer damaged file hiding a valid one."""
    series = {}
    for row in rows:
        if row.get("error") or (series_id and row.get("series_id") != series_id):
            continue
        key = row.get("series_id") or row.get("path")
        current = series.get(key)
        candidate = (int(row.get("revision_number") or 0), _date(row))
        if current is None or candidate > (int(current.get("revision_number") or 0), _date(current)):
            series[key] = row
    return sorted(series.values(), key=lambda row: (int(row.get("revision_number") or 0), _date(row)), reverse=True)


def _distance(first: dict, second: dict) -> float:
    import math
    lat1, lon1, lat2, lon2 = (math.radians(float(row.get(key, 0.0)))
                              for row, key in ((first, "lat"), (first, "lon"), (second, "lat"), (second, "lon")))
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def similar(rows: list[dict], reference: dict, power_from: float = 0.5, power_to: float = 2.0,
            client: str = "") -> list[dict]:
    """Compatible series newest first, with the components of similarity made explicit."""
    if not 0 < power_from <= power_to:
        raise ValueError("the power range is not valid")
    out = []
    reference_power = float(reference.get("power_kwp") or 0.0)
    for row in revisions(rows):
        if row.get("series_id") == reference.get("series_id") or row.get("kind") != reference.get("kind"):
            continue
        power = float(row.get("power_kwp") or 0.0)
        if reference_power > 0 and not reference_power * power_from <= power <= reference_power * power_to:
            continue
        if reference_power == 0 and power != 0:
            continue
        if client and client.casefold() not in str(row.get("client_name", "")).casefold():
            continue
        same_mounting = bool(set(row.get("mountings") or []) & set(reference.get("mountings") or []))
        same_tilt = any(abs(a - b) <= 5 for a in (row.get("tilts") or []) for b in (reference.get("tilts") or []))
        distance = _distance(row, reference)
        score = 2 * same_mounting + same_tilt + 1 / (1 + distance / 100)
        out.append({**row, "similarity": round(score, 3), "same_mounting": same_mounting,
                    "same_tilt": same_tilt, "distance_km": round(distance, 1),
                    "reference_power_kwp": reference_power})
    return sorted(out, key=lambda row: (_date(row), row["similarity"]), reverse=True)
