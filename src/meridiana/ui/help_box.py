"""The help next to things in the window (study 17, E; design document 3.6, C3, C7 and 5.1; R24). Daniel chose
E3 on 23/10/2026, «confermato come riquadro in fondo alle Proprietà»: the help box at the foot of the right
panel, in every phase, explains the field of the panel that has the keyboard or the result tile under the
pointer, three lines of text with the source and three links (the manual, how it is computed, ask Meridio). It
folds to its title and stays as it is left (the settings), and hides by itself in a panel lower than 480 px:
then the «?» open the same text as a pop-up (E1). The «?» beside the titles of the groups and of the result
tiles open the box on that text; F1 explains the field with the keyboard, Shift+F1 («What's this?», Qt's
mode) what is clicked next. The manual is read inside the program (ManualView), not left to the system's
choice of a program for .md files.

The texts are in the core (help.py), by id; a widget gets its id with `register` (a dynamic property, the text
as its «What's this?», a filter that sends Shift+F1 to the box), and a widget without one has its parent's: a
field in a group is explained by the group unless it has a text of its own."""

from __future__ import annotations

import html

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPalette, QTextCursor
from PySide6.QtWidgets import (QApplication, QDialog, QDockWidget, QFrame, QGroupBox, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QScrollArea, QSizePolicy, QSplitter, QTabWidget, QTextBrowser,
                               QToolButton, QVBoxLayout, QWidget)

from .. import help as helps
from ..i18n import _
from .design import Button, Text, set_text, strong

HELP = "help"                   # the dynamic property with a widget's help id
HOVER = "help_hover"            # the box follows the pointer over it (the result tiles)
BUTTON = Button.HELP[0]         # logical pixels of the «?»


def help_id(widget) -> str:
    """The help of a widget: its own id, or the nearest parent's."""
    while widget is not None:
        value = widget.property(HELP)
        if isinstance(value, str) and value:
            return value
        widget = widget.parentWidget()
    return ""


def whats_this(h: helps.Help) -> str:
    """The text of Qt's «What's this?» (and of a reader of the screen): the same as the box."""
    sources = helps.sources(h)
    tail = f"<br><i>{html.escape(_('Source: {source}').format(source='; '.join(sources)))}</i>" if sources else ""
    return f"{strong(html.escape(h.title))}<br>{html.escape(h.text)}{tail}"


def box_of(widget) -> HelpBox | None:
    """The help box of the window a widget is in, when that window has one."""
    if widget is None:
        return None
    box = getattr(widget.window(), "help_box", None)
    return box if isinstance(box, HelpBox) else None


def request(hid: str, widget=None, at: QPoint | None = None) -> None:
    """Show the help `hid`: in the box of the widget's window when it is on screen, else as a pop-up beside the
    widget (or at `at`, global)."""
    if not helps.get(hid):
        return
    box = box_of(widget)
    # a closed help card is a folded box: the «?» and F1 open it again, unless the window is too low for it
    if box is not None and (box.isVisible() or (box.dock() is not None and box.room())):
        box.request(hid)
    else:
        HelpPopup.show_for(hid, widget, at, box)


class _Router(QObject):
    """Shift+F1 on a registered widget, or the pointer over a result tile: to the box of its window."""

    def eventFilter(self, obj, event) -> bool:
        kind = event.type()
        if kind == QEvent.Type.WhatsThis:
            hid = help_id(obj)
            if hid:
                request(hid, obj, event.globalPos())
                return True
        elif kind == QEvent.Type.Enter and obj.property(HOVER):
            box = box_of(obj)
            if box is not None:
                box.hovered(help_id(obj))
        return False


_router: _Router | None = None


def register(widget: QWidget, hid: str, hover: bool = False) -> QWidget:
    """Give `widget` the help `hid`: what it and the widgets inside it without their own are explained by."""
    global _router
    h = helps.get(hid)
    if h is None:
        raise ValueError(f"no help {hid!r} in help.py")
    if _router is None:
        _router = _Router(QApplication.instance())
    widget.setProperty(HELP, hid)
    widget.setWhatsThis(whats_this(h))
    if hover:
        widget.setProperty(HOVER, True)
    widget.installEventFilter(_router)
    return widget


