"""R497: with «Align the view to a side» waiting, the command's icon stands beside the pointer only while the pointer
is on a side the command takes, and that side is lit; nothing in Select, nothing away from the sides."""
import unittest

from PySide6.QtCore import QPoint
from PySide6.QtQml import QQmlEngine, QQmlExpression
from PySide6.QtTest import QTest

from quick.pianta import test_edit_window as edit

setUpModule = edit.setUpModule


class AlignBadge(unittest.TestCase):
    setUp = edit.EditWindowTest.setUp
    tearDown = edit.EditWindowTest.tearDown
    visual = edit.EditWindowTest.visual

    def at(self, east, north):
        """The window point of a plan point."""
        e = QQmlExpression(QQmlEngine.contextForObject(self.plan), self.plan, f'screen({east}, {north})')
        p = e.evaluate()[0]
        self.assertFalse(e.hasError(), e.error().toString())
        return self.plan.mapToScene(p).toPoint()

    def hover(self, east, north):
        QTest.mouseMove(self.window, self.at(east, north))
        QTest.qWait(40)

    def lit(self):
        return [d for d in self.controller._draft if d.get('stroke') == '#ffb000']

    def test_badge_and_lit_side_only_on_a_side_while_align_waits(self):
        badge = self.visual('collectBadge')
        self.assertIsNotNone(badge)
        self.hover(20, 0.05)                             # Select: a side gives no badge
        self.assertFalse(badge.isVisible())
        self.controller.pickAnyEdge('align')
        self.hover(20, 10)                               # inside, far from every side: nothing
        self.assertEqual(self.controller.collectBadge, '')
        self.assertFalse(badge.isVisible())
        self.assertFalse(self.lit())
        self.hover(20, 0.05)                             # on the south side of the building
        self.assertEqual(self.controller.collectBadge, 'view_align')
        self.assertTrue(badge.isVisible())
        pointer = self.at(20, 0.05)
        corner = badge.mapToScene(badge.boundingRect().topLeft()).toPoint()
        self.assertLessEqual(abs(corner.x() - pointer.x() - 14), 2)
        self.assertLessEqual(abs(corner.y() - pointer.y() - 16), 2)
        icon = badge.childItems()[0]
        self.assertEqual(icon.property('name'), 'view_align')
        self.assertEqual(len(self.lit()), 1)
        self.hover(40.05, 12)                            # the east side
        self.assertTrue(badge.isVisible())
        self.hover(50, 25)                               # away from the building
        self.assertFalse(badge.isVisible())
        self.assertFalse(self.lit())
        angles = []
        self.controller.alignRequested.connect(angles.append)
        self.hover(20, 19.95)
        QTest.mouseClick(self.window, edit.Qt.LeftButton, edit.Qt.NoModifier, self.at(20, 19.95))
        QTest.qWait(40)
        self.assertEqual(len(angles), 1)
        self.assertFalse(self.controller.collecting)
        self.assertFalse(badge.isVisible())


if __name__ == '__main__':
    unittest.main()
