"""The few things Meridiana draws itself in Qt's style (the target of 24/10/2026, docs/studio/19-grafica): the
groups as in the mockups' C3, a frame with a header band the whole width (a style sheet draws a group's title as
a tab only), and the menus without their mnemonics underlined (Windows shows them only with Alt; Fusion always,
and the row of menus looked like a page of links). Alt and its letters work as before.

The style is set on those widgets only (`Group`, `quiet_menus`). It is the application's style with these things more,
never another one: under the global sheet a style set on a widget goes down to its children (R339)."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPointF, QRect, QRectF, QSize, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QGroupBox, QHBoxLayout, QMenu, QStyle, QVBoxLayout, QWidget

from .. import theme_colors
from .design import Icon, Line, Motion, Radius, Space
from .scrollbars import ScrollStyle

GROUP_RADIUS = Radius.CONTROL   # a group is a control's depth (ui/design.py)
HEAD_PAD = Space.M              # the header band over the title's line of text
TITLE_X = Line.TEXT_INSET       # the title from the group's left edge, as a field's text
CHEVRON = 10                    # the fold's sign: a chevron this wide at the title's left (R287)
CHEVRON_GAP = Space.S           # between the chevron and the title
QWIDGETSIZE_MAX = (1 << 24) - 1


def is_nested(widget: QWidget) -> bool:
    """A group inside a group draws no card (R343); a plain QGroupBox is never asked."""
    return bool(getattr(widget, "nested", False))


def title_x(widget: QWidget) -> int:
    """Where a group's title starts: after the fold's chevron when the group folds; a nested group's on its parent's
    text, the chevron's edge there."""
    return (0 if is_nested(widget) else TITLE_X) + (CHEVRON + CHEVRON_GAP if getattr(widget, "collapsible", False) else 0)


class MeridianaStyle(ScrollStyle):
    """The application's style (scrollbars.ScrollStyle), with the groups of C3 and without the menus' underlines.
    Under a global sheet a style set on a group goes down to everything inside it: when this was plain Fusion, every
    area inside a group had Fusion's bars with their arrows and no room kept (R339). `tokens` are the theme's colours
    (set by ui/theme.Theme at each change)."""

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_UnderlineShortcut:
            return 0
        return super().styleHint(hint, option, widget, returnData)

    @staticmethod
    def head(widget: QWidget) -> int:
        return QFontMetrics(widget.font()).height() + HEAD_PAD

    def subControlRect(self, cc, opt, sc, widget=None):
        if cc == QStyle.ComplexControl.CC_GroupBox and isinstance(widget, QGroupBox):
            r, h = opt.rect, self.head(widget)
            if sc == QStyle.SubControl.SC_GroupBoxFrame:
                return QRect(r)
            if sc == QStyle.SubControl.SC_GroupBoxLabel:
                x = title_x(widget)
                return QRect(r.left() + x, r.top(), max(0, r.width() - x - TITLE_X), h)
            if sc == QStyle.SubControl.SC_GroupBoxContents:
                return r.adjusted(0, h, 0, 0) if is_nested(widget) else r.adjusted(1, h, -1, -1)
            if sc == QStyle.SubControl.SC_GroupBoxCheckBox:
                return QRect()
        return super().subControlRect(cc, opt, sc, widget)

    def drawComplexControl(self, cc, opt, p, widget=None):
        if cc == QStyle.ComplexControl.CC_GroupBox and isinstance(widget, QGroupBox) and self.tokens:
            t = self.tokens
            r = QRectF(opt.rect).adjusted(0.5, 0.5, -0.5, -0.5)
            h = self.head(widget)
            if is_nested(widget):
                self._nested(p, widget, r, h)
                return
            frame = QPainterPath()
            frame.addRoundedRect(r, GROUP_RADIUS, GROUP_RADIUS)
            p.save()
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setClipPath(frame)
            band = t["line_soft"]
            if getattr(widget, "hot", False):           # the pointer on the header of a group that folds (R160)
                band = theme_colors.state(t, band, theme_colors.HOVER)
            p.fillRect(QRectF(r.left(), r.top(), r.width(), h), QColor(band))
            p.setClipping(False)
            p.setPen(QPen(QColor(t["line"]), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(frame)
            x = title_x(widget)
            if getattr(widget, "collapsible", False):
                self._chevron(p, QPointF(r.left() + TITLE_X + CHEVRON / 2, r.top() + h / 2),
                              float(getattr(widget, "progress", 1.0)), QColor(t["muted"]))
            font = QFont(widget.font())
            font.setWeight(QFont.Weight.DemiBold)
            p.setFont(font)
            p.setPen(QColor(t["text"] if widget.isEnabled() else t["muted"]))
            room = r.width() - x - TITLE_X
            title = QFontMetrics(font).elidedText(widget.title(), Qt.TextElideMode.ElideRight, int(max(0.0, room)))
            p.drawText(QRectF(r.left() + x, r.top(), room, h),
                       int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), title)
            p.restore()
            return
        super().drawComplexControl(cc, opt, p, widget)

    def _nested(self, p: QPainter, widget: QWidget, r: QRectF, h: int) -> None:
        """A group inside a group (R343): the title on a thin line, nothing behind it; the pointer on a header that
        folds darkens its chevron, no fill."""
        t = self.tokens
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(t["line"]), Line.HAIR))
        p.drawLine(QPointF(0.0, h - 0.5), QPointF(float(widget.width()), h - 0.5))
        x = title_x(widget)
        if getattr(widget, "collapsible", False):
            self._chevron(p, QPointF(CHEVRON / 2, h / 2), float(getattr(widget, "progress", 1.0)),
                          QColor(t["text"] if getattr(widget, "hot", False) else t["muted"]))
        font = QFont(widget.font())
        font.setWeight(QFont.Weight.DemiBold)
        p.setFont(font)
        p.setPen(QColor(t["text"] if widget.isEnabled() else t["muted"]))
        room = max(0.0, r.width() - x)
        title = QFontMetrics(font).elidedText(widget.title(), Qt.TextElideMode.ElideRight, int(room))
        p.drawText(QRectF(float(x), 0.0, room, h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), title)
        p.restore()

    @staticmethod
    def _chevron(p: QPainter, centre: QPointF, progress: float, colour: QColor) -> None:
        """The fold's sign (R287): a chevron of the icons' stroke, pointing right when the group is closed and down
        when open, turned by the fold's progress (0 closed, 1 open) so that it rotates with the movement."""
        p.save()
        p.translate(centre)
        p.rotate(-90.0 * (1.0 - max(0.0, min(1.0, progress))))
        pen = QPen(colour, Icon.STROKE)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        half = CHEVRON / 2 - 1.5
        p.drawPolyline([QPointF(-half, -half / 2), QPointF(0.0, half / 2), QPointF(half, -half / 2)])
        p.restore()


