"""The scroll bars (R100, Daniel 25/10/2026: «Le varie barre di scorrimento, quando compaiono, spostano tutti i
contenuti in modo fastidioso. Forse deve occupare meno spazio e avere spazio già assegnato?»; and later «per semplici
ridimensionamenti ci sono notevoli scombinamenti dovuti soprattutto alla comparsa della barra di scorrimento»).

A thin thumb (Size.THUMB, 6 px) and nothing else, no groove and no arrows, in a room of Size.SCROLLBAR (10 px) that a
list, a form or a text keeps on its right whether it scrolls or not: the content never moves when the bar comes or
goes. While there is nothing to scroll the room stays empty.

Why not Qt's transient bars, laid over the content as VS Code's (tried on 25/10/2026): QStyleSheetStyle answers
SH_ScrollBar_Transient with 0 as soon as a rule of the sheet reaches the bar; drawn by a style instead, the bar lay
over the rows' right end (the marks of the project's tree, the «Correggi» of the checks) and took their clicks; and
the tree views set their viewport's margins themselves at every layout, so no room could be kept beside an overlay.

`ScrollStyle` is the application's style: Fusion, with the scroll bars drawn here. The global sheet has no rule that
reaches a QScrollBar (one would make QStyleSheetStyle draw the bar itself, with Qt's arrows)."""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette
from PySide6.QtWidgets import (QAbstractScrollArea, QGraphicsView, QPlainTextEdit, QProxyStyle, QStyle,
                               QStyleFactory, QTextEdit)

from .design import Size, Space

THUMB = Size.THUMB
END = Space.XS                  # the thumb's way from the bar's ends: off a card's rounded corners


def keeps_room(area: QAbstractScrollArea) -> bool:
    """Whether `area` keeps the bar's room on its right: a list, a form, a text to read; not the plan (it pans), not
    a little window's list (a drop-down measures itself), not a field one types into."""
    if isinstance(area, QGraphicsView):
        return False
    if isinstance(area, (QTextEdit, QPlainTextEdit)) and not area.isReadOnly():
        return False
    flags = area.window().windowFlags()
    if flags & Qt.WindowType.Popup == Qt.WindowType.Popup or flags & Qt.WindowType.ToolTip == Qt.WindowType.ToolTip:
        return False
    return area.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded


def keep_room(area: QAbstractScrollArea) -> None:
    """The vertical bar always there, so its room is kept (drawn empty while nothing scrolls)."""
    if keeps_room(area):
        area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)


