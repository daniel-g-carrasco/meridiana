"""Starting the window: the Qt application, the settings, the main window, a project given on the
command line or the last one opened. With MERIDIANA_SCREENSHOT set, the window writes a PNG of itself
after MERIDIANA_SCREENSHOT_DELAY seconds and closes (for the tests and the CI)."""

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


def main(argv: list[str]) -> int:
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
    cfg = config.load(paths.config_file)
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
    given = [a for a in argv[1:] if not a.startswith("-")]
    target = Path(given[0]) if given else (Path(cfg.last_project) if cfg.last_project else None)
    # a copy left by a session that stopped without saving comes first: opening the file would drop it
    if not win.offer_recovery() and target and target.exists():
        win.open_path(target)
    win.show()

    shot = os.environ.get(f"{ENV_PREFIX}_SCREENSHOT")
    if shot:
        delay = float(os.environ.get(f"{ENV_PREFIX}_SCREENSHOT_DELAY", "3"))

        def take():
            win.grab().save(shot)
            app.quit()
        QTimer.singleShot(int(delay * 1000), take)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