_SHARED: list[MeridianaStyle] = []


def shared() -> MeridianaStyle:
    """The one style of the process (a widget does not own the style set on it: this list keeps it), owned by the
    application: owned by Python alone, the interpreter may drop it at exit while the windows still use it (a crash
    as the process ended in 2 to 6 runs in 8 in qt-app-template, none in 8 since)."""
    if not _SHARED:
        style = MeridianaStyle()
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            style.setParent(app)
            _watch_fields(style)
        _SHARED.append(style)
    return _SHARED[0]


def _watch_fields(owner) -> None:
    """Every number and date field of the process gets its text inset when Qt polishes it (R283): the sheet's
    padding never reaches the line edit inside a QAbstractSpinBox, and `pad_fields` was called place by place
    (the window once, the properties' pages, the gallery), so a field made later in a dialog (the canopy, the
    templates, the site) stood with its text on the edge. One handler on the application's filter (ui/app_events),
    alive with the style."""
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QAbstractSpinBox, QCheckBox, QRadioButton
    from .app_events import events

    def polished(obj, _event) -> bool:
        if isinstance(obj, QAbstractSpinBox):
            pad_fields(obj)
        elif isinstance(obj, (QCheckBox, QRadioButton)) and len(obj.text()) > LONG_TEXT:
            wrap_check(obj)                         # a long checkbox made later (the Settings, a dialog) as well
        return False

    events().on((QEvent.Type.Polish,), owner, polished)


class EmptyState(QWidget):
    """What a card says while it has nothing to show (R321, Daniel 02/11/2026: the report's «Calcola la producibilità
    per vedere la relazione...» stood half way down a blank card, against its left edge): the words in the middle
    of the card, in the catalogue's secondary text, in a column no wider than reading asks (`Size.READING`), the
    card's margins around them, and below them the command that fills the card when there is one («Calcola»).
    One for every empty card: the report's preview and every chart (`charts.Chart.message`). `text()` and
    `setText()` as a label's."""

    def __init__(self, text: str = "", parent=None):
        from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy
        from .design import Size, Text, set_text
        super().__init__(parent)
        self.setObjectName("empty-state")
        box = QVBoxLayout(self)
        box.setContentsMargins(Space.XL, Space.L, Space.XL, Space.L)
        box.setSpacing(Space.M)
        box.addStretch(1)
        self.words = set_text(QLabel(text), Text.SECONDARY)
        self.words.setObjectName("empty-state-text")
        self.words.setWordWrap(True)
        self.words.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.words.setMaximumWidth(Size.READING)
        # as wide as the card lets it, up to the reading width, between two stretches (an alignment flag instead
        # makes a wrapped label take Qt's guess of its width: a narrow column of three lines)
        self.words.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.words, 100)
        row.addStretch(1)
        box.addLayout(row)
        self.button = QPushButton()
        self.button.hide()
        self.button.clicked.connect(self._run)
        box.addWidget(self.button, 0, Qt.AlignmentFlag.AlignHCenter)
        box.addStretch(1)
        self._action = None

    def text(self) -> str:
        return self.words.text()

    def setText(self, text: str) -> None:
        self.words.setText(text)

    def set_action(self, action=None, text: str = "") -> None:
        """The command below the words (a QAction: its words without the accelerator, or `text`); none hides it."""
        self._action = action
        if action is not None:
            from .. import shortcuts
            self.button.setText(text or shortcuts.plain(action.text()))
        self.button.setVisible(action is not None)

    def _run(self) -> None:
        if self._action is not None and self._action.isEnabled():
            self._action.trigger()


