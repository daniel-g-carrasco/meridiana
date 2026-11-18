"""Selective shared table styling keeps navigation and custom delegates intact."""

import unittest

import _setup
from PySide6.QtGui import QFont, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QStyledItemDelegate, QTableView, QTreeWidget, QWidget

from meridiana.ui import shared_tables

setUpModule = _setup.keep_global_state


class SharedTables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.root = QWidget()
        self.addCleanup(_setup.dispose, self.root)
        self.table = QTableView(self.root)
        self.model = QStandardItemModel(2, 2, self.table)
        for row in range(2):
            self.model.setItem(row, 0, QStandardItem("Synthetic"))
            self.model.setItem(row, 1, QStandardItem("111,11"))
        self.table.setModel(self.model)
        self.delegate = QStyledItemDelegate(self.table)
        self.table.setItemDelegateForColumn(1, self.delegate)

    def test_only_data_tables_receive_style_and_custom_delegate_stays(self):
        navigation = QTreeWidget(self.root)
        navigation.setColumnCount(2)
        navigation.setObjectName("project-tree")
        navigation.setHeaderHidden(True)
        checks = QTreeWidget(self.root)
        checks.setColumnCount(2)
        checks.setObjectName("checks-tree")
        hidden = QTreeWidget(self.root)
        hidden.setColumnCount(2)
        hidden.setHeaderHidden(True)
        single = QTreeWidget(self.root)
        single.setColumnCount(1)
        installed = shared_tables.install_data_tables(self.root, excluded=("project-tree", "checks-tree"))
        self.assertEqual(len(installed), 1)
        self.assertIs(self.table.itemDelegateForColumn(1), self.delegate)
        self.assertEqual(self.table.font().featureValue(QFont.Tag("tnum")), 1)
        for excluded in (navigation, checks, hidden, single):
            self.assertIsNone(excluded.findChild(shared_tables.TableStyle))
        self.assertEqual(shared_tables.install_data_tables(self.root, excluded=("project-tree", "checks-tree")), installed)

    def test_existing_tables_follow_light_and_dark_palette(self):
        theme = _setup.meridiana_look("light")
        controller, = shared_tables.install_data_tables(self.root, excluded=("project-tree", "checks-tree"))
        # the rules are in the application's sheet, under the views marked `ptable`: no sheet on the table itself
        # (19 of them cost 1.2 s of each change of theme)
        self.assertEqual(self.table.styleSheet(), "")
        self.assertEqual(self.table.property("ptable"), "true")
        before = self.app.styleSheet()
        self.assertIn(shared_tables.band_colour(self.app.palette()), before)
        _setup.meridiana_look("dark")
        self.app.processEvents()
        self.app.processEvents()
        self.assertNotEqual(before, self.app.styleSheet())
        self.assertIn(shared_tables.band_colour(self.app.palette()), self.app.styleSheet())
        self.assertEqual(self.table.styleSheet(), "")
        self.assertIs(self.table.findChild(shared_tables.TableStyle), controller)
        theme.apply()
        # _setup owns cached themes: deleting one leaves later modules a dead C++ wrapper.

    def test_the_equal_width_figures_come_back_when_the_font_is_made_again(self):
        """The application's sheet makes the view's font again as it polishes the view: the figures lost `tnum`, and
        the numbers stopped lining up (found by Quotario, 03/11/2026)."""
        from PySide6.QtWidgets import QApplication
        view = QTableView(self.root)
        self.addCleanup(view.deleteLater)
        model = QStandardItemModel(1, 1, view)
        model.setItem(0, 0, QStandardItem("1"))
        view.setModel(model)
        shared_tables.install(view)
        tag = QFont.Tag("tnum")
        self.assertEqual(view.font().featureValue(tag), 1)
        plain = QFont(view.font())
        plain.unsetFeature(tag)
        view.setFont(plain)
        for _round in range(4):
            QApplication.processEvents()
        self.assertEqual(view.font().featureValue(tag), 1)


if __name__ == "__main__":
    unittest.main()
