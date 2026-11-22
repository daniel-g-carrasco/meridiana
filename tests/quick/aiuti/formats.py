"""The files of every version (tests/formati/file) opened in a real Quick window."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import _setup
from meridiana.app.platform import config
from meridiana.core.model import model
from quick.aiuti.differential import compare


@dataclass(frozen=True)
class FrozenCase:
    path: Path
    kind: str


def frozen_cases(folder=_setup.FORMATS):
    """Include malformed/future files too; an unknown fixture must fail classification."""
    cases = []
    for path in sorted(Path(folder).iterdir()):
        if path.name.startswith("config-v") and path.suffix == ".json":
            kind = "config"
        elif path.name in {"config-futuro.json", "config-troncato.json"}:
            kind = "invalid_config"
        elif path.name in {"progetto-futuro.meridiana", "progetto-latin1.meridiana", "progetto-troncato.meridiana"}:
            kind = "invalid_project"
        elif path.suffix in {".meridiana", ".mer"}:
            kind = "project"
        else:
            raise ValueError(f"Unclassified frozen fixture: {path.name}")
        cases.append(FrozenCase(path, kind))
    return cases


class QuickFiles:
    """The current Quick startup path: Project.load then an actual QML QuickWindow."""
    def __init__(self, cache):
        self.cache = Path(cache)
        self.host = None

    @property
    def project(self):
        if self.host is None:
            raise RuntimeError("Quick has no open project")
        return self.host.bridge.session.project

    def open(self, path):
        from meridiana.gui.application import QuickWindow
        self.close()
        # the startup loader of quick.app.main, not an invented Open slot
        project, notice = model.Project.load(Path(path))
        self.host = QuickWindow(project, self.cache)
        if notice:
            self.host.bridge._error = notice
            self.host.bridge.stateChanged.emit()
        return notice

    def close(self):
        if self.host is not None:
            from PySide6.QtCore import QCoreApplication, QEvent
            self.host.close()
            self.host = None
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def current_config_roundtrip(source, folder):
    """The settings file's contract: load the current fixture, save its current schema, reopen it. Never migrate
    back to an old schema, and never load a malformed original in place: config.load can quarantine damaged files."""
    source, folder = Path(source), Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    copied, saved = folder / "current-config-input.json", folder / "current-config-saved.json"
    if copied.exists() or saved.exists():
        raise FileExistsError("The configuration roundtrip requires a fresh folder")
    shutil.copyfile(source, copied)
    original = config.load(copied)
    config.save(original, saved)
    reopened = config.load(saved)
    differences = compare(original.to_json(), reopened.to_json())
    return {"status": "different" if differences else "equal", "differences": differences,
            "version": reopened.to_json()["version"]}
