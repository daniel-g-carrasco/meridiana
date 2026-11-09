"""What the plan as a DXF holds and in which coordinates (R513): asked after the file, before the job. The frames come
from dxf_export.frame_choices (one that cannot be used is off, with why in its tip), the parts from
dxf_export.part_names; the last choice of the session is proposed again."""

from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QGroupBox, QLabel, QRadioButton,
                               QVBoxLayout)

from ..i18n import _


class DxfOptionsDialog(QDialog):
    def __init__(self, frames: list[dict], parts: dict, last=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Export the plan as DXF"))
        box = QVBoxLayout(self)
        where = QGroupBox(_("Coordinates"))
        rows = QVBoxLayout(where)
        self.frames = QButtonGroup(self)
        self.keys = []
        wanted = last[0] if last else "local"
        for i, f in enumerate(frames):
            button = QRadioButton(f["text"])
            button.setObjectName(f"frame-{f['key']}")
            button.setEnabled(bool(f["enabled"]))
            if not f["enabled"] and f.get("why"):
                button.setToolTip(f["why"])
            self.frames.addButton(button, i)
            self.keys.append(f["key"])
            rows.addWidget(button)
            if f["key"] == wanted and f["enabled"]:
                button.setChecked(True)
        if self.frames.checkedButton() is None:
            self.frames.button(0).setChecked(True)
        note = QLabel(_("The unit is written in the file: metres, or the drawing's own. The dimensions read in "
                        "metres."))
        note.setWordWrap(True)
        rows.addWidget(note)
        box.addWidget(where)
        what = QGroupBox(_("What goes in the plan"))
        lines = QVBoxLayout(what)
        self.parts = {}
        chosen = set(last[1]) if last else set(parts)
        for key, text in parts.items():
            check = QCheckBox(text)
            check.setObjectName(f"part-{key}")
            check.setChecked(key in chosen)
            lines.addWidget(check)
            self.parts[key] = check
        box.addWidget(what)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(_("Export"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        for check in self.parts.values():
            check.toggled.connect(lambda _on: buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
                any(c.isChecked() for c in self.parts.values())))
        box.addWidget(buttons)

    def choice(self) -> tuple[str, tuple]:
        """(the frame's key, the parts asked)."""
        return self.keys[self.frames.checkedId()], tuple(k for k, c in self.parts.items() if c.isChecked())
