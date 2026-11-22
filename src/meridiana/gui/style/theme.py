"""The pieces of the look that do not need a widget (r30-struttura: taken out of the Widgets window's theme, which
stays in ui/theme.py until that window goes): the names of the choices of Settings > Appearance, a QPalette from the
roles of theme_colors.derive, the arrows of the fields, the fonts read from their files (data/fonts) and given to the
charts of the report, and what the system says for the look.

- The system's accent: on Windows the Highlight of the platform's palette; on Linux the portal
  (org.freedesktop.appearance, accent-color), read with gdbus because PySide's QtDBus cannot read the (ddd) it
  answers, and read again on SettingChanged. Without one, the default colour."""

from __future__ import annotations

import sys

from PySide6.QtCore import QObject, QProcess, Signal, Slot
from PySide6.QtGui import QColor, QFontDatabase, QGuiApplication, QPalette

from meridiana.app.platform import log, paths
from meridiana.app.interface import theme_colors
from meridiana.app.platform.config import Config
from meridiana.i18n import _

PORTAL = ("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop", "org.freedesktop.portal.Settings")
# Inter since 25/10/2026 (R95: Daniel chose it at 14 px on the real window at 200 %; Titillium Web, before it, read
# thin and small)
FONT_DIR = "inter"
FONT_FILES = ("Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf")
FONT_WEIGHTS = dict(zip(FONT_FILES, (400, 600, 700), strict=True))
# The fonts to choose from in Preferences > Appearance (Daniel, 03/11/2026, study 29): each one's folder in data/fonts,
# its files and, where it has one, a condensed cut for where room is short (the words of the phase bars). Static files:
# on Linux a variable font with its width axis loses it, or its weight, when a weight is asked (study 29, section 4).
PLEX_WEIGHTS = ("Regular", "SemiBold", "Bold")
FONTS = {"inter": {"dir": FONT_DIR, "files": FONT_FILES, "tight": ()},
         "plex": {"dir": "ibm-plex", "files": tuple(f"IBMPlexSans-{w}.ttf" for w in PLEX_WEIGHTS),
                  "tight": tuple(f"IBMPlexSansCondensed-{w}.ttf" for w in PLEX_WEIGHTS)}}
FONT_WEIGHTS.update({f: weight for files in (FONTS["plex"]["files"], FONTS["plex"]["tight"])
                     for f, weight in zip(files, (400, 600, 700), strict=True)})
DEFAULT_FONT = Config().font


def theme_names() -> dict:
    return {"system": _("As the system"), "light": _("Light"), "dark": _("Dark")}


def colour_names() -> dict:
    """The ready-made colours of section 12.1, in the order of the menu."""
    return {"system": _("System"), "bronze": _("Bronze"), "terracotta": _("Terracotta"), "olive": _("Olive"),
            "forest": _("Forest"), "petrol": _("Petrol"), "blue": _("Blue"), "indigo": _("Indigo"),
            "plum": _("Plum"), "graphite": _("Graphite")}


def background_names() -> dict:
    return {"meridiana": _("Meridiana: lime and night"), "tinted": _("From the colour"), "grey": _("Grey")}


def qpalette(roles: dict) -> QPalette:
    pal = QPalette()
    for group, colours in roles.items():
        g = getattr(QPalette.ColorGroup, group)
        for role, hex_ in colours.items():
            pal.setColor(g, getattr(QPalette.ColorRole, role), QColor(hex_))
    return pal


ARROWS = {"up": ("M2 9L8 3L14 9", 16, 12), "down": ("M2 3L8 9L14 3", 16, 12), "open": ("M2 4L8 10L14 4", 16, 14)}


