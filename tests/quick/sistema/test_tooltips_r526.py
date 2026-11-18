"""R526, R550: when a tooltip comes and where it goes.

R526 (Daniel 07/11/2026: «sembra che le modifiche che avevamo fatto ai tooltip non ci siano più, tipo il ritardo
all'apertura»): the first tooltip waits ControlMetrics.tipDelay (700 ms), whatever became of the tooltips shown before.
R550 (Daniel 08/11/2026: «sul primo elemento lo rispetta, nei successivi no. Inoltre compare mai vicino al cursore, ma di
solito vicino all'elemento che lo ha triggerato ma allo stesso tempo a 5 millimetri da esso»): every tooltip waits, the
next ones too; it appears a little below and right of the pointer, where the pointer is when it appears, and stays
whole inside the window (left of the pointer at the right edge, above it at the bottom).

    python -m unittest quick.sistema.test_tooltips_r526
"""
import time
import unittest

import _setup
from PySide6.QtCore import QObject, QPoint, QPointF
from PySide6.QtTest import QTest

from quick.gestures import pump
from quick.sistema import test_controls

WAIT = 0.65         # ControlMetrics.tipDelay, 700 ms, less what the timers of a loaded machine may take off

SCENE = '''Item { id: page; width: 600; height: 400
    property alias kept: loader.active
    property alias boxShown: box.visible
    Loader { id: loader; x: 400; width: 200; height: 30
        sourceComponent: Item { width: 200; height: 30; M.ToolTip { objectName: "inDelegate"; text: "In a delegate"; visible: true } } }
    Item { id: box; x: 400; y: 40; width: 200; height: 30
        M.ToolTip { objectName: "inBox"; text: "In a box hidden while open"; visible: true } }
    // the two tooltips shown from the start stand away from the buttons: a tooltip over a control takes its hover
    M.Button { objectName: "first"; x: 20; y: 100; width: 160; text: "First"; tip: "The first tooltip" }
    M.Button { objectName: "second"; x: 220; y: 100; width: 160; text: "Second"; tip: "The next tooltip" }
    M.Button { objectName: "corner"; x: 470; y: 360; width: 130; height: 40; text: "Corner"
        tip: "A tooltip long enough to pass the window's right edge if it went right of the pointer" }
}'''


class TooltipWait(unittest.TestCase):
    setUpClass = classmethod(test_controls.ControlsTest.setUpClass.__func__)
    scene = test_controls.ControlsTest.scene

    def tip(self, root, name):
        control = root.findChild(QObject, name)
        return control, next(t for t in root.findChildren(QObject, 'controlTip')
                             if t.parent() is control or t.property('parent') is control)

    def corner_of(self, tip):
        """The tooltip's top left corner, in the window."""
        return tip.property('parent').mapToScene(QPointF(tip.property('x'), tip.property('y')))

    def hover(self, window, start, end, steps=6):
        for i in range(steps + 1):
            QTest.mouseMove(window, QPoint(start.x() + (end.x() - start.x()) * i // steps,
                                           start.y() + (end.y() - start.y()) * i // steps))
            pump(15)

    def shown_after(self, tip):
        """Seconds from now to the tooltip shown."""
        start = time.monotonic()
        self.assertTrue(_setup.wait_for(lambda: tip.property('visible'), 3000))
        return time.monotonic() - start

    def test_r526_after_tooltips_destroyed_or_hidden_while_open_the_next_waits(self):
        root, window = self.scene(SCENE)
        self.assertTrue(_setup.wait_for(lambda: root.findChild(QObject, 'inBox').property('opened'), 3000))
        root.setProperty('kept', False)             # the delegate with its tooltip open destroyed
        root.setProperty('boxShown', False)         # the control of an open tooltip hidden (a menu, a window closing)
        _control, tip = self.tip(root, 'second')
        QTest.mouseMove(window, QPoint(300, 110))
        self.assertGreater(self.shown_after(tip), WAIT, 'R468: the tooltip waits 700 ms')

    def test_r550_the_next_tooltip_waits_too_and_comes_at_the_pointer(self):
        root, window = self.scene(SCENE)
        _first, first = self.tip(root, 'first')
        _second, second = self.tip(root, 'second')
        self.hover(window, QPoint(30, 105), QPoint(60, 110))
        self.assertGreater(self.shown_after(first), WAIT - .1)
        corner = self.corner_of(first)
        self.assertEqual((corner.x(), corner.y()), (60 + 2, 110 + 21), 'below and right of the pointer')
        # straight on to the next control: it waits as the first did
        self.hover(window, QPoint(60, 110), QPoint(240, 112))
        start = time.monotonic()
        self.hover(window, QPoint(240, 112), QPoint(290, 118))     # the pointer goes on moving on the control
        self.assertFalse(second.property('visible'), 'R550: no tooltip at once')
        self.assertGreater(time.monotonic() - start + self.shown_after(second), WAIT, 'R550: the next waits too')
        corner = self.corner_of(second)
        self.assertEqual((corner.x(), corner.y()), (290 + 2, 118 + 21), 'where the pointer is when it appears')

    def test_r550_at_the_window_s_edges_the_tooltip_goes_left_of_and_above_the_pointer(self):
        root, window = self.scene(SCENE)
        _corner, tip = self.tip(root, 'corner')
        self.hover(window, QPoint(500, 370), QPoint(580, 385))
        self.shown_after(tip)
        corner = self.corner_of(tip)
        width, height = tip.property('width'), tip.property('height')
        self.assertLessEqual(corner.x() + width, window.width())
        self.assertLessEqual(corner.y() + height, window.height())
        self.assertLessEqual(corner.x() + width, 580, 'left of the pointer')
        self.assertLessEqual(corner.y() + height, 385, 'above the pointer')


if __name__ == '__main__':
    unittest.main()
