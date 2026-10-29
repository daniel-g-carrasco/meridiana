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
        before = self.table.styleSheet()
        dark = _setup.meridiana_look("dark")
        self.app.processEvents()
        self.app.processEvents()
        self.assertNotEqual(before, self.table.styleSheet())
        self.assertIn(shared_tables.band_colour(self.app.palette()), self.table.styleSheet())
        self.assertIs(self.table.findChild(shared_tables.TableStyle), controller)
        theme.apply()
        dark.deleteLater()


if __name__ == "__main__":
    unittest.main()
