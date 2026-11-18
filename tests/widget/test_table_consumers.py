"""Data views created after the main window receive the common treatment without navigation changes."""

import unittest
from types import SimpleNamespace

import _setup
from meridiana import catalog
from meridiana.ui import charts, shared_tables
from meridiana.ui.catalog_dialog import CatalogDialog
from meridiana.ui.shortcuts_dialog import ShortcutsEditor
from meridiana.ui.variants import VariantsDialog

setUpModule = _setup.keep_global_state


class TableConsumers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        catalog.prepare("modules")

    def treated(self, view):
        controller = view.findChild(shared_tables.TableStyle)
        self.assertIsNotNone(controller)
        self.assertTrue(view.alternatingRowColors())
        self.assertIs(shared_tables.install(view), controller)

    def test_catalogue_dialog_preserves_its_proxy_model_and_sort_contract(self):
        dialog = CatalogDialog("modules")
        self.addCleanup(_setup.dispose, dialog)
        self.treated(dialog.table)
        self.assertIs(dialog.table.model(), dialog.rows)
        self.assertIs(dialog.rows.sourceModel(), dialog.model)
        self.assertTrue(dialog.table.isSortingEnabled())
        self.assertEqual(dialog.table.horizontalHeader().sortIndicatorSection(), -1)

    def test_chart_table_is_treated_before_its_columns_are_filled(self):
        chart = charts.Chart("Example chart")
        self.addCleanup(_setup.dispose, chart)
        self.assertEqual(chart.table.columnCount(), 0)
        self.treated(chart.table)
        chart._set_table(charts.Table(["Month", "Energy"], [["January", 100]]))
        chart.toggle.setChecked(True)
        self.assertEqual(chart.table.columnCount(), 2)
        self.assertEqual(chart.table.item(0, 0).text(), "January")
        self.treated(chart.table)

    def test_variant_comparison_keeps_its_rows_and_columns(self):
        dialog = VariantsDialog([("a", "Base"), ("b", "Alternative")], lambda _vid: {},
                                pool=SimpleNamespace(start=lambda _job: None))
        self.addCleanup(_setup.dispose, dialog)
        self.treated(dialog.table)
        self.assertEqual(dialog.ids, ["a", "b"])
        self.assertEqual(dialog.table.columnCount(), 2)

    def test_shortcuts_editor_keeps_its_three_columns_and_commands(self):
        editor = ShortcutsEditor({})
        self.addCleanup(_setup.dispose, editor)
        self.treated(editor.tree)
        self.assertEqual(editor.tree.columnCount(), 3)
        self.assertGreater(editor.tree.topLevelItemCount(), 20)
