"""Meridio in the window (study 14, 7.3 and 8; study 17, theme G; design 3.9): one widget for the window, a child
of the central area, the character alone in a circle of 46 px that floats over the views, can be dragged and
stays where he is when the phase changes (R155): he moves only off what the new phase keeps at the bottom of its card
(the sun bar of the model), sliding in 320 ms (at once when the desktop asks for less motion), his bubble open
sliding with him. A click or Ctrl+L opens his speech bubble beside him (R33: never over him, the tail towards
him, from his free side towards the middle of the view; no room there, he slides to a free corner first), with
the conversation, the three questions ready numbered 1, 2, 3, the field; Esc closes it. The bubble grows from
the character in 220 ms and fades out in 160 ms, is resized from the corner opposite the tail (QSizeGrip) and
remembers its size. Docked (R17, «Dock in the panels») the same conversation goes into a panel of the window
with the character at its head; there is no bubble then.

The character moves a little (G2 and the decisions of 23/10/2026): the rays turn one turn a minute and stop a
few seconds after the chat is closed, the disc breathes, the eyes blink, glance aside and follow the pointer,
four brief faces come when the chat is used and now and then. All of it is `assistant.Mood`, asked twenty times
a second by one QTimer; the character is redrawn only when the frame changed, from pixmaps in a cache (the
turning rays are one pixmap turned by QPainter; in the pixel style eight pre-drawn steps). The timer is stopped
when the window is not active, when the character is hidden, with «less motion» from the desktop and with
«Meridio animated» off in the preferences: then the face only changes state (G3). The two drawings, smooth and
pixel (R34), are computed in meridiana/assistant/__init__.py, as where he stands.

What he answers is the conversation's (ui/assistant_chat.Chat, task 14): his bubble shows the words as he says
them (R156: a few characters at every frame, steadier than the pieces the model sends, an answer that came whole
said in three seconds at most; all at once when nothing is to move), what he read or did as small lines (`note`), the cards of his
proposals and of the consent above the field, the line of the tokens and the cost; at its head the chip of where he
thinks, with its menu, and the speaker of his voice; on the character, a house or a cloud. A widget alone, without a
conversation behind it, still ends each turn by saying that it is not connected."""

from __future__ import annotations

import functools
import math
import time

from PySide6.QtCore import (QByteArray, QEasingCurve, QEvent, QParallelAnimationGroup, QPoint, QPointF,
                            QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer, Signal)
from PySide6.QtGui import QColor, QCursor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLayout, QLineEdit,
                               QPushButton, QSizeGrip, QSizePolicy, QTextBrowser, QToolButton, QVBoxLayout, QWidget)

from .. import assistant
from ..assistant import text as words
from ..i18n import _
from . import icons
from .cards import default_tokens
from .design import Icon, Motion, Space, Text, Type, set_text, text_font

MIN_OPEN_HEIGHT = 220
QUESTIONS_HEIGHT = 260          # below this the questions ready are hidden: the field and the conversation stay
SLIDE_MS = 320                  # his own pace (R155, Daniel 25/10/2026: at 130 ms «troppo rapido, meglio com'era
                                # prima»)
# the bubble at its size from the start, fading in as it slides a few pixels from his side, and out the same way:
# growing from the tail laid its content out again at every frame, in jerks (Daniel, 24/10/2026)
OPEN_MS, CLOSE_MS = Motion.NORMAL, Motion.QUICK         # the bubble comes, it goes (ui/design.py)
SLIDE_IN = 10                   # pixels the bubble comes from, towards the character
FRAME_MS = 50                   # twenty frames a second
ANSWER_WAIT_MS = 600            # without a conversation behind him (a widget alone): the turn lasts this long
RENDER_MS = 50                  # the answer as it comes is drawn again at most twenty times a second
DOTS_MS = 300
SPEAK_CPS = 60                  # his words as he says them (R156): this many characters a second at least,
SPEAK_MAX_S = 3.0               # and what he has still to say said in this long at most
RADIUS = 10                     # the bubble's corners


def render(text: str, size: int, crisp: bool = False, dpr: float = 1.0) -> QPixmap:
    """An SVG drawn `size` logical pixels across at the screen's density `dpr` (drawn at 1 and stretched it was
    blurred on Daniel's screens at 2 and 2.5, 24/10/2026); `crisp` for the pixel style (no antialiasing)."""
    pix = QPixmap(round(size * dpr), round(size * dpr))
    pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(text.encode("utf-8")))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, not crisp)
    renderer.render(p, QRectF(0, 0, size, size))
    p.end()
    return pix


@functools.lru_cache(maxsize=256)
def picture(text: str, colour: str, size: int, thinking: bool = False, gaze: tuple[int, int] = (0, 0),
            blink: bool = False, expression: str = "", style: str = "smooth", rays: float = 0.0,
            parts: str = "all", dpr: float = 1.0) -> QPixmap:
    """Meridio drawn `size` pixels across, without his circle: once per look, not at every paint. `parts` picks
    the layer ("all", "rays", "face"); in the pixel style `rays` is turned into one of the eight steps."""
    if style == "pixel":
        text_svg = assistant.pixel_svg(text, colour, thinking, gaze, blink, expression, assistant.pixel_step(rays),
                                       parts=parts)
        return render(text_svg, size, crisp=True, dpr=dpr)
    return render(assistant.svg(text, colour, thinking, gaze, blink, expression, rays, parts=parts), size, dpr=dpr)


def inner_size(width: int, style: str) -> int:
    """How wide the character is drawn inside a circle of `width`: 74 %, and in the pixel style a multiple of
    the grid (17 cells), so that every cell is whole pixels."""
    inner = int(width * 0.74)
    if style == "pixel":
        inner = max(assistant.PIXEL_N, (inner // assistant.PIXEL_N) * assistant.PIXEL_N)
    return inner


class Face(QWidget):
    """The character in his circle: the floating assistant, and the head of the panel when docked. It draws the
    owner's current frame: the rays turned, the face with its gaze, blink and expression, the breath's scale."""

    def __init__(self, size: int, owner: "Assistant"):
        super().__init__(owner)
        self.owner = owner
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _event) -> None:
        c = self.owner.colours
        f = self.owner.frame
        style = self.owner.style
        w = self.width()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(c["line"]), 1.0))
        p.setBrush(QColor(c["panel"]))
        p.drawEllipse(QRectF(0.5, 0.5, w - 1, w - 1))
        inner = inner_size(w, style)
        off = (w - inner) / 2
        dpr = self.devicePixelRatioF()
        if style == "pixel":
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
            p.drawPixmap(QPointF(off, off), picture(c["text"], c["assistant"], inner, style="pixel", rays=f.rays,
                                                    parts="rays", dpr=dpr))
            p.drawPixmap(QPointF(off, off), picture(c["text"], c["assistant"], inner, f.thinking, f.gaze, f.blink,
                                                    f.expression, style="pixel", parts="face", dpr=dpr))
            self._mark(p)
            return
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        cx, cy, _r = assistant.DISC
        unit = inner / 24
        p.save()
        p.setClipRect(QRectF(off, off, inner, unit * assistant.RAYS_CLIP_Y))
        p.translate(off + cx * unit, off + cy * unit)
        p.rotate(f.rays)
        p.drawPixmap(QPointF(-cx * unit, -cy * unit), picture(c["text"], c["assistant"], inner, parts="rays",
                                                              dpr=dpr))
        p.restore()
        face = picture(c["text"], c["assistant"], inner, f.thinking, f.gaze, f.blink, f.expression, parts="face",
                       dpr=dpr)
        side = inner * f.scale
        o = (w - side) / 2
        p.drawPixmap(QRectF(o, o, side, side), face, QRectF(face.rect()))     # the source in device pixels
        self._mark(p)

    def _mark(self, p: QPainter) -> None:
        """Where he thinks (study 14, 6.6 and 8): a house for the local model, a cloud for a cloud one, on a small
        disc at the bottom right of the character; nothing while no conversation is behind him."""
        where = self.owner.where
        if not where or self.width() < assistant.SIZE:
            return
        c = self.owner.colours
        d = Icon.CONTROL
        disc = QRectF(self.width() - d - 0.5, self.height() - d - 0.5, d, d)
        p.setPen(QPen(QColor(c["line"]), 1.0))
        p.setBrush(QColor(c["panel"]))
        p.drawEllipse(disc)
        glyph = d - 2 * Space.XXS
        pix = icons.icon("house" if where == "local" else "cloud").pixmap(QSize(glyph, glyph),
                                                                          self.devicePixelRatioF())
        p.drawPixmap(QRectF(disc.x() + Space.XXS, disc.y() + Space.XXS, glyph, glyph), pix, QRectF(pix.rect()))


