"""The local SQLite registry of clients, jobs, project series and their folders (R150)."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
import uuid
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import atomic

SCHEMA_VERSION = 2
EXCHANGE_VERSION = 1
MANIFEST_NAME = ".meridiana-commessa.json"
STATUSES = ("waiting", "in_progress", "delivered", "archived")
PHASES = ("preliminary", "definitive", "executive", "construction")

_SCHEMA = """
CREATE TABLE clients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'other',
    contacts TEXT NOT NULL DEFAULT '{}',
    notes TEXT NOT NULL DEFAULT '',
    archived INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    client_id TEXT NOT NULL REFERENCES clients(id),
    status TEXT NOT NULL,
    phase TEXT NOT NULL,
    reserved INTEGER NOT NULL DEFAULT 0,
    due TEXT NOT NULL DEFAULT '',
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON UPDATE CASCADE,
    path TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    modified TEXT NOT NULL,
    revision TEXT NOT NULL DEFAULT ''
);
CREATE TABLE folders (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON UPDATE CASCADE,
    path TEXT NOT NULL UNIQUE,
    manifest_consent INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);
CREATE INDEX jobs_client ON jobs(client_id);
CREATE INDEX projects_job ON projects(job_id);
CREATE INDEX folders_job ON folders(job_id);
"""

_INDEX_SCHEMA = """
CREATE TABLE project_index (
    path TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);
"""


class RegistryError(ValueError):
    """A registry write or schema cannot be accepted."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _path(path) -> str:
    return str(Path(path).expanduser().absolute())


