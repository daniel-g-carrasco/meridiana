"""The few things Meridiana draws itself in Qt's style (the target of 24/10/2026, docs/studio/19-grafica): the
groups as in the mockups' C3, a frame with a header band the whole width (a style sheet draws a group's title as
a tab only), and the menus without their mnemonics underlined (Windows shows them only with Alt; Fusion always,
and the row of menus looked like a page of links). Alt and its letters work as before.

The style is set on those widgets only (`Group`, `quiet_menus`), not on the application: a style written in
Python is asked for everything it draws, and the rest of the window stays on Fusion, as fast as it was."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGroupBox, QMenu, QProxyStyle, QStyle, QStyleFactory, QWidget

from .design import Line, Radius, Space

GROUP_RADIUS = Radius.CONTROL   # a group is a control's depth (ui/design.py)
HEAD_PAD = Space.M              # the header band over the title's line of text
TITLE_X = Line.TEXT_INSET       # the title from the group's left edge, as a field's text


class MeridianaStyle(QProxyStyle):
    """Fusion, with the groups of C3 and without the menus' underlines. `tokens` are the theme's colours (set by
    ui/theme.Theme at each change)."""

    def __init__(self):
        super().__init__(QStyleFactory.create("Fusion"))
        self.tokens: dict = {}

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
                return QRect(r.left() + TITLE_X, r.top(), max(0, r.width() - 2 * TITLE_X), h)
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
            p.fillRect(QRectF(r.left(), r.top(), r.width(), h), QColor(t["line_soft"]))
            p.setClipping(False)
            p.setPen(QPen(QColor(t["line"]), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(frame)
            font = QFont(widget.font())
            font.setWeight(QFont.Weight.DemiBold)
            p.setFont(font)
            p.setPen(QColor(t["text"] if widget.isEnabled() else t["muted"]))
            room = r.width() - 2 * TITLE_X
            title = QFontMetrics(font).elidedText(widget.title(), Qt.TextElideMode.ElideRight, int(max(0.0, room)))
            p.drawText(QRectF(r.left() + TITLE_X, r.top(), room, h),
                       int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), title)
            p.restore()
            return
        super().drawComplexControl(cc, opt, p, widget)


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
        _SHARED.append(style)
    return _SHARED[0]


class Group(QGroupBox):
    """A group of fields as C3: a frame, the title in a band the whole width (the shared style draws it). A long
    title is shortened, never widens the group: in a card that scrolls it pushed the fields past the card's edge
    (the Balance's «Energia acquistata (tutti i costi variabili, imposte comprese)», 25/10/2026)."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(title, parent)
        self.setStyle(shared())

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        lay = self.layout()
        if lay is None:
            return hint
        m = self.contentsMargins()
        inside = lay.minimumSize().width() + m.left() + m.right() + 2
        return QSize(min(hint.width(), max(inside, 2 * TITLE_X + 40)), hint.height())


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