_FOLDED: dict[str, bool] = {}   # the groups closed in this session, by kind (their help id, else their title)


class Group(QGroupBox):
    """A group of fields as C3: a frame, the title in a band the whole width (the shared style draws it). A long
    title is shortened, never widens the group: in a card that scrolls it pushed the fields past the card's edge
    (the Balance's «Energia acquistata (tutti i costi variabili, imposte comprese)», 25/10/2026).

    It folds (R287, Daniel 30/10/2026: «tutte le sottosezioni nella barra di destra devono poter essere collassate»):
    a click on its header closes it to the header alone and opens it again, a chevron before the title says which,
    the «?» stays. The caller lays its fields out on the group as always (`QFormLayout(group)`); the group then
    moves that layout, with its fields, into a body of its own, so that the body can be hidden whole: a hidden body
    takes the keyboard from none of its fields (Tab skips them) and leaves the group as tall as its header, with no
    hole. The height moves with `Motion.NORMAL` and the curve of every movement (motion.py); with «less motion»
    the body is hidden or shown at once. Which kinds of group are closed is remembered for the session
    (`_FOLDED`, by help id or title), so that a page built again, or the same group of another object, comes
    back as it was left.

    A group inside a group is no card (R343, Daniel 03/11/2026: «non mi piacciono le schede dentro le schede»): the
    one rule, here and in the style, for every group inside another at any depth: no frame and no band, the title in
    its strong weight on a thin line, the content on the parent's text with no margin of its own; the chevron stays
    when it folds. `nested` says it, nobody asks for it."""

    folded = Signal(bool)           # closed (True) or opened, once the movement is over

    def __init__(self, title: str = "", parent=None, collapsible: bool = True):
        super().__init__(title, parent)
        self.collapsible = collapsible
        self.expanded = True
        self.progress = 1.0             # the chevron's turn: 1 open, 0 closed
        self.hot = False                # the pointer over the header
        self._body: QWidget | None = None
        self._fold: _Fold | None = None
        self._pressed = False
        self._remembered = False
        self._as_nested = False         # what the margins were last set for (_settle_nesting)
        self._nest_layout = None
        self._own_margins = None
        self.setStyle(shared())
        if collapsible:
            self.setMouseTracking(True)

    # the body

    def event(self, e) -> bool:
        if e.type() == QEvent.Type.ChildAdded and self.collapsible and self._body is None:
            # a layout given to the group (QFormLayout(group)): adopted once it is whole, on the next turn
            QTimer.singleShot(0, self, self._adopt)
        return super().event(e)

    def _adopt(self) -> None:
        """The caller's layout moved into the body, with its widgets (Qt lets a widget take a layout off another)."""
        if self._body is not None or not self.collapsible:
            return
        inner = QGroupBox.layout(self)
        if inner is None:
            return
        body = QWidget(self)
        body.setObjectName("group-body")
        # as wide as the group's contents before the fields come in: a new widget is 100 px wide, and a wrapped
        # label laid out at that width once kept its height (grow_label's minimum, and QLabel's heightForWidth never
        # goes under it): the Plant's groups came out three times as tall as their text (30/10/2026)
        body.setGeometry(self.contentsRect())
        body.setLayout(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(body)
        self._body = body
        self._remember()

    def body(self) -> QWidget | None:
        """The widget holding the group's fields, None until a layout was given."""
        self._adopt()
        return self._body

    def layout(self):
        """The caller's layout, wherever it lives now."""
        self._adopt()
        return self._body.layout() if self._body is not None else super().layout()

    def _folded_height(self) -> int | None:
        """The group's height while its body is closed or moving: the header, the frame's line under it and what
        the body may take now; None when the body is open and still (the layout's own hint then)."""
        body = self._body
        if body is None:
            return None
        frame = 0 if self.nested else 1
        if body.isHidden():
            return MeridianaStyle.head(self) + frame
        if self._fold is not None and self._fold.running:
            return MeridianaStyle.head(self) + frame + body.maximumHeight()
        return None

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        folded = self._folded_height()
        return hint if folded is None else QSize(hint.width(), folded)

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        folded = self._folded_height()
        if folded is not None:
            hint = QSize(hint.width(), folded)
        # asked from inside a layout pass: no adoption here
        lay = self._body.layout() if self._body is not None else QGroupBox.layout(self)
        if lay is None:
            return hint
        m = self.contentsMargins()
        inside = lay.minimumSize().width() + m.left() + m.right() + 2
        return QSize(min(hint.width(), max(inside, 2 * TITLE_X + 40)), hint.height())

    # the fold

    def kind(self) -> str:
        """What the remembered state is kept under: the help id of the group, else its title."""
        hid = self.property("help")
        return hid if isinstance(hid, str) and hid else self.title()

    def _remember(self) -> None:
        """The state this kind of group was left in, applied once, when the group is first on screen."""
        if self._remembered or self._body is None or self.isHidden():
            return
        self._remembered = True
        wanted = not _FOLDED.get(self.kind(), False)
        if wanted != self.expanded:
            self.set_expanded(wanted, ms=0)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if self.collapsible:
            self._adopt()
            self._remember()
        self._settle_nesting()

    # a group inside a group (R343)

    @property
    def nested(self) -> bool:
        """Whether this group stands inside another, at any depth: through a page, a scroll area, a stack."""
        parent = self.parentWidget()
        while parent is not None:
            if isinstance(parent, QGroupBox):
                return True
            parent = parent.parentWidget()
        return False

    def _settle_nesting(self) -> None:
        """The margins the place asks for, over whatever the maker gave: a nested group has none but the air under
        its line, and gets its own back when it is a card again (the Properties, lent to the Plant and returned).
        Asked when the group is shown, moved, or about to come out of a fold."""
        now = self.nested
        lay = self._body.layout() if self._body is not None else QGroupBox.layout(self)
        changed = now != self._as_nested
        if not changed and (not now or lay is None or lay is self._nest_layout):
            return
        self._as_nested = now
        if changed:         # the contents' rect of QGroupBox, read again by Qt on a change of style
            QApplication.sendEvent(self, QEvent(QEvent.Type.StyleChange))
        if lay is not None:
            if now:
                if self._nest_layout is not lay:
                    self._own_margins, self._nest_layout = lay.contentsMargins(), lay
                lay.setContentsMargins(0, Space.S, 0, 0)
            elif self._nest_layout is lay and self._own_margins is not None:
                lay.setContentsMargins(self._own_margins)
                self._own_margins, self._nest_layout = None, None
        self.updateGeometry()
        self.update()

    def changeEvent(self, e) -> None:
        super().changeEvent(e)
        if e.type() == QEvent.Type.ParentChange:
            self._settle_nesting()

    def set_expanded(self, expanded: bool, ms: int = Motion.NORMAL) -> None:
        """Open or close the body; `ms` the movement's time (0: at once)."""
        if not self.collapsible:
            return
        self._adopt()
        expanded = bool(expanded)
        _FOLDED[self.kind()] = not expanded
        if self._fold is None:
            self._fold = _Fold(self)
        self._fold.set_expanded(expanded, ms)

    def natural_height(self, width: int) -> int:
        """The height of the body open at `width`: where the movement of the fold goes."""
        body = self._body
        lay = body.layout()
        if lay is None:
            return body.sizeHint().height()
        if lay.hasHeightForWidth():
            return lay.totalHeightForWidth(width)
        return lay.totalSizeHint().height()

    def toggle(self) -> None:
        self.set_expanded(not self.expanded)

    def header_rect(self) -> QRect:
        return QRect(0, 0, self.width(), MeridianaStyle.head(self))

    def mousePressEvent(self, e) -> None:
        if self.collapsible and e.button() == Qt.MouseButton.LeftButton and self.header_rect().contains(e.position().toPoint()):
            self._pressed = True
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e) -> None:
        if self._pressed:
            self._pressed = False
            if self.header_rect().contains(e.position().toPoint()):
                self.toggle()
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def mouseMoveEvent(self, e) -> None:
        if self.collapsible:
            self._set_hot(self.header_rect().contains(e.position().toPoint()))
        super().mouseMoveEvent(e)

    def leaveEvent(self, e) -> None:
        self._set_hot(False)
        super().leaveEvent(e)

    def _set_hot(self, hot: bool) -> None:
        if hot != self.hot:
            self.hot = hot
            self.setCursor(Qt.CursorShape.PointingHandCursor if hot else Qt.CursorShape.ArrowCursor)
            self.update(self.header_rect())


