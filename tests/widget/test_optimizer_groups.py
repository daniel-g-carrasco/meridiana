"""Physical grouping edits cannot accidentally connect three modules to a dual optimizer."""
import unittest
import _setup

setUpModule = _setup.keep_global_state


class Groups(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_groups_roundtrip_and_three_modules_are_not_accepted(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDialogButtonBox
        from meridiana.ui.optimizer_groups import OptimizerGroupsDialog
        dialog = OptimizerGroupsDialog(list('abcde'), 2, [2, 1, 2])
        self.addCleanup(dialog.close)
        self.assertEqual(dialog.group_sizes(), [2, 1, 2])
        dialog.tree.topLevelItem(2).setCheckState(0, Qt.CheckState.Checked)
        self.assertEqual(dialog.group_sizes(), [3, 2])
        self.assertFalse(dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled())
        dialog.tree.topLevelItem(1).setCheckState(0, Qt.CheckState.Unchecked)
        self.assertEqual(dialog.group_sizes(), [1, 2, 2])
        self.assertTrue(dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled())

    def test_single_module_optimizers_cannot_be_joined(self):
        from PySide6.QtCore import Qt
        from meridiana.ui.optimizer_groups import OptimizerGroupsDialog
        dialog = OptimizerGroupsDialog(list('abc'), 1)
        self.addCleanup(dialog.close)
        self.assertEqual(dialog.group_sizes(), [1, 1, 1])
        self.assertFalse(dialog.tree.topLevelItem(1).flags() & Qt.ItemFlag.ItemIsUserCheckable)
