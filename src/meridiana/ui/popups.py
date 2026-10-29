"""The little windows that come and go (Daniel, 24/10/2026: «finestrelle… compaiono a scatti»): the tooltips, the
menus, the lists of the drop-down fields, the help beside things. One look and one way of coming for all of them.

- **Coming**: Qt's screen-grab effects are off. Menus and lists fade with window opacity (110 ms) unless less
  motion is requested. Tooltips appear once after the short wake-up delay, without an entrance to replay.
- **Corners**: on Windows 11 the system rounds them as it rounds its own (8 px a menu and a popup, 4 px a
  tooltip; Geometry in Windows, learn.microsoft.com), with its shadow and a border in the theme's line colour
  (DwmSetWindowAttribute, DWMWA_WINDOW_CORNER_PREFERENCE and DWMWA_BORDER_COLOR, build 22000 and later). The
  style sheet then leaves their border to the system (`native_corners`). Elsewhere the sheet draws the border,
  and a tooltip, see-through around its corners, the same 4 px radius (R162: on Linux «c'entra proprio poco»).
- **Tooltips** (R162, Daniel 25/10/2026: «una larghezza massima in cui il testo va in colonna ... una bella
  formattazione ai contenuti come fanno programmi tipo VS Code»): every tooltip is Qt's one label (QTipLabel),
  whoever asks for it (a button, an action, a row of a list, a shape on the plan). Its original text is kept for
  Qt's reuse checks; an independent document paints «Name (key)» and the explanation under it as the
  name semibold, the key muted beside it, the explanation in the tooltip's softer ink; one line as it is; wrapped at
  TIP_WIDTH pixels when longer.

`install(app)` once; `set_colours(t)` with the theme; `set_motion(on)` with the preference."""

from __future__ import annotations

import html
import math
import re
import sys

from PySide6 import QtGui
from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, QRect, Qt
from PySide6.QtGui import QAbstractTextDocumentLayout, QColor, QGuiApplication, QKeySequence, QPainter, QPalette, QPen, QTextDocument
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QWidget

from .. import theme_colors
from .cards import default_tokens
from .design import Motion, Radius, Space, Text, Type, text_font

FADE_MS = Motion.FAST
TIP_WIDTH = 340                 # a tooltip's text wraps at this width (R162): some 45 characters of the text
COMBO_WIDTH = 360               # a stretched settings row does not make its list span the whole window
TIP_SOFT, TIP_KEY = 0.22, 0.42  # the explanation and the key: the tooltip's ink this much towards its ground
_STATE = {"border": default_tokens()["line"], "motion": True, "tip": default_tokens()["tooltip_fg"],
          "tip_bg": default_tokens()["tooltip_bg"], "popup_bg": default_tokens()["card"]}
_KINDS = (Qt.WindowType.Popup, Qt.WindowType.ToolTip)
_HEAD = re.compile(r"^(?P<name>.+?) \((?P<key>[^()]+)\)$")
_LAID = "meridiana_tip"         # original text, style key, formatted document text, wrapping and size
_DOCUMENT = "tooltip-document"


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
    """Lay out and paint Qt's own tooltip without replacing the text Qt uses as its identity."""

    def eventFilter(self, label, event) -> bool:
        if isinstance(label, QLabel):
            try:
                if event.type() == QEvent.Type.Resize:
                    lay_out_tip(label)
                elif event.type() == QEvent.Type.Paint:
                    lay_out_tip(label)
                    paint_tip(label)
                    return True
            except RuntimeError:  # The native tooltip can disappear during its last event.
                return False
        return False


def lay_out_tip(label: QLabel) -> None:
    """Keep the original plain/rich text unchanged: Qt can then reuse it on the same target.

    Replacing plain text with formatted HTML made every repeated showText request look like new content,
    rebuilding its layout as the pointer moved. A separate document owns typography and colour instead.
    """
    text = label.text()
    font = text_font(Text.BODY)
    key = (text, font.key(), _STATE["tip"], _STATE["tip_bg"], _STATE["border"])
    laid = label.property(_LAID)
    document = label.findChild(QTextDocument, _DOCUMENT)
    if laid is None or laid[1] != key or document is None:
        rich = tip_html(text)
        if document is None:
            document = QTextDocument(label)
            document.setObjectName(_DOCUMENT)
        document.setDefaultFont(font)
        document.setDocumentMargin(0)
        document.setTextWidth(-1)
        document.setHtml(f'<div style="color:{_STATE["tip"]}">{rich}</div>')
        natural = math.ceil(document.idealWidth()) + 2 * Space.M
        wrap = natural > TIP_WIDTH
        width = min(TIP_WIDTH, natural)
        document.setTextWidth(max(1, width - 2 * Space.M))
        size = label.size()
        size.setWidth(width)
        size.setHeight(math.ceil(document.size().height()) + 2 * Space.S)
        label.setProperty(_LAID, (text, key, rich, wrap, size))
    else:
        _original, _key, _rich, wrap, size = laid
    label.setWordWrap(wrap)
    if label.size() != size:
        label.resize(size)
    screen = label.screen()
    if screen is not None:
        room, at = screen.availableGeometry(), QRect(label.pos(), size)
        x = min(at.x(), room.right() + 1 - size.width())
        y = min(at.y(), room.bottom() + 1 - size.height())
        if (x, y) != (at.x(), at.y()):
            label.move(max(room.x(), x), max(room.y(), y))