class Dots(QWidget):
    """Three dots while Meridio answers, the raised one going round (with less motion, three still dots)."""

    def __init__(self, owner: "Assistant", parent=None):
        super().__init__(parent)
        self.owner = owner
        self.phase = 0
        self.setFixedHeight(14)
        self.timer = QTimer(self, interval=DOTS_MS)
        self.timer.timeout.connect(self._step)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.owner.moving():
            self.timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.timer.stop()
        self.phase = 0

    def _step(self) -> None:
        self.phase = (self.phase + 1) % 3
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        moving = self.timer.isActive()
        for n in range(3):
            colour = QColor(self.owner.colours["text" if (not moving or n == self.phase) else "muted"])
            p.setBrush(colour)
            y = 7 - (3 if moving and n == self.phase else 0)
            p.drawEllipse(QPointF(10 + n * 10, y), 3, 3)


class QuestionRow(QPushButton):
    """A response option as a program button, with its hover, a number and the whole wrapped text (R197)."""

    chosen = Signal(str)

    def __init__(self, number: int, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        row = QHBoxLayout(self)
        self.setObjectName("assistant-suggestion")
        row.setContentsMargins(Space.M, Space.S, Space.M, Space.S)
        row.setSpacing(Space.M)
        self.number = QLabel(str(number))
        self.number.setFixedWidth(12)
        self.number.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        row.addWidget(self.number)
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        row.addWidget(self.label, 1)
        self.arrow = QLabel("›")
        self.arrow.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.arrow)
        for child in (self.number, self.label, self.arrow):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.clicked.connect(lambda: self.chosen.emit(self.text()))

    def text(self) -> str:
        return self.label.text()

    def setText(self, text: str) -> None:
        self.label.setText(text)
        self.setAccessibleName(text)
        self.setToolTip(text)

    def set_colours(self, muted: str) -> None:
        for w in (self.number, self.arrow):
            w.setStyleSheet(f"color: {muted};")

    def sizeHint(self):
        hint = super().sizeHint().expandedTo(QSize(280, 0))
        hint.setHeight(self.heightForWidth(hint.width()))
        return hint

    def heightForWidth(self, width: int) -> int:
        margins = self.layout().contentsMargins()
        room = (width - margins.left() - margins.right() - self.number.width()
                - self.arrow.sizeHint().width() - 2 * self.layout().spacing())
        needed = self.label.heightForWidth(max(1, room))
        return max(28, needed + margins.top() + margins.bottom())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.label.updateGeometry()
        self.updateGeometry()


class Bubble(QFrame):
    """The speech bubble: a rounded card with a tail towards the character, resized from the corner opposite the
    tail. A sub-window (Qt.SubWindow) so that the size grip resizes it and not the window."""

    resizedByHand = Signal()

    def __init__(self, area: QWidget, owner: "Assistant"):
        super().__init__(area)
        self.owner = owner
        self.setWindowFlag(Qt.WindowType.SubWindow, True)
        self.setObjectName("bubble")
        self.setMinimumSize(*assistant.BUBBLE_MIN)
        self.shape: assistant.Bubble | None = None
        self.placing = False
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(1, 1, 1, 1)
        self.box.setSpacing(0)
        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(14, 14)
        self.grip.raise_()
        self.hide()

    def set_shape(self, shape: assistant.Bubble) -> None:
        """The place, the size, the tail's side: the margins leave room for the tail, the grip goes to the
        opposite corner."""
        self.shape = shape
        t = assistant.TAIL + 1
        self.box.setContentsMargins(t if shape.tail == "left" else 1, t if shape.tail == "top" else 1,
                                    t if shape.tail == "right" else 1, t if shape.tail == "bottom" else 1)
        self.placing = True
        self.setGeometry(QRect(shape.x, shape.y, shape.width, shape.height))
        self.placing = False
        self._place_grip()
        if hasattr(self.owner, "title"):
            self.owner.title.setAlignment(Qt.AlignmentFlag.AlignRight if shape.grip.endswith("left")
                                          else Qt.AlignmentFlag.AlignLeft)
        self.update()

    def _place_grip(self) -> None:
        if self.shape is None:
            return
        corner = self.shape.grip
        inset = {"left": 2 + (assistant.TAIL if self.shape.tail == "left" else 0),
                 "right": 2 + (assistant.TAIL if self.shape.tail == "right" else 0),
                 "top": 2 + (assistant.TAIL if self.shape.tail == "top" else 0),
                 "bottom": 2 + (assistant.TAIL if self.shape.tail == "bottom" else 0)}
        x = inset["left"] if corner.endswith("left") else self.width() - self.grip.width() - inset["right"]
        y = inset["top"] if corner.startswith("top") else self.height() - self.grip.height() - inset["bottom"]
        self.grip.move(x, y)
        self.grip.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place_grip()
        if not self.placing and self.shape is not None and self.isVisible():
            self.resizedByHand.emit()

    def body(self) -> QRectF:
        """The card without the tail."""
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        if self.shape is not None:
            t = assistant.TAIL
            r.adjust(t if self.shape.tail == "left" else 0, t if self.shape.tail == "top" else 0,
                     -t if self.shape.tail == "right" else 0, -t if self.shape.tail == "bottom" else 0)
        return r

    def paintEvent(self, _event) -> None:
        c = self.owner.colours
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = self.body()
        path = QPainterPath()
        path.addRoundedRect(body, RADIUS, RADIUS)
        if self.shape is not None:
            t, half = assistant.TAIL, 11.0
            tail = QPainterPath()
            s = self.shape
            if s.tail in ("left", "right"):
                at = min(max(s.at, RADIUS + half), self.height() - RADIUS - half)
                x = body.left() if s.tail == "left" else body.right()
                tip = x - t if s.tail == "left" else x + t
                tail.moveTo(x, at - half)
                tail.lineTo(tip, at)
                tail.lineTo(x, at + half)
            else:
                at = min(max(s.at, RADIUS + half), self.width() - RADIUS - half)
                y = body.top() if s.tail == "top" else body.bottom()
                tip = y - t if s.tail == "top" else y + t
                tail.moveTo(at - half, y)
                tail.lineTo(at, tip)
                tail.lineTo(at + half, y)
            tail.closeSubpath()
            path = path.united(tail)
        p.setPen(QPen(QColor(c["line"]), 1.0))
        p.setBrush(QColor(c["panel"]))
        p.drawPath(path.simplified())


