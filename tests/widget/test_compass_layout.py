"""The compass yields the top row to the tools on narrow maps."""
import unittest

import _setup
from _fixtures import capannone, plan_view

setUpModule = _setup.keep_global_state


class CompassLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_compass_moves_below_the_tools_and_returns_when_room_is_available(self):
        from PySide6.QtGui import QAction
        from meridiana.ui import motion, plan_overlays
        from meridiana.ui.viewbar import ViewBar

        plan, _ = plan_view(self, capannone())
        actions = [QAction(str(n), plan) for n in range(8)]
        plan.viewbar = ViewBar(plan, [actions])
        plan.viewbar.show()
        old = motion.reduced()
        motion.set_reduced(True)
        self.addCleanup(motion.set_reduced, old)
        plan.resize(plan.viewbar.width() + plan.north.width(), 480)
        self.app.processEvents()
        plan_overlays.place(plan)
        self.assertEqual(plan.viewbar.y(), plan.viewport().y() + plan_overlays.MARGIN)
        self.assertGreater(plan.north.y(), plan.viewbar.geometry().bottom())
        self.assertLess(plan.north.geometry().bottom(), plan.scale_bar.y())
        self.assertFalse(plan.north.geometry().intersects(plan.viewbar.geometry()))
        plan.resize(1000, 600)
        self.app.processEvents()
        plan_overlays.place(plan)
        self.assertEqual(plan.north.y(), plan.viewport().y() + plan_overlays.MARGIN)

    def test_the_centre_dot_is_fixed_while_the_letter_turns_with_the_arrow(self):
        from meridiana.ui.plan_overlays import NorthArrow
        north = NorthArrow(None)
        self.addCleanup(_setup.dispose, north)
        centre = north.CENTRE
        for angle in (0, 45, 90, 150, 270):
            north.set_rotation(angle)
            image = north.grab().toImage()
            dpr = image.devicePixelRatio()
            self.assertGreater(image.pixelColor(round(centre.x() * dpr), round(centre.y() * dpr)).lightness(), 180)
            delta = north.letter_centre() - centre
            self.assertAlmostEqual(delta.x() ** 2 + delta.y() ** 2, north.LETTER ** 2)

    def test_corner_changes_animate_once_and_stop_at_the_latest_target(self):
        from PySide6.QtCore import QPoint, QPropertyAnimation
        from meridiana.ui import motion
        from meridiana.ui.plan_overlays import NorthArrow
        north = NorthArrow(None)
        self.addCleanup(_setup.dispose, north)
        old = motion.reduced()
        motion.set_reduced(False)
        self.addCleanup(motion.set_reduced, old)
        north.show()
        north.place_at(QPoint(200, 8), False)
        north.place_at(QPoint(200, 260), True)
        self.assertEqual(north._travel.state(), QPropertyAnimation.State.Running)
        north.place_at(QPoint(200, 8), False)
        self.assertTrue(_setup.wait_until(self.app, lambda: north._travel.state() != QPropertyAnimation.State.Running))
        self.assertEqual(north.pos(), QPoint(200, 8))
