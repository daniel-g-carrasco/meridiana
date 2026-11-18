"""The field of a side in the Properties lights that side on the plan (study 22, 3.6; R276), and leaving it puts it
out: the plan's numbered pills and the Properties' «Side n» say the same side."""
import unittest

import _setup
from _fixtures import capannone


class SideLight(unittest.TestCase):
    def test_the_field_of_a_side_lights_it_on_the_plan(self):
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QApplication, QDoubleSpinBox
        self.app = _setup.qt_or_skip()
        _setup.window(self, capannone())
        win = self.win
        bid = win.project.buildings[0].id
        win._select("building", bid)
        _setup.turn_events(self.app, 200)
        fields = [w for w in win.findChildren(QDoubleSpinBox) if w.property("side") is not None and w.isVisibleTo(win)]
        self.assertEqual(len(fields), len(win.project.buildings[0].footprint))
        QApplication.sendEvent(fields[1], QEvent(QEvent.Type.Enter))
        self.assertEqual(win.plan.lit_side, 1)
        QApplication.sendEvent(fields[1], QEvent(QEvent.Type.Leave))
        self.assertIsNone(win.plan.lit_side)


if __name__ == "__main__":
    unittest.main()
