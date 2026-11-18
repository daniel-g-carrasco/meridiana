"""The window as the system shows it: the title bar of Windows in the theme's light or dark (R482) and the Alt key of
the menu bar wherever the keyboard's focus is (R481).

R482 (Daniel 06/11/2026: «da quando abbiamo la Quick non segue più il colore del tema di Meridiana»): the Widgets ask
the application's colour scheme (ui/theme.py, styleHints().setColorScheme), which Qt passes to the title bars of its
windows; the Quick did not. Here the same request, and the attribute of DWM set on every window of the program at
once (DWMWA_USE_IMMERSIVE_DARK_MODE), at the opening, when the theme changes and when a new window comes (a dialog of
its own), so that it does not wait for the scheme to reach it.

R544 (Daniel 08/11/2026: «su Linux vorrei che come prima il colore del bordo della finestra e della barra del titolo
seguano i colori di sfondo di Meridiana [...] Non so se si può fare la stessa cosa con la barra del titolo di Windows»):
- Linux, Wayland: Niri (Lucciola has no `prefer-no-csd`) leaves the title bar to the program, and Qt draws it with its
  «bradient» decoration, which paints bar and frame with the application palette's Window and the title with its
  WindowText (Disabled WindowText when the window is not active), read at every paint, and repaints on
  ApplicationPaletteChange (qtbase 6.12, plugins/platforms/wayland). The Widgets set the whole palette from the theme
  (ui/theme.py), so the bar had Meridiana's ground: «come prima». The Quick never set it, so the bar stayed in Qt's
  default grey, light in the dark theme too. Here the palette's Window and WindowText from the theme's `window`,
  `text` and `muted`, at the opening and at every change of theme; nothing else of the palette is touched.
- Windows 11 (build 22000 and later): DWMWA_CAPTION_COLOR, DWMWA_TEXT_COLOR and DWMWA_BORDER_COLOR with the same three
  colours, on every window, as the dark mode attribute. Windows 10 refuses them and keeps the light or dark bar.

R481 (Daniel 06/11/2026: «ora voglio nascondere il menu superiore con Alt ma non funziona»): Alt was read by the Keys of
five items of the workbench, so it did nothing with the focus in a field, the plan, the 3D view, a list, a popup or the
menu bar itself (where the second Alt should hide it). Read here for the whole window, as in the programs of Windows:
Alt pressed and let go with nothing else in between is a tap; another key, a button of the mouse, the wheel or the
window losing the focus (Alt+Tab) in between make it a combination, which does nothing."""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPalette, QWindow

from . import activity

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_BORDER_COLOR, DWMWA_CAPTION_COLOR, DWMWA_TEXT_COLOR = 34, 35, 36


def frame_colours(colors) -> dict[str, QColor]:
    """The frame's colours from the theme's tokens: bar and border on the window's ground, the title in the text."""
    return {"ground": QColor(colors["window"]), "text": QColor(colors["text"]),
            "quiet": QColor(colors.get("muted", colors["text"]))}


def frame_palette(colours: dict[str, QColor], palette: QPalette | None = None) -> QPalette:
    """`palette` (the application's) with Window and WindowText from `colours`: what Qt's Wayland decoration paints."""
    palette = QPalette(palette if palette is not None else QGuiApplication.palette())
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
        palette.setColor(group, QPalette.ColorRole.Window, colours["ground"])
        palette.setColor(group, QPalette.ColorRole.WindowText,
                         colours["quiet"] if group == QPalette.ColorGroup.Disabled else colours["text"])
    return palette


def draws_own_frame() -> bool:
    """Whether Qt draws the title bar itself (Wayland, client-side decorations), with the application palette."""
    return QGuiApplication.platformName() == "wayland"


def _colorref(colour: QColor) -> int:
    return colour.red() | colour.green() << 8 | colour.blue() << 16


def set_frame_colours(window: QWindow, colours: dict[str, QColor]) -> bool:
    """Bar, title and border of `window` in `colours` (Windows 11); False where DWM refuses them (Windows 10)."""
    if sys.platform != "win32":
        return False
    try:
        from ctypes import wintypes
        hwnd = wintypes.HWND(int(window.winId()))
        done = True
        for attribute, key in ((DWMWA_CAPTION_COLOR, "ground"), (DWMWA_BORDER_COLOR, "ground"),
                               (DWMWA_TEXT_COLOR, "text")):
            value = wintypes.DWORD(_colorref(colours[key]))
            done = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)) == 0 and done
        return done          # DWM keeps these three write-only: DwmGetWindowAttribute refuses to give them back
    except (OSError, AttributeError, ValueError):
        return False


def set_dark_frame(window: QWindow, dark: bool) -> bool:
    """The title bar of `window` dark or light (Windows 10 2004 and later); False where there is none to set."""
    if sys.platform != "win32":
        return False
    try:
        from ctypes import wintypes
        hwnd = wintypes.HWND(int(window.winId()))
        value = ctypes.c_int(1 if dark else 0)
        return ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)) == 0
    except (OSError, AttributeError, ValueError):
        return False


