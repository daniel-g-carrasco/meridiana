"""Qt's disk caches of the program in the profile (study 56, point 1): the compiled QML and the graphics pipelines
(the shaders compiled for the graphics card), kept from one start to the next, so the window is built in 6,6-7,0 s
instead of 10,7-15,7 (offscreen, 20/11/2026).

They were off everywhere since the Quick's trial (R389, 04/11/2026), to keep the measures and the package's self-test
out of the user's folders: Qt puts them under its own cache folder (%LOCALAPPDATA%\\Meridiana\\cache on Windows,
whatever the XDG variables say, docs/progetto.md). Here they are put where Meridiana says, never there:

- in `<profile>/qt-cache/<key>/`, `key` the version of Meridiana and of Qt: a new version starts with an empty folder
  and the folders of the other versions are thrown away (an update never meets a cache of the build before);
- the QML in `qml/` (QML_DISK_CACHE_PATH; Qt checks each file against its source anyway), the pipelines in the file
  `pipeline.bin` (QSG_RHI_PIPELINE_CACHE_SAVE and _LOAD: an explicit file wins over QT_DISABLE_SHADER_DISK_CACHE,
  qsgrhisupport.cpp, Qt 6.12);
- Qt Quick 3D's shader cache stays off: Qt keeps it only under its own cache folder, the same for every profile
  (qssgrendershadercache.cpp, QStandardPaths::CacheLocation), so QT_DISABLE_SHADER_DISK_CACHE stays set.

Only the program's start asks for them (gui/application.main): the tests, the tools and the package's check keep them
off (create_app), and MERIDIANA_QT_DISK_CACHE=0 turns them off in the program too (tests/_setup.py sets it)."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

FOLDER = "qt-cache"
SWITCH = "MERIDIANA_QT_DISK_CACHE"
MARK = ".meridiana-qt-cache"        # in each folder of a version: what makes it ours to throw away


def wanted(environ=None) -> bool:
    """Whether the program's start keeps Qt's disk caches (MERIDIANA_QT_DISK_CACHE=0: not)."""
    environ = os.environ if environ is None else environ
    return environ.get(SWITCH, "1") != "0"


def key_of(version: str, qt: str) -> str:
    """The folder of a version: Meridiana's and Qt's, in characters any file system takes."""
    return re.sub(r"[^0-9A-Za-z._-]", "_", f"{version}-qt{qt}")


def prepare(profile: Path, key: str, environ=None, complain=None) -> Path | None:
    """The caches of version `key` in `profile`, written in `environ` for Qt to find before the window's QML engine
    and scene graph exist; the folders of other versions thrown away (only those with our mark). The folder, or None
    when it cannot be made (said through `complain(what, error)`; the program then starts without them)."""
    environ = os.environ if environ is None else environ
    root = Path(profile) / FOLDER
    folder = root / key
    try:
        (folder / "qml").mkdir(parents=True, exist_ok=True)
        (folder / MARK).touch()
    except OSError as error:
        if complain is not None:
            complain(f"Qt's disk caches in {folder}", error)
        return None
    for other in root.iterdir():
        if other != folder and other.is_dir() and (other / MARK).exists():
            def said(_function, path, error, _other=other):
                if complain is not None:
                    complain(f"the Qt disk cache of another version, {path}", error)
            shutil.rmtree(other, onexc=said)
    pipelines = folder / "pipeline.bin"
    environ.pop("QML_DISABLE_DISK_CACHE", None)
    environ["QML_DISK_CACHE_PATH"] = str(folder / "qml")
    environ["QSG_RHI_PIPELINE_CACHE_SAVE"] = str(pipelines)
    if pipelines.is_file():
        environ["QSG_RHI_PIPELINE_CACHE_LOAD"] = str(pipelines)
    else:
        environ.pop("QSG_RHI_PIPELINE_CACHE_LOAD", None)
    environ["QT_DISABLE_SHADER_DISK_CACHE"] = "1"       # Qt Quick 3D's, under Qt's own folder: off
    return folder


def turn_off(environ=None) -> None:
    """Every Qt disk cache off (create_app: the tests, the tools, the package's check)."""
    environ = os.environ if environ is None else environ
    environ["QML_DISABLE_DISK_CACHE"] = "1"
    environ["QT_DISABLE_SHADER_DISK_CACHE"] = "1"
    for name in ("QML_DISK_CACHE_PATH", "QSG_RHI_PIPELINE_CACHE_SAVE", "QSG_RHI_PIPELINE_CACHE_LOAD"):
        environ.pop(name, None)
