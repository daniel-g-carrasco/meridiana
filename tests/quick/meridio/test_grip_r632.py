"""R632 (1): the grip of Meridio's bubble (Daniel 15/11/2026, on the Linux laptop at scale 2: «spostala un po' più in
basso e a destra così da dargli un leggerissimo margine dall'angolo e dalle lo stesso colore del bordino del
fumetto»).

Its strokes touched the rounded corner of the outline. Measured on the pixels, for a grip at the top left (the
character low on the right, as at his home) and one at the bottom right: the grip's ink is what a grab with its
strokes has more than one without them, the outline's ink what differs from the bubble's ground. The strokes stand
clear of the outline by about a step (Theme.space.XXS), the same from the two edges, and are no darker than the
outline's line (the same token, Theme.colors.line). Offscreen, in the window of the page alone.
"""
import math
import unittest

from PySide6.QtCore import QObject, QPointF, QRect
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from meridiana.gui.backend.assistant import build_page
from quick.gestures import wait_for

STEP = 2            # Theme.space.XXS, the margin asked for


def apart(a, b):
    return abs(a.red() - b.red()) + abs(a.green() - b.green()) + abs(a.blue() - b.blue())


class GripTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['r632-tests'])

    def corner(self, theme, high):
        engine, window, _ = build_page('meridio', options={'reducedMotion': True, 'theme': theme})
        self.addCleanup(lambda: (window.close(), delete(engine)))
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        layer = window.findChild(QObject, 'assistantLayer')
        wait_for(lambda: not layer.property('relocating'), 5)
        if high:
            layer.setProperty('avatarX', 60)
            layer.setProperty('avatarY', 80)
            layer.setProperty('tail', 'left')
        layer.placeBubble()
        grip = layer.findChild(QObject, 'assistantGrip')
        mark = layer.findChild(QObject, 'assistantGripMark')
        bubble = layer.findChild(QObject, 'assistantBubble')
        left, top = grip.property('gripLeft'), grip.property('gripTop')
        self.assertEqual((left, top), (False, False) if high else (True, True))
        shown = window.grabWindow()
        mark.setProperty('visible', False)          # a grab renders the scene as it is now
        hidden = window.grabWindow()
        mark.setProperty('visible', True)
        dpr = shown.width() / window.width()
        at = bubble.mapToScene(QPointF(0 if left else bubble.width(), 0 if top else bubble.height()))
        size = 24
        rect = QRect(round((at.x() - (0 if left else size)) * dpr), round((at.y() - (0 if top else size)) * dpr),
                     round(size * dpr), round(size * dpr))
        a, b = shown.copy(rect), hidden.copy(rect)
        w, h = a.width(), a.height()
        ground = b.pixelColor(w // 2, h // 2)
        grip_ink = [(x, y) for y in range(h) for x in range(w) if apart(a.pixelColor(x, y), b.pixelColor(x, y)) > 30]
        line_ink = [(x, y) for y in range(h) for x in range(w) if apart(b.pixelColor(x, y), ground) > 30]
        far_row, far_col = (h - 1 if top else 0), (w - 1 if left else 0)
        cols = [x for x, y in line_ink if y == far_row]
        rows = [y for x, y in line_ink if x == far_col]
        self.assertTrue(grip_ink and cols and rows, (len(grip_ink), cols, rows))
        edge_x, edge_y = (min(cols) if left else max(cols)), (min(rows) if top else max(rows))
        return dict(
            dpr=dpr,
            from_x=min(abs(x - edge_x) for x, _ in grip_ink) - 1,
            from_y=min(abs(y - edge_y) for _, y in grip_ink) - 1,
            nearest=min(math.hypot(x - u, y - v) for x, y in grip_ink for u, v in line_ink),
            grip=max(apart(a.pixelColor(x, y), ground) for x, y in grip_ink),
            line=apart(b.pixelColor(edge_x, far_row), ground))

    def test_the_grip_stands_clear_of_the_corner_in_the_outline_colour(self):
        for theme in ('light', 'dark'):
            for high in (False, True):
                with self.subTest(theme=theme, corner='bottom right' if high else 'top left'):
                    m = self.corner(theme, high)
                    # a margin: not touching the outline any more (it touched: 0 px)
                    self.assertGreaterEqual(m['nearest'], STEP * m['dpr'], m)
                    # the same from the two edges of the corner (within the one device pixel of the antialiasing: at
                    # scale 1 the top left reads 3 and 2, at scale 2 both 6)
                    self.assertLessEqual(abs(m['from_x'] - m['from_y']), 1, m)
                    # light, as the outline's line: no darker than it (it was the muted text's grey)
                    self.assertLessEqual(m['grip'], m['line'] + 12, m)


if __name__ == '__main__':
    unittest.main()
