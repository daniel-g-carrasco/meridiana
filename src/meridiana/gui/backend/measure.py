"""The measuring tool's bridge to the window (study 46, state of r34-righello section 2.2).

One per window, shared by the plan and the 3D view: it holds the tool (app/view/measure_tool.py) and nothing of a
view. A view registers its probe, `register(view, probe)` with probe(x, y, scale, wanted) -> Probe or None (the
plan: gui/backend/plan_measure.py), then sends its gestures with its name: `move`, `click`, `doubleClick` with the
point the view gives its probe and its scale, `key` with the key's name. What it draws it asks in three parts, each
again when its revision changes, so that a step of the pointer sends only what it changed: `display(view)` (the span
to the pointer, the total in hand, the pointer, the guides, the small pills: measure_display.build without "done" and
with only "elastic", "total" and "closed" in "current"; `revision`), `placed(view)` (the points placed of the
measurement in hand, their marks and spans, or None; `placedRevision`) and `done(view)` (the measurements made;
`doneRevision`).

Every call on the window's thread is timed (`reset_stats()`, `stats()`, the shape of tests/quick/aiuti/
finestra_libera.py): the window never waits for the tool. A step of the pointer finds its point at once and tells the
views at the next turn of the events ("draw"): the views draw once for the steps that came together (a mouse of 1000
steps a second gives several between two frames), and the finding and the drawing are two short calls, not one.
"""
from __future__ import annotations

import time

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from meridiana.app.view import measure_text as words
from meridiana.app.view.measure_tool import IGNORED, LEAVE, USED, MeasureTool
from meridiana.gui.style.design import Motion


def modifiers(bits) -> frozenset:
    """The views' bits (Plan.qml mods): 1 Ctrl, 2 Shift, 4 Alt."""
    return frozenset(name for bit, name in ((1, "ctrl"), (2, "shift"), (4, "alt")) if int(bits) & bit)