class _Fold(QObject):
    """The movement of a group's body (R287): its height from what it is to nothing and back, in the time and with
    the curve of every movement, with the body's own layout held still meanwhile so that the fields are cut by the
    body's edge instead of being squeezed into it (a form shrunk to half its height piles its rows). Opening, the
    body is first laid out at its full height, then shown from nothing. The chevron turns with the height."""

    def __init__(self, group: Group):
        super().__init__(group)
        self.group = group
        self.natural = 1
        self.animation = QVariantAnimation(self)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._frame)
        self.animation.finished.connect(self._finish)
        from . import motion
        motion._RESPONSIVE.add(self)            # «less motion» switched on mid-way ends the movement at once

    @property
    def running(self) -> bool:
        return self.animation.state() == QVariantAnimation.State.Running

    def set_expanded(self, expanded: bool, ms: int) -> None:
        from .motion import reduced
        g, body = self.group, self.group._body
        self.animation.stop()
        g.expanded = expanded
        if body is None:
            g.progress = 1.0 if expanded else 0.0
            g.update()
            return
        if ms <= 0 or reduced() or not g.isVisible():
            self._finish()
            return
        inner = body.layout()
        if expanded:
            body.setMaximumHeight(QWIDGETSIZE_MAX)
            inner.setEnabled(True)
            cr = g.contentsRect()
            # showing a widget first asks its parent's layout: the group's, closed as it is, pressed the body into its
            # header and the fields were laid out there, and held there through the movement (photo 51, R341, R338)
            outer = QGroupBox.layout(g)
            outer.setEnabled(False)
            # shown first, nothing is painted before the end of this call: never shown, the fields have no font or
            # padding of the sheet and their rows wrap elsewhere (a first opening went 58 px too far and came back)
            body.setGeometry(cr.x(), cr.y(), cr.width(), max(1, body.height()))
            body.show()
            for group in body.findChildren(Group):      # the groups inside it as they will stand (R343)
                group._settle_nesting()
            self.natural = max(1, g.natural_height(cr.width()))
            body.setGeometry(cr.x(), cr.y(), cr.width(), self.natural)      # its fields in their places
            inner.activate()
            outer.setEnabled(True)
            start, end = 0, self.natural
        else:
            self.natural = max(1, body.height())
            start, end = body.height(), 0
        inner.setEnabled(False)                 # the fields keep their places while the body's edge moves
        body.setMaximumHeight(start)
        self.animation.setStartValue(float(start))
        self.animation.setEndValue(float(end))
        self.animation.setDuration(ms)
        self.animation.start()

    def _frame(self, value) -> None:
        body = self.group._body
        if body is not None:
            body.setMaximumHeight(max(0, round(float(value))))
        self.group.progress = max(0.0, min(1.0, float(value) / self.natural))
        self.group.update(self.group.header_rect())

    def _finish(self) -> None:
        self.animation.stop()
        g, body = self.group, self.group._body
        if body is not None:
            inner = body.layout()
            if inner is not None:
                inner.setEnabled(True)
            body.setMaximumHeight(QWIDGETSIZE_MAX)
            body.setVisible(g.expanded)
            if inner is not None:
                inner.invalidate()      # what it was told while held (a resize, a field that grew) is not lost
        g.progress = 1.0 if g.expanded else 0.0
        g.updateGeometry()
        g.update()
        g.folded.emit(not g.expanded)

    def refresh_motion(self) -> None:
        from .motion import reduced
        if reduced() and self.running:
            self._finish()