def dark_frame(window: QWindow) -> bool | None:
    """What the title bar of `window` is, read back from DWM; None where it cannot be read."""
    if sys.platform != "win32":
        return None
    try:
        from ctypes import wintypes
        hwnd = wintypes.HWND(int(window.winId()))
        value = ctypes.c_int(0)
        if ctypes.windll.dwmapi.DwmGetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)) != 0:
            return None
        return bool(value.value)
    except (OSError, AttributeError, ValueError):
        return None


class FrameTheme(QObject):
    """Keeps the title bars of the program's windows in the theme of `theme` (backend.tokens.ThemeTokens)."""

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        app = QGuiApplication.instance()
        theme.changed.connect(self.apply)
        # a method of this object, not a lambda: the application outlives the window, and a lambda kept framing new
        # windows with the theme of a window already closed (its colours read as the bare Property: TypeError, r24-unita)
        app.focusWindowChanged.connect(self._focused)
        self.apply()

    def _focused(self, window) -> None:
        if window is not None:
            self.frame(window)

    def frame(self, window: QWindow) -> None:
        if not isinstance(self.theme.colors, dict):                            # the theme's window already taken apart
            return
        if window.type() in (Qt.WindowType.Window, Qt.WindowType.Dialog):        # not a popup, not a tooltip
            set_dark_frame(window, bool(self.theme.dark))
            set_frame_colours(window, frame_colours(self.theme.colors))       # R544, Windows 11

    def apply(self) -> None:
        if draws_own_frame():                                                  # R544: Qt's own decoration
            palette = frame_palette(frame_colours(self.theme.colors))
            if palette != QGuiApplication.palette():
                QGuiApplication.setPalette(palette)
        if sys.platform == "win32":
            wanted = {"light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}.get(
                self.theme.options.get("theme"), Qt.ColorScheme.Unknown)
            hints = QGuiApplication.styleHints()
            if getattr(QGuiApplication.instance(), "_meridiana_scheme", None) != wanted:
                QGuiApplication.instance()._meridiana_scheme = wanted
                hints.setColorScheme(wanted)
        for window in QGuiApplication.topLevelWindows():
            self.frame(window)


_INPUT = frozenset((QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick,
                    QEvent.Type.Wheel, QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.NativeGesture))


class AltTap(QObject):
    """Alt pressed and let go alone, anywhere in `window`: `tapped`. Anything else in between makes it a combination:
    another key, a button of the mouse pressed, moved with or let go (R527: Alt held to carry a card as a tab never
    opens the menu). `held` tells Alt down and up, a combination or not, for whoever reads it while carrying."""

    tapped = Signal()
    pressed = Signal(float, float)          # a button of the mouse, where in the window (the menu bar hides)
    held = Signal(bool)                     # Alt down or up (R527, the cards carried as tabs)

    def __init__(self, window: QWindow, parent=None):
        super().__init__(parent)
        self.armed = False
        self.buttons = Qt.MouseButton.NoButton
        window.installEventFilter(self)

    def eventFilter(self, _obj, event) -> bool:
        kind = event.type()
        if kind in _INPUT or (kind == QEvent.Type.MouseMove and event.buttons() != Qt.MouseButton.NoButton):
            activity.touch()            # r27: the designer at work, nothing made ahead now (activity.py)
        if kind == QEvent.Type.KeyPress:
            alone = event.key() == Qt.Key.Key_Alt and not event.isAutoRepeat() and not (
                event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
                                     | Qt.KeyboardModifier.MetaModifier)) and self.buttons == Qt.MouseButton.NoButton
            if event.key() == Qt.Key.Key_Alt and event.isAutoRepeat():
                return False
            self.armed = alone
            if event.key() == Qt.Key.Key_Alt:
                self.held.emit(True)
        elif kind == QEvent.Type.KeyRelease:
            if event.key() == Qt.Key.Key_Alt and not event.isAutoRepeat():
                self.held.emit(False)
                if self.armed:
                    self.armed = False
                    self.tapped.emit()
                    return True
        elif kind == QEvent.Type.MouseButtonPress:
            self.armed = False
            self.buttons = event.buttons()
            self.pressed.emit(event.position().x(), event.position().y())
        elif kind == QEvent.Type.MouseButtonRelease:
            self.armed = False
            self.buttons = event.buttons()
        elif kind == QEvent.Type.MouseMove:
            self.buttons = event.buttons()
            if self.buttons != Qt.MouseButton.NoButton:
                self.armed = False
        elif kind in (QEvent.Type.MouseButtonDblClick, QEvent.Type.Wheel,
                      QEvent.Type.FocusOut, QEvent.Type.WindowDeactivate, QEvent.Type.TouchBegin):
            self.armed = False
            if kind in (QEvent.Type.FocusOut, QEvent.Type.WindowDeactivate):
                self.held.emit(False)
        return False
