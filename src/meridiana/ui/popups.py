"""The little windows that come and go (Daniel, 24/10/2026: «finestrelle… compaiono a scatti»): the tooltips, the
menus, the lists of the drop-down fields, the help beside things. One look and one way of coming for all of them.

- **Coming**: Qt's own effects fade a tooltip by grabbing the screen behind it and blending it on a timer, and
  roll the menus open: at 200 % they stutter. They are turned off, and each little window fades in with its
  window opacity instead (110 ms, composited by the system), unless less motion is asked for.
- **Corners**: on Windows 11 the system rounds them as it rounds its own (8 px a menu and a popup, 4 px a
  tooltip; Geometry in Windows, learn.microsoft.com), with its shadow and a border in the theme's line colour
  (DwmSetWindowAttribute, DWMWA_WINDOW_CORNER_PREFERENCE and DWMWA_BORDER_COLOR, build 22000 and later). The
  style sheet then leaves their border to the system (`native_corners`). Elsewhere the sheet draws the border.

`install(app)` once; `set_colours(t)` with the theme; `set_motion(on)` with the preference."""

from __future__ import annotations

import sys

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QWidget

from .cards import default_tokens
from .design import Motion

FADE_MS = Motion.FAST
_STATE = {"border": default_tokens()["line"], "motion": True}
_KINDS = (Qt.WindowType.Popup, Qt.WindowType.ToolTip)


def native_corners() -> bool:
    """Whether the system rounds the little windows (Windows 11): then the sheet draws no border of its own."""
    if sys.platform != "win32":
        return False
    return sys.getwindowsversion().build >= 22000


def _dwm(widget: QWidget, small: bool) -> None:
    """The system's rounded corners and border on a little window (Windows 11)."""
    import ctypes
    from ctypes import wintypes
    try:
        hwnd = wintypes.HWND(int(widget.winId()))
        dwm = ctypes.windll.dwmapi
        corner = ctypes.c_int(3 if small else 2)           # DWMWCP_ROUNDSMALL, DWMWCP_ROUND
        dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner), ctypes.sizeof(corner))
        c = QColor(_STATE["border"])
        colour = ctypes.c_uint(c.red() | (c.green() << 8) | (c.blue() << 16))     # a COLORREF: 0x00BBGGRR
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(colour), ctypes.sizeof(colour))
    except (OSError, AttributeError, ValueError):
        pass                                                # an older system: square corners, as before


class Popups(QObject):
    def __init__(self, app: QApplication):
        super().__init__(app)
        self.native = native_corners()
        from .app_events import events     # the application's one filter (R120)
        events().on((QEvent.Type.Show,), self, self.eventFilter)

    def eventFilter(self, obj, event) -> bool:
        if event.type() != QEvent.Type.Show or not isinstance(obj, QWidget) or not obj.isWindow():
            return False
        kind = obj.windowType()
        if kind not in _KINDS:
            return False
        try:
            if self.native:
                _dwm(obj, kind == Qt.WindowType.ToolTip)
            if _STATE["motion"]:
                obj.setWindowOpacity(0.0)                   # the Show event comes before the window is on screen
                fade = QPropertyAnimation(obj, b"windowOpacity", obj)
                fade.setDuration(FADE_MS)
                fade.setStartValue(0.0)
                fade.setEndValue(1.0)
                fade.setEasingCurve(QEasingCurve.Type.OutCubic)
                fade.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
            elif obj.windowOpacity() < 1.0:
                obj.setWindowOpacity(1.0)
        except RuntimeError:                                # a window going while it shows
            pass
        return False


def install(app: QApplication) -> Popups:
    """The little windows of `app` made one way, once."""
    found = app.findChild(Popups)
    if found is not None:
        return found
    for effect in (Qt.UIEffect.UI_AnimateMenu, Qt.UIEffect.UI_FadeMenu, Qt.UIEffect.UI_AnimateCombo,
                   Qt.UIEffect.UI_AnimateTooltip, Qt.UIEffect.UI_FadeTooltip, Qt.UIEffect.UI_AnimateToolBox):
        QApplication.setEffectEnabled(effect, False)
    return Popups(app)


def set_colours(t: dict) -> None:
    """The theme's line colour for the border the system draws."""
    _STATE["border"] = t["line"]


def set_motion(on: bool) -> None:
    """Fade in, or appear at once (less motion asked for)."""
    _STATE["motion"] = bool(on)