class SectionGate(QObject):
    """Fields owned by a checkbox, writable in its checked or unchecked state as declared (R194)."""

    def __init__(self, checkbox, reason: str, fields, writable_when_checked: bool = True):
        super().__init__(checkbox)
        self.checkbox = checkbox
        self.reason = reason
        self.fields = list(fields)
        self.writable_when_checked = writable_when_checked
        self.tips = {field: field.toolTip() for field in self.fields}
        checkbox.toggled.connect(self.apply)
        self.apply(checkbox.isChecked())

    def apply(self, on: bool) -> None:
        writable = on == self.writable_when_checked
        for field in self.fields:
            field.setEnabled(writable)
            field.setToolTip(self.tips[field] if writable else self.reason)


class _LabelGrowth(QObject):
    """A wrapped label's real height follows its width and font, so its form row grows with it (R193)."""

    def __init__(self, label):
        super().__init__(label)
        self.label = label
        label.installEventFilter(self)
        # a new text sends the label no event of its own: the status of a page, empty when the page was built, was
        # cut to one line on Windows («Fetch the weather of the site first», 28/10/2026)
        set_text = label.setText
        label.setText = lambda text: (set_text(text), self.fit())[0]
        self.floor = label.minimumHeight()          # what the label was given by its maker (a chart's note: 160)
        self.fit()

    def fit(self):
        label = self.label
        # a label not shown has no width of its own yet (Qt's 100 or 640 px, or its last one): measured there, a
        # page in a stack not shown kept a minimum taller than its text, and the stack took it (the Settings, whose
        # pages are made at every visit, stood 2188 px tall, 02/11/2026); it is measured again when shown
        if label.width() <= 0 or not label.isVisible():
            return
        # QLabel.heightForWidth never answers less than the label's minimum: measured with the minimum on, a label
        # once laid out narrow stayed that tall at any width, its row with a hole above and below (R310: why R285's
        # chart titles came back, on the tab open when the window was first laid out)
        before = label.minimumHeight()
        if before != self.floor:
            label.setMinimumHeight(self.floor)
        needed = label.heightForWidth(label.width())
        wanted = max(needed, self.floor) if needed >= 0 else before
        if label.minimumHeight() != wanted:
            label.setMinimumHeight(wanted)
        if wanted != before:
            label.updateGeometry()

    def eventFilter(self, _obj, event) -> bool:
        if event.type() in (QEvent.Type.Resize, QEvent.Type.FontChange, QEvent.Type.Show):
            self.fit()
        return False


