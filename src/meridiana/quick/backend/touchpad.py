"""The pace of two fingers on a touchpad under Wayland (R545).

Daniel 08/11/2026: «lo scrolling in verticale è troppo troppo lento». Measured on the Framework under Niri with a
virtual touchpad through libinput (docs/quick/stato/r24-finestra.md): two fingers moved 33 mm give 49 wheel events of one
pixel each, and Qt Quick moves a list, a page or the plan by exactly those 49 pixels. Nothing in Meridiana slows them
down: Qt Quick takes `pixelDelta` one to one, while GTK 4 multiplies the same compositor value by 2.5
(MAGIC_SCROLL_FACTOR in gtkscrolledwindow.c) and the Widgets turned the angle into lines of three steps. Lucciola's
`scroll-factor` (0.15 for the touchpad) is chosen so that GTK 4's 2.5 gives the right distance, and it tunes the other
toolkits to the same pace with window rules: a Qt Quick program, one to one, goes 2.5 times slower than every other
window. The same holds on GNOME, which has no factor at all and whose programs are GTK 4.

So on Wayland the pixels of a touchpad gesture (an event in a scroll phase, with pixels) are multiplied by GTK 4's
2.5, the remainder carried to the next event, before Qt Quick delivers them: every list, page, table, the plan and the
3D view get the same pace as the other programs, with no change in each of them. A mouse wheel (no phase, no pixels),
the pinch (a native gesture, not a wheel) and Windows (angles only, no phases) are not touched here: Windows has
WindowsTouchpad, below (R556)."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPoint, Qt
from PySide6.QtGui import QGuiApplication, QWheelEvent

GTK_SCROLL_FACTOR = 2.5         # gtk/gtkscrolledwindow.c, MAGIC_SCROLL_FACTOR: what the other windows do with a pixel


class TouchpadPace(QObject):
    """Multiplies the pixels of touchpad scrolls by `factor` in the windows it watches; `active` False lets every
    event through untouched (other platforms than Wayland)."""

    def __init__(self, parent=None, *, factor: float = GTK_SCROLL_FACTOR, active: bool | None = None):
        super().__init__(parent)
        self.factor = factor
        self.active = QGuiApplication.platformName() == "wayland" if active is None else active
        self.carry = [0.0, 0.0]
        self.sending = False
        self.watched: set[int] = set()

    def watch(self, window) -> None:
        if window is None or id(window) in self.watched:
            return
        self.watched.add(id(window))
        window.installEventFilter(self)
        window.destroyed.connect(lambda *_: self.watched.discard(id(window)))

    def follow(self, app) -> None:
        """Every top-level window of the program, the dialogs of their own included, as they get the focus."""
        app.focusWindowChanged.connect(self.watch)
        for window in app.topLevelWindows():
            self.watch(window)

    def scaled(self, event: QWheelEvent) -> QWheelEvent | None:
        """The event with its pixels multiplied, or None when it is to go as it is."""
        phase = event.phase()
        if phase in (Qt.ScrollPhase.ScrollBegin, Qt.ScrollPhase.ScrollEnd):
            self.carry = [0.0, 0.0]
        if not self.active or phase == Qt.ScrollPhase.NoScrollPhase or event.pixelDelta().isNull():
            return None
        moved = []
        for axis, value in enumerate((event.pixelDelta().x(), event.pixelDelta().y())):
            exact = value * self.factor + self.carry[axis]
            whole = round(exact)
            self.carry[axis] = exact - whole
            moved.append(whole)
        angle = event.angleDelta()
        return QWheelEvent(event.position(), event.globalPosition(), QPoint(*moved),
                           QPoint(round(angle.x() * self.factor), round(angle.y() * self.factor)),
                           event.buttons(), event.modifiers(), phase, event.inverted(), event.source(),
                           event.pointingDevice())

    def eventFilter(self, obj, event) -> bool:
        if self.sending or event.type() != QEvent.Type.Wheel:
            return False
        scaled = self.scaled(event)
        if scaled is None:
            return False
        scaled.setTimestamp(event.timestamp())
        self.sending = True
        try:
            QCoreApplication.sendEvent(obj, scaled)
        finally:
            self.sending = False
        event.setAccepted(scaled.isAccepted())
        return True


# R556 (Daniel 08/11/2026, Windows: «la navigazione con il touchpad non è il massimo [...] troppo sensibile, e lo
# scrolling verticale con due dita fa zoom al posto di spostare»). A precision touchpad on Windows gives Qt plain
# WM_MOUSEWHEEL / WM_MOUSEHWHEEL messages: angles only, no pixels, no phases, and the device of the event is the
# mouse; Qt 6.12 does not tell them apart (its Windows plugin reads neither GetCurrentInputMessageSource nor
# DirectManipulation). So the plan and the 3D took two fingers for a mouse wheel: zoom, at each of the many small steps.
# What tells them apart, in order:
#   1. Windows itself, when it says it (GetCurrentInputMessageSource: the device of the input message being handled,
#      Windows 8 and later; reliable only while that message is the current one, so a hardware mouse is believed and
#      anything else goes to the next rules);
#   2. the size of the step: a mouse wheel turns by notches of 120 (WHEEL_DELTA), a touchpad by any amount (8, 16, 37...);
#   3. the gesture: the events of two fingers come every 8-16 ms, so a step of 120 within WINDOWS_STREAM_MS of a touchpad
#      step belongs to the same gesture.
# A touchpad step then goes on as on Linux: pixels (WINDOWS_PIXELS_PER_UNIT, a notch as the 100 px of the browsers on
# Windows) in scroll phases (begin, update, end after WINDOWS_STREAM_MS of quiet), so that every area, the plan and the
# 3D take it for two fingers (Plan/Navigation.js, View3D/Navigation.js: phases mean pan). With Ctrl (what Windows sends
# for the pinch, and Ctrl + wheel) it goes as it is: zoom. A mouse that turns by fractions of a notch (a «high
# resolution» wheel) goes as a touchpad unless Windows says that it is a mouse (rule 1).

WINDOWS_PIXELS_PER_UNIT = 100 / 120     # 120 (a notch) = 100 px, as Edge and Chrome scroll a page for a notch
WINDOWS_STREAM_MS = 250                 # two fingers give an event every 8-16 ms: a longer quiet ends the gesture
WHEEL_DELTA = 120


def input_source() -> str | None:
    """'touchpad', 'mouse' or None: what Windows says sent the input message being handled, when it is hardware."""
    import sys
    if sys.platform != 'win32':
        return None
    try:
        import ctypes

        class Source(ctypes.Structure):
            _fields_ = [('deviceType', ctypes.c_int), ('originId', ctypes.c_int)]
        source = Source()
        if not ctypes.windll.user32.GetCurrentInputMessageSource(ctypes.byref(source)):
            return None
    except (OSError, AttributeError):
        return None
    if source.originId != 1:            # IMO_HARDWARE
        return None
    return {0x10: 'touchpad', 0x02: 'mouse'}.get(source.deviceType)    # IMDT_TOUCHPAD, IMDT_MOUSE


class WheelKind:
    """Tells a touchpad's step from a mouse wheel's notch (rules 1-3 above); `last` is the time of the last touchpad
    step, in the events' milliseconds."""

    def __init__(self):
        self.last = None

    def touchpad(self, angle_x: int, angle_y: int, timestamp: int, source: str | None = None) -> bool:
        if source == 'mouse':
            found = False
        elif source == 'touchpad' or angle_x % WHEEL_DELTA or angle_y % WHEEL_DELTA:
            found = True
        else:
            found = self.last is not None and 0 <= timestamp - self.last <= WINDOWS_STREAM_MS
        if found:
            self.last = timestamp
        return found


