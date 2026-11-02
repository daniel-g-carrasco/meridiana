"""A phase's page made the first time the phase is shown.

The three pages of the results (Production, Consumption, Economics) and their forms on the right are about 1,100 of
the window's 2,300 widgets, and each widget costs 0.2 ms at every application of the style sheet, shown or not: a
change of theme paid 0.4 s for pages nobody had visited (02/11/2026). `LazyPage` stands in their place: a plain page
for the phases' stack and a slot for the form in the inspector, and the real page is made when the phase is first
shown (or when something asks the page for a widget it does not yet have).

What the window tells a page meanwhile (`show_project`, `show_results`, the status, the year being computed...) is kept,
the last of each, and told to the page when it is made, in the order it was last said: the page is then as if it had
been there all the time. What the window connects (`edited`, `computeRequested`, the page's own requests) is
connected here, and the real page's signals are passed on to them."""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

# the calls the window makes of a page that only set what it shows: the last of each is what the page will show
DEFERRED = ("show_project", "show_results", "show_strings", "show_meteo", "show_sizing", "show_basis", "set_stale",
            "set_computing", "place_meteo")


class _Said(QObject):
    """`page.status`, the one label the window writes to before the page is there: its last `setText`."""

    def __init__(self, page: LazyPage):
        super().__init__(page)
        self._page = page

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        page = self._page
        if page._real is not None:
            return getattr(page._real.status, name)
        if name == "setText":
            return lambda text: page._keep("status.setText", (text,))
        return getattr(page.real().status, name)


class LazyPage(QWidget):
    edited = Signal(str, str, object)
    computeRequested = Signal()
    built = Signal()

    def __init__(self, factory: Callable[[], QWidget], parent=None):
        super().__init__(parent)
        self._factory = factory
        self._real = None
        self._calls: OrderedDict = OrderedDict()
        self._hooks: list = []
        self._said = _Said(self)
        self.setMinimumWidth(320)                   # the page's own (energy_pages.Page)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        self._box = box
        # the form on the right, where the inspector has it: empty until the page is made
        self.side_slot = QWidget()
        self._slot_box = QVBoxLayout(self.side_slot)
        self._slot_box.setContentsMargins(0, 0, 0, 0)

    # made

    def is_built(self) -> bool:
        return self._real is not None

    def real(self) -> QWidget:
        """The page, made now when it was not."""
        if self._real is None:
            page = self._factory()
            self._real = page
            self._box.addWidget(page)
            self._slot_box.addWidget(page.side)
            for name in ("edited", "computeRequested"):
                getattr(page, name).connect(getattr(self, name))
            for name in self._own_signals():
                getattr(page, name).connect(getattr(self, name))
            for key, (args, kwargs) in list(self._calls.items()):
                self._tell(key, args, kwargs)
            self._calls.clear()
            for hook in self._hooks:
                hook(page)
            # shown at once, after what was told it (the charts note what to draw and draw it as they show): a layout
            # shows what is added to it only a turn of the events later
            if self.isVisible():
                page.show()
            if self.side_slot.isVisible():
                page.side.show()
            self.built.emit()
        return self._real

    def _own_signals(self) -> tuple:
        return ()

    def when_built(self, hook: Callable) -> None:
        """`hook(page)` now when the page is made, otherwise as soon as it is."""
        if self._real is not None:
            hook(self._real)
        else:
            self._hooks.append(hook)

    def showEvent(self, event) -> None:
        self.real()
        super().showEvent(event)

    # what is told meanwhile

    def _keep(self, key: str, args: tuple, kwargs: dict | None = None) -> None:
        self._calls.pop(key, None)                   # the order it was last said in
        self._calls[key] = (args, kwargs or {})

    def _tell(self, key: str, args: tuple, kwargs: dict) -> None:
        target = self._real
        for part in key.split("."):
            target = getattr(target, part)
        target(*args, **kwargs)

    def __getattr__(self, name: str):
        # only what the class has not: the real page's
        if name.startswith("_") or name in ("side_slot", "built"):
            raise AttributeError(name)
        if name == "status":
            return self._said
        if self._real is None and name in DEFERRED:
            return lambda *args, **kwargs: self._keep(name, args, kwargs)
        return getattr(self.real(), name)


class LazyEnergyPage(LazyPage):
    inverterRequested = Signal()

    def _own_signals(self) -> tuple:
        return ("inverterRequested",)


class LazyConsumptionPage(LazyPage):
    importRequested = Signal(str, str)

    def _own_signals(self) -> tuple:
        return ("importRequested",)


class LazyEconomicsPage(LazyPage):
    batteryRequested = Signal()

    def _own_signals(self) -> tuple:
        return ("batteryRequested",)


class InputClock(QObject):
    """When the designer last touched the window (a click, a key, the wheel, a move of the pointer), for what is done
    only while it rests: the pages made after the start, one at a time (MainWindow._rest_build)."""

    TOUCH = (QEvent.Type.MouseButtonPress, QEvent.Type.MouseMove, QEvent.Type.KeyPress, QEvent.Type.Wheel,
             QEvent.Type.TouchBegin)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.last = time.monotonic()

    def touch(self) -> None:
        self.last = time.monotonic()

    def still_for(self) -> float:
        """Seconds since the last touch."""
        return time.monotonic() - self.last

    def eventFilter(self, obj, event) -> bool:
        if event.type() in self.TOUCH:
            self.last = time.monotonic()
        return False