def grow_label(label) -> None:
    """Keep a wrapped label, including one added after the window was built, as tall as its text."""
    if not hasattr(label, "_meridiana_growth"):
        label._meridiana_growth = _LabelGrowth(label)


LONG_TEXT = 28      # characters: a label or a checkbox longer than this goes onto more lines rather than widen its card


class _CheckWrap(QObject):
    """A checkbox or radio button whose text goes onto more lines when its card is narrow, as a wrapped label
    (Daniel, 02/11/2026: the Settings' «Meridio animato: i raggi girano, ...» kept the Assistant page 51 px wider
    than its scroll area at a window of 1000 px; the Consumption's «Mese per mese e per fascia (bollette)» its
    column 37 px wider than the card, cut). Qt's never wrap and their minimum width is the whole text. The button
    keeps its text, name and key; its sizes, picture and click area are answered here: the square or the dot at the
    first line, the lines beside it, the whole text clickable. One line is as tall as every control."""

    FLAGS = Qt.TextFlag.TextWordWrap | Qt.TextFlag.TextShowMnemonic

    def __init__(self, box):
        from PySide6.QtWidgets import QRadioButton
        super().__init__(box)
        self.box = box
        radio = isinstance(box, QRadioButton)
        self.control = QStyle.ControlElement.CE_RadioButton if radio else QStyle.ControlElement.CE_CheckBox
        self.contents = (QStyle.SubElement.SE_RadioButtonContents if radio else
                         QStyle.SubElement.SE_CheckBoxContents)
        box.minimumSizeHint = self.minimum
        box.hasHeightForWidth = lambda: True
        box.heightForWidth = self.height_for
        box.paintEvent = self.paint
        box.hitButton = self.hit
        policy = box.sizePolicy()
        policy.setHorizontalPolicy(policy.Policy.Preferred)         # Qt's Minimum never goes under the whole text
        policy.setVerticalPolicy(policy.Policy.Minimum)             # Fixed would hold it at one line
        policy.setHeightForWidth(True)
        box.setSizePolicy(policy)
        box.updateGeometry()

    def _option(self, height: int):
        from PySide6.QtWidgets import QStyleOptionButton
        from .design import Size
        opt = QStyleOptionButton()
        self.box.initStyleOption(opt)
        opt.rect = QRect(0, 0, self.box.width(), min(height, Size.CONTROL))
        return opt

    def _indent(self) -> int:
        opt = self._option(self.box.height())
        return self.box.style().subElementRect(self.contents, opt, self.box).left()

    def _pad(self) -> int:
        from .design import Size
        return max(0, (Size.CONTROL - QFontMetrics(self.box.font()).height()) // 2)

    def minimum(self) -> QSize:
        """As narrow as its longest word, as a wrapped label; one line tall."""
        from .design import Size
        metrics = QFontMetrics(self.box.font())
        word = max((metrics.horizontalAdvance(w) for w in self.box.text().replace("&", "").split()), default=0)
        return QSize(self._indent() + word, Size.CONTROL)

    def height_for(self, width: int) -> int:
        from .design import Size
        room = max(1, width - self._indent())
        lines = QFontMetrics(self.box.font()).boundingRect(QRect(0, 0, room, 100000), int(self.FLAGS),
                                                            self.box.text())
        return max(Size.CONTROL, lines.height() + 2 * self._pad())

    def hit(self, pos) -> bool:
        """The square or dot and the box of the text, as Qt's own: not the empty width beyond the text."""
        from .design import Size
        box, left, pad = self.box, self._indent(), self._pad()
        lines = QFontMetrics(box.font()).boundingRect(QRect(left, pad, box.width() - left, box.height() - 2 * pad),
                                                      int(self.FLAGS), box.text())
        return (QRect(0, 0, left, min(box.height(), Size.CONTROL)).contains(pos)
                or lines.adjusted(0, -pad, 0, pad).contains(pos))

    def paint(self, _event) -> None:
        from PySide6.QtGui import QPalette
        box = self.box
        opt = self._option(box.height())
        text, opt.text = opt.text, ""
        painter = QPainter(box)
        style = box.style()
        style.drawControl(self.control, opt, painter, box)          # the square or the dot, and its focus ring
        left = self._indent()
        pad = self._pad()
        style.drawItemText(painter, QRect(left, pad, box.width() - left, box.height() - 2 * pad),
                           int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop) | int(self.FLAGS),
                           opt.palette, box.isEnabled(), text, QPalette.ColorRole.WindowText)
        painter.end()