class MeasureBridge(QObject):
    changed = Signal()          # the measurement in hand, the pointer, the hint, the state, the mode
    placedChanged = Signal()    # the points placed of the measurement in hand
    doneChanged = Signal()      # the measurements made: one more, fewer, selected
    left = Signal()             # Esc found nothing left to take back: the view gives the tool up
    numbersChanged = Signal()   # R609: the numbers of the span to the pointer, for the hint bar, once the pointer rests

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tool = MeasureTool()
        self._probes = {}
        self._pointer = None            # the last (view, x, y, scale) a view gave: found again when a key changes the aids
        self._revision = 0
        self._placed_revision = 0
        self._done_revision = 0
        self._builds = {}
        self._dones = {}
        self._placed_seen = self._placed_key()
        self._done_seen = self._done_key()
        self._pending = False           # a step of the pointer not yet told to the views
        # R609: the hint bar's numbers follow the pointer once it rests (Motion.REST), not at every step: the status
        # line is the window's, and a change of it is not light
        self._numbers = ""
        self._numbers_wait = QTimer(self)
        self._numbers_wait.setSingleShot(True)
        self._numbers_wait.setInterval(Motion.REST)
        self._numbers_wait.timeout.connect(self._tell_numbers)
        self.reset_stats()

    # -- the window's time --------------------------------------------------------------------------------------

    def reset_stats(self):
        self._longest, self._calls = (0.0, ""), 0

    def stats(self) -> dict:
        return {"longest_call": self._longest, "calls": self._calls}

    def _timed(self, name, work):
        started = time.perf_counter()
        try:
            return work()
        finally:
            took = time.perf_counter() - started
            self._calls += 1
            if took > self._longest[0]:
                self._longest = (took, name)

    # -- the views ----------------------------------------------------------------------------------------------

    def register(self, view: str, probe):
        """`probe(x, y, scale, wanted)`: the view's Probe under its point, or None."""
        self._probes[view] = probe

    def _probe(self, view, x, y, bits, scale):
        self._pointer = (view, x, y, scale)
        probe = self._probes.get(view)
        return probe(float(x), float(y), float(scale), self.tool.wanted(modifiers(bits))) if probe else None

    def _again(self, bits):
        """A key changed what the probe looks for (an arrow's axis, F8): the point under the pointer found again."""
        if self._pointer is not None and self.tool.points:
            view, x, y, scale = self._pointer
            said = self.tool.message        # what the key said (Down without an edge) stays in the hint
            self.tool.move(self._probe(view, x, y, bits, scale), modifiers(bits))
            self.tool.message = said

    def _done_key(self):
        return tuple(m.id for m in self.tool.measures), frozenset(self.tool.selected)

    def _placed_key(self):
        return self.tool.mode, tuple((p.point, p.kind, p.exact) for p in self.tool.points)

    def _changed(self, moving=False):
        self._pending = False
        self._revision += 1
        self._builds = {}
        key = self._placed_key()
        if key != self._placed_seen:
            self._placed_seen = key
            self._placed_revision += 1
            self.placedChanged.emit()
        key = self._done_key()
        if key != self._done_seen:
            self._done_seen = key
            self._done_revision += 1
            self._dones = {}
            self.doneChanged.emit()
        self.changed.emit()
        if moving and self.tool.points:
            self._numbers_wait.start()  # a step of the pointer: told once it rests
        else:
            self._tell_numbers()        # a click, a key, nothing in hand: at once

    def _tell_numbers(self):
        self._numbers_wait.stop()
        numbers = self.tool.numbers
        if numbers != self._numbers:
            self._numbers = numbers
            self.numbersChanged.emit()

    @Property(str, notify=numbersChanged)
    def numbers(self):
        """R609: the numbers the drawing does not write of the span to the pointer, for the hint bar."""
        return self._numbers

    @Slot(str, float, float, int, float)
    def move(self, view, x, y, bits=0, scale=1.0):
        def work():
            self.tool.move(self._probe(view, x, y, bits, scale), modifiers(bits))
            self._builds = {}           # asked before the views are told, the display is already the new one
            if not self._pending:
                self._pending = True
                QTimer.singleShot(0, self, self._draw)
        self._timed("move", work)

    def _draw(self):
        if self._pending:
            self._timed("draw", lambda: self._changed(moving=True))

    @Slot(str, float, float, int, float)
    def click(self, view, x, y, bits=0, scale=1.0):
        def work():
            self.tool.click(self._probe(view, x, y, bits, scale), modifiers(bits))
            self._changed()
        self._timed("click", work)

    @Slot(str, float, float, int, float)
    def doubleClick(self, view, x, y, bits=0, scale=1.0):
        def work():
            self.tool.double_click(None, modifiers(bits))
            self._changed()
        self._timed("doubleClick", work)

    @Slot(str, str, int, result=str)
    def key(self, key, text="", bits=0):
        """IGNORED ("") when the key is not the tool's (the view may use it), "used", or "leave" (the signal `left`
        too): Esc found nothing left to take back."""
        def work():
            answer = self.tool.key(key, text, modifiers(bits))
            if answer == USED:
                self._again(bits)
            if answer != IGNORED:
                self._changed()
            if answer == LEAVE:
                self.left.emit()
            return answer
        return self._timed("key", work)

    @Slot(str)
    def release(self, key):
        """A key let go (Shift: the direction held goes)."""
        def work():
            if self.tool.release(key):
                self._changed()
        self._timed("release", work)

    @Slot()
    def leave(self):
        """Another tool: the measurement in hand is kept from two points, the measurements made stay."""
        def work():
            self.tool.leave()
            self._changed()
        self._timed("leave", work)

    @Slot(str)
    def setMode(self, mode):
        def work():
            self.tool.set_mode(mode)
            self._changed()
        self._timed("setMode", work)

    @Slot(str)
    def setSnap(self, kind):
        """The snaps' menu (Shift + right button): the snap for the point being placed ("none": none), the point under
        the pointer found again with it; after that point the snaps are all back (the tool's set_snap)."""
        def work():
            self.tool.set_snap(kind or None)
            if self._pointer is not None:
                view, x, y, scale = self._pointer
                self.tool.move(self._probe(view, x, y, 0, scale))
            self._changed()
        self._timed("setSnap", work)

    @Property('QVariantList', constant=True)
    def snapChoices(self):
        """The snaps' menu's entries ({kind, text}, a rule before «None»), as Controls/MenuEntry.qml reads them."""
        return words.snap_menu()

    @Property(str, notify=changed)
    def snap(self):
        """The snap asked from the menu for the point being placed, "" when they are all on."""
        return self.tool.snap_request or ""

    @Slot(bool)
    def setPolar(self, on):
        """The 15° guides follow the plan's Ortho (gui/backend/plan.py holds the one setting, for drawing and
        measuring): the point under the pointer found again with them or without."""
        def work():
            if bool(on) != self.tool.polar:
                self.tool.set_polar(on)
                self._again(0)
                self._changed()
        self._timed("setPolar", work)

    # -- the measurements made: chosen, removed, copied (study 46, 3.6). They stay in the session until removed or
    # another project is in hand, never in the project: no session.edit(), nothing to save, nothing to undo.

    @Slot(int, int)
    def select(self, measure_id, bits=0):
        """A click on a measurement made (MeasureLayer.qml, the pill), by the rule of the selection."""
        def work():
            self.tool.choose(int(measure_id), modifiers(bits))
            self._changed()
        self._timed("select", work)

    @Slot()
    def clearSelection(self):
        if self.tool.selected:
            self.tool.select([])
            self._changed()

    @Slot(result=int)
    def removeSelected(self):
        removed = self.tool.remove_selected()
        if removed:
            self._changed()
        return removed

    @Slot(result=int)
    def removeAll(self):
        removed = self.tool.remove_all()
        if removed:
            self._changed()
        return removed

    @Slot(str, int, result=bool)
    def chosenKey(self, key, bits=0):
        """With measurements chosen (the views' Select), Delete removes them, Ctrl+C copies their text, Esc lets them
        go: True when the key was theirs; with none chosen the view's keys do what they did (plan and 3D view)."""
        mods = modifiers(bits)
        if not self.tool.selected:
            return False
        if key in ("Delete", "Del"):
            self.removeSelected()
        elif key == "C" and "ctrl" in mods and "alt" not in mods:
            self.copySelected()
        elif key in ("Escape", "Esc"):
            self.clearSelection()
        else:
            return False
        return True

    @Slot(result=bool)
    def copySelected(self):
        """The text of the measurements chosen in the clipboard; False when none is chosen."""
        text = self.tool.copy_selected()
        if text:
            QGuiApplication.clipboard().setText(text)
        return bool(text)

    def reset(self):
        """Another project in hand: the measurement in hand and those made go."""
        if self.tool.points or self.tool.measures:
            self.tool.reset()
            self._changed()

    @Property(int, notify=doneChanged)
    def chosen(self):
        """How many measurements made are chosen."""
        return len(self.tool.selected)

    @Property(str, notify=doneChanged)
    def chosenHint(self):
        """The hint bar's line with Select while measurements made are chosen, '' with none."""
        return self.tool.chosen_hint

    # -- what the views draw ------------------------------------------------------------------------------------

    @Property(int, notify=changed)
    def revision(self):
        return self._revision

    @Property(int, notify=placedChanged)
    def placedRevision(self):
        return self._placed_revision

    @Property(int, notify=doneChanged)
    def doneRevision(self):
        return self._done_revision

    def _build(self, view):
        """The tool's display for the view without "done", split into what follows the pointer and what is placed;
        kept until the next change."""
        if view not in self._builds:
            whole = self.tool.display(view, with_done=False)
            current = whole["current"]
            placed = None
            if current is not None:
                placed = {k: current[k] for k in ("marks", "segments", "closed", "sources")}
                whole["current"] = {k: current[k] for k in ("elastic", "total", "closed")}
            self._builds[view] = (whole, placed)
        return self._builds[view]

    @Slot(str, result='QVariantMap')
    def display(self, view):
        """What the view draws that follows the pointer: the span to it, the total in hand, the pointer, the guides,
        the reference edge, the small pills."""
        return self._timed("display", lambda: self._build(view)[0])

    @Slot(str, result='QVariant')
    def placed(self, view):
        """The points placed of the measurement in hand ({marks, segments, closed}), None at rest."""
        return self._timed("placed", lambda: self._build(view)[1])

    @Slot(str, result='QVariantList')
    def done(self, view):
        """The measurements made as the view draws them, kept until one is added, taken away or selected."""
        def work():
            if view not in self._dones:
                self._dones[view] = self.tool.done(view)
            return self._dones[view]
        return self._timed("done", work)

    @Property(str, notify=changed)
    def hint(self):
        return self.tool.hint

    @Property(str, notify=changed)
    def state(self):
        return self.tool.state

    @Property(str, notify=changed)
    def mode(self):
        return self.tool.mode

    @Property(bool, notify=changed)
    def polar(self):
        return bool(self.tool.polar)

    @Property(bool, notify=placedChanged)
    def inHand(self):
        """A point is placed: the arrows, the digits, Enter and Backspace are the tool's."""
        return bool(self.tool.points)

    @Property(int, notify=doneChanged)
    def count(self):
        return len(self.tool.measures)
