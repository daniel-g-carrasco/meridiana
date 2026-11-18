"""R472: the side pills of Modelling, drawn over the side's highlight, a badge that grows with the side's number."""
import math
import unittest

from PySide6.QtTest import QTest

from meridiana import model
from quick.pianta import test_edit_window as edit

setUpModule = edit.setUpModule


def painted_above(a, b):
    """True when item `a` is painted over item `b` (siblings or a's ancestor sibling of b's)."""
    def chain(item):
        out = []
        while item is not None:
            out.append(item)
            item = item.parentItem()
        return out[::-1]
    ca, cb = chain(a), chain(b)
    at = 0
    while at < min(len(ca), len(cb)) and ca[at] == cb[at]:
        at += 1
    sa, sb = ca[at], cb[at]
    if sa.z() != sb.z():
        return sa.z() > sb.z()
    siblings = ca[at - 1].childItems()
    return siblings.index(sa) > siblings.index(sb)


class SidePillsWindow(unittest.TestCase):
    setUp = edit.EditWindowTest.setUp
    tearDown = edit.EditWindowTest.tearDown
    visual = edit.EditWindowTest.visual

    def twelve_sides(self):
        ring = [[60 + 30 * math.cos(2 * math.pi * k / 12), 60 + 30 * math.sin(2 * math.pi * k / 12)]
                for k in range(12)]
        self.controller.session.edit('Building', lambda p: p.buildings.append(model.Building(
            id='b12', name='Twelve', footprint=ring)))
        self.controller.editor.select('building', 'b12')
        self.controller._overlays()
        self.plan.fit()
        QTest.qWait(120)

    def test_the_pill_is_drawn_over_the_lit_side(self):
        self.twelve_sides()
        pill = self.visual('sidePill10')
        self.assertIsNotNone(pill)
        pill.parentItem().setProperty('hoverSide', 10)
        QTest.qWait(30)
        light = self.visual('sideHighlight')
        self.assertIsNotNone(light)
        self.assertTrue(light.isVisible())
        self.assertTrue(painted_above(pill, light), 'the pill lies over the highlight of its side')

    def test_the_badge_grows_with_the_digits_and_stays_a_disc_for_one(self):
        self.twelve_sides()
        for side in (0, 8):
            pill, badge = self.visual(f'sidePill{side}'), self.visual(f'sideBadge{side}')
            self.assertAlmostEqual(badge.width(), pill.height() - 2 * 2, delta=1e-6)
            self.assertAlmostEqual(badge.width(), badge.height(), delta=1e-6)
        for side in (9, 10, 11):
            pill, badge = self.visual(f'sidePill{side}'), self.visual(f'sideBadge{side}')
            self.assertIsNotNone(badge, side)
            digits = next(c for c in badge.childItems() if c.property('text') is not None)
            self.assertEqual(digits.property('text'), str(side + 1))
            self.assertGreaterEqual(badge.width(), digits.property('contentWidth') + 6, side)
            self.assertLessEqual(badge.x() + badge.width(), pill.width(), side)
            length = next((c for c in pill.childItems() if c.property('text') and 'm' in c.property('text')), None)
            if length is not None and length.isVisible():
                self.assertGreaterEqual(length.x(), badge.x() + badge.width(), side)
                self.assertLessEqual(length.x() + length.property('contentWidth'), pill.width(), side)
        self.assertFalse(self.warnings, self.warnings)


if __name__ == "__main__":
    unittest.main()
