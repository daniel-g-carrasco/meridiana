"""Explicit physical optimizer groups, preserving the order of the drawn string."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPushButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from ..energy.optimizers import module_groups
from ..i18n import _


class OptimizerGroupsDialog(QDialog):
    def __init__(self, modules: list[str], per: int, sizes: list[int] | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Modules on each optimizer"))
        self.resize(560, 480)
        self.per = per
        self.modules = list(modules)
        self.loading = False
        box = QVBoxLayout(self)
        help_text = QLabel(_("Check a module to connect it to the same optimizer as the previous module. "
                            "Modules on one optimizer share its MPPT and must have the same type, orientation and tilt."))
        help_text.setWordWrap(True)
        box.addWidget(help_text)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([_("Join to previous module"), _("Optimizer")])
        self.tree.setRootIsDecorated(False)
        for i, key in enumerate(self.modules):
            row = QTreeWidgetItem([_("Module {n}").format(n=i + 1), ""])
            row.setToolTip(0, key)
            row.setFlags(row.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            row.setCheckState(0, Qt.CheckState.Unchecked)
            if i and per == 2:
                row.setFlags(row.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            else:
                row.setFlags(row.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.tree.addTopLevelItem(row)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, self.tree.header().ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, self.tree.header().ResizeMode.ResizeToContents)
        box.addWidget(self.tree, 1)
        presets = QHBoxLayout()
        for text, size in ((_("One module each"), 1), (_("Pairs in string order"), per)):
            button = QPushButton(text)
            button.clicked.connect(lambda _checked=False, n=size: self._set_groups(
                [len(g) for g in module_groups(self.modules, n)]))
            presets.addWidget(button)
        box.addLayout(presets)
        self.message = QLabel()
        self.message.setWordWrap(True)
        box.addWidget(self.message)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        box.addWidget(self.buttons)
        self.tree.itemChanged.connect(self._changed)
        try:
            groups = module_groups(self.modules, per, sizes)
        except ValueError:
            # Opening a malformed saved partition never silently accepts a replacement.
            groups = [[m] for m in self.modules]
        self._set_groups([len(g) for g in groups])

    def _set_groups(self, sizes: list[int]) -> None:
        self.loading = True
        starts, offset = set(), 0
        for n in sizes:
            starts.add(offset)
            offset += n
        for i in range(1, len(self.modules)) if self.per == 2 else ():
            self.tree.topLevelItem(i).setCheckState(
                0, Qt.CheckState.Unchecked if i in starts else Qt.CheckState.Checked)
        self.loading = False
        self._changed()

    def group_sizes(self) -> list[int]:
        sizes = []
        for i in range(len(self.modules)):
            joined = i and self.tree.topLevelItem(i).checkState(0) == Qt.CheckState.Checked
            if joined:
                sizes[-1] += 1
            else:
                sizes.append(1)
        return sizes

    def _changed(self, *_args) -> None:
        if self.loading:
            return
        sizes = self.group_sizes()
        valid = all(n <= self.per for n in sizes)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(valid)
        self.message.setText(_("{n} optimizers for {m} modules").format(n=len(sizes), m=len(self.modules))
                             if valid else _("An optimizer cannot take more than {n} modules.").format(n=self.per))
        self.loading = True
        offset = 0
        for group, count in enumerate(sizes, 1):
            for row in range(offset, offset + count):
                self.tree.topLevelItem(row).setText(1, str(group))
            offset += count
        self.loading = False
