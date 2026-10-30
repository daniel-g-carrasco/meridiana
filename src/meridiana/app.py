"""Starting the window: the Qt application, the settings, the main window and its first page: a copy to
recover, the project given on the command line, File > New the first time, File > Open afterwards. With
MERIDIANA_SCREENSHOT set, the window writes a PNG of itself after MERIDIANA_SCREENSHOT_DELAY seconds and closes
(for the tests and the CI). When a Meridiana is already running, a start hands it its project and ends
(single_instance.py; never a run for a photograph, see instance_channel)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


# desktops whose look Qt already follows with a theme of its own (kde, gtk3, lxqt)
KNOWN_DESKTOPS = ("kde", "gnome", "unity", "cinnamon", "xfce", "mate", "budgie", "lxqt")


def linux_theme(environ=os.environ) -> None:
    """On a Linux desktop Qt does not know (niri, sway, Hyprland...) its generic theme ignores the dark
    preference and has its own file dialogs; the portal's theme follows the preference, live, and opens
    the desktop's dialogs (tried on niri 26.04, 21/10/2026: generic light, portal dark). A theme the
    user chose (QT_QPA_PLATFORMTHEME) stays."""
    if not sys.platform.startswith("linux") or environ.get("QT_QPA_PLATFORMTHEME"):
        return
    desktop = environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if not any(name in desktop for name in KNOWN_DESKTOPS):
        environ["QT_QPA_PLATFORMTHEME"] = "xdgdesktopportal"


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


def instance_channel(environ=os.environ) -> str | None:
    """The channel of the single instance (single_instance.py), or None for none. MERIDIANA_INSTANCE names another
    channel, or «off»; a run for a photograph (MERIDIANA_SCREENSHOT: the tests, the CI, the scripts of the
    pictures) has none unless it names one, so that it never hands its project to the window the person has open
    (Quotario's rule)."""
    from . import APP_ID, ENV_PREFIX
    from .single_instance import channel_name

    chosen = environ.get(f"{ENV_PREFIX}_INSTANCE", "")
    if chosen:
        return None if chosen == "off" else chosen
    if environ.get(f"{ENV_PREFIX}_SCREENSHOT"):
        return None
    return channel_name(APP_ID, environ=environ)


def prepare_workspace(win, explicit: Path | None) -> bool:
    """Recovery and an explicitly opened document precede onboarding; never reopen the last file implicitly. With
    a project asked for by name only its own copy is offered (the copies of other projects wait for a start
    without one): «Yes» on another project's copy left the project asked for unopened, without a word."""
    if win.offer_recovery(explicit):
        return False
    if explicit is not None:
        if win.open_path(explicit) is False:
            win.open_file_page("open")
        return False
    first = win.cfg.tour_status == "new"
    win.open_file_page("new" if first else "open")
    return first


def main(argv: list[str]) -> int:
    if "--kokoro-worker" in argv:
        from .assistant.kokoro_worker import main as voice_worker
        return voice_worker(argv[argv.index("--kokoro-worker") + 1:])
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from PySide6.QtCore import QLocale

    from . import APP_ID, APP_NAME, ENV_PREFIX, config, i18n, log
    from .paths import Paths

    linux_theme()
    windows_identity(APP_ID)
    QApplication.setApplicationName(APP_NAME)
    QApplication.setDesktopFileName(APP_ID)
    app = QApplication(argv)
    from PySide6.QtGui import QIcon

    from .paths import shipped
    icon = shipped("icons", "hicolor", "scalable", "apps", f"{APP_ID}.svg")
    if icon is not None:                 # the title bars and the taskbar (on Wayland the desktop file's icon)
        app.setWindowIcon(QIcon(str(icon)))
    paths = Paths.from_env()
    log.setup(paths.log_file)
    log.install_excepthook()             # the window takes over the telling once it exists
    # one window for every start: a Meridiana already running takes the project and comes to the front
    from . import recovery, single_instance
    explicit = explicit_project(app.arguments())
    channel = instance_channel()
    given = [str(explicit.expanduser().resolve())] if explicit is not None else []
    if channel and single_instance.hand_over(channel, given, os.environ.get("XDG_ACTIVATION_TOKEN", "")):
        return 0
    handed: list = []                    # what a later start hands over before the window can take it
    receiver = None
    if channel:                          # listened to before the window exists: a start meanwhile waits for it
        receiver = single_instance.Receiver(channel, app)
        receiver.listen()
        receiver.received.connect(lambda files, token: handed.append((files, token)))
    try:                                 # the recovery copies of this start are its own while it runs
        recovery.claim(paths.state)
    except OSError as error:
        log.complain("claim the recovery copies", error)
    cfg = config.load(paths.config_file)
    # the size of the text before any widget or font is made (R133)
    from .ui import design
    design.set_text_size(cfg.text_size)
    if cfg.language:
        i18n.setup(cfg.language)
    # spin boxes write numbers as the labels do: in the language of the window
    QLocale.setDefault(QLocale(i18n.language()))
    # Qt's own words too (OK, Cancel, the file dialogs): «Cancel» stood in the Italian window (R26)
    from .ui import qt_translations
    qt_translations.install(app, i18n.language())
    # the theme (Fusion, the palette of the colour chosen, the font) is the window's: ui/theme.py

    from .ui.window import MainWindow
    win = MainWindow(paths, cfg)
    log.tell_with(win.tell_error)
    show_tour = prepare_workspace(win, explicit)
    win.show()
    if receiver is not None:             # from now on straight to the window; what came meanwhile, in order
        receiver.received.disconnect()
        receiver.received.connect(win.open_handed_over)
        for files, token in handed:
            win.open_handed_over(files, token)
    if show_tour and not handed:         # a project handed over meanwhile is the work in hand, not the tour
        QTimer.singleShot(1200, win, win._offer_tour)

    shot = os.environ.get(f"{ENV_PREFIX}_SCREENSHOT")
    if shot:
        delay = float(os.environ.get(f"{ENV_PREFIX}_SCREENSHOT_DELAY", "3"))

        def take():
            win.grab().save(shot)
            app.quit()
        QTimer.singleShot(int(delay * 1000), take)
    code = app.exec()
    recovery.release(paths.state)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
