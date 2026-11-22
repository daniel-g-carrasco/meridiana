"""The IFC models' geometry kept under the caches (study 48, chapter 8): the folder the import's reader writes its
files in (`ifc_worker.context` and `keep_result`, given `paths.cache / FOLDER` by gui/backend/dialogs.py) is a store
under the one ceiling of the stores on disk (app/platform/disk_cap.py), and the files of the model linked to the open
project are declared in use. From outside the reader: it only names the folder and reads the project's reference
(ifc_import.reference: `resources["ifc_reference"]["context"]["mesh"]`). Without Qt."""

from __future__ import annotations

import os
from pathlib import Path

from meridiana.app.platform import disk_cap

FOLDER = "ifc"          # under the window's caches (paths.cache); gui/backend/dialogs.py gives the reader the same one
OWNER = "ifc"           # the name of the lease (disk_cap.protect)


def folder_of(caches) -> Path:
    """The folder of the IFC geometry under `caches` (the window's paths.cache)."""
    return Path(caches) / FOLDER


def groups_in_use(project, folder) -> set:
    """The groups (disk_cap.group_of) of the geometry the project's IFC model is shown with, when it lies in `folder`:
    the mesh and the reading kept beside it («ifc-<key>-m3.npz», «ifc-<key>-m3.read-<code>.json»)."""
    ref = (getattr(project, "resources", None) or {}).get("ifc_reference")
    context = ref.get("context") if isinstance(ref, dict) else None
    mesh = context.get("mesh") if isinstance(context, dict) else None
    if not mesh:
        return set()
    where = os.path.normcase(os.path.abspath(os.path.dirname(str(mesh))))
    if where != os.path.normcase(os.path.abspath(str(folder))):
        return set()                        # a geometry kept elsewhere is not this store's
    group = disk_cap.group_of(os.path.basename(str(mesh)))
    return {group} if group else set()


class Follow:
    """The session's listener that keeps the open project's IFC geometry in `folder` declared in use under the
    ceiling of `root` (written off the window's thread, only when it changes)."""

    def __init__(self, session, folder, root):
        self.session, self.folder, self.root = session, Path(folder), Path(root)
        self.groups: set = set()
        session.subscribe(self.changed)
        self.changed(set())

    def changed(self, _topics) -> None:
        groups = groups_in_use(self.session.project, self.folder)
        if groups != self.groups:
            self.groups = groups
            disk_cap.protect_soon(self.folder, OWNER, groups, self.root)

    def close(self) -> None:
        if self.changed in self.session.listeners:
            self.session.listeners.remove(self.changed)
        if self.groups:
            disk_cap.protect_soon(self.folder, OWNER, (), self.root)