def paint_tip(label: QLabel) -> None:
    """Paint an independent tooltip surface and text, unaffected by a source label's style sheet."""
    document = label.findChild(QTextDocument, _DOCUMENT)
    if document is None:
        return
    painter = QPainter(label)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(_STATE["border"]), 1))
    painter.setBrush(QColor(_STATE["tip_bg"]))
    painter.drawRoundedRect(label.rect().toRectF().adjusted(0.5, 0.5, -0.5, -0.5), Radius.INNER, Radius.INNER)
    painter.translate(Space.M, Space.S)
    context = QAbstractTextDocumentLayout.PaintContext()
    context.palette.setColor(QPalette.ColorRole.Text, QColor(_STATE["tip"]))
    document.documentLayout().draw(painter, context)
    painter.end()


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
        dark = ctypes.c_int(QColor(_STATE["popup_bg"]).lightness() < 128)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))
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
        # Wayland gives a window no opacity of its own: there each little window comes at once (it printed «This
        # plugin does not support setting window opacity» at every one, and faded nothing)
        self.fades = not QGuiApplication.platformName().startswith("wayland")
        self.tips = TipLayout(self)
        from .app_events import events     # the application's one filter (R120)
        events().on((QEvent.Type.Show,), self, self.eventFilter)
        events().on((QEvent.Type.Polish,), self, self._polished)
        events().on((QEvent.Type.FocusIn,), self, self._combo_focused)

    def _combo_focused(self, obj, event) -> bool:
        """Refresh the hidden list's margins before Qt measures a focused combo's popup.

        Qt caches PM_MenuVMargin in its container when the combo is made, then measures the popup with the
        current value. Our focus border reduces field padding by one pixel: stale margins leave the list two
        pixels short, which adds a scroll strip and clips the last choice even with only four choices.
        A style-change event lets Qt update its own margins, before showing or restricting it to the screen.
        """
        if isinstance(obj, QComboBox):
            popup = obj.view().window()
            if not popup.isVisible():
                QApplication.sendEvent(popup, QEvent(QEvent.Type.StyleChange))
                self._size_combo(obj)
        return False

    @staticmethod
    def _size_combo(combo: QComboBox) -> None:
        """Fit the list to its choices and a bounded field width before Qt places it on screen."""
        view = combo.view()
        popup = view.window()
        natural = view.sizeHintForColumn(combo.modelColumn()) + 2 * Space.XS + Space.XL
        screen = combo.screen()
        limit = min(COMBO_WIDTH, screen.availableGeometry().width()) if screen is not None else COMBO_WIDTH
        width = min(limit, max(natural, min(combo.width(), limit)))
        popup.setMaximumWidth(width)
        popup.resize(width, popup.height())
        palette = popup.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(_STATE["popup_bg"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(_STATE["popup_bg"]))
        popup.setPalette(palette)

    def _polished(self, obj, event) -> bool:
        """A tooltip's label being made (Qt polishes it in its constructor, before its window exists): see-through
        around its corners where the system does not round them, and watched for its texts (R162)."""
        if isinstance(obj, QLabel) and obj.isWindow() and obj.windowType() == Qt.WindowType.ToolTip:
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
            if kind == Qt.WindowType.Popup and isinstance(obj.parentWidget(), QComboBox):
                self._size_combo(obj.parentWidget())
            if self.native:
                _dwm(obj, kind == Qt.WindowType.ToolTip)
            if kind == Qt.WindowType.ToolTip:
                # A tooltip appears once after its short wake-up delay, with no entrance to replay.
                if obj.windowOpacity() < 1.0:
                    obj.setWindowOpacity(1.0)
                return False
            if _STATE["motion"] and self.fades:
                obj.setWindowOpacity(0.0)                   # the Show event comes before the window is on screen
                fade = QPropertyAnimation(obj, b"windowOpacity", obj)
                fade.setDuration(FADE_MS)
                fade.setStartValue(0.0)
                fade.setEndValue(1.0)
                fade.setEasingCurve(QEasingCurve.Type.OutCubic)
                fade.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
            elif self.fades and obj.windowOpacity() < 1.0:
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
    _STATE["popup_bg"] = t["card"]


def set_motion(on: bool) -> None:
    """Fade in, or appear at once (less motion asked for)."""
    _STATE["motion"] = bool(on)
