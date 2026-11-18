"""The controls on a card's title line (R345): in order on one row where they fit, wrapped whole under it where they do
not, reduced only what is wider than a whole row, the tail beside the cross, the end against the right edge."""
import unittest

import _setup
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QWidget

setUpModule = _setup.keep_global_state


class Box(QWidget):
    def __init__(self, width, least=None, height=28):
        super().__init__()
        self.w, self.least, self.h = width, width if least is None else least, height

    def sizeHint(self):
        return QSize(self.w, self.h)

    def minimumSizeHint(self):
        return QSize(self.least, self.h)


class TitleToolsPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def tools(self, *specs):
        from meridiana.ui.title_tools import TitleTools
        tools = TitleTools()
        self.addCleanup(_setup.dispose, tools)
        boxes = []
        for width, align, *rest in specs:
            boxes.append(tools.add(Box(width, *rest), align))
        return tools, boxes

    def test_one_row_in_order_with_the_end_at_the_right_and_the_tail_last(self):
        tools, (views, counts, filters, copy) = self.tools((300, "start", 100), (180, "start"), (200, "end"),
                                                           (20, "tail", None, 20))
        placed, heights = tools.plan(1000, indent=100, first=17)
        where = {w: r for w, r in placed}
        self.assertEqual(heights, [28])
        self.assertEqual(where[views].left(), 100)                             # after the title's words
        self.assertGreater(where[counts].left(), where[views].right())
        self.assertEqual(where[copy].right() + 1, 1000)                        # the tail against the cross
        self.assertEqual(where[filters].right() + 1 + 8 + 20, 1000)            # the end, then a gap, then the tail
        self.assertEqual({r.center().y() for w, r in placed if w is not copy}, {13})

    def test_what_does_not_fit_goes_whole_to_the_next_row_never_past_the_edge(self):
        tools, (views, counts, filters, copy) = self.tools((300, "start", 100), (180, "start"), (200, "end"),
                                                           (20, "tail", None, 20))
        for width in (900, 700, 500, 420, 330):
            placed, heights = tools.plan(width, indent=100, first=17)
            where = {w: r for w, r in placed}
            for w, r in placed:
                self.assertGreaterEqual(r.left(), 0, width)
                self.assertLessEqual(r.right() + 1, width, width)
                self.assertEqual(r.width(), w.sizeHint().width(), (width, w))     # each whole, none reduced
            for i, (w1, r1) in enumerate(placed):
                for w2, r2 in placed[i + 1:]:
                    self.assertFalse(r1.intersects(r2), (width, w1, w2))
            self.assertEqual(where[copy].top() < heights[0], True)                 # the tail on the first row
        placed, heights = tools.plan(700, indent=100, first=17)
        self.assertGreater(len(heights), 1)
        where = {w: r for w, r in placed}
        self.assertEqual(where[filters].right() + 1, 700)                          # alone on its row, at the right
        self.assertEqual(tools.height_for(700, 100, 17), sum(heights) + 4 * (len(heights) - 1))

    def test_one_wider_than_a_row_is_reduced_to_its_least_and_no_more(self):
        tools, (views,) = self.tools((500, "start", 120))
        self.assertEqual(tools.plan(300)[0][0][1].width(), 300)
        self.assertEqual(tools.plan(80)[0][0][1].width(), 120)                     # not below its least

    def test_the_first_row_is_at_least_as_tall_as_the_title_and_the_rest_by_their_height(self):
        tools, _ = self.tools((300, "start", 100, 24), (300, "start", 100, 28))
        self.assertEqual(tools.plan(700, first=40)[1], [40])
        self.assertEqual(tools.plan(400, first=10)[1], [24, 28])


if __name__ == "__main__":
    unittest.main()
