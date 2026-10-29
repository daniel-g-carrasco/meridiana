"""The marks of the checks drawn sharp (Daniel, R30: «piccolissimi e renderizzati male»): painted at the size and
the density asked, never an image of 22 x 20 points enlarged; in the project's tree as tall as the text of the
row, the number beside it in the row's font. PySide6 and a display (offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


def inked(image) -> int:
    return sum(1 for x in range(image.width()) for y in range(image.height()) if image.pixelColor(x, y).alpha() > 0)


class Sharp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_an_icon_is_painted_at_the_density_asked(self):
        from PySide6.QtCore import QSize

        from meridiana.ui.marks import icon
        one = icon("warn").pixmap(QSize(20, 20), 1.0)
        two = icon("warn").pixmap(QSize(20, 20), 2.0)
        self.assertEqual((two.width(), two.height(), two.devicePixelRatio()), (40, 40, 2.0))
        # drawn again at twice the pixels, not the small one enlarged: about four times the ink
        self.assertGreater(inked(two.toImage()), 3 * inked(one.toImage()))

    def test_in_the_tree_the_mark_is_as_tall_as_the_text_and_the_number_beside_it(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFontMetrics
        from PySide6.QtWidgets import QStyleOptionViewItem, QTreeWidget, QTreeWidgetItem

        from meridiana.ui.marks import MARK_ROLE, MarkDelegate
        from meridiana.ui.design import Text, text_font
        from meridiana.ui import status_pill
        tree = QTreeWidget()
        self.addCleanup(tree.deleteLater)
        tree.setColumnCount(2)
        delegate = MarkDelegate(tree)
        tree.setItemDelegateForColumn(1, delegate)
        one, many = QTreeWidgetItem(tree, ["a", ""]), QTreeWidgetItem(tree, ["b", ""])
        one.setData(1, MARK_ROLE, ("info", 1))
        many.setData(1, MARK_ROLE, ("warn", 12))
        option = QStyleOptionViewItem()
        option.initFrom(tree)
        text = QFontMetrics(tree.font()).height()
        small, big = (delegate.sizeHint(option, tree.indexFromItem(it, 1)) for it in (one, many))
        self.assertGreaterEqual(small.height(), text)
        # a pill with the number always written («✘ 1», study 17, T2): wider by the second digit
        metrics = QFontMetrics(text_font(Text.LABEL, tree.font()))
        self.assertGreaterEqual(big.width() - small.width(), metrics.horizontalAdvance("12") - metrics.horizontalAdvance("1"))
        self.assertGreater(small.width(), text + metrics.horizontalAdvance("1"))
        self.assertIsNone(tree.indexFromItem(QTreeWidgetItem(tree, ["c", ""]), 1).data(MARK_ROLE))
        tree.resize(300, 120)
        tree.show()
        self.app.processEvents()
        shot = tree.viewport().grab().toImage()
        rect = tree.visualItemRect(many)
        dpr = shot.devicePixelRatio()                        # on a real screen the grab is in device pixels
        row = shot.copy(round(tree.header().sectionPosition(1) * dpr), round(rect.y() * dpr),
                        round(tree.header().sectionSize(1) * dpr), round(rect.height() * dpr))
        ground = status_pill.colours("warn", tree.palette())[0]
        tinted = sum(1 for x in range(row.width()) for y in range(row.height())
                     if row.pixelColor(x, y) == ground)
        self.assertGreater(tinted, 0.25 * text * text / 2 * dpr * dpr)
        self.assertGreaterEqual(small.height(), 24, "The 20 px pill has air above and below")
        # the mark has a role of its own: the index the Checks keep in UserRole stays beside it, and the text too
        many.setData(1, Qt.ItemDataRole.UserRole, 7)
        self.assertEqual((many.data(1, Qt.ItemDataRole.UserRole), many.data(1, MARK_ROLE)), (7, ("warn", 12)))
        self.assertEqual(many.text(0), "b")


if __name__ == "__main__":
    unittest.main()
