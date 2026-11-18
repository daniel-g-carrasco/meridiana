"""The wheel scrolls the page; it changes a number or a choice only in the field that has the keyboard.

Qt gives the wheel to the field under the pointer, focused or not, and the field keeps it: scrolling a form
stopped as soon as the pointer crossed a field, and the field changed its value, an edit like any other with
its computation (measured on 22/10/2026, «Soiling» 2.5 -> 2.4). Firefox 130, WinUI's NumberBox and Qt Quick
Controls do the same as here: a click gives the field the keyboard, then the wheel works on it. A chart does
not use the wheel and lets it go to the page too."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QAbstractSpinBox, QApplication, QComboBox


def _field(obj) -> QAbstractSpinBox | QComboBox | None:
    """The spin box or the list an event is for: the widget itself, or the line edit inside it."""
    if isinstance(obj, (QAbstractSpinBox, QComboBox)):
        return obj
    parent = obj.parent() if isinstance(obj, QObject) else None
    return parent if isinstance(parent, (QAbstractSpinBox, QComboBox)) else None


class WheelGuard(QObject):
    """An application-wide event filter. A field polished for the first time takes the keyboard on a click,
    not on the wheel (with WheelFocus, Qt would give it the focus before the wheel arrives). A wheel over a
    field without the keyboard, or over a chart, is ignored by it and goes on to the scroll area under it."""

    def eventFilter(self, obj, event) -> bool:
        kind = event.type()
        if kind == QEvent.Type.Polish:
            if isinstance(obj, (QAbstractSpinBox, QComboBox)) and obj.focusPolicy() == Qt.FocusPolicy.WheelFocus:
                obj.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            return False
        if kind != QEvent.Type.Wheel:
            return False
        field = _field(obj)
        if field is not None:
            if field.hasFocus():
                return False
            event.ignore()
            return True
        if any(c.__name__ == "FigureCanvasQTAgg" for c in type(obj).__mro__):     # charts.Canvas too
            event.ignore()
            return True
        return False


def guard(app: QApplication | None = None) -> WheelGuard:
    """Install the guard once on the application; the same one is given back afterwards."""
    app = app or QApplication.instance()
    existing = getattr(app, "_meridiana_wheel_guard", None)
    if existing is not None:
        return existing
    g = WheelGuard(app)
    from .app_events import events         # the application's one filter (R120)
    events().on((QEvent.Type.Polish, QEvent.Type.Wheel), g, g.eventFilter)
    app._meridiana_wheel_guard = g
    return g