class WindowsTouchpad(QObject):
    """Two fingers on a precision touchpad under Windows given to Qt Quick as on Linux: pixels in scroll phases (R556).
    `active` False lets every event through (other platforms)."""

    def __init__(self, parent=None, *, active: bool | None = None, source=input_source):
        super().__init__(parent)
        self.active = QGuiApplication.platformName() == "windows" if active is None else active
        self.kind = WheelKind()
        self.source = source
        self.carry = [0.0, 0.0]
        self.sending = False
        self.watched: set[int] = set()
        self.gesture = None                     # (window, position, global position, buttons, modifiers) of the last step
        from PySide6.QtCore import QTimer
        self.quiet = QTimer(self)
        self.quiet.setSingleShot(True)
        self.quiet.setInterval(WINDOWS_STREAM_MS)
        self.quiet.timeout.connect(self.end)

    watch = TouchpadPace.watch
    follow = TouchpadPace.follow

    def _send(self, obj, event, phase, pixels, angle) -> bool:
        made = QWheelEvent(event.position(), event.globalPosition(), QPoint(*pixels), QPoint(*angle),
                           event.buttons(), event.modifiers(), phase, event.inverted(), event.source(),
                           event.pointingDevice())
        made.setTimestamp(event.timestamp())
        self.sending = True
        try:
            QCoreApplication.sendEvent(obj, made)
        finally:
            self.sending = False
        return made.isAccepted()

    def end(self) -> None:
        """The gesture over: its end said where it was (a WheelHandler leaves its active state)."""
        gesture, self.gesture = self.gesture, None
        self.carry = [0.0, 0.0]
        if gesture is None:
            return
        window, event = gesture
        try:
            self._send(window, event, Qt.ScrollPhase.ScrollEnd, (0, 0), (0, 0))
        except RuntimeError:                    # the window is gone
            pass

    def eventFilter(self, obj, event) -> bool:
        if self.sending or not self.active or event.type() != QEvent.Type.Wheel:
            return False
        if event.phase() != Qt.ScrollPhase.NoScrollPhase or not event.pixelDelta().isNull():
            return False                        # a device that already says what it is
        angle = event.angleDelta()
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.end()
            return False                        # the pinch, or Ctrl + wheel: zoom, as it is
        if not self.kind.touchpad(angle.x(), angle.y(), event.timestamp(), self.source()):
            self.end()
            return False
        if self.gesture is not None and self.gesture[0] is not obj:
            self.end()
        if self.gesture is None:
            self._send(obj, event, Qt.ScrollPhase.ScrollBegin, (0, 0), (0, 0))
        pixels = []
        for axis, value in enumerate((angle.x(), angle.y())):
            exact = value * WINDOWS_PIXELS_PER_UNIT + self.carry[axis]
            whole = round(exact)
            self.carry[axis] = exact - whole
            pixels.append(whole)
        accepted = self._send(obj, event, Qt.ScrollPhase.ScrollUpdate, pixels, (angle.x(), angle.y()))
        # the copy kept for the end: the event itself is Qt's and goes when this returns
        self.gesture = (obj, QWheelEvent(event.position(), event.globalPosition(), QPoint(), QPoint(), event.buttons(),
                                         event.modifiers(), Qt.ScrollPhase.NoScrollPhase, event.inverted(),
                                         event.source(), event.pointingDevice()))
        self.quiet.start()
        event.setAccepted(accepted)
        return True
