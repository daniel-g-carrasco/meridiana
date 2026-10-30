"""The few things Meridiana draws itself in Qt's style (the target of 24/10/2026, docs/studio/19-grafica): the
groups as in the mockups' C3, a frame with a header band the whole width (a style sheet draws a group's title as
a tab only), and the menus without their mnemonics underlined (Windows shows them only with Alt; Fusion always,
and the row of menus looked like a page of links). Alt and its letters work as before.

The style is set on those widgets only (`Group`, `quiet_menus`), not on the application: a style written in
Python is asked for everything it draws, and the rest of the window stays on Fusion, as fast as it was."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPointF, QRect, QRectF, QSize, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGroupBox, QMenu, QProxyStyle, QStyle, QStyleFactory, QVBoxLayout, QWidget

from .. import theme_colors
from .checkboxes import CheckboxStyle
from .design import Icon, Line, Motion, Radius, Space

GROUP_RADIUS = Radius.CONTROL   # a group is a control's depth (ui/design.py)
HEAD_PAD = Space.M              # the header band over the title's line of text
TITLE_X = Line.TEXT_INSET       # the title from the group's left edge, as a field's text
CHEVRON = 10                    # the fold's sign: a chevron this wide at the title's left (R287)
CHEVRON_GAP = Space.S           # between the chevron and the title
QWIDGETSIZE_MAX = (1 << 24) - 1


def title_x(widget: QWidget) -> int:
    """Where a group's title starts: after the fold's chevron when the group folds."""
    return TITLE_X + (CHEVRON + CHEVRON_GAP if getattr(widget, "collapsible", False) else 0)


class MeridianaStyle(CheckboxStyle, QProxyStyle):
    """Fusion, with the groups of C3 and without the menus' underlines. `tokens` are the theme's colours (set by
    ui/theme.Theme at each change)."""

    def __init__(self):
        super().__init__(QStyleFactory.create("Fusion"))
        self.tokens: dict = {}

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return Motion.NORMAL
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
                return r.adjusted(1, h, -1, -1)
            if sc == QStyle.SubControl.SC_GroupBoxCheckBox:
                return QRect()
        return super().subControlRect(cc, opt, sc, widget)

    def drawComplexControl(self, cc, opt, p, widget=None):
        if cc == QStyle.ComplexControl.CC_GroupBox and isinstance(widget, QGroupBox) and self.tokens:
            t = self.tokens
            r = QRectF(opt.rect).adjusted(0.5, 0.5, -0.5, -0.5)
            h = self.head(widget)
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
    from PySide6.QtWidgets import QAbstractSpinBox
    from .app_events import events

    def polished(obj, _event) -> bool:
        if isinstance(obj, QAbstractSpinBox):
            pad_fields(obj)
        return False

    events().on((QEvent.Type.Polish,), owner, polished)


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
    back as it was left."""

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
        if body.isHidden():
            return MeridianaStyle.head(self) + 1
        if self._fold is not None and self._fold.running:
            return MeridianaStyle.head(self) + 1 + body.maximumHeight()
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
        self.natural = max(1, self._natural())
        if expanded:
            body.setMaximumHeight(QWIDGETSIZE_MAX)
            inner.setEnabled(True)
            cr = g.contentsRect()
            body.setGeometry(cr.x(), cr.y(), cr.width(), self.natural)      # its fields in their places
            body.show()
            inner.activate()
            start, end = 0, self.natural
        else:
            start, end = body.height(), 0
        inner.setEnabled(False)                 # the fields keep their places while the body's edge moves
        body.setMaximumHeight(start)
        self.animation.setStartValue(float(start))
        self.animation.setEndValue(float(end))
        self.animation.setDuration(ms)
        self.animation.start()

    def _natural(self) -> int:
        body = self.group._body
        lay = body.layout()
        width = self.group.contentsRect().width()
        if lay is None:
            return body.sizeHint().height()
        if lay.hasHeightForWidth():
            return lay.totalHeightForWidth(width)
        return lay.totalSizeHint().height()

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
        self.fit()

    def fit(self):
        if self.label.width() > 0:
            needed = self.label.heightForWidth(self.label.width())
            if needed >= 0 and self.label.minimumHeight() != needed:
                self.label.setMinimumHeight(needed)
                self.label.updateGeometry()

    def eventFilter(self, _obj, event) -> bool:
        if event.type() in (QEvent.Type.Resize, QEvent.Type.FontChange, QEvent.Type.Show):
            self.fit()
        return False


def grow_label(label) -> None:
    """Keep a wrapped label, including one added after the window was built, as tall as its text."""
    if not hasattr(label, "_meridiana_growth"):
        label._meridiana_growth = _LabelGrowth(label)


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
    # a long label of a form in a card goes onto two lines rather than widen the column past its card
    from PySide6.QtWidgets import QLabel, QStackedWidget
    for label in root.findChildren(QLabel):
        if not label.wordWrap() and len(label.text()) > 28 and _in_scroll(label) and not label.pixmap():
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
