"""R570: stand-ins for what lies behind a floating surface, and the gestures given over it (synthetic events only).

A probe is one kind of thing behind (the handlers of the plan and of the 3D view, the mouse area of a chart, a list
that scrolls, a button with its tip, a field) and counts what reaches it; `PointerProbes` builds a window with a probe
behind everything else, gives the gestures to the window (QTest's mouse and touch go through the window system's queue
of the window, never the system pointer) and says what went through. Used by quick/meridio/test_pointer_shield.py and
quick/controlli/test_superfici_r570.py.
"""
from PySide6.QtCore import QCoreApplication, QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QInputDevice, QNativeGestureEvent, QWheelEvent
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from meridiana.gui.backend.assistant import build_page
from quick.gestures import pump, wait_for

DOWN = QPointF(0, 3)
WHEEL = QPoint(0, -120)


def settle():
    # a gesture's events are delivered before QTest returns; one turn of the loop lets the bindings follow them
    pump(5)

# One stand-in for each kind of thing behind: it counts what reaches it. `hovered` is what lights a hover or a tip.
PROBES = {
    # the plan and the 3D view: pointer handlers on an item
    'handlers': '''
        Item {
            property int taps: 0; property int wheels: 0; property int pinches: 0; property int drags: 0
            readonly property bool hovered: hover.hovered
            HoverHandler { id: hover; cursorShape: Qt.CrossCursor }
            TapHandler { acceptedButtons: Qt.AllButtons; onTapped: parent.taps++ }
            WheelHandler { target: null; acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                onWheel: function(event) { parent.wheels++ } }
            PinchHandler { target: null; onActiveChanged: if (active) parent.pinches++ }
            DragHandler { target: null; onActiveChanged: if (active) parent.drags++ }
        }''',
    # a chart, the plan: one mouse area with its hover, its clicks and its wheel
    'mouse': '''
        MouseArea {
            property int taps: 0; property int wheels: 0; property int pinches: 0; property int drags: 0
            readonly property bool hovered: containsMouse
            hoverEnabled: true; acceptedButtons: Qt.AllButtons; cursorShape: Qt.CrossCursor
            onPressed: taps++
            onDoubleClicked: taps++
            onWheel: wheels++
            onPositionChanged: if (pressed) drags++
        }''',
    # a table or a page that scrolls
    'list': '''
        ListView {
            property int taps: 0; property int pinches: 0; property int drags: 0
            readonly property int wheels: contentY !== 0 ? 1 : 0
            readonly property bool hovered: false
            model: 400; clip: true
            delegate: Text { required property int index; text: "row " + index; height: 24 }
            onMovementStarted: drags++
        }''',
    # a button with its tip
    'button': '''
        M.Button {
            property int taps: 0; property int wheels: 0; property int pinches: 0; property int drags: 0
            text: "behind"; tip: "behind"
            onPressedChanged: if (pressed) taps++
        }''',
    # a field: its hover and its clicks (its cursor is the text's, as the conversation's)
    'field': '''
        M.TextField {
            property int taps: 0; property int wheels: 0; property int pinches: 0; property int drags: 0
            hoverEnabled: true
            onPressed: taps++
        }''',
}
COUNTERS = ('taps', 'wheels', 'pinches', 'drags')
# the drag last: on Meridio's character it carries him away from the point
GESTURES = ('move', 'wheel', 'sideways', 'ctrl-wheel', 'pad-scroll', 'left', 'right', 'double', 'tap', 'pinch', 'drag')
IMPORTS = 'import QtQuick\nimport QtQuick.Controls\nimport Meridiana.Theme\nimport Meridiana.Controls as M\n'


