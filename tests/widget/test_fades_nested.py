"""The fades of a page that holds a table with fades of its own, and of a view whose rows are drawn on a colour of
their own (Daniel, 30/10/2026: «problemi di velatura che non avviene come dovrebbe nel pannello verifiche, in Consumi
e in bilancio ed economia»). PySide6 and a display (offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state


class NestedFades(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_a_page_with_a_table_inside_gets_fades_of_its_own_and_the_table_keeps_its(self):
        """attach looked for fades among all the children: it found the inner table's, took them for the page's and
        turned them into a page's; the page itself never had any."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QLabel, QScrollArea, QTableWidget, QVBoxLayout, QWidget

        from meridiana.ui import fades
        page = QScrollArea()
        self.addCleanup(page.deleteLater)
        page.setWidgetResizable(True)
        inside = QWidget()
        box = QVBoxLayout(inside)
        table = QTableWidget(40, 3)
        box.addWidget(table)
        box.addWidget(QLabel("\n".join(f"riga {i}" for i in range(80))))
        page.setWidget(inside)
        page.resize(300, 200)
        page.show()
        own_table = fades.attach(table, table=True)
        own_page = fades.attach(page, air=True)
        self.app.processEvents()
        self.assertIsNot(own_page, own_table)
        self.assertIs(own_page.area, page)
        self.assertIs(page.findChild(fades.Fades, "", Qt.FindChildOption.FindDirectChildrenOnly), own_page)
        self.assertFalse(own_table.edges[0].page)                   # the table stays a table
        self.assertTrue(own_page.edges[0].page)
        bar = page.verticalScrollBar()
        bar.setValue(bar.maximum() // 2)
        self.app.processEvents()
        self.assertTrue(own_page.edges[0].isVisible() and own_page.edges[1].isVisible())

    def test_a_view_on_a_transparent_ground_fades_into_the_colour_of_its_rows(self):
        """The checks' rows are drawn on the theme's card while the view's own ground is transparent in its dock: the
        bands took that ground's Base (black) until set_ground told them the rows' colour."""
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

        from meridiana.ui import fades
        tree = QTreeWidget()
        self.addCleanup(tree.deleteLater)
        for i in range(60):
            QTreeWidgetItem(tree, [f"verifica {i}"])
        tree.setStyleSheet("QTreeWidget { background: transparent; }")
        tree.resize(300, 200)
        tree.show()
        f = fades.attach(tree, table=True)
        fades.set_ground(tree, "#fafafa")
        tree.verticalScrollBar().setValue(10)
        self.app.processEvents()
        image = f.edges[0].grab().toImage()
        edge = QColor(image.pixel(image.width() // 2, 0))
        self.assertGreater(edge.lightness(), 200, edge.name())          # the rows' colour, not black


    def test_a_list_can_take_the_pages_fade(self):
        """The checks fade as the right panels and the report (Daniel, 30/10/2026: «quell'effetto lì»): a list
        attached with page_list gets the pages' curve; a list without it keeps the lists' lighter one."""
        from PySide6.QtWidgets import QTreeWidget

        from meridiana.ui import fades
        plain, paged = QTreeWidget(), QTreeWidget()
        for view in (plain, paged):
            self.addCleanup(view.deleteLater)
        self.assertFalse(fades.attach(plain, air=True).edges[0].page)
        self.assertTrue(fades.attach(paged, air=True, page_list=True).edges[0].page)

if __name__ == "__main__":
    unittest.main()
