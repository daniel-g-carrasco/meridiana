"""The plan's side of the measuring tool (study 46): its probe registered with the window's MeasureBridge
(gui/backend/measure.py), the references kept with the project, the plan's gestures sent to the bridge.

The probe itself, the snaps and the height of the surface under the point, is app/view/plan_probe.py (no Qt); this
module only joins the plan's controller and the bridge.
"""
from __future__ import annotations

from PySide6.QtCore import QObject

from meridiana.app.view.measure_tool import IGNORED
from meridiana.app.view.plan_probe import PlanProbe

VIEW = "plan"


class PlanMeasure(QObject):
    def __init__(self, controller, bridge):
        super().__init__(controller)
        self.controller, self.bridge = controller, bridge
        self.probe = PlanProbe(controller.session.project)
        self._hint = bridge.hint
        bridge.register(VIEW, self._probe)
        bridge.changed.connect(self._changed)
        bridge.left.connect(self._left)
        bridge.doneChanged.connect(self._chosen)

    def _probe(self, x, y, scale, wanted):
        return self.probe.probe((x, y), scale, wanted, snaps_on=self.controller.editor.snaps_on)

    def refresh(self):
        """The project's geometry changed: the outlines snapped to and the roofs under the points."""
        self.probe.set_project(self.controller.session.project)

    def _active(self) -> bool:
        return self.controller.tool == "measure"

    def _changed(self):
        # the plan's hint follows the tool's: told only when it changes, not at every step of the pointer
        if self._active() and self.bridge.hint != self._hint:
            self._hint = self.bridge.hint
            self.controller.stateChanged.emit()

    def _left(self):
        if self._active():
            self.controller.setTool("select")

    # the plan's gestures with the tool Measure in hand

    def pointer(self, x, y, bits, scale):
        self.bridge.move(VIEW, x, y, bits, scale)

    def click(self, x, y, bits, scale):
        self.bridge.click(VIEW, x, y, bits, scale)

    def double_click(self, x, y, bits, scale):
        self.bridge.doubleClick(VIEW, x, y, bits, scale)

    def key(self, key, text, bits) -> bool:
        """True when the key was the tool's (or it left the tool), False when the plan may use it."""
        return self.bridge.key(key, text, bits) != IGNORED

    # the measurements made, chosen with Select (study 46, 3.6): a click on a pill chooses (MeasureLayer.qml)

    def chosen_key(self, key, mods) -> bool:
        """With Select and measurements chosen, Delete removes them, Ctrl+C copies their text, Esc lets them go:
        True when the key was theirs. With none chosen the plan's keys do what they did."""
        if self.controller.tool != "select":
            return False
        return self.bridge.chosenKey(key, (1 if "ctrl" in mods else 0) | (4 if "alt" in mods else 0))

    def let_go(self):
        """A click elsewhere in the plan with Select: the measurements chosen are let go."""
        self.bridge.clearSelection()

    def project_replaced(self):
        """Another project in hand (opened, new, imported, recovered): the measurements of the one before go. The one
        place where they go with the project (Daniel's choice 3: they are of the session, never saved)."""
        self.bridge.reset()

    def _chosen(self):
        # the hint bar says what Delete, Ctrl+C and Esc do while measurements are chosen
        if self.controller.tool == "select":
            self.controller.stateChanged.emit()