class HelpButton(QToolButton):
    """The «?»: a round flat button of 16 px, the short sentence as its tooltip; a click opens the box on its
    text, or the pop-up where the box is not shown. It does not take the keyboard: F1 is the keyboard's way."""

    def __init__(self, hid: str, parent=None):
        super().__init__(parent)
        h = helps.get(hid)
        if h is None:
            raise ValueError(f"no help {hid!r} in help.py")
        self.hid = hid
        self.setObjectName("help-button")
        self.setText("?")
        self.setAutoRaise(True)
        self.setFixedSize(BUTTON, BUTTON)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(h.short)
        self.setAccessibleName(_("Help: {title}").format(title=h.title))
        set_text(self, Text.LABEL)                  # a round button of the global sheet (Button.HELP)
        register(self, hid)
        self.clicked.connect(lambda: request(self.hid, self))


class _Corner(QObject):
    """Keeps a «?» in the top right corner of its host: on the title's row of a group, inside a tile."""

    def __init__(self, host: QWidget, button: HelpButton):
        super().__init__(host)
        self.host, self.button = host, button
        host.installEventFilter(self)
        self.place()

    def place(self) -> None:
        group = isinstance(self.host, QGroupBox)
        top = max(0, (self.host.fontMetrics().height() + 8 - BUTTON) // 2) if group else 6
        self.button.move(self.host.width() - BUTTON - 6, top)
        self.button.raise_()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.host and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.place()
        return False


def help_button(host: QWidget, hid: str, hover: bool = False, beside: QLabel | None = None) -> HelpButton:
    """A «?» in the top right corner of `host` (a group: on its title's row; a result tile: inside it), and the
    host given the same help, so that what is inside it is explained by it; `beside`, a label on the button's
    row, keeps clear of it."""
    register(host, hid, hover)
    if beside is not None:
        margins = beside.contentsMargins()
        beside.setContentsMargins(margins.left(), margins.top(), margins.right() + BUTTON + 4, margins.bottom())
    button = HelpButton(hid, host)
    host._help_corner = _Corner(host, button)      # kept with the host
    button.show()
    return button


class HintLabel(QLabel):
    """The short sentence under a field that does not explain itself (study 17, E.7), muted and small."""

    def __init__(self, hid: str, parent=None):
        h = helps.get(hid)
        if h is None:
            raise ValueError(f"no help {hid!r} in help.py")
        super().__init__(h.short, parent)
        self.hid = hid
        self.setObjectName("hint")
        self.setWordWrap(True)
        set_text(self, Text.SECONDARY)


def _muted(widget: QWidget) -> str:
    return widget.palette().color(QPalette.ColorGroup.Active, QPalette.ColorRole.PlaceholderText).name()


class _FitScroll(QScrollArea):
    """A scroll area that asks for the height of its text (`want`): the layout gives it that when the card has
    the room, less down to its minimum when not (R102: it asked for nothing and got its minimum, the room going to the
    stretch under it)."""

    want = 0

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        return QSize(hint.width(), self.want or hint.height())


class HelpView(QWidget):
    """A help's text with its source and its links; `limit` lines of text at most, the rest scrolled (the box),
    or all of it (the pop-up)."""

    link = Signal(str, str)             # "manual", "how" or "ask"; the chapter#anchor, the step, the help id

    def __init__(self, limit: int = 0, parent=None):
        super().__init__(parent)
        self.limit = limit
        self.fill = False                   # in a card: as tall as the text, up to the card's room (R76)
        self.hid = ""
        self.links_wanted = {"manual": True, "how": True, "ask": True}
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setTextFormat(Qt.TextFormat.RichText)
        self.text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.text.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        if limit:
            self.scroll = _FitScroll()
            self.scroll.setWidgetResizable(True)
            self.scroll.setFrameShape(QFrame.Shape.NoFrame)
            self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.scroll.setWidget(self.text)
            box.addWidget(self.scroll)
        else:
            box.addWidget(self.text)
        self.links = QLabel()
        self.links.setWordWrap(True)
        self.links.setTextFormat(Qt.TextFormat.RichText)
        self.links.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse |
                                           Qt.TextInteractionFlag.LinksAccessibleByKeyboard)
        self.links.linkActivated.connect(self._activated)
        box.addWidget(self.links)

    def show_help(self, hid: str) -> None:
        h = helps.get(hid)
        if h is None:
            return
        self.hid = hid
        sources = helps.sources(h)
        tail = ""
        if sources:
            said = _("Source: {source}").format(source="; ".join(sources))
            tail = f"<br><span style='color:{_muted(self)}'>{html.escape(said)}</span>"
        self.text.setText(html.escape(h.text) + tail)
        parts = []
        if h.manual and self.links_wanted["manual"]:
            parts.append(f"<a href='manual:{h.manual}'>{html.escape(_('Manual ›'))}</a>")
        if h.pedigree and self.links_wanted["how"]:
            parts.append(f"<a href='how:{h.pedigree}'>{html.escape(_('How it is computed ›'))}</a>")
        if self.links_wanted["ask"]:
            from ..assistant import NAME
            parts.append(f"<a href='ask:{hid}'>{html.escape(_('Ask {name} ›').format(name=NAME))}</a>")
        self.links.setText("&nbsp;&nbsp; ".join(parts))
        self.links.setVisible(bool(parts))
        self.settle()

    def show_html(self, text: str, manual: str = "") -> None:
        """A text of its own (the steps of a gesture, R43) with the link to the manual's chapter."""
        self.hid = ""
        self.text.setText(text)
        parts = []
        if manual and self.links_wanted["manual"]:
            parts.append(f"<a href='manual:{manual}'>{html.escape(_('Manual ›'))}</a>")
        self.links.setText("&nbsp;&nbsp; ".join(parts))
        self.links.setVisible(bool(parts))
        self.settle()

    def settle(self) -> None:
        """The text's room: as tall as the text, `limit` lines at most."""
        if not self.limit:
            return
        lines = self.fontMetrics().lineSpacing() * self.limit + 4
        width = max(80, self.scroll.width() or self.width())
        tall = max(self.fontMetrics().lineSpacing(), self._text_height(width))
        if self.fill:
            # in its own card the text takes the room there is (Daniel, 24/10/2026: «come mai anche se Aiuto ha
            # tutto questo spazio il suo contenuto viene compresso?»): as tall as it is, scrolled only when the card
            # is lower, never under two lines
            self.scroll.want = tall + 2
            self.scroll.setMinimumHeight(min(tall, 2 * self.fontMetrics().lineSpacing() + 4))
            self.scroll.setMaximumHeight(tall + 2)
            self.scroll.updateGeometry()
            return
        self.scroll.setFixedHeight(min(lines, tall))

    def _text_height(self, width: int) -> int:
        """The text's height at `width`, laid out as the label lays it (its font, its rich text): the label's own
        heightForWidth fell short on the guide's mixed styles, and the card cut the last lines with room to spare
        under them (R102, 25/10/2026)."""
        import math

        from PySide6.QtGui import QTextDocument
        doc = QTextDocument()
        doc.setDefaultFont(self.text.font())
        doc.setDocumentMargin(0)
        doc.setHtml(self.text.text())
        doc.setTextWidth(width)
        return math.ceil(doc.size().height()) + 4

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.settle()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange and self.hid:
            self.show_help(self.hid)            # the source's muted colour from the new palette

    def _activated(self, href: str) -> None:
        kind, _colon, value = href.partition(":")
        self.link.emit(kind, value)