class Registry:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.manifest_errors: dict[str, tuple[str, str]] = {}
        self.backup_path = self.path.with_name(self.path.name + ".bak")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, isolation_level=None, timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = FULL")
        try:
            self._migrate()
            self.backup()
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def _migrate(self) -> None:
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RegistryError(f"registry schema {version} is newer than {SCHEMA_VERSION}")
        if version == 0:
            tables = self.connection.execute("SELECT count(*) FROM sqlite_master WHERE type = 'table'").fetchone()[0]
            if tables:
                raise RegistryError("an unversioned registry is not empty; no safe migration is known")
        migrations = {0: _SCHEMA, 1: _INDEX_SCHEMA}
        while version < SCHEMA_VERSION:
            script = migrations.get(version)
            if script is None:
                raise RegistryError(f"no migration from registry schema {version}")
            self.connection.executescript(
                f"BEGIN IMMEDIATE;\n{script}\nPRAGMA user_version = {version + 1};\nCOMMIT;")
            version += 1

    @contextmanager
    def _write(self):
        manifests = self._manifest_states()
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()
            self.backup()
            self._sync_manifests(manifests)

    def backup(self, destination: Path | None = None) -> Path:
        """A consistent SQLite backup, written whole or not at all."""
        target = Path(destination) if destination is not None else self.backup_path
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        os.close(fd)
        try:
            with closing(sqlite3.connect(temporary)) as backup:
                self.connection.backup(backup)
                backup.commit()
            with open(temporary, "rb") as file:
                os.fsync(file.fileno())
            os.replace(temporary, target)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
        return target

    @staticmethod
    def _client_row(row) -> dict:
        out = dict(row)
        out["contacts"] = json.loads(out["contacts"])
        out["archived"] = bool(out["archived"])
        return out

    @staticmethod
    def _job_row(row) -> dict:
        return {**dict(row), "reserved": bool(row["reserved"])}

    @staticmethod
    def _folder_row(row) -> dict:
        return {**dict(row), "manifest_consent": bool(row["manifest_consent"])}

    def create_client(self, name: str, kind: str = "other", contacts: dict | None = None,
                      notes: str = "", client_id: str | None = None) -> dict:
        name = name.strip()
        if not name:
            raise RegistryError("a client needs a name")
        now, cid = _now(), client_id or uuid.uuid4().hex
        try:
            with self._write() as connection:
                connection.execute(
                    "INSERT INTO clients(id, name, kind, contacts, notes, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (cid, name, kind, json.dumps(contacts or {}, ensure_ascii=False), notes, now, now))
        except sqlite3.IntegrityError as error:
            raise RegistryError(str(error)) from error
        return self.client(cid)

    def client(self, client_id: str) -> dict | None:
        row = self.connection.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        return self._client_row(row) if row is not None else None

    def list_clients(self, search: str = "", include_archived: bool = False) -> list[dict]:
        rows = self.connection.execute("SELECT * FROM clients ORDER BY name COLLATE NOCASE, id").fetchall()
        words = search.casefold().split()
        return [self._client_row(row) for row in rows
                if (include_archived or not row["archived"])
                and all(word in f"{row['name']} {row['notes']}".casefold() for word in words)]

    def update_client(self, client_id: str, **changes) -> dict:
        allowed = {"name", "kind", "notes", "archived"}
        fields = {key: value for key, value in changes.items() if key in allowed}
        if "name" in fields and not str(fields["name"]).strip():
            raise RegistryError("a client needs a name")
        if "contacts" in changes:
            fields["contacts"] = json.dumps(changes["contacts"], ensure_ascii=False)
        if not fields:
            return self.client(client_id)
        fields["updated"] = _now()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        with self._write() as connection:
            cursor = connection.execute(f"UPDATE clients SET {assignments} WHERE id = ?", (*fields.values(), client_id))
        if cursor.rowcount == 0:
            raise RegistryError("client not found")
        return self.client(client_id)

    def archive_client(self, client_id: str) -> dict:
        return self.update_client(client_id, archived=True)

    def delete_client(self, client_id: str) -> None:
        if self.connection.execute("SELECT count(*) FROM jobs WHERE client_id = ?", (client_id,)).fetchone()[0]:
            raise RegistryError("a client with jobs is archived, not deleted")
        with self._write() as connection:
            connection.execute("DELETE FROM clients WHERE id = ?", (client_id,))

    def create_job(self, code: str, name: str, client_id: str, status: str = "waiting",
                   phase: str = "preliminary", reserved: bool = False, due: str = "",
                   job_id: str | None = None) -> dict:
        code, name = code.strip(), name.strip()
        if not re.fullmatch(r"\d{5}", code):
            raise RegistryError("a job code is five digits")
        if not name:
            raise RegistryError("a job needs a name")
        if status not in STATUSES or phase not in PHASES:
            raise RegistryError("unknown job status or phase")
        now, jid = _now(), job_id or uuid.uuid4().hex
        try:
            with self._write() as connection:
                connection.execute(
                    "INSERT INTO jobs(id, code, name, client_id, status, phase, reserved, due, created, updated) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (jid, code, name, client_id, status, phase, int(reserved), due, now, now))
        except sqlite3.IntegrityError as error:
            raise RegistryError(str(error)) from error
        return self.job(jid)

    def job(self, job_id: str) -> dict | None:
        row = self.connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._job_row(row) if row is not None else None

    def list_jobs(self, search: str = "", client_id: str = "", include_archived: bool = False) -> list[dict]:
        rows = self.connection.execute(
            "SELECT jobs.*, clients.name AS client_name FROM jobs JOIN clients ON clients.id = jobs.client_id "
            "ORDER BY jobs.code, jobs.id").fetchall()
        words = search.casefold().split()
        return [self._job_row(row) for row in rows
                if (include_archived or row["status"] != "archived") and (not client_id or row["client_id"] == client_id)
                and all(word in f"{row['code']} {row['name']} {row['client_name']}".casefold() for word in words)]

    def update_job(self, job_id: str, **changes) -> dict:
        allowed = {"code", "name", "client_id", "status", "phase", "reserved", "due"}
        fields = {key: value for key, value in changes.items() if key in allowed}
        if "code" in fields and not re.fullmatch(r"\d{5}", str(fields["code"])):
            raise RegistryError("a job code is five digits")
        if "name" in fields and not str(fields["name"]).strip():
            raise RegistryError("a job needs a name")
        if fields.get("status") is not None and fields["status"] not in STATUSES:
            raise RegistryError("unknown job status")
        if fields.get("phase") is not None and fields["phase"] not in PHASES:
            raise RegistryError("unknown job phase")
        if not fields:
            return self.job(job_id)
        fields["updated"] = _now()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        try:
            with self._write() as connection:
                cursor = connection.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", (*fields.values(), job_id))
                if fields.get("reserved"):
                    connection.execute("UPDATE folders SET manifest_consent = 0 WHERE job_id = ?", (job_id,))
        except sqlite3.IntegrityError as error:
            raise RegistryError(str(error)) from error
        if cursor.rowcount == 0:
            raise RegistryError("job not found")
        return self.job(job_id)

    def link_project(self, job_id: str, path: Path, title: str, project_id: str | None = None,
                     revision: str = "") -> dict:
        pid, now = project_id or uuid.uuid4().hex, _now()
        try:
            with self._write() as connection:
                connection.execute(
                    "INSERT INTO projects(id, job_id, path, title, modified, revision) VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET job_id = excluded.job_id, path = excluded.path, "
                    "title = excluded.title, modified = excluded.modified, revision = excluded.revision",
                    (pid, job_id, _path(path), title, now, revision))
        except sqlite3.IntegrityError as error:
            raise RegistryError(str(error)) from error
        return dict(self.connection.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone())

    def list_projects(self, job_id: str = "") -> list[dict]:
        rows = self.connection.execute("SELECT * FROM projects ORDER BY modified DESC, title COLLATE NOCASE").fetchall()
        return [dict(row) for row in rows if not job_id or row["job_id"] == job_id]

    def project_at(self, path: Path) -> dict | None:
        row = self.connection.execute("SELECT * FROM projects WHERE path = ?", (_path(path),)).fetchone()
        return dict(row) if row is not None else None

    def unlink_project(self, project_id: str) -> None:
        with self._write() as connection:
            connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    def replace_index(self, rows: list[dict]) -> None:
        """Replace the derived index atomically; the project files remain the source of its contents."""
        with self._write() as connection:
            connection.execute("DELETE FROM project_index")
            connection.executemany(
                "INSERT INTO project_index(path, payload) VALUES (?, ?)",
                [(row["path"], json.dumps(row, ensure_ascii=False, sort_keys=True)) for row in rows])

    def list_index(self) -> list[dict]:
        rows = self.connection.execute("SELECT payload FROM project_index ORDER BY path").fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def link_folder(self, job_id: str, path: Path) -> dict:
        fid, now, folder = uuid.uuid4().hex, _now(), _path(path)
        existing = self.connection.execute("SELECT * FROM folders WHERE path = ?", (folder,)).fetchone()
        if existing is not None:
            if existing["job_id"] != job_id:
                raise RegistryError("the folder is already linked to another job")
            return self._folder_row(existing)
        try:
            with self._write() as connection:
                connection.execute("INSERT INTO folders(id, job_id, path, created, updated) VALUES (?, ?, ?, ?, ?)",
                                   (fid, job_id, folder, now, now))
        except sqlite3.IntegrityError as error:
            raise RegistryError(str(error)) from error
        return self._folder_row(self.connection.execute("SELECT * FROM folders WHERE id = ?", (fid,)).fetchone())

    def list_folders(self, job_id: str = "") -> list[dict]:
        rows = self.connection.execute("SELECT * FROM folders ORDER BY path").fetchall()
        return [self._folder_row(row) for row in rows if not job_id or row["job_id"] == job_id]

    def set_manifest_consent(self, folder_id: str, allowed: bool) -> dict:
        row = self.connection.execute(
            "SELECT folders.*, jobs.reserved FROM folders JOIN jobs ON jobs.id = folders.job_id WHERE folders.id = ?",
            (folder_id,)).fetchone()
        if row is None:
            raise RegistryError("folder not found")
        if allowed and row["reserved"]:
            raise RegistryError("a reserved job never writes a folder manifest")
        with self._write() as connection:
            connection.execute("UPDATE folders SET manifest_consent = ?, updated = ? WHERE id = ?",
                               (int(allowed), _now(), folder_id))
        return self._folder_row(self.connection.execute("SELECT * FROM folders WHERE id = ?", (folder_id,)).fetchone())

    def _manifest_states(self) -> dict[str, tuple[bool, str]]:
        rows = self.connection.execute(
            "SELECT folders.id, folders.path, folders.manifest_consent, jobs.reserved FROM folders "
            "JOIN jobs ON jobs.id = folders.job_id").fetchall()
        return {row["id"]: (bool(row["manifest_consent"] and not row["reserved"]), row["path"]) for row in rows}

    def _sync_manifests(self, before: dict[str, tuple[bool, str]]) -> None:
        after = self._manifest_states()
        for folder_id in sorted(before.keys() | after.keys()):
            allowed, folder = after.get(folder_id, (False, ""))
            if allowed:
                try:
                    self.write_manifest(folder_id)
                except OSError as error:
                    self.manifest_errors[folder_id] = (folder, str(error))
                else:
                    self.manifest_errors.pop(folder_id, None)
            elif before.get(folder_id, (False, ""))[0] or folder_id in self.manifest_errors:
                previous = before.get(folder_id, (False, ""))[1]
                failed = self.manifest_errors.get(folder_id, ("", ""))[0]
                try:
                    self.remove_manifest(folder_id, previous or failed or folder)
                except OSError as error:
                    self.manifest_errors[folder_id] = (previous or failed or folder, str(error))
                else:
                    self.manifest_errors.pop(folder_id, None)

    def write_manifest(self, folder_id: str) -> Path:
        row = self.connection.execute(
            "SELECT folders.path, folders.manifest_consent, jobs.* FROM folders "
            "JOIN jobs ON jobs.id = folders.job_id WHERE folders.id = ?", (folder_id,)).fetchone()
        if row is None:
            raise RegistryError("folder not found")
        if row["reserved"]:
            raise RegistryError("a reserved job never writes a folder manifest")
        if not row["manifest_consent"]:
            raise RegistryError("the folder has not consented to a job manifest")
        target = Path(row["path"]) / MANIFEST_NAME
        job = {key: row[key] for key in ("id", "code", "name", "phase")}
        data = {"format": "meridiana-job-manifest", "version": EXCHANGE_VERSION,
                "job": job, "projects": self.list_projects(job["id"])}
        atomic.write_json(target, data)
        return target

    def remove_manifest(self, folder_id: str, folder: str | Path | None = None) -> None:
        if folder is None:
            row = self.connection.execute("SELECT path FROM folders WHERE id = ?", (folder_id,)).fetchone()
            if row is None:
                return
            folder = row["path"]
        target = Path(folder) / MANIFEST_NAME
        target.unlink(missing_ok=True)
        target.with_name(target.name + ".bak").unlink(missing_ok=True)

    def export_data(self) -> dict:
        jobs = [{key: value for key, value in row.items() if key != "client_name"}
                for row in self.list_jobs(include_archived=True)]
        folders = [{**row, "manifest_consent": False} for row in self.list_folders()]
        return {"format": "meridiana-registry", "version": EXCHANGE_VERSION,
                "clients": self.list_clients(include_archived=True), "jobs": jobs,
                "projects": self.list_projects(), "folders": folders}

    def export(self, path: Path) -> Path:
        target = Path(path)
        atomic.write_json(target, self.export_data())
        return target

    def preview_import(self, data: dict) -> dict:
        _validate_exchange(data)
        current = self.export_data()
        preview = {"new": 0, "updated": 0, "unchanged": 0, "conflicts": []}
        for kind in ("clients", "jobs", "projects", "folders"):
            existing = {row["id"]: row for row in current[kind]}
            seen = set()
            for row in data[kind]:
                record_id = row.get("id", "") if isinstance(row, dict) else ""
                if not isinstance(record_id, str) or not record_id:
                    raise RegistryError(f"an imported {kind} record has no stable id")
                if record_id in seen:
                    preview["conflicts"].append(f"duplicate imported id: {record_id}")
                seen.add(record_id)
                if record_id not in existing:
                    preview["new"] += 1
                elif existing[record_id] == row:
                    preview["unchanged"] += 1
                else:
                    preview["updated"] += 1
        for kind, key in (("jobs", "code"), ("projects", "path"), ("folders", "path")):
            existing = {row[key]: row["id"] for row in current[kind]}
            imported = {}
            for row in data[kind]:
                value, record_id = row.get(key), row["id"]
                if value in imported and imported[value] != record_id:
                    preview["conflicts"].append(f"duplicate imported {kind} {key}: {value}")
                imported[value] = record_id
                if value in existing and existing[value] != record_id:
                    preview["conflicts"].append(f"conflicting {kind} {key}: {value}")
        return preview

    def import_data(self, data: dict) -> dict:
        preview = self.preview_import(data)
        if preview["conflicts"]:
            raise RegistryError("the registry import has conflicts; nothing was imported")
        now = _now()
        try:
            with self._write() as connection:
                for row in data["clients"]:
                    name = str(row.get("name", "")).strip()
                    contacts = row.get("contacts", {})
                    if not name or not isinstance(contacts, dict):
                        raise RegistryError("an imported client is not valid")
                    connection.execute(
                        "INSERT INTO clients(id, name, kind, contacts, notes, archived, created, updated) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET name = excluded.name, "
                        "kind = excluded.kind, contacts = excluded.contacts, notes = excluded.notes, "
                        "archived = excluded.archived, created = excluded.created, updated = excluded.updated",
                        (row["id"], name, row.get("kind", "other"), json.dumps(contacts, ensure_ascii=False),
                         row.get("notes", ""), int(bool(row.get("archived", False))),
                         row.get("created", now), row.get("updated", now)))
                for row in data["jobs"]:
                    code, name = str(row.get("code", "")).strip(), str(row.get("name", "")).strip()
                    status, phase = row.get("status"), row.get("phase")
                    if not re.fullmatch(r"\d{5}", code) or not name or status not in STATUSES or phase not in PHASES:
                        raise RegistryError("an imported job is not valid")
                    connection.execute(
                        "INSERT INTO jobs(id, code, name, client_id, status, phase, reserved, due, created, updated) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET code = excluded.code, "
                        "name = excluded.name, client_id = excluded.client_id, status = excluded.status, "
                        "phase = excluded.phase, reserved = excluded.reserved, due = excluded.due, "
                        "created = excluded.created, updated = excluded.updated",
                        (row["id"], code, name, row["client_id"], status, phase,
                         int(bool(row.get("reserved", False))), row.get("due", ""),
                         row.get("created", now), row.get("updated", now)))
                for row in data["projects"]:
                    connection.execute(
                        "INSERT INTO projects(id, job_id, path, title, modified, revision) VALUES (?, ?, ?, ?, ?, ?) "
                        "ON CONFLICT(id) DO UPDATE SET job_id = excluded.job_id, path = excluded.path, "
                        "title = excluded.title, modified = excluded.modified, revision = excluded.revision",
                        (row["id"], row["job_id"], _path(row["path"]), row.get("title", ""),
                         row.get("modified", now), row.get("revision", "")))
                for row in data["folders"]:
                    reserved = connection.execute("SELECT reserved FROM jobs WHERE id = ?", (row["job_id"],)).fetchone()
                    local = connection.execute("SELECT job_id, path, manifest_consent FROM folders WHERE id = ?",
                                               (row["id"],)).fetchone()
                    same_folder = bool(local and local["job_id"] == row["job_id"]
                                       and local["path"] == _path(row["path"]))
                    consent = bool(local and local["manifest_consent"] and same_folder) and not bool(reserved["reserved"])
                    connection.execute(
                        "INSERT INTO folders(id, job_id, path, manifest_consent, created, updated) "
                        "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET job_id = excluded.job_id, "
                        "path = excluded.path, manifest_consent = excluded.manifest_consent, "
                        "created = excluded.created, updated = excluded.updated",
                        (row["id"], row["job_id"], _path(row["path"]), int(consent),
                         row.get("created", now), row.get("updated", now)))
        except (KeyError, TypeError, sqlite3.Error) as error:
            raise RegistryError(f"the registry import is not valid: {error}") from error
        return preview


def _validate_records(data: dict) -> None:
    strings = {
        "clients": ("id", "name", "kind", "notes", "created", "updated"),
        "jobs": ("id", "code", "name", "client_id", "status", "phase", "due", "created", "updated"),
        "projects": ("id", "job_id", "path", "title", "modified", "revision"),
        "folders": ("id", "job_id", "path", "created", "updated"),
    }
    required = {"clients": ("id", "name"), "jobs": ("id", "code", "name", "client_id", "status", "phase"),
                "projects": ("id", "job_id", "path", "title"), "folders": ("id", "job_id", "path")}
    booleans = {"clients": ("archived",), "jobs": ("reserved",), "folders": ("manifest_consent",)}
    for kind in ("clients", "jobs", "projects", "folders"):
        for row in data[kind]:
            if not isinstance(row, dict) or any(field not in row for field in required[kind]):
                raise RegistryError(f"an imported {kind} record is not valid")
            for field in strings[kind]:
                if field in row and type(row[field]) is not str:
                    raise RegistryError(f"an imported {kind} {field} is not text")
            for field in booleans.get(kind, ()):
                if field in row and type(row[field]) is not bool:
                    raise RegistryError(f"an imported {kind} {field} is not a boolean")
            if not row["id"] or any(field in row and row[field] is None for field in strings[kind]):
                raise RegistryError(f"an imported {kind} record is not valid")
            if kind == "clients" and (not row["name"].strip() or
                                      ("contacts" in row and not isinstance(row["contacts"], dict))):
                raise RegistryError("an imported client is not valid")
            if kind == "jobs" and (not re.fullmatch(r"\d{5}", row["code"]) or not row["name"].strip()
                                   or row["status"] not in STATUSES or row["phase"] not in PHASES):
                raise RegistryError("an imported job is not valid")


def _validate_exchange(data: dict, manifest: bool = False) -> None:
    expected = "meridiana-job-manifest" if manifest else "meridiana-registry"
    if not isinstance(data, dict) or data.get("format") != expected:
        raise RegistryError("the file is not a Meridiana registry exchange")
    if data.get("version") != EXCHANGE_VERSION:
        raise RegistryError("the registry exchange version is not supported")
    if manifest:
        if not isinstance(data.get("job"), dict) or not isinstance(data.get("projects"), list):
            raise RegistryError("the job manifest is not valid")
        return
    if any(not isinstance(data.get(kind), list) for kind in ("clients", "jobs", "projects", "folders")):
        raise RegistryError("the registry exchange is not valid")
    _validate_records(data)


def read_exchange(path: Path, manifest: bool = False) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RegistryError(f"the exchange file could not be read: {error}") from error
    _validate_exchange(data, manifest=manifest)
    return data
