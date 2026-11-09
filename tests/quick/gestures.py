"""Synthetic Qt events only: these helpers never move the system pointer."""
import time

from PySide6.QtCore import QEvent, QEventLoop, QObject, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent


def pump(milliseconds=16):
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def wait_for(predicate, seconds=30):
    end = time.perf_counter()+seconds
    while not predicate() and time.perf_counter()<end:
        pump(10)
    if not predicate():
        raise AssertionError('Timed out waiting for the Quick state')


def item(window, name):
    found = window.findChild(QObject, name)
    if found is None:
        pending = [window.contentItem()]
        while pending:
            obj = pending.pop()
            if obj.objectName() == name:
                return obj
            pending.extend(obj.childItems())
    if found is None:
        raise AssertionError('Missing Quick item: ' + name)
    return found


def point(obj, x=None, y=None):
    return obj.mapToScene(QPointF(obj.width()/2 if x is None else x, obj.height()/2 if y is None else y))


def mouse(app, window, kind, pos, button, buttons):
    app.sendEvent(window, QMouseEvent(kind, pos, pos, QPointF(window.mapToGlobal(pos.toPoint())),
                                     button, buttons, Qt.KeyboardModifier.NoModifier))


def click(app, window, pos):
    mouse(app, window, QEvent.Type.MouseButtonPress, pos, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
    mouse(app, window, QEvent.Type.MouseButtonRelease, pos, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)


def drag(app, window, start, end, steps=40, button=Qt.MouseButton.LeftButton, pause=16):
    mouse(app, window, QEvent.Type.MouseButtonPress, start, button, button)
    for i in range(1, steps+1):
        mouse(app, window, QEvent.Type.MouseMove, start+(end-start)*(i/steps), Qt.MouseButton.NoButton, button)
        pump(pause)
    mouse(app, window, QEvent.Type.MouseButtonRelease, end, button, Qt.MouseButton.NoButton)


def wheel(app, window, pos, notches=10, dy=-120):
    for _ in range(notches):
        app.sendEvent(window, QWheelEvent(pos, QPointF(window.mapToGlobal(pos.toPoint())), QPoint(), QPoint(0, dy),
                                         Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                                         Qt.ScrollPhase.NoScrollPhase, False))
        pump()


def key(app, window, keycode, text='', modifiers=Qt.KeyboardModifier.NoModifier):
    app.sendEvent(window, QKeyEvent(QEvent.Type.KeyPress, keycode, modifiers, text))
    app.sendEvent(window, QKeyEvent(QEvent.Type.KeyRelease, keycode, modifiers, text))
