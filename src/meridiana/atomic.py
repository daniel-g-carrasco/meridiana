"""Files written whole or not at all, with the previous version kept.

A temporary file in the same folder, flushed to the disk, then renamed over the target: a crash, a full
disk or a pulled cable leave either the old file or the new one, never half of one. The file as it was
before is kept next to it as <name>.bak, and reading falls back to it when the file is damaged, saying so.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path


def write_json(path: Path, data, keep_backup: bool = True) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        if keep_backup and path.exists():
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def read_json(path: Path) -> tuple[object, str | None]:
    """The data and, when the file could not be read and the backup was used instead, why."""
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, ValueError) as error:
        backup = path.with_name(path.name + ".bak")
        if not backup.exists():
            raise
        data = json.loads(backup.read_text(encoding="utf-8"))
        return data, f"{path.name} could not be read ({type(error).__name__}: {error}); the previous save was opened"