class ScrollStyle(QProxyStyle):
    """Fusion with Meridiana's scroll bars. `tokens` are the theme's colours (set by ui/theme.Theme); without them
    the palette's (Mid, PlaceholderText, Text)."""

    def __init__(self, base=None):
        super().__init__(base if base is not None else QStyleFactory.create("Fusion"))
        self.tokens: dict = {}

    # the standard icons as the window's symbols (R154, Daniel 25/10/2026: «non hai applicato i simboli nuovi
    # dappertutto»: on Linux OK and Cancel had the desktop theme's green arrow and red cross); a button with no
    # symbol of its own has no icon, the same on every system
    SYMBOLS = {
        QStyle.StandardPixmap.SP_DialogOkButton: "check", QStyle.StandardPixmap.SP_DialogApplyButton: "check",
        QStyle.StandardPixmap.SP_DialogYesButton: "check", QStyle.StandardPixmap.SP_DialogYesToAllButton: "check",
        QStyle.StandardPixmap.SP_DialogCancelButton: "cross", QStyle.StandardPixmap.SP_DialogNoButton: "cross",
        QStyle.StandardPixmap.SP_DialogNoToAllButton: "cross", QStyle.StandardPixmap.SP_DialogCloseButton: "cross",
        QStyle.StandardPixmap.SP_DialogAbortButton: "cross", QStyle.StandardPixmap.SP_DialogDiscardButton: "cross",
        QStyle.StandardPixmap.SP_MessageBoxInformation: "info", QStyle.StandardPixmap.SP_MessageBoxQuestion: "info",
        QStyle.StandardPixmap.SP_MessageBoxWarning: "warning", QStyle.StandardPixmap.SP_MessageBoxCritical: "error",
    }
    PLAIN = {QStyle.StandardPixmap.SP_DialogSaveButton, QStyle.StandardPixmap.SP_DialogOpenButton,
             QStyle.StandardPixmap.SP_DialogResetButton, QStyle.StandardPixmap.SP_DialogHelpButton,
             QStyle.StandardPixmap.SP_DialogRetryButton, QStyle.StandardPixmap.SP_DialogIgnoreButton,
             QStyle.StandardPixmap.SP_DialogSaveAllButton}

    def standardIcon(self, standard, option=None, widget=None):
        if standard in self.SYMBOLS:
            from . import symbols
            return symbols.icon(self.SYMBOLS[standard])
        if standard in self.PLAIN:
            return QIcon()
        return super().standardIcon(standard, option, widget)

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_DialogButtonBox_ButtonsHaveIcons:
            return 1                                    # the symbols on Windows too: one look on every system
        return super().styleHint(hint, option, widget, returnData)

    def pixelMetric(self, metric, option=None, widget=None):
        if metric == QStyle.PixelMetric.PM_ScrollBarExtent:
            return Size.SCROLLBAR
        if metric == QStyle.PixelMetric.PM_ScrollBarSliderMin:
            return Size.CONTROL
        if metric == QStyle.PixelMetric.PM_ScrollView_ScrollBarSpacing:
            return 0
        return super().pixelMetric(metric, option, widget)

    def polish(self, target):
        out = super().polish(target)
        if isinstance(target, QAbstractScrollArea):
            keep_room(target)
        return out

    @staticmethod
    def _groove(opt) -> QRect:
        r = opt.rect
        if opt.orientation == Qt.Orientation.Horizontal:
            return r.adjusted(END, 0, -END, 0)
        return r.adjusted(0, END, 0, -END)

    def _slider(self, opt) -> QRect:
        groove = self._groove(opt)
        horizontal = opt.orientation == Qt.Orientation.Horizontal
        length = groove.width() if horizontal else groove.height()
        span = opt.maximum - opt.minimum
        size = length if span <= 0 else max(Size.CONTROL, round(length * opt.pageStep / (span + opt.pageStep)))
        size = min(size, length)
        at = QStyle.sliderPositionFromValue(opt.minimum, opt.maximum, opt.sliderPosition, max(0, length - size),
                                            opt.upsideDown) if span > 0 else 0
        if horizontal:
            return QRect(groove.x() + at, groove.y(), size, groove.height())
        return QRect(groove.x(), groove.y() + at, groove.width(), size)

    def subControlRect(self, cc, opt, sc, widget=None):
        if cc != QStyle.ComplexControl.CC_ScrollBar:
            return super().subControlRect(cc, opt, sc, widget)
        SC = QStyle.SubControl
        groove, slider = self._groove(opt), self._slider(opt)
        horizontal = opt.orientation == Qt.Orientation.Horizontal
        if sc == SC.SC_ScrollBarGroove:
            return groove
        if sc == SC.SC_ScrollBarSlider:
            return slider
        if sc == SC.SC_ScrollBarSubPage:
            return (QRect(groove.left(), groove.top(), slider.left() - groove.left(), groove.height()) if horizontal
                    else QRect(groove.left(), groove.top(), groove.width(), slider.top() - groove.top()))
        if sc == SC.SC_ScrollBarAddPage:
            return (QRect(slider.right() + 1, groove.top(), groove.right() - slider.right(), groove.height())
                    if horizontal else
                    QRect(groove.left(), slider.bottom() + 1, groove.width(), groove.bottom() - slider.bottom()))
        return QRect()                  # no arrows, no first and last

    def colour(self, opt, on_thumb: bool, pressed: bool) -> QColor:
        t = self.tokens
        if t:
            return QColor(t["text2"] if pressed else t["muted"] if on_thumb else t["line"])
        role = (QPalette.ColorRole.Text if pressed else QPalette.ColorRole.PlaceholderText if on_thumb
                else QPalette.ColorRole.Mid)
        return opt.palette.color(QPalette.ColorGroup.Active, role)

    def drawComplexControl(self, cc, opt, p, widget=None):
        if cc != QStyle.ComplexControl.CC_ScrollBar:
            super().drawComplexControl(cc, opt, p, widget)
            return
        if opt.maximum <= opt.minimum:
            return                      # nothing to scroll: the room stays empty
        slider = QRectF(self._slider(opt))
        horizontal = opt.orientation == Qt.Orientation.Horizontal
        across = slider.height() if horizontal else slider.width()
        inset = max(0.0, (across - THUMB) / 2)
        thumb = slider.adjusted(0, inset, 0, -inset) if horizontal else slider.adjusted(inset, 0, -inset, 0)
        S = QStyle.StateFlag
        active = bool(opt.activeSubControls & QStyle.SubControl.SC_ScrollBarSlider)
        on_thumb = bool(opt.state & S.State_MouseOver) and active
        pressed = bool(opt.state & S.State_Sunken) and active
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.colour(opt, on_thumb, pressed))
        p.drawRoundedRect(thumb, THUMB / 2, THUMB / 2)
        p.restore()


def install(app) -> ScrollStyle:
    """The application's style, once (setting a style polishes every widget again); owned by the application, as
    style.shared(): owned by Python alone, it may be dropped at exit while the windows still use it."""
    found = getattr(app, "_scroll_style", None)
    if isinstance(found, ScrollStyle):
        return found
    style = ScrollStyle()
    style.setParent(app)
    app.setStyle(style)
    app._scroll_style = style
    return style
