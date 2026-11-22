"""Starting Meridiana, the pieces that need no window: the program's identity on Windows (taskbar, the mutex an
update looks for), the project given on the command line, the channel of the single instance (single_instance.py:
when a Meridiana is already running, a start hands it its project and ends; never a run for a photograph, see instance_channel). The Qt Quick window's start is gui/application.py (main)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNNING: list = []         # the handle of the mutex, held while the program runs


def windows_identity(app_id: str) -> int:
    """Windows: the program's AppUserModelID, the one its installer gives the shortcuts (its taskbar button groups
    with them, a pinned shortcut is its button), and a mutex of that name held while it runs, which tells an update
    whether to start the program again (meridiana.iss, CheckForMutexes). Elsewhere nothing; the mutex's handle."""
    if sys.platform != "win32":
        return 0
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ctypes.c_wchar_p(app_id))
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, ctypes.c_wchar_p(app_id))
    except (AttributeError, OSError):
        return 0
    if handle:
        _RUNNING.append(handle)
    return handle or 0


def explicit_project(arguments: list[str]) -> Path | None:
    """The project given on the command line, from the arguments Qt left (QApplication.arguments(): its own
    options and their values, -platform offscreen or -style Fusion, are taken out); the program's name first."""
    given = [a for a in arguments[1:] if not a.startswith("-")]
    return Path(given[0]) if given else None


def instance_channel(environ=os.environ, profile: Path | None = None, platform: str | None = None) -> str | None:
    """The channel of the single instance (single_instance.py), or None for none. MERIDIANA_INSTANCE names another
    channel, or «off»; a run for a photograph (MERIDIANA_SCREENSHOT: the tests, the CI, the scripts of the
    pictures) has none unless it names one, so that it never hands its project to the window the person has open
    (Quotario's rule). With a `profile` (the folder of the Quick's preferences and caches) the channel is that
    profile's: a start from a checkout or with a temporary profile (a test, a tool) never reaches the installed
    program's window, and two programs with different settings stay two. The profile goes in as a hash of its
    resolved path, so the channel's length never depends on the folder's; `platform` (sys.platform by default) is
    the system the name is made for."""
    import hashlib

    from meridiana import APP_ID, ENV_PREFIX
    from .single_instance import channel_name

    chosen = environ.get(f"{ENV_PREFIX}_INSTANCE", "")
    if chosen:
        return None if chosen == "off" else chosen
    if environ.get(f"{ENV_PREFIX}_SCREENSHOT"):
        return None
    if profile is None:
        return channel_name(APP_ID, environ=environ, platform=platform)
    place = os.path.normcase(str(Path(profile).expanduser().resolve()))
    return channel_name(APP_ID, environ=environ, platform=platform,
                        profile_key=hashlib.sha256(place.encode("utf-8")).hexdigest()[:8])