class Assistant(QFrame):
    """The floating character; `area` is where he may stand (the main window: over every card, Daniel 24/10/2026),
    between `top` and `bottom` pixels; `home` the card he starts on (the views), in the area's pixels."""

    openedChanged = Signal(bool)
    dockRequested = Signal(bool)                            # its button: into the panels (True) or floating
    bubbleResized = Signal(int, int)                        # the bubble's size, to remember
    asked = Signal(str)                                     # a question, to the conversation (ui/assistant_chat.py)
    stopped = Signal()                                      # «Stop»: the turn dropped

    def __init__(self, area: QWidget):
        super().__init__(area)
        self.area = area
        self.setObjectName("assistant")
        t = default_tokens()
        self.colours = {"text": t["text"], "assistant": t["assistant"], "panel": t["panel"], "line": t["line"],
                        "muted": t["muted"]}
        self.tab = "model"
        self.followed: list[QWidget] = []                   # widgets its place depends on (follow)
        self.places: dict[str, assistant.Anchor] = {}      # the places the designer dragged it to, per tab
        self.reserved = lambda: 0                           # the pixels at the bottom of the model (the sun bar)
        self.top = lambda: 0                                # the pixels at the top it leaves free (the tabs' bar)
        self.bottom = lambda: 0                             # and at the bottom (the status bar)
        self.home = lambda: QRect()                         # the card of his first place, when it is not the area
        self.avoid = lambda: []                             # rectangles (area coordinates) the bubble keeps off
        self._reduced_motion = False
        self.animated = True                                # Preferences > Assistant, «Meridio animated»
        self.style = "smooth"                               # or "pixel" (R34)
        self.opened = False
        self.drag: tuple | None = None                      # (where the press was, global; the widget's place)
        self.dock = None                                    # the window's panel for it (set_dock), when docked
        self.docked = False
        self.moved = False
        self.bubble_dims = assistant.BUBBLE_DEFAULT
        self.clock = time.monotonic
        self.mood = assistant.Mood(seed=int(self.clock() * 1000) % 100000, now=self.clock())
        self.frame = assistant.Frame()
        self.timer = QTimer(self, interval=FRAME_MS)
        self.timer.timeout.connect(self._tick)
        self.pointer_seen = QPoint()                        # where the pointer was at the last frame (the gaze)
        self.pending = QTimer(self, singleShot=True, interval=ANSWER_WAIT_MS)
        self.pending.timeout.connect(self._not_connected)
        self.connected = False                              # a conversation behind him (ui/assistant_chat.Chat)
        self.restore = lambda text: text                    # the names withheld from the cloud, put back
        self.suggest = assistant.questions                  # tab -> the questions ready (the conversation's, R108)
        self.empty = ""                                     # what an empty conversation shows: his greeting
        self.live = ""                                      # the answer being written
        self.where = ""                                     # "local" or "cloud": the mark on the character
        self.render_timer = QTimer(self, singleShot=True, interval=RENDER_MS)
        self.render_timer.timeout.connect(self._show_messages)
        self.told = 0                                       # the characters of his words shown so far (R156)
        self.heard = 0                                      # and of those he had to say at the last frame
        self.speak_until = 0.0                              # when what he has to say is to be said (monotonic)
        self.speak_timer = QTimer(self, interval=FRAME_MS)
        self.speak_timer.timeout.connect(self._speak)
        self.animation = QPropertyAnimation(self, b"pos", self)
        self.animation.setDuration(SLIDE_MS)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.bubble_animation: QParallelAnimationGroup | None = None
        self.after_slide = None                             # what to do when the slide ends (open the bubble)
        self.animation.finished.connect(self._slide_done)
        self.bubble_slide: QPropertyAnimation | None = None  # the bubble open going with him (R155)

        self.setFixedSize(assistant.SIZE, assistant.SIZE)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)
        self.face = Face(assistant.SIZE, self)              # the character
        self.face.setToolTip(_("{name}, the assistant: click to open (Ctrl+L)").format(name=assistant.NAME))
        box.addWidget(self.face)

        self.bubble = Bubble(area, self)                    # open: the conversation beside him
        self.bubble.resizedByHand.connect(self._bubble_resized)
        self.panel = QWidget(self.bubble)
        self.bubble.box.addWidget(self.panel)
        inside = QVBoxLayout(self.panel)
        inside.setContentsMargins(10, 8, 10, 10)
        inside.setSpacing(6)
        self.head = QWidget(self.panel)
        row = QHBoxLayout(self.head)
        row.setContentsMargins(0, 0, 0, 0)
        self.small = Face(28, self)                         # the character at the head, when docked
        self.small.hide()                                   # floating, he is right beside the bubble
        row.addWidget(self.small)
        self.title = set_text(QLabel(assistant.NAME), Text.TITLE)
        row.addWidget(self.title, 1)
        # where he thinks, with its menu (the conversation's: ui/assistant_chat.Chat), and his spoken voice; both
        # hidden while nothing is behind him
        self.where_button = QToolButton()
        self.where_button.setAutoRaise(True)
        self.where_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.where_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.where_button.setIconSize(QSize(Icon.CONTROL, Icon.CONTROL))
        self.where_button.hide()
        row.addWidget(self.where_button)
        self.voice_button = QToolButton()
        self.voice_button.setCheckable(True)
        self.voice_button.setAutoRaise(True)
        self.voice_button.setIcon(icons.icon("volume-x"))
        self.voice_button.toggled.connect(self._voice_icon)
        self.voice_button.hide()
        row.addWidget(self.voice_button)
        self.dock_button = QToolButton()
        self.dock_button.setCheckable(True)
        self.dock_button.setAutoRaise(True)
        self.dock_button.setIcon(icons.icon("dock"))
        self.dock_button.setToolTip(_("Dock in the panels, as Project and Properties"))
        self.dock_button.clicked.connect(lambda on: self.dockRequested.emit(on))
        row.addWidget(self.dock_button)
        self.close_button = QToolButton()
        self.close_button.setText("–")
        self.close_button.setAutoRaise(True)
        self.close_button.setToolTip(_("Back to the character (Esc)"))
        self.close_button.clicked.connect(self.close_panel)
        row.addWidget(self.close_button)
        inside.addWidget(self.head)
        self.context = QLabel()                            # what the conversation is about: the tab
        inside.addWidget(self.context)
        self.cost = QLabel()                               # the tokens and the cost of the conversation
        self.cost.setWordWrap(True)
        self.cost.setFont(text_font(Text.CAPTION))
        self.cost.hide()
        inside.addWidget(self.cost)
        self.conversation = QTextBrowser()
        self.conversation.setObjectName("assistant-conversation")
        self.conversation.setFrameShape(QFrame.Shape.NoFrame)
        self.conversation.setOpenLinks(False)
        self.conversation.setMinimumHeight(24)              # it gives way before the field in a low area
        # his bold the catalogue's semibold (R121): «<b>» is 700, a third weight
        self.conversation.document().setDefaultStyleSheet(f"b, strong {{ font-weight: {Type.SEMIBOLD}; }}")
        # the last words stay in sight when the conversation gets lower (the questions ready come back after the
        # answer, a card comes): at the bottom it stays at the bottom, until the designer scrolls up
        self.at_bottom = True
        bar = self.conversation.verticalScrollBar()
        bar.valueChanged.connect(self._scrolled)
        bar.rangeChanged.connect(self._range_changed)
        inside.addWidget(self.conversation, 1)
        self.dots = Dots(self, self.panel)
        self.dots.hide()
        inside.addWidget(self.dots)
        self.cards = QWidget(self.panel)                    # the proposals and the consent, above the field
        self.cards_box = QVBoxLayout(self.cards)
        self.cards_box.setContentsMargins(0, 0, 0, 0)
        self.cards_box.setSpacing(Space.S)
        self.cards.hide()
        inside.addWidget(self.cards)
        self.questions_box = QWidget(self.panel)
        qbox = QVBoxLayout(self.questions_box)
        qbox.setContentsMargins(0, 0, 0, 0)
        qbox.setSpacing(Space.XXS)
        qbox.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.questions_title = QToolButton()
        self.questions_title.setText(_("Suggestions"))
        self.questions_title.setToolTip(_("Show or hide suggestions. Keys: 1, 2, 3."))
        self.questions_title.setAutoRaise(True)
        self.questions_title.setCheckable(True)
        self.questions_title.setChecked(True)
        self.questions_title.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.questions_title.setArrowType(Qt.ArrowType.DownArrow)
        self.questions_title.setFont(text_font(Text.SECONDARY))
        self.questions_title.toggled.connect(self._toggle_suggestions)
        qbox.addWidget(self.questions_title)
        self.questions: list[QuestionRow] = []
        for n in range(3):
            q = QuestionRow(n + 1)
            q.chosen.connect(self.ask)
            qbox.addWidget(q)
            self.questions.append(q)
        inside.addWidget(self.questions_box)
        self.questions_timer = QTimer(self.questions_box, singleShot=True)
        self.questions_timer.timeout.connect(self._fit_questions)
        self.field = QLineEdit()
        self.field.setPlaceholderText(_("Ask {name}…").format(name=assistant.NAME))
        self.field.returnPressed.connect(lambda: self.ask(self.field.text()))
        self.send_action = self.field.addAction(icons.icon("arrow-up"), QLineEdit.ActionPosition.TrailingPosition)
        self.send_action.setText(_("Send message"))
        self.send_action.setToolTip(_("Send message"))
        self.send_action.triggered.connect(lambda: self.ask(self.field.text()))
        self.stop_action = self.field.addAction(QIcon(), QLineEdit.ActionPosition.TrailingPosition)
        self.stop_action.setText(_("Stop"))
        self.stop_action.setToolTip(_("Stop the answer"))
        self.stop_action.triggered.connect(self.stop)
        self.stop_action.setVisible(False)
        inside.addWidget(self.field)
        self.messages: list[tuple[str, str]] = []           # (who, text): "you", "assistant" or "note"
        # the filters last, when every widget they look at exists
        for w in (self.face, self.small, self.head, self.bubble, self.panel, self.conversation, self.field, area):
            w.installEventFilter(self)
        # bound methods, not lambdas: Qt drops these connections when the assistant is deleted (a window
        # closed), a lambda would still be called by the application's signals and find him gone
        app = QApplication.instance()
        app.applicationStateChanged.connect(self._application_changed)
        app.focusWindowChanged.connect(self._application_changed)
        self.set_tab("model", animate=False)
        self._update_timer()

    # look

    def set_colours(self, tokens: dict) -> None:
        self.colours = {"text": tokens["text"], "assistant": tokens["assistant"], "panel": tokens["panel"],
                        "line": tokens["line"], "muted": tokens["muted"]}
        self.questions_title.setStyleSheet(f"color: {self.colours['muted']};")
        self.cost.setStyleSheet(f"color: {self.colours['muted']};")
        self.context.setStyleSheet(f"color: {self.colours['muted']};")
        self.conversation.setStyleSheet("QTextBrowser#assistant-conversation { background: transparent; border: none; }")
        for q in self.questions:
            q.set_colours(self.colours["muted"])
        self.stop_action.setIcon(self._stop_icon())
        self._frame()
        self.update()
        self.face.update()
        self.small.update()
        self.bubble.update()

    def _stop_icon(self) -> QIcon:
        pix = QPixmap(16, 16)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.colours["text"]))
        p.drawRoundedRect(QRectF(3, 3, 10, 10), 2, 2)
        p.end()
        return QIcon(pix)

    def _frame(self) -> None:
        self.setStyleSheet("#assistant { background: transparent; border: none; }")

    def icon(self, size: int = 16) -> QIcon:
        if self.style == "pixel":
            size = max(assistant.PIXEL_N, (size // assistant.PIXEL_N) * assistant.PIXEL_N)   # whole cells
        dpr = self.devicePixelRatioF()                  # the icon of the status bar, sharp on the screen's density
        return QIcon(picture(self.colours["text"], self.colours["assistant"], size, style=self.style, dpr=dpr))

    def set_style(self, style: str) -> None:
        """The smooth or the pixel drawing (R34), the same movements."""
        self.style = style if style in assistant.STYLES else "smooth"
        self.face.update()
        self.small.update()

    def set_animated(self, on: bool) -> None:
        """Preferences > Assistant, «Meridio animated»: off, he only changes state."""
        self.animated = on
        self._update_timer()

    def set_bubble_size(self, width: int, height: int) -> None:
        self.bubble_dims = (max(assistant.BUBBLE_MIN[0], int(width)), max(assistant.BUBBLE_MIN[1], int(height)))
        if self.opened and not self.docked:
            self.place_bubble()

    @property
    def reduced_motion(self) -> bool:
        return self._reduced_motion

    @reduced_motion.setter
    def reduced_motion(self, on: bool) -> None:
        self._reduced_motion = bool(on)
        self._update_timer()

    def moving(self) -> bool:
        """Whether anything moves: the desktop and the preferences allow it."""
        return self.animated and not self._reduced_motion

    # the small movements

    def _update_timer(self) -> None:
        """The frame timer runs only when something can be seen moving: the character or the docked panel
        visible, the application active, and movement allowed."""
        app = QApplication.instance()
        shown = self.isVisible() or (self.docked and self.panel.isVisible())
        active = app.applicationState() == Qt.ApplicationState.ApplicationActive
        want = self.moving() and shown and active and self._window_active()
        if want and not self.timer.isActive():
            self.mood.touch(self.clock())
            self.timer.start()
        elif not want and self.timer.isActive():
            self.timer.stop()
        if not want:
            self._still()

    def _application_changed(self, _what=None) -> None:
        """The application active or not, another window with the keyboard: the timer follows."""
        self._update_timer()

    def _window_active(self) -> bool:
        """The window active: on the offscreen platform no window may be active at all, and then it counts
        as active (the application state says when the user is elsewhere)."""
        return self.window().isActiveWindow() or QApplication.activeWindow() is None

    def _still(self) -> None:
        """The still face of the state (G3), when nothing moves."""
        self._show_frame(assistant.Frame(thinking=self.mood.state == assistant.THINKING))

    def _tick(self) -> None:
        if not self._window_active():
            self._update_timer()
            return
        self._gaze()
        self._show_frame(self.mood.frame(self.clock()))

    def _gaze(self) -> None:
        """The pointer over the area, read at each frame: his eyes follow it (R120: an application-wide event filter
        did it before, and every event of every widget went through it)."""
        where = QCursor.pos()
        if where == self.pointer_seen or self.drag is not None:
            return
        self.pointer_seen = where
        if self.area.rect().contains(self.area.mapFromGlobal(where)):
            self._look_at_global(QPointF(where))

    def _show_frame(self, frame: assistant.Frame) -> None:
        if frame == self.frame:
            return
        self.frame = frame
        if self.face.isVisible():
            self.face.update()
        if self.small.isVisible():
            self.small.update()

    def set_state(self, state: str) -> None:
        self.mood.set_state(state, self.clock())
        if not self.timer.isActive():
            self._still()

    def _look_at_global(self, where: QPointF) -> None:
        """The pointer, in character sizes from the centre of the character, to the mood."""
        local = self.mapFromGlobal(where.toPoint())
        w = self.width() or 1
        self.mood.look_at(((local.x() - w / 2) / w, (local.y() - w / 2) / w), self.clock())

    # where it stands

    def free(self) -> tuple[int, int, int]:
        """The part of the area it may stand in: below the tabs' bar (`top` pixels) and above the status bar
        (`bottom`), its width and height."""
        top = self.top()
        return top, self.area.width(), max(0, self.area.height() - top - self.bottom())

    def size_now(self) -> tuple[int, int]:
        return assistant.SIZE, assistant.SIZE

    def anchor(self, tab: str | None = None) -> assistant.Anchor:
        tab = tab or self.tab
        return self.places.get(tab) or assistant.default_anchor(tab, self.reserved())

    def target(self) -> QPoint:
        top, w, h = self.free()
        home = self.home()
        if self.tab not in self.places and home.isValid() and not home.isEmpty():
            return self.at_home(self.anchor())
        x, y = assistant.place(self.anchor(), self.size_now(), (w, h))
        return self.off_band(QPoint(x, y + top))

    def band(self) -> QRect:
        """The strip at the bottom of the card in the middle he does not stand on (`reserved`: the sun bar on the
        model, the plan's attribution on the plant), with his margin above it, in the area's pixels; none when
        nothing is kept."""
        kept = self.reserved()
        if kept <= 0:
            return QRect()
        home = self.home()
        if not home.isValid() or home.isEmpty():
            top, w, h = self.free()
            home = QRect(0, top, w, h)
        return QRect(home.left(), home.bottom() + 1 - kept - assistant.MARGIN, home.width(), kept + assistant.MARGIN)

    def off_band(self, at: QPoint) -> QPoint:
        """`at`, or just above the band when he would stand on it there."""
        band = self.band()
        if band.isEmpty() or not band.intersects(QRect(at, QSize(*self.size_now()))):
            return at
        return QPoint(at.x(), max(self.top(), band.top() - assistant.SIZE))

    def stay(self) -> None:
        """The phase changed: his place in it is where he stands now, clamped to the free part and off its band
        (R155: he no longer goes to a place of each phase)."""
        top, w, h = self.free()
        x, y = assistant.clamp((self.x(), self.y() - top), (w, h), self.size_now())
        at = self.off_band(QPoint(x, y + top))
        self.places[self.tab] = assistant.anchor_of((at.x(), at.y() - top), self.size_now(), (w, h))

    def at_home(self, anchor: assistant.Anchor) -> QPoint:
        """Where `anchor` puts him on the home card (the views), in the area's pixels."""
        home = self.home()
        x, y = assistant.place(anchor, self.size_now(), (home.width(), home.height()))
        return QPoint(home.x() + x, home.y() + y)

    def home_anchor(self, anchor: assistant.Anchor) -> assistant.Anchor:
        """The place in the area's terms of `anchor` on the home card: a place the window sets (the stringing
        sends him to the views' bottom left) stays on the views."""
        home = self.home()
        if not home.isValid() or home.isEmpty():
            return anchor
        top, w, h = self.free()
        at = self.at_home(anchor)
        return assistant.anchor_of((at.x(), at.y() - top), self.size_now(), (w, h))

    def follow(self, widget: QWidget) -> None:
        """A widget its place depends on (the sun bar): it moves when that one changes size or shows."""
        self.followed.append(widget)
        widget.installEventFilter(self)

    def set_tab(self, tab: str, animate: bool = True) -> None:
        """The tab changed: the same widget, the same conversation, where he stands (R155); before he is shown, at
        the tab's place."""
        self.tab = tab
        if self.isVisible() and not self.docked and self.drag is None:
            self.stay()
        from ..phases import phases
        names = {phase.id: phase.title for phase in phases()}
        self.context.setText(_("Tab: {tab}").format(tab=names.get(tab, tab)))
        self.fill_questions()
        self.reposition(animate)

    def fill_questions(self) -> None:
        """The questions ready of now (R108): from `suggest`, which the conversation behind him sets to follow what
        is being said (assistant/suggestions.py); alone, the three of the phase. A row without a question hides."""
        try:
            texts = list(self.suggest(self.tab))[:len(self.questions)]
        except Exception as error:  # noqa: BLE001  a rule that failed must not leave him without questions
            from .. import log
            log.complain("assistant", error)
            texts = assistant.questions(self.tab)
        texts += [""] * (len(self.questions) - len(texts))
        changed = texts != [row.text() for row in self.questions]
        for row, text in zip(self.questions, texts, strict=True):
            row.setText(text)
            row.setVisible(bool(text) and self.questions_title.isChecked())
        if changed:
            self.questions_timer.start(0)

    def _toggle_suggestions(self, expanded: bool) -> None:
        self.questions_title.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        for row in self.questions:
            row.setVisible(expanded and bool(row.text()))
        self.questions_box.setMinimumHeight(0)
        self.questions_timer.start(0)

    def _fit_questions(self) -> None:
        self.questions_box.setMinimumHeight(0 if self.docked else self.questions_box.sizeHint().height())
        self.panel.layout().activate()
        self._fit_bubble_content()

    def _fit_bubble_content(self) -> None:
        if self.docked or not self.opened or self.bubble.shape is None or self.bubble.placing \
                or self.bubble_animation is not None:
            return
        last = self.questions_box.mapTo(self.panel, QPoint(0, self.questions_box.height())).y()
        overflow = max(0, last - self.field.y())
        margins = self.bubble.box.contentsMargins()
        needed = max(self.bubble.height() + overflow + (Space.S if overflow else 0),
                     self.panel.sizeHint().height() + margins.top() + margins.bottom())
        if needed <= self.bubble.height():
            return
        shape = self.bubble.shape
        top, _width, available = self.free()
        bottom = shape.y + shape.height
        if shape.tail in ("left", "right"):
            height = min(needed, available)
            y = max(top, bottom - height)
        else:
            height = min(needed, top + available - shape.y)
            y = shape.y
        at = shape.at + shape.y - y if shape.tail in ("left", "right") else shape.at
        self.bubble_dims = (shape.width, height)
        self.bubble.set_shape(assistant.Bubble(shape.x, y, shape.width, height, shape.tail, at))

    def reposition(self, animate: bool = False) -> None:
        self._stop_slide()
        self.after_slide = None
        goal = self.target()
        if animate and self.moving() and self.isVisible() and goal != self.pos():
            self._bubble_along(goal)
            self.animation.setStartValue(self.pos())
            self.animation.setEndValue(goal)
            self.animation.start()
            self.raise_()
            return
        self.move(goal)
        self.raise_()
        if self.opened and not self.docked:
            self.place_bubble()

    def _bubble_along(self, goal: QPoint) -> None:
        """The bubble open slides with him to where it opens for him at `goal`, in step with him (R155: it stayed
        behind and jumped there at the end)."""
        if not self.opened or self.docked or not self.bubble.isVisible() or self.bubble_animation is not None:
            return
        shape = self.bubble_shape(goal)
        if shape is None:
            final = self.bubble.geometry().translated(goal - self.pos())
        else:
            final = QRect(shape.x, shape.y + self.top(), shape.width, shape.height)
        slide = QPropertyAnimation(self.bubble, b"geometry", self)
        slide.setDuration(SLIDE_MS)
        slide.setEasingCurve(self.animation.easingCurve())
        slide.setStartValue(self.bubble.geometry())
        slide.setEndValue(final)
        self.bubble.placing = True                          # moved with him, not resized by hand
        self.bubble_slide = slide
        slide.start()

    def _stop_slide(self) -> None:
        """His slide stopped where it is (a new place, a drag), the bubble's with it."""
        self.animation.stop()
        if self.bubble_slide is not None:
            self.bubble_slide.stop()
            self.bubble_slide.deleteLater()
            self.bubble_slide = None
            self.bubble.placing = False

    def _slide_done(self) -> None:
        if self.bubble_slide is not None:
            self.bubble_slide.stop()
            self.bubble_slide.deleteLater()
            self.bubble_slide = None
            self.bubble.placing = False
        todo, self.after_slide = self.after_slide, None
        if todo is not None:
            todo()
        elif self.opened and not self.docked:
            self.place_bubble()

    # the bubble

    def avoided(self) -> list[assistant.Rect]:
        """What the bubble keeps off, in the coordinates of the free part of the area."""
        top = self.top()
        out = []
        for r in self.avoid():
            x, y, w, h = (int(v) for v in r)
            if w > 0 and h > 0:
                out.append((x, y - top, w, h))
        return out

    def bubble_shape(self, at: QPoint | None = None) -> assistant.Bubble | None:
        """Where the bubble opens for the character at `at` (his place now when None)."""
        top, w, h = self.free()
        pos = at if at is not None else self.pos()
        character = (pos.x(), pos.y() - top, assistant.SIZE, assistant.SIZE)
        size = assistant.bubble_size(self.bubble_dims, (w, h))
        return assistant.bubble_place(character, size, (w, h), self.avoided())

    def place_bubble(self) -> None:
        """The bubble at its place beside the character, now (the area changed, he was dragged, it was resized)."""
        shape = self.bubble_shape()
        if shape is None:
            top, w, h = self.free()
            size = assistant.bubble_size(self.bubble_dims, (w, h))
            shape = assistant.bubble_place((self.x(), self.y() - top, assistant.SIZE, assistant.SIZE), size, (w, h))
        top, w, h = self.free()
        if shape is None:                                   # not even so: an area too small for both of them
            size = assistant.bubble_size(self.bubble_dims, (w, h))
            shape = assistant.bubble_fallback((self.x(), self.y() - top, assistant.SIZE, assistant.SIZE), size, (w, h))
        self.bubble.setMaximumSize(max(assistant.BUBBLE_MIN[0], w - assistant.SIZE - assistant.GAP - 2 * assistant.MARGIN),
                                   max(assistant.BUBBLE_MIN[1], h - 2 * assistant.MARGIN))    # the grip stops here
        self.bubble.set_shape(assistant.Bubble(shape.x, shape.y + top, shape.width, shape.height, shape.tail,
                                               shape.at))
        self.bubble.raise_()
        self.raise_()

    def _bubble_resized(self) -> None:
        """Dragged by its grip: the size is the new one, remembered; the tail follows."""
        self.bubble_dims = (self.bubble.width(), self.bubble.height())
        self.bubbleResized.emit(*self.bubble_dims)
        self.place_bubble()

    def _open_bubble(self, animate: bool) -> None:
        self._stop_bubble_animation()
        shape = self.bubble_shape()
        if shape is None:
            # no room beside him here: a free corner, the farthest from what is to be avoided, and open there
            top, w, h = self.free()
            character = (self.x(), self.y() - top, assistant.SIZE, assistant.SIZE)
            for corner in assistant.free_corners(character, (w, h), self.avoided(), (assistant.MARGIN, assistant.MARGIN)):
                there = QPoint(corner[0], corner[1] + top)
                if self.bubble_shape(there) is not None:
                    self.places[self.tab] = assistant.anchor_of(corner, self.size_now(), (w, h))
                    if animate and self.moving() and self.isVisible():
                        self.after_slide = lambda: self._open_bubble(animate)
                        self.animation.setStartValue(self.pos())
                        self.animation.setEndValue(there)
                        self.animation.start()
                        return
                    self.move(there)
                    break
        self.place_bubble()
        self.bubble.show()
        self._fit_questions()
        self.bubble.raise_()
        self.raise_()
        if animate and self.moving():
            final = self.bubble.geometry()
            start = self._towards_him(final)
            effect = QGraphicsOpacityEffect(self.bubble)
            self.bubble.setGraphicsEffect(effect)
            group = QParallelAnimationGroup(self)
            geom = QPropertyAnimation(self.bubble, b"geometry", group)
            geom.setDuration(OPEN_MS)
            geom.setEasingCurve(QEasingCurve.Type.OutCubic)
            geom.setStartValue(start)
            geom.setEndValue(final)
            fade = QPropertyAnimation(effect, b"opacity", group)
            fade.setDuration(OPEN_MS)
            fade.setStartValue(0.0)
            fade.setEndValue(1.0)
            group.addAnimation(geom)
            group.addAnimation(fade)
            group.finished.connect(self._opened)
            self.bubble.placing = True                      # growing is not a resize by hand (until _opened)
            self.bubble.setGeometry(start)
            self.bubble_animation = group
            group.start()

    def _towards_him(self, final: QRect) -> QRect:
        """The bubble's place moved SLIDE_IN pixels towards the character: where it fades in from."""
        s = self.bubble.shape
        tail = s.tail if s is not None else "right"
        dx = {"left": -SLIDE_IN, "right": SLIDE_IN}.get(tail, 0)
        dy = {"top": -SLIDE_IN, "bottom": SLIDE_IN}.get(tail, 0)
        return final.translated(dx, dy)

    def _opened(self) -> None:
        self._stop_bubble_animation()
        if self.opened and not self.docked:
            self.place_bubble()                             # the geometry whole again, the effect gone
            self._fit_questions()

    def _stop_bubble_animation(self) -> None:
        if self.bubble_animation is not None:
            self.bubble_animation.stop()
            self.bubble_animation.deleteLater()
            self.bubble_animation = None
        self.bubble.placing = False
        self.bubble.setGraphicsEffect(None)                 # the effect doubles the cost of every paint

    def _close_bubble(self, animate: bool) -> None:
        self._stop_bubble_animation()
        if animate and self.moving() and self.bubble.isVisible():
            final = self.bubble.geometry()
            effect = QGraphicsOpacityEffect(self.bubble)
            self.bubble.setGraphicsEffect(effect)
            group = QParallelAnimationGroup(self)
            geom = QPropertyAnimation(self.bubble, b"geometry", group)
            geom.setDuration(CLOSE_MS)
            geom.setEasingCurve(QEasingCurve.Type.InCubic)
            geom.setStartValue(final)
            geom.setEndValue(self._towards_him(final))
            fade = QPropertyAnimation(effect, b"opacity", group)
            fade.setDuration(CLOSE_MS)
            fade.setStartValue(1.0)
            fade.setEndValue(0.0)
            group.addAnimation(geom)
            group.addAnimation(fade)
            group.finished.connect(self._closed)
            self.bubble.placing = True
            self.bubble_animation = group
            group.start()
        else:
            self.bubble.hide()

    def _closed(self) -> None:
        self.bubble.placing = False
        self._stop_bubble_animation()
        self.bubble.hide()
        if self.bubble.shape is not None:
            self.bubble.set_shape(self.bubble.shape)

    # events

    def eventFilter(self, watched, event) -> bool:
        kind = event.type()
        if watched is self.area or any(watched is w for w in self.followed):
            # a move too: the page moves when the bar of the phase changes height or the gaps settle (task 17b)
            if kind in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Hide, QEvent.Type.Move) and self.drag is None:
                try:
                    self.reposition()
                except RuntimeError:        # the window going away: the widgets he reads are no longer there
                    pass
            return False
        if watched is self.bubble:
            if kind == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape and self.opened:
                self.close_panel()
                return True
            return False
        if watched is self.panel and kind == QEvent.Type.Resize:
            # a low bubble or panel: the questions ready give way to the conversation and the field
            self.questions_box.setVisible(event.size().height() >= QUESTIONS_HEIGHT and self.questions_wanted())
            return False
        if watched in (self.field, self.conversation) and kind == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape and self.opened:
                self.close_panel()
                return True
            text = event.text()
            if text in ("1", "2", "3") and self.questions_box.isVisible() and not self.field.text().strip() \
                    and self.questions[int(text) - 1].text():
                self.ask(self.questions[int(text) - 1].text())
                return True
            return False
        if self.docked or watched not in (self.face, self.small, self.head):
            return False
        if kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self._stop_slide()
            self.drag = (event.globalPosition().toPoint(), self.pos())
            self.moved = False
            return True
        if kind == QEvent.Type.MouseMove and self.drag is not None:
            delta = event.globalPosition().toPoint() - self.drag[0]
            if self.moved or delta.manhattanLength() >= QApplication.startDragDistance():
                self.moved = True
                top, w, h = self.free()
                start = self.drag[1] + delta
                x, y = assistant.clamp((start.x(), start.y() - top), (w, h), self.size_now())
                self.move(QPoint(x, y + top))
                if self.opened:
                    self.place_bubble()
            return True
        if kind == QEvent.Type.MouseButtonRelease and self.drag is not None:
            self.drag = None
            if self.moved:
                self.dropped()
            elif watched is self.face:
                self.toggle()
            return True
        return False

    def dropped(self) -> None:
        """Dragged: this is his place from now on, in every phase (R155)."""
        top, w, h = self.free()
        self.places[self.tab] = assistant.anchor_of((self.x(), self.y() - top), self.size_now(), (w, h))
        if self.opened:
            self.place_bubble()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._update_timer()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._update_timer()

    # open and closed

    def toggle(self) -> None:
        """Ctrl+L, or a click on him: open with the cursor in the field, or close."""
        if self.opened:
            self.close_panel()
        else:
            self.open_panel()

    # docked in the panels

    def set_dock(self, dock) -> None:
        """The window's QDockWidget the conversation goes into when docked; its own close button closes it."""
        self.dock = dock
        dock.toggleViewAction().toggled.connect(self._dock_shown)

    def set_docked(self, on: bool) -> None:
        """The conversation into the panel (on) or floating again: the same widgets moved, so the conversation and
        the text being typed stay as they are, and so does open or closed."""
        if on == self.docked or self.dock is None:
            return
        typing = self.field.hasFocus()
        self.docked = on
        constraint = QLayout.SizeConstraint.SetDefaultConstraint if on else QLayout.SizeConstraint.SetMinimumSize
        self.questions_box.layout().setSizeConstraint(constraint)
        self.questions_box.setMinimumHeight(0 if on else self.questions_box.sizeHint().height())
        self.dock_button.setChecked(on)
        self.dock_button.setToolTip(_("Float over the views again") if on else
                                     _("Dock in the panels, as Project and Properties"))
        self.head.setCursor(Qt.CursorShape.ArrowCursor if on else Qt.CursorShape.SizeAllCursor)
        self.small.setVisible(on)                           # floating, the character is right beside the bubble
        if on:
            self._stop_bubble_animation()
            self.bubble.hide()
            self.bubble.box.removeWidget(self.panel)
            self.dock.setWidget(self.panel)
            self.panel.show()
            self.hide()                                     # the floating character goes
            self.dock.setVisible(self.opened)
        else:
            self.panel.setParent(self.bubble)               # out of the panel, back into the bubble
            self.bubble.box.addWidget(self.panel)
            self.dock.hide()
            self.panel.show()
            self.show()
            self.reposition()
            if self.opened:
                self._open_bubble(animate=False)
            else:
                self.bubble.hide()
        if typing and self.opened:
            self.field.setFocus(Qt.FocusReason.OtherFocusReason)
        self._update_timer()

    def _dock_shown(self, shown: bool) -> None:
        """The panel shown or closed by the window (its button, a layout restored): open or closed as it."""
        if self.docked and shown != self.opened:
            self.opened = shown
            self.mood.set_opened(shown, self.clock())
            self.openedChanged.emit(shown)
            self._update_timer()

    def open_panel(self) -> None:
        if self.docked:
            self.dock.show()
            self.dock.raise_()
            self._dock_shown(True)
            self.field.setFocus(Qt.FocusReason.ShortcutFocusReason)
            return
        if not self.opened:
            self.opened = True
            self.mood.set_opened(True, self.clock())
            self.show()
            self._open_bubble(animate=True)
            self.openedChanged.emit(True)
        self.raise_()
        self.field.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def close_panel(self) -> None:
        if self.docked:
            had_focus = self.panel.isAncestorOf(QApplication.focusWidget())
            self.dock.hide()
            self._dock_shown(False)
            if had_focus:
                self.area.setFocus(Qt.FocusReason.OtherFocusReason)
            return
        if self.opened:
            had_focus = self.bubble.isAncestorOf(QApplication.focusWidget())
            self.opened = False
            self.mood.set_opened(False, self.clock())
            self._close_bubble(animate=True)
            self.openedChanged.emit(False)
            if had_focus:
                self.area.setFocus(Qt.FocusReason.OtherFocusReason)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and self.opened:
            self.close_panel()
            return
        super().keyPressEvent(event)

    # the conversation

    def questions_wanted(self) -> bool:
        """The questions ready are shown between turns and not under a proposal confirmation."""
        pending = any(widget.property("confirmation") for widget in self.cards.children())
        return self.mood.state == assistant.IDLE and not pending

    def ask(self, text: str) -> None:
        text = text.strip()
        if not text or self.mood.state != assistant.IDLE:
            return
        self.field.clear()
        self.told = self.heard = self._speech()            # what he was still saying, said: the question after it
        self.messages.append(("you", text))
        self._show_messages()
        self.set_state(assistant.THINKING)
        self.questions_box.hide()                           # gone for this turn
        self.dots.show()
        self.stop_action.setVisible(True)
        if self.connected:
            self.asked.emit(text)                           # the conversation behind him (ui/assistant_chat.py)
        else:
            self.pending.start()

    def _not_connected(self) -> None:
        self.answer(_("Assistant not connected yet"))

    def stream(self, piece: str) -> None:
        """A piece of the answer as the model writes it: he answers, the dots give way to the words."""
        if not self.live:
            self.set_state(assistant.ANSWERING)
            self.dots.hide()
        self.live += piece
        if self.moving():
            if not self.speak_timer.isActive():
                self.speak_timer.start()                    # he says it at his pace, frame by frame
        elif not self.render_timer.isActive():
            self.render_timer.start()

    def settle(self) -> None:
        """The words of a round kept, the tools at work: he thinks again."""
        if self.live.strip():
            self.messages.append(("assistant", self.live))
        self.live = ""
        self.set_state(assistant.THINKING)
        self.dots.show()
        self._show_messages()

    def note(self, text: str, who: str = "note") -> None:
        """A line of what happened ("tool": what Meridio read or did; "note": what the window says)."""
        if self.live.strip() and who == "note":
            self.messages.append(("assistant", self.live))
            self.live = ""
        self.messages.append((who, text))
        self._show_messages()

    def finish(self) -> None:
        """The turn ended: the answer kept, the questions ready back."""
        self.pending.stop()
        if self.live.strip():
            self.messages.append(("assistant", self.live))
        self.live = ""
        self._show_messages()
        self.set_state(assistant.IDLE)
        self.dots.hide()
        self.stop_action.setVisible(False)
        self.fill_questions()                               # they follow what was just said (R108)
        self.questions_box.setVisible(self.panel.height() >= QUESTIONS_HEIGHT and self.questions_wanted())

    def greet(self, text: str) -> None:
        """What he says of his own, not as an answer (his presentation, R106): in the conversation as his words,
        between two turns, the questions ready left as they are."""
        self.messages.append(("assistant", text))
        self._show_messages()

    def answer(self, text: str, who: str = "assistant") -> None:
        """The answer arrived (or the turn ended): shown, and the questions ready come back."""
        if self.live.strip():
            self.messages.append(("assistant", self.live))
            self.live = ""
        self.messages.append((who, text))
        self.finish()

    def waiting_for_card(self) -> None:
        """A card asks the designer first (the consent): no dots, «Stop» still drops the question."""
        self.dots.hide()

    def stop(self) -> None:
        """«Stop» in the field: the request is dropped."""
        if self.mood.state == assistant.IDLE:
            return
        if self.connected:
            self.stopped.emit()
        self.answer(_("Stopped."), who="note")

    def clear(self) -> None:
        """A new conversation."""
        self.messages, self.live, self.told, self.heard = [], "", 0, 0
        self.finish()

    # what the conversation shows besides the words

    def _fit_cards(self) -> None:
        self.cards.setMinimumHeight(self.cards_box.sizeHint().height())
        self.cards.updateGeometry()

    def add_card(self, card: QWidget) -> None:
        self.cards_box.addWidget(card)
        self._fit_cards()
        self.questions_box.setVisible(self.panel.height() >= QUESTIONS_HEIGHT and self.questions_wanted())
        self.cards.show()

    def remove_card(self, card: QWidget) -> None:
        self.cards_box.removeWidget(card)
        card.hide()
        card.setProperty("confirmation", False)
        card.deleteLater()
        self.cards.setVisible(self.cards_box.count() > 0)
        self._fit_cards()
        self.questions_box.setVisible(self.panel.height() >= QUESTIONS_HEIGHT and self.questions_wanted())

    def set_where(self, where: str, label: str, tip: str) -> None:
        """Where the next question goes ("local" or "cloud"): the chip at the head, the mark on the character."""
        self.where = where
        self.where_button.setText(label)
        self.where_button.setIcon(icons.icon("house" if where == "local" else "cloud"))
        self.where_button.setToolTip(tip)
        self.where_button.show()
        self.face.update()

    def set_cost(self, text: str) -> None:
        self.cost.setText(text)
        self.cost.setVisible(bool(text))

    def set_voice(self, available: bool, why: str = "") -> None:
        """The speaker at the head: enabled when a voice of the program's language is there, else why not."""
        self.voice_button.show()
        self.voice_button.setEnabled(available)
        self.voice_tip = why
        self._voice_icon(self.voice_button.isChecked())

    def _voice_icon(self, on: bool) -> None:
        self.voice_button.setIcon(icons.icon("volume-2" if on else "volume-x"))
        if not self.voice_button.isEnabled():
            self.voice_button.setToolTip(getattr(self, "voice_tip", ""))
        else:
            self.voice_button.setToolTip(_("{name} reads his answers aloud: on").format(name=assistant.NAME) if on
                                         else _("{name} reads his answers aloud: off").format(name=assistant.NAME))

    def _speech(self) -> int:
        """The characters of all he said, the answer being written included, as shown (the names put back)."""
        said = [t for who, t in self.messages if who == "assistant"] + ([self.live] if self.live else [])
        return sum(len(self.restore(t)) for t in said)

    def _speak(self) -> None:
        """A frame of his speech: a few characters more, as many as it takes to say what is left by SPEAK_MAX_S
        after the last words came."""
        total = self._speech()
        now = time.monotonic()
        if total > self.heard:
            self.heard, self.speak_until = total, now + SPEAK_MAX_S
        if not self.moving() or self.told >= total:
            self.told = total
            self.speak_timer.stop()
        else:
            frames = max(1.0, (self.speak_until - now) * 1000 / FRAME_MS)
            step = max(math.ceil(SPEAK_CPS * FRAME_MS / 1000), math.ceil((total - self.told) / frames))
            self.told = min(total, self.told + step)
            if self.told >= total:
                self.speak_timer.stop()                     # all said
        self._show_messages()

    def _show_messages(self) -> None:
        self.render_timer.stop()
        muted = self.colours["muted"]
        rows = []
        shown = list(self.messages) + ([("assistant", self.live)] if self.live else [])
        # his words as far as he has said them (R156); what comes after them waits for them
        if not self.moving():
            self.told = self._speech()
        elif self.told < self._speech() and not self.speak_timer.isActive():
            self.speak_timer.start()
        budget, cut = self.told, False
        for who, text in shown:
            if cut:
                break
            if who == "assistant":
                said = self.restore(text)
                if budget <= 0 and said:
                    break
                if budget < len(said):
                    said, cut = said[:budget], True
                budget -= len(said)
                rows.append(f'<p style="margin-bottom:0"><span style="color:{muted}">{assistant.NAME}</span></p>'
                            f'{words.html(said)}')
                continue
            if who == "info":                               # what Meridio says of himself (the consent)
                rows.append(f'<div style="color:{muted}">{words.html(text)}</div>')
                continue
            if who in ("note", "tool"):
                safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                size = f"font-size:{Type.SMALL}px;" if who == "tool" else ""
                mark = "› " if who == "tool" else ""
                rows.append(f'<p><span style="color:{muted};{size}"><i>{mark}{safe}</i></span></p>')
                continue
            body = "<p>" + text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "</p>"
            name = _("You")
            rows.append(f'<p style="margin-bottom:0"><span style="color:{muted}">{name}</span></p>{body}')
        if not rows and self.empty:                         # an empty conversation: his greeting, attenuated
            safe = self.empty.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            rows.append(f'<p><span style="color:{muted}">{safe}</span></p>')
        self.conversation.setHtml("".join(rows))
        bar = self.conversation.verticalScrollBar()
        bar.setValue(bar.maximum())
        self.at_bottom = True

    def _scrolled(self, value: int) -> None:
        self.at_bottom = value >= self.conversation.verticalScrollBar().maximum() - 2

    def _range_changed(self, _low: int, high: int) -> None:
        if self.at_bottom:
            self.conversation.verticalScrollBar().setValue(high)