def wrap_check(box) -> None:
    """Let a long checkbox or radio button go onto more lines rather than widen its card (`_CheckWrap`); once per checkbox."""
    if not hasattr(box, "_meridiana_wrap") and not box.property("sized_by_owner"):
        box._meridiana_wrap = _CheckWrap(box)


class _ButtonWrap(QObject):
    """A command whose words go onto more lines when its panel is narrow (R341: «Scegli gli inverter in automatico…» held
    the Plant's page 33 px wider than the panel, and everything on it was cut at the right). The button keeps its text,
    key and tooltip; at the width where it fits on one line it is Qt's button. Its minimum is its longest word."""

    def __init__(self, button):
        from PySide6.QtWidgets import QSizePolicy
        super().__init__(button)
        self.button = button
        button.minimumSizeHint = self.minimum
        button.hasHeightForWidth = lambda: True
        button.heightForWidth = self.height_for
        button.paintEvent = self.paint
        policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum, QSizePolicy.ControlType.PushButton)
        policy.setHeightForWidth(True)
        button.setSizePolicy(policy)
        button.updateGeometry()

    def _pad(self) -> int:
        """What the button takes round its text across: its own one-line hint less the text."""
        b = self.button
        return max(0, type(b).sizeHint(b).width() - QFontMetrics(b.font()).horizontalAdvance(b.text().replace("&", "")))

    def minimum(self) -> QSize:
        b = self.button
        metrics = QFontMetrics(b.font())
        word = max((metrics.horizontalAdvance(w) for w in b.text().replace("&", "").split()), default=0)
        return QSize(word + self._pad(), type(b).sizeHint(b).height())

    def lines(self, width: int) -> list[str]:
        """The words shared out in lines of `width` at most, greedily."""
        b = self.button
        metrics = QFontMetrics(b.font())
        room = max(1, width - self._pad())
        out, line = [], ""
        for word in b.text().split():
            joined = f"{line} {word}" if line else word
            if line and metrics.horizontalAdvance(joined.replace("&", "")) > room:
                out.append(line)
                line = word
            else:
                line = joined
        return out + [line] if line else out

    def height_for(self, width: int) -> int:
        b = self.button
        extra = max(0, len(self.lines(width)) - 1)
        return type(b).sizeHint(b).height() + extra * QFontMetrics(b.font()).lineSpacing()

    def paint(self, event) -> None:
        from PySide6.QtWidgets import QPushButton, QStyleOptionButton
        b = self.button
        lines = self.lines(b.width())
        if len(lines) <= 1:
            QPushButton.paintEvent(b, event)
            return
        opt = QStyleOptionButton()
        b.initStyleOption(opt)
        opt.text = "\n".join(lines)
        painter = QPainter(b)
        b.style().drawControl(QStyle.ControlElement.CE_PushButton, opt, painter, b)
        painter.end()


def wrap_button(button) -> None:
    """Let a long command go onto more lines rather than widen its panel (`_ButtonWrap`); once per button."""
    if not hasattr(button, "_meridiana_wrap"):
        button._meridiana_wrap = _ButtonWrap(button)


