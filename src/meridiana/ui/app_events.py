"""One event filter on the application for what needs every widget's events (R120, docs/prestazioni/README.md):
the menus that Alt shows, the little windows that fade in, the wheel kept off the fields. An event filter on the
application sees every event of every widget, and with three of them in Python each event crossed into Python
three times: some 20 000 events at every change of phase or step of a panel's edge dragged. Here one filter hands
each event only to the handlers of its kind.

`events().on(kinds, owner, handler)`: `handler(obj, event)` for the events of those kinds while `owner` lives;
True from it stops the event, as an event filter's."""

from __future__ import annotations

from collections.abc import Callable, Iterable

import shiboken6
from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QApplication


class AppEvents(QObject):
    def __init__(self, app: QApplication):
        super().__init__(app)
        self.handlers: dict = {}
        app.installEventFilter(self)

    def on(self, kinds: Iterable, owner: QObject, handler: Callable) -> None:
        for kind in kinds:
            self.handlers.setdefault(kind, []).append((owner, handler))

    def eventFilter(self, obj, event) -> bool:
        listed = self.handlers.get(event.type())
        if not listed:
            return False
        for owner, handler in list(listed):
            if not shiboken6.isValid(owner):            # its window gone: the handler with it
                listed.remove((owner, handler))
                continue
            if handler(obj, event):
                return True
        return False


def events() -> AppEvents:
    """The application's one filter, made the first time."""
    app = QApplication.instance()
    found = app.findChild(AppEvents, options=Qt.FindChildOption.FindDirectChildrenOnly)
    return found if found is not None else AppEvents(app)
