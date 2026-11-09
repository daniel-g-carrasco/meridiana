"""Frozen-format compatibility, with unavailable frontend I/O kept explicit.

Quick currently has a startup loader, but no Save or configuration commands. The
``save_command`` injection must be a real frontend handler when one is implemented,
never Project.save. Likewise ``widgets_open`` must reopen in a Widgets frontend.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import _setup
from meridiana import config, model
from quick.parity.differential import MissingCommand, canonical_project, compare


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
    def __init__(self, cache, *, save_command=None):
        self.cache = Path(cache)
        self.host = None
        self.save_command = save_command

    @property
    def project(self):
        if self.host is None:
            raise RuntimeError("Quick has no open project")
        return self.host.bridge.session.project

    @property
    def can_save(self):
        return self.save_command is not None

    def open(self, path):
        from meridiana.quick.app import QuickWindow
        self.close()
        # This is the startup loader in quick.app.main, not an invented Open slot.
        project, notice = model.Project.load(Path(path))
        self.host = QuickWindow(project, self.cache)
        if notice:
            self.host.bridge._error = notice
            self.host.bridge.stateChanged.emit()
        return notice

    def save(self, path):
        if not self.can_save:
            raise MissingCommand("Quick:save")
        return self.save_command(self.host, Path(path))

    def config_status(self, path):
        return {"file": Path(path).name, "status": "missing",
                "missing": ["Quick:load_config", "Quick:save_config"]}

    def close(self):
        if self.host is not None:
            from PySide6.QtCore import QCoreApplication, QEvent
            self.host.close()
            self.host = None
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def roundtrip(source, destination, quick, *, widgets_open=None):
    """Quick open/save -> real Widgets reopen; compare every semantic project field.

    ``widgets_open(path)`` returns the project from the reopened MainWindow. Missing
    capabilities are returned before writing anything. Destinations must be new files.
    """
    source, destination = Path(source), Path(destination)
    result = {"file": source.name, "status": "missing", "missing": [], "differences": []}
    notice = quick.open(source)
    result["notice"] = notice
    before = canonical_project(quick.project)
    if not quick.can_save:
        result["missing"].append("Quick:save")
        return result
    if widgets_open is None:
        result["missing"].append("Widgets:reopen_adapter")
        return result
    if destination.exists() or destination.resolve() == source.resolve():
        raise FileExistsError(destination)
    quick.save(destination)
    reopened = widgets_open(destination)
    result["differences"] = compare(before, canonical_project(reopened))
    result["status"] = "different" if result["differences"] else "equal"
    return result


def current_config_roundtrip(source, folder):
    """Shared config-file contract only, without claiming Quick settings support.

    Load the current fixture, save its current schema, reopen it. Never migrate back
    to an old application schema, and never load a malformed original in place:
    config.load can quarantine damaged input files.
    """
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
            "scope": "shared config file contract; Quick configuration commands are missing",
            "version": reopened.to_json()["version"]}