class SystemAccent(QObject):
    """What the system says for the look, one reader for the application (a child of it): the accent and whether
    it asks for less motion. On Windows the Highlight of the platform's palette, read before Meridiana sets its own
    (#0078d4 on Daniel's PC), and SPI_GETCLIENTAREAANIMATION; on Linux the portal's accent-color and
    reduced-motion, read with gdbus (PySide's QtDBus cannot read the (ddd) the portal answers) without waiting,
    and again on SettingChanged."""

    changed = Signal(str)
    motion = Signal(bool)            # True: less motion, please

    def __init__(self, app):
        if not isinstance(app, QGuiApplication):    # its palette() on a QCoreApplication is an access violation
            raise RuntimeError(f"SystemAccent needs a QGuiApplication, not {type(app).__name__}")
        super().__init__(app)
        self.value = ""
        self.reduced_motion = False
        self._processes: dict = {}
        if sys.platform == "win32":
            self.value = QGuiApplication.palette().color(QPalette.ColorRole.Highlight).name()
            self.reduced_motion = _windows_reduced_motion()
        elif sys.platform.startswith("linux"):
            # a gdbus still running when the program ends is stopped first: destroyed with it, Qt said «QProcess:
            # Destroyed while process ("gdbus") is still running» (a short process, a test's picture maker, the CI)
            import atexit
            import weakref
            mine = weakref.ref(self)
            atexit.register(lambda: mine() is not None and mine().stop())
            app.aboutToQuit.connect(self.stop)
            self._listen()
            self.read()
            self.read("reduced-motion")

    def stop(self) -> None:
        """The readings still running, ended and waited for."""
        from shiboken6 import isValid
        if not isValid(self):
            return
        for process in list(self._processes.values()):
            if isValid(process) and process.state() != QProcess.ProcessState.NotRunning:
                process.kill()
                process.waitForFinished(1000)
        self._processes.clear()

    @classmethod
    def of(cls, app) -> "SystemAccent":
        found = next((child for child in app.children() if isinstance(child, cls)), None)   # made with app as parent
        return found if found is not None else cls(app)

    def _listen(self) -> None:
        try:
            from PySide6.QtCore import SLOT
            from PySide6.QtDBus import QDBusConnection
        except ImportError:
            return
        bus = QDBusConnection.sessionBus()
        if bus.isConnected():
            bus.connect("", PORTAL[1], PORTAL[2], "SettingChanged", self, SLOT("_setting_changed(QDBusMessage)"))

    @Slot("QDBusMessage")
    def _setting_changed(self, message) -> None:
        args = message.arguments()
        if len(args) >= 2 and args[0] == "org.freedesktop.appearance" and args[1] in ("accent-color", "reduced-motion"):
            self.read(args[1])

    def read(self, key: str = "accent-color") -> None:
        if key in self._processes:
            return
        process = QProcess(self)
        process.finished.connect(lambda _code, _status: self._answered(key, process))
        process.errorOccurred.connect(lambda _e: self._answered(key, process))
        self._processes[key] = process
        process.start("gdbus", ["call", "--session", "--dest", PORTAL[0], "--object-path", PORTAL[1], "--method",
                                PORTAL[2] + ".ReadOne", "org.freedesktop.appearance", key])

    def _answered(self, key: str, process: QProcess) -> None:
        if self._processes.get(key) is not process:
            return                                  # an answer already taken (an error, then the end)
        del self._processes[key]
        from shiboken6 import isValid
        if not isValid(process):
            return          # the program quitting while gdbus still ran: Qt ends it and says so (seen on Linux)
        text = bytes(process.readAllStandardOutput()).decode("utf-8", "replace")
        process.deleteLater()
        if key == "reduced-motion":
            reduced = theme_colors.gdbus_number(text) == 1
            if reduced != self.reduced_motion:
                self.reduced_motion = reduced
                self.motion.emit(reduced)
            return
        accent = theme_colors.gdbus_accent(text)
        if accent != self.value:
            self.value = accent
            self.changed.emit(accent)


def _windows_reduced_motion() -> bool:
    """Windows' «Animation effects» switched off (SPI_GETCLIENTAREAANIMATION): less motion."""
    try:
        import ctypes
        on = ctypes.c_int(1)
        if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(on), 0):
            return not on.value
    except (AttributeError, OSError):
        pass
    return False


