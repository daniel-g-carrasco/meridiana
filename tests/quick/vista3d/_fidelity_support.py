"""Real-window harness shared by fidelity tests and the comparison journey."""
import json
import time

import numpy as np
from PySide6.QtCore import QCoreApplication, QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtQml import QQmlExpression, QQmlEngine


def settle(app, seconds=0.15):
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        app.processEvents()
        time.sleep(0.003)


def js(obj, source):
    expression = QQmlExpression(QQmlEngine.contextForObject(obj), obj, source)
    value = expression.evaluate()
    if expression.hasError():
        raise AssertionError(expression.error().toString())
    return value[0] if isinstance(value, tuple) else value


def data(obj, source):
    return json.loads(js(obj, 'JSON.stringify(' + source + ')'))


def click(window, x, y, button=Qt.MouseButton.LeftButton):
    p = QPointF(x, y)
    for kind, buttons in ((QEvent.Type.MouseButtonPress, button),
                          (QEvent.Type.MouseButtonRelease, Qt.MouseButton.NoButton)):
        QCoreApplication.sendEvent(window, QMouseEvent(kind, p, p, p, button, buttons, Qt.KeyboardModifier.NoModifier))


def pixels(image):
    image = image.convertToFormat(image.Format.Format_RGBA8888)
    return np.frombuffer(image.bits(), np.uint8).reshape(image.height(), image.width(), 4).copy()