class HelpBox(QFrame):
    """The help box (see the module's text). Since 24/10/2026 a card of its own under the properties (Daniel:
    «una scheda a parte, posizionata nel punto dedicato a destra sotto proprietà»): in a dock the title says the
    help's subject, closing the card is folding it (the settings remember it), and a window too low for it hides
    the card as it hid the box; alone (the tests of the box) it folds as before."""

    LOWEST_PANEL = 480          # logical pixels: below it the box hides and the «?» open a pop-up instead (C3)
    LINES = 3                   # lines of text, the rest scrolled

    openedChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("help-box")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("QFrame#help-box { border-top: 1px solid palette(mid); }")
        self.host = None                 # the main window, from attach()
        self.panel = None                # the panel whose fields it explains (the properties)
        self.hid = ""
        self.opened = True
        self.fitting = False             # the card hidden or shown for the window's height, not by the designer
        self.manual_view: ManualView | None = None
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(2, 4, 2, 2)
        self.box.setSpacing(2)
        self.head = QToolButton()
        self.head.setObjectName("help-head")
        self.head.setAutoRaise(True)
        self.head.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.head.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.head.setStyleSheet("QToolButton#help-head { text-align: left; padding: 1px 2px; border: none; }")
        set_text(self.head, Text.STRONG)
        self.head.clicked.connect(lambda: self.set_open(not self.opened) if self.dock() is None else None)
        self.box.addWidget(self.head)
        self.subject = QLabel()             # in a card: the help's subject, where the head was
        self.subject.setObjectName("help-subject")
        set_text(self.subject, Text.STRONG)
        self.subject.hide()
        # in a card, on the subject's row: the pin (a «?» or F1 pins the subject, R44) and «Detach» (R68)
        self.pinned = False
        self.guide = None                   # (tool, step) while the card guides a gesture (R43)
        self.notes: list = []               # the subjects detached into windows of their own
        self.subject_row = QWidget()
        row = QHBoxLayout(self.subject_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)
        row.addWidget(self.subject, 1)
        from . import icons
        self.pin_button = QToolButton()
        self.pin_button.setObjectName("help-pin")
        self.pin_button.setCheckable(True)
        self.pin_button.setAutoRaise(True)
        self.pin_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pin_button.setIcon(icons.icon("pin"))
        self.pin_button.toggled.connect(self.set_pinned)
        self.detach_button = QToolButton()
        self.detach_button.setObjectName("help-detach")
        self.detach_button.setAutoRaise(True)
        self.detach_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.detach_button.setIcon(icons.icon("external-link"))
        self.detach_button.setToolTip(_("Detach: this help in a small window of its own, to keep beside the work"))
        self.detach_button.clicked.connect(self.detach)
        row.addWidget(self.pin_button)
        row.addWidget(self.detach_button)
        self.subject_row.hide()
        self.box.addWidget(self.subject_row)
        self._pin_tip()
        self.view = HelpView(self.LINES)
        self.view.link.connect(self.follow)
        self.box.addWidget(self.view)
        self._show_head()

    # what it shows

    def show_help(self, hid: str) -> None:
        """The box on the help `hid` (help.py), open or folded as it is."""
        h = helps.get(hid)
        if h is None:
            return
        self.guide = None
        self.hid = hid
        self.view.links_wanted = self.links_wanted()
        self.view.show_help(hid)
        self._show_head()

    def request(self, hid: str) -> None:
        """A «?», F1 or Shift+F1: the box opened on that help, remembered open, and pinned on it (R44): the pointer
        on its way to the links no longer changes it."""
        self.set_open(True)
        self.show_help(hid)
        if self.dock() is not None:
            self.set_pinned(True)

    def show_guide(self, tool: str, step: int) -> None:
        """The steps of the gesture of `tool` with step `step` marked (R43; guides.py); "" or a tool without a guide
        brings back the help of the context. A pinned subject stays."""
        from .. import guides
        g = guides.guides().get(tool)
        if g is None:
            if self.guide is not None:
                self.guide = None
                self.show_help(self.hid or helps.for_phase(self.host.phase() if self.host else "model"))
            return
        if self.pinned:
            return
        self.guide = (tool, step)
        # the step in hand first, whole, and the next one under it, quiet: the card is low, a list of four would
        # show only the first (24/10/2026)
        at = min(step, len(g.steps) - 1)
        muted = _muted(self)
        text = f"<p style='margin:0 0 6px 0'>{html.escape(g.steps[at])}</p>"
        if at + 1 < len(g.steps):
            text += (f"<p style='margin:0; color:{muted}'>{html.escape(_('Then: {step}').format(step=g.steps[at + 1]))}"
                     "</p>")
        self.subject.setText(_("{title} · step {n} of {m}").format(title=g.title, n=at + 1, m=len(g.steps)))
        self.view.show_html(text, g.manual)

    def set_pinned(self, on: bool) -> None:
        """The subject held (a «?», F1, the pin) or following the context again."""
        self.pinned = bool(on)
        if self.pin_button.isChecked() != self.pinned:
            self.pin_button.blockSignals(True)
            self.pin_button.setChecked(self.pinned)
            self.pin_button.blockSignals(False)
        self._pin_tip()

    def _pin_tip(self) -> None:
        from . import icons
        self.pin_button.setIcon(icons.icon("pin" if self.pinned else "pin-off"))
        self.pin_button.setToolTip(_("Pinned on this subject: the pointer and the fields do not change it; click to "
                                     "let it follow them again") if self.pinned else
                                   _("Following the field in hand and the pointer; a «?» or a click here pins it"))

    def follow_context(self, hid: str) -> None:
        """A subject the context offers (a field, a tile, a phase, a page of the properties): taken unless the
        designer pinned one or the card is guiding a gesture."""
        if hid and not self.pinned and self.guide is None and hid != self.hid:
            self.show_help(hid)

    def hovered(self, hid: str) -> None:
        """The pointer over a result tile: its help, if the box is there to say it and is not pinned."""
        if self.isVisible():
            self.follow_context(hid)

    def detach(self) -> None:
        """The subject in a small window of its own (R68), and the card free to follow the context again."""
        if not self.hid:
            return
        note = HelpNote(self.hid, self, self.window())
        self.notes.append(note)
        note.destroyed.connect(lambda *_a, n=note: self.notes.remove(n) if n in self.notes else None)
        at = self.mapToGlobal(QPoint(0, 0))
        note.move(at.x() - note.width() - 16, max(0, at.y() - 40))
        note.show()
        self.set_pinned(False)

    def dock(self) -> QDockWidget | None:
        """The card it stands in, when it is one."""
        w = self.parentWidget()
        return w if isinstance(w, QDockWidget) else None

    def set_open(self, on: bool) -> None:
        changed = on != self.opened
        self.opened = on
        if self.dock() is None:
            self.view.setVisible(on)
        else:
            self.view.setVisible(True)
            self._fit()
        self._show_head()
        if changed:
            self.openedChanged.emit(on)

    def _show_head(self) -> None:
        h = helps.get(self.hid)
        if self.dock() is not None:                 # the card's title says «Help»: here the subject
            self.head.hide()
            self.subject.show()
            self.subject_row.show()
            self.subject.setText(h.title if h else "")
            return
        self.head.setText(_("Help · {title}").format(title=h.title) if h else _("Help"))
        self.head.setArrowType(Qt.ArrowType.DownArrow if self.opened else Qt.ArrowType.RightArrow)
        self.head.setToolTip(_("Fold the help to its title") if self.opened else _("Open the help"))

    def links_wanted(self) -> dict:
        """«How it is computed» and «Ask Meridio» need the window; Meridio can be switched off."""
        host = self.host
        return {"manual": True, "how": host is not None,
                "ask": host is not None and bool(getattr(getattr(host, "cfg", None), "assistant", False))}

    # the window around it

    def attach(self, host) -> None:
        """Wire the box to the main window: its settings, the panel it stands in, the keyboard, the phases, the
        pages of the properties and the checks."""
        self.host = host
        dock = self.dock()
        if dock is not None:
            self.panel = getattr(host, "inspector", None)
            self.setStyleSheet("")
            self.box.setContentsMargins(6, 0, 6, 4)
            self.subject.setContentsMargins(0, 0, 0, 2)
            self.view.fill = True               # the text as tall as the card lets it be (R76)
            self.view.settle()
            self.box.addStretch(1)              # the links right under the text, the room of the card below
            dock.toggleViewAction().toggled.connect(self._dock_toggled)
            host.installEventFilter(self)
        else:
            self.panel = self.parentWidget()
            if self.panel is not None:
                self.panel.installEventFilter(self)
        self.set_open(host.cfg.help_open)
        self.openedChanged.connect(self._remember)
        QApplication.instance().focusChanged.connect(self._focus)
        host.tabs.currentChanged.connect(self._phase)
        host.props.pageShown.connect(self.follow_context)
        host.checks_page.setProperty(HELP, "checks")
        self.show_help(helps.for_phase(host.phase()))
        self._fit()

    def _remember(self, on: bool) -> None:
        self.host.cfg.help_open = on

    def _phase(self, _index: int) -> None:
        self.follow_context(helps.for_phase(self.host.phase()))

    def room(self) -> bool:
        """The right column tall enough for the help under the properties (C3: LOWEST_PANEL pixels)."""
        if self.host is None:
            return True
        from .cards import GAP, arena
        return arena(self.host).height() - 2 * GAP >= self.LOWEST_PANEL

    def _fit(self) -> None:
        """Hidden in a panel lower than LOWEST_PANEL (C3): the «?» open the pop-up meanwhile. As a card: shown
        when it is open and the column has room, hidden otherwise, without forgetting that it is open."""
        dock = self.dock()
        if dock is not None:
            want = self.opened and self.room()
            if dock.isHidden() == want and not dock.isFloating():
                self.fitting = True
                dock.setVisible(want)
                self.fitting = False
            return
        panel = self.parentWidget()
        if panel is not None:
            self.setVisible(panel.height() >= self.LOWEST_PANEL)

    def _dock_toggled(self, on: bool) -> None:
        """The card closed or opened by the designer (its cross, View > Panels): that is folding it."""
        if not self.fitting and on != self.opened:
            self.opened = on
            self.openedChanged.emit(on)

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.Resize and (obj is self.parentWidget() or obj is self.host):
            try:
                self._fit()
            except RuntimeError:            # the window going away
                pass
        return False

    def _focus(self, _old, new) -> None:
        """The field of the panel that takes the keyboard: its help (in the panel only, design C3: the keyboard
        going round the window with Tab would change it at every key)."""
        panel = self.panel
        if new is None or panel is None or not panel.isAncestorOf(new) or self.isAncestorOf(new):
            return
        hid = help_id(new)
        if hid:
            self.follow_context(hid)

    def context_help(self) -> None:
        """F1: the help of the field with the keyboard, anywhere in the window; in the checks, of the level of
        the item in hand; else of the phase."""
        widget = QApplication.focusWidget()
        hid = help_id(widget) if widget is not None and widget.window() is self.window() else ""
        if hid == "checks":
            item = self.host.checks_page.selected()
            hid = f"checks.{item.level}" if item is not None else hid
        request(hid or helps.for_phase(self.host.phase()), widget if hid else self)

    # the links

    def follow(self, kind: str, value: str) -> None:
        if kind == "manual":
            self.open_manual(value)
        elif kind == "how":
            self.how(value)
        elif kind == "ask":
            self.ask(value)

    def open_manual(self, ref: str = "") -> ManualView:
        """The manual inside the program (design 5.1), at `ref` («chapter.md#anchor»); without one, the chapter
        of the phase open."""
        if not ref and self.host is not None:
            ref = helps.split(helps.get(helps.for_phase(self.host.phase())).manual)[0]
        if self.manual_view is None:
            self.manual_view = ManualView(self.window())
        self.manual_view.open(ref)
        return self.manual_view

    def how(self, pedigree: str) -> None:
        """«How it is computed ›»: the page of the phase, its tab of the computation, at the step."""
        phase, _colon, step = pedigree.partition(":")
        page = {"production": self.host.energy_page, "consumption": self.host.consumption_page,
                "economics": self.host.economics_page}.get(phase)
        if page is None:
            return
        self.host.show_phase(phase)
        view = page.pedigree
        tabs = view.parentWidget()
        while tabs is not None and not isinstance(tabs, QTabWidget):
            tabs = tabs.parentWidget()
        if tabs is not None:
            tabs.setCurrentWidget(view)
        title = next((s.title for r in view.records for s in r.steps if s.key == step), "") if step else ""
        if title:
            if view.pending and view.isVisible():
                view._draw()
            view.moveCursor(QTextCursor.MoveOperation.Start)
            view.find(title)

    def ask(self, hid: str) -> None:
        """«Ask Meridio ›»: the assistant open, with the question written in its field, to send or change."""
        h = helps.get(hid)
        assistant = getattr(self.host, "assistant", None)
        if h is None or assistant is None:
            return
        assistant.open_panel()
        assistant.field.setText(helps.question(h))
        assistant.field.setFocus(Qt.FocusReason.OtherFocusReason)


