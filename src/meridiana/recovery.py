"""Autosave and recovery. While a project has unsaved changes a copy goes to the state folder every few
minutes; a save, or a close that discards the changes, takes it away. A copy still there at the next start
means Meridiana stopped without saving, and the designer is offered it back. The copy never replaces the
project's file by itself.

Revisions follow the habit of the office: a new revision is a new file next to the previous one, with the
suffix _Rnn, and no file is ever written over."""

from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path

from . import atomic

REVISION = re.compile(r"^(?P<stem>.*?)_R(?P<n>\d{2,})$")


def slot(state_dir: Path, project_path: Path | None) -> Path:
    """Where the copy of a project goes: one place per project file, one for a project not yet saved."""
    if project_path is None:
        key = "new"
    else:
        key = hashlib.sha1(str(Path(project_path).resolve()).encode("utf-8")).hexdigest()[:16]
    return Path(state_dir) / "recovery" / f"{key}.json"


def write(state_dir: Path, project_path: Path | None, data: dict) -> Path:
    path = slot(state_dir, project_path)
    atomic.write_json(path, {"path": str(project_path) if project_path else "", "saved": time.time(), "project": data},
                      keep_backup=False)
    return path


def clear(state_dir: Path, project_path: Path | None) -> None:
    slot(state_dir, project_path).unlink(missing_ok=True)


def pending(state_dir: Path) -> list[dict]:
    """The copies left behind, newest first: {"file", "path", "saved", "project"}. A copy that cannot be
    read is set aside (renamed), not lost and not offered again."""
    folder = Path(state_dir) / "recovery"
    out = []
    for f in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            data, _notice = atomic.read_json(f)
            out.append({"file": f, "path": str(data.get("path") or ""), "saved": float(data["saved"]),
                        "project": data["project"]})
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            f.replace(f.with_suffix(".unreadable"))
    return sorted(out, key=lambda c: c["saved"], reverse=True)


def next_revision(path: Path) -> Path:
    """The file of the next revision next to `path`: name_R01 after name, name_R04 after name_R03, never a
    file that exists."""
    path = Path(path)
    m = REVISION.match(path.stem)
    stem, n = (m.group("stem"), int(m.group("n"))) if m else (path.stem, 0)
    while True:
        n += 1
        candidate = path.with_name(f"{stem}_R{n:02d}{path.suffix}")
        if not candidate.exists():
            return candidate