_CHART_FONTS: list = []     # (file, family, weight): given to matplotlib at its first figure or formula
_MATPLOTLIB_READY: list = []
_LOADED: dict = {}          # a key of FONTS -> (family, condensed family): files are read once


def _font_files(folder, names) -> str:
    """The files of a family given to Qt and noted for the charts; the family as Qt names it, "" if none is read."""
    family = ""
    for name in names:
        f = folder / name
        fid = QFontDatabase.addApplicationFont(str(f)) if f.exists() else -1
        families = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
        if not families:
            log.complain("fonts", OSError(f"{f} could not be loaded"))
            continue
        family = family or families[0]
        _CHART_FONTS.append((f, families[0], FONT_WEIGHTS[name]))
        if _MATPLOTLIB_READY:
            _register_for_charts(f, families[0], FONT_WEIGHTS[name])
    return family


def _font_families(choice: str) -> tuple[str, str]:
    """The family of a key of FONTS and its condensed one, loaded the first time they are asked."""
    if choice not in _LOADED:
        entry = FONTS[choice]
        folder = paths.shipped("fonts", entry["dir"])
        _LOADED[choice] = ((_font_files(folder, entry["files"]), _font_files(folder, entry["tight"]))
                           if folder is not None else ("", ""))
    return _LOADED[choice]


def matplotlib_fonts() -> None:
    """The program's fonts given to matplotlib and its list cut (lean_chart_fonts), before its first figure or
    formula: done at the start, with matplotlib's import, they cost the window 0.8 s before it showed (R120)."""
    if _MATPLOTLIB_READY:
        return
    _MATPLOTLIB_READY.append(True)
    for path, family, weight in _CHART_FONTS:
        _register_for_charts(path, family, weight)
    try:
        lean_chart_fonts()
    except (AttributeError, TypeError, RuntimeError) as error:
        log.complain("fonts for the charts", error)


def lean_chart_fonts() -> int:
    """matplotlib's list of fonts cut to its own (DejaVu, the STIX and Computer Modern of the formulas) and the
    program's: each font it looks for is scored against every font of the list, and with Windows' ~1800 the first
    formulas of «How it is computed» cost 0.65 s (R120, 25/10/2026). The fonts left; nothing changes on paper."""
    try:
        import matplotlib
        from matplotlib import font_manager
    except ImportError:
        return 0
    import os
    shipped = paths.shipped("fonts")
    # the folders as text, compared as text: resolving 1800 paths on the disk cost half a second
    keep = tuple(os.path.normcase(os.path.abspath(str(k))) + os.sep
                 for k in [matplotlib.get_data_path(), *([shipped] if shipped is not None else [])])
    manager = font_manager.fontManager

    def ours(entry) -> bool:
        return os.path.normcase(os.path.abspath(entry.fname)).startswith(keep)
    before = len(manager.ttflist)
    manager.ttflist = [f for f in manager.ttflist if ours(f)]
    manager.afmlist = [f for f in manager.afmlist if ours(f)]
    cached = getattr(manager, "_findfont_cached", None)
    if cached is not None:
        cached.cache_clear()
    return before - len(manager.ttflist)


def _register_for_charts(path, family: str, weight: int) -> None:
    """The font in matplotlib's list as an entry made here: its addfont reads every name table of the file,
    half a second each (measured on 22/10/2026), for what is already known."""
    try:
        from matplotlib import font_manager
        font_manager.fontManager.ttflist.append(font_manager.FontEntry(
            fname=str(path), name=family, style="normal", variant="normal", weight=weight, stretch="normal",
            size="scalable"))
        cached = getattr(font_manager.fontManager, "_findfont_cached", None)     # a font looked up before
        if cached is not None:
            cached.cache_clear()
    except (ImportError, AttributeError, TypeError) as error:
        log.complain("fonts for the charts", error)
