"""The little windows that come and go (Daniel, 24/10/2026: «finestrelle… compaiono a scatti»): the tooltips, the
menus, the lists of the drop-down fields, the help beside things. One look and one way of coming for all of them.

- **Coming**: Qt's own effects fade a tooltip by grabbing the screen behind it and blending it on a timer, and
  roll the menus open: at 200 % they stutter. They are turned off, and each little window fades in with its
  window opacity instead (110 ms, composited by the system), unless less motion is asked for.
- **Corners**: on Windows 11 the system rounds them as it rounds its own (8 px a menu and a popup, 4 px a
  tooltip; Geometry in Windows, learn.microsoft.com), with its shadow and a border in the theme's line colour
  (DwmSetWindowAttribute, DWMWA_WINDOW_CORNER_PREFERENCE and DWMWA_BORDER_COLOR, build 22000 and later). The
  style sheet then leaves their border to the system (`native_corners`). Elsewhere the sheet draws the border,
  and a tooltip, see-through around its corners, the same 4 px radius (R162: on Linux «c'entra proprio poco»).
- **Tooltips** (R162, Daniel 25/10/2026: «una larghezza massima in cui il testo va in colonna ... una bella
  formattazione ai contenuti come fanno programmi tipo VS Code»): every tooltip is Qt's one label (QTipLabel),
  whoever asks for it (a button, an action, a row of a list, a shape on the plan). Taken as it is made, it is laid
  out again whenever Qt gives it a text: «Name (key)» and the explanation under it (the window's `_tip_head`) as the
  name semibold, the key muted beside it, the explanation in the tooltip's softer ink; one line as it is; wrapped at
  TIP_WIDTH pixels when longer.

`install(app)` once; `set_colours(t)` with the theme; `set_motion(on)` with the preference."""

from __future__ import annotations

import html
import re
import sys

from PySide6 import QtGui
from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, QRect, Qt
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from .. import theme_colors
from .cards import default_tokens
from .design import Motion, Space, Type

FADE_MS = Motion.FAST
TIP_WIDTH = 340                 # a tooltip's text wraps at this width (R162): some 45 characters of the text
TIP_SOFT, TIP_KEY = 0.22, 0.42  # the explanation and the key: the tooltip's ink this much towards its ground
_STATE = {"border": default_tokens()["line"], "motion": True, "tip": default_tokens()["tooltip_fg"],
          "tip_bg": default_tokens()["tooltip_bg"]}
_KINDS = (Qt.WindowType.Popup, Qt.WindowType.ToolTip)
_HEAD = re.compile(r"^(?P<name>.+?) \((?P<key>[^()]+)\)$")
_LAID = "meridiana_tip"         # the label's property: (its text, wrapped, its size) as last laid out


def _is_key(text: str) -> bool:
    """Whether `text` is a key as the window writes it («Ctrl+1», «F1», «W»), not words in brackets."""
    native = QKeySequence.SequenceFormat.NativeText
    seq = QKeySequence.fromString(text, native)
    return not seq.isEmpty() and seq.toString(native) == text


def tip_html(text: str, ink: str | None = None, ground: str | None = None) -> str:
    """A tooltip's text as the label shows it: «Name (key)» on the first line and the explanation on the next ones
    as the name (semibold when an explanation follows), the key muted beside it, the explanation softer under it;
    a text already rich as it is."""
    if QtGui.Qt.mightBeRichText(text):                    # (QtGui's Qt: QtCore's has not this one)
        return text
    ink = ink or _STATE["tip"]
    ground = ground or _STATE["tip_bg"]
    lines = [line.strip() for line in text.split("\n")]
    head, body = lines[0], [line for line in lines[1:] if line]
    m = _HEAD.match(head)
    name, key = (m["name"], m["key"]) if m and _is_key(m["key"]) else (head, "")
    soft, muted = theme_colors.mix(ink, ground, TIP_SOFT), theme_colors.mix(ink, ground, TIP_KEY)
    weight = f"font-weight:{Type.SEMIBOLD};" if body else ""
    out = f'<p style="margin:0;{weight}">{html.escape(name)}'
    if key:
        out += f'&nbsp;&nbsp;<span style="color:{muted};font-weight:{Type.REGULAR}">{html.escape(key)}</span>'
    out += "</p>"
    for line in body:
        out += f'<p style="margin:0;margin-top:{Space.XS}px;color:{soft}">{html.escape(line)}</p>'
    return out


class TipLayout(QObject):
    """Watches a tooltip's label from when it is made: every text Qt gives it laid out again (`tip_html`), wrapped
    at TIP_WIDTH, kept on the screen."""

    def eventFilter(self, label, event) -> bool:
        if event.type() == QEvent.Type.Resize and isinstance(label, QLabel):
            try:
                lay_out_tip(label)
            except RuntimeError:                            # the label going while it resizes
                pass
        return False


def lay_out_tip(label: QLabel) -> None:
    """The label's text laid out again and its size set; its size set back when Qt measures it again its way (it
    does, after placing a new tooltip: QTBUG-64550, in QToolTip::showText)."""
    text = label.text()
    laid = label.property(_LAID)
    if laid is not None and text == laid[0]:
        rich, wrap, size = laid
        if label.size() == size and label.wordWrap() == wrap:
            return                                          # its own size, being set
    else:
        rich = tip_html(text)
        # its padding here, once: Qt adds the sheet's padding to its own margin, twice the room (42 px a line)
        label.setMargin(0)
        label.setIndent(0)
        label.setContentsMargins(Space.M, Space.S, Space.M, Space.S)          # a line: 28 px, a control's height
        label.setText(rich)
        label.setWordWrap(False)
        size = label.sizeHint()
        wrap = size.width() > TIP_WIDTH
        if wrap:                                            # wrapped: as wide as the width, as tall as it takes
            label.setWordWrap(True)
            size.setWidth(TIP_WIDTH)
            size.setHeight(label.heightForWidth(TIP_WIDTH))
        label.setProperty(_LAID, (rich, wrap, size))
    label.setWordWrap(wrap)
    label.resize(size)
    screen = label.screen()
    if screen is not None:                                  # where Qt put it for its first size: on the screen
        room, at = screen.availableGeometry(), QRect(label.pos(), size)
        x = min(at.x(), room.right() + 1 - size.width())
        y = min(at.y(), room.bottom() + 1 - size.height())
        if (x, y) != (at.x(), at.y()):
            label.move(max(room.x(), x), max(room.y(), y))


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
        self.tips = TipLayout(self)
        from .app_events import events     # the application's one filter (R120)
        events().on((QEvent.Type.Show,), self, self.eventFilter)
        events().on((QEvent.Type.Polish,), self, self._polished)

    def _polished(self, obj, event) -> bool:
        """A tooltip's label being made (Qt polishes it in its constructor, before its window exists): see-through
        around its corners where the system does not round them, and watched for its texts (R162)."""
        if isinstance(obj, QLabel) and obj.isWindow() and obj.windowType() == Qt.WindowType.ToolTip:
            if not self.native:
                obj.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            obj.installEventFilter(self.tips)
        return False

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
    """The theme's line colour for the border the system draws; the tooltip's inks."""
    _STATE["border"] = t["line"]
    _STATE["tip"], _STATE["tip_bg"] = t["tooltip_fg"], t["tooltip_bg"]


def set_motion(on: bool) -> None:
    """Fade in, or appear at once (less motion asked for)."""
    _STATE["motion"] = bool(on)