class HelpNote(QFrame):
    """A help detached from the card (R68): a small window of its own over the main one, with the subject's title,
    its text and links, moved where the designer wants it and closed by its cross or Esc."""

    def __init__(self, hid: str, box, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)
        self.setObjectName("help-note")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.box = box
        h = helps.get(hid)
        self.setWindowTitle(h.title if h else _("Help"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        title = set_text(QLabel(h.title if h else ""), Text.STRONG)
        layout.addWidget(title)
        self.view = HelpView(0)
        self.view.links_wanted = box.links_wanted() if box is not None else {"manual": True, "how": False,
                                                                             "ask": False}
        self.view.show_help(hid)
        self.view.link.connect(lambda kind, value: box.follow(kind, value) if box is not None else None)
        layout.addWidget(self.view)
        layout.addStretch(1)
        self.resize(320, 220)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)


class HelpPopup(QFrame):
    """The same text as the box, beside what asked for it, where the box is not shown (a low panel, the panel
    closed, a dialog): one at a time, closed by Esc, by a click outside or by its «?» again."""

    WIDTH = 280
    current: HelpPopup | None = None

    def __init__(self, box: HelpBox | None, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("help-popup")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedWidth(self.WIDTH)
        self.box = box
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        self.title = set_text(QLabel(), Text.STRONG)
        layout.addWidget(self.title)
        self.view = HelpView(0)
        self.view.link.connect(self._follow)
        layout.addWidget(self.view)

    @classmethod
    def show_for(cls, hid: str, widget=None, at: QPoint | None = None, box: HelpBox | None = None) -> HelpPopup:
        if cls.current is not None:
            cls.current.close()
        popup = cls(box, widget.window() if widget is not None else None)
        h = helps.get(hid)
        popup.title.setText(h.title)
        popup.view.links_wanted = box.links_wanted() if box is not None else {"manual": True, "how": False,
                                                                              "ask": False}
        popup.view.show_help(hid)
        popup.adjustSize()
        if at is None:
            at = widget.mapToGlobal(QPoint(0, widget.height() + 2)) if widget is not None else QPoint(0, 0)
        screen = QApplication.screenAt(at) or QApplication.primaryScreen()
        area = screen.availableGeometry() if screen is not None else QRect(at, popup.size())
        x = min(max(area.left(), at.x()), area.right() - popup.width())
        y = at.y() if at.y() + popup.height() <= area.bottom() else max(area.top(), at.y() - popup.height() - 24)
        popup.move(x, y)
        popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        popup.show()
        cls.current = popup
        return popup

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        if HelpPopup.current is self:
            HelpPopup.current = None
        super().closeEvent(event)

    def _follow(self, kind: str, value: str) -> None:
        self.close()
        if self.box is not None:
            self.box.follow(kind, value)
        elif kind == "manual":
            ManualView(self.parentWidget()).open(value)


def dress(doc) -> None:
    """A document made from markdown in the catalogue's styles (R121): Qt makes a first heading 28 px and its bold
    700; here the first heading is Text.DISPLAY, the second Text.HEADING, the others Text.TITLE, the bold the
    semibold."""
    from PySide6.QtGui import QTextCursor, QTextFormat
    from .design import Type
    sizes = {1: Text.DISPLAY, 2: Text.HEADING}
    block = doc.begin()
    while block.isValid():
        level = block.blockFormat().headingLevel()
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            it += 1
            fmt = fragment.charFormat()
            if level:
                # the size of its own: Qt's adjustment of a heading, even at nought, would win over it
                style = sizes.get(level, Text.TITLE)
                fmt.clearProperty(QTextFormat.Property.FontSizeAdjustment)
                fmt.setProperty(QTextFormat.Property.FontPixelSize, style.size)
                fmt.setFontWeight(style.weight)
            elif fmt.fontWeight() > Type.SEMIBOLD:
                fmt.setFontWeight(Type.SEMIBOLD)
            else:
                continue
            cursor = QTextCursor(doc)
            cursor.setPosition(fragment.position())
            cursor.setPosition(fragment.position() + fragment.length(), QTextCursor.MoveMode.KeepAnchor)
            cursor.setCharFormat(fmt)
        block = block.next()


class ManualView(QDialog):
    """The manual (docs/manuale) inside the program: the chapters on the left, the chapter on the right, opened at
    a heading's anchor; the links between chapters followed here, those to the web in the browser."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Meridiana's manual"))
        self.setWindowFlag(Qt.WindowType.Window)
        self.setModal(False)
        self.folder = helps.manual_dir()
        self.chapter, self.anchor = "", ""
        self.chapters = QListWidget()
        self.chapters.setMaximumWidth(220)
        for name in helps.CHAPTERS:
            path = self.folder / name if self.folder is not None else None
            if path is None or not path.exists():
                continue
            item = QListWidgetItem(helps.chapter_title(path.read_text(encoding="utf-8")) or name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.chapters.addItem(item)
        self.chapters.currentItemChanged.connect(self._chosen)
        self.page = QTextBrowser()
        self.page.setOpenLinks(False)
        self.page.anchorClicked.connect(self._follow)
        split = QSplitter()
        split.addWidget(self.chapters)
        split.addWidget(self.page)
        split.setStretchFactor(1, 1)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(split)
        self.resize(940, 680)

    def open(self, ref: str = "") -> None:
        chapter, anchor = helps.split(ref or helps.CHAPTERS[0])
        self.load(chapter or self.chapter or helps.CHAPTERS[0])
        self.show()
        self.raise_()
        self.activateWindow()
        self.go_to(anchor)
        QTimer.singleShot(0, self, lambda: self.go_to(self.anchor))      # again once laid out at its width

    def load(self, chapter: str) -> None:
        if chapter == self.chapter:
            return
        path = self.folder / chapter if self.folder is not None else None
        if path is None or not path.is_file():
            self.page.setPlainText(_("The manual is not installed with this copy of Meridiana."))
            self.chapter = ""
            return
        self.chapter = chapter
        self.page.setMarkdown(path.read_text(encoding="utf-8"))
        dress(self.page.document())
        for row in range(self.chapters.count()):
            if self.chapters.item(row).data(Qt.ItemDataRole.UserRole) == chapter:
                blocked = self.chapters.blockSignals(True)
                self.chapters.setCurrentRow(row)
                self.chapters.blockSignals(blocked)

    def go_to(self, anchor: str) -> bool:
        """The heading with this anchor at the top of the page, the cursor on it; the top without one."""
        self.anchor = anchor
        bar = self.page.verticalScrollBar()
        if not anchor:
            bar.setValue(0)
            return True
        doc = self.page.document()
        seen: dict = {}
        block = doc.begin()
        while block.isValid():
            if block.blockFormat().headingLevel():
                base = helps.slug(block.text())
                n = seen.get(base, 0)
                seen[base] = n + 1
                if (base if n == 0 else f"{base}-{n}") == anchor:
                    self.page.setTextCursor(QTextCursor(block))
                    bar.setValue(int(doc.documentLayout().blockBoundingRect(block).top()))
                    return True
            block = block.next()
        return False

    def _chosen(self, item, _previous) -> None:
        if item is not None:
            self.load(item.data(Qt.ItemDataRole.UserRole))
            self.go_to("")

    def _follow(self, url: QUrl) -> None:
        if url.scheme() in ("http", "https", "mailto"):
            QDesktopServices.openUrl(url)
            return
        name = url.path().rsplit("/", 1)[-1]
        if name.endswith(".md"):
            self.load(name)
        self.go_to(url.fragment())