class PointerProbes:
    """A mixin for unittest.TestCase."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['r570-tests'])
        cls.touch = QTest.createTouchDevice(QInputDevice.DeviceType.TouchScreen)
        cls.pad = QTest.createTouchDevice(QInputDevice.DeviceType.TouchPad)

    def create(self, engine, text, parent):
        component = QQmlComponent(engine)
        component.setData((IMPORTS + text).encode(), QUrl('probe.qml'))
        made = component.create()
        self.assertIsNotNone(made, component.errorString())
        # the wrappers of the component and of the parent outlive what was made (or Python deletes it)
        self._kept.append((component, made, parent))
        made.setParent(parent)
        made.setParentItem(parent)
        return made

    def scene(self, kind, surface=None, opened=True, chat=None):
        """Meridio's preview window (its bubble open unless `opened` is false) with the probe `kind` behind
        everything; `surface`, QML text, is made over the probe and Meridio (its root fills the window)."""
        engine, window, _ = build_page('meridio', options={'reducedMotion': True}, chat=chat)
        # what the main window gives the help's bubble and the cards (application.py), as little as they read
        engine.rootContext().setContextProperty('helpBook', {'labels': {'manual': 'Manuale', 'ask': 'Chiedi'},
                                                             'canAsk': False})
        engine.rootContext().setContextProperty('L', {'closeCard': 'Chiudi'})
        errors = []
        engine.warnings.connect(lambda items: errors.extend(i.toString() for i in items))
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        layer = window.findChild(QObject, 'assistantLayer')
        wait_for(lambda: not layer.property('relocating'), 5)
        layer.setProperty('opened', opened)
        self._kept = []
        content = layer.parentItem()
        probe = self.create(engine, PROBES[kind], content)
        probe.setSize(content.size())
        # behind the layer, as every view is behind Meridio
        probe.stackBefore(layer)
        self.assertLess(content.childItems().index(probe), content.childItems().index(layer))
        made = None
        if surface is not None:
            made = self.create(engine, surface, content)
            made.setSize(content.size())
        # the surface's first frame (a popup opens in it)
        pump(50)

        def cleanup():
            # what QML said while the test ran (taking it all down says more, about the objects going)
            said = list(errors)
            for _, item, _ in reversed(self._kept):
                delete(item)
            window.close()
            delete(engine)
            self.assertEqual(said, [])
        self.addCleanup(cleanup)
        return window, layer, probe, made

    # the gestures
    def move(self, window, pos):
        QTest.mouseMove(window, pos.toPoint())
        settle()

    def click(self, window, pos, button=Qt.MouseButton.LeftButton, double=False):
        if double:
            QTest.mouseDClick(window, button, Qt.KeyboardModifier.NoModifier, pos.toPoint())
        else:
            QTest.mouseClick(window, button, Qt.KeyboardModifier.NoModifier, pos.toPoint())
        settle()

    def drag(self, window, pos, way=DOWN):
        button = Qt.MouseButton.LeftButton
        QTest.mousePress(window, button, Qt.KeyboardModifier.NoModifier, pos.toPoint())
        for step in range(1, 9):
            QTest.mouseMove(window, (pos + way * step).toPoint())
            settle()
        QTest.mouseRelease(window, button, Qt.KeyboardModifier.NoModifier, (pos + way * 8).toPoint())
        settle()

    def wheel(self, window, pos, delta=WHEEL, modifiers=Qt.KeyboardModifier.NoModifier):
        # the mouse's wheel; sideways, two fingers on a touchpad; with Ctrl, the touchpad's pinch as Windows gives it
        for _ in range(3):
            QCoreApplication.sendEvent(window, QWheelEvent(
                pos, QPointF(window.mapToGlobal(pos.toPoint())), QPoint(), delta, Qt.MouseButton.NoButton,
                modifiers, Qt.ScrollPhase.NoScrollPhase, False))
            settle()

    def pad_scroll(self, window, pos, dy=-40):
        # two fingers on a touchpad: pixels, with the phases of a gesture (begin, moves, end), then its momentum
        globalpos = QPointF(window.mapToGlobal(pos.toPoint()))
        phases = ([Qt.ScrollPhase.ScrollBegin] + [Qt.ScrollPhase.ScrollUpdate] * 6 + [Qt.ScrollPhase.ScrollEnd]
                  + [Qt.ScrollPhase.ScrollMomentum] * 3)
        for phase in phases:
            moving = phase in (Qt.ScrollPhase.ScrollUpdate, Qt.ScrollPhase.ScrollMomentum)
            QCoreApplication.sendEvent(window, QWheelEvent(
                pos, globalpos, QPoint(0, dy if moving else 0), QPoint(0, dy * 3 if moving else 0),
                Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, phase, False, Qt.MouseEventSource.MouseEventNotSynthesized,
                self.pad))
            settle()

    def tap(self, window, pos):
        QTest.touchEvent(window, self.touch).press(0, pos.toPoint(), window)
        QTest.touchEvent(window, self.touch).release(0, pos.toPoint(), window)
        settle()

    def pinch(self, window, pos):
        # two fingers one above the other, both on the surface, moving apart
        a, b = pos.toPoint() - QPoint(0, 3), pos.toPoint() + QPoint(0, 3)
        QTest.touchEvent(window, self.touch).press(0, a, window).press(1, b, window)
        for step in range(1, 9):
            QTest.touchEvent(window, self.touch).move(0, a - QPoint(0, step * 2), window).move(
                1, b + QPoint(0, step * 2), window)
            settle()
        QTest.touchEvent(window, self.touch).release(0, a - QPoint(0, 16), window).release(1, b + QPoint(0, 16), window)
        settle()

    def pad_pinch(self, window, pos):
        # the touchpad's own pinch (Wayland, macOS), as QGuiApplication sends it to the window
        globalpos = QPointF(window.mapToGlobal(pos.toPoint()))
        for kind, value in ((Qt.NativeGestureType.BeginNativeGesture, 0), (Qt.NativeGestureType.ZoomNativeGesture, 0.1),
                            (Qt.NativeGestureType.ZoomNativeGesture, 0.1), (Qt.NativeGestureType.EndNativeGesture, 0)):
            QCoreApplication.sendEvent(window, QNativeGestureEvent(kind, self.pad, 2, pos, pos, globalpos, value,
                                                                   QPointF(), 1))
            settle()

    # what went through
    def counts(self, probe):
        return {name: probe.property(name) for name in COUNTERS}

    def cursor_is_behind(self, window):
        # the probes' own (a field's is the text's, as the conversation's: its hover says it went through)
        return window.cursor().shape() == Qt.CursorShape.CrossCursor

    def check_blocked(self, window, probe, pos, where, way=DOWN, skip_drag=False):
        # from what is behind (hovered there) onto the surface
        self.move(window, QPointF(20, 20))
        before = self.counts(probe)
        for gesture in GESTURES[:-1] if skip_drag else GESTURES:
            with self.subTest(where=where, gesture=gesture):
                # from beside it: Qt drops a move to where it already has the mouse, and would keep what that hovered
                self.move(window, pos - QPointF(1, 0))
                self.move(window, pos)
                if gesture == 'wheel':
                    self.wheel(window, pos)
                elif gesture == 'sideways':
                    self.wheel(window, pos, QPoint(-120, 0))
                elif gesture == 'ctrl-wheel':
                    self.wheel(window, pos, modifiers=Qt.KeyboardModifier.ControlModifier)
                elif gesture == 'pad-scroll':
                    self.pad_scroll(window, pos)
                elif gesture == 'left':
                    self.click(window, pos)
                elif gesture == 'right':
                    self.click(window, pos, Qt.MouseButton.RightButton)
                elif gesture == 'double':
                    self.click(window, pos, double=True)
                elif gesture == 'drag':
                    # the pointer stays where the drag ended, on the surface (Meridio goes with it)
                    self.drag(window, pos, way)
                elif gesture == 'tap':
                    self.tap(window, pos)
                elif gesture == 'pinch':
                    self.pinch(window, pos)
                if gesture in ('tap', 'pinch'):
                    # a touch moves the mouse that Qt makes of it, not the pointer: the pointer comes back over it
                    self.move(window, pos - QPointF(1, 0))
                    self.move(window, pos)
                after = self.counts(probe)
                through = [name for name in COUNTERS if after[name] != before[name]]
                through += ['hover'] if probe.property('hovered') else []
                through += ['cursor'] if self.cursor_is_behind(window) else []
                before = after
                self.assertEqual(through, [], 'what went through the surface to what is behind')

    def check_passes(self, window, probe, pos, where):
        with self.subTest(where=where, gesture='move'):
            self.move(window, QPointF(20, 20))
            self.move(window, pos)
            self.assertTrue(probe.property('hovered'))
            self.assertEqual(window.cursor().shape(), Qt.CursorShape.CrossCursor)
        with self.subTest(where=where, gesture='wheel'):
            wheels = probe.property('wheels')
            self.wheel(window, pos)
            self.assertGreater(probe.property('wheels'), wheels)
        with self.subTest(where=where, gesture='click'):
            taps = probe.property('taps')
            self.click(window, pos, Qt.MouseButton.RightButton)
            self.assertGreater(probe.property('taps'), taps)
