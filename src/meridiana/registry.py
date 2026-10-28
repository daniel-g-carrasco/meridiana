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

SCHEMA_VERSION = 1
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


class RegistryError(ValueError):
    """A registry write or schema cannot be accepted."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _path(path) -> str:
    return str(Path(path).expanduser().absolute())


class Registry:
    def __init__(self, path: Path):
        self.path = Path(path)
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
        migrations = {0: _SCHEMA}
        while version < SCHEMA_VERSION:
            script = migrations.get(version)
            if script is None:
                raise RegistryError(f"no migration from registry schema {version}")
            self.connection.executescript(
                f"BEGIN IMMEDIATE;\n{script}\nPRAGMA user_version = {version + 1};\nCOMMIT;")
            version += 1

    @contextmanager
    def _write(self):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()
            self.backup()

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