class FitArea(QWidget):
    """A scroll area as tall as the page it holds and no taller, in a column that gives what it can (R337, Daniel
    03/11/2026: the Plant's sections took the whole panel, frame and all, for two lines of text): the hint is the page's
    height at the width the area has, followed when the page changes or is replaced; the minimum is the area's, so that
    where there is less room the area scrolls. `width` gives the column's width while the area is folded away."""

    def __init__(self, area=None, width=None, parent=None):
        super().__init__(parent)
        self.area = None
        self.column = width
        self.page = None
        self.last_width = 0
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        self.set_area(area)

    def set_area(self, area) -> None:
        """The area held, in the place of the one before (which is left where it is, for its owner to take)."""
        if self.area is not None:
            self.area.viewport().removeEventFilter(self)
            self.layout().removeWidget(self.area)
        self.area = area
        if area is not None:
            self.layout().addWidget(area)
            area.viewport().installEventFilter(self)
        self._watch()

    def _watch(self) -> None:
        page = self.area.widget() if self.area is not None else None
        if page is not self.page:
            self.page = page
            if page is not None:
                page.installEventFilter(self)
            self.updateGeometry()

    def eventFilter(self, obj, event) -> bool:
        kind = event.type()
        if kind == QEvent.Type.ChildAdded and self.area is not None and obj is self.area.viewport():
            QTimer.singleShot(0, self, self._watch)     # setWidget says it before it keeps it
        elif kind == QEvent.Type.LayoutRequest and obj is self.page:
            self.updateGeometry()
        return False

    def content_height(self, width: int) -> int:
        area = self.area
        page = area.widget() if area is not None else None
        if page is None:
            return 0
        bar = area.verticalScrollBar()
        margins = area.viewportMargins()            # the air of the area's soft edges (ui/fades.py)
        room = (width - 2 * area.frameWidth() - margins.left() - margins.right()
                - bar.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent, None, bar))
        lay = page.layout()
        if lay is None:
            high = page.sizeHint().height()
        elif lay.hasHeightForWidth():
            high = lay.totalHeightForWidth(max(1, room))
        else:
            high = lay.totalSizeHint().height()
        return high + 2 * area.frameWidth() + margins.top() + margins.bottom()

    def sizeHint(self) -> QSize:
        width = self.column() if self.column is not None else self.width()
        return QSize(self.area.sizeHint().width() if self.area is not None else 0, self.content_height(width))

    def minimumSizeHint(self) -> QSize:
        return self.area.minimumSizeHint() if self.area is not None else QSize(0, 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.width() != self.last_width:
            self.last_width = self.width()
            self.updateGeometry()


def pad_fields(root: QWidget) -> None:
    """The text of the number and date fields under `root` off their left edge: a style sheet's padding does not
    reach the line edit inside a QAbstractSpinBox, whose text stood at 2 px from the edge (Daniel, 24/10/2026)."""
    from PySide6.QtWidgets import QAbstractSpinBox, QLineEdit
    if root is None:
        return
    fields = root.findChildren(QAbstractSpinBox)
    if isinstance(root, QAbstractSpinBox):
        fields.append(root)
    for f in fields:
        edit = f.findChild(QLineEdit)
        if edit is not None and edit.textMargins().left() != FIELD_TEXT:
            edit.setTextMargins(FIELD_TEXT, 0, 2, 0)
    # a long label or checkbox of a form in a card goes onto two lines rather than widen the column past its card
    from PySide6.QtWidgets import QCheckBox, QLabel, QRadioButton, QStackedWidget
    for check in (root.findChildren(QCheckBox) + root.findChildren(QRadioButton)
                  + ([root] if isinstance(root, (QCheckBox, QRadioButton)) else [])):
        if len(check.text()) > LONG_TEXT:
            wrap_check(check)
    for label in root.findChildren(QLabel):
        if label.property("sized_by_owner"):        # a result tile measures its own texts (energy_pages.Tiles)
            continue
        if not label.wordWrap() and len(label.text()) > LONG_TEXT and _in_scroll(label) and not label.pixmap():
            label.setWordWrap(True)
        if label.wordWrap():
            grow_label(label)
    # a stack of pages in a form as wide as the page shown, not as the widest of them
    for stack in root.findChildren(QStackedWidget):
        if _in_scroll(stack) and not stack.property("fitted"):
            stack.setProperty("fitted", True)
            stack.currentChanged.connect(lambda _i, s=stack: _fit_stack(s))
            _fit_stack(stack)
    # the lists of a form in a card as wide as the card lets them be: a long choice no longer widens the column
    # past its card (Daniel, 24/10/2026: «contenuti che fuoriescono»); the whole text in the open list and the tooltip
    from PySide6.QtWidgets import QComboBox, QScrollArea
    for c in root.findChildren(QComboBox) + ([root] if isinstance(root, QComboBox) else []):
        w, inside = c.parentWidget(), False
        while w is not None and not inside:
            inside, w = isinstance(w, QScrollArea), w.parentWidget()
        if inside and c.sizeAdjustPolicy() != QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon:
            c.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            c.setMinimumContentsLength(8)
            if not c.toolTip():                     # a tooltip of its own stays; else the choice in full
                c.currentTextChanged.connect(c.setToolTip)
                c.setToolTip(c.currentText())


# the line edit inside a number field starts 2 px in from the field's edge (Qt): 6 more put its text at
# Line.TEXT_INSET, as every control's
FIELD_TEXT = Line.TEXT_INSET - 2


def _in_scroll(widget: QWidget) -> bool:
    """Whether `widget` stands in a scroll area: a form of a card."""
    from PySide6.QtWidgets import QScrollArea
    w = widget.parentWidget()
    while w is not None:
        if isinstance(w, QScrollArea):
            return True
        w = w.parentWidget()
    return False


def _fit_stack(stack) -> None:
    """The pages not shown leave the stack's size to the one shown."""
    from PySide6.QtWidgets import QSizePolicy
    for k in range(stack.count()):
        on = k == stack.currentIndex()
        policy = QSizePolicy.Policy.Preferred if on else QSizePolicy.Policy.Ignored
        stack.widget(k).setSizePolicy(policy, policy)
    stack.updateGeometry()


def quiet_menus(bar: QWidget) -> None:
    """The menu bar and its menus without the underlined letters."""
    for w in [bar, *bar.findChildren(QMenu)]:
        w.setStyle(shared())
