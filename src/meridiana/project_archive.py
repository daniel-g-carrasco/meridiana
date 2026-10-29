"""The .mer envelope: JSON metadata and bounded, content-addressed binary resources.

The logical project schema stays independent of this container. Only the three known binary fields are
replaced by references on disk, and they become their original base64 strings again on a full read.
Metadata reads validate the structure and JSON digest, not the bytes of the assets: opening the project
always performs that last check. Nothing is extracted using a path supplied by an archive.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import os
import re
import shutil
import stat
import struct
import tempfile
import zipfile
import zlib
from pathlib import Path

from . import APP_NAME, __version__

MIMETYPE = b"application/x-meridiana-project+zip"
CONTAINER_VERSION = 1
RESOURCE_LIMIT = 64 << 20
JSON_LIMIT = 32 << 20
MANIFEST_LIMIT = 2 << 20
TOTAL_LIMIT = 512 << 20
ENTRY_LIMIT = 10_000
DEPTH_LIMIT = 64
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class FutureVersionError(ValueError):
    """A newer document must not be mistaken for a corrupt one and replaced by its backup."""


def _binary_fields(data):
    """Yield mutable containers and keys only for fields owned by the project format."""
    underlays = data.get("underlays") or []
    if not isinstance(underlays, list):
        raise ValueError("underlays: expected a list")
    for item in underlays:
        if isinstance(item, dict) and "image" in item:
            yield item, "image"
    report = data.get("report")
    if isinstance(report, dict):
        attachments = report.get("attachments") or []
        if not isinstance(attachments, list):
            raise ValueError("attachments: expected a list")
        for item in attachments:
            if isinstance(item, dict) and "data" in item:
                yield item, "data"
    resources = data.get("resources")
    profile = resources.get("report_profile") if isinstance(resources, dict) else None
    if isinstance(profile, dict) and "logo_data" in profile:
        yield profile, "logo_data"


def _depth(data):
    pending = [(data, 0)]
    while pending:
        item, level = pending.pop()
        if level > DEPTH_LIMIT:
            raise ValueError("project JSON exceeds the nesting limit")
        if isinstance(item, dict):
            pending.extend((value, level + 1) for value in item.values())
        elif isinstance(item, list):
            pending.extend((value, level + 1) for value in item)
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError("non-finite JSON number")


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f"non-finite JSON number: {value}")


def _json(raw):
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
        _depth(data)
    except (RecursionError, UnicodeError) as error:
        raise ValueError("invalid project JSON") from error
    if not isinstance(data, dict):
        raise ValueError("project metadata must be an object")
    return data


def _json_bytes(data, limit):
    _depth(data)
    out = bytearray()
    for part in json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(",", ":")).iterencode(data):
        out.extend(part.encode("utf-8"))
        if len(out) > limit:
            raise ValueError("project JSON exceeds the size limit")
    return bytes(out)


def _descriptor(data):
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _pack(data):
    _depth(data)
    packed = copy.deepcopy(data)
    members = {}
    total = 0
    for item, key in _binary_fields(packed):
        raw = item[key]
        if not isinstance(raw, str):
            raise ValueError(f"{key}: expected base64 text")
        if not raw:
            continue
        if len(raw) > 4 * ((RESOURCE_LIMIT + 2) // 3):
            raise ValueError("embedded resource exceeds the size limit")
        try:
            value = base64.b64decode(raw, validate=True)
        except (ValueError, UnicodeError) as error:
            raise ValueError(f"{key}: invalid base64 resource") from error
        if len(value) > RESOURCE_LIMIT:
            raise ValueError("embedded resource exceeds the size limit")
        digest = hashlib.sha256(value).hexdigest()
        name = f"assets/{digest}"
        if name not in members:
            total += len(value)
            if total > TOTAL_LIMIT or len(members) + 4 > ENTRY_LIMIT:
                raise ValueError("project resources exceed the archive limit")
            members[name] = value
        item[key] = {"$asset": digest}
    members["project.json"] = _json_bytes(packed, JSON_LIMIT)
    manifest = {"format": "meridiana-project-archive", "container_version": CONTAINER_VERSION,
                "project_version": data.get("version"),
                "producer": {"name": APP_NAME, "version": __version__},
                "members": {name: _descriptor(value) for name, value in members.items()}}
    manifest_raw = _json_bytes(manifest, MANIFEST_LIMIT)
    if sum(map(len, members.values())) + len(manifest_raw) + len(MIMETYPE) > TOTAL_LIMIT:
        raise ValueError("project exceeds the archive size limit")
    return members, manifest_raw


def _read_member(archive, info, limit, descriptor=None):
    if info.file_size > limit:
        raise ValueError(f"{info.filename}: exceeds the size limit")
    data = bytearray()
    with archive.open(info) as source:
        while block := source.read(min(1 << 20, limit - len(data) + 1)):
            data.extend(block)
            if len(data) > limit:
                raise ValueError(f"{info.filename}: exceeds the size limit")
    if len(data) != info.file_size:
        raise ValueError(f"{info.filename}: size mismatch")
    if descriptor is not None and _descriptor(data) != descriptor:
        raise ValueError(f"{info.filename}: integrity check failed")
    return bytes(data)


def _check_directory(path):
    """Bound the central directory before ZipFile allocates its member objects. ZIP64 is not needed here."""
    size = path.stat().st_size
    if size > TOTAL_LIMIT:
        raise ValueError("project exceeds the archive size limit")
    with path.open("rb") as source:
        start = max(0, size - (65535 + 22 + 20))
        source.seek(start)
        tail = source.read(65535 + 22 + 20)
    end = tail.rfind(b"PK\x05\x06")
    if end < 0 or len(tail) - end < 22:
        raise ValueError("incomplete archive directory")
    _, disk, directory_disk, count_disk, count, length, offset, comment = struct.unpack_from("<4s4H2LH", tail, end)
    if (disk or directory_disk or count_disk != count or (end >= 20 and tail[end - 20:end - 16] == b"PK\x06\x07")
            or count == 65535 or length == 0xffffffff or offset == 0xffffffff):
        raise ValueError("multipart and ZIP64 archives are not supported")
    if count > ENTRY_LIMIT or length > count * 1024:
        raise ValueError("archive directory exceeds the size or entry limit")
    if end + 22 + comment != len(tail) or offset + length > start + end:
        raise ValueError("invalid archive directory bounds")


def read(path: Path, *, include_assets: bool = True) -> dict:
    """Read one ZIP, without backup fallback; metadata-only reads never decompress binary assets."""
    path = Path(path)
    _check_directory(path)
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > ENTRY_LIMIT or sum(i.file_size for i in infos) > TOTAL_LIMIT:
                raise ValueError("project exceeds the archive limit")
            entries = {i.filename: i for i in infos}
            if len(entries) != len(infos):
                raise ValueError("duplicate archive member")
            for info in infos:
                name = info.filename
                if name not in ("mimetype", "manifest.json", "project.json") and not (
                        name.startswith("assets/") and _DIGEST.fullmatch(name[7:])):
                    raise ValueError("invalid archive member name")
                mode = stat.S_IFMT(info.external_attr >> 16)
                if mode not in (0, stat.S_IFREG) or info.flag_bits & 1:
                    raise ValueError("encrypted or non-regular archive member")
                if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise ValueError("unsupported archive compression")
                if name.startswith("assets/") and info.file_size > RESOURCE_LIMIT:
                    raise ValueError("resource exceeds the size limit")
            if not {"mimetype", "manifest.json", "project.json"} <= entries.keys():
                raise ValueError("incomplete Meridiana archive")
            if _read_member(archive, entries["mimetype"], len(MIMETYPE)) != MIMETYPE:
                raise ValueError("not a Meridiana project archive")
            manifest = _json(_read_member(archive, entries["manifest.json"], MANIFEST_LIMIT))
            version = manifest.get("container_version")
            if type(version) is not int or version < 1:
                raise ValueError("invalid container version")
            if version > CONTAINER_VERSION:
                raise FutureVersionError("made by a newer Meridiana; update the program to open it")
            if manifest.get("format") != "meridiana-project-archive":
                raise ValueError("not a Meridiana project archive")
            members = manifest.get("members")
            if not isinstance(members, dict) or set(members) != entries.keys() - {"mimetype", "manifest.json"}:
                raise ValueError("archive members do not match the manifest")
            for name, descriptor in members.items():
                if (not isinstance(descriptor, dict) or set(descriptor) != {"size", "sha256"}
                        or type(descriptor["size"]) is not int or descriptor["size"] != entries[name].file_size
                        or not isinstance(descriptor["sha256"], str)
                        or not _DIGEST.fullmatch(descriptor["sha256"])
                        or (name.startswith("assets/") and name[7:] != descriptor["sha256"])):
                    raise ValueError("invalid archive member descriptor")
            data = _json(_read_member(archive, entries["project.json"], JSON_LIMIT, members["project.json"]))
            if data.get("version") != manifest.get("project_version"):
                raise ValueError("project version does not match the manifest")
            used = set()
            decoded = {}
            for item, key in _binary_fields(data):
                reference = item[key]
                if reference == "":
                    continue
                if (not isinstance(reference, dict) or set(reference) != {"$asset"}
                        or not isinstance(reference["$asset"], str) or not _DIGEST.fullmatch(reference["$asset"])):
                    raise ValueError("invalid binary resource reference")
                name = f"assets/{reference['$asset']}"
                if name not in members:
                    raise ValueError("missing binary resource")
                used.add(name)
                if include_assets and name not in decoded:
                    raw = _read_member(archive, entries[name], RESOURCE_LIMIT, members[name])
                    decoded[name] = base64.b64encode(raw).decode("ascii")
                item[key] = decoded[name] if include_assets else ""
            if used != set(members) - {"project.json"}:
                raise ValueError("unreferenced binary resource")
            return data
    except (zipfile.BadZipFile, EOFError, RuntimeError, NotImplementedError, zlib.error) as error:
        raise ValueError(f"invalid Meridiana archive: {error}") from error


def read_document(path: Path, *, include_assets: bool = True) -> dict:
    """The shared reader for projects and their local index; JSON remains readable for historical fixtures."""
    path = Path(path)
    with path.open("rb") as source:
        magic = source.read(4)
    if magic.startswith(b"PK") or path.name.casefold().endswith((".mer", ".mer.bak")):
        return read(path, include_assets=include_assets)
    if path.stat().st_size > TOTAL_LIMIT:
        raise ValueError("project exceeds the size limit")
    with path.open("rb") as source:
        raw = source.read(TOTAL_LIMIT + 1)
    if len(raw) > TOTAL_LIMIT:
        raise ValueError("project exceeds the size limit")
    return _json(raw.decode("utf-8"))


def write(path: Path, data: dict, *, keep_backup: bool = True, validate=None) -> None:
    """Replace a document only after its complete new archive and previous valid backup are durable."""
    members, manifest = _pack(data)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    backup_temp = None
    try:
        with os.fdopen(fd, "w+b") as stream:
            with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6,
                                 allowZip64=False) as archive:
                archive.writestr("mimetype", MIMETYPE, compress_type=zipfile.ZIP_STORED)
                archive.writestr("manifest.json", manifest)
                for name, value in members.items():
                    archive.writestr(name, value)
            stream.flush()
            os.fsync(stream.fileno())
        if keep_backup and path.exists():
            try:
                previous = read(path)
                if validate is not None:
                    validate(previous)
            except FutureVersionError:
                raise
            except ValueError:
                # Preserve a valid recovery backup instead of copying damaged bytes over it.
                previous = None
            if previous is not None:
                backup_fd, backup_temp = tempfile.mkstemp(prefix=f".{path.name}.bak.", suffix=".tmp", dir=path.parent)
                with os.fdopen(backup_fd, "wb") as destination, path.open("rb") as source:
                    shutil.copyfileobj(source, destination)
                    destination.flush()
                    os.fsync(destination.fileno())
                os.replace(backup_temp, path.with_name(path.name + ".bak"))
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
        if backup_temp is not None:
            Path(backup_temp).unlink(missing_ok=True)
